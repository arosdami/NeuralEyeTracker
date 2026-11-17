"""Local HTTP API for the real Neural Eye Tracker processing core."""

from __future__ import annotations

import json
import os
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


API_HOST = "127.0.0.1"
API_PORT = 8765
FRAME_JPEG_QUALITY = 82
DEFAULT_CAMERA_INDEX = 0


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
        }

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

        capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
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

            result = self.detector.detect(frame)
            raw_data = result.get("raw_data") or {}
            detected = bool(result.get("detected", False))
            confidence = float(result.get("confidence", 0.0))

            neural_az = None
            neural_el = None
            if self.neural_model.is_trained and detected:
                neural_az, neural_el = self.neural_model.predict(raw_data)

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
            self._json({"ok": service.start(camera_index)})
        elif path == "/api/stop":
            service.stop()
            self._json({"ok": True})
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
