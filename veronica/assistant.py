"""Assistant orchestration for Veronica."""

from __future__ import annotations

from collections.abc import Callable
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .local_ai import LocalAIBackend
from .skills import AssistantContext, Skill, build_default_skills
from .memory_manager import MemoryManager
from .tts_engine import TTSEngine


@dataclass(slots=True)
class AssistantConfig:
    """Runtime configuration for the assistant."""

    name: str = "Veronica"
    data_dir: Path = field(default_factory=lambda: Path.home() / ".veronica")
    start_reminder_thread: bool = False
    reminder_speaker: Callable[[str], None] | None = None
    focus_speaker: Callable[[str], None] | None = None
    track_productivity: bool = True


CHAIN_SEPARATORS = re.compile(r"\s+(?:and then|then|aur phir|phir)\s+|\s*;\s*")


class Assistant:
    """A JARVIS-like assistant with offline skills and a local AI backend."""

    def __init__(
        self,
        config: AssistantConfig | None = None,
        skills: Iterable[Skill] | None = None,
        ai_backend: LocalAIBackend | None = None,
    ) -> None:
        self.config = config or AssistantConfig()
        self.context = AssistantContext(data_dir=self.config.data_dir, assistant_name=self.config.name)
        self.skills = list(skills) if skills is not None else build_default_skills()
        self.ai_backend = ai_backend or LocalAIBackend()
        if self.config.reminder_speaker is not None:
            self.context.reminders.speaker = self.config.reminder_speaker
        if self.config.focus_speaker is not None:
            self.context.fun.speaker = self.config.focus_speaker
        if self.config.start_reminder_thread:
            self.context.reminders.start_background()
        self.memory = MemoryManager(self.config.data_dir)
        self.tts = TTSEngine()
        self.last_response: str = ""

    @property
    def shortcuts_file(self) -> Path:
        return self.config.data_dir / "shortcuts.json"

    def _resolve_shortcut(self, message: str) -> str:
        lowered = message.lower().strip()
        if not lowered.startswith(("shortcut ", "run ", "do ")):
            return message

        parts = lowered.split(maxsplit=1)
        if len(parts) < 2:
            return message
        alias = parts[1].strip()

        try:
            if not self.shortcuts_file.exists():
                return message
            raw = self.shortcuts_file.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return message

        if not isinstance(data, dict):
            return message
        target = data.get(alias)
        if isinstance(target, str) and target.strip():
            return target.strip()
        return message

    def respond(self, message: str) -> str:
        """Return a response for a user message."""
        cleaned = self._resolve_shortcut(message.strip())
        if not cleaned:
            return "I'm online. Tell me what you need."

        lowered = cleaned.lower()
        if lowered in {"repeat", "repeat that", "last response", "last answer", "phir se", "dobara"}:
            if self.last_response:
                return f"Last response: {self.last_response}"
            return "Abhi tak koi response nahi diya hai."

        commands = [part.strip() for part in CHAIN_SEPARATORS.split(cleaned) if part.strip()]
        if len(commands) > 1:
            responses = [self._respond_single(command) for command in commands]
            combined = "\n".join(f"{index}. {item}" for index, item in enumerate(responses, start=1))
            self.last_response = combined
            return combined

        response = self._respond_single(cleaned)
        self.last_response = response
        return response

    def _respond_single(self, cleaned: str) -> str:
        if not cleaned:
            return "I'm online. Tell me what you need."

        # Check Safety Policy Engine
        from .policy_agent import check_command_safety
        is_safe, warn_msg = check_command_safety(cleaned)
        if not is_safe:
            return warn_msg
        elif warn_msg:
            print(f"   [Safety Policy] {warn_msg}")

        if self.config.track_productivity:
            self.context.fun.log_command_usage()

        if self.context.dictation.active:
            return self.context.dictation.handle_active_text(cleaned)

        for skill in self.skills:
            if skill.matches(cleaned):
                result = skill.handle(cleaned, self.context)
                if result.handled:
                    return result.response

        # Semantic Memory Recall
        memory_context = self.memory.recall_memory(cleaned)
        prompt = cleaned
        if memory_context:
            prompt = f"Relevant past conversations:\n{memory_context}\n\nUser request: {cleaned}"

        from .router_agent import route_and_execute
        
        def run_gemini():
            return self.ai_backend.reply(prompt, self.context)

        response = route_and_execute(cleaned, self.context, run_gemini)
        
        # Save Semantic Memory
        self.memory.save_memory(cleaned, response)
        
        # Speak the response
        self.tts.speak(response)
        
        return response

    def greeting(self) -> str:
        """Return a startup greeting."""
        return f"{self.config.name} online. Local intelligence systems are ready. How can I help?"
