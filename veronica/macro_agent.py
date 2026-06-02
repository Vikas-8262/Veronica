"""GUI Macro Recorder & Player Agent for Veronica.

Uses pynput (or pyautogui polling fallback) to record keyboard/mouse actions,
saves them to ~/.veronica/macros/, and replays them via pyautogui.
"""

import os
import json
import time
import threading
from pathlib import Path
from .skills import AssistantContext, SkillResult

def get_macros_dir(data_dir: Path | None = None) -> Path:
    if data_dir is None:
        data_dir = Path(os.path.expanduser("~")) / ".veronica"
    macros_dir = data_dir / "macros"
    macros_dir.mkdir(parents=True, exist_ok=True)
    return macros_dir

_recording_macro = False
_recorded_actions = []
_record_lock = threading.Lock()
_record_start_time = 0.0

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_macro_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered.startswith("record macro ")
        or lowered == "stop recording"
        or lowered.startswith("play macro ")
        or lowered.startswith("run macro ")
        or lowered == "list macros"
        or lowered.startswith("delete macro ")
    )

# ──────────────────────────────────────────────
# Listener Callbacks
# ──────────────────────────────────────────────
def _on_click(x, y, button, pressed):
    global _recording_macro, _recorded_actions
    if not _recording_macro:
        return False  # Stop listener
        
    if pressed:
        delay = time.time() - _record_start_time
        with _record_lock:
            _recorded_actions.append({
                "type": "click",
                "x": x,
                "y": y,
                "button": str(button).split(".")[-1],
                "time": delay
            })

def _on_press(key):
    global _recording_macro, _recorded_actions
    if not _recording_macro:
        return False  # Stop listener
        
    try:
        char = key.char
    except AttributeError:
        char = str(key).split(".")[-1]
        
    delay = time.time() - _record_start_time
    with _record_lock:
        _recorded_actions.append({
            "type": "key",
            "key": char,
            "time": delay
        })

# ──────────────────────────────────────────────
# Recording Thread
# ──────────────────────────────────────────────
def _record_thread_proc():
    pynput = None
    try:
        pynput = importlib.import_module("pynput")
    except ImportError:
        pass
        
    if pynput:
        # Start global mouse and keyboard listeners
        mouse_listener = pynput.mouse.Listener(on_click=_on_click)
        keyboard_listener = pynput.keyboard.Listener(on_press=_on_press)
        mouse_listener.start()
        keyboard_listener.start()
        
        while _recording_macro:
            time.sleep(0.1)
            
        mouse_listener.stop()
        keyboard_listener.stop()
    else:
        # Fallback: simple cursor position logger if pynput is not installed
        pyautogui = None
        try:
            pyautogui = importlib.import_module("pyautogui")
        except ImportError:
            return
            
        print("   [Macro Agent] Fallback active: polling cursor position...")
        last_pos = pyautogui.position()
        while _recording_macro:
            pos = pyautogui.position()
            if pos != last_pos:
                delay = time.time() - _record_start_time
                with _record_lock:
                    _recorded_actions.append({
                        "type": "move",
                        "x": pos[0],
                        "y": pos[1],
                        "time": delay
                    })
                last_pos = pos
            time.sleep(0.1)

# ──────────────────────────────────────────────
# Playback Engine
# ──────────────────────────────────────────────
def _play_macro(macro_actions):
    pyautogui = None
    try:
        pyautogui = importlib.import_module("pyautogui")
    except ImportError:
        return "pyautogui is not installed."
        
    pynput = None
    try:
        pynput = importlib.import_module("pynput")
    except ImportError:
        pass

    pyautogui.PAUSE = 0.05
    start_time = time.time()
    
    for action in macro_actions:
        # Calculate delay
        target_time = start_time + action["time"]
        current_time = time.time()
        if target_time > current_time:
            time.sleep(target_time - current_time)
            
        # Execute action
        a_type = action["type"]
        if a_type == "click":
            pyautogui.click(x=action["x"], y=action["y"], button=action["button"])
        elif a_type == "move":
            pyautogui.moveTo(action["x"], action["y"])
        elif a_type == "key":
            key_val = action["key"]
            if len(key_val) > 1:
                # Special key
                if pynput:
                    pyautogui.press(key_val)
            else:
                pyautogui.write(key_val)

    return "Playback completed."

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
import importlib

