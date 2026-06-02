"""Command-line entry point for Veronica."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections.abc import Callable
from pathlib import Path

from .assistant import Assistant, AssistantConfig
from .gui import launch_gui
from .mobile import run_mobile_server
from .security import SecurityShield
from .speech import speak
from .startup import DEFAULT_STARTUP_ARGS, StartupShortcutConfig, install_windows_startup_shortcut

VEER_BANNER = """\
╔══════════════════════════════════════════════════╗
║       Veronica v3.0 — Full Local Assistant       ║
║       VEER-inspired, private, and extensible     ║
║                                                  ║
║  NEW in v3:                                      ║
║  ✓ Battery + System Stats                        ║
║  ✓ Auto-type / Dictation mode                    ║
║  ✓ News Headlines                                ║
║  ✓ Screen OCR (text padhna)                      ║
║  ✓ Jokes, Quotes, Quiz game                      ║
║  ✓ Focus Mode (Pomodoro)                         ║
║  ✓ Productivity Tracker                          ║
║  ✓ Smart Greeting                                ║
║                                                  ║
║  Optional integrations:                          ║
║  ✓ Voice + Text commands                         ║
║  ✓ Fully local AI backend                        ║
║  ✓ Security camera + face alert                  ║
║  ✓ Mobile control (Flask)                        ║
║  ✓ Reminders + Alarms                            ║
║  ✓ System Tray + Popup GUI                       ║
╚══════════════════════════════════════════════════╝"""

READY_HINTS = (
    "Voice ya text dono se boliye when --speak is enabled",
    "Try: 'joke sunao', 'news sunao', 'battery batao'",
    "Try: 'focus mode on', 'screen padho', 'quiz khelo'",
    "Use 'bye' ya 'alvida' to stop",
)
SHUTDOWN_RESPONSE = "Powering down. Goodbye."


def _configure_stdout() -> None:
    """Prefer UTF-8 console output for Hindi/Hinglish status text."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Veronica local JARVIS/VEER-inspired assistant.",
        epilog=(
            "VEER compatibility: use --full for GUI + reminders + voice + security, "
            "then disable pieces with --no-voice, --no-gui, or --no-security."
        ),
    )
    parser.add_argument("--name", default="Veronica", help="Assistant wake/name label.")
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".veronica", help="Directory for notes, reminders, and logs.")
    parser.add_argument("--full", action="store_true", help="VEER-style full mode: voice, GUI, reminders, and security where available.")
    parser.add_argument("--speak", action="store_true", help="Read assistant responses aloud with local text-to-speech.")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice output even in --full mode.")
    parser.add_argument("--reminders", action="store_true", help="Start the local reminder scheduler thread.")
    parser.add_argument("--gui", action="store_true", help="Launch optional popup and tray GUI helpers.")
    parser.add_argument("--no-gui", action="store_true", help="Disable GUI helpers in --full mode.")
    parser.add_argument("--mobile", action="store_true", help="Run the optional same-WiFi mobile web server.")
    parser.add_argument("--mobile-host", default="0.0.0.0", help="Host for --mobile server.")
    parser.add_argument("--mobile-port", type=int, default=5000, help="Port for --mobile server.")
    parser.add_argument("--mobile-speak", action="store_true", help="Speak responses triggered from the mobile web UI.")
    parser.add_argument("--register-face", "--register", action="store_true", help="Register owner face samples for the optional security shield.")
    parser.add_argument("--security", action="store_true", help="Start the optional webcam security shield.")
    parser.add_argument("--no-security", action="store_true", help="Disable security startup in --full mode.")
    parser.add_argument("--add-startup", action="store_true", help="Add Veronica to the current user's Windows Startup folder.")
    parser.add_argument("--startup-name", default="Veronica", help="Shortcut name to use with --add-startup.")
    parser.add_argument(
        "--startup-args",
        nargs=argparse.REMAINDER,
        default=None,
        help="Arguments the Startup shortcut should pass to python -m veronica; keep this option last. Defaults to --gui --reminders.",
    )
    return parser.parse_args()


