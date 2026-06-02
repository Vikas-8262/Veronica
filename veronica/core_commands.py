"""VEER-inspired core command router for Veronica.

This module adapts the user's VEER v3 master router into safe, optional, local
commands. It avoids hardcoded phone numbers, API keys, hosted AI fallbacks, and
unconditional destructive power actions.
"""

from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import os
import platform
import re
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

APP_MAP = {
    "chrome": "chrome",
    "firefox": "firefox",
    "notepad": "notepad",
    "calculator": "calc" if platform.system() == "Windows" else "gnome-calculator",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "vs code": "code",
    "vscode": "code",
    "task manager": "taskmgr",
    "file explorer": "explorer" if platform.system() == "Windows" else "xdg-open",
    "paint": "mspaint",
    "vlc": "vlc",
    "spotify": "spotify",
    "telegram": "telegram",
    "zoom": "zoom",
    "cmd": "cmd" if platform.system() == "Windows" else "x-terminal-emulator",
}

CLOSE_MAP = {
    "chrome": "chrome.exe" if platform.system() == "Windows" else "chrome",
    "firefox": "firefox.exe" if platform.system() == "Windows" else "firefox",
    "notepad": "notepad.exe" if platform.system() == "Windows" else "notepad",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "vlc": "vlc.exe" if platform.system() == "Windows" else "vlc",
    "spotify": "Spotify.exe" if platform.system() == "Windows" else "spotify",
    "zoom": "Zoom.exe" if platform.system() == "Windows" else "zoom",
}

OPEN_WORDS = ("kholo", "open", "chalaao", "start karo")
CLOSE_WORDS = ("band karo", "close", "khatam karo")
WEATHER_WORDS = ("weather", "mausam")
SEARCH_WORDS = ("search", "google", "dhundo")
WHATSAPP_WORDS = ("whatsapp", "message bhejo", "wa bhejo")
SCREENSHOT_WORDS = ("screenshot",)
FILE_WORDS = ("file dhundo", "file search", "search file")
GREETING_WORDS = ("hello", "hi", "namaste", "kya haal")
GOODBYE_WORDS = ("bye", "alvida", "band ho", "quit", "exit")
POWER_WORDS = ("shutdown", "laptop band", "band karo laptop", "restart", "reboot", "sleep", "so ja", "hibernate", "lock", "lock karo")


def handle_core_command(command: str, data_dir: Path | None = None) -> str | None:
    """Route VEER-style core commands, returning None when no command matches."""
    normalized = _normalize(command)
    if not normalized:
        return "Kuch suna nahi."

    power_response = system_control(normalized)
    if power_response is not None:
        return power_response

    if _contains_any(normalized, ("time", "kitne baje", "baj")):
        return tell_time()
    if _contains_any(normalized, ("date", "aaj ka din", "tarikh")):
        return tell_date()
    if _contains_any(normalized, OPEN_WORDS):
        return open_app(normalized)
    if _contains_any(normalized, CLOSE_WORDS):
        return close_app(normalized)
    if _contains_any(normalized, WEATHER_WORDS):
        return get_weather(_extract_weather_city(command))
    if "youtube" in normalized or ("play" in normalized and "song" in normalized):
        return search_youtube(command)
    if _contains_any(normalized, SCREENSHOT_WORDS):
        return take_screenshot(data_dir=data_dir)
    if _contains_any(normalized, FILE_WORDS):
        return find_file(command)
    if _contains_any(normalized, SEARCH_WORDS):
        return search_google(command)
    if _contains_any(normalized, WHATSAPP_WORDS):
        return send_whatsapp(command)
    if _contains_any(normalized, GREETING_WORDS):
        return "Bilkul ready hoon! Kya kaam hai?"
    if _contains_any(normalized, GOODBYE_WORDS):
        return "Powering down. Goodbye."
    return None


def is_core_command(command: str) -> bool:
    """Return True when a command can be handled by this router."""
    return _core_action(command) is not None


def open_app(command: str) -> str:
    """Open a known local app or attempt to launch it dynamically on the system."""
    # 1. Try static APP_MAP matching first
    for label, executable in APP_MAP.items():
        if label in command:
            try:
                subprocess.Popen([executable], shell=(platform.system() == "Windows"))
                return f"{label.title()} khol diya!"
            except OSError:
                return f"{label} nahi mila."

    # 2. Dynamic Fallback: extract app name candidate after open words
    normalized = _normalize(command)
    candidate = ""
    for word in OPEN_WORDS:
        if word in normalized:
            parts = normalized.split(word, 1)
            if len(parts) > 1:
                candidate = parts[1].strip()
                break

    if candidate:
        try:
            if platform.system() == "Windows":
                try:
                    os.startfile(candidate)
                    return f"{candidate.title()} khol diya!"
                except Exception:
                    subprocess.Popen([candidate], shell=True)
                    return f"{candidate.title()} khol diya!"
            else:
                subprocess.Popen([candidate])
                return f"{candidate.title()} khol diya!"
        except Exception:
            pass

    return "Yeh app nahi pehchana."


