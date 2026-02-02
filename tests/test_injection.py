# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for memory injection (Phase 3A: Project-Aware Loading)."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from anima.core import Memory, MemoryKind, ImpactLevel, RegionType, Agent, Project
from anima.lifecycle.injection import MemoryInjector
from anima.storage import MemoryStore


class TestProjectAwareLoading:
    """Tests for Phase 3A: Project-Aware Loading."""

    def setup_method(self, method):
        """Create a fresh store for each test."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "test.db"
        self.store = MemoryStore(db_path=self.db_path)

        # Create agent and project
        self.agent = Agent(id="test-agent", name="Test")
        self.project = Project(id="test-project", name="TestProject", path=Path("/test"))
        self.store.save_agent(self.agent)
        self.store.save_project(self.project)

    def teardown_method(self, method):
        """Clean up temp files."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_memory(
        self,
        content: str,
        session_id: str = None,
        region: RegionType = RegionType.PROJECT,
        project_id: str = None,
    ) -> Memory:
        """Helper to create and save a memory."""
        memory = Memory(
            agent_id=self.agent.id,
            region=region,
            project_id=project_id or (self.project.id if region == RegionType.PROJECT else None),
            kind=MemoryKind.LEARNINGS,
            content=content,
            original_content=content,
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            session_id=session_id,
        )
        self.store.save_memory(memory)
        return memory

    @patch("anima.lifecycle.injection.get_previous_session_id")
    def test_loads_previous_session_memories(self, mock_prev_session):
        """Test that memories from previous session are loaded for project continuity."""
        prev_session = "20260129-120000-abc12345"
        curr_session = "20260130-100000-def67890"
        mock_prev_session.return_value = prev_session

        # Create memory from previous session (side effect: populates store)
        _prev_memory = self._create_memory(
            "This is from the previous session",
            session_id=prev_session,
        )

        # Create memory from current session (side effect: populates store)
        _curr_memory = self._create_memory(
            "This is from the current session",
            session_id=curr_session,
        )

        # Inject with project context
        injector = MemoryInjector(store=self.store)
        dsl = injector.inject(self.agent, self.project)

        # Both memories should be in the output
        assert "previous session" in dsl
        assert "current session" in dsl

    @patch("anima.lifecycle.injection.get_previous_session_id")
    def test_deduplicates_memories(self, mock_prev_session):
        """Test that memories are not loaded twice."""
        session_id = "20260129-120000-abc12345"
        mock_prev_session.return_value = session_id

        # Create a memory that would match both tier loading and session loading
        _memory = self._create_memory(
            "Unique memory content",
            session_id=session_id,
        )

        injector = MemoryInjector(store=self.store)
        dsl = injector.inject(self.agent, self.project)

        # Memory should appear only once
        count = dsl.count("Unique memory content")
        assert count == 1

    @patch("anima.lifecycle.injection.get_previous_session_id")
    def test_no_previous_session(self, mock_prev_session):
        """Test graceful handling when no previous session exists."""
        mock_prev_session.return_value = None

        _memory = self._create_memory("Test memory")

        injector = MemoryInjector(store=self.store)
        dsl = injector.inject(self.agent, self.project)

        # Should still work without previous session
        assert "Test memory" in dsl

    @patch("anima.lifecycle.injection.get_previous_session_id")
    def test_only_loads_project_session_memories(self, mock_prev_session):
        """Test that only project-specific memories from previous session are loaded."""
        prev_session = "20260129-120000-abc12345"
        mock_prev_session.return_value = prev_session

        # Create a different project
        other_project = Project(id="other-project", name="Other", path=Path("/other"))
        self.store.save_project(other_project)

        # Create memory for other project in same session (side effect: populates store)
        _other_memory = self._create_memory(
            "Memory from other project",
            session_id=prev_session,
            project_id=other_project.id,
        )

        # Create memory for our project in same session (side effect: populates store)
        _our_memory = self._create_memory(
            "Memory from our project",
            session_id=prev_session,
        )

        injector = MemoryInjector(store=self.store)
        dsl = injector.inject(self.agent, self.project)

        # Only our project's memory should be loaded
        assert "our project" in dsl
        assert "other project" not in dsl


class TestPrioritization:
    """Tests for memory prioritization."""

    def setup_method(self, method):
        """Create a fresh store for each test."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "test.db"
        self.store = MemoryStore(db_path=self.db_path)

        self.agent = Agent(id="test-agent", name="Test")
        self.store.save_agent(self.agent)

    def teardown_method(self, method):
        """Clean up temp files."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_critical_memories_first(self):
        """Critical memories should come before lower impact ones."""
        # Create low impact first
        low_memory = Memory(
            agent_id=self.agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Low impact memory",
            original_content="Low impact memory",
            impact=ImpactLevel.LOW,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        self.store.save_memory(low_memory)

        # Create critical second
        critical_memory = Memory(
            agent_id=self.agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.EMOTIONAL,
            content="Critical emotional memory",
            original_content="Critical emotional memory",
            impact=ImpactLevel.CRITICAL,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        self.store.save_memory(critical_memory)

        injector = MemoryInjector(store=self.store)
        dsl = injector.inject(self.agent)

        # Critical should come before low
        critical_pos = dsl.find("Critical emotional")
        low_pos = dsl.find("Low impact")

        assert critical_pos < low_pos

    def test_introspect_prioritized_after_emotional(self):
        """INTROSPECT memories should come after EMOTIONAL but before others."""
        # Create in wrong order
        learning = Memory(
            agent_id=self.agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Learning memory",
            original_content="Learning memory",
            impact=ImpactLevel.HIGH,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        self.store.save_memory(learning)

        introspect = Memory(
            agent_id=self.agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.INTROSPECT,
            content="Introspect memory",
            original_content="Introspect memory",
            impact=ImpactLevel.HIGH,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        self.store.save_memory(introspect)

        emotional = Memory(
            agent_id=self.agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.EMOTIONAL,
            content="Emotional memory",
            original_content="Emotional memory",
            impact=ImpactLevel.HIGH,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        self.store.save_memory(emotional)

        injector = MemoryInjector(store=self.store)
        dsl = injector.inject(self.agent)

        # Order should be: EMOTIONAL, INTROSPECT, LEARNINGS
        emot_pos = dsl.find("Emotional")
        intro_pos = dsl.find("Introspect")
        learn_pos = dsl.find("Learning")

        assert emot_pos < intro_pos < learn_pos
