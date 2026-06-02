"""Autonomous Computer Use agent for Veronica."""

import os
import json
import base64
import importlib
import re
from io import BytesIO
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_computer_request(message: str) -> bool:
    """Matcher for Computer Use requests."""
    lowered = message.lower().strip()
    return any(phrase in lowered for phrase in ("click on", "take over my mouse", "move my mouse"))

def handle_computer_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to locate elements on screen via AI and physically click them."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return SkillResult(True, "Computer Use requires a GEMINI_API_KEY. Please set it in your environment.")

    requests = _optional_module("requests")
    ImageGrab = _optional_module("PIL.ImageGrab")
    pyautogui = _optional_module("pyautogui")
    
    if None in (requests, ImageGrab, pyautogui):
        return SkillResult(True, "Computer Use requires 'requests', 'Pillow', and 'pyautogui'.")
        
    try:
        # Take a screenshot
        screenshot = ImageGrab.grab()
        width, height = screenshot.size
        
        # Convert to RGB and base64
        if screenshot.mode != 'RGB':
            screenshot = screenshot.convert('RGB')
            
        buffer = BytesIO()
        screenshot.save(buffer, format="JPEG", quality=80)
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        # Prepare the Multimodal Payload for Gemini
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        prompt_text = (
            f"You are an autonomous computer agent. I need to: '{message}'. "
            f"My screen resolution is {width}x{height}. "
            "Analyze the screenshot and find the exact X and Y pixel coordinates to click on to accomplish this task. "
            "Return ONLY a valid JSON object in this exact format, with no markdown formatting or other text: "
            '{"x": 500, "y": 300}. If you cannot find the target, return {"x": -1, "y": -1}.'
        )
        
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
        
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()
        
        if "error" in data:
            return SkillResult(True, f"Gemini API Error: {data['error'].get('message', 'Unknown Error')}")
            
        if "candidates" in data and len(data["candidates"]) > 0:
            content = data["candidates"][0].get("content", {})
            parts = content.get("parts", [])
            for part in parts:
                if "text" in part:
                    # Parse the JSON
                    raw_text = part["text"].strip()
                    # Strip possible markdown code blocks
                    raw_text = re.sub(r'```(?:json)?|```', '', raw_text).strip()
                    try:
                        coords = json.loads(raw_text)
                        x, y = coords.get("x", -1), coords.get("y", -1)
                        
                        if x == -1 and y == -1:
                            return SkillResult(True, "I couldn't find the target on your screen.")
                            
                        # Perform the physical action!
                        pyautogui.moveTo(x, y, duration=1.0)
                        pyautogui.click()
                        return SkillResult(True, f"Agent Action: Took control of your mouse and clicked at ({x}, {y}).")
                    except json.JSONDecodeError:
                        return SkillResult(True, f"Failed to parse coordinates from AI response: {raw_text}")
                        
        return SkillResult(True, "Could not extract vision data from the Gemini response.")
        
    except Exception as e:
        return SkillResult(True, f"An error occurred during Computer Use: {e}")
