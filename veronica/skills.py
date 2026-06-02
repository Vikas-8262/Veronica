"""Built-in offline skills for Veronica."""

from __future__ import annotations

import ast
import datetime as dt
import operator
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .advanced import roadmap_mark_done, roadmap_next, roadmap_reset, roadmap_status
from .core_commands import handle_core_command, is_core_command
from .dictation import DictationController
from .fun import FunManager, is_fun_command
from .news import handle_news_command, is_news_command
from .openclaw_bridge import bridge_status, list_tools, run_tool
from .openclaw_runtime import handle_runtime_command
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
    def memory_file(self) -> Path:
        return self.data_dir / "memory.json"

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
    from .crew_agent import is_crew_request, handle_crew_request
    from .flow_agent import is_flow_request, handle_flow_request
    from .extractor_agent import is_extraction_request, handle_extraction_request
    from .sandbox_agent import is_sandbox_request, handle_sandbox_request
    from .canvas_agent import is_canvas_request, handle_canvas_request
    from .vision_agent import is_vision_request, handle_vision_request
    from .search_agent import is_search_request, handle_search_request
    from .iot_agent import is_iot_request, handle_iot_request
    from .media_agent import is_media_request, handle_media_request
    from .computer_use_agent import is_computer_request, handle_computer_request
    from .document_agent import is_doc_request, handle_doc_request
    from .system_os_agent import is_os_request, handle_os_request
    from .voice_agent import is_voice_request, handle_voice_request
    from .email_agent import is_email_request, handle_email_request
    from .youtube_agent import is_youtube_request, handle_youtube_request
    from .whatsapp_agent import is_whatsapp_request, handle_whatsapp_request
    from .camera_agent import is_camera_request, handle_camera_request
    from .reminder_agent import is_reminder_request, handle_reminder_request
    from .weather_agent import is_weather_request, handle_weather_request
    from .news_agent import is_news_request, handle_news_request
    from .finance_agent import is_finance_request, handle_finance_request
    from .wiki_agent import is_wiki_request, handle_wiki_request
    from .speedtest_agent import is_speedtest_request, handle_speedtest_request
    from .syshealth_agent import is_syshealth_request, handle_syshealth_request
    from .clipboard_agent import is_clipboard_request, handle_clipboard_request
    from .translator_agent import is_translator_request, handle_translator_request
    from .qrcode_agent import is_qrcode_request, handle_qrcode_request
    from .research_agent import is_research_request, handle_research_request
    from .screen_agent import is_screen_request, handle_screen_request
    from .coder_agent import is_coder_request, handle_coder_request
    from .memory_agent import is_memory_request, handle_memory_request
    from .rag_agent import is_rag_request, handle_rag_request
    from .router_agent import is_router_request, handle_router_request
    from .plugin_agent import is_plugin_request, handle_plugin_request, load_plugins, get_dynamic_plugin_skills
    from .runner_agent import is_runner_request, handle_runner_request
    from .doctor_agent import is_doctor_request, handle_doctor_request
    from .policy_agent import is_policy_request, handle_policy_request
    from .voice_v2_agent import is_voice_v2_request, handle_voice_v2_request
    from .macro_agent import is_macro_request, handle_macro_request
    from .mobile_v2_agent import is_mobile_v2_request, handle_mobile_v2_request
    from .dashboard_agent import is_dashboard_request, handle_dashboard_request
    from .gui_viewer_agent import is_gui_viewer_request, handle_gui_viewer_request
    from .git_committer_agent import is_git_committer_request, handle_git_committer_request
    from .api_tester_agent import is_api_tester_request, handle_api_tester_request
    from .soundboard_agent import is_soundboard_request, handle_soundboard_request
    from .summarizer_agent import is_summarizer_request, handle_summarizer_request
    from .login_agent import is_login_request, handle_login_request
    from .media_control_agent import is_media_control_request, handle_media_control_request
    from .calendar_agent import is_calendar_request, handle_calendar_request

    load_plugins()

    core_skills = [
        # 1. Exit / Meta Control
        Skill("exit", _contains_any("exit", "quit"), _exit),
        Skill("router", is_router_request, handle_router_request),
        Skill("plugins", is_plugin_request, handle_plugin_request),
        Skill("runner", is_runner_request, handle_runner_request),
        
        # 2. Specific Agents / Skills (Checked before Core to prevent greeting/open hijacking)
        Skill("doctor", is_doctor_request, handle_doctor_request),
        Skill("policy", is_policy_request, handle_policy_request),
        Skill("voice_v2", is_voice_v2_request, handle_voice_v2_request),
        Skill("macro", is_macro_request, handle_macro_request),
        Skill("mobile_v2", is_mobile_v2_request, handle_mobile_v2_request),
        Skill("dashboard", is_dashboard_request, handle_dashboard_request),
        Skill("gui_viewer", is_gui_viewer_request, handle_gui_viewer_request),
        Skill("git_committer", is_git_committer_request, handle_git_committer_request),
        Skill("api_tester", is_api_tester_request, handle_api_tester_request),
        Skill("soundboard", is_soundboard_request, handle_soundboard_request),
        Skill("summarizer", is_summarizer_request, handle_summarizer_request),
        Skill("login_automation", is_login_request, handle_login_request),
        Skill("media_control", is_media_control_request, handle_media_control_request),
        Skill("calendar", is_calendar_request, handle_calendar_request),
        Skill("email", is_email_request, handle_email_request),
        Skill("whatsapp", is_whatsapp_request, handle_whatsapp_request),
        Skill("dictation", _is_dictation_request, _dictation),
        Skill("news_offline", _is_news_request, _news),
        Skill("ocr", _is_ocr_request, _ocr),
        Skill("openclaw", _is_openclaw_request, _openclaw),
        Skill("fun", _is_fun_request, _fun),
        Skill("advanced", _is_advanced_request, _advanced),
        Skill("help", _contains_any("help", "what can you do"), _help),
        Skill("crewai", is_crew_request, handle_crew_request),
        Skill("flow", is_flow_request, handle_flow_request),
        Skill("extract", is_extraction_request, handle_extraction_request),
        Skill("sandbox", is_sandbox_request, handle_sandbox_request),
        Skill("canvas", is_canvas_request, handle_canvas_request),
        Skill("vision", is_vision_request, handle_vision_request),
        Skill("search", is_search_request, handle_search_request),
        Skill("iot", is_iot_request, handle_iot_request),
        Skill("media", is_media_request, handle_media_request),
        Skill("computer", is_computer_request, handle_computer_request),
        Skill("document", is_doc_request, handle_doc_request),
        Skill("voice_input", is_voice_request, handle_voice_request),
        Skill("youtube", is_youtube_request, handle_youtube_request),
        Skill("camera", is_camera_request, handle_camera_request),
        Skill("reminder", is_reminder_request, handle_reminder_request),
        Skill("news", is_news_request, handle_news_request),
        Skill("finance", is_finance_request, handle_finance_request),
        Skill("speedtest", is_speedtest_request, handle_speedtest_request),
        Skill("memory", is_memory_request, handle_memory_request),
        Skill("syshealth", is_syshealth_request, handle_syshealth_request),
        Skill("clipboard", is_clipboard_request, handle_clipboard_request),
        Skill("translator", is_translator_request, handle_translator_request),
        Skill("qrcode", is_qrcode_request, handle_qrcode_request),
        Skill("research", is_research_request, handle_research_request),
        Skill("screen", is_screen_request, handle_screen_request),
        Skill("coder", is_coder_request, handle_coder_request),
        Skill("rag", is_rag_request, handle_rag_request),

        # 3. Core command router (VEER-style Hinglish and common mappings)
        Skill("core", _is_core_request, _core),

        # 4. Standard Basic / Fallback skills (Checked after Core so Core Hinglish takes precedence)
        Skill("time", _contains_any("time"), _time),
        Skill("date", _contains_any("date", "today"), _date),
        Skill("weather", is_weather_request, handle_weather_request),
        Skill("os_control", is_os_request, handle_os_request),
        Skill("calculate", _is_calculation_request, _calculate),
        Skill("wikipedia", is_wiki_request, handle_wiki_request),
        Skill("notes", _starts_with_any("remember", "note", "show notes", "list notes"), _notes),
        Skill("reminders", _is_reminder_request, _reminders),
        Skill("system", _is_stats_request, _system_status),
    ]
    core_skills.extend(get_dynamic_plugin_skills())
    return core_skills


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








