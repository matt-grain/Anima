# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for git utilities and git event correlation."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from anima.core import Memory, MemoryKind, ImpactLevel, RegionType
from anima.utils.git import GitContext, get_git_context, get_commit_info, get_recent_commits
from anima.storage import MemoryStore


class TestGitContext:
    """Tests for GitContext dataclass."""

    def test_default_values(self):
        """Test default context has None values."""
        ctx = GitContext()
        assert ctx.commit is None
        assert ctx.branch is None
        assert ctx.is_dirty is False
        assert ctx.commit_time is None

    def test_populated_context(self):
        """Test context with values."""
        now = datetime.now()
        ctx = GitContext(
            commit="abc1234",
            branch="main",
            is_dirty=True,
            commit_time=now,
        )
        assert ctx.commit == "abc1234"
        assert ctx.branch == "main"
        assert ctx.is_dirty is True
        assert ctx.commit_time == now


class TestGetGitContext:
    """Tests for get_git_context function."""

    @patch("anima.utils.git.subprocess.run")
    def test_full_git_context(self, mock_run):
        """Test getting full git context."""
        # Mock all subprocess calls
        def side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "rev-parse" in cmd and "--short" in cmd:
                result.stdout = "abc1234\n"
            elif "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main\n"
            elif "status" in cmd:
                result.stdout = ""
            elif "show" in cmd:
                result.stdout = "2026-01-30 15:30:00 +0100\n"
            return result

        mock_run.side_effect = side_effect

        ctx = get_git_context()
        assert ctx.commit == "abc1234"
        assert ctx.branch == "main"
        assert ctx.is_dirty is False
        assert ctx.commit_time is not None

    @patch("anima.utils.git.subprocess.run")
    def test_dirty_repository(self, mock_run):
        """Test detection of uncommitted changes."""
        def side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "rev-parse" in cmd and "--short" in cmd:
                result.stdout = "abc1234\n"
            elif "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "feature\n"
            elif "status" in cmd:
                result.stdout = "M file.py\n"
            elif "show" in cmd:
                result.stdout = "2026-01-30 15:30:00 +0100\n"
            return result

        mock_run.side_effect = side_effect

        ctx = get_git_context()
        assert ctx.is_dirty is True
        assert ctx.branch == "feature"

    @patch("anima.utils.git.subprocess.run")
    def test_not_a_git_repo(self, mock_run):
        """Test handling of non-git directory."""
        def side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 128
            result.stdout = ""
            return result

        mock_run.side_effect = side_effect

        ctx = get_git_context()
        assert ctx.commit is None
        assert ctx.branch is None

    @patch("anima.utils.git.subprocess.run")
    def test_git_timeout(self, mock_run):
        """Test handling of git command timeout."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("git", 5)

        ctx = get_git_context()
        assert ctx.commit is None
        assert ctx.branch is None


class TestGetCommitInfo:
    """Tests for get_commit_info function."""

    @patch("anima.utils.git.subprocess.run")
    def test_valid_commit(self, mock_run):
        """Test getting info for a valid commit."""
        result = MagicMock()
        result.returncode = 0
        result.stdout = "abc1234567890|2026-01-30 15:30:00 +0100|Add feature\n"
        mock_run.return_value = result

        info = get_commit_info("abc1234")
        assert info is not None
        assert info["hash"] == "abc12345"
        assert info["subject"] == "Add feature"
        assert info["time"] is not None

    @patch("anima.utils.git.subprocess.run")
    def test_invalid_commit(self, mock_run):
        """Test handling of invalid commit ref."""
        result = MagicMock()
        result.returncode = 128
        result.stdout = ""
        mock_run.return_value = result

        info = get_commit_info("invalid")
        assert info is None


class TestGetRecentCommits:
    """Tests for get_recent_commits function."""

    @patch("anima.utils.git.subprocess.run")
    def test_get_commits(self, mock_run):
        """Test getting recent commits."""
        result = MagicMock()
        result.returncode = 0
        result.stdout = (
            "abc1234567890|2026-01-30 15:30:00 +0100|Add feature\n"
            "def5678901234|2026-01-29 10:00:00 +0100|Fix bug\n"
        )
        mock_run.return_value = result

        commits = get_recent_commits(count=5)
        assert len(commits) == 2
        assert commits[0]["subject"] == "Add feature"
        assert commits[1]["subject"] == "Fix bug"


class TestGitCorrelationStorage:
    """Tests for git correlation in storage layer."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary memory store."""
        db_path = tmp_path / "test.db"
        return MemoryStore(db_path=db_path)

    @pytest.fixture
    def sample_agent(self, store):
        """Create and save a sample agent."""
        from anima.core import Agent
        agent = Agent(id="test-agent", name="Test")
        store.save_agent(agent)
        return agent

    @pytest.fixture
    def sample_project(self, store):
        """Create and save a sample project."""
        from anima.core import Project
        project = Project(id="test-project", name="Test", path=Path("/test"))
        store.save_project(project)
        return project

    def test_save_memory_with_git_context(self, store, sample_agent):
        """Test saving a memory with git commit and branch."""
        memory = Memory(
            agent_id=sample_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test with git context",
            original_content="Test with git context",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            git_commit="abc1234",
            git_branch="main",
        )
        store.save_memory(memory)

        retrieved = store.get_memory(memory.id)
        assert retrieved is not None
        assert retrieved.git_commit == "abc1234"
        assert retrieved.git_branch == "main"

    def test_get_memories_by_git_commit(self, store, sample_agent):
        """Test retrieving memories by git commit."""
        # Create memories with different commits
        for i, commit in enumerate(["abc1234", "abc1234", "def5678"]):
            memory = Memory(
                agent_id=sample_agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content=f"Memory {i}",
                original_content=f"Memory {i}",
                impact=ImpactLevel.MEDIUM,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                git_commit=commit,
            )
            store.save_memory(memory)

        # Query by commit
        abc_memories = store.get_memories_by_git_commit("abc1234", agent_id=sample_agent.id)
        assert len(abc_memories) == 2

        def_memories = store.get_memories_by_git_commit("def5678", agent_id=sample_agent.id)
        assert len(def_memories) == 1

    def test_get_memories_by_git_commit_prefix(self, store, sample_agent):
        """Test prefix matching for git commits."""
        memory = Memory(
            agent_id=sample_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Test",
            original_content="Test",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            git_commit="abc1234def",
        )
        store.save_memory(memory)

        # Should match with partial hash
        memories = store.get_memories_by_git_commit("abc1234", agent_id=sample_agent.id)
        assert len(memories) == 1

        # Should match with shorter prefix
        memories = store.get_memories_by_git_commit("abc", agent_id=sample_agent.id)
        assert len(memories) == 1

    def test_get_memories_by_git_branch(self, store, sample_agent):
        """Test retrieving memories by git branch."""
        # Create memories on different branches
        for branch in ["main", "main", "feature/auth"]:
            memory = Memory(
                agent_id=sample_agent.id,
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content=f"On {branch}",
                original_content=f"On {branch}",
                impact=ImpactLevel.MEDIUM,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                git_branch=branch,
            )
            store.save_memory(memory)

        main_memories = store.get_memories_by_git_branch("main", agent_id=sample_agent.id)
        assert len(main_memories) == 2

        feature_memories = store.get_memories_by_git_branch("feature/auth", agent_id=sample_agent.id)
        assert len(feature_memories) == 1

    def test_memory_without_git_context(self, store, sample_agent):
        """Test that git fields are optional."""
        memory = Memory(
            agent_id=sample_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="No git context",
            original_content="No git context",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        store.save_memory(memory)

        retrieved = store.get_memory(memory.id)
        assert retrieved is not None
        assert retrieved.git_commit is None
        assert retrieved.git_branch is None

    def test_combined_git_and_session_query(self, store, sample_agent):
        """Test filtering by both git and session context."""
        # Create memories with different combinations
        memory1 = Memory(
            agent_id=sample_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Session A, Commit X",
            original_content="Session A, Commit X",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            session_id="session-a",
            git_commit="xxx",
        )
        memory2 = Memory(
            agent_id=sample_agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Session B, Commit X",
            original_content="Session B, Commit X",
            impact=ImpactLevel.MEDIUM,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            session_id="session-b",
            git_commit="xxx",
        )
        store.save_memory(memory1)
        store.save_memory(memory2)

        # Both have same commit
        commit_memories = store.get_memories_by_git_commit("xxx", agent_id=sample_agent.id)
        assert len(commit_memories) == 2

        # Different sessions
        session_a = store.get_memories_by_session("session-a", agent_id=sample_agent.id)
        assert len(session_a) == 1
        assert session_a[0].git_commit == "xxx"
