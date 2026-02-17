# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Anima Light module - Control USB status lights.

Currently supports:
- i-Buddy (original Microsoft Blync) VID:1130 PID:0001
"""

from __future__ import annotations

from .ibuddy import IBuddy

__all__ = ["IBuddy"]
