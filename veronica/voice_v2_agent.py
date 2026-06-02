"""Voice v2 Agent for Veronica.

Provides conversational controls, speech speed adjustments, voice parameters configuration,
and wake word bridge connectivity checks.
"""

import os
import json
import importlib
from pathlib import Path
from .skills import AssistantContext, SkillResult

def get_voice_config_path() -> Path:
    data_dir = Path(os.path.expanduser("~")) / ".veronica"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "voice_config.json"

def load_voice_config() -> dict:
    path = get_voice_config_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "rate": 170,
        "gender": "female"
    }

def save_voice_config(config: dict):
    path = get_voice_config_path()
    try:
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except Exception:
        pass

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_voice_v2_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered in ("voice status", "wake status", "wake word status")
        or lowered.startswith("set voice speed ")
        or lowered.startswith("set voice gender ")
    )

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_voice_v2_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    config = load_voice_config()
    
    if lowered == "voice status" or lowered in ("wake status", "wake word status"):
        # Check local dependencies
        pyttsx3_spec = importlib.util.find_spec("pyttsx3")
        sr_spec = importlib.util.find_spec("speech_recognition")
        pyaudio_spec = importlib.util.find_spec("pyaudio")
        
        status_report = (
            f"🎙️ **Voice System Diagnostics**\n"
            f"───────────────────────────\n"
            f"• Text-to-Speech (pyttsx3)  : {'✅ Ready' if pyttsx3_spec else '❌ Missing'}\n"
            f"• Speech-to-Text (SR Engine): {'✅ Ready' if sr_spec else '❌ Missing'}\n"
            f"• Microphone Driver (PyAudio): {'✅ Ready' if pyaudio_spec else '❌ Missing'}\n"
            f"• Persistent Config Speed  : {config['rate']} WPM\n"
            f"• Configured Voice Gender  : {config['gender'].upper()}\n"
            f"───────────────────────────\n"
            f"Use `set voice speed <slow|normal|fast>` or `set voice gender <male|female>` to configure."
        )
        return SkillResult(True, status_report)
        
    if lowered.startswith("set voice speed "):
        speed = message[len("set voice speed "):].strip().lower()
        rates = {"slow": 130, "normal": 170, "fast": 210}
        
        if speed in rates:
            config["rate"] = rates[speed]
            save_voice_config(config)
            return SkillResult(True, f"🗣️ Voice speed updated to: **{speed.upper()}** ({rates[speed]} WPM).")
        
        # Try raw integer WPM if provided
        try:
            wpm = int(speed)
            if 50 <= wpm <= 400:
                config["rate"] = wpm
                save_voice_config(config)
                return SkillResult(True, f"🗣️ Voice speed rate updated to: **{wpm} WPM**.")
        except ValueError:
            pass
            
        return SkillResult(True, "Invalid speed. Choose: slow (130), normal (170), fast (210) or a custom number (50-400).")
        
    if lowered.startswith("set voice gender "):
        gender = message[len("set voice gender "):].strip().lower()
        if gender in ("male", "female"):
            config["gender"] = gender
            save_voice_config(config)
            return SkillResult(True, f"🗣️ Voice gender updated to: **{gender.upper()}**.")
        return SkillResult(True, "Invalid voice parameter. Choose: male or female.")

    return SkillResult(False, "")
