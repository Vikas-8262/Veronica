"""Optional VEER-style mobile web server for Veronica.

The server lets another device on the same network send commands to the local
assistant from a browser. Flask is optional and loaded only when this feature is
started.
"""

from __future__ import annotations

import os
import json
import importlib
import importlib.util
import socket
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .assistant import Assistant

MOBILE_UI = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#030712">
<title>{assistant_name} Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;700&family=Orbitron:wght@500;700;900&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #030712;
    --card-bg: rgba(17, 24, 39, 0.7);
    --border: rgba(82, 247, 212, 0.15);
    --accent: #10b981;
    --accent-glow: rgba(16, 185, 129, 0.4);
    --cpu-glow: #06b6d4;
    --ram-glow: #8b5cf6;
    --whatsapp-glow: #ec4899;
    --safety-glow: #f59e0b;
    --jobs-glow: #10b981;
    --text-primary: #f3f4f6;
    --text-muted: #9ca3af;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  body {{
    font-family: 'Inter', sans-serif;
    background: radial-gradient(circle at 50% 50%, #0c1220 0%, var(--bg) 100%);
    color: var(--text-primary);
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
    overflow-x: hidden;
  }}

  body::before {{
    content: " ";
    display: block;
    position: fixed;
    top: 0; left: 0; bottom: 0; right: 0;
    background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
    z-index: 9999;
    opacity: 0.15;
    pointer-events: none;
    background-size: 100% 4px, 6px 100%;
  }}

  .dashboard-container {{
    width: 100%;
    max-width: 1000px;
    background: rgba(10, 15, 30, 0.8);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    border-radius: 24px;
    box-shadow: 0 0 50px rgba(6, 182, 212, 0.15);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }}

  .top-bar {{
    padding: 20px 30px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(3, 7, 18, 0.4);
    flex-wrap: wrap;
    gap: 15px;
  }}

  .brand {{
    display: flex;
    align-items: center;
    gap: 15px;
  }}

  .brand h1 {{
    font-family: 'Orbitron', sans-serif;
    font-size: 24px;
    font-weight: 900;
    letter-spacing: 2px;
    background: linear-gradient(to right, #00f5c4, #3b82f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 15px rgba(0, 245, 196, 0.2);
  }}

  .status-indicator {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--text-muted);
    font-family: 'Orbitron', sans-serif;
  }}

  .status-dot {{
    width: 8px;
    height: 8px;
    background-color: #00f5c4;
    border-radius: 50%;
    box-shadow: 0 0 8px #00f5c4;
    animation: pulse 2s infinite;
  }}

  @keyframes pulse {{
    0% {{ opacity: 0.3; box-shadow: 0 0 2px #00f5c4; }}
    50% {{ opacity: 1; box-shadow: 0 0 10px #00f5c4; }}
    100% {{ opacity: 0.3; box-shadow: 0 0 2px #00f5c4; }}
  }}

  .controls-row {{
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }}

  .voice-control {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}

  .switch {{
    position: relative;
    display: inline-block;
    width: 48px;
    height: 24px;
  }}

  .switch input {{
    opacity: 0;
    width: 0;
    height: 0;
  }}

  .slider {{
    position: absolute;
    cursor: pointer;
    top: 0; left: 0; right: 0; bottom: 0;
    background-color: #374151;
    transition: .4s;
    border-radius: 24px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }}

  .slider::before {{
    position: absolute;
    content: "";
    height: 16px;
    width: 16px;
    left: 3px;
    bottom: 3px;
    background-color: #9ca3af;
    transition: .4s;
    border-radius: 50%;
  }}

  input:checked + .slider {{
    background-color: rgba(6, 182, 212, 0.2);
    border-color: #06b6d4;
  }}

  input:checked + .slider::before {{
    transform: translateX(24px);
    background-color: #06b6d4;
    box-shadow: 0 0 8px #06b6d4;
  }}

  .main-grid {{
    display: grid;
    grid-template-columns: 1fr 1.2fr;
    border-bottom: 1px solid var(--border);
  }}

  @media (max-width: 800px) {{
    .main-grid {{
      grid-template-columns: 1fr;
    }}
  }}

  .left-panel {{
    padding: 30px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border-right: 1px solid var(--border);
    background: rgba(6, 11, 25, 0.2);
  }}

  @media (max-width: 800px) {{
    .left-panel {{
      border-right: none;
      border-bottom: 1px solid var(--border);
    }}
  }}

  .reactor-container {{
    position: relative;
    width: 260px;
    height: 260px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 25px;
  }}

  .telemetry-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
    width: 100%;
    max-width: 320px;
  }}

  .tel-card {{
    background: rgba(17, 24, 39, 0.4);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 15px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
  }}

  .tel-card:hover {{
    border-color: rgba(6, 182, 212, 0.4);
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(6, 182, 212, 0.05);
  }}

  .tel-label {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-muted);
    margin-bottom: 8px;
    font-family: 'Orbitron', sans-serif;
  }}

  .dial-svg {{
    width: 70px;
    height: 70px;
    transform: rotate(-90deg);
  }}

  .dial-bg {{
    fill: none;
    stroke: rgba(255, 255, 255, 0.05);
    stroke-width: 6;
  }}

  .dial-fill {{
    fill: none;
    stroke-width: 6;
    stroke-linecap: round;
    transition: stroke-dashoffset 0.6s ease;
  }}

  .cpu-fill {{
    stroke: var(--cpu-glow);
    filter: drop-shadow(0 0 3px var(--cpu-glow));
  }}

  .ram-fill {{
    stroke: var(--ram-glow);
    filter: drop-shadow(0 0 3px var(--ram-glow));
  }}

  .dial-val {{
    font-size: 14px;
    font-weight: 700;
    font-family: 'Orbitron', sans-serif;
    position: absolute;
    top: 50px;
    width: 100%;
    left: 0;
  }}

  .tel-badge {{
    font-family: 'Orbitron', sans-serif;
    font-size: 18px;
    font-weight: 700;
    margin-top: 5px;
  }}

  .whatsapp-badge {{
    color: var(--whatsapp-glow);
    text-shadow: 0 0 8px rgba(236, 72, 153, 0.4);
  }}

  .safety-badge {{
    color: var(--safety-glow);
    text-shadow: 0 0 8px rgba(245, 158, 11, 0.4);
  }}

  .jobs-badge {{
    color: var(--jobs-glow);
    text-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
  }}

  .right-panel {{
    padding: 30px;
    display: flex;
    flex-direction: column;
    height: 500px;
    background: rgba(3, 7, 18, 0.1);
  }}

  .tab-btn {{
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.05);
    color: var(--text-muted);
    padding: 8px 14px;
    border-radius: 8px;
    font-family: 'Orbitron', sans-serif;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.3s ease;
    outline: none;
  }}

  .tab-btn.active {{
    background: rgba(6, 182, 212, 0.12);
    border-color: #00f5c4;
    color: #00f5c4;
    box-shadow: 0 0 10px rgba(0, 245, 196, 0.15);
  }}

  .tab-content {{
    display: none;
  }}

  .tab-content.active {{
    display: flex;
    flex-direction: column;
    height: 100%;
    animation: fadeIn 0.3s ease;
  }}

  .console {{
    flex: 1;
    background: rgba(3, 7, 18, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 20px;
    overflow-y: auto;
    font-family: 'Courier New', Courier, monospace;
    font-size: 13px;
    line-height: 1.5;
    margin-bottom: 20px;
    scroll-behavior: smooth;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}

  .console::-webkit-scrollbar {{
    width: 6px;
  }}

  .console::-webkit-scrollbar-thumb {{
    background: rgba(255, 255, 255, 0.1);
    border-radius: 10px;
  }}

  .log-entry {{
    animation: fadeIn 0.3s ease;
  }}

  @keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(5px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}

  .log-time {{
    color: var(--text-muted);
    font-size: 10px;
    margin-right: 8px;
  }}

  .log-user {{
    color: #3b82f6;
    font-weight: 700;
  }}

  .log-assistant {{
    color: #00f5c4;
    font-weight: 700;
  }}

  .log-text {{
    white-space: pre-wrap;
  }}

  .input-container {{
    display: flex;
    gap: 12px;
    position: relative;
  }}

  input[type=text] {{
    flex: 1;
    background: rgba(17, 24, 39, 0.8);
    border: 1px solid var(--border);
    border-radius: 14px;
    color: var(--text-primary);
    padding: 16px 20px;
    font-size: 15px;
    outline: none;
    transition: all 0.3s ease;
  }}

  input[type=text]:focus {{
    border-color: #00f5c4;
    box-shadow: 0 0 15px rgba(0, 245, 196, 0.15);
  }}

  .send-btn {{
    background: linear-gradient(135deg, #00f5c4, #3b82f6);
    color: #030712;
    border: none;
    border-radius: 14px;
    padding: 0 20px;
    font-weight: 700;
    cursor: pointer;
    font-family: 'Orbitron', sans-serif;
    letter-spacing: 1px;
    transition: all 0.3s ease;
    box-shadow: 0 0 15px rgba(0, 245, 196, 0.2);
  }}

  .send-btn:hover {{
    transform: translateY(-1px);
    box-shadow: 0 0 20px rgba(0, 245, 196, 0.4);
  }}

  .send-btn:active {{
    transform: translateY(1px);
    opacity: 0.9;
  }}

  .bottom-actions {{
    padding: 25px 30px;
    background: rgba(3, 7, 18, 0.5);
  }}

  .actions-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 12px;
  }}

  .action-btn {{
    background: rgba(17, 24, 39, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 12px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }}

  .action-btn:hover {{
    background: rgba(6, 182, 212, 0.08);
    border-color: rgba(6, 182, 212, 0.3);
    transform: translateY(-2px);
  }}

  .action-icon {{
    font-size: 20px;
  }}

  .action-name {{
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    font-family: 'Orbitron', sans-serif;
    letter-spacing: 0.5px;
  }}

  .action-btn:hover .action-name {{
    color: #00f5c4;
  }}

  .pulse-ring {{
    position: absolute;
    border: 2px solid rgba(0, 245, 196, 0.4);
    border-radius: 50%;
    animation: rip 2.5s infinite ease-out;
    pointer-events: none;
  }}

  @keyframes rip {{
    0% {{ width: 140px; height: 140px; opacity: 1; }}
    100% {{ width: 280px; height: 280px; opacity: 0; }}
  }}
</style>
</head>
<body>
<div class="dashboard-container">
  <div class="top-bar">
    <div class="brand">
      <div class="status-dot"></div>
      <h1>{assistant_name}</h1>
    </div>
    
    <div class="controls-row">
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 11px; font-family: 'Orbitron', sans-serif; color: var(--text-muted);">Brain Node</span>
        <select id="brain-select" onchange="changeBrain()" style="background: #111827; color: #00f5c4; border: 1px solid var(--border); border-radius: 8px; padding: 6px 12px; font-size: 11px; font-family: 'Orbitron'; outline: none; cursor: pointer;">
          <option value="local">LOCAL (KEYWORDS)</option>
          <option value="ollama">OLLAMA (OFFLINE LLM)</option>
          <option value="gemini">GEMINI (CLOUD)</option>
        </select>
      </div>

      <div class="voice-control">
        <span style="font-size: 11px; font-family: 'Orbitron', sans-serif; color: var(--text-muted);">Vocal Audio</span>
        <label class="switch">
          <input type="checkbox" id="voice-toggle" checked>
          <span class="slider"></span>
        </label>
      </div>
    </div>
  </div>

  <div class="main-grid">
    <div class="left-panel">
      <div class="reactor-container">
        <div class="pulse-ring" id="reactor-pulse" style="animation-play-state: paused;"></div>
        <canvas id="reactor-canvas" width="260" height="260"></canvas>
      </div>

      <div class="telemetry-grid">
        <div class="tel-card">
          <div class="tel-label">CPU Core</div>
          <svg class="dial-svg">
            <circle class="dial-bg" cx="35" cy="35" r="28" />
            <circle class="dial-fill cpu-fill" id="cpu-dial" cx="35" cy="35" r="28" stroke-dasharray="175" stroke-dashoffset="175" />
          </svg>
          <div class="dial-val" id="cpu-val">0%</div>
        </div>

        <div class="tel-card">
          <div class="tel-label">RAM Pool</div>
          <svg class="dial-svg">
            <circle class="dial-bg" cx="35" cy="35" r="28" />
            <circle class="dial-fill ram-fill" id="ram-dial" cx="35" cy="35" r="28" stroke-dasharray="175" stroke-dashoffset="175" />
          </svg>
          <div class="dial-val" id="ram-val">0%</div>
        </div>

        <div class="tel-card">
          <div class="tel-label">Safety Shield</div>
          <div class="tel-badge safety-badge" id="safety-badge">MEDIUM</div>
        </div>

        <div class="tel-card">
          <div class="tel-label">Active Jobs</div>
          <div class="tel-badge jobs-badge" id="jobs-badge">0</div>
        </div>

        <div class="tel-card" style="grid-column: span 2;">
          <div class="tel-label" style="display:inline-block;">WhatsApp Inbox</div>
          <div class="tel-badge whatsapp-badge" id="whatsapp-badge" style="display:inline-block; margin-left: 10px;">0 UNREAD</div>
        </div>
      </div>
    </div>

    <div class="right-panel">
      <div class="tabs-header" style="display: flex; gap: 8px; margin-bottom: 15px; border-bottom: 1px solid var(--border); padding-bottom: 10px;">
        <button class="tab-btn active" id="btn-terminal" onclick="switchTab('terminal')">TERMINAL</button>
        <button class="tab-btn" id="btn-iot" onclick="switchTab('iot')">SMART HOME</button>
        <button class="tab-btn" id="btn-vision" onclick="switchTab('vision')">VISION</button>
        <button class="tab-btn" id="btn-scripts" onclick="switchTab('scripts')">SCRIPTS</button>
      </div>

      <!-- Tab 1: Terminal Console -->
      <div class="tab-content active" id="tab-terminal">
        <div class="console" id="console-logs">
          <div class="log-entry">
            <span class="log-time" id="init-time"></span>
            <span class="log-assistant">{assistant_name}:</span>
            <span class="log-text"> Jarvis-style web telemetry and neural speech node initialized. Waiting for input...</span>
          </div>
        </div>

        <div class="input-container">
          <input type="text" id="cmd-input" placeholder="Enter voice protocol command..." onkeydown="if(event.key==='Enter') sendCmd()">
          <button class="send-btn" id="send-button" onclick="sendCmd()">SEND</button>
        </div>
      </div>

      <!-- Tab 2: Smart Home IoT -->
      <div class="tab-content" id="tab-iot">
        <div id="iot-devices-list" style="display: flex; flex-direction: column; gap: 12px; overflow-y: auto; flex: 1; max-height: 380px; padding-right: 5px;">
          <div style="color: var(--text-muted); font-size: 13px; text-align: center; margin-top: 30px;">Loading smart home devices...</div>
        </div>
      </div>

      <!-- Tab 3: Webcam Vision Security -->
      <div class="tab-content" id="tab-vision">
        <div style="display: flex; flex-direction: column; gap: 15px; flex: 1; overflow-y: auto; padding-right: 5px;">
          <div class="tel-card" style="text-align: left;">
            <div class="tel-label">Diagnostics</div>
            <div style="margin-top: 10px; font-size: 13px; line-height: 1.6;">
              <div>• Registered Face Samples: <strong id="face-count-val" style="color: #00f5c4;">0</strong></div>
              <div>• WhatsApp Alerts: <strong id="wa-alert-val" style="color: #00f5c4;">Active (Same WiFi)</strong></div>
            </div>
          </div>
          <div style="display: flex; gap: 10px;">
            <button class="send-btn" onclick="describeScene()" style="flex: 1;">DESCRIBE SCENE</button>
            <button class="send-btn" onclick="quick('register face')" style="flex: 1; background: linear-gradient(135deg, #f59e0b, #ef4444); box-shadow: 0 0 15px rgba(245, 158, 11, 0.2);">SCAN FACE</button>
          </div>
          <div class="console" id="vision-logs" style="flex: 1; min-height: 150px; font-size: 12px;">
            <div style="color: var(--text-muted);">[Vision Core]: Ready to describe scenes...</div>
          </div>
        </div>
      </div>

      <!-- Tab 4: Generated Scripts Executor -->
      <div class="tab-content" id="tab-scripts">
        <div style="display: flex; flex-direction: column; gap: 15px; flex: 1; overflow-y: auto; padding-right: 5px;">
          <div id="scripts-list" style="display: flex; flex-direction: column; gap: 8px;">
            <div style="color: var(--text-muted); font-size: 13px; text-align: center;">Loading scripts...</div>
          </div>
          <div class="console" id="scripts-output" style="flex: 1; min-height: 150px; font-size: 12px;">
            <div style="color: var(--text-muted);">[Execution Core]: Output will load here on script run.</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="bottom-actions">
    <div class="actions-grid">
      <div class="action-btn" onclick="quick('time batao')">
        <span class="action-icon">🕐</span>
        <span class="action-name">Time Protocol</span>
      </div>
      <div class="action-btn" onclick="quick('weather status')">
        <span class="action-icon">🌤</span>
        <span class="action-name">Weather</span>
      </div>
      <div class="action-btn" onclick="quick('brain status')">
        <span class="action-icon">🧠</span>
        <span class="action-name">Brain Config</span>
      </div>
      <div class="action-btn" onclick="quick('safety status')">
        <span class="action-icon">🛡️</span>
        <span class="action-name">Safety Shield</span>
      </div>
      <div class="action-btn" onclick="quick('list jobs')">
        <span class="action-icon">⚙️</span>
        <span class="action-name">Background Jobs</span>
      </div>
      <div class="action-btn" onclick="quick('check whatsapp')">
        <span class="action-icon">📬</span>
        <span class="action-name">WhatsApp Inbox</span>
      </div>
    </div>
  </div>
</div>

<script>
  document.getElementById('init-time').innerText = new Date().toLocaleTimeString();

  let synthAvailable = 'speechSynthesis' in window;
  
  function speakText(text) {{
    if (!synthAvailable || !document.getElementById('voice-toggle').checked) return;
    
    let clean = text.replace(/[*#`_\-]/g, '').trim();
    window.speechSynthesis.cancel();
    
    let utterance = new SpeechSynthesisUtterance(clean);
    let voices = window.speechSynthesis.getVoices();
    let targetVoice = voices.find(v => v.lang.includes('en-') || v.lang.includes('hi-')) || voices[0];
    if (targetVoice) {{
      utterance.voice = targetVoice;
    }}
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  }}

  if (synthAvailable) {{
    window.speechSynthesis.getVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {{
      window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    }}
  }}

  function switchTab(tabId) {{
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    document.getElementById('btn-' + tabId).classList.add('active');
    document.getElementById('tab-' + tabId).classList.add('active');
  }}

  function addLog(sender, text, isUser = false) {{
    const consoleLogs = document.getElementById('console-logs');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    
    const timeSpan = document.createElement('span');
    timeSpan.className = 'log-time';
    timeSpan.innerText = new Date().toLocaleTimeString();
    
    const nameSpan = document.createElement('span');
    nameSpan.className = isUser ? 'log-user' : 'log-assistant';
    nameSpan.innerText = sender + ': ';
    
    const textSpan = document.createElement('span');
    textSpan.className = 'log-text';
    textSpan.innerText = ' ' + text;
    
    entry.appendChild(timeSpan);
    entry.appendChild(nameSpan);
    entry.appendChild(textSpan);
    consoleLogs.appendChild(entry);
    consoleLogs.scrollTop = consoleLogs.scrollHeight;
  }}

  let thinking = false;
  async function execute(cmd) {{
    if (thinking) return;
    thinking = true;
    
    const pulseRing = document.getElementById('reactor-pulse');
    const inputField = document.getElementById('cmd-input');
    const sendButton = document.getElementById('send-button');
    
    addLog('USER', cmd, true);
    inputField.disabled = true;
    sendButton.disabled = true;
    pulseRing.style.animationPlayState = 'running';
    
    try {{
      const res = await fetch('/command', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{command: cmd}})
      }});
      const data = await res.json();
      const answer = data.response || 'No response received.';
      addLog('{assistant_name}', answer, false);
      speakText(answer);
    }} catch(e) {{
      addLog('SYSTEM', 'Protocol error: Link to Veronica core failed.', false);
    }} finally {{
      thinking = false;
      inputField.disabled = false;
      sendButton.disabled = false;
      pulseRing.style.animationPlayState = 'paused';
      pollStats();
    }}
  }}

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

  async function changeBrain() {{
    const select = document.getElementById('brain-select');
    const brain = select.value;
    try {{
      const res = await fetch('/set_brain', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{brain: brain}})
      }});
      const data = await res.json();
      addLog('SYSTEM', 'Brain provider set to: ' + data.brain.toUpperCase(), false);
    }} catch(e) {{
      addLog('SYSTEM', 'Failed to update brain provider.', false);
    }}
  }}

  async function toggleDevice(entityId, state) {{
    try {{
      await fetch('/iot/toggle', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{entity_id: entityId, state: state}})
      }});
      pollStats();
    }} catch(e) {{
      console.warn('Failed to toggle device');
    }}
  }}

  async function setTemperature(entityId, temp) {{
    try {{
      await fetch('/command', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{command: `set temperature of ${entityId} to ${temp}`}})
      }});
      pollStats();
    }} catch(e) {{
      console.warn('Failed to set temperature');
    }}
  }}

  async function runScript(filename) {{
    const outputBox = document.getElementById('scripts-output');
    outputBox.innerHTML = '<div style="color: #00f5c4;">[System]: Executing script ' + filename + '...</div>';
    switchTab('scripts');
    try {{
      const res = await fetch('/scripts/run', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{filename: filename}})
      }});
      const data = await res.json();
      outputBox.innerText = data.output || 'No output returned.';
    }} catch(e) {{
      outputBox.innerText = 'Failed to execute script.';
    }}
  }}

  async function describeScene() {{
    const outputBox = document.getElementById('vision-logs');
    outputBox.innerHTML = '<div style="color: #00f5c4;">[System]: Activating camera and running scene diagnostics...</div>';
    switchTab('vision');
    try {{
      const res = await fetch('/camera/describe');
      const data = await res.json();
      outputBox.innerText = data.response || 'No description returned.';
      speakText(data.response);
    }} catch(e) {{
      outputBox.innerText = 'Failed to scan camera view.';
    }}
  }}

  function updateDial(id, value, fillId) {{
    const radius = 28;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (value / 100) * circumference;
    
    const dial = document.getElementById(fillId);
    dial.style.strokeDashoffset = offset;
    document.getElementById(id).innerText = Math.round(value) + '%';
  }}

  async function pollStats() {{
    try {{
      const res = await fetch('/status');
      const data = await res.json();
      
      if (data.cpu !== undefined) {{
        updateDial('cpu-val', data.cpu, 'cpu-dial');
      }}
      if (data.ram !== undefined) {{
        updateDial('ram-val', data.ram, 'ram-dial');
      }}
      if (data.safety_level !== undefined) {{
        const safetyBadge = document.getElementById('safety-badge');
        safetyBadge.innerText = data.safety_level.toUpperCase();
        if (data.safety_level.toLowerCase() === 'high') {{
          safetyBadge.style.color = '#ef4444';
          safetyBadge.style.textShadow = '0 0 8px rgba(239, 68, 68, 0.4)';
        }} else if (data.safety_level.toLowerCase() === 'low') {{
          safetyBadge.style.color = '#10b981';
          safetyBadge.style.textShadow = '0 0 8px rgba(16, 185, 129, 0.4)';
        }} else {{
          safetyBadge.style.color = '#f59e0b';
          safetyBadge.style.textShadow = '0 0 8px rgba(245, 158, 11, 0.4)';
        }}
      }}
      if (data.active_jobs !== undefined) {{
        document.getElementById('jobs-badge').innerText = data.active_jobs;
      }}
      if (data.unread_whatsapp !== undefined) {{
        document.getElementById('whatsapp-badge').innerText = data.unread_whatsapp + ' UNREAD';
      }}
      if (data.brain !== undefined) {{
        const select = document.getElementById('brain-select');
        if (document.activeElement !== select) {{
          select.value = data.brain;
        }}
      }}
      if (data.known_faces_count !== undefined) {{
        document.getElementById('face-count-val').innerText = data.known_faces_count;
      }}

      // Dynamic IoT device loading
      if (data.iot_devices !== undefined) {{
        const list = document.getElementById('iot-devices-list');
        list.innerHTML = '';
        data.iot_devices.forEach(d => {{
          const card = document.createElement('div');
          card.className = 'tel-card';
          card.style.textAlign = 'left';
          card.style.display = 'flex';
          card.style.justifyContent = 'space-between';
          card.style.alignItems = 'center';
          card.style.padding = '12px 20px';
          
          const info = document.createElement('div');
          info.innerHTML = "<span style=\\"font-family:'Orbitron'; font-size:12px; color:var(--text-primary);\\">" + d.name + "</span><br><span style=\\"font-size:10px; color:var(--text-muted);\\">" + d.entity_id + "</span>";
          
          const ctrl = document.createElement('div');
          if (d.type === 'climate') {{
            ctrl.innerHTML = "<span style=\\"font-family:'Orbitron'; color:var(--safety-glow); margin-right:8px;\\">" + d.state + "°C</span>" +
              "<input type=\\"range\\" min=\\"16\\" max=\\"30\\" value=\\"" + d.state + "\\" onchange=\\"setTemperature('" + d.entity_id + "', this.value)\\" style=\\"width:70px; vertical-align:middle;\\">";
          }} else {{
            const isChecked = d.state === 'on' ? 'checked' : '';
            ctrl.innerHTML = "<label class=\\"switch\\">" +
              "<input type=\\"checkbox\\" " + isChecked + " onchange=\\"toggleDevice('" + d.entity_id + "', this.checked ? 'on' : 'off')\\">" +
              "<span class=\\"slider\\"></span>" +
              "</label>";
          }}
          
          card.appendChild(info);
          card.appendChild(ctrl);
          list.appendChild(card);
        }});
      }}

      // Dynamic Script list loading
      if (data.scripts !== undefined) {{
        const list = document.getElementById('scripts-list');
        list.innerHTML = '';
        if (data.scripts.length === 0) {{
          list.innerHTML = '<div style="color: var(--text-muted); font-size: 13px; text-align: center;">No automation scripts generated yet. Try: "write a script that..."</div>';
        }}
        data.scripts.forEach(s => {{
          const row = document.createElement('div');
          row.className = 'tel-card';
          row.style.textAlign = 'left';
          row.style.display = 'flex';
          row.style.justifyContent = 'space-between';
          row.style.alignItems = 'center';
          row.style.padding = '10px 15px';
          
          const label = document.createElement('span');
          label.innerText = s;
          label.style.fontFamily = 'Courier New';
          label.style.fontSize = '12px';
          
          const btn = document.createElement('button');
          btn.innerText = 'RUN';
          btn.className = 'send-btn';
          btn.style.padding = '4px 10px';
          btn.style.fontSize = '10px';
          btn.style.height = 'auto';
          btn.style.width = 'auto';
          btn.onclick = () => runScript(s);
          
          row.appendChild(label);
          row.appendChild(btn);
          list.appendChild(row);
        }});
      }}
    }} catch(e) {{
      console.warn('Telemetry link offline.');
    }}
  }}

  setInterval(pollStats, 2000);
  pollStats();

  const canvas = document.getElementById('reactor-canvas');
  const ctx = canvas.getContext('2d');
  const cx = canvas.width / 2;
  const cy = canvas.height / 2;

  let angleOuter = 0;
  let angleInner = 0;
  let baseCoreRadius = 35;
  let corePulseVal = 0;
  
  const particles = [];
  function createParticle() {{
    if (particles.length > 30) return;
    particles.push({{
      x: 0,
      y: 0,
      radius: Math.random() * 2 + 1,
      angle: Math.random() * Math.PI * 2,
      speed: Math.random() * 0.8 + 0.2,
      dist: Math.random() * 10 + 20,
      opacity: 1,
      fade: Math.random() * 0.02 + 0.01
    }});
  }}

  function animate() {{
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    corePulseVal += 0.05 * (thinking ? 2.5 : 1);
    const pulseFactor = Math.sin(corePulseVal) * 6;
    const currentCoreRadius = baseCoreRadius + pulseFactor;
    
    angleOuter += 0.015 * (thinking ? 3 : 1);
    angleInner -= 0.025 * (thinking ? 3 : 1);
    
    ctx.shadowBlur = 0;
    ctx.shadowColor = 'transparent';

    ctx.strokeStyle = 'rgba(0, 245, 196, 0.08)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(cx, cy, 100, 0, Math.PI * 2);
    ctx.stroke();
    
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angleOuter);
    ctx.shadowBlur = 12;
    ctx.shadowColor = 'rgba(0, 245, 196, 0.4)';
    ctx.strokeStyle = 'rgba(0, 245, 196, 0.85)';
    ctx.lineWidth = 3;
    ctx.setLineDash([12, 18, 4, 18]);
    ctx.beginPath();
    ctx.arc(0, 0, 85, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angleInner);
    ctx.shadowBlur = 10;
    ctx.shadowColor = 'rgba(59, 130, 246, 0.4)';
    ctx.strokeStyle = 'rgba(59, 130, 246, 0.75)';
    ctx.lineWidth = 2;
    ctx.setLineDash([20, 10, 30, 15]);
    ctx.beginPath();
    ctx.arc(0, 0, 60, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
    
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
    ctx.lineWidth = 1;
    for (let i = 0; i < 8; i++) {{
      const angle = (i * Math.PI) / 4;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(angle) * 35, cy + Math.sin(angle) * 35);
      ctx.lineTo(cx + Math.cos(angle) * 80, cy + Math.sin(angle) * 80);
      ctx.stroke();
    }}

    const grad = ctx.createRadialGradient(cx, cy, 2, cx, cy, currentCoreRadius);
    if (thinking) {{
      grad.addColorStop(0, '#ffffff');
      grad.addColorStop(0.2, '#fca5a5');
      grad.addColorStop(1, 'rgba(239, 68, 68, 0)');
      ctx.shadowColor = '#ef4444';
    }} else {{
      grad.addColorStop(0, '#ffffff');
      grad.addColorStop(0.3, '#00f5c4');
      grad.addColorStop(0.8, '#3b82f6');
      grad.addColorStop(1, 'rgba(59, 130, 246, 0)');
      ctx.shadowColor = '#00f5c4';
    }}
    
    ctx.shadowBlur = thinking ? 25 : 18;
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, currentCoreRadius, 0, Math.PI * 2);
    ctx.fill();

    createParticle();
    for (let i = particles.length - 1; i >= 0; i--) {{
      const p = particles[i];
      p.dist += p.speed * (thinking ? 2.2 : 1.2);
      p.opacity -= p.fade;
      if (p.opacity <= 0 || p.dist > 95) {{
        particles.splice(i, 1);
        continue;
      }}
      const px = cx + Math.cos(p.angle) * p.dist;
      const py = cy + Math.sin(p.angle) * p.dist;
      ctx.fillStyle = thinking ? "rgba(239, 68, 68, " + p.opacity + ")" : "rgba(0, 245, 196, " + p.opacity + ")";
      ctx.beginPath();
      ctx.arc(px, py, p.radius, 0, Math.PI * 2);
      ctx.fill();
    }}
    
    requestAnimationFrame(animate);
  }}

  animate();
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
        return flask.jsonify(mobile_status(assistant.config.name, assistant.config.data_dir))

    @app.route("/set_brain", methods=["POST"])
    def set_brain():
        data = flask.request.get_json(silent=True) or {}
        provider = str(data.get("brain", "")).strip().lower()
        if provider not in ("local", "ollama", "gemini"):
            return flask.jsonify({"error": "Invalid brain provider"}), 400
        from .local_ai import _save_brain_provider
        _save_brain_provider(assistant.config.data_dir, provider)
        return flask.jsonify({"success": True, "brain": provider})

    @app.route("/iot/toggle", methods=["POST"])
    def iot_toggle():
        data = flask.request.get_json(silent=True) or {}
        entity_id = str(data.get("entity_id", "")).strip()
        state = str(data.get("state", "")).strip().lower()
        if not entity_id:
            return flask.jsonify({"error": "Missing entity_id"}), 400
            
        from .iot_agent import _load_devices, _save_devices
        devices = _load_devices(assistant.config.data_dir)
        matched = False
        for d in devices:
            if d["entity_id"] == entity_id:
                d["state"] = state
                matched = True
                break
        if matched:
            _save_devices(assistant.config.data_dir, devices)
            return flask.jsonify({"success": True, "entity_id": entity_id, "state": state})
        return flask.jsonify({"error": "Device not found"}), 404

    @app.route("/scripts/run", methods=["POST"])
    def scripts_run():
        data = flask.request.get_json(silent=True) or {}
        filename = str(data.get("filename", "")).strip()
        if not filename:
            return flask.jsonify({"error": "Missing filename"}), 400
        filename = os.path.basename(filename)
        filepath = assistant.config.data_dir / "veronica_scripts" / filename
        if not filepath.exists():
            return flask.jsonify({"error": "Script not found"}), 404
            
        from .coder_agent import _execute_script
        output = _execute_script(str(filepath))
        return flask.jsonify({"success": True, "output": output})

    @app.route("/camera/describe")
    def camera_describe():
        from .camera_agent import handle_camera_request
        res = handle_camera_request("describe the scene in the camera view in detail", assistant.context)
        return flask.jsonify({"success": True, "response": res.response})

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


