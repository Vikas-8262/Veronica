"""Safety Policy Engine for Veronica.

Classifies commands into risk levels and blocks or warns for high-risk actions.
"""

import os
import json
import re
from pathlib import Path
from .skills import AssistantContext, SkillResult

def _get_policy_file(data_dir: Path | None = None) -> Path:
    if data_dir is None:
        data_dir = Path(os.path.expanduser("~")) / ".veronica"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "policy_config.json"

def _load_policy(data_dir: Path | None = None) -> dict:
    path = _get_policy_file(data_dir)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "safety_level": "medium",
        "blocked_count": 0
    }

def _save_policy(config: dict, data_dir: Path | None = None):
    path = _get_policy_file(data_dir)
    try:
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except Exception:
        pass

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_policy_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered.startswith("set safety level")
        or lowered in ("safety status", "safety audit", "safety diagnostics")
    )

# ──────────────────────────────────────────────
# Risk Interceptor
# ──────────────────────────────────────────────
def check_command_safety(message: str, data_dir: Path | None = None) -> tuple[bool, str | None]:
    """Inspects a query to verify if it complies with the current safety level.
    
    Returns (is_safe, error_message).
    """
    config = _load_policy(data_dir)
    level = config["safety_level"]
    
    if level == "low":
        return True, None
        
    lowered = message.lower().strip()
    
    # Dangerous keywords indicating file deletions or system commands execution
    high_risk_patterns = [
        r"\brm\s+-rf\b",
        r"\brmdir\s+/s\b",
        r"\bshred\b",
        r"\bos\.system\b",
        r"\bsubprocess\.\b",
        r"\bformat\s+[a-z]:\b",
        r"\bdelete\s+all\s+files\b",
        r"\bwipe\s+disk\b"
    ]
    
    for pattern in high_risk_patterns:
        if re.search(pattern, lowered):
            # High risk pattern detected
            if level == "high":
                config["blocked_count"] += 1
                _save_policy(config, data_dir)
                return False, f"🚨 Command blocked by safety policy (Level: HIGH). High-risk pattern detected."
            elif level == "medium":
                return True, f"⚠️ Warning: This command contains high-risk actions. Proceeding under safety level MEDIUM."

    # Intercept sandbox or Docker instructions under HIGH safety
    if level == "high" and any(trigger in lowered for trigger in ("run in sandbox", "run sandbox", "execute sandbox")):
        config["blocked_count"] += 1
        _save_policy(config, data_dir)
        return False, "🚨 Sandbox execution is restricted under safety level: HIGH."
        
    return True, None

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_policy_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    config = _load_policy(context.data_dir)
    
    if lowered.startswith("set safety level "):
        level = message[len("set safety level "):].strip().lower()
        if level not in ("low", "medium", "high"):
            return SkillResult(True, "Invalid safety level. Choose: low, medium, or high.")
            
        config["safety_level"] = level
        _save_policy(config, context.data_dir)
        return SkillResult(True, f"🛡️ Safety level updated to: **{level.upper()}**")
        
    if lowered in ("safety status", "safety audit", "safety diagnostics"):
        report = (
            f"🛡️ **Safety Policy Engine Status**\n"
            f"───────────────────────────\n"
            f"• Current Policy Level: **{config['safety_level'].upper()}**\n"
            f"• Actions Intercepted & Blocked: {config['blocked_count']}\n"
            f"───────────────────────────\n"
            f"Use `set safety level <low|medium|high>` to update policy rules."
        )
        return SkillResult(True, report)
        
    return SkillResult(False, "")
