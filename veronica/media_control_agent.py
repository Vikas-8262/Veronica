"""System Media and Music Controller Agent for Veronica.

Provides native keyboard simulation for play, pause, track skipping, and volume adjustment.
"""

import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_media_control_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered in ("play music", "pause music", "resume music", "stop music", "playpause music")
        or lowered in ("next track", "next song", "skip song", "skip track")
        or lowered in ("previous track", "previous song", "prev track", "prev song")
        or lowered in ("volume up", "louder", "volume down", "quieter")
        or lowered in ("mute music", "unmute music", "mute", "unmute")
    )

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_media_control_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    pyautogui = _optional_module("pyautogui")
    
    if not pyautogui:
        return SkillResult(True, "❌ Media control fails — pyautogui is not installed.")

    # 1. Play / Pause / Resume
    if lowered in ("play music", "pause music", "resume music", "playpause music", "stop music"):
        pyautogui.press("playpause")
        return SkillResult(True, "🎵 Media play/pause toggled.")

    # 2. Next Track
    if lowered in ("next track", "next song", "skip song", "skip track"):
        pyautogui.press("nexttrack")
        return SkillResult(True, "⏭️ Playing next track.")

    # 3. Previous Track
    if lowered in ("previous track", "previous song", "prev track", "prev song"):
        pyautogui.press("prevtrack")
        return SkillResult(True, "⏮️ Playing previous track.")

    # 4. Volume Up
    if lowered in ("volume up", "louder"):
        # Press twice for a noticeble difference
        pyautogui.press("volumeup")
        pyautogui.press("volumeup")
        return SkillResult(True, "🔊 System volume increased.")

    # 5. Volume Down
    if lowered in ("volume down", "quieter"):
        pyautogui.press("volumedown")
        pyautogui.press("volumedown")
        return SkillResult(True, "🔉 System volume decreased.")

    # 6. Mute / Unmute
    if lowered in ("mute music", "unmute music", "mute", "unmute"):
        pyautogui.press("volumemute")
        return SkillResult(True, "🔇 System mute toggled.")

    return SkillResult(False, "")
