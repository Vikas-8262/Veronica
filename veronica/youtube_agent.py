"""YouTube Player agent for Veronica."""

import importlib
import re
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_youtube_request(message: str) -> bool:
    """Matcher for YouTube Integration requests."""
    lowered = message.lower().strip()
    return "play" in lowered and "youtube" in lowered

def handle_youtube_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to search and play a video on YouTube."""
    pwk = _optional_module("pywhatkit")
    if pwk is None:
        return SkillResult(True, "YouTube Player requires 'pywhatkit'. Run: pip install pywhatkit")

    lowered = message.lower().strip()
    
    # Extract the search term (e.g. "play bohemian rhapsody on youtube" -> "bohemian rhapsody")
    search_term = lowered
    search_term = re.sub(r'play\s+', '', search_term, flags=re.IGNORECASE)
    search_term = re.sub(r'\s*on\s*youtube\s*', '', search_term, flags=re.IGNORECASE)
    search_term = re.sub(r'\s*from\s*youtube\s*', '', search_term, flags=re.IGNORECASE)
    search_term = search_term.strip()
    
    if not search_term:
        return SkillResult(True, "Please specify what you want to play on YouTube. Example: 'play interstellar soundtrack on youtube'")
        
    try:
        # playonyt automatically opens the default browser and plays the first result
        pwk.playonyt(search_term)
        return SkillResult(True, f"▶️ Searching and playing '{search_term}' on YouTube...")
    except Exception as e:
        return SkillResult(True, f"Failed to play on YouTube: {e}")
