"""Website and URL Summarizer Agent for Veronica.

Fetches the contents of a target webpage or article, extracts the main readable text,
and generates a structured summary using Gemini (or a smart local fallback).
"""

import os
import re
import importlib
from urllib.parse import urlparse
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_summarizer_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered.startswith("summarize url ")
        or lowered.startswith("summarize article ")
        or lowered.startswith("summarize website ")
        or lowered.startswith("web summarize ")
        or lowered.startswith("url summarize ")
    )

# ──────────────────────────────────────────────
# URL Text Extractor
# ──────────────────────────────────────────────
def extract_text_from_url(url: str) -> tuple[str, str | None]:
    """Fetch URL and extract main body text. Returns (cleaned_text, error_message)."""
    requests = _optional_module("requests")
    if not requests:
        return "", "requests is not installed. Run: pip install requests"

    # Add a user-agent to avoid HTTP 403 Forbidden on common websites
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            return "", f"HTTP Error {resp.status_code}: Unable to access webpage."
        
        html_content = resp.text
        
        # Try using BeautifulSoup if available
        bs4 = _optional_module("bs4")
        if bs4:
            soup = bs4.BeautifulSoup(html_content, "html.parser")
            
            # Remove scripts, styles, navs, headers, footers
            for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
                element.decompose()
                
            text = soup.get_text(separator=" ")
        else:
            # Fallback basic regex cleaning if bs4 is not available
            # Remove script, style, header, footer, nav, aside content blocks
            cleaned = re.sub(r'<(script|style|header|footer|nav|aside).*?>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            # Strip remaining HTML tags
            text = re.sub(r'<[^>]*>', ' ', cleaned)
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned_text = " ".join(chunk for chunk in chunks if chunk)
        
        if not cleaned_text.strip():
            return "", "Webpage has no readable text content."
            
        # Limit text length to prevent context blowup (e.g. max 5000 words)
        words = cleaned_text.split()
        if len(words) > 4000:
            cleaned_text = " ".join(words[:4000]) + "..."
            
        return cleaned_text, None
        
    except Exception as e:
        return "", f"Connection failed: {e}"

# ──────────────────────────────────────────────
# Summarization Logic
# ──────────────────────────────────────────────
def summarize_text(text: str, url: str) -> str:
    """Generate summary using Gemini or local template fallback."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    requests = _optional_module("requests")
    
    domain = urlparse(url).netloc
    
    # If Gemini is enabled/configured, use it!
    if api_key and requests:
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        prompt = (
            f"Please read the following text extracted from {domain} and generate a concise summary. "
            f"Highlight key takeaways, main arguments, or core topics in a bulleted format. "
            f"Keep it professional and easy to scan.\n\nText:\n{text}"
        )
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        try:
            resp = requests.post(endpoint, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                summary = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return f"📰 **Web Summary ({domain})**\n\n{summary}"
        except Exception as e:
            # Fall back to local if network fails
            pass
            
    # Local fallback/dry-run summary
    words = text.split()
    total_words = len(words)
    preview = " ".join(words[:40]) + "..." if total_words > 40 else text
    
    return (
        f"📰 **Web Summary ({domain}) [Local Offline Mode]**\n\n"
        f"• **Source**: {url}\n"
        f"• **Length**: {total_words} words extracted.\n"
        f"• **Preview**: \"{preview}\"\n\n"
        f"*(Optional: Enable Gemini mode with `set router policy gemini` & `GEMINI_API_KEY` for full AI summaries)*"
    )

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_summarizer_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    
    # Extract URL from prompt
    prefixes = ["summarize url ", "summarize article ", "summarize website ", "web summarize ", "url summarize "]
    target_url = ""
    for prefix in prefixes:
        if lowered.startswith(prefix):
            target_url = message[len(prefix):].strip()
            break
            
    if not target_url:
        return SkillResult(True, "Please provide a valid URL to summarize (e.g. `summarize URL https://example.com`).")
        
    # Ensure scheme is present
    if not target_url.startswith(("http://", "https://")):
        # Basic guess
        target_url = "https://" + target_url
        
    # Basic URL structure check
    parsed = urlparse(target_url)
    if not parsed.netloc or "." not in parsed.netloc:
        return SkillResult(True, f"❌ Invalid URL provided: '{target_url}'")
        
    # Run fetch and summarize
    print(f"   [Summarizer] Fetching content from: {target_url}")
    text, err = extract_text_from_url(target_url)
    if err:
        return SkillResult(True, f"❌ Summarizer Error: {err}")
        
    summary = summarize_text(text, target_url)
    return SkillResult(True, summary)
