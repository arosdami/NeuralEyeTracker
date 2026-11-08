# core/tracker_thread.py
# Valós idejű okulometriai és pupillometriai feldolgozószál
# Tobii Pro Lab & Clinical Standard annotációs motor

import os
import time
import math
import cv2
import numpy as np
from collections import deque
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

from core.pupil_detector import PupilDetector
from core.neural_model import NeuralGazeModel


# ---------- KUTATÓI SZÍNPALETTA (BGR formátum OpenCV-hez) ----------
# Tompa, funkcionális színek (nem neon!)
COLOR_PRIMARY_BLUE = (240, 140, 45)     # Tobii orvosi kék (#2d8cf0 BGR-ben)
COLOR_SUCCESS_GREEN = (80, 185, 63)     # Tompa mérnöki zöld
COLOR_WARNING_AMBER = (34, 153, 210)    # Figyelmeztető borostyán
COLOR_WHITE_MUTED = (210, 210, 215)     # Finom szürke/fehér
COLOR_EYE_CONTOUR = (220, 160, 60)      # Acélkék szemrés kontúr

STYLE_COLORS = {
    1: COLOR_WHITE_MUTED,     # Minimal Point
    2: COLOR_PRIMARY_BLUE,    # Precision Crosshair
    3: COLOR_SUCCESS_GREEN,   # Calibrated Ring
    4: COLOR_PRIMARY_BLUE,    # Fitted Ellipse
    5: COLOR_WARNING_AMBER,   # Gaze Vector
}


# ============================================================
# NEURÁLIS SZEMRÉS-SZAPORÍTÓ HÁLÓ (Almond Shape MLP)
# ============================================================
class AlmondShapeNet:
    """
    Kompakt MLP, ami 8 strukturális jellemzőből becsüli meg a szemrés
    (palpebral fissure) 4 anatómiai referenciapontját.
    """

    def __init__(self, input_dim=8, hidden=32, output_dim=4):
        self.input_dim = input_dim
        self.hidden = hidden
        self.output_dim = output_dim

        rng = np.random.default_rng(42)
        self.W1 = rng.normal(0, math.sqrt(2.0 / input_dim), (input_dim, hidden)).astype(np.float32)
        self.b1 = np.zeros(hidden, dtype=np.float32)
        self.W2 = rng.normal(0, math.sqrt(2.0 / hidden), (hidden, output_dim)).astype(np.float32)
        self.b2 = np.zeros(output_dim, dtype=np.float32)

        self.lr = 0.001
        self.trained_samples = 0

        self._feat_mean = np.zeros(input_dim, dtype=np.float32)
        self._feat_std = np.ones(input_dim, dtype=np.float32)
        self._alpha_norm = 0.01

    def _normalize(self, x):
        return (x - self._feat_mean) / (self._feat_std + 1e-6)

    def _update_norm_stats(self, x):
        self._feat_mean = (1 - self._alpha_norm) * self._feat_mean + self._alpha_norm * x
        self._feat_std = (1 - self._alpha_norm) * self._feat_std + self._alpha_norm * np.abs(x - self._feat_mean)

    def _forward(self, x):
        z1 = x @ self.W1 + self.b1
        a1 = np.tanh(z1)
        z2 = a1 @ self.W2 + self.b2
        return z2, a1

    def predict(self, x):
        x = np.asarray(x, dtype=np.float32).flatten()
        xn = self._normalize(x)
        out, _ = self._forward(xn)
        return 1.0 / (1.0 + np.exp(-out))

    def train_step(self, x, y_target):
        x = np.asarray(x, dtype=np.float32).flatten()
        y = np.asarray(y_target, dtype=np.float32).flatten()

        self._update_norm_stats(x)
        xn = self._normalize(x)

        z1 = xn @ self.W1 + self.b1
        a1 = np.tanh(z1)
        z2 = a1 @ self.W2 + self.b2
        y_hat = 1.0 / (1.0 + np.exp(-z2))

        dL_dy = (y_hat - y) * y_hat * (1 - y_hat) * 2.0 / self.output_dim
        dW2 = np.outer(a1, dL_dy)
        db2 = dL_dy
        da1 = dL_dy @ self.W2.T
        dz1 = da1 * (1 - a1 * a1)
        dW1 = np.outer(xn, dz1)
        db1 = dz1

        self.W2 -= self.lr * dW2
        self.b2 -= self.lr * db2
        self.W1 -= self.lr * dW1
        self.b1 -= self.lr * db1

        self.trained_samples += 1
        return float(np.mean((y_hat - y) ** 2))


