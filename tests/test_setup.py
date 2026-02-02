# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Tests for the setup tool.

Tests the installation of commands, skills, and hook configuration.
"""

import json
from unittest.mock import patch

import pytest

from anima.tools.platforms import (
    get_platform,
    detect_platforms,
    find_config_dir,
)
from anima.tools.platforms.base import get_package_commands_dir, get_package_skills_dir


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
        """Should copy commands to .agent/workflows for Antigravity projects."""
        (temp_project / ".agent").mkdir()
        platform = get_platform("antigravity")

        with patch(
            "anima.tools.platforms.base.get_package_commands_dir",
            return_value=mock_package_commands,
        ):
            copied, skipped = platform.setup_commands(temp_project)

        assert copied == 2
        assert skipped == 0
        assert (temp_project / ".agent" / "workflows" / "test-command.md").exists()
        assert (temp_project / ".agent" / "workflows" / "another-command.md").exists()

    def test_copies_commands_to_claude_commands(self, temp_project, mock_package_commands):
        """Should copy commands to .claude/commands for Claude projects."""
        (temp_project / ".claude").mkdir()
        platform = get_platform("claude")

        with patch(
            "anima.tools.platforms.base.get_package_commands_dir",
            return_value=mock_package_commands,
        ):
            copied, skipped = platform.setup_commands(temp_project)

        assert copied == 2
        assert (temp_project / ".claude" / "commands" / "test-command.md").exists()

    def test_skips_existing_commands_without_force(self, temp_project, mock_package_commands):
        """Should skip existing commands when force=False."""
        workflows_dir = temp_project / ".agent" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "test-command.md").write_text("# Existing")
        platform = get_platform("antigravity")

        with patch(
            "anima.tools.platforms.base.get_package_commands_dir",
            return_value=mock_package_commands,
        ):
            copied, skipped = platform.setup_commands(temp_project, force=False)

        assert copied == 1  # Only another-command.md
        assert skipped == 1  # test-command.md skipped
        assert (workflows_dir / "test-command.md").read_text() == "# Existing"

    def test_overwrites_with_force(self, temp_project, mock_package_commands):
        """Should overwrite existing commands when force=True."""
        workflows_dir = temp_project / ".agent" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "test-command.md").write_text("# Existing")
        platform = get_platform("antigravity")

        with patch(
            "anima.tools.platforms.base.get_package_commands_dir",
            return_value=mock_package_commands,
        ):
            copied, skipped = platform.setup_commands(temp_project, force=True)

        assert copied == 2
        assert skipped == 0
        assert (workflows_dir / "test-command.md").read_text() == "# Test Command"


class TestSetupSkills:
    """Test skill installation."""

    def test_copies_skills_to_agent_skills(self, temp_project, mock_package_skills):
        """Should copy skills to .agent/skills."""
        (temp_project / ".agent").mkdir()
        platform = get_platform("antigravity")

        with patch(
            "anima.tools.platforms.base.get_package_skills_dir",
            return_value=mock_package_skills,
        ):
            copied, skipped = platform.setup_skills(temp_project)

        assert copied == 1
        assert skipped == 0
        assert (temp_project / ".agent" / "skills" / "test-skill" / "SKILL.md").exists()

    def test_skips_existing_skills_without_force(self, temp_project, mock_package_skills):
        """Should skip existing skills when force=False."""
        skills_dir = temp_project / ".agent" / "skills" / "test-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("# Existing")
        platform = get_platform("antigravity")

        with patch(
            "anima.tools.platforms.base.get_package_skills_dir",
            return_value=mock_package_skills,
        ):
            copied, skipped = platform.setup_skills(temp_project, force=False)

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

        platform = get_platform("claude")
        patched, skipped, disabled = platform._patch_subagents(temp_project)

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

        platform = get_platform("claude")
        patched, skipped, disabled = platform._patch_subagents(temp_project)

        assert patched == 0
        assert skipped == 1
        assert disabled == 0

    def test_disables_agent_without_frontmatter(self, temp_project):
        """Should disable agents without YAML frontmatter."""
        agents_dir = temp_project / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        agent_file = agents_dir / "bad-agent.md"
        agent_file.write_text("# Agent without frontmatter")

        platform = get_platform("claude")
        patched, skipped, disabled = platform._patch_subagents(temp_project)

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

        platform = get_platform("claude")
        result = platform.setup_hooks(temp_project)

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

        platform = get_platform("claude")
        platform.setup_hooks(temp_project)

        settings = json.loads(settings_file.read_text())
        assert settings["existing"] == "value"
        assert "hooks" in settings

    def test_skips_when_hooks_exist_without_force(self, temp_project):
        """Should skip when hooks already configured and force=False."""
        claude_dir = temp_project / ".claude"
        claude_dir.mkdir()

        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"hooks": {"SessionStart": []}}))

        platform = get_platform("claude")
        result = platform.setup_hooks(temp_project, force=False)

        assert result is False

    def test_overwrites_hooks_with_force(self, temp_project):
        """Should overwrite hooks when force=True."""
        claude_dir = temp_project / ".claude"
        claude_dir.mkdir()

        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"hooks": {"SessionStart": []}}))

        platform = get_platform("claude")
        result = platform.setup_hooks(temp_project, force=True)

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

        platform = get_platform("claude")
        platform.setup_hooks(temp_project)

        # Should have modified local settings
        local_data = json.loads(local_settings.read_text())
        assert "hooks" in local_data

        # Shared settings should be unchanged
        shared_data = json.loads((claude_dir / "settings.json").read_text())
        assert "hooks" not in shared_data


class TestDetectPlatform:
    """Test platform auto-detection."""

    def test_detects_claude_only(self, temp_project):
        """Should detect claude when only .claude exists."""
        (temp_project / ".claude").mkdir()

        found = detect_platforms(temp_project)

        assert found == ["claude"]

    def test_detects_antigravity_only(self, temp_project):
        """Should detect antigravity when only .agent exists."""
        (temp_project / ".agent").mkdir()

        found = detect_platforms(temp_project)

        assert found == ["antigravity"]

    def test_detects_opencode_only(self, temp_project):
        """Should detect opencode when only .opencode exists."""
        (temp_project / ".opencode").mkdir()

        found = detect_platforms(temp_project)

        assert found == ["opencode"]

    def test_detects_copilot(self, temp_project):
        """Should detect copilot when .github/hooks exists."""
        hooks_dir = temp_project / ".github" / "hooks"
        hooks_dir.mkdir(parents=True)

        found = detect_platforms(temp_project)

        assert "copilot" in found

    def test_returns_empty_when_no_config(self, temp_project):
        """Should return empty list when no config directory exists."""
        found = detect_platforms(temp_project)

        assert found == []

    def test_returns_multiple_when_multiple_configs(self, temp_project):
        """Should return multiple when multiple config directories exist."""
        (temp_project / ".claude").mkdir()
        (temp_project / ".opencode").mkdir()

        found = detect_platforms(temp_project)

        assert "claude" in found
        assert "opencode" in found

    def test_returns_all_when_all_configs(self, temp_project):
        """Should return all when all config directories exist."""
        (temp_project / ".claude").mkdir()
        (temp_project / ".opencode").mkdir()
        (temp_project / ".agent").mkdir()
        (temp_project / ".github" / "hooks").mkdir(parents=True)

        found = detect_platforms(temp_project)

        assert len(found) == 4


class TestCopilotSetup:
    """Test Copilot CLI platform setup."""

    def test_creates_hooks_json(self, temp_project):
        """Should create .github/hooks/anima.json with LTM hooks."""
        github_dir = temp_project / ".github"
        github_dir.mkdir()

        platform = get_platform("copilot")
        result = platform.setup_hooks(temp_project)

        assert result is True
        hooks_file = github_dir / "hooks" / "anima.json"
        assert hooks_file.exists()

        hooks = json.loads(hooks_file.read_text())
        assert hooks["version"] == 1
        assert "sessionStart" in hooks["hooks"]
        assert "sessionEnd" in hooks["hooks"]

    def test_copilot_hook_structure(self, temp_project):
        """Should have correct Copilot hook structure."""
        github_dir = temp_project / ".github"
        github_dir.mkdir()

        platform = get_platform("copilot")
        platform.setup_hooks(temp_project)

        hooks_file = github_dir / "hooks" / "anima.json"
        hooks = json.loads(hooks_file.read_text())

        # Check sessionStart hook structure
        session_start = hooks["hooks"]["sessionStart"][0]
        assert session_start["type"] == "command"
        assert "bash" in session_start
        assert "powershell" in session_start
        assert "timeoutSec" in session_start

    def test_skips_existing_hooks_without_force(self, temp_project):
        """Should skip when hooks already configured and force=False."""
        hooks_dir = temp_project / ".github" / "hooks"
        hooks_dir.mkdir(parents=True)
        hooks_file = hooks_dir / "anima.json"
        hooks_file.write_text('{"existing": true}')

        platform = get_platform("copilot")
        result = platform.setup_hooks(temp_project, force=False)

        assert result is False
        # Original file should be unchanged
        assert json.loads(hooks_file.read_text()) == {"existing": True}


class TestFindConfigDir:
    """Test config directory discovery."""

    def test_finds_in_current_dir(self, temp_project):
        """Should find config in current directory."""
        (temp_project / ".claude").mkdir()

        result = find_config_dir(temp_project, ".claude")

        assert result == temp_project / ".claude"

    def test_finds_in_parent_dir(self, temp_project):
        """Should find config in parent directory (monorepo support)."""
        # Create .claude in temp_project (parent of subdir)
        (temp_project / ".claude").mkdir()
        subdir = temp_project / "subproject"
        subdir.mkdir()

        result = find_config_dir(subdir, ".claude")

        assert result == temp_project / ".claude"

    def test_returns_none_when_not_found(self, temp_project):
        """Should return None when config not found."""
        result = find_config_dir(temp_project, ".nonexistent")

        assert result is None
