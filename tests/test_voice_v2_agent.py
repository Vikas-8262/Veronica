"""Unit tests for the new Voice v2 Agent."""

import os
import unittest
from veronica.assistant import Assistant, AssistantConfig

class TestVoiceV2Agent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_voice_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Ask for voice status
        status_res = self.assistant.respond("voice status")
        safe_print("Voice Status:", status_res)
        self.assertIn("Voice System Diagnostics", status_res)
        
        # 2. Set voice speed
        speed_res = self.assistant.respond("set voice speed fast")
        safe_print("Set Voice Speed:", speed_res)
        self.assertIn("FAST", speed_res)
        
        # 3. Set voice gender
        gender_res = self.assistant.respond("set voice gender male")
        safe_print("Set Voice Gender:", gender_res)
        self.assertIn("MALE", gender_res)
        
        # 4. Verify updated status
        status_res2 = self.assistant.respond("voice status")
        safe_print("Updated Voice Status:", status_res2)
        self.assertIn("210 WPM", status_res2)
        self.assertIn("MALE", status_res2)

if __name__ == "__main__":
    unittest.main()
