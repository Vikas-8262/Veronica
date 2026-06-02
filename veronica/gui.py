"""Optional VEER-style GUI helpers for Veronica.

The GUI is intentionally optional. It uses tkinter from the standard library for
popup/input windows and pystray/Pillow only when installed for a system tray icon.
"""

from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import threading
from collections.abc import Callable
from typing import Any

BG = "#0a0a0a"
ACCENT = "#00f5c4"
TEXT = "#ffffff"
MUTED = "#666666"
PLACEHOLDER = "Boliye Veronica se..."


def show_greeting_popup(message: str | None = None, assistant_name: str = "Veronica") -> str:
    """Show a bottom-right JARVIS-style greeting popup."""
    tkinter = _optional_module("tkinter")
    if tkinter is None:
        return "GUI ke liye tkinter install/enable karo."

    try:
        root = tkinter.Tk()
    except Exception as exc:  # pragma: no cover - display availability is environment-specific
        return f"GUI popup nahi khul saka: {exc}"

    greeting, time_text, date_text = _greeting_parts()
    main_message = message or "System ready. Awaiting your command."

    root.title(assistant_name)
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.0)

    width, height = 400, 170
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.geometry(f"{width}x{height}+{screen_width - width - 20}+{screen_height - height - 60}")
    root.configure(bg=BG)

    border = tkinter.Frame(root, bg=ACCENT, padx=1, pady=1)
    border.pack(fill="both", expand=True)
    inner = tkinter.Frame(border, bg=BG, padx=18, pady=14)
    inner.pack(fill="both", expand=True)

    top = tkinter.Frame(inner, bg=BG)
    top.pack(fill="x")
    tkinter.Label(top, text=f"● {assistant_name}", font=("Courier New", 9, "bold"), fg=ACCENT, bg=BG).pack(side="left")
    tkinter.Label(top, text=time_text, font=("Courier New", 9), fg=MUTED, bg=BG).pack(side="right")

    tkinter.Label(
        inner,
        text=f"{greeting}!",
        font=("Courier New", 20, "bold"),
        fg=ACCENT,
        bg=BG,
    ).pack(anchor="w", pady=(8, 2))
    tkinter.Label(inner, text=date_text, font=("Courier New", 10), fg=MUTED, bg=BG).pack(anchor="w")
    tkinter.Label(inner, text=main_message, font=("Courier New", 9), fg=TEXT, bg=BG).pack(anchor="w", pady=(4, 0))

    alpha = [0.0]

    def fade_in() -> None:
        if alpha[0] < 1.0:
            alpha[0] = min(1.0, alpha[0] + 0.06)
            root.attributes("-alpha", alpha[0])
            root.after(25, fade_in)

    def fade_out() -> None:
        if alpha[0] > 0:
            alpha[0] = max(0.0, alpha[0] - 0.05)
            root.attributes("-alpha", alpha[0])
            root.after(25, fade_out)
        else:
            root.destroy()

    fade_in()
    root.bind("<Button-1>", lambda _event: root.destroy())
    root.after(7000, fade_out)
    root.mainloop()
    return "GUI popup closed."


