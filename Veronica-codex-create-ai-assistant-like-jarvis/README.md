# Veronica JARVIS Assistant

Veronica is a lightweight, extensible AI assistant inspired by JARVIS. It is fully local: no external AI service, hosted model, API key, or network call is required for its intelligence.

## Features

- Conversational command-line assistant
- Local AI algorithms for intent matching, keyword extraction, and response synthesis
- Offline skills for time, date, math, notes, JSON-backed timed reminders, jokes, quiz, focus mode, productivity reports, app launching, browser search, screenshots, file search, optional news headlines, local screen OCR, dictation auto-type, and detailed system stats
- Optional natural Edge TTS voice output with `edge-tts` and `pygame`, plus `pyttsx3` fallback
- Optional VEER-style popup and system-tray GUI
- Optional same-WiFi mobile web control server
- Optional local webcam security shield
- Optional Windows full installer and Startup shortcut helpers
- Optional local auto-type support with `pyautogui` and `pyperclip`
- Extensible skill registry for adding new commands

## VEER-style full guide

For a Hindi/Hinglish, VEER v3-style setup guide with full command lists, Windows steps, API-key locations, command-line options, and the adapted folder structure, see [`docs/VERONICA_V3_GUIDE.md`](docs/VERONICA_V3_GUIDE.md).

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m veronica
# VEER-style full mode (voice + GUI + reminders + security when configured):
python -m veronica --full
# Text-only full mode without popup/camera:
python -m veronica --full --no-voice --no-gui --no-security
# Optional reminder background thread:
python -m veronica --reminders
# Optional popup/tray GUI:
python -m veronica --gui
# Optional same-WiFi mobile web server:
python -m veronica --mobile
# Optional webcam security shield:
python -m veronica --register-face
python -m veronica --security
# Optional Windows full optional dependency installer:
scripts\install_windows_full.bat
# Optional Windows launcher with GUI, reminders, and voice:
scripts\start_veronica.bat
# Optional Windows startup shortcut, run from PowerShell/CMD on Windows:
python -m veronica --add-startup --startup-args --gui --reminders
```

Optional natural voice output and auto-type dependencies:

```bash
pip install -r requirements-voice.txt
python -m veronica --speak
```

Voice output uses Microsoft Edge TTS through `edge-tts` with `pygame` playback and falls back to `pyttsx3` if Edge TTS playback is unavailable. Windows setup can use `scripts/install_windows_full.bat` for all optional Python packages; startup setup uses the standard-library helper in `veronica/startup.py` and no extra dependency. Security shield needs OpenCV, face-recognition, numpy, and optionally pywhatkit. Mobile web control needs `flask`. GUI tray commands need `pystray` and `pillow`; tkinter is required for popup/input windows. Auto-type commands need `pyautogui`; Unicode-friendly paste also uses `pyperclip`. Optional weather uses `requests` and a locally provided `WEATHER_API_KEY`. Optional WhatsApp uses `pywhatkit` and a locally provided `WHATSAPP_NUMBER`. Optional news headlines use `requests` and a locally provided `NEWS_API_KEY`. Optional screen OCR uses Tesseract, `pytesseract`, `pillow`, and `pyautogui`. Optional detailed system stats use `psutil`.

## Example commands

- `who are you`
- `make a plan to organize my desk`
- `joke sunao`
- `motivate karo`
- `quiz khelo`
- `focus mode on 25 minute`
- `focus mode off`
- `aaj ka report`
- `coin uchhalo`
- `dice daalo`
- `open chrome`
- `google local AI`
- `youtube lo fi song`
- `weather in Mumbai`
- `screenshot`
- `file dhundo report`
- `screen padho`
- `copy karo screen`
- `technology news`
- `khel khabar`
- `dictation mode on`
- `dictation mode off`
- `yeh type karo: hello from Veronica`
- `what time is it`
- `what is today's date`
- `calculate 42 * (8 + 2)`
- `remember buy batteries`
- `show notes`
- `10 minute baad remind karo meeting hai`
- `remind me to call Sam at 18:00`
- `battery status`
- `cpu report`
- `ram memory`
- `disk space`
- `temperature`
- `running apps`
- `system status`
- `help`
- `exit`

## How the local AI works

Veronica uses transparent algorithms implemented in `veronica/local_ai.py`:

1. Tokenize the message and remove common stop words.
2. Convert the remaining terms into frequency vectors.
3. Compare the message vector to local intent prototypes with cosine similarity.
4. Extract the most important keywords.
5. Generate a response from deterministic local templates.

This is not a hosted large language model. It is a small local reasoning layer intended to be private, inspectable, and easy to extend.

## Project layout

