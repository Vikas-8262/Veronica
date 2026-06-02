"""Git Auto-Committer Agent for Veronica.

Runs subprocess git calls, analyzes diffs using Gemini to write commit descriptions,
and automates commits and pushes.
"""

import os
import subprocess
import importlib
from .skills import AssistantContext, SkillResult

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_git_committer_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered in ("commit changes", "auto commit", "push updates", "git push", "git status check")
    )

# ──────────────────────────────────────────────
# Subprocess Helper
# ──────────────────────────────────────────────
def _run_git_cmd(args: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout.strip() + "\n" + result.stderr.strip()
    except Exception as e:
        return -1, str(e)

# ──────────────────────────────────────────────
# Gemini Commit Msg Generator
# ──────────────────────────────────────────────
def _generate_commit_message(diff_text: str, api_key: str) -> str:
    requests = importlib.util.find_spec("requests")
    if not requests or not api_key:
        return "Auto-commit updates via Veronica"

    import requests as req
    prompt = f"""You are a professional software engineer. Write a concise, conventional commit message (one line, under 70 chars) describing the changes shown in this git diff.
Do not output any explanation, markdown, or code blocks — output ONLY the raw, single-line commit message.

Git Diff:
{diff_text[:3000]}

Commit Message:"""

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 60}
    }

    try:
        resp = req.post(url, json=payload, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            if "candidates" in data and data["candidates"]:
                parts = data["candidates"][0].get("content", {}).get("parts", [])
                for part in parts:
                    if "text" in part:
                        return part["text"].strip().strip('\'"')
    except Exception:
        pass
    return "Auto-commit updates via Veronica"

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_git_committer_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    # 1. Git Status Check
    if lowered == "git status check":
        code, output = _run_git_cmd(["status", "--short"])
        if code != 0:
            return SkillResult(True, f"❌ Failed to run git status:\n{output}")
        if not output.strip():
            return SkillResult(True, "✅ Workspace clean. No modifications detected.")
        return SkillResult(True, f"📂 **Git Status Output:**\n{output}")

    # 2. Push Updates
    if lowered in ("push updates", "git push"):
        print("   [Git Committer] Pushing changes to remote remote...")
        # Get active branch name
        _, branch = _run_git_cmd(["branch", "--show-current"])
        branch = branch.strip() if branch.strip() else "main"
        
        code, output = _run_git_cmd(["push", "origin", branch])
        if code != 0:
            return SkillResult(True, f"❌ Git Push failed:\n{output}")
        return SkillResult(True, f"🚀 Changes pushed to remote branch **{branch}** successfully!")

    # 3. Auto Commit
    if lowered in ("commit changes", "auto commit"):
        # First check status
        code, status = _run_git_cmd(["status", "--short"])
        if code != 0:
            return SkillResult(True, f"❌ Git command failed. Is this a Git repository?\n{status}")
            
        if not status.strip():
            return SkillResult(True, "✅ Workspace clean. Nothing to commit.")
            
        print("   [Git Committer] Staging modified files...")
        _run_git_cmd(["add", "-A"])
        
        # Get diff details
        _, diff = _run_git_cmd(["diff", "--cached"])
        if not diff.strip():
            return SkillResult(True, "⚠️ Staging failed. No cached diff found.")
            
        # Call Gemini message generator
        print("   [Git Committer] Generating commit message via Gemini...")
        msg = _generate_commit_message(diff, api_key)
        
        # Run commit
        code, output = _run_git_cmd(["commit", "-m", msg])
        if code != 0:
            return SkillResult(True, f"❌ Git commit failed:\n{output}")
            
        return SkillResult(
            True,
            f"💾 **Staged files committed successfully!**\n"
            f"• Commit Message: \"*{msg}*\"\n"
            f"• Use `push updates` to sync with your remote branch."
        )

    return SkillResult(False, "")
