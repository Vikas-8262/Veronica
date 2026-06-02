"""Optional news headline support for Veronica.

This module adapts the user-provided VEER news flow while avoiding hardcoded
secrets. It uses NewsAPI only when the user provides `NEWS_API_KEY` in the local
environment. The feature is not AI-based and is isolated from Veronica's local AI
backend.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

MAX_HEADLINES = 5
NEWS_ENDPOINT = "https://newsapi.org/v2/everything"

CATEGORY_QUERIES = {
    "technology": "technology India",
    "sports": "sports India cricket",
    "business": "business economy India",
    "health": "health India",
    "science": "science India",
    "world": "world news",
    "general": "India news today",
}

CATEGORY_MAP = {
    "tech": "technology",
    "technology": "technology",
    "sports": "sports",
    "khel": "sports",
    "business": "business",
    "vyapaar": "business",
    "world": "world",
    "duniya": "world",
    "health": "health",
    "sehat": "health",
    "science": "science",
    "vigyan": "science",
}

NEWS_COMMAND_WORDS = ("news", "khabar", "headlines")
QUIZ_WORDS = ("quiz", "khelo", "sawaal")


@dataclass(frozen=True, slots=True)
class NewsConfig:
    """Configuration for headline lookup."""

    api_key_env: str = "NEWS_API_KEY"
    max_headlines: int = MAX_HEADLINES
    endpoint: str = NEWS_ENDPOINT


def is_news_command(command: str) -> bool:
    """Return True when a message looks like a news/headline request."""
    normalized = _normalize(command)
    tokens = set(normalized.split())
    if tokens & set(QUIZ_WORDS):
        return False
    if tokens & set(NEWS_COMMAND_WORDS):
        return True
    return normalized in CATEGORY_MAP


def handle_news_command(command: str, config: NewsConfig | None = None) -> str | None:
    """Return a news response for a supported command, otherwise None."""
    normalized = _normalize(command)
    if not is_news_command(normalized):
        return None

    tokens = set(normalized.split())
    for key, category in CATEGORY_MAP.items():
        if key in tokens or normalized == key:
            return get_headlines(category, config=config)

    return get_headlines("general", config=config)


def get_headlines(category: str = "general", config: NewsConfig | None = None) -> str:
    """Fetch and format top headlines for a category using optional NewsAPI credentials."""
    active_config = config or NewsConfig()
    api_key = os.getenv(active_config.api_key_env, "").strip()
    if not api_key:
        return f"News ke liye {active_config.api_key_env} environment variable set karo."

    requests = _optional_module("requests")
    if requests is None:
        return "News ke liye requests install karo: pip install -r requirements-news.txt"

    query = CATEGORY_QUERIES.get(category, CATEGORY_QUERIES["general"])
    params = urlencode(
        {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "apiKey": api_key,
            "pageSize": active_config.max_headlines,
        }
    )
    url = f"{active_config.endpoint}?{params}"

    try:
        response = requests.get(url, timeout=8)
        data = response.json()
    except requests.exceptions.ConnectionError:
        return "Internet nahi hai."
    except requests.exceptions.Timeout:
        return "News request timeout ho gaya."
    except ValueError:
        return "News response samajh nahi aaya."
    except Exception as exc:  # pragma: no cover - defensive third-party boundary
        return f"News error: {exc}"

    if data.get("status") != "ok":
        return f"News error: {data.get('message', 'unknown')}"

    headlines = _extract_headlines(data, max_headlines=active_config.max_headlines)
    if not headlines:
        return "Koi headline nahi mili."
    return f"Yeh hain aaj ki top {category} news: " + " ... ".join(headlines)


def _extract_headlines(data: dict[str, Any], max_headlines: int = MAX_HEADLINES) -> list[str]:
    headlines: list[str] = []
    articles = data.get("articles", [])
    for article in articles[:max_headlines]:
        title = str(article.get("title", "")).split(" - ")[0].strip()
        if title and "[Removed]" not in title and len(title) > 10:
            headlines.append(f"{len(headlines) + 1}. {title}")
    return headlines


def _optional_module(module_name: str):
    if importlib.util.find_spec(module_name) is None:
        return None
    return importlib.import_module(module_name)


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())
