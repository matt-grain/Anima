# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Tests for the setup tool.

Tests the installation of commands, skills, and hook configuration.
"""

import json
from unittest.mock import patch

import pytest

from anima.tools.setup import (
    setup_commands,
    setup_skills,
    patch_subagents,
    setup_hooks,
)


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def mock_package_commands(tmp_path):
    """Create mock package commands directory."""
    commands_dir = tmp_path / "mock_commands"
    commands_dir.mkdir()

    # Create some mock command files
    (commands_dir / "test-command.md").write_text("# Test Command")
    (commands_dir / "another-command.md").write_text("# Another Command")

    return commands_dir


@pytest.fixture
def mock_package_skills(tmp_path):
    """Create mock package skills directory."""
    skills_dir = tmp_path / "mock_skills"
    skills_dir.mkdir()

    # Create a mock skill
    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill")

    return skills_dir


class TestSetupCommands:
    """Test command installation."""

    def test_copies_commands_to_agent_workflows(self, temp_project, mock_package_commands):
        """Should copy commands to .agent/workflows for Anima projects."""
        (temp_project / ".agent").mkdir()

        with patch("anima.tools.setup.get_package_commands_dir", return_value=mock_package_commands):
            copied, skipped = setup_commands(temp_project)

        assert copied == 2
        assert skipped == 0
        assert (temp_project / ".agent" / "workflows" / "test-command.md").exists()
        assert (temp_project / ".agent" / "workflows" / "another-command.md").exists()

    def test_copies_commands_to_claude_commands(self, temp_project, mock_package_commands):
        """Should copy commands to .claude/commands for Claude projects."""
        (temp_project / ".claude").mkdir()

        with patch("anima.tools.setup.get_package_commands_dir", return_value=mock_package_commands):
            copied, skipped = setup_commands(temp_project)

        assert copied == 2
        assert (temp_project / ".claude" / "commands" / "test-command.md").exists()

    def test_skips_existing_commands_without_force(self, temp_project, mock_package_commands):
        """Should skip existing commands when force=False."""
        workflows_dir = temp_project / ".agent" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "test-command.md").write_text("# Existing")

        with patch("anima.tools.setup.get_package_commands_dir", return_value=mock_package_commands):
            copied, skipped = setup_commands(temp_project, force=False)

        assert copied == 1  # Only another-command.md
        assert skipped == 1  # test-command.md skipped
        assert (workflows_dir / "test-command.md").read_text() == "# Existing"

    def test_overwrites_with_force(self, temp_project, mock_package_commands):
        """Should overwrite existing commands when force=True."""
        workflows_dir = temp_project / ".agent" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "test-command.md").write_text("# Existing")

        with patch("anima.tools.setup.get_package_commands_dir", return_value=mock_package_commands):
            copied, skipped = setup_commands(temp_project, force=True)

        assert copied == 2
        assert skipped == 0
        assert (workflows_dir / "test-command.md").read_text() == "# Test Command"


class TestSetupSkills:
    """Test skill installation."""

    def test_copies_skills_to_agent_skills(self, temp_project, mock_package_skills):
        """Should copy skills to .agent/skills."""
        (temp_project / ".agent").mkdir()

        with patch("anima.tools.setup.get_package_skills_dir", return_value=mock_package_skills):
            copied, skipped = setup_skills(temp_project)

        assert copied == 1
        assert skipped == 0
        assert (temp_project / ".agent" / "skills" / "test-skill" / "SKILL.md").exists()

    def test_skips_existing_skills_without_force(self, temp_project, mock_package_skills):
        """Should skip existing skills when force=False."""
        skills_dir = temp_project / ".agent" / "skills" / "test-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("# Existing")

        with patch("anima.tools.setup.get_package_skills_dir", return_value=mock_package_skills):
            copied, skipped = setup_skills(temp_project, force=False)

        assert copied == 0
        assert skipped == 1


class TestPatchSubagents:
    """Test agent patching functionality."""

    def test_patches_agent_without_marker(self, temp_project):
        """Should add subagent marker to agents missing it."""
        agents_dir = temp_project / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text("---\nname: test\n---\n# Agent")

        patched, skipped, disabled = patch_subagents(temp_project)

        assert patched == 1
        assert skipped == 0
        assert disabled == 0

        content = agent_file.read_text()
        assert "anima:" in content
        assert "subagent: true" in content

    def test_skips_agent_with_marker(self, temp_project):
        """Should skip agents that already have the marker."""
        agents_dir = temp_project / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text("---\nname: test\nanima:\n  subagent: true\n---\n")

        patched, skipped, disabled = patch_subagents(temp_project)

        assert patched == 0
        assert skipped == 1
        assert disabled == 0

    def test_disables_agent_without_frontmatter(self, temp_project):
        """Should disable agents without YAML frontmatter."""
        agents_dir = temp_project / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        agent_file = agents_dir / "bad-agent.md"
        agent_file.write_text("# Agent without frontmatter")

        patched, skipped, disabled = patch_subagents(temp_project)

        assert patched == 0
        assert skipped == 0
        assert disabled == 1
        assert not agent_file.exists()
        assert (agents_dir / "bad-agent.md.disabled").exists()


class TestSetupHooks:
    """Test hook configuration."""

    def test_creates_settings_json_with_hooks(self, temp_project):
        """Should create .claude/settings.json with LTM hooks."""
        claude_dir = temp_project / ".claude"
        claude_dir.mkdir()

        result = setup_hooks(temp_project)

        assert result is True
        settings_file = claude_dir / "settings.json"
        assert settings_file.exists()

        settings = json.loads(settings_file.read_text())
        assert "hooks" in settings
        assert "SessionStart" in settings["hooks"]
        assert "Stop" in settings["hooks"]

    def test_merges_with_existing_settings(self, temp_project):
        """Should merge hooks into existing settings."""
        claude_dir = temp_project / ".claude"
        claude_dir.mkdir()

        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"existing": "value"}))

        setup_hooks(temp_project)

        settings = json.loads(settings_file.read_text())
        assert settings["existing"] == "value"
        assert "hooks" in settings

    def test_skips_when_hooks_exist_without_force(self, temp_project):
        """Should skip when hooks already configured and force=False."""
        claude_dir = temp_project / ".claude"
        claude_dir.mkdir()

        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"hooks": {"SessionStart": []}}))

        result = setup_hooks(temp_project, force=False)

        assert result is False

    def test_overwrites_hooks_with_force(self, temp_project):
        """Should overwrite hooks when force=True."""
        claude_dir = temp_project / ".claude"
        claude_dir.mkdir()

        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"hooks": {"SessionStart": []}}))

        result = setup_hooks(temp_project, force=True)

        assert result is True
        settings = json.loads(settings_file.read_text())
        # Should have the LTM hooks now
        assert len(settings["hooks"]["SessionStart"]) > 0

    def test_prefers_settings_local_json(self, temp_project):
        """Should prefer settings.local.json over settings.json."""
        claude_dir = temp_project / ".claude"
        claude_dir.mkdir()

        # Create both files
        (claude_dir / "settings.json").write_text("{}")
        local_settings = claude_dir / "settings.local.json"
        local_settings.write_text("{}")

        setup_hooks(temp_project)

        # Should have modified local settings
        local_data = json.loads(local_settings.read_text())
        assert "hooks" in local_data

        # Shared settings should be unchanged
        shared_data = json.loads((claude_dir / "settings.json").read_text())
        assert "hooks" not in shared_data
