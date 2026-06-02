"""System OS Control agent for Veronica."""

import os
import platform
import subprocess
from .skills import AssistantContext, SkillResult

def is_os_request(message: str) -> bool:
    """Matcher for OS Control requests."""
    lowered = message.lower().strip()
    return any(lowered.startswith(prefix) for prefix in ("open ", "launch ", "start ")) or "lock pc" in lowered or "sleep pc" in lowered or "lock computer" in lowered

def handle_os_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to launch apps or lock the computer."""
    lowered = message.lower().strip()
    
    try:
        # Check for Lock PC
        if "lock pc" in lowered or "lock my pc" in lowered or "lock computer" in lowered:
            if platform.system() == "Windows":
                os.system("rundll32.exe user32.dll,LockWorkStation")
                return SkillResult(True, "PC Locked. 🔒")
            else:
                return SkillResult(True, "Locking is only supported on Windows currently.")
                
        # Check for Sleep PC
        if "sleep pc" in lowered or "sleep my pc" in lowered or "sleep computer" in lowered:
            if platform.system() == "Windows":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                return SkillResult(True, "Putting PC to sleep. 🌙")
            else:
                return SkillResult(True, "Sleep is only supported on Windows currently.")
                
        # Handle App Launching
        app_name = ""
        for prefix in ["open ", "launch ", "start "]:
            if lowered.startswith(prefix):
                app_name = message[len(prefix):].strip()
                break
                
        if not app_name:
            return SkillResult(True, "Please specify an app to open. Example: 'open notepad'")
            
        # Map common names to executables
        app_map = {
            "notepad": "notepad",
            "calculator": "calc",
            "chrome": "chrome",
            "edge": "msedge",
            "spotify": "spotify",
            "vscode": "code",
            "code": "code",
            "cmd": "cmd",
            "command prompt": "cmd",
            "terminal": "wt",
            "explorer": "explorer",
            "files": "explorer"
        }
        
        exe = app_map.get(app_name.lower(), app_name)
        
        # Launching on Windows
        if platform.system() == "Windows":
            # using 'start' built-in to cmd
            subprocess.Popen(f"start {exe}", shell=True)
            return SkillResult(True, f"Launched {app_name}. 🚀")
        else:
            return SkillResult(True, "App launching is currently optimized for Windows.")
            
    except Exception as e:
        return SkillResult(True, f"Failed to execute OS command: {e}")
