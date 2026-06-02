"""Optional VEER-style webcam security shield for Veronica.

The shield is opt-in and local. It uses OpenCV plus face_recognition only when
installed, stores known-face samples and intruder snapshots under the assistant
data directory, and never hardcodes WhatsApp numbers.
"""

from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ALERT_COOLDOWN_SECONDS = 60
DEFAULT_OWNER_NAME = "Owner"
KNOWN_FACE_SUFFIXES = (".jpg", ".jpeg", ".png")


@dataclass(slots=True)
class SecurityShield:
    """Manage face registration, intruder snapshots, and background monitoring."""

    data_dir: Path
    owner_name: str = DEFAULT_OWNER_NAME
    alert_cooldown: int = ALERT_COOLDOWN_SECONDS
    _running: bool = False
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _last_alert_time: float = field(default=0.0, init=False, repr=False)

    @property
    def photos_dir(self) -> Path:
        return self.data_dir / "logs" / "intruders"

    @property
    def known_faces_dir(self) -> Path:
        return self.data_dir / "known_faces"

    @property
    def running(self) -> bool:
        return self._running

    def check_dependencies(self, require_face_recognition: bool = True) -> str | None:
        """Return setup guidance when required optional security modules are missing."""
        missing = []
        if _optional_module("cv2") is None:
            missing.append("opencv-python")
        if require_face_recognition and _optional_module("face_recognition") is None:
            missing.append("face-recognition")
        if require_face_recognition and _optional_module("numpy") is None:
            missing.append("numpy")
        if missing:
            return "Security shield ke liye install karo: pip install -r requirements-security.txt"
        return None

    def register_face(self, sample_count: int = 10, camera_index: int = 0) -> str:
        """Capture face samples for the owner from the webcam."""
        ready_message = self.check_dependencies(require_face_recognition=True)
        if ready_message is not None:
            return ready_message

        cv2 = _optional_module("cv2")
        face_recognition = _optional_module("face_recognition")
        self.known_faces_dir.mkdir(parents=True, exist_ok=True)
        camera = cv2.VideoCapture(camera_index)
        captured = 0
        try:
            while captured < sample_count:
                ok, frame = camera.read()
                if not ok:
                    time.sleep(0.1)
                    continue
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                faces = face_recognition.face_locations(rgb_frame)
                if not faces:
                    continue
                path = self.known_faces_dir / f"{self.owner_name}_{captured}.jpg"
                cv2.imwrite(str(path), frame)
                captured += 1
                time.sleep(0.1)
        finally:
            camera.release()
            destroy_windows = getattr(cv2, "destroyAllWindows", None)
            if callable(destroy_windows):
                destroy_windows()
        return f"{self.owner_name} ka face register ho gaya! {captured} photo saved."

    def load_known_encodings(self) -> tuple[list[Any], list[str]]:
        """Load face encodings from known-face images."""
        face_recognition = _optional_module("face_recognition")
        if face_recognition is None or not self.known_faces_dir.exists():
            return [], []

        encodings: list[Any] = []
        names: list[str] = []
        for path in sorted(self.known_faces_dir.iterdir()):
            if path.suffix.lower() not in KNOWN_FACE_SUFFIXES:
                continue
            image = face_recognition.load_image_file(str(path))
            face_encodings = face_recognition.face_encodings(image)
            if face_encodings:
                encodings.append(face_encodings[0])
                names.append(path.stem.split("_", 1)[0])
        return encodings, names

    def capture_intruder(self, frame: Any, cv2_module: Any | None = None) -> Path:
        """Save an intruder frame to the local data directory."""
        cv2 = cv2_module or _optional_module("cv2")
        if cv2 is None:
            raise RuntimeError("opencv-python is required to save intruder snapshots")
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.photos_dir / f"intruder_{timestamp}.jpg"
        cv2.imwrite(str(path), frame)
        return path

    def send_whatsapp_alert(self, photo_path: str | Path) -> str:
        """Send an optional WhatsApp alert when configured and cooldown allows it."""
        now = time.time()
        if now - self._last_alert_time < self.alert_cooldown:
            return "Security alert cooldown active hai."

        phone_number = os.getenv("SECURITY_WHATSAPP_NUMBER", "").strip() or os.getenv("WHATSAPP_NUMBER", "").strip()
        if not phone_number:
            return "Security alert ke liye SECURITY_WHATSAPP_NUMBER environment variable set karo."

        pywhatkit = _optional_module("pywhatkit")
        if pywhatkit is None:
            return "Security WhatsApp alert ke liye pywhatkit install karo: pip install -r requirements-security.txt"

        timestamp = dt.datetime.now().strftime("%d/%m/%Y %I:%M %p")
        message = (
            "🚨 VERONICA SECURITY ALERT!\n"
            "Unknown person detected on your laptop!\n"
            f"Time: {timestamp}\n"
            f"Photo: {Path(photo_path).name}"
        )
        send_time = dt.datetime.now() + dt.timedelta(minutes=1)
        try:
            pywhatkit.sendwhatmsg(phone_number, message, send_time.hour, send_time.minute, wait_time=10)
        except Exception as exc:  # pragma: no cover - third-party integration boundary
            return f"Security WhatsApp error: {exc}"
        self._last_alert_time = now
        return "Security WhatsApp alert bheja."

    def security_loop(self, on_alert: Callable[[Path], None] | None = None, camera_index: int = 0) -> str:
        """Run the webcam monitoring loop until stopped."""
        ready_message = self.check_dependencies(require_face_recognition=True)
        if ready_message is not None:
            self._running = False
            return ready_message

        cv2 = _optional_module("cv2")
        face_recognition = _optional_module("face_recognition")
        numpy = _optional_module("numpy")
        known_encodings, known_names = self.load_known_encodings()
        if not known_encodings:
            self._running = False
            return "Koi registered face nahi! Pehle register face chalao."

        camera = cv2.VideoCapture(camera_index)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._running = True
        frame_count = 0
        try:
            while self._running:
                ok, frame = camera.read()
                if not ok:
                    time.sleep(1)
                    continue
                frame_count += 1
                if frame_count % 5 != 0:
                    continue
                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                locations = face_recognition.face_locations(rgb_frame)
                encodings = face_recognition.face_encodings(rgb_frame, locations)
                for encoding in encodings:
                    matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.5)
                    distances = face_recognition.face_distance(known_encodings, encoding)
                    if True in matches:
                        best_index = int(numpy.argmin(distances))
                        if matches[best_index]:
                            continue
                    photo_path = self.capture_intruder(frame, cv2_module=cv2)
                    self.send_whatsapp_alert(photo_path)
                    if on_alert is not None:
                        on_alert(photo_path)
                time.sleep(0.1)
        finally:
            camera.release()
            self._running = False
        return "Security shield deactivated."

    def start_security(self, on_alert: Callable[[Path], None] | None = None) -> str:
        """Start the security loop in a daemon thread."""
        if self._running:
            return "Security shield pehle se chal raha hai."
        ready_message = self.check_dependencies(require_face_recognition=True)
        if ready_message is not None:
            return ready_message
        known_encodings, _known_names = self.load_known_encodings()
        if not known_encodings:
            return "Koi registered face nahi! Pehle register face chalao."
        self._thread = threading.Thread(target=self.security_loop, kwargs={"on_alert": on_alert}, daemon=True)
        self._thread.start()
        return "Security shield start ho gaya."

    def stop_security(self) -> str:
        """Stop the background security loop."""
        self._running = False
        return "Security shield stop kar diya."


def _optional_module(module_name: str):
    if importlib.util.find_spec(module_name) is None:
        return None
    return importlib.import_module(module_name)
