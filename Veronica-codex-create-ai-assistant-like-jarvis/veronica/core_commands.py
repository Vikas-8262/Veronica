"""VEER-inspired core command router for Veronica — Enhanced Edition.

Extra powers added:
- Chrome open + URL navigate + type in search bar
- VS Code open + open folder + find/edit lines of code
- Full Windows control (volume, brightness, clipboard, notifications)
- pyautogui based keyboard/mouse automation
"""

from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import os
import platform
import re
import subprocess
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

APP_MAP = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": "firefox",
    "notepad": "notepad",
    "calculator": "calc" if platform.system() == "Windows" else "gnome-calculator",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "vs code": "code",
    "vscode": "code",
    "task manager": "taskmgr",
    "file explorer": "explorer",
    "paint": "mspaint",
    "vlc": "vlc",
    "spotify": "spotify",
    "telegram": "telegram",
    "zoom": "zoom",
    "cmd": "cmd",
    "powershell": "powershell",
}

CLOSE_MAP = {
    "chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "notepad": "notepad.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "vlc": "vlc.exe",
    "spotify": "Spotify.exe",
    "zoom": "Zoom.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
}

OPEN_WORDS      = ("kholo", "open", "chalaao", "start karo", "open karo")
CLOSE_WORDS     = ("band karo", "close", "khatam karo", "close karo")
WEATHER_WORDS   = ("weather", "mausam")
SEARCH_WORDS    = ("search", "google", "dhundo", "search karo")
YOUTUBE_WORDS   = ("youtube",)
SCREENSHOT_WORDS= ("screenshot",)
FILE_WORDS      = ("file dhundo", "file search", "search file", "find file")
GREETING_WORDS  = ("hello", "hi", "namaste", "kya haal")
GOODBYE_WORDS   = ("bye", "alvida", "band ho", "quit", "exit")
POWER_WORDS     = ("shutdown", "laptop band", "band karo laptop", "restart",
                   "reboot", "sleep", "so ja", "hibernate", "lock", "lock karo")

# Chrome control keywords
CHROME_TYPE_WORDS  = ("chrome mein type karo", "chrome mein likho", "search bar mein",
                      "type in chrome", "chrome type")
CHROME_OPEN_WORDS  = ("chrome open karo", "open chrome", "chrome kholo", "chrome chalaao")
CHROME_SEARCH_WORDS= ("chrome mein search karo", "chrome search", "google search karo",
                      "search on chrome")
CHROME_URL_WORDS   = ("chrome mein kholo", "open in chrome", "url kholo", "website kholo")

# VS Code control keywords
VSCODE_FOLDER_WORDS= ("vscode mein folder kholo", "open folder in vscode",
                       "vscode folder open", "folder open karo vscode mein",
                       "open this folder", "is folder ko open karo")
VSCODE_FILE_WORDS  = ("vscode mein file kholo", "open file in vscode", "file open karo vscode")
VSCODE_FIND_WORDS  = ("line dhundo", "find line", "find this line", "yeh line dhundo",
                      "code mein dhundo", "find in code")
VSCODE_EDIT_WORDS  = ("line change karo", "code edit karo", "yeh line change karo",
                      "edit this line", "code badlo")
VSCODE_TERMINAL_WORDS = ("terminal kholo", "open terminal", "vscode terminal")

# Windows control keywords
VOLUME_WORDS    = ("volume badhaao", "volume kam karo", "volume up", "volume down",
                   "mute karo", "unmute karo", "volume")
CLIPBOARD_WORDS = ("clipboard", "copy kiya kya", "clipboard dekho")
NOTIFY_WORDS    = ("notification", "remind karo", "popup dikhaao")
BRIGHTNESS_WORDS= ("brightness", "screen bright karo", "screen dim karo")
WINDOW_WORDS    = ("minimize karo", "maximize karo", "window close karo",
                   "alt tab", "sabke windows dikhaao")


# ─────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────

def is_core_command(command: str) -> bool:
    """Return True when a command can be handled by this router."""
    return handle_core_command(command) is not None


