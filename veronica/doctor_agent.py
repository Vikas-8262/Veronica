"""Observability & Doctor Agent for Veronica.

Checks dependency status, API latencies, Python environment health, and suggests fixes.
"""

import os
import sys
import time
import importlib
import platform
from .skills import AssistantContext, SkillResult

DEPENDENCY_MAP = {
    "chromadb": "chromadb",
    "crewai": "crewai",
    "PyPDF2": "PyPDF2",
    "pyautogui": "pyautogui",
    "requests": "requests",
    "yfinance": "yfinance",
    "wikipedia": "wikipedia",
    "speech_recognition": "speech_recognition",
}

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_doctor_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered in ("doctor check", "system diagnostic", "system diagnostics", "doctor status")
        or lowered.startswith("doctor fix ")
    )

# ──────────────────────────────────────────────
# API Ping Helper
# ──────────────────────────────────────────────
def _check_gemini_api_latency() -> tuple[float | None, str]:
    requests = importlib.util.find_spec("requests")
    if not requests:
        return None, "requests library is missing"
        
    import requests as req
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None, "GEMINI_API_KEY is not set in environment"
        
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": "ping"}]}],
        "generationConfig": {"maxOutputTokens": 5}
    }
    
    start = time.time()
    try:
        resp = req.post(url, json=payload, timeout=10)
        latency = (time.time() - start) * 1000
        if resp.status_code == 200:
            return latency, "OK"
        else:
            return None, f"HTTP {resp.status_code}: {resp.text[:60]}"
    except Exception as e:
        return None, str(e)

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_doctor_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    
    # 1. Doctor Fix Suggestion
    if lowered.startswith("doctor fix "):
        target = message[len("doctor fix "):].strip()
        if target in DEPENDENCY_MAP:
            pkg = DEPENDENCY_MAP[target]
            return SkillResult(True, f"🔧 To fix the missing dependency **{target}**, run:\n`pip install {pkg}`")
        return SkillResult(True, f"❓ Unknown dependency: '{target}'. Try running `pip install {target}`.")
        
    # 2. Run Diagnostics
    lines = [
        "🩺 **Veronica System Diagnostics Report**",
        "────────────────────────────────────────",
        "**Python Environment:**",
        f"• Python: {platform.python_version()}",
        f"• Platform: {platform.system()} {platform.release()}",
        f"• OS Version: {platform.version()}",
        "",
        "**Core Integrations & Dependencies:**"
    ]
    
    missing_count = 0
    for name, module_name in DEPENDENCY_MAP.items():
        spec = importlib.util.find_spec(module_name)
        status = "✅ Functional" if spec is not None else "❌ Missing"
        if spec is None:
            missing_count += 1
        lines.append(f"• {name:<20} : {status}")
        
    lines.append("")
    lines.append("**API Connectivity & Observability:**")
    
    latency, err = _check_gemini_api_latency()
    if latency is not None:
        lines.append(f"• Gemini API Key       : ✅ Valid")
        lines.append(f"• Gemini Latency       : ✅ {latency:.1f}ms")
    else:
        lines.append(f"• Gemini API Status    : ❌ Failed ({err})")
        
    lines.append("────────────────────────────────────────")
    
    if missing_count > 0:
        lines.append(f"⚠️ **Notice:** {missing_count} dependencies are missing. Run `doctor fix <package>` for installation details.")
    else:
        lines.append("🎉 **All systems nominal! Veronica is in perfect health.**")
        
    return SkillResult(True, "\n".join(lines))
