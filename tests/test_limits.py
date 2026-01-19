# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for LTM memory limits.
"""

import tempfile
from pathlib import Path

import pytest

from anima.core import (
    Agent,
    Memory,
    MemoryKind,
    Project,
    RegionType,
    MemoryLimits,
    MemoryLimitExceeded,
    DEFAULT_LIMITS,
    NO_LIMITS,
)
from anima.storage import MemoryStore


@pytest.fixture
def limited_store() -> MemoryStore:
    """Create a MemoryStore with strict limits for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    limits = MemoryLimits(
        max_memories_per_agent=5, max_memories_per_project=3, max_memories_per_kind=2
    )
    return MemoryStore(db_path=db_path, limits=limits)


@pytest.fixture
def test_agent() -> Agent:
    """Create a test agent."""
    return Agent(
        id="test-agent", name="Test Agent", definition_path=None, signing_key=None
    )


@pytest.fixture
def test_project() -> Project:
    """Create a test project."""
    return Project(
        id="test-project", name="Test Project", path=Path("/tmp/test-project")
    )


class TestMemoryLimits:
    """Tests for MemoryLimits dataclass."""

    def test_default_limits_have_values(self) -> None:
        """Test that DEFAULT_LIMITS has sensible values."""
        assert DEFAULT_LIMITS.max_memories_per_agent is not None
        assert DEFAULT_LIMITS.max_memories_per_agent > 0
        assert DEFAULT_LIMITS.max_memories_per_project is not None
        assert DEFAULT_LIMITS.max_memories_per_kind is not None

    def test_no_limits_are_none(self) -> None:
        """Test that NO_LIMITS has all None values."""
        assert NO_LIMITS.max_memories_per_agent is None
        assert NO_LIMITS.max_memories_per_project is None
        assert NO_LIMITS.max_memories_per_kind is None

    def test_custom_limits(self) -> None:
        """Test creating custom limits."""
        limits = MemoryLimits(
            max_memories_per_agent=100,
            max_memories_per_project=50,
            max_memories_per_kind=20,
        )
        assert limits.max_memories_per_agent == 100
        assert limits.max_memories_per_project == 50
        assert limits.max_memories_per_kind == 20


class TestMemoryLimitExceeded:
    """Tests for MemoryLimitExceeded exception."""

    def test_exception_message(self) -> None:
        """Test that the exception has a descriptive message."""
        exc = MemoryLimitExceeded("agent total", 100, 100)
        assert "agent total" in str(exc)
        assert "100" in str(exc)

    def test_exception_attributes(self) -> None:
        """Test that exception stores relevant data."""
        exc = MemoryLimitExceeded("project 'test'", 50, 50)
        assert exc.limit_type == "project 'test'"
        assert exc.current == 50
        assert exc.limit == 50


