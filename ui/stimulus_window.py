# ui/stimulus_window.py
# Páciens felőli ingerablak (Dual-Display kimenet)
# Az ablak a program indulásától nyitva van a 2. monitoron, alapból teljesen
# fekete (standby). A kísérlet indításakor vált tartalomra, a kísérlet végén
# visszavált feketére. Nem záródik be automatikusan.

import os
import time
import cv2
import numpy as np
from typing import List, Optional, Dict, Tuple

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel,
    QPushButton, QApplication
)
from PyQt5.QtCore import Qt, QTimer, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QFont

from config.settings import PALETTE
from config.paths import STIMULI_DIR
from core.stimulus_task import (
    StimulusTask, Trial, ExperimentResult, STROOP_COLORS
)
from core.emotion_analyzer import EmotionAnalyzer
from core.report_generator import ReportGenerator
from core.heatmap_generator import GazeAnalytics


class CalibrationPoint:
    def __init__(self, x_ratio: float, y_ratio: float):
        self.x_ratio = x_ratio
        self.y_ratio = y_ratio
        self.samples: List[Dict] = []

    def add_sample(self, data: dict):
        self.samples.append(data)


# ============================================================
# PÁCIENS ABLAK
# ============================================================
class StimulusWindow(QMainWindow):

    experiment_finished = pyqtSignal(object)
    experiment_progress = pyqtSignal(dict)
    gaze_feed = pyqtSignal(object, float, float)

    CALIB_TARGETS = [
        (0.15, 0.15), (0.50, 0.15), (0.85, 0.15),
        (0.15, 0.50), (0.50, 0.50), (0.85, 0.50),
        (0.15, 0.85), (0.50, 0.85), (0.85, 0.85),
    ]

    # Gaze feed küldés csak minden 2. képkockán (kb. 15 Hz)
    GAZE_FEED_DECIMATION = 2

    def __init__(self, tracker_thread, parent=None, config: dict = None):
        super().__init__(parent)
        self.tracker = tracker_thread

        self.config = config or {}
        self.mode = self.config.get("mode", "images")
        self.subject_id = self.config.get("subject_id", "SUBJ_001")
        self.subject_note = self.config.get("subject_note", "")

        # Fázis: standby -> baseline -> calibration -> fixation/image -> done -> standby
        self.phase = "standby"
        self.phase_start_time = time.time()
        self.session_start = 0.0
        self.session_end = 0.0

        self.current_trial_idx = 0
        self.current_image: Optional[QPixmap] = None
        self.current_cv_image: Optional[np.ndarray] = None
        self.current_pupil_samples: List[float] = []
        self.current_baseline_pupil = 0.0
        self.current_first_fixation = None
        self.current_fixation_start = 0.0
        self.total_fixation_time = 0.0
        self.total_blinks = 0

        self.baseline_samples: List[float] = []
        self.calib_idx = 0
        self.calib_points: List[CalibrationPoint] = [
            CalibrationPoint(x, y) for x, y in self.CALIB_TARGETS
        ]
        self.calib_current_samples: List[Dict] = []
        self.calib_done = False
        self.current_gaze_samples: List[Tuple[float, float, float]] = []

        self.stroop_response_start = 0.0
        self._gaze_feed_counter = 0

        self.TIME_BASELINE = float(self.config.get("time_baseline", 5.0))
        self.TIME_FIXATION = float(self.config.get("time_fixation", 1.0))
        self.TIME_IMAGE = float(self.config.get("time_image", 3.0))
        self.TIME_CALIB = float(self.config.get("time_calibration", 1.2))

        self.task = StimulusTask(image_dir=str(STIMULI_DIR))
        self.analyzer = EmotionAnalyzer()
        self.reporter = ReportGenerator()

        self.trials: List[Trial] = []

        # Ablak azonnal fekete, teljes képernyőn a 2. monitoron
        self.setWindowTitle("NeuroEye – Páciens Prezentáció")
        self.setStyleSheet("background-color: #000000;")
        self.setCursor(Qt.BlankCursor)
        self.setAutoFillBackground(True)

        pal = self.palette()
        pal.setColor(self.backgroundRole(), QColor(0, 0, 0))
        self.setPalette(pal)

        self._position_on_screen()

        try:
            self.tracker.frame_ready.connect(self._on_frame)
        except Exception:
            pass

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(20)

        self.update()

    # ------------------------------------------------------------
    # Képernyő-pozicionálás
    # ------------------------------------------------------------
    def _position_on_screen(self):
        screens = QApplication.screens()
        if len(screens) > 1:
            patient_screen = screens[1]
            geom = patient_screen.geometry()
            self.move(geom.left(), geom.top())
            self.resize(geom.width(), geom.height())
            self.showFullScreen()
        else:
            self.showFullScreen()

    # ------------------------------------------------------------
    # KÍSÉRLET INDÍTÁSA – a MainWindow hívja
    # ------------------------------------------------------------
    def start_experiment(self, config: dict = None):
        if self.phase not in ("standby", "done"):
            return

        if config:
            self.config = config
            self.mode = config.get("mode", "images")
            self.subject_id = config.get("subject_id", "SUBJ_001")
            self.subject_note = config.get("subject_note", "")
            self.TIME_BASELINE = float(config.get("time_baseline", 5.0))
            self.TIME_FIXATION = float(config.get("time_fixation", 1.0))
            self.TIME_IMAGE = float(config.get("time_image", 3.0))
            self.TIME_CALIB = float(config.get("time_calibration", 1.2))

        # Protokoll építése
        self.trials = []
        if self.mode == "stroop":
            n_stroop = int(self.config.get("n_stroop_trials", 20))
            self.trials = self.task.build_stroop_protocol(n_trials=n_stroop, congruent_ratio=0.5)
        else:
            cats = self.config.get("categories", {})
            try:
                self.trials = self.task.build_protocol(category_counts=cats, randomize=True)
            except Exception as e:
                print(f"[PROTOKOLL] Hiba: {e}")
                self.trials = []

        if not self.trials:
            print("[KÍSÉRLET] Nem sikerült próbákat összeállítani!")
            self.phase = "standby"
            self.update()
            return

        # Állapotok visszaállítása
        self.current_trial_idx = 0
        self.baseline_samples.clear()
        self.calib_idx = 0
        self.calib_current_samples.clear()
        self.calib_done = False
        self.total_blinks = 0
        self.total_fixation_time = 0.0
        self.session_start = time.time()
        self.session_end = 0.0
        self._gaze_feed_counter = 0

        QTimer.singleShot(200, self._start_baseline)

    # ------------------------------------------------------------
    # FÁZIS-ÁTMENETEK
    # ------------------------------------------------------------
    def _start_baseline(self):
        self.phase = "baseline"
        self.phase_start_time = time.time()
        self.baseline_samples.clear()
        self.update()

    def _end_baseline(self):
        if self.baseline_samples:
            base_val = float(np.median(self.baseline_samples))
            self.analyzer.reset_baseline(base_val)
        self._start_calibration()

    def _start_calibration(self):
        self.phase = "calibration"
        self.calib_idx = 0
        self.calib_current_samples.clear()
        self.phase_start_time = time.time()
        self.update()

        self.experiment_progress.emit({
            "current_trial": 0,
            "total_trials": len(self.trials),
            "category": "Kalibráció",
            "phase": "calibration",
        })

    def _next_calibration_point(self):
        if self.calib_current_samples and self.calib_idx > 0:
            p_prev = self.calib_points[self.calib_idx - 1]
            for s in self.calib_current_samples:
                p_prev.add_sample(s)
                target_az = (p_prev.x_ratio - 0.5) * 50.0
                target_el = -(p_prev.y_ratio - 0.5) * 36.0
                if hasattr(self.tracker, "neural_model"):
                    self.tracker.neural_model.add_training_sample(s, (target_az, target_el))

        self.calib_current_samples.clear()

        if self.calib_idx >= len(self.calib_points):
            self._finalize_calibration()
            return

        self.phase_start_time = time.time()
        self.update()

    def _finalize_calibration(self):
        self.calib_done = True
        if hasattr(self.tracker, "neural_model"):
            try:
                self.tracker.neural_model.train()
            except Exception as e:
                print(f"[KALIB] Tanítási hiba: {e}")

        self._start_next_trial()

    def _start_next_trial(self):
        if self.current_trial_idx >= len(self.trials):
            self._finish_experiment()
            return

        trial = self.trials[self.current_trial_idx]

        self.current_image = None
        self.current_cv_image = None
        if not trial.is_stroop and trial.image_path:
            pm = QPixmap(trial.image_path)
            if not pm.isNull():
                self.current_image = pm
                self.current_cv_image = cv2.imread(trial.image_path)

        self.current_pupil_samples.clear()
        self.current_gaze_samples.clear()
        self.current_first_fixation = None
        self.total_fixation_time = 0.0
        self.stroop_response_start = 0.0
        self.current_baseline_pupil = self.analyzer.baseline if self.analyzer.baseline > 0 else 1.0

        self.phase = "fixation"
        self.phase_start_time = time.time()
        self.update()

        self.experiment_progress.emit({
            "current_trial": self.current_trial_idx + 1,
            "total_trials": len(self.trials),
            "category": trial.category,
            "phase": "fixation",
        })

    def _show_image(self):
        self.phase = "image"
        self.phase_start_time = time.time()
        self.current_fixation_start = time.time()
        self.stroop_response_start = time.time()
        self.update()

        trial = self.trials[self.current_trial_idx]
        self.experiment_progress.emit({
            "current_trial": self.current_trial_idx + 1,
            "total_trials": len(self.trials),
            "category": trial.category,
            "phase": "image",
        })

    def _end_image(self):
        trial = self.trials[self.current_trial_idx]
        trial.t_start = self.phase_start_time
        trial.t_end = time.time()

        if self.current_pupil_samples:
            trial.pupil_samples = list(self.current_pupil_samples)
            trial.pupil_baseline = self.current_baseline_pupil
            trial.pupil_mean = float(np.mean(self.current_pupil_samples))
            trial.pupil_median = float(np.median(self.current_pupil_samples))
            trial.pupil_max = float(np.max(self.current_pupil_samples))
            trial.pupil_min = float(np.min(self.current_pupil_samples))
            if len(self.current_pupil_samples) > 1:
                trial.pupil_std = float(np.std(self.current_pupil_samples))

        if self.current_first_fixation is not None:
            trial.first_fixation_x = self.current_first_fixation[0]
            trial.first_fixation_y = self.current_first_fixation[1]
            trial.first_fixation_latency_ms = self.current_first_fixation[2] * 1000.0
            trial.reaction_time_ms = trial.first_fixation_latency_ms

        trial.total_fixation_time_ms = self.total_fixation_time

        if not trial.is_stroop and trial.image_path and os.path.exists(trial.image_path):
            self._save_gaze_visualizations(trial)

        self.current_trial_idx += 1
        self._start_next_trial()

    def _save_gaze_visualizations(self, trial: Trial):
        try:
            if self.current_cv_image is None or not self.current_gaze_samples:
                return

            orig_img = self.current_cv_image
            os.makedirs("reports", exist_ok=True)
            ih, iw = orig_img.shape[:2]
            sw, sh = self.width(), self.height()

            if sw <= 0 or sh <= 0:
                return

            scaled_samples = [
                (x * (iw / sw), y * (ih / sh), dt)
                for x, y, dt in self.current_gaze_samples
            ]

            heatmap = GazeAnalytics.generate_heatmap(orig_img, scaled_samples, gaussian_radius=45)
            hm_path = os.path.join("reports", f"heatmap_{self.subject_id}_t{trial.index}_{trial.category}.jpg")
            cv2.imwrite(hm_path, heatmap)

            sparse_fixations = scaled_samples[::6]
            if len(sparse_fixations) >= 2:
                scanpath = GazeAnalytics.generate_scanpath(orig_img, sparse_fixations)
                sp_path = os.path.join("reports", f"scanpath_{self.subject_id}_t{trial.index}_{trial.category}.jpg")
                cv2.imwrite(sp_path, scanpath)

        except Exception as e:
            print(f"[VIZUALIZÁCIÓ] Hiba: {e}")

    def _finish_experiment(self):
        self.phase = "done"
        self.session_end = time.time()

        result = self.task.analyze(
            subject_id=self.subject_id,
            subject_note=self.subject_note,
            session_start=self.session_start,
            session_end=self.session_end,
            baseline_pupil=self.analyzer.baseline,
            total_blinks=self.total_blinks,
            vas_before=-1.0,
            vas_after=-1.0,
        )

        try:
            self.reporter.save_report(result)
            self.reporter.save_csv(result)
        except Exception as e:
            print(f"[REPORTER] Hiba: {e}")

        self.experiment_finished.emit(result)
        self.update()

        QTimer.singleShot(2500, self.return_to_standby)

    def return_to_standby(self):
        self.phase = "standby"
        self.current_image = None
        self.current_cv_image = None
        self.update()

    # ------------------------------------------------------------
    # FŐ CIKLUS
    # ------------------------------------------------------------
    def _tick(self):
        if not hasattr(self, "phase"):
            return

        now = time.time()
        elapsed = now - self.phase_start_time

        if self.phase == "baseline" and elapsed >= self.TIME_BASELINE:
            self._end_baseline()
        elif self.phase == "calibration" and elapsed >= self.TIME_CALIB:
            self.calib_idx += 1
            self._next_calibration_point()
        elif self.phase == "fixation" and elapsed >= self.TIME_FIXATION:
            self._show_image()
        elif self.phase == "image" and elapsed >= self.TIME_IMAGE:
            self._end_image()

    def _on_frame(self, frame, result: dict):
        if not hasattr(self, "phase"):
            return

        if self.phase in ("standby", "done"):
            return

        conf = float(result.get("confidence", 0.0))
        detected = bool(result.get("detected", False))
        size = float(result.get("pupil_size", 1.0))
        raw_data = getattr(self.tracker, "last_raw_data", {})

        if not detected and conf < 0.15:
            self.total_blinks += 1
            self.analyzer.add_blink(time.time())

        if self.phase == "baseline":
            if detected and conf > 0.35:
                self.baseline_samples.append(size)
            return

        if self.phase == "calibration":
            if detected and conf > 0.30 and raw_data:
                self.calib_current_samples.append(raw_data)
            return

        if self.phase == "image" and detected and conf > 0.30:
            self.current_pupil_samples.append(size)
            self.analyzer.add_pupil_sample(size, time.time())
            self.total_fixation_time += 20.0

            sw, sh = self.width(), self.height()
            az = result.get("neural_az", 0.0)
            el = result.get("neural_el", 0.0)

            rel_x = float(np.clip((az + 25.0) / 50.0, 0.0, 1.0))
            rel_y = float(np.clip((-el + 18.0) / 36.0, 0.0, 1.0))

            gaze_x = rel_x * sw
            gaze_y = rel_y * sh
            self.current_gaze_samples.append((gaze_x, gaze_y, 0.020))

            # Csak minden 2. képkockánál küldjük a gaze_feed jelet
            self._gaze_feed_counter += 1
            if (
                self.current_cv_image is not None
                and (self._gaze_feed_counter % self.GAZE_FEED_DECIMATION == 0)
            ):
                self.gaze_feed.emit(self.current_cv_image, rel_x, rel_y)

            if self.current_first_fixation is None and conf > 0.55:
                latency = time.time() - self.current_fixation_start
                self.current_first_fixation = (gaze_x, gaze_y, latency)

    # ------------------------------------------------------------
    # RAJZOLÁS
    # ------------------------------------------------------------
    def paintEvent(self, event):
        if not hasattr(self, "phase"):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        painter.fillRect(self.rect(), QColor("#000000"))

        if self.phase == "standby":
            return

        if self.phase == "baseline":
            painter.fillRect(self.rect(), QColor("#161618"))
            painter.setPen(QColor("#808088"))
            painter.setFont(QFont("Segoe UI", 16))
            rem = max(0.0, self.TIME_BASELINE - (time.time() - self.phase_start_time))
            painter.drawText(
                self.rect(), Qt.AlignCenter,
                f"Kérjük, fókuszáljon a középső pontra ({rem:.1f} s)"
            )
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(PALETTE.get('accent_primary', '#007acc'))))
            painter.drawEllipse(QPointF(w / 2, h / 2), 6, 6)
            return

        if self.phase == "calibration":
            self._paint_calibration(painter, w, h)
            return

        if self.phase == "fixation":
            painter.fillRect(self.rect(), QColor("#121214"))
            cx, cy = w // 2, h // 2
            painter.setPen(QPen(QColor("#a0a0a8"), 2))
            painter.drawLine(cx - 24, cy, cx + 24, cy)
            painter.drawLine(cx, cy - 24, cx, cy + 24)
            return

        if self.phase == "image":
            if self.current_trial_idx < len(self.trials):
                trial = self.trials[self.current_trial_idx]
                if trial.is_stroop:
                    self._paint_stroop(painter, w, h, trial)
                elif self.current_image is not None:
                    iw, ih = self.current_image.width(), self.current_image.height()
                    scale = min(w / iw, h / ih)
                    nw, nh = int(iw * scale), int(ih * scale)
                    painter.drawPixmap((w - nw) // 2, (h - nh) // 2, nw, nh, self.current_image)
            return

        if self.phase == "done":
            painter.setPen(QColor(PALETTE.get('accent_success', '#3fb950')))
            painter.setFont(QFont("Segoe UI", 22, QFont.Bold))
            painter.drawText(self.rect(), Qt.AlignCenter, "MÉRÉS BEFEJEZŐDÖTT")
            return

    def _paint_calibration(self, painter: QPainter, w: int, h: int):
        painter.fillRect(self.rect(), QColor("#121214"))

        if self.calib_idx < len(self.calib_points):
            p = self.calib_points[self.calib_idx]
            cx = int(p.x_ratio * w)
            cy = int(p.y_ratio * h)

            acc_col = QColor(PALETTE.get('accent_primary', '#007acc'))
            painter.setPen(QPen(acc_col, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), 14, 14)
            painter.drawEllipse(QPointF(cx, cy), 4, 4)

            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawLine(cx - 20, cy, cx + 20, cy)
            painter.drawLine(cx, cy - 20, cx, cy + 20)

        for i in range(self.calib_idx):
            p_done = self.calib_points[i]
            px = int(p_done.x_ratio * w)
            py = int(p_done.y_ratio * h)
            painter.setPen(QPen(QColor("#3a3a40"), 1))
            painter.drawEllipse(QPointF(px, py), 4, 4)

    def _paint_stroop(self, painter: QPainter, w: int, h: int, trial: Trial):
        color_bgr = STROOP_COLORS.get(trial.stroop_color, (255, 255, 255))
        color_rgb = QColor(color_bgr[2], color_bgr[1], color_bgr[0])

        painter.setPen(color_rgb)
        painter.setFont(QFont("Segoe UI", 92, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, trial.stroop_word.upper())

    # ------------------------------------------------------------
    # BILLENTYŰZET
    # ------------------------------------------------------------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return

        if hasattr(self, "phase") and self.phase == "image" and self.current_trial_idx < len(self.trials):
            trial = self.trials[self.current_trial_idx]
            if not trial.is_stroop:
                return

            keymap = {
                Qt.Key_P: "piros",
                Qt.Key_Z: "zöld",
                Qt.Key_K: "kék",
                Qt.Key_S: "sárga",
            }
            if event.key() in keymap:
                resp = keymap[event.key()]
                trial.stroop_correct = (resp == trial.stroop_color)
                if self.stroop_response_start > 0:
                    trial.stroop_response_ms = (time.time() - self.stroop_response_start) * 1000.0
                self._end_image()