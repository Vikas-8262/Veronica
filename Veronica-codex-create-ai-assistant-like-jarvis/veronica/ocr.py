"""Optional screen OCR support for Veronica.

This module adapts the user-provided VEER Screen OCR flow. OCR is local and
optional: install Tesseract plus Python helpers, then set `TESSERACT_CMD` if the
binary is not on PATH.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import time
from pathlib import Path
from typing import Any

DEFAULT_OCR_LANGUAGES = "eng+hin"
MAX_OCR_WORDS = 100
OCR_COMMAND_WORDS = (
    "screen padho",
    "screen read",
    "kya likha hai screen pe",
)
OCR_COPY_WORDS = (
    "screen copy",
    "copy screen",
    "copy karo screen",
    "clipboard mein daalo",
)
OCR_AREA_WORDS = (
    "area padho",
    "select karke padho",
)


def handle_ocr_command(command: str) -> str | None:
    """Return an OCR response for a supported command, otherwise None."""
    action = _ocr_action(command)
    if action == "read":
        return read_screen()
    if action == "copy":
        return copy_screen_text()
    if action == "area":
        return read_selected_area()
    return None


def is_ocr_command(command: str) -> bool:
    """Return True when a message looks like a screen OCR request."""
    return _ocr_action(command) is not None


def _ocr_action(command: str) -> str | None:
    normalized = _normalize(command)
    if any(phrase in normalized for phrase in OCR_COMMAND_WORDS):
        return "read"
    if any(phrase in normalized for phrase in OCR_COPY_WORDS):
        return "copy"
    if any(phrase in normalized for phrase in OCR_AREA_WORDS):
        return "area"
    return None


def read_screen(region: tuple[int, int, int, int] | None = None) -> str:
    """Capture the screen and read text from it with local Tesseract OCR."""
    ready_message = _check_ocr_ready()
    if ready_message is not None:
        return ready_message

    pyautogui = _optional_module("pyautogui")
    pytesseract = _optional_module("pytesseract")
    if pyautogui is None or pytesseract is None:
        return "Screen OCR ke liye pyautogui aur pytesseract install karo."

    _configure_tesseract(pytesseract)
    try:
        screenshot = pyautogui.screenshot(region=region) if region else pyautogui.screenshot()
        text = _extract_text_from_image(pytesseract, screenshot)
    except FileNotFoundError:
        return _missing_tesseract_message()
    except Exception as exc:  # pragma: no cover - defensive third-party boundary
        return f"OCR error: {exc}"

    if not text:
        return "Screen pe koi readable text nahi mila."
    return f"Screen pe yeh likha hai: {_limit_words(text)}"


def read_selected_area(delay_seconds: float = 3.0) -> str:
    """Wait briefly so the user can focus/select an area, then OCR the screen."""
    time.sleep(delay_seconds)
    return read_screen()


def copy_screen_text() -> str:
    """Copy OCR text from the current screen to the local clipboard."""
    ready_message = _check_ocr_ready(require_clipboard=True)
    if ready_message is not None:
        return ready_message

    pyautogui = _optional_module("pyautogui")
    pyperclip = _optional_module("pyperclip")
    pytesseract = _optional_module("pytesseract")
    if pyautogui is None or pyperclip is None or pytesseract is None:
        return "Screen copy ke liye pyautogui, pyperclip, aur pytesseract install karo."

    _configure_tesseract(pytesseract)
    try:
        screenshot = pyautogui.screenshot()
        text = _extract_text_from_image(pytesseract, screenshot)
    except FileNotFoundError:
        return _missing_tesseract_message()
    except Exception as exc:  # pragma: no cover - defensive third-party boundary
        return f"Copy error: {exc}"

    if not text:
        return "Koi text nahi mila screen pe."
    pyperclip.copy(text)
    return f"Screen text clipboard mein copy kar diya! ({len(text.split())} words)"


def read_image_file(path: str | Path) -> str:
    """Read text from an image file using local Tesseract OCR."""
    image_path = Path(path)
    if not image_path.exists():
        return f"File nahi mili: {image_path}"

    ready_message = _check_ocr_ready(require_pyautogui=False)
    if ready_message is not None:
        return ready_message

    image_module = _optional_module("PIL.Image")
    pytesseract = _optional_module("pytesseract")
    if image_module is None or pytesseract is None:
        return "Image OCR ke liye pillow aur pytesseract install karo."

    _configure_tesseract(pytesseract)
    try:
        image = image_module.open(image_path)
        text = _extract_text_from_image(pytesseract, image)
    except FileNotFoundError:
        return _missing_tesseract_message()
    except Exception as exc:  # pragma: no cover - defensive third-party boundary
        return f"Image read error: {exc}"
    return text if text else "Image mein koi text nahi mila."


def _check_ocr_ready(require_pyautogui: bool = True, require_clipboard: bool = False) -> str | None:
    missing = []
    if _optional_module("pytesseract") is None:
        missing.append("pytesseract")
    if _optional_module("PIL.Image") is None:
        missing.append("pillow")
    if require_pyautogui and _optional_module("pyautogui") is None:
        missing.append("pyautogui")
    if require_clipboard and _optional_module("pyperclip") is None:
        missing.append("pyperclip")
    if missing:
        return f"Screen OCR ke liye install karo: pip install {' '.join(missing)}"
    return None


def _configure_tesseract(pytesseract: Any) -> None:
    tesseract_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def _extract_text_from_image(pytesseract: Any, image: Any) -> str:
    return pytesseract.image_to_string(image, lang=DEFAULT_OCR_LANGUAGES).strip()


def _limit_words(text: str, max_words: int = MAX_OCR_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "... aur bhi hai."


def _missing_tesseract_message() -> str:
    return "Tesseract nahi mila. Install karo aur zarurat ho to TESSERACT_CMD set karo."


def _optional_module(module_name: str):
    top_level = module_name.split(".", 1)[0]
    if importlib.util.find_spec(top_level) is None:
        return None
    if importlib.util.find_spec(module_name) is None:
        return None
    return importlib.import_module(module_name)


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())