def handle_core_command(command: str, data_dir: Path | None = None) -> str | None:
    """Route all commands. Returns None if no match found."""
    norm = _normalize(command)
    if not norm:
        return "Kuch suna nahi."

    # Power commands
    power = system_control(norm)
    if power is not None:
        return power

    # Time / Date
    if _contains_any(norm, ("time", "kitne baje", "baj")):
        return tell_time()
    if _contains_any(norm, ("date", "aaj ka din", "tarikh")):
        return tell_date()

    # ── Chrome advanced control ──
    if _contains_any(norm, CHROME_TYPE_WORDS):
        return chrome_type(command)
    if _contains_any(norm, CHROME_SEARCH_WORDS):
        return chrome_search(command)
    if _contains_any(norm, CHROME_URL_WORDS):
        return chrome_open_url(command)

    # ── VS Code advanced control ──
    if _contains_any(norm, VSCODE_FOLDER_WORDS):
        return vscode_open_folder(command)
    if _contains_any(norm, VSCODE_FILE_WORDS):
        return vscode_open_file(command)
    if _contains_any(norm, VSCODE_FIND_WORDS):
        return vscode_find_line(command)
    if _contains_any(norm, VSCODE_EDIT_WORDS):
        return vscode_edit_line(command)
    if _contains_any(norm, VSCODE_TERMINAL_WORDS):
        return vscode_open_terminal()

    # ── Windows control ──
    if _contains_any(norm, VOLUME_WORDS):
        return windows_volume(norm)
    if _contains_any(norm, WINDOW_WORDS):
        return windows_window_control(norm)
    if _contains_any(norm, CLIPBOARD_WORDS):
        return windows_clipboard()
    if _contains_any(norm, BRIGHTNESS_WORDS):
        return windows_brightness(norm)

    # ── Standard commands ──
    if _contains_any(norm, OPEN_WORDS):
        return open_app(norm)
    if _contains_any(norm, CLOSE_WORDS):
        return close_app(norm)
    if _contains_any(norm, WEATHER_WORDS):
        return get_weather(_extract_weather_city(command))
    if "youtube" in norm or ("play" in norm and "song" in norm):
        return search_youtube(command)
    if _contains_any(norm, SCREENSHOT_WORDS):
        return take_screenshot(data_dir=data_dir)
    if _contains_any(norm, FILE_WORDS):
        return find_file(command)
    if _contains_any(norm, SEARCH_WORDS):
        return search_google(command)
    if _contains_any(norm, GREETING_WORDS):
        return "Bilkul ready hoon! Kya kaam hai?"
    if _contains_any(norm, GOODBYE_WORDS):
        return "Powering down. Goodbye."

    return None


# ─────────────────────────────────────────────
# CHROME CONTROL
# ─────────────────────────────────────────────

def chrome_type(command: str) -> str:
    """Open Chrome and type text in address/search bar."""
    pyautogui = _optional_module("pyautogui")
    if pyautogui is None:
        return "pyautogui install karo: pip install pyautogui pyperclip"

    text = _remove_words(command, CHROME_TYPE_WORDS + CHROME_OPEN_WORDS)
    if not text:
        return "Kya type karoon Chrome mein?"

    # Open Chrome
    _launch_chrome()
    time.sleep(2)

    # Focus address bar and type
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.5)
    pyautogui.typewrite(text, interval=0.05)
    pyautogui.press("enter")
    return f"Chrome mein type kar diya: '{text}'"


def chrome_search(command: str) -> str:
    """Open Chrome and search something on Google."""
    query = _remove_words(command, CHROME_SEARCH_WORDS + ("chrome", "google", "search", "karo"))
    if not query:
        return "Kya search karoon?"
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    _launch_chrome(url)
    return f"Chrome mein '{query}' search kar diya!"


def chrome_open_url(command: str) -> str:
    """Open a specific URL in Chrome."""
    url = _remove_words(command, CHROME_URL_WORDS + ("chrome", "mein", "kholo", "open"))
    if not url:
        return "Kaunsi website kholuun?"
    if not url.startswith("http"):
        url = "https://" + url
    _launch_chrome(url)
    return f"Chrome mein {url} khol diya!"


def _launch_chrome(url: str = "") -> None:
    """Launch Chrome with optional URL."""
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            args = [path]
            if url:
                args.append(url)
            subprocess.Popen(args)
            return
    # Fallback
    if url:
        webbrowser.open(url)
    else:
        webbrowser.open("https://www.google.com")


# ─────────────────────────────────────────────
# VS CODE CONTROL
# ─────────────────────────────────────────────