class TestStoreLimits:
    """Tests for MemoryStore limit enforcement."""

    def test_store_accepts_limits_in_constructor(
        self, limited_store: MemoryStore
    ) -> None:
        """Test that MemoryStore accepts limits parameter."""
        assert limited_store.limits.max_memories_per_agent == 5

    def test_agent_limit_enforced(
        self, limited_store: MemoryStore, test_agent: Agent
    ) -> None:
        """Test that agent-wide limit is enforced."""
        limited_store.save_agent(test_agent)

        # Add 5 memories (at the limit)
        for i in range(5):
            memory = Memory(
                agent_id=test_agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind(
                    ["EMOTIONAL", "ARCHITECTURAL", "LEARNINGS", "ACHIEVEMENTS"][i % 4]
                ),
                content=f"Memory {i}",
            )
            limited_store.save_memory(memory)

        # 6th should fail
        memory = Memory(
            agent_id=test_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="This should fail",
        )
        with pytest.raises(MemoryLimitExceeded) as exc_info:
            limited_store.save_memory(memory)

        assert "agent total" in str(exc_info.value)

    def test_project_limit_enforced(
        self, limited_store: MemoryStore, test_agent: Agent, test_project: Project
    ) -> None:
        """Test that per-project limit is enforced."""
        limited_store.save_agent(test_agent)
        limited_store.save_project(test_project)

        # Add 3 project memories (at the limit)
        for i in range(3):
            memory = Memory(
                agent_id=test_agent.id,
                region=RegionType.PROJECT,
                project_id=test_project.id,
                kind=MemoryKind(["EMOTIONAL", "ARCHITECTURAL", "LEARNINGS"][i]),
                content=f"Project memory {i}",
            )
            limited_store.save_memory(memory)

        # 4th should fail
        memory = Memory(
            agent_id=test_agent.id,
            region=RegionType.PROJECT,
            project_id=test_project.id,
            kind=MemoryKind.ACHIEVEMENTS,
            content="This should fail",
        )
        with pytest.raises(MemoryLimitExceeded) as exc_info:
            limited_store.save_memory(memory)

        assert "project" in str(exc_info.value)

    def test_kind_limit_enforced(
        self, limited_store: MemoryStore, test_agent: Agent
    ) -> None:
        """Test that per-kind limit is enforced."""
        limited_store.save_agent(test_agent)

        # Add 2 LEARNINGS memories (at the kind limit)
        for i in range(2):
            memory = Memory(
                agent_id=test_agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content=f"Learning {i}",
            )
            limited_store.save_memory(memory)

        # 3rd LEARNINGS should fail
        memory = Memory(
            agent_id=test_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="This should fail",
        )
        with pytest.raises(MemoryLimitExceeded) as exc_info:
            limited_store.save_memory(memory)

        assert "kind" in str(exc_info.value)
        assert "LEARNINGS" in str(exc_info.value)

    def test_updates_dont_count_against_limits(
        self, limited_store: MemoryStore, test_agent: Agent
    ) -> None:
        """Test that updating an existing memory doesn't hit limits."""
        limited_store.save_agent(test_agent)

        # Create a memory
        memory = Memory(
            agent_id=test_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Original content",
        )
        limited_store.save_memory(memory)

        # Fill up to the limit with other memories
        for i in range(4):
            m = Memory(
                agent_id=test_agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind(["EMOTIONAL", "ARCHITECTURAL", "ACHIEVEMENTS"][i % 3]),
                content=f"Memory {i}",
            )
            limited_store.save_memory(m)

        # Now update the original memory - should work
        memory.content = "Updated content"
        limited_store.save_memory(memory)  # Should not raise

        retrieved = limited_store.get_memory(memory.id)
        assert retrieved is not None
        assert retrieved.content == "Updated content"

    def test_no_limits_allows_unlimited(self) -> None:
        """Test that NO_LIMITS allows saving many memories."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        store = MemoryStore(db_path=db_path, limits=NO_LIMITS)
        agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        # Add many memories - should all succeed
        for i in range(50):
            memory = Memory(
                agent_id=agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content=f"Memory {i}",
            )
            store.save_memory(memory)

        assert store.count_memories(agent.id) == 50


class TestCountMemoriesByKind:
    """Tests for count_memories_by_kind method."""

    def test_count_by_kind(self, limited_store: MemoryStore, test_agent: Agent) -> None:
        """Test counting memories by kind."""
        limited_store.save_agent(test_agent)

        # Add memories of different kinds
        limited_store.save_memory(
            Memory(
                agent_id=test_agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content="Learning 1",
            )
        )
        limited_store.save_memory(
            Memory(
                agent_id=test_agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content="Learning 2",
            )
        )
        limited_store.save_memory(
            Memory(
                agent_id=test_agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.EMOTIONAL,
                content="Emotional 1",
            )
        )

        assert (
            limited_store.count_memories_by_kind(test_agent.id, MemoryKind.LEARNINGS)
            == 2
        )
        assert (
            limited_store.count_memories_by_kind(test_agent.id, MemoryKind.EMOTIONAL)
            == 1
        )
        assert (
            limited_store.count_memories_by_kind(
                test_agent.id, MemoryKind.ARCHITECTURAL
            )
            == 0
        )

    def test_count_by_kind_excludes_superseded(
        self, limited_store: MemoryStore, test_agent: Agent
    ) -> None:
        """Test that superseded memories aren't counted."""
        limited_store.save_agent(test_agent)

        # Add and supersede a memory
        old_memory = Memory(
            agent_id=test_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Old learning",
        )
        new_memory = Memory(
            agent_id=test_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="New learning",
        )
        limited_store.save_memory(old_memory)
        limited_store.save_memory(new_memory)
        limited_store.supersede_memory(old_memory.id, new_memory.id)

        # Should only count the non-superseded one
        assert (
            limited_store.count_memories_by_kind(test_agent.id, MemoryKind.LEARNINGS)
            == 1
        )
