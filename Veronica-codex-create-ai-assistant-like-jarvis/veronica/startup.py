"""Windows startup shortcut helpers for Veronica."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence


STARTUP_RELATIVE_PATH = Path("Microsoft") / "Windows" / "Start Menu" / "Programs" / "Startup"
DEFAULT_STARTUP_ARGS = ("--gui", "--reminders")


@dataclass(frozen=True, slots=True)
class StartupShortcutConfig:
    """Configuration for the Windows Startup shortcut."""

    shortcut_name: str = "Veronica"
    module_name: str = "veronica"
    pythonw_path: Path | None = None
    working_directory: Path = field(default_factory=Path.cwd)
    arguments: Sequence[str] = DEFAULT_STARTUP_ARGS
    startup_dir: Path | None = None


def is_windows() -> bool:
    """Return True when running on Windows."""
    return platform.system() == "Windows"


def windows_startup_dir(env: Mapping[str, str] | None = None) -> Path:
    """Return the current user's Windows Startup folder."""
    values = env or os.environ
    appdata = values.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set; Windows Startup folder cannot be detected.")
    return Path(appdata) / STARTUP_RELATIVE_PATH


def _escape_vbs(value: str) -> str:
    """Escape a string for a VBScript double-quoted literal."""
    return value.replace('"', '""')


def _argument_string(module_name: str, arguments: Sequence[str]) -> str:
    """Build the argument string passed to pythonw."""
    parts = ["-m", module_name, *arguments]
    return subprocess.list2cmdline(parts)


def _pythonw_path(configured_path: Path | None = None) -> Path | str:
    """Find pythonw, falling back to the current Python executable."""
    if configured_path is not None:
        return configured_path
    discovered = shutil.which("pythonw")
    if discovered:
        return Path(discovered)
    executable = Path(sys.executable)
    sibling = executable.with_name("pythonw.exe")
    if sibling.exists():
        return sibling
    return executable


def build_shortcut_vbs(config: StartupShortcutConfig) -> str:
    """Build the VBScript used to create a Startup shortcut."""
    startup_dir = config.startup_dir or windows_startup_dir()
    shortcut_path = startup_dir / f"{config.shortcut_name}.lnk"
    target_path = _pythonw_path(config.pythonw_path)
    arguments = _argument_string(config.module_name, config.arguments)
    working_directory = config.working_directory

    return "\n".join(
        [
            'Set oWS = WScript.CreateObject("WScript.Shell")',
            f'sLinkFile = "{_escape_vbs(str(shortcut_path))}"',
            "Set oLink = oWS.CreateShortcut(sLinkFile)",
            f'oLink.TargetPath = "{_escape_vbs(str(target_path))}"',
            f'oLink.Arguments = "{_escape_vbs(arguments)}"',
            f'oLink.WorkingDirectory = "{_escape_vbs(str(working_directory))}"',
            "oLink.WindowStyle = 7",
            "oLink.Save",
            "",
        ]
    )


def install_windows_startup_shortcut(config: StartupShortcutConfig | None = None) -> str:
    """Create a per-user Windows Startup shortcut for Veronica."""
    if not is_windows():
        return "Windows startup shortcut sirf Windows par ban sakta hai."

    shortcut_config = config or StartupShortcutConfig()
    startup_dir = shortcut_config.startup_dir or windows_startup_dir()
    startup_dir.mkdir(parents=True, exist_ok=True)
    vbs_content = build_shortcut_vbs(shortcut_config)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".vbs", encoding="utf-8") as script_file:
            script_file.write(vbs_content)
            temp_path = Path(script_file.name)

        subprocess.run(["cscript", "//nologo", str(temp_path)], check=True, capture_output=True, text=True)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    shortcut_path = startup_dir / f"{shortcut_config.shortcut_name}.lnk"
    return (
        f"{shortcut_config.shortcut_name} ab Windows startup mein add ho gaya! "
        f"Har baar laptop on hone par automatically chalega: {shortcut_path}"
    )