def mobile_status(assistant_name: str = "Veronica", data_dir: Path | None = None) -> dict[str, Any]:
    """Return mobile server status metadata."""
    res = {"status": "online", "name": assistant_name, "ip": get_local_ip()}
    res.update({
        "cpu": 0.0,
        "ram": 0.0,
        "safety_level": "medium",
        "active_jobs": 0,
        "unread_whatsapp": 0,
        "brain": "local",
        "iot_devices": [],
        "scripts": [],
        "known_faces_count": 0,
        "security_running": False
    })
    if data_dir is not None:
        cpu_percent = 0.0
        ram_percent = 0.0
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=None) or 0.0
            ram_percent = psutil.virtual_memory().percent or 0.0
        except Exception:
            pass
            
        from .policy_agent import _load_policy
        policy = _load_policy(data_dir)
        
        from .runner_agent import _load_jobs
        jobs = _load_jobs(data_dir)
        active_jobs = sum(1 for j in jobs.values() if j.get("status") in ("running", "pending"))
        
        from .whatsapp_agent import _load_messages
        msgs = _load_messages(data_dir)
        unread_whatsapp = sum(1 for m in msgs if not m.get("read", False))
        
        from .local_ai import _load_brain_provider
        brain = _load_brain_provider(data_dir)
        
        from .iot_agent import _load_devices
        devices = _load_devices(data_dir)
        
        scripts_dir = data_dir / "veronica_scripts"
        scripts = []
        if scripts_dir.exists():
            scripts = sorted(f.name for f in scripts_dir.iterdir() if f.is_file() and f.suffix == ".py")
            
        known_faces_dir = data_dir / "known_faces"
        known_faces_count = 0
        if known_faces_dir.exists():
            known_faces_count = len([f for f in known_faces_dir.iterdir() if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png")])
            
        security_running = False
        
        res.update({
            "cpu": cpu_percent,
            "ram": ram_percent,
            "safety_level": policy.get("safety_level", "medium"),
            "active_jobs": active_jobs,
            "unread_whatsapp": unread_whatsapp,
            "brain": brain,
            "iot_devices": devices,
            "scripts": scripts,
            "known_faces_count": known_faces_count,
            "security_running": security_running
        })
    return res


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
