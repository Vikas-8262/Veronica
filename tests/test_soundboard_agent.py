"""Unit tests for the new Soundboard Agent."""

import os
import unittest
from veronica.assistant import Assistant, AssistantConfig

class TestSoundboardAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_soundboard_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Ask to list available sound effects
        list_res = self.assistant.respond("list sounds")
        safe_print("List Sounds Output:", list_res)
        self.assertIn("Available Soundboard Alerts", list_res)
        self.assertIn("laser", list_res)
        
        # 2. Trigger play sound laser
        play_res = self.assistant.respond("play sound: laser")
        safe_print("Play Sound Output:", play_res)
        self.assertIn("laser", play_res.lower())

if __name__ == "__main__":
    unittest.main()
