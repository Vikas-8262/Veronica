"""Assistant orchestration for Veronica."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .local_ai import LocalAIBackend
from .skills import AssistantContext, Skill, build_default_skills


@dataclass(slots=True)
class AssistantConfig:
    """Runtime configuration for the assistant."""

    name: str = "Veronica"
    data_dir: Path = field(default_factory=lambda: Path.home() / ".veronica")
    start_reminder_thread: bool = False
    reminder_speaker: Callable[[str], None] | None = None
    focus_speaker: Callable[[str], None] | None = None
    track_productivity: bool = True


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

    def respond(self, message: str) -> str:
        """Return a response for a user message."""
        cleaned = message.strip()
        if not cleaned:
            return "I'm online. Tell me what you need."

        if self.config.track_productivity:
            self.context.fun.log_command_usage()

        if self.context.dictation.active:
            return self.context.dictation.handle_active_text(cleaned)

        for skill in self.skills:
            if skill.matches(cleaned):
                result = skill.handle(cleaned, self.context)
                if result.handled:
                    return result.response

        return self.ai_backend.reply(cleaned, self.context)

    def greeting(self) -> str:
        """Return a startup greeting."""
        return f"{self.config.name} online. Local intelligence systems are ready. How can I help?"
