# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Gemini CLI platform setup."""

import json
import shutil
from pathlib import Path

from anima.tools.platforms.base import BasePlatformSetup
from anima.utils.agent_patching import has_subagent_marker, add_subagent_marker
from anima.utils.terminal import safe_print, get_icon


class GeminiSetup(BasePlatformSetup):
    """Setup implementation for Gemini CLI.

    Gemini CLI (geminicli.com) uses a similar hooks system to Claude Code,
    with settings.json configuration and hook events like SessionStart,
    SessionEnd, BeforeTool, AfterTool, etc.

    Config locations:
        - Project: .gemini/settings.json
        - User: ~/.gemini/settings.json
        - System: /etc/gemini-cli/settings.json
    """

    name = "gemini"
    config_dir = ".gemini"
    commands_subdir = "commands"

    @property
    def display_name(self) -> str:
        return "Gemini CLI"

    def setup_hooks(self, project_dir: Path, force: bool = False) -> bool:
        """Add LTM hooks to Gemini's settings.json."""
        config_dir = self.get_config_path(project_dir)
        if not config_dir:
            safe_print(f"  {get_icon('', '[!]')}  No .gemini directory found (checked current and parent dir)")
            return False

        settings_file = config_dir / "settings.json"

        # Get monorepo command prefix if needed
        cmd_prefix = self.get_monorepo_cmd_prefix(project_dir)
        if cmd_prefix:
            safe_print(f"  {get_icon('', '[D]')} Monorepo detected: hooks will cd to {project_dir.name}/ first")

        # Gemini CLI hook events are similar to Claude Code
        # See: https://geminicli.com/docs/hooks/
        ltm_hooks = {
            "SessionStart": [
                {
                    "matcher": "startup",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.session_start",
                            "name": "anima-session-start",
                        }
                    ],
                },
                {
                    "matcher": "resume",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.session_start",
                            "name": "anima-session-resume",
                        }
                    ],
                },
                {
                    "matcher": "clear",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.tools.detect_achievements --since 24",
                            "name": "anima-detect-achievements",
                        },
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.session_start",
                            "name": "anima-session-clear",
                        },
                    ],
                },
            ],
            "SessionEnd": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.session_end",
                            "name": "anima-session-end",
                        },
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.tools.detect_achievements --since 24",
                            "name": "anima-detect-achievements-end",
                        },
                    ]
                }
            ],
            # Gemini CLI supports PreCompress (similar to Claude's PreCompact)
            "PreCompress": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.pre_compact",
                            "name": "anima-pre-compress",
                        }
                    ],
                }
            ],
        }

        # Load existing settings or create new
        if settings_file.exists():
            try:
                settings = json.loads(settings_file.read_text())
            except json.JSONDecodeError:
                safe_print(f"  {get_icon('', '[!]')}  Invalid JSON in {settings_file}, creating backup")
                shutil.copy2(settings_file, settings_file.with_suffix(".json.bak"))
                settings = {}
        else:
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            settings = {}

        # Merge hooks
        if "hooks" not in settings:
            settings["hooks"] = {}

        # Update hooks to latest configuration
        settings["hooks"].update(ltm_hooks)

        # Write back
        settings_file.write_text(json.dumps(settings, indent=2) + "\n")
        safe_print(f"  {get_icon('', '[OK]')} Hooks configured in {settings_file}")
        return True

    def setup_extras(self, project_dir: Path, force: bool = False) -> bool:
        """Patch agent definition files to add subagent marker if agents exist."""
        config_dir = self.get_config_path(project_dir)
        if not config_dir:
            return True  # No config dir, nothing to patch

        # Gemini CLI might use agents directory similar to Claude
        agents_dir = config_dir / "agents"
        if not agents_dir.exists() or not list(agents_dir.glob("*.md")):
            return True  # No agents to patch

        print("Patching agent definitions...")
        patched, skipped, disabled = self._patch_subagents(project_dir)

        if patched > 0 or skipped > 0 or disabled > 0:
            parts = []
            if patched > 0:
                parts.append(f"{patched} patched")
            if skipped > 0:
                parts.append(f"{skipped} skipped")
            if disabled > 0:
                parts.append(f"{disabled} disabled")
            print(f"  Agents: {', '.join(parts)}\n")
        else:
            print("  No agent files found\n")

        return True

    def _patch_subagents(self, project_dir: Path) -> tuple[int, int, int]:
        """Patch agent definition files to add subagent: true marker.

        Returns:
            Tuple of (patched_count, skipped_count, disabled_count)
        """
        config_dir = self.get_config_path(project_dir)
        if not config_dir:
            return (0, 0, 0)

        agents_dir = config_dir / "agents"
        if not agents_dir.exists():
            return (0, 0, 0)

        patched = 0
        skipped = 0
        disabled = 0

        for agent_file in sorted(agents_dir.glob("*.md")):
            content = agent_file.read_text(encoding="utf-8")

            # Check if it already has ltm: subagent: true
            if has_subagent_marker(content):
                skipped += 1
                continue

            # Check if it has frontmatter at all
            if not content.startswith("---"):
                # Incompatible format - disable by renaming
                disabled_path = agent_file.with_suffix(".md.disabled")
                agent_file.rename(disabled_path)
                print(f"  {get_icon('', '[!]')}  {agent_file.name} -> {disabled_path.name} (missing frontmatter, disabled)")
                print('      To fix: add ---\\nname: "AgentName"\\nltm: subagent: true\\n--- at top')
                disabled += 1
                continue

            # Add ltm: subagent: true after the opening ---
            new_content = add_subagent_marker(content)

            if new_content != content:
                agent_file.write_text(new_content, encoding="utf-8")
                safe_print(f"  {get_icon('', '[OK]')} {agent_file.name} (marked as subagent)")
                patched += 1
            else:
                skipped += 1

        return (patched, skipped, disabled)
