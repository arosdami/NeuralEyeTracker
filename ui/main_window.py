# ui/main_window.py
# NeuroEye Tracker – Clinical Edition v14.0
# Tobii Pro Lab Analyze stílusú, teljesen működő felület

import os
import time
import html
import cv2
import numpy as np
from typing import List, Optional, Dict, Tuple
from collections import deque
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QDialog,
    QPushButton, QLabel, QStatusBar, QMessageBox, QFrame,
    QGroupBox, QProgressBar, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QRadioButton, QButtonGroup, QTabWidget, QComboBox,
    QSlider, QFileDialog, QListWidget, QListWidgetItem,
    QSizePolicy, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QStackedWidget, QToolButton, QScrollArea,
    QSplitter, QSpacerItem, QAbstractItemView, QAction, QMenu
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QPixmap, QImage, QFont, QColor, QPainter, QPen, QBrush, QKeyEvent

from config.settings import (
    PALETTE, PUPIL_STYLES, DEFAULT_PUPIL_STYLE, build_stylesheet,
    FONT_FAMILY, FONT_MONO, FONT_SIZE_XS, FONT_SIZE_SM,
    FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_XXL,
)
from config.paths import REPORTS_DIR, STIMULI_DIR, USERS_FILE
from core.project_manager import save_project
from core.update_manager import UpdateManager
from config.version import APP_VERSION
from core.tracker_thread import TrackerThread
from core.user_manager import UserManager
from core.heatmap_generator import GazeAnalytics


