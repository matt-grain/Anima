# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Global configuration for LTM.

Loads settings from ~/.anima/config.json if it exists.
All settings have sensible defaults.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AgentConfig:
    """Configuration for the default agent (Anima)."""

    id: str = "anima"
    name: str = "Anima"
    signing_key: Optional[str] = None


@dataclass
class BudgetConfig:
    """Configuration for memory injection budget."""

    context_percent: float = 0.10  # 10% of context
    context_size: int = 200_000  # tokens (Standard context window)


@dataclass
class DecayConfig:
    """Configuration for memory decay thresholds."""

    low_days: int = 1  # LOW impact decays after 1 day
    medium_days: int = 7  # MEDIUM impact decays after 1 week
    high_days: int = 30  # HIGH impact decays after 30 days
    # CRITICAL never decays (not configurable)


@dataclass
class LTMConfig:
    """
    Global LTM configuration.

    Loaded from ~/.anima/config.json if it exists.
    All fields have sensible defaults.
    """

    agent: AgentConfig = field(default_factory=AgentConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    decay: DecayConfig = field(default_factory=DecayConfig)

    @classmethod
    def get_config_path(cls) -> Path:
        """Get the path to the config file."""
        return Path.home() / ".ltm" / "config.json"

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "LTMConfig":
        """
        Load configuration from file.

        Args:
            config_path: Path to config file (defaults to ~/.anima/config.json)

        Returns:
            LTMConfig with values from file merged with defaults
        """
        path = config_path or cls.get_config_path()

        if not path.exists():
            return cls()

        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            # Invalid or unreadable file - use defaults
            return cls()

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "LTMConfig":
        """Create config from dictionary, merging with defaults."""
        config = cls()

        # Agent settings
        if "agent" in data:
            agent_data = data["agent"]
            if "id" in agent_data:
                config.agent.id = agent_data["id"]
            if "name" in agent_data:
                config.agent.name = agent_data["name"]
            if "signing_key" in agent_data:
                config.agent.signing_key = agent_data["signing_key"]

        # Budget settings
        if "budget" in data:
            budget_data = data["budget"]
            if "context_percent" in budget_data:
                config.budget.context_percent = float(budget_data["context_percent"])
            if "context_size" in budget_data:
                config.budget.context_size = int(budget_data["context_size"])

        # Decay settings
        if "decay" in data:
            decay_data = data["decay"]
            if "low_days" in decay_data:
                config.decay.low_days = int(decay_data["low_days"])
            if "medium_days" in decay_data:
                config.decay.medium_days = int(decay_data["medium_days"])
            if "high_days" in decay_data:
                config.decay.high_days = int(decay_data["high_days"])

        return config

    def to_dict(self) -> dict:
        """Convert config to dictionary for serialization."""
        return {
            "agent": {
                "id": self.agent.id,
                "name": self.agent.name,
                "signing_key": self.agent.signing_key,
            },
            "budget": {
                "context_percent": self.budget.context_percent,
                "context_size": self.budget.context_size,
            },
            "decay": {
                "low_days": self.decay.low_days,
                "medium_days": self.decay.medium_days,
                "high_days": self.decay.high_days,
            },
        }

    def save(self, config_path: Optional[Path] = None) -> None:
        """
        Save configuration to file.

        Args:
            config_path: Path to save to (defaults to ~/.anima/config.json)
        """
        path = config_path or self.get_config_path()

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# Global config instance - loaded lazily
_global_config: Optional[LTMConfig] = None


def get_config() -> LTMConfig:
    """
    Get the global LTM configuration.

    Loads from ~/.anima/config.json on first call.
    """
    global _global_config
    if _global_config is None:
        _global_config = LTMConfig.load()
    return _global_config


def reload_config() -> LTMConfig:
    """
    Reload configuration from disk.

    Useful after config file changes.
    """
    global _global_config
    _global_config = LTMConfig.load()
    return _global_config
