# core/heatmap_generator.py
# Professzionális szemmozgás-analitika és hőtérkép generátor (Tobii Lab Standard)

import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional


class GazeAnalytics:
    """
    Szemmozgás adatokból hőtérképet (Heatmap) és fixációs útvonalat (Scanpath)
    előállító motor.
    """

    @staticmethod
    def generate_heatmap(
        image_bgr: np.ndarray,
        gaze_points: List[Tuple[float, float, float]],  # (x, y, duration_s)
        gaussian_radius: int = 50,
        alpha: float = 0.55
    ) -> np.ndarray:
        """
        Időtartammal súlyozott Gauss-hőtérkép rávetítése az eredeti képre.
        """
        h, w = image_bgr.shape[:2]
        if not gaze_points or h == 0 or w == 0:
            return image_bgr.copy()

        # 1. 32 bites akkumulációs mátrix
        density = np.zeros((h, w), dtype=np.float32)

        # Gauss-maszk előállítása
        k_size = gaussian_radius * 2 + 1
        sigma = gaussian_radius / 2.5
        kernel_1d = cv2.getGaussianKernel(k_size, sigma)
        kernel_2d = np.outer(kernel_1d, kernel_1d)

        for x, y, duration in gaze_points:
            ix, iy = int(round(x)), int(round(y))
            if 0 <= ix < w and 0 <= iy < h:
                # Képernyőhatárok kezelése (clipping)
                x_min = max(0, ix - gaussian_radius)
                x_max = min(w, ix + gaussian_radius + 1)
                y_min = max(0, iy - gaussian_radius)
                y_max = min(h, iy + gaussian_radius + 1)

                kx_min = x_min - (ix - gaussian_radius)
                kx_max = kx_min + (x_max - x_min)
                ky_min = y_min - (iy - gaussian_radius)
                ky_max = ky_min + (y_max - y_min)

                # Súlyozás a fixáció hosszával
                weight = max(0.05, float(duration))
                density[y_min:y_max, x_min:x_max] += (
                    kernel_2d[ky_min:ky_max, kx_min:kx_max] * weight
                )

        # Normalizálás 0..255 közé
        max_val = np.max(density)
        if max_val < 1e-5:
            return image_bgr.copy()

        norm_density = (density / max_val * 255.0).astype(np.uint8)

        # 2. Színezés Jet / Turbo palettával (Kék -> Zöld -> Sárga -> Piros)
        heatmap_color = cv2.applyColorMap(norm_density, cv2.COLORMAP_JET)

        # 3. Maszkolás: ahol nincs tekintet, ott az eredeti kép maradjon változatlan
        mask = norm_density > 15
        blended = image_bgr.copy()

        for c in range(3):
            blended[:, :, c] = np.where(
                mask,
                cv2.addWeighted(image_bgr[:, :, c], 1.0 - alpha, heatmap_color[:, :, c], alpha, 0),
                image_bgr[:, :, c]
            )

        return blended

    @staticmethod
    def generate_scanpath(
        image_bgr: np.ndarray,
        fixations: List[Tuple[float, float, float]],  # (x, y, duration_s)
        color_rgb: Tuple[int, int, int] = (45, 140, 240)  # Tobii orvosi narancs/kék
    ) -> np.ndarray:
        """
        Fixációs útvonal (Scanpath): Sorszámozott körök a fókuszidő szerint méretezve,
        összekötve szakkád vonalakkal (lásd a 2. referencia képet).
        """
        output = image_bgr.copy()
        if not fixations:
            return output

        overlay = output.copy()
        bgr = (color_rgb[2], color_rgb[1], color_rgb[0])

        # 1. Szakkád-vonalak rajzolása a fixációk között
        pts = [(int(f[0]), int(f[1])) for f in fixations]
        for i in range(len(pts) - 1):
            cv2.line(overlay, pts[i], pts[i + 1], (180, 180, 185), 1, cv2.LINE_AA)

        # 2. Fixációs körök időarányos átmérővel
        for i, (x, y, dur) in enumerate(fixations):
            ix, iy = int(round(x)), int(round(y))
            # Minimális sugár 12px, maximum 45px az eltöltött idő szerint
            radius = int(np.clip(dur * 25.0, 12, 45))

            # Félig áttetsző kitöltés
            cv2.circle(overlay, (ix, iy), radius, bgr, -1, cv2.LINE_AA)
            # Éles keret
            cv2.circle(overlay, (ix, iy), radius, (255, 255, 255), 1, cv2.LINE_AA)

        # Áttetszőség összefűzése
        cv2.addWeighted(overlay, 0.65, output, 0.35, 0, output)

        # 3. Sorszámok kiírása az éles rétegre
        font = cv2.FONT_HERSHEY_SIMPLEX
        for i, (x, y, _) in enumerate(fixations):
            ix, iy = int(round(x)), int(round(y))
            lbl = str(i + 1)
            (tw, th), _ = cv2.getTextSize(lbl, font, 0.38, 1)
            cv2.putText(output, lbl, (ix - tw // 2, iy + th // 2), font, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

        return output