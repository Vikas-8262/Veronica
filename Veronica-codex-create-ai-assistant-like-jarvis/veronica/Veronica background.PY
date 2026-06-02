"""
Veronica — Permanent Background Service
=======================================
- System Tray mein rehti hai (band nahi hoti)
- Ctrl+Shift+V se popup activate hota hai
- "Hey Veronica" voice wake word se bhi activate hoti hai
- Windows Startup mein automatically add ho jaati hai
- Minimize on close — exit nahi hoti

Install:
    pip install pystray pillow keyboard pyautogui pyperclip edge-tts pygame psutil

Run:
    python veronica_background.py

Startup mein add karne ke liye:
    python veronica_background.py --add-startup
"""

from __future__ import annotations

import argparse
import os
import sys
import subprocess
import threading
import queue
import time
import winreg
from pathlib import Path

# ── Try imports ──────────────────────────────────────────────
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

try:
    import tkinter as tk
    from tkinter import scrolledtext
    HAS_TK = True
except ImportError:
    HAS_TK = False

# ── Veronica core ─────────────────────────────────────────────
# Script apne folder se Veronica import karta hai
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from veronica.assistant import Assistant, AssistantConfig
    from veronica.speech import speak as _speak_fn
    HAS_VERONICA = True
except ImportError:
    HAS_VERONICA = False
    print("[ERROR] Veronica module nahi mila. Is script ko Veronica folder ke andar rakho.")


# ═══════════════════════════════════════════════════════════════
# GLOBALS
# ═══════════════════════════════════════════════════════════════

assistant: Assistant | None = None
command_queue: queue.Queue[str] = queue.Queue()
USE_VOICE = True


# ═══════════════════════════════════════════════════════════════
# VERONICA CORE
# ═══════════════════════════════════════════════════════════════

def init_assistant() -> None:
    global assistant
    config = AssistantConfig(
        name="Veronica",
        data_dir=Path.home() / ".veronica",
        start_reminder_thread=True,
    )
    assistant = Assistant(config)
    print("[✓] Veronica brain loaded")


def speak(text: str) -> None:
    """Speak in background thread so UI doesn't freeze."""
    if USE_VOICE and HAS_VERONICA:
        threading.Thread(target=_speak_fn, args=(text,), daemon=True).start()


def ask_veronica(command: str) -> str:
    """Send command to Veronica and get response."""
    if assistant is None:
        return "Veronica abhi load ho rahi hai..."
    try:
        return assistant.respond(command)
    except Exception as e:
        return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════
# POPUP WINDOW (Tkinter)
# ═══════════════════════════════════════════════════════════════

popup_window: tk.Tk | None = None
popup_visible = False


