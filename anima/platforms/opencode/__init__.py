"""Opencode platform integration for Anima LTM."""

from pathlib import Path


def is_opencode_environment() -> bool:
    """Detect if we are running inside an Opencode project."""
    # Check for .opencode directory in current or parent dirs
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".opencode").exists():
            return True
    return False
