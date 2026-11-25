"""Local HTTP API for the real Neural Eye Tracker processing core."""

from __future__ import annotations

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.neural_model import NeuralGazeModel
from core.pupil_detector import PupilDetector
from config.settings import (
    AZIMUTH_RANGE,
    CALIB_GRID_COLS,
    CALIB_GRID_ROWS,
    CALIB_MARGIN,
    CALIB_SAMPLES_PER_POINT,
    ELEVATION_RANGE,
)


API_HOST = "127.0.0.1"
API_PORT = 8765
FRAME_JPEG_QUALITY = 82
DEFAULT_CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
UNCALIBRATED_AZIMUTH_SPAN = 40.0
UNCALIBRATED_ELEVATION_SPAN = 30.0


class TrackerService:
    """Owns the camera loop and exposes only measured tracker state."""

    def __init__(self) -> None:
        self.detector = PupilDetector()
        self.neural_model = NeuralGazeModel()
        self._lock = threading.Lock()
        self._capture: cv2.VideoCapture | None = None
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._frame_jpeg: bytes | None = None
        self._last_frame_time = 0.0
        self._fps = 0.0
        self._camera_index = DEFAULT_CAMERA_INDEX
        self._calibration_targets = self._build_calibration_targets()
        self._calibration_target_index = 0
        self._calibration_samples = 0
        self._calibration_target: tuple[float, float] | None = None
        self._state: dict[str, Any] = {
            "status": "idle",
            "error": None,
            "running": False,
            "tracking": False,
            "model_trained": False,
            "camera_index": DEFAULT_CAMERA_INDEX,
            "fps": 0.0,
            "confidence": None,
            "cx": None,
            "cy": None,
            "pupil_size": None,
            "radius_px": None,
            "neural_az": None,
            "neural_el": None,
            "raw_data": None,
            "updated_at": None,
            "calibration_active": False,
            "calibration_index": 0,
            "calibration_total": len(self._calibration_targets),
            "calibration_samples": 0,
            "calibration_samples_required": CALIB_SAMPLES_PER_POINT,
            "calibration_x": None,
            "calibration_y": None,
        }

    @staticmethod
    def _build_calibration_targets() -> list[tuple[float, float, float, float]]:
        targets = []
        for row in range(CALIB_GRID_ROWS):
            y = CALIB_MARGIN + (1 - 2 * CALIB_MARGIN) * row / max(CALIB_GRID_ROWS - 1, 1)
            elevation = ELEVATION_RANGE[1] - y * (ELEVATION_RANGE[1] - ELEVATION_RANGE[0])
            for col in range(CALIB_GRID_COLS):
                x = CALIB_MARGIN + (1 - 2 * CALIB_MARGIN) * col / max(CALIB_GRID_COLS - 1, 1)
                azimuth = AZIMUTH_RANGE[0] + x * (AZIMUTH_RANGE[1] - AZIMUTH_RANGE[0])
                targets.append((x, y, azimuth, elevation))
        return targets

    def state(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def frame(self) -> bytes | None:
        with self._lock:
            return self._frame_jpeg

    def start(self, camera_index: int = DEFAULT_CAMERA_INDEX) -> bool:
        with self._lock:
            if self._worker and self._worker.is_alive():
                return True

        capture = self._open_capture(camera_index)
        if capture is None:
            self._set_error(
                f"A kamera nem nyitható meg (index: {camera_index})."
            )
            return False

        self._camera_index = camera_index
        self.detector.reset()
        self._stop_event.clear()
        with self._lock:
            self._capture = capture
            self._state.update({
                "status": "starting",
                "error": None,
                "running": True,
                "camera_index": camera_index,
            })

        self._worker = threading.Thread(
            target=self._run,
            name="neural-eye-tracker",
            daemon=True,
        )
        self._worker.start()
        return True

    @staticmethod
    def _open_capture(camera_index: int) -> cv2.VideoCapture | None:
        """Use the same backend fallback order as the desktop application."""
        camera_indexes = [camera_index] if camera_index == DEFAULT_CAMERA_INDEX else [camera_index, DEFAULT_CAMERA_INDEX]
        for selected_camera in camera_indexes:
            for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY):
                try:
                    capture = cv2.VideoCapture(selected_camera, backend)
                    if not capture.isOpened():
                        capture.release()
                        continue
                    ok, first_frame = capture.read()
                    if not ok or first_frame is None:
                        capture.release()
                        continue
                    capture.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    return capture
                except cv2.error:
                    continue
        return None

    def stop(self) -> None:
        self._stop_event.set()
        worker = self._worker
        if worker and worker.is_alive():
            worker.join(timeout=2.0)
        with self._lock:
            if self._capture is not None:
                self._capture.release()
            self._capture = None
            self._worker = None
            self._state.update({
                "status": "idle",
                "running": False,
                "tracking": False,
            })

    def start_calibration(self) -> tuple[bool, str | None]:
        with self._lock:
            if not self._state["running"]:
                return False, "A kalibrációhoz előbb indítsd el a kamerát."
            self.neural_model.reset()
            self._calibration_target_index = 0
            self._calibration_samples = 0
            self._calibration_target = None
            self._state.update({
                "calibration_active": True,
                "calibration_index": 0,
                "calibration_samples": 0,
                "calibration_x": None,
                "calibration_y": None,
                "model_trained": False,
            })
        return True, None

    def _run(self) -> None:
        previous_time = time.perf_counter()
        while not self._stop_event.is_set():
            with self._lock:
                capture = self._capture
            if capture is None:
                break

            ok, frame = capture.read()
            if not ok or frame is None:
                self._set_error("A kamerából nem érkezik érvényes képkocka.")
                break

            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            result = self.detector.detect(frame)
            raw_data = result.get("raw_data") or {}
            detected = bool(result.get("detected", False))
            confidence = float(result.get("confidence", 0.0))

            self._collect_calibration_sample(raw_data, detected, confidence)

            neural_az = None
            neural_el = None
            if self.neural_model.is_trained and detected:
                neural_az, neural_el = self.neural_model.predict(raw_data)
            elif detected:
                # This is the same uncalibrated geometric preview as the
                # desktop UI; trained predictions still come exclusively
                # from NeuralGazeModel.
                neural_az = (
                    (float(result.get("cx", FRAME_WIDTH / 2)) - FRAME_WIDTH / 2)
                    / (FRAME_WIDTH / 2) * UNCALIBRATED_AZIMUTH_SPAN
                )
                neural_el = (
                    -(float(result.get("cy", FRAME_HEIGHT / 2)) - FRAME_HEIGHT / 2)
                    / (FRAME_HEIGHT / 2) * UNCALIBRATED_ELEVATION_SPAN
                )

            now = time.perf_counter()
            elapsed = now - previous_time
            previous_time = now
            if elapsed > 0:
                self._fps = 1.0 / elapsed

            display_frame = frame.copy()
            self._draw_overlay(display_frame, result, neural_az, neural_el)
            encoded, buffer = cv2.imencode(
                ".jpg",
                display_frame,
                [cv2.IMWRITE_JPEG_QUALITY, FRAME_JPEG_QUALITY],
            )
            if not encoded:
                continue

            with self._lock:
                self._frame_jpeg = buffer.tobytes()
                self._state.update({
                    "status": "tracking" if detected else "waiting",
                    "error": None,
                    "running": True,
                    "tracking": detected,
                    "model_trained": self.neural_model.is_trained,
                    "fps": round(self._fps, 1),
                    "confidence": round(confidence, 4),
                    "cx": round(float(result.get("cx", 0.0)), 2),
                    "cy": round(float(result.get("cy", 0.0)), 2),
                    "pupil_size": round(float(result.get("pupil_size", 0.0)), 4),
                    "radius_px": round(float(result.get("radius_px", 0.0)), 2),
                    "neural_az": neural_az,
                    "neural_el": neural_el,
                    "raw_data": raw_data,
                    "updated_at": time.time(),
                })

        with self._lock:
            self._state.update({
                "running": False,
                "tracking": False,
            })

    @staticmethod
    def _draw_overlay(
        frame: Any,
        result: dict[str, Any],
        neural_az: float | None,
        neural_el: float | None,
    ) -> None:
        if not result.get("detected"):
            return
        cx = int(result.get("cx", 0))
        cy = int(result.get("cy", 0))
        radius = max(3, int(result.get("radius_px", 3)))
        cv2.ellipse(
            frame,
            (cx, cy),
            (radius, radius),
            0,
            0,
            360,
            (0, 193, 255),
            2,
            cv2.LINE_AA,
        )
        if neural_az is not None and neural_el is not None:
            label = f"az {neural_az:.1f}  el {neural_el:.1f}"
            cv2.putText(
                frame,
                label,
                (16, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._state.update({
                "status": "error",
                "error": message,
                "running": False,
                "tracking": False,
            })

    def _collect_calibration_sample(
        self, raw_data: dict[str, Any], detected: bool, confidence: float
    ) -> None:
        with self._lock:
            if not self._state["calibration_active"] or self._calibration_target is None:
                return
            if not detected or confidence < 0.15:
                return
            target = self._calibration_target
            self._calibration_samples += 1
            samples = self._calibration_samples
            index = self._calibration_target_index
        self.neural_model.add_training_sample(raw_data, target)
        if samples < CALIB_SAMPLES_PER_POINT:
            with self._lock:
                self._state["calibration_samples"] = samples
            return

        with self._lock:
            self._calibration_target_index += 1
            self._calibration_samples = 0
            completed = self._calibration_target_index >= len(self._calibration_targets)
            self._state["calibration_index"] = self._calibration_target_index
            self._state["calibration_samples"] = 0
            if completed:
                self._state["calibration_active"] = False
                self._calibration_target = None
                self._state["calibration_x"] = None
                self._state["calibration_y"] = None
        if completed:
            result = self.neural_model.train()
            with self._lock:
                self._state["model_trained"] = not bool(result.get("error"))

    def set_calibration_target(self) -> tuple[bool, str | None]:
        with self._lock:
            if not self._state["calibration_active"]:
                return False, "Nincs aktív kalibráció."
            if self._calibration_target_index >= len(self._calibration_targets):
                return False, "A kalibráció befejeződött."
            x, y, azimuth, elevation = self._calibration_targets[self._calibration_target_index]
            self._calibration_target = (azimuth, elevation)
            self._state.update({
                "calibration_x": x,
                "calibration_y": y,
            })
        return True, None


service = TrackerService()


class ApiHandler(BaseHTTPRequestHandler):
    """Small dependency-free JSON/JPEG API used by the local React client."""

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json({"ok": True})
        elif path == "/api/state":
            self._json(service.state())
        elif path == "/api/frame.jpg":
            self._frame()
        else:
            self.send_error(404, "Ismeretlen API útvonal.")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        if path == "/api/start":
            try:
                camera_index = int(query.get("camera", ["0"])[0])
            except ValueError:
                self._json({"ok": False, "error": "Érvénytelen kameraindex."}, 400)
                return
            started = service.start(camera_index)
            state = service.state()
            self._json({"ok": started, "error": state.get("error")})
        elif path == "/api/stop":
            service.stop()
            self._json({"ok": True})
        elif path == "/api/calibration/start":
            ok, error = service.start_calibration()
            if ok:
                ok, error = service.set_calibration_target()
            self._json({"ok": ok, "error": error}, 200 if ok else 409)
        elif path == "/api/calibration/target":
            ok, error = service.set_calibration_target()
            self._json({"ok": ok, "error": error}, 200 if ok else 409)
        else:
            self.send_error(404, "Ismeretlen API útvonal.")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _frame(self) -> None:
        frame = service.frame()
        if frame is None:
            self.send_error(404, "Még nincs elérhető kamera képkocka.")
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(frame)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(frame)


def main() -> None:
    server = ThreadingHTTPServer((API_HOST, API_PORT), ApiHandler)
    print(f"Neural Eye Tracker API: http://{API_HOST}:{API_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()
        server.server_close()


if __name__ == "__main__":
    main()
