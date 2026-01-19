# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for the sign_memories tool.
"""

import json
from pathlib import Path

import pytest

from anima.core import (
    Agent,
    Memory,
    MemoryKind,
    RegionType,
    ImpactLevel,
    sign_memory,
    verify_signature,
    LTMConfig,
    reload_config,
)
from anima.storage import MemoryStore
from anima.tools.sign_memories import run


class TestSignMemoriesTool:
    """Tests for the sign_memories tool."""

    @pytest.fixture
    def configured_env(self, tmp_path: Path, monkeypatch):
        """Set up environment with signing key configured."""
        # Create config with signing key
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "agent": {
                        "id": "test-agent",
                        "name": "TestAgent",
                        "signing_key": "test-secret-key-123",
                    }
                }
            )
        )

        monkeypatch.setattr(LTMConfig, "get_config_path", lambda: config_path)
        reload_config()

        # Create database
        db_path = tmp_path / "memories.db"
        store = MemoryStore(db_path=db_path)

        # Patch default DB path
        monkeypatch.setattr(
            "anima.tools.sign_memories.MemoryStore",
            lambda: MemoryStore(db_path=db_path),
        )

        # Patch Path.home() to avoid picking up global agent files
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # Create agent
        agent = Agent(id="test-agent", name="TestAgent", signing_key="test-secret-key-123")
        store.save_agent(agent)

        return store, agent, tmp_path

    def test_signs_unsigned_memories(self, configured_env, monkeypatch) -> None:
        """Unsigned memories get signed."""
        store, agent, tmp_path = configured_env

        # Patch cwd to tmp_path
        monkeypatch.chdir(tmp_path)

        # Create unsigned memory
        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test unsigned memory",
            impact=ImpactLevel.MEDIUM,
        )
        store.save_memory(memory)

        # Verify it's unsigned
        saved = store.get_memory(memory.id)
        assert saved.signature is None

        # Run tool
        result = run([])
        assert result == 0

        # Verify it's now signed
        signed = store.get_memory(memory.id)
        assert signed.signature is not None
        assert verify_signature(signed, agent.signing_key)

    def test_skips_already_signed_memories(self, configured_env, monkeypatch) -> None:
        """Already signed memories are not re-signed."""
        store, agent, tmp_path = configured_env
        monkeypatch.chdir(tmp_path)

        # Create and sign a memory
        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test already signed memory",
            impact=ImpactLevel.MEDIUM,
        )
        memory.signature = sign_memory(memory, agent.signing_key)
        original_signature = memory.signature
        store.save_memory(memory)

        # Run tool
        result = run([])
        assert result == 0

        # Verify signature unchanged
        after = store.get_memory(memory.id)
        assert after.signature == original_signature

    def test_cannot_resign_with_different_key(self, configured_env, monkeypatch) -> None:
        """Signed memories keep their original signature even if key changes."""
        store, agent, tmp_path = configured_env
        monkeypatch.chdir(tmp_path)

        # Create and sign a memory with original key
        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test memory signed with original key",
            impact=ImpactLevel.MEDIUM,
        )
        original_key = "original-secret-key"
        memory.signature = sign_memory(memory, original_key)
        original_signature = memory.signature
        store.save_memory(memory)

        # Config has different key ("test-secret-key-123")
        # Run tool - should skip this memory because it's already signed
        result = run([])
        assert result == 0

        # Verify signature is unchanged (NOT re-signed with new key)
        after = store.get_memory(memory.id)
        assert after.signature == original_signature

        # Verify original signature still valid with original key
        assert verify_signature(after, original_key)

        # Verify signature FAILS with new key (proves it wasn't re-signed)
        assert not verify_signature(after, "test-secret-key-123")

    def test_dry_run_does_not_modify(self, configured_env, monkeypatch) -> None:
        """Dry run shows what would be signed but doesn't change anything."""
        store, agent, tmp_path = configured_env
        monkeypatch.chdir(tmp_path)

        # Create unsigned memory
        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test dry run memory",
            impact=ImpactLevel.MEDIUM,
        )
        store.save_memory(memory)

        # Run with dry-run
        result = run(["--dry-run"])
        assert result == 0

        # Verify still unsigned
        after = store.get_memory(memory.id)
        assert after.signature is None

    def test_fails_without_signing_key(self, tmp_path: Path, monkeypatch) -> None:
        """Tool fails if no signing key is configured."""
        # Config without signing key
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "agent": {"id": "test-agent", "name": "TestAgent"}
                    # No signing_key
                }
            )
        )

        monkeypatch.setattr(LTMConfig, "get_config_path", lambda: config_path)
        reload_config()
        monkeypatch.chdir(tmp_path)

        result = run([])
        assert result == 1  # Should fail


class TestSignatureImmutability:
    """Tests ensuring signatures cannot be overwritten."""

    def test_signature_protects_memory_integrity(self) -> None:
        """A signed memory's signature proves it hasn't been tampered with."""
        memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Original content",
            impact=ImpactLevel.MEDIUM,
        )

        key = "my-secret-key"
        memory.signature = sign_memory(memory, key)

        # Verify original
        assert verify_signature(memory, key)

        # Tamper with content
        memory.content = "Tampered content"

        # Signature now invalid (content is in payload via original_content)
        # Note: content can change (compaction), but original_content cannot
        # So this test checks that original_content is protected
        original = Memory(
            id=memory.id,
            agent_id=memory.agent_id,
            region=memory.region,
            kind=memory.kind,
            content="Tampered",
            original_content="Tampered original",  # This would break signature
            impact=memory.impact,
            created_at=memory.created_at,
            signature=memory.signature,
        )

        # This should fail because original_content changed
        assert not verify_signature(original, key)

    def test_only_original_content_in_signature(self) -> None:
        """Compacted content doesn't affect signature (original_content is signed)."""
        memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="I think this is a very verbose learning that will be compacted",
            impact=ImpactLevel.LOW,
        )

        key = "my-secret-key"
        memory.signature = sign_memory(memory, key)

        # Compact the content (simulating decay)
        memory.content = "This is a compacted learning"

        # Signature still valid because original_content unchanged
        assert verify_signature(memory, key)
