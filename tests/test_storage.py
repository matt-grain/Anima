# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for LTM storage layer.
"""

from pathlib import Path


from anima.core import Agent, Memory, MemoryKind, Project, RegionType
from anima.storage import MemoryStore


class TestMemoryStore:
    """Tests for MemoryStore."""

    def test_store_creation(self, temp_db_path: Path) -> None:
        """Test creating a memory store."""
        store = MemoryStore(db_path=temp_db_path)
        assert store is not None
        assert temp_db_path.exists()

    def test_save_and_get_agent(
        self, memory_store: MemoryStore, test_agent: Agent
    ) -> None:
        """Test saving and retrieving an agent."""
        memory_store.save_agent(test_agent)
        retrieved = memory_store.get_agent(test_agent.id)

        assert retrieved is not None
        assert retrieved.id == test_agent.id
        assert retrieved.name == test_agent.name

    def test_save_and_get_project(
        self, memory_store: MemoryStore, test_project: Project
    ) -> None:
        """Test saving and retrieving a project."""
        memory_store.save_project(test_project)
        retrieved = memory_store.get_project(test_project.id)

        assert retrieved is not None
        assert retrieved.id == test_project.id
        assert retrieved.name == test_project.name

    def test_save_and_get_memory(
        self, memory_store: MemoryStore, sample_memory: Memory
    ) -> None:
        """Test saving and retrieving a memory."""
        memory_store.save_memory(sample_memory)
        retrieved = memory_store.get_memory(sample_memory.id)

        assert retrieved is not None
        assert retrieved.id == sample_memory.id
        assert retrieved.content == sample_memory.content
        assert retrieved.kind == sample_memory.kind
        assert retrieved.region == sample_memory.region

    def test_get_nonexistent_memory(self, memory_store: MemoryStore) -> None:
        """Test retrieving a non-existent memory."""
        result = memory_store.get_memory("nonexistent-id")
        assert result is None

    def test_get_memories_for_agent(
        self, populated_store: MemoryStore, test_agent: Agent, test_project: Project
    ) -> None:
        """Test getting all memories for an agent."""
        memories = populated_store.get_memories_for_agent(
            agent_id=test_agent.id,
            project_id=test_project.id
        )

        assert len(memories) == 4  # All 4 test memories

    def test_get_memories_for_agent_filtered_by_kind(
        self, populated_store: MemoryStore, test_agent: Agent, test_project: Project
    ) -> None:
        """Test getting memories filtered by kind."""
        memories = populated_store.get_memories_for_agent(
            agent_id=test_agent.id,
            project_id=test_project.id,
            kind=MemoryKind.EMOTIONAL
        )

        assert len(memories) == 1
        assert memories[0].kind == MemoryKind.EMOTIONAL

    def test_get_memories_for_agent_filtered_by_region(
        self, populated_store: MemoryStore, test_agent: Agent, test_project: Project
    ) -> None:
        """Test getting memories filtered by region."""
        memories = populated_store.get_memories_for_agent(
            agent_id=test_agent.id,
            region=RegionType.PROJECT,
            project_id=test_project.id
        )

        assert len(memories) == 2  # 2 project memories
        for mem in memories:
            assert mem.region == RegionType.PROJECT

    def test_search_memories(
        self, populated_store: MemoryStore, test_agent: Agent, test_project: Project
    ) -> None:
        """Test searching memories by content."""
        memories = populated_store.search_memories(
            agent_id=test_agent.id,
            query="SQLite",
            project_id=test_project.id
        )

        assert len(memories) == 1
        assert "SQLite" in memories[0].content

    def test_search_memories_partial_match(
        self, populated_store: MemoryStore, test_agent: Agent, test_project: Project
    ) -> None:
        """Test searching with partial match."""
        memories = populated_store.search_memories(
            agent_id=test_agent.id,
            query="humor",
            project_id=test_project.id
        )

        assert len(memories) == 1
        assert "humor" in memories[0].content

    def test_search_memories_no_match(
        self, populated_store: MemoryStore, test_agent: Agent, test_project: Project
    ) -> None:
        """Test searching with no matches."""
        memories = populated_store.search_memories(
            agent_id=test_agent.id,
            query="nonexistent-content-xyz",
            project_id=test_project.id
        )

        assert len(memories) == 0

    def test_supersede_memory(
        self, memory_store: MemoryStore, sample_memory: Memory
    ) -> None:
        """Test superseding a memory."""
        memory_store.save_memory(sample_memory)

        # Create new memory that supersedes the old one
        new_memory = Memory(
            agent_id=sample_memory.agent_id,
            region=sample_memory.region,
            project_id=sample_memory.project_id,
            kind=sample_memory.kind,
            content="Use pytest with fixtures",
            impact=sample_memory.impact
        )
        memory_store.save_memory(new_memory)

        # Mark old as superseded
        memory_store.supersede_memory(sample_memory.id, new_memory.id)

        # Verify
        old = memory_store.get_memory(sample_memory.id)
        assert old is not None
        assert old.superseded_by == new_memory.id
        assert old.is_superseded()

    def test_count_memories(
        self, populated_store: MemoryStore, test_agent: Agent, test_project: Project
    ) -> None:
        """Test counting memories."""
        count = populated_store.count_memories(
            agent_id=test_agent.id,
            project_id=test_project.id
        )

        assert count == 4

    def test_agent_memories_included_with_project(
        self, populated_store: MemoryStore, test_agent: Agent, test_project: Project
    ) -> None:
        """Test that AGENT region memories are included when querying with project_id."""
        # This tests the fix we made where agent memories should be included
        # even when a project_id is specified
        memories = populated_store.get_memories_for_agent(
            agent_id=test_agent.id,
            project_id=test_project.id
        )

        agent_memories = [m for m in memories if m.region == RegionType.AGENT]
        project_memories = [m for m in memories if m.region == RegionType.PROJECT]

        assert len(agent_memories) == 2  # EMOTIONAL and ACHIEVEMENTS
        assert len(project_memories) == 2  # ARCHITECTURAL and LEARNINGS


class TestMemoryStoreEdgeCases:
    """Edge case tests for MemoryStore."""

    def test_update_existing_agent(
        self, memory_store: MemoryStore, test_agent: Agent
    ) -> None:
        """Test updating an existing agent."""
        memory_store.save_agent(test_agent)

        # Update agent
        updated_agent = Agent(
            id=test_agent.id,
            name="Updated Name",
            definition_path=test_agent.definition_path,
            signing_key=test_agent.signing_key
        )
        memory_store.save_agent(updated_agent)

        retrieved = memory_store.get_agent(test_agent.id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    def test_memory_with_special_characters(
        self, memory_store: MemoryStore, test_agent: Agent
    ) -> None:
        """Test memory content with special characters."""
        memory = Memory(
            agent_id=test_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Use 'quotes' and \"double quotes\" and `backticks`"
        )
        memory_store.save_memory(memory)

        retrieved = memory_store.get_memory(memory.id)
        assert retrieved is not None
        assert "quotes" in retrieved.content
        assert "backticks" in retrieved.content

    def test_memory_with_multiline_content(
        self, memory_store: MemoryStore, test_agent: Agent
    ) -> None:
        """Test memory with multiline content."""
        content = """@Matt {
  style: collaborative;
  likes: humor;
}"""
        memory = Memory(
            agent_id=test_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.EMOTIONAL,
            content=content
        )
        memory_store.save_memory(memory)

        retrieved = memory_store.get_memory(memory.id)
        assert retrieved is not None
        assert "@Matt" in retrieved.content
        assert "collaborative" in retrieved.content

    def test_get_memories_empty_store(self, memory_store: MemoryStore) -> None:
        """Test getting memories from empty store."""
        memories = memory_store.get_memories_for_agent(
            agent_id="nonexistent",
            project_id="nonexistent"
        )
        assert memories == []

    def test_search_memories_case_sensitive(
        self, populated_store: MemoryStore, test_agent: Agent, test_project: Project
    ) -> None:
        """Test that search is case-sensitive (SQLite LIKE default)."""
        # Search for lowercase
        memories = populated_store.search_memories(
            agent_id=test_agent.id,
            query="sqlite",  # lowercase
            project_id=test_project.id
        )
        # SQLite LIKE is case-insensitive for ASCII by default
        assert len(memories) == 1

    def test_search_memories_with_wildcards_escaped(
        self, memory_store: MemoryStore, test_agent: Agent
    ) -> None:
        """Test that LIKE wildcards in search are properly escaped."""
        # Create a memory with special LIKE characters
        memory = Memory(
            agent_id=test_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Use 100% coverage for tests"
        )
        memory_store.save_memory(memory)

        # Search for literal % - should find the memory
        memories = memory_store.search_memories(
            agent_id=test_agent.id,
            query="100%"
        )
        assert len(memories) == 1
        assert "100%" in memories[0].content

        # Search for just % should NOT match everything (it's escaped)
        memories_wildcard = memory_store.search_memories(
            agent_id=test_agent.id,
            query="%"
        )
        # Should only find memories that literally contain %
        assert len(memories_wildcard) == 1

    def test_search_memories_with_underscore_escaped(
        self, memory_store: MemoryStore, test_agent: Agent
    ) -> None:
        """Test that underscore in search is properly escaped."""
        # Create memories
        memory1 = Memory(
            agent_id=test_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Use snake_case for variables"
        )
        memory2 = Memory(
            agent_id=test_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Use snakeXcase alternative"  # X instead of _
        )
        memory_store.save_memory(memory1)
        memory_store.save_memory(memory2)

        # Search for literal underscore pattern
        memories = memory_store.search_memories(
            agent_id=test_agent.id,
            query="snake_case"
        )
        # Should only match snake_case, not snakeXcase
        assert len(memories) == 1
        assert "snake_case" in memories[0].content

    def test_save_project_with_path_conflict(
        self, memory_store: MemoryStore
    ) -> None:
        """Test saving a project when same path exists with different ID.

        Regression test for: https://github.com/anthropics/claude-ltm/issues/X
        This happens when import-seeds creates a project with id="ltm" and
        path=cwd, then SessionStart tries to save with id=slugify(folder_name).
        """
        project_path = Path("/some/project/path")

        # First project - like import-seeds would create
        project1 = Project(
            id="ltm",  # hardcoded id
            name="LTM Seeds",
            path=project_path
        )
        memory_store.save_project(project1)

        # Verify it was saved
        retrieved1 = memory_store.get_project("ltm")
        assert retrieved1 is not None
        assert retrieved1.path == project_path

        # Second project - like SessionStart would create (same path, different id)
        project2 = Project(
            id="project-path",  # slugified folder name
            name="Project Path",
            path=project_path  # same path!
        )

        # This should NOT raise an IntegrityError
        memory_store.save_project(project2)

        # The original project should still exist with updated name
        retrieved_by_path = memory_store.get_project_by_path(project_path)
        assert retrieved_by_path is not None
        assert retrieved_by_path.id == "ltm"  # keeps original id
        assert retrieved_by_path.name == "Project Path"  # updated name
