# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for the keygen tool.
"""

from pathlib import Path

import pytest

from anima.core import Memory, MemoryKind, RegionType, ImpactLevel, verify_signature
from anima.storage import MemoryStore
from anima.tools.keygen import (
    run,
    find_agent_file,
    get_key_from_agent_file,
    add_key_to_agent_file,
    generate_key,
)


class TestGenerateKey:
    """Tests for key generation."""

    def test_generates_hex_string(self) -> None:
        """Generated key is a valid hex string."""
        key = generate_key()
        # Should be 64 chars (32 bytes * 2 for hex)
        assert len(key) == 64
        # Should be valid hex
        int(key, 16)

    def test_keys_are_unique(self) -> None:
        """Each generated key is unique."""
        keys = [generate_key() for _ in range(10)]
        assert len(set(keys)) == 10


class TestFindAgentFile:
    """Tests for finding agent files."""

    def test_finds_local_agent(self, tmp_path: Path, monkeypatch) -> None:
        """Finds agent in project .claude/agents/."""
        monkeypatch.chdir(tmp_path)

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text("---\nname: test-agent\n---\n")

        found, is_global = find_agent_file("test-agent")
        assert found == agent_file
        assert not is_global

    def test_finds_global_agent(self, tmp_path: Path, monkeypatch) -> None:
        """Finds agent in ~/.claude/agents/ when local doesn't exist."""
        monkeypatch.chdir(tmp_path)

        # Create global agents dir
        global_agents = tmp_path / "home_claude" / "agents"
        global_agents.mkdir(parents=True)
        agent_file = global_agents / "global-agent.md"
        agent_file.write_text("---\nname: global-agent\n---\n")

        # Patch Path.home()
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home_claude" / "..")

        # Actually need to patch properly for ~/.claude
        home_dir = tmp_path / "fake_home"
        home_dir.mkdir()
        (home_dir / ".claude" / "agents").mkdir(parents=True)
        (home_dir / ".claude" / "agents" / "global-agent.md").write_text("---\nname: global-agent\n---\n")
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        found, is_global = find_agent_file("global-agent")
        assert found is not None
        assert is_global

    def test_local_takes_priority(self, tmp_path: Path, monkeypatch) -> None:
        """Local agent file takes priority over global."""
        monkeypatch.chdir(tmp_path)

        # Create both local and global
        local_agents = tmp_path / ".claude" / "agents"
        local_agents.mkdir(parents=True)
        local_file = local_agents / "shared-agent.md"
        local_file.write_text("---\nname: shared-agent\nlocation: local\n---\n")

        home_dir = tmp_path / "fake_home"
        global_agents = home_dir / ".claude" / "agents"
        global_agents.mkdir(parents=True)
        global_file = global_agents / "shared-agent.md"
        global_file.write_text("---\nname: shared-agent\nlocation: global\n---\n")
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        found, is_global = find_agent_file("shared-agent")
        assert found == local_file
        assert not is_global

    def test_returns_none_when_not_found(self, tmp_path: Path, monkeypatch) -> None:
        """Returns None when agent file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        home_dir = tmp_path / "fake_home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        found, is_global = find_agent_file("nonexistent")
        assert found is None
        assert not is_global


class TestGetKeyFromAgentFile:
    """Tests for extracting signing key from agent files."""

    def test_extracts_quoted_key(self, tmp_path: Path) -> None:
        """Extracts key with double quotes."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text('---\nname: test\nsigning_key: "my-secret-key"\n---\n')

        key = get_key_from_agent_file(agent_file)
        assert key == "my-secret-key"

    def test_extracts_unquoted_key(self, tmp_path: Path) -> None:
        """Extracts key without quotes."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("---\nname: test\nsigning_key: my-secret-key\n---\n")

        key = get_key_from_agent_file(agent_file)
        assert key == "my-secret-key"

    def test_returns_none_without_key(self, tmp_path: Path) -> None:
        """Returns None when no signing key."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("---\nname: test\n---\n")

        key = get_key_from_agent_file(agent_file)
        assert key is None

    def test_returns_none_without_frontmatter(self, tmp_path: Path) -> None:
        """Returns None when no frontmatter."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("# Just a markdown file\n")

        key = get_key_from_agent_file(agent_file)
        assert key is None


class TestAddKeyToAgentFile:
    """Tests for adding signing key to agent files."""

    def test_adds_key_to_frontmatter(self, tmp_path: Path) -> None:
        """Adds signing_key to existing frontmatter."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("---\nname: test-agent\ncolor: blue\n---\n\n# Test Agent\n")

        add_key_to_agent_file(agent_file, "new-secret-key")

        content = agent_file.read_text()
        assert 'signing_key: "new-secret-key"' in content
        assert "name: test-agent" in content
        assert "# Test Agent" in content

    def test_preserves_body_content(self, tmp_path: Path) -> None:
        """Body content after frontmatter is preserved."""
        agent_file = tmp_path / "agent.md"
        original_body = "\n# Agent\n\nThis is the agent description.\n\n## Usage\n\nUse it wisely."
        agent_file.write_text(f"---\nname: test\n---\n{original_body}")

        add_key_to_agent_file(agent_file, "key123")

        content = agent_file.read_text()
        assert original_body in content


