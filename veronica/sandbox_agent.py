"""Secure sandboxing for Veronica using Docker."""

import subprocess
import tempfile
from pathlib import Path
from .skills import AssistantContext, SkillResult

def is_sandbox_request(message: str) -> bool:
    """Matcher for Sandbox requests."""
    lowered = message.lower().strip()
    return lowered.startswith(("run in sandbox", "safe execute"))

def handle_sandbox_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to execute Python code safely inside a Docker container."""
    lowered = message.lower().strip()
    code = ""
    for prefix in ["run in sandbox:", "run in sandbox ", "safe execute:", "safe execute "]:
        if lowered.startswith(prefix):
            code = message[len(prefix):].strip()
            break
            
    if not code:
        return SkillResult(True, "Please provide the Python code to run in the sandbox. Example: 'run in sandbox: print(\"hello\")'")
        
    try:
        # Check if docker is installed
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return SkillResult(True, "Docker is not installed or not running. Please install Docker Desktop to use the Secure Sandbox.")
        
    from .local_ai import _ai_provider, _gemini_reply, _ollama_reply
    
    max_retries = 3
    attempts = 0
    healing_log = ""
    
    while attempts < max_retries:
        attempts += 1
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
                clean_code = code
                if clean_code.startswith("```python"):
                    clean_code = clean_code[9:]
                elif clean_code.startswith("```"):
                    clean_code = clean_code[3:]
                if clean_code.endswith("```"):
                    clean_code = clean_code[:-3]
                    
                temp_file.write(clean_code.strip())
                temp_path = Path(temp_file.name)
                
            cmd = [
                "docker", "run", "--rm", "--network", "none",
                "-v", f"{temp_path.absolute()}:/app/script.py:ro",
                "python:3.11-alpine",
                "python", "/app/script.py"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
                
            output = result.stdout.strip()
            errors = result.stderr.strip()
            
            if result.returncode == 0 and not errors:
                final_out = healing_log
                if attempts > 1:
                    final_out += f"**[HEALED CODE AFTER {attempts-1} CRASHES]**\\n```python\\n{clean_code.strip()}\\n```\\n\\n"
                final_out += f"Output:\\n```\\n{output or 'Code executed successfully with no output.'}\\n```"
                return SkillResult(True, final_out)
                
            if attempts < max_retries:
                error_snippet = errors.splitlines()[-1] if errors else 'Unknown Crash'
                healing_log += f"*Attempt {attempts} crashed: {error_snippet} - AI fixing...*\\n"
                
                provider = _ai_provider()
                prompt = f"This python code failed to run.\\nCode:\\n```python\\n{clean_code}\\n```\\nError:\\n{errors}\\nReturn ONLY the fixed python code inside a ```python block. Do not add any conversational text or explanations."
                
                ai_response = None
                if provider == "ollama":
                    ai_response = _ollama_reply(prompt)
                elif provider == "gemini":
                    ai_response = _gemini_reply(prompt)
                    
                if ai_response:
                    code = ai_response 
                else:
                    break
            else:
                final_out = healing_log + f"\\n**Final Errors after {attempts} attempts:**\\n```\\n{errors}\\n```"
                if output:
                    final_out += f"\\nOutput:\\n```\\n{output}\\n```"
                return SkillResult(True, final_out)
                
        except subprocess.TimeoutExpired:
            return SkillResult(True, "Execution timed out after 15 seconds (infinite loop protection).")
        except Exception as e:
            return SkillResult(True, f"An error occurred in the sandbox: {str(e)}")
            
    return SkillResult(True, "Could not execute the sandbox code.")
