"""Unit tests for the new Agent Task Runner."""

import os
import time
import unittest
from veronica.assistant import Assistant, AssistantConfig

class TestRunnerAgent(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant(AssistantConfig(name="VeronicaTest", start_reminder_thread=False))
        
    def test_runner_lifecycle(self):
        # Helper to print safely in Windows consoles
        def safe_print(label, val):
            print(f"{label} {val.encode('ascii', errors='replace').decode('ascii')}")

        # 1. Run a background job consisting of two local commands (so it runs fast and offline)
        # Note: the commands are separated by comma
        run_res = self.assistant.respond("run job: time, date")
        safe_print("Run result:", run_res)
        self.assertIn("launched", run_res.lower())
        
        # Extract job id (e.g. from "... job **abcd1234** launched ...")
        # Find double stars and capture the ID
        import re
        match = re.search(r"\*\*([a-f0-9]+)\*\*", run_res)
        self.assertTrue(match is not None, "Job ID not found in launch response")
        job_id = match.group(1)
        safe_print("Extracted Job ID:", job_id)
        
        # 2. Wait up to 5 seconds for the background job to finish
        completed = False
        for _ in range(5):
            time.sleep(1)
            status_res = self.assistant.respond(f"job status {job_id}")
            safe_print("Job status query:", status_res)
            if "COMPLETED" in status_res:
                completed = True
                break
                
        self.assertTrue(completed, "Background job failed to complete in time")
        
        # 3. Check list jobs output
        list_res = self.assistant.respond("list jobs")
        safe_print("List jobs result:", list_res)
        self.assertIn(job_id, list_res)

if __name__ == "__main__":
    unittest.main()
