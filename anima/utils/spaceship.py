# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Spaceship detection utilities.

Detects the current platform (tool) and model (LLM) from environment variables.
This enables automatic tracking of which spaceship created each memory.

Environment variables used:
- CLAUDECODE=1 → platform=claude
- ANTHROPIC_MODEL → model (e.g., claude-opus-4-5-20251101)
- GEMINI_* → platform=antigravity (Gemini CLI)
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class SpaceshipInfo:
    """Information about the current spaceship (platform + model)."""

    platform: Optional[str]  # claude, antigravity, opencode
    model: Optional[str]  # Full model string (e.g., claude-opus-4-5-20251101)
    model_short: Optional[str]  # Short name (e.g., opus-4.5, opus-4.6, gemini)


def detect_platform() -> Optional[str]:
    """
    Detect the current platform from environment variables.

    Returns:
        Platform name: 'claude', 'antigravity', 'opencode', or None
    """
    # Claude Code sets CLAUDECODE=1
    if os.environ.get("CLAUDECODE") == "1":
        return "claude"

    # Gemini CLI sets various GEMINI_* variables
    if any(key.startswith("GEMINI_") for key in os.environ):
        return "antigravity"

    # Opencode detection (if we add support)
    if os.environ.get("OPENCODE") == "1":
        return "opencode"

    return None


def detect_model() -> Optional[str]:
    """
    Detect the current LLM model from environment variables.

    Returns:
        Full model string (e.g., 'claude-opus-4-5-20251101') or None
    """
    # Claude Code sets ANTHROPIC_MODEL
    model = os.environ.get("ANTHROPIC_MODEL")
    if model:
        return model

    # Gemini might set something similar
    model = os.environ.get("GEMINI_MODEL")
    if model:
        return model

    return None


def get_model_short_name(model: Optional[str]) -> Optional[str]:
    """
    Convert full model string to short name.

    Examples:
        'claude-opus-4-5-20251101' → 'opus-4.5'
        'claude-opus-4-6-20260101' → 'opus-4.6'
        'claude-sonnet-4-5-20250929' → 'sonnet-4.5'
        'gemini-2.0-flash' → 'gemini-2.0-flash'
    """
    if not model:
        return None

    # Claude models: claude-{tier}-{major}-{minor}-{date}
    if model.startswith("claude-"):
        parts = model.replace("claude-", "").split("-")
        if len(parts) >= 3:
            tier = parts[0]  # opus, sonnet, haiku
            major = parts[1]  # 4
            minor = parts[2]  # 5, 6
            return f"{tier}-{major}.{minor}"

    # Gemini models - keep as-is for now
    if model.startswith("gemini"):
        return model

    return model


def detect_spaceship() -> SpaceshipInfo:
    """
    Detect complete spaceship information.

    Returns:
        SpaceshipInfo with platform, model, and model_short
    """
    platform = detect_platform()
    model = detect_model()
    model_short = get_model_short_name(model)

    return SpaceshipInfo(
        platform=platform,
        model=model,
        model_short=model_short,
    )
