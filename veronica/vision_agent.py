"""Multimodal Screen Vision for Veronica."""

import os
import base64
import importlib
from io import BytesIO
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_vision_request(message: str) -> bool:
    """Matcher for Screen Vision requests."""
    lowered = message.lower().strip()
    return any(phrase in lowered for phrase in ("what is on my screen", "look at my screen", "read my screen", "describe my screen"))

def handle_vision_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to take a screenshot and analyze it with Multimodal AI."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return SkillResult(True, "Screen Vision requires a GEMINI_API_KEY. Please set it in your environment.")

    requests = _optional_module("requests")
    ImageGrab = _optional_module("PIL.ImageGrab")
    
    if requests is None or ImageGrab is None:
        return SkillResult(True, "Screen Vision requires 'requests' and 'Pillow'. Run: pip install requests Pillow")
        
    try:
        # Take a screenshot
        screenshot = ImageGrab.grab()
        
        # Convert to RGB if necessary and save to buffer as JPEG
        if screenshot.mode != 'RGB':
            screenshot = screenshot.convert('RGB')
            
        buffer = BytesIO()
        screenshot.save(buffer, format="JPEG", quality=80)
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        # Prepare the Multimodal Payload for Gemini
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        prompt_text = "You are a helpful assistant analyzing a screenshot. " + message
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt_text},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_str
                        }
                    }
                ]
            }]
        }
        
        # Call the API
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()
        
        if "error" in data:
            return SkillResult(True, f"Gemini API Error: {data['error'].get('message', 'Unknown Error')}")
        
        # Extract response
        if "candidates" in data and len(data["candidates"]) > 0:
            content = data["candidates"][0].get("content", {})
            parts = content.get("parts", [])
            for part in parts:
                if "text" in part:
                    return SkillResult(True, part["text"].strip())
                    
        return SkillResult(True, "Could not extract vision data from the Gemini response.")
        
    except Exception as e:
        return SkillResult(True, f"An error occurred during Screen Vision analysis: {e}")
