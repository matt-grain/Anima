# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Base class for platform setup implementations.

Provides shared functionality for all platforms with hooks for customization.
"""

import shutil
from abc import ABC, abstractmethod
from importlib import resources
from pathlib import Path

from anima.utils.terminal import safe_print, get_icon


def find_config_dir(project_dir: Path, config_name: str) -> Path | None:
    """Find a config directory, checking both project_dir and parent (for monorepos).

    Args:
        project_dir: Starting directory to search from
        config_name: Name of config directory (e.g., ".claude", ".opencode", ".agent")

    Returns:
        Path to config directory if found, None otherwise
    """
    # Check current directory first
    if (project_dir / config_name).exists():
        return project_dir / config_name
    # Check parent directory (monorepo support: backend/ with ../.claude)
    if (project_dir.parent / config_name).exists():
        return project_dir.parent / config_name
    return None


def get_package_commands_dir(platform: str) -> Path:
    """Get the platform-specific commands directory from the installed package."""
    try:
        anima_files = resources.files("anima")
        package_base = Path(str(anima_files))
        platform_commands = package_base / "platforms" / platform / "commands"
        if platform_commands.exists():
            return platform_commands
    except (TypeError, AttributeError):
        pass

    # Fallback: look relative to this file (for editable installs)
    platform_commands = Path(__file__).parent.parent.parent / "platforms" / platform / "commands"
    if platform_commands.exists():
        return platform_commands

    raise FileNotFoundError(f"Could not find commands directory for platform '{platform}'")


def get_package_skills_dir() -> Path:
    """Get the skills directory from the installed package."""
    try:
        anima_files = resources.files("anima")
        skills_dir = Path(str(anima_files)) / "skills"
        if skills_dir.exists():
            return skills_dir
    except (TypeError, AttributeError):
        pass

    # Fallback: look relative to this file
    package_root = Path(__file__).parent.parent.parent
    skills_dir = package_root / "skills"
    if skills_dir.exists():
        return skills_dir

    raise FileNotFoundError("Could not find skills directory in package")


class BasePlatformSetup(ABC):
    """Abstract base class for platform setup implementations.

    Subclasses must define:
        - name: Platform identifier (e.g., "claude")
        - config_dir: Config directory name (e.g., ".claude")

    Optional overrides:
        - commands_subdir: Where commands go within config_dir (default: "commands")
        - setup_hooks(): Configure platform-specific hooks
        - setup_extras(): Any additional platform-specific setup
    """

    name: str
    config_dir: str
    commands_subdir: str = "commands"

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable platform name for UI."""
        ...

    def detect(self, project_dir: Path) -> bool:
        """Check if this platform is configured in the project."""
        return find_config_dir(project_dir, self.config_dir) is not None

    def get_config_path(self, project_dir: Path) -> Path | None:
        """Get the config directory path if it exists."""
        return find_config_dir(project_dir, self.config_dir)

    def get_or_create_config_path(self, project_dir: Path) -> Path:
        """Get or create the config directory path."""
        config = find_config_dir(project_dir, self.config_dir)
        if config:
            return config
        # Create in project_dir
        config = project_dir / self.config_dir
        config.mkdir(parents=True, exist_ok=True)
        return config

    def get_commands_dest(self, project_dir: Path) -> Path:
        """Get the destination directory for commands/workflows."""
        config = self.get_or_create_config_path(project_dir)
        return config / self.commands_subdir

    def get_skills_dest(self, project_dir: Path) -> Path:
        """Get the destination directory for skills."""
        config = self.get_or_create_config_path(project_dir)
        return config / "skills"

    def setup_commands(self, project_dir: Path, force: bool = False) -> tuple[int, int]:
        """Copy command files to project's commands directory.

        Returns:
            Tuple of (copied_count, skipped_count)
        """
        try:
            src_dir = get_package_commands_dir(self.name)
        except FileNotFoundError as e:
            safe_print(f"  {get_icon('', '[!]')}  {e}")
            return (0, 0)

        dest_dir = self.get_commands_dest(project_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        skipped = 0

        for src_file in src_dir.glob("*.md"):
            dest_file = dest_dir / src_file.name
            is_update = dest_file.exists()

            shutil.copy2(src_file, dest_file)
            status = "updated" if is_update else "installed"
            safe_print(f"  {get_icon('', '[OK]')} {src_file.name} ({status})")
            copied += 1

        return (copied, skipped)

    def setup_skills(self, project_dir: Path, force: bool = False) -> tuple[int, int]:
        """Copy skill directories to project's skills directory.

        Returns:
            Tuple of (copied_count, skipped_count)
        """
        try:
            src_dir = get_package_skills_dir()
        except FileNotFoundError as e:
            safe_print(f"  {get_icon('', '[!]')}  {e}")
            return (0, 0)

        dest_dir = self.get_skills_dest(project_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        skipped = 0

        for skill_dir in src_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            dest_skill_dir = dest_dir / skill_dir.name
            is_update = dest_skill_dir.exists()

            # Copy entire skill directory (replace if exists)
            if is_update:
                shutil.rmtree(dest_skill_dir)
            shutil.copytree(skill_dir, dest_skill_dir)
            status = "updated" if is_update else "installed"
            safe_print(f"  {get_icon('', '[OK]')} {skill_dir.name}/ ({status})")
            copied += 1

        return (copied, skipped)

    def setup_hooks(self, project_dir: Path, force: bool = False) -> bool:
        """Configure platform-specific hooks.

        Default implementation: no hooks needed.

        Returns:
            True if successful or no hooks needed, False on error.
        """
        return True

    def setup_extras(self, project_dir: Path, force: bool = False) -> bool:
        """Perform any additional platform-specific setup.

        Default implementation: nothing extra needed.

        Returns:
            True if successful or nothing needed, False on error.
        """
        return True

    def get_monorepo_cmd_prefix(self, project_dir: Path) -> str:
        """Get command prefix for monorepo setups where config is in parent dir.

        If .claude is in parent dir but pyproject.toml is in project_dir,
        we need to cd into the subfolder before running uv.
        """
        config_dir = self.get_config_path(project_dir)
        if config_dir and config_dir == project_dir.parent / self.config_dir and (project_dir / "pyproject.toml").exists():
            subfolder = project_dir.name
            return f"cd {subfolder} && "
        return ""

    def run_full_setup(self, project_dir: Path, force: bool = False, no_patch: bool = False) -> bool:
        """Run the complete setup for this platform.

        Args:
            project_dir: Target project directory
            force: Overwrite existing files
            no_patch: Skip agent patching (for Claude/Antigravity)

        Returns:
            True if all setup steps succeeded
        """
        success = True

        # Commands
        print(f"Installing commands ({self.name})...")
        try:
            copied, skipped = self.setup_commands(project_dir, force)
            print(f"  Commands: {copied} installed, {skipped} skipped\n")
        except Exception as e:
            print(f"  Error installing commands: {e}\n")
            success = False

        # Skills
        print("Installing skills...")
        try:
            copied, skipped = self.setup_skills(project_dir, force)
            if copied > 0 or skipped > 0:
                print(f"  Skills: {copied} installed, {skipped} skipped\n")
            else:
                print("  No skills found in package\n")
        except Exception as e:
            print(f"  Error installing skills: {e}\n")
            success = False

        # Hooks
        print(f"Configuring {self.display_name} hooks...")
        try:
            if not self.setup_hooks(project_dir, force):
                pass  # Warning already printed
            print()
        except Exception as e:
            print(f"  Error configuring hooks: {e}\n")
            success = False

        # Extras
        try:
            if not self.setup_extras(project_dir, force):
                pass  # Warning already printed
        except Exception as e:
            print(f"  Error in platform extras: {e}\n")
            success = False

        return success
