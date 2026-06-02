import pytest
from pathlib import Path
from veronica import Assistant, AssistantConfig
from veronica.local_ai import LocalAIBackend

def make_assistant(tmp_path: Path) -> Assistant:
    return Assistant(
        AssistantConfig(data_dir=tmp_path),
        ai_backend=LocalAIBackend(),
    )

def test_login_agent_lifecycle(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    
    # 1. List credentials (initially empty)
    list_empty = assistant.respond("list logins")
    assert "matches zero" in list_empty.lower() or "empty" in list_empty.lower()
    
    # 2. Set login credentials
    set_resp = assistant.respond("set login credential for mock_site user_test pass_secret")
    assert "mock_site" in set_resp
    assert "saved" in set_resp.lower()
    
    # 3. List again (now has mock_site)
    list_active = assistant.respond("list login services")
    assert "mock_site" in list_active
    
    # 4. Trigger auto-login
    # Mock pyautogui and time.sleep to run instantly and avoid actual UI focus/typing
    typed_keys = []
    
    class FakePyAutoGUI:
        @staticmethod
        def write(text, interval=0):
            typed_keys.append(text)
            
        @staticmethod
        def press(key):
            typed_keys.append(key)
            
        @staticmethod
        def hotkey(*keys):
            typed_keys.append("+".join(keys))
            
    class FakePyperclip:
        @staticmethod
        def copy(text):
            typed_keys.append(f"copy:{text}")
            
    monkeypatch.setattr("veronica.login_agent._optional_module", lambda name: {
        "pyautogui": FakePyAutoGUI,
        "pyperclip": FakePyperclip
    }.get(name))
    
    # Bypass the thread wait for test execution speed by monkeypatching time.sleep in login_agent
    monkeypatch.setattr("veronica.login_agent.time.sleep", lambda s: None)
    
    login_resp = assistant.respond("login to mock_site")
    assert "starting auto-login" in login_resp.lower()
    assert "mock_site" in login_resp.lower()
    
    # Allow the background thread to run or execute synchronously
    from veronica.login_agent import _type_credentials_worker, _obfuscate
    _type_credentials_worker("user_test", _obfuscate("pass_secret"), delay=0)
    
    assert "copy:user_test" in typed_keys
    assert "tab" in typed_keys
    assert "copy:pass_secret" in typed_keys
    assert "enter" in typed_keys
    
    # 5. Delete credential
    del_resp = assistant.respond("delete login credential for mock_site")
    assert "deleted" in del_resp.lower()
    
    list_after_del = assistant.respond("list logins")
    assert "mock_site" not in list_after_del