# ============================================================
# BETÖLTŐ SZÁL
# ============================================================
class LoaderThread(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.main = main_window

    def run(self):
        try:
            self.progress.emit("Kamerák keresése...", 15)
            time.sleep(0.15)
            self.main._scan_cameras_bg()

            self.progress.emit("Pupillometriai motor indítása...", 50)
            time.sleep(0.15)

            self.progress.emit("Ingeranyag és előzmények betöltése...", 85)
            self.main._scan_stimuli_bg()
            self.main._scan_reports_bg()

            self.progress.emit("Kész", 100)
        except Exception as e:
            self.progress.emit(f"Hiba: {e}", 100)
        self.finished.emit()


# ============================================================
# PUPILLOMETRIAI IDŐSOR
# ============================================================
class PupilGraph(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.max_points = 500
        self.series = {}
        self._order = []

    def register_series(self, name: str, color: QColor, label: str = None):
        self.series[name] = {"data": deque(maxlen=self.max_points), "color": color, "label": label or name}
        if name not in self._order:
            self._order.append(name)

    def add_point(self, name: str, value: float):
        if name not in self.series:
            return
        self.series[name]["data"].append((time.time(), float(value)))
        self.update()

    def clear(self):
        for name in self.series:
            self.series[name]["data"].clear()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        painter.fillRect(0, 0, w, h, QColor(PALETTE['bg_input']))
        painter.setPen(QPen(QColor(PALETTE['border']), 1, Qt.SolidLine))
        for i in range(1, 5):
            painter.drawLine(0, h * i // 5, w, h * i // 5)
        for i in range(1, 10):
            painter.drawLine(w * i // 10, 0, w * i // 10, h)
        painter.setPen(QPen(QColor(PALETTE['border_light']), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(0, 0, w - 1, h - 1)

        has_data = any(len(s["data"]) >= 2 for s in self.series.values())
        if not has_data:
            painter.setPen(QColor(PALETTE['text_muted']))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(16, 28, "Adatfolyam várakozás...")
            return

        for name in self._order:
            s = self.series.get(name)
            if not s or len(s["data"]) < 2:
                continue
            vals = [d[1] for d in s["data"]]
            min_v, max_v = min(vals), max(vals)
            span = max_v - min_v
            if span < 1e-4:
                span = max(abs(max_v), 1e-2) * 0.2 or 0.2
                min_v -= span / 2
            points = []
            n = len(s["data"])
            for i, (_, val) in enumerate(s["data"]):
                x = int(w * i / max(1, n - 1))
                y = int(h - 15 - ((val - min_v) / span) * (h - 35))
                y = max(4, min(h - 4, y))
                points.append(QPoint(x, y))
            painter.setPen(QPen(s["color"], 1.8))
            painter.drawPolyline(*points)


# ============================================================
# VALÓS IDEJŰ HŐTÉRKÉP-MONITOR
# ============================================================
class LiveGazeMonitor(QWidget):
    RENDER_INTERVAL_MS = 100
    MIN_POINTS_FOR_RENDER = 8
    SHORT_WINDOW = 60
    LONG_WINDOW = 240
    SCANPATH_STRIDE = 8
    SCANPATH_MAX = 40
    GAUSS_RADIUS_SHORT = 55
    GAUSS_RADIUS_LONG = 80
    EMA_DECAY = 0.75

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._current_image = None
        self._image_shape = None
        self._short_points = deque(maxlen=self.SHORT_WINDOW)
        self._long_points = deque(maxlen=self.LONG_WINDOW)
        self._last_gaze_rel = (0.5, 0.5)
        self._ema_heatmap = None
        self._cached_pixmap = None
        self._cached_overlay_rel = (0.5, 0.5)
        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(self._render_tick)
        self._render_timer.start(self.RENDER_INTERVAL_MS)
        self._dirty = False

    def set_frame(self, cv_img, rel_x, rel_y):
        if cv_img is not None and getattr(cv_img, "shape", None):
            ih, iw = cv_img.shape[:2]
            if iw > 0 and ih > 0:
                if self._image_shape is not None and self._image_shape != (ih, iw):
                    self._short_points.clear()
                    self._long_points.clear()
                    self._ema_heatmap = None
                    self._cached_pixmap = None
                self._image_shape = (ih, iw)
                self._current_image = cv_img
        if not (0.0 <= rel_x <= 1.0 and 0.0 <= rel_y <= 1.0):
            return
        self._last_gaze_rel = (float(rel_x), float(rel_y))
        if self._current_image is None or self._image_shape is None:
            return
        ih, iw = self._image_shape
        self._short_points.append((float(rel_x) * iw, float(rel_y) * ih, 0.05))
        self._long_points.append((float(rel_x) * iw, float(rel_y) * ih, 0.05))
        self._dirty = True

    def reset_view(self):
        self._current_image = None
        self._image_shape = None
        self._short_points.clear()
        self._long_points.clear()
        self._last_gaze_rel = (0.5, 0.5)
        self._ema_heatmap = None
        self._cached_pixmap = None
        self._dirty = False
        self.update()

    def _render_tick(self):
        if not self._dirty:
            return
        if (self._current_image is None or self._image_shape is None
                or len(self._short_points) < self.MIN_POINTS_FOR_RENDER):
            self._dirty = False
            self.update()
            return
        self._rebuild()
        self._dirty = False
        self.update()

    def _rebuild(self):
        try:
            w, h = self.width(), self.height()
            if w <= 0 or h <= 0:
                return
            img = self._current_image
            short_alpha = min(0.60, 0.20 + 0.006 * len(self._short_points))
            heat_short = GazeAnalytics.generate_heatmap(
                img, list(self._short_points),
                gaussian_radius=self.GAUSS_RADIUS_SHORT, alpha=short_alpha
            )
            if len(self._long_points) >= self.MIN_POINTS_FOR_RENDER:
                long_alpha = min(0.35, 0.10 + 0.002 * len(self._long_points))
                heat_long = GazeAnalytics.generate_heatmap(
                    img, list(self._long_points),
                    gaussian_radius=self.GAUSS_RADIUS_LONG, alpha=long_alpha
                )
            else:
                heat_long = None
            fresh = heat_short
            if heat_long is not None:
                fresh = cv2.addWeighted(fresh, 0.65, heat_long, 0.35, 0)
            if self._ema_heatmap is not None and self._ema_heatmap.shape == fresh.shape:
                blended = cv2.addWeighted(
                    self._ema_heatmap, self.EMA_DECAY,
                    fresh, 1.0 - self.EMA_DECAY, 0
                )
            else:
                blended = fresh
            self._ema_heatmap = blended
            trimmed = list(self._short_points)[-self.SCANPATH_MAX:]
            sparse = trimmed[:: self.SCANPATH_STRIDE]
            if len(sparse) >= 2:
                rendered = GazeAnalytics.generate_scanpath(blended, sparse)
            else:
                rendered = blended
            rgb = cv2.cvtColor(rendered, cv2.COLOR_BGR2RGB)
            ih, iw, ch = rgb.shape
            qi = QImage(rgb.data, iw, ih, ch * iw, QImage.Format_RGB888).copy()
            self._cached_pixmap = QPixmap.fromImage(qi).scaled(
                w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self._cached_overlay_rel = self._last_gaze_rel
        except Exception as e:
            print(f"[GAZE MONITOR] Hiba: {e}")
            self._cached_pixmap = None
            self._ema_heatmap = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(PALETTE['bg_input']))
        if self._cached_pixmap is not None and not self._cached_pixmap.isNull():
            x = (w - self._cached_pixmap.width()) // 2
            y = (h - self._cached_pixmap.height()) // 2
            painter.drawPixmap(x, y, self._cached_pixmap)
            lx = int(x + self._cached_overlay_rel[0] * self._cached_pixmap.width())
            ly = int(y + self._cached_overlay_rel[1] * self._cached_pixmap.height())
            painter.setPen(QPen(QColor(PALETTE['accent_danger']), 2))
            painter.drawEllipse(QPoint(lx, ly), 10, 10)
            painter.drawLine(lx - 14, ly, lx + 14, ly)
            painter.drawLine(lx, ly - 14, lx, ly + 14)
            return
        painter.setPen(QColor(PALETTE['text_muted']))
        painter.setFont(QFont("Segoe UI", 12))
        painter.drawText(self.rect(), Qt.AlignCenter,
            "A kísérlet indítása után itt jelenik meg a valós idejű hőtérkép.")


# ============================================================
# BEÁGYAZOTT RIPORT-NÉZET
# ============================================================
class ReportViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QFrame()
        header.setObjectName("card")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 10, 14, 10)
        self.lbl_title = QLabel("Riport betöltése...")
        self.lbl_title.setStyleSheet(
            f"color: {PALETTE['accent_primary']}; font-size: 13px; font-weight: 600;"
        )
        hl.addWidget(self.lbl_title)
        hl.addStretch()
        self.lbl_meta = QLabel("")
        self.lbl_meta.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 11px;")
        hl.addWidget(self.lbl_meta)
        layout.addWidget(header)

        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        layout.addWidget(self.text_view, stretch=1)

    def load_report(self, path: str) -> bool:
        if not path or not os.path.exists(path):
            self.lbl_title.setText("Riport nem található")
            self.text_view.setPlainText(f"A megadott fájl nem létezik:\n{path}")
            self.lbl_meta.setText("")
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.lbl_title.setText("Hiba")
            self.text_view.setPlainText(str(e))
            self.lbl_meta.setText("")
            return False
        fname = os.path.basename(path)
        mtime = os.path.getmtime(path)
        dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_title.setText(f"Riport: {fname}")
        self.lbl_meta.setText(f"Betöltve: {dt}")
        self.text_view.setHtml(self._format_report(content))
        return True

    @staticmethod
    def _format_report(content: str) -> str:
        body = html.escape(content).replace("\n", "<br>")
        return f"""
        <html>
        <head>
        <style>
          body {{ background:#fbfaf7; color:#20242a; font-family: Georgia, serif;
                 font-size: 13px; line-height: 1.45; margin: 34px 46px; }}
          .sheet {{ position:relative; max-width:860px; margin:auto; }}
          .watermark {{ position:fixed; top:42%; left:18%; transform:rotate(-28deg);
                        color:rgba(38,99,150,.07); font-size:54px; font-weight:bold;
                        letter-spacing:7px; }}
          .brand {{ border-bottom:2px solid #2c668f; padding-bottom:12px;
                    color:#214d6b; font-size:21px; font-weight:bold;
                    letter-spacing:2px; }}
          .meta {{ color:#66717c; font-size:11px; margin:10px 0 24px; }}
          .content {{ white-space:normal; }}
          .footer {{ border-top:1px solid #c7cdd2; margin-top:28px; padding-top:10px;
                     color:#66717c; font-size:10px; }}
          .signature {{ margin-top:24px; color:#214d6b; font-style:italic; }}
        </style>
        </head>
        <body><div class="sheet">
          <div class="watermark">NEURO EYE LAB</div>
          <div class="brand">NEURO EYE LAB</div>
          <div class="meta">Hivatalos pupillometriai és tekintetkövetési vizsgálati riport</div>
          <div class="content">{body}</div>
          <div class="signature">Elektronikusan generált, hitelesítést igénylő dokumentum<br>
          Neuro Eye Lab • Vizsgálati rendszer</div>
          <div class="footer">Automatikus kiértékelés. Klinikai diagnózis kizárólag szakorvosi értékelés alapján állítható fel.</div>
        </div></body></html>
        """


# ============================================================
# FŐ ABLAK
# ============================================================
class MainWindow(QMainWindow):

    def __init__(
        self,
        user_data: dict = None,
        project_data: dict = None,
        project_path: str = "",
    ):
        super().__init__()
        self.setWindowTitle("NeuroEye Lab – Clinical Edition")
        self.setMinimumSize(1500, 900)

        self._user_data = user_data or {"username": "Kutató", "role": "operátor"}
        self.project_data = project_data or {}
        self.project_path = project_path
        self._user_manager = UserManager(USERS_FILE)

        self._frames_received = 0
        self._last_report_path = None
        self._camera_found = []
        self._reports_list = []
        self._log_lines = []
        self._current_source = "none"
        self._pupil_style = DEFAULT_PUPIL_STYLE
        self._stim_task = None
        self.stimulus_manager = None

        # Analyze állapot
        self._analyze_loader = None
        self._analyze_reports: list = []
        self._analyze_selected: list = []
        self._analyze_analyzer = None

        self.tracker = TrackerThread()
        self.tracker.set_pupil_style(self._pupil_style)
        self.tracker.frame_ready.connect(self._on_frame)
        self.tracker.status.connect(self._set_status)
        self.tracker.fps_update.connect(self._on_fps)

        self.setStyleSheet(build_stylesheet())
        self._build_ui()
        self._connect_signals()

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(500)

        self.stim_win = None
        QTimer.singleShot(100, self._init_patient_screen)
        QTimer.singleShot(50, self._run_loader)

    # ============================================================
    # UI ÉPÍTÉS
    # ============================================================
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        main.addWidget(self._make_menubar())
        main.addWidget(self._make_top_tabs())

        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        workspace_layout.addWidget(self._make_navigation_sidebar())
        self.main_stack = QStackedWidget()
        self.main_stack.addWidget(self._make_live_page())
        self.main_stack.addWidget(self._make_calibration_page())
        self.main_stack.addWidget(self._make_analyze_page())
        self.main_stack.addWidget(self._make_system_page())
        workspace_layout.addWidget(self.main_stack, stretch=1)
        main.addWidget(workspace, stretch=1)

        self.statusbar = QStatusBar()
        self._status_left = QLabel("Készenlét")
        self.statusbar.addWidget(self._status_left)
        self._status_right = QLabel("")
        self.statusbar.addPermanentWidget(self._status_right)
        self.setStatusBar(self.statusbar)

    def _make_menubar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("appMenuBar")
        bar.setFixedHeight(34)

        h = QHBoxLayout(bar)
        h.setContentsMargins(8, 0, 8, 0)
        h.setSpacing(2)

        title = QLabel("◎")
        title.setObjectName("appLogo")
        title.setToolTip("Neural Eye Tracker")
        h.addWidget(title)
        h.addSpacing(8)

        self._add_menu(h, "Fájl", (
            ("Riport megnyitása", self._open_selected_report),
            ("Videófájl megnyitása", self._open_video),
            ("Projekt mentése másként", self._save_project_as),
            None,
            ("Kilépés", self.close),
        ))
        self._add_menu(h, "Szerkesztés", (
            ("Nézet alaphelyzetbe állítása", self._reset_workspace),
            ("Munkamenet leállítása", self._stop),
        ))
        self._add_menu(h, "Nézet", (
            ("Élő nézet", lambda: self._switch_page(0)),
            ("Riport nézet", lambda: self._switch_exp_view("report")),
            None,
            ("Teljes képernyő", self._toggle_fullscreen),
        ))
        self._add_menu(h, "Ablak", (
            ("Kalibráció", lambda: self._switch_page(1)),
            ("Elemzés", lambda: self._switch_page(2)),
            ("Rendszer", lambda: self._switch_page(3)),
        ))
        self._add_menu(h, "Súgó", (
            ("Billentyűparancsok", self._show_shortcuts),
            ("Névjegy", self._show_about),
            ("Frissítések keresése", self._check_for_updates),
        ))

        h.addStretch()

        self.hdr_cam_status = QLabel("Forrás: –")
        self.hdr_cam_status.setStyleSheet(
            f"color: {PALETTE['text_secondary']}; font-size: {FONT_SIZE_SM}px; "
            f"background-color: {PALETTE['bg_panel']}; "
            f"border: 1px solid {PALETTE['border']}; "
            f"border-radius: 3px; padding: 3px 10px;"
        )
        h.addWidget(self.hdr_cam_status)

        self.hdr_det_status = QLabel("Detektor: –")
        self.hdr_det_status.setStyleSheet(
            f"color: {PALETTE['text_secondary']}; font-size: {FONT_SIZE_SM}px; "
            f"background-color: {PALETTE['bg_panel']}; "
            f"border: 1px solid {PALETTE['border']}; "
            f"border-radius: 3px; padding: 3px 10px;"
        )
        h.addWidget(self.hdr_det_status)

        self.fps_badge = QLabel("0 FPS")
        self.fps_badge.setStyleSheet(
            f"color: {PALETTE['accent_success']}; font-size: {FONT_SIZE_SM}px; "
            f"font-family: {FONT_MONO}; "
            f"background-color: {PALETTE['bg_panel']}; "
            f"border: 1px solid {PALETTE['border']}; "
            f"border-radius: 3px; padding: 3px 10px;"
        )
        h.addWidget(self.fps_badge)

        h.addSpacing(8)

        self.fullscreen_btn = QToolButton()
        self.fullscreen_btn.setObjectName("windowActionBtn")
        self.fullscreen_btn.setText("Teljes képernyő")
        self.fullscreen_btn.setToolTip("Teljes képernyő be- vagy kikapcsolása (F11)")
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        h.addWidget(self.fullscreen_btn)

        self.start_btn = QPushButton("Rögzítés")
        self.start_btn.setProperty("class", "primary")
        self.start_btn.setMinimumHeight(28)
        h.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Leállítás")
        self.stop_btn.setMinimumHeight(28)
        self.stop_btn.setEnabled(False)
        h.addWidget(self.stop_btn)

        return bar

    def _make_navigation_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("navigationSidebar")
        sidebar.setFixedWidth(72)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(8)
        self.sidebar_buttons = []
        for index, (icon, label, tip) in enumerate((
            ("◉", "Élő", "Élő mérés"),
            ("✥", "Kalibr.", "Kalibráció"),
            ("▣", "Elemzés", "Elemzés"),
            ("⚙", "Rendsz.", "Rendszer és beállítások"),
        )):
            button = QToolButton()
            button.setObjectName("navigationButton")
            button.setText(f"{icon}\n{label}")
            button.setToolTip(tip)
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setFixedHeight(52)
            button.clicked.connect(lambda checked, i=index: self._switch_page(i))
            layout.addWidget(button)
            self.sidebar_buttons.append(button)
        layout.addStretch()
        return sidebar

    def _make_top_tabs(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topTabs")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(2)
        self.nav_buttons = []
        for index, (label, subtitle) in enumerate((
            ("Élő", "Mérés és hőtérkép"),
            ("Kalibráció", "Kalibrációs pontok"),
            ("Elemzés", "Riportok és statisztika"),
            ("Rendszer", "Kamera és beállítások"),
        )):
            button = QToolButton()
            button.setObjectName("topTab")
            button.setText(f"{label}\n{subtitle}")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setFixedHeight(48)
            button.clicked.connect(lambda checked, i=index: self._switch_page(i))
            layout.addWidget(button)
            self.nav_buttons.append(button)
        layout.addStretch()
        project_name = self.project_data.get("name", "Nincs projekt")
        patient = self.project_data.get("patient", {})
        context = QLabel(f"{project_name}  •  {patient.get('name', 'Nincs páciens')}")
        context.setObjectName("workspaceContext")
        layout.addWidget(context)
        return bar

    def _add_menu(self, layout: QHBoxLayout, title: str, items: tuple):
        button = QToolButton()
        button.setObjectName("appMenuItem")
        button.setText(title)
        button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(button)
        for item in items:
            if item is None:
                menu.addSeparator()
                continue
            action = QAction(item[0], self)
            action.triggered.connect(item[1])
            menu.addAction(action)
        button.setMenu(menu)
        layout.addWidget(button)

    def _make_options_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("optionsBar")
        bar.setFixedHeight(32)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)

        home = QToolButton()
        home.setObjectName("toolbarButton")
        home.setText("⌂")
        home.setToolTip("Élő nézet")
        home.clicked.connect(lambda: self._switch_page(0))
        layout.addWidget(home)

        tool_label = QLabel("Munkaterület")
        tool_label.setObjectName("toolbarLabel")
        layout.addWidget(tool_label)

        layout.addWidget(self._make_toolbar_combo("Forrás:", ("Kamera", "Videófájl")))
        layout.addWidget(self._make_toolbar_combo("Mód:", ("Képi ingerek", "Stroop teszt")))
        layout.addWidget(self._make_toolbar_combo("Méret:", ("Illesztés", "100%", "75%")))
        layout.addStretch()

        hint = QLabel("Kész • F11 teljes képernyő")
        hint.setObjectName("toolbarHint")
        layout.addWidget(hint)
        return bar

    def _make_toolbar_combo(self, label: str, values: tuple) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(QLabel(label))
        combo = QComboBox()
        combo.addItems(values)
        combo.setFixedHeight(24)
        combo.setMinimumWidth(110)
        layout.addWidget(combo)
        return wrapper

    def _make_tool_toolbar(self) -> QWidget:
        toolbar = QFrame()
        toolbar.setObjectName("toolToolbar")
        toolbar.setFixedWidth(118)
        layout = QVBoxLayout(toolbar)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(4)

        self.nav_buttons = []
        for index, (label, icon, tip) in enumerate((
            ("Élő", "◉", "Élő mérés és hőtérkép"),
            ("Kalibráció", "✥", "Kalibráció"),
            ("Elemzés", "▣", "Riportok elemzése"),
            ("Rendszer", "⚙", "Rendszer és beállítások"),
        )):
            button = QToolButton()
            button.setObjectName("toolButton")
            button.setText(f"{icon}  {label}")
            button.setToolTip(tip)
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setFixedHeight(32)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.clicked.connect(lambda checked, i=index: self._switch_page(i))
            layout.addWidget(button)
            self.nav_buttons.append(button)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("toolbarSeparator")
        layout.addWidget(separator)

        tools_title = QLabel("ESZKÖZÖK")
        tools_title.setObjectName("toolbarSection")
        layout.addWidget(tools_title)
        for label, tip in (
            ("Nagyítás", "Nagyítás"),
            ("Pupilla", "Pupilladetektor"),
            ("Hőtérkép", "Hőtérkép"),
        ):
            button = QToolButton()
            button.setObjectName("toolButton")
            button.setText(label)
            button.setToolTip(tip)
            button.setFixedHeight(28)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            layout.addWidget(button)

        layout.addStretch()
        colors = QFrame()
        colors.setObjectName("colorSwatches")
        colors.setFixedSize(26, 34)
        layout.addWidget(colors, alignment=Qt.AlignHCenter)
        return toolbar

    def _make_right_dock(self) -> QWidget:
        dock = QFrame()
        dock.setObjectName("rightDock")
        dock.setFixedWidth(260)
        layout = QVBoxLayout(dock)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QHBoxLayout()
        tabs.setContentsMargins(0, 0, 0, 0)
        for text in ("Tulajdonságok", "Mérések"):
            tab = QToolButton()
            tab.setObjectName("dockTab")
            tab.setText(text)
            tabs.addWidget(tab)
        layout.addLayout(tabs)

        properties = QGroupBox("Aktuális állapot")
        properties.setObjectName("dockGroup")
        properties_layout = QGridLayout(properties)
        properties_layout.setContentsMargins(10, 14, 10, 10)
        properties_layout.setHorizontalSpacing(8)
        for row, (label, value) in enumerate((
            ("Forrás", "hdr_cam_status"),
            ("Detektor", "hdr_det_status"),
            ("Mintavétel", "metric_fps"),
            ("Konfidencia", "metric_conf"),
        )):
            properties_layout.addWidget(QLabel(label), row, 0)
            value_label = QLabel("–")
            value_label.setObjectName("dockValue")
            properties_layout.addWidget(value_label, row, 1)
            if value == "metric_fps":
                self._dock_fps = value_label
            elif value == "metric_conf":
                self._dock_conf = value_label
        layout.addWidget(properties)

        layers = QGroupBox("Munkamenet")
        layers.setObjectName("dockGroup")
        layers_layout = QVBoxLayout(layers)
        layers_layout.setContentsMargins(8, 14, 8, 8)
        for text in ("Élő adatfolyam", "Pupillometriai idősor",
                     "Tekintetvektor", "Aktív riport"):
            item = QToolButton()
            item.setObjectName("dockItem")
            item.setText("◉  " + text)
            item.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            layers_layout.addWidget(item)
        layers_layout.addStretch()
        layout.addWidget(layers, stretch=1)
        return dock

    def _switch_page(self, idx: int):
        self.main_stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == idx)
        for i, btn in enumerate(getattr(self, "sidebar_buttons", [])):
            btn.setChecked(i == idx)
        # Analyze oldalra váltva frissítjük a riportlistát
        if idx == 2:
            QTimer.singleShot(50, self._analyze_refresh)

    def _open_panel_fullscreen(self, widget: QWidget, title: str):
        if widget is None:
            return
        original_parent = widget.parentWidget()
        original_layout = original_parent.layout() if original_parent else None
        if original_layout is None:
            return
        original_index = original_layout.indexOf(widget)
        original_layout.removeWidget(widget)

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setStyleSheet(build_stylesheet())
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(12, 12, 12, 12)
        widget.setParent(dialog)
        dialog_layout.addWidget(widget)
        dialog.finished.connect(
            lambda: self._restore_fullscreen_widget(
                widget, original_parent, original_layout, original_index
            )
        )
        dialog.showFullScreen()

    @staticmethod
    def _restore_fullscreen_widget(widget, parent, layout, index):
        widget.setParent(parent)
        layout.insertWidget(max(index, 0), widget)

    def _reset_workspace(self):
        self._switch_page(0)
        self._switch_exp_view("live")
        if hasattr(self, "gaze_monitor"):
            self.gaze_monitor.reset_view()

    def _show_shortcuts(self):
        QMessageBox.information(
            self,
            "Billentyűparancsok",
            "F11  Teljes képernyő\n"
            "Esc  Kilépés teljes képernyőből\n"
            "Ctrl+O  Videófájl megnyitása",
        )

    def _show_about(self):
        QMessageBox.information(
            self,
            "Neural Eye Tracker",
            "Neural Eye Tracker\nValós idejű pupilla- és tekintetkövető rendszer",
        )

    def _check_for_updates(self):
        manager = UpdateManager()
        available, version, setup_url, page = manager.check()
        if not available:
            if version is None:
                QMessageBox.warning(
                    self,
                    "Frissítés",
                    "A GitHub kiadási információi jelenleg nem érhetők el.",
                )
            else:
                QMessageBox.information(
                    self,
                    "Frissítés",
                    f"Az alkalmazás naprakész (v{manager.current_version}).",
                )
            return
        if not setup_url:
            QMessageBox.information(
                self,
                "Frissítés",
                f"Új verzió érhető el: v{version}\n\nA kiadási oldal megnyitása szükséges.",
            )
            import webbrowser
            webbrowser.open(page)
            return
        answer = QMessageBox.question(
            self,
            "Frissítés érhető el",
            f"Új verzió érhető el: v{version}. Letöltsem és indítsam a telepítőt?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            path = manager.download_and_launch(setup_url)
        except OSError as error:
            QMessageBox.critical(self, "Frissítési hiba", str(error))
            return
        QMessageBox.information(
            self,
            "Frissítés",
            f"A telepítő letöltve:\n{path}\n\nA frissítés a telepítő bezárása után fejeződik be.",
        )

    def _save_project_as(self):
        if not self.project_data:
            QMessageBox.warning(self, "Projekt mentése", "Nincs aktív projekt.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Projekt mentése másként", "", "Neural Eye projekt (*.nep)"
        )
        if not path:
            return
        if not path.lower().endswith(".nep"):
            path += ".nep"
        try:
            save_project(path, self.project_data)
        except OSError as error:
            QMessageBox.critical(self, "Mentési hiba", str(error))
            return
        self.project_path = path
        self._set_status(f"Projekt mentve: {os.path.basename(path)}")

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        self._update_fullscreen_button()

    def _update_fullscreen_button(self):
        if not hasattr(self, "fullscreen_btn"):
            return
        if self.isFullScreen():
            self.fullscreen_btn.setText("Ablakos nézet")
            self.fullscreen_btn.setToolTip("Visszatérés ablakos nézetbe (F11 vagy Esc)")
        else:
            self.fullscreen_btn.setText("Teljes képernyő")
            self.fullscreen_btn.setToolTip("Teljes képernyő be- vagy kikapcsolása (F11)")

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_F11:
            self._toggle_fullscreen()
            event.accept()
            return
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self.showNormal()
            self._update_fullscreen_button()
            event.accept()
            return
        super().keyPressEvent(event)

    # ============================================================
    # ÉLŐ OLDAL
    # ============================================================
    def _make_live_page(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # BAL: mért csatornák
        left = QFrame()
        left.setObjectName("sidePanel")
        left.setFixedWidth(240)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        left_title = QLabel("Mért csatornák")
        left_title.setObjectName("sectionTitle")
        left_layout.addWidget(left_title)

        self.metric_conf = self._make_metric("Konfidencia", "0.00")
        self.metric_size = self._make_metric("Átmérő", "1.00")
        self.metric_az = self._make_metric("Yaw", "0.0°")
        self.metric_el = self._make_metric("Pitch", "0.0°")
        self.metric_pos_x = self._make_metric("Centrum X", "0 px")
        self.metric_pos_y = self._make_metric("Centrum Y", "0 px")
        self.metric_radius = self._make_metric("Sugár", "0 px")
        self.metric_fps = self._make_metric("Mintavétel", "0 Hz")

        for m in [self.metric_conf, self.metric_size, self.metric_az, self.metric_el,
                  self.metric_pos_x, self.metric_pos_y, self.metric_radius, self.metric_fps]:
            left_layout.addWidget(m)
        left_layout.addStretch()
        root.addWidget(left)

        # KÖZÉP
        center = QFrame()
        center.setObjectName("centerPanel")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(16, 16, 16, 16)
        center_layout.setSpacing(12)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        t1 = QLabel("Élő tekintetkövetés")
        t1.setObjectName("sectionTitle")
        title_box.addWidget(t1)
        t2 = QLabel("Valós idejű hőtérkép és pupillometriai telemetria")
        t2.setObjectName("sectionSubtitle")
        title_box.addWidget(t2)
        header.addLayout(title_box)
        header.addStretch()

        self.btn_view_live = QToolButton()
        self.btn_view_live.setText("Élő hőtérkép")
        self.btn_view_live.setProperty("class", "toggle")
        self.btn_view_live.setCheckable(True)
        self.btn_view_live.setChecked(True)
        self.btn_view_live.clicked.connect(lambda: self._switch_exp_view("live"))
        header.addWidget(self.btn_view_live)

        self.btn_view_report = QToolButton()
        self.btn_view_report.setText("Riport")
        self.btn_view_report.setProperty("class", "toggle")
        self.btn_view_report.setCheckable(True)
        self.btn_view_report.clicked.connect(lambda: self._switch_exp_view("report"))
        header.addWidget(self.btn_view_report)

        center_layout.addLayout(header)

        self.exp_stack = QStackedWidget()
        self.exp_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        live_page = QWidget()
        live_l = QVBoxLayout(live_page)
        live_l.setContentsMargins(0, 0, 0, 0)
        self.gaze_monitor = LiveGazeMonitor()
        live_l.addWidget(self.gaze_monitor)
        self.exp_stack.addWidget(live_page)

        self.report_viewer = ReportViewer()
        self.exp_stack.addWidget(self.report_viewer)

        center_layout.addWidget(self.exp_stack, stretch=4)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        spatial_group = QGroupBox("Tekintetvektor")
        spatial_layout = QVBoxLayout(spatial_group)
        spatial_layout.setContentsMargins(10, 14, 10, 10)
        spatial_fullscreen = QPushButton("Teljes nézet")
        spatial_fullscreen.setProperty("class", "ghost")
        spatial_fullscreen.clicked.connect(
            lambda: self._open_panel_fullscreen(self.gl_widget, "Tekintetvektor")
        )
        spatial_layout.addWidget(spatial_fullscreen, alignment=Qt.AlignRight)
        try:
            from ui.eye_widget import EyeGLWidget
            self.gl_widget = EyeGLWidget()
            self.gl_widget.setMinimumHeight(160)
            self.gl_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            spatial_layout.addWidget(self.gl_widget, stretch=1)
        except Exception:
            err = QLabel("3D nézet nem elérhető")
            err.setAlignment(Qt.AlignCenter)
            spatial_layout.addWidget(err, stretch=1)
        bottom_row.addWidget(spatial_group, stretch=1)

        graph_group = QGroupBox("Pupillometriai idősor")
        graph_layout = QVBoxLayout(graph_group)
        graph_layout.setContentsMargins(10, 14, 10, 10)
        graph_fullscreen = QPushButton("Teljes nézet")
        graph_fullscreen.setProperty("class", "ghost")
        graph_fullscreen.clicked.connect(
            lambda: self._open_panel_fullscreen(self.pupil_graph, "Pupillometriai idősor")
        )
        graph_layout.addWidget(graph_fullscreen, alignment=Qt.AlignRight)
        self.pupil_graph = PupilGraph()
        self.pupil_graph.register_series("size", QColor(PALETTE['accent_primary']), "Átmérő")
        self.pupil_graph.register_series("conf", QColor(PALETTE['accent_success']), "Stabilitás")
        self.pupil_graph.register_series("radius", QColor(PALETTE['accent_warning']), "Sugár (px)")
        graph_layout.addWidget(self.pupil_graph, stretch=1)
        bottom_row.addWidget(graph_group, stretch=1)

        center_layout.addLayout(bottom_row, stretch=2)

        # Kísérlet vezérlés
        exp_card = QFrame()
        exp_card.setObjectName("card")
        exp_layout = QHBoxLayout(exp_card)
        exp_layout.setContentsMargins(14, 12, 14, 12)
        exp_layout.setSpacing(10)

        exp_layout.addWidget(QLabel("Alany:"))
        patient = self.project_data.get("patient", {})
        self.subject_input = QLineEdit(patient.get("patient_id", ""))
        self.subject_input.setFixedWidth(120)
        exp_layout.addWidget(self.subject_input)

        exp_layout.addWidget(QLabel("Mód:"))
        self.exp_mode_combo = QComboBox()
        self.exp_mode_combo.addItem("Képi ingerek", "images")
        self.exp_mode_combo.addItem("Stroop teszt", "stroop")
        self.exp_mode_combo.setFixedWidth(160)
        exp_layout.addWidget(self.exp_mode_combo)

        exp_layout.addSpacing(16)
        exp_layout.addWidget(QLabel("Próba:"))
        self.lbl_trial = QLabel("0 / 0")
        self.lbl_trial.setStyleSheet(
            f"color: {PALETTE['accent_primary']}; "
            f"font-weight: 700; font-family: {FONT_MONO}; font-size: 13px;"
        )
        self.lbl_trial.setFixedWidth(70)
        exp_layout.addWidget(self.lbl_trial)

        exp_layout.addWidget(QLabel("Fázis:"))
        self.lbl_phase = QLabel("Készenlét")
        self.lbl_phase.setStyleSheet("font-weight: 600;")
        self.lbl_phase.setFixedWidth(100)
        exp_layout.addWidget(self.lbl_phase)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(150)
        exp_layout.addWidget(self.progress)
        exp_layout.addStretch()

        self.start_exp_btn = QPushButton("Kísérlet indítása")
        self.start_exp_btn.setProperty("class", "primary")
        self.start_exp_btn.setMinimumHeight(34)
        self.start_exp_btn.clicked.connect(self._start_experiment)
        exp_layout.addWidget(self.start_exp_btn)

        self.stop_exp_btn = QPushButton("Stop")
        self.stop_exp_btn.setProperty("class", "danger")
        self.stop_exp_btn.setMinimumHeight(34)
        self.stop_exp_btn.setEnabled(False)
        self.stop_exp_btn.clicked.connect(self._stop_experiment)
        exp_layout.addWidget(self.stop_exp_btn)

        center_layout.addWidget(exp_card)
        root.addWidget(center, stretch=1)

        # JOBB
        right = QFrame()
        right.setObjectName("rightPanel")
        right.setFixedWidth(320)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        cam_title = QLabel("Szenzor kamera")
        cam_title.setObjectName("sectionTitle")
        right_layout.addWidget(cam_title)

        self.camera_view = QLabel()
        self.camera_view.setFixedSize(296, 222)
        self.camera_view.setStyleSheet(
            f"background-color: #000; "
            f"border: 1px solid {PALETTE['border']}; border-radius: 4px;"
        )
        right_layout.addWidget(self.camera_view, alignment=Qt.AlignCenter)

        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("Bemenet:"))
        self.live_cam_combo = QComboBox()
        self.live_cam_combo.addItems(["Kamera 0", "Kamera 1", "Kamera 2"])
        src_row.addWidget(self.live_cam_combo, stretch=1)
        right_layout.addLayout(src_row)

        btn_row = QHBoxLayout()
        self.live_cam_start_btn = QPushButton("Kamera")
        self.live_cam_start_btn.clicked.connect(self._start)
        btn_row.addWidget(self.live_cam_start_btn)
        self.live_video_open_btn = QPushButton("Fájl...")
        self.live_video_open_btn.clicked.connect(self._open_video)
        btn_row.addWidget(self.live_video_open_btn)
        right_layout.addLayout(btn_row)

        hist_title = QLabel("Korábbi riportok")
        hist_title.setObjectName("sectionTitle")
        right_layout.addWidget(hist_title)

        self.history_list = QListWidget()
        self.history_list.setMinimumHeight(200)
        self.history_list.itemDoubleClicked.connect(self._on_history_open)
        self.history_list.itemClicked.connect(self._on_history_selected)
        right_layout.addWidget(self.history_list, stretch=1)

        self.open_report_btn = QPushButton("Megnyitás")
        self.open_report_btn.setEnabled(False)
        self.open_report_btn.clicked.connect(self._open_selected_report)
        right_layout.addWidget(self.open_report_btn)

        root.addWidget(right)
        return page

    def _make_metric(self, label: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setFixedHeight(46)
        v = QVBoxLayout(card)
        v.setContentsMargins(10, 5, 10, 5)
        v.setSpacing(0)
        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"color: {PALETTE['metric_label']}; "
            f"font-size: {FONT_SIZE_XS}px; font-weight: 600; letter-spacing: 0.5px;"
        )
        val = QLabel(value)
        val.setStyleSheet(
            f"color: {PALETTE['metric_value']}; "
            f"font-size: {FONT_SIZE_LG}px; font-weight: 700; "
            f"font-family: {FONT_MONO};"
        )
        v.addWidget(lbl)
        v.addWidget(val)
        card._value_label = val
        return card

    def _set_metric(self, card, value):
        if hasattr(card, "_value_label"):
            card._value_label.setText(value)

    def _switch_exp_view(self, which: str):
        if which == "live":
            self.exp_stack.setCurrentIndex(0)
            self.btn_view_live.setChecked(True)
            self.btn_view_report.setChecked(False)
        else:
            self.exp_stack.setCurrentIndex(1)
            self.btn_view_live.setChecked(False)
            self.btn_view_report.setChecked(True)

    # ============================================================
    # KALIBRÁCIÓ OLDAL
    # ============================================================
    def _make_calibration_page(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        left_inner = QWidget()
        left_col = QVBoxLayout(left_inner)
        left_col.setContentsMargins(12, 12, 12, 12)
        left_col.setSpacing(12)

        cam_group = QGroupBox("Videóbemenet")
        cam_layout = QVBoxLayout(cam_group)
        cam_layout.setContentsMargins(12, 16, 12, 12)
        row = QHBoxLayout()
        row.addWidget(QLabel("Kamera:"))
        self.cam_combo = QComboBox()
        self.cam_combo.addItems(["Kamera 0", "Kamera 1", "Kamera 2"])
        row.addWidget(self.cam_combo, stretch=1)
        cam_layout.addLayout(row)

        self.flip_h_cb = QCheckBox("Vízszintes tükrözés")
        self.flip_h_cb.setChecked(True)
        self.flip_h_cb.stateChanged.connect(self._on_flip_changed_sett)
        cam_layout.addWidget(self.flip_h_cb)

        self.flip_v_cb = QCheckBox("Függőleges tükrözés")
        self.flip_v_cb.stateChanged.connect(self._on_flip_changed_sett)
        cam_layout.addWidget(self.flip_v_cb)

        cam_layout.addSpacing(6)
        cam_layout.addWidget(QLabel("Megjelenítési stílus:"))
        self.style_combo = QComboBox()
        for sid, sname in PUPIL_STYLES.items():
            self.style_combo.addItem(sname, sid)
        self.style_combo.currentIndexChanged.connect(self._on_style_changed)
        cam_layout.addWidget(self.style_combo)
        left_col.addWidget(cam_group)

        det_group = QGroupBox("Pupilla küszöbök")
        det_layout = QVBoxLayout(det_group)
        det_layout.setContentsMargins(12, 16, 12, 12)
        det_layout.setSpacing(10)
        slider_defs = [
            ("Küszöbérték", 10, 120, 40),
            ("Min terület (px)", 10, 500, 30),
            ("Max terület (px)", 500, 10000, 6000),
            ("Kerekségi tolerancia", 20, 80, 30),
            ("Max sötétség", 40, 150, 80),
        ]
        for label, lo, hi, default in slider_defs:
            r = QHBoxLayout()
            r.setSpacing(8)
            lbl = QLabel(label)
            lbl.setMinimumWidth(150)
            lbl.setStyleSheet(f"color: {PALETTE['text_secondary']};")
            r.addWidget(lbl)
            s = QSlider(Qt.Horizontal)
            s.setRange(lo, hi)
            s.setValue(default)
            r.addWidget(s, stretch=1)
            vl = QLabel(str(default))
            vl.setFixedWidth(50)
            vl.setStyleSheet(
                f"color: {PALETTE['accent_primary']}; font-family: {FONT_MONO}; "
                f"font-weight: 700; background-color: {PALETTE['bg_input']}; "
                f"border-radius: 3px; padding: 2px 6px;"
            )
            s.valueChanged.connect(lambda v, l=vl: l.setText(str(v)))
            r.addWidget(vl)
            det_layout.addLayout(r)
        left_col.addWidget(det_group)

        trk_group = QGroupBox("Simítás és Kálmán-szűrés")
        trk_layout = QVBoxLayout(trk_group)
        trk_layout.setContentsMargins(12, 16, 12, 12)
        trk_layout.setSpacing(10)
        tracker_defs = [
            ("Pozíció simítás (%)", 10, 99, 85),
            ("Geometriai simítás (%)", 10, 99, 75),
            ("Ugrás küszöb (px)", 20, 200, 70),
            ("Min konfidencia (%)", 15, 80, 35),
        ]
        for label, lo, hi, default in tracker_defs:
            r = QHBoxLayout()
            r.setSpacing(8)
            lbl = QLabel(label)
            lbl.setMinimumWidth(150)
            lbl.setStyleSheet(f"color: {PALETTE['text_secondary']};")
            r.addWidget(lbl)
            s = QSlider(Qt.Horizontal)
            s.setRange(lo, hi)
            s.setValue(default)
            r.addWidget(s, stretch=1)
            vl = QLabel(str(default))
            vl.setFixedWidth(50)
            vl.setStyleSheet(
                f"color: {PALETTE['accent_primary']}; font-family: {FONT_MONO}; "
                f"font-weight: 700; background-color: {PALETTE['bg_input']}; "
                f"border-radius: 3px; padding: 2px 6px;"
            )
            s.valueChanged.connect(lambda v, l=vl: l.setText(str(v)))
            r.addWidget(vl)
            trk_layout.addLayout(r)
        left_col.addWidget(trk_group)
        left_col.addStretch()

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left_inner)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setFixedWidth(420)
        left_scroll.setStyleSheet(
            f"QScrollArea {{ background: {PALETTE['bg_panel']}; border: none; }}"
        )
        root.addWidget(left_scroll)

        try:
            from ui.stimulus_manager import StimulusManager
            self.stimulus_manager = StimulusManager(stimuli_dir="stimuli")
            self.stimulus_manager.categories_changed.connect(self._on_categories_changed)
            root.addWidget(self.stimulus_manager, stretch=1)
        except Exception as e:
            err = QLabel(f"Ingerkategória-kezelő nem elérhető:\n\n{e}")
            err.setAlignment(Qt.AlignCenter)
            err.setWordWrap(True)
            err.setStyleSheet(f"color: {PALETTE['accent_danger']}; font-size: 12px; padding: 20px;")
            root.addWidget(err, stretch=1)
            self.stimulus_manager = None

        return page

    # ============================================================
    # ANALYZE OLDAL – VALÓDI ADATELEMZÉS
    # ============================================================
    def _make_analyze_page(self) -> QWidget:
        from core.report_loader import ReportLoader
        from core.analyzer import Analyzer, METRICS
        from ui.analyze_chart import AnalyzeChart

        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._analyze_loader = ReportLoader(reports_dir=REPORTS_DIR)
        self._analyze_reports = []
        self._analyze_selected = []
        self._analyze_analyzer = None

        # ---------- BAL: rögzítések ----------
        left = QFrame()
        left.setObjectName("sidePanel")
        left.setFixedWidth(280)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        head = QFrame()
        head.setObjectName("panelSection")
        hh = QHBoxLayout(head)
        hh.setContentsMargins(12, 8, 12, 8)
        ic = QLabel("▦")
        ic.setObjectName("panelSectionIcon")
        hh.addWidget(ic)
        t = QLabel("Rögzítések")
        t.setObjectName("panelSectionTitle")
        hh.addWidget(t)
        hh.addStretch()
        self.analyze_count_lbl = QLabel("0")
        self.analyze_count_lbl.setStyleSheet(
            f"color: {PALETTE['accent_primary']}; "
            f"font-family: {FONT_MONO}; font-weight: 700;"
        )
        hh.addWidget(self.analyze_count_lbl)
        left_layout.addWidget(head)

        search_wrap = QWidget()
        sw = QVBoxLayout(search_wrap)
        sw.setContentsMargins(10, 10, 10, 6)
        self.analyze_search = QLineEdit()
        self.analyze_search.setPlaceholderText("Keresés alany szerint...")
        self.analyze_search.textChanged.connect(self._analyze_filter_list)
        sw.addWidget(self.analyze_search)
        left_layout.addWidget(search_wrap)

        self.analyze_list = QListWidget()
        self.analyze_list.setStyleSheet(
            f"QListWidget {{ background: {PALETTE['bg_panel']}; border: none; "
            f"border-top: 1px solid {PALETTE['border']}; "
            f"border-bottom: 1px solid {PALETTE['border']}; }}"
        )
        self.analyze_list.itemChanged.connect(self._analyze_on_item_changed)
        left_layout.addWidget(self.analyze_list, stretch=1)

        btn_wrap = QWidget()
        bw = QVBoxLayout(btn_wrap)
        bw.setContentsMargins(10, 8, 10, 10)
        bw.setSpacing(6)

        b_row = QHBoxLayout()
        self.analyze_btn_all = QPushButton("Összes")
        self.analyze_btn_all.clicked.connect(lambda: self._analyze_set_all(True))
        b_row.addWidget(self.analyze_btn_all)
        self.analyze_btn_none = QPushButton("Egyik sem")
        self.analyze_btn_none.clicked.connect(lambda: self._analyze_set_all(False))
        b_row.addWidget(self.analyze_btn_none)
        bw.addLayout(b_row)

        self.analyze_btn_refresh = QPushButton("Frissítés")
        self.analyze_btn_refresh.setProperty("class", "primary")
        self.analyze_btn_refresh.clicked.connect(self._analyze_refresh)
        bw.addWidget(self.analyze_btn_refresh)

        left_layout.addWidget(btn_wrap)
        root.addWidget(left)

        # ---------- KÖZÉP: grafikon ----------
        center = QFrame()
        center.setObjectName("centerPanel")
        cl = QVBoxLayout(center)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(12)

        header = QHBoxLayout()
        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        self.analyze_title = QLabel("Metrika vizualizáció")
        self.analyze_title.setObjectName("sectionTitle")
        t_box.addWidget(self.analyze_title)
        self.analyze_subtitle = QLabel("Válassz metrikát és rögzítéseket")
        self.analyze_subtitle.setObjectName("sectionSubtitle")
        t_box.addWidget(self.analyze_subtitle)
        header.addLayout(t_box)
        header.addStretch()

        header.addWidget(QLabel("Grafikon:"))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItem("Scatter", "scatter")
        self.chart_type_combo.addItem("Box plot", "box")
        self.chart_type_combo.addItem("Bar chart", "bar")
        self.chart_type_combo.addItem("3D idősor", "3d_surface")
        self.chart_type_combo.setFixedWidth(120)
        self.chart_type_combo.currentIndexChanged.connect(self._analyze_update_chart)
        header.addWidget(self.chart_type_combo)

        cl.addLayout(header)

        self.analyze_chart = AnalyzeChart()
        cl.addWidget(self.analyze_chart, stretch=1)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        # Csoportosítás
        grp_card = QFrame()
        grp_card.setObjectName("card")
        grp_l = QVBoxLayout(grp_card)
        grp_l.setContentsMargins(12, 10, 12, 12)
        grp_l.setSpacing(8)
        grp_title = QLabel("Csoportosítás")
        grp_title.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-weight: 600; "
            f"font-size: {FONT_SIZE_MD}px;"
        )
        grp_l.addWidget(grp_title)

        self.group_by_combo = QComboBox()
        self.group_by_combo.addItem("Kategória", "category")
        self.group_by_combo.addItem("Alany", "subject")
        self.group_by_combo.addItem("Munkamenet", "session")
        self.group_by_combo.addItem("Összes (egy csoport)", "all")
        self.group_by_combo.currentIndexChanged.connect(self._analyze_update_chart)
        grp_l.addWidget(self.group_by_combo)

        grp_l.addSpacing(4)
        grp_l.addWidget(QLabel("Kategória szűrő:"))
        self.cat_filter_list = QListWidget()
        self.cat_filter_list.setMaximumHeight(120)
        self.cat_filter_list.setSelectionMode(QListWidget.MultiSelection)
        self.cat_filter_list.itemSelectionChanged.connect(self._analyze_update_chart)
        grp_l.addWidget(self.cat_filter_list)

        bottom.addWidget(grp_card, stretch=1)

        # Statisztika
        stat_card = QFrame()
        stat_card.setObjectName("card")
        st_l = QVBoxLayout(stat_card)
        st_l.setContentsMargins(12, 10, 12, 12)
        st_l.setSpacing(6)
        st_title = QLabel("Statisztika")
        st_title.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-weight: 600; "
            f"font-size: {FONT_SIZE_MD}px;"
        )
        st_l.addWidget(st_title)

        self.stat_table = QTableWidget()
        self.stat_table.setColumnCount(6)
        self.stat_table.setHorizontalHeaderLabels(
            ["Csoport", "N", "Átlag", "Medián", "Szórás", "Min / Max"]
        )
        self.stat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stat_table.verticalHeader().setVisible(False)
        self.stat_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stat_table.setMaximumHeight(180)
        st_l.addWidget(self.stat_table)

        bottom.addWidget(stat_card, stretch=2)

        # Export
        exp_card = QFrame()
        exp_card.setObjectName("card")
        exp_l = QVBoxLayout(exp_card)
        exp_l.setContentsMargins(12, 10, 12, 12)
        exp_l.setSpacing(8)
        exp_title = QLabel("Exportálás")
        exp_title.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-weight: 600; "
            f"font-size: {FONT_SIZE_MD}px;"
        )
        exp_l.addWidget(exp_title)

        self.btn_export_png = QPushButton("PNG mentés")
        self.btn_export_png.clicked.connect(lambda: self._analyze_export("png"))
        exp_l.addWidget(self.btn_export_png)

        self.btn_export_svg = QPushButton("SVG mentés")
        self.btn_export_svg.clicked.connect(lambda: self._analyze_export("svg"))
        exp_l.addWidget(self.btn_export_svg)

        self.btn_export_csv = QPushButton("CSV export")
        self.btn_export_csv.clicked.connect(lambda: self._analyze_export("csv"))
        exp_l.addWidget(self.btn_export_csv)

        exp_l.addStretch()
        bottom.addWidget(exp_card, stretch=1)

        cl.addLayout(bottom)
        root.addWidget(center, stretch=1)

        # ---------- JOBB: metrika + beállítások ----------
        right = QFrame()
        right.setObjectName("rightPanel")
        right.setFixedWidth(300)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        m_head = QFrame()
        m_head.setObjectName("panelSection")
        mh = QHBoxLayout(m_head)
        mh.setContentsMargins(12, 8, 12, 8)
        mi = QLabel("◆")
        mi.setObjectName("panelSectionIcon")
        mh.addWidget(mi)
        mt = QLabel("Metrika")
        mt.setObjectName("panelSectionTitle")
        mh.addWidget(mt)
        mh.addStretch()
        rl.addWidget(m_head)

        m_body = QWidget()
        m_l = QVBoxLayout(m_body)
        m_l.setContentsMargins(12, 12, 12, 12)
        m_l.setSpacing(6)

        self.metric_combo = QComboBox()
        for key, info in METRICS.items():
            self.metric_combo.addItem(info["label"], key)
        self.metric_combo.currentIndexChanged.connect(self._analyze_update_chart)
        m_l.addWidget(self.metric_combo)
        rl.addWidget(m_body)

        s_head = QFrame()
        s_head.setObjectName("panelSection")
        sh = QHBoxLayout(s_head)
        sh.setContentsMargins(12, 8, 12, 8)
        si = QLabel("⚙")
        si.setObjectName("panelSectionIcon")
        sh.addWidget(si)
        st = QLabel("Beállítások")
        st.setObjectName("panelSectionTitle")
        sh.addWidget(st)
        sh.addStretch()
        rl.addWidget(s_head)

        s_body = QWidget()
        s_l = QVBoxLayout(s_body)
        s_l.setContentsMargins(12, 12, 12, 12)
        s_l.setSpacing(8)

        ref_row = QHBoxLayout()
        ref_row.addWidget(QLabel("Referencia:"))
        self.ref_slider = QSlider(Qt.Horizontal)
        self.ref_slider.setRange(0, 2000)
        self.ref_slider.setValue(0)
        ref_row.addWidget(self.ref_slider, stretch=1)
        self.ref_val_lbl = QLabel("0")
        self.ref_val_lbl.setFixedWidth(40)
        self.ref_val_lbl.setStyleSheet(
            f"color: {PALETTE['accent_primary']}; font-family: {FONT_MONO}; "
            f"font-weight: 700;"
        )
        self.ref_slider.valueChanged.connect(self._on_ref_changed)
        ref_row.addWidget(self.ref_val_lbl)
        s_l.addLayout(ref_row)

        self.ref_enable_cb = QCheckBox("Referencia vonal megjelenítése")
        self.ref_enable_cb.stateChanged.connect(self._analyze_update_chart)
        s_l.addWidget(self.ref_enable_cb)

        s_l.addSpacing(8)

        self.btn_ttest = QPushButton("t-próba (első 2 csoport)")
        self.btn_ttest.clicked.connect(self._analyze_run_ttest)
        s_l.addWidget(self.btn_ttest)

        self.ttest_result = QLabel("")
        self.ttest_result.setWordWrap(True)
        self.ttest_result.setStyleSheet(
            f"color: {PALETTE['text_secondary']}; font-size: {FONT_SIZE_SM}px; "
            f"background-color: {PALETTE['bg_input']}; "
            f"border: 1px solid {PALETTE['border']}; "
            f"border-radius: 3px; padding: 8px;"
        )
        self.ttest_result.setMinimumHeight(80)
        s_l.addWidget(self.ttest_result)

        s_l.addStretch()
        rl.addWidget(s_body, stretch=1)
        root.addWidget(right)

        QTimer.singleShot(200, self._analyze_refresh)
        return page

    # ============================================================
    # ANALYZE LOGIKA
    # ============================================================
    def _analyze_refresh(self):
        from core.report_loader import ReportLoader
        from core.analyzer import Analyzer

        self._analyze_loader = ReportLoader(reports_dir=REPORTS_DIR)
        self._analyze_reports = self._analyze_loader.scan()
        self._analyze_analyzer = Analyzer(self._analyze_reports)

        self.analyze_list.blockSignals(True)
        self.analyze_list.clear()
        for rep in self._analyze_reports:
            item = QListWidgetItem(rep.label())
            item.setData(Qt.UserRole, rep.path)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.analyze_list.addItem(item)
        self.analyze_list.blockSignals(False)

        self.cat_filter_list.clear()
        for cat in self._analyze_analyzer.all_categories():
            self.cat_filter_list.addItem(cat)

        self.analyze_count_lbl.setText(str(len(self._analyze_reports)))

        if self.analyze_list.count() > 0:
            self.analyze_list.item(0).setCheckState(Qt.Checked)
            self._analyze_update_selection()
        else:
            self.analyze_chart._draw_empty("Nincs JSON riport a reports/ mappában")
            self.analyze_subtitle.setText("Nincs elérhető rögzítés")

    def _analyze_filter_list(self, text: str):
        text = text.strip().lower()
        for i in range(self.analyze_list.count()):
            item = self.analyze_list.item(i)
            item.setHidden(text not in item.text().lower())

    def _analyze_set_all(self, state: bool):
        self.analyze_list.blockSignals(True)
        for i in range(self.analyze_list.count()):
            item = self.analyze_list.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.Checked if state else Qt.Unchecked)
        self.analyze_list.blockSignals(False)
        self._analyze_update_selection()

    def _analyze_on_item_changed(self, item):
        self._analyze_update_selection()

    def _analyze_update_selection(self):
        from core.analyzer import Analyzer

        selected = []
        for i in range(self.analyze_list.count()):
            item = self.analyze_list.item(i)
            if item.checkState() == Qt.Checked:
                path = item.data(Qt.UserRole)
                for rep in self._analyze_reports:
                    if rep.path == path:
                        selected.append(rep)
                        break

        self._analyze_selected = selected
        self._analyze_analyzer = Analyzer(selected)

        if not selected:
            self.analyze_subtitle.setText("Nincs kijelölt rögzítés")
        else:
            n_trials = sum(r.n_trials for r in selected)
            self.analyze_subtitle.setText(
                f"{len(selected)} rögzítés • {n_trials} próba • "
                f"{len(self._analyze_analyzer.all_categories())} kategória"
            )

        self._analyze_update_chart()

    def _on_ref_changed(self, v):
        self.ref_val_lbl.setText(str(v))
        self._analyze_update_chart()

    def _analyze_update_chart(self):
        if self._analyze_analyzer is None:
            return

        metric_key = self.metric_combo.currentData()
        group_by = self.group_by_combo.currentData()

        selected_cats = [it.text() for it in self.cat_filter_list.selectedItems()]
        cat_filter = selected_cats if selected_cats else None

        data = self._analyze_analyzer.collect(
            metric_key, group_by=group_by, category_filter=cat_filter
        )

        chart_type = self.chart_type_combo.currentData()
        ref_line = float(self.ref_slider.value()) if self.ref_enable_cb.isChecked() else None

        self.analyze_chart.plot(data, chart_type=chart_type, ref_line=ref_line)
        self.analyze_title.setText(data.get("metric_label", ""))

        groups = data.get("groups", [])
        self.stat_table.setRowCount(len(groups))
        for i, g in enumerate(groups):
            self.stat_table.setItem(i, 0, QTableWidgetItem(g["name"]))
            self.stat_table.setItem(i, 1, QTableWidgetItem(str(g["n"])))
            self.stat_table.setItem(i, 2, QTableWidgetItem(f"{g['mean']:.3f}"))
            self.stat_table.setItem(i, 3, QTableWidgetItem(f"{g['median']:.3f}"))
            self.stat_table.setItem(i, 4, QTableWidgetItem(f"{g['std']:.3f}"))
            self.stat_table.setItem(i, 5, QTableWidgetItem(f"{g['min']:.2f} / {g['max']:.2f}"))

    def _analyze_run_ttest(self):
        if self._analyze_analyzer is None:
            return
        metric_key = self.metric_combo.currentData()
        data = self._analyze_analyzer.collect(metric_key, group_by="category")
        groups = data.get("groups", [])
        if len(groups) < 2:
            self.ttest_result.setText("Legalább 2 csoport szükséges.")
            return
        cat_a, cat_b = groups[0]["name"], groups[1]["name"]
        res = self._analyze_analyzer.compare_two_groups(metric_key, cat_a, cat_b)
        if res is None:
            self.ttest_result.setText("Nem sikerült (kevés adat).")
            return
        text = (
            f"<b>{cat_a}</b> vs <b>{cat_b}</b><br>"
            f"Átlag: {res['mean_a']:.3f} vs {res['mean_b']:.3f}<br>"
            f"Különbség: {res['diff']:+.3f}<br>"
        )
        if res.get("p_value") is not None:
            p = res["p_value"]
            sig = "SZIGNIFIKÁNS" if p < 0.05 else "nem szignifikáns"
            text += f"t = {res['t']:.3f}<br>p = {p:.4f} → {sig}"
        else:
            text += "(scipy nincs telepítve – csak leíró statisztika)"
        self.ttest_result.setText(text)

    def _analyze_export(self, fmt: str):
        if self._analyze_analyzer is None or not self._analyze_selected:
            QMessageBox.warning(self, "Figyelem", "Nincs kijelölt rögzítés!")
            return

        metric_key = self.metric_combo.currentData()
        group_by = self.group_by_combo.currentData()
        selected_cats = [it.text() for it in self.cat_filter_list.selectedItems()]
        cat_filter = selected_cats if selected_cats else None
        data = self._analyze_analyzer.collect(
            metric_key, group_by=group_by, category_filter=cat_filter
        )

        if fmt == "png":
            path, _ = QFileDialog.getSaveFileName(
                self, "PNG mentés", f"analyze_{metric_key}.png", "PNG (*.png)"
            )
            if path:
                if self.analyze_chart.save_png(path):
                    self._add_log(f"PNG mentve: {os.path.basename(path)}")
        elif fmt == "svg":
            path, _ = QFileDialog.getSaveFileName(
                self, "SVG mentés", f"analyze_{metric_key}.svg", "SVG (*.svg)"
            )
            if path:
                if self.analyze_chart.save_svg(path):
                    self._add_log(f"SVG mentve: {os.path.basename(path)}")
        elif fmt == "csv":
            path, _ = QFileDialog.getSaveFileName(
                self, "CSV export", f"analyze_{metric_key}.csv", "CSV (*.csv)"
            )
            if path:
                try:
                    import csv as _csv
                    with open(path, "w", newline="", encoding="utf-8") as f:
                        w = _csv.writer(f, delimiter=";")
                        w.writerow(["group", "n", "mean", "median", "std", "min", "max"])
                        for g in data.get("groups", []):
                            w.writerow([
                                g["name"], g["n"],
                                f"{g['mean']:.6f}", f"{g['median']:.6f}",
                                f"{g['std']:.6f}", f"{g['min']:.6f}", f"{g['max']:.6f}",
                            ])
                    self._add_log(f"CSV exportálva: {os.path.basename(path)}")
                except Exception as e:
                    QMessageBox.critical(self, "Hiba", f"CSV export hiba:\n{e}")

    # ============================================================
    # RENDSZER OLDAL
    # ============================================================
    def _make_system_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        info_group = QGroupBox("Futáskörnyezet")
        info_layout = QGridLayout(info_group)
        info_layout.setContentsMargins(14, 18, 14, 14)
        info_layout.setSpacing(10)

        params = [
            ("Verzió:", "version"),
            ("Python:", "python"),
            ("OpenCV:", "opencv"),
            ("Qt:", "qt"),
            ("OS:", "os"),
            ("Forrás:", "camera"),
            ("Képkockák:", "frames"),
        ]
        for idx, (label, key) in enumerate(params):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {PALETTE['text_secondary']};")
            info_layout.addWidget(lbl, idx, 0)
            val = QLabel("-")
            val.setStyleSheet(
                f"font-family: {FONT_MONO}; font-weight: 600; "
                f"color: {PALETTE['text_primary']};"
            )
            info_layout.addWidget(val, idx, 1)
            self.__dict__[f"_sys_{key}"] = val

        top_row.addWidget(info_group, stretch=1)

        desc_group = QGroupBox("Kutatási háttér")
        desc_layout = QVBoxLayout(desc_group)
        desc_layout.setContentsMargins(12, 16, 12, 12)
        desc_text = QTextEdit()
        desc_text.setReadOnly(True)
        desc_text.setPlainText(
            "Téma: Adaptív neurokognitív architektúrák\n"
            "Modul: Valós idejű okulometriai és pupillometriai mérőszoftver\n"
            "Konzulens: Dr. Kéri Szabolcs\n"
            "Intézmény: Tokaj-Hegyalja Egyetem\n\n"
            "Funkcionalitás:\n"
            "- Kétképernyős (Dual-Display) klinikai ingerprezentáció\n"
            "- Valós idejű akkumulált Gauss-hőtérkép és szakkád-lánc elemzés\n"
            "- 60 Hz mintavételű pupillometria és mikroszakkád-analízis\n"
            "- Analyze fül: JSON riportok statisztikai elemzése"
        )
        desc_layout.addWidget(desc_text)
        top_row.addWidget(desc_group, stretch=1)

        layout.addLayout(top_row, stretch=1)

        update_group = QGroupBox("Karbantartás")
        update_layout = QHBoxLayout(update_group)
        update_layout.setContentsMargins(12, 16, 12, 12)
        update_layout.addWidget(QLabel("GitHub Releases"))
        update_layout.addStretch()
        update_button = QPushButton("Frissítések keresése")
        update_button.setProperty("class", "primary")
        update_button.clicked.connect(self._check_for_updates)
        update_layout.addWidget(update_button)
        layout.addWidget(update_group)

        log_group = QGroupBox("Rendszernapló")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(12, 16, 12, 12)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        layout.addWidget(log_group, stretch=2)

        self._refresh_system_info()
        return page

    # ============================================================
    # Páciens-kijelző
    # ============================================================
    def _init_patient_screen(self):
        try:
            from ui.stimulus_window import StimulusWindow
        except Exception as e:
            print(f"[STIM] Hiba: {e}")
            return

        init_config = {
            "subject_id": self.project_data.get("patient", {}).get("patient_id", "unknown"),
            "mode": "images",
            "categories": {},
            "time_baseline": 4.0,
            "time_fixation": 1.0,
            "time_image": 3.0,
            "time_calibration": 1.2,
        }
        try:
            self.stim_win = StimulusWindow(self.tracker, config=init_config)
            self.stim_win.gaze_feed.connect(self._on_gaze_feed)
            self.stim_win.experiment_progress.connect(self._on_experiment_progress)
            self.stim_win.experiment_finished.connect(self._on_experiment_finished)
            self.stim_win.show()
            self._add_log("Páciens-kijelző megnyitva.")
        except Exception as e:
            print(f"[STIM] Hiba: {e}")
            self.stim_win = None

    def _on_gaze_feed(self, cv_img, rel_x, rel_y):
        if self.gaze_monitor is None:
            return
        try:
            self.gaze_monitor.set_frame(cv_img, rel_x, rel_y)
        except Exception as e:
            print(f"[GAZE FEED] Hiba: {e}")

    # ============================================================
    # KÍSÉRLET
    # ============================================================
    def _start_experiment(self):
        if not self.tracker.isRunning():
            QMessageBox.warning(self, "Figyelem", "Előbb indítsa el a kamerát!")
            return
        if self.stim_win is None:
            QMessageBox.warning(self, "Figyelem", "A páciens-kijelző nem elérhető!")
            return

        subject = self.subject_input.text().strip() or "SUBJ_001"

        categories = {}
        category_meta = {}
        if getattr(self, "stimulus_manager", None) is not None:
            categories = self.stimulus_manager.get_active_categories()
            category_meta = self.stimulus_manager.get_category_metadata()

        if self.exp_mode_combo.currentData() == "images" and not categories:
            QMessageBox.warning(self, "Figyelem",
                "Nincs aktív kategória!\n\nMenj a Kalibráció fülre.")
            return

        config = {
            "subject_id": subject,
            "mode": self.exp_mode_combo.currentData(),
            "categories": categories,
            "category_meta": category_meta,
            "time_baseline": 4.0,
            "time_fixation": 1.0,
            "time_image": 3.0,
            "time_calibration": 1.2,
        }

        self.start_exp_btn.setEnabled(False)
        self.stop_exp_btn.setEnabled(True)
        if hasattr(self, "gaze_monitor") and self.gaze_monitor is not None:
            self.gaze_monitor.reset_view()
        if hasattr(self, "pupil_graph") and self.pupil_graph is not None:
            self.pupil_graph.clear()
        self._switch_exp_view("live")

        try:
            self.stim_win.start_experiment(config=config)
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Nem sikerült elindítani:\n{e}")
            self.start_exp_btn.setEnabled(True)
            self.stop_exp_btn.setEnabled(False)
            return
        self._add_log(f"Kísérlet elindítva: {subject}")

    def _stop_experiment(self):
        if self.stim_win is not None:
            try:
                self.stim_win.return_to_standby()
            except Exception:
                pass
        if hasattr(self, "gaze_monitor") and self.gaze_monitor is not None:
            self.gaze_monitor.reset_view()
        self.start_exp_btn.setEnabled(True)
        self.stop_exp_btn.setEnabled(False)
        self.lbl_phase.setText("Megszakítva")
        self._add_log("Kísérlet megszakítva.")

    def _on_experiment_progress(self, info: dict):
        cur = info.get("current_trial", 0)
        tot = info.get("total_trials", 0)
        self.lbl_trial.setText(f"{cur} / {tot}")
        if tot > 0:
            self.progress.setValue(int(100 * cur / tot))
        self.lbl_phase.setText(str(info.get("phase", "-")).capitalize())

    def _on_experiment_finished(self, result):
        self.start_exp_btn.setEnabled(True)
        self.stop_exp_btn.setEnabled(False)
        self.lbl_phase.setText("Kész")
        self.progress.setValue(100)
        self.open_report_btn.setEnabled(True)
        if hasattr(self, "gaze_monitor") and self.gaze_monitor is not None:
            self.gaze_monitor.reset_view()
        self._scan_reports_bg()

        latest_path = None
        if self._reports_list:
            latest_path = self._reports_list[0][1]
        else:
            rp = getattr(result, "report_path", None)
            if rp and os.path.exists(rp):
                latest_path = rp

        if latest_path:
            self._show_report_in_main(latest_path)
            self._add_log(f"Riport betöltve: {os.path.basename(latest_path)}")
        else:
            self._add_log("Kísérlet kész, riport nem található.")

        if self.project_data and self.project_path:
            self.project_data.setdefault("sessions", []).append({
                "started_at": getattr(result, "session_start", 0),
                "finished_at": getattr(result, "session_end", 0),
                "patient_id": getattr(result, "subject_id", ""),
                "report_path": latest_path or "",
            })
            try:
                save_project(self.project_path, self.project_data)
            except OSError as error:
                self._add_log(f"Projektmentési hiba: {error}")

        # Analyze frissítés
        QTimer.singleShot(500, self._analyze_refresh)

    def _show_report_in_main(self, path: str):
        if self.report_viewer.load_report(path):
            self._switch_exp_view("report")
            self._last_report_path = path

    def _on_history_selected(self, item):
        self.open_report_btn.setEnabled(True)

    def _on_history_open(self, item):
        path = item.data(Qt.UserRole)
        if path and os.path.exists(path):
            self._show_report_in_main(path)

    def _open_selected_report(self):
        item = self.history_list.currentItem()
        if item:
            path = item.data(Qt.UserRole)
            if path and os.path.exists(path):
                self._show_report_in_main(path)
        elif self._reports_list:
            self._show_report_in_main(self._reports_list[0][1])

    def _on_categories_changed(self):
        if getattr(self, "stimulus_manager", None) is not None:
            n = len(self.stimulus_manager.get_active_categories())
            self._add_log(f"Ingerkategóriák frissítve ({n} aktív).")

    # ============================================================
    # KAMERA
    # ============================================================
    def _start(self):
        if self.tracker.isRunning():
            return
        idx = 0
        try:
            idx = int(self.live_cam_combo.currentText().split()[-1])
        except Exception:
            pass
        self.tracker.set_video_path(None)
        self.tracker.set_camera(idx)
        self.tracker.start()
        self._current_source = f"Kamera {idx}"
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.live_cam_start_btn.setEnabled(False)
        self.live_video_open_btn.setEnabled(False)
        self._set_status(f"Adatgyűjtés: Kamera {idx}")
        self.hdr_cam_status.setText(f"Forrás: Kamera {idx}")
        self._refresh_system_info()

    def _stop(self):
        self.tracker.stop()
        self.tracker.wait(1500)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.live_cam_start_btn.setEnabled(True)
        self.live_video_open_btn.setEnabled(True)
        self._set_status("Rögzítés felfüggesztve")
        self._add_log("Adatgyűjtés leállítva.")
        self.hdr_cam_status.setText("Forrás: –")
        self._current_source = "none"
        self._refresh_system_info()

    def _open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Mérési videó", "", "Videók (*.mp4 *.avi *.mov)"
        )
        if not path or not os.path.exists(path):
            return
        if self.tracker.isRunning():
            self.tracker.stop()
            self.tracker.wait(1000)
        self.tracker.set_video_path(path)
        self._current_source = "Videófájl"
        self.tracker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.live_cam_start_btn.setEnabled(False)
        self.live_video_open_btn.setEnabled(False)
        self._add_log(f"Fájl betöltve: {os.path.basename(path)}")
        self._refresh_system_info()

    def _on_frame(self, frame: np.ndarray, result: dict):
        self._frames_received += 1
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, c = rgb.shape
        qi = QImage(rgb.data, w, h, c * w, QImage.Format_RGB888).copy()
        pm = QPixmap.fromImage(qi).scaled(
            self.camera_view.width(), self.camera_view.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.camera_view.setPixmap(pm)

        conf = float(result.get("confidence", 0.0))
        size = float(result.get("pupil_size", 1.0))
        pitch = float(result.get("neural_el", 0.0))
        yaw = float(result.get("neural_az", 0.0))
        cx = float(result.get("cx", 0.0))
        cy = float(result.get("cy", 0.0))
        radius = float(result.get("radius_px", 0.0))

        if hasattr(self, "gl_widget"):
            try:
                self.gl_widget.set_eye_pose(pitch, yaw, size, conf)
            except Exception:
                pass
        if hasattr(self, "pupil_graph"):
            self.pupil_graph.add_point("size", size)
            self.pupil_graph.add_point("conf", conf)
            if radius > 0:
                self.pupil_graph.add_point("radius", min(radius, 80.0))

        self._set_metric(self.metric_conf, f"{conf:.2f}")
        self._set_metric(self.metric_size, f"{size:.2f}")
        self._set_metric(self.metric_az, f"{yaw:+.1f}°")
        self._set_metric(self.metric_el, f"{pitch:+.1f}°")
        self._set_metric(self.metric_pos_x, f"{cx:.0f} px")
        self._set_metric(self.metric_pos_y, f"{cy:.0f} px")
        self._set_metric(self.metric_radius, f"{radius:.1f} px")

        if conf > 0.4:
            self.hdr_det_status.setText(f"Detektor: Stabil ({conf:.2f})")
            self.hdr_det_status.setStyleSheet(
                f"color: {PALETTE['accent_success']}; font-size: {FONT_SIZE_SM}px; "
                f"background-color: {PALETTE['bg_panel']}; "
                f"border: 1px solid {PALETTE['border']}; "
                f"border-radius: 3px; padding: 3px 10px;"
            )
        else:
            self.hdr_det_status.setText("Detektor: Zajos")
            self.hdr_det_status.setStyleSheet(
                f"color: {PALETTE['accent_warning']}; font-size: {FONT_SIZE_SM}px; "
                f"background-color: {PALETTE['bg_panel']}; "
                f"border: 1px solid {PALETTE['border']}; "
                f"border-radius: 3px; padding: 3px 10px;"
            )

    def _on_fps(self, fps: float):
        self.fps_badge.setText(f"{fps:.0f} FPS")
        self._set_metric(self.metric_fps, f"{fps:.0f} Hz")

    def _set_status(self, msg: str):
        self._status_left.setText(msg)

    def _update_clock(self):
        if self.tracker.isRunning():
            mins = self._frames_received // (30 * 60)
            secs = (self._frames_received // 30) % 60
            self._status_right.setText(f"Képkockák: {self._frames_received}  •  {mins:02d}:{secs:02d}")

    def _add_log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self._log_lines.append(f"[{ts}] {msg}")
        if len(self._log_lines) > 80:
            self._log_lines.pop(0)
        if hasattr(self, "log_view"):
            self.log_view.setPlainText("\n".join(self._log_lines))
            sb = self.log_view.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _run_loader(self):
        self.loader = LoaderThread(self)
        self.loader.finished.connect(self._refresh_after_load)
        self.loader.start()

    def _refresh_after_load(self):
        self.showMaximized()
        self._scan_reports_bg()
        self._refresh_system_info()

    def _scan_cameras_bg(self):
        self._camera_found = []
        for i in range(4):
            for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF):
                try:
                    cap = cv2.VideoCapture(i, backend)
                    if cap.isOpened():
                        ret, _ = cap.read()
                        cap.release()
                        if ret:
                            self._camera_found.append(f"Kamera {i}")
                            break
                except Exception:
                    pass

    def _scan_stimuli_bg(self):
        from core.stimulus_task import StimulusTask
        self._stim_task = StimulusTask(image_dir=str(STIMULI_DIR))

    def _scan_reports_bg(self):
        self._reports_list = []
        reports_dir = str(REPORTS_DIR)
        if not os.path.isdir(reports_dir):
            return
        for fname in os.listdir(reports_dir):
            if fname.startswith("report_") and fname.endswith(".txt"):
                path = os.path.join(reports_dir, fname)
                mtime = os.path.getmtime(path)
                self._reports_list.append((mtime, path, fname))
        self._reports_list.sort(reverse=True)

        if hasattr(self, "history_list"):
            self.history_list.clear()
            for mtime, path, fname in self._reports_list[:20]:
                dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                item = QListWidgetItem(f"{fname}\n{dt}")
                item.setData(Qt.UserRole, path)
                self.history_list.addItem(item)

    def _connect_signals(self):
        self.start_btn.clicked.connect(self._start)
        self.stop_btn.clicked.connect(self._stop)

    def _on_flip_changed_sett(self):
        try:
            self.tracker.flip_h = self.flip_h_cb.isChecked()
            self.tracker.flip_v = self.flip_v_cb.isChecked()
        except Exception as e:
            print(f"[FLIP] Hiba: {e}")

    def _on_style_changed(self, index: int):
        style = self.style_combo.currentData()
        if style is not None:
            self._pupil_style = style
            try:
                self.tracker.set_pupil_style(style)
            except Exception:
                pass

    def _refresh_system_info(self):
        import sys, platform
        if hasattr(self, "_sys_version"):
            self._sys_version.setText(APP_VERSION)
            self._sys_python.setText(sys.version.split()[0])
            self._sys_opencv.setText(cv2.__version__)
            self._sys_qt.setText("PyQt5")
            self._sys_os.setText(f"{platform.system()} {platform.release()}")
            self._sys_camera.setText(self._current_source)
            self._sys_frames.setText(str(self._frames_received))

    def _on_logout(self):
        if QMessageBox.question(
            self, "Kilépés", "Biztosan befejezi a munkamenetet?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self.close()

    def closeEvent(self, event):
        try:
            self.tracker.stop()
            self.tracker.wait(1500)
        except Exception:
            pass
        if self.stim_win:
            try:
                self.stim_win.close()
            except Exception:
                pass
        event.accept()