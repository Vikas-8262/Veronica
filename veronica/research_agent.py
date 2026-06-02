"""Autonomous Deep Research & Report Writer agent for Veronica.

Pipeline:
  1. Search  - DuckDuckGo top-5 URLs for the topic
  2. Scrape  - Parallel fetch & parse of each page (threading)
  3. Synthesize - Gemini LLM compiles a structured research report
  4. Save    - Timestamped .md written to Desktop, auto-opened
"""

import importlib
import os
import datetime
import threading
import re
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_research_request(message: str) -> bool:
    lowered = message.lower().strip()
    return any(phrase in lowered for phrase in (
        "research ", "write a report on", "write a report about",
        "deep dive into", "investigate ", "find out about",
    ))

# ──────────────────────────────────────────────
# Step 1 — Search
# ──────────────────────────────────────────────
def _search_topic(topic: str, max_results: int = 5) -> list[str]:
    """Return a list of URLs via DuckDuckGo."""
    ddg = _optional_module("duckduckgo_search")
    if ddg is None:
        return []
    try:
        ddgs = ddg.DDGS()
        results = list(ddgs.text(topic, max_results=max_results))
        return [r.get("href", "") for r in results if r.get("href")]
    except Exception:
        return []

# ──────────────────────────────────────────────
# Step 2 — Scrape
# ──────────────────────────────────────────────
def _scrape_url(url: str, results: list, index: int) -> None:
    """Scrape readable text from a single URL into results[index]."""
    requests = _optional_module("requests")
    bs4 = _optional_module("bs4")
    if not requests or not bs4:
        results[index] = ""
        return
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; VeronicaBot/1.0)"}
        resp = requests.get(url, timeout=10, headers=headers)
        soup = bs4.BeautifulSoup(resp.text, "html.parser")

        # Remove clutter
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Collapse whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Limit to first 3000 chars per source to stay within token budget
        results[index] = text[:3000]
    except Exception:
        results[index] = ""

def _scrape_all(urls: list[str]) -> list[str]:
    """Scrape all URLs in parallel using threads."""
    results = [""] * len(urls)
    threads = []
    for i, url in enumerate(urls):
        t = threading.Thread(target=_scrape_url, args=(url, results, i))
        t.daemon = True
        threads.append(t)
        t.start()
    for t in threads:
        t.join(timeout=15)
    return results

# ──────────────────────────────────────────────
# Step 3 — Synthesize via Gemini
# ──────────────────────────────────────────────
def _synthesize(topic: str, sources: list[str], urls: list[str]) -> str:
    """Send scraped data to Gemini and return the formatted report."""
    requests = _optional_module("requests")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not requests or not api_key:
        return ""

    # Build the context block
    context_parts = []
    for i, (url, text) in enumerate(zip(urls, sources)):
        if text.strip():
            context_parts.append(f"--- Source {i+1}: {url} ---\n{text}\n")

    context = "\n".join(context_parts) if context_parts else "No sources could be scraped."

    prompt = f"""You are an elite research analyst. Using the source material below, write a comprehensive, professional research report on the topic: "{topic}".

The report MUST follow this exact structure with markdown headers:

# Research Report: {topic}

## Executive Summary
(3-4 sentence high-level overview of the topic and key insights)

## Background & Context
(What is this topic? History and foundational knowledge)

## Key Findings
(Bullet-pointed main discoveries, facts, and insights from the sources)

## Current Developments & Trends
(What is happening right now? Recent news and innovations)

## Expert Perspectives
(What do experts, researchers, or industry leaders say?)

## Conclusion & Implications
(What does this mean for the future? What should a reader take away?)

## Sources Consulted
(List the source URLs used)

SOURCE MATERIAL:
{context}

Write the full report now. Be comprehensive, insightful, and professional. Use markdown formatting throughout."""

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096,
        }
    }

    try:
        resp = requests.post(url, json=payload, timeout=90)
        data = resp.json()
        if "candidates" in data and data["candidates"]:
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    return part["text"].strip()
        return f"[Gemini returned no content: {data.get('error', data)}]"
    except Exception as e:
        return f"[Gemini synthesis failed: {e}]"

# ──────────────────────────────────────────────
# Step 4 — Save Report
# ──────────────────────────────────────────────
def _save_report(topic: str, content: str) -> str:
    """Save the report to the Desktop and return the filepath."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = re.sub(r'[^\w\s-]', '', topic).strip().replace(' ', '_')[:40]
    filename = f"research_{safe_topic}_{timestamp}.md"
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    filepath = os.path.join(desktop, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_research_request(message: str, context: AssistantContext) -> SkillResult:
    """Orchestrate the full autonomous research pipeline."""
    # Parse topic from command
    lowered = message.lower().strip()
    topic = message.strip()
    prefixes = [
        "research ", "write a report on ", "write a report about ",
        "deep dive into ", "investigate ", "find out about ",
    ]
    for prefix in prefixes:
        if lowered.startswith(prefix):
            topic = message[len(prefix):].strip().strip("?.!")
            break

    if not topic or len(topic) < 3:
        return SkillResult(True, "Please specify a topic (e.g., 'Research quantum computing').")

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return SkillResult(True, "Research Agent requires a GEMINI_API_KEY environment variable to synthesize the report.")

    print(f"\n🔬 [RESEARCH AGENT ACTIVATED]")
    print(f"📌 Topic: {topic}")

    # ── Phase 1: Search ──
    print("🔍 [Phase 1/4] Searching the web for relevant sources...")
    urls = _search_topic(topic, max_results=5)
    if not urls:
        return SkillResult(True, "Could not find any search results. Check that `duckduckgo-search` is installed.")
    print(f"   ✅ Found {len(urls)} sources")

    # ── Phase 2: Scrape ──
    print("🌐 [Phase 2/4] Scraping sources in parallel...")
    scraped = _scrape_all(urls)
    valid = sum(1 for s in scraped if s.strip())
    print(f"   ✅ Successfully scraped {valid}/{len(urls)} sources")

    # ── Phase 3: Synthesize ──
    print("🧠 [Phase 3/4] Synthesizing report with Gemini (this may take ~30s)...")
    report_content = _synthesize(topic, scraped, urls)
    if not report_content:
        return SkillResult(True, "Gemini synthesis failed. Ensure your GEMINI_API_KEY is valid.")
    print("   ✅ Report synthesized")

    # ── Phase 4: Save ──
    print("💾 [Phase 4/4] Saving report to Desktop...")
    filepath = _save_report(topic, report_content)
    print(f"   ✅ Saved: {filepath}")

    # Auto-open
    try:
        os.startfile(filepath)
    except Exception:
        import subprocess
        subprocess.Popen(["start", filepath], shell=True)

    word_count = len(report_content.split())

    return SkillResult(True, (
        f"\n✅ Research Complete!\n\n"
        f"📄 Report: {os.path.basename(filepath)}\n"
        f"📁 Location: {filepath}\n"
        f"📊 Length: ~{word_count:,} words\n"
        f"🌐 Sources: {len(urls)} web pages analyzed\n\n"
        f"The report has been opened automatically!"
    ))