def log_event(data_dir: Path, text: str) -> None:
    """Append a timestamped CLI event to the local Veronica log."""
    try:
        logs_dir = data_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with (logs_dir / "veronica_log.txt").open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {text}\n")
    except OSError:
        pass


def process_command(
    assistant: Assistant,
    command: str,
    *,
    speaker: Callable[[str], None] | None = None,
    data_dir: Path | None = None,
) -> tuple[str, bool]:
    """Process one command, log it, optionally speak it, and return (response, should_continue)."""
    cleaned = command.strip()
    if not cleaned:
        return "", True

    log_dir = data_dir or assistant.config.data_dir
    log_event(log_dir, f"CMD: {cleaned}")
    response = assistant.respond(cleaned)
    log_event(log_dir, f"RESP: {response}")
    if speaker is not None and response:
        speaker(response)
    return response, response != SHUTDOWN_RESPONSE


def _print_ready_banner() -> None:
    print("\n[Veronica v3]: Ready! Commands:")
    for hint in READY_HINTS:
        print(f"  {hint}")
    print()


def _run_text_loop(assistant: Assistant, args: argparse.Namespace, speaker: Callable[[str], None] | None) -> None:
    running = True
    while running:
        try:
            user_message = input(f"\n{args.name} > ")
        except (EOFError, KeyboardInterrupt):
            print("\nPowering down. Goodbye.")
            break

        response, running = process_command(assistant, user_message, speaker=speaker, data_dir=args.data_dir)
        if response:
            print(f"{args.name}: {response}")


def _install_startup(args: argparse.Namespace) -> None:
    startup_args = tuple(args.startup_args) if args.startup_args is not None else DEFAULT_STARTUP_ARGS
    print(
        install_windows_startup_shortcut(
            StartupShortcutConfig(
                shortcut_name=args.startup_name,
                working_directory=Path.cwd(),
                arguments=startup_args,
            )
        )
    )


def main() -> None:
    _configure_stdout()
    args = parse_args()

    if args.add_startup:
        _install_startup(args)
        return

    use_voice = (args.speak or args.full or args.mobile_speak) and not args.no_voice
    use_gui = (args.gui or args.full) and not args.no_gui
    use_security = (args.security or args.full) and not args.no_security
    use_reminders = args.reminders or args.full
    speaker = speak if use_voice else None

    print(VEER_BANNER)
    log_event(args.data_dir, "Veronica v3.0 started")

    if args.register_face:
        result = SecurityShield(args.data_dir, owner_name=args.name).register_face()
        print(result)
        log_event(args.data_dir, f"REGISTER_FACE: {result}")
        return

    assistant = Assistant(
        AssistantConfig(
            name=args.name,
            data_dir=args.data_dir,
            start_reminder_thread=use_reminders,
            reminder_speaker=speaker,
            focus_speaker=speaker,
        )
    )

    greeting = assistant.greeting()
    print(greeting)
    if speaker is not None:
        speaker(greeting)

    if use_reminders:
        print("[✓] Reminder system ready")

    if use_security:
        shield = SecurityShield(args.data_dir, owner_name=args.name)
        security_result = shield.start_security(
            on_alert=lambda path: speaker("Khabardar! Anjaan chehra detect hua!") if speaker else None
        )
        status_prefix = "[✓]" if "start" in security_result.lower() else "[!]"
        print(f"{status_prefix} Security: {security_result}")
        log_event(args.data_dir, f"SECURITY: {security_result}")

    if use_gui:
        def handle_gui_command(command: str) -> None:
            response, _running = process_command(assistant, command, speaker=speaker, data_dir=args.data_dir)
            print(f"{args.name}: {response}")

        launch_gui(handle_gui_command, lambda: None, assistant_name=args.name, greeting_message=greeting)
        print("[✓] GUI + System tray ready")

    if args.mobile:
        run_mobile_server(
            assistant,
            host=args.mobile_host,
            port=args.mobile_port,
            speak_responses=args.mobile_speak and speaker is not None,
            speaker=speaker,
        )
        return

    _print_ready_banner()
    _run_text_loop(assistant, args, speaker)
    print("\n[Veronica]: Shutdown complete. Radhe Radhe!")
    log_event(args.data_dir, "Veronica stopped")


if __name__ == "__main__":
    main()
