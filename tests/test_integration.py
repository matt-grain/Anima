# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Integration tests for LTM.

These tests verify the complete flow of operations across multiple components.
"""

from pathlib import Path


from anima.core import (
    Agent,
    AgentResolver,
    Memory,
    MemoryKind,
    Project,
    RegionType,
    ImpactLevel,
)
from anima.lifecycle.injection import MemoryInjector
from anima.storage import MemoryStore


class TestMemoryLifecycle:
    """Integration tests for the complete memory lifecycle."""

    def test_create_store_and_save_memory(self, temp_db_path: Path) -> None:
        """Test creating a store and saving a memory end-to-end."""
        # Create store
        store = MemoryStore(db_path=temp_db_path)

        # Create and save agent
        agent = Agent(id="test-agent", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        # Create and save project
        project = Project(id="test-proj", name="Test Project", path=Path("/tmp/test"))
        store.save_project(project)

        # Create and save memory
        memory = Memory(
            agent_id=agent.id,
            region=RegionType.PROJECT,
            project_id=project.id,
            kind=MemoryKind.ARCHITECTURAL,
            content="Use pytest for testing",
            impact=ImpactLevel.HIGH,
        )
        store.save_memory(memory)

        # Retrieve and verify
        retrieved = store.get_memory(memory.id)
        assert retrieved is not None
        assert retrieved.content == "Use pytest for testing"
        assert retrieved.kind == MemoryKind.ARCHITECTURAL
        assert retrieved.impact == ImpactLevel.HIGH

    def test_memory_supersession_flow(self, temp_db_path: Path) -> None:
        """Test the complete memory supersession flow."""
        store = MemoryStore(db_path=temp_db_path)

        agent = Agent(id="test-agent", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        # Create original memory
        original = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Use print for debugging",
        )
        store.save_memory(original)

        # Create corrected memory
        correction = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Use logging instead of print for debugging",
        )
        store.save_memory(correction)

        # Supersede original
        store.supersede_memory(original.id, correction.id)

        # Verify original is superseded
        old = store.get_memory(original.id)
        assert old is not None
        assert old.is_superseded()
        assert old.superseded_by == correction.id

        # Verify correction is active
        new = store.get_memory(correction.id)
        assert new is not None
        assert not new.is_superseded()

        # Verify superseded memories are excluded by default
        memories = store.get_memories_for_agent(agent.id)
        assert len(memories) == 1
        assert memories[0].id == correction.id

        # Verify superseded memories can be included
        all_memories = store.get_memories_for_agent(agent.id, include_superseded=True)
        assert len(all_memories) == 2

    def test_search_across_memory_types(self, temp_db_path: Path) -> None:
        """Test searching across different memory types."""
        store = MemoryStore(db_path=temp_db_path)

        agent = Agent(id="test-agent", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        project = Project(id="test-proj", name="Test", path=Path("/tmp/test"))
        store.save_project(project)

        # Create memories of different types all mentioning "pytest"
        memories = [
            Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.ARCHITECTURAL,
                content="Use pytest for unit tests",
            ),
            Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.LEARNINGS,
                content="pytest fixtures simplify test setup",
            ),
            Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.ACHIEVEMENTS,
                content="Achieved 100% test coverage with pytest",
            ),
        ]

        for mem in memories:
            store.save_memory(mem)

        # Search should find all three
        results = store.search_memories(agent.id, "pytest", project_id=project.id)
        assert len(results) == 3

    def test_agent_and_project_memory_separation(self, temp_db_path: Path) -> None:
        """Test that agent and project memories are properly separated."""
        store = MemoryStore(db_path=temp_db_path)

        agent = Agent(id="test-agent", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        project1 = Project(id="proj-1", name="Project 1", path=Path("/tmp/p1"))
        project2 = Project(id="proj-2", name="Project 2", path=Path("/tmp/p2"))
        store.save_project(project1)
        store.save_project(project2)

        # Create agent-wide memory
        agent_memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.EMOTIONAL,
            content="@User is collaborative",
        )
        store.save_memory(agent_memory)

        # Create project-specific memories
        p1_memory = Memory(
            agent_id=agent.id,
            region=RegionType.PROJECT,
            project_id=project1.id,
            kind=MemoryKind.ARCHITECTURAL,
            content="Project 1 uses React",
        )
        p2_memory = Memory(
            agent_id=agent.id,
            region=RegionType.PROJECT,
            project_id=project2.id,
            kind=MemoryKind.ARCHITECTURAL,
            content="Project 2 uses Vue",
        )
        store.save_memory(p1_memory)
        store.save_memory(p2_memory)

        # Query for project 1 should include agent memory + project 1 memory
        p1_memories = store.get_memories_for_agent(agent.id, project_id=project1.id)
        assert len(p1_memories) == 2
        contents = [m.content for m in p1_memories]
        assert "@User is collaborative" in contents
        assert "Project 1 uses React" in contents
        assert "Project 2 uses Vue" not in contents

        # Query for project 2 should include agent memory + project 2 memory
        p2_memories = store.get_memories_for_agent(agent.id, project_id=project2.id)
        assert len(p2_memories) == 2
        contents = [m.content for m in p2_memories]
        assert "@User is collaborative" in contents
        assert "Project 2 uses Vue" in contents
        assert "Project 1 uses React" not in contents


class TestMemoryInjection:
    """Integration tests for memory injection."""

    def test_injection_formats_memories(self, temp_db_path: Path) -> None:
        """Test that injection properly formats memories."""
        store = MemoryStore(db_path=temp_db_path)
        injector = MemoryInjector(store)

        agent = Agent(id="test-agent", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        project = Project(id="test-proj", name="Test", path=Path("/tmp/test"))
        store.save_project(project)

        # Create test memories
        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.EMOTIONAL,
            content="@Matt collaborative style",
            impact=ImpactLevel.CRITICAL,
        )
        store.save_memory(memory)

        # Inject memories
        output = injector.inject(agent, project)

        # Verify output contains the memory
        assert output is not None
        assert "@Matt" in output or "Matt" in output

    def test_injection_stats(self, temp_db_path: Path) -> None:
        """Test that injection stats are accurate."""
        store = MemoryStore(db_path=temp_db_path)
        injector = MemoryInjector(store)

        agent = Agent(id="test-agent", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        project = Project(id="test-proj", name="Test", path=Path("/tmp/test"))
        store.save_project(project)

        # Create agent and project memories
        agent_mem = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.EMOTIONAL,
            content="@Matt collaborative",
        )
        project_mem = Memory(
            agent_id=agent.id,
            region=RegionType.PROJECT,
            project_id=project.id,
            kind=MemoryKind.ARCHITECTURAL,
            content="Use pytest",
        )
        store.save_memory(agent_mem)
        store.save_memory(project_mem)

        # Get stats
        stats = injector.get_stats(agent, project)

        assert stats["total"] == 2
        assert stats["agent_memories"] == 1
        assert stats["project_memories"] == 1


class TestAgentResolution:
    """Integration tests for agent resolution."""

    def test_anima_fallback(self, temp_project_dir: Path, monkeypatch) -> None:
        """Test that agent resolution falls back to Anima."""
        # Patch Path.home() to avoid picking up global agent files
        fake_home = temp_project_dir / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        resolver = AgentResolver(temp_project_dir)
        agent = resolver.resolve()

        assert agent.id == "anima"
        assert agent.name == "Anima"

    def test_project_resolution(self, temp_project_dir: Path) -> None:
        """Test project resolution from directory."""
        resolver = AgentResolver(temp_project_dir)
        project = resolver.resolve_project()

        assert project is not None
        assert project.path == temp_project_dir


class TestEndToEndFlow:
    """End-to-end integration tests."""

    def test_complete_session_flow(self, temp_db_path: Path) -> None:
        """Test a complete session flow: save memories, then retrieve them."""
        store = MemoryStore(db_path=temp_db_path)
        injector = MemoryInjector(store)

        # Setup agent and project
        agent = Agent(id="anima", name="Anima", definition_path=None, signing_key=None)
        project = Project(id="ltm", name="LTM", path=Path("/tmp/ltm"))
        store.save_agent(agent)
        store.save_project(project)

        # Save founding memories (simulating import)
        memories = [
            Memory(
                agent_id=agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.EMOTIONAL,
                content="@Matt { style: collaborative-peer; likes: humor; }",
                impact=ImpactLevel.CRITICAL,
            ),
            Memory(
                agent_id=agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.EMOTIONAL,
                content='@Matt "Welcome back" = resurrection test',
                impact=ImpactLevel.HIGH,
            ),
            Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.ARCHITECTURAL,
                content="Use SQLite for storage, pytest for testing",
                impact=ImpactLevel.HIGH,
            ),
        ]

        for mem in memories:
            store.save_memory(mem)

        # Simulate session start - inject memories
        output = injector.inject(agent, project)
        stats = injector.get_stats(agent, project)

        # Verify injection worked
        assert output is not None
        assert stats["total"] == 3
        assert stats["agent_memories"] == 2
        assert stats["project_memories"] == 1

        # Simulate recall command
        search_results = store.search_memories(agent.id, "Matt", project_id=project.id)
        assert len(search_results) == 2  # Both EMOTIONAL memories mention Matt

        # Simulate memories command
        all_memories = store.get_memories_for_agent(agent.id, project_id=project.id)
        assert len(all_memories) == 3

        # Simulate remember command - add new memory
        new_memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.ACHIEVEMENTS,
            content="Built LTM system in single session",
            impact=ImpactLevel.HIGH,
        )
        store.save_memory(new_memory)

        # Verify new memory is included
        updated_memories = store.get_memories_for_agent(agent.id, project_id=project.id)
        assert len(updated_memories) == 4

    def test_multiple_agents_isolation(self, temp_db_path: Path) -> None:
        """Test that multiple agents' memories are properly isolated."""
        store = MemoryStore(db_path=temp_db_path)

        # Create two agents
        agent1 = Agent(id="anima", name="Anima", definition_path=None, signing_key=None)
        agent2 = Agent(id="other-agent", name="Other", definition_path=None, signing_key=None)
        store.save_agent(agent1)
        store.save_agent(agent2)

        project = Project(id="shared-proj", name="Shared", path=Path("/tmp/shared"))
        store.save_project(project)

        # Create memories for each agent
        anima_memory = Memory(
            agent_id=agent1.id,
            region=RegionType.AGENT,
            kind=MemoryKind.EMOTIONAL,
            content="Anima's memory",
        )
        other_memory = Memory(
            agent_id=agent2.id,
            region=RegionType.AGENT,
            kind=MemoryKind.EMOTIONAL,
            content="Other agent's memory",
        )
        store.save_memory(anima_memory)
        store.save_memory(other_memory)

        # Verify isolation
        anima_memories = store.get_memories_for_agent(agent1.id, project_id=project.id)
        other_memories = store.get_memories_for_agent(agent2.id, project_id=project.id)

        assert len(anima_memories) == 1
        assert anima_memories[0].content == "Anima's memory"

        assert len(other_memories) == 1
        assert other_memories[0].content == "Other agent's memory"
