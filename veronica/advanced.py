"""Step-by-step advanced roadmap tracker for Veronica."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AdvancedStep:
    key: str
    title: str
    detail: str


ADVANCED_STEPS: tuple[AdvancedStep, ...] = (
    AdvancedStep("plugins", "Plugin architecture", "Dynamic plugin loader, manifests, and permission scopes."),
    AdvancedStep("memory_v3", "Memory v3", "Namespaced memory, timestamps, confidence, and memory search."),
    AdvancedStep("hybrid_router", "Hybrid AI router", "Provider policy for local/gemini/auto based on task confidence."),
    AdvancedStep("local_rag", "Local RAG", "Index local docs and answer with local citations."),
    AdvancedStep("agent_runner", "Agent task runner", "Multi-step jobs, retries, checkpoints, and job status."),
    AdvancedStep("security_v2", "Security v2", "Schedules, zones, escalation rules, and timeline export."),
    AdvancedStep("mobile_v2", "Mobile v2", "Auth token/PIN, push alerts, richer quick actions."),
    AdvancedStep("voice_v2", "Voice v2", "Wake-word/push-to-talk and optional offline STT backends."),
    AdvancedStep("observability", "Observability + doctor", "Structured logs, latency metrics, dependency diagnostics."),
    AdvancedStep("policy_engine", "Safety policy engine", "Risk profiles, confirmations, and dry-run protections."),
)


def progress_file(data_dir: Path) -> Path:
    return data_dir / "advanced_progress.json"


def load_progress(data_dir: Path) -> dict[str, bool]:
    path = progress_file(data_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): bool(v) for k, v in data.items()}


def save_progress(data_dir: Path, progress: dict[str, bool]) -> None:
    progress_file(data_dir).write_text(json.dumps(progress, indent=2), encoding="utf-8")


def roadmap_status(data_dir: Path) -> str:
    progress = load_progress(data_dir)
    lines: list[str] = []
    done_count = 0
    for index, step in enumerate(ADVANCED_STEPS, start=1):
        done = progress.get(step.key, False)
        if done:
            done_count += 1
        mark = "✅" if done else "⬜"
        lines.append(f"{mark} {index}. {step.title} ({step.key})")
    return f"Advanced roadmap progress: {done_count}/{len(ADVANCED_STEPS)}\n" + "\n".join(lines)


def roadmap_next(data_dir: Path) -> str:
    progress = load_progress(data_dir)
    for index, step in enumerate(ADVANCED_STEPS, start=1):
        if not progress.get(step.key, False):
            return f"Next step {index}: {step.title} ({step.key}) — {step.detail}"
    return "Saare advanced steps complete ho chuke hain. Great job!"


def roadmap_mark_done(data_dir: Path, key: str) -> str:
    normalized = key.strip().lower()
    valid_keys = {step.key for step in ADVANCED_STEPS}
    if normalized not in valid_keys:
        return "Unknown step key. Use: advance status"
    progress = load_progress(data_dir)
    progress[normalized] = True
    save_progress(data_dir, progress)
    return f"Marked done: {normalized}"


def roadmap_reset(data_dir: Path) -> str:
    save_progress(data_dir, {})
    return "Advanced roadmap progress reset kar diya."
