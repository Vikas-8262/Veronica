"""WhatsApp automation agent and message watcher for Veronica."""

import importlib
import json
import re
import threading
import time
from pathlib import Path
from .skills import AssistantContext, SkillResult

# Module-level watcher control
_watcher_thread = None
_watcher_active = False
_watcher_lock = threading.Lock()
_watcher_interval = 5.0

MOCK_MESSAGES = [
    {"sender": "Veer", "message": "Kahan ho? Server down hai!"},
    {"sender": "Raj", "message": "Meeting is postponed to 4 PM."},
    {"sender": "Mom", "message": "Call me when you are free."},
    {"sender": "Boss", "message": "Please check the email dispatch report."},
    {"sender": "Google DeepMind", "message": "Your model is running perfectly."}
]

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def _load_messages(data_dir: Path):
    file_path = data_dir / "whatsapp_received.json"
    if not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_messages(data_dir: Path, messages):
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / "whatsapp_received.json"
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=4)
    except Exception:
        pass

def _watcher_loop(data_dir: Path, interval: float = 5.0):
    global _watcher_active
    message_idx = 0
    while True:
        with _watcher_lock:
            if not _watcher_active:
                break
        
        # Simulate incoming message
        msg_template = MOCK_MESSAGES[message_idx % len(MOCK_MESSAGES)]
        message_idx += 1
        
        # Load, append, save
        msgs = _load_messages(data_dir)
        new_msg = {
            "sender": msg_template["sender"],
            "message": msg_template["message"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "read": False
        }
        msgs.append(new_msg)
        _save_messages(data_dir, msgs)
        
        # Sleep checking active flag periodically
        for _ in range(int(interval * 10)):
            with _watcher_lock:
                if not _watcher_active:
                    break
            time.sleep(0.1)

def is_whatsapp_request(message: str) -> bool:
    """Matcher for WhatsApp Integration requests."""
    lowered = message.lower().strip()
    return "whatsapp" in lowered

def handle_whatsapp_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to dispatch or watch WhatsApp messages."""
    global _watcher_thread, _watcher_active, _watcher_interval
    lowered = message.lower().strip()
    
    # 1. Watcher start command
    if "watcher start" in lowered or "start watcher" in lowered or "start whatsapp watcher" in lowered:
        with _watcher_lock:
            if _watcher_active:
                return SkillResult(True, "WhatsApp Watcher is already running in the background.")
            _watcher_active = True
            _watcher_thread = threading.Thread(target=_watcher_loop, args=(context.data_dir, _watcher_interval), daemon=True)
            _watcher_thread.start()
        return SkillResult(True, "✅ WhatsApp Watcher started. I am monitoring incoming messages in the background.")
        
    # 2. Watcher stop command
    elif "watcher stop" in lowered or "stop watcher" in lowered or "stop whatsapp watcher" in lowered:
        with _watcher_lock:
            if not _watcher_active:
                return SkillResult(True, "WhatsApp Watcher is not running.")
            _watcher_active = False
        return SkillResult(True, "🛑 WhatsApp Watcher has been stopped.")
        
    # 3. Watcher status command
    elif "status" in lowered:
        with _watcher_lock:
            active = _watcher_active
        msgs = _load_messages(context.data_dir)
        unread_count = sum(1 for m in msgs if not m.get("read", False))
        status_str = "RUNNING" if active else "STOPPED"
        return SkillResult(True, f"📊 WhatsApp Watcher Status: {status_str}\nTotal Received: {len(msgs)}\nUnread: {unread_count}")
        
    # 4. Read/List messages command
    elif "list" in lowered or "read" in lowered or "check" in lowered:
        msgs = _load_messages(context.data_dir)
        if not msgs:
            return SkillResult(True, "No WhatsApp messages received yet.")
            
        lines = []
        for i, m in enumerate(msgs, start=1):
            unread_indicator = "🔵" if not m.get("read", False) else "⚪"
            lines.append(f"{i}. {unread_indicator} [{m['timestamp']}] {m['sender']}: {m['message']}")
            m["read"] = True
            
        _save_messages(context.data_dir, msgs)
        return SkillResult(True, "📬 WhatsApp Messages:\n" + "\n".join(lines))
        
    # 5. Clear messages command
    elif "clear" in lowered:
        _save_messages(context.data_dir, [])
        return SkillResult(True, "🗑️ All simulated WhatsApp messages have been cleared.")
        
    # 6. Fallback to existing send message command
    elif "send" in lowered:
        pwk = _optional_module("pywhatkit")
        if pwk is None:
            return SkillResult(True, "WhatsApp Agent requires 'pywhatkit'. Run: pip install pywhatkit")
            
        words = lowered.split()
        if "to" not in words:
            return SkillResult(True, "Please specify a phone number with country code. Example: 'send whatsapp to +1234567890 saying hello'")
            
        to_idx = words.index("to")
        if to_idx + 1 >= len(words):
            return SkillResult(True, "Please specify a phone number.")
            
        phone_no = words[to_idx + 1]
        
        if not phone_no.startswith("+"):
            return SkillResult(True, "Please include the country code in the phone number (e.g., +1234567890).")
            
        msg_payload = "Hello from Veronica AI!"
        if "saying" in words:
            idx = message.lower().find("saying")
            if idx != -1:
                msg_payload = message[idx + len("saying"):].strip()
        elif "message" in words:
            idx = message.lower().find("message")
            if idx != -1:
                msg_payload = message[idx + len("message"):].strip()
                msg_payload = msg_payload.replace(phone_no, "").strip()
            
        try:
            pwk.sendwhatmsg_instantly(phone_no, msg_payload, wait_time=15, tab_close=True)
            return SkillResult(True, f"✅ WhatsApp message successfully dispatched to {phone_no}!")
        except Exception as e:
            return SkillResult(True, f"Failed to send WhatsApp message: {e}")

    return SkillResult(False, "Could not understand WhatsApp command.")
