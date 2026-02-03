# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Pydantic models for command specifications."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Argument(BaseModel):
    """A positional argument for a command."""

    name: str
    description: str
    required: bool = True


class Option(BaseModel):
    """An optional flag/parameter for a command."""

    name: str
    short: str | None = None
    description: str
    choices: list[str] | None = None
    default: Any = None
    value_name: str | None = None  # e.g., "<id>" for --id <id>


class PlatformOverride(BaseModel):
    """Platform-specific overrides for a command."""

    name: str | None = None  # Different command name (e.g., please-remember)
    execution: str | None = None  # Different execution command
    description: str | None = None  # Different short description
    skip: bool = False  # Don't generate for this platform


class CommandSpec(BaseModel):
    """Specification for a command that generates platform-specific docs."""

    name: str
    description: str  # Short description for frontmatter
    detailed_description: str  # Full description in body

    arguments: list[Argument] = Field(default_factory=list)
    options: list[Option] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)

    execution: str  # e.g., "uv run anima remember"
    output_message: str | None = None  # For OpenCode: message after command

    # Additional sections (raw markdown)
    extra_sections: dict[str, str] = Field(default_factory=dict)

    # Platform-specific overrides
    platforms: dict[str, PlatformOverride] = Field(default_factory=dict)

    def get_name(self, platform: str) -> str:
        """Get command name for platform (may be overridden)."""
        if platform in self.platforms:
            override_name = self.platforms[platform].name
            if override_name is not None:
                return override_name
        return self.name

    def get_execution(self, platform: str) -> str:
        """Get execution command for platform."""
        if platform in self.platforms:
            override_exec = self.platforms[platform].execution
            if override_exec is not None:
                return override_exec
        # Antigravity uses python -m syntax
        if platform == "antigravity":
            # Convert "uv run anima X" to "uv run python -m anima.commands.X"
            if self.execution.startswith("uv run anima "):
                cmd = self.execution.replace("uv run anima ", "")
                return f"uv run python -m anima.commands.{cmd}"
        return self.execution

    def get_description(self, platform: str) -> str:
        """Get short description for platform."""
        if platform in self.platforms:
            override_desc = self.platforms[platform].description
            if override_desc is not None:
                return override_desc
        return self.description

    def should_skip(self, platform: str) -> bool:
        """Check if this command should be skipped for platform."""
        if platform in self.platforms:
            return self.platforms[platform].skip
        return False
