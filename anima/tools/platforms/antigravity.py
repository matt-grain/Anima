# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Google Antigravity platform setup."""

from pathlib import Path

from anima.tools.platforms.base import BasePlatformSetup
from anima.utils.agent_patching import has_subagent_marker, add_subagent_marker
from anima.utils.terminal import safe_print, get_icon


class AntigravitySetup(BasePlatformSetup):
    """Setup implementation for Google Antigravity."""

    name = "antigravity"
    config_dir = ".agent"
    commands_subdir = "workflows"  # Antigravity uses "workflows" not "commands"

    @property
    def display_name(self) -> str:
        return "Google Antigravity"

    def setup_hooks(self, project_dir: Path, force: bool = False) -> bool:
        """Antigravity hooks are configured via rules files, not JSON.

        The LTM integration is handled through workflow triggers.
        """
        safe_print(f"  {get_icon('', '[i]')} Antigravity uses rules-based hook integration")
        return True

    def setup_extras(self, project_dir: Path, force: bool = False) -> bool:
        """Patch agent definition files to add subagent marker."""
        config_dir = self.get_config_path(project_dir)
        if not config_dir:
            return True

        agents_dir = config_dir / "agents"
        if not agents_dir.exists() or not list(agents_dir.glob("*.md")):
            return True

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

        return True

    def _patch_subagents(self, project_dir: Path) -> tuple[int, int, int]:
        """Patch agent definition files to add subagent: true marker."""
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

            if has_subagent_marker(content):
                skipped += 1
                continue

            if not content.startswith("---"):
                disabled_path = agent_file.with_suffix(".md.disabled")
                agent_file.rename(disabled_path)
                print(f"  {get_icon('', '[!]')}  {agent_file.name} -> {disabled_path.name} (missing frontmatter)")
                disabled += 1
                continue

            new_content = add_subagent_marker(content)
            if new_content != content:
                agent_file.write_text(new_content, encoding="utf-8")
                safe_print(f"  {get_icon('', '[OK]')} {agent_file.name} (marked as subagent)")
                patched += 1
            else:
                skipped += 1

        return (patched, skipped, disabled)
