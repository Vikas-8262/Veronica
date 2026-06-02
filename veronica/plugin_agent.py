"""Dynamic Plugin Loader Agent for Veronica.

Scans ~/.veronica/plugins/ at startup (and on reload command), dynamically loads
them as new skills, and registers them in the main skills registry.
"""

import os
import importlib.util
from pathlib import Path
from .skills import AssistantContext, SkillResult, Skill

# Directory to scan for plugins: ~/.veronica/plugins
def get_plugins_dir() -> Path:
    plugins_dir = Path(os.path.expanduser("~")) / ".veronica" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    return plugins_dir

# List of loaded plugin definitions
_loaded_plugins = {}

def is_plugin_request(message: str) -> bool:
    lowered = message.lower().strip()
    return lowered in ("list plugins", "reload plugins", "plugin status")

def handle_plugin_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    
    if lowered == "reload plugins":
        count = load_plugins()
        return SkillResult(True, f"🔄 Reloaded plugins! Discoverd and loaded {count} plugin(s).")
        
    if lowered in ("list plugins", "plugin status"):
        if not _loaded_plugins:
            return SkillResult(True, "🔌 No dynamic plugins are currently loaded. Drop python scripts into `~/.veronica/plugins/` to extend capabilities.")
            
        lines = []
        for name, meta in _loaded_plugins.items():
            lines.append(f"• **{name}** (v{meta['version']}): {meta['description']}")
        return SkillResult(True, "🔌 **Loaded Plugins**\n" + "\n".join(lines))
        
    return SkillResult(False, "")

def load_plugins() -> int:
    """Scan and dynamically import plugins from ~/.veronica/plugins/."""
    global _loaded_plugins
    _loaded_plugins.clear()
    
    plugins_dir = get_plugins_dir()
    plugin_files = [f for f in plugins_dir.glob("*.py") if f.name != "__init__.py"]
    
    count = 0
    for file_path in plugin_files:
        module_name = file_path.stem
        try:
            # Dynamically import module from path
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                continue
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Verify interface requirements:
            # Must have: PLUGIN_MANIFEST (dict), is_match (callable), handle (callable)
            manifest = getattr(module, "PLUGIN_MANIFEST", None)
            is_match_fn = getattr(module, "is_match", None)
            handle_fn = getattr(module, "handle", None)
            
            if not isinstance(manifest, dict) or not callable(is_match_fn) or not callable(handle_fn):
                print(f"   [Plugin Loader] Warning: Skip invalid plugin structure at {file_path.name}")
                continue
                
            name = manifest.get("name", module_name)
            _loaded_plugins[name] = {
                "version": manifest.get("version", "1.0"),
                "description": manifest.get("description", "No description provided"),
                "is_match": is_match_fn,
                "handle": handle_fn,
                "file": file_path.name
            }
            count += 1
            print(f"   [Plugin Loader] Loaded plugin: {name} (v{manifest.get('version', '1.0')})")
        except Exception as e:
            print(f"   [Plugin Loader] Failed to load plugin {module_name} error: {e}")
            
    return count

def get_dynamic_plugin_skills() -> list[Skill]:
    """Wraps each loaded plugin into a dynamic Skill instance."""
    skills = []
    for name, plugin in _loaded_plugins.items():
        skills.append(Skill(
            name=name,
            matches=plugin["is_match"],
            handle=plugin["handle"]
        ))
    return skills
