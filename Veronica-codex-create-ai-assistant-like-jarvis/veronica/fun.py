"""VEER-inspired fun, focus, and productivity helpers for Veronica.

The module keeps everything local and inspectable: jokes, quotes, quiz prompts,
coin/dice games, JSON-backed productivity counts, and a safe focus timer. Focus
mode never closes apps unless explicitly enabled with an environment variable.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import random
import re
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

JOKES = (
    "Teacher: Sentence mein 'because' use karo. Student: Kyunki 'because' ek word hai. 😄",
    "Ek aadmi doctor ke paas gaya. Doctor: Kya problem hai? Aadmi: Mujhe lagta hai main invisible hoon. Doctor: Next please!",
    "Boss: Tum late kyu aaye? Employee: Sir, aapne kaha tha 9 baje aao, main 9 baj ke 60 minute pe aaya — exactly!",
    "Ek programmer ki wife ne kaha: Baazar jao, ek litre doodh lo, aur agar eggs mile to 6 lana. Woh 6 litre doodh laya — eggs mile the.",
    "Python developer ne kya kaha apni maa ko? Mom, indentation sahi karo warna main ghar se run nahi karunga!",
    "VEER joke: Main itna smart hoon ke mujhe khud nahi pata! 🤖",
)

QUOTES = (
    "Kaam karo aur results ki chinta mat karo — Bhagavad Gita.",
    "Sapne woh nahi jo neend mein aate hain, sapne woh hain jo neend nahi aane dete — APJ Abdul Kalam.",
    "Har subah ek nayi shuruaat hai — uthho, try karo, grow karo!",
    "Code likha toh galti hogi, galti se seekha toh developer banega — VEER.",
    "Success woh log paate hain jo try karna band nahi karte.",
    "Zindagi mein shortcuts mat dhundo — effort hi shortcut hai.",
)

QUIZ = (
    {"q": "Python kaun si programming language hai?", "a": ("interpreted", "high level"), "hint": "C nahi hai yeh"},
    {"q": "CPU ka full form kya hai?", "a": ("central processing unit",), "hint": "Computer ka brain"},
    {"q": "Bharat ki rajdhani kya hai?", "a": ("delhi", "new delhi"), "hint": "North mein hai"},
    {"q": "1 GB mein kitne MB hote hain?", "a": ("1024",), "hint": "1000 nahi, thoda zyada"},
    {"q": "HTTP ka full form kya hai?", "a": ("hypertext transfer protocol",), "hint": "Web ka protocol"},
    {"q": "Cricket mein ek over mein kitni balls hoti hain?", "a": ("6",), "hint": "Half dozen"},
    {"q": "Python file ka extension kya hota hai?", "a": (".py", "py"), "hint": "2 letters"},
)

DISTRACTION_APPS = (
    "chrome.exe",
    "youtube.exe",
    "instagram.exe",
    "facebook.exe",
    "twitter.exe",
)

JOKE_WORDS = ("joke", "hasao", "funny")
QUOTE_WORDS = ("motivate", "quote", "inspire", "himmat do")
QUIZ_WORDS = ("quiz khelo", "quiz", "gk question", "sawaal poochho", "gk")
COIN_WORDS = ("coin", "heads tails", "uchhalo")
DICE_WORDS = ("dice", "pasha", "number nikalo")
FOCUS_ON_WORDS = ("focus on", "focus mode on", "concentrate")
FOCUS_OFF_WORDS = ("focus off", "focus mode off", "focus band", "break lo")
REPORT_WORDS = ("productivity", "kitna kaam", "aaj ka report")
GREETING_WORDS = ("smart greeting", "good morning", "good afternoon", "good evening")


@dataclass(slots=True)
class FunManager:
    """Manage fun commands, productivity counters, and focus mode."""

    data_dir: Path
    speaker: Callable[[str], None] | None = None
    randomizer: random.Random = field(default_factory=random.Random)
    focus_active: bool = False
    focus_start: dt.datetime | None = None
    session_commands: int = 0
    _focus_timer: threading.Timer | None = field(default=None, init=False, repr=False)

    @property
    def productivity_file(self) -> Path:
        return self.data_dir / "productivity.json"

    def handle(self, command: str) -> str | None:
        """Handle a fun/productivity command, returning None when not matched."""
        normalized = _normalize(command)
        if _contains_any(normalized, FOCUS_OFF_WORDS):
            return self.stop_focus()
        if _contains_any(normalized, JOKE_WORDS):
            return self.tell_joke()
        if _contains_any(normalized, QUOTE_WORDS):
            return self.motivate()
        if _contains_any(normalized, QUIZ_WORDS):
            return self.play_quiz()
        if _contains_any(normalized, COIN_WORDS):
            return self.coin_flip()
        if _contains_any(normalized, DICE_WORDS):
            return self.dice_roll()
        if _contains_any(normalized, FOCUS_ON_WORDS):
            return self.start_focus(_extract_minutes(normalized) or 25)
        if _contains_any(normalized, REPORT_WORDS):
            return self.get_productivity_report()
        if _contains_any(normalized, GREETING_WORDS):
            return self.smart_greeting()
        return None

    def load_productivity(self) -> dict[str, int]:
        """Load daily command counts from disk."""
        if not self.productivity_file.exists():
            return {}
        try:
            data = json.loads(self.productivity_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(day): int(count) for day, count in data.items() if isinstance(count, int)}

    def save_productivity(self, data: dict[str, int]) -> None:
        """Persist daily command counts."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.productivity_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def log_command_usage(self, day: dt.date | None = None) -> None:
        """Record one assistant command for the productivity report."""
        self.session_commands += 1
        active_day = (day or dt.date.today()).isoformat()
        data = self.load_productivity()
        data[active_day] = data.get(active_day, 0) + 1
        self.save_productivity(data)

    def get_productivity_report(self, today: dt.date | None = None) -> str:
        """Return today's count, weekly count, and current streak."""
        active_day = today or dt.date.today()
        data = self.load_productivity()
        week = [(active_day - dt.timedelta(days=offset)).isoformat() for offset in range(7)]
        today_count = data.get(active_day.isoformat(), 0)
        week_count = sum(data.get(day, 0) for day in week)
        streak = 0
        for day in week:
            if data.get(day, 0) > 0:
                streak += 1
            else:
                break
        encouragement = "Kya baat hai!" if streak >= 3 else "Aur mehnat karo!"
        return (
            f"Aaj tumne Veronica se {today_count} commands liye. "
            f"Is hafte total {week_count} commands. {streak} din ka streak chal raha hai! {encouragement}"
        )

    def start_focus(self, minutes: int = 25) -> str:
        """Start a focus timer and optionally close distraction apps when enabled."""
        safe_minutes = max(1, minutes)
        self.focus_active = True
        self.focus_start = dt.datetime.now()
        killed = self._close_distractions_if_enabled()
        if self._focus_timer is not None:
            self._focus_timer.cancel()
        self._focus_timer = threading.Timer(safe_minutes * 60, self._finish_focus, args=(safe_minutes,))
        self._focus_timer.daemon = True
        self._focus_timer.start()
        killed_text = f" {', '.join(killed)} band kar diya." if killed else ""
        return (
            f"Focus mode on! {safe_minutes} minute ke liye concentrate karo.{killed_text} "
            f"Main {safe_minutes} minute baad remind karunga."
        )

    def stop_focus(self) -> str:
        """Stop the active focus session."""
        if not self.focus_active:
            return "Focus mode abhi chal nahi raha."
        self.focus_active = False
        if self._focus_timer is not None:
            self._focus_timer.cancel()
            self._focus_timer = None
        if self.focus_start is None:
            return "Focus mode band kar diya."
        elapsed = int((dt.datetime.now() - self.focus_start).total_seconds() / 60)
        return f"Focus mode band! Tumne {elapsed} minute focus kiya — shabash!"

    def play_quiz(self) -> str:
        """Return one quiz question."""
        question = self.randomizer.choice(QUIZ)
        return f"Quiz time! {question['q']} (Hint: {question['hint']})"

    def coin_flip(self) -> str:
        """Flip a virtual coin."""
        result = self.randomizer.choice(("Heads", "Tails"))
        return f"Coin uchhala... {result}! {'Aage' if result == 'Heads' else 'Peeche'}"

    def dice_roll(self) -> str:
        """Roll a virtual six-sided die."""
        return f"Dice daala... {self.randomizer.randint(1, 6)} aaya!"

    def tell_joke(self) -> str:
        """Return a random joke."""
        return self.randomizer.choice(JOKES)

    def motivate(self) -> str:
        """Return a random motivational quote."""
        return self.randomizer.choice(QUOTES)

    def smart_greeting(self, now: dt.datetime | None = None) -> str:
        """Return a time/day-aware greeting."""
        current = now or dt.datetime.now()
        if 5 <= current.hour < 12:
            greeting = "Good Morning"
        elif 12 <= current.hour < 17:
            greeting = "Good Afternoon"
        elif 17 <= current.hour < 21:
            greeting = "Good Evening"
        else:
            greeting = "Good Night"

        extras: list[str] = []
        if current.strftime("%A") == "Monday":
            extras.append("Naye hafte ki shuruaat — ache se karo!")
        elif current.strftime("%A") == "Friday":
            extras.append("Aaj Friday hai — weekend aane wala hai!")
        elif current.strftime("%A") in {"Saturday", "Sunday"}:
            extras.append("Weekend hai — relax karo thoda!")
        if current.hour < 9:
            extras.append(self.motivate())
        extra_text = " ".join(extras)
        return f"{greeting}! {extra_text} Kya kaam hai aaj?".strip()

    def _close_distractions_if_enabled(self) -> list[str]:
        if os.getenv("VERONICA_FOCUS_CLOSE_APPS") != "1":
            return []
        killed: list[str] = []
        for app in DISTRACTION_APPS:
            command = ["taskkill", "/f", "/im", app] if os.name == "nt" else ["pkill", "-x", app.removesuffix(".exe")]
            result = subprocess.run(command, capture_output=True, check=False)
            if result.returncode == 0:
                killed.append(app.removesuffix(".exe"))
        return killed

    def _finish_focus(self, minutes: int) -> None:
        self.focus_active = False
        self._focus_timer = None
        if self.speaker is not None:
            self.speaker(f"{minutes} minute poore ho gaye. Focus session khatam — ab break lo!")


def is_fun_command(command: str) -> bool:
    """Return True when a message should be handled by FunManager."""
    normalized = _normalize(command)
    return any(
        _contains_any(normalized, words)
        for words in (
            FOCUS_OFF_WORDS,
            JOKE_WORDS,
            QUOTE_WORDS,
            QUIZ_WORDS,
            COIN_WORDS,
            DICE_WORDS,
            FOCUS_ON_WORDS,
            REPORT_WORDS,
            GREETING_WORDS,
        )
    )


def check_quiz_answer(answer: str, question_data: dict[str, object]) -> bool:
    """Check a quiz answer against a question dictionary."""
    accepted = question_data.get("a", ())
    if not isinstance(accepted, (tuple, list)):
        return False
    return any(str(option).lower() in answer.lower() for option in accepted)


def _extract_minutes(command: str) -> int | None:
    match = re.search(r"(\d+)\s*(minute|min)", command)
    return int(match.group(1)) if match else None


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())
