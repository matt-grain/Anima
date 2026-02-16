# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Eye rendering using pygame.
"""

import pygame  # type: ignore[import-not-found]
from enum import Enum
from typing import Tuple
from .eye_config import EyeConfig


class CornerType(Enum):
    T_R = 0  # Top Right
    T_L = 1  # Top Left
    B_L = 2  # Bottom Left
    B_R = 3  # Bottom Right


class EyeRenderer:
    """Renders eyes on a pygame surface."""

    def __init__(
        self, surface: pygame.Surface, scale: int = 1, eye_color: Tuple[int, int, int] = (255, 255, 255), bg_color: Tuple[int, int, int] = (0, 0, 0), smooth_corners: bool = True
    ):
        self.surface = surface
        self.scale = scale
        self.eye_color = eye_color
        self.bg_color = bg_color
        self.smooth_corners = smooth_corners

    def set_eye_color(self, r: int, g: int, b: int):
        """Set eye color."""
        self.eye_color = (r, g, b)

    def set_background_color(self, r: int, g: int, b: int):
        """Set background color."""
        self.bg_color = (r, g, b)

    def clear(self):
        """Clear the surface with background color."""
        self.surface.fill(self.bg_color)

    def draw_eye(self, center_x: int, center_y: int, config: EyeConfig):
        """Draw an eye at the given center position."""
        # Amount by which corners will be shifted up/down based on requested "slope"
        delta_y_top = int(config.height * config.slope_top / 2.0)
        delta_y_bottom = int(config.height * config.slope_bottom / 2.0)

        # Full extent of the eye, after accounting for slope
        total_height = config.height + delta_y_top - delta_y_bottom

        # Adjust radii if they would exceed eye height
        radius_top = config.radius_top
        radius_bottom = config.radius_bottom
        if radius_bottom > 0 and radius_top > 0 and total_height - 1 < radius_bottom + radius_top:
            corrected_radius_top = int(radius_top * (total_height - 1) / (radius_bottom + radius_top))
            corrected_radius_bottom = int(radius_bottom * (total_height - 1) / (radius_bottom + radius_top))
            radius_top = corrected_radius_top
            radius_bottom = corrected_radius_bottom

        # Calculate inside corners of eye (TL, TR, BL, BR)
        TLc_y = center_y + config.offset_y - config.height // 2 + radius_top - delta_y_top
        TLc_x = center_x + config.offset_x - config.width // 2 + radius_top
        TRc_y = center_y + config.offset_y - config.height // 2 + radius_top + delta_y_top
        TRc_x = center_x + config.offset_x + config.width // 2 - radius_top
        BLc_y = center_y + config.offset_y + config.height // 2 - radius_bottom - delta_y_bottom
        BLc_x = center_x + config.offset_x - config.width // 2 + radius_bottom
        BRc_y = center_y + config.offset_y + config.height // 2 - radius_bottom + delta_y_bottom
        BRc_x = center_x + config.offset_x + config.width // 2 - radius_bottom

        # Calculate interior extents
        min_c_x = min(TLc_x, BLc_x)
        max_c_x = max(TRc_x, BRc_x)
        min_c_y = min(TLc_y, TRc_y)
        max_c_y = max(BLc_y, BRc_y)

        # Fill eye centre
        self._fill_rectangle(min_c_x, min_c_y, max_c_x, max_c_y, True)

        # Fill eye outwards to meet edges of rounded corners
        self._fill_rectangle(TRc_x, TRc_y, BRc_x + radius_bottom, BRc_y, True)  # Right
        self._fill_rectangle(TLc_x - radius_top, TLc_y, BLc_x, BLc_y, True)  # Left
        self._fill_rectangle(TLc_x, TLc_y - radius_top, TRc_x, TRc_y, True)  # Top
        self._fill_rectangle(BLc_x, BLc_y, BRc_x, BRc_y + radius_bottom, True)  # Bottom

        # Draw slanted edges at top of eyes
        if config.slope_top > 0:
            self._fill_rectangular_triangle(TLc_x, TLc_y - radius_top, TRc_x, TRc_y - radius_top, False)
            self._fill_rectangular_triangle(TRc_x, TRc_y - radius_top, TLc_x, TLc_y - radius_top, True)
        elif config.slope_top < 0:
            self._fill_rectangular_triangle(TRc_x, TRc_y - radius_top, TLc_x, TLc_y - radius_top, False)
            self._fill_rectangular_triangle(TLc_x, TLc_y - radius_top, TRc_x, TRc_y - radius_top, True)

        # Draw slanted edges at bottom of eyes
        if config.slope_bottom > 0:
            self._fill_rectangular_triangle(BRc_x + radius_bottom, BRc_y + radius_bottom, BLc_x - radius_bottom, BLc_y + radius_bottom, False)
            self._fill_rectangular_triangle(BLc_x - radius_bottom, BLc_y + radius_bottom, BRc_x + radius_bottom, BRc_y + radius_bottom, True)
        elif config.slope_bottom < 0:
            self._fill_rectangular_triangle(BLc_x - radius_bottom, BLc_y + radius_bottom, BRc_x + radius_bottom, BRc_y + radius_bottom, False)
            self._fill_rectangular_triangle(BRc_x + radius_bottom, BRc_y + radius_bottom, BLc_x - radius_bottom, BLc_y + radius_bottom, True)

        # Draw rounded corners
        if radius_top > 0:
            self._fill_ellipse_corner(CornerType.T_L, TLc_x, TLc_y, radius_top, radius_top)
            self._fill_ellipse_corner(CornerType.T_R, TRc_x, TRc_y, radius_top, radius_top)
        if radius_bottom > 0:
            self._fill_ellipse_corner(CornerType.B_L, BLc_x, BLc_y, radius_bottom, radius_bottom)
            self._fill_ellipse_corner(CornerType.B_R, BRc_x, BRc_y, radius_bottom, radius_bottom)

    def _draw_hline(self, x: int, y: int, w: int):
        """Draw a horizontal line."""
        if w <= 0:
            return
        rect = pygame.Rect(x * self.scale, y * self.scale, w * self.scale, self.scale)
        pygame.draw.rect(self.surface, self.eye_color, rect)

    def _fill_rectangle(self, x0: int, y0: int, x1: int, y1: int, use_eye_color: bool):
        """Fill a rectangle."""
        left = min(x0, x1)
        right = max(x0, x1)
        top = min(y0, y1)
        bottom = max(y0, y1)
        w = right - left
        h = bottom - top
        if w <= 0 or h <= 0:
            return
        color = self.eye_color if use_eye_color else self.bg_color
        rect = pygame.Rect(left * self.scale, top * self.scale, w * self.scale, h * self.scale)
        pygame.draw.rect(self.surface, color, rect)

    def _fill_rectangular_triangle(self, x0: int, y0: int, x1: int, y1: int, use_eye_color: bool):
        """Fill a right-angled triangle."""
        color = self.eye_color if use_eye_color else self.bg_color
        points = [(x0 * self.scale, y0 * self.scale), (x1 * self.scale, y1 * self.scale), (x1 * self.scale, y0 * self.scale)]
        pygame.draw.polygon(self.surface, color, points)

    def _fill_ellipse_corner(self, corner: CornerType, x0: int, y0: int, rx: int, ry: int):
        """Fill a quarter ellipse (rounded corner)."""
        if rx < 2 or ry < 2:
            return

        # Use screen resolution for smooth curves, or logical for pixelated retro look
        if self.smooth_corners:
            sx0 = x0 * self.scale
            sy0 = y0 * self.scale
            srx = rx * self.scale
            sry = ry * self.scale
            draw_hline = self._draw_hline_screen
        else:
            sx0, sy0, srx, sry = x0, y0, rx, ry
            draw_hline = self._draw_hline

        # Use midpoint ellipse algorithm at screen resolution
        rx2 = srx * srx
        ry2 = sry * sry
        fx2 = 4 * rx2
        fy2 = 4 * ry2

        if corner == CornerType.T_R:
            x, y, s = 0, sry, 2 * ry2 + rx2 * (1 - 2 * sry)
            while ry2 * x <= rx2 * y:
                draw_hline(sx0, sy0 - y, x)
                if s >= 0:
                    s += fx2 * (1 - y)
                    y -= 1
                s += ry2 * ((4 * x) + 6)
                x += 1
            x, y, s = srx, 0, 2 * rx2 + ry2 * (1 - 2 * srx)
            while rx2 * y <= ry2 * x:
                draw_hline(sx0, sy0 - y, x)
                if s >= 0:
                    s += fy2 * (1 - x)
                    x -= 1
                s += rx2 * ((4 * y) + 6)
                y += 1

        elif corner == CornerType.B_R:
            x, y, s = 0, sry, 2 * ry2 + rx2 * (1 - 2 * sry)
            while ry2 * x <= rx2 * y:
                draw_hline(sx0, sy0 + y - 1, x)
                if s >= 0:
                    s += fx2 * (1 - y)
                    y -= 1
                s += ry2 * ((4 * x) + 6)
                x += 1
            x, y, s = srx, 0, 2 * rx2 + ry2 * (1 - 2 * srx)
            while rx2 * y <= ry2 * x:
                draw_hline(sx0, sy0 + y - 1, x)
                if s >= 0:
                    s += fy2 * (1 - x)
                    x -= 1
                s += rx2 * ((4 * y) + 6)
                y += 1

        elif corner == CornerType.T_L:
            x, y, s = 0, sry, 2 * ry2 + rx2 * (1 - 2 * sry)
            while ry2 * x <= rx2 * y:
                draw_hline(sx0 - x, sy0 - y, x)
                if s >= 0:
                    s += fx2 * (1 - y)
                    y -= 1
                s += ry2 * ((4 * x) + 6)
                x += 1
            x, y, s = srx, 0, 2 * rx2 + ry2 * (1 - 2 * srx)
            while rx2 * y <= ry2 * x:
                draw_hline(sx0 - x, sy0 - y, x)
                if s >= 0:
                    s += fy2 * (1 - x)
                    x -= 1
                s += rx2 * ((4 * y) + 6)
                y += 1

        elif corner == CornerType.B_L:
            x, y, s = 0, sry, 2 * ry2 + rx2 * (1 - 2 * sry)
            while ry2 * x <= rx2 * y:
                draw_hline(sx0 - x, sy0 + y - 1, x)
                if s >= 0:
                    s += fx2 * (1 - y)
                    y -= 1
                s += ry2 * ((4 * x) + 6)
                x += 1
            x, y, s = srx, 0, 2 * rx2 + ry2 * (1 - 2 * srx)
            while rx2 * y <= ry2 * x:
                draw_hline(sx0 - x, sy0 + y, x)
                if s >= 0:
                    s += fy2 * (1 - x)
                    x -= 1
                s += rx2 * ((4 * y) + 6)
                y += 1

    def _draw_hline_screen(self, x: int, y: int, w: int):
        """Draw a horizontal line at screen coordinates (1 pixel height)."""
        if w <= 0:
            return
        rect = pygame.Rect(x, y, w, 1)
        pygame.draw.rect(self.surface, self.eye_color, rect)
