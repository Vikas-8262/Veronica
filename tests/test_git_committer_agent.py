"""Unit tests for the new Git Auto-Committer Agent."""

import os
import unittest
from veronica.assistant import Assistant, AssistantConfig

class TestGitCommitterAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_git_committer_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Ask for git status check
        status_res = self.assistant.respond("git status check")
        safe_print("Git Status Check:", status_res)
        self.assertTrue("Workspace clean" in status_res or "Git Status" in status_res or "not a git repository" in status_res.lower())
        
        # 2. Trigger auto commit (if clean, it will return "Workspace clean")
        commit_res = self.assistant.respond("auto commit")
        safe_print("Commit Result:", commit_res)
        self.assertTrue("Workspace clean" in commit_res or "committed successfully" in commit_res or "not a git repository" in commit_res.lower())

if __name__ == "__main__":
    unittest.main()
