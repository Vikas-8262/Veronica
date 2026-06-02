"""VEER-style mobile web server for Veronica — Enhanced Edition.

Features:
- JARVIS-style dark UI with animations
- Voice input (mobile mic se bolo)
- Quick command buttons
- QR code for easy connection
- Real-time battery/system status
- Same WiFi pe koi bhi device se control
"""

from __future__ import annotations

import importlib
import importlib.util
import socket
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .assistant import Assistant

# ═══════════════════════════════════════════════════════════════
# MOBILE UI HTML
# ═══════════════════════════════════════════════════════════════

MOBILE_UI = """<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<meta name="theme-color" content="#050510">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>{assistant_name}</title>
<style>
  :root {{
    --primary: #00d4ff;
    --primary-dim: #003344;
    --bg: #050510;
    --bg2: #0a0a1a;
    --bg3: #0f0f22;
    --text: #e0e0e0;
    --text-dim: #666688;
    --green: #00ff88;
    --red: #ff4466;
    --border: #1a1a33;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    overflow-x: hidden;
  }}

  /* ── Header ── */
  .header {{
    background: linear-gradient(180deg, #000020 0%, var(--bg) 100%);
    padding: 20px 16px 14px;
    text-align: center;
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(10px);
  }}
  .header h1 {{
    font-size: 22px;
    letter-spacing: 6px;
    color: var(--primary);
    text-shadow: 0 0 20px rgba(0,212,255,0.5);
    font-weight: 700;
  }}
  .status-row {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    margin-top: 6px;
  }}
  .dot {{
    width: 7px; height: 7px;
    background: var(--green);
    border-radius: 50%;
    animation: pulse 2s infinite;
    box-shadow: 0 0 6px var(--green);
  }}
  .status-text {{ font-size: 11px; color: var(--text-dim); letter-spacing: 1px; }}
  @keyframes pulse {{ 0%,100%{{opacity:1;transform:scale(1)}} 50%{{opacity:.4;transform:scale(0.8)}} }}

  /* ── Response box ── */
  .response-wrap {{ padding: 12px 16px 0; }}
  .response-box {{
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 16px;
    min-height: 90px;
    font-size: 15px;
    line-height: 1.6;
    color: #aaa;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
  }}
  .response-box::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--primary), transparent);
    opacity: 0;
    transition: opacity 0.3s;
  }}
  .response-box.active {{
    border-color: var(--primary);
    color: var(--text);
    box-shadow: 0 0 20px rgba(0,212,255,0.1);
  }}
  .response-box.active::before {{ opacity: 1; }}
  .response-label {{
    font-size: 10px;
    color: var(--primary);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 6px;
  }}

  /* ── Loader ── */
  .loader {{
    display: none;
    text-align: center;
    padding: 8px;
    color: var(--primary);
    font-size: 12px;
    letter-spacing: 2px;
  }}
  .loader-dots span {{
    display: inline-block;
    width: 6px; height: 6px;
    background: var(--primary);
    border-radius: 50%;
    margin: 0 2px;
    animation: bounce 1.2s infinite;
  }}
  .loader-dots span:nth-child(2) {{ animation-delay: 0.2s; }}
  .loader-dots span:nth-child(3) {{ animation-delay: 0.4s; }}
  @keyframes bounce {{ 0%,80%,100%{{transform:scale(0)}} 40%{{transform:scale(1)}} }}

  /* ── Input area ── */
  .input-wrap {{
    padding: 12px 16px;
    display: flex;
    gap: 8px;
    align-items: center;
    background: var(--bg);
    position: sticky;
    bottom: 0;
    border-top: 1px solid var(--border);
  }}
  .cmd-input {{
    flex: 1;
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 13px 15px;
    border-radius: 12px;
    font-size: 15px;
    outline: none;
    transition: border-color 0.2s;
  }}
  .cmd-input:focus {{ border-color: var(--primary); }}
  .cmd-input::placeholder {{ color: var(--text-dim); }}

  .btn {{
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    padding: 13px 16px;
  }}
  .btn:active {{ transform: scale(0.93); opacity: 0.8; }}
  .btn-send {{ background: var(--primary); color: #000; }}
  .btn-mic {{
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--primary);
    font-size: 18px;
  }}
  .btn-mic.listening {{
    background: rgba(255,68,102,0.15);
    border-color: var(--red);
    color: var(--red);
    animation: mic-pulse 0.8s infinite;
  }}
  @keyframes mic-pulse {{ 0%,100%{{box-shadow:0 0 0 0 rgba(255,68,102,0.4)}} 50%{{box-shadow:0 0 0 8px rgba(255,68,102,0)}} }}

  /* ── Scroll area ── */
  .scroll-area {{
    flex: 1;
    overflow-y: auto;
    padding-bottom: 8px;
  }}

  /* ── Section title ── */
  .section-title {{
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 14px 16px 8px;
  }}

  /* ── Quick grid ── */
  .quick-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    padding: 0 16px;
  }}
  .quick-btn {{
    background: var(--bg2);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 14px 10px;
    border-radius: 12px;
    font-size: 13px;
    cursor: pointer;
    text-align: center;
    transition: all 0.2s;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }}
  .quick-btn:active {{
    border-color: var(--primary);
    color: var(--primary);
    background: var(--primary-dim);
    transform: scale(0.96);
  }}
  .quick-btn .icon {{ font-size: 20px; }}
  .quick-btn .label {{ font-size: 11px; color: var(--text-dim); }}

  /* ── Chat history ── */
  .chat-wrap {{ padding: 0 16px; }}
  .chat-msg {{
    margin-bottom: 8px;
    padding: 10px 14px;
    border-radius: 12px;
    font-size: 13px;
    line-height: 1.5;
    max-width: 85%;
  }}
  .chat-msg.user {{
    background: var(--primary-dim);
    border: 1px solid var(--primary);
    color: var(--primary);
    margin-left: auto;
    border-bottom-right-radius: 4px;
  }}
  .chat-msg.veronica {{
    background: var(--bg2);
    border: 1px solid var(--border);
    color: var(--text);
    border-bottom-left-radius: 4px;
  }}

  /* ── Status cards ── */
  .status-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    padding: 0 16px;
  }}
  .stat-card {{
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px;
    text-align: center;
  }}
  .stat-label {{ font-size: 10px; color: var(--text-dim); letter-spacing: 1px; }}
  .stat-value {{ font-size: 18px; font-weight: 700; color: var(--primary); margin-top: 4px; }}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <h1>⚡ {assistant_name}</h1>
  <div class="status-row">
    <div class="dot"></div>
    <span class="status-text">ONLINE — SAME WIFI</span>
  </div>
</div>

<div class="scroll-area" id="scroll-area">

  <!-- Response -->
  <div class="response-wrap">
    <div class="response-label">▸ VERONICA</div>
    <div class="response-box" id="response">Namaste! Kya hukum hai, Vikas?</div>
    <div class="loader" id="loader">
      <div class="loader-dots">
        <span></span><span></span><span></span>
      </div>
    </div>
  </div>

  <!-- System Status -->
  <div class="section-title">System Status</div>
  <div class="status-grid">
    <div class="stat-card">
      <div class="stat-label">🔋 BATTERY</div>
      <div class="stat-value" id="stat-battery">--</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">🕐 TIME</div>
      <div class="stat-value" id="stat-time">--</div>
    </div>
  </div>

  <!-- Quick Commands -->
  <div class="section-title">Quick Commands</div>
  <div class="quick-grid">
    <div class="quick-btn" onclick="quick('time batao')">
      <span class="icon">🕐</span><span class="label">Time</span>
    </div>
    <div class="quick-btn" onclick="quick('battery status')">
      <span class="icon">🔋</span><span class="label">Battery</span>
    </div>
    <div class="quick-btn" onclick="quick('chrome kholo')">
      <span class="icon">🌐</span><span class="label">Chrome</span>
    </div>
    <div class="quick-btn" onclick="quick('screenshot lo')">
      <span class="icon">📸</span><span class="label">Screenshot</span>
    </div>
    <div class="quick-btn" onclick="quick('volume mute karo')">
      <span class="icon">🔇</span><span class="label">Mute</span>
    </div>
    <div class="quick-btn" onclick="quick('volume badhaao')">
      <span class="icon">🔊</span><span class="label">Volume Up</span>
    </div>
    <div class="quick-btn" onclick="quick('joke sunao')">
      <span class="icon">😄</span><span class="label">Joke</span>
    </div>
    <div class="quick-btn" onclick="quick('lock karo')">
      <span class="icon">🔒</span><span class="label">Lock PC</span>
    </div>
    <div class="quick-btn" onclick="quick('vscode kholo')">
      <span class="icon">💻</span><span class="label">VS Code</span>
    </div>
    <div class="quick-btn" onclick="quick('system status')">
      <span class="icon">📊</span><span class="label">System</span>
    </div>
    <div class="quick-btn" onclick="quick('minimize karo')">
      <span class="icon">⬇️</span><span class="label">Minimize</span>
    </div>
    <div class="quick-btn" onclick="quick('aaj ka report')">
      <span class="icon">📋</span><span class="label">Report</span>
    </div>
  </div>

  <!-- Chat History -->
  <div class="section-title">Chat History</div>
  <div class="chat-wrap" id="chat-history"></div>

</div>

<!-- Input -->
<div class="input-wrap">
  <button class="btn btn-mic" id="mic-btn" onclick="startVoice()" title="Voice input">🎤</button>
  <input
    type="text"
    id="cmd-input"
    class="cmd-input"
    placeholder="Command likho ya mic se bolo..."
    onkeydown="if(event.key==='Enter') sendCmd()"
    autocomplete="off"
  >
  <button class="btn btn-send" onclick="sendCmd()">Send</button>
</div>

<script>
// ── State ──
let chatHistory = [];
let isListening = false;
let recognition = null;

// ── Send command ──
async function sendCmd() {{
  const input = document.getElementById('cmd-input');
  const cmd = input.value.trim();
  if (!cmd) return;
  input.value = '';
  await execute(cmd);
}}

async function quick(cmd) {{
  await execute(cmd);
}}

async function execute(cmd) {{
  const box = document.getElementById('response');
  const loader = document.getElementById('loader');

  // Add to chat
  addChat('user', cmd);

  box.classList.remove('active');
  loader.style.display = 'block';

  try {{
    const res = await fetch('/command', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{command: cmd}})
    }});
    const data = await res.json();
    const reply = data.response || 'Koi jawab nahi mila.';
    box.textContent = reply;
    box.classList.add('active');
    addChat('veronica', reply);

    // Vibrate on response (mobile)
    if (navigator.vibrate) navigator.vibrate(30);

  }} catch(e) {{
    box.textContent = '❌ Laptop se connect nahi ho saka. Same WiFi pe ho?';
    box.classList.add('active');
  }} finally {{
    loader.style.display = 'none';
    // Scroll to response
    document.getElementById('scroll-area').scrollTo({{top: 0, behavior: 'smooth'}});
  }}
}}

// ── Chat history ──
function addChat(who, text) {{
  chatHistory.push({{who, text}});
  if (chatHistory.length > 20) chatHistory.shift();
  renderChat();
}}

function renderChat() {{
  const wrap = document.getElementById('chat-history');
  wrap.innerHTML = chatHistory.slice().reverse().map(m =>
    `<div class="chat-msg ${{m.who}}">${{m.text}}</div>`
  ).join('');
}}

// ── Voice input ──
function startVoice() {{
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
    alert('Aapke browser mein voice input support nahi hai. Chrome use karo.');
    return;
  }}

  if (isListening) {{
    recognition && recognition.stop();
    return;
  }}

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = 'hi-IN';
  recognition.continuous = false;
  recognition.interimResults = false;

  const micBtn = document.getElementById('mic-btn');

  recognition.onstart = () => {{
    isListening = true;
    micBtn.classList.add('listening');
    micBtn.textContent = '⏹';
  }};

  recognition.onresult = (e) => {{
    const transcript = e.results[0][0].transcript;
    document.getElementById('cmd-input').value = transcript;
    execute(transcript);
  }};

  recognition.onerror = (e) => {{
    console.error('Voice error:', e.error);
  }};

  recognition.onend = () => {{
    isListening = false;
    micBtn.classList.remove('listening');
    micBtn.textContent = '🎤';
  }};

  recognition.start();
}}

// ── Status updates ──
async function updateStatus() {{
  try {{
    const res = await fetch('/status');
    const data = await res.json();
    if (data.battery) document.getElementById('stat-battery').textContent = data.battery;
    if (data.time)    document.getElementById('stat-time').textContent    = data.time;
  }} catch(e) {{}}
}}

// Update time locally every second
function updateTime() {{
  const now = new Date();
  const h = now.getHours().toString().padStart(2,'0');
  const m = now.getMinutes().toString().padStart(2,'0');
  document.getElementById('stat-time').textContent = `${{h}}:${{m}}`;
}}

// Init
updateStatus();
setInterval(updateStatus, 30000);
setInterval(updateTime, 1000);
updateTime();
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# FLASK APP
# ═══════════════════════════════════════════════════════════════

def create_mobile_app(
    assistant: Assistant,
    speak_responses: bool = False,
    speaker: Callable[[str], None] | None = None,
    flask_module: Any | None = None,
):
    """Create Flask app for mobile control."""
    flask = flask_module or _optional_module("flask")
    if flask is None:
        return None

    app = flask.Flask(__name__)

    @app.route("/")
    def index():
        return flask.render_template_string(
            MOBILE_UI.format(assistant_name=assistant.config.name)
        )

    @app.route("/command", methods=["POST"])
    def command():
        data = flask.request.get_json(silent=True) or {}
        user_command = str(data.get("command", "")).strip()
        if not user_command:
            return flask.jsonify({"response": "Command empty hai."})
        response = assistant.respond(user_command)
        if speak_responses and speaker is not None:
            threading.Thread(target=speaker, args=(response,), daemon=True).start()
        return flask.jsonify({"response": response})

    @app.route("/status")
    def status():
        import datetime as dt
        result = {
            "status": "online",
            "name": assistant.config.name,
            "ip": get_local_ip(),
            "time": dt.datetime.now().strftime("%H:%M"),
        }
        # Battery status
        try:
            import psutil
            batt = psutil.sensors_battery()
            if batt:
                charging = "⚡" if batt.power_plugged else "🔋"
                result["battery"] = f"{charging}{int(batt.percent)}%"
        except Exception:
            pass
        return flask.jsonify(result)

    @app.route("/qr")
    def qr_page():
        """Show QR code page for easy mobile connection."""
        ip = get_local_ip()
        port = flask.request.host.split(":")[-1] if ":" in flask.request.host else "5000"
        url = f"http://{ip}:{port}"
        return flask.render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
          <title>Connect Veronica</title>
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <style>
            body {{ background:#050510; color:#00d4ff; font-family:monospace;
                   text-align:center; padding:40px 20px; }}
            h2 {{ font-size:20px; letter-spacing:4px; margin-bottom:20px; }}
            .url {{ background:#0a0a1a; border:1px solid #00d4ff; border-radius:12px;
                   padding:16px; font-size:16px; margin:20px auto; max-width:300px;
                   word-break:break-all; }}
            img {{ border:4px solid #00d4ff; border-radius:12px; margin:20px auto;
                  display:block; }}
            p {{ color:#666; font-size:12px; margin-top:10px; }}
          </style>
        </head>
        <body>
          <h2>⚡ VERONICA MOBILE</h2>
          <p>Phone se yeh URL kholo:</p>
          <div class="url">{url}</div>
          <img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url}"
               width="200" height="200" alt="QR Code">
          <p>Same WiFi pe hona chahiye</p>
        </body>
        </html>
        """)

    @app.route("/desktop")
    def desktop():
        desktop_path = Path(r"C:\Users\admin\Downloads\Veronica-codex-create-ai-assistant-like-jarvis\Veronica-codex-create-ai-assistant-like-jarvis\veronica\Veronica_desktop_ui.HTML")
        if desktop_path.exists():
            return desktop_path.read_text(encoding="utf-8")
        return "Desktop UI file nahi mili.", 404

    return app


