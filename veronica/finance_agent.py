"""Real-Time Financial Markets Tracking agent for Veronica."""

import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_finance_request(message: str) -> bool:
    """Matcher for Finance requests."""
    lowered = message.lower().strip()
    return any(phrase in lowered for phrase in ("stock price", "crypto price", "price of", "check stock"))

def handle_finance_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to fetch live ticker data via yfinance."""
    yf = _optional_module("yfinance")
    if yf is None:
        return SkillResult(True, "Finance Agent requires 'yfinance'. Run: pip install yfinance")

    lowered = message.lower().strip()
    
    # Extract ticker symbol (e.g., "what is the price of AAPL" -> "AAPL")
    symbol = ""
    if "price of" in lowered:
        symbol = lowered.split("price of")[-1].strip()
    elif "check stock" in lowered:
        symbol = lowered.split("check stock")[-1].strip()
    elif "stock price" in lowered:
        # e.g. "aapl stock price"
        symbol = lowered.replace("stock price", "").strip()
        if "for" in symbol:
            symbol = symbol.split("for")[-1].strip()
    elif "crypto price" in lowered:
        symbol = lowered.replace("crypto price", "").strip()
        if "for" in symbol:
            symbol = symbol.split("for")[-1].strip()
            
    # Clean up common punctuation and words
    symbol = symbol.replace("what is", "").replace("the", "").strip("?.! ").upper()
    
    # Common mappings
    if symbol == "BITCOIN" or symbol == "BTC":
        symbol = "BTC-USD"
    elif symbol == "ETHEREUM" or symbol == "ETH":
        symbol = "ETH-USD"
        
    if not symbol:
        return SkillResult(True, "Please specify a valid ticker symbol (e.g., 'What is the price of AAPL?').")
        
    try:
        print(f"📊 [Fetching live market data for {symbol} from Yahoo Finance...]")
        ticker = yf.Ticker(symbol)
        
        # fast_info is much quicker than full info
        fast_info = ticker.fast_info
        
        if not hasattr(fast_info, "last_price") or fast_info.last_price is None:
            return SkillResult(True, f"Could not find live trading data for symbol: {symbol}")
            
        current_price = fast_info.last_price
        prev_close = fast_info.previous_close
        
        change = current_price - prev_close
        percent_change = (change / prev_close) * 100
        
        trend = "📈" if change >= 0 else "📉"
        
        output = (
            f"💰 {symbol} Live Market Data:\n\n"
            f"- Current Price: ${current_price:,.2f}\n"
            f"- Today's Change: ${change:,.2f} ({percent_change:+.2f}%) {trend}\n"
        )
        
        return SkillResult(True, output)
        
    except Exception as e:
        return SkillResult(True, f"Failed to fetch financial data for {symbol}. Make sure it is a valid Yahoo Finance ticker: {e}")
