"""QR Code Generator agent for Veronica."""

import importlib
import os
import subprocess
import datetime
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_qrcode_request(message: str) -> bool:
    """Matcher for QR Code requests."""
    lowered = message.lower().strip()
    return any(phrase in lowered for phrase in ("qr code", "qr for", "generate qr", "create qr", "make qr"))

def handle_qrcode_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to generate and save a QR code image."""
    qrcode = _optional_module("qrcode")
    if qrcode is None:
        return SkillResult(True, "QR Code Agent requires 'qrcode[pil]'. Run: pip install qrcode[pil]")

    lowered = message.lower().strip()

    # Extract content to encode
    content = ""
    triggers = ["generate a qr code for", "generate qr code for", "create a qr code for",
                "create qr code for", "make a qr code for", "make qr code for",
                "qr code for", "generate qr for", "create qr for", "make qr for"]

    for trigger in triggers:
        if trigger in lowered:
            idx = lowered.find(trigger)
            orig_idx = idx + len(trigger)
            content = message[orig_idx:].strip().strip("?.!")
            break

    if not content:
        return SkillResult(True, "Please specify what to encode (e.g., 'Generate a QR code for https://google.com').")

    try:
        print(f"📱 [Generating QR code for: {content[:60]}...]")

        # Generate QR code with high error correction
        qr = qrcode.QRCode(
            version=None,  # Auto-size
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=12,
            border=4,
        )
        qr.add_data(content)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Save to Desktop with timestamped filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        filename = f"veronica_qr_{timestamp}.png"
        filepath = os.path.join(desktop, filename)

        img.save(filepath)

        # Auto-open the image
        try:
            os.startfile(filepath)
        except Exception:
            subprocess.Popen(["start", filepath], shell=True)

        return SkillResult(True, (
            f"✅ QR Code generated and saved!\n\n"
            f"  📁 File: {filepath}\n"
            f"  🔗 Content encoded: \"{content[:80]}{'...' if len(content) > 80 else ''}\"\n\n"
            f"The image has been opened automatically!"
        ))

    except Exception as e:
        return SkillResult(True, f"Failed to generate QR code: {e}")
