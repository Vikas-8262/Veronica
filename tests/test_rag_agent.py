"""Unit tests for the new Local RAG Agent."""

import os
import unittest
from pathlib import Path
from veronica.assistant import Assistant, AssistantConfig

class TestRagAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        # Create a temp txt file inside tests directory for RAG indexing
        self.temp_dir = Path("tests/temp_rag_test")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.temp_file = self.temp_dir / "about_veronica.txt"
        
        # Write some sample knowledge
        self.temp_file.write_text(
            "Veronica version 3.0 has a special feature called Mega-Intelligence.\n"
            "This feature allows her to solve complex math equations and write code for rocket engines.\n"
            "It was built by team Antigravity in 2026.",
            encoding="utf-8"
        )
        
    def tearDown(self):
        if self.temp_file.exists():
            self.temp_file.unlink()
        if self.temp_dir.exists():
            self.temp_dir.rmdir()
        
    def test_rag_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Index the temp folder
        index_res = self.assistant.respond(f"index folder tests/temp_rag_test")
        safe_print("Index result:", index_res)
        self.assertIn("indexed", index_res.lower())
        self.assertIn("1 files", index_res.lower())
        
        # 2. List indexed files
        list_res = self.assistant.respond("list indexed")
        safe_print("List result:", list_res)
        self.assertIn("about_veronica.txt", list_res.lower())
        
        # 3. Query the RAG agent
        query_res = self.assistant.respond("ask RAG: Who built the Mega-Intelligence feature?")
        safe_print("Query result:", query_res)
        self.assertIn("Antigravity", query_res)

if __name__ == "__main__":
    unittest.main()
