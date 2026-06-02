"""Webcam Vision agent for Veronica."""

import os
import base64
import time
import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_camera_request(message: str) -> bool:
    """Matcher for Camera requests."""
    lowered = message.lower().strip()
    return any(phrase in lowered for phrase in (
        "look at me", "take a picture", "what is in the camera", "use webcam",
        "what do you see in the camera", "describe scene", "webcam scan", "webcam diagnostics"
    ))

def handle_camera_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to take a picture with the webcam and analyze it via Gemini."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return SkillResult(True, "Camera Agent requires a GEMINI_API_KEY. Please set it in your environment.")

    requests = _optional_module("requests")
    cv2 = _optional_module("cv2")
    
    if None in (requests, cv2):
        return SkillResult(True, "Camera Agent requires 'requests' and 'opencv-python'. Run: pip install requests opencv-python")
        
    try:
        # Open default webcam
        print("📸 [Warming up the webcam...]")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            return SkillResult(True, "Failed to open the webcam. Ensure it is connected and not being used by another application.")
            
        # Give the camera a brief moment to adjust light levels
        time.sleep(1.0)
        
        # Capture frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return SkillResult(True, "Failed to grab a frame from the webcam.")
            
        print("⏳ [Sending picture to the neural network...]")
        
        # Convert frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            return SkillResult(True, "Failed to encode the webcam frame.")
            
        img_str = base64.b64encode(buffer).decode("utf-8")
        
        # Prepare the Multimodal Payload for Gemini
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        prompt_text = (
            f"You are an AI assistant analyzing a picture taken from my webcam. "
            f"User request: '{message}'. "
            "Please describe what you see in the image and directly answer the user's request."
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
                    return SkillResult(True, f"📷 Webcam Vision Results:\n\n{part['text'].strip()}")
                        
        return SkillResult(True, "Could not extract vision data from the Gemini response.")
        
    except Exception as e:
        return SkillResult(True, f"An error occurred during Camera Vision: {e}")