def show_command_window(on_command: Callable[[str], None], assistant_name: str = "Veronica") -> str:
    """Show a compact command input window."""
    tkinter = _optional_module("tkinter")
    if tkinter is None:
        return "GUI ke liye tkinter install/enable karo."

    try:
        root = tkinter.Tk()
    except Exception as exc:  # pragma: no cover - display availability is environment-specific
        return f"Command window nahi khul saka: {exc}"

    root.title(f"{assistant_name} — Command")
    root.geometry(f"420x100+{root.winfo_screenwidth() // 2 - 210}+{root.winfo_screenheight() - 160}")
    root.attributes("-topmost", True)
    root.configure(bg=BG)
    root.overrideredirect(True)

    frame = tkinter.Frame(root, bg=ACCENT, padx=1, pady=1)
    frame.pack(fill="both", expand=True)
    inner = tkinter.Frame(frame, bg=BG, padx=10, pady=8)
    inner.pack(fill="both", expand=True)

    entry = tkinter.Entry(
        inner,
        bg=BG,
        fg=ACCENT,
        font=("Courier New", 13),
        insertbackground=ACCENT,
        relief="flat",
        width=38,
    )
    entry.pack(side="top", fill="x", expand=False, pady=(0, 8))
    entry.insert(0, PLACEHOLDER)
    entry.focus()
    
    def trigger(cmd: str) -> None:
        root.destroy()
        on_command(cmd)
        
    btn_frame = tkinter.Frame(inner, bg=BG)
    btn_frame.pack(side="top", fill="x", expand=True)
    
    btn_style = {"bg": "#1a1a1a", "fg": ACCENT, "relief": "flat", "font": ("Courier New", 9, "bold"), "activebackground": ACCENT, "activeforeground": BG, "cursor": "hand2"}
    
    b1 = tkinter.Button(btn_frame, text="Analysis Flow", command=lambda: trigger("run analysis flow"), **btn_style)
    b1.pack(side="left", padx=3, fill="x", expand=True)
    
    b2 = tkinter.Button(btn_frame, text="Voice On", command=lambda: trigger("start voice"), **btn_style)
    b2.pack(side="left", padx=3, fill="x", expand=True)
    
    b3 = tkinter.Button(btn_frame, text="Sandbox", command=lambda: trigger('run in sandbox: print("Secure Sandbox Active!")'), **btn_style)
    b3.pack(side="left", padx=3, fill="x", expand=True)

    def clear_placeholder(_event: object | None = None) -> None:
        if entry.get() == PLACEHOLDER:
            entry.delete(0, "end")

    def submit(_event: object | None = None) -> None:
        command = entry.get().strip()
        root.destroy()
        if command and command != PLACEHOLDER:
            on_command(command)

    entry.bind("<FocusIn>", clear_placeholder)
    entry.bind("<Return>", submit)
    entry.bind("<Escape>", lambda _event: root.destroy())
    root.mainloop()
    return "Command window closed."


def run_tray_icon(
    on_command: Callable[[str], None],
    on_quit: Callable[[], None],
    assistant_name: str = "Veronica",
) -> str:
    """Run a pystray system-tray icon with command and quit menu items."""
    pystray = _optional_module("pystray")
    image_module = _optional_module("PIL.Image")
    draw_module = _optional_module("PIL.ImageDraw")
    if pystray is None or image_module is None or draw_module is None:
        return "GUI tray ke liye pystray aur pillow install karo: pip install -r requirements-gui.txt"

    image = image_module.new("RGB", (64, 64), color=BG)
    draw = draw_module.Draw(image)
    draw.ellipse([8, 8, 56, 56], fill=ACCENT)
    draw.text((18, 18), assistant_name[:1].upper(), fill="#000000")

    def open_command(_icon: object, _item: object) -> None:
        show_command_window(on_command, assistant_name=assistant_name)

    def quit_assistant(icon: object, _item: object) -> None:
        icon.stop()
        on_quit()

    menu = pystray.Menu(
        pystray.MenuItem(f"{assistant_name} Command", open_command),
        pystray.MenuItem(f"Quit {assistant_name}", quit_assistant),
    )
    icon = pystray.Icon(assistant_name, image, f"{assistant_name} Assistant", menu)
    icon.run()
    return "Tray icon stopped."


def launch_gui(
    on_command: Callable[[str], None],
    on_quit: Callable[[], None],
    assistant_name: str = "Veronica",
    greeting_message: str | None = None,
) -> list[threading.Thread]:
    """Launch greeting popup and tray icon in daemon threads."""
    popup_thread = threading.Thread(
        target=show_greeting_popup,
        kwargs={"message": greeting_message, "assistant_name": assistant_name},
        daemon=True,
    )
    tray_thread = threading.Thread(
        target=run_tray_icon,
        args=(on_command, on_quit, assistant_name),
        daemon=True,
    )
    popup_thread.start()
    tray_thread.start()
    return [popup_thread, tray_thread]


def _greeting_parts(now: dt.datetime | None = None) -> tuple[str, str, str]:
    current = now or dt.datetime.now()
    if 5 <= current.hour < 12:
        greeting = "Good Morning"
    elif 12 <= current.hour < 17:
        greeting = "Good Afternoon"
    elif 17 <= current.hour < 21:
        greeting = "Good Evening"
    else:
        greeting = "Good Night"
    return greeting, current.strftime("%I:%M %p"), current.strftime("%A, %d %B")


def _optional_module(module_name: str) -> Any | None:
    top_level = module_name.split(".", 1)[0]
    if importlib.util.find_spec(top_level) is None:
        return None
    if importlib.util.find_spec(module_name) is None:
        return None
    return importlib.import_module(module_name)
