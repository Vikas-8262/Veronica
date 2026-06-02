"""Live Web Search agent for Veronica."""

import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_search_request(message: str) -> bool:
    """Matcher for Web Search requests."""
    lowered = message.lower().strip()
    return lowered.startswith("search for ") or lowered.startswith("look up ") or "search the web" in lowered

def handle_search_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to search the web and synthesize results."""
    # We import dynamically to handle graceful failures
    duckduckgo_search = _optional_module("duckduckgo_search")
    
    if duckduckgo_search is None:
        return SkillResult(True, "Web Search requires 'duckduckgo-search'. Run: pip install duckduckgo-search")
        
    DDGS = getattr(duckduckgo_search, "DDGS", None)
    if DDGS is None:
         return SkillResult(True, "Invalid duckduckgo-search installation. Please update the package.")
         
    try:
        # Extract query
        query = message
        if query.lower().startswith("search for "):
            query = query[11:].strip()
        elif query.lower().startswith("look up "):
            query = query[8:].strip()
            
        if not query or query == "search the web":
            return SkillResult(True, "Please specify what you want to search for. For example: 'search for latest ai news'.")

        # Search the web
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            
        if not results:
            return SkillResult(True, f"I couldn't find any recent results for '{query}'.")
            
        # Format the results
        formatted = f"Here are the top web results for '{query}':\n\n"
        for i, res in enumerate(results, 1):
            title = res.get('title', 'No Title')
            body = res.get('body', 'No Description')
            href = res.get('href', '#')
            formatted += f"{i}. **{title}**\n   {body}\n   {href}\n\n"
            
        return SkillResult(True, formatted.strip())
        
    except Exception as e:
        return SkillResult(True, f"An error occurred during Web Search: {e}")
