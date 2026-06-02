"""Unit tests for the new Terminal Rich Dashboard."""

import os
import unittest
from veronica.assistant import Assistant, AssistantConfig

class TestDashboardAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_dashboard_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Request dashboard status
        dash_res = self.assistant.respond("show dashboard")
        safe_print("Dashboard Layout Output:", dash_res)
        self.assertIn("CONTROL PANEL", dash_res)
        self.assertIn("System Specs", dash_res)
        self.assertIn("Security", dash_res)
        
        # 2. Update theme config
        theme_res = self.assistant.respond("dashboard theme dark")
        safe_print("Theme Update Result:", theme_res)
        self.assertIn("DARK", theme_res)

if __name__ == "__main__":
    unittest.main()
