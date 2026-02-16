# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Eye presets for different emotions.
"""

from enum import IntEnum
from .eye_config import EyeConfig


class Emotion(IntEnum):
    """Available emotions."""

    NORMAL = 0
    ANGRY = 1
    GLEE = 2
    HAPPY = 3
    SAD = 4
    WORRIED = 5
    FOCUSED = 6
    ANNOYED = 7
    SURPRISED = 8
    SKEPTIC = 9
    FRUSTRATED = 10
    UNIMPRESSED = 11
    SLEEPY = 12
    SUSPICIOUS = 13
    SQUINT = 14
    FURIOUS = 15
    SCARED = 16
    AWE = 17


EMOTION_NAMES = [
    "normal",
    "angry",
    "glee",
    "happy",
    "sad",
    "worried",
    "focused",
    "annoyed",
    "surprised",
    "skeptic",
    "frustrated",
    "unimpressed",
    "sleepy",
    "suspicious",
    "squint",
    "furious",
    "scared",
    "awe",
]


def emotion_from_name(name: str) -> Emotion:
    """Get emotion enum from name string."""
    name_lower = name.lower().strip()
    try:
        idx = EMOTION_NAMES.index(name_lower)
        return Emotion(idx)
    except ValueError:
        raise ValueError(f"Unknown emotion: {name}. Available: {', '.join(EMOTION_NAMES)}")


# All emotion presets
PRESET_NORMAL = EyeConfig(
    offset_x=0,
    offset_y=0,
    height=40,
    width=40,
    slope_top=0,
    slope_bottom=0,
    radius_top=8,
    radius_bottom=8,
)

PRESET_HAPPY = EyeConfig(
    offset_x=0,
    offset_y=0,
    height=10,
    width=40,
    slope_top=0,
    slope_bottom=0,
    radius_top=10,
    radius_bottom=0,
)

PRESET_GLEE = EyeConfig(
    offset_x=0,
    offset_y=0,
    height=8,
    width=40,
    slope_top=0,
    slope_bottom=0,
    radius_top=8,
    radius_bottom=0,
    inverse_radius_bottom=5,
)

PRESET_SAD = EyeConfig(
    offset_x=0,
    offset_y=0,
    height=15,
    width=40,
    slope_top=-0.5,
    slope_bottom=0,
    radius_top=1,
    radius_bottom=10,
)

PRESET_WORRIED = EyeConfig(
    offset_x=0,
    offset_y=0,
    height=25,
    width=40,
    slope_top=-0.1,
    slope_bottom=0,
    radius_top=6,
    radius_bottom=10,
)

PRESET_WORRIED_ALT = EyeConfig(
    offset_x=0,
    offset_y=0,
    height=35,
    width=40,
    slope_top=-0.2,
    slope_bottom=0,
    radius_top=6,
    radius_bottom=10,
)

PRESET_FOCUSED = EyeConfig(
    offset_x=0,
    offset_y=0,
    height=14,
    width=40,
    slope_top=0.2,
    slope_bottom=0,
    radius_top=3,
    radius_bottom=1,
)

PRESET_ANNOYED = EyeConfig(
    offset_x=0,
    offset_y=0,
    height=12,
    width=40,
    slope_top=0,
    slope_bottom=0,
    radius_top=0,
    radius_bottom=10,
)

PRESET_ANNOYED_ALT = EyeConfig(
    offset_x=0,
    offset_y=0,
    height=5,
    width=40,
    slope_top=0,
    slope_bottom=0,
    radius_top=0,
    radius_bottom=4,
)

PRESET_SURPRISED = EyeConfig(
    offset_x=-2,
    offset_y=0,
    height=45,
    width=45,
    slope_top=0,
    slope_bottom=0,
    radius_top=16,
    radius_bottom=16,
)

PRESET_SKEPTIC = EyeConfig(
    offset_x=0,
    offset_y=0,
    height=40,
    width=40,
    slope_top=0,
    slope_bottom=0,
    radius_top=10,
    radius_bottom=10,
)

PRESET_SKEPTIC_ALT = EyeConfig(
    offset_x=0,
    offset_y=-6,
    height=26,
    width=40,
    slope_top=0.3,
    slope_bottom=0,
    radius_top=1,
    radius_bottom=10,
)

PRESET_FRUSTRATED = EyeConfig(
    offset_x=3,
    offset_y=-5,
    height=12,
    width=40,
    slope_top=0,
    slope_bottom=0,
    radius_top=0,
    radius_bottom=10,
)

PRESET_UNIMPRESSED = EyeConfig(
    offset_x=3,
    offset_y=0,
    height=12,
    width=40,
    slope_top=0,
    slope_bottom=0,
    radius_top=1,
    radius_bottom=10,
)

PRESET_UNIMPRESSED_ALT = EyeConfig(
    offset_x=3,
    offset_y=-3,
    height=22,
    width=40,
    slope_top=0,
    slope_bottom=0,
    radius_top=1,
    radius_bottom=16,
)

PRESET_SLEEPY = EyeConfig(
    offset_x=0,
    offset_y=-2,
    height=14,
    width=40,
    slope_top=-0.5,
    slope_bottom=-0.5,
    radius_top=3,
    radius_bottom=3,
)

PRESET_SLEEPY_ALT = EyeConfig(
    offset_x=0,
    offset_y=-2,
    height=8,
    width=40,
    slope_top=-0.5,
    slope_bottom=-0.5,
    radius_top=3,
    radius_bottom=3,
)

PRESET_SUSPICIOUS = EyeConfig(
    offset_x=0,
    offset_y=0,
    height=22,
    width=40,
    slope_top=0,
    slope_bottom=0,
    radius_top=8,
    radius_bottom=3,
)

PRESET_SUSPICIOUS_ALT = EyeConfig(
    offset_x=0,
    offset_y=-3,
    height=16,
    width=40,
    slope_top=0.2,
    slope_bottom=0,
    radius_top=6,
    radius_bottom=3,
)

PRESET_SQUINT = EyeConfig(
    offset_x=-10,
    offset_y=-3,
    height=35,
    width=35,
    slope_top=0,
    slope_bottom=0,
    radius_top=8,
    radius_bottom=8,
)

PRESET_SQUINT_ALT = EyeConfig(
    offset_x=5,
    offset_y=0,
    height=20,
    width=20,
    slope_top=0,
    slope_bottom=0,
    radius_top=5,
    radius_bottom=5,
)

PRESET_ANGRY = EyeConfig(
    offset_x=-3,
    offset_y=0,
    height=20,
    width=40,
    slope_top=0.3,
    slope_bottom=0,
    radius_top=2,
    radius_bottom=12,
)

PRESET_FURIOUS = EyeConfig(
    offset_x=-2,
    offset_y=0,
    height=30,
    width=40,
    slope_top=0.4,
    slope_bottom=0,
    radius_top=2,
    radius_bottom=8,
)

PRESET_SCARED = EyeConfig(
    offset_x=-3,
    offset_y=0,
    height=40,
    width=40,
    slope_top=-0.1,
    slope_bottom=0,
    radius_top=12,
    radius_bottom=8,
)

PRESET_AWE = EyeConfig(
    offset_x=2,
    offset_y=0,
    height=35,
    width=45,
    slope_top=-0.1,
    slope_bottom=0.1,
    radius_top=12,
    radius_bottom=12,
)