def handle_macro_request(message: str, context: AssistantContext) -> SkillResult:
    global _recording_macro, _recorded_actions, _record_start_time
    lowered = message.lower().strip()
    
    # 1. Record Macro
    if lowered.startswith("record macro "):
        if _recording_macro:
            return SkillResult(True, "A macro is already being recorded! Say 'stop recording' first.")
            
        macro_name = message[len("record macro "):].strip()
        if not macro_name:
            return SkillResult(True, "Please provide a name for the macro.")
            
        _recorded_actions = []
        _record_start_time = time.time()
        _recording_macro = True
        
        # Save active name in context temp dict
        context.ensure_data_dir()
        temp_file = context.data_dir / "temp_macro_name.txt"
        temp_file.write_text(macro_name, encoding="utf-8")
        
        # Run background capture thread
        t = threading.Thread(target=_record_thread_proc, daemon=True)
        t.start()
        
        return SkillResult(True, f"🔴 Recording macro '**{macro_name}**'... Perform your actions. Say **'stop recording'** when finished.")

    # 2. Stop Recording
    if lowered == "stop recording":
        if not _recording_macro:
            return SkillResult(True, "No macro is currently being recorded.")
            
        _recording_macro = False
        time.sleep(0.5)  # Wait for listeners to settle
        
        # Load macro name
        temp_file = context.data_dir / "temp_macro_name.txt"
        macro_name = temp_file.read_text(encoding="utf-8").strip() if temp_file.exists() else "unnamed_macro"
        if temp_file.exists():
            temp_file.unlink()
            
        if not _recorded_actions:
            return SkillResult(True, f"⚠️ Stopped recording. No actions were captured for macro '{macro_name}'.")
            
        # Save macro file
        macro_path = get_macros_dir(context.data_dir) / f"{macro_name}.json"
        with open(macro_path, "w", encoding="utf-8") as f:
            json.dump(_recorded_actions, f, indent=2)
            
        return SkillResult(True, f"💾 Macro '**{macro_name}**' saved successfully with {len(_recorded_actions)} action steps.")

    # 3. Play Macro
    play_prefix = "play macro " if lowered.startswith("play macro ") else "run macro "
    if lowered.startswith("play macro ") or lowered.startswith("run macro "):
        macro_name = message[len(play_prefix):].strip()
        macro_path = get_macros_dir(context.data_dir) / f"{macro_name}.json"
        
        if not macro_path.exists():
            return SkillResult(True, f"❌ Macro '{macro_name}' not found.")
            
        try:
            with open(macro_path, "r", encoding="utf-8") as f:
                actions = json.load(f)
        except Exception as e:
            return SkillResult(True, f"❌ Failed to load macro: {e}")
            
        # Spawn thread for playback to avoid blocking Assistant
        t = threading.Thread(target=_play_macro, args=(actions,), daemon=True)
        t.start()
        
        return SkillResult(True, f"▶️ Playing back macro '**{macro_name}**' ({len(actions)} actions) in background...")

    # 4. List Macros
    if lowered == "list macros":
        macros_dir = get_macros_dir(context.data_dir)
        files = list(macros_dir.glob("*.json"))
        if not files:
            return SkillResult(True, "📁 No macros saved yet. Try: 'record macro my_work'")
            
        lines = []
        for file in files:
            lines.append(f"• **{file.stem}**")
        return SkillResult(True, "📁 **Saved GUI Macros**\n" + "\n".join(lines))

    # 5. Delete Macro
    if lowered.startswith("delete macro "):
        macro_name = message[len("delete macro "):].strip()
        macro_path = get_macros_dir() / f"{macro_name}.json"
        
        if not macro_path.exists():
            return SkillResult(True, f"❌ Macro '{macro_name}' not found.")
            
        macro_path.unlink()
        return SkillResult(True, f"🗑️ Deleted macro '**{macro_name}**'.")

    return SkillResult(False, "")
