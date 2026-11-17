# config/settings.py
# NeuroEye Tracker – Clinical Edition v14.0
# Tobii Pro Lab Analyze stílus

# ==========================================================
# PALETTE – Windows 11 Fluent clinical workstation
# ==========================================================
PALETTE = {
    # ---- HÁTTÉR ----
    "bg_primary":       "#f6f8fb",   # Fő háttér
    "bg_secondary":     "#ffffff",   # Panelek
    "bg_card":          "#ffffff",   # Kártyák
    "bg_elevated":      "#f0f3f8",   # Hover
    "bg_input":         "#ffffff",   # Beviteli mezők
    "bg_panel":         "#fafbfd",   # Oldalsó panelek
    "bg_toolbar":       "#ffffff",   # Toolbar
    "bg_darkest":       "#f3f3f3",   # Menüsáv

    # ---- SZEGÉLYEK ----
    "border":           "#e4e9f0",
    "border_light":     "#cfd7e3",
    "border_strong":    "#b7c3d2",
    "border_glow":      "#0b6bcb",

    # ---- AKCENT (Tobii kék) ----
    "accent_primary":   "#0b6bcb",
    "accent_secondary": "#3a95f0",
    "accent_hover":     "#0958a8",
    "accent_success":   "#0f8a3c",
    "accent_warning":   "#b45309",
    "accent_danger":    "#c42b1c",
    "accent_cyan":      "#0078d4",
    "accent_purple":    "#6b4bb1",
    "accent_pink":      "#b4009e",

    # ---- SZÖVEG ----
    "text_primary":     "#0f172a",
    "text_secondary":   "#334155",
    "text_muted":       "#64748b",
    "text_inverse":     "#ffffff",
    "text_sidebar":     "#334155",
    "text_sidebar_active":"#0f172a",

    # ---- METRIKÁK ----
    "metric_bg":        "#fafbfd",
    "metric_value":     "#0f172a",
    "metric_label":     "#94a3b8",

    # ---- KATEGÓRIA SZÍNEK (Tobii Targets) ----
    "cat_dog":          "#f0a838",   # narancs
    "cat_cat":          "#ef4a8c",   # rózsa
    "cat_bird":         "#4ec976",   # zöld
    "cat_horse":        "#20c4d8",   # cián
    "cat_geometry":     "#0e8cf0",   # kék
    "cat_car":          "#f0d838",   # sárga
}

# Visszafelé kompatibilis aliasok
PALETTE["bg_deep"]      = PALETTE["bg_primary"]
PALETTE["bg_panel"]     = "#fafbfd"
PALETTE["bg_panel_alt"] = PALETTE["bg_card"]
PALETTE["bg_surface"]   = PALETTE["bg_secondary"]
PALETTE["accent_blue"]  = PALETTE["accent_primary"]
PALETTE["accent_green"] = PALETTE["accent_success"]
PALETTE["accent_yellow"]= PALETTE["accent_warning"]
PALETTE["accent_red"]   = PALETTE["accent_danger"]


# ==========================================================
# TIPOGRAFIA
# ==========================================================
FONT_FAMILY = "'Inter', 'Segoe UI Variable', 'Segoe UI', -apple-system, Arial, sans-serif"
FONT_MONO   = "'Consolas', 'Monaco', 'Courier New', monospace"

FONT_SIZE_XS = 10
FONT_SIZE_SM = 11
FONT_SIZE_MD = 12
FONT_SIZE_LG = 13
FONT_SIZE_XL = 15
FONT_SIZE_XXL = 20


# ==========================================================
# KAMERA
# ==========================================================
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
TARGET_FPS = 30
ROI_SIZE = 280
DETECT_SIZE = 240
CAMERA_AUTO_EXPOSURE = False
CAMERA_EXPOSURE_VALUE = -6
CAMERA_GAIN = 0