def run_mobile_server(
    assistant: Assistant,
    host: str = "0.0.0.0",
    port: int = 5000,
    speak_responses: bool = False,
    speaker: Callable[[str], None] | None = None,
) -> str:
    """Start mobile Flask server."""
    app = create_mobile_app(
        assistant, speak_responses=speak_responses, speaker=speaker
    )
    if app is None:
        return "Flask install karo: pip install flask"

    ip = get_local_ip()
    print("\n" + "═" * 45)
    print("  📱 VERONICA MOBILE SERVER READY!")
    print("═" * 45)
    print(f"  🌐 Phone mein kholo: http://{ip}:{port}")
    print(f"  📷 QR Code:          http://{ip}:{port}/qr")
    print("  ⚠️  Same WiFi pe hona chahiye!")
    print("═" * 45 + "\n")

    app.run(host=host, port=port, debug=False, use_reloader=False)
    return "Mobile server stopped."


# ── Helpers ──

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def mobile_status(assistant_name: str = "Veronica") -> dict:
    return {"status": "online", "name": assistant_name, "ip": get_local_ip()}


def security_snapshot(data_dir: Path) -> dict:
    photos_dir = data_dir / "logs" / "intruders"
    if not photos_dir.exists():
        return {"latest": None, "count": 0}
    files = sorted(p.name for p in photos_dir.iterdir() if p.suffix.lower() == ".jpg")
    return {"latest": files[-1] if files else None, "count": len(files)}


def _optional_module(module_name: str):
    if importlib.util.find_spec(module_name) is None:
        return None
    return importlib.import_module(module_name)
