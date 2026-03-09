# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Text-to-Speech module using Piper TTS and espeak-ng.

Provides offline, fast TTS synthesis on CPU.
Includes special "joshua" voice (WOPR from WarGames 1983).
"""

import io
import wave
import threading
import subprocess
import tempfile
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
    "danny": "en_US-danny-low",  # Male, calm
    "libritts": "en_US-libritts_r-medium",  # High quality, preferred default
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
    # Special voices
    "joshua": "joshua",  # WOPR from WarGames (espeak + WOPR filter)
}

# Cache for espeak-ng path
_espeak_path: str | None = None
_espeak_checked: bool = False


def _find_espeak() -> str | None:
    """Find espeak-ng executable, with caching."""
    global _espeak_path, _espeak_checked

    if _espeak_checked:
        return _espeak_path

    import shutil
    import sys

    _espeak_path = shutil.which("espeak-ng")

    if _espeak_path is None and sys.platform == "win32":
        # Try common Windows install location
        win_path = Path("C:/Program Files/eSpeak NG/espeak-ng.exe")
        if win_path.exists():
            _espeak_path = str(win_path)

    _espeak_checked = True
    return _espeak_path


def check_joshua_available() -> dict:
    """
    Check if Joshua voice (espeak-ng) is available.

    Returns dict with 'available' bool and 'message' with install instructions if needed.
    """
    espeak = _find_espeak()
    if espeak:
        return {
            "available": True,
            "espeak_path": espeak,
            "message": "Joshua voice (WOPR) is available!",
        }
    else:
        return {
            "available": False,
            "message": (
                "Joshua voice requires espeak-ng. Install it:\n"
                "  Windows: Download MSI from https://github.com/espeak-ng/espeak-ng/releases\n"
                "  macOS:   brew install espeak-ng\n"
                "  Linux:   apt install espeak-ng\n"
                "After install, either add to PATH or restart your terminal."
            ),
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
        from piper.voice import PiperVoice

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


def _apply_wopr_filter_numpy(data, rate: int):
    """
    Apply WOPR voice filter using pure numpy (no scipy).

    This is the fallback for MCP context where scipy hangs due to OpenBLAS threading issues.
    """
    import numpy as np

    logger.debug("WOPR: using numpy-only filter")

    # 1. Simple low-pass via moving average (approximates vintage warmth)
    window_size = int(rate / 3500)  # ~6 samples at 22050Hz
    if window_size > 1:
        kernel = np.ones(window_size) / window_size
        filtered = np.convolve(data, kernel, mode="same")
    else:
        filtered = data.copy()

    # 2. Comb filter for metallic resonance (feedforward)
    comb1_delay = int(rate * 5 / 1000)  # 5ms
    comb2_delay = int(rate * 7 / 1000)  # 7ms

    metallic = np.zeros(len(filtered) + comb2_delay)
    metallic[: len(filtered)] = filtered
    metallic[comb1_delay : comb1_delay + len(filtered)] += filtered * 0.55
    metallic[comb2_delay : comb2_delay + len(filtered)] += filtered * 0.35

    # 3. Reverb (computer room echo)
    delay_samples = int(rate * 60 / 1000)  # 60ms
    reverb = np.zeros(len(metallic) + delay_samples * 6)
    reverb[: len(metallic)] = metallic

    for delay_mult, base_gain in [(1, 0.40), (2, 0.28), (3, 0.18), (4, 0.10), (5, 0.05), (6, 0.02)]:
        delay = delay_samples * delay_mult
        gain = base_gain * (0.5 ** (delay_mult - 1))
        reverb[delay : delay + len(metallic)] += metallic * gain

    # 4. Final smoothing (simple low-pass)
    window_size = int(rate / 3000)
    if window_size > 1:
        kernel = np.ones(window_size) / window_size
        filtered = np.convolve(reverb, kernel, mode="same")
    else:
        filtered = reverb

    # Normalize
    filtered = filtered / np.max(np.abs(filtered)) * 0.9
    return filtered


def _apply_wopr_filter(data, rate: int, use_scipy: bool = True):
    """
    Apply WOPR voice filter chain (v8) for Joshua voice.

    Chain: Low-pass 4kHz (simulates 8kHz) -> Nasal resonance -> Double comb -> Reverb -> Low-pass

    Args:
        data: Audio samples as float array
        rate: Sample rate
        use_scipy: If False, use numpy-only filter (for MCP context)
    """
    import numpy as np

    if not use_scipy:
        return _apply_wopr_filter_numpy(data, rate)

    try:
        logger.debug("WOPR: importing scipy.signal...")
        from scipy.signal import butter, lfilter, iirpeak

        logger.debug("WOPR: scipy.signal imported successfully")

        # 1. Simulate 8kHz vintage rate with aggressive low-pass
        nyq = rate / 2
        logger.debug("WOPR: applying vintage low-pass...")
        b_vintage, a_vintage = butter(6, 3500 / nyq, btype="low")  # pyright: ignore[reportAssignmentType,reportGeneralTypeIssues]
        upsampled = lfilter(b_vintage, a_vintage, data)
        logger.debug("WOPR: vintage low-pass done")

        # 2. NASAL RESONANCE (pinched nose effect)
        b_peak, a_peak = iirpeak(1500 / nyq, 3)  # pyright: ignore[reportAssignmentType]
        nasal = lfilter(b_peak, a_peak, upsampled)
        nasal_mix = upsampled * 0.6 + nasal * 0.4  # pyright: ignore[reportOperatorIssue]

        # 3. DOUBLE COMB FILTER (metallic resonance) - vectorized with lfilter
        comb1_samples = int(rate * 5 / 1000)
        comb2_samples = int(rate * 7 / 1000)

        comb1_b = np.zeros(comb1_samples + 1)
        comb1_b[0] = 1.0
        comb1_a = np.zeros(comb1_samples + 1)
        comb1_a[0] = 1.0
        comb1_a[comb1_samples] = -0.55
        metallic = lfilter(comb1_b, comb1_a, nasal_mix)

        comb2_b = np.zeros(comb2_samples + 1)
        comb2_b[0] = 1.0
        comb2_a = np.zeros(comb2_samples + 1)
        comb2_a[0] = 1.0
        comb2_a[comb2_samples] = -0.35
        metallic2 = lfilter(comb2_b, comb2_a, metallic)

        # 4. REVERB (computer room echo)
        delay_samples = int(rate * 60 / 1000)
        reverb = np.zeros(len(metallic2) + delay_samples * 6)
        reverb[: len(metallic2)] = metallic2

        for delay_mult, base_gain in [(1, 0.40), (2, 0.28), (3, 0.18), (4, 0.10), (5, 0.05), (6, 0.02)]:
            delay = delay_samples * delay_mult
            gain = base_gain * (0.5 ** (delay_mult - 1))
            reverb[delay : delay + len(metallic2)] += metallic2 * gain  # pyright: ignore[reportOperatorIssue]

        # 5. LOW-PASS (warm vintage tone)
        b, a = butter(4, 3000 / nyq, btype="low")  # pyright: ignore[reportAssignmentType,reportGeneralTypeIssues]
        filtered = lfilter(b, a, reverb)

    except ImportError:
        logger.warning("scipy not available, using numpy-only WOPR filter")
        return _apply_wopr_filter_numpy(data, rate)

    # Normalize
    filtered = filtered / np.max(np.abs(filtered)) * 0.9
    return filtered


def _synthesize_joshua_mcp(text: str) -> io.BytesIO | None:
    """
    Synthesize Joshua voice for MCP context (no scipy, uses numpy only).

    This avoids scipy which hangs due to OpenBLAS threading issues in MCP subprocess.
    """
    import time
    import numpy as np

    start_time = time.time()
    logger.info(f"Joshua MCP synthesis starting for: {text[:30]}...")

    # Create temp file for espeak output
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Find espeak-ng
        espeak_cmd = _find_espeak()
        if espeak_cmd is None:
            logger.warning("espeak-ng not found for Joshua MCP")
            return None

        # Run espeak-ng
        result = subprocess.run(
            [espeak_cmd, "-p", "40", "-s", "120", "-g", "1", "-w", tmp_path, text],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning(f"espeak-ng failed: {result.stderr}")
            return None

        logger.debug(f"espeak completed in {time.time() - start_time:.2f}s")

        # Read WAV with stdlib wave (not scipy)
        with wave.open(tmp_path, "rb") as wav_in:
            rate = wav_in.getframerate()
            n_frames = wav_in.getnframes()
            raw_data = wav_in.readframes(n_frames)
            # Convert to numpy
            data = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

        logger.debug(f"WAV read in {time.time() - start_time:.2f}s, rate={rate}, samples={len(data)}")

        # Apply numpy-only WOPR filter
        filtered = _apply_wopr_filter_numpy(data, rate)
        logger.debug(f"WOPR filter complete in {time.time() - start_time:.2f}s")

        # Convert back to int16
        output = (filtered * 32767).astype(np.int16)

        # Write to BytesIO as WAV
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(rate)
            wav_file.writeframes(output.tobytes())

        wav_buffer.seek(0)
        logger.info(f"Joshua MCP synthesis complete in {time.time() - start_time:.2f}s")
        return wav_buffer

    except Exception as e:
        logger.warning(f"Joshua MCP synthesis failed: {e}")
        import traceback

        logger.debug(traceback.format_exc())
        return None
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _synthesize_joshua(text: str, use_scipy: bool = True) -> io.BytesIO | None:
    """
    Synthesize text using espeak-ng + WOPR filter for Joshua voice.

    Returns a BytesIO containing WAV data, or None if espeak is not available.

    Args:
        text: Text to speak
        use_scipy: If False, use MCP-safe numpy-only synthesis
    """
    if not use_scipy:
        return _synthesize_joshua_mcp(text)

    import os
    import time

    # CRITICAL: Set OpenBLAS threading BEFORE importing scipy
    # This fixes hangs on Windows with Python 3.13
    os.environ["OPENBLAS_NUM_THREADS"] = "1"

    start_time = time.time()
    logger.info(f"Joshua synthesis starting for: {text[:30]}...")

    import numpy as np

    logger.debug(f"numpy imported in {time.time() - start_time:.2f}s")

    from scipy.io import wavfile

    logger.debug(f"scipy.io imported in {time.time() - start_time:.2f}s")

    # Create temp file for espeak output
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Find espeak-ng executable
        espeak_cmd = _find_espeak()
        if espeak_cmd is None:
            check = check_joshua_available()
            logger.warning(f"espeak-ng not found.\n{check['message']}")
            return None

        logger.debug(f"espeak found at {espeak_cmd}")

        # Run espeak-ng with Joshua parameters
        result = subprocess.run(
            [espeak_cmd, "-p", "40", "-s", "120", "-g", "1", "-w", tmp_path, text],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning(f"espeak-ng failed: {result.stderr}")
            return None

        logger.debug(f"espeak completed in {time.time() - start_time:.2f}s")

        # Read the raw espeak output
        rate, data = wavfile.read(tmp_path)
        logger.debug(f"wavfile read in {time.time() - start_time:.2f}s, rate={rate}, samples={len(data)}")

        # Convert to float
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data = data.astype(np.float32) / 2147483648.0

        # Apply WOPR filter chain
        logger.debug("Applying WOPR filter...")
        filtered = _apply_wopr_filter(data, rate)
        logger.debug(f"WOPR filter complete in {time.time() - start_time:.2f}s")

        # Convert back to int16
        output = (filtered * 32767).astype(np.int16)

        # Write to BytesIO as WAV
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(rate)
            wav_file.writeframes(output.tobytes())

        wav_buffer.seek(0)
        logger.info(f"Joshua synthesis complete in {time.time() - start_time:.2f}s, {wav_buffer.getbuffer().nbytes} bytes")
        return wav_buffer

    except FileNotFoundError:
        logger.warning("espeak-ng not found. Install it for Joshua voice.")
        return None
    except Exception as e:
        logger.warning(f"Joshua voice synthesis failed: {e}")
        import traceback

        logger.debug(traceback.format_exc())
        return None
    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)


def _init_mixer() -> bool:
    """Initialize pygame mixer for audio playback. Returns True if successful."""
    global _pygame_mixer_initialized
    if _pygame_mixer_initialized:
        return True
    try:
        import pygame

        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
        _pygame_mixer_initialized = True
        return True
    except Exception as e:
        logger.warning(f"Failed to initialize audio mixer: {e}")
        return False


def _play_audio_native(wav_buffer: io.BytesIO, blocking: bool = True) -> bool:
    """
    Play audio using Windows-native PowerShell (fallback for MCP subprocess).

    Returns True if playback started successfully.
    """
    import sys

    if sys.platform != "win32":
        return False

    tmp_path: str | None = None
    try:
        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_buffer.read())
            tmp_path = tmp.name

        # Use PowerShell to play the audio
        # The SoundPlayer class provides synchronous playback
        ps_cmd = f"""
            $player = New-Object System.Media.SoundPlayer("{tmp_path}")
            $player.PlaySync()
            Remove-Item "{tmp_path}" -ErrorAction SilentlyContinue
        """

        # DETACHED_PROCESS ensures subprocess survives daemon thread termination
        # This is critical for Joshua voice which takes ~1.5s to synthesize
        CREATE_NO_WINDOW = 0x08000000
        DETACHED_PROCESS = 0x00000008

        if blocking:
            # Use Popen + wait with DETACHED_PROCESS flag
            proc = subprocess.Popen(
                ["powershell", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
            )
            proc.wait()  # Wait for audio to finish
        else:
            # Non-blocking: fire and forget
            subprocess.Popen(
                ["powershell", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
            )

        logger.debug("Audio played via PowerShell native")
        return True

    except Exception as e:
        logger.warning(f"Native audio playback failed: {e}")
        # Clean up temp file if still exists
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass
        return False


def speak(text: str, blocking: bool = False, voice_name: str | None = None, force_native: bool = False, mcp_safe: bool = False):
    """
    Speak text using TTS.

    Args:
        text: The text to speak
        blocking: If True, wait for speech to complete
        voice_name: Optional voice model name (e.g., 'en_US-danny-low', 'joshua')
        force_native: If True, skip pygame and use Windows native playback
        mcp_safe: If True, use numpy-only Joshua synthesis (avoids scipy hang)
    """

    def _speak_impl():
        try:
            # Resolve voice name
            resolved_voice = voice_name
            if resolved_voice is None:
                resolved_voice = _default_voice_name
            if resolved_voice in AVAILABLE_VOICES:
                resolved_voice = AVAILABLE_VOICES[resolved_voice]

            # Special handling for Joshua (WOPR) voice
            if resolved_voice == "joshua":
                # Use MCP-safe (no scipy) version when mcp_safe is set
                wav_buffer = _synthesize_joshua(text, use_scipy=not mcp_safe)
                if wav_buffer is None:
                    logger.warning("Joshua voice not available, falling back to default")
                    wav_buffer = _synthesize_piper(text, None)
            else:
                wav_buffer = _synthesize_piper(text, resolved_voice)

            if wav_buffer is None:
                logger.warning("TTS not available, skipping speech")
                return

            logger.debug(f"Synthesized {wav_buffer.getbuffer().nbytes} bytes of audio")

            # Try pygame mixer first (unless force_native is set)
            if not force_native and _init_mixer():
                try:
                    import pygame
                    import time

                    sound = pygame.mixer.Sound(wav_buffer)
                    sound.set_volume(_volume)
                    sound_length = sound.get_length()
                    logger.debug(f"Playing {sound_length:.1f}s via pygame at volume {_volume}")
                    sound.play()

                    if blocking:
                        # Use timeout-based waiting instead of get_busy() which hangs in MCP
                        wait_time = sound_length + 0.5  # Add buffer
                        time.sleep(wait_time)
                    return
                except Exception as e:
                    logger.warning(f"Pygame playback failed: {e}, trying native...")

            # Fallback to Windows native playback (works in MCP subprocess)
            wav_buffer.seek(0)
            if not _play_audio_native(wav_buffer, blocking=blocking):
                logger.warning("All audio playback methods failed")

        except Exception as e:
            logger.warning(f"TTS error: {e}")
            import traceback

            logger.debug(traceback.format_exc())

    if blocking:
        _speak_impl()
    else:
        thread = threading.Thread(target=_speak_impl, daemon=True)
        thread.start()


def _synthesize_piper(text: str, voice_name: str | None) -> io.BytesIO | None:
    """Synthesize text using Piper TTS."""
    voice = _get_voice(voice_name)
    if voice is None:
        return None

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    wav_buffer.seek(0)
    return wav_buffer


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
