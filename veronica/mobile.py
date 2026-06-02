"""Optional VEER-style mobile web server for Veronica.

The server lets another device on the same network send commands to the local
assistant from a browser. Flask is optional and loaded only when this feature is
started.
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

MOBILE_UI = """<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0b1020">
<title>{assistant_name} Assistant</title>
<style>
  :root {{
    --bg: #060b16;
    --panel: #0e1629;
    --panel-soft: #121e37;
    --txt: #e7efff;
    --muted: #90a0c2;
    --line: #243451;
    --accent: #52f7d4;
    --accent-2: #6ea8ff;
    --danger: #ff6b80;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: radial-gradient(circle at 20% 0%, #152440 0%, var(--bg) 45%);
    color: var(--txt);
    min-height: 100vh;
    padding: 16px;
  }}
  .shell {{
    max-width: 720px;
    margin: 0 auto;
    background: linear-gradient(180deg, rgba(14,22,41,.9), rgba(10,16,30,.88));
    border: 1px solid var(--line);
    border-radius: 22px;
    overflow: hidden;
    box-shadow: 0 18px 44px rgba(0,0,0,.45);
  }}
  .header {{
    padding: 18px 20px;
    border-bottom: 1px solid var(--line);
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }}
  .brand h1 {{ font-size: 21px; letter-spacing: .11em; color: var(--accent); }}
  .brand p {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}
  .online {{
    border: 1px solid rgba(82,247,212,.35);
    color: var(--accent);
    border-radius: 999px;
    font-size: 11px;
    padding: 6px 10px;
    background: rgba(82,247,212,.08);
    white-space: nowrap;
  }}
  .content {{ padding: 16px; display: grid; gap: 14px; }}
  .response-box {{
    background: var(--panel-soft);
    border: 1px solid var(--line);
    border-radius: 14px;
    min-height: 110px;
    padding: 14px;
    font-size: 15px;
    line-height: 1.6;
    white-space: pre-wrap;
  }}
  .response-box.active {{ border-color: rgba(82,247,212,.55); }}
  .loader {{ display:none; color: var(--accent); font-size: 13px; text-align: center; }}
  .input-row {{ display: grid; grid-template-columns: 1fr auto; gap: 10px; }}
  input[type=text] {{
    border-radius: 12px;
    border: 1px solid var(--line);
    background: #0b1426;
    color: var(--txt);
    font-size: 15px;
    padding: 13px 14px;
    outline: none;
  }}
  input[type=text]:focus {{ border-color: var(--accent-2); box-shadow: 0 0 0 3px rgba(110,168,255,.2); }}
  button {{
    border: 1px solid rgba(82,247,212,.3);
    border-radius: 12px;
    background: linear-gradient(135deg, rgba(82,247,212,.18), rgba(110,168,255,.18));
    color: var(--txt);
    font-weight: 700;
    padding: 13px 16px;
    cursor: pointer;
  }}
  button:active {{ transform: translateY(1px); }}
  .section-title {{ font-size: 11px; color: var(--muted); letter-spacing: .12em; text-transform: uppercase; }}
  .quick-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 9px; }}
  .quick-btn {{
    border-radius: 11px;
    border: 1px solid var(--line);
    background: #0c162c;
    color: var(--txt);
    padding: 12px;
    text-align: left;
    font-size: 13px;
    cursor: pointer;
  }}
  .quick-btn small {{ color: var(--muted); display:block; margin-top: 2px; font-size: 11px; }}
  .quick-btn:active {{ border-color: var(--accent-2); }}
  .footer {{
    border-top: 1px solid var(--line);
    padding: 10px 16px;
    font-size: 11px;
    color: var(--muted);
    display: flex;
    justify-content: space-between;
  }}
  @media (max-width: 520px) {{
    .header {{ flex-direction: column; align-items: flex-start; }}
    .quick-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<div class="shell">
  <div class="header">
    <div class="brand">
      <h1>{assistant_name}</h1>
      <p>VEER-style mobile control panel</p>
    </div>
    <div class="online">● Online</div>
  </div>

  <div class="content">
    <div class="response-box" id="response">Namaste! Kya hukum hai?</div>
    <div class="loader" id="loader">Processing command...</div>

    <div class="input-row">
      <input type="text" id="cmd-input" placeholder="Command likho..." onkeydown="if(event.key==='Enter') sendCmd()">
      <button onclick="sendCmd()">Send</button>
    </div>

    <div class="section-title">Quick Commands</div>
    <div class="quick-grid">
      <div class="quick-btn" onclick="quick('time batao')">🕐 Time<small>Current time</small></div>
      <div class="quick-btn" onclick="quick('weather batao')">🌤 Weather<small>Local weather</small></div>
      <div class="quick-btn" onclick="quick('chrome kholo')">🌐 Chrome<small>Open browser</small></div>
      <div class="quick-btn" onclick="quick('screenshot lo')">📸 Screenshot<small>Capture screen</small></div>
      <div class="quick-btn" onclick="quick('battery status')">🔋 Battery<small>Power status</small></div>
      <div class="quick-btn" onclick="quick('joke sunao')">😄 Joke<small>Light mood</small></div>
      <div class="quick-btn" onclick="quick('show memory')">🧠 Memory<small>Saved memory</small></div>
      <div class="quick-btn" onclick="quick('advance next')">🚀 Advance<small>Next roadmap step</small></div>
    </div>
  </div>

  <div class="footer">
    <span>Same WiFi required</span>
    <span>/status • /command • /security/snapshot</span>
  </div>
<meta name="theme-color" content="#0a0a0a">
<title>{assistant_name} Assistant</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0a0a0a; color: #ffffff; min-height: 100vh;
    display: flex; flex-direction: column; padding: 20px;
  }}
  .header {{
    text-align: center; padding: 24px 0 16px;
    border-bottom: 1px solid #1e1e1e; margin-bottom: 20px;
  }}
  .header h1 {{ font-size: 28px; letter-spacing: 4px; color: #00f5c4; }}
  .header p  {{ font-size: 12px; color: #555; margin-top: 4px; }}
  .status-dot {{
    display: inline-block; width: 8px; height: 8px;
    background: #00f5c4; border-radius: 50%; margin-right: 6px;
    animation: pulse 2s infinite;
  }}
  @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.3}} }}
  .response-box {{
    background: #111; border: 1px solid #1e1e1e; border-radius: 12px;
    padding: 16px; margin-bottom: 20px; min-height: 80px;
    font-size: 15px; line-height: 1.6; color: #ccc;
  }}
  .response-box.active {{ border-color: #00f5c4; color: #fff; }}
  .input-row {{ display: flex; gap: 10px; margin-bottom: 16px; }}
  input[type=text] {{
    flex: 1; background: #111; border: 1px solid #2e2e2e;
    color: #fff; padding: 14px 16px; border-radius: 10px;
    font-size: 16px; outline: none;
  }}
  input[type=text]:focus {{ border-color: #00f5c4; }}
  input::placeholder {{ color: #444; }}
  button {{
    background: #00f5c4; color: #000; border: none;
    padding: 14px 20px; border-radius: 10px;
    font-size: 15px; font-weight: 600; cursor: pointer;
  }}
  button:active {{ opacity: 0.8; transform: scale(0.97); }}
  .quick-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
    margin-bottom: 20px;
  }}
  .quick-btn {{
    background: #111; border: 1px solid #2e2e2e; color: #ccc;
    padding: 14px 10px; border-radius: 10px; font-size: 14px;
    cursor: pointer; text-align: center;
  }}
  .quick-btn:active {{ border-color: #00f5c4; color: #00f5c4; }}
  .section-title {{ font-size: 11px; color: #444; letter-spacing: .1em;
    text-transform: uppercase; margin-bottom: 10px; }}
  .loader {{ display:none; text-align:center; color:#00f5c4; font-size:13px; padding:8px 0; }}
</style>
</head>
<body>
<div class="header">
  <h1>{assistant_name}</h1>
  <p><span class="status-dot"></span>Personal Assistant — Online</p>
</div>

<div class="response-box" id="response">Namaste! Kya hukum hai?</div>
<div class="loader" id="loader">Soch raha hoon...</div>

<div class="input-row">
  <input type="text" id="cmd-input" placeholder="Command likho..." onkeydown="if(event.key==='Enter') sendCmd()">
  <button onclick="sendCmd()">Bhejo</button>
</div>

<div class="section-title">Quick Commands</div>
<div class="quick-grid">
  <div class="quick-btn" onclick="quick('time batao')">🕐 Time</div>
  <div class="quick-btn" onclick="quick('weather batao')">🌤 Weather</div>
  <div class="quick-btn" onclick="quick('chrome kholo')">🌐 Chrome</div>
  <div class="quick-btn" onclick="quick('screenshot lo')">📸 Screenshot</div>
  <div class="quick-btn" onclick="quick('battery status')">🔋 Battery</div>
  <div class="quick-btn" onclick="quick('joke sunao')">😄 Joke</div>
  <div class="quick-btn" onclick="quick('laptop lock karo')">🔒 Lock</div>
  <div class="quick-btn" onclick="quick('date batao')">📅 Date</div>
</div>

<script>
async function sendCmd() {{
  const input = document.getElementById('cmd-input');
  const cmd = input.value.trim();
  if (!cmd) return;
  input.value = '';
  await execute(cmd);
}}
async function quick(cmd) {{ await execute(cmd); }}
async function execute(cmd) {{
  const box = document.getElementById('response');
  const loader = document.getElementById('loader');
  box.classList.remove('active');
  loader.style.display = 'block';
  try {{
    const res = await fetch('/command', {{
      method: 'POST',
      headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify({{command: cmd}})
    }});
    const data = await res.json();
    box.innerHTML = data.response || 'Koi jawab nahi mila.';
    box.classList.add('active');
  }} catch(e) {{
    box.innerHTML = 'Error: Laptop se connect nahi ho saka.';
  }} finally {{
    loader.style.display = 'none';
  }}
}}
</script>
</body>
</html>"""


def create_mobile_app(
    assistant: Assistant,
    speak_responses: bool = False,
    speaker: Callable[[str], None] | None = None,
    flask_module: Any | None = None,
):
    """Create a Flask app bound to an Assistant instance."""
    flask = flask_module or _optional_module("flask")
    if flask is None:
        return None

    app = flask.Flask(__name__)

    @app.route("/")
    def index():
        return flask.render_template_string(MOBILE_UI.format(assistant_name=assistant.config.name))

    @app.route("/command", methods=["POST"])
    def command():
        data = flask.request.get_json(silent=True) or {}
        user_command = str(data.get("command", "")).strip()
        if not user_command:
            return flask.jsonify({"response": "Command empty hai."})
        response = assistant.respond(user_command)
        if speak_responses and speaker is not None and response != "Powering down. Goodbye.":
            threading.Thread(target=speaker, args=(response,), daemon=True).start()
        return flask.jsonify({"response": response})

    @app.route("/openclaw/webhook", methods=["POST"])
    def openclaw_webhook():
        data = flask.request.get_json(silent=True) or {}
        user_command = ""
        if "text" in data:
            user_command = str(data["text"]).strip()
        elif "message" in data and isinstance(data["message"], dict):
            user_command = str(data["message"].get("content", "")).strip()
            
        if not user_command:
            return flask.jsonify({"error": "No text found in payload"}), 400
            
        response = assistant.respond(user_command)
        
        if speak_responses and speaker is not None and response != "Powering down. Goodbye.":
            threading.Thread(target=speaker, args=(response,), daemon=True).start()
            
        return flask.jsonify({
            "messages": [
                {
                    "type": "text",
                    "text": response
                }
            ]
        })

    @app.route("/status")
    def status():
        return flask.jsonify(mobile_status(assistant.config.name))

    @app.route("/security/snapshot")
    def snapshot():
        return flask.jsonify(security_snapshot(assistant.config.data_dir))

    return app


def run_mobile_server(
    assistant: Assistant,
    host: str = "0.0.0.0",
    port: int = 5000,
    speak_responses: bool = False,
    speaker: Callable[[str], None] | None = None,
) -> str:
    """Run the optional mobile Flask server."""
    app = create_mobile_app(assistant, speak_responses=speak_responses, speaker=speaker)
    if app is None:
        return "Mobile server ke liye Flask install karo: pip install -r requirements-mobile.txt"
    ip_address = get_local_ip()
    print("\n[Veronica Mobile]: Server chal raha hai!")
    print(f"[Veronica Mobile]: Phone pe yeh open karo: http://{ip_address}:{port}")
    print("[Veronica Mobile]: Same WiFi pe hona chahiye.\n")
    app.run(host=host, port=port, debug=False)
    return "Mobile server stopped."


def mobile_status(assistant_name: str = "Veronica") -> dict[str, str]:
    """Return mobile server status metadata."""
    return {"status": "online", "name": assistant_name, "ip": get_local_ip()}


def security_snapshot(data_dir: Path) -> dict[str, str | int | None]:
    """Return the latest intruder snapshot filename from the local data directory."""
    photos_dir = data_dir / "logs" / "intruders"
    if not photos_dir.exists():
        return {"latest": None, "count": 0}
    files = sorted(path.name for path in photos_dir.iterdir() if path.suffix.lower() == ".jpg")
    return {"latest": files[-1] if files else None, "count": len(files)}


def get_local_ip() -> str:
    """Best-effort local IP address for same-WiFi mobile access."""
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except OSError:
        return "127.0.0.1"


def _optional_module(module_name: str):
    if importlib.util.find_spec(module_name) is None:
        return None
    return importlib.import_module(module_name)
