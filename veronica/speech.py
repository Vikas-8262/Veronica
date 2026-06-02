"""Optional local speech output helper with Edge TTS voices."""

from __future__ import annotations

import asyncio
import datetime as dt
import importlib
import os
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

VOICE = "hi-IN-MadhurNeural"
RATE = "+10%"
VOLUME = "+0%"

HINDI_VOICES = (
    "hi-IN-MadhurNeural",
    "hi-IN-SwaraNeural",
    "en-IN-PrabhatNeural",
    "en-IN-NeerjaNeural",
)


def _optional_module(module_name: str) -> ModuleType | None:
    """Import an optional module, returning None when it is unavailable."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


async def _speak_edge_async(
    text: str,
    *,
    voice: str = VOICE,
    rate: str = RATE,
    volume: str = VOLUME,
    edge_tts_module: Any | None = None,
    pygame_module: Any | None = None,
) -> None:
    """Render and play speech through Microsoft Edge TTS and pygame."""
    edge_tts = edge_tts_module or _optional_module("edge_tts")
    pygame = pygame_module or _optional_module("pygame")
    if edge_tts is None or pygame is None:
        raise RuntimeError("Install requirements-voice.txt to enable Edge TTS speech output.")

    tmp_path: Path | None = None
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
            tmp_path = Path(audio_file.name)

        await communicate.save(str(tmp_path))

        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(str(tmp_path))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
        if hasattr(pygame.mixer.music, "unload"):
            pygame.mixer.music.unload()
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass


def _speak_pyttsx3(text: str) -> None:
    """Fallback speech output through pyttsx3 when Edge TTS is unavailable."""
    pyttsx3 = _optional_module("pyttsx3")
    if pyttsx3 is None:
        raise RuntimeError("Install requirements-voice.txt to enable local speech output.")

    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def _run_coro_sync(coro_factory: Callable[[], Any]) -> None:
    """Run an async speech coroutine from synchronous code."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro_factory())
        return

    error: BaseException | None = None

    def runner() -> None:
        nonlocal error
        try:
            asyncio.run(coro_factory())
        except BaseException as exc:  # pragma: no cover - re-raised below
            error = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if error is not None:
        raise error


def speak(text: str, *, voice: str = VOICE, rate: str = RATE, volume: str = VOLUME) -> None:
    """Read text aloud using Edge TTS, falling back to pyttsx3 if needed."""
    print(f"\n[VEER]: {text}")
    try:
        _run_coro_sync(lambda: _speak_edge_async(text, voice=voice, rate=rate, volume=volume))
    except Exception as edge_error:
        try:
            _speak_pyttsx3(text)
        except RuntimeError:
            raise edge_error


def greeting_text(
    *,
    user_name: str = "Vikas",
    assistant_name: str = "VEER",
    now: dt.datetime | None = None,
) -> str:
    """Return the VEER-style startup greeting text."""
    current = now or dt.datetime.now()
    hour = current.hour
    if 5 <= hour < 12:
        greeting = "Radhe Radhe"
    elif 12 <= hour < 17:
        greeting = "Jai Shree Krishna"
    elif 17 <= hour < 21:
        greeting = "Radhe Radhe"
    else:
        greeting = "Jai Shree Krishna"

    time_text = current.strftime("%I:%M %p")
    day_text = current.strftime("%A")
    return (
        f"{greeting} {user_name}! Aaj {day_text} hai, time hai {time_text}. "
        f"Main {assistant_name} hoon — aapki seva mein hazir hoon!"
    )


def greet(*, user_name: str = "Vikas", assistant_name: str = "VEER") -> None:
    """Speak a VEER-style startup greeting."""
    speak(greeting_text(user_name=user_name, assistant_name=assistant_name))
