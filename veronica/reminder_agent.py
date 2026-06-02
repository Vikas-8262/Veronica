"""Smart Reminders (Background Timers) agent for Veronica."""

import importlib
import threading
import re
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_reminder_request(message: str) -> bool:
    """Matcher for Reminder requests."""
    lowered = message.lower().strip()
    return "remind me in" in lowered or "set a timer for" in lowered

def _trigger_reminder(payload: str):
    """Callback function executed when the timer finishes."""
    print(f"\n\n⏰ [REMINDER ALERT]: {payload}\n\n> ", end="", flush=True)
    
    # Fallback to Windows beep
    winsound = _optional_module("winsound")
    if winsound:
        winsound.Beep(1000, 500)
        winsound.Beep(1000, 500)
        
    # Attempt to speak it out loud
    pyttsx3 = _optional_module("pyttsx3")
    if pyttsx3:
        try:
            engine = pyttsx3.init()
            engine.say(f"Reminder: {payload}")
            engine.runAndWait()
        except Exception:
            pass # ignore threading issues with COM on Windows if any

def handle_reminder_request(message: str, context: AssistantContext) -> SkillResult:
    """Parse time and start a background timer."""
    lowered = message.lower().strip()
    
    # Extract number
    number_match = re.search(r'\b(\d+)\b', lowered)
    if not number_match:
        return SkillResult(True, "Please specify a number for the time (e.g., 'remind me in 5 seconds to ...').")
        
    amount = int(number_match.group(1))
    
    if amount <= 0:
         return SkillResult(True, "Time must be greater than zero.")
         
    # Extract unit
    seconds = 0
    if "second" in lowered:
        seconds = amount
    elif "minute" in lowered:
        seconds = amount * 60
    elif "hour" in lowered:
        seconds = amount * 3600
    else:
        return SkillResult(True, "Please specify 'seconds', 'minutes', or 'hours'.")
        
    # Extract payload
    payload = "Timer is up!"
    if " to " in lowered:
        # split safely finding the last "to" or similar
        idx = lowered.find(" to ")
        if idx != -1:
            # try to preserve original case from message
            orig_idx = message.lower().find(" to ")
            if orig_idx != -1:
                payload = message[orig_idx + 4:].strip()
            
    # Start the background timer
    t = threading.Timer(seconds, _trigger_reminder, args=[payload])
    t.daemon = True # allow program to exit even if timer is running
    t.start()
    
    unit_str = "seconds" if seconds == amount else "minutes" if seconds == amount*60 else "hours"
    return SkillResult(True, f"✅ Timer set for {amount} {unit_str}. I will remind you in the background!")
