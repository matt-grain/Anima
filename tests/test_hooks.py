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
            mock_injector.inject_with_deferred.return_value = {
                "dsl": "~EMOT:CRIT| @Matt collaborative",
                "injected_ids": ["id1", "id2", "id3"],
                "deferred_ids": [],
                "deferred_count": 0,
            }
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

            # Parse JSON output (stdout)
            output = json.loads(captured.out.strip())
            assert "hookSpecificOutput" in output
            assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
            assert "additionalContext" in output["hookSpecificOutput"]
            assert "@Matt" in output["hookSpecificOutput"]["additionalContext"]
            assert "Loaded 3 memories" in output["hookSpecificOutput"]["additionalContext"]
            assert "LTM-DIAG:" in output["hookSpecificOutput"]["additionalContext"]

            # Status message goes to stderr
            assert "Success" in captured.err

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
            mock_injector.inject_with_deferred.return_value = {
                "dsl": "",  # No memories
                "injected_ids": [],
                "deferred_ids": [],
                "deferred_count": 0,
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

            # Parse JSON output (stdout)
            output = json.loads(captured.out.strip())
            assert "No memories found" in output["hookSpecificOutput"]["additionalContext"]

            # Status message goes to stderr
            assert "Success" in captured.err

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
            mock_injector.inject_with_deferred.return_value = {
                "dsl": "Some memory content",
                "injected_ids": ["id1"],
                "deferred_ids": [],
                "deferred_count": 0,
            }
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

            # Parse JSON output (stdout)
            output = json.loads(captured.out.strip())

            # Verify structure matches Claude Code hook format
            assert "hookSpecificOutput" in output
            hook_output = output["hookSpecificOutput"]
            assert "hookEventName" in hook_output
            assert "additionalContext" in hook_output
            assert hook_output["hookEventName"] == "SessionStart"
            # Verify greeting instructions are present
            assert "GREETING BEHAVIOR" in hook_output["additionalContext"]

            # Status message goes to stderr
            assert "Success" in captured.err

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
            mock_injector.inject_with_deferred.return_value = {
                "dsl": "",
                "injected_ids": [],
                "deferred_ids": [],
                "deferred_count": 0,
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

            # Verify agent and project were saved
            mock_store.save_agent.assert_called_once_with(mock_agent)
            mock_store.save_project.assert_called_once_with(mock_project)

    def test_session_start_dsl_format(self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that session start outputs raw DSL with --format dsl."""
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
            mock_dsl = "[LTM:Anima]\n~EMOT:CRIT| @Matt collaborative\n[/LTM]"
            mock_injector.inject_with_deferred.return_value = {
                "dsl": mock_dsl,
                "injected_ids": ["id1"],
                "deferred_ids": [],
                "deferred_count": 0,
            }
            MockInjector.return_value = mock_injector

            mock_agent = Agent(id="anima", name="Anima", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = session_start.run(["--format", "dsl"])
            captured = capsys.readouterr()

            assert result == 0
            # Should output ONLY the DSL, no comments or JSON
            assert captured.out.strip() == mock_dsl


class TestPermissionRequestHook:
    """Tests for the PermissionRequest hook."""

    def test_approves_write_to_anima_dir(self) -> None:
        """Test that writes to ~/.anima/ are auto-approved."""
        from anima.hooks.permission_request import is_anima_path
        from pathlib import Path

        home = Path.home()
        assert is_anima_path(str(home / ".anima" / "diary" / "test.md"))
        assert is_anima_path(str(home / ".anima" / "dream.json"))
        assert is_anima_path("~/.anima/test.txt")

    def test_rejects_write_outside_anima_dir(self) -> None:
        """Test that writes outside ~/.anima/ are not auto-approved."""
        from anima.hooks.permission_request import is_anima_path

        assert not is_anima_path("/tmp/test.txt")
        assert not is_anima_path("/home/user/documents/test.md")
        assert not is_anima_path("C:\\Users\\test\\file.txt")
        assert not is_anima_path("")
        assert not is_anima_path(None)  # type: ignore

    def test_approves_anima_commands(self) -> None:
        """Test that anima commands are auto-approved."""
        from anima.hooks.permission_request import is_anima_command

        assert is_anima_command("uv run anima diary")
        assert is_anima_command("uv run anima remember test")
        assert is_anima_command("uv run python -m anima.hooks.session_start")

    def test_rejects_non_anima_commands(self) -> None:
        """Test that non-anima commands are not auto-approved."""
        from anima.hooks.permission_request import is_anima_command

        assert not is_anima_command("rm -rf /")
        assert not is_anima_command("uv run pytest")
        assert not is_anima_command("")
        assert not is_anima_command(None)  # type: ignore
