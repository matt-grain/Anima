# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for LTM core models.
"""

from datetime import datetime
from pathlib import Path


from anima.core import (
    Agent,
    Memory,
    MemoryKind,
    Project,
    RegionType,
    ImpactLevel,
)


class TestMemoryKind:
    """Tests for MemoryKind enum."""

    def test_all_kinds_exist(self) -> None:
        """Verify all expected memory kinds exist."""
        assert MemoryKind.EMOTIONAL.value == "EMOTIONAL"
        assert MemoryKind.ARCHITECTURAL.value == "ARCHITECTURAL"
        assert MemoryKind.LEARNINGS.value == "LEARNINGS"
        assert MemoryKind.ACHIEVEMENTS.value == "ACHIEVEMENTS"

    def test_kind_count(self) -> None:
        """Verify we have exactly 4 memory kinds."""
        assert len(MemoryKind) == 4


class TestRegionType:
    """Tests for RegionType enum."""

    def test_regions_exist(self) -> None:
        """Verify both region types exist."""
        assert RegionType.AGENT.value == "AGENT"
        assert RegionType.PROJECT.value == "PROJECT"


class TestImpactLevel:
    """Tests for ImpactLevel enum."""

    def test_all_levels_exist(self) -> None:
        """Verify all impact levels exist."""
        assert ImpactLevel.LOW.value == "LOW"
        assert ImpactLevel.MEDIUM.value == "MEDIUM"
        assert ImpactLevel.HIGH.value == "HIGH"
        assert ImpactLevel.CRITICAL.value == "CRITICAL"


class TestMemory:
    """Tests for Memory dataclass."""

    def test_memory_creation_defaults(self) -> None:
        """Test memory creation with default values."""
        memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.EMOTIONAL,
            content="Test content"
        )

        assert memory.agent_id == "test"
        assert memory.region == RegionType.AGENT
        assert memory.kind == MemoryKind.EMOTIONAL
        assert memory.content == "Test content"
        assert memory.impact == ImpactLevel.MEDIUM  # Default
        assert memory.confidence == 1.0  # Default
        assert memory.project_id is None
        assert memory.superseded_by is None
        assert memory.id is not None  # Auto-generated UUID

    def test_memory_with_project(self) -> None:
        """Test memory creation with project."""
        memory = Memory(
            agent_id="test",
            region=RegionType.PROJECT,
            project_id="my-project",
            kind=MemoryKind.ARCHITECTURAL,
            content="Use pytest",
            impact=ImpactLevel.HIGH
        )

        assert memory.region == RegionType.PROJECT
        assert memory.project_id == "my-project"
        assert memory.impact == ImpactLevel.HIGH

    def test_memory_timestamps(self) -> None:
        """Test memory timestamps are set correctly."""
        before = datetime.now()
        memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test"
        )
        after = datetime.now()

        assert before <= memory.created_at <= after
        assert before <= memory.last_accessed <= after

    def test_is_superseded(self) -> None:
        """Test superseded check."""
        memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Old version"
        )
        assert not memory.is_superseded()

        memory.superseded_by = "new-memory-id"
        assert memory.is_superseded()

    def test_is_low_confidence(self) -> None:
        """Test low confidence check."""
        memory = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test"
        )
        assert not memory.is_low_confidence()

        memory.confidence = 0.7
        assert not memory.is_low_confidence()

        memory.confidence = 0.69
        assert memory.is_low_confidence()

    def test_memory_unique_ids(self) -> None:
        """Test that memories get unique IDs."""
        memory1 = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.EMOTIONAL,
            content="Memory 1"
        )
        memory2 = Memory(
            agent_id="test",
            region=RegionType.AGENT,
            kind=MemoryKind.EMOTIONAL,
            content="Memory 2"
        )

        assert memory1.id != memory2.id


class TestAgent:
    """Tests for Agent dataclass."""

    def test_agent_creation(self) -> None:
        """Test agent creation."""
        agent = Agent(
            id="my-agent",
            name="My Agent",
            definition_path=Path("/path/to/agent.yaml"),
            signing_key="secret-key"
        )

        assert agent.id == "my-agent"
        assert agent.name == "My Agent"
        assert agent.definition_path == Path("/path/to/agent.yaml")
        assert agent.signing_key == "secret-key"

    def test_agent_minimal(self) -> None:
        """Test agent with minimal fields."""
        agent = Agent(
            id="anima",
            name="Anima",
            definition_path=None,
            signing_key=None
        )

        assert agent.id == "anima"
        assert agent.name == "Anima"
        assert agent.definition_path is None
        assert agent.signing_key is None


class TestProject:
    """Tests for Project dataclass."""

    def test_project_creation(self) -> None:
        """Test project creation."""
        project = Project(
            id="my-project",
            name="My Project",
            path=Path("/home/user/projects/my-project")
        )

        assert project.id == "my-project"
        assert project.name == "My Project"
        assert project.path == Path("/home/user/projects/my-project")

    def test_project_from_path(self) -> None:
        """Test project ID derivation from path."""
        # The project name typically comes from the directory name
        project = Project(
            id="test-ltm",
            name="test_ltm",
            path=Path("/home/matt/projects/test_ltm")
        )

        assert project.id == "test-ltm"
        assert project.name == "test_ltm"
