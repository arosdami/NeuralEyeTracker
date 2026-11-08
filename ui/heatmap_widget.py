# ui/heatmap_widget.py

import numpy as np
import cv2
from scipy.ndimage import gaussian_filter
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QImage

from config.settings import PALETTE


class HeatmapWidget(QLabel):
    """Real-time gaze heatmap visualization"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 150)
        self.setStyleSheet(f"border: 1px solid {PALETTE['border']}; border-radius: 6px; background: {PALETTE['bg_deep']};")
        self._heatmap = np.zeros((480, 640), np.float32)
    
    def update_heatmap(self, heatmap: np.ndarray):
        self._heatmap = heatmap.copy()
        self._render()
    
    def _render(self):
        blurred = gaussian_filter(self._heatmap, sigma=25)
        if blurred.max() > 0:
            norm = (blurred / blurred.max() * 255).astype(np.uint8)
        else:
            norm = blurred.astype(np.uint8)
        colored = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
        rgb = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
        h, w, c = rgb.shape
        qi = QImage(rgb.data, w, h, c * w, QImage.Format_RGB888)
        pm = QPixmap.fromImage(qi).scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        super().setPixmap(pm)