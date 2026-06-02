"""Local dictation and auto-type support for Veronica.

The module is adapted from the VEER dictation flow supplied by the user. It keeps
the feature local and optional: no hosted AI, no API key, and no network-based
speech recognizer is required. In the CLI, dictation mode means subsequent typed
messages are pasted into the active app until dictation is turned off.
"""

from __future__ import annotations

import importlib
import importlib.util
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field


DEFAULT_STOP_WORDS = ("dictation band", "stop dictation", "dictation off", "bas karo")
NEW_LINE_COMMANDS = ("new line", "nai line")
BACKSPACE_COMMANDS = ("backspace", "mita do")
SPACE_COMMANDS = ("space",)
START_COMMANDS = ("dictation on", "dictation mode on", "dictation start", "type mode")
STOP_COMMANDS = ("dictation off", "dictation mode off", "dictation band", "stop dictation")
TYPE_PREFIXES = ("yeh type karo:", "yeh type karo", "type karo:", "type karo", "yeh likho:", "yeh likho")


@dataclass(slots=True)
class AutoTypeResult:
    """Result returned by local auto-type actions."""

    success: bool
    message: str


@dataclass(slots=True)
class DictationController:
    """Manage local dictation state and auto-typing commands."""

    stop_words: tuple[str, ...] = DEFAULT_STOP_WORDS
    active: bool = False
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)

    def start(self) -> str:
        """Start CLI dictation mode.

        The CLI already receives text from the user, so this mode types each
        following CLI message into the currently focused application.
        """
        if self.active:
            return "Dictation pehle se chal raha hai!"
        self.active = True
        return "Dictation mode on! Jo likhoge wo active app mein type ho jayega. 'dictation band' se band karo."

    def stop(self) -> str:
        """Stop dictation mode."""
        self.active = False
        return "Dictation band kar diya."

    def type_once(self, text: str) -> str:
        """Type one piece of text into the active app."""
        cleaned = text.strip()
        if not cleaned:
            return "Kya type karoon?"
        result = type_text(cleaned)
        return f"Type kar diya: '{cleaned}'" if result.success else result.message

    def handle_command(self, command: str) -> str | None:
        """Handle dictation start/stop/type commands, returning None when not matched."""
        normalized = _normalize(command)
        if any(phrase in normalized for phrase in START_COMMANDS):
            return self.start()
        if any(phrase in normalized for phrase in STOP_COMMANDS):
            return self.stop()

        text = _extract_type_once_text(command)
        if text is not None:
            return self.type_once(text)

        if self.active:
            return self.handle_active_text(command)
        return None

    def handle_active_text(self, text: str) -> str:
        """Process text while CLI dictation mode is active."""
        normalized = _normalize(text)
        if any(stop_word in normalized for stop_word in self.stop_words):
            return self.stop()
        if any(command in normalized for command in NEW_LINE_COMMANDS):
            return _press_key("enter", "New line type kar diya.")
        if any(command in normalized for command in BACKSPACE_COMMANDS):
            return _press_key("backspace", "Backspace kar diya.")
        if any(command == normalized for command in SPACE_COMMANDS):
            return _press_key("space", "Space type kar diya.")

        result = type_text(f"{text} ")
        return f"[Dictation]: Typing: {text}" if result.success else result.message

    def start_background(
        self,
        listen: Callable[[], str | None],
        speak: Callable[[str], None] | None = None,
        timeout_seconds: float = 5.0,
    ) -> str:
        """Start background dictation with an injected local listener.

        This preserves the user's previous project design while avoiding a hard
        dependency on any specific voice package. The caller supplies a local
        `listen` function and optional `speak` function.
        """
        if self.active:
            return "Dictation pehle se chal raha hai!"
        self.active = True
        self._thread = threading.Thread(
            target=self._background_loop,
            args=(listen, speak, timeout_seconds),
            daemon=True,
        )
        self._thread.start()
        return "Dictation mode starting..."

    def _background_loop(
        self,
        listen: Callable[[], str | None],
        speak: Callable[[str], None] | None,
        timeout_seconds: float,
    ) -> None:
        if speak is not None:
            speak("Dictation mode on! Jo bologe wo type ho jayega. 'Dictation band' bolne par rukuunga.")
        while self.active:
            text = listen()
            if text is None:
                time.sleep(timeout_seconds)
                continue
            response = self.handle_active_text(text)
            if speak is not None and not self.active:
                speak(response)


def type_text(text: str, paste_delay: float = 0.2) -> AutoTypeResult:
    """Type text into the active app, preferring clipboard paste for Unicode."""
    pyautogui = _optional_module("pyautogui")
    if pyautogui is None:
        return AutoTypeResult(False, "Type nahi ho saka — pyautogui install karo.")

    pyperclip = _optional_module("pyperclip")
    if pyperclip is not None:
        pyperclip.copy(text)
        time.sleep(paste_delay)
        pyautogui.hotkey("ctrl", "v")
        return AutoTypeResult(True, "Typed with clipboard paste.")

    pyautogui.write(text, interval=0.03)
    return AutoTypeResult(True, "Typed with keyboard emulation.")


def _press_key(key: str, success_message: str) -> str:
    pyautogui = _optional_module("pyautogui")
    if pyautogui is None:
        return "Key press nahi ho saka — pyautogui install karo."
    pyautogui.press(key)
    return success_message


def _optional_module(module_name: str):
    if importlib.util.find_spec(module_name) is None:
        return None
    return importlib.import_module(module_name)


def _extract_type_once_text(command: str) -> str | None:
    normalized = _normalize(command)
    for prefix in TYPE_PREFIXES:
        if normalized.startswith(prefix):
            return command[len(prefix) :].strip()
    return None


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())
