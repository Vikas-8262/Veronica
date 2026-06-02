"""Unit tests for the new Dynamic Plugin Loader Agent."""

import os
import unittest
from pathlib import Path
from veronica.assistant import Assistant, AssistantConfig
from veronica.plugin_agent import get_plugins_dir

class TestPluginAgent(unittest.TestCase):
    def setUp(self):
        # Locate plugins dir and create a dummy plugin script
        self.plugins_dir = get_plugins_dir()
        self.plugin_file = self.plugins_dir / "temp_test_plugin.py"
        
        # Write dummy plugin code
        self.plugin_file.write_text(
            "PLUGIN_MANIFEST = {\n"
            "    'name': 'temp_test_plugin',\n"
            "    'description': 'A temporary plugin for test purposes',\n"
            "    'version': '1.3'\n"
            "}\n\n"
            "def is_match(message: str) -> bool:\n"
            "    return message.lower().strip() == 'test plugin trigger'\n\n"
            "from veronica.skills import SkillResult\n"
            "def handle(message: str, context) -> SkillResult:\n"
            "    return SkillResult(True, 'Successfully triggered temp plugin!')\n",
            encoding="utf-8"
        )
        
        # Instantiate assistant (which loads plugins at startup)
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def tearDown(self):
        if self.plugin_file.exists():
            self.plugin_file.unlink()
            
    def test_plugin_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Reload plugins so our newly created test plugin is scanned and loaded
        reload_res = self.assistant.respond("reload plugins")
        safe_print("Reload result:", reload_res)
        self.assertIn("reloaded", reload_res.lower())
        
        # 2. Check plugin list
        list_res = self.assistant.respond("list plugins")
        safe_print("List result:", list_res)
        self.assertIn("temp_test_plugin", list_res)
        
        # 3. Test running the custom plugin skill command
        custom_res = self.assistant.respond("test plugin trigger")
        safe_print("Custom command result:", custom_res)
        self.assertIn("triggered temp plugin", custom_res.lower())

if __name__ == "__main__":
    unittest.main()
