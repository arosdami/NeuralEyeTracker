# core/pupil_detector.py
# PROFESSZIONÁLIS PUPILLA-DETEKTOR v3.0
# Szem-szegmentálással + sub-pixel finomítással
#
# ÚJ:
#   - EyeSegmenter integrálva
#   - A pupilla CSAK a szem belsejében keres
#   - A ROI dinamikusan a szemhez igazodik
#   - Szem nyitás/zárás detektálás
#   - Sub-pixel finomítás (Canny + fitEllipseAMS)
#   - Kontraszt-ellenőrzés
#   - Bilaterális szűrő

import math
import cv2
import numpy as np
from collections import deque

from core.eye_segmenter import EyeSegmenter


class PupilDetector:
    """
    Professzionális pupilladetektor:
    - Szem-szegmentálás (EyeSegmenter)
    - A pupilla csak a szem nyílásán belül
    - CLAHE + bilaterális szűrő (zajmentes)
    - Adaptív + Otsu + Fix küszöb
    - Sub-pixel finomítás
    - Kontraszt-ellenőrzés
    - Robusztus pontszámítás
    """

    # ---- Geometriai szűrési paraméterek ----
    MIN_PUPIL_AREA = 40
    MAX_PUPIL_AREA = 4000
    MIN_RADIUS = 3.0
    MIN_CIRCULARITY = 0.55
    MIN_ASPECT_RATIO = 0.55
    MAX_MEAN_INTENSITY = 75
    MIN_SCORE = 0.30

    # ---- Kontraszt-küszöb ----
    MIN_CONTRAST = 12.0

    def __init__(self):
        self.roi = None
        self.auto_roi_frames = 30
        self.last_center = None
        self.last_radius = 0.0
        self.size_history = deque(maxlen=7)
        self.blink_counter = 0
        self.BLINK_THRESHOLD = 3

        # CLAHE
        self.clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

        # Szemrégió
        self.eye_region_top = 0.08
        self.eye_region_bottom = 0.75

        # ---- SZEM-SZEGMENTÁLÓ ----
        self.eye_segmenter = EyeSegmenter()
        self.last_eye_bbox = None
        self.last_eye_contour = None
        self.last_eye_open_ratio = 1.0

        # ---- FIX ROI (a szem helye a 640×480-as képen) ----
        # Ha az EyeSegmenter nem működik, ez a fix ROI lesz használva
        self.use_eye_segmenter = True       # ← ha nem talál szemet, False-ra!
        self.fixed_roi = (150, 120, 340, 220)   # (x, y, w, h)

    # ==========================================================
    def set_roi(self, roi):
        self.roi = roi
        self.auto_roi_frames = 0

    def reset(self):
        self.last_center = None
        self.last_radius = 0.0
        self.size_history.clear()
        self.blink_counter = 0
        self.eye_segmenter.reset()
        self.last_eye_bbox = None
        self.last_eye_contour = None
        self.last_eye_open_ratio = 1.0

    def _is_in_eye_region(self, y_global, H):
        rel_y = y_global / H
        return self.eye_region_top <= rel_y <= self.eye_region_bottom

    # ==========================================================
    def _ring_contrast(self, gray, cx, cy, base_r,
                       inner_scale=0.85, outer_scale=1.5):
        """Kontraszt: pupilla (belső) vs írisz (külső gyűrű)."""
        try:
            cxi = int(cx)
            cyi = int(cy)
            r_in = max(2, int(base_r * inner_scale))
            r_out = max(r_in + 2, int(base_r * outer_scale))

            inner_mask = np.zeros_like(gray)
            cv2.circle(inner_mask, (cxi, cyi), r_in, 255, -1)
            inner_mean = cv2.mean(gray, mask=inner_mask)[0]

            ring_mask = np.zeros_like(gray)
            cv2.circle(ring_mask, (cxi, cyi), r_out, 255, -1)
            cv2.circle(ring_mask, (cxi, cyi), r_in, 0, -1)
            ring_mean = cv2.mean(gray, mask=ring_mask)[0]

            return float(ring_mean - inner_mean)
        except Exception:
            return 0.0

    # ==========================================================
    def _refine_subpixel(self, cx, cy, er, gray):
        """Canny-alapú sub-pixel finomítás."""
        try:
            H, W = gray.shape[:2]
            pad = int(er * 1.8)
            x1 = max(0, int(cx - pad))
            y1 = max(0, int(cy - pad))
            x2 = min(W, int(cx + pad))
            y2 = min(H, int(cy + pad))

            if x2 - x1 < 12 or y2 - y1 < 12:
                return None

            crop = gray[y1:y2, x1:x2]
            edges = cv2.Canny(crop, 40, 100)

            mask = np.zeros_like(edges)
            cv2.circle(
                mask,
                (int(cx - x1), int(cy - y1)),
                int(er * 1.2),
                255, -1,
            )
            edges = cv2.bitwise_and(edges, mask)

            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
            )
            if not contours:
                return None

            contours = sorted(contours, key=cv2.contourArea, reverse=True)

            for ec in contours[:4]:
                if len(ec) < 12:
                    continue

                try:
                    (ex, ey), (ew, eh), eang = cv2.fitEllipseAMS(ec)
                except cv2.error:
                    continue

                if ew < 4 or eh < 4:
                    continue

                aspect = min(ew, eh) / max(ew, eh)
                if aspect < 0.5:
                    continue

                avg_d = (ew + eh) / 2.0
                if abs(avg_d - 2 * er) > er * 0.7:
                    continue

                edge_contrast = self._edge_contrast(
                    crop, ex, ey, avg_d / 2.0
                )
                if edge_contrast < 8.0:
                    continue

                return (
                    float(ex + x1),
                    float(ey + y1),
                    float(ew),
                    float(eh),
                    float(eang),
                )

            return None
        except Exception:
            return None

    def _edge_contrast(self, crop, cx, cy, radius):
        """Él-kontraszt ellenőrzés."""
        try:
            cxi, cyi = int(cx), int(cy)
            ri = max(2, int(radius))

            inner_mask = np.zeros_like(crop)
            cv2.circle(inner_mask, (cxi, cyi), max(1, int(ri * 0.7)), 255, -1)
            inner_mean = cv2.mean(crop, mask=inner_mask)[0]

            outer_mask = np.zeros_like(crop)
            cv2.circle(outer_mask, (cxi, cyi), int(ri * 1.4), 255, -1)
            cv2.circle(outer_mask, (cxi, cyi), int(ri * 1.1), 0, -1)
            outer_mean = cv2.mean(crop, mask=outer_mask)[0]

            return float(outer_mean - inner_mean)
        except Exception:
            return 0.0

    # ==========================================================
    def detect(self, frame: np.ndarray) -> dict:
        H, W = frame.shape[:2]

        # ==========================================================
        # 1) SZEM-SZEGMENTÁLÁS vagy FIX ROI
        # ==========================================================
        if self.use_eye_segmenter:
            eye = self.eye_segmenter.detect(frame)

            if eye is not None:
                self.last_eye_bbox = eye["bbox"]
                self.last_eye_contour = eye["contour"]
                self.last_eye_open_ratio = eye["open_ratio"]

                ex, ey, ew, eh = eye["bbox"]
                margin = 12
                self.roi = (
                    max(0, ex - margin),
                    max(0, ey - margin),
                    min(W, ew + 2 * margin),
                    min(H, eh + 2 * margin),
                )
        else:
            # ---- FIX ROI ----
            self.roi = self.fixed_roi

        # ==========================================================
        # 2) PUPILLA KERESÉS A SZEM ROI-BAN
        # ==========================================================
        if self.roi:
            rx, ry, rw, rh = self.roi
            rx = max(0, min(rx, W - 10))
            ry = max(0, min(ry, H - 10))
            rw = min(rw, W - rx)
            rh = min(rh, H - ry)
            work = frame[ry:ry + rh, rx:rx + rw]
            ox, oy = rx, ry
        else:
            work = frame
            ox, oy = 0, 0

        work_h, work_w = work.shape[:2]
        if work_h < 20 or work_w < 20:
            return self._empty_result(W, H, ox, oy)

        # ---- Szürke ----
        gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)

        # ---- CLAHE ----
        try:
            enhanced = self.clahe.apply(gray)
        except Exception:
            enhanced = gray

        # ---- Bilaterális szűrő ----
        try:
            filtered = cv2.bilateralFilter(
                enhanced, d=5, sigmaColor=50, sigmaSpace=50
            )
        except Exception:
            filtered = enhanced

        # ---- Gauss ----
        blurred = cv2.GaussianBlur(filtered, (5, 5), 1.2)

        # ---- Küszöbök ----
        try:
            th_adaptive = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 15, 3
            )
        except Exception:
            th_adaptive = np.zeros_like(blurred)

        try:
            _, th_otsu = cv2.threshold(
                blurred, 0, 255,
                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )
        except Exception:
            th_otsu = np.zeros_like(blurred)

        _, th_fixed = cv2.threshold(blurred, 45, 255, cv2.THRESH_BINARY_INV)

        # ---- Kombinálás ----
        th_combined = cv2.bitwise_and(th_adaptive, th_fixed)
        th_combined = cv2.bitwise_or(
            th_combined, cv2.bitwise_and(th_otsu, th_fixed)
        )

        # ---- Morfológiai tisztítás ----
        k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        th_clean = cv2.morphologyEx(
            th_combined, cv2.MORPH_OPEN, k3, iterations=1
        )
        th_clean = cv2.morphologyEx(
            th_clean, cv2.MORPH_CLOSE, k5, iterations=2
        )

        # ---- Kontúrok ----
        try:
            contours, _ = cv2.findContours(
                th_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
        except cv2.error:
            contours = []

        if len(contours) == 0:
            _, th_backup = cv2.threshold(
                blurred, 60, 255, cv2.THRESH_BINARY_INV
            )
            th_backup = cv2.morphologyEx(
                th_backup, cv2.MORPH_CLOSE, k5, iterations=2
            )
            try:
                contours, _ = cv2.findContours(
                    th_backup, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
            except cv2.error:
                contours = []

        # ---- Referencia ----
        if self.last_center is not None:
            ref_x = self.last_center[0] - ox
            ref_y = self.last_center[1] - oy
        else:
            ref_x = work_w / 2.0
            ref_y = work_h / 2.0

        # ---- Jelöltek ----
        best = None
        best_score = -1.0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.MIN_PUPIL_AREA or area > self.MAX_PUPIL_AREA:
                continue
            if len(cnt) < 5:
                continue

            try:
                hull = cv2.convexHull(cnt)
                (x, y), (w, h), angle = cv2.fitEllipseAMS(hull)
            except cv2.error:
                continue

            if w < 4 or h < 4:
                continue

            try:
                (_, _), er = cv2.minEnclosingCircle(hull)
            except cv2.error:
                continue

            if er < self.MIN_RADIUS:
                continue

            global_y = y + oy
            if not self._is_in_eye_region(global_y, H):
                continue

            try:
                peri = cv2.arcLength(cnt, True)
            except cv2.error:
                continue

            circ = 4 * math.pi * area / (peri * peri) if peri > 0 else 0
            if circ < self.MIN_CIRCULARITY:
                continue

            aspect = min(w, h) / max(w, h)
            if aspect < self.MIN_ASPECT_RATIO:
                continue

            mask = np.zeros_like(gray)
            cv2.drawContours(mask, [cnt], -1, 255, -1)
            mean_val = cv2.mean(gray, mask=mask)[0]
            if mean_val > self.MAX_MEAN_INTENSITY:
                continue

            contrast = self._ring_contrast(gray, x, y, er)
            if contrast < self.MIN_CONTRAST:
                continue

            darkness = 1.0 - mean_val / 255.0
            dist = math.hypot(x - ref_x, y - ref_y)
            position = max(0.0, 1.0 - dist / 200.0)
            size_score = 1.0 - abs(area - 500) / 800.0
            size_score = max(0.0, size_score)
            contrast_score = min(1.0, contrast / 50.0)

            score = (
                darkness * 0.30 +
                circ * 0.15 +
                aspect * 0.10 +
                position * 0.25 +
                contrast_score * 0.15 +
                size_score * 0.05
            )

            if score > best_score and score > self.MIN_SCORE:
                best_score = score
                best = (x, y, w, h, angle, area, score, mean_val, contrast, er)

        if best is None:
            self.blink_counter += 1
            return self._empty_result(W, H, ox, oy)

        # ---- Sub-pixel finomítás ----
        x, y, w, h, angle, area, score, mean_val, contrast, er = best
        refined = self._refine_subpixel(x, y, er, gray)
        if refined is not None:
            rx_, ry_, rw_, rh_, ra_ = refined
            x, y = rx_, ry_
            w, h, angle = rw_, rh_, ra_
            area = math.pi * (w / 2.0) * (h / 2.0)

        # ---- Eredmény ----
        cx = float(x + ox)
        cy = float(y + oy)
        self.last_center = (cx, cy)
        self.blink_counter = 0

        ellipse = ((x, y), (w, h), angle)

        pupil_area = math.pi * (w / 2.0) * (h / 2.0)
        norm_size = float(np.clip(pupil_area / 300.0, 0.2, 4.0))

        self.size_history.append(norm_size)
        smooth_size = float(np.median(list(self.size_history))) \
            if self.size_history else 1.0

        radius_px = max(w, h) / 2.0
        self.last_radius = radius_px

        return {
            "cx": cx,
            "cy": cy,
            "draw_ellipse": ellipse,
            "draw_offset": (ox, oy),
            "confidence": float(min(1.0, score)),
            "pupil_size": smooth_size,
            "radius_px": radius_px,
            # ---- SZEM ADATOK ----
            "eye_bbox": self.last_eye_bbox,
            "eye_contour": self.last_eye_contour,
            "eye_open_ratio": self.last_eye_open_ratio,
            "raw_data": {
                "cx": cx,
                "cy": cy,
                "frame_w": W,
                "frame_h": H,
                "ellipse_major": max(w, h),
                "ellipse_minor": min(w, h),
                "ellipse_angle": angle,
                "pupil_area": pupil_area,
                "inner_darkness": float(mean_val),
                "contrast": float(contrast),
                "refined": refined is not None,
            },
            "detected": True,
        }

    # ==========================================================
    def _empty_result(self, W, H, ox, oy):
        if self.last_center is None:
            cx, cy = W / 2.0, H / 2.0
        else:
            cx, cy = self.last_center

        smooth_size = float(np.median(list(self.size_history))) \
            if self.size_history else 1.0

        return {
            "cx": cx,
            "cy": cy,
            "draw_ellipse": None,
            "draw_offset": (ox, oy),
            "confidence": 0.0,
            "pupil_size": smooth_size,
            "radius_px": 0.0,
            "eye_bbox": self.last_eye_bbox,
            "eye_contour": self.last_eye_contour,
            "eye_open_ratio": self.last_eye_open_ratio,
            "raw_data": {
                "cx": cx, "cy": cy,
                "frame_w": W, "frame_h": H,
                "refined": False,
            },
            "detected": False,
        }

    def is_blinking(self):
        return self.blink_counter >= self.BLINK_THRESHOLD