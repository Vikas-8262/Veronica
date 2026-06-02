"""Unit tests for the new Safety Policy Engine."""

import os
import re
import unittest
from veronica.assistant import Assistant, AssistantConfig

class TestPolicyAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_policy_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Check current safety status
        status_res = self.assistant.respond("safety status")
        safe_print("Initial Status:", status_res)
        self.assertIn("Safety Policy Engine Status", status_res)
        
        # Parse initial block count
        initial_match = re.search(r"Blocked:\s*(\d+)", status_res)
        initial_count = int(initial_match.group(1)) if initial_match else 0
        safe_print("Initial Blocked Count:", str(initial_count))
        
        # 2. Set safety level to high
        set_res = self.assistant.respond("set safety level high")
        safe_print("Set safety level high:", set_res)
        self.assertIn("HIGH", set_res)
        
        # 3. Request a hazardous command that should be blocked
        blocked_res = self.assistant.respond("run in sandbox: import os; os.system('rm -rf /')")
        safe_print("Dangerous Command Result:", blocked_res)
        self.assertIn("blocked by safety policy", blocked_res.lower())
        
        # 4. Set safety level to low
        set_res2 = self.assistant.respond("set safety level low")
        safe_print("Set safety level low:", set_res2)
        self.assertIn("LOW", set_res2)
        
        # 5. Check status again to verify audit block counter increments
        status_res2 = self.assistant.respond("safety status")
        safe_print("Updated Status:", status_res2)
        
        updated_match = re.search(r"Blocked:\s*(\d+)", status_res2)
        updated_count = int(updated_match.group(1)) if updated_match else 0
        safe_print("Updated Blocked Count:", str(updated_count))
        
        self.assertEqual(updated_count, initial_count + 2)

if __name__ == "__main__":
    unittest.main()
