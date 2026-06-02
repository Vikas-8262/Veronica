"""Internet Speed Test agent for Veronica."""

import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_speedtest_request(message: str) -> bool:
    """Matcher for Speedtest requests."""
    lowered = message.lower().strip()
    return "speed test" in lowered or "internet speed" in lowered or "fast is my internet" in lowered

def handle_speedtest_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to run an internet speed diagnostic."""
    speedtest = _optional_module("speedtest")
    if speedtest is None:
        return SkillResult(True, "Speedtest Agent requires 'speedtest-cli'. Run: pip install speedtest-cli")

    try:
        print("⚡ [Initializing Speedtest.net client... this may take 10-15 seconds]")
        st = speedtest.Speedtest()
        
        print("🌍 [Finding the optimal server...]")
        st.get_best_server()
        
        print("⬇️  [Testing Download Speed...]")
        download_speed = st.download()
        
        print("⬆️  [Testing Upload Speed...]")
        upload_speed = st.upload()
        
        print("🏓 [Fetching Ping...]")
        ping = st.results.ping
        
        # Convert bits per second to Megabits per second
        mbps_down = download_speed / 1_000_000
        mbps_up = upload_speed / 1_000_000
        
        output = (
            f"⚡ Network Diagnostics Complete:\n\n"
            f"- Download: {mbps_down:.2f} Mbps ⬇️\n"
            f"- Upload: {mbps_up:.2f} Mbps ⬆️\n"
            f"- Ping: {ping} ms 🏓"
        )
        
        return SkillResult(True, output)
        
    except Exception as e:
        return SkillResult(True, f"Failed to execute speed test. Ensure you have an active connection: {e}")
