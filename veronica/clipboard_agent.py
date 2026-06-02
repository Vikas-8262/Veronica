"""Smart Clipboard Manager agent for Veronica."""

import importlib
import json
import os
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

# Path to the persistent clipboard history file
_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "clipboard_history.json")


def _load_history() -> dict:
    """Load the saved clipboard snippets from disk."""
    if os.path.exists(_HISTORY_FILE):
        try:
            with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_history(history: dict) -> None:
    """Persist the clipboard history to disk."""
    with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def is_clipboard_request(message: str) -> bool:
    """Matcher for Clipboard requests."""
    lowered = message.lower().strip()
    return any(phrase in lowered for phrase in (
        "read clipboard", "read my clipboard",
        "save clipboard", "clipboard history",
        "show clipboard", "clear clipboard",
        "paste "
    ))


def handle_clipboard_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler for all clipboard operations."""
    pyperclip = _optional_module("pyperclip")
    if pyperclip is None:
        return SkillResult(True, "Clipboard Agent requires 'pyperclip'. Run: pip install pyperclip")

    lowered = message.lower().strip()
    history = _load_history()

    # --- READ CLIPBOARD ---
    if "read clipboard" in lowered or "read my clipboard" in lowered:
        try:
            content = pyperclip.paste()
            if not content:
                return SkillResult(True, "Your clipboard is currently empty.")
            preview = content[:500] + ("..." if len(content) > 500 else "")
            return SkillResult(True, f"📋 Current Clipboard Contents:\n\n{preview}")
        except Exception as e:
            return SkillResult(True, f"Failed to read clipboard: {e}")

    # --- SAVE CLIPBOARD AS <name> ---
    if "save clipboard as" in lowered:
        try:
            name = lowered.split("save clipboard as")[-1].strip().strip("?.! ")
            if not name:
                return SkillResult(True, "Please provide a name (e.g., 'save clipboard as my_email').")
            content = pyperclip.paste()
            if not content:
                return SkillResult(True, "Cannot save — your clipboard is currently empty. Copy something first!")
            history[name] = content
            _save_history(history)
            preview = content[:100] + ("..." if len(content) > 100 else "")
            return SkillResult(True, f"✅ Saved clipboard snippet as '{name}':\n  \"{preview}\"")
        except Exception as e:
            return SkillResult(True, f"Failed to save clipboard: {e}")

    # --- PASTE <name> ---
    if lowered.startswith("paste "):
        try:
            name = lowered[len("paste "):].strip().strip("?.! ")
            if name not in history:
                available = ", ".join(history.keys()) if history else "none"
                return SkillResult(True, f"No snippet found with name '{name}'. Available snippets: {available}")
            content = history[name]
            pyperclip.copy(content)
            preview = content[:100] + ("..." if len(content) > 100 else "")
            return SkillResult(True, f"📋 Copied '{name}' to clipboard:\n  \"{preview}\"\n\nYou can now Ctrl+V to paste it anywhere!")
        except Exception as e:
            return SkillResult(True, f"Failed to paste snippet: {e}")

    # --- SHOW / LIST CLIPBOARD HISTORY ---
    if "clipboard history" in lowered or "show clipboard" in lowered:
        if not history:
            return SkillResult(True, "No saved clipboard snippets yet. Use 'save clipboard as <name>' to create one!")
        lines = []
        for name, content in history.items():
            preview = content[:60].replace("\n", " ") + ("..." if len(content) > 60 else "")
            lines.append(f"  • {name}: \"{preview}\"")
        return SkillResult(True, f"📋 Saved Clipboard Snippets ({len(history)}):\n\n" + "\n".join(lines))

    # --- CLEAR CLIPBOARD HISTORY ---
    if "clear clipboard" in lowered:
        count = len(history)
        _save_history({})
        return SkillResult(True, f"🗑️ Cleared {count} saved clipboard snippet(s).")

    return SkillResult(True, "Clipboard command not recognized. Try: 'read clipboard', 'save clipboard as <name>', 'paste <name>', 'show clipboard history', or 'clear clipboard history'.")
