#!/usr/bin/env python3
# main.py - Neural Eye Tracker Professional

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from config.paths import STYLESHEET_FILE, prepare_data_directories
from ui.main_window import MainWindow
from ui.project_dialog import ProjectDialog


def load_stylesheet(path: str) -> str:
    """Betölti a stíluslapot, ha létezik."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        print(f"[WARNING] Stylesheet not found: {path}")
        return ""
    except OSError as error:
        print(f"[WARNING] Failed to load stylesheet: {error}")
        return ""


def main():
    prepare_data_directories()

    # ---- High DPI támogatás ----
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Neural Eye Tracker Pro")
    app.setOrganizationName("NeuralVision")

    # ---- Stíluslap betöltése ----
    stylesheet = load_stylesheet(STYLESHEET_FILE)
    if stylesheet:
        app.setStyleSheet(stylesheet)
        print("[INFO] Stylesheet loaded successfully")

    project_dialog = ProjectDialog()
    if project_dialog.exec_() != project_dialog.Accepted:
        sys.exit(0)

    window = MainWindow(
        project_data=project_dialog.project,
        project_path=project_dialog.project_path,
    )
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()