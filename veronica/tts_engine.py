"""Text-to-Speech (TTS) Engine for Veronica."""

import importlib
import threading
import queue
import re

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

class TTSEngine:
    """A background TTS engine using pyttsx3."""
    
    def __init__(self):
        self.pyttsx3 = _optional_module("pyttsx3")
        self.enabled = self.pyttsx3 is not None
        
        if self.enabled:
            # We use a queue and a dedicated thread for speech because pyttsx3
            # is synchronous and blocks the main thread during speech execution.
            self.speech_queue = queue.Queue()
            self.thread = threading.Thread(target=self._speech_worker, daemon=True)
            self.thread.start()
            
    def _speech_worker(self):
        """Background worker that initializes the engine and processes the queue."""
        try:
            # Initialize in the thread it will run in (Windows SAPI5 requirement)
            engine = self.pyttsx3.init()
            
            # Make the voice sound a bit better if possible (e.g. Zira on Windows)
            voices = engine.getProperty('voices')
            for voice in voices:
                if "Zira" in voice.name or "female" in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
                    
            engine.setProperty('rate', 170) # Slightly faster than default
            
            while True:
                text = self.speech_queue.get()
                if text is None:
                    break
                    
                try:
                    # Dynamically adjust voice configs from file
                    try:
                        from .voice_v2_agent import load_voice_config
                        config = load_voice_config()
                        engine.setProperty('rate', config.get("rate", 170))
                        
                        target_gender = config.get("gender", "female").lower()
                        voices = engine.getProperty('voices')
                        selected_voice = None
                        for voice in voices:
                            v_name = voice.name.lower()
                            if target_gender == "female" and ("zira" in v_name or "female" in v_name or "hazel" in v_name or "haruka" in v_name):
                                selected_voice = voice.id
                                break
                            elif target_gender == "male" and ("david" in v_name or "male" in v_name or "ravi" in v_name or "george" in v_name):
                                selected_voice = voice.id
                                break
                        if selected_voice:
                            engine.setProperty('voice', selected_voice)
                    except Exception:
                        pass

                    engine.say(text)
                    engine.runAndWait()
                except Exception:
                    pass
                finally:
                    self.speech_queue.task_done()
        except Exception:
            pass
                
    def speak(self, text: str) -> None:
        """Adds text to the speech queue to be spoken asynchronously."""
        if not self.enabled or not text:
            return
            
        # Clean up markdown code blocks and syntax before speaking
        clean_text = re.sub(r'```.*?```', ' code snippet ', text, flags=re.DOTALL)
        clean_text = clean_text.replace("*", "").replace("`", "")
        
        # Truncate very long responses so the user doesn't have to listen to an essay
        if len(clean_text) > 400:
            clean_text = clean_text[:400] + "... I have more information, please read the screen for details."
            
        self.speech_queue.put(clean_text)
