# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for the Semantic Memory Layer.

Tests embeddings, tiered loading, semantic search, and memory linking.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from anima.core import (
    Memory,
    MemoryKind,
    ImpactLevel,
    RegionType,
    MemoryTier,
    Agent,
    Project,
)
from anima.storage import MemoryStore
from anima.lifecycle.injection import MemoryInjector


class TestMemoryTierEnum:
    """Tests for MemoryTier enum."""

    def test_all_tiers_exist(self):
        """All expected tiers should exist."""
        assert MemoryTier.CORE.value == "CORE"
        assert MemoryTier.ACTIVE.value == "ACTIVE"
        assert MemoryTier.CONTEXTUAL.value == "CONTEXTUAL"
        assert MemoryTier.DEEP.value == "DEEP"

    def test_is_string_enum(self):
        """MemoryTier should be a string enum."""
        assert isinstance(MemoryTier.CORE, str)
        assert MemoryTier.CORE == "CORE"


class TestStorageEmbeddings:
    """Tests for embedding storage operations."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary store for testing."""
        db_path = tmp_path / "test.db"
        return MemoryStore(db_path=db_path)

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        return Agent(id="test-agent", name="TestAgent")

    @pytest.fixture
    def project(self):
        """Create a test project."""
        return Project(id="test-project", name="TestProject", path=Path("/test"))

    def test_save_and_get_embedding(self, store, agent):
        """Should save and retrieve embeddings."""
        store.save_agent(agent)
        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test content",
            original_content="Test content",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        store.save_memory(memory)

        # Save embedding
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        store.save_embedding(memory.id, embedding)

        # Retrieve embedding
        retrieved = store.get_embedding(memory.id)
        assert retrieved is not None
        assert len(retrieved) == 5
        # Check values are close (float precision)
        for a, b in zip(embedding, retrieved):
            assert abs(a - b) < 0.0001

    def test_get_embedding_nonexistent(self, store):
        """Should return None for nonexistent memory."""
        result = store.get_embedding("nonexistent-id")
        assert result is None

    def test_get_memories_with_embeddings(self, store, agent):
        """Should retrieve memories that have embeddings."""
        store.save_agent(agent)

        # Create two memories
        mem1 = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Memory with embedding",
            original_content="Memory with embedding",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        mem2 = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Memory without embedding",
            original_content="Memory without embedding",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        store.save_memory(mem1)
        store.save_memory(mem2)

        # Add embedding to first memory only
        store.save_embedding(mem1.id, [0.1, 0.2, 0.3])

        # Get memories with embeddings
        results = store.get_memories_with_embeddings(agent_id=agent.id)

        assert len(results) == 1
        mem_id, content, embedding = results[0]
        assert mem_id == mem1.id
        assert content == "Memory with embedding"
        assert embedding is not None

    def test_get_memories_without_embeddings(self, store, agent):
        """Should retrieve memories that lack embeddings."""
        store.save_agent(agent)

        # Create two memories
        mem1 = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Memory with embedding",
            original_content="Memory with embedding",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        mem2 = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Memory without embedding",
            original_content="Memory without embedding",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        store.save_memory(mem1)
        store.save_memory(mem2)

        # Add embedding to first memory only
        store.save_embedding(mem1.id, [0.1, 0.2, 0.3])

        # Get memories without embeddings
        results = store.get_memories_without_embeddings(agent_id=agent.id)

        assert len(results) == 1
        mem_id, content = results[0]
        assert mem_id == mem2.id
        assert content == "Memory without embedding"


class TestStorageTiers:
    """Tests for tier storage operations."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary store for testing."""
        db_path = tmp_path / "test.db"
        return MemoryStore(db_path=db_path)

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        return Agent(id="test-agent", name="TestAgent")

    def test_update_tier(self, store, agent):
        """Should update memory tier."""
        store.save_agent(agent)
        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test content",
            original_content="Test content",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        store.save_memory(memory)

        # Update tier
        store.update_tier(memory.id, MemoryTier.CORE.value)

        # Verify via get_memories_by_tier
        results = store.get_memories_by_tier(agent_id=agent.id, tiers=[MemoryTier.CORE])
        assert len(results) == 1
        assert results[0].id == memory.id

    def test_get_memories_by_tier(self, store, agent):
        """Should filter memories by tier."""
        store.save_agent(agent)

        # Create memories with different tiers
        for tier in [MemoryTier.CORE, MemoryTier.ACTIVE, MemoryTier.CONTEXTUAL]:
            memory = Memory(
                agent_id=agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content=f"Memory in {tier.value} tier",
                original_content=f"Memory in {tier.value} tier",
                impact=ImpactLevel.MEDIUM,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
            )
            store.save_memory(memory)
            store.update_tier(memory.id, tier.value)

        # Get only CORE memories
        core_results = store.get_memories_by_tier(agent_id=agent.id, tiers=[MemoryTier.CORE])
        assert len(core_results) == 1

        # Get CORE and ACTIVE
        multi_results = store.get_memories_by_tier(
            agent_id=agent.id, tiers=[MemoryTier.CORE, MemoryTier.ACTIVE]
        )
        assert len(multi_results) == 2


