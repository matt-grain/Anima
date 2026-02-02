# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""GitHub Copilot CLI platform setup."""

import json
import shutil
from pathlib import Path

from anima.tools.platforms.base import BasePlatformSetup
from anima.utils.terminal import safe_print, get_icon


class CopilotSetup(BasePlatformSetup):
    """Setup implementation for GitHub Copilot CLI.

    Copilot hooks are stored in .github/hooks/*.json with the format:
    {
        "version": 1,
        "hooks": {
            "sessionStart": [...],
            "sessionEnd": [...],
            "preToolUse": [...],
            "postToolUse": [...]
        }
    }
    """

    name = "copilot"
    config_dir = ".github"
    commands_subdir = "commands"  # Copilot may use agent instructions elsewhere

    @property
    def display_name(self) -> str:
        return "GitHub Copilot CLI"

    def detect(self, project_dir: Path) -> bool:
        """Check if Copilot hooks directory exists."""
        config_dir = self.get_config_path(project_dir)
        if not config_dir:
            return False
        # Look for .github/hooks/ specifically for Copilot
        hooks_dir = config_dir / "hooks"
        return hooks_dir.exists()

    def get_hooks_dir(self, project_dir: Path) -> Path:
        """Get the hooks directory path."""
        config_dir = self.get_or_create_config_path(project_dir)
        hooks_dir = config_dir / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        return hooks_dir

    def setup_commands(self, project_dir: Path, force: bool = False) -> tuple[int, int]:
        """Copilot may not have the same command structure yet.

        For now, we skip command installation as Copilot uses a different
        agent instruction model. This can be extended when Copilot's
        command/skill format is documented.
        """
        safe_print(f"  {get_icon('', '[i]')} Copilot command structure TBD - skipping")
        return (0, 0)

    def setup_hooks(self, project_dir: Path, force: bool = False) -> bool:
        """Configure Anima hooks in .github/hooks/anima.json."""
        hooks_dir = self.get_hooks_dir(project_dir)
        hooks_file = hooks_dir / "anima.json"

        # Get monorepo command prefix if needed
        cmd_prefix = self.get_monorepo_cmd_prefix(project_dir)

        # Build the Python command to run
        # Copilot supports bash and powershell, we use bash for cross-platform
        session_start_cmd = f"{cmd_prefix}uv run python -m anima.hooks.session_start"
        session_end_cmd = f"{cmd_prefix}uv run python -m anima.hooks.session_end"
        detect_achievements_cmd = f"{cmd_prefix}uv run python -m anima.tools.detect_achievements --since 24"

        ltm_hooks = {
            "version": 1,
            "hooks": {
                "sessionStart": [
                    {
                        "type": "command",
                        "bash": session_start_cmd,
                        "powershell": "uv run python -m anima.hooks.session_start",
                        "timeoutSec": 30,
                    }
                ],
                "sessionEnd": [
                    {
                        "type": "command",
                        "bash": session_end_cmd,
                        "powershell": "uv run python -m anima.hooks.session_end",
                        "timeoutSec": 30,
                    },
                    {
                        "type": "command",
                        "bash": detect_achievements_cmd,
                        "powershell": "uv run python -m anima.tools.detect_achievements --since 24",
                        "timeoutSec": 30,
                    },
                ],
            },
        }

        # Check if hooks already exist
        if hooks_file.exists() and not force:
            safe_print(f"  {get_icon('', '[!]')}  Hooks already configured in {hooks_file.name} (use --force to overwrite)")
            return False

        # Backup existing file if forcing
        if hooks_file.exists() and force:
            shutil.copy2(hooks_file, hooks_file.with_suffix(".json.bak"))

        # Write hooks file
        hooks_file.write_text(json.dumps(ltm_hooks, indent=2) + "\n")
        safe_print(f"  {get_icon('', '[OK]')} Hooks configured in {hooks_file}")

        return True

    def setup_extras(self, project_dir: Path, force: bool = False) -> bool:
        """No extra setup needed for Copilot currently."""
        return True