def vscode_open_folder(command: str) -> str:
    """Open a folder in VS Code."""
    folder = _remove_words(command, VSCODE_FOLDER_WORDS + ("vscode", "mein", "open", "karo", "folder"))
    folder = folder.strip().strip("'\"")

    if not folder:
        # Open current directory
        try:
            subprocess.Popen(["code", "."])
            return "VS Code mein current folder khol diya!"
        except OSError:
            return "VS Code nahi mila. 'code' command PATH mein add karo."

    folder_path = Path(folder)
    if not folder_path.exists():
        # Search common locations
        search_dirs = [Path.home() / "Downloads", Path.home() / "Documents",
                       Path.home() / "Desktop", Path("C:/Projects")]
        for base in search_dirs:
            candidate = base / folder
            if candidate.exists():
                folder_path = candidate
                break

    try:
        subprocess.Popen(["code", str(folder_path)])
        return f"VS Code mein '{folder_path.name}' folder khol diya!"
    except OSError:
        return "VS Code nahi mila. 'code' command PATH mein add karo."


def vscode_open_file(command: str) -> str:
    """Open a specific file in VS Code."""
    filename = _remove_words(command, VSCODE_FILE_WORDS + ("vscode", "mein", "open", "karo"))
    filename = filename.strip()
    if not filename:
        return "Kaunsi file kholuun VS Code mein?"

    # Search for file
    results = []
    for directory in [Path.home() / "Downloads", Path.home() / "Documents",
                      Path.home() / "Desktop", Path("C:/Projects")]:
        if directory.exists():
            for p in directory.rglob(f"*{filename}*"):
                results.append(p)
                if len(results) >= 3:
                    break

    if results:
        try:
            subprocess.Popen(["code", str(results[0])])
            return f"VS Code mein '{results[0].name}' khol diya!"
        except OSError:
            return "VS Code nahi mila."
    return f"'{filename}' file nahi mili."


def vscode_find_line(command: str) -> str:
    """Find a line of code in VS Code using Ctrl+Shift+F."""
    pyautogui = _optional_module("pyautogui")
    if pyautogui is None:
        return "pyautogui install karo: pip install pyautogui"

    search_term = _remove_words(command, VSCODE_FIND_WORDS + ("vscode", "mein", "code", "dhundo"))
    search_term = search_term.strip()
    if not search_term:
        return "Kya dhundoon VS Code mein?"

    # Ctrl+Shift+F = Global search in VS Code
    pyautogui.hotkey("ctrl", "shift", "f")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.typewrite(search_term, interval=0.05)
    pyautogui.press("enter")
    return f"VS Code mein '{search_term}' dhund raha hoon!"


def vscode_edit_line(command: str) -> str:
    """Find and highlight a line for editing in VS Code."""
    pyautogui = _optional_module("pyautogui")
    if pyautogui is None:
        return "pyautogui install karo: pip install pyautogui"

    # Extract line number or text
    line_match = re.search(r"line\s*(\d+)", command, re.IGNORECASE)
    if line_match:
        line_num = line_match.group(1)
        # Ctrl+G = Go to line in VS Code
        pyautogui.hotkey("ctrl", "g")
        time.sleep(0.3)
        pyautogui.typewrite(line_num, interval=0.05)
        pyautogui.press("enter")
        return f"VS Code mein line {line_num} pe jump kar diya! Ab edit karo."

    search_term = _remove_words(command, VSCODE_EDIT_WORDS + ("vscode", "mein", "code", "karo"))
    if search_term:
        pyautogui.hotkey("ctrl", "shift", "f")
        time.sleep(0.5)
        pyautogui.typewrite(search_term.strip(), interval=0.05)
        return f"VS Code mein '{search_term}' dhund diya — wahan jaake edit karo!"

    return "Kaunsi line edit karni hai? Line number ya text batao."


def vscode_open_terminal() -> str:
    """Open integrated terminal in VS Code."""
    pyautogui = _optional_module("pyautogui")
    if pyautogui is None:
        return "pyautogui install karo: pip install pyautogui"

    pyautogui.hotkey("ctrl", "`")
    return "VS Code mein terminal khol diya!"


# ─────────────────────────────────────────────
# WINDOWS CONTROL
# ─────────────────────────────────────────────

