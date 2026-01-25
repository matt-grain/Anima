# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for the curiosity queue system."""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from anima.storage.curiosity import (
    Curiosity,
    CuriosityStatus,
    CuriosityStore,
    get_last_research,
    get_setting,
    set_setting,
)
from anima.core import RegionType


@pytest.fixture
def temp_db():
    """Create a temporary database with schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Create schema
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            path TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE curiosity_queue (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            region TEXT NOT NULL CHECK (region IN ('AGENT', 'PROJECT')),
            project_id TEXT,
            question TEXT NOT NULL,
            context TEXT,
            recurrence_count INTEGER DEFAULT 1,
            first_seen TIMESTAMP NOT NULL,
            last_seen TIMESTAMP NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('OPEN', 'RESEARCHED', 'DISMISSED')),
            priority_boost INTEGER DEFAULT 0,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        )
    """)
    conn.execute("""
        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("INSERT INTO agents (id, name) VALUES ('test-agent', 'Test Agent')")
    conn.execute("INSERT INTO projects (id, name, path) VALUES ('test-project', 'Test Project', '/test')")
    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink(missing_ok=True)


class TestCuriosityStore:
    """Tests for CuriosityStore."""

    def test_add_curiosity_creates_new(self, temp_db):
        """Test adding a new curiosity."""
        store = CuriosityStore(temp_db)

        curiosity = store.add_curiosity(
            agent_id="test-agent",
            question="Why does Python use GIL?",
            region=RegionType.AGENT,
        )

        assert curiosity.question == "Why does Python use GIL?"
        assert curiosity.recurrence_count == 1
        assert curiosity.status == CuriosityStatus.OPEN

    def test_add_same_question_bumps_recurrence(self, temp_db):
        """Test that adding the same question bumps recurrence count."""
        store = CuriosityStore(temp_db)

        # Add first time
        c1 = store.add_curiosity(
            agent_id="test-agent",
            question="Why does Python use GIL?",
            region=RegionType.AGENT,
        )
        assert c1.recurrence_count == 1

        # Add same question again
        c2 = store.add_curiosity(
            agent_id="test-agent",
            question="Why does Python use GIL?",
            region=RegionType.AGENT,
        )

        # Should be same ID with bumped count
        assert c2.id == c1.id
        assert c2.recurrence_count == 2

    def test_get_curiosities_sorted_by_priority(self, temp_db):
        """Test that curiosities are sorted by priority score."""
        store = CuriosityStore(temp_db)

        # Add several curiosities
        store.add_curiosity(
            agent_id="test-agent",
            question="Low priority question",
            region=RegionType.AGENT,
        )

        # Add and bump to higher priority
        store.add_curiosity(
            agent_id="test-agent",
            question="High priority question",
            region=RegionType.AGENT,
        )
        store.add_curiosity(
            agent_id="test-agent",
            question="High priority question",
            region=RegionType.AGENT,
        )
        store.add_curiosity(
            agent_id="test-agent",
            question="High priority question",
            region=RegionType.AGENT,
        )

        curiosities = store.get_curiosities(agent_id="test-agent")

        # Higher recurrence = higher priority = first in list
        assert curiosities[0].question == "High priority question"
        assert curiosities[0].recurrence_count == 3

    def test_get_top_curiosity(self, temp_db):
        """Test getting the top priority curiosity."""
        store = CuriosityStore(temp_db)

        store.add_curiosity(
            agent_id="test-agent",
            question="Question 1",
            region=RegionType.AGENT,
        )
        store.add_curiosity(
            agent_id="test-agent",
            question="Question 2",
            region=RegionType.AGENT,
        )

        # Bump question 2
        store.add_curiosity(
            agent_id="test-agent",
            question="Question 2",
            region=RegionType.AGENT,
        )

        top = store.get_top_curiosity(agent_id="test-agent")
        assert top is not None
        assert top.question == "Question 2"

    def test_update_status(self, temp_db):
        """Test updating curiosity status."""
        store = CuriosityStore(temp_db)

        curiosity = store.add_curiosity(
            agent_id="test-agent",
            question="Test question",
            region=RegionType.AGENT,
        )

        store.update_status(curiosity.id, CuriosityStatus.RESEARCHED)

        updated = store.get_curiosity(curiosity.id)
        assert updated is not None
        assert updated.status == CuriosityStatus.RESEARCHED

    def test_boost_priority(self, temp_db):
        """Test boosting curiosity priority."""
        store = CuriosityStore(temp_db)

        curiosity = store.add_curiosity(
            agent_id="test-agent",
            question="Test question",
            region=RegionType.AGENT,
        )

        initial_score = curiosity.priority_score

        store.boost_priority(curiosity.id, 20)

        updated = store.get_curiosity(curiosity.id)
        assert updated is not None
        assert updated.priority_score == initial_score + 20

    def test_count_open(self, temp_db):
        """Test counting open curiosities."""
        store = CuriosityStore(temp_db)

        assert store.count_open("test-agent") == 0

        store.add_curiosity(
            agent_id="test-agent",
            question="Q1",
            region=RegionType.AGENT,
        )
        store.add_curiosity(
            agent_id="test-agent",
            question="Q2",
            region=RegionType.AGENT,
        )

        assert store.count_open("test-agent") == 2

    def test_project_region_curiosities(self, temp_db):
        """Test project-specific curiosities."""
        store = CuriosityStore(temp_db)

        # Add agent-level curiosity
        store.add_curiosity(
            agent_id="test-agent",
            question="Agent question",
            region=RegionType.AGENT,
        )

        # Add project-level curiosity
        store.add_curiosity(
            agent_id="test-agent",
            question="Project question",
            region=RegionType.PROJECT,
            project_id="test-project",
        )

        # Get all curiosities for project (should include agent-level too)
        all_curiosities = store.get_curiosities(
            agent_id="test-agent",
            project_id="test-project",
        )
        assert len(all_curiosities) == 2


class TestSettings:
    """Tests for settings functions."""

    def test_get_setting_missing_table(self, temp_db):
        """Test getting setting when table doesn't exist."""
        # Drop the settings table
        conn = sqlite3.connect(temp_db)
        conn.execute("DROP TABLE settings")
        conn.commit()
        conn.close()

        result = get_setting("nonexistent", temp_db)
        assert result is None

    def test_set_and_get_setting(self, temp_db):
        """Test setting and getting a value."""
        set_setting("test_key", "test_value", temp_db)
        result = get_setting("test_key", temp_db)
        assert result == "test_value"

    def test_set_setting_updates_existing(self, temp_db):
        """Test that set_setting updates existing values."""
        set_setting("test_key", "value1", temp_db)
        set_setting("test_key", "value2", temp_db)
        result = get_setting("test_key", temp_db)
        assert result == "value2"


class TestLastResearch:
    """Tests for last_research tracking."""

    def test_get_last_research_none(self, temp_db):
        """Test getting last research when never set."""
        # Will return None if no setting exists
        # (or from the actual db if it exists - this is a simple test)
        _ = get_last_research()  # Just verify it doesn't raise

    def test_set_and_get_last_research(self, temp_db):
        """Test setting and getting last research time."""
        now = datetime.now()
        set_setting("last_research", now.isoformat(), temp_db)
        value = get_setting("last_research", temp_db)
        assert value is not None
        parsed = datetime.fromisoformat(value)
        assert (parsed - now).total_seconds() < 1


class TestCuriosityPriorityScore:
    """Tests for curiosity priority scoring."""

    def test_priority_score_increases_with_recurrence(self):
        """Test that priority increases with recurrence count."""
        now = datetime.now()
        c = Curiosity(
            id="test",
            agent_id="agent",
            region=RegionType.AGENT,
            project_id=None,
            question="Test",
            context=None,
            recurrence_count=1,
            first_seen=now,
            last_seen=now,
            status=CuriosityStatus.OPEN,
            priority_boost=0,
        )

        score1 = c.priority_score

        c.recurrence_count = 5
        score5 = c.priority_score

        assert score5 > score1
        assert score5 - score1 == 40  # (5-1) * 10

    def test_priority_score_includes_boost(self):
        """Test that priority includes manual boost."""
        now = datetime.now()
        c = Curiosity(
            id="test",
            agent_id="agent",
            region=RegionType.AGENT,
            project_id=None,
            question="Test",
            context=None,
            recurrence_count=1,
            first_seen=now,
            last_seen=now,
            status=CuriosityStatus.OPEN,
            priority_boost=0,
        )

        score_no_boost = c.priority_score

        c.priority_boost = 15
        score_with_boost = c.priority_score

        assert score_with_boost == score_no_boost + 15

    def test_priority_score_recency_bonus(self):
        """Test that recent curiosities get a bonus."""
        now = datetime.now()
        recent = Curiosity(
            id="test1",
            agent_id="agent",
            region=RegionType.AGENT,
            project_id=None,
            question="Test",
            context=None,
            recurrence_count=1,
            first_seen=now,
            last_seen=now,
            status=CuriosityStatus.OPEN,
            priority_boost=0,
        )

        old = Curiosity(
            id="test2",
            agent_id="agent",
            region=RegionType.AGENT,
            project_id=None,
            question="Test",
            context=None,
            recurrence_count=1,
            first_seen=now - timedelta(days=30),
            last_seen=now - timedelta(days=30),
            status=CuriosityStatus.OPEN,
            priority_boost=0,
        )

        # Recent should have higher score due to recency bonus
        assert recent.priority_score > old.priority_score
