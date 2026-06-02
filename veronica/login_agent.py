"""Auto-Login Skill and Credentials Manager for Veronica.

Saves service credentials with base64 obfuscation to a local JSON keychain file
and automates form inputs using pyautogui.
"""

import os
import json
import base64
import time
import threading
import importlib
from pathlib import Path
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def _get_keychain_path(data_dir: Path | None = None) -> Path:
    if data_dir is None:
        data_dir = Path(os.path.expanduser("~")) / ".veronica"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "keychain.json"

def _load_keychain(data_dir: Path | None = None) -> dict:
    path = _get_keychain_path(data_dir)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _save_keychain(keychain: dict, data_dir: Path | None = None):
    path = _get_keychain_path(data_dir)
    try:
        path.write_text(json.dumps(keychain, indent=2), encoding="utf-8")
    except Exception:
        pass

def _obfuscate(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")

def _deobfuscate(obfuscated: str) -> str:
    return base64.b64decode(obfuscated.encode("utf-8")).decode("utf-8")

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_login_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered.startswith("login to ")
        or lowered.startswith("set login credential for ")
        or lowered.startswith("delete login credential for ")
        or lowered in ("list login services", "list logins")
    )

# ──────────────────────────────────────────────
# Typing Automation Worker
# ──────────────────────────────────────────────
def _type_credentials_worker(username: str, password_obf: str, delay: int = 5):
    """Wait for delay, then type username, Tab, type password, and Enter."""
    time.sleep(delay)
    
    pyautogui = _optional_module("pyautogui")
    pyperclip = _optional_module("pyperclip")
    
    if not pyautogui:
        print("   [Auto-Login] pyautogui is not installed.")
        return
        
    password = _deobfuscate(password_obf)
    
    # Type username
    if pyperclip:
        pyperclip.copy(username)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(username, interval=0.02)
        
    time.sleep(0.1)
    pyautogui.press("tab")
    time.sleep(0.1)
    
    # Type password
    if pyperclip:
        pyperclip.copy(password)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(password, interval=0.02)
        
    time.sleep(0.1)
    pyautogui.press("enter")
    print("   [Auto-Login] Typed credentials successfully.")

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_login_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    keychain = _load_keychain(context.data_dir)
    
    # 1. Set login credentials
    if lowered.startswith("set login credential for "):
        body = message[len("set login credential for "):].strip()
        parts = body.split()
        
        if len(parts) < 3:
            return SkillResult(
                True, 
                "Format error. Use: `set login credential for <service> <username> <password>`"
            )
            
        service = parts[0].strip().lower()
        username = parts[1].strip()
        password = " ".join(parts[2:]).strip()
        
        keychain[service] = {
            "username": username,
            "password": _obfuscate(password)
        }
        _save_keychain(keychain, context.data_dir)
        return SkillResult(True, f"🔑 Credentials saved for service: **{service}**.")
        
    # 2. Delete login credentials
    if lowered.startswith("delete login credential for "):
        service = message[len("delete login credential for "):].strip().lower()
        if service not in keychain:
            return SkillResult(True, f"❌ Service '{service}' not found in keychain.")
            
        del keychain[service]
        _save_keychain(keychain, context.data_dir)
        return SkillResult(True, f"🗑️ Credentials for service '{service}' deleted.")
        
    # 3. List login services
    if lowered in ("list login services", "list logins"):
        if not keychain:
            return SkillResult(True, "🔑 Keychain matches zero stored login services.")
            
        services = "\n".join(f"• {s}" for s in sorted(keychain.keys()))
        return SkillResult(True, f"🔑 **Stored Login Services**:\n\n{services}")
        
    # 4. Perform login trigger
    if lowered.startswith("login to "):
        service = message[len("login to "):].strip().lower()
        if service not in keychain:
            return SkillResult(True, f"❌ No saved credentials found for: '{service}'. Use `set login credential for {service} <user> <pass>`.")
            
        cred = keychain[service]
        
        # Start background typing worker thread to prevent assistant block
        t = threading.Thread(
            target=_type_credentials_worker,
            args=(cred["username"], cred["password"]),
            daemon=True
        )
        t.start()
        
        return SkillResult(
            True, 
            f"🔄 Starting auto-login for **{service}**. "
            f"Please focus the target login username field now (countdown: 5 seconds)..."
        )
        
    return SkillResult(False, "")