# ============================================================
# SZEMRÉS KÖVETŐ MODUL
# ============================================================
class AlmondEyeTracker:
    def __init__(self):
        self.net = AlmondShapeNet()
        self.last_shape = None
        self.shape_history = deque(maxlen=8)
        self.loss_history = deque(maxlen=50)

    def _extract_features(self, gray, pupil_cx, pupil_cy, pupil_r):
        H, W = gray.shape[:2]
        eps = 1e-6

        mean_val = float(np.mean(gray)) / 255.0
        std_val = float(np.std(gray)) / 255.0

        try:
            edges = cv2.Canny(gray, 40, 100)
            edge_density = float(np.count_nonzero(edges)) / (H * W + eps)
        except Exception:
            edge_density = 0.0

        aspect = W / (H + eps)

        try:
            _, dark = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
            dark_ratio = float(np.count_nonzero(dark)) / (H * W + eps)
        except Exception:
            dark_ratio = 0.0

        return np.array([
            pupil_cx / (W + eps),
            pupil_cy / (H + eps),
            pupil_r / (W + eps),
            mean_val,
            std_val,
            edge_density,
            aspect,
            dark_ratio,
        ], dtype=np.float32)

    def _find_almond_corners(self, gray, pupil_cx, pupil_cy, pupil_r):
        H, W = gray.shape[:2]
        try:
            edges = cv2.Canny(gray, 30, 90)
            edges = cv2.morphologyEx(
                edges, cv2.MORPH_CLOSE,
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
                iterations=2
            )
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        except Exception:
            return None

        if not contours:
            return None

        best = None
        best_score = -1.0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 200 or area > W * H * 0.95:
                continue

            try:
                M = cv2.moments(cnt)
                if M["m00"] < 1e-6:
                    continue
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
            except Exception:
                continue

            d = math.hypot(cx - pupil_cx, cy - pupil_cy)
            size_score = min(area / 5000.0, 1.0)
            score = size_score - d / (W + 1e-6)
            if score > best_score:
                best_score = score
                best = cnt

        if best is None:
            return None

        pts = best.reshape(-1, 2)
        left = pts[int(np.argmin(pts[:, 0]))]
        right = pts[int(np.argmax(pts[:, 0]))]
        top = pts[int(np.argmin(pts[:, 1]))]
        bot = pts[int(np.argmax(pts[:, 1]))]

        def norm(p):
            return np.array([p[0] / (W + 1e-6), p[1] / (H + 1e-6)], dtype=np.float32)

        return (norm(left), norm(top), norm(right), norm(bot))

    def update(self, gray, pupil_cx, pupil_cy, pupil_r):
        H, W = gray.shape[:2]
        feat = self._extract_features(gray, pupil_cx, pupil_cy, pupil_r)
        pred = self.net.predict(feat)
        gt = self._find_almond_corners(gray, pupil_cx, pupil_cy, pupil_r)

        if gt is not None:
            gt_flat = np.concatenate([p for p in gt])
            loss = self.net.train_step(feat, gt_flat)
            self.loss_history.append(loss)

        if gt is not None and self.net.trained_samples < 50:
            shape_norm = np.concatenate([p for p in gt])
        else:
            shape_norm = pred

        left = (shape_norm[0] * W, shape_norm[1] * H)
        top = (shape_norm[2] * W, shape_norm[3] * H)
        right = (shape_norm[4] * W, shape_norm[5] * H)
        bot = (shape_norm[6] * W, shape_norm[7] * H)

        if self.last_shape is not None:
            a = 0.5
            left = self._blend(self.last_shape[0], left, a)
            top = self._blend(self.last_shape[1], top, a)
            right = self._blend(self.last_shape[2], right, a)
            bot = self._blend(self.last_shape[3], bot, a)

        self.last_shape = (left, top, right, bot)
        self.shape_history.append(self.last_shape)
        return self._build_almond_contour(left, top, right, bot)

    @staticmethod
    def _blend(p1, p2, a):
        return (p1[0] * (1 - a) + p2[0] * a, p1[1] * (1 - a) + p2[1] * a)

    @staticmethod
    def _build_almond_contour(left, top, right, bot, n=24):
        pts = []
        for i in range(n):
            t = i / (n - 1)
            x = (1 - t) ** 2 * left[0] + 2 * (1 - t) * t * top[0] + t ** 2 * right[0]
            y = (1 - t) ** 2 * left[1] + 2 * (1 - t) * t * top[1] + t ** 2 * right[1]
            pts.append((x, y))

        for i in range(n):
            t = i / (n - 1)
            x = (1 - t) ** 2 * right[0] + 2 * (1 - t) * t * bot[0] + t ** 2 * left[0]
            y = (1 - t) ** 2 * right[1] + 2 * (1 - t) * t * bot[1] + t ** 2 * left[1]
            pts.append((x, y))

        return np.array(pts, dtype=np.int32).reshape(-1, 1, 2)


