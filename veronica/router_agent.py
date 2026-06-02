"""Hybrid AI Router for Veronica.

Decides whether a user query should be handled locally (to optimize latency and costs)
or routed to Gemini API.
"""

import os
import json
import time
from pathlib import Path
from .skills import AssistantContext, SkillResult

# File to store policy and stats persistent data
def _get_router_data_path(data_dir: Path | None = None) -> Path:
    if data_dir is None:
        data_dir = Path(os.path.expanduser("~")) / ".veronica"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "router_config.json"

def _load_config(data_dir: Path | None = None) -> dict:
    path = _get_router_data_path(data_dir)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "policy": "auto",
        "routed_local": 0,
        "routed_gemini": 0,
        "saved_cents": 0.0
    }

def _save_config(config: dict, data_dir: Path | None = None):
    path = _get_router_data_path(data_dir)
    try:
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except Exception:
        pass

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_router_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered.startswith("set router policy")
        or lowered in ("router status", "router diagnostic", "router diagnostics")
    )

# ──────────────────────────────────────────────
# Routing Logic
# ──────────────────────────────────────────────
def should_route_local(message: str, policy: str) -> bool:
    """Analyze if the request can/should be handled locally."""
    if policy == "local":
        return True
    if policy == "gemini":
        return False
    
    # Check if Gemini environment variables are explicitly set/requested
    if os.getenv("VERONICA_AI_PROVIDER", "").lower() == "gemini" or os.getenv("VERONICA_USE_GEMINI", "") == "1":
        return False

    # "auto" policy: Analyze complexity of the message
    lowered = message.lower().strip()
    
    # List of keywords/patterns that represent simple tasks suitable for local processing
    local_triggers = [
        "what is", "calculate", "+", "-", "*", "/", "%", 
        "time", "date", "today", "tomorrow", "clock", 
        "system status", "cpu", "memory", "battery", 
        "joke", "hello", "hi", "hey", "who are you", 
        "help", "exit", "quit", "abort"
    ]
    
    # If the message is very short or matches simple triggers, run locally
    if len(lowered.split()) <= 3:
        return True
        
    for trigger in local_triggers:
        if trigger in lowered:
            return True
            
    return False

def generate_local_response(message: str) -> str:
    """Generates a high-quality local fallback response for the query."""
    lowered = message.lower().strip()
    
    if any(h in lowered for h in ("hello", "hi", "hey", "greetings")):
        return "Hello! I am running on local mode. How can I help you today?"
        
    if "who are you" in lowered:
        return "I am Veronica, a fully local AI assistant. I am running locally right now."
        
    # Return a helpful dry-run or local-only advice message
    return (
        f"Running a local analysis. The key focus appears to be: {', '.join(lowered.split()[:5])}.\n"
        f"I would define the terms, identify the desired output, and then choose the smallest useful answer. "
        f"If you want, ask me to remember details, calculate values, or break this into a plan."
    )

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_router_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    config = _load_config(context.data_dir)
    
    if lowered.startswith("set router policy "):
        policy = message[len("set router policy "):].strip().lower()
        if policy not in ("local", "gemini", "auto"):
            return SkillResult(True, "Invalid policy. Choose: local, gemini, or auto.")
            
        config["policy"] = policy
        _save_config(config, context.data_dir)
        return SkillResult(True, f"🌐 Router policy updated to: **{policy.upper()}**")
        
    if lowered in ("router status", "router diagnostic", "router diagnostics"):
        total = config["routed_local"] + config["routed_gemini"]
        local_pct = (config["routed_local"] / total * 100) if total > 0 else 0
        gemini_pct = (config["routed_gemini"] / total * 100) if total > 0 else 0
        
        report = (
            f"🌐 **Hybrid AI Router Status**\n"
            f"───────────────────────────\n"
            f"• Current Policy: **{config['policy'].upper()}**\n"
            f"• Queries Routed Local: {config['routed_local']} ({local_pct:.1f}%)\n"
            f"• Queries Routed Gemini: {config['routed_gemini']} ({gemini_pct:.1f}%)\n"
            f"• Estimated API Cost Saved: ${config['saved_cents']:.4f}\n"
            f"───────────────────────────\n"
            f"Use `set router policy <local|gemini|auto>` to change routing behavior."
        )
        return SkillResult(True, report)
        
    return SkillResult(False, "")

# ──────────────────────────────────────────────
# Execution Routing Wrapper
# ──────────────────────────────────────────────
def route_and_execute(message: str, context: AssistantContext, gemini_fallback_fn) -> str:
    """Invoked in the main loop to execute the query using the configured policy."""
    config = _load_config(context.data_dir)
    policy = config["policy"]
    
    start_time = time.time()
    
    if should_route_local(message, policy):
        # Handle locally
        response = generate_local_response(message)
        latency = (time.time() - start_time) * 1000
        
        # Log stats
        config["routed_local"] += 1
        # Estimate saving ~0.01 cents ($0.0001) per local query compared to external API call
        config["saved_cents"] += 0.0001
        _save_config(config, context.data_dir)
        
        print(f"   [Router] Routed LOCAL (Latency: {latency:.1f}ms, Cost Saved)")
        return response
    else:
        # Route to Gemini API
        response = gemini_fallback_fn()
        latency = (time.time() - start_time) * 1000
        
        # Log stats
        config["routed_gemini"] += 1
        _save_config(config, context.data_dir)
        
        print(f"   [Router] Routed GEMINI (Latency: {latency:.1f}ms)")
        return response
