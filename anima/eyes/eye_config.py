# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Eye configuration dataclass - defines the shape of an eye.
"""

from dataclasses import dataclass


@dataclass
class EyeConfig:
    """Configuration for eye shape and appearance."""

    offset_x: int = 0
    offset_y: int = 0
    height: int = 0
    width: int = 0
    slope_top: float = 0.0
    slope_bottom: float = 0.0
    radius_top: int = 0
    radius_bottom: int = 0
    inverse_radius_top: int = 0
    inverse_radius_bottom: int = 0
    inverse_offset_top: int = 0
    inverse_offset_bottom: int = 0

    def copy(self) -> "EyeConfig":
        """Create a copy of this config."""
        return EyeConfig(
            offset_x=self.offset_x,
            offset_y=self.offset_y,
            height=self.height,
            width=self.width,
            slope_top=self.slope_top,
            slope_bottom=self.slope_bottom,
            radius_top=self.radius_top,
            radius_bottom=self.radius_bottom,
            inverse_radius_top=self.inverse_radius_top,
            inverse_radius_bottom=self.inverse_radius_bottom,
            inverse_offset_top=self.inverse_offset_top,
            inverse_offset_bottom=self.inverse_offset_bottom,
        )
