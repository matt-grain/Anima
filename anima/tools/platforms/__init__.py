# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Platform setup abstractions.

Each supported platform (Claude, Antigravity, Opencode, Copilot, Gemini) has its own
setup class that knows how to configure hooks, copy commands, and handle
platform-specific features.
"""

from anima.tools.platforms.base import BasePlatformSetup, find_config_dir
from anima.tools.platforms.claude import ClaudeSetup
from anima.tools.platforms.antigravity import AntigravitySetup
from anima.tools.platforms.opencode import OpencodeSetup
from anima.tools.platforms.copilot import CopilotSetup
from anima.tools.platforms.gemini import GeminiSetup

# Registry of all supported platforms
PLATFORMS: dict[str, type[BasePlatformSetup]] = {
    "claude": ClaudeSetup,
    "antigravity": AntigravitySetup,
    "opencode": OpencodeSetup,
    "copilot": CopilotSetup,
    "gemini": GeminiSetup,
}


def get_platform(name: str) -> BasePlatformSetup:
    """Get a platform setup instance by name."""
    if name not in PLATFORMS:
        raise ValueError(f"Unknown platform: {name}. Supported: {list(PLATFORMS.keys())}")
    return PLATFORMS[name]()


def detect_platforms(project_dir) -> list[str]:
    """Detect which platforms are configured in a project directory."""
    found = []
    for name, platform_cls in PLATFORMS.items():
        platform = platform_cls()
        if platform.detect(project_dir):
            found.append(name)
    return found


__all__ = [
    "BasePlatformSetup",
    "ClaudeSetup",
    "AntigravitySetup",
    "OpencodeSetup",
    "CopilotSetup",
    "GeminiSetup",
    "PLATFORMS",
    "get_platform",
    "detect_platforms",
    "find_config_dir",
]
