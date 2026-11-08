# core/eye_segmenter.py
# SZEM-SZEGMENTÁLÁS v4.0 – STABIL, PONTOS
#
# Alapelvek:
#   1. Az előző frame-ben talált szem körül keresünk (ROI)
#   2. Csak akkor frissít, ha az új jelölt hasonló méretű/pozíciójú
#   3. Fallback: ha 5 frame-en át nem talál, akkor az egész képen keres
#   4. Első frame: az egész képen keres
#
# Ez sokkal stabilabb, mert:
#   - Nem ugrál ide-oda
#   - Ha egyszer megtalálta, nem veszíti el
#   - Újra tud indulni, ha elveszik

import math
import cv2
import numpy as np
from collections import deque


class EyeSegmenter:

    # ---- KÜSZÖBÖK ----
    SCLERA_THRESHOLD = 145
    DARK_THRESHOLD = 95

    # ---- Geometriai szűrés ----
    MIN_EYE_AREA = 1200
    MAX_EYE_AREA = 60000
    MIN_ASPECT = 1.2
    MAX_ASPECT = 6.0
    MIN_FILL = 0.30

    # ---- Szem pozíció ----
    EYE_REGION_TOP = 0.05
    EYE_REGION_BOTTOM = 0.85

    # ---- Temporális stabilizálás ----
    HISTORY_LEN = 8
    OUTLIER_THRESHOLD = 0.35
    LOST_FRAMES_MAX = 5     # ennyi frame után újra az egész képen keres

    # ---- ROI méret a kereséshez (a talált szem körül) ----
    ROI_MARGIN = 80         # px

    def __init__(self):
        self.history = deque(maxlen=self.HISTORY_LEN)
        self.last_eye = None
        self.last_bbox = None
        self.last_open_ratio = 1.0
        self.lost_frames = 0

    def reset(self):
        self.history.clear()
        self.last_eye = None
        self.last_bbox = None
        self.last_open_ratio = 1.0
        self.lost_frames = 0

    # ==========================================================
    def _is_in_eye_region(self, cy, H):
        rel_y = cy / H
        return self.EYE_REGION_TOP <= rel_y <= self.EYE_REGION_BOTTOM

    # ==========================================================
    def _find_candidate(self, frame_bgr, offset_x=0, offset_y=0):
        """
        Egy adott területen keres jelöltet.
        Visszaad: (cnt, x, y, w, h, area, contour_pts) vagy None
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return None

        H, W = frame_bgr.shape[:2]

        # Szürke + CLAHE
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        try:
            enhanced = clahe.apply(gray)
        except Exception:
            enhanced = gray

        blurred = cv2.GaussianBlur(enhanced, (7, 7), 1.8)

        # Sclera maszk
        _, sclera_mask = cv2.threshold(
            blurred, self.SCLERA_THRESHOLD, 255, cv2.THRESH_BINARY
        )

        # Sötét maszk
        _, dark_mask = cv2.threshold(
            blurred, self.DARK_THRESHOLD, 255, cv2.THRESH_BINARY_INV
        )

        # Kombinálás
        eye_mask = cv2.bitwise_or(sclera_mask, dark_mask)

        # Morfológiai tisztítás
        k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        k9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))

        eye_mask = cv2.morphologyEx(
            eye_mask, cv2.MORPH_CLOSE, k9, iterations=2
        )
        eye_mask = cv2.morphologyEx(
            eye_mask, cv2.MORPH_OPEN, k5, iterations=1
        )

        # Kontúrok
        try:
            contours, _ = cv2.findContours(
                eye_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
        except cv2.error:
            return None

        if not contours:
            return None

        # A legjobb jelölt
        best = None
        best_score = -1.0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.MIN_EYE_AREA or area > self.MAX_EYE_AREA:
                continue
            if len(cnt) < 5:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            if h < 1:
                continue

            # Aspektus
            aspect = w / float(h)
            if aspect < self.MIN_ASPECT or aspect > self.MAX_ASPECT:
                continue

            # Kitöltöttség
            fill = area / float(w * h) if w * h > 0 else 0
            if fill < self.MIN_FILL:
                continue

            # Szemrégió (globális koordinátában)
            global_cy = y + h / 2.0 + offset_y
            if not self._is_in_eye_region(global_cy, H + offset_y):
                # A magasságot H-ra kell venni, de a képen kívül is lehet
                pass

            # Pontszám
            score = (
                min(1.0, area / 10000.0) * 0.35 +
                min(1.0, aspect / 3.5) * 0.25 +
                fill * 0.40
            )

            if score > best_score:
                best_score = score
                # A kontúr pontjait eltoljuk a globális koordinátákra
                contour_pts = cnt.reshape(-1, 2).tolist()
                contour_global = [
                    [px + offset_x, py + offset_y] for px, py in contour_pts
                ]
                best = (cnt, x, y, w, h, area, contour_global)

        return best

    # ==========================================================
    def detect(self, frame_bgr):
        if frame_bgr is None or frame_bgr.size == 0:
            return self._fallback()

        H, W = frame_bgr.shape[:2]

        # ---- Van-e előző szem? ----
        if self.last_eye is not None and self.lost_frames < self.LOST_FRAMES_MAX:
            # Az előző szem körül keresünk (ROI)
            lcx, lcy, lw, lh = self.last_eye

            margin = self.ROI_MARGIN
            x1 = int(max(0, lcx - lw / 2.0 - margin))
            y1 = int(max(0, lcy - lh / 2.0 - margin))
            x2 = int(min(W, lcx + lw / 2.0 + margin))
            y2 = int(min(H, lcy + lh / 2.0 + margin))

            if x2 - x1 > 40 and y2 - y1 > 40:
                roi = frame_bgr[y1:y2, x1:x2]
                candidate = self._find_candidate(roi, x1, y1)
            else:
                candidate = None
        else:
            # Az egész képen keresünk
            candidate = self._find_candidate(frame_bgr, 0, 0)

        # ---- Ha nincs jelölt ----
        if candidate is None:
            self.lost_frames += 1
            return self._fallback()

        cnt, x, y, w, h, area, contour_global = candidate

        # ---- Szem középpont (globális) ----
        M = cv2.moments(cnt)
        if M["m00"] > 0:
            # A M a ROI-hoz képest van → eltoljuk globálissá
            # Az offset a candidate-ben már benne van a kontúrban
            pts = np.array(contour_global, dtype=np.int32)
            M = cv2.moments(pts)
            if M["m00"] > 0:
                ecx = M["m10"] / M["m00"]
                ecy = M["m01"] / M["m00"]
            else:
                ecx = x + w / 2.0
                ecy = y + h / 2.0
        else:
            ecx = x + w / 2.0
            ecy = y + h / 2.0

        # ---- Nyitás/zárás arány ----
        open_ratio = min(1.0, area / float(w * h)) if w * h > 0 else 0.5
        self.last_open_ratio = open_ratio

        # ---- Temporális stabilizálás ----
        stabilized = self._stabilize(ecx, ecy, w, h, area)
        if stabilized is None:
            return self._fallback()

        ecx, ecy, w, h, conf = stabilized

        # ---- Bounding box ----
        bbox = (int(ecx - w / 2), int(ecy - h / 2), int(w), int(h))
        bbox = self._clamp_bbox(bbox, W, H)

        # ---- Sikeres detektálás ----
        self.lost_frames = 0

        return {
            "eye_cx": float(ecx),
            "eye_cy": float(ecy),
            "bbox": bbox,
            "contour": contour_global,
            "open_ratio": float(open_ratio),
            "confidence": float(conf),
        }

    # ==========================================================
    def _stabilize(self, cx, cy, w, h, area):
        if self.last_eye is None:
            self.last_eye = (cx, cy, w, h)
            self.history.append((cx, cy, w, h))
            return cx, cy, w, h, 1.0

        lcx, lcy, lw, lh = self.last_eye

        size_ratio = (w * h) / max(lw * lh, 1.0)
        is_outlier = (
            size_ratio > (1 + self.OUTLIER_THRESHOLD) or
            size_ratio < (1 - self.OUTLIER_THRESHOLD)
        )

        dist = math.hypot(cx - lcx, cy - lcy)
        if dist > max(lw, lh) * 0.6:
            is_outlier = True

        if is_outlier:
            if len(self.history) >= 3:
                arr = np.array(self.history)
                mcx = float(np.median(arr[:, 0]))
                mcy = float(np.median(arr[:, 1]))
                mw = float(np.median(arr[:, 2]))
                mh = float(np.median(arr[:, 3]))
                return mcx, mcy, mw, mh, 0.5
            else:
                return lcx, lcy, lw, lh, 0.5

        self.history.append((cx, cy, w, h))
        self.last_eye = (cx, cy, w, h)

        if len(self.history) >= 5:
            arr = np.array(self.history)
            mcx = float(np.median(arr[:, 0]))
            mcy = float(np.median(arr[:, 1]))
            mw = float(np.median(arr[:, 2]))
            mh = float(np.median(arr[:, 3]))
            return mcx, mcy, mw, mh, 1.0

        return cx, cy, w, h, 1.0

    def _clamp_bbox(self, bbox, W, H):
        x, y, w, h = bbox
        x = max(0, min(x, W - 20))
        y = max(0, min(y, H - 20))
        w = min(w, W - x)
        h = min(h, H - y)
        return (x, y, w, h)

    def _fallback(self):
        if self.last_eye is None:
            return None
        lcx, lcy, lw, lh = self.last_eye
        return {
            "eye_cx": float(lcx),
            "eye_cy": float(lcy),
            "bbox": (int(lcx - lw / 2), int(lcy - lh / 2),
                     int(lw), int(lh)),
            "contour": [],
            "open_ratio": self.last_open_ratio,
            "confidence": 0.3,
        }