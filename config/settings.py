# config/settings.py
# NeuroEye Tracker – Clinical Edition v14.0
# Tobii Pro Lab Analyze stílus

# ==========================================================
# PALETTE – Tobii Pro Lab Analyze (sötét, professzionális)
# ==========================================================
PALETTE = {
    # ---- HÁTTÉR ----
    "bg_primary":       "#1e1e22",   # Fő háttér (sötét grafit)
    "bg_secondary":     "#24242a",   # Panelek
    "bg_card":          "#2a2a30",   # Kártyák
    "bg_elevated":      "#33333b",   # Hover
    "bg_input":         "#1a1a1e",   # Beviteli mezők
    "bg_panel":         "#26262c",   # Oldalsó panelek
    "bg_toolbar":       "#2a2a30",   # Toolbar
    "bg_darkest":       "#151517",   # Legmélyebb

    # ---- SZEGÉLYEK ----
    "border":           "#33333b",
    "border_light":     "#42424a",
    "border_strong":    "#52525c",
    "border_glow":      "#0e8cf0",

    # ---- AKCENT (Tobii kék) ----
    "accent_primary":   "#0e8cf0",
    "accent_secondary": "#3ba0f5",
    "accent_hover":     "#2a9bf5",
    "accent_success":   "#4ec976",
    "accent_warning":   "#f0a838",
    "accent_danger":    "#ef4a5a",
    "accent_cyan":      "#20c4d8",
    "accent_purple":    "#a06cf0",
    "accent_pink":      "#ef4a8c",

    # ---- SZÖVEG ----
    "text_primary":     "#e8e8ee",
    "text_secondary":   "#a8a8b4",
    "text_muted":       "#6a6a78",
    "text_inverse":     "#ffffff",
    "text_sidebar":     "#c8ccd1",
    "text_sidebar_active":"#ffffff",

    # ---- METRIKÁK ----
    "metric_bg":        "#24242a",
    "metric_value":     "#e8e8ee",
    "metric_label":     "#6a6a78",

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
PALETTE["bg_panel"]     = PALETTE["bg_secondary"]
PALETTE["bg_panel_alt"] = PALETTE["bg_card"]
PALETTE["bg_surface"]   = PALETTE["bg_secondary"]
PALETTE["accent_blue"]  = PALETTE["accent_primary"]
PALETTE["accent_green"] = PALETTE["accent_success"]
PALETTE["accent_yellow"]= PALETTE["accent_warning"]
PALETTE["accent_red"]   = PALETTE["accent_danger"]


# ==========================================================
# TIPOGRAFIA
# ==========================================================
FONT_FAMILY = "'Segoe UI', -apple-system, 'Helvetica Neue', Arial, sans-serif"
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
    """