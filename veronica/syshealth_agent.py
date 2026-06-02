"""System Diagnostics & Health agent for Veronica."""

import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_syshealth_request(message: str) -> bool:
    """Matcher for System Health requests."""
    lowered = message.lower().strip()
    if any(phrase in lowered for phrase in ("system health", "disk usage", "computer health")):
        return True
    import re
    return bool(re.search(r"\b(cpu|ram|memory)\b", lowered))

def handle_syshealth_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to check the hardware telemetry of the PC."""
    psutil = _optional_module("psutil")
    if psutil is None:
        return SkillResult(True, "SysHealth Agent requires 'psutil'. Run: pip install psutil")

    try:
        print("🩺 [Reading hardware sensors...]")
        
        # CPU
        # Calling it once might give 0.0, we pass an interval to get an accurate reading over 0.5s
        cpu_usage = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count(logical=True)
        
        # RAM
        ram = psutil.virtual_memory()
        total_ram_gb = ram.total / (1024 ** 3)
        used_ram_gb = ram.used / (1024 ** 3)
        ram_percent = ram.percent
        
        # Disk (Assuming C: drive on Windows, fallback to / on others)
        import os
        drive = "C:\\" if os.name == 'nt' else "/"
        try:
            disk = psutil.disk_usage(drive)
            total_disk_gb = disk.total / (1024 ** 3)
            free_disk_gb = disk.free / (1024 ** 3)
            disk_percent = disk.percent
        except Exception:
            total_disk_gb = free_disk_gb = disk_percent = 0
            
        output = (
            f"🩺 System Hardware Telemetry:\n\n"
            f"💻 CPU ({cpu_count} Threads): {cpu_usage}%\n"
            f"🧠 RAM Usage: {used_ram_gb:.1f} GB / {total_ram_gb:.1f} GB ({ram_percent}%)\n"
            f"💾 Disk Space ({drive}): {free_disk_gb:.1f} GB Free / {total_disk_gb:.1f} GB Total ({disk_percent}% Used)"
        )
        
        return SkillResult(True, output)
        
    except Exception as e:
        return SkillResult(True, f"An unexpected error occurred while reading system sensors: {e}")
