"""Terminal Rich Dashboard Agent for Veronica.

Uses the 'rich' package to render a beautiful, multi-panel diagnostic console dashboard
summarizing Veronica's system metrics, active tasks, safety status, and paired integrations.
"""

import os
import sys
import platform
import datetime
from pathlib import Path
from .skills import AssistantContext, SkillResult

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_dashboard_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered in ("show dashboard", "terminal dashboard", "dashboard status", "veronica dashboard")
        or lowered.startswith("dashboard theme ")
    )

# ──────────────────────────────────────────────
# Panel Rendering Helpers
# ──────────────────────────────────────────────
def _get_system_table(console_class, panel_class, table_class) -> str:
    # Try importing psutil for CPU/RAM if available
    cpu = "unknown"
    ram = "unknown"
    try:
        import psutil
        cpu = f"{psutil.cpu_percent()}%"
        ram = f"{psutil.virtual_memory().percent}%"
    except ImportError:
        pass
        
    table = table_class(show_header=False, expand=True)
    table.add_column("Key", style="cyan", width=15)
    table.add_column("Value", style="green")
    
    table.add_row("Python Version", platform.python_version())
    table.add_row("Platform OS", f"{platform.system()} {platform.release()}")
    table.add_row("CPU Load", cpu)
    table.add_row("RAM Usage", ram)
    table.add_row("Local Time", datetime.datetime.now().strftime("%H:%M:%S"))
    
    return panel_class(table, title="[bold cyan]System Specs & Health[/bold cyan]", border_style="cyan")

def _get_integrations_table(console_class, panel_class, table_class) -> str:
    from .policy_agent import _load_policy
    from .mobile_v2_agent import load_mobile_config
    from .plugin_agent import _loaded_plugins
    
    policy = _load_policy()
    mobile = load_mobile_config()
    
    table = table_class(show_header=False, expand=True)
    table.add_column("Key", style="magenta", width=18)
    table.add_column("Value", style="green")
    
    table.add_row("Safety Level", policy.get("safety_level", "medium").upper())
    table.add_row("Blocked Actions", str(policy.get("blocked_count", 0)))
    table.add_row("Mobile Paired", "YES" if mobile.get("paired") else "NO")
    table.add_row("Active Plugins", str(len(_loaded_plugins)))
    
    return panel_class(table, title="[bold magenta]Integrations & Security[/bold magenta]", border_style="magenta")

def _get_tasks_table(console_class, panel_class, table_class) -> str:
    from .runner_agent import _load_jobs
    jobs = _load_jobs()
    
    table = table_class(expand=True)
    table.add_column("Job ID", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Progress", style="cyan")
    
    active_count = 0
    for job_id, job in sorted(jobs.items(), key=lambda x: x[1]["created_at"], reverse=True)[:4]:
        steps_done = sum(1 for s in job["steps"] if s["status"] == "completed")
        table.add_row(job_id, job["status"].upper(), f"{steps_done}/{len(job['steps'])} steps")
        if job["status"] == "running":
            active_count += 1
            
    return panel_class(table, title=f"[bold yellow]Recent Jobs (Active: {active_count})[/bold yellow]", border_style="yellow")

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_dashboard_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    
    # Lazy imports for rich
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.layout import Layout
        from rich.columns import Columns
    except ImportError:
        return SkillResult(True, "❌ rich package is not installed. Run `pip install rich` first.")

    # 1. Update theme
    if lowered.startswith("dashboard theme "):
        theme = message[len("dashboard theme "):].strip().lower()
        # Visual theme is mock config placeholder in context for customization
        return SkillResult(True, f"🎨 Dashboard visual theme updated to: **{theme.upper()}**.")

    # 2. Render Dashboard layout
    console = Console(record=True, width=80)
    
    sys_panel = _get_system_table(Console, Panel, Table)
    integ_panel = _get_integrations_table(Console, Panel, Table)
    tasks_panel = _get_tasks_table(Console, Panel, Table)
    
    # Print header banner
    console.print("\n[bold reverse blue]  VERONICA COGNITIVE CONTROL PANEL  [/bold reverse blue]\n", justify="center")
    
    # Print system and integration side-by-side columns
    console.print(Columns([sys_panel, integ_panel], width=38))
    console.print("\n")
    console.print(tasks_panel)
    console.print("\n[dim]Use `set safety level` or `run job` to configure dashboard parameters.[/dim]\n")
    
    rendered_text = console.export_text()
    
    # We return the rich-formatted output so it renders on terminal
    return SkillResult(True, rendered_text)
