# core/calibration.py - STABIL KALIBRÁCIÓS ABLAK

import time
from typing import List, Optional

from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QLinearGradient, QRadialGradient

from config.settings import PALETTE


class CalibrationWindow(QDialog):
    """
    Teljes képernyős 9 pontos kalibrációs ablak.

    Fontos javítások:
      - NINCS time.sleep a fő szálon (QTimer-rel gyűjtünk mintát)
      - A mintavétel a tracker.last_raw_data-ból történik
      - Eseményvezérelt, nem blokkol
    """

    calibration_done = pyqtSignal(list)

    CALIB_TARGETS = [
        (0.1, 0.1), (0.5, 0.1), (0.9, 0.1),
        (0.1, 0.5), (0.5, 0.5), (0.9, 0.5),
        (0.1, 0.9), (0.5, 0.9), (0.9, 0.9),
    ]

    SAMPLES_PER_POINT = 15
    SAMPLE_INTERVAL_MS = 33
    PRESENTATION_MS = 1800
    SHRINK_TICK_MS = 30
    SHRINK_MAX_TICKS = 60

    def __init__(self, tracker_engine, parent=None):
        super().__init__(parent)
        self.tracker = tracker_engine

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setStyleSheet(f"background: {PALETTE['bg_deep']};")
        self.showFullScreen()

        self.current_idx = -1
        self.collected: List = []

        self.dot_radius = 30
        self.shrink_step = 0

        self._sample_buffer: List = []

        self.shrink_timer = QTimer(self)
        self.shrink_timer.timeout.connect(self._shrink_tick)

        self.sample_timer = QTimer(self)
        self.sample_timer.timeout.connect(self._collect_sample)

        self.advance_timer = QTimer(self)
        self.advance_timer.setSingleShot(True)
        self.advance_timer.timeout.connect(self._next_point)

        # Indítás késleltetve
        QTimer.singleShot(800, self._next_point)

    # ------------------------------------------------------------------
    def _next_point(self):
        self.current_idx += 1
        if self.current_idx >= len(self.CALIB_TARGETS):
            self.calibration_done.emit(self.collected)
            self.close()
            return

        self.dot_radius = 30
        self.shrink_step = 0
        self.shrink_timer.start(self.SHRINK_TICK_MS)

    # ------------------------------------------------------------------
    def _shrink_tick(self):
        self.shrink_step += 1
        self.dot_radius = max(8.0, 30.0 - self.shrink_step * 0.4)
        self.update()

        if self.shrink_step >= self.SHRINK_MAX_TICKS:
            self.shrink_timer.stop()
            self._sample_buffer = []
            self.sample_timer.start(self.SAMPLE_INTERVAL_MS)

    # ------------------------------------------------------------------
    def _collect_sample(self):
        raw = self.tracker.last_raw_data
        if raw:
            self._sample_buffer.append(dict(raw))

        if len(self._sample_buffer) >= self.SAMPLES_PER_POINT:
            self.sample_timer.stop()

            tx, ty = self.CALIB_TARGETS[self.current_idx]
            self.collected.append((tx, ty, list(self._sample_buffer)))

            self.advance_timer.start(300)

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        p.fillRect(0, 0, w, h, QColor(PALETTE["bg_deep"]))

        # Fejléc
        if self.current_idx >= 0:
            p.setFont(QFont("Segoe UI", 16, QFont.Light))
            p.setPen(QColor(PALETTE["text_secondary"]))
            p.drawText(
                0, 0, w, 60, Qt.AlignCenter,
                f"Nézz a célpontra  {self.current_idx + 1} / {len(self.CALIB_TARGETS)}"
            )

        # Progress bar
        if self.current_idx >= 0:
            prog_w = int(
                (self.current_idx / len(self.CALIB_TARGETS)) * (w - 100)
            )
            p.fillRect(50, h - 30, w - 100, 3, QColor(PALETTE["border"]))

            grad = QLinearGradient(50, 0, 50 + prog_w, 0)
            grad.setColorAt(0, QColor(PALETTE["accent_blue"]))
            grad.setColorAt(1, QColor(PALETTE["accent_cyan"]))
            p.fillRect(50, h - 30, prog_w, 3, grad)

        # Célpont
        if 0 <= self.current_idx < len(self.CALIB_TARGETS):
            tx, ty = self.CALIB_TARGETS[self.current_idx]
            cx = int(tx * w)
            cy = int(ty * h)
            r = self.dot_radius

            # Glow
            for glow_r in (r + 20, r + 12, r + 5):
                alpha = int(max(0, 60 - (glow_r - r) * 2))
                p.setPen(Qt.NoPen)
                glow_col = QColor(PALETTE["accent_cyan"])
                glow_col.setAlpha(alpha)
                p.setBrush(glow_col)
                p.drawEllipse(
                    cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2
                )

            # Belső gradiens
            grad2 = QRadialGradient(cx, cy, max(1.0, r))
            grad2.setColorAt(0, QColor(PALETTE["accent_cyan"]))
            grad2.setColorAt(0.5, QColor(PALETTE["accent_blue"]))
            grad2.setColorAt(1, QColor(PALETTE["bg_deep"]))
            p.setBrush(grad2)
            p.setPen(Qt.NoPen)
            p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

            # Középpont
            p.setBrush(QColor("white"))
            p.drawEllipse(cx - 3, cy - 3, 6, 6)

        p.end()

    # ------------------------------------------------------------------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.shrink_timer.stop()
            self.sample_timer.stop()
            self.advance_timer.stop()
            self.close()