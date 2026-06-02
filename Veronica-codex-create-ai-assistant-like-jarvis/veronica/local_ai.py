"""Local AI algorithms for Veronica — with Ollama smart fallback.

Built-in intent matching handles quick commands. For anything complex or
conversational, Ollama (Mistral) takes over automatically.
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass
from typing import Iterable

from .skills import AssistantContext


_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9']+")
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "our",
    "please", "the", "to", "we", "what", "when", "where", "with", "you", "your",
}

# Ollama config — change model name here if needed
OLLAMA_MODEL = "gemma3:4b"
OLLAMA_SYSTEM_PROMPT = (
    "You are Veronica, a JARVIS-inspired AI assistant. "
    "You are helpful, smart, and speak in a natural, friendly tone. "
    "Keep replies short and conversational — 1 to 3 sentences max. "
    "If the user speaks Hindi or Hinglish, reply in Hinglish naturally."
)


def _ask_ollama(text: str) -> str | None:
    """Send message to Ollama and return response. Returns None if unavailable."""
    try:
        import ollama
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": OLLAMA_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        return response["message"]["content"].strip()
    except Exception:
        return None


@dataclass(frozen=True, slots=True)
class LocalIntent:
    """An intent prototype used by the local similarity classifier."""

    name: str
    examples: tuple[str, ...]
    response_template: str


class LocalAIBackend:
    """Conversational backend with Ollama smart fallback.

    Flow:
    1. Try built-in intent matching (fast, offline).
    2. If confidence is low, ask Ollama (Mistral) for a smart reply.
    3. If Ollama is unavailable, fall back to local synthesis.
    """

    def __init__(self, seed: int = 7) -> None:
        self._random = random.Random(seed)
        self._intents = _build_intents()
        self._intent_vectors = {
            intent.name: _vectorize(" ".join(intent.examples)) for intent in self._intents
        }

    def reply(self, message: str, context: AssistantContext) -> str:
        tokens = _content_tokens(message)
        if not tokens:
            return "Main online hoon. Batao kya karna hai?"

        intent, score = self._classify(tokens)
        keywords = _keywords(tokens)

        # High confidence — use built-in intent
        if score >= 0.35:
            return intent.response_template.format(
                assistant=context.assistant_name,
                keywords=_format_keywords(keywords),
            )

        # Low confidence — ask Ollama for smart response
        ollama_reply = _ask_ollama(message)
        if ollama_reply:
            return ollama_reply

        # Ollama unavailable — use local synthesis
        return self._synthesize_general_response(message, context, keywords)

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
                "Main locally soch sakta hoon is baare mein.",
                "Yeh interesting question hai.",
                "Local analysis chal rahi hai.",
            )
        )
        focus = _format_keywords(keywords) if keywords else "aapki request"
        action = _question_strategy(message)
        return (
            f"{opener} Focus area: {focus}. {action} "
            f"Chahein to mujhe details yaad karne, calculate karne, ya plan banane ko bolein."
        )


def _build_intents() -> list[LocalIntent]:
    return [
        LocalIntent(
            name="identity",
            examples=("who are you", "what is your name", "introduce yourself", "are you jarvis", "kaun ho tum"),
            response_template=(
                "Main {assistant} hoon — ek JARVIS-inspired AI assistant. "
                "Main locally kaam karta hoon, koi cloud ya API key ki zarurat nahi."
            ),
        ),
        LocalIntent(
            name="planning",
            examples=("make a plan", "break this down", "steps to build", "organize task", "plan banao"),
            response_template=(
                "Plan for {keywords}: 1) Goal define karo, 2) Constraints list karo, "
                "3) Kaam ko chhote steps mein toddo, 4) Pehla step execute karo, 5) Result review karo."
            ),
        ),
        LocalIntent(
            name="automation",
            examples=("automate", "script", "workflow", "run command", "control computer", "automation"),
            response_template=(
                "{keywords} ke liye automation flow: trigger → inputs → safe command → validation → rollback step."
            ),
        ),
        LocalIntent(
            name="coding",
            examples=("code", "program", "debug", "function", "python", "software", "coding"),
            response_template=(
                "{keywords} ke liye: issue reproduce karo, smallest case isolate karo, "
                "ek component edit karo, tests run karo, phir document karo."
            ),
        ),
        LocalIntent(
            name="security",
            examples=("secure", "password", "privacy", "safe", "permission", "encrypt", "security"),
            response_template=(
                "{keywords} security tip: secrets local rakho, permissions minimize karo, "
                "inputs validate karo, important actions log karo."
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
        return "Pehle question ko actions mein toddo aur pehla action test karo."
    if lowered.startswith("why"):
        return "Likely causes, evidence, aur assumptions compare karo."
    if lowered.startswith("what"):
        return "Terms define karo, desired output identify karo, phir sabse chhota useful answer do."
    if lowered.startswith("can") or lowered.startswith("could"):
        return "Capability, risk, required inputs, aur safest approach check karo."
    return "Goal identify karo, missing info dhundo, aur next concrete step choose karo."