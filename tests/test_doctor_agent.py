"""Unit tests for the new Observability & Doctor Agent."""

import os
import unittest
from veronica.assistant import Assistant, AssistantConfig

class TestDoctorAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_doctor_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Ask for doctor check
        check_res = self.assistant.respond("doctor check")
        safe_print("Doctor Check Result:", check_res)
        self.assertIn("Diagnostics", check_res)
        
        # 2. Ask for doctor fix suggest
        fix_res = self.assistant.respond("doctor fix pyautogui")
        safe_print("Doctor Fix Result:", fix_res)
        self.assertIn("pip install pyautogui", fix_res)

if __name__ == "__main__":
    unittest.main()