def windows_volume(command: str) -> str:
    """Control system volume."""
    pyautogui = _optional_module("pyautogui")
    if pyautogui is None:
        return "pyautogui install karo: pip install pyautogui"

    if "mute" in command:
        pyautogui.press("volumemute")
        return "Volume mute kar diya!"
    if "unmute" in command:
        pyautogui.press("volumemute")
        return "Volume unmute kar diya!"
    if any(w in command for w in ("badhaao", "up", "increase", "zyada")):
        for _ in range(5):
            pyautogui.press("volumeup")
        return "Volume badha diya!"
    if any(w in command for w in ("kam karo", "down", "decrease", "kam")):
        for _ in range(5):
            pyautogui.press("volumedown")
        return "Volume kam kar diya!"

    return "Volume up/down/mute — kya karna hai?"


def windows_window_control(command: str) -> str:
    """Control windows — minimize, maximize, alt+tab."""
    pyautogui = _optional_module("pyautogui")
    if pyautogui is None:
        return "pyautogui install karo: pip install pyautogui"

    if "minimize" in command:
        pyautogui.hotkey("win", "down")
        return "Window minimize kar diya!"
    if "maximize" in command:
        pyautogui.hotkey("win", "up")
        return "Window maximize kar diya!"
    if "alt tab" in command or "switch" in command:
        pyautogui.hotkey("alt", "tab")
        return "Window switch kar diya!"
    if "sabke" in command or "all windows" in command:
        pyautogui.hotkey("win", "tab")
        return "Sab windows dikha diye!"
    if "close" in command or "band" in command:
        pyautogui.hotkey("alt", "f4")
        return "Window close kar diya!"

    return "Window control: minimize/maximize/close/switch — kya karna hai?"


def windows_clipboard() -> str:
    """Show clipboard content."""
    pyperclip = _optional_module("pyperclip")
    if pyperclip is None:
        return "pyperclip install karo: pip install pyperclip"
    try:
        content = pyperclip.paste()
        if content:
            return f"Clipboard mein yeh hai: '{content[:100]}'"
        return "Clipboard khaali hai."
    except Exception:
        return "Clipboard access nahi ho saka."


def windows_brightness(command: str) -> str:
    """Control screen brightness on Windows."""
    try:
        if any(w in command for w in ("bright", "badhaao", "increase", "zyada")):
            subprocess.run(["powershell", "-Command",
                "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,80)"],
                capture_output=True)
            return "Screen brightness badha diya!"
        if any(w in command for w in ("dim", "kam", "decrease")):
            subprocess.run(["powershell", "-Command",
                "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,40)"],
                capture_output=True)
            return "Screen dim kar diya!"
    except Exception:
        return "Brightness change nahi ho saka."
    return "Brightness badhaaun ya kam karun?"


# ─────────────────────────────────────────────
# STANDARD COMMANDS
# ─────────────────────────────────────────────

def open_app(command: str) -> str:
    """Open a known app."""
    for label, executable in APP_MAP.items():
        if label in command:
            try:
                if label == "chrome":
                    _launch_chrome()
                    return "Chrome khol diya!"
                subprocess.Popen([executable])
                return f"{label.title()} khol diya!"
            except OSError:
                return f"{label} nahi mila."
    return "Yeh app nahi pehchana."


def close_app(command: str) -> str:
    """Close a known app."""
    for label, process_name in CLOSE_MAP.items():
        if label in command:
            try:
                subprocess.run(["taskkill", "/f", "/im", process_name],
                               check=False, capture_output=True)
                return f"{label.title()} band kar diya!"
            except OSError as exc:
                return f"{label} band nahi ho saka: {exc}"
    return "Kaunsa app band karoon?"


def tell_time() -> str:
    return f"Abhi time hai {dt.datetime.now().strftime('%I:%M %p')}"


def tell_date() -> str:
    return f"Aaj {dt.datetime.now().strftime('%A, %d %B %Y')} hai."


def get_weather(city: str | None = None) -> str:
    api_key = os.getenv("WEATHER_API_KEY", "").strip()
    if not api_key:
        return "Weather ke liye WEATHER_API_KEY environment variable set karo."
    requests = _optional_module("requests")
    if requests is None:
        return "Weather ke liye: pip install requests"
    active_city = city or os.getenv("WEATHER_CITY", "Pune")
    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": active_city, "appid": api_key, "units": "metric"},
            timeout=5,
        )
        data = response.json()
    except Exception:
        return "Weather fetch nahi ho saka."
    if data.get("main"):
        return (f"{active_city} mein {data['main']['temp']:.0f}°C hai, "
                f"{data['weather'][0]['description']}. Humidity {data['main']['humidity']}%.")
    return "Weather nahi mila."


