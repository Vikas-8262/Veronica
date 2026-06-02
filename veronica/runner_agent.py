"""Agent Task Runner for Veronica.

Decomposes a multi-step user request into individual commands and executes them
sequentially in a background thread. Supports retries, checkpoints, status reports,
and cancellations.
"""

import os
import json
import uuid
import time
import threading
from pathlib import Path
from .skills import AssistantContext, SkillResult

# Persistence path for background jobs: ~/.veronica/jobs.json
def _get_jobs_file() -> Path:
    data_dir = Path(os.path.expanduser("~")) / ".veronica"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "jobs.json"

def _load_jobs() -> dict:
    path = _get_jobs_file()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _save_jobs(jobs: dict):
    path = _get_jobs_file()
    try:
        path.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    except Exception:
        pass

# Lock for editing jobs store safely across threads
_jobs_lock = threading.Lock()

# Thread mapping to support canceling running threads
_active_threads = {}

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_runner_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered.startswith("run job:")
        or lowered.startswith("run task:")
        or lowered == "list jobs"
        or lowered == "list tasks"
        or lowered.startswith("job status ")
        or lowered.startswith("task status ")
        or lowered.startswith("cancel job ")
        or lowered.startswith("cancel task ")
        or lowered.startswith("retry job ")
        or lowered.startswith("retry task ")
    )

