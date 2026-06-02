"""Unit tests for the new Desktop Memory & RAG Viewer Agent."""

import os
import unittest
from veronica.assistant import Assistant, AssistantConfig

class TestGuiViewerAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_gui_viewer_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Ask to spawn database inspector
        spawn_res = self.assistant.respond("open database inspector")
        safe_print("Spawn result:", spawn_res)
        self.assertIn("spawning", spawn_res.lower())
        self.assertIn("desktop database inspector", spawn_res.lower())

if __name__ == "__main__":
    unittest.main()