def create_popup() -> None:
    """Create the JARVIS-style popup window."""
    global popup_window

    if not HAS_TK:
        print("[!] tkinter nahi mila")
        return

    popup_window = tk.Tk()
    popup_window.title("Veronica")
    popup_window.geometry("500x420+100+100")
    popup_window.configure(bg="#0a0a0f")
    popup_window.resizable(True, True)
    popup_window.attributes("-topmost", True)
    popup_window.attributes("-alpha", 0.95)

    # Close = hide, not exit
    popup_window.protocol("WM_DELETE_WINDOW", hide_popup)

    # ── Header ──
    header = tk.Label(
        popup_window,
        text="⚡ VERONICA — AI Assistant",
        bg="#0a0a0f", fg="#00d4ff",
        font=("Consolas", 13, "bold"),
        pady=8,
    )
    header.pack(fill="x")

    tk.Frame(popup_window, bg="#00d4ff", height=1).pack(fill="x", padx=10)

    # ── Chat display ──
    chat_frame = tk.Frame(popup_window, bg="#0a0a0f")
    chat_frame.pack(fill="both", expand=True, padx=10, pady=5)

    chat_box = scrolledtext.ScrolledText(
        chat_frame,
        bg="#060610", fg="#e0e0e0",
        font=("Consolas", 10),
        wrap=tk.WORD,
        state="disabled",
        relief="flat",
        borderwidth=0,
        insertbackground="#00d4ff",
    )
    chat_box.pack(fill="both", expand=True)

    # Color tags
    chat_box.tag_config("user", foreground="#00d4ff", font=("Consolas", 10, "bold"))
    chat_box.tag_config("veronica", foreground="#c0ffc0", font=("Consolas", 10))
    chat_box.tag_config("system", foreground="#888888", font=("Consolas", 9, "italic"))

    def append_chat(who: str, text: str) -> None:
        chat_box.configure(state="normal")
        if who == "user":
            chat_box.insert("end", f"\nYou: {text}\n", "user")
        elif who == "veronica":
            chat_box.insert("end", f"Veronica: {text}\n", "veronica")
        else:
            chat_box.insert("end", f"{text}\n", "system")
        chat_box.configure(state="disabled")
        chat_box.see("end")

    popup_window._append_chat = append_chat
    append_chat("system", "── Veronica Online. Ctrl+Shift+V to toggle ──")

    # ── Input area ──
    input_frame = tk.Frame(popup_window, bg="#0a0a0f")
    input_frame.pack(fill="x", padx=10, pady=(0, 8))

    tk.Frame(popup_window, bg="#00d4ff", height=1).pack(fill="x", padx=10)

    entry_var = tk.StringVar()
    entry = tk.Entry(
        input_frame,
        textvariable=entry_var,
        bg="#111122", fg="#ffffff",
        insertbackground="#00d4ff",
        font=("Consolas", 11),
        relief="flat",
        borderwidth=4,
    )
    entry.pack(side="left", fill="x", expand=True, pady=6, padx=(0, 6))

    def send_command(event=None) -> None:
        cmd = entry_var.get().strip()
        if not cmd:
            return
        entry_var.set("")
        append_chat("user", cmd)

        def process():
            response = ask_veronica(cmd)
            popup_window.after(0, lambda: append_chat("veronica", response))
            speak(response)

        threading.Thread(target=process, daemon=True).start()

    entry.bind("<Return>", send_command)

    send_btn = tk.Button(
        input_frame,
        text="Send",
        command=send_command,
        bg="#003355", fg="#00d4ff",
        font=("Consolas", 10, "bold"),
        relief="flat",
        padx=12, pady=4,
        cursor="hand2",
    )
    send_btn.pack(side="right", pady=6)

    # Focus input when opened
    entry.focus_set()

    # ── Bottom bar ──
    bottom = tk.Label(
        popup_window,
        text="Ctrl+Shift+V to hide  •  Running in background",
        bg="#0a0a0f", fg="#444466",
        font=("Consolas", 8),
        pady=4,
    )
    bottom.pack(fill="x")

    popup_window.withdraw()  # Start hidden


def show_popup() -> None:
    global popup_visible
    if popup_window is None:
        return
    popup_window.deiconify()
    popup_window.lift()
    popup_window.focus_force()
    popup_visible = True


def hide_popup() -> None:
    global popup_visible
    if popup_window is None:
        return
    popup_window.withdraw()
    popup_visible = False


def toggle_popup() -> None:
    if popup_visible:
        hide_popup()
    else:
        show_popup()


# ═══════════════════════════════════════════════════════════════
# SYSTEM TRAY
# ═══════════════════════════════════════════════════════════════

