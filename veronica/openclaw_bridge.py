"""OpenClaw-style bridge primitives for Veronica.

This module does not vendor third-party OpenClaw code. Instead, it adds a safe
compatibility layer inspired by OpenClaw concepts: a tool registry, manifest
loading, and explicit policy boundaries before any risky execution is allowed.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .advanced import roadmap_mark_done, roadmap_next, roadmap_status


@dataclass(frozen=True, slots=True)
class BridgeTool:
    """A safe OpenClaw-style tool descriptor."""

    name: str
    description: str
    kind: str = "builtin"
    command: str = ""
    requires_approval: bool = True


BUILTIN_TOOLS: tuple[BridgeTool, ...] = (
    BridgeTool("roadmap_next", "Show the next pending advanced roadmap step."),
    BridgeTool("roadmap_status", "Show all advanced roadmap progress."),
    BridgeTool("memory_list", "List structured memory entries saved in memory.json."),
    BridgeTool("bridge_complete", "Mark OpenClaw bridge roadmap step complete."),
)


MANIFEST_NAMES = ("openclaw_tools.json", "openclaw_manifest.json")


def manifest_paths(data_dir: Path) -> tuple[Path, ...]:
    """Return supported OpenClaw-style manifest locations."""
    return tuple([data_dir / name for name in MANIFEST_NAMES] + [data_dir / "openclaw" / "tools.json"])


def load_manifest_tools(data_dir: Path) -> list[BridgeTool]:
    """Load safe tool descriptors from an OpenClaw-style JSON manifest."""
    tools: list[BridgeTool] = []
    for path in manifest_paths(data_dir):
        if not path.exists():
            continue
        data = _read_json_object(path)
        raw_tools = data.get("tools", [])
        if not isinstance(raw_tools, list):
            continue
        for item in raw_tools:
            tool = _tool_from_manifest_item(item)
            if tool is not None:
                tools.append(tool)
    return tools


def list_tools(data_dir: Path) -> str:
    """Return a user-facing list of bridge tools."""
    tools = [*BUILTIN_TOOLS, *load_manifest_tools(data_dir)]
    lines = [f"- {tool.name} [{tool.kind}]: {tool.description}" for tool in tools]
    return "OpenClaw-style bridge tools:\n" + "\n".join(lines)


def bridge_status(data_dir: Path) -> str:
    """Return bridge configuration status."""
    custom_count = len(load_manifest_tools(data_dir))
    paths = ", ".join(str(path) for path in manifest_paths(data_dir))
    return (
        "OpenClaw bridge ready. "
        f"Built-in tools: {len(BUILTIN_TOOLS)}. Custom manifest tools: {custom_count}. "
        f"Manifest paths checked: {paths}"
    )


def run_tool(data_dir: Path, name: str) -> str:
    """Run a safe bridge tool or explain why it is blocked."""
    normalized = name.strip().lower()
    if normalized == "roadmap_next":
        return roadmap_next(data_dir)
    if normalized == "roadmap_status":
        return roadmap_status(data_dir)
    if normalized == "memory_list":
        return _memory_list(data_dir)
    if normalized == "bridge_complete":
        return roadmap_mark_done(data_dir, "plugins")

    for tool in load_manifest_tools(data_dir):
        if tool.name.lower() != normalized:
            continue
        if tool.kind == "assistant":
            return f"Assistant tool '{tool.name}' maps to command: {tool.command}"
        if tool.kind == "shell":
            return _run_shell_tool(tool)
        return f"Tool '{tool.name}' loaded hai, but kind '{tool.kind}' abhi executable nahi hai."

    return f"OpenClaw bridge tool '{name}' nahi mila. Use: openclaw tools"


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _tool_from_manifest_item(item: object) -> BridgeTool | None:
    if not isinstance(item, dict):
        return None
    name = str(item.get("name", "")).strip()
    if not name:
        return None
    description = str(item.get("description", "Custom OpenClaw-style tool")).strip()
    kind = str(item.get("kind", "assistant")).strip().lower() or "assistant"
    command = str(item.get("command", "")).strip()
    requires_approval = bool(item.get("requires_approval", True))
    return BridgeTool(name=name, description=description, kind=kind, command=command, requires_approval=requires_approval)


def _run_shell_tool(tool: BridgeTool) -> str:
    if tool.requires_approval:
        return "Shell tool approval required. Manifest me requires_approval=false set karo only trusted commands ke liye."
    if not tool.command:
        return f"Shell tool '{tool.name}' ka command empty hai."
    try:
        completed = subprocess.run(tool.command, shell=True, capture_output=True, text=True, timeout=20, check=False)
    except Exception as exc:
        return f"Shell tool '{tool.name}' error: {exc}"
    output = (completed.stdout or completed.stderr or "").strip()
    if not output:
        output = f"exit code {completed.returncode}"
    return f"Shell tool '{tool.name}' result: {output[:1000]}"


def _memory_list(data_dir: Path) -> str:
    path = data_dir / "memory.json"
    data = _read_json_object(path)
    if not data:
        return "Memory store empty hai."
    lines = [f"- {key}: {value}" for key, value in sorted(data.items())]
    return "Saved memory:\n" + "\n".join(lines)
