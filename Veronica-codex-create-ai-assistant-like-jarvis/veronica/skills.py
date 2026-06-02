"""Built-in offline skills for Veronica."""

from __future__ import annotations

import ast
import datetime as dt
import operator
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .core_commands import handle_core_command, is_core_command
from .dictation import DictationController
from .fun import FunManager, is_fun_command
from .news import handle_news_command, is_news_command
from .ocr import handle_ocr_command, is_ocr_command
from .reminders import ReminderManager, is_reminder_command
from .system_stats import handle_stats_command, is_stats_command


@dataclass(slots=True)
class AssistantContext:
    """Shared context available to skills."""

    data_dir: Path
    assistant_name: str
    _dictation: DictationController = field(default_factory=DictationController, init=False, repr=False)
    _reminders: ReminderManager | None = field(default=None, init=False, repr=False)
    _fun: FunManager | None = field(default=None, init=False, repr=False)

    @property
    def notes_file(self) -> Path:
        return self.data_dir / "notes.txt"

    @property
    def reminders_file(self) -> Path:
        return self.data_dir / "reminders.json"

    @property
    def reminders(self) -> ReminderManager:
        if self._reminders is None:
            self._reminders = ReminderManager(self.data_dir)
        return self._reminders

    @property
    def fun(self) -> FunManager:
        if self._fun is None:
            self._fun = FunManager(self.data_dir)
        return self._fun

    @property
    def dictation(self) -> DictationController:
        return self._dictation

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class SkillResult:
    """Result returned by a skill handler."""

    handled: bool
    response: str


Matcher = Callable[[str], bool]
Handler = Callable[[str, AssistantContext], SkillResult]


@dataclass(slots=True)
class Skill:
    """A simple intent matcher and handler."""

    name: str
    matches: Matcher
    handle: Handler


def build_default_skills() -> list[Skill]:
    """Create the built-in skill registry."""
    return [
        Skill("exit", _contains_any("exit", "quit"), _exit),
        Skill("dictation", _is_dictation_request, _dictation),
        Skill("news", _is_news_request, _news),
        Skill("ocr", _is_ocr_request, _ocr),
        Skill("core", _is_core_request, _core),
        Skill("fun", _is_fun_request, _fun),
        Skill("help", _contains_any("help", "what can you do"), _help),
        Skill("time", _contains_any("time"), _time),
        Skill("date", _contains_any("date", "today"), _date),
        Skill("calculate", _is_calculation_request, _calculate),
        Skill("notes", _starts_with_any("remember", "note", "show notes", "list notes"), _notes),
        Skill("reminders", _is_reminder_request, _reminders),
        Skill("system", _is_stats_request, _system_status),
    ]


def _contains_any(*needles: str) -> Matcher:
    return lambda message: any(needle in message.lower() for needle in needles)


def _starts_with_any(*prefixes: str) -> Matcher:
    return lambda message: any(message.lower().startswith(prefix) for prefix in prefixes)


def _is_dictation_request(message: str) -> bool:
    lowered = message.lower()
    return (
        "dictation" in lowered
        or "type mode" in lowered
        or "type karo" in lowered
        or "yeh likho" in lowered
        or "yeh type karo" in lowered
    )


def _is_news_request(message: str) -> bool:
    return is_news_command(message)


def _is_ocr_request(message: str) -> bool:
    return is_ocr_command(message)


def _is_stats_request(message: str) -> bool:
    return is_stats_command(message)


def _is_core_request(message: str) -> bool:
    return is_core_command(message)


def _is_reminder_request(message: str) -> bool:
    return is_reminder_command(message)


def _is_fun_request(message: str) -> bool:
    return is_fun_command(message)


def _is_calculation_request(message: str) -> bool:
    lowered = message.lower().strip()
    if lowered.startswith(("calculate", "compute")):
        return True
    if lowered.startswith("what is"):
        expression = lowered.removeprefix("what is").strip()
        return bool(re.fullmatch(r"[0-9+\-*/().% ]+", expression))
    return False


