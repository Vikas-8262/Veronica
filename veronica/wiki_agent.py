"""Wikipedia Integration agent for Veronica."""

import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_wiki_request(message: str) -> bool:
    """Matcher for Wikipedia requests."""
    lowered = message.lower().strip()
    return lowered.startswith(("who is", "what is", "search wikipedia for")) or "wikipedia" in lowered

def handle_wiki_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to query Wikipedia for a factual summary."""
    wikipedia = _optional_module("wikipedia")
    if wikipedia is None:
        return SkillResult(True, "Wikipedia Agent requires 'wikipedia'. Run: pip install wikipedia")

    lowered = message.lower().strip()
    
    # Extract search term
    search_term = lowered
    prefixes = ["who is", "what is", "search wikipedia for", "search wikipedia", "look up on wikipedia"]
    for prefix in prefixes:
        if search_term.startswith(prefix):
            search_term = search_term[len(prefix):].strip()
            break
            
    # Clean up trailing punctuation
    search_term = search_term.strip("?.! ")
    
    if not search_term:
        return SkillResult(True, "Please specify what you want to search for on Wikipedia (e.g., 'Who is Alan Turing?').")
        
    try:
        print(f"📚 [Searching Wikipedia for '{search_term}'...]")
        
        # Fetch summary, limiting to 3 sentences to keep it concise
        summary = wikipedia.summary(search_term, sentences=3)
        
        return SkillResult(True, f"📖 Wikipedia says:\n\n{summary}")
        
    except wikipedia.exceptions.DisambiguationError as e:
        options = e.options[:5] # Limit options to top 5
        return SkillResult(True, f"The search term is too ambiguous. Did you mean one of these?\n- " + "\n- ".join(options))
    except wikipedia.exceptions.PageError:
        return SkillResult(True, f"Could not find any Wikipedia page matching '{search_term}'.")
    except Exception as e:
        return SkillResult(True, f"An error occurred while accessing Wikipedia: {e}")
