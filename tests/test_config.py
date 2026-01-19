# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for LTM configuration.
"""

import json
from pathlib import Path


from anima.core.config import LTMConfig, get_config, reload_config


class TestConfigDefaults:
    """Tests for default configuration values."""

    def test_default_agent_config(self) -> None:
        """Test default agent configuration."""
        config = LTMConfig()
        assert config.agent.id == "anima"
        assert config.agent.name == "Anima"
        assert config.agent.signing_key is None

    def test_default_budget_config(self) -> None:
        """Test default budget configuration."""
        config = LTMConfig()
        assert config.budget.context_percent == 0.10
        assert config.budget.context_size == 200_000

    def test_default_decay_config(self) -> None:
        """Test default decay configuration."""
        config = LTMConfig()
        assert config.decay.low_days == 1
        assert config.decay.medium_days == 7
        assert config.decay.high_days == 30


class TestConfigLoading:
    """Tests for loading configuration from file."""

    def test_load_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        """Loading from non-existent file returns defaults."""
        config = LTMConfig.load(tmp_path / "nonexistent.json")
        assert config.agent.id == "anima"
        assert config.budget.context_percent == 0.10

    def test_load_empty_file_returns_defaults(self, tmp_path: Path) -> None:
        """Loading from empty JSON object returns defaults."""
        config_path = tmp_path / "config.json"
        config_path.write_text("{}")

        config = LTMConfig.load(config_path)
        assert config.agent.id == "anima"
        assert config.budget.context_percent == 0.10

    def test_load_partial_config(self, tmp_path: Path) -> None:
        """Partial config merges with defaults."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"agent": {"signing_key": "my-secret-key"}}))

        config = LTMConfig.load(config_path)
        # Custom value
        assert config.agent.signing_key == "my-secret-key"
        # Default values preserved
        assert config.agent.id == "anima"
        assert config.agent.name == "Anima"
        assert config.budget.context_percent == 0.10

    def test_load_full_config(self, tmp_path: Path) -> None:
        """Full config overrides all defaults."""
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "agent": {
                        "id": "custom-agent",
                        "name": "CustomName",
                        "signing_key": "secret123",
                    },
                    "budget": {"context_percent": 0.15, "context_size": 500000},
                    "decay": {"low_days": 2, "medium_days": 14, "high_days": 60},
                }
            )
        )

        config = LTMConfig.load(config_path)
        assert config.agent.id == "custom-agent"
        assert config.agent.name == "CustomName"
        assert config.agent.signing_key == "secret123"
        assert config.budget.context_percent == 0.15
        assert config.budget.context_size == 500000
        assert config.decay.low_days == 2
        assert config.decay.medium_days == 14
        assert config.decay.high_days == 60

    def test_load_invalid_json_returns_defaults(self, tmp_path: Path) -> None:
        """Invalid JSON file returns defaults."""
        config_path = tmp_path / "config.json"
        config_path.write_text("not valid json {{{")

        config = LTMConfig.load(config_path)
        assert config.agent.id == "anima"


class TestConfigSerialization:
    """Tests for saving configuration."""

    def test_to_dict(self) -> None:
        """Config converts to dictionary correctly."""
        config = LTMConfig()
        config.agent.signing_key = "test-key"

        data = config.to_dict()
        assert data["agent"]["id"] == "anima"
        assert data["agent"]["signing_key"] == "test-key"
        assert data["budget"]["context_percent"] == 0.10
        assert data["decay"]["low_days"] == 1

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Config survives save/load roundtrip."""
        config_path = tmp_path / "config.json"

        # Create custom config
        config = LTMConfig()
        config.agent.id = "my-agent"
        config.agent.signing_key = "secret"
        config.budget.context_percent = 0.20
        config.decay.high_days = 45

        # Save
        config.save(config_path)

        # Load
        loaded = LTMConfig.load(config_path)
        assert loaded.agent.id == "my-agent"
        assert loaded.agent.signing_key == "secret"
        assert loaded.budget.context_percent == 0.20
        assert loaded.decay.high_days == 45


class TestGlobalConfig:
    """Tests for global config access."""

    def test_get_config_returns_instance(self) -> None:
        """get_config returns an LTMConfig instance."""
        config = get_config()
        assert isinstance(config, LTMConfig)

    def test_reload_config_refreshes(self, tmp_path: Path, monkeypatch) -> None:
        """reload_config reads fresh values from disk."""
        config_path = tmp_path / "config.json"

        # Patch the config path
        monkeypatch.setattr(LTMConfig, "get_config_path", lambda: config_path)

        # Start with no config file
        reload_config()
        config = get_config()
        assert config.agent.signing_key is None

        # Create config file
        config_path.write_text(json.dumps({"agent": {"signing_key": "new-key"}}))

        # Reload
        reload_config()
        config = get_config()
        assert config.agent.signing_key == "new-key"


class TestConfigIntegration:
    """Integration tests with other LTM components."""

    def test_agent_resolver_uses_config(self, tmp_path: Path, monkeypatch) -> None:
        """AgentResolver uses config for default agent."""
        from anima.core.agent import AgentResolver

        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "agent": {
                        "id": "custom-soul",
                        "name": "MySoul",
                        "signing_key": "soul-key",
                    }
                }
            )
        )

        # Patch config path and reload
        monkeypatch.setattr(LTMConfig, "get_config_path", lambda: config_path)
        reload_config()

        # Patch Path.home() to avoid picking up global agent files
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # Resolve with no agent files - should use config
        resolver = AgentResolver(project_path=tmp_path)
        agent = resolver.resolve()

        assert agent.id == "custom-soul"
        assert agent.name == "MySoul"
        assert agent.signing_key == "soul-key"

    def test_injection_uses_config_budget(self, tmp_path: Path, monkeypatch) -> None:
        """Injection budget respects config."""
        from anima.lifecycle.injection import get_memory_budget

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"budget": {"context_percent": 0.20, "context_size": 100000}}))

        monkeypatch.setattr(LTMConfig, "get_config_path", lambda: config_path)
        reload_config()

        budget = get_memory_budget()
        assert budget == 20000  # 20% of 100k

    def test_decay_uses_config_thresholds(self, tmp_path: Path, monkeypatch) -> None:
        """Decay thresholds respect config."""
        from datetime import datetime, timedelta
        from anima.core import Memory, MemoryKind, RegionType, ImpactLevel
        from anima.lifecycle.decay import MemoryDecay
        from anima.storage import MemoryStore

        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "decay": {
                        "low_days": 5  # Changed from 1 to 5
                    }
                }
            )
        )

        monkeypatch.setattr(LTMConfig, "get_config_path", lambda: config_path)
        reload_config()

        db_path = tmp_path / "test.db"
        store = MemoryStore(db_path=db_path)
        decay = MemoryDecay(store)

        # Memory from 3 days ago - should NOT decay with 5-day threshold
        memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test content",
            impact=ImpactLevel.LOW,
            created_at=datetime.now() - timedelta(days=3),
        )

        # With default 1-day threshold, this would decay
        # With 5-day threshold, it should NOT decay
        assert not decay.should_compact(memory)

        # Memory from 6 days ago - should decay
        old_memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Old content",
            impact=ImpactLevel.LOW,
            created_at=datetime.now() - timedelta(days=6),
        )
        assert decay.should_compact(old_memory)