# ──────────────────────────────────────────────
# Background Worker Function
# ──────────────────────────────────────────────
def _job_worker(job_id: str, commands: list[str]):
    from .assistant import Assistant, AssistantConfig

    # Instantiate assistant dynamically to prevent circular imports
    assistant = Assistant(AssistantConfig(name="VeronicaJobRunner", start_reminder_thread=False))
    
    for idx, cmd in enumerate(commands):
        # Check cancellation
        with _jobs_lock:
            jobs = _load_jobs()
            job = jobs.get(job_id)
            if not job or job["status"] == "cancelled":
                return
            
            # Update current running index
            job["status"] = "running"
            job["current_step"] = idx
            job["steps"][idx]["status"] = "running"
            job["steps"][idx]["started_at"] = time.time()
            _save_jobs(jobs)

        # Execute step with retries
        success = False
        response = ""
        max_retries = 3
        
        for attempt in range(1, max_retries + 1):
            # Check cancel in-between retries
            with _jobs_lock:
                jobs = _load_jobs()
                if jobs.get(job_id, {}).get("status") == "cancelled":
                    return

            try:
                print(f"   [Task Runner] Job {job_id} | Step {idx+1}/{len(commands)} | Attempt {attempt}/{max_retries}: Running '{cmd}'")
                response = assistant.respond(cmd)
                
                # Check for apparent failures in the response (e.g. error words, exceptions)
                lowered_resp = response.lower()
                if "error" in lowered_resp or "failed" in lowered_resp or "exception" in lowered_resp:
                    raise Exception(response)
                    
                success = True
                break
            except Exception as e:
                response = f"Attempt {attempt} failed: {e}"
                time.sleep(1)

        # Update step status
        with _jobs_lock:
            jobs = _load_jobs()
            job = jobs.get(job_id)
            if not job:
                return
                
            step = job["steps"][idx]
            step["ended_at"] = time.time()
            step["attempts"] = attempt
            step["output"] = response
            
            if success:
                step["status"] = "completed"
            else:
                step["status"] = "failed"
                job["status"] = "failed"
                _save_jobs(jobs)
                break # Stop entire pipeline on step failure
            
            _save_jobs(jobs)

    # Wrap up job status
    with _jobs_lock:
        jobs = _load_jobs()
        job = jobs.get(job_id)
        if job and job["status"] == "running":
            job["status"] = "completed"
            _save_jobs(jobs)
            
    # Cleanup thread mapping
    _active_threads.pop(job_id, None)

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_runner_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    
    # 1. Run Job
    if lowered.startswith("run job:") or lowered.startswith("run task:"):
        prefix = "run job:" if lowered.startswith("run job:") else "run task:"
        raw_commands = message[len(prefix):].strip()
        
        # Split on commas (avoiding commas inside parentheses if possible)
        commands = [c.strip() for c in raw_commands.split(",") if c.strip()]
        if not commands:
            return SkillResult(True, "Please provide at least one command. (e.g. 'run job: time, date')")
            
        job_id = str(uuid.uuid4())[:8]
        
        # Initialize job metadata
        job_info = {
            "id": job_id,
            "status": "pending",
            "created_at": time.time(),
            "current_step": 0,
            "steps": [{"command": cmd, "status": "pending", "output": ""} for cmd in commands]
        }
        
        with _jobs_lock:
            jobs = _load_jobs()
            jobs[job_id] = job_info
            _save_jobs(jobs)
            
        # Spawn background execution thread
        t = threading.Thread(target=_job_worker, args=(job_id, commands), daemon=True)
        _active_threads[job_id] = t
        t.start()
        
        return SkillResult(True, f"🚀 Background job **{job_id}** launched with {len(commands)} steps.\nCheck status with: `job status {job_id}`.")

    # 2. List Jobs
    if lowered in ("list jobs", "list tasks"):
        with _jobs_lock:
            jobs = _load_jobs()
            
        if not jobs:
            return SkillResult(True, "No background jobs have been created yet.")
            
        lines = []
        # Sort by creation time descending
        for job_id, job in sorted(jobs.items(), key=lambda x: x[1]["created_at"], reverse=True)[:10]:
            steps_done = sum(1 for s in job["steps"] if s["status"] == "completed")
            lines.append(f"• **{job_id}**: {job['status'].upper()} ({steps_done}/{len(job['steps'])} steps completed)")
            
        return SkillResult(True, "⚙️ **Recent Background Jobs**\n" + "\n".join(lines))

    # Helper to parse ID
    def parse_id(cmd_prefix):
        return message[len(cmd_prefix):].strip()

    # 3. Job Status
    status_prefixes = ["job status ", "task status "]
    for prefix in status_prefixes:
        if lowered.startswith(prefix):
            job_id = parse_id(prefix)
            with _jobs_lock:
                jobs = _load_jobs()
            job = jobs.get(job_id)
            if not job:
                return SkillResult(True, f"Job '{job_id}' not found.")
                
            lines = [
                f"⚙️ **Job Details: {job_id}**",
                f"───────────────────────────",
                f"• Status: **{job['status'].upper()}**",
                f"• Steps:"
            ]
            for idx, step in enumerate(job["steps"]):
                status_char = "⏳" if step["status"] == "pending" else "🔄" if step["status"] == "running" else "✅" if step["status"] == "completed" else "❌"
                lines.append(f"  {idx+1}. {status_char} `{step['command']}` — {step['status'].upper()}")
                if step.get("output"):
                    # Display first line of output or snippet
                    snippet = step["output"].split("\n")[0][:60]
                    lines.append(f"     └─ output: \"{snippet}...\"")
                    
            lines.append("───────────────────────────")
            return SkillResult(True, "\n".join(lines))

    # 4. Cancel Job
    cancel_prefixes = ["cancel job ", "cancel task "]
    for prefix in cancel_prefixes:
        if lowered.startswith(prefix):
            job_id = parse_id(prefix)
            with _jobs_lock:
                jobs = _load_jobs()
                job = jobs.get(job_id)
                if not job:
                    return SkillResult(True, f"Job '{job_id}' not found.")
                
                if job["status"] in ("completed", "failed", "cancelled"):
                    return SkillResult(True, f"Job '{job_id}' is already finished ({job['status']}).")
                    
                job["status"] = "cancelled"
                for step in job["steps"]:
                    if step["status"] in ("pending", "running"):
                        step["status"] = "cancelled"
                _save_jobs(jobs)
                
            return SkillResult(True, f"🛑 Cancelled active background job **{job_id}**.")

    # 5. Retry Job
    retry_prefixes = ["retry job ", "retry task "]
    for prefix in retry_prefixes:
        if lowered.startswith(prefix):
            job_id = parse_id(prefix)
            with _jobs_lock:
                jobs = _load_jobs()
                job = jobs.get(job_id)
                if not job:
                    return SkillResult(True, f"Job '{job_id}' not found.")
                
                if job["status"] != "failed":
                    return SkillResult(True, f"Only failed jobs can be retried. Current status: {job['status']}")
                
                # Reset failed status to pending
                job["status"] = "pending"
                commands = []
                for step in job["steps"]:
                    if step["status"] in ("failed", "pending", "cancelled"):
                        step["status"] = "pending"
                        step["output"] = ""
                    commands.append(step["command"])
                _save_jobs(jobs)
                
            t = threading.Thread(target=_job_worker, args=(job_id, commands), daemon=True)
            _active_threads[job_id] = t
            t.start()
            return SkillResult(True, f"🔄 Retrying failed background job **{job_id}**.")

    return SkillResult(False, "")
