# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Pytest fixtures for LTM tests.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from anima.core import Agent, Memory, MemoryKind, Project, RegionType, ImpactLevel
from anima.core.config import reload_config, LTMConfig
from anima.storage import MemoryStore


def _embedder_available() -> bool:
    """Check if the FastEmbed model is available (cached locally)."""
    try:
        from anima.embeddings.embedder import get_embedder
        # This will fail in CI where model isn't cached
        get_embedder(quiet=True)
        return True
    except Exception:
        return False


# Check once at module load
_EMBEDDER_AVAILABLE = None


def embedder_available() -> bool:
    """Cached check for embedder availability."""
    global _EMBEDDER_AVAILABLE
    if _EMBEDDER_AVAILABLE is None:
        # Skip the check entirely in CI to avoid download attempts
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
            _EMBEDDER_AVAILABLE = False
        else:
            _EMBEDDER_AVAILABLE = _embedder_available()
    return _EMBEDDER_AVAILABLE


requires_embedder = pytest.mark.skipif(
    not embedder_available(),
    reason="FastEmbed model not available (skipped in CI)"
)


@pytest.fixture(autouse=True)
def reset_config(monkeypatch, tmp_path: Path):
    """Reset config to defaults before each test.

    This prevents config changes from one test affecting others.
    """
    # Point config to a non-existent file so defaults are used
    config_path = tmp_path / "nonexistent_config.json"
    monkeypatch.setattr(LTMConfig, "get_config_path", lambda: config_path)
    reload_config()
    yield
    # Reset after test too
    reload_config()


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def memory_store(temp_db_path: Path) -> MemoryStore:
    """Create a MemoryStore with a temporary database."""
    return MemoryStore(db_path=temp_db_path)


@pytest.fixture
def test_agent() -> Agent:
    """Create a test agent."""
    return Agent(id="test-agent", name="Test Agent", definition_path=None, signing_key=None)


@pytest.fixture
def anima_agent() -> Agent:
    """Create the default Anima agent."""
    return Agent(id="anima", name="Anima", definition_path=None, signing_key=None)


@pytest.fixture
def test_project() -> Project:
    """Create a test project."""
    return Project(id="test-project", name="Test Project", path=Path("/tmp/test-project"))


@pytest.fixture
def sample_memory(test_agent: Agent, test_project: Project) -> Memory:
    """Create a sample memory for testing."""
    return Memory(
        agent_id=test_agent.id,
        region=RegionType.PROJECT,
        project_id=test_project.id,
        kind=MemoryKind.ARCHITECTURAL,
        content="Use pytest for testing",
        impact=ImpactLevel.MEDIUM,
    )


@pytest.fixture
def sample_agent_memory(test_agent: Agent) -> Memory:
    """Create a sample agent-wide memory for testing."""
    return Memory(
        agent_id=test_agent.id,
        region=RegionType.AGENT,
        project_id=None,
        kind=MemoryKind.EMOTIONAL,
        content="@User collaborative style",
        impact=ImpactLevel.CRITICAL,
    )


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        # Create .git directory to simulate a git repo
        (project_path / ".git").mkdir()
        yield project_path


@pytest.fixture
def populated_store(memory_store: MemoryStore, test_agent: Agent, test_project: Project) -> MemoryStore:
    """Create a store with some test data."""
    # Save agent and project
    memory_store.save_agent(test_agent)
    memory_store.save_project(test_project)

    # Add various memories
    memories = [
        Memory(
            agent_id=test_agent.id,
            region=RegionType.AGENT,
            project_id=None,
            kind=MemoryKind.EMOTIONAL,
            content="@Matt collaborative style, likes humor",
            impact=ImpactLevel.CRITICAL,
        ),
        Memory(
            agent_id=test_agent.id,
            region=RegionType.PROJECT,
            project_id=test_project.id,
            kind=MemoryKind.ARCHITECTURAL,
            content="Use SQLite for storage",
            impact=ImpactLevel.HIGH,
        ),
        Memory(
            agent_id=test_agent.id,
            region=RegionType.PROJECT,
            project_id=test_project.id,
            kind=MemoryKind.LEARNINGS,
            content="Never use print for logging",
            impact=ImpactLevel.MEDIUM,
        ),
        Memory(
            agent_id=test_agent.id,
            region=RegionType.AGENT,
            project_id=None,
            kind=MemoryKind.ACHIEVEMENTS,
            content="Built LTM system in single session",
            impact=ImpactLevel.HIGH,
        ),
    ]

    for memory in memories:
        memory_store.save_memory(memory)

    return memory_store
