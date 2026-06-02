"""Home Automation IoT Agent for Veronica."""

import os
import re
import json
import importlib
from pathlib import Path
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def _get_devices_file(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "iot_devices.json"

def _load_devices(data_dir: Path) -> list[dict]:
    path = _get_devices_file(data_dir)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    default_devices = [
        {"entity_id": "light.living_room_lights", "name": "Living Room Lights", "state": "off", "type": "light"},
        {"entity_id": "light.bedroom_lights", "name": "Bedroom Lights", "state": "off", "type": "light"},
        {"entity_id": "fan.bedroom_fan", "name": "Bedroom Fan", "state": "off", "type": "fan"},
        {"entity_id": "climate.living_room_thermostat", "name": "Living Room Thermostat", "state": "22", "type": "climate"}
    ]
    _save_devices(data_dir, default_devices)
    return default_devices

def _save_devices(data_dir: Path, devices: list[dict]):
    path = _get_devices_file(data_dir)
    try:
        path.write_text(json.dumps(devices, indent=2), encoding="utf-8")
    except Exception:
        pass

def is_iot_request(message: str) -> bool:
    """Matcher for Home Automation requests."""
    lowered = message.lower().strip()
    return (
        any(lowered.startswith(prefix) for prefix in ("turn on ", "turn off ", "set temperature ", "dim ", "add iot device "))
        or lowered in ("iot status", "list iot devices")
    )

def handle_iot_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to dispatch IoT commands to a local smart home server or emulated database."""
    lowered = message.lower().strip()
    devices = _load_devices(context.data_dir)
    
    # 1. List IoT devices
    if lowered in ("iot status", "list iot devices"):
        if not devices:
            return SkillResult(True, "No IoT devices found.")
        lines = []
        for d in devices:
            state_val = d.get("state", "unknown")
            lines.append(f"• **{d['name']}** (`{d['entity_id']}`): {state_val.upper()}")
        return SkillResult(True, "🏠 **Smart Home Devices Status**\n" + "\n".join(lines))

    # 2. Add IoT device
    if lowered.startswith("add iot device "):
        parts = message[15:].strip().split()
        if len(parts) < 2:
            return SkillResult(True, "Use: add iot device <name> <type>")
        dev_type = parts[-1].lower() if parts[-1].lower() in ("light", "fan", "climate", "switch", "media_player") else "light"
        dev_name = " ".join(parts[:-1]) if parts[-1].lower() == dev_type else " ".join(parts)
        entity_name = dev_name.lower().replace(" ", "_")
        entity_id = f"{dev_type}.{entity_name}"
        
        if any(d["entity_id"] == entity_id for d in devices):
            return SkillResult(True, f"Device with ID '{entity_id}' already exists.")
            
        new_dev = {
            "entity_id": entity_id,
            "name": dev_name.title(),
            "state": "off",
            "type": dev_type
        }
        devices.append(new_dev)
        _save_devices(context.data_dir, devices)
        return SkillResult(True, f"✅ Device added: **{new_dev['name']}** (`{new_dev['entity_id']}`)")

    # 3. Control Action Parsing
    action = "unknown"
    target_name = ""
    value = "on"
    
    if lowered.startswith("turn on "):
        action = "turn_on"
        target_name = lowered[8:].strip()
        value = "on"
    elif lowered.startswith("turn off "):
        action = "turn_off"
        target_name = lowered[9:].strip()
        value = "off"
    elif lowered.startswith("dim "):
        action = "dim"
        target_name = lowered[4:].strip()
        value = "dimmed"
    elif lowered.startswith("set temperature "):
        action = "set_temperature"
        match = re.search(r"\b(\d+)\b", lowered)
        if match:
            value = match.group(1)
        target_name = lowered[16:].strip()
        target_name = re.sub(r"\bof\b|\bto\s+\d+\b", "", target_name).strip()

    target_clean = target_name.replace("the ", "").strip()
    matched_device = None
    for d in devices:
        if (target_clean == d["entity_id"].lower()) or (target_clean == d["name"].lower()) or (target_clean in d["name"].lower()):
            matched_device = d
            break
            
    if not matched_device:
        entity_clean = target_clean.replace(" ", "_")
        domain = "light"
        if "fan" in entity_clean:
            domain = "fan"
        elif "thermostat" in entity_clean or action == "set_temperature":
            domain = "climate"
        elif "tv" in entity_clean or "media" in entity_clean:
            domain = "media_player"
        entity_id = f"{domain}.{entity_clean}"
    else:
        entity_id = matched_device["entity_id"]
        domain = matched_device["type"]
        matched_device["state"] = value
        _save_devices(context.data_dir, devices)

    # Smart Home API
    ha_url = os.getenv("HOME_ASSISTANT_URL", "http://localhost:8123").rstrip("/")
    ha_token = os.getenv("HOME_ASSISTANT_TOKEN", "")
    
    requests = _optional_module("requests")
    if requests and ha_token:
        try:
            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json",
            }
            ha_action = "turn_on" if action == "dim" else action
            url = f"{ha_url}/api/services/{domain}/{ha_action}"
            payload = {"entity_id": entity_id}
            if action == "set_temperature":
                payload["temperature"] = float(value)
            elif action == "dim":
                payload["brightness_pct"] = 50
                
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            response.raise_for_status()
            return SkillResult(True, f"IoT Action successful: {action} applied to {entity_id}.")
        except Exception as e:
            return SkillResult(True, f"Failed to connect to Smart Home API: {e}\n\n*Simulated Fallback*: Executed **{action}** on **{entity_id}** (Value: {value}).")
            
    return SkillResult(True, f"**Simulated IoT Action**\nDevice: `{entity_id}`\nAction: `{action}`\nValue: `{value}`\n\n*(To enable real control, set HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN)*")
