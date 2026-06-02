"""Interactive Canvas skills for Veronica."""

from .skills import AssistantContext, SkillResult

def is_canvas_request(message: str) -> bool:
    """Matcher for Canvas requests."""
    lowered = message.lower().strip()
    return lowered.startswith(("show canvas", "render widget", "interactive canvas"))

def handle_canvas_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to return rich HTML widgets for the mobile UI."""
    # A simple, elegant HTML widget demonstrating the "Canvas" capability
    html_payload = """
    <div style="background: linear-gradient(135deg, #1e293b, #0f172a); padding: 20px; border-radius: 12px; border: 1px solid #334155; font-family: sans-serif; color: #f8fafc; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
        <h3 style="margin: 0 0 10px 0; color: #38bdf8;">Live Canvas Widget</h3>
        <p style="margin: 0 0 15px 0; font-size: 14px; color: #94a3b8;">This is a rich HTML element rendered dynamically by Veronica.</p>
        <div style="display: flex; justify-content: space-around; gap: 10px;">
            <div style="background: #334155; padding: 15px; border-radius: 8px; flex: 1;">
                <div style="font-size: 24px; font-weight: bold; color: #10b981;">85%</div>
                <div style="font-size: 12px; text-transform: uppercase; color: #cbd5e1;">Efficiency</div>
            </div>
            <div style="background: #334155; padding: 15px; border-radius: 8px; flex: 1;">
                <div style="font-size: 24px; font-weight: bold; color: #f59e0b;">2.4s</div>
                <div style="font-size: 12px; text-transform: uppercase; color: #cbd5e1;">Latency</div>
            </div>
        </div>
        <button style="margin-top: 15px; background: #38bdf8; color: #0f172a; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer;" onclick="alert('Canvas is fully interactive!')">Click Me!</button>
    </div>
    """
    
    return SkillResult(True, html_payload)
