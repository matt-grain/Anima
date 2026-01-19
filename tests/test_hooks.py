# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Tests for LTM hooks.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from anima.core import Agent, Project
from anima.hooks import session_start


class TestSessionStartHook:
    """Tests for the SessionStart hook."""

    def test_session_start_with_memories(self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test session start with memories available."""
        with (
            patch("anima.hooks.session_start.MemoryStore") as MockStore,
            patch("anima.hooks.session_start.MemoryInjector") as MockInjector,
            patch("anima.hooks.session_start.AgentResolver") as MockResolver,
            patch("anima.hooks.session_start.Path") as MockPath,
        ):
            # Setup mocks
            mock_store = MagicMock()
            MockStore.return_value = mock_store

            mock_injector = MagicMock()
            mock_injector.inject.return_value = "~EMOT:CRIT| @Matt collaborative"
            mock_injector.get_stats.return_value = {
                "total": 3,
                "agent_memories": 2,
                "project_memories": 1,
                "budget_tokens": 10000,
                "priority_counts": {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 1, "LOW": 0},
            }
            MockInjector.return_value = mock_injector

            mock_agent = Agent(id="anima", name="Anima", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = session_start.run(["--format", "json"])
            captured = capsys.readouterr()

            assert result == 0

            # Parse output - first line is JSON, second line is status message
            lines = captured.out.strip().split("\n")
            output = json.loads(lines[0])
            assert "hookSpecificOutput" in output
            assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
            assert "additionalContext" in output["hookSpecificOutput"]
            assert "@Matt" in output["hookSpecificOutput"]["additionalContext"]
            assert "Loaded 3 memories" in output["hookSpecificOutput"]["additionalContext"]
            assert "LTM-DIAG:" in output["hookSpecificOutput"]["additionalContext"]

            # Check status message
            assert len(lines) >= 2
            assert "Success: 3 memories loaded" in lines[1]

    def test_session_start_no_memories(self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test session start with no memories."""
        with (
            patch("anima.hooks.session_start.MemoryStore") as MockStore,
            patch("anima.hooks.session_start.MemoryInjector") as MockInjector,
            patch("anima.hooks.session_start.AgentResolver") as MockResolver,
            patch("anima.hooks.session_start.Path") as MockPath,
        ):
            mock_store = MagicMock()
            MockStore.return_value = mock_store

            mock_injector = MagicMock()
            mock_injector.inject.return_value = ""  # No memories
            MockInjector.return_value = mock_injector

            mock_agent = Agent(id="anima", name="Anima", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = session_start.run(["--format", "json"])
            captured = capsys.readouterr()

            assert result == 0

            # Parse output - first line is JSON, second line is status message
            lines = captured.out.strip().split("\n")
            output = json.loads(lines[0])
            assert "No memories found" in output["hookSpecificOutput"]["additionalContext"]

            # Check status message
            assert len(lines) >= 2
            assert "Success: No memories found yet" in lines[1]

    def test_session_start_json_format(self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that session start outputs valid JSON."""
        with (
            patch("anima.hooks.session_start.MemoryStore") as MockStore,
            patch("anima.hooks.session_start.MemoryInjector") as MockInjector,
            patch("anima.hooks.session_start.AgentResolver") as MockResolver,
            patch("anima.hooks.session_start.Path") as MockPath,
        ):
            mock_store = MagicMock()
            MockStore.return_value = mock_store

            mock_injector = MagicMock()
            mock_injector.inject.return_value = "Some memory content"
            mock_injector.get_stats.return_value = {
                "total": 1,
                "agent_memories": 1,
                "project_memories": 0,
                "budget_tokens": 10000,
                "priority_counts": {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 0, "LOW": 0},
            }
            MockInjector.return_value = mock_injector

            mock_agent = Agent(id="anima", name="Anima", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            session_start.run(["--format", "json"])
            captured = capsys.readouterr()

            # Parse output - first line is JSON, second line is status message
            lines = captured.out.strip().split("\n")
            output = json.loads(lines[0])

            # Verify structure matches Claude Code hook format
            assert "hookSpecificOutput" in output
            hook_output = output["hookSpecificOutput"]
            assert "hookEventName" in hook_output
            assert "additionalContext" in hook_output
            assert hook_output["hookEventName"] == "SessionStart"
            # Verify greeting instructions are present
            assert "GREETING BEHAVIOR" in hook_output["additionalContext"]

            # Check status message is present
            assert len(lines) >= 2
            assert "Success:" in lines[1]

    def test_session_start_saves_agent_and_project(self, temp_project_dir: Path) -> None:
        """Test that session start saves agent and project."""
        with (
            patch("anima.hooks.session_start.MemoryStore") as MockStore,
            patch("anima.hooks.session_start.MemoryInjector") as MockInjector,
            patch("anima.hooks.session_start.AgentResolver") as MockResolver,
            patch("anima.hooks.session_start.Path") as MockPath,
        ):
            mock_store = MagicMock()
            MockStore.return_value = mock_store

            mock_injector = MagicMock()
            mock_injector.inject.return_value = ""
            MockInjector.return_value = mock_injector

            mock_agent = Agent(id="anima", name="Anima", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            session_start.run(["--format", "json"])

            # Verify agent and project were saved
            mock_store.save_agent.assert_called_once_with(mock_agent)
            mock_store.save_project.assert_called_once_with(mock_project)
