"""Calendar and Event Planner Agent for Veronica.

Provides offline local scheduling and event listing inside calendar.json.
"""

import os
import json
import re
import datetime
from pathlib import Path
from .skills import AssistantContext, SkillResult

def _get_calendar_path(data_dir: Path | None = None) -> Path:
    if data_dir is None:
        data_dir = Path(os.path.expanduser("~")) / ".veronica"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "calendar.json"

def _load_calendar(data_dir: Path | None = None) -> list:
    path = _get_calendar_path(data_dir)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []

def _save_calendar(calendar: list, data_dir: Path | None = None):
    path = _get_calendar_path(data_dir)
    try:
        path.write_text(json.dumps(calendar, indent=2), encoding="utf-8")
    except Exception:
        pass

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_calendar_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered.startswith("schedule event ")
        or lowered.startswith("add event ")
        or lowered in ("show calendar", "show schedule", "clear calendar", "clear schedule", "today's schedule")
        or "agenda for today" in lowered
    )

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_calendar_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    calendar = _load_calendar(context.data_dir)
    
    # 1. Schedule event: schedule/add event <description> on <YYYY-MM-DD> at <HH:MM>
    if lowered.startswith("schedule event ") or lowered.startswith("add event "):
        # Matches: add/schedule event <desc> on <date> at <time>
        pattern = r"(?:schedule|add)\s+event\s+(.+?)\s+on\s+(\d{4}-\d{2}-\d{2})\s+at\s+(\d{2}:\d{2})"
        match = re.search(pattern, message, re.IGNORECASE)
        
        if not match:
            return SkillResult(
                True, 
                "Format error. Use: `schedule event <description> on YYYY-MM-DD at HH:MM`"
            )
            
        description = match.group(1).strip()
        date_str = match.group(2).strip()
        time_str = match.group(3).strip()
        
        # Verify date/time formatting
        try:
            datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            return SkillResult(True, "❌ Invalid date or time format. Please verify calendar parameters.")
            
        calendar.append({
            "description": description,
            "date": date_str,
            "time": time_str
        })
        # Sort calendar chronologically
        calendar.sort(key=lambda x: f"{x['date']} {x['time']}")
        _save_calendar(calendar, context.data_dir)
        
        return SkillResult(
            True, 
            f"📅 Event scheduled successfully!\n"
            f"• **Event**: {description}\n"
            f"• **Date**: {date_str}\n"
            f"• **Time**: {time_str}"
        )
        
    # 2. Clear calendar / schedule
    if lowered in ("clear calendar", "clear schedule"):
        _save_calendar([], context.data_dir)
        return SkillResult(True, "🧹 Calendar cleared successfully. All events deleted.")
        
    # 3. Today's Agenda
    if lowered == "today's schedule" or "agenda for today" in lowered:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        today_events = [e for e in calendar if e["date"] == today_str]
        
        if not today_events:
            return SkillResult(True, f"📅 No events scheduled for today ({today_str}). Enjoy your free day!")
            
        lines = [f"• [{e['time']}] {e['description']}" for e in today_events]
        return SkillResult(True, f"📅 **Agenda for Today ({today_str})**:\n\n" + "\n".join(lines))
        
    # 4. Show calendar / schedule (all upcoming events)
    if lowered in ("show calendar", "show schedule"):
        if not calendar:
            return SkillResult(True, "📅 Your calendar is currently empty.")
            
        # Group by date
        grouped = {}
        for event in calendar:
            grouped.setdefault(event["date"], []).append(event)
            
        lines = []
        for date, events in sorted(grouped.items()):
            lines.append(f"📅 **{date}**:")
            for e in events:
                lines.append(f"  • [{e['time']}] {e['description']}")
            lines.append("")
            
        return SkillResult(True, "📅 **Scheduled Events**:\n\n" + "\n".join(lines).strip())
        
    return SkillResult(False, "")
