import pytest
from pathlib import Path
from veronica import Assistant, AssistantConfig
from veronica.local_ai import LocalAIBackend

def make_assistant(tmp_path: Path) -> Assistant:
    return Assistant(
        AssistantConfig(data_dir=tmp_path),
        ai_backend=LocalAIBackend(),
    )

def test_media_control_hotkeys(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    
    pressed_keys = []
    
    class FakePyAutoGUI:
        @staticmethod
        def press(key):
            pressed_keys.append(key)
            
    monkeypatch.setattr("veronica.media_control_agent._optional_module", lambda name: FakePyAutoGUI if name == "pyautogui" else None)
    
    # 1. Play / Pause
    resp_play = assistant.respond("play music")
    assert "toggled" in resp_play.lower()
    assert "playpause" in pressed_keys
    
    # 2. Next track
    pressed_keys.clear()
    resp_next = assistant.respond("skip track")
    assert "next" in resp_next.lower()
    assert "nexttrack" in pressed_keys
    
    # 3. Volume Up
    pressed_keys.clear()
    resp_vol = assistant.respond("volume up")
    assert "increased" in resp_vol.lower()
    assert pressed_keys == ["volumeup", "volumeup"]
    
    # 4. Mute
    pressed_keys.clear()
    resp_mute = assistant.respond("mute")
    assert "mute" in resp_mute.lower()
    assert "volumemute" in pressed_keys
