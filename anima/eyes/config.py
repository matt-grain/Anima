# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Configuration management for Anima Eyes.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Tuple


@dataclass
class DisplayConfig:
    """Display/window settings."""

    width: int = 128  # Logical width (like OLED)
    height: int = 64  # Logical height
    scale: int = 5  # Scale factor for window (128*5 = 640px)
    fps: int = 60  # Target frame rate
    fullscreen: bool = False
    borderless: bool = False  # Remove window title bar (useful for MCP mode)
    window_x: int | None = None  # Window X position (None = system default)
    window_y: int | None = None  # Window Y position (None = system default)
    title: str = "Anima Eyes"
    smooth_corners: bool = True  # Draw corners at screen resolution for smooth curves


@dataclass
class ColorConfig:
    """Color settings."""

    eye_color: Tuple[int, int, int] = (173, 216, 230)  # Light blue (Cozmo-like)
    background_color: Tuple[int, int, int] = (0, 0, 0)  # Black


@dataclass
class AnimationConfig:
    """Animation speed settings."""

    transition_speed: float = 1.0  # Multiplier for emotion transitions
    look_speed: float = 1.0  # Multiplier for look movements
    blink_speed: float = 1.0  # Multiplier for blink animation
    variation_speed: float = 1.0  # Multiplier for idle variations


@dataclass
class BehaviorConfig:
    """Automatic behavior settings."""

    random_look: bool = True  # Enable random look direction
    random_blink: bool = True  # Enable automatic blinking
    random_behavior: bool = False  # Enable random emotion changes
    blink_interval_ms: int = 3500  # Time between blinks
    look_interval_ms: int = 4000  # Time between random looks


@dataclass
class EyeShapeConfig:
    """Eye shape settings."""

    eye_size: int = 40  # Base eye size
    eye_spacing: int = 4  # Distance between eyes


@dataclass
class TTSConfig:
    """Text-to-speech settings."""

    enabled: bool = True
    voice: str = "en_US-danny-low"  # Piper voice model name
    # Available voices: en_US-lessac-medium, en_US-danny-low, en_US-amy-medium, etc.
    # See: https://rhasspy.github.io/piper-samples/
    speak_on_startup: bool = True
    volume: float = 1.0  # 0.0 to 1.0


@dataclass
class Config:
    """Main configuration container."""

    display: DisplayConfig = field(default_factory=DisplayConfig)
    colors: ColorConfig = field(default_factory=ColorConfig)
    animation: AnimationConfig = field(default_factory=AnimationConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    eye_shape: EyeShapeConfig = field(default_factory=EyeShapeConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)

    @classmethod
    def load(cls, path: Path | str | None = None) -> "Config":
        """Load config from file, or return defaults."""
        if path is None:
            # Try default locations
            for p in [Path("anima_eyes.json"), Path.home() / ".anima" / "anima_eyes.json"]:
                if p.exists():
                    path = p
                    break

        if path is None or not Path(path).exists():
            return cls()

        with open(path) as f:
            data = json.load(f)

        return cls(
            display=DisplayConfig(**data.get("display", {})),
            colors=ColorConfig(
                eye_color=tuple(data.get("colors", {}).get("eye_color", (173, 216, 230))),
                background_color=tuple(data.get("colors", {}).get("background_color", (0, 0, 0))),
            ),
            animation=AnimationConfig(**data.get("animation", {})),
            behavior=BehaviorConfig(**data.get("behavior", {})),
            eye_shape=EyeShapeConfig(**data.get("eye_shape", {})),
            tts=TTSConfig(**data.get("tts", {})),
        )

    def save(self, path: Path | str):
        """Save config to file."""
        data = {
            "display": asdict(self.display),
            "colors": {
                "eye_color": list(self.colors.eye_color),
                "background_color": list(self.colors.background_color),
            },
            "animation": asdict(self.animation),
            "behavior": asdict(self.behavior),
            "eye_shape": asdict(self.eye_shape),
            "tts": asdict(self.tts),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


# Default config instance
default_config = Config()
