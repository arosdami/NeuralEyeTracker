"""Project and patient persistence for the application workspace."""

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from config.paths import DATA_DIR


RECENT_PROJECTS_FILE = DATA_DIR / "recent_projects.json"
PATIENT_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,31}$")
TAJ_PATTERN = re.compile(r"^\d{9}$")


def new_patient_id() -> str:
    return f"P-{uuid.uuid4().hex[:8].upper()}"


def validate_patient(patient: Dict[str, str]) -> Tuple[bool, str]:
    if not patient.get("name", "").strip():
        return False, "A páciens neve kötelező."
    if not TAJ_PATTERN.fullmatch(patient.get("taj", "").strip()):
        return False, "A TAJ-szám pontosan 9 számjegy legyen."
    if not patient.get("diagnosis", "").strip():
        return False, "A diagnózis vagy vizsgálati cél kötelező."

    patient_id = patient.get("patient_id", "").strip()
    if patient_id and not PATIENT_ID_PATTERN.fullmatch(patient_id):
        return False, "A páciensazonosító csak betűt, számot, kötőjelet és aláhúzást tartalmazhat."
    return True, ""


def create_project(name: str, patient: Dict[str, str]) -> Dict:
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "format": "neural-eye-project",
        "version": 1,
        "name": name.strip() or "Új projekt",
        "created_at": now,
        "updated_at": now,
        "patient": patient,
        "sessions": [],
    }


def save_project(path: str, project: Dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    project["updated_at"] = datetime.now().isoformat(timespec="seconds")
    target.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    _remember_project(str(target))


def load_project(path: str) -> Dict:
    project = json.loads(Path(path).read_text(encoding="utf-8"))
    if project.get("format") != "neural-eye-project":
        raise ValueError("A fájl nem Neural Eye Tracker projekt.")
    valid, message = validate_patient(project.get("patient", {}))
    if not valid:
        raise ValueError(message)
    _remember_project(str(Path(path)))
    return project


def recent_projects() -> list[str]:
    if not RECENT_PROJECTS_FILE.exists():
        return []
    try:
        paths = json.loads(RECENT_PROJECTS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [path for path in paths if Path(path).is_file()]


def _remember_project(path: str) -> None:
    paths = [path] + [item for item in recent_projects() if item != path]
    RECENT_PROJECTS_FILE.write_text(
        json.dumps(paths[:10], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