def close_app(command: str) -> str:
    """Close a known local app from the safe close allow-list."""
    for label, process_name in CLOSE_MAP.items():
        if label in command:
            try:
                if platform.system() == "Windows":
                    subprocess.run(["taskkill", "/f", "/im", process_name], check=False, capture_output=True)
                else:
                    subprocess.run(["pkill", "-x", process_name], check=False, capture_output=True)
                return f"{label.title()} band kar diya!"
            except OSError as exc:
                return f"{label} band nahi ho saka: {exc}"
    return "Kaunsa app band karoon?"


def tell_time() -> str:
    """Return the current local time."""
    return f"Abhi time hai {dt.datetime.now().strftime('%I:%M %p')}"


def tell_date() -> str:
    """Return the current local date."""
    return f"Aaj {dt.datetime.now().strftime('%A, %d %B %Y')} hai."


def get_weather(city: str | None = None) -> str:
    """Fetch weather only when the user provides a local OpenWeather key."""
    api_key = os.getenv("WEATHER_API_KEY", "").strip()
    if not api_key:
        return "Weather ke liye WEATHER_API_KEY environment variable set karo."

    requests = _optional_module("requests")
    if requests is None:
        return "Weather ke liye requests install karo: pip install -r requirements-integrations.txt"

    active_city = city or os.getenv("WEATHER_CITY", "Pune")
    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": active_city, "appid": api_key, "units": "metric"},
            timeout=5,
        )
        data = response.json()
    except requests.exceptions.ConnectionError:
        return "Internet nahi hai."
    except requests.exceptions.Timeout:
        return "Weather request timeout ho gaya."
    except ValueError:
        return "Weather response samajh nahi aaya."
    except Exception as exc:  # pragma: no cover - defensive third-party boundary
        return f"Weather check nahi ho saka: {exc}"

    if data.get("main"):
        return (
            f"{active_city} mein {data['main']['temp']:.0f}°C hai, "
            f"{data['weather'][0]['description']}. Humidity {data['main']['humidity']}%."
        )
    return "Weather nahi mila."


def search_google(command: str) -> str:
    """Open a Google search in the default browser."""
    query = _remove_words(command, ("search", "google", "dhundo"))
    if not query:
        return "Kya search karoon?"
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"'{query}' Google par search kar diya!"


def search_youtube(command: str) -> str:
    """Open a YouTube search in the default browser."""
    query = _remove_words(command, ("youtube", "play", "chalaao"))
    if not query:
        return "Kya YouTube par dhundoon?"
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
    return f"YouTube par '{query}' dhund diya!"


def send_whatsapp(command: str) -> str:
    """Schedule a WhatsApp message when pywhatkit and WHATSAPP_NUMBER are configured."""
    phone_number = os.getenv("WHATSAPP_NUMBER", "").strip()
    if not phone_number:
        return "WhatsApp ke liye WHATSAPP_NUMBER environment variable set karo."

    pywhatkit = _optional_module("pywhatkit")
    if pywhatkit is None:
        return "WhatsApp ke liye pywhatkit install karo: pip install -r requirements-integrations.txt"

    message = _remove_words(command, ("whatsapp", "bhejo", "message", "msg", "wa")) or "Veronica ki taraf se namaste!"
    send_time = dt.datetime.now() + dt.timedelta(minutes=2)
    try:
        pywhatkit.sendwhatmsg(phone_number, message, send_time.hour, send_time.minute, wait_time=10)
        return f"WhatsApp message schedule hua: '{message}'"
    except Exception as exc:  # pragma: no cover - defensive third-party boundary
        return f"WhatsApp error: {exc}"


def take_screenshot(data_dir: Path | None = None) -> str:
    """Take a screenshot into Veronica's data directory when pyautogui is installed."""
    pyautogui = _optional_module("pyautogui")
    if pyautogui is None:
        return "Screenshot ke liye pyautogui install karo: pip install -r requirements-integrations.txt"

    screenshot_dir = (data_dir or Path.home() / ".veronica") / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = screenshot_dir / f"ss_{timestamp}.png"
    try:
        pyautogui.screenshot(str(path))
        return f"Screenshot liya: {path.name}"
    except Exception as exc:  # pragma: no cover - defensive third-party boundary
        return f"Screenshot error: {exc}"


