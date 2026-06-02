"""Unit tests for the new Hybrid AI Router Agent."""

import os
import unittest
from veronica.assistant import Assistant, AssistantConfig

class TestRouterAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_routing_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Check router status initially
        status_res = self.assistant.respond("router status")
        safe_print("Initial Status:", status_res)
        self.assertIn("Hybrid AI Router Status", status_res)
        
        # 2. Set router policy to local
        policy_res = self.assistant.respond("set router policy local")
        safe_print("Policy Update Local:", policy_res)
        self.assertIn("LOCAL", policy_res)
        
        # 3. Request something complex under local policy (should trigger local fallback)
        complex_res = self.assistant.respond("write a complex python script for quantum computing")
        safe_print("Complex Query (Local Policy):", complex_res)
        self.assertIn("local analysis", complex_res.lower())
        
        # 4. Set policy back to auto
        policy_res2 = self.assistant.respond("set router policy auto")
        safe_print("Policy Update Auto:", policy_res2)
        self.assertIn("AUTO", policy_res2)
        
        # 5. Check status again to verify query counter increment
        status_res2 = self.assistant.respond("router status")
        safe_print("Updated Status:", status_res2)
        self.assertIn("Queries Routed Local", status_res2)

if __name__ == "__main__":
    unittest.main()
