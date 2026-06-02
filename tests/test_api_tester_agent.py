"""Unit tests for the new API Endpoint Tester."""

import os
import sys
import unittest
from unittest.mock import MagicMock
from veronica.assistant import Assistant, AssistantConfig

class TestApiTesterAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        self.orig_requests = sys.modules.get("requests")
        
        # Mock requests
        self.mock_requests = MagicMock()
        self.mock_requests.__spec__ = MagicMock()
        
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.reason = "OK"
        mock_get_response.text = '{"headers": {"User-Agent": "Veronica-Assistant-Diagnostic-Client/3.0"}}'
        mock_get_response.json.return_value = {"headers": {"User-Agent": "Veronica-Assistant-Diagnostic-Client/3.0"}}
        mock_get_response.content = b'{"headers": {"User-Agent": "Veronica-Assistant-Diagnostic-Client/3.0"}}'
        
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.reason = "OK"
        mock_post_response.text = '{"json": {"user": "veronica"}}'
        mock_post_response.json.return_value = {"json": {"user": "veronica"}}
        mock_post_response.content = b'{"json": {"user": "veronica"}}'
        
        self.mock_requests.get.return_value = mock_get_response
        self.mock_requests.post.return_value = mock_post_response
        
        sys.modules["requests"] = self.mock_requests

        from unittest.mock import patch
        self.patcher = patch("importlib.util.find_spec")
        self.mock_find_spec = self.patcher.start()
        self.mock_find_spec.return_value = MagicMock()

    def tearDown(self):
        self.patcher.stop()
        if self.orig_requests is not None:
            sys.modules["requests"] = self.orig_requests
        elif "requests" in sys.modules:
            del sys.modules["requests"]
        
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

