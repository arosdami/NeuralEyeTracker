"""Application paths shared by the runtime and the packaged application."""

import os
import shutil
from pathlib import Path


APP_NAME = "NeuralEyeTracker"
PROJECT_DIR = Path(__file__).resolve().parent.parent


def _data_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


DATA_DIR = _data_dir()
REPORTS_DIR = DATA_DIR / "reports"
MODELS_DIR = DATA_DIR / "models"
USERS_FILE = DATA_DIR / "users.json"
TRACKER_SETTINGS_FILE = DATA_DIR / "tracker_settings.pkl"
STIMULI_DIR = PROJECT_DIR / "stimuli"
STYLESHEET_FILE = PROJECT_DIR / "resources" / "styles.qss"
INSTALLER_NAME = "NeuralEyeTracker-Setup.exe"


def prepare_data_directories() -> None:
    """Create writable directories and preserve data from older dev runs."""
    for directory in (DATA_DIR, REPORTS_DIR, MODELS_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    legacy_users = PROJECT_DIR / "users.json"
    if legacy_users.is_file() and not USERS_FILE.exists():
        shutil.copy2(legacy_users, USERS_FILE)

    legacy_settings = PROJECT_DIR / "tracker_settings.pkl"
    if legacy_settings.is_file() and not TRACKER_SETTINGS_FILE.exists():
        shutil.copy2(legacy_settings, TRACKER_SETTINGS_FILE)

    legacy_reports = PROJECT_DIR / "reports"
    if legacy_reports.is_dir():
        for source in legacy_reports.iterdir():
            target = REPORTS_DIR / source.name
            if source.is_file() and not target.exists():
                shutil.copy2(source, target)
