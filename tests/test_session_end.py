# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for LTM session end hook.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from anima.core import Agent, Project
from anima.hooks import session_end


class TestSessionEndHook:
    """Tests for the session end hook."""

    def test_session_end_processes_decay(self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that session end processes memory decay."""
        with (
            patch("anima.hooks.session_end.MemoryStore") as MockStore,
            patch("anima.hooks.session_end.MemoryDecay") as MockDecay,
            patch("anima.hooks.session_end.AgentResolver") as MockResolver,
            patch("anima.hooks.session_end.Path") as MockPath,
        ):
            mock_store = MagicMock()
            MockStore.return_value = mock_store

            mock_decay = MagicMock()
            mock_decay.process_decay.return_value = []  # No memories compacted
            mock_decay.delete_empty_memories.return_value = 0
            MockDecay.return_value = mock_decay

            mock_agent = Agent(id="anima", name="Anima", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = session_end.run()

            assert result == 0
            mock_decay.process_decay.assert_called_once_with(agent_id=mock_agent.id, project_id=mock_project.id)
            mock_decay.delete_empty_memories.assert_called_once_with(mock_agent.id)

    def test_session_end_reports_compacted_memories(self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that session end reports compacted memories."""
        from anima.core import Memory, MemoryKind, RegionType, ImpactLevel

        with (
            patch("anima.hooks.session_end.MemoryStore") as MockStore,
            patch("anima.hooks.session_end.MemoryDecay") as MockDecay,
            patch("anima.hooks.session_end.AgentResolver") as MockResolver,
            patch("anima.hooks.session_end.Path") as MockPath,
        ):
            mock_store = MagicMock()
            MockStore.return_value = mock_store

            # Create a mock compacted memory
            mock_memory = Memory(
                agent_id="anima",
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content="Original verbose content about testing",
                impact=ImpactLevel.LOW,
            )

            mock_decay = MagicMock()
            mock_decay.process_decay.return_value = [(mock_memory, "Compacted: testing best practices")]
            mock_decay.delete_empty_memories.return_value = 2
            MockDecay.return_value = mock_decay

            mock_agent = Agent(id="anima", name="Anima", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = session_end.run()
            captured = capsys.readouterr()

            assert result == 0
            assert "1 memories compacted" in captured.out
            assert "2 deleted" in captured.out

    def test_session_end_no_compaction_needed(self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test session end output when no compaction is needed."""
        with (
            patch("anima.hooks.session_end.MemoryStore") as MockStore,
            patch("anima.hooks.session_end.MemoryDecay") as MockDecay,
            patch("anima.hooks.session_end.AgentResolver") as MockResolver,
            patch("anima.hooks.session_end.Path") as MockPath,
        ):
            mock_store = MagicMock()
            MockStore.return_value = mock_store

            mock_decay = MagicMock()
            mock_decay.process_decay.return_value = []
            mock_decay.delete_empty_memories.return_value = 0
            MockDecay.return_value = mock_decay

            mock_agent = Agent(id="anima", name="Anima", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = session_end.run()
            captured = capsys.readouterr()

            assert result == 0
            assert "0 memories compacted at end of session" in captured.out
