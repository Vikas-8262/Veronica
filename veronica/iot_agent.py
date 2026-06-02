"""Home Automation IoT Agent for Veronica."""

import os
import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_iot_request(message: str) -> bool:
    """Matcher for Home Automation requests."""
    lowered = message.lower().strip()
    return any(lowered.startswith(prefix) for prefix in ("turn on ", "turn off ", "set temperature ", "dim "))

def handle_iot_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to dispatch IoT commands to a local smart home server (like Home Assistant)."""
    lowered = message.lower().strip()
    
    # Extract action and entity
    action = "unknown"
    entity_str = ""
    
    if lowered.startswith("turn on "):
        action = "turn_on"
        entity_str = lowered[8:].strip()
    elif lowered.startswith("turn off "):
        action = "turn_off"
        entity_str = lowered[9:].strip()
    elif lowered.startswith("dim "):
        action = "dim"
        entity_str = lowered[4:].strip()
    elif lowered.startswith("set temperature "):
        action = "set_temperature"
        entity_str = lowered[16:].strip()
        
    # Clean up entity string (e.g., "the living room lights" -> "living_room_lights")
    entity_clean = entity_str.replace("the ", "").replace(" ", "_").strip()
    
    # Guess domain based on keywords
    domain = "light"
    if "tv" in entity_clean or "television" in entity_clean:
        domain = "media_player"
    elif "fan" in entity_clean:
        domain = "fan"
    elif action == "set_temperature":
        domain = "climate"
        
    entity_id = f"{domain}.{entity_clean}"
    
    # Attempt to hit local Home Assistant API if configured
    ha_url = os.getenv("HOME_ASSISTANT_URL", "http://localhost:8123").rstrip("/")
    ha_token = os.getenv("HOME_ASSISTANT_TOKEN", "")
    
    requests = _optional_module("requests")
    
    if requests and ha_token:
        try:
            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json",
            }
            url = f"{ha_url}/api/services/{domain}/{action}"
            payload = {"entity_id": entity_id}
            
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            response.raise_for_status()
            return SkillResult(True, f"IoT Action successful: {action} applied to {entity_id}.")
        except Exception as e:
            return SkillResult(True, f"Failed to connect to Smart Home API: {e}\n\n*Simulated Fallback*: Executed **{action}** on **{entity_id}**.")
            
    # Fallback simulation if no Token or Requests library
    return SkillResult(True, f"**Simulated IoT Action**\nDevice: `{entity_id}`\nAction: `{action}`\n\n*(To enable real control, set HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN in your environment variables)*")
