# utils/data_logger.py

import csv
import os
import time
from typing import Optional


class DataLogger:
    """Időbélyeges pupillometriai adatrögzítő CSV-be."""

    HEADERS = [
        "timestamp",
        "frame_w", "frame_h",
        "cx", "cy",
        "pupil_area",
        "ellipse_major", "ellipse_minor", "ellipse_angle",
        "inner_darkness", "iris_contrast",
        "confidence",
        "neural_az", "neural_el",
        "gaze_screen_x", "gaze_screen_y",
        "stimulus_x", "stimulus_y",
    ]

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.file = None
        self.writer = None
        self.active = False

    def start(self, path: str) -> bool:
        try:
            self.stop()
            dirname = os.path.dirname(path) or "."
            os.makedirs(dirname, exist_ok=True)
            self.file = open(path, "w", newline="", encoding="utf-8")
            self.writer = csv.DictWriter(self.file, fieldnames=self.HEADERS)
            self.writer.writeheader()
            self.active = True
            self.path = path
            return True
        except Exception as e:
            print(f"[LOGGER] Hiba indításkor: {e}")
            self.active = False
            return False

    def log(
        self,
        raw_data: dict,
        neural_az: float,
        neural_el: float,
        gaze_sx: float,
        gaze_sy: float,
        stimulus_x: Optional[float] = None,
        stimulus_y: Optional[float] = None,
    ):
        if not self.active or self.writer is None:
            return

        try:
            row = {
                "timestamp": time.time(),
                "frame_w": raw_data.get("frame_w", 0),
                "frame_h": raw_data.get("frame_h", 0),
                "cx": raw_data.get("cx", 0.0),
                "cy": raw_data.get("cy", 0.0),
                "pupil_area": raw_data.get("pupil_area", 0.0),
                "ellipse_major": raw_data.get("ellipse_major", 0.0),
                "ellipse_minor": raw_data.get("ellipse_minor", 0.0),
                "ellipse_angle": raw_data.get("ellipse_angle", 0.0),
                "inner_darkness": raw_data.get("inner_darkness", 0.0),
                "iris_contrast": raw_data.get("iris_contrast", 0.0),
                "confidence": raw_data.get("confidence", 0.0),
                "neural_az": neural_az,
                "neural_el": neural_el,
                "gaze_screen_x": gaze_sx,
                "gaze_screen_y": gaze_sy,
                "stimulus_x": stimulus_x if stimulus_x is not None else "",
                "stimulus_y": stimulus_y if stimulus_y is not None else "",
            }
            self.writer.writerow(row)
        except Exception:
            pass

    def stop(self):
        if self.file is not None:
            try:
                self.file.close()
            except Exception:
                pass
        self.file = None
        self.writer = None
        self.active = False