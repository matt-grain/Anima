# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for LTM memory decay and compaction.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from anima.core import Agent, Memory, MemoryKind, Project, RegionType, ImpactLevel
from anima.lifecycle.decay import MemoryDecay
from anima.storage import MemoryStore


class TestDecayThresholds:
    """Tests for decay threshold logic."""

    def test_critical_never_decays(self, temp_db_path: Path) -> None:
        """Test that CRITICAL memories never decay."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.ARCHITECTURAL,
            content="Critical architecture decision",
            impact=ImpactLevel.CRITICAL,
            created_at=datetime.now() - timedelta(days=365),  # Very old
        )

        assert not decay.should_compact(memory)

    def test_low_impact_decays_after_one_day(self, temp_db_path: Path) -> None:
        """Test that LOW impact memories decay after 1 day."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        # Memory from 2 days ago
        old_memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Minor learning",
            impact=ImpactLevel.LOW,
            created_at=datetime.now() - timedelta(days=2),
        )

        # Memory from 12 hours ago
        recent_memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Recent learning",
            impact=ImpactLevel.LOW,
            created_at=datetime.now() - timedelta(hours=12),
        )

        assert decay.should_compact(old_memory)
        assert not decay.should_compact(recent_memory)

    def test_medium_impact_decays_after_one_week(self, temp_db_path: Path) -> None:
        """Test that MEDIUM impact memories decay after 1 week."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        # Memory from 10 days ago
        old_memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Medium importance learning",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now() - timedelta(days=10),
        )

        # Memory from 3 days ago
        recent_memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Recent medium learning",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now() - timedelta(days=3),
        )

        assert decay.should_compact(old_memory)
        assert not decay.should_compact(recent_memory)

    def test_high_impact_decays_after_one_month(self, temp_db_path: Path) -> None:
        """Test that HIGH impact memories decay after 1 month."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        # Memory from 60 days ago
        old_memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.ARCHITECTURAL,
            content="High importance architecture",
            impact=ImpactLevel.HIGH,
            created_at=datetime.now() - timedelta(days=60),
        )

        # Memory from 15 days ago
        recent_memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.ARCHITECTURAL,
            content="Recent high importance",
            impact=ImpactLevel.HIGH,
            created_at=datetime.now() - timedelta(days=15),
        )

        assert decay.should_compact(old_memory)
        assert not decay.should_compact(recent_memory)

    def test_timezone_aware_memory_handled(self, temp_db_path: Path) -> None:
        """Test that timezone-aware memories are handled correctly."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        # Memory with timezone-aware datetime (as might be stored by some code paths)
        tz_aware_memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Timezone aware learning",
            impact=ImpactLevel.LOW,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )

        # Should not raise TypeError when comparing with naive datetime
        result = decay.should_compact(tz_aware_memory)
        assert result is True  # Old enough to compact

    def test_mixed_timezone_naive_memories(self, temp_db_path: Path) -> None:
        """Test decay works with mix of naive and aware datetimes."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        # Naive datetime memory
        naive_memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Naive datetime memory",
            impact=ImpactLevel.LOW,
            created_at=datetime.now() - timedelta(days=2),
        )

        # Timezone-aware memory (e.g., +01:00 offset)
        aware_memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Aware datetime memory",
            impact=ImpactLevel.LOW,
            created_at=datetime.now(timezone(timedelta(hours=1))) - timedelta(days=2),
        )

        # Both should work without raising errors
        assert decay.should_compact(naive_memory) is True
        assert decay.should_compact(aware_memory) is True


