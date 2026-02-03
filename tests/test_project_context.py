# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for project context fingerprinting (Phase 3A)."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime

from anima.core import RegionType
from anima.lifecycle.project_context import (
    ProjectFingerprint,
    get_project_relevant_memories,
    README_FILES,
    MAX_README_CHARS,
)


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory with README and pyproject.toml."""
    readme = tmp_path / "README.md"
    readme.write_text("# Test Project\n\nThis is a test project for unit testing.\n\n## Features\n- Feature 1\n- Feature 2")

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\n')

    return tmp_path


class TestProjectFingerprint:
    """Tests for ProjectFingerprint."""

    @patch("anima.lifecycle.project_context.embed_text")
    @patch("anima.lifecycle.project_context.get_recent_commits")
    def test_from_directory_extracts_readme(self, mock_commits, mock_embed, temp_project):
        """Extracts README content."""
        mock_commits.return_value = []
        mock_embed.return_value = [0.1, 0.2, 0.3]

        fingerprint = ProjectFingerprint.from_directory(temp_project)

        assert fingerprint.readme_excerpt is not None
        assert "Test Project" in fingerprint.readme_excerpt
        assert "unit testing" in fingerprint.readme_excerpt

    @patch("anima.lifecycle.project_context.embed_text")
    @patch("anima.lifecycle.project_context.get_recent_commits")
    def test_from_directory_detects_python(self, mock_commits, mock_embed, temp_project):
        """Detects Python project type."""
        mock_commits.return_value = []
        mock_embed.return_value = [0.1, 0.2, 0.3]

        fingerprint = ProjectFingerprint.from_directory(temp_project)

        assert fingerprint.metadata_type == "python"

    @patch("anima.lifecycle.project_context.embed_text")
    @patch("anima.lifecycle.project_context.get_recent_commits")
    def test_from_directory_includes_commits(self, mock_commits, mock_embed, temp_project):
        """Includes recent commit messages."""
        mock_commits.return_value = [
            {"message": "Add feature X"},
            {"message": "Fix bug Y"},
        ]
        mock_embed.return_value = [0.1, 0.2, 0.3]

        fingerprint = ProjectFingerprint.from_directory(temp_project)

        assert len(fingerprint.recent_commits) == 2
        assert "Add feature X" in fingerprint.recent_commits

    @patch("anima.lifecycle.project_context.embed_text")
    @patch("anima.lifecycle.project_context.get_recent_commits")
    def test_from_directory_without_commits(self, mock_commits, mock_embed, temp_project):
        """Works without git commits."""
        mock_commits.side_effect = Exception("Not a git repo")
        mock_embed.return_value = [0.1, 0.2, 0.3]

        fingerprint = ProjectFingerprint.from_directory(temp_project)

        assert fingerprint.recent_commits == []
        assert fingerprint.readme_excerpt is not None

    @patch("anima.lifecycle.project_context.embed_text")
    def test_from_directory_no_readme(self, mock_embed, tmp_path):
        """Works without README."""
        mock_embed.return_value = [0.1, 0.2, 0.3]

        fingerprint = ProjectFingerprint.from_directory(tmp_path)

        assert fingerprint.readme_excerpt is None
        assert fingerprint.project_name == tmp_path.name


class TestProjectFingerprintToText:
    """Tests for fingerprint text conversion."""

    def test_to_text_includes_name(self):
        """Text includes project name."""
        fp = ProjectFingerprint(project_name="my-project")
        text = fp.to_text()

        assert "Project: my-project" in text

    def test_to_text_includes_type(self):
        """Text includes project type."""
        fp = ProjectFingerprint(
            project_name="my-project",
            metadata_type="python",
        )
        text = fp.to_text()

        assert "python project" in text

    def test_to_text_includes_readme(self):
        """Text includes README excerpt."""
        fp = ProjectFingerprint(
            project_name="my-project",
            readme_excerpt="This is a great project",
        )
        text = fp.to_text()

        assert "Description: This is a great project" in text

    def test_to_text_includes_commits(self):
        """Text includes recent commits."""
        fp = ProjectFingerprint(
            project_name="my-project",
            recent_commits=["Add X", "Fix Y", "Update Z"],
        )
        text = fp.to_text()

        assert "Recent work:" in text
        assert "Add X" in text


class TestExtractReadme:
    """Tests for README extraction."""

    def test_extracts_md_readme(self, tmp_path):
        """Extracts from README.md."""
        readme = tmp_path / "README.md"
        readme.write_text("# Hello World")

        result = ProjectFingerprint._extract_readme(tmp_path)

        assert result == "# Hello World"

    def test_extracts_rst_readme(self, tmp_path):
        """Extracts from README.rst."""
        readme = tmp_path / "README.rst"
        readme.write_text("Hello RST")

        result = ProjectFingerprint._extract_readme(tmp_path)

        assert result == "Hello RST"

    def test_truncates_long_readme(self, tmp_path):
        """Truncates very long README."""
        readme = tmp_path / "README.md"
        readme.write_text("A" * 5000)

        result = ProjectFingerprint._extract_readme(tmp_path)

        assert len(result) <= MAX_README_CHARS

    def test_no_readme(self, tmp_path):
        """Returns None when no README exists."""
        result = ProjectFingerprint._extract_readme(tmp_path)

        assert result is None


class TestDetectProjectType:
    """Tests for project type detection."""

    def test_detects_python_pyproject(self, tmp_path):
        """Detects Python from pyproject.toml."""
        (tmp_path / "pyproject.toml").touch()

        result = ProjectFingerprint._detect_project_type(tmp_path)

        assert result == "python"

    def test_detects_node(self, tmp_path):
        """Detects Node.js from package.json."""
        (tmp_path / "package.json").touch()

        result = ProjectFingerprint._detect_project_type(tmp_path)

        assert result == "node"

    def test_detects_rust(self, tmp_path):
        """Detects Rust from Cargo.toml."""
        (tmp_path / "Cargo.toml").touch()

        result = ProjectFingerprint._detect_project_type(tmp_path)

        assert result == "rust"

    def test_detects_go(self, tmp_path):
        """Detects Go from go.mod."""
        (tmp_path / "go.mod").touch()

        result = ProjectFingerprint._detect_project_type(tmp_path)

        assert result == "go"

    def test_unknown_project(self, tmp_path):
        """Returns None for unknown project type."""
        result = ProjectFingerprint._detect_project_type(tmp_path)

        assert result is None


class TestFindRelevantMemories:
    """Tests for finding relevant PROJECT memories."""

    @patch("anima.lifecycle.project_context.find_similar")
    def test_returns_matching_memories(self, mock_find_similar):
        """Returns PROJECT memories matching fingerprint."""
        # Setup mock store
        mock_store = MagicMock()
        mock_store.get_memories_with_embeddings.return_value = [
            ("mem1", "Always call Task-Review", [0.1, 0.2, 0.3]),
            ("mem2", "Use pytest for testing", [0.4, 0.5, 0.6]),
        ]

        mock_memory1 = MagicMock()
        mock_memory1.id = "mem1"
        mock_memory2 = MagicMock()
        mock_memory2.id = "mem2"
        mock_store.get_memories_for_agent.return_value = [mock_memory1, mock_memory2]

        # Setup mock similarity results
        mock_result1 = MagicMock()
        mock_result1.item = "mem1"
        mock_result2 = MagicMock()
        mock_result2.item = "mem2"
        mock_find_similar.return_value = [mock_result1, mock_result2]

        fingerprint = ProjectFingerprint(
            project_name="test",
            _embedding=[0.1, 0.2, 0.3],
        )

        memories = fingerprint.find_relevant_memories(
            store=mock_store,
            agent_id="anima",
            project_id="test_project",
        )

        assert len(memories) == 2
        # Verify region filter was used
        mock_store.get_memories_with_embeddings.assert_called_once()
        call_kwargs = mock_store.get_memories_with_embeddings.call_args[1]
        assert call_kwargs.get("region") == RegionType.PROJECT

    def test_returns_empty_when_no_embeddings(self):
        """Returns empty when no embedded memories exist."""
        mock_store = MagicMock()
        mock_store.get_memories_with_embeddings.return_value = []

        fingerprint = ProjectFingerprint(
            project_name="test",
            _embedding=[0.1, 0.2, 0.3],
        )

        memories = fingerprint.find_relevant_memories(
            store=mock_store,
            agent_id="anima",
            project_id="test_project",
        )

        assert memories == []


class TestGetProjectRelevantMemories:
    """Tests for convenience function."""

    @patch("anima.lifecycle.project_context.ProjectFingerprint")
    def test_creates_fingerprint_and_searches(self, mock_fp_class, tmp_path):
        """Convenience function creates fingerprint and searches."""
        mock_fp = MagicMock()
        mock_fp.find_relevant_memories.return_value = []
        mock_fp_class.from_directory.return_value = mock_fp

        mock_store = MagicMock()

        get_project_relevant_memories(
            project_dir=tmp_path,
            store=mock_store,
            agent_id="anima",
            project_id="test",
        )

        mock_fp_class.from_directory.assert_called_once()
        mock_fp.find_relevant_memories.assert_called_once()


class TestEmbeddingProperty:
    """Tests for embedding property."""

    @patch("anima.lifecycle.project_context.embed_text")
    def test_generates_embedding_lazily(self, mock_embed):
        """Embedding is generated on first access."""
        mock_embed.return_value = [0.1, 0.2, 0.3]

        fp = ProjectFingerprint(project_name="test")

        # Not called yet
        assert fp._embedding is None

        # Access embedding
        embedding = fp.embedding

        # Now generated
        assert embedding == [0.1, 0.2, 0.3]
        mock_embed.assert_called_once()

    @patch("anima.lifecycle.project_context.embed_text")
    def test_caches_embedding(self, mock_embed):
        """Embedding is cached after first generation."""
        mock_embed.return_value = [0.1, 0.2, 0.3]

        fp = ProjectFingerprint(project_name="test")

        # Access twice
        fp.embedding
        fp.embedding

        # Only called once
        mock_embed.assert_called_once()