def _is_openclaw_request(message: str) -> bool:
    lowered = message.lower().strip()
    voice_triggers = ("start voice", "voice start", "wake word on", "voice on", 
                      "stop voice", "voice stop", "wake word off", "voice off", 
                      "voice status", "wake word status")
    return lowered.startswith(("openclaw", "claw")) or lowered in voice_triggers


def _openclaw(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    context.ensure_data_dir()

    if lowered in {"start voice", "voice start", "wake word on", "voice on"}:
        return SkillResult(True, handle_runtime_command("openclaw full voice start"))
    if lowered in {"stop voice", "voice stop", "wake word off", "voice off"}:
        return SkillResult(True, handle_runtime_command("openclaw full voice stop"))
    if lowered in {"voice status", "wake word status"}:
        return SkillResult(True, handle_runtime_command("openclaw full voice status"))

    if lowered.startswith(("openclaw full", "claw full")):
        return SkillResult(True, handle_runtime_command(message))

    if lowered in {"openclaw", "openclaw status", "claw status"}:
        return SkillResult(True, bridge_status(context.data_dir))
    if lowered in {"openclaw tools", "claw tools"}:
        return SkillResult(True, list_tools(context.data_dir))
    if lowered.startswith(("openclaw run ", "claw run ")):
        tool_name = message.split(maxsplit=2)[-1].strip()
        return SkillResult(True, run_tool(context.data_dir, tool_name))

    return SkillResult(True, "Use: openclaw status | openclaw tools | openclaw run <tool_name> | openclaw full status")
def _is_advanced_request(message: str) -> bool:
    lowered = message.lower().strip()
    return lowered.startswith(("advance", "advanced roadmap", "roadmap"))


def _advanced(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    context.ensure_data_dir()

    if lowered in {"advance status", "advanced roadmap", "roadmap", "roadmap status"}:
        return SkillResult(True, roadmap_status(context.data_dir))
    if lowered in {"advance next", "roadmap next"}:
        return SkillResult(True, roadmap_next(context.data_dir))
    if lowered in {"advance reset", "roadmap reset"}:
        return SkillResult(True, roadmap_reset(context.data_dir))

    if lowered.startswith(("advance done ", "roadmap done ")):
        key = message.split(maxsplit=2)[-1]
        return SkillResult(True, roadmap_mark_done(context.data_dir, key))

    return SkillResult(
        True,
        "Use: advance status | advance next | advance done <step_key> | advance reset",
    )
def _is_memory_request(message: str) -> bool:
    lowered = message.lower().strip()
    return lowered.startswith((
        "remember that",
        "save memory",
        "store memory",
        "show memory",
        "list memory",
        "forget memory",
        "delete memory",
    ))


def _load_memory(context: AssistantContext) -> dict[str, str]:
    if not context.memory_file.exists():
        return {}
    try:
        import json

        data = json.loads(context.memory_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def _save_memory(context: AssistantContext, memory: dict[str, str]) -> None:
    import json

    context.memory_file.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")


def _memory(message: str, context: AssistantContext) -> SkillResult:
    context.ensure_data_dir()
    lowered = message.lower().strip()
    memory = _load_memory(context)

    if lowered.startswith(("show memory", "list memory")):
        if not memory:
            return SkillResult(True, "Memory store empty hai.")
        lines = [f"- {k}: {v}" for k, v in sorted(memory.items())]
        return SkillResult(True, "Saved memory:\n" + "\n".join(lines))

    if lowered.startswith(("forget memory", "delete memory")):
        key = message.split(maxsplit=2)[-1].strip() if len(message.split()) >= 3 else ""
        if not key:
            return SkillResult(True, "Kaunsa memory key delete karna hai?")
        if key not in memory:
            return SkillResult(True, f"Memory key '{key}' mila nahi.")
        del memory[key]
        _save_memory(context, memory)
        return SkillResult(True, f"Memory '{key}' delete kar diya.")

    body = ""
    if lowered.startswith("remember that"):
        body = message[len("remember that") :].strip()
    elif lowered.startswith(("save memory", "store memory")):
        body = message.split(maxsplit=2)[-1].strip() if len(message.split()) >= 3 else ""

    if "=" not in body:
        return SkillResult(True, "Use format: remember that key = value")
    key, value = [part.strip() for part in body.split("=", 1)]
    if not key or not value:
        return SkillResult(True, "Key aur value dono dene honge: key = value")

    memory[key] = value
    _save_memory(context, memory)
    return SkillResult(True, f"Memory saved: {key} = {value}")
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
        "set timed reminders, show reminders, save/list/delete structured memory, fetch optional news headlines, read screen text "
        "with local OCR, open apps, search the web, take screenshots, find files, "
        "tell jokes, play quiz, run focus mode, track productivity, auto-type text "
        "with dictation commands, report detailed system stats, and "
        "answer general questions with my fully local AI algorithms. I can also track advanced roadmap steps and expose an OpenClaw-style bridge with openclaw status/tools/run.",
        "answer general questions with my fully local AI algorithms. I can also track advanced roadmap steps with advance status/next/done.",
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