# ==========================================================
# DETEKTOR
# ==========================================================
MIN_PUPIL_AREA = 80
MAX_PUPIL_AREA = 2500
MIN_CIRCULARITY = 0.65
MIN_ASPECT_RATIO = 0.55
MAX_MEAN_INTENSITY = 60
MAX_POSITION_JUMP = 120
DETECTOR_MIN_RADIUS = 3.0
DETECTOR_MIN_CONTRAST = 12.0
DETECTOR_MIN_SCORE = 0.30
DETECTOR_EYE_REGION_TOP = 0.08
DETECTOR_EYE_REGION_BOTTOM = 0.75
DETECTOR_CLAHE_CLIP_LIMIT = 2.5
DETECTOR_CLAHE_GRID_SIZE = (8, 8)
DETECTOR_BILATERAL_DIAMETER = 5
DETECTOR_BILATERAL_SIGMA_COLOR = 50
DETECTOR_BILATERAL_SIGMA_SPACE = 50
DETECTOR_GAUSSIAN_KERNEL = (5, 5)
DETECTOR_GAUSSIAN_SIGMA = 1.2
DETECTOR_ADAPTIVE_BLOCK_SIZE = 15
DETECTOR_ADAPTIVE_C = 3
DETECTOR_FIXED_THRESHOLD = 45
DETECTOR_FALLBACK_THRESHOLD = 60
DETECTOR_MORPH_OPEN_KERNEL = (3, 3)
DETECTOR_MORPH_CLOSE_KERNEL = (5, 5)
DETECTOR_MORPH_OPEN_ITERATIONS = 1
DETECTOR_MORPH_CLOSE_ITERATIONS = 2
DETECTOR_DETECTION_WEIGHTS = (0.30, 0.15, 0.10, 0.25, 0.15, 0.05)
DETECTOR_SIZE_REFERENCE = 500
DETECTOR_SIZE_TOLERANCE = 800
DETECTOR_POSITION_SCALE = 200
DETECTOR_CONTRAST_SCALE = 50


# ==========================================================
# SZEM RÉGIÓ
# ==========================================================
EYE_WIDTH_FACTOR = 3.8
EYE_HEIGHT_FACTOR = 2.3
EYE_MIN_WIDTH = 80
EYE_MIN_HEIGHT = 40
EYE_VERTICAL_OFFSET = -0.05


# ==========================================================
# KALMAN
# ==========================================================
KALMAN_PROCESS_NOISE = 0.02
KALMAN_MEASUREMENT_NOISE = 4.0


# ==========================================================
# NEURÁLIS MODELL
# ==========================================================
FEATURE_COUNT = 13
AZIMUTH_RANGE = (-45.0, 45.0)
ELEVATION_RANGE = (-35.0, 35.0)
MIN_TRAINING_SAMPLES = 30
MODEL_HIDDEN_LAYERS = (256, 128, 64, 32)
MODEL_LEARNING_RATE = 0.0008
MODEL_MAX_ITERATIONS = 1500
MODEL_VALIDATION_FRACTION = 0.15
MODEL_EARLY_STOPPING_ROUNDS = 30
MODEL_L2_REGULARIZATION = 1e-4
MODEL_TOLERANCE = 1e-7
BASELINE_SAMPLE_COUNT = 10
RELATIVE_POSITION_GAIN = 10.0
PREDICTION_HISTORY_LENGTH = 3
OUTLIER_MIN_SAMPLES = 10
OUTLIER_QUANTILES = (5, 95)
OUTLIER_IQR_FACTOR = 1.5
OUTLIER_MIN_RETAIN_RATIO = 0.7


# ==========================================================
# KALIBRÁCIÓ
# ==========================================================
CALIB_GRID_COLS = 8
CALIB_GRID_ROWS = 6
CALIB_MARGIN = 0.05
CALIB_PRESENTATION_MS = 1800
CALIB_SAMPLES_PER_POINT = 15
CALIB_SAMPLE_INTERVAL_MS = 33


# ==========================================================
# MENTÉS
# ==========================================================
MODEL_DIR = "models"
MODEL_FILENAME = "gaze_model.pkl"
SCALER_FILENAME = "gaze_scaler.pkl"


# ==========================================================
# PUPILLA MEGJELENÍTÉS
# ==========================================================
DEFAULT_PUPIL_STYLE = 1
PUPIL_STYLES = {
    1: "Clinical Crosshair",
    2: "Minimal Ring",
    3: "Data Point",
}
PUPIL_COLORS = {
    "high_conf":  (204, 122, 0),
    "mid_conf":   (0, 193, 255),
    "low_conf":   (85, 53, 220),
    "accent":     (204, 122, 0),
    "center":     (255, 255, 255),
    "cross":      (200, 200, 200),
    "video":      (204, 122, 0),
}
CROSSHAIR_LENGTH = 15
CROSSHAIR_THICKNESS = 1
RING_THICKNESS = 2
RING_RADIUS_OFFSET = 5
MESH_NUM_RINGS = 0
MESH_NUM_SPOKES = 0
MESH_LINE_THICKNESS = 0
MESH_OUTLINE_THICKNESS = 0
MESH_SHOW_NODES = False


