# core/report_loader.py
# JSON riportok betöltése és indexelése

import os
import json
from datetime import datetime
from typing import List, Dict, Optional

from config.paths import REPORTS_DIR


class ReportRecord:
    """Egy kísérleti riport rekordja (JSON-ból)."""

    def __init__(self, path: str, data: dict):
        self.path = path
        self.data = data
        self.subject_id: str = data.get("subject_id", "UNKNOWN")
        self.mode: str = data.get("mode", "images")
        self.session_start: Optional[float] = data.get("session_start")
        self.session_end: Optional[float] = data.get("session_end")
        self.trials: List[dict] = data.get("trials", []) or []

        # Dátum string
        if self.session_start:
            self.date_str = datetime.fromtimestamp(self.session_start).strftime("%Y-%m-%d %H:%M")
        else:
            self.date_str = "?"

    @property
    def n_trials(self) -> int:
        return len(self.trials)

    @property
    def categories(self) -> List[str]:
        return sorted(set(t.get("category", "") for t in self.trials if t.get("category")))

    def label(self) -> str:
        return f"{self.subject_id}  •  {self.date_str}  •  {self.n_trials} próba"


class ReportLoader:
    """Az összes JSON riportot betölti a reports/ mappából."""

    def __init__(self, reports_dir: str = str(REPORTS_DIR)):
        self.reports_dir = str(reports_dir)
        self.reports: List[ReportRecord] = []

    def scan(self) -> List[ReportRecord]:
        self.reports = []
        if not os.path.isdir(self.reports_dir):
            return []

        for fname in os.listdir(self.reports_dir):
            if not (fname.startswith("report_") and fname.endswith(".json")):
                continue
            path = os.path.join(self.reports_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.reports.append(ReportRecord(path, data))
            except Exception as e:
                print(f"[LOADER] Hiba: {path} – {e}")

        # Legfrissebb elöl
        self.reports.sort(
            key=lambda r: r.session_start or 0,
            reverse=True
        )
        return self.reports