class TestCompaction:
    """Tests for memory compaction logic."""

    def test_short_content_not_compacted(self, temp_db_path: Path) -> None:
        """Test that short content is not compacted further."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Short",
            impact=ImpactLevel.LOW,
        )

        result = decay.compact_content(memory)
        assert result == "Short"

    def test_filler_phrases_removed(self, temp_db_path: Path) -> None:
        """Test that filler phrases are removed during compaction."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="I think we should use pytest. I believe it's the best choice.",
            impact=ImpactLevel.LOW,
        )

        result = decay.compact_content(memory)
        assert "I think " not in result
        assert "I believe " not in result
        assert "pytest" in result

    def test_long_content_truncated(self, temp_db_path: Path) -> None:
        """Test that very long content is truncated."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        long_content = "First sentence here. " + "Middle content. " * 50 + "Last sentence here."
        memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content=long_content,
            impact=ImpactLevel.LOW,
        )

        result = decay.compact_content(memory)
        assert len(result) <= 250  # Should be significantly shorter
        assert "First sentence here" in result
        assert "Last sentence here" in result


class TestProcessDecay:
    """Tests for the full decay process."""

    def test_process_decay_updates_memories(self, temp_db_path: Path) -> None:
        """Test that process_decay updates old memories."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        # Setup agent
        agent = Agent(id="test-agent", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        project = Project(id="test-proj", name="Test", path=Path("/tmp/test"))
        store.save_project(project)

        # Create an old LOW impact memory with verbose content
        old_memory = Memory(
            agent_id=agent.id,
            region=RegionType.PROJECT,
            project_id=project.id,
            kind=MemoryKind.LEARNINGS,
            content="I think we discussed this at length. After investigation we found that pytest is the best framework for testing.",
            impact=ImpactLevel.LOW,
            created_at=datetime.now() - timedelta(days=5),  # Old enough to decay
        )
        store.save_memory(old_memory)

        # Process decay
        compacted = decay.process_decay(agent_id=agent.id, project_id=project.id)

        assert len(compacted) == 1
        assert compacted[0][0].id == old_memory.id

        # Verify the memory was updated in the store
        updated = store.get_memory(old_memory.id)
        assert updated is not None
        assert "I think " not in updated.content
        assert "After investigation " not in updated.content

    def test_process_decay_dry_run(self, temp_db_path: Path) -> None:
        """Test that dry_run doesn't actually update memories."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        agent = Agent(id="test-agent", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        project = Project(id="test-proj", name="Test", path=Path("/tmp/test"))
        store.save_project(project)

        original_content = "I think we should use pytest for all our tests."
        old_memory = Memory(
            agent_id=agent.id,
            region=RegionType.PROJECT,
            project_id=project.id,
            kind=MemoryKind.LEARNINGS,
            content=original_content,
            impact=ImpactLevel.LOW,
            created_at=datetime.now() - timedelta(days=5),
        )
        store.save_memory(old_memory)

        # Process with dry_run=True
        compacted = decay.process_decay(agent_id=agent.id, project_id=project.id, dry_run=True)

        assert len(compacted) == 1

        # Verify the memory was NOT updated in the store
        unchanged = store.get_memory(old_memory.id)
        assert unchanged is not None
        assert unchanged.content == original_content

    def test_process_decay_skips_critical(self, temp_db_path: Path) -> None:
        """Test that CRITICAL memories are never processed."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        agent = Agent(id="test-agent", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        project = Project(id="test-proj", name="Test", path=Path("/tmp/test"))
        store.save_project(project)

        critical_memory = Memory(
            agent_id=agent.id,
            region=RegionType.PROJECT,
            project_id=project.id,
            kind=MemoryKind.ARCHITECTURAL,
            content="I think this is a crucial architecture decision that must never be forgotten.",
            impact=ImpactLevel.CRITICAL,
            created_at=datetime.now() - timedelta(days=365),  # Very old
        )
        store.save_memory(critical_memory)

        compacted = decay.process_decay(agent_id=agent.id, project_id=project.id)

        assert len(compacted) == 0


class TestDeleteEmptyMemories:
    """Tests for deleting empty/superseded memories."""

    def test_delete_superseded_empty_memories(self, temp_db_path: Path) -> None:
        """Test that superseded memories with minimal content are deleted."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        agent = Agent(id="test-agent", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        # Create a superseded memory with very short content
        superseded = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="x",  # Shorter than MIN_CONTENT_LENGTH
            superseded_by="some-other-id",
        )
        store.save_memory(superseded)

        deleted_count = decay.delete_empty_memories(agent.id)

        assert deleted_count == 1
        assert store.get_memory(superseded.id) is None

    def test_keep_non_superseded_memories(self, temp_db_path: Path) -> None:
        """Test that non-superseded memories are kept even if short."""
        store = MemoryStore(db_path=temp_db_path)
        decay = MemoryDecay(store)

        agent = Agent(id="test-agent", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        # Create a non-superseded memory with short content
        short_memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="x",  # Short but not superseded
        )
        store.save_memory(short_memory)

        deleted_count = decay.delete_empty_memories(agent.id)

        assert deleted_count == 0
        assert store.get_memory(short_memory.id) is not None
