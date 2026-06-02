"""Unit tests for the new Mobile v2 Agent."""

import os
import unittest
from veronica.assistant import Assistant, AssistantConfig

class TestMobileV2Agent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_mobile_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Ask for mobile status
        status_res = self.assistant.respond("mobile status")
        safe_print("Mobile Status:", status_res)
        self.assertIn("Mobile Integration Bridge", status_res)
        
        # 2. Generate pairing pin
        pin_res = self.assistant.respond("generate pairing pin")
        safe_print("Generate PIN:", pin_res)
        self.assertIn("Pairing PIN Generated", pin_res)
        
        # 3. Send mobile alert
        alert_res = self.assistant.respond("send mobile alert: Warning! CPU usage high.")
        safe_print("Send Alert:", alert_res)
        self.assertIn("simulated successfully", alert_res)

if __name__ == "__main__":
    unittest.main()