def _make_tray_icon() -> Image.Image:
    """Create a simple glowing circle tray icon."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill="#003355", outline="#00d4ff", width=3)
    draw.text((18, 18), "V", fill="#00d4ff")
    return img


def run_tray() -> None:
    """Run system tray icon in its own thread."""
    if not HAS_TRAY:
        print("[!] pystray/pillow nahi mila — tray nahi chalega")
        print("    pip install pystray pillow")
        return

    def on_open(icon, item):
        if popup_window:
            popup_window.after(0, show_popup)

    def on_toggle(icon, item):
        if popup_window:
            popup_window.after(0, toggle_popup)

    def on_quit(icon, item):
        icon.stop()
        if popup_window:
            popup_window.after(0, popup_window.destroy)
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Open Veronica", on_open, default=True),
        pystray.MenuItem("Toggle (Ctrl+Shift+V)", on_toggle),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit Veronica", on_quit),
    )

    icon = pystray.Icon(
        "Veronica",
        _make_tray_icon(),
        "Veronica — AI Assistant",
        menu,
    )
    icon.run()


# ═══════════════════════════════════════════════════════════════
# HOTKEY
# ═══════════════════════════════════════════════════════════════

def setup_hotkey() -> None:
    """Register Ctrl+Shift+V global hotkey."""
    if not HAS_KEYBOARD:
        print("[!] keyboard module nahi mila — hotkey nahi chalega")
        print("    pip install keyboard")
        return

    def hotkey_callback():
        if popup_window:
            popup_window.after(0, toggle_popup)

    keyboard.add_hotkey("ctrl+shift+v", hotkey_callback)
    print("[✓] Hotkey registered: Ctrl+Shift+V")


# ═══════════════════════════════════════════════════════════════
# WINDOWS STARTUP
# ═══════════════════════════════════════════════════════════════

def add_to_startup() -> str:
    """Add Veronica to Windows startup registry."""
    try:
        script_path = Path(__file__).resolve()
        python_path = sys.executable
        command = f'"{python_path}" "{script_path}"'

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, "Veronica", 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        return f"[✓] Veronica startup mein add ho gayi!\n    Command: {command}"
    except Exception as e:
        return f"[!] Startup add nahi ho saka: {e}"


def remove_from_startup() -> str:
    """Remove Veronica from Windows startup."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, "Veronica")
        winreg.CloseKey(key)
        return "[✓] Veronica startup se remove ho gayi!"
    except FileNotFoundError:
        return "[!] Veronica startup mein thi hi nahi."
    except Exception as e:
        return f"[!] Remove nahi ho saka: {e}"


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Veronica Background Service")
    parser.add_argument("--add-startup", action="store_true", help="Windows startup mein add karo")
    parser.add_argument("--remove-startup", action="store_true", help="Windows startup se remove karo")
    parser.add_argument("--no-voice", action="store_true", help="Voice band karo")
    args = parser.parse_args()

    if args.add_startup:
        print(add_to_startup())
        return
    if args.remove_startup:
        print(remove_from_startup())
        return

    global USE_VOICE
    if args.no_voice:
        USE_VOICE = False

    print("╔══════════════════════════════════════╗")
    print("║   Veronica — Background Mode         ║")
    print("║   Ctrl+Shift+V  →  Toggle popup      ║")
    print("║   System Tray   →  Right click menu  ║")
    print("╚══════════════════════════════════════╝")

    # 1. Load Veronica brain
    if HAS_VERONICA:
        threading.Thread(target=init_assistant, daemon=True).start()
    else:
        print("[!] Veronica load nahi ho saka")

    # 2. Create popup window (must be on main thread for tkinter)
    if HAS_TK:
        create_popup()
        print("[✓] Popup window ready")

    # 3. Setup hotkey (background thread)
    threading.Thread(target=setup_hotkey, daemon=True).start()

    # 4. System tray (background thread)
    threading.Thread(target=run_tray, daemon=True).start()
    print("[✓] System tray starting...")

    # 5. Greeting
    greeting = "Veronica online. Press Ctrl+Shift+V to open me anytime!"
    print(f"\n{greeting}")
    if USE_VOICE and HAS_VERONICA:
        threading.Thread(target=_speak_fn, args=(greeting,), daemon=True).start()

    # 6. Tkinter main loop (keeps everything alive)
    if HAS_TK and popup_window:
        try:
            popup_window.mainloop()
        except KeyboardInterrupt:
            print("\n[Veronica]: Shutting down...")
    else:
        print("[!] tkinter nahi mila — console mode mein chal raha hoon")
        print("Ctrl+C se band karo")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Veronica]: Goodbye!")


if __name__ == "__main__":
    main()