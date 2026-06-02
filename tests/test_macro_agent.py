"""Unit tests for the new GUI Macro Agent."""

import os
import time
import unittest
from veronica.assistant import Assistant, AssistantConfig
import veronica.macro_agent as macro_agent

class TestMacroAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_macro_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Start recording macro
        record_res = self.assistant.respond("record macro test_recording_flow")
        safe_print("Record result:", record_res)
        self.assertIn("recording", record_res.lower())
        
        # Mock capture actions in headless run environment
        with macro_agent._record_lock:
            macro_agent._recorded_actions.append({
                "type": "click",
                "x": 100,
                "y": 200,
                "button": "left",
                "time": 0.1
            })
            macro_agent._recorded_actions.append({
                "type": "key",
                "key": "a",
                "time": 0.2
            })
            
        time.sleep(0.5)
        
        # 3. Stop recording
        stop_res = self.assistant.respond("stop recording")
        safe_print("Stop result:", stop_res)
        self.assertIn("saved successfully", stop_res.lower())
        
        # 4. Check list macros
        list_res = self.assistant.respond("list macros")
        safe_print("List result:", list_res)
        self.assertIn("test_recording_flow", list_res)
        
        # 5. Playback macro
        play_res = self.assistant.respond("play macro test_recording_flow")
        safe_print("Play result:", play_res)
        self.assertIn("playing", play_res.lower())
        
        # 6. Delete macro
        delete_res = self.assistant.respond("delete macro test_recording_flow")
        safe_print("Delete result:", delete_res)
        self.assertIn("deleted", delete_res.lower())

if __name__ == "__main__":
    unittest.main()
