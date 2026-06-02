import datetime as dt

import pytest
from pathlib import Path

from veronica import Assistant, AssistantConfig
from veronica.local_ai import LocalAIBackend


def make_assistant(tmp_path: Path) -> Assistant:
    return Assistant(
        AssistantConfig(data_dir=tmp_path),
        ai_backend=LocalAIBackend(),
    )


def test_calculator_skill(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    assert assistant.respond("calculate 42 * (8 + 2)") == "The answer is 420."


def test_notes_skill_persists_notes(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    assert assistant.respond("remember buy batteries") == "Noted: buy batteries"
    assert "buy batteries" in assistant.respond("show notes")


def test_local_ai_identity_without_external_api(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    response = assistant.respond("who are you")

    assert "fully local" in response
    assert "API" not in response


def test_local_ai_synthesizes_unknown_prompt(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    response = assistant.respond("design a new suit")

    assert "local" in response.lower()
    assert "hosted model" not in response.lower()


def test_type_once_command_uses_dictation_controller(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    typed: list[str] = []

    def fake_type_text(text: str):
        from veronica.dictation import AutoTypeResult

        typed.append(text)
        return AutoTypeResult(True, "typed")

    monkeypatch.setattr("veronica.dictation.type_text", fake_type_text)

    response = assistant.respond("yeh type karo: namaste duniya")

    assert response == "Type kar diya: 'namaste duniya'"
    assert typed == ["namaste duniya"]


def test_cli_dictation_mode_types_following_messages(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    typed: list[str] = []

    def fake_type_text(text: str):
        from veronica.dictation import AutoTypeResult

        typed.append(text)
        return AutoTypeResult(True, "typed")

    monkeypatch.setattr("veronica.dictation.type_text", fake_type_text)

    assert "Dictation mode on" in assistant.respond("dictation mode on")
    assert assistant.respond("hello active window") == "[Dictation]: Typing: hello active window"
    assert assistant.respond("dictation band") == "Dictation band kar diya."
    assert typed == ["hello active window "]


def test_news_command_reports_missing_key_without_hardcoded_secret(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.delenv("NEWS_API_KEY", raising=False)

    response = assistant.respond("technology news")

    assert "NEWS_API_KEY" in response
    assert "6d0d" not in response


def test_news_headline_formatting_uses_optional_provider(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.setenv("NEWS_API_KEY", "test-key")

    class FakeResponse:
        def json(self):
            return {
                "status": "ok",
                "articles": [
                    {"title": "India launches local assistant - Example"},
                    {"title": "[Removed]"},
                    {"title": "AI research expands across India - Example"},
                ],
            }

    class FakeRequests:
        class exceptions:
            class ConnectionError(Exception):
                pass

            class Timeout(Exception):
                pass

        @staticmethod
        def get(url: str, timeout: int):
            assert "apiKey=test-key" in url
            assert timeout == 8
            return FakeResponse()

    monkeypatch.setattr("veronica.news._optional_module", lambda module_name: FakeRequests)
    response = assistant.respond("tech headlines")

    assert response == (
        "Yeh hain aaj ki top technology news: "
        "1. India launches local assistant ... 2. AI research expands across India"
    )


def test_category_words_do_not_steal_general_local_ai_prompts(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.delenv("NEWS_API_KEY", raising=False)

    response = assistant.respond("make a business plan")

    assert "NEWS_API_KEY" not in response
    assert "Local plan" in response


def test_ocr_command_reports_missing_dependencies(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.setattr("veronica.ocr._optional_module", lambda module_name: None)

    response = assistant.respond("screen padho")

    assert "Screen OCR ke liye install karo" in response
    assert "TESSERACT_PATH" not in response


def test_ocr_screen_read_uses_local_modules(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)

    class FakePyAutoGUI:
        @staticmethod
        def screenshot(region=None):
            assert region is None
            return "fake-screen-image"

    class FakeTesseractInner:
        tesseract_cmd = ""

    class FakePyTesseract:
        pytesseract = FakeTesseractInner()

        @staticmethod
        def image_to_string(image, lang: str):
            assert image == "fake-screen-image"
            assert lang == "eng+hin"
            return "Hello screen namaste duniya"

    class FakeImage:
        pass

    modules = {
        "pyautogui": FakePyAutoGUI,
        "pytesseract": FakePyTesseract,
        "PIL.Image": FakeImage,
    }
    monkeypatch.setenv("TESSERACT_CMD", "/usr/bin/tesseract")
    monkeypatch.setattr("veronica.ocr._optional_module", lambda module_name: modules.get(module_name))

    response = assistant.respond("screen read")

    assert response == "Screen pe yeh likha hai: Hello screen namaste duniya"
    assert FakePyTesseract.pytesseract.tesseract_cmd == "/usr/bin/tesseract"


def test_ocr_copy_screen_text_uses_clipboard(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    copied: list[str] = []

    class FakePyAutoGUI:
        @staticmethod
        def screenshot(region=None):
            return "fake-screen-image"

    class FakePyperclip:
        @staticmethod
        def copy(text: str):
            copied.append(text)

    class FakeTesseractInner:
        tesseract_cmd = ""

    class FakePyTesseract:
        pytesseract = FakeTesseractInner()

        @staticmethod
        def image_to_string(image, lang: str):
            return "copy this screen text"

    class FakeImage:
        pass

    modules = {
        "pyautogui": FakePyAutoGUI,
        "pyperclip": FakePyperclip,
        "pytesseract": FakePyTesseract,
        "PIL.Image": FakeImage,
    }
    monkeypatch.setattr("veronica.ocr._optional_module", lambda module_name: modules.get(module_name))

    response = assistant.respond("copy karo screen")

    assert response == "Screen text clipboard mein copy kar diya! (4 words)"
    assert copied == ["copy this screen text"]


def test_system_stats_reports_missing_psutil(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.setattr("veronica.system_stats._optional_module", lambda module_name: None)

    response = assistant.respond("battery status")

    assert "requirements-system.txt" in response


def test_system_stats_full_report_uses_optional_psutil(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)

    class FakeBattery:
        percent = 18
        power_plugged = False
        secsleft = 3_600

    class FakeFrequency:
        current = 2400

    class FakeMemory:
        total = 16 * 1024**3
        used = 10 * 1024**3
        available = 6 * 1024**3
        percent = 62

    class FakeDisk:
        total = 512 * 1024**3
        used = 400 * 1024**3
        free = 112 * 1024**3
        percent = 78

    class FakePsutil:
        @staticmethod
        def sensors_battery():
            return FakeBattery()

        @staticmethod
        def cpu_percent(interval=1):
            assert interval == 1
            return 55

        @staticmethod
        def cpu_count(logical=True):
            return 8 if logical else 4

        @staticmethod
        def cpu_freq():
            return FakeFrequency()

        @staticmethod
        def virtual_memory():
            return FakeMemory()

        @staticmethod
        def disk_usage(path):
            assert path
            return FakeDisk()

    monkeypatch.setattr("veronica.system_stats._optional_module", lambda module_name: FakePsutil)

    response = assistant.respond("system report")

    assert "Battery 18% hai" in response
    assert "Charger lagao" in response
    assert "CPU 55% use ho raha hai" in response
    assert "RAM: 10 GB use" in response
    assert "Disk" in response


def test_system_stats_temperature_and_running_apps(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)

    class FakeTemperature:
        current = 82

    class FakeProcess:
        def __init__(self, name: str, cpu_percent: float) -> None:
            self.info = {"name": name, "cpu_percent": cpu_percent, "memory_percent": 1.0}

    class FakePsutil:
        @staticmethod
        def sensors_temperatures():
            return {"coretemp": [FakeTemperature()]}

        @staticmethod
        def process_iter(attrs):
            assert attrs == ["name", "cpu_percent", "memory_percent"]
            return [FakeProcess("editor", 3.5), FakeProcess("browser", 1.0)]

    monkeypatch.setattr("veronica.system_stats._optional_module", lambda module_name: FakePsutil)

    assert assistant.respond("temperature") == "CPU temperature 82°C hai — Laptop garam ho raha hai!"
    assert assistant.respond("running apps") == "Heavy apps chal rahi hain: editor"


def test_core_router_google_and_youtube_search(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    opened: list[str] = []
    monkeypatch.setattr("veronica.core_commands.webbrowser.open", opened.append)

    assert assistant.respond("google local ai") == "'local ai' Google par search kar diya!"
    assert assistant.respond("youtube lo fi song") == "YouTube par 'lo fi song' dhund diya!"
    assert opened == [
        "https://www.google.com/search?q=local+ai",
        "https://www.youtube.com/results?search_query=lo+fi+song",
    ]


def test_core_router_weather_uses_environment_key(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.setenv("WEATHER_API_KEY", "weather-test-key")

    class FakeResponse:
        def json(self):
            return {
                "main": {"temp": 28.4, "humidity": 61},
                "weather": [{"description": "clear sky"}],
            }

    class FakeRequests:
        class exceptions:
            class ConnectionError(Exception):
                pass

            class Timeout(Exception):
                pass

        @staticmethod
        def get(url: str, params: dict[str, str], timeout: int):
            assert params["appid"] == "weather-test-key"
            assert params["q"] == "mumbai"
            assert timeout == 5
            return FakeResponse()

    monkeypatch.setattr("veronica.core_commands._optional_module", lambda module_name: FakeRequests)

    assert assistant.respond("weather in Mumbai") == "mumbai mein 28°C hai, clear sky. Humidity 61%."


def test_core_router_weather_reports_missing_key(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.delenv("WEATHER_API_KEY", raising=False)

    response = assistant.respond("mausam")

    assert "WEATHER_API_KEY" in response
    assert "0ab13" not in response


def test_core_router_screenshot_uses_data_dir(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    screenshots: list[str] = []

    class FakePyAutoGUI:
        @staticmethod
        def screenshot(path: str):
            screenshots.append(path)

    monkeypatch.setattr("veronica.core_commands._optional_module", lambda module_name: FakePyAutoGUI)

    response = assistant.respond("screenshot")

    assert response.startswith("Screenshot liya: ss_")
    assert screenshots
    assert str(tmp_path / "screenshots") in screenshots[0]


def test_core_router_power_commands_are_disabled_by_default(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.delenv("VERONICA_ENABLE_POWER_COMMANDS", raising=False)

    response = assistant.respond("shutdown laptop")

    assert "Power commands disabled" in response


def test_core_router_open_app_uses_allow_list(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    launched: list[list[str]] = []

    class FakePopen:
        def __init__(self, command):
            launched.append(command)

    monkeypatch.setattr("veronica.core_commands.subprocess.Popen", FakePopen)

    response = assistant.respond("open chrome")

    assert response == "Chrome khol diya!"
    assert launched == [["chrome"]]


def test_timed_reminder_parses_minutes_and_persists_json(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    response = assistant.respond("10 minute baad remind karo meeting hai")
    listed = assistant.respond("show reminders")

    assert response.startswith("Reminder set!")
    assert "meeting hai" in response
    assert "meeting hai" in listed
    assert (tmp_path / "reminders.json").exists()


def test_timed_reminder_parses_clock_time(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    response = assistant.respond("remind me to call Sam at 18:00")

    assert "18:00" in response
    assert "call Sam" in response


def test_reminder_manager_marks_due_reminders_done(tmp_path: Path) -> None:
    from veronica.reminders import ReminderManager

    spoken: list[str] = []
    manager = ReminderManager(tmp_path, speaker=spoken.append)
    manager.save_reminders(
        [
            {
                "message": "drink water",
                "time": "09:00",
                "trigger_at": "2026-05-09T09:00",
                "done": False,
            }
        ]
    )

    notifications = manager.run_pending(now=dt.datetime(2026, 5, 9, 9, 1))

    assert notifications == ["Yaad dilana tha — drink water"]
    assert spoken == ["Yaad dilana tha — drink water"]
    assert manager.load_reminders()[0]["done"] is True


def test_fun_joke_coin_dice_and_quiz_commands(tmp_path: Path, monkeypatch) -> None:
    from veronica.fun import JOKES

    assistant = make_assistant(tmp_path)

    class FakeRandom:
        def choice(self, values):
            return values[0]

        def randint(self, start: int, end: int) -> int:
            assert (start, end) == (1, 6)
            return 4

    assistant.context.fun.randomizer = FakeRandom()

    assert assistant.respond("joke sunao") == JOKES[0]
    assert assistant.respond("coin uchhalo") == "Coin uchhala... Heads! Aage"
    assert assistant.respond("dice daalo") == "Dice daala... 4 aaya!"
    assert assistant.respond("quiz khelo").startswith("Quiz time!")


def test_fun_productivity_report_counts_commands(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    assistant.respond("joke sunao")
    response = assistant.respond("aaj ka report")

    assert "Aaj tumne Veronica se 2 commands liye" in response
    assert (tmp_path / "productivity.json").exists()


def test_fun_focus_mode_start_and_stop(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    timers: list[object] = []

    class FakeTimer:
        daemon = False

        def __init__(self, seconds, callback, args=()):
            self.seconds = seconds
            self.callback = callback
            self.args = args
            timers.append(self)

        def start(self):
            return None

        def cancel(self):
            return None

    monkeypatch.setattr("veronica.fun.threading.Timer", FakeTimer)

    started = assistant.respond("focus mode on 5 minute")
    stopped = assistant.respond("focus mode off")

    assert "Focus mode on! 5 minute" in started
    assert timers[0].seconds == 300
    assert "Focus mode band!" in stopped


def test_fun_focus_mode_does_not_close_apps_without_env(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.delenv("VERONICA_FOCUS_CLOSE_APPS", raising=False)
    calls: list[list[str]] = []

    class FakeTimer:
        daemon = False

        def __init__(self, seconds, callback, args=()):
            pass

        def start(self):
            return None

        def cancel(self):
            return None

    monkeypatch.setattr("veronica.fun.threading.Timer", FakeTimer)
    monkeypatch.setattr("veronica.fun.subprocess.run", lambda command, capture_output, check: calls.append(command))

    assistant.respond("focus mode on")

    assert calls == []


def test_gui_greeting_parts() -> None:
    from veronica.gui import _greeting_parts

    greeting, time_text, date_text = _greeting_parts(dt.datetime(2026, 5, 9, 6, 30))

    assert greeting == "Good Morning"
    assert time_text == "06:30 AM"
    assert date_text == "Saturday, 09 May"


def test_gui_tray_reports_missing_optional_dependencies(monkeypatch) -> None:
    from veronica.gui import run_tray_icon

    monkeypatch.setattr("veronica.gui._optional_module", lambda module_name: None)

    response = run_tray_icon(lambda command: None, lambda: None)

    assert "requirements-gui.txt" in response


def test_gui_launch_starts_popup_and_tray_threads(monkeypatch) -> None:
    from veronica.gui import launch_gui

    started: list[dict[str, object]] = []

    class FakeThread:
        def __init__(self, target, args=(), kwargs=None, daemon=False):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}
            self.daemon = daemon

        def start(self):
            started.append({"target": self.target.__name__, "args": self.args, "kwargs": self.kwargs, "daemon": self.daemon})

    monkeypatch.setattr("veronica.gui.threading.Thread", FakeThread)

    threads = launch_gui(lambda command: None, lambda: None, assistant_name="Veronica", greeting_message="Ready")

    assert len(threads) == 2
    assert started[0]["target"] == "show_greeting_popup"
    assert started[0]["kwargs"] == {"message": "Ready", "assistant_name": "Veronica"}
    assert started[1]["target"] == "run_tray_icon"
    assert started[1]["daemon"] is True


def test_mobile_status_and_snapshot(tmp_path: Path, monkeypatch) -> None:
    from veronica.mobile import mobile_status, security_snapshot

    monkeypatch.setattr("veronica.mobile.get_local_ip", lambda: "192.168.1.10")
    intruders = tmp_path / "logs" / "intruders"
    intruders.mkdir(parents=True)
    (intruders / "old.jpg").write_text("old", encoding="utf-8")
    (intruders / "new.jpg").write_text("new", encoding="utf-8")
    (intruders / "note.txt").write_text("skip", encoding="utf-8")

    assert mobile_status("Veronica") == {"status": "online", "name": "Veronica", "ip": "192.168.1.10"}
    snapshot = security_snapshot(tmp_path)
    assert snapshot["latest"] in {"old.jpg", "new.jpg"}
    assert snapshot["count"] == 2


def test_mobile_server_reports_missing_flask(tmp_path: Path, monkeypatch) -> None:
    from veronica.mobile import run_mobile_server

    assistant = make_assistant(tmp_path)
    monkeypatch.setattr("veronica.mobile._optional_module", lambda module_name: None)

    response = run_mobile_server(assistant)

    assert "requirements-mobile.txt" in response


def test_mobile_flask_app_routes_when_flask_available(tmp_path: Path) -> None:
    from veronica.mobile import create_mobile_app

    flask = pytest.importorskip("flask")
    assistant = make_assistant(tmp_path)
    app = create_mobile_app(assistant, flask_module=flask)
    assert app is not None
    client = app.test_client()

    index_response = client.get("/")
    command_response = client.post("/command", json={"command": "calculate 2 + 3"})
    empty_response = client.post("/command", json={"command": ""})

    assert index_response.status_code == 200
    assert b"Veronica" in index_response.data
    assert command_response.get_json() == {"response": "The answer is 5."}
    assert empty_response.get_json() == {"response": "Command empty hai."}


def test_security_reports_missing_dependencies(tmp_path: Path, monkeypatch) -> None:
    from veronica.security import SecurityShield

    shield = SecurityShield(tmp_path)
    monkeypatch.setattr("veronica.security._optional_module", lambda module_name: None)

    assert "requirements-security.txt" in shield.register_face()
    assert "requirements-security.txt" in shield.start_security()


def test_security_capture_intruder_uses_data_dir(tmp_path: Path) -> None:
    from veronica.security import SecurityShield

    written: list[tuple[str, object]] = []

    class FakeCv2:
        @staticmethod
        def imwrite(path: str, frame: object) -> bool:
            written.append((path, frame))
            return True

    shield = SecurityShield(tmp_path)
    path = shield.capture_intruder("frame", cv2_module=FakeCv2)

    assert path.parent == tmp_path / "logs" / "intruders"
    assert path.name.startswith("intruder_")
    assert written == [(str(path), "frame")]


def test_security_whatsapp_alert_requires_configured_number(tmp_path: Path, monkeypatch) -> None:
    from veronica.security import SecurityShield

    monkeypatch.delenv("SECURITY_WHATSAPP_NUMBER", raising=False)
    monkeypatch.delenv("WHATSAPP_NUMBER", raising=False)
    shield = SecurityShield(tmp_path)

    response = shield.send_whatsapp_alert(tmp_path / "intruder.jpg")

    assert "SECURITY_WHATSAPP_NUMBER" in response
    assert "+91" not in response


def test_security_start_requires_registered_face(tmp_path: Path, monkeypatch) -> None:
    from veronica.security import SecurityShield

    class FakeModule:
        pass

    shield = SecurityShield(tmp_path)
    monkeypatch.setattr("veronica.security._optional_module", lambda module_name: FakeModule)

    assert shield.start_security() == "Koi registered face nahi! Pehle register face chalao."


def test_speech_uses_edge_tts_and_pygame(monkeypatch) -> None:
    from veronica import speech

    events: list[tuple[str, object]] = []

    class FakeCommunicate:
        def __init__(self, text: str, voice: str, rate: str, volume: str):
            events.append(("communicate", (text, voice, rate, volume)))

        async def save(self, path: str):
            events.append(("save", path.endswith(".mp3")))
            Path(path).write_bytes(b"mp3")

    class FakeEdgeTTS:
        Communicate = FakeCommunicate

    class FakeMusic:
        busy = True

        @staticmethod
        def load(path: str):
            events.append(("load", Path(path).exists()))

        @staticmethod
        def play():
            events.append(("play", True))

        @classmethod
        def get_busy(cls):
            was_busy = cls.busy
            cls.busy = False
            return was_busy

        @staticmethod
        def unload():
            events.append(("unload", True))

    class FakeMixer:
        music = FakeMusic
        initialized = False

        @classmethod
        def get_init(cls):
            return cls.initialized

        @classmethod
        def init(cls):
            cls.initialized = True
            events.append(("init", True))

    class FakePygame:
        mixer = FakeMixer

    monkeypatch.setattr(speech, "_optional_module", lambda module_name: {"edge_tts": FakeEdgeTTS, "pygame": FakePygame}.get(module_name))

    speech.speak("Radhe Radhe")

    assert events[0] == ("communicate", ("Radhe Radhe", "hi-IN-MadhurNeural", "+10%", "+0%"))
    assert ("init", True) in events
    assert ("play", True) in events
    assert ("unload", True) in events


def test_speech_falls_back_to_pyttsx3(monkeypatch) -> None:
    from veronica import speech

    spoken: list[str] = []

    class FakeEngine:
        def say(self, text: str):
            spoken.append(text)

        def runAndWait(self):
            spoken.append("done")

    class FakePyttsx3:
        @staticmethod
        def init():
            return FakeEngine()

    def fake_optional_module(module_name: str):
        if module_name == "pyttsx3":
            return FakePyttsx3
        return None

    monkeypatch.setattr(speech, "_optional_module", fake_optional_module)

    speech.speak("fallback voice")

    assert spoken == ["fallback voice", "done"]


def test_speech_greeting_text_is_veer_style() -> None:
    from veronica.speech import greeting_text

    message = greeting_text(user_name="Vikas", assistant_name="VEER", now=dt.datetime(2026, 5, 9, 6, 30))

    assert message == "Radhe Radhe Vikas! Aaj Saturday hai, time hai 06:30 AM. Main VEER hoon — aapki seva mein hazir hoon!"


def test_startup_builds_vbs_shortcut_script(tmp_path: Path, monkeypatch) -> None:
    from veronica.startup import StartupShortcutConfig, build_shortcut_vbs

    config = StartupShortcutConfig(
        shortcut_name="VEER",
        module_name="veronica",
        pythonw_path=tmp_path / "pythonw.exe",
        working_directory=tmp_path,
        arguments=("--gui", "--reminders", "--speak"),
        startup_dir=tmp_path / "Startup",
    )

    script = build_shortcut_vbs(config)

    assert 'sLinkFile = "' in script
    assert str(tmp_path / "Startup" / "VEER.lnk") in script
    assert f'oLink.TargetPath = "{tmp_path / "pythonw.exe"}"' in script
    assert 'oLink.Arguments = "-m veronica --gui --reminders --speak"' in script
    assert f'oLink.WorkingDirectory = "{tmp_path}"' in script
    assert "oLink.WindowStyle = 7" in script
    assert "oLink.Save" in script


def test_startup_installer_reports_non_windows(monkeypatch) -> None:
    from veronica import startup

    monkeypatch.setattr(startup, "is_windows", lambda: False)

    assert startup.install_windows_startup_shortcut() == "Windows startup shortcut sirf Windows par ban sakta hai."


def test_startup_installer_runs_cscript_and_removes_temp_file(tmp_path: Path, monkeypatch) -> None:
    from veronica import startup

    calls: list[list[str]] = []

    def fake_run(command, check, capture_output, text):
        calls.append(command)
        assert check is True
        assert capture_output is True
        assert text is True

    monkeypatch.setattr(startup, "is_windows", lambda: True)
    monkeypatch.setattr(startup.subprocess, "run", fake_run)
    config = startup.StartupShortcutConfig(
        shortcut_name="Veronica",
        pythonw_path=tmp_path / "pythonw.exe",
        working_directory=tmp_path,
        startup_dir=tmp_path / "Startup",
    )

    response = startup.install_windows_startup_shortcut(config)

    assert "Veronica ab Windows startup mein add ho gaya" in response
    assert calls and calls[0][:2] == ["cscript", "//nologo"]
    assert not Path(calls[0][2]).exists()


def test_cli_startup_args_capture_remaining_flags(monkeypatch) -> None:
    from veronica.__main__ import parse_args

    monkeypatch.setattr(
        "sys.argv",
        ["veronica", "--add-startup", "--startup-args", "--gui", "--reminders", "--speak"],
    )

    args = parse_args()

    assert args.add_startup is True
    assert args.startup_args == ["--gui", "--reminders", "--speak"]


def test_windows_full_installer_points_to_veronica_files() -> None:
    script = Path("scripts/install_windows_full.bat").read_text(encoding="utf-8")

    assert "requirements-all.txt" in script
    assert "python -m veronica" in script
    assert "scripts\\add_to_startup.bat" in script
    assert "veer.py" not in script.lower()
    assert "brain\\modules" not in script.lower()
    assert "ollama pull" not in script.lower()


def test_requirements_all_includes_optional_feature_dependencies() -> None:
    requirements = Path("requirements-all.txt").read_text(encoding="utf-8")

    for package_name in (
        "edge-tts",
        "pygame",
        "pyttsx3",
        "requests",
        "pywhatkit",
        "flask",
        "opencv-python",
        "face-recognition",
        "pystray",
        "psutil",
        "pyautogui",
        "pyperclip",
        "pytesseract",
    ):
        assert package_name in requirements


def test_veer_style_guide_uses_veronica_paths() -> None:
    guide = Path("docs/VERONICA_V3_GUIDE.md").read_text(encoding="utf-8")

    assert "python -m veronica" in guide
    assert "scripts\\start_veronica.bat" in guide
    assert "WEATHER_API_KEY" in guide
    assert "NEWS_API_KEY" in guide
    assert "TESSERACT_CMD" in guide
    assert "No Ollama" in guide
    assert "brain\\commands.py" not in guide
    assert "brain\\modules\\news.py" not in guide
    assert "python veer.py" not in guide.lower()


def test_start_veronica_script_launches_package() -> None:
    script = Path("scripts/start_veronica.bat").read_text(encoding="utf-8")

    assert "-m veronica --gui --reminders --speak" in script
    assert "veer.py" not in script.lower()


def test_cli_accepts_veer_compatibility_flags(monkeypatch) -> None:
    from veronica.__main__ import VEER_BANNER, parse_args

    monkeypatch.setattr(
        "sys.argv",
        ["veronica", "--full", "--no-voice", "--no-gui", "--no-security", "--register"],
    )

    args = parse_args()

    assert args.full is True
    assert args.no_voice is True
    assert args.no_gui is True
    assert args.no_security is True
    assert args.register_face is True
    assert "Battery + System Stats" in VEER_BANNER
    assert "Fully local AI backend" in VEER_BANNER


def test_process_command_logs_and_speaks_response(tmp_path: Path) -> None:
    from veronica.__main__ import process_command

    assistant = make_assistant(tmp_path)
    spoken: list[str] = []

    response, running = process_command(assistant, "calculate 2 + 2", speaker=spoken.append, data_dir=tmp_path)

    assert response == "The answer is 4."
    assert running is True
    assert spoken == ["The answer is 4."]
    log_text = (tmp_path / "logs" / "veronica_log.txt").read_text(encoding="utf-8")
    assert "CMD: calculate 2 + 2" in log_text
    assert "RESP: The answer is 4." in log_text


def test_process_command_stops_on_goodbye(tmp_path: Path) -> None:
    from veronica.__main__ import process_command

    assistant = make_assistant(tmp_path)

    response, running = process_command(assistant, "bye", data_dir=tmp_path)

    assert response == "Powering down. Goodbye."
    assert running is False


def test_assistant_can_chain_multiple_commands(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    response = assistant.respond("what time is it and then calculate 2 + 3")

    lines = response.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("1. Abhi time hai")
    assert lines[1] == "2. The answer is 5."


def test_assistant_repeat_replays_last_response(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    first = assistant.respond("calculate 3 * 3")
    repeated = assistant.respond("repeat")

    assert first == "The answer is 9."
    assert repeated == "Last response: The answer is 9."


def test_assistant_repeat_without_history(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    assert assistant.respond("repeat") == "Abhi tak koi response nahi diya hai."


def test_local_ai_gemini_mode_requires_key(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.setenv("VERONICA_AI_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = assistant.respond("explain transformers")

    assert response == "Gemini provider selected hai, but GEMINI_API_KEY set nahi hai."


def test_local_ai_gemini_mode_uses_optional_requests(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.setenv("VERONICA_AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeResponse:
        @staticmethod
        def json():
            return {
                "candidates": [
                    {"content": {"parts": [{"text": "Namaste from Gemini"}]}}
                ]
            }

    class FakeRequests:
        @staticmethod
        def post(url: str, json: dict, timeout: int):
            assert "key=test-key" in url
            assert timeout == 20
            assert json["contents"][0]["parts"][0]["text"] == "explain transformers"
            return FakeResponse()

    monkeypatch.setattr("veronica.local_ai._optional_module", lambda module_name: FakeRequests if module_name == "requests" else None)

    response = assistant.respond("explain transformers")

    assert response == "Namaste from Gemini"


def test_local_ai_provider_defaults_to_local(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.delenv("VERONICA_AI_PROVIDER", raising=False)
    monkeypatch.delenv("VERONICA_USE_GEMINI", raising=False)

    response = assistant.respond("who are you")

    assert "fully local" in response


def test_assistant_shortcut_alias_executes_saved_command(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)
    (tmp_path / "shortcuts.json").write_text('{"morning":"calculate 10 + 5"}', encoding="utf-8")

    response = assistant.respond("shortcut morning")

    assert response == "The answer is 15."


def test_assistant_shortcut_supports_run_prefix(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)
    (tmp_path / "shortcuts.json").write_text('{"brief":"what is today\'s date"}', encoding="utf-8")

    response = assistant.respond("run brief")

    assert response.startswith("Aaj ")


def test_assistant_shortcut_ignores_bad_shortcuts_file(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)
    (tmp_path / "shortcuts.json").write_text('{bad json', encoding="utf-8")

    response = assistant.respond("shortcut morning")

    assert "local" in response.lower() or "plan" in response.lower() or "analysis" in response.lower()


def test_memory_skill_save_and_list(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    assert assistant.respond("remember that city = pune") == "Memory saved: city = pune"
    listed = assistant.respond("show memory")

    assert "Saved memory:" in listed
    assert "- city: pune" in listed


def test_memory_skill_delete(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)
    assistant.respond("remember that city = pune")

    assert assistant.respond("forget memory city") == "Memory 'city' delete kar diya."
    assert assistant.respond("show memory") == "Memory store empty hai."


def test_memory_skill_requires_key_value_format(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    assert assistant.respond("remember that city pune") == "Use format: remember that key = value"


def test_advanced_roadmap_status_and_next(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    status = assistant.respond("advance status")
    nxt = assistant.respond("advance next")

    assert "Advanced roadmap progress: 0/10" in status
    assert "Next step 1:" in nxt
    assert "plugins" in nxt


def test_advanced_roadmap_mark_done_and_reset(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    assert assistant.respond("advance done plugins") == "Marked done: plugins"
    status = assistant.respond("advance status")
    assert "Advanced roadmap progress: 1/10" in status
    assert "✅ 1. Plugin architecture (plugins)" in status

    assert assistant.respond("advance reset") == "Advanced roadmap progress reset kar diya."
    status_after_reset = assistant.respond("advance status")
    assert "Advanced roadmap progress: 0/10" in status_after_reset


def test_openclaw_bridge_lists_builtin_tools(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    response = assistant.respond("openclaw tools")

    assert "OpenClaw-style bridge tools:" in response
    assert "roadmap_next" in response
    assert "memory_list" in response


def test_openclaw_bridge_runs_builtin_tool(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    response = assistant.respond("openclaw run roadmap_next")

    assert response.startswith("Next step 1:")
    assert "plugins" in response


def test_openclaw_bridge_loads_manifest_and_requires_shell_approval(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)
    manifest = {
        "tools": [
            {"name": "danger", "description": "shell test", "kind": "shell", "command": "del *"},
            {"name": "brief", "description": "assistant command", "kind": "assistant", "command": "advance next"},
        ]
    }
    (tmp_path / "openclaw_tools.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")

    tools = assistant.respond("openclaw tools")
    blocked = assistant.respond("openclaw run danger")
    mapped = assistant.respond("openclaw run brief")

    assert "danger [shell]" in tools
    assert blocked == "Shell tool approval required. Manifest me requires_approval=false set karo only trusted commands ke liye."
    assert mapped == "Assistant tool 'brief' maps to command: advance next"


def test_openclaw_bridge_runs_approved_shell_tool(tmp_path: Path) -> None:
    import sys

    assistant = make_assistant(tmp_path)
    manifest = {
        "tools": [
            {
                "name": "safe_echo",
                "description": "approved shell test",
                "kind": "shell",
                "command": f"{sys.executable} -c \"print(\'shell-safe\')\"",
                "requires_approval": False,
            }
        ]
    }
    (tmp_path / "openclaw_tools.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")

    response = assistant.respond("openclaw run safe_echo")

    assert response == "Shell tool 'safe_echo' result: shell-safe"


def test_openclaw_bridge_can_mark_bridge_step_complete(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)

    response = assistant.respond("openclaw run bridge_complete")
    status = assistant.respond("advance status")

    assert response == "Marked done: plugins"
    assert "Advanced roadmap progress: 1/10" in status
    assert "✅ 1. Plugin architecture (plugins)" in status


def test_openclaw_full_status_reports_missing_runtime(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    monkeypatch.delenv("VERONICA_OPENCLAW_BIN", raising=False)
    monkeypatch.delenv("VERONICA_OPENCLAW_SOURCE", raising=False)
    monkeypatch.setattr("veronica.openclaw_runtime.shutil.which", lambda name: None)

    response = assistant.respond("openclaw full status")

    assert "Full OpenClaw runtime abhi configured nahi hai" in response
    assert "npm install -g openclaw@latest" in response


def test_openclaw_full_agent_forwards_to_real_runtime_adapter(tmp_path: Path, monkeypatch) -> None:
    from veronica.openclaw_runtime import OpenClawCommand

    assistant = make_assistant(tmp_path)
    calls: list[list[str]] = []

    monkeypatch.setattr(
        "veronica.openclaw_runtime.resolve_openclaw_command",
        lambda: OpenClawCommand(("openclaw",), source="test"),
    )

    class Completed:
        stdout = "agent-ok"
        stderr = ""
        returncode = 0

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        assert kwargs["timeout"] == 60
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is False
        return Completed()

    monkeypatch.setattr("veronica.openclaw_runtime.subprocess.run", fake_run)

    response = assistant.respond("openclaw full agent Ship checklist")

    assert response == "OpenClaw runtime (0): agent-ok"
    assert calls == [["openclaw", "agent", "--message", "Ship checklist"]]
