"""Soundboard Agent for Veronica.

Provides audio alerts and synthesizes cool sound effects using Windows' built-in winsound.
"""

import time
import threading
from .skills import AssistantContext, SkillResult

# Try importing winsound (Windows only)
winsound = None
try:
    import winsound
except ImportError:
    pass

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_soundboard_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered.startswith("play sound:")
        or lowered == "list sounds"
    )

# ──────────────────────────────────────────────
# Audio Synthesis Core
# ──────────────────────────────────────────────
def _play_beeps(sound_name: str):
    if not winsound:
        print("   [Soundboard] winsound is only supported on Windows.")
        return
        
    try:
        if sound_name == "laser":
            # Rapid pitch downward slide
            for freq in range(2000, 400, -80):
                winsound.Beep(freq, 12)
                
        elif sound_name == "success":
            # Major arpeggio upward chord
            winsound.Beep(523, 120)  # C5
            winsound.Beep(659, 120)  # E5
            winsound.Beep(784, 120)  # G5
            winsound.Beep(1046, 250) # C6
            
        elif sound_name == "error":
            # Low alert tone double buzz
            winsound.Beep(180, 250)
            time.sleep(0.05)
            winsound.Beep(180, 250)
            
        elif sound_name == "dramatic":
            # Suspend-like low heavy warning
            winsound.Beep(220, 150)
            winsound.Beep(200, 150)
            winsound.Beep(180, 400)
            
        elif sound_name == "alert":
            # High warning chime
            winsound.Beep(1200, 80)
            winsound.Beep(1500, 150)
            
        else:
            # System alias defaults
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
    except Exception as e:
        print(f"   [Soundboard] Playback error: {e}")

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_soundboard_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    
    if lowered == "list sounds":
        report = (
            f"🔊 **Available Soundboard Alerts**\n"
            f"───────────────────────────\n"
            f"• laser    : Sci-Fi pitch slide down\n"
            f"• success  : Upward arpeggio melody\n"
            f"• error    : Double low buzzer alert\n"
            f"• dramatic : Heavy triple tone alarm\n"
            f"• alert    : Double high warning chime\n"
            f"───────────────────────────\n"
            f"Use `play sound: <name>` to trigger on speakers."
        )
        return SkillResult(True, report)
        
    if lowered.startswith("play sound:"):
        sound_name = message[len("play sound:"):].strip().lower()
        valid_sounds = ("laser", "success", "error", "dramatic", "alert")
        
        # Fire background thread so we don't block Veronica's replies
        t = threading.Thread(target=_play_beeps, args=(sound_name,), daemon=True)
        t.start()
        
        return SkillResult(True, f"🔊 Playing sound effect '**{sound_name}**'...")
        
    return SkillResult(False, "")
