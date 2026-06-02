"""Automated Test Suite for Mega-Veronica Integrations."""

from veronica.assistant import Assistant, AssistantConfig
import time

def run_tests():
    print("=" * 60)
    print("INITIALIZING MEGA-VERONICA TEST SUITE")
    print("=" * 60 + "\\n")
    
    # Initialize the core without background threads for safe testing
    assistant = Assistant(AssistantConfig(name="MegaVeronica", start_reminder_thread=False))
    
    commands = [
        # Basic functionality check
        "time batao",
        
        # OpenClaw Voice Node Bridge
        "voice status",
        
        # Interactive Canvas rendering
        "show canvas",
        
        # Secure Sandboxing (Docker)
        "run in sandbox: print('Secure Sandbox successfully executed!')",
        
        # CrewAI Integration (Structured extraction)
        # Note: If GEMINI_API_KEY is not set, this will return a graceful error.
        "extract data from: Vikas bought 3 laptops for 1500 USD yesterday."
    ]
    
    for cmd in commands:
        print(f"[{time.strftime('%H:%M:%S')}] USER: {cmd}")
        
        try:
            response = assistant.respond(cmd)
            print(f"[{time.strftime('%H:%M:%S')}] VERONICA:\\n{response}\\n")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ERROR:\\n{e}\\n")
            
        print("-" * 60)
        
    print("\\nTest Suite Completed!")

if __name__ == "__main__":
    run_tests()