class TestKeygenCommand:
    """Tests for the keygen command."""

    @pytest.fixture
    def env_with_agent(self, tmp_path: Path, monkeypatch):
        """Set up environment with an agent file."""
        monkeypatch.chdir(tmp_path)

        # Create agent file
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "my-agent.md"
        agent_file.write_text("---\nname: my-agent\nmodel: sonnet\n---\n\n# My Agent\n")

        # Create database
        db_path = tmp_path / "memories.db"
        store = MemoryStore(db_path=db_path)

        # Patch default DB path
        monkeypatch.setattr("anima.tools.keygen.MemoryStore", lambda: MemoryStore(db_path=db_path))

        # Patch home to avoid global agent lookup issues
        home_dir = tmp_path / "fake_home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        return store, agent_file, tmp_path

    def test_generates_key_for_agent(self, env_with_agent) -> None:
        """Generates and saves key for existing agent."""
        store, agent_file, tmp_path = env_with_agent

        result = run(["my-agent"])
        assert result == 0

        # Check key was added to file
        key = get_key_from_agent_file(agent_file)
        assert key is not None
        assert len(key) == 64  # hex key

        # Check agent was created in database
        agent = store.get_agent("my-agent")
        assert agent is not None
        assert agent.signing_key == key

    def test_signs_existing_memories(self, env_with_agent) -> None:
        """Signs any unsigned memories for the agent."""
        store, agent_file, tmp_path = env_with_agent

        # Create unsigned memory
        memory = Memory(
            agent_id="my-agent",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test memory to be signed",
            impact=ImpactLevel.MEDIUM,
        )
        store.save_memory(memory)

        # Verify unsigned
        saved = store.get_memory(memory.id)
        assert saved is not None
        assert saved.signature is None

        # Run keygen
        result = run(["my-agent"])
        assert result == 0

        # Get the key that was generated
        key = get_key_from_agent_file(agent_file)
        assert key is not None

        # Verify memory is now signed
        signed = store.get_memory(memory.id)
        assert signed is not None
        assert signed.signature is not None
        assert verify_signature(signed, key)

    def test_fails_if_agent_not_found(self, tmp_path: Path, monkeypatch) -> None:
        """Fails with error if agent file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        home_dir = tmp_path / "fake_home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        result = run(["nonexistent-agent"])
        assert result == 1

    def test_fails_if_key_already_exists(self, env_with_agent) -> None:
        """Fails if agent already has a signing key."""
        store, agent_file, tmp_path = env_with_agent

        # Add key to file
        add_key_to_agent_file(agent_file, "existing-key")

        result = run(["my-agent"])
        assert result == 1

    def test_shows_help_without_args(self, tmp_path: Path, monkeypatch) -> None:
        """Shows help when no agent name provided."""
        monkeypatch.chdir(tmp_path)

        result = run([])
        assert result == 1  # Help is shown, returns 1
