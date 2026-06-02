"""API Endpoint Tester Agent for Veronica.

Provides a fast HTTP client to check status, body content, and latency of API endpoints.
"""

import os
import re
import time
import json
import importlib
from .skills import AssistantContext, SkillResult

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_api_tester_request(message: str) -> bool:
    return message.lower().strip().startswith("test api:")

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_api_tester_request(message: str, context: AssistantContext) -> SkillResult:
    requests = importlib.util.find_spec("requests")
    if not requests:
        return SkillResult(True, "❌ requests library is missing. Run `pip install requests` first.")
        
    import requests as req
    
    # Match command: test api: GET https://example.com/api {"key": "val"}
    cmd_body = message[len("test api:"):].strip()
    match = re.match(r"^(GET|POST|PUT|DELETE)\s+(\S+)(.*)$", cmd_body, re.IGNORECASE)
    if not match:
        return SkillResult(True, "Invalid format. Use: `test api: <GET|POST|PUT|DELETE> <URL> [optional JSON payload]`")
        
    method = match.group(1).upper()
    url = match.group(2)
    payload_str = match.group(3).strip()
    
    headers = {
        "User-Agent": "Veronica-Assistant-Diagnostic-Client/3.0",
        "Content-Type": "application/json"
    }
    
    # Parse payload if provided
    data = None
    if payload_str:
        try:
            data = json.loads(payload_str)
        except Exception as e:
            return SkillResult(True, f"❌ Failed to parse JSON payload: {e}")
            
    print(f"   [API Tester] Dispatching {method} request to: {url}")
    
    start_time = time.time()
    try:
        if method == "GET":
            resp = req.get(url, headers=headers, timeout=15)
        elif method == "POST":
            resp = req.post(url, json=data, headers=headers, timeout=15)
        elif method == "PUT":
            resp = req.put(url, json=data, headers=headers, timeout=15)
        elif method == "DELETE":
            resp = req.delete(url, json=data, headers=headers, timeout=15)
            
        latency = (time.time() - start_time) * 1000
        
        # Format response body
        body_text = resp.text
        try:
            # Pretty print JSON if response is JSON
            parsed_json = resp.json()
            body_text = json.dumps(parsed_json, indent=2)
        except Exception:
            pass
            
        # Truncate large body outputs
        if len(body_text) > 800:
            body_text = body_text[:800] + "\n\n... (Output truncated to 800 characters) ..."
            
        summary = (
            f"📡 **API Diagnostic Response**\n"
            f"───────────────────────────\n"
            f"• Method & URL : {method} {url}\n"
            f"• Status Code  : **{resp.status_code} {resp.reason}**\n"
            f"• Response Time: **{latency:.1f} ms**\n"
            f"• Content Size : {len(resp.content)} bytes\n"
            f"───────────────────────────\n"
            f"• Response Body:\n{body_text}"
        )
        return SkillResult(True, summary)
        
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        return SkillResult(
            True,
            f"❌ **API Request Failed**\n"
            f"• Target URL: {url}\n"
            f"• Duration  : {latency:.1f} ms\n"
            f"• Error     : {e}"
        )