# ============================================================
# KÖVETŐ SZÁL (TRACKER THREAD)
# ============================================================
class TrackerThread(QThread):
    frame_ready = pyqtSignal(np.ndarray, dict)
    status = pyqtSignal(str)
    fps_update = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.running = False
        self.camera_idx = 0
        self.video_path = None
        self.flip_h = True
        self.flip_v = False
        self.detector = PupilDetector()
        self.neural_model = NeuralGazeModel()
        self.almond_tracker = AlmondEyeTracker()
        self.last_raw_data = {}
        self.fps_buf = deque(maxlen=60)

        self._mutex = QMutex()
        self._is_tracking = False
        self._blink_frames = 0

        # Alapértelmezett: 2-es (Precision Crosshair)
        self.pupil_style = 2

        self.display = {
            "cx": 320.0, "cy": 240.0,
            "confidence": 0.0,
            "pupil_size": 1.0,
            "draw_ellipse": None,
            "draw_offset": (0, 0),
            "detected": False,
            "neural_az": 0.0,
            "neural_el": 0.0,
            "radius_px": 0.0,
            "almond_contour": None,
        }

        self.DISPLAY_ALPHA = 0.85
        self.ELLIPSE_ALPHA = 0.75
        self.RADIUS_ALPHA = 0.12
        self.RADIUS_DEADZONE = 0.3
        self._radius_history = deque(maxlen=20)

        self.PUPIL_SIZE_ALPHA = 0.05
        self.PUPIL_SIZE_DEADZONE = 0.015
        self._pupil_size_history = deque(maxlen=20)

        self._last_process_time = 0.0

        # Kálmán szűrés
        self._kalman_x = 320.0
        self._kalman_y = 240.0
        self._kalman_vx = 0.0
        self._kalman_vy = 0.0
        self._kalman_pxx = 50.0
        self._kalman_pyy = 50.0
        self._kalman_q = 0.004
        self._kalman_r = 5.0
        self._last_kalman_time = time.time()

    def set_camera(self, idx):
        self.camera_idx = idx
        self.video_path = None

    def set_video_path(self, path):
        self.video_path = path

    def set_pupil_style(self, style):
        try:
            s = int(style)
            if 1 <= s <= 5:
                self.pupil_style = s
        except Exception:
            pass

    def stop(self):
        with QMutexLocker(self._mutex):
            self.running = False

    def _open_capture(self):
        if self.video_path:
            if not os.path.exists(self.video_path):
                return None
            for backend in [cv2.CAP_FFMPEG, cv2.CAP_ANY]:
                try:
                    cap = cv2.VideoCapture(str(self.video_path), backend)
                    if cap.isOpened():
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            return cap
                        cap.release()
                except Exception:
                    pass
            return None

        for cam_idx in [self.camera_idx, 0]:
            for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
                try:
                    cap = cv2.VideoCapture(cam_idx, backend)
                    if cap.isOpened():
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            return cap
                        cap.release()
                except Exception:
                    pass
        return None

    def _kalman_update(self, mx, my, dt):
        self._kalman_x += self._kalman_vx * dt
        self._kalman_y += self._kalman_vy * dt
        self._kalman_pxx += self._kalman_q
        self._kalman_pyy += self._kalman_q

        if mx is not None and my is not None:
            kx = self._kalman_pxx / (self._kalman_pxx + self._kalman_r)
            ky = self._kalman_pyy / (self._kalman_pyy + self._kalman_r)

            self._kalman_vx = (mx - self._kalman_x) / max(dt, 0.001) * 0.35
            self._kalman_vy = (my - self._kalman_y) / max(dt, 0.001) * 0.35
            self._kalman_x += kx * (mx - self._kalman_x)
            self._kalman_y += ky * (my - self._kalman_y)

            self._kalman_pxx *= (1 - kx)
            self._kalman_pyy *= (1 - ky)

        return self._kalman_x, self._kalman_y

    def _smooth_val(self, cur, target, alpha):
        return cur * (1 - alpha) + target * alpha

    def _smooth_ellipse(self, cur, target, alpha):
        if cur is None: return target
        if target is None: return cur
        (cx1, cy1), (w1, h1), a1 = cur
        (cx2, cy2), (w2, h2), a2 = target
        cx = self._smooth_val(cx1, cx2, alpha)
        cy = self._smooth_val(cy1, cy2, alpha)
        w = self._smooth_val(w1, w2, alpha)
        h = self._smooth_val(h1, h2, alpha)
        diff = a2 - a1
        while diff > 180: diff -= 360
        while diff < -180: diff += 360
        return ((cx, cy), (w, h), a1 + diff * alpha)

    def run(self):
        self.running = True
        cap = self._open_capture()
        if cap is None:
            self.status.emit("HIBA: Bemeneti jelfolyam nem elérhető")
            return

        self.status.emit("Szenzor aktív")
        t_prev = time.time()
        frame_no = 0

        try:
            while self.running:
                ret, frame = cap.read()
                if not ret or frame is None:
                    if self.video_path:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                        if not ret or frame is None:
                            self.msleep(5)
                            continue
                    else:
                        self.msleep(5)
                        continue

                if self.flip_h:
                    frame = cv2.flip(frame, 1)
                if self.flip_v:
                    frame = cv2.flip(frame, 0)
                frame = cv2.resize(frame, (640, 480))

                now = time.time()
                dt = now - self._last_kalman_time
                if dt <= 0 or dt > 0.5:
                    dt = 0.033
                self._last_kalman_time = now

                if (now - self._last_process_time) >= 0.020:
                    self._last_process_time = now

                    result = self.detector.detect(frame)
                    self.last_raw_data = result.get("raw_data", {})

                    raw_conf = result.get("confidence", 0.0)
                    detected = result.get("detected", False)
                    raw_cx = result.get("cx", 320)
                    raw_cy = result.get("cy", 240)
                    raw_size = result.get("pupil_size", 1.0)
                    raw_ellipse = result.get("draw_ellipse", None)
                    raw_offset = result.get("draw_offset", (0, 0))
                    raw_radius = result.get("radius_px", 0.0)

                    # Pislogás detektálás
                    if not detected or raw_conf < 0.15:
                        self._blink_frames += 1
                    else:
                        self._blink_frames = 0
                    self._is_tracking = (self._blink_frames < 4 and raw_conf > 0.15)

                    # Kálmán állapotfrissítés
                    if detected and raw_conf > 0.2:
                        kx, ky = self._kalman_update(raw_cx, raw_cy, dt)
                    else:
                        kx, ky = self._kalman_update(None, None, dt)

                    self.display["cx"] = self._smooth_val(self.display["cx"], kx, self.DISPLAY_ALPHA)
                    self.display["cy"] = self._smooth_val(self.display["cy"], ky, self.DISPLAY_ALPHA)
                    self.display["confidence"] = self._smooth_val(self.display["confidence"], raw_conf, self.DISPLAY_ALPHA)

                    # Pupillaméret és szűrés
                    if abs(raw_size - self.display["pupil_size"]) > self.PUPIL_SIZE_DEADZONE:
                        self._pupil_size_history.append(raw_size)
                        med_s = float(np.median(self._pupil_size_history))
                        self.display["pupil_size"] = self._smooth_val(self.display["pupil_size"], med_s, self.PUPIL_SIZE_ALPHA)

                    self.display["draw_ellipse"] = self._smooth_ellipse(self.display["draw_ellipse"], raw_ellipse, self.ELLIPSE_ALPHA)
                    self.display["draw_offset"] = raw_offset
                    self.display["detected"] = self._is_tracking

                    # Sugár simítás
                    if detected and 3.0 <= raw_radius <= 200.0:
                        self._radius_history.append(raw_radius)
                        med_r = float(np.median(self._radius_history))
                        self.display["radius_px"] = self._smooth_val(self.display["radius_px"], med_r, self.RADIUS_ALPHA)

                    # Szemrés leképezés (Almond tracker)
                    try:
                        ox, oy = raw_offset
                        rx = max(0, int(raw_cx - ox - 80))
                        ry = max(0, int(raw_cy - oy - 60))
                        rx2 = min(frame.shape[1], int(raw_cx - ox + 80))
                        ry2 = min(frame.shape[0], int(raw_cy - oy + 60))

                        if rx2 - rx > 20 and ry2 - ry > 20:
                            roi_gray = cv2.cvtColor(frame[ry:ry2, rx:rx2], cv2.COLOR_BGR2GRAY)
                            contour = self.almond_tracker.update(
                                roi_gray, raw_cx - ox - rx, raw_cy - oy - ry, max(1.0, raw_radius)
                            )
                            if contour is not None:
                                self.display["almond_contour"] = contour + np.array([[[rx, ry]]], dtype=np.int32)
                    except Exception:
                        pass

                    # Neurális szög becslés
                    if self.neural_model.is_trained and self._is_tracking:
                        az, el = self.neural_model.predict(self.last_raw_data)
                    else:
                        az = (self.display["cx"] - 320) / 320 * 40.0
                        el = -(self.display["cy"] - 240) / 240 * 30.0
                    self.display["neural_az"] = az
                    self.display["neural_el"] = el

                # Letisztult orvostechnikai annotálás
                self._annotate(frame, self.display)
                self.frame_ready.emit(frame, self.display)

                t_now = time.time()
                dt_fps = t_now - t_prev
                if dt_fps > 0:
                    self.fps_buf.append(1.0 / dt_fps)
                t_prev = t_now

                if frame_no % 25 == 0:
                    self.fps_update.emit(float(np.mean(self.fps_buf)) if self.fps_buf else 0.0)

                frame_no += 1
                self.msleep(15)

        except Exception as exc:
            self.status.emit(f"Hiba: {exc}")
        finally:
            cap.release()

    # ==========================================================
    # ANNOTÁLÁS: Diszkrét kutatói rétegek (Tobii Pro Lab stílus)
    # ==========================================================
    def _annotate(self, frame, result):
        try:
            # 1. Szemrés (Palpebral fissure) kontúr – szolid, vékony vonal
            almond = result.get("almond_contour")
            if almond is not None and len(almond) > 4:
                cv2.polylines(frame, [almond], True, COLOR_EYE_CONTOUR, 1, cv2.LINE_AA)

            # 2. Pupilla mérési jelek (Kutatói stílusok)
            ell = result.get("draw_ellipse")
            tracking = bool(result.get("detected", False))
            er = int(result.get("radius_px", 0))
            conf = float(result.get("confidence", 0.0))
            ox, oy = result.get("draw_offset", (0, 0))

            if ell is not None and er < 3:
                try:
                    er = max(4, int((ell[1][0] + ell[1][1]) / 4.0))
                except Exception:
                    er = 0

            if ell is not None and tracking and er >= 3:
                pupil_ellipse = ((ell[0][0] + ox, ell[0][1] + oy), ell[1], ell[2])
                ecx = int(pupil_ellipse[0][0])
                ecy = int(pupil_ellipse[0][1])

                color = STYLE_COLORS.get(self.pupil_style, COLOR_PRIMARY_BLUE)

                if self.pupil_style == 1:
                    self._draw_minimal_point(frame, ecx, ecy, er, conf, color, pupil_ellipse)
                elif self.pupil_style == 2:
                    self._draw_precision_crosshair(frame, ecx, ecy, er, conf, color, pupil_ellipse)
                elif self.pupil_style == 3:
                    self._draw_calibrated_ring(frame, ecx, ecy, er, conf, color, pupil_ellipse)
                elif self.pupil_style == 4:
                    self._draw_fitted_axes(frame, ecx, ecy, er, conf, color, pupil_ellipse)
                elif self.pupil_style == 5:
                    self._draw_gaze_vector_target(frame, ecx, ecy, er, conf, color, pupil_ellipse)

            # 3. Diszkrét alsó telemetria-sáv
            self._draw_bottom_telemetry(frame, result, conf, tracking)

        except Exception as e:
            print(f"[ANNOTATE] Hiba: {e}")

    # ==========================================================
    # LETISZTULT TELEMETRIA SÁV (Képernyő alján, nem zavar)
    # ==========================================================
    def _draw_bottom_telemetry(self, frame, result, conf, tracking):
        H, W = frame.shape[:2]
        bar_h = 24

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, H - bar_h), (W, H), (20, 20, 22), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.38
        th = 1

        cx = int(result.get("cx", 0))
        cy = int(result.get("cy", 0))
        r = float(result.get("radius_px", 0.0))

        # Státusz jelzés
        status_text = "LOCK" if tracking else "SEARCH"
        status_color = COLOR_SUCCESS_GREEN if tracking else COLOR_WARNING_AMBER
        cv2.putText(frame, status_text, (8, H - 7), font, scale, status_color, th, cv2.LINE_AA)

        # Telemetria adatok
        info_str = f"| POS: ({cx:3d}, {cy:3d}) | R: {r:4.1f}px | CONF: {conf:4.2f}"
        cv2.putText(frame, info_str, (60, H - 7), font, scale, COLOR_WHITE_MUTED, th, cv2.LINE_AA)

    # ==========================================================
    # STÍLUS 1: MINIMAL POINT (Klinikai alappont)
    # ==========================================================
    def _draw_minimal_point(self, frame, cx, cy, r, conf, color, pupil_ellipse):
        cv2.ellipse(frame, pupil_ellipse, (120, 120, 125), 1, cv2.LINE_AA)
        cv2.drawMarker(frame, (cx, cy), color, cv2.MARKER_CROSS, 8, 1, cv2.LINE_AA)

    # ==========================================================
    # STÍLUS 2: PRECISION CROSSHAIR (Tobii standard szálkereszt)
    # ==========================================================
    def _draw_precision_crosshair(self, frame, cx, cy, r, conf, color, pupil_ellipse):
        cv2.ellipse(frame, pupil_ellipse, color, 1, cv2.LINE_AA)

        # Diszkrét szálkereszt túllógással
        arm = int(r + 6)
        gap = 3
        # Vízszintes
        cv2.line(frame, (cx - arm, cy), (cx - gap, cy), color, 1, cv2.LINE_AA)
        cv2.line(frame, (cx + gap, cy), (cx + arm, cy), color, 1, cv2.LINE_AA)
        # Függőleges
        cv2.line(frame, (cx, cy - arm), (cx, cy - gap), color, 1, cv2.LINE_AA)
        cv2.line(frame, (cx, cy + gap), (cx, cy + arm), color, 1, cv2.LINE_AA)

        cv2.circle(frame, (cx, cy), 1, (255, 255, 255), -1, cv2.LINE_AA)

    # ==========================================================
    # STÍLUS 3: CALIBRATED RING (Mérőgyűrű)
    # ==========================================================
    def _draw_calibrated_ring(self, frame, cx, cy, r, conf, color, pupil_ellipse):
        cv2.ellipse(frame, pupil_ellipse, color, 1, cv2.LINE_AA)
        # Koncentrikus mérőzóna
        cv2.circle(frame, (cx, cy), max(2, int(r * 0.5)), (140, 140, 145), 1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 2, color, -1, cv2.LINE_AA)

    # ==========================================================
    # STÍLUS 4: FITTED AXES (Fő- és kistengely orientáció)
    # ==========================================================
    def _draw_fitted_axes(self, frame, cx, cy, r, conf, color, pupil_ellipse):
        cv2.ellipse(frame, pupil_ellipse, color, 1, cv2.LINE_AA)

        (_, _), (w, h), angle = pupil_ellipse
        rad = math.radians(angle)

        # Főtengely
        dx_maj = math.cos(rad) * (w / 2.0)
        dy_maj = math.sin(rad) * (w / 2.0)
        cv2.line(frame, (int(cx - dx_maj), int(cy - dy_maj)),
                 (int(cx + dx_maj), int(cy + dy_maj)), (80, 220, 240), 1, cv2.LINE_AA)

        # Kistengely
        dx_min = -math.sin(rad) * (h / 2.0)
        dy_min = math.cos(rad) * (h / 2.0)
        cv2.line(frame, (int(cx - dx_min), int(cy - dy_min)),
                 (int(cx + dx_min), int(cy + dy_min)), (180, 180, 185), 1, cv2.LINE_AA)

    # ==========================================================
    # STÍLUS 5: GAZE VECTOR TARGET (Irányvektoros célpont)
    # ==========================================================
    def _draw_gaze_vector_target(self, frame, cx, cy, r, conf, color, pupil_ellipse):
        cv2.ellipse(frame, pupil_ellipse, color, 1, cv2.LINE_AA)

        az = self.display.get("neural_az", 0.0)
        el = self.display.get("neural_el", 0.0)

        # Vektor nyíl rajzolása a pupilla centrumából
        vx = int(cx + (az / 40.0) * (r + 14))
        vy = int(cy - (el / 30.0) * (r + 14))
        cv2.arrowedLine(frame, (cx, cy), (vx, vy), color, 1, cv2.LINE_AA, tipLength=0.35)
        cv2.circle(frame, (cx, cy), 2, (255, 255, 255), -1, cv2.LINE_AA)