"""Live Screen Intelligence Agent for Veronica.

Captures the live screen, sends it to Gemini Vision, and returns
a full AI-powered analysis of what is displayed.

No new dependencies — uses pyautogui (already installed) + Gemini API.
"""

import base64
import importlib
import io
import os
from .skills import AssistantContext, SkillResult


def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_screen_request(message: str) -> bool:
    """Matcher for Screen Intelligence requests."""
    lowered = message.lower().strip()
    return any(phrase in lowered for phrase in (
        "on my screen",
        "on the screen",
        "my screen",
        "what do you see on",
        "look at my screen",
        "read my screen",
        "analyze my screen",
        "what's open",
        "what am i looking at",
    ))


# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_screen_request(message: str, context: AssistantContext) -> SkillResult:
    """Capture the screen and analyze it via Gemini Vision."""

    # ── Dependency check ──
    pyautogui = _optional_module("pyautogui")
    requests  = _optional_module("requests")
    PIL       = _optional_module("PIL")

    if pyautogui is None:
        return SkillResult(True, "Screen Agent requires 'pyautogui'. Run: pip install pyautogui")
    if requests is None:
        return SkillResult(True, "Screen Agent requires 'requests'. Run: pip install requests")

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return SkillResult(True, "Screen Agent requires a GEMINI_API_KEY environment variable.")

    try:
        # ── Phase 1: Capture ──
        print("🖥️  [Capturing screen...]")
        screenshot = pyautogui.screenshot()        # Returns a PIL.Image

        # ── Phase 2: Encode to base64 JPEG ──
        buffer = io.BytesIO()
        screenshot.save(buffer, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # ── Phase 3: Build Gemini Vision prompt ──
        # The user's original question becomes the instruction
        prompt = (
            f"You are an AI assistant with access to a live screenshot of my computer screen.\n"
            f"My request: \"{message}\"\n\n"
            "Please analyze the screenshot and directly answer my request. "
            "Be specific, accurate, and helpful. If you see code, read it. "
            "If you see error messages, explain them. "
            "If you see a document, summarize it. "
            "Be as detailed as the user's question requires."
        )

        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_b64,
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 2048,
            }
        }

        print("🧠 [Sending to Gemini Vision for analysis...]")
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()

        if "error" in data:
            return SkillResult(True, f"Gemini API Error: {data['error'].get('message', 'Unknown Error')}")

        if "candidates" in data and data["candidates"]:
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    return SkillResult(True, f"🖥️ Screen Analysis:\n\n{part['text'].strip()}")

        return SkillResult(True, "Gemini returned no analysis. Please try again.")

    except Exception as e:
        return SkillResult(True, f"Screen Intelligence failed: {e}")
