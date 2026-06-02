"""Unit tests for the new API Endpoint Tester."""

import os
import unittest
from veronica.assistant import Assistant, AssistantConfig

class TestApiTesterAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_api_tester_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Test GET request
        get_res = self.assistant.respond("test api: GET https://httpbin.org/get")
        safe_print("GET Result:", get_res)
        self.assertIn("Response Time", get_res)
        self.assertIn("200 OK", get_res)
        
        # 2. Test POST request
        post_res = self.assistant.respond('test api: POST https://httpbin.org/post {"user": "veronica"}')
        safe_print("POST Result:", post_res)
        self.assertIn("Response Time", post_res)
        self.assertIn("200 OK", post_res)
        self.assertIn("veronica", post_res)

if __name__ == "__main__":
    unittest.main()
