"""Local AI algorithms for Veronica.

This module intentionally avoids hosted AI services, API keys, and network calls. It uses
small, transparent algorithms for tokenization, intent scoring, keyword extraction, and
response synthesis so Veronica remains fully local and inspectable.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import importlib
import importlib.util
from dataclasses import dataclass
from typing import Any, Iterable
import math
import random
import re
from dataclasses import dataclass
from typing import Iterable

from .skills import AssistantContext


_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9']+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "please",
    "the",
    "to",
    "we",
    "what",
    "when",
    "where",
    "with",
    "you",
    "your",
}


@dataclass(frozen=True, slots=True)
class LocalIntent:
    """An intent prototype used by the local similarity classifier."""

    name: str
    examples: tuple[str, ...]
    response_template: str


class LocalAIBackend:
    """A deterministic, local conversational backend.

    The backend combines three simple algorithms:
    1. tokenization and stop-word filtering,
    2. cosine similarity over term-frequency vectors for intent selection,
    3. template-based response synthesis using extracted keywords.
    """

    def __init__(self, seed: int = 7) -> None:
        self._random = random.Random(seed)
        self._intents = _build_intents()
        self._intent_vectors = {
            intent.name: _vectorize(" ".join(intent.examples)) for intent in self._intents
        }

    def reply(self, message: str, context: AssistantContext) -> str:
        provider = _ai_provider(context.data_dir)
        
        history = _load_history(context.data_dir)
        context_str = ""
        if history:
            context_str = "Conversation history:\n"
            for item in history:
                context_str += f"User: {item['user']}\nAssistant: {item['assistant']}\n"
            context_str += "\n"
            
        full_prompt = f"{context_str}User request: {message}"

        response_text = ""
        if provider == "ollama":
            ollama_text = _ollama_reply(full_prompt)
            if ollama_text:
                response_text = ollama_text
                
        elif provider == "gemini":
            gemini_text = _gemini_reply(full_prompt)
            if gemini_text:
                response_text = gemini_text

        if response_text:
            history.append({"user": message, "assistant": response_text})
            _save_history(context.data_dir, history)
            return response_text

        tokens = _content_tokens(message)
        if not tokens:
            return "I'm online locally. Give me a goal, question, or command."

        intent, score = self._classify(tokens)
        keywords = _keywords(tokens)

        if score >= 0.18:
            response_text = intent.response_template.format(
                assistant=context.assistant_name,
                keywords=_format_keywords(keywords),
            )
        else:
            response_text = self._synthesize_general_response(message, context, keywords)

        history.append({"user": message, "assistant": response_text})
        _save_history(context.data_dir, history)
        return response_text

    def _classify(self, tokens: list[str]) -> tuple[LocalIntent, float]:
        message_vector = _vectorize_tokens(tokens)
        scored = [
            (intent, _cosine_similarity(message_vector, self._intent_vectors[intent.name]))
            for intent in self._intents
        ]
        return max(scored, key=lambda item: item[1])

    def _synthesize_general_response(
        self,
        message: str,
        context: AssistantContext,
        keywords: list[str],
    ) -> str:
        opener = self._random.choice(
            (
                "I can reason about that locally.",
                "Running a local analysis.",
                "No cloud model needed; here is my local read.",
            )
        )
        focus = _format_keywords(keywords) if keywords else "your request"
        action = _question_strategy(message)
        return (
            f"{opener} The key focus appears to be {focus}. {action} "
            f"If you want, ask me to remember details, calculate values, or break this into a plan."
        )




def _optional_module(module_name: str):
    if importlib.util.find_spec(module_name) is None:
        return None
    return importlib.import_module(module_name)


def _ai_provider(data_dir: Path | None = None) -> str:
    if data_dir is not None:
        path = data_dir / "brain_config.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8")).get("provider", "local")
            except Exception:
                pass
    provider = os.getenv("VERONICA_AI_PROVIDER", "").strip().lower()
    if provider:
        return provider
    use_gemini = os.getenv("VERONICA_USE_GEMINI", "").strip().lower()
    if use_gemini in {"1", "true", "yes", "on"}:
        return "gemini"
        
    use_ollama = os.getenv("VERONICA_USE_OLLAMA", "").strip().lower()
    if use_ollama in {"1", "true", "yes", "on"}:
        return "ollama"
        
    return "local"


def _ollama_reply(message: str) -> str | None:
    requests = _optional_module("requests")
    if requests is None:
        return "Ollama mode ke liye requests install karo: pip install -r requirements-integrations.txt"

    model = os.getenv("OLLAMA_MODEL", "llama3")
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    url = f"{host}/api/generate"
    payload = {
        "model": model,
        "prompt": message,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except Exception as exc:
        return f"Ollama local request error: {exc}. Ensure Ollama is running (`ollama run llama3`)."

def _gemini_reply(message: str) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return "Gemini provider selected hai, but GEMINI_API_KEY set nahi hai."

    requests = _optional_module("requests")
    if requests is None:
        return "Gemini mode ke liye requests install karo: pip install -r requirements-integrations.txt"

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": message}]}]}

    try:
        response = requests.post(url, json=payload, timeout=20)
        data = response.json()
    except Exception as exc:
        return f"Gemini request error: {exc}"

    text = _extract_gemini_text(data)
    if text:
        return text
    return "Gemini response parse nahi ho saka."


def _extract_gemini_text(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        return ""
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content")
        if not isinstance(content, dict):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str) and part["text"].strip():
                return part["text"].strip()
    return ""
def _build_intents() -> list[LocalIntent]:
    return [
        LocalIntent(
            name="identity",
            examples=("who are you", "what is your name", "introduce yourself", "are you jarvis"),
            response_template=(
                "I am {assistant}, a fully local JARVIS-inspired assistant. My responses come from "
                "built-in algorithms for intent matching, keyword extraction, and response synthesis."
            ),
        ),
        LocalIntent(
            name="planning",
            examples=("make a plan", "break this down", "steps to build", "organize task"),
            response_template=(
                "Local plan for {keywords}: 1) define the goal, 2) list constraints, 3) split the work "
                "into small actions, 4) execute the next action, and 5) review the result."
            ),
        ),
        LocalIntent(
            name="automation",
            examples=("automate", "script", "workflow", "run command", "control computer"),
            response_template=(
                "For {keywords}, I can help design a local automation flow: trigger, required inputs, "
                "safe command, validation check, and rollback step."
            ),
        ),
        LocalIntent(
            name="coding",
            examples=("code", "program", "debug", "function", "python", "software"),
            response_template=(
                "For {keywords}, I recommend a local coding loop: reproduce the issue, isolate the "
                "smallest case, edit one component, run tests, then document the change."
            ),
        ),
        LocalIntent(
            name="security",
            examples=("secure", "password", "privacy", "safe", "permission", "encrypt"),
            response_template=(
                "Security note for {keywords}: keep secrets local, minimize permissions, validate inputs, "
                "log important actions, and require confirmation before destructive commands."
            ),
        ),
    ]


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text)]


def _content_tokens(text: str) -> list[str]:
    return [token for token in _tokenize(text) if token not in _STOP_WORDS]


def _keywords(tokens: Iterable[str], limit: int = 5) -> list[str]:
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    return [token for token, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _format_keywords(keywords: list[str]) -> str:
    if not keywords:
        return "the request"
    if len(keywords) == 1:
        return keywords[0]
    return ", ".join(keywords[:-1]) + f", and {keywords[-1]}"


def _vectorize(text: str) -> dict[str, float]:
    return _vectorize_tokens(_content_tokens(text))


def _vectorize_tokens(tokens: Iterable[str]) -> dict[str, float]:
    vector: dict[str, float] = {}
    for token in tokens:
        vector[token] = vector.get(token, 0.0) + 1.0
    return vector


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    shared = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _question_strategy(message: str) -> str:
    lowered = message.strip().lower()
    if lowered.startswith("how"):
        return "A useful next step is to turn the question into a sequence of actions and test the first action."
    if lowered.startswith("why"):
        return "I would compare likely causes, available evidence, and the assumptions behind each cause."
    if lowered.startswith("what"):
        return "I would define the terms, identify the desired output, and then choose the simplest useful answer."
    if lowered.startswith("can") or lowered.startswith("could"):
        return "I would check capability, risk, required inputs, and the safest way to proceed."
    return "I would treat it as a goal, identify missing information, and choose the next concrete step."

# ──────────────────────────────────────────────
# Chat History and Brain Switch Config
# ──────────────────────────────────────────────
def _get_history_file(data_dir: Path) -> Path:
    return data_dir / "chat_history.json"

def _load_history(data_dir: Path, limit: int = 5) -> list[dict[str, str]]:
    path = _get_history_file(data_dir)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))[-limit:]
        except Exception:
            pass
    return []

def _save_history(data_dir: Path, history: list[dict[str, str]]):
    path = _get_history_file(data_dir)
    try:
        path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    except Exception:
        pass

def _get_brain_file(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "brain_config.json"

def _load_brain_provider(data_dir: Path) -> str:
    path = _get_brain_file(data_dir)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("provider", "local")
        except Exception:
            pass
    prov = os.getenv("VERONICA_AI_PROVIDER", "").strip().lower()
    if prov in ("local", "ollama", "gemini"):
        return prov
    if os.getenv("VERONICA_USE_GEMINI", "").strip().lower() in ("1", "true", "yes", "on"):
        return "gemini"
    if os.getenv("VERONICA_USE_OLLAMA", "").strip().lower() in ("1", "true", "yes", "on"):
        return "ollama"
    return "local"

def _save_brain_provider(data_dir: Path, provider: str):
    path = _get_brain_file(data_dir)
    try:
        path.write_text(json.dumps({"provider": provider}, indent=2), encoding="utf-8")
    except Exception:
        pass

def is_brain_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered.startswith("set brain ")
        or lowered in ("brain status", "brain diagnostic", "brain diagnostics")
    )

def handle_brain_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    if lowered.startswith("set brain "):
        provider = lowered[10:].strip()
        if provider not in ("local", "ollama", "gemini"):
            return SkillResult(True, "Invalid provider. Choose: local, ollama, or gemini.")
        _save_brain_provider(context.data_dir, provider)
        return SkillResult(True, f"🧠 Brain provider updated to: **{provider.upper()}**")
        
    if lowered in ("brain status", "brain diagnostic", "brain diagnostics"):
        provider = _load_brain_provider(context.data_dir)
        ollama_status = "Not Checked"
        if provider == "ollama":
            requests = _optional_module("requests")
            if requests is None:
                ollama_status = "Ollama requires requests library."
            else:
                host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
                try:
                    resp = requests.get(f"{host}/api/tags", timeout=3)
                    if resp.status_code == 200:
                        models = [m["name"] for m in resp.json().get("models", [])]
                        ollama_status = f"✅ Connected (Models: {', '.join(models) if models else 'None'})"
                    else:
                        ollama_status = "⚠️ Error status from Ollama endpoint."
                except Exception as e:
                    ollama_status = f"❌ Offline ({e})"
        elif provider == "gemini":
            ollama_status = "N/A (using cloud Gemini)"
        else:
            ollama_status = "N/A (using keyword similarity)"
            
        report = (
            f"🧠 **AI Brain Configuration**\n"
            f"───────────────────────────\n"
            f"• Current Brain: **{provider.upper()}**\n"
            f"• Ollama Diagnostics: {ollama_status}\n"
            f"───────────────────────────\n"
            f"Use `set brain <local|ollama|gemini>` to select AI brain node."
        )
        return SkillResult(True, report)
    return SkillResult(False, "")
