"""Mobile v2 Agent for Veronica.

Handles pairing token generation, mobile webhook alerts, and device connection status.
"""

import os
import json
import random
import time
from pathlib import Path
from .skills import AssistantContext, SkillResult

def get_mobile_config_path() -> Path:
    data_dir = Path(os.path.expanduser("~")) / ".veronica"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "mobile_config.json"

def load_mobile_config() -> dict:
    path = get_mobile_config_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "paired": False,
        "pairing_pin": None,
        "pin_expires": 0.0,
        "device_info": {}
    }

def save_mobile_config(config: dict):
    path = get_mobile_config_path()
    try:
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except Exception:
        pass

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_mobile_v2_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered in ("mobile status", "device status", "generate pairing pin")
        or lowered.startswith("send mobile alert ")
        or lowered.startswith("send mobile alert:")
    )

# ──────────────────────────────────────────────
# Push Alert Client
# ──────────────────────────────────────────────
def send_push_notification(text: str) -> str:
    """Send alert via standard URL Webhook or log it as mock."""
    config = load_mobile_config()
    
    # We can fetch custom webhooks if user specifies them, otherwise log it
    webhook_url = config.get("device_info", {}).get("webhook_url")
    
    print(f"   [Mobile Agent] Sending push notification: '{text}'")
    
    if webhook_url:
        try:
            # Lazy import requests
            import requests
            resp = requests.post(webhook_url, json={"alert": text}, timeout=5)
            if resp.status_code == 200:
                return "Push notification sent successfully."
            else:
                return f"Webhook failed: HTTP {resp.status_code}"
        except Exception as e:
            return f"Failed to call webhook: {e}"
            
    # Mock/simulated success response
    return "Notification simulated successfully (paired device webhook not configured)."

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_mobile_v2_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    config = load_mobile_config()
    
    # 1. Generate Pairing PIN
    if lowered == "generate pairing pin":
        pin = f"{random.randint(100000, 999999)}"
        expires = time.time() + 300.0  # 5 minutes expiry
        
        config["pairing_pin"] = pin
        config["pin_expires"] = expires
        config["paired"] = False
        save_mobile_config(config)
        
        return SkillResult(
            True,
            f"📱 **Pairing PIN Generated**\n"
            f"───────────────────────────\n"
            f"• Enter this PIN on your device: **{pin}**\n"
            f"• This code is valid for 5 minutes.\n"
            f"───────────────────────────"
        )
        
    # 2. Send Mobile Alert
    alert_prefix = "send mobile alert " if lowered.startswith("send mobile alert ") else "send mobile alert:"
    if lowered.startswith(alert_prefix):
        alert_msg = message[len(alert_prefix):].strip()
        if not alert_msg:
            return SkillResult(True, "Please enter the alert message details.")
            
        result = send_push_notification(alert_msg)
        return SkillResult(True, f"🔔 {result}")
        
    # 3. Mobile Status
    if lowered in ("mobile status", "device status"):
        status_char = "✅ Paired" if config["paired"] else "❌ Not Paired"
        device = config["device_info"].get("name", "Unknown Device")
        
        report = (
            f"📱 **Mobile Integration Bridge**\n"
            f"───────────────────────────\n"
            f"• Status: **{status_char}**\n"
            f"• Device Name: {device}\n"
            f"• Last Synced: {config['device_info'].get('last_sync', 'never')}\n"
            f"───────────────────────────\n"
            f"Use `generate pairing pin` to pair a new mobile device."
        )
        return SkillResult(True, report)
        
    return SkillResult(False, "")