```text
veronica/
  __main__.py      # CLI entry point
  assistant.py     # Assistant orchestration
  core_commands.py # VEER-inspired app/search/weather/screenshot/file router
  gui.py           # Optional popup, command window, and system tray helpers
  local_ai.py      # Fully local AI algorithms
  mobile.py        # Optional same-WiFi Flask mobile web server
  security.py      # Optional webcam security shield
  reminders.py     # JSON-backed timed reminders and scheduler
  fun.py           # Jokes, quiz, focus mode, and productivity reports
  dictation.py     # Local dictation and auto-type controller
  news.py          # Optional NewsAPI headline lookup without hardcoded secrets
  ocr.py           # Optional local screen OCR via Tesseract
  system_stats.py  # Optional psutil-powered system report helpers
  skills.py        # Built-in offline skills
  speech.py        # Optional Edge TTS voice helper with pyttsx3 fallback
  startup.py       # Optional Windows Startup shortcut installer
scripts/
  add_to_startup.bat      # Convenience Windows Startup installer
  install_windows_full.bat # Full optional dependency installer
  start_veronica.bat      # Convenience Windows launcher
tests/
  test_assistant.py
```

## Adding a skill

Add a handler to `veronica/skills.py` and register it in `build_default_skills()`. Skill handlers receive the user message and a shared `AssistantContext`, then return a `SkillResult`.

## Adding a local AI intent

Add a `LocalIntent` in `_build_intents()` inside `veronica/local_ai.py`. Provide example phrases and a response template. Veronica will automatically include it in the local cosine-similarity classifier.

## Optional Windows full installer

Veronica adapts the provided VEER v3.0 installer as `scripts/install_windows_full.bat`, but points it at this package instead of hardcoded `veer.py` or `brain\modules` paths. From Command Prompt or PowerShell on Windows, run:

```bat
scripts\install_windows_full.bat
```

The installer upgrades `pip`, installs `requirements-all.txt`, and verifies the main Veronica modules compile. Use `scripts\start_veronica.bat` when you want a one-click Windows launcher for `python -m veronica --gui --reminders --speak`. The CLI also accepts VEER-style compatibility flags such as `--full`, `--no-voice`, `--no-gui`, `--no-security`, and `--register`. It also prints manual follow-up steps for Tesseract OCR, `NEWS_API_KEY`, optional weather/WhatsApp environment variables, face-recognition build prerequisites, and the Startup shortcut helper. Core Veronica still works without this installer; use it only when you want all optional integrations at once.

## Optional Windows startup

Veronica adapts the provided VEER startup batch flow without hardcoding a local `veer.py` path. On Windows, either run the bundled batch file or call the CLI directly:

```bat
scripts\add_to_startup.bat
python -m veronica --add-startup --startup-name Veronica --startup-args --gui --reminders
```

The installer creates a per-user `.lnk` in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`, targets `pythonw` when available, passes `-m veronica` plus your startup arguments, sets the current repository directory as the working directory, and uses `WindowStyle = 7` for a minimized/background launch. Keep `--startup-args` last because it captures the remaining flags for the shortcut. The default shortcut arguments are `--gui --reminders`; add options such as `--speak` only after installing the matching optional dependencies.

## Optional security shield

Veronica adapts the provided VEER security shield in `veronica/security.py`. It can register known-face samples and monitor the webcam for unknown faces, saving intruder snapshots under `logs/intruders` inside the assistant data directory. Install optional dependencies first:

```bash
pip install -r requirements-security.txt
python -m veronica --register-face
python -m veronica --security
```

WhatsApp alerts are optional and never use a hardcoded number. Set `SECURITY_WHATSAPP_NUMBER` (or `WHATSAPP_NUMBER`) to enable alerts. The security shield is opt-in and never starts unless you pass `--security`.

## Optional mobile web server

Veronica adapts the provided VEER mobile server in `veronica/mobile.py`. Install Flask and run the server, then open the printed URL from a phone on the same WiFi network:

```bash
pip install -r requirements-mobile.txt
python -m veronica --mobile
```

The mobile server exposes `/`, `/command`, `/status`, and `/security/snapshot`. It routes commands through the same local `Assistant` instance and does not import old `brain` or `voice` packages. Use `--mobile-host` and `--mobile-port` to change the bind address, and `--mobile-speak` if you want mobile-triggered responses spoken locally.

## Optional Edge TTS voice

Veronica adapts the provided VEER voice module in `veronica/speech.py`. The default voice is `hi-IN-MadhurNeural`, with `+10%` rate and normal volume for a natural Hindi male voice. Other useful Microsoft voices include `hi-IN-SwaraNeural`, `en-IN-PrabhatNeural`, and `en-IN-NeerjaNeural`.

```bash
pip install -r requirements-voice.txt
python -m veronica --speak
```

The voice helper initializes `pygame` only when speech is requested, writes Edge TTS audio to a temporary MP3, removes the file after playback, and falls back to `pyttsx3` if Edge TTS or playback is unavailable. The helper also exposes `greeting_text()` and `greet()` for VEER-style startup greetings.

## Optional GUI

Veronica adapts the provided VEER popup and tray flow in `veronica/gui.py`. Use `python -m veronica --gui` to launch the greeting popup and optional tray icon. If tray dependencies are missing, install them with:

```bash
pip install -r requirements-gui.txt
```

The GUI stays optional and degrades gracefully when tkinter, pystray, Pillow, or a desktop display is unavailable.

## Fun, focus, and productivity

Veronica adapts the provided VEER fun module in `veronica/fun.py`. Supported commands include `joke sunao`, `motivate karo`, `quiz khelo`, `coin uchhalo`, `dice daalo`, `focus mode on 25 minute`, `focus mode off`, and `aaj ka report`. Productivity counts are stored locally in `productivity.json` inside the assistant data directory.

Focus mode starts a local timer and is safe by default. It does not close distraction apps unless `VERONICA_FOCUS_CLOSE_APPS=1` is set intentionally. With `--speak`, focus-complete notifications can use Edge TTS or the local fallback voice.

## Timed reminders

Veronica adapts the provided VEER reminder flow in `veronica/reminders.py`. Reminders are stored locally as JSON in the assistant data directory. Supported commands include `10 minute baad remind karo meeting hai`, `remind me to call Sam at 18:00`, `9 baje reminder gym jaana`, and `show reminders`.

Use `python -m veronica --reminders` to start the lightweight background checker. With `--speak`, due reminders can use the Edge TTS voice helper. The scheduler is standard-library based, so no external `schedule` package is required.

## VEER-style core commands

Veronica adapts the provided VEER master router as `veronica/core_commands.py`. It supports safe allow-listed app open/close commands, Google and YouTube browser searches, screenshots, common-folder file search, greetings, local time/date phrases, optional weather, and optional WhatsApp scheduling. No phone number or weather key is hardcoded.

```bash
pip install -r requirements-integrations.txt
export WEATHER_API_KEY="your-openweather-key"      # optional weather
export WEATHER_CITY="Pune"                         # optional default city
export WHATSAPP_NUMBER="+910000000000"             # optional WhatsApp
python -m veronica
```

Power commands such as shutdown/restart/sleep/lock are disabled by default. To enable them intentionally, set `VERONICA_ENABLE_POWER_COMMANDS=1`.

## Optional detailed system stats

Veronica adapts the provided VEER system stats flow for battery, CPU, RAM, disk, temperature, running apps, and full system reports. Install the optional dependency to enable richer stats:

```bash
pip install -r requirements-system.txt
python -m veronica
```

Supported commands include `battery`, `charge`, `cpu`, `processor`, `ram`, `memory`, `disk`, `storage`, `temperature`, `apps`, `running`, `system`, `report`, and `status`. Disk usage uses the current platform default path instead of a hardcoded drive.

## Optional news headlines

Veronica can adapt the provided news command flow with `news`, `khabar`, `headlines`, and category words like `technology`, `sports`, `khel`, `business`, `health`, `science`, and `world`. To keep secrets out of source control, set your own key locally before using news commands:

```bash
pip install -r requirements-news.txt
export NEWS_API_KEY="your-newsapi-key"
python -m veronica
```

If `NEWS_API_KEY` is not set, Veronica explains how to enable news instead of using a hardcoded key.

## Optional screen OCR

Veronica can adapt the provided VEER screen OCR flow with commands like `screen padho`, `screen read`, `kya likha hai screen pe`, `copy karo screen`, and `area padho`. OCR is local, but it requires Tesseract to be installed on your computer:

```bash
pip install -r requirements-ocr.txt
export TESSERACT_CMD="/path/to/tesseract"  # optional when tesseract is already on PATH
python -m veronica
```

The code does not hardcode a Windows Tesseract path; use `TESSERACT_CMD` when your install needs an explicit binary path.

## Dictation and auto-type

Veronica includes an adapted VEER-style dictation controller in `veronica/dictation.py`. In the CLI, `dictation mode on` makes the next typed assistant inputs paste into the currently focused application. Use `dictation band`, `dictation off`, or `stop dictation` to stop. You can also type one message without staying in dictation mode by saying `yeh type karo: your text` or `type karo: your text`.

Special dictation commands include `new line` / `nai line`, `backspace` / `mita do`, and `space`.