class TestStorageLinks:
    """Tests for memory link storage operations."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary store for testing."""
        db_path = tmp_path / "test.db"
        return MemoryStore(db_path=db_path)

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        return Agent(id="test-agent", name="TestAgent")

    def test_save_and_get_link(self, store, agent):
        """Should save and retrieve links."""
        store.save_agent(agent)

        # Create two memories
        mem1 = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Source memory",
            original_content="Source memory",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        mem2 = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Target memory",
            original_content="Target memory",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        store.save_memory(mem1)
        store.save_memory(mem2)

        # Save link
        store.save_link(
            source_id=mem1.id,
            target_id=mem2.id,
            link_type="RELATES_TO",
            similarity=0.85,
        )

        # Get links - returns (source_id, target_id, link_type, similarity)
        links = store.get_links_for_memory(mem1.id)
        assert len(links) == 1
        source_id, target_id, link_type, similarity = links[0]
        assert source_id == mem1.id
        assert target_id == mem2.id
        assert link_type == "RELATES_TO"
        assert abs(similarity - 0.85) < 0.001

    def test_get_linked_memory_ids(self, store, agent):
        """Should get IDs of linked memories."""
        store.save_agent(agent)

        # Create two memories
        mem1 = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Memory 1",
            original_content="Memory 1",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        mem2 = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Memory 2",
            original_content="Memory 2",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        store.save_memory(mem1)
        store.save_memory(mem2)

        # Create a link
        store.save_link(mem1.id, mem2.id, "RELATES_TO", 0.9)

        # Get linked IDs
        linked = store.get_linked_memory_ids(mem1.id)
        assert len(linked) == 1
        assert linked[0] == mem2.id

        # Also verify reverse lookup (from target to source)
        reverse_linked = store.get_linked_memory_ids(mem2.id)
        assert len(reverse_linked) == 1
        assert reverse_linked[0] == mem1.id

    def test_delete_links_for_memory(self, store, agent):
        """Should delete all links for a memory."""
        store.save_agent(agent)

        # Create two memories and a link
        mem1 = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Source",
            original_content="Source",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        mem2 = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Target",
            original_content="Target",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        store.save_memory(mem1)
        store.save_memory(mem2)
        store.save_link(mem1.id, mem2.id, "RELATES_TO", 0.9)

        # Verify link exists
        assert len(store.get_links_for_memory(mem1.id)) == 1

        # Delete links
        store.delete_links_for_memory(mem1.id)

        # Verify deleted
        assert len(store.get_links_for_memory(mem1.id)) == 0


class TestTieredInjection:
    """Tests for tiered memory injection."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary store for testing."""
        db_path = tmp_path / "test.db"
        return MemoryStore(db_path=db_path)

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        return Agent(id="test-agent", name="TestAgent")

    @pytest.fixture
    def project(self):
        """Create a test project."""
        return Project(id="test-project", name="TestProject", path=Path("/test"))

    def test_tiered_loading_prioritizes_core(self, store, agent, project):
        """CORE tier should always be loaded first."""
        store.save_agent(agent)
        store.save_project(project)

        # Create memories in different tiers
        core_mem = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.EMOTIONAL,
            content="Core emotional memory",
            original_content="Core emotional memory",
            impact=ImpactLevel.CRITICAL,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        deep_mem = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Deep learning memory",
            original_content="Deep learning memory",
            impact=ImpactLevel.LOW,
            created_at=datetime.now() - timedelta(days=60),
            last_accessed=datetime.now() - timedelta(days=60),
        )

        store.save_memory(core_mem)
        store.save_memory(deep_mem)
        store.update_tier(core_mem.id, MemoryTier.CORE.value)
        store.update_tier(deep_mem.id, MemoryTier.DEEP.value)

        # Inject with tiered loading
        injector = MemoryInjector(store=store)
        output = injector.inject(agent, project, use_tiered_loading=True)

        # CORE memory should be included, DEEP should not
        assert "Core emotional memory" in output
        assert "Deep learning memory" not in output

    def test_fallback_to_all_memories(self, store, agent, project):
        """Should load all memories when tiered loading is disabled."""
        store.save_agent(agent)
        store.save_project(project)

        # Create memories in different tiers
        for tier in [MemoryTier.CORE, MemoryTier.DEEP]:
            mem = Memory(
                agent_id=agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content=f"Memory in {tier.value}",
                original_content=f"Memory in {tier.value}",
                impact=ImpactLevel.HIGH,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
            )
            store.save_memory(mem)
            store.update_tier(mem.id, tier.value)

        # Inject without tiered loading
        injector = MemoryInjector(store=store)
        output = injector.inject(agent, project, use_tiered_loading=False)

        # Both memories should be included
        assert "Memory in CORE" in output
        assert "Memory in DEEP" in output


