"""Voice Input (Speech-to-Text) agent for Veronica."""

import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_voice_request(message: str) -> bool:
    """Matcher for Voice Input requests."""
    lowered = message.lower().strip()
    return lowered in ("listen", "voice mode", "start listening")

def handle_voice_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to activate the microphone and transcribe speech."""
    sr = _optional_module("speech_recognition")
    
    if sr is None:
        return SkillResult(True, "Voice input requires 'SpeechRecognition' and 'PyAudio'. Run: pip install SpeechRecognition PyAudio")
        
    recognizer = sr.Recognizer()
    
    try:
        # Check if PyAudio is working by attempting to use the Microphone
        with sr.Microphone() as source:
            # We print directly since we are blocking the assistant loop
            print("\n🎙️ [Veronica is listening... Speak now!] 🎙️")
            
            # Adjust for ambient noise briefly
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Listen for up to 5 seconds of speech
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
            
            print("⏳ [Processing audio...]")
            
            # Use Google's free web speech API for transcription
            text = recognizer.recognize_google(audio)
            
            return SkillResult(True, f"🗣️ Voice Transcription:\n\"{text}\"\n\n(Tip: You can copy and paste this back to me as a command!)")
            
    except sr.WaitTimeoutError:
        return SkillResult(True, "Listening timed out. I didn't hear anything.")
    except sr.UnknownValueError:
        return SkillResult(True, "I couldn't understand what was said. Please try speaking more clearly.")
    except sr.RequestError as e:
        return SkillResult(True, f"Could not request results from Speech Recognition service; {e}")
    except Exception as e:
        return SkillResult(True, f"Failed to access the microphone. Ensure PyAudio is installed correctly: {e}")
