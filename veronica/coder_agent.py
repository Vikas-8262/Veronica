"""Autonomous Code Writing & Execution Agent for Veronica.

Pipeline:
  1. Generate  - Gemini writes a complete Python script
  2. Extract   - Strip markdown fences, validate clean Python
  3. Save      - Write to ~/veronica_scripts/<name>.py
  4. Display   - Print the code to terminal
  5. Execute   - (opt-in) Run via subprocess if user said "run it"
"""

import importlib
import os
import re
import subprocess
import sys
import datetime
from .skills import AssistantContext, SkillResult


def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_coder_request(message: str) -> bool:
    lowered = message.lower().strip()
    return any(phrase in lowered for phrase in (
        "write me a script",
        "write a script",
        "write a python",
        "code a ",
        "create a script",
        "build a script",
        "generate a script",
        "write code that",
        "write code to",
    ))


# ──────────────────────────────────────────────
# Step 1 — Generate
# ──────────────────────────────────────────────
def _generate_code(description: str, api_key: str) -> str:
    """Ask Gemini to write a complete Python script."""
    requests = _optional_module("requests")
    if not requests:
        return ""

    prompt = f"""You are an expert Python developer. Write a complete, production-quality Python script based on this description:

"{description}"

Rules:
- Output ONLY raw Python code — no explanations, no markdown, no prose
- The script must be complete and immediately runnable with no placeholders
- Include all necessary imports at the top
- Add a __main__ guard if appropriate
- Include brief inline comments explaining key logic
- Handle errors gracefully with try/except where appropriate
- Use f-strings for formatting
- Make the code clean, readable, and Pythonic

Output ONLY the Python code, starting with the first import or statement."""

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
        }
    }

    try:
        resp = requests.post(url, json=payload, timeout=60)
        data = resp.json()
        if "candidates" in data and data["candidates"]:
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    return part["text"].strip()
    except Exception as e:
        print(f"   [Gemini error: {e}]")
    return ""


# ──────────────────────────────────────────────
# Step 2 — Extract clean Python
# ──────────────────────────────────────────────
def _extract_code(raw: str) -> str:
    """Strip markdown code fences if present."""
    # Remove ```python ... ``` or ``` ... ```
    raw = re.sub(r"^```(?:python)?\n?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\n?```$", "", raw, flags=re.MULTILINE)
    return raw.strip()


# ──────────────────────────────────────────────
# Step 3 — Save
# ──────────────────────────────────────────────
def _save_script(description: str, code: str) -> str:
    """Save the script to ~/veronica_scripts/ and return the filepath."""
    scripts_dir = os.path.join(os.path.expanduser("~"), "veronica_scripts")
    os.makedirs(scripts_dir, exist_ok=True)

    # Generate a sensible filename from the description
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r'[^\w\s-]', '', description.lower())
    safe_name = re.sub(r'[\s-]+', '_', safe_name).strip('_')[:35]
    filename = f"{safe_name}_{timestamp}.py"
    filepath = os.path.join(scripts_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)

    return filepath


# ──────────────────────────────────────────────
# Step 4 — Display
# ──────────────────────────────────────────────
def _display_code(code: str, filepath: str) -> None:
    """Print the generated code to terminal with visual separators."""
    lines = code.split("\n")
    print(f"\n{'─'*60}")
    print(f"📄 Generated Script ({len(lines)} lines):")
    print(f"{'─'*60}")
    for i, line in enumerate(lines, 1):
        print(f"  {i:>3} │ {line}")
    print(f"{'─'*60}")
    print(f"💾 Saved to: {filepath}\n")


# ──────────────────────────────────────────────
# Step 5 — Execute (opt-in)
# ──────────────────────────────────────────────
def _execute_script(filepath: str) -> str:
    """Run the script in a subprocess and return its output."""
    try:
        result = subprocess.run(
            [sys.executable, filepath],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        errors = result.stderr.strip()

        if result.returncode == 0:
            return f"✅ Execution Output:\n{output}" if output else "✅ Script ran successfully (no output)."
        else:
            return f"⚠️ Script exited with errors:\n{errors}"
    except subprocess.TimeoutExpired:
        return "⏱️ Script timed out after 30 seconds."
    except Exception as e:
        return f"❌ Execution failed: {e}"


# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_coder_request(message: str, context: AssistantContext) -> SkillResult:
    """Orchestrate the full code writing pipeline."""

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return SkillResult(True, "Coder Agent requires a GEMINI_API_KEY environment variable.")

    lowered = message.lower().strip()
    should_run = any(phrase in lowered for phrase in ("and run it", "run it", "and execute", "and run"))

    # Extract the description (strip trigger phrase)
    description = message.strip()
    triggers = [
        "write me a script that ", "write me a script to ",
        "write a script that ", "write a script to ",
        "write a python script that ", "write a python script to ",
        "code a ", "create a script that ", "create a script to ",
        "build a script that ", "build a script to ",
        "generate a script that ", "generate a script to ",
        "write code that ", "write code to ",
    ]
    for trigger in triggers:
        if lowered.startswith(trigger):
            description = message[len(trigger):].strip().strip("?.!")
            break

    if not description or len(description) < 5:
        return SkillResult(True, "Please describe what the script should do (e.g., 'Write me a script that monitors CPU usage').")

    print(f"\n⚡ [CODER AGENT ACTIVATED]")
    print(f"📌 Task: {description}")

    # ── Phase 1: Generate ──
    print("🧠 [Phase 1/4] Asking Gemini to write the code...")
    raw_code = _generate_code(description, api_key)
    if not raw_code:
        return SkillResult(True, "Gemini failed to generate code. Ensure your GEMINI_API_KEY is valid.")

    # ── Phase 2: Extract ──
    print("🔍 [Phase 2/4] Extracting clean Python...")
    clean_code = _extract_code(raw_code)

    # ── Phase 3: Save ──
    print("💾 [Phase 3/4] Saving script to ~/veronica_scripts/...")
    filepath = _save_script(description, clean_code)

    # ── Phase 4: Display ──
    print("📄 [Phase 4/4] Displaying the generated code...")
    _display_code(clean_code, filepath)

    # ── Phase 5 (opt-in): Execute ──
    if should_run:
        print("🚀 [Executing script...]")
        execution_output = _execute_script(filepath)
        return SkillResult(True, (
            f"✅ Script generated and executed!\n"
            f"📁 Saved: {filepath}\n\n"
            f"{execution_output}"
        ))

    return SkillResult(True, (
        f"✅ Script generated and saved!\n"
        f"📁 Location: {filepath}\n\n"
        f"To run it: `python \"{filepath}\"`\n"
        f"Or ask me: \"run it\" to execute it now."
    ))
