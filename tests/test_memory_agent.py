"""Unit tests for the new Semantic Memory Agent."""

import os
import unittest
from veronica.assistant import Assistant, AssistantConfig

class TestMemoryAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_memory_lifecycle(self):
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Clear any existing memories to start fresh
        clear_res = self.assistant.respond("clear all memories")
        safe_print("Clear result:", clear_res)
        self.assertIn("cleared", clear_res.lower())
        
        # 2. Add memories
        resp1 = self.assistant.respond("remember that my secret token is super-secret-12345")
        safe_print("Save result 1:", resp1)
        self.assertIn("stored in memory", resp1.lower())
        
        resp2 = self.assistant.respond("remember that my favorite programming language is Python")
        safe_print("Save result 2:", resp2)
        self.assertIn("stored in memory", resp2.lower())
        
        # 3. Retrieve / Query memories (semantic search)
        query_resp1 = self.assistant.respond("What is my secret token?")
        safe_print("Query 1:", query_resp1)
        self.assertIn("super-secret-12345", query_resp1)
        
        query_resp2 = self.assistant.respond("what do you know about coding language?")
        safe_print("Query 2:", query_resp2)
        self.assertIn("Python", query_resp2)
        
        # 4. List all memories
        list_resp = self.assistant.respond("list all memories")
        safe_print("List result:", list_resp)
        self.assertIn("super-secret-12345", list_resp)
        self.assertIn("Python", list_resp)
        
        # 5. Forget a specific memory
        forget_resp = self.assistant.respond("forget my secret token")
        safe_print("Forget result:", forget_resp)
        self.assertIn("forgotten", forget_resp.lower())
        
        # Query again to verify it is gone
        query_resp3 = self.assistant.respond("What is my secret token?")
        safe_print("Query 3:", query_resp3)
        self.assertNotIn("super-secret-12345", query_resp3)
        
        # Python should still be there
        query_resp4 = self.assistant.respond("What is my favorite programming language?")
        safe_print("Query 4:", query_resp4)
        self.assertIn("Python", query_resp4)

if __name__ == "__main__":
    unittest.main()
