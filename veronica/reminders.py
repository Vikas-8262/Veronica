"""Local reminder storage, parsing, and background scheduling.

This module adapts the user's VEER reminder flow while keeping it standard-library
only. Reminders are stored as JSON in the assistant data directory and can be
checked by a lightweight background thread when enabled.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REMINDER_COMMAND_WORDS = (
    "remind me",
    "remind karo",
    "reminder",
    "yaad dilao",
    "yaad dilaao",
)
LIST_REMINDER_WORDS = ("show reminders", "list reminders", "reminders", "reminder list")
DEFAULT_MESSAGE = "Kuch kaam tha!"


@dataclass(slots=True)
class ReminderManager:
    """Manage JSON-backed reminders and an optional background scheduler."""

    data_dir: Path
    speaker: Callable[[str], None] | None = None
    poll_seconds: float = 30.0
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, init=False, repr=False)

    @property
    def reminders_file(self) -> Path:
        return self.data_dir / "reminders.json"

    def load_reminders(self) -> list[dict[str, Any]]:
        """Load reminders from disk, returning an empty list for missing/corrupt files."""
        if not self.reminders_file.exists():
            return []
        try:
            data = json.loads(self.reminders_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def save_reminders(self, reminders: list[dict[str, Any]]) -> None:
        """Persist reminders to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reminders_file.write_text(json.dumps(reminders, indent=2), encoding="utf-8")

    def set_reminder(self, message: str, minutes: int | None = None, at_time: str | None = None) -> str:
        """Create a reminder for a relative minute delay or HH:MM local time."""
        cleaned = _clean_message(message)
        trigger_at = _trigger_time(minutes=minutes, at_time=at_time)
        if trigger_at is None:
            return "Kab remind karoon? Time ya minutes batao."

        reminder = {
            "message": cleaned or DEFAULT_MESSAGE,
            "time": trigger_at.strftime("%H:%M"),
            "trigger_at": trigger_at.isoformat(timespec="minutes"),
            "done": False,
        }
        reminders = self.load_reminders()
        reminders.append(reminder)
        self.save_reminders(reminders)
        return f"Reminder set! {reminder['time']} par yaad dilaaoonga: '{reminder['message']}'"

    def parse_and_set_reminder(self, command: str) -> str:
        """Parse common Hinglish reminder commands and create a reminder."""
        normalized = _normalize(command)

        minute_match = re.search(r"(\d+)\s*(minute|min|mins)", normalized)
        if minute_match:
            minutes = int(minute_match.group(1))
            message = _remove_patterns(
                command,
                (
                    r"\d+\s*(minute|min|mins)\s*(baad|mein|me)?",
                    r"remind\s+me\s+to",
                    r"remind\s+me",
                    r"remind\s+karo",
                    r"reminder",
                    r"yaad\s+dila(?:o|ao)",
                ),
            )
            return self.set_reminder(message, minutes=minutes)

        time_match = re.search(r"(\d{1,2})[:\s](\d{2})", normalized)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            at_time = f"{hour:02d}:{minute:02d}"
            message = _remove_patterns(
                command,
                (
                    r"\d{1,2}[:\s]\d{2}",
                    r"remind\s+me\s+to",
                    r"remind\s+me",
                    r"remind\s+karo",
                    r"reminder",
                    r"at",
                    r"baje",
                    r"yaad\s+dila(?:o|ao)",
                ),
            )
            return self.set_reminder(message, at_time=at_time)

        baje_match = re.search(r"(\d{1,2})\s*baje", normalized)
        if baje_match:
            hour = int(baje_match.group(1))
            at_time = f"{hour:02d}:00"
            message = _remove_patterns(
                command,
                (
                    r"\d{1,2}\s*baje",
                    r"remind\s+me\s+to",
                    r"remind\s+me",
                    r"remind\s+karo",
                    r"reminder",
                    r"yaad\s+dila(?:o|ao)",
                ),
            )
            return self.set_reminder(message, at_time=at_time)

        return "Sahi format mein batao: '10 minute baad meeting remind karo'"

    def list_reminders(self) -> str:
        """Return up to five active reminders."""
        active = [reminder for reminder in self.load_reminders() if not reminder.get("done")]
        if not active:
            return "Koi reminder nahi hai abhi."
        summary = " | ".join(
            f"{reminder.get('time', '??:??')} - {reminder.get('message', DEFAULT_MESSAGE)}"
            for reminder in active[:5]
        )
        return f"{len(active)} reminder hain: {summary}"

    def run_pending(self, now: dt.datetime | None = None) -> list[str]:
        """Mark due reminders done and speak/return their notification messages."""
        current = now or dt.datetime.now()
        reminders = self.load_reminders()
        notifications: list[str] = []
        changed = False
        for reminder in reminders:
            if reminder.get("done"):
                continue
            trigger_at = _parse_trigger_at(reminder)
            if trigger_at is None or trigger_at > current:
                continue
            reminder["done"] = True
            changed = True
            notification = f"Yaad dilana tha — {reminder.get('message', DEFAULT_MESSAGE)}"
            notifications.append(notification)
            if self.speaker is not None:
                self.speaker(notification)
        if changed:
            self.save_reminders(reminders)
        return notifications

    def start_background(self, speaker: Callable[[str], None] | None = None) -> str:
        """Start checking reminders in a daemon thread."""
        if speaker is not None:
            self.speaker = speaker
        if self._thread and self._thread.is_alive():
            return "Reminder scheduler pehle se chal raha hai."
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        return "Reminder scheduler start ho gaya."

    def stop_background(self) -> str:
        """Stop the background reminder checker."""
        self._stop_event.set()
        return "Reminder scheduler stop ho gaya."

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.run_pending()
            self._stop_event.wait(self.poll_seconds)


def is_reminder_command(command: str) -> bool:
    """Return True when a message should be handled by reminders."""
    normalized = _normalize(command)
    return any(word in normalized for word in (*REMINDER_COMMAND_WORDS, *LIST_REMINDER_WORDS))


def _trigger_time(minutes: int | None = None, at_time: str | None = None) -> dt.datetime | None:
    now = dt.datetime.now().replace(second=0, microsecond=0)
    if minutes is not None:
        return now + dt.timedelta(minutes=minutes)
    if at_time is None:
        return None
    hour_text, minute_text = at_time.split(":", 1)
    trigger = now.replace(hour=int(hour_text), minute=int(minute_text))
    if trigger <= now:
        trigger += dt.timedelta(days=1)
    return trigger


def _parse_trigger_at(reminder: dict[str, Any]) -> dt.datetime | None:
    trigger_at = reminder.get("trigger_at")
    if isinstance(trigger_at, str):
        try:
            return dt.datetime.fromisoformat(trigger_at)
        except ValueError:
            return None
    reminder_time = reminder.get("time")
    if isinstance(reminder_time, str) and re.fullmatch(r"\d{2}:\d{2}", reminder_time):
        hour, minute = reminder_time.split(":", 1)
        now = dt.datetime.now().replace(second=0, microsecond=0)
        return now.replace(hour=int(hour), minute=int(minute))
    return None


def _clean_message(message: str) -> str:
    return " ".join(message.strip(" :-").split())


def _remove_patterns(text: str, patterns: tuple[str, ...]) -> str:
    result = text
    for pattern in patterns:
        result = re.sub(pattern, " ", result, flags=re.IGNORECASE)
    return _clean_message(result)


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())
