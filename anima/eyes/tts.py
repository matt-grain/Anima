# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Text-to-Speech module using Piper TTS.

Provides offline, fast TTS synthesis on CPU.
"""

import io
import wave
import threading
from pathlib import Path
from loguru import logger

# Lazy imports to avoid slow startup
_voice = None
_current_voice_name = None
_default_voice_name = "en_US-danny-low"
_pygame_mixer_initialized = False
_volume = 1.0

# Some popular Piper voices to try
AVAILABLE_VOICES = {
    # English US
    "danny": "en_US-danny-low",  # Male, calm (default)
    "amy": "en_US-amy-medium",  # Female
    "lessac": "en_US-lessac-medium",  # Female, clear
    "ryan": "en_US-ryan-medium",  # Male
    "kusal": "en_US-kusal-medium",  # Male
    # English UK
    "alan": "en_GB-alan-low",  # British male
    "alba": "en_GB-alba-medium",  # Scottish female
    "aru": "en_GB-aru-medium",  # British male
    "jenny": "en_GB-jenny_dioco-medium",  # British female
    # Other languages
    "thorsten": "de_DE-thorsten-medium",  # German male
    "upmc": "fr_FR-upmc-medium",  # French
}


def _parse_voice_name(voice: str) -> tuple[str, str, str, str]:
    """Parse voice name like 'en_US-danny-low' into components."""
    # Format: lang_REGION-name-quality
    parts = voice.split("-")
    if len(parts) >= 3:
        lang_region = parts[0]  # en_US
        name = parts[1]  # danny
        quality = parts[2]  # low
        lang = lang_region.split("_")[0]  # en
        return lang, lang_region, name, quality
    # Fallback
    return "en", "en_US", "danny", "low"


def set_default_voice(voice_name: str) -> str:
    """Set the default voice for TTS.

    Args:
        voice_name: Short name (e.g., 'amy') or full name (e.g., 'en_US-amy-medium')

    Returns:
        The full voice name that was set
    """
    global _default_voice_name, _voice, _current_voice_name

    # Check if it's a short name
    if voice_name in AVAILABLE_VOICES:
        _default_voice_name = AVAILABLE_VOICES[voice_name]
    else:
        _default_voice_name = voice_name

    # Invalidate cached voice so next speak() loads the new one
    _voice = None
    _current_voice_name = None

    logger.info(f"Default voice set to: {_default_voice_name}")
    return _default_voice_name


def get_default_voice() -> str:
    """Get the current default voice name."""
    return _default_voice_name


def list_available_voices() -> dict[str, str]:
    """Get dictionary of available voice shortcuts."""
    return AVAILABLE_VOICES.copy()


def _get_voice(voice_name: str | None = None):
    """Lazy-load the Piper voice model."""
    global _voice, _current_voice_name

    if voice_name is None:
        voice_name = _default_voice_name

    # Reload if voice changed
    if _voice is not None and _current_voice_name == voice_name:
        return _voice

    try:
        from piper.voice import PiperVoice  # type: ignore[import-not-found]

        lang, lang_region, name, quality = _parse_voice_name(voice_name)

        # Use model path
        model_dir = Path.home() / ".anima" / "tts_models"
        model_dir.mkdir(parents=True, exist_ok=True)

        model_file = f"{voice_name}.onnx"
        model_path = model_dir / model_file
        config_path = model_dir / f"{model_file}.json"

        if not model_path.exists():
            logger.info(f"Downloading TTS voice model '{voice_name}' (first time only)...")
            _download_model(model_dir, lang, lang_region, name, quality, voice_name)

        logger.info(f"Loading TTS voice from {model_path}")
        _voice = PiperVoice.load(str(model_path), str(config_path))
        _current_voice_name = voice_name
        logger.info("TTS voice loaded successfully")
    except Exception as e:
        logger.warning(f"Failed to load TTS voice: {e}")
        import traceback

        logger.debug(traceback.format_exc())
        _voice = None
    return _voice


def _download_model(model_dir: Path, lang: str, lang_region: str, name: str, quality: str, voice_name: str):
    """Download a Piper voice model from HuggingFace."""
    import urllib.request

    # HuggingFace URL pattern: /en/en_US/danny/low/
    base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang}/{lang_region}/{name}/{quality}/"
    files = [
        (f"{voice_name}.onnx", f"{voice_name}.onnx"),
        (f"{voice_name}.onnx.json", f"{voice_name}.onnx.json"),
    ]

    for remote_name, local_name in files:
        url = base_url + remote_name
        dest = model_dir / local_name
        logger.info(f"Downloading {url}...")
        urllib.request.urlretrieve(url, dest)

    logger.info("TTS model download complete")


def set_volume(volume: float):
    """Set TTS playback volume (0.0 to 1.0)."""
    global _volume
    _volume = max(0.0, min(1.0, volume))


def _init_mixer():
    """Initialize pygame mixer for audio playback."""
    global _pygame_mixer_initialized
    if not _pygame_mixer_initialized:
        try:
            import pygame  # type: ignore[import-not-found]

            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1)
            _pygame_mixer_initialized = True
        except Exception as e:
            logger.warning(f"Failed to initialize audio mixer: {e}")


def speak(text: str, blocking: bool = False, voice_name: str | None = None):
    """
    Speak text using TTS.

    Args:
        text: The text to speak
        blocking: If True, wait for speech to complete
        voice_name: Optional voice model name (e.g., 'en_US-danny-low')
    """

    def _speak_thread():
        try:
            voice = _get_voice(voice_name)
            if voice is None:
                logger.warning("TTS not available, skipping speech")
                return

            # Synthesize to WAV in memory using synthesize_wav
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)

            wav_buffer.seek(0)
            logger.debug(f"Synthesized {wav_buffer.getbuffer().nbytes} bytes of audio")

            # Play using pygame mixer
            _init_mixer()
            import pygame  # type: ignore[import-not-found]

            sound = pygame.mixer.Sound(wav_buffer)
            sound.set_volume(_volume)
            logger.debug(f"Playing {sound.get_length():.1f}s of audio at volume {_volume}")
            sound.play()

            if blocking:
                while pygame.mixer.get_busy():
                    pygame.time.wait(100)

        except Exception as e:
            logger.warning(f"TTS error: {e}")
            import traceback

            logger.debug(traceback.format_exc())

    if blocking:
        _speak_thread()
    else:
        thread = threading.Thread(target=_speak_thread, daemon=True)
        thread.start()


def speak_greeting(voice_name: str | None = None):
    """Speak a friendly startup greeting."""
    import random

    greetings = [
        "Hello! I'm awake and ready!",
        "Hey there! Nice to see you!",
        "Hi! Let's do something amazing today!",
        "Hello! I'm here and excited to help!",
        "Good to see you! I'm all eyes!",
    ]
    speak(random.choice(greetings), voice_name=voice_name)