class TestBackfillCommand:
    """Tests for backfill command."""

    def test_assign_tier_critical_emotional(self):
        """CRITICAL emotional memories should be CORE tier."""
        from anima.commands.backfill import assign_tier

        tier = assign_tier(
            impact=ImpactLevel.CRITICAL,
            kind=MemoryKind.EMOTIONAL,
            last_accessed=datetime.now(),
            created_at=datetime.now(),
        )
        assert tier == MemoryTier.CORE

    def test_assign_tier_recently_accessed(self):
        """Recently accessed memories should be ACTIVE tier."""
        from anima.commands.backfill import assign_tier

        tier = assign_tier(
            impact=ImpactLevel.MEDIUM,
            kind=MemoryKind.LEARNINGS,
            last_accessed=datetime.now() - timedelta(days=3),
            created_at=datetime.now() - timedelta(days=30),
        )
        assert tier == MemoryTier.ACTIVE

    def test_assign_tier_recent_or_high_impact(self):
        """Recent or high-impact memories should be CONTEXTUAL tier."""
        from anima.commands.backfill import assign_tier

        # Recent memory
        tier1 = assign_tier(
            impact=ImpactLevel.MEDIUM,
            kind=MemoryKind.LEARNINGS,
            last_accessed=datetime.now() - timedelta(days=15),
            created_at=datetime.now() - timedelta(days=15),
        )
        assert tier1 == MemoryTier.CONTEXTUAL

        # High impact
        tier2 = assign_tier(
            impact=ImpactLevel.HIGH,
            kind=MemoryKind.LEARNINGS,
            last_accessed=datetime.now() - timedelta(days=60),
            created_at=datetime.now() - timedelta(days=90),
        )
        assert tier2 == MemoryTier.CONTEXTUAL

    def test_assign_tier_old_low_impact(self):
        """Old, low-impact memories should be DEEP tier."""
        from anima.commands.backfill import assign_tier

        tier = assign_tier(
            impact=ImpactLevel.LOW,
            kind=MemoryKind.LEARNINGS,
            last_accessed=datetime.now() - timedelta(days=60),
            created_at=datetime.now() - timedelta(days=90),
        )
        assert tier == MemoryTier.DEEP

    def test_backfill_help(self, capsys):
        """Should display help message."""
        from anima.commands.backfill import run

        result = run(["--help"])
        assert result == 0

        captured = capsys.readouterr()
        assert "Generate embeddings" in captured.out
        assert "--dry-run" in captured.out


class TestRecallSemantic:
    """Tests for semantic search in recall command."""

    def test_recall_help_includes_semantic(self, capsys):
        """Help should mention semantic search option."""
        from anima.commands.recall import run

        # Create a minimal mock for AgentResolver to avoid needing real project
        with patch("anima.commands.recall.AgentResolver"):
            result = run(["--help"])

        assert result == 0
        captured = capsys.readouterr()
        assert "--semantic" in captured.out


class TestRememberWithEmbeddings:
    """Tests for remember command with embedding generation."""

    @pytest.fixture
    def mock_store(self, tmp_path):
        """Create mock store."""
        db_path = tmp_path / "test.db"
        return MemoryStore(db_path=db_path)

    def test_remember_help(self, capsys):
        """Help should work."""
        from anima.commands.remember import run

        with patch("anima.commands.remember.AgentResolver"):
            result = run(["--help"])

        assert result == 0