def search_google(command: str) -> str:
    query = _remove_words(command, ("search", "google", "dhundo", "search karo"))
    if not query:
        return "Kya search karoon?"
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"'{query}' Google par search kar diya!"


def search_youtube(command: str) -> str:
    query = _remove_words(command, ("youtube", "play", "chalaao"))
    if not query:
        return "Kya YouTube par dhundoon?"
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
    return f"YouTube par '{query}' dhund diya!"


def send_whatsapp(command: str) -> str:
    phone_number = os.getenv("WHATSAPP_NUMBER", "").strip()
    if not phone_number:
        return "WhatsApp ke liye WHATSAPP_NUMBER set karo."
    pywhatkit = _optional_module("pywhatkit")
    if pywhatkit is None:
        return "pip install pywhatkit"
    message = _remove_words(command, ("whatsapp", "bhejo", "message", "msg")) or "Namaste!"
    send_time = dt.datetime.now() + dt.timedelta(minutes=2)
    try:
        pywhatkit.sendwhatmsg(phone_number, message, send_time.hour, send_time.minute, wait_time=10)
        return f"WhatsApp message schedule hua: '{message}'"
    except Exception as exc:
        return f"WhatsApp error: {exc}"


def take_screenshot(data_dir: Path | None = None) -> str:
    pyautogui = _optional_module("pyautogui")
    if pyautogui is None:
        return "pip install pyautogui"
    screenshot_dir = (data_dir or Path.home() / ".veronica") / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = screenshot_dir / f"ss_{timestamp}.png"
    try:
        pyautogui.screenshot(str(path))
        return f"Screenshot liya: {path.name}"
    except Exception as exc:
        return f"Screenshot error: {exc}"


def find_file(command: str) -> str:
    query = _remove_words(command, ("file dhundo", "dhundo", "search file", "file search", "find"))
    if not query:
        return "Kaunsi file dhundoon?"
    results: list[Path] = []
    for directory in (Path.home() / "Desktop", Path.home() / "Documents",
                      Path.home() / "Downloads"):
        if not directory.exists():
            continue
        for path in directory.rglob(f"*{query}*"):
            results.append(path)
            if len(results) >= 5:
                break
    if results:
        names = ", ".join(p.name for p in results[:3])
        return f"{len(results)} file mili: {names}"
    return f"'{query}' naam ki file nahi mili."


def system_control(command: str) -> str | None:
    if not _contains_any(command, POWER_WORDS):
        return None
    if os.getenv("VERONICA_ENABLE_POWER_COMMANDS") != "1":
        return ("Power commands disabled hain. "
                "Enable karne ke liye terminal mein: $env:VERONICA_ENABLE_POWER_COMMANDS='1'")
    if _contains_any(command, ("shutdown", "laptop band", "band karo laptop")):
        return _run_power(["shutdown", "/s", "/t", "10"], "10 second mein shutdown!")
    if _contains_any(command, ("restart", "reboot")):
        return _run_power(["shutdown", "/r", "/t", "5"], "Restart ho raha hai!")
    if _contains_any(command, ("sleep", "so ja", "hibernate")):
        return _run_power(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], "Sleep mode!")
    if _contains_any(command, ("lock", "lock karo")):
        return _run_power(["rundll32.exe", "user32.dll,LockWorkStation"], "Laptop lock!")
    return None


def _run_power(cmd: list[str], msg: str) -> str:
    try:
        subprocess.run(cmd, check=False, capture_output=True)
        return msg
    except OSError as exc:
        return f"Power command error: {exc}"


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _contains_any(text: str, words: tuple[str, ...] | list[str]) -> bool:
    return any(word in text for word in words)


def _remove_words(command: str, words: tuple[str, ...] | list[str]) -> str:
    result = command
    for word in sorted(words, key=len, reverse=True):
        result = re.sub(re.escape(word), "", result, flags=re.IGNORECASE)
    return " ".join(result.strip().split())


def _extract_weather_city(command: str) -> str | None:
    normalized = _normalize(command)
    for marker in ("weather in", "weather", "mausam in", "mausam"):
        if marker in normalized:
            candidate = normalized.split(marker, 1)[1].strip()
            return candidate or None
    return None


def _optional_module(module_name: str):
    if importlib.util.find_spec(module_name) is None:
        return None
    return importlib.import_module(module_name)