# ==========================================================
# QSS – Tobii Pro Lab Analyze stílus
# ==========================================================
def build_stylesheet() -> str:
    p = PALETTE
    return f"""
    /* ===== ALAP ===== */
    QMainWindow, QWidget {{
        background-color: {p['bg_primary']};
        color: {p['text_primary']};
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_MD}px;
    }}
    QLabel {{ background: transparent; color: {p['text_primary']}; }}

    /* ===== TOP MENUBAR ===== */
    QWidget#appMenuBar {{
        background-color: {p['bg_darkest']};
        border-bottom: 1px solid {p['border']};
    }}
    QLabel#appLogo {{
        background-color: #001d36;
        color: #31a8ff;
        border: 1px solid #31a8ff;
        border-radius: 2px;
        padding: 2px 4px;
        font-size: {FONT_SIZE_XS}px;
        font-weight: 700;
    }}
    QToolButton#appMenuItem {{
        background: transparent;
        color: {p['text_secondary']};
        border: none;
        padding: 4px 7px;
        font-size: {FONT_SIZE_SM}px;
    }}
    QToolButton#appMenuItem:hover {{
        background-color: {p['bg_elevated']};
        color: {p['text_primary']};
    }}
    QToolButton#appMenuItem::menu-indicator {{
        image: none;
        width: 0;
    }}
    QMenu {{
        background-color: #2d2d2d;
        color: #dddddd;
        border: 1px solid #111111;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 26px 6px 12px;
        border-radius: 2px;
    }}
    QMenu::item:selected {{
        background-color: #0e4b85;
        color: #ffffff;
    }}
    QMenu::separator {{
        height: 1px;
        background-color: #4a4a4a;
        margin: 4px 8px;
    }}
    QFrame#menuSeparator {{
        color: {p['border_light']};
        margin: 7px 5px;
    }}
    QWidget#topTabs {{
        background-color: #26272b;
        border-bottom: 1px solid #141517;
    }}
    QToolButton#topTab {{
        background-color: transparent;
        color: #8f949d;
        border: none;
        border-bottom: 2px solid transparent;
        padding: 5px 18px 4px;
        text-align: left;
        font-size: {FONT_SIZE_SM}px;
        font-weight: 600;
    }}
    QToolButton#topTab:hover {{
        background-color: #303238;
        color: #e9ebef;
    }}
    QToolButton#topTab:checked {{
        color: #f5f7fa;
        border-bottom-color: #42a5f5;
        background-color: #303238;
    }}
    QLabel#workspaceContext {{
        color: #8f949d;
        background-color: #202125;
        border: 1px solid #3b3e45;
        border-radius: 5px;
        padding: 7px 12px;
        font-size: {FONT_SIZE_XS}px;
    }}
    QLabel#dialogTitle {{
        color: #f5f7fa;
        font-size: 18px;
        font-weight: 700;
        padding: 5px 0;
    }}
    QLabel#dialogSubtitle {{
        color: #9aa0aa;
        padding-bottom: 8px;
    }}
    QWidget#optionsBar {{
        background-color: #383838;
        border-bottom: 1px solid #222222;
    }}
    QWidget#optionsBar QLabel {{
        color: #cccccc;
        font-size: {FONT_SIZE_XS}px;
    }}
    QLabel#toolbarLabel {{
        color: {p['text_primary']};
        font-weight: 600;
        padding: 0 6px;
    }}
    QLabel#toolbarHint {{
        color: #888888;
        padding-right: 4px;
    }}
    QFrame#toolToolbar {{
        background-color: #383838;
        border-right: 1px solid #222222;
    }}
    QFrame#navigationSidebar {{
        background-color: #202125;
        border-right: 1px solid #141517;
    }}
    QToolButton#navigationButton {{
        background-color: transparent;
        color: #8f949d;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 5px 2px;
        font-size: 10px;
        font-weight: 600;
    }}
    QToolButton#navigationButton:hover {{
        background-color: #303238;
        color: #f5f7fa;
    }}
    QToolButton#navigationButton:checked {{
        background-color: #183c5a;
        color: #ffffff;
        border-color: #2f83bb;
    }}
    QLabel#toolbarSection {{
        color: #777777;
        font-size: {FONT_SIZE_XS}px;
        font-weight: 700;
        padding: 8px 4px 2px;
    }}
    QFrame#toolbarSeparator {{
        color: #555555;
        margin: 5px 4px;
    }}
    QToolButton#toolbarButton, QToolButton#toolButton {{
        background-color: transparent;
        color: #a0a0a0;
        border: 1px solid transparent;
        border-radius: 3px;
        font-size: 15px;
    }}
    QToolButton#toolbarButton:hover, QToolButton#toolButton:hover {{
        background-color: #4a4a4a;
        color: #eeeeee;
        border-color: #555555;
    }}
    QToolButton#toolButton:checked {{
        background-color: #191919;
        color: #ffffff;
    }}
    QToolButton#toolButton:checked {{
        border-left: 2px solid #31a8ff;
    }}
    QFrame#colorSwatches {{
        background-color: #111111;
        border: 2px solid #cccccc;
        border-radius: 2px;
    }}
    QFrame#rightDock {{
        background-color: #383838;
        border-left: 1px solid #222222;
    }}
    QToolButton#dockTab {{
        background-color: #2d2d2d;
        color: #888888;
        border: none;
        border-top: 2px solid transparent;
        padding: 7px 8px;
        font-size: {FONT_SIZE_XS}px;
    }}
    QToolButton#dockTab:first-child {{
        color: #ffffff;
        border-top-color: #31a8ff;
    }}
    QGroupBox#dockGroup {{
        background-color: #383838;
        border: none;
        border-bottom: 1px solid #222222;
        border-radius: 0;
        margin-top: 10px;
        padding-top: 12px;
        color: #cccccc;
        font-size: {FONT_SIZE_XS}px;
    }}
    QGroupBox#dockGroup::title {{
        background-color: #383838;
        color: #ffffff;
        left: 8px;
        top: 0;
        padding: 0 3px;
    }}
    QLabel#dockValue {{
        color: #eeeeee;
        font-family: {FONT_MONO};
        font-size: {FONT_SIZE_XS}px;
    }}
    QToolButton#dockItem {{
        background: transparent;
        color: #cccccc;
        border: none;
        text-align: left;
        padding: 6px 5px;
        font-size: {FONT_SIZE_XS}px;
    }}
    QToolButton#dockItem:hover {{
        background-color: #4a4a4a;
        color: #ffffff;
    }}
    QToolButton#appMenuBtn {{
        background: transparent;
        color: {p['text_secondary']};
        border: none;
        padding: 6px 14px;
        font-size: {FONT_SIZE_MD}px;
        font-weight: 500;
    }}
    QToolButton#appMenuBtn:hover {{
        background-color: {p['bg_elevated']};
        color: {p['text_primary']};
    }}
    QToolButton#appMenuBtn:checked {{
        color: {p['accent_primary']};
        border-bottom: 2px solid {p['accent_primary']};
    }}
    QToolButton#windowActionBtn {{
        background-color: {p['bg_panel']};
        color: {p['text_secondary']};
        border: 1px solid {p['border']};
        border-radius: 4px;
        padding: 5px 10px;
        font-size: {FONT_SIZE_SM}px;
    }}
    QToolButton#windowActionBtn:hover {{
        background-color: {p['bg_elevated']};
        color: {p['text_primary']};
        border-color: {p['accent_primary']};
    }}
    QLabel#appTitle {{
        color: {p['text_primary']};
        font-size: {FONT_SIZE_LG}px;
        font-weight: 600;
        padding: 6px 14px;
    }}

    /* ===== PANELEK ===== */
    QFrame#sidePanel {{
        background-color: {p['bg_panel']};
        border-right: 1px solid {p['border']};
    }}
    QFrame#rightPanel {{
        background-color: {p['bg_panel']};
        border-left: 1px solid {p['border']};
    }}
    QFrame#centerPanel {{
        background-color: {p['bg_primary']};
    }}

    /* ===== SZAKASZ-CÍM ===== */
    QLabel#sectionTitle {{
        color: {p['text_primary']};
        font-size: {FONT_SIZE_LG}px;
        font-weight: 600;
        padding: 4px 0;
    }}
    QLabel#sectionSubtitle {{
        color: {p['text_muted']};
        font-size: {FONT_SIZE_SM}px;
        padding-bottom: 4px;
    }}

    /* ===== KÁRTYA ===== */
    QFrame#card {{
        background-color: {p['bg_card']};
        border: 1px solid {p['border']};
        border-radius: 4px;
    }}

    /* ===== PANEL SZAKASZ (kis fejléc) ===== */
    QFrame#panelSection {{
        background-color: {p['bg_panel']};
        border-bottom: 1px solid {p['border']};
    }}
    QLabel#panelSectionTitle {{
        color: {p['text_primary']};
        font-size: {FONT_SIZE_MD}px;
        font-weight: 600;
    }}
    QLabel#panelSectionIcon {{
        color: {p['text_secondary']};
        font-size: {FONT_SIZE_LG}px;
    }}

    /* ===== GROUPBOX ===== */
    QGroupBox {{
        background-color: {p['bg_secondary']};
        border: 1px solid {p['border']};
        border-radius: 4px;
        margin-top: 16px;
        padding-top: 12px;
        font-size: {FONT_SIZE_MD}px;
        font-weight: 600;
        color: {p['text_primary']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        top: 2px;
        padding: 0 6px;
        background-color: {p['bg_secondary']};
        color: {p['text_primary']};
    }}

    /* ===== GOMBOK ===== */
    QPushButton {{
        background-color: {p['bg_elevated']};
        color: {p['text_primary']};
        border: 1px solid {p['border_light']};
        border-radius: 4px;
        padding: 6px 14px;
        font-size: {FONT_SIZE_MD}px;
        font-weight: 500;
        min-height: 22px;
    }}
    QPushButton:hover {{
        background-color: {p['border_light']};
        border-color: {p['accent_primary']};
    }}
    QPushButton:pressed {{ background-color: {p['border']}; }}
    QPushButton:disabled {{
        color: {p['text_muted']};
        background-color: {p['bg_secondary']};
        border-color: {p['border']};
    }}
    QPushButton[class="primary"] {{
        background-color: {p['accent_primary']};
        color: white;
        border: 1px solid {p['accent_primary']};
        font-weight: 600;
    }}
    QPushButton[class="primary"]:hover {{
        background-color: {p['accent_hover']};
        border-color: {p['accent_hover']};
    }}
    QPushButton[class="ghost"] {{
        background-color: transparent;
        border: 1px solid transparent;
        color: {p['text_secondary']};
        padding: 4px 8px;
    }}
    QPushButton[class="ghost"]:hover {{
        background-color: {p['bg_elevated']};
        color: {p['text_primary']};
    }}
    QPushButton[class="danger"] {{
        color: {p['accent_danger']};
        border-color: {p['border_light']};
    }}
    QPushButton[class="danger"]:hover {{
        background-color: {p['accent_danger']};
        color: white;
        border-color: {p['accent_danger']};
    }}

    /* ===== INPUT ===== */
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {p['bg_input']};
        color: {p['text_primary']};
        border: 1px solid {p['border_light']};
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 22px;
        selection-background-color: {p['accent_primary']};
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {p['accent_primary']};
    }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {p['text_secondary']};
        margin-right: 6px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p['bg_card']};
        color: {p['text_primary']};
        border: 1px solid {p['border_light']};
        selection-background-color: {p['accent_primary']};
    }}

    /* ===== CHECKBOX / RADIO ===== */
    QCheckBox {{ spacing: 8px; color: {p['text_primary']}; }}
    QCheckBox::indicator {{
        width: 14px; height: 14px;
        border: 1px solid {p['border_strong']};
        border-radius: 3px;
        background-color: {p['bg_input']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {p['accent_primary']};
        border-color: {p['accent_primary']};
    }}
    QRadioButton {{ spacing: 6px; color: {p['text_primary']}; }}
    QRadioButton::indicator {{
        width: 12px; height: 12px;
        border: 1px solid {p['border_strong']};
        border-radius: 7px;
        background-color: {p['bg_input']};
    }}
    QRadioButton::indicator:checked {{
        background-color: {p['accent_primary']};
        border: 3px solid {p['bg_input']};
    }}

    /* ===== SLIDER ===== */
    QSlider::groove:horizontal {{
        height: 3px;
        background: {p['border']};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {p['accent_primary']};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: #ffffff;
        border: 1px solid {p['border_strong']};
        width: 12px; height: 12px;
        margin: -5px 0;
        border-radius: 6px;
    }}
    QSlider::handle:horizontal:hover {{ background: {p['accent_primary']}; }}

    /* ===== PROGRESS ===== */
    QProgressBar {{
        background-color: {p['bg_input']};
        border: 1px solid {p['border']};
        border-radius: 3px;
        height: 10px;
        text-align: center;
        color: {p['text_primary']};
        font-size: {FONT_SIZE_XS}px;
    }}
    QProgressBar::chunk {{ background-color: {p['accent_primary']}; }}

    /* ===== LISTÁK / TÁBLÁZAT ===== */
    QListWidget, QTableWidget, QTreeWidget {{
        background-color: {p['bg_secondary']};
        color: {p['text_primary']};
        border: 1px solid {p['border']};
        border-radius: 3px;
        outline: none;
    }}
    QListWidget::item {{ padding: 5px 10px; border-bottom: 1px solid {p['border']}; }}
    QListWidget::item:hover {{ background-color: {p['bg_elevated']}; }}
    QListWidget::item:selected {{
        background-color: {p['bg_elevated']};
        color: {p['accent_primary']};
        border-left: 2px solid {p['accent_primary']};
    }}
    QHeaderView::section {{
        background-color: {p['bg_primary']};
        color: {p['text_secondary']};
        padding: 5px 8px;
        border: none;
        border-bottom: 1px solid {p['border']};
        font-weight: 600;
        font-size: {FONT_SIZE_SM}px;
    }}

    /* ===== TEXTEDIT ===== */
    QTextEdit, QPlainTextEdit {{
        background-color: {p['bg_input']};
        color: {p['text_primary']};
        border: 1px solid {p['border']};
        border-radius: 3px;
        padding: 6px;
        font-family: {FONT_MONO};
        font-size: {FONT_SIZE_SM}px;
    }}

    /* ===== TABS ===== */
    QTabWidget::pane {{ border: none; background-color: {p['bg_primary']}; }}
    QTabBar {{ background-color: {p['bg_darkest']}; }}
    QTabBar::tab {{
        background-color: transparent;
        color: {p['text_secondary']};
        padding: 8px 18px;
        font-size: {FONT_SIZE_MD}px;
        font-weight: 500;
        border: none;
    }}
    QTabBar::tab:hover {{ color: {p['text_primary']}; }}
    QTabBar::tab:selected {{
        color: {p['accent_primary']};
        border-bottom: 2px solid {p['accent_primary']};
        font-weight: 600;
    }}

    /* ===== TOGGLE ===== */
    QToolButton[class="toggle"] {{
        background-color: {p['bg_elevated']};
        color: {p['text_secondary']};
        border: 1px solid {p['border_light']};
        border-radius: 4px;
        padding: 5px 12px;
        font-size: {FONT_SIZE_MD}px;
        font-weight: 500;
    }}
    QToolButton[class="toggle"]:hover {{
        background-color: {p['border_light']};
        color: {p['text_primary']};
    }}
    QToolButton[class="toggle"]:checked {{
        background-color: {p['accent_primary']};
        color: white;
        border-color: {p['accent_primary']};
        font-weight: 600;
    }}
    QToolButton[class="iconBtn"] {{
        background: transparent;
        color: {p['text_secondary']};
        border: 1px solid transparent;
        border-radius: 3px;
        padding: 3px;
        min-width: 22px;
        min-height: 22px;
    }}
    QToolButton[class="iconBtn"]:hover {{
        background-color: {p['bg_elevated']};
        color: {p['text_primary']};
    }}

    /* ===== SCROLLBAR ===== */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {p['border_strong']};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {p['text_muted']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; }}
    QScrollBar::handle:horizontal {{
        background: {p['border_strong']};
        border-radius: 5px;
        min-width: 24px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    /* ===== STATUS ===== */
    QStatusBar {{
        background-color: {p['bg_darkest']};
        color: {p['text_secondary']};
        border-top: 1px solid {p['border']};
        font-size: {FONT_SIZE_SM}px;
    }}
    QStatusBar::item {{ border: none; }}

    /* ===== SPLITTER ===== */
    QSplitter::handle {{ background-color: {p['border']}; }}
    QSplitter::handle:horizontal {{ width: 1px; }}
    QSplitter::handle:vertical {{ height: 1px; }}

    /* ===== FLUENT CLINICAL OVERRIDES ===== */
    QMainWindow, QWidget {{ font-family: "Segoe UI Variable", "Segoe UI", sans-serif; }}
    QWidget#appMenuBar, QWidget#topTabs, QWidget#optionsBar {{
        background-color: #ffffff;
        border-color: #e5e5e5;
    }}
    QToolButton#appMenuItem, QToolButton#appMenuBtn, QToolButton#topTab {{
        color: #424242;
        border-radius: 4px;
    }}
    QToolButton#appMenuItem {{
        padding: 4px 8px;
        font-size: 11px;
    }}
    QToolButton#appMenuItem:hover, QToolButton#appMenuBtn:hover,
    QToolButton#topTab:hover {{ background-color: #f3f3f3; color: #1f1f1f; }}
    QToolButton#topTab:checked {{
        background-color: #e8f1fb;
        color: #0067c0;
        border-bottom-color: #0067c0;
    }}
    QLabel#appLogo {{
        background-color: #e8f1fb;
        color: #0067c0;
        border-color: #b9d5ee;
        border-radius: 5px;
    }}
    QFrame#navigationSidebar {{
        background-color: #f9f9f9;
        border-right: 1px solid #e5e5e5;
    }}
    QToolButton#navigationButton {{
        color: #5f5f5f;
        border-radius: 5px;
    }}
    QToolButton#navigationButton:hover {{ background-color: #f0f0f0; color: #1f1f1f; }}
    QToolButton#navigationButton:checked {{
        background-color: #e8f1fb;
        color: #0067c0;
        border-color: #b9d5ee;
    }}
    QFrame#sidePanel, QFrame#rightPanel, QFrame#centerPanel {{
        background-color: #f9f9f9;
        border-color: #e5e5e5;
    }}
    QLabel#sectionTitle {{
        color: #1f1f1f;
        font-size: 14px;
        font-weight: 650;
    }}
    QLabel#sectionSubtitle {{
        color: #707070;
        font-size: 11px;
    }}
    QFrame#card, QGroupBox {{
        background-color: #ffffff;
        border-color: #e5e5e5;
        border-radius: 5px;
    }}
    QGroupBox::title {{ background-color: #ffffff; color: #1f1f1f; }}
    QPushButton {{
        background-color: #ffffff;
        color: #1f1f1f;
        border-color: #d1d1d1;
        border-radius: 4px;
    }}
    QPushButton:hover {{ background-color: #f3f3f3; border-color: #0067c0; }}
    QPushButton[class="primary"] {{
        background-color: #0067c0;
        border-color: #0067c0;
        color: #ffffff;
    }}
    QPushButton[class="primary"]:hover {{
        background-color: #005aab;
        border-color: #005aab;
    }}
    QToolButton#windowActionBtn {{
        background-color: #ffffff;
        color: #424242;
        border: 1px solid #d1d1d1;
        border-radius: 4px;
        padding: 4px 10px;
    }}
    QToolButton#windowActionBtn:hover {{
        background-color: #f3f3f3;
        border-color: #0067c0;
        color: #0067c0;
    }}
    QToolButton#toolbarButton {{
        color: #0067c0;
        border-radius: 4px;
        padding: 2px 6px;
    }}
    QToolButton#toolbarButton:hover {{
        background-color: #e8f1fb;
    }}
    QWidget#optionsBar QLabel {{
        color: #5f5f5f;
        font-size: 11px;
    }}
    QWidget#optionsBar QComboBox {{
        min-height: 22px;
        padding: 2px 8px;
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
        background-color: #ffffff;
        color: #1f1f1f;
        border-color: #d1d1d1;
    }}
    QListWidget, QTableWidget, QTreeWidget {{
        background-color: #ffffff;
        color: #1f1f1f;
        border-color: #e5e5e5;
    }}
    QListWidget::item:selected {{
        background-color: #e8f1fb;
        color: #0067c0;
        border-left-color: #0067c0;
    }}
    QHeaderView::section {{
        background-color: #f3f3f3;
        color: #5f5f5f;
        border-bottom-color: #e5e5e5;
        padding: 4px 8px;
    }}
    QTableWidget, QListWidget {{
        alternate-background-color: #fbfbfb;
    }}
    QTableWidget::item {{
        padding: 4px 6px;
        border-bottom: 1px solid #f0f0f0;
    }}
    QStatusBar {{
        background-color: #ffffff;
        color: #5f5f5f;
        border-top-color: #e5e5e5;
    }}
    QFrame#patientBanner {{
        background-color: #ffffff;
        border-bottom: 1px solid #e5e5e5;
    }}
    QLabel#patientName {{
        color: #1f1f1f;
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel#patientMeta, QLabel#patientFieldLabel {{
        color: #707070;
        font-size: 10px;
    }}
    QLabel#patientFieldValue {{
        color: #1f1f1f;
        font-size: 12px;
        font-weight: 600;
    }}
    QFrame#patientAlert, QFrame#patientWarning {{
        border-radius: 4px;
        padding: 1px;
    }}
    QFrame#patientAlert {{
        background-color: #fff1f0;
        border: 1px solid #f1b9b7;
    }}
    QFrame#patientWarning {{
        background-color: #fff8e6;
        border: 1px solid #e5c365;
    }}
    QFrame#patientAlert QLabel {{
        color: #a4262c;
        font-size: 10px;
    }}
    QFrame#patientWarning QLabel {{
        color: #7a4d00;
        font-size: 10px;
    }}
    QTextEdit {{
        font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
        font-size: 12px;
    }}
    QToolButton[class="iconBtn"] {{
        color: #0067c0;
        background-color: #f3f7fb;
        border: 1px solid #d5e5f4;
        border-radius: 4px;
        padding: 3px 4px;
    }}
    QToolButton[class="iconBtn"]:hover {{
        background-color: #e8f1fb;
        border-color: #0067c0;
    }}
    /* ===== MOCKUP-MATCHED FLUENT CHROME ===== */
    QMainWindow, QWidget {{
        background-color: #f6f8fb;
        color: #0f172a;
        font-family: "Inter", "Segoe UI Variable", "Segoe UI", sans-serif;
    }}
    QWidget#appMenuBar, QWidget#optionsBar, QWidget#topTabs {{
        background-color: #ffffff;
        border-bottom: 1px solid #e4e9f0;
    }}
    QWidget#appMenuBar {{
        min-height: 44px;
    }}
    QLabel#appLogo {{
        min-width: 28px;
        min-height: 28px;
        padding: 0;
        border: none;
        border-radius: 7px;
        color: #ffffff;
        background-color: #0b6bcb;
        font-size: 11px;
        font-weight: 800;
    }}
    QToolButton#appMenuItem {{
        color: #334155;
        border-radius: 4px;
        padding: 7px 10px;
        font-size: 12px;
        font-weight: 500;
    }}
    QToolButton#appMenuItem:hover {{
        color: #0b6bcb;
        background-color: #f0f3f8;
    }}
    QWidget#optionsBar {{
        background-color: #fafbfd;
    }}
    QWidget#optionsBar QLabel, QLabel#toolbarLabel, QLabel#toolbarHint {{
        color: #64748b;
        font-size: 11px;
    }}
    QToolButton#toolbarButton {{
        min-width: 30px;
        min-height: 30px;
        color: #334155;
        border-radius: 4px;
        font-size: 15px;
    }}
    QToolButton#toolbarButton:hover {{
        color: #0b6bcb;
        background-color: #eaf3fb;
    }}
    QWidget#optionsBar QLineEdit, QWidget#optionsBar QComboBox {{
        background-color: #ffffff;
        border: 1px solid #cfd7e3;
        border-radius: 6px;
        color: #0f172a;
        font-size: 12px;
    }}
    QWidget#optionsBar QLineEdit {{
        padding: 0 11px;
    }}
    QWidget#topTabs {{
        background-color: #ffffff;
    }}
    QToolButton#topTab {{
        min-height: 46px;
        padding: 0 16px;
        border: none;
        border-radius: 0;
        color: #64748b;
        font-size: 12px;
        font-weight: 600;
    }}
    QToolButton#topTab:hover {{
        color: #0f172a;
        background-color: #fafbfd;
    }}
    QToolButton#topTab:checked {{
        color: #0b6bcb;
        background-color: #eaf3fb;
        border-bottom: 2px solid #0b6bcb;
    }}
    QFrame#patientBanner {{
        background-color: #ffffff;
        border-bottom: 1px solid #e4e9f0;
    }}
    QLabel#patientAvatar {{
        min-width: 42px;
        min-height: 42px;
        max-width: 42px;
        max-height: 42px;
        qproperty-alignment: AlignCenter;
        border: 2px solid #ffffff;
        border-radius: 21px;
        color: #0b6bcb;
        background-color: #dbe9f8;
        font-size: 14px;
        font-weight: 700;
    }}
    QLabel#patientName {{
        color: #0f172a;
        font-size: 16px;
        font-weight: 700;
    }}
    QLabel#patientMeta, QLabel#patientFieldLabel {{
        color: #94a3b8;
        font-size: 10px;
    }}
    QLabel#patientFieldValue {{
        color: #0f172a;
        font-size: 12px;
        font-weight: 600;
    }}
    QFrame#patientAlert, QFrame#patientWarning {{
        border-radius: 6px;
    }}
    QFrame#patientAlert {{
        background-color: #fdeceb;
        border: 1px solid #f5c2be;
    }}
    QFrame#patientWarning {{
        background-color: #fff8e6;
        border: 1px solid #f0d69a;
    }}
    QFrame#patientAlert QLabel {{
        color: #c42b1c;
        font-size: 10px;
    }}
    QFrame#patientWarning QLabel {{
        color: #b45309;
        font-size: 10px;
    }}
    QFrame#sidePanel, QFrame#rightPanel {{
        background-color: #fafbfd;
        border-color: #e4e9f0;
    }}
    QFrame#centerPanel {{
        background-color: #f6f8fb;
    }}
    QFrame#card, QGroupBox {{
        background-color: #ffffff;
        border: 1px solid #e4e9f0;
        border-radius: 10px;
    }}
    QGroupBox::title {{
        background-color: #ffffff;
        color: #334155;
    }}
    QListWidget, QTableWidget, QTreeWidget, QTextEdit, QLineEdit, QComboBox {{
        background-color: #ffffff;
        color: #0f172a;
        border-color: #cfd7e3;
        border-radius: 6px;
    }}
    QPushButton {{
        background-color: #ffffff;
        color: #334155;
        border: 1px solid #cfd7e3;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: #eaf3fb;
        border-color: #0b6bcb;
        color: #0b6bcb;
    }}
    QPushButton[class="primary"] {{
        color: #ffffff;
        background-color: #0b6bcb;
        border-color: #0b6bcb;
    }}
    QPushButton[class="primary"]:hover {{
        background-color: #0958a8;
        border-color: #0958a8;
    }}
    QStatusBar {{
        min-height: 28px;
        background-color: #ffffff;
        border-top: 1px solid #e4e9f0;
        color: #64748b;
        font-size: 11px;
    }}
    """