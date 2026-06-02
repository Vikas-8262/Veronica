# Veronica v3 — Full Local AI Assistant

```text
╔══════════════════════════════════════════════════════╗
║        Veronica v3 — Full Local AI Assistant         ║
║        VEER-style setup guide for local use          ║
╚══════════════════════════════════════════════════════╝
```

Veronica keeps the VEER v3 workflow, but paths and commands are adapted to this repository. There are no legacy VEER entrypoint or brain settings files to edit. Use environment variables for secrets and run the package with `python -m veronica`.

## Quick setup (5 steps)

1. **Install optional packages** when you want the full Windows experience:
   ```bat
   scripts\install_windows_full.bat
   ```
   For a smaller install, use one targeted file such as `requirements-voice.txt`, `requirements-news.txt`, or `requirements-ocr.txt`.
2. **Add local settings as environment variables** instead of editing Python files:
   ```bat
   set WEATHER_CITY=Pune
   set WEATHER_API_KEY=your-openweather-key
   set NEWS_API_KEY=your-newsapi-key
   set WHATSAPP_NUMBER=+910000000000
   set SECURITY_WHATSAPP_NUMBER=+910000000000
   set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```
3. **Register your face** for the optional security shield:
   ```bat
   python -m veronica --register-face
   ```
4. **Start Veronica**:
   ```bat
   scripts\start_veronica.bat
   ```
   Or directly:
   ```bat
   python -m veronica --gui --reminders --speak
   ```
5. **Add auto-start on boot** when you want it:
   ```bat
   scripts\add_to_startup.bat
   ```
   Administrator rights are usually not required because the shortcut is created in the current user's Startup folder.

## Free API keys and local tools

| Feature | Where to get it | How Veronica reads it |
| --- | --- | --- |
| Weather | `openweathermap.org` → free account → API keys | `WEATHER_API_KEY`, optional `WEATHER_CITY` |
| News | `newsapi.org` → free account → API key | `NEWS_API_KEY` |
| OCR | Tesseract for Windows from the UB Mannheim build | Optional `TESSERACT_CMD` |
| WhatsApp | Local `pywhatkit` browser flow | `WHATSAPP_NUMBER` |
| Security alerts | Local `pywhatkit` browser flow | `SECURITY_WHATSAPP_NUMBER` or `WHATSAPP_NUMBER` |
| Offline AI | Built-in deterministic local backend | No Ollama or hosted model required |

## Full commands list — v3

### System stats

- `battery batao` → battery percentage and charging status
- `cpu kitna use ho raha` → CPU load
- `ram kitni hai` → memory usage
- `disk space batao` → disk usage for the current platform default path
- `temperature` → temperature sensors when available
- `running apps` → active process summary
- `system report` → combined system report

### News

- `news sunao` → top India headlines
- `tech news` / `technology news` → technology headlines
- `sports news` / `khel khabar` → sports headlines
- `business news` → business headlines
- `world news` → international headlines

### Dictation and auto-type

- `dictation mode on` → subsequent CLI messages are typed into the active app
- `dictation mode off` / `dictation band` → stop dictation mode
- `type karo: hello world` → type one message once
- `new line` / `nai line` → press Enter while dictation mode is active
- `backspace` / `mita do` → press Backspace while dictation mode is active

### Screen OCR

- `screen padho` → read screen text with local Tesseract OCR
- `screen copy` / `copy karo screen` → copy screen text to clipboard
- `area padho` / `select karke padho` → brief delay, then OCR the screen after you focus/select the area

### Fun and focus

- `joke sunao` → Hinglish joke
- `motivate karo` → motivational line
- `quiz khelo` → GK question
- `coin uchhalo` → heads or tails
- `dice daalo` → 1–6 random number
- `focus mode on` → 25-minute focus timer
- `focus mode on 45 minute` → custom duration
- `focus mode off` → stop focus timer
- `aaj ka report` → local productivity stats

### Time and date

- `time batao` → current local time
- `date batao` → current local date

### Apps

- `chrome kholo` → open Chrome if installed
- `notepad kholo` → open Notepad on Windows
- `vlc band karo` → close VLC if it is in the safe allow-list
- `open calculator` → open Calculator if available

### Weather

- `weather batao` → weather for `WEATHER_CITY` or Pune by default
- `weather in Mumbai` → weather for a specific city

### Search

- `google search Python` → Google search in your browser
- `youtube play Arijit` → YouTube search in your browser

### WhatsApp

- `whatsapp bhejo hello` → send a configured WhatsApp message through local `pywhatkit`

### Reminders

- `10 minute baad chai yaad dilao`
- `9 baje meeting remind karo`
- `reminder list dikhao`
- `show reminders`

### System actions

- `screenshot lo` → save a screenshot under the configured data directory
- `laptop lock karo` → lock the screen only when power commands are enabled
- `laptop band karo` → shutdown only when power commands are enabled

Power actions are disabled by default for safety. Set `VERONICA_ENABLE_POWER_COMMANDS=1` only if you intentionally want shutdown/restart/sleep/lock commands to execute.

### Security

- `python -m veronica --register-face` → register owner face samples
- `python -m veronica --security` → start the optional webcam security shield

### Local AI brain

Ask any general question and Veronica's deterministic local backend will classify intent, extract keywords, and answer from local templates. No Ollama, OpenAI key, or hosted model is required by default.

### Quit

- `bye`
- `alvida`
- `exit`

## Command-line options

```text
python -m veronica                         Text CLI mode
python -m veronica --full                  VEER-style full mode
python -m veronica --full --no-voice       Full mode, keyboard/text only
python -m veronica --full --no-gui         Full mode without popup/tray
python -m veronica --full --no-security    Full mode without camera security
python -m veronica --gui                   Popup/tray helpers
python -m veronica --speak                 Edge TTS voice output with fallback
python -m veronica --reminders             Background reminder checker
python -m veronica --mobile                Mobile web server
python -m veronica --mobile-speak          Speak mobile-triggered responses
python -m veronica --register-face         Face registration flow
python -m veronica --register              VEER-compatible face registration alias
python -m veronica --security              Webcam security shield
python -m veronica --data-dir PATH         Custom notes/reminders/logs directory
python -m veronica --add-startup --startup-args --gui --reminders
```

## Folder structure

```text
Veronica/
├── veronica/                  # Python package
│   ├── __main__.py            # CLI entry point
│   ├── assistant.py           # Assistant orchestration
│   ├── core_commands.py       # App/search/weather/screenshot/WhatsApp router
│   ├── reminders.py           # JSON-backed reminders
│   ├── system_stats.py        # Optional psutil system reports
│   ├── news.py                # Optional NewsAPI headlines
│   ├── dictation.py           # Auto-type controller
│   ├── ocr.py                 # Screen OCR
│   ├── fun.py                 # Jokes, quiz, focus, productivity
│   ├── security.py            # Webcam security shield
│   ├── mobile.py              # Same-WiFi Flask server
│   ├── gui.py                 # Popup/tray helpers
│   ├── speech.py              # Edge TTS voice helper
│   └── startup.py             # Windows Startup shortcut helper
├── scripts/
│   ├── install_windows_full.bat
│   ├── start_veronica.bat
│   └── add_to_startup.bat
├── requirements-all.txt       # All optional integrations
├── requirements-*.txt         # Targeted optional groups
├── tests/test_assistant.py
└── README.md
```

## Coming later ideas

- Gmail integration for reading and sending mail
- Google Calendar event read/add flows
- Spotify music control
- WhatsApp incoming-message watcher
