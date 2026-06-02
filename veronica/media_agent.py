"""Media Control agent for Veronica."""

import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_media_request(message: str) -> bool:
    """Matcher for Media Control requests."""
    lowered = message.lower().strip()
    media_phrases = (
        "play music", "pause music", "stop music", "resume music",
        "play the music", "pause the music", 
        "next song", "next track", "skip track", "skip song",
        "previous song", "previous track",
        "volume up", "volume down", "mute", "unmute", "louder", "quieter", "softer"
    )
    return any(phrase in lowered for phrase in media_phrases)

def handle_media_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to control system media keys via pyautogui."""
    pyautogui = _optional_module("pyautogui")
    
    if pyautogui is None:
        return SkillResult(True, "Media Control requires 'pyautogui'. Run: pip install pyautogui")
        
    lowered = message.lower().strip()
    
    try:
        if any(p in lowered for p in ["play", "pause", "stop", "resume"]):
            pyautogui.press("playpause")
            return SkillResult(True, "Toggled media playback.")
            
        elif any(p in lowered for p in ["next", "skip"]):
            pyautogui.press("nexttrack")
            return SkillResult(True, "Skipped to the next track.")
            
        elif "previous" in lowered or "back" in lowered:
            pyautogui.press("prevtrack")
            return SkillResult(True, "Playing the previous track.")
            
        elif "volume up" in lowered or "louder" in lowered:
            # Press multiple times for noticeable difference
            for _ in range(5):
                pyautogui.press("volumeup")
            return SkillResult(True, "Turned the volume up.")
            
        elif "volume down" in lowered or "softer" in lowered or "quieter" in lowered:
            for _ in range(5):
                pyautogui.press("volumedown")
            return SkillResult(True, "Turned the volume down.")
            
        elif "mute" in lowered or "unmute" in lowered:
            pyautogui.press("volumemute")
            return SkillResult(True, "Toggled system mute.")
            
        return SkillResult(True, "I didn't quite catch which media action you wanted.")
        
    except Exception as e:
        return SkillResult(True, f"Failed to control media: {e}")