def find_file(command: str) -> str:
    """Search common user folders for a filename fragment."""
    query = _remove_words(command, ("file dhundo", "dhundo", "search file", "file search", "find"))
    if not query:
        return "Kaunsi file dhundoon?"

    results: list[Path] = []
    for directory in _search_directories():
        if not directory.exists():
            continue
        for path in directory.rglob(f"*{query}*"):
            results.append(path)
            if len(results) >= 5:
                break
        if len(results) >= 5:
            break

    if results:
        names = ", ".join(path.name for path in results[:3])
        return f"{len(results)} file mili: {names}"
    return f"'{query}' naam ki file nahi mili."


def system_control(command: str) -> str | None:
    """Handle power commands, disabled by default for safety."""
    if not _contains_any(command, POWER_WORDS):
        return None
    if os.getenv("VERONICA_ENABLE_POWER_COMMANDS") != "1":
        return "Power commands disabled hain. Enable karne ke liye VERONICA_ENABLE_POWER_COMMANDS=1 set karo."

    if _contains_any(command, ("shutdown", "laptop band", "band karo laptop")):
        return _run_power_command(_shutdown_command(), "10 second mein shutdown ho raha hai!")
    if _contains_any(command, ("restart", "reboot")):
        return _run_power_command(_restart_command(), "Restart ho raha hai!")
    if _contains_any(command, ("sleep", "so ja", "hibernate")):
        return _run_power_command(_sleep_command(), "Sleep mode mein ja raha hoon!")
    if _contains_any(command, ("lock", "lock karo")):
        return _run_power_command(_lock_command(), "Laptop lock kar diya!")
    return None


def _core_action(command: str) -> str | None:
    normalized = _normalize(command)
    checks = (
        (POWER_WORDS, "power"),
        (("time", "kitne baje", "baj"), "time"),
        (("date", "aaj ka din", "tarikh"), "date"),
        (OPEN_WORDS, "open"),
        (CLOSE_WORDS, "close"),
        (WEATHER_WORDS, "weather"),
        (SCREENSHOT_WORDS, "screenshot"),
        (FILE_WORDS, "file"),
        (SEARCH_WORDS, "search"),
        (WHATSAPP_WORDS, "whatsapp"),
        (GREETING_WORDS, "greeting"),
        (GOODBYE_WORDS, "goodbye"),
    )
    if "youtube" in normalized or ("play" in normalized and "song" in normalized):
        return "youtube"
    for words, action in checks:
        if _contains_any(normalized, words):
            return action
    return None


def _run_power_command(command: list[str], success_message: str) -> str:
    try:
        subprocess.run(command, check=False, capture_output=True)
        return success_message
    except OSError as exc:
        return f"Power command nahi chal saka: {exc}"


def _shutdown_command() -> list[str]:
    if platform.system() == "Windows":
        return ["shutdown", "/s", "/t", "10"]
    return ["shutdown", "-h", "+1"]


def _restart_command() -> list[str]:
    if platform.system() == "Windows":
        return ["shutdown", "/r", "/t", "5"]
    return ["shutdown", "-r", "+1"]


def _sleep_command() -> list[str]:
    if platform.system() == "Windows":
        return ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]
    if platform.system() == "Darwin":
        return ["pmset", "sleepnow"]
    return ["systemctl", "suspend"]


def _lock_command() -> list[str]:
    if platform.system() == "Windows":
        return ["rundll32.exe", "user32.dll,LockWorkStation"]
    if platform.system() == "Darwin":
        return ["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"]
    return ["loginctl", "lock-session"]


def _extract_weather_city(command: str) -> str | None:
    normalized = _normalize(command)
    for marker in ("weather in", "weather", "mausam in", "mausam"):
        if marker in normalized:
            candidate = normalized.split(marker, 1)[1].strip()
            return candidate or None
    return None


def _remove_words(command: str, words: tuple[str, ...]) -> str:
    result = command
    for word in words:
        result = re.sub(re.escape(word), "", result, flags=re.IGNORECASE)
    return " ".join(result.strip().split())


def _search_directories() -> tuple[Path, ...]:
    home = Path.home()
    return (home / "Desktop", home / "Documents", home / "Downloads")


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _optional_module(module_name: str):
    if importlib.util.find_spec(module_name) is None:
        return None
    return importlib.import_module(module_name)


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())
