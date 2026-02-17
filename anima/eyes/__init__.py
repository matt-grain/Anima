# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Anima Eyes - Visual expression module for Anima.

This module provides animated eyes that can express emotions,
look around, and speak using text-to-speech.

Requires optional dependencies: pip install anima[eyes]
"""

from .presets import Emotion, EMOTION_NAMES, emotion_from_name

__all__ = [
    "Emotion",
    "EMOTION_NAMES",
    "emotion_from_name",
]


# Lazy imports to avoid pygame/piper import overhead when not using eyes
def get_display():
    """Get the EyesDisplay class (lazy import)."""
    from .display import EyesDisplay

    return EyesDisplay


def get_config():
    """Get the Config class (lazy import)."""
    from .config import Config

    return Config


def get_daemon_client():
    """Get the EyesDaemonClient class (lazy import)."""
    from .client import EyesDaemonClient

    return EyesDaemonClient


def get_daemon_server():
    """Get the EyesDaemonServer class (lazy import)."""
    from .daemon import EyesDaemonServer

    return EyesDaemonServer
