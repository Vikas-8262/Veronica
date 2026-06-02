"""Runtime adapter for using the real OpenClaw CLI from Veronica.

The bridge module gives Veronica a small OpenClaw-style manifest surface. This
adapter is for users who want to run the actual OpenClaw runtime side-by-side:
it discovers an installed `openclaw` CLI (or a source checkout configured via
environment variables) and forwards selected non-interactive commands to it.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 60


@dataclass(frozen=True, slots=True)
class OpenClawCommand:
    """Resolved command used to call the real OpenClaw runtime."""

    argv: tuple[str, ...]
    cwd: Path | None = None
    source: str = ""


def resolve_openclaw_command() -> OpenClawCommand | None:
    """Resolve a real OpenClaw CLI command from env, PATH, or source checkout."""
    env_bin = os.environ.get("VERONICA_OPENCLAW_BIN", "").strip()
    if env_bin:
        return OpenClawCommand(tuple(shlex.split(env_bin)), source="VERONICA_OPENCLAW_BIN")

    path_bin = shutil.which("openclaw")
    if path_bin:
        return OpenClawCommand((path_bin,), source="PATH")

    source_dir = os.environ.get("VERONICA_OPENCLAW_SOURCE", "").strip()
    if source_dir:
        root = Path(source_dir).expanduser()
        if (root / "package.json").exists():
            return OpenClawCommand(("pnpm", "openclaw"), cwd=root, source="VERONICA_OPENCLAW_SOURCE")

    return None


def runtime_status() -> str:
    """Return human-friendly status for full OpenClaw runtime availability."""
    command = resolve_openclaw_command()
    if command is None:
        return (
            "Full OpenClaw runtime abhi configured nahi hai. Install karo: npm install -g openclaw@latest; "
            "ya source checkout ke liye VERONICA_OPENCLAW_SOURCE set karo."
        )
    location = " ".join(command.argv)
    cwd = f" cwd={command.cwd}" if command.cwd else ""
    return f"Full OpenClaw runtime ready via {command.source}: {location}{cwd}"


def install_instructions() -> str:
    """Explain how to install the real OpenClaw runtime next to Veronica."""
    return (
        "Full OpenClaw use karne ke liye Node runtime chahiye. Recommended: "
        "npm install -g openclaw@latest && openclaw onboard. "
        "Source mode: git clone https://github.com/openclaw/openclaw.git, pnpm install, "
        "then VERONICA_OPENCLAW_SOURCE=/path/to/openclaw set karo."
    )


def run_openclaw(args: list[str], timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Run the real OpenClaw CLI with bounded output."""
    command = resolve_openclaw_command()
    if command is None:
        return runtime_status()
    if not args:
        return "Use: openclaw full status | install | doctor | gateway status | agent <message> | raw <args>"

    try:
        completed = subprocess.run(
            [*command.argv, *args],
            cwd=command.cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return f"OpenClaw runtime command missing: {exc}"
    except subprocess.TimeoutExpired:
        return f"OpenClaw runtime timeout after {timeout} seconds."

    output = (completed.stdout or completed.stderr or "").strip()
    if not output:
        output = f"exit code {completed.returncode}"
    return f"OpenClaw runtime ({completed.returncode}): {output[:2000]}"


def handle_runtime_command(message: str) -> str:
    """Parse Veronica's full-runtime OpenClaw commands."""
    lowered = message.lower().strip()
    if lowered in {"openclaw full", "openclaw full status", "claw full", "claw full status"}:
        return runtime_status()
    if lowered in {"openclaw full install", "claw full install"}:
        return install_instructions()
    if lowered in {"openclaw full doctor", "claw full doctor"}:
        return run_openclaw(["doctor"])
    if lowered in {"openclaw full gateway status", "claw full gateway status"}:
        return run_openclaw(["gateway", "status"])
    if lowered.startswith(("openclaw full agent ", "claw full agent ")):
        prompt = message.split("agent", 1)[-1].strip()
        if not prompt:
            return "Use: openclaw full agent <message>"
        return run_openclaw(["agent", "--message", prompt])
    if lowered.startswith(("openclaw full raw ", "claw full raw ")):
        raw = message.split("raw", 1)[-1].strip()
        if not raw:
            return "Use: openclaw full raw <args>"
        return run_openclaw(shlex.split(raw))
    if lowered in {"openclaw full voice start", "claw full voice start"}:
        return run_openclaw(["voice", "start"])
    if lowered in {"openclaw full voice stop", "claw full voice stop"}:
        return run_openclaw(["voice", "stop"])
    if lowered in {"openclaw full voice status", "claw full voice status"}:
        return run_openclaw(["voice", "status"])
    return "Use: openclaw full status | install | doctor | gateway status | voice start | voice stop | agent <message> | raw <args>"
