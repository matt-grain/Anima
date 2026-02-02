# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Opencode platform setup."""

import shutil
from pathlib import Path

from anima.tools.platforms.base import BasePlatformSetup
from anima.utils.terminal import safe_print, get_icon


class OpencodeSetup(BasePlatformSetup):
    """Setup implementation for Opencode."""

    name = "opencode"
    config_dir = ".opencode"
    commands_subdir = "commands"

    @property
    def display_name(self) -> str:
        return "Opencode"

    def setup_hooks(self, project_dir: Path, force: bool = False) -> bool:
        """Opencode uses a plugin-based hook system."""
        safe_print(f"  {get_icon('', '[i]')} Opencode uses plugin-based hook integration")
        return True

    def setup_extras(self, project_dir: Path, force: bool = False) -> bool:
        """Set up the Opencode plugin bridge."""
        config_dir = self.get_config_path(project_dir)
        if not config_dir:
            safe_print(f"  {get_icon('', '[!]')}  Opencode directory (.opencode) not found")
            return False

        plugins_dir = config_dir / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)

        dest_plugin_dir = plugins_dir / "anima"

        # Resolve source from package
        try:
            from importlib import resources

            anima_files = resources.files("anima")
            src_plugin_dir = Path(str(anima_files)) / "platforms" / "opencode"
        except (TypeError, AttributeError, ImportError):
            # Fallback for dev/editable installs
            src_plugin_dir = Path(__file__).parent.parent.parent / "platforms" / "opencode"

        if not src_plugin_dir.exists():
            safe_print(f"  {get_icon('', '[!]')}  Opencode plugin source not found in package")
            return False

        if dest_plugin_dir.exists() and not force:
            safe_print(f"  {get_icon('', '[>>]')}  Opencode plugin exists (use --force)")
        else:
            if dest_plugin_dir.exists():
                shutil.rmtree(dest_plugin_dir)
            shutil.copytree(src_plugin_dir, config_dir, dirs_exist_ok=True)
            safe_print(f"  {get_icon('', '[OK]')} Opencode plugin bridge installed in .opencode/plugins/anima")

        # Check package.json
        pkg_json = config_dir / "plugins" / "anima" / "package.json"
        if pkg_json.exists():
            safe_print(f"  {get_icon('', '->')} Note: Add '@anima-ltm/opencode-plugin': 'file:./plugins/anima' to your dependencies.")
        else:
            safe_print(f"  {get_icon('', '->')} Note: Create .opencode/package.json to register the anima plugin.")

        return True
