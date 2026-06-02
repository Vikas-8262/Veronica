"""Live News Integration agent for Veronica."""

import xml.etree.ElementTree as ET
import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_news_request(message: str) -> bool:
    """Matcher for News requests."""
    lowered = message.lower().strip()
    return "news" in lowered or "headlines" in lowered

def handle_news_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to fetch and parse the latest news RSS feed."""
    requests = _optional_module("requests")
    if requests is None:
        return SkillResult(True, "News Agent requires 'requests'. Run: pip install requests")

    try:
        # BBC World News RSS Feed
        url = "http://feeds.bbci.co.uk/news/world/rss.xml"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return SkillResult(True, f"Failed to fetch news. Status Code: {response.status_code}")
            
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Extract the top 5 items from the channel
        items = root.findall('./channel/item')[:5]
        
        if not items:
            return SkillResult(True, "No news headlines found in the feed.")
            
        output = "📰 Top Global Headlines:\n\n"
        for i, item in enumerate(items, 1):
            title = item.find('title')
            desc = item.find('description')
            
            t_text = title.text if title is not None else "No Title"
            d_text = desc.text if desc is not None else "No Description"
            
            output += f"{i}. {t_text}\n   - {d_text}\n\n"
            
        return SkillResult(True, output.strip())
        
    except requests.RequestException as e:
        return SkillResult(True, f"Network error while fetching news: {e}")
    except ET.ParseError as e:
        return SkillResult(True, f"Error parsing the news feed XML: {e}")
    except Exception as e:
        return SkillResult(True, f"An unexpected error occurred: {e}")