def _exit(message: str, context: AssistantContext) -> SkillResult:
    return SkillResult(True, "Powering down. Goodbye.")


def _dictation(message: str, context: AssistantContext) -> SkillResult:
    response = context.dictation.handle_command(message)
    if response is None:
        return SkillResult(False, "")
    return SkillResult(True, response)


def _news(message: str, context: AssistantContext) -> SkillResult:
    response = handle_news_command(message)
    if response is None:
        return SkillResult(False, "")
    return SkillResult(True, response)


def _ocr(message: str, context: AssistantContext) -> SkillResult:
    response = handle_ocr_command(message)
    if response is None:
        return SkillResult(False, "")
    return SkillResult(True, response)


def _core(message: str, context: AssistantContext) -> SkillResult:
    response = handle_core_command(message, data_dir=context.data_dir)
    if response is None:
        return SkillResult(False, "")
    return SkillResult(True, response)


def _fun(message: str, context: AssistantContext) -> SkillResult:
    response = context.fun.handle(message)
    if response is None:
        return SkillResult(False, "")
    return SkillResult(True, response)


def _help(message: str, context: AssistantContext) -> SkillResult:
    return SkillResult(
        True,
        "I can check time and date, calculate expressions, remember notes, list notes, "
        "set timed reminders, show reminders, fetch optional news headlines, read screen text "
        "with local OCR, open apps, search the web, take screenshots, find files, "
        "tell jokes, play quiz, run focus mode, track productivity, auto-type text "
        "with dictation commands, report detailed system stats, and "
        "answer general questions with my fully local AI algorithms.",
    )


def _time(message: str, context: AssistantContext) -> SkillResult:
    now = dt.datetime.now().strftime("%H:%M")
    return SkillResult(True, f"The current time is {now}.")


def _date(message: str, context: AssistantContext) -> SkillResult:
    today = dt.date.today().strftime("%A, %B %d, %Y")
    return SkillResult(True, f"Today is {today}.")


def _calculate(message: str, context: AssistantContext) -> SkillResult:
    expression = message
    for prefix in ("calculate", "compute", "what is"):
        if expression.lower().startswith(prefix):
            expression = expression[len(prefix) :].strip()
            break

    if not expression:
        return SkillResult(True, "Give me an expression to calculate.")

    try:
        value = _safe_eval(expression)
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return SkillResult(True, f"I couldn't calculate that: {exc}")
    return SkillResult(True, f"The answer is {value}.")


def _notes(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower()
    context.ensure_data_dir()

    if lowered.startswith(("show notes", "list notes")):
        if not context.notes_file.exists() or not context.notes_file.read_text(encoding="utf-8").strip():
            return SkillResult(True, "You do not have any saved notes yet.")
        notes = context.notes_file.read_text(encoding="utf-8").strip()
        return SkillResult(True, f"Your notes:\n{notes}")

    note = message.split(" ", 1)[1].strip() if " " in message else ""
    if not note:
        return SkillResult(True, "Tell me what you want me to remember.")

    with context.notes_file.open("a", encoding="utf-8") as file:
        file.write(f"- {note}\n")
    return SkillResult(True, f"Noted: {note}")


def _reminders(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower()
    if lowered.startswith(("show reminders", "list reminders")) or lowered in {"reminders", "reminder list"}:
        return SkillResult(True, context.reminders.list_reminders())
    return SkillResult(True, context.reminders.parse_and_set_reminder(message))


def _system_status(message: str, context: AssistantContext) -> SkillResult:
    response = handle_stats_command(message)
    if response is None:
        return SkillResult(False, "")
    return SkillResult(True, response)


_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(expression: str) -> int | float:
    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree.body)


def _eval_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise ValueError("exponent is too large")
        return _ALLOWED_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_eval_node(node.operand))
    raise ValueError("only numeric expressions are allowed")
