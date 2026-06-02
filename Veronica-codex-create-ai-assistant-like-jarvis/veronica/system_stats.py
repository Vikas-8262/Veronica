"""Optional system statistics support for Veronica.

This module adapts the user-provided VEER system stats flow. It uses `psutil`
when available and gracefully explains how to enable the feature when it is not
installed.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import platform
from pathlib import Path

LOW_BATTERY_THRESHOLD = 20
HIGH_CPU_THRESHOLD = 85
ELEVATED_CPU_THRESHOLD = 60
HIGH_RAM_THRESHOLD = 85
ELEVATED_RAM_THRESHOLD = 70
LOW_DISK_SPACE_THRESHOLD = 85
HOT_CPU_THRESHOLD = 80
ACTIVE_PROCESS_CPU_THRESHOLD = 2.0
MAX_RUNNING_APPS = 5

BATTERY_WORDS = ("battery", "charge", "kitni battery")
CPU_WORDS = ("cpu", "processor", "processor kitna")
RAM_WORDS = ("ram", "memory", "kitni memory")
DISK_WORDS = ("disk", "storage", "drive", "space")
TEMPERATURE_WORDS = ("temperature", "garam", "temp")
RUNNING_APPS_WORDS = ("apps", "kya chal raha", "running")
REPORT_WORDS = (
    "system",
    "report",
    "sab batao",
    "status",
    "system status",
    "status report",
)


def handle_stats_command(command: str) -> str | None:
    """Return a system-stats response for a supported command, otherwise None."""
    action = _stats_action(command)
    if action == "battery":
        return get_battery()
    if action == "cpu":
        return get_cpu()
    if action == "ram":
        return get_ram()
    if action == "disk":
        return get_disk()
    if action == "temperature":
        return get_temperature()
    if action == "apps":
        return get_running_apps()
    if action == "report":
        return get_full_report()
    return None


def is_stats_command(command: str) -> bool:
    """Return True when a message looks like a system statistics request."""
    return _stats_action(command) is not None


def _stats_action(command: str) -> str | None:
    normalized = _normalize(command)
    tokens = set(normalized.split())
    if _matches_words(normalized, tokens, BATTERY_WORDS):
        return "battery"
    if _matches_words(normalized, tokens, CPU_WORDS):
        return "cpu"
    if _matches_words(normalized, tokens, RAM_WORDS):
        return "ram"
    if _matches_words(normalized, tokens, DISK_WORDS):
        return "disk"
    if _matches_words(normalized, tokens, TEMPERATURE_WORDS):
        return "temperature"
    if _matches_words(normalized, tokens, RUNNING_APPS_WORDS):
        return "apps"
    if _matches_words(normalized, tokens, REPORT_WORDS):
        return "report"
    return None


def get_battery() -> str:
    """Return battery percentage, charging state, and low-battery warning."""
    psutil = _optional_module("psutil")
    if psutil is None:
        return _missing_psutil_message()

    try:
        battery = psutil.sensors_battery()
        if battery is None:
            return "Battery sensor nahi mila — shayad desktop hai."

        percent = int(battery.percent)
        charging = bool(battery.power_plugged)
        minutes_left = _minutes_left(getattr(battery, "secsleft", None))
        status = "charge ho rahi hai" if charging else "battery pe chal raha hai"
        time_left = f", lagbhag {minutes_left} minute bacha hai" if minutes_left and not charging else ""
        warning = " — Charger lagao, battery kam hai!" if percent < LOW_BATTERY_THRESHOLD and not charging else ""
        return f"Battery {percent}% hai, {status}{time_left}{warning}"
    except Exception as exc:  # pragma: no cover - defensive third-party boundary
        return f"Battery info nahi mili: {exc}"


def get_cpu() -> str:
    """Return CPU utilization, load label, frequency, and core counts."""
    psutil = _optional_module("psutil")
    if psutil is None:
        return _missing_psutil_message()

    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        cores = psutil.cpu_count(logical=False)
        threads = psutil.cpu_count(logical=True)
        frequency = psutil.cpu_freq()
        frequency_text = f", {frequency.current:.0f} MHz pe chal raha hai" if frequency else ""
        load_text = _cpu_load_text(cpu_percent)
        return f"CPU {cpu_percent}% use ho raha hai — {load_text}{frequency_text}. {cores} cores, {threads} threads."
    except Exception as exc:  # pragma: no cover - defensive third-party boundary
        return f"CPU info nahi mili: {exc}"


def get_ram() -> str:
    """Return RAM usage summary."""
    psutil = _optional_module("psutil")
    if psutil is None:
        return _missing_psutil_message()

    try:
        ram = psutil.virtual_memory()
        total = _bytes_to_gib(ram.total)
        used = _bytes_to_gib(ram.used)
        free = _bytes_to_gib(ram.available)
        load_text = _ram_load_text(ram.percent)
        return f"RAM: {used} GB use, {free} GB free — total {total} GB. Load {load_text}."
    except Exception as exc:  # pragma: no cover - defensive third-party boundary
        return f"RAM info nahi mili: {exc}"


def get_disk(path: str | Path | None = None) -> str:
    """Return disk usage for the default system drive/path."""
    psutil = _optional_module("psutil")
    if psutil is None:
        return _missing_psutil_message()

    disk_path = str(path or _default_disk_path())
    try:
        disk = psutil.disk_usage(disk_path)
        total = _bytes_to_gib(disk.total)
        used = _bytes_to_gib(disk.used)
        free = _bytes_to_gib(disk.free)
        warning = " — Space kam ho raha hai!" if disk.percent > LOW_DISK_SPACE_THRESHOLD else ""
        return f"Disk {disk_path}: {used} GB used, {free} GB free — total {total} GB{warning}"
    except Exception as exc:  # pragma: no cover - defensive third-party boundary
        return f"Disk info nahi mili: {exc}"


def get_temperature() -> str:
    """Return CPU temperature when the platform exposes sensors through psutil."""
    psutil = _optional_module("psutil")
    if psutil is None:
        return _missing_psutil_message()

    try:
        temperatures = psutil.sensors_temperatures()
        if not temperatures:
            return "Temperature sensor nahi mila."
        for key in ("coretemp", "cpu_thermal", "k10temp"):
            if key in temperatures and temperatures[key]:
                current = temperatures[key][0].current
                warning = " — Laptop garam ho raha hai!" if current > HOT_CPU_THRESHOLD else ""
                return f"CPU temperature {current:.0f}°C hai{warning}"
        return "Temperature abhi nahi mila."
    except Exception:  # pragma: no cover - platform sensor APIs vary widely
        return "Temperature sensor usually har system pe available nahi hota."


def get_running_apps() -> str:
    """Return process names that are currently using noticeable CPU."""
    psutil = _optional_module("psutil")
    if psutil is None:
        return _missing_psutil_message()

    try:
        process_names: list[str] = []
        for process in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
            info = getattr(process, "info", {})
            try:
                cpu_percent = float(info.get("cpu_percent") or 0.0)
            except (TypeError, ValueError):
                cpu_percent = 0.0
            name = info.get("name") or "unknown"
            if cpu_percent > ACTIVE_PROCESS_CPU_THRESHOLD:
                process_names.append(str(name))
        if process_names:
            return f"Heavy apps chal rahi hain: {', '.join(process_names[:MAX_RUNNING_APPS])}"
        return "Sab apps normal chal rahi hain."
    except Exception as exc:  # pragma: no cover - defensive third-party boundary
        return f"Apps info nahi mili: {exc}"


def get_full_report() -> str:
    """Return a combined battery, CPU, RAM, and disk report."""
    return " | ".join([get_battery(), get_cpu(), get_ram(), get_disk()])


def _optional_module(module_name: str):
    if importlib.util.find_spec(module_name) is None:
        return None
    return importlib.import_module(module_name)


def _missing_psutil_message() -> str:
    return "System stats ke liye psutil install karo: pip install -r requirements-system.txt"


def _minutes_left(seconds_left: int | None) -> int | None:
    if seconds_left is None or seconds_left <= 0 or seconds_left >= 86_400:
        return None
    return seconds_left // 60


def _cpu_load_text(cpu_percent: float) -> str:
    if cpu_percent < ELEVATED_CPU_THRESHOLD:
        return "normal"
    if cpu_percent < HIGH_CPU_THRESHOLD:
        return "thoda zyada"
    return "bahut zyada — koi bhari app chal rahi hai!"


def _ram_load_text(ram_percent: float) -> str:
    if ram_percent < ELEVATED_RAM_THRESHOLD:
        return "normal"
    if ram_percent < HIGH_RAM_THRESHOLD:
        return "thoda tight"
    return "RAM full hone wali hai!"


def _bytes_to_gib(value: int) -> int:
    return int(value) // (1024**3)


def _default_disk_path() -> str:
    if platform.system() == "Windows":
        system_drive = os.getenv("SystemDrive")
        if system_drive:
            return f"{system_drive}{os.sep}"
    return Path.home().anchor or os.sep


def _matches_words(normalized: str, tokens: set[str], words: tuple[str, ...]) -> bool:
    for word in words:
        if " " in word and word in normalized:
            return True
        if word in tokens:
            return True
    return False


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())
