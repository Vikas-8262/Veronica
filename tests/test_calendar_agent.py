import pytest
import datetime
from pathlib import Path
from veronica import Assistant, AssistantConfig
from veronica.local_ai import LocalAIBackend

def make_assistant(tmp_path: Path) -> Assistant:
    return Assistant(
        AssistantConfig(data_dir=tmp_path),
        ai_backend=LocalAIBackend(),
    )

def test_calendar_agent_lifecycle(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)
    
    # 1. Clear calendar initially
    assistant.respond("clear calendar")
    
    # 2. Show calendar (initially empty)
    show_empty = assistant.respond("show schedule")
    assert "empty" in show_empty.lower()
    
    # 3. Schedule event
    schedule_resp = assistant.respond("schedule event Team Sync on 2026-06-12 at 15:30")
    assert "scheduled successfully" in schedule_resp.lower()
    assert "Team Sync" in schedule_resp
    assert "2026-06-12" in schedule_resp
    assert "15:30" in schedule_resp
    
    # 4. Show calendar (has event)
    show_full = assistant.respond("show calendar")
    assert "Team Sync" in show_full
    assert "2026-06-12" in show_full
    
    # 5. Invalid schedule parameters
    invalid_resp = assistant.respond("schedule event Sync on 2026-15-40 at 25:80")
    assert "invalid date or time format" in invalid_resp.lower()
    
    # 6. Today's agenda (schedule event for today)
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    assistant.respond(f"add event Daily Standup on {today_str} at 09:30")
    
    today_resp = assistant.respond("today's schedule")
    assert "Daily Standup" in today_resp
    assert "09:30" in today_resp
    
    # 7. Clear schedule
    clear_resp = assistant.respond("clear calendar")
    assert "cleared successfully" in clear_resp.lower()
    assert "empty" in assistant.respond("show calendar").lower()
