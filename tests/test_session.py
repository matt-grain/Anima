# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for session management (Phase 3: Temporal Infrastructure)."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from anima.core import Memory, MemoryKind, ImpactLevel, RegionType, Agent, Project
from anima.lifecycle.session import (
    generate_session_id,
    start_session,
    get_current_session_id,
    get_session_start_time,
    get_previous_session_id,
)
from anima.storage import MemoryStore


class TestSessionGeneration:
    """Tests for session ID generation."""

    def test_generate_session_id_format(self):
        """Session ID should have timestamp prefix and random suffix."""
        session_id = generate_session_id()
        # Format: YYYYMMDD-HHMMSS-xxxxxxxx
        parts = session_id.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 8  # YYYYMMDD
        assert len(parts[1]) == 6  # HHMMSS
        assert len(parts[2]) == 8  # Random suffix

    def test_generate_session_id_unique(self):
        """Each generated session ID should be unique."""
        ids = [generate_session_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique

    def test_generate_session_id_sortable(self):
        """Session IDs should be roughly sortable by time."""
        id1 = generate_session_id()
        id2 = generate_session_id()
        # Both should start with today's date
        today = datetime.now().strftime("%Y%m%d")
        assert id1.startswith(today)
        assert id2.startswith(today)


class TestSessionLifecycle:
    """Tests for session start/get lifecycle."""

    @pytest.fixture
    def mock_settings(self, tmp_path):
        """Mock the settings storage to use temp db."""
        db_path = tmp_path / "test.db"
        with patch(
            "anima.storage.curiosity.get_default_db_path", return_value=db_path
        ), patch(
            "anima.lifecycle.session.get_setting"
        ) as mock_get, patch(
            "anima.lifecycle.session.set_setting"
        ) as mock_set:
            # Track settings in memory
            settings = {}

            def get_impl(key):
                return settings.get(key)

            def set_impl(key, value):
                settings[key] = value

            mock_get.side_effect = get_impl
            mock_set.side_effect = set_impl

            yield settings

    def test_start_session_returns_id(self, mock_settings):
        """start_session should return a valid session ID."""
        session_id = start_session()
        assert session_id is not None
        assert len(session_id) > 0

    def test_start_session_stores_id(self, mock_settings):
        """start_session should store the ID in settings."""
        session_id = start_session()
        assert mock_settings["current_session_id"] == session_id

    def test_start_session_stores_time(self, mock_settings):
        """start_session should store the start time."""
        start_session()
        assert "session_start_time" in mock_settings

    def test_get_current_session_id(self, mock_settings):
        """get_current_session_id should return the stored session."""
        started_id = start_session()
        retrieved_id = get_current_session_id()
        assert retrieved_id == started_id


class TestSessionQueries:
    """Tests for session-based memory queries."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a test store."""
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

    def test_get_memories_by_session(self, store, agent, project):
        """Should retrieve only memories from specified session."""
        store.save_agent(agent)
        store.save_project(project)

        # Create memories in different sessions
        session1 = "20260130-100000-session1"
        session2 = "20260130-110000-session2"

        mem1 = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Session 1 memory",
            impact=ImpactLevel.MEDIUM,
            session_id=session1,
        )
        mem2 = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Session 2 memory",
            impact=ImpactLevel.MEDIUM,
            session_id=session2,
        )
        store.save_memory(mem1)
        store.save_memory(mem2)

        # Query by session
        result = store.get_memories_by_session(session1)
        assert len(result) == 1
        assert result[0].content == "Session 1 memory"

    def test_get_distinct_sessions(self, store, agent, project):
        """Should return distinct session IDs ordered by recency."""
        store.save_agent(agent)
        store.save_project(project)

        sessions = [
            "20260128-100000-session1",
            "20260129-100000-session2",
            "20260130-100000-session3",
        ]

        for i, session_id in enumerate(sessions):
            mem = Memory(
                agent_id=agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content=f"Memory {i}",
                impact=ImpactLevel.MEDIUM,
                session_id=session_id,
                created_at=datetime(2026, 1, 28 + i, 10, 0, 0),
            )
            store.save_memory(mem)

        # Get sessions (most recent first)
        result = store.get_distinct_sessions(agent_id=agent.id)
        assert result[0] == "20260130-100000-session3"
        assert result[1] == "20260129-100000-session2"
        assert result[2] == "20260128-100000-session1"

    def test_get_distinct_sessions_limit(self, store, agent, project):
        """Should respect the limit parameter."""
        store.save_agent(agent)
        store.save_project(project)

        for i in range(5):
            mem = Memory(
                agent_id=agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content=f"Memory {i}",
                impact=ImpactLevel.MEDIUM,
                session_id=f"session{i}",
                created_at=datetime(2026, 1, 25 + i, 10, 0, 0),
            )
            store.save_memory(mem)

        result = store.get_distinct_sessions(agent_id=agent.id, limit=3)
        assert len(result) == 3

    def test_session_id_stored_on_memory(self, store, agent, project):
        """Memory should preserve session_id through save/load cycle."""
        store.save_agent(agent)

        session_id = "20260130-150000-testtest"
        mem = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test memory",
            impact=ImpactLevel.MEDIUM,
            session_id=session_id,
        )
        store.save_memory(mem)

        loaded = store.get_memory(mem.id)
        assert loaded is not None
        assert loaded.session_id == session_id


class TestMigration:
    """Tests for schema migration to v5."""

    def test_session_id_column_nullable(self, tmp_path):
        """Existing memories without session_id should still work."""
        db_path = tmp_path / "test.db"
        store = MemoryStore(db_path=db_path)

        agent = Agent(id="test-agent", name="TestAgent")
        store.save_agent(agent)

        # Create memory without session_id
        mem = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Legacy memory",
            impact=ImpactLevel.MEDIUM,
            # session_id not set
        )
        store.save_memory(mem)

        # Should load without error
        loaded = store.get_memory(mem.id)
        assert loaded is not None
        assert loaded.session_id is None
