import pytest
import time
from pathlib import Path
from veronica import Assistant, AssistantConfig
from veronica.local_ai import LocalAIBackend
import veronica.whatsapp_agent as wa

def make_assistant(tmp_path: Path) -> Assistant:
    return Assistant(
        AssistantConfig(data_dir=tmp_path),
        ai_backend=LocalAIBackend(),
    )

def test_whatsapp_watcher_lifecycle(tmp_path: Path, monkeypatch) -> None:
    # Set the watcher interval to be very fast for testing (0.1s)
    monkeypatch.setattr(wa, "_watcher_interval", 0.1)
    
    # Mock pywhatkit
    class MockPyWhatKit:
        def __init__(self):
            self.dispatched = []
        def sendwhatmsg_instantly(self, phone_no, message, wait_time=15, tab_close=True):
            self.dispatched.append((phone_no, message))

    mock_pwk = MockPyWhatKit()
    monkeypatch.setattr(wa, "_optional_module", lambda name: mock_pwk if name == "pywhatkit" else None)

    assistant = make_assistant(tmp_path)
    
    # Ensure watcher is stopped initially
    assistant.respond("whatsapp watcher stop")
    
    # Clear any leftover messages
    clear_resp = assistant.respond("clear whatsapp messages")
    assert "cleared" in clear_resp.lower()

    # 1. Check status (STOPPED, 0 messages)
    status_resp = assistant.respond("whatsapp status")
    assert "STOPPED" in status_resp
    assert "Total Received: 0" in status_resp

    # 2. Start watcher
    start_resp = assistant.respond("whatsapp watcher start")
    assert "started" in start_resp.lower()

    # Verify duplicate start response
    duplicate_start_resp = assistant.respond("whatsapp watcher start")
    assert "already running" in duplicate_start_resp.lower()

    # Check status (RUNNING)
    status_resp2 = assistant.respond("whatsapp status")
    assert "RUNNING" in status_resp2

    # 3. Wait a moment to accumulate simulated messages
    time.sleep(0.3)
    
    # Check status should show received messages
    status_resp3 = assistant.respond("whatsapp status")
    assert "Total Received:" in status_resp3
    
    # 4. List / read messages
    list_resp = assistant.respond("list whatsapp messages")
    assert "WhatsApp Messages" in list_resp
    assert "Veer" in list_resp or "Raj" in list_resp
    
    # Verify unread count becomes 0
    status_resp4 = assistant.respond("whatsapp status")
    assert "Unread: 0" in status_resp4

    # 5. Send message fallback
    send_resp = assistant.respond("send whatsapp to +1234567890 saying Hello test")
    assert "successfully dispatched" in send_resp.lower()
    assert len(mock_pwk.dispatched) == 1
    assert mock_pwk.dispatched[0][0] == "+1234567890"
    assert mock_pwk.dispatched[0][1] == "Hello test"

    # Send message with invalid phone number
    send_resp_invalid = assistant.respond("send whatsapp to 1234567890 saying Hello")
    assert "country code" in send_resp_invalid.lower()

    # 6. Stop watcher
    stop_resp = assistant.respond("whatsapp watcher stop")
    assert "stopped" in stop_resp.lower()

    # Verify duplicate stop
    duplicate_stop_resp = assistant.respond("whatsapp watcher stop")
    assert "not running" in duplicate_stop_resp.lower()
