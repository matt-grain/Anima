# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
LTM setup tool.

Sets up LTM in a project by copying commands and optionally configuring hooks.
Works for users who installed via wheel and don't have access to the source tree.
"""

import json
import shutil
import sys
from importlib import resources
from pathlib import Path

from anima.utils.agent_patching import has_subagent_marker, add_subagent_marker


def get_package_commands_dir() -> Path:
    """Get the commands directory from the installed package."""
    # Try to find commands in the package
    try:
        # For Python 3.9+
        anima_files = resources.files("anima")
        commands_dir = Path(str(anima_files)).parent / "commands"
        if commands_dir.exists():
            return commands_dir
    except (TypeError, AttributeError):
        pass

    # Fallback: look relative to this file (for editable installs)
    package_root = Path(__file__).parent.parent.parent
    commands_dir = package_root / "commands"
    if commands_dir.exists():
        return commands_dir

    raise FileNotFoundError("Could not find commands directory in package")


def get_package_seeds_dir() -> Path:
    """Get the seeds directory from the installed package."""
    try:
        anima_files = resources.files("anima")
        seeds_dir = Path(str(anima_files)).parent / "seeds"
        if seeds_dir.exists():
            return seeds_dir
    except (TypeError, AttributeError):
        pass

    # Fallback: look relative to this file
    package_root = Path(__file__).parent.parent.parent
    seeds_dir = package_root / "seeds"
    if seeds_dir.exists():
        return seeds_dir

    raise FileNotFoundError("Could not find seeds directory in package")


def get_package_skills_dir() -> Path:
    """Get the skills directory from the installed package."""
    try:
        anima_files = resources.files("anima")
        skills_dir = Path(str(anima_files)) / "skills"
        if skills_dir.exists():
            return skills_dir
    except (TypeError, AttributeError):
        pass

    # Fallback: look relative to this file (ltm/tools/setup.py -> ltm/skills)
    package_root = Path(__file__).parent.parent
    skills_dir = package_root / "skills"
    if skills_dir.exists():
        return skills_dir

    raise FileNotFoundError("Could not find skills directory in package")


def setup_skills(project_dir: Path, force: bool = False) -> tuple[int, int]:
    """Copy skill directories to project's .agent/skills (or .claude/skills) directory."""
    try:
        src_dir = get_package_skills_dir()
    except FileNotFoundError as e:
        print(f"  ⚠️  {e}")
        return (0, 0)

    # Prefer .agent/skills for Anima, fallback to .claude/skills
    dest_dir = project_dir / ".agent" / "skills"
    if not (project_dir / ".agent").exists() and (project_dir / ".claude").exists():
        dest_dir = project_dir / ".claude" / "skills"

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

        if dest_skill_dir.exists() and not force:
            print(f"  ⏭️  {skill_dir.name}/ (exists, use --force to overwrite)")
            skipped += 1
            continue

        # Copy entire skill directory
        if dest_skill_dir.exists():
            shutil.rmtree(dest_skill_dir)
        shutil.copytree(skill_dir, dest_skill_dir)
        print(f"  ✅ {skill_dir.name}/")
        copied += 1

    return (copied, skipped)


def setup_commands(project_dir: Path, force: bool = False) -> tuple[int, int]:
    """Copy command files to project's commands directory."""
    try:
        src_dir = get_package_commands_dir()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return (0, 0)

    # Prefer .agent/workflows for Anima, fallback to .claude/commands
    dest_dir = project_dir / ".agent" / "workflows"
    if not (project_dir / ".agent").exists() and (project_dir / ".claude").exists():
        dest_dir = project_dir / ".claude" / "commands"

    # Create directory if needed
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0

    for src_file in src_dir.glob("*.md"):
        dest_file = dest_dir / src_file.name

        if dest_file.exists() and not force:
            print(f"  ⏭️  {src_file.name} (exists, use --force to overwrite)")
            skipped += 1
            continue

        shutil.copy2(src_file, dest_file)
        print(f"  ✅ {src_file.name}")
        copied += 1

    return (copied, skipped)


def patch_subagents(project_dir: Path) -> tuple[int, int, int]:
    """
    Patch agent definition files to add subagent: true marker.

    If a project has agent files without ltm: subagent: true,
    they will shadow the global Anima agent. This function adds the marker
    so these agents are treated as subagents (invoked via Task tool) rather
    than the main session identity.

    Agents without YAML frontmatter are incompatible and will be disabled
    by renaming to .md.disabled.

    Returns:
        Tuple of (patched_count, skipped_count, disabled_count)
    """
    # Check both .agent and .claude directories
    local_dirs = [project_dir / ".agent" / "agents", project_dir / ".claude" / "agents"]

    patched = 0
    skipped = 0
    disabled = 0

    for agents_dir in local_dirs:
        if not agents_dir.exists():
            continue

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
                print(f"  ⚠️  {agent_file.name} → {disabled_path.name} (missing frontmatter, disabled)")
                print('      To fix: add ---\\nname: "AgentName"\\nltm: subagent: true\\n--- at top')
                disabled += 1
                continue

            # Add ltm: subagent: true after the opening ---
            new_content = add_subagent_marker(content)

            if new_content != content:
                agent_file.write_text(new_content, encoding="utf-8")
                print(f"  ✅ {agent_file.name} (marked as subagent)")
                patched += 1
            else:
                skipped += 1

    return (patched, skipped, disabled)


def setup_opencode(project_dir: Path, force: bool = False) -> bool:
    """
    Set up the Opencode plugin bridge.

    1. Ensures .opencode/plugins exists.
    2. Copies anima/platforms/opencode to .opencode/plugins/anima.
    3. Provides instructions for package.json.
    """
    opencode_dir = project_dir / ".opencode"
    if not opencode_dir.exists():
        # Only setup if the directory exists or if explicitly requested (handled in run)
        return False

    plugins_dir = opencode_dir / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    dest_plugin_dir = plugins_dir / "anima"

    # Resolve source from package
    try:
        from importlib import resources

        anima_files = resources.files("anima")
        src_plugin_dir = Path(str(anima_files)) / "platforms" / "opencode"
    except (TypeError, AttributeError, ImportError):
        # Fallback for dev/editable installs
        src_plugin_dir = Path(__file__).parent.parent / "platforms" / "opencode"

    if not src_plugin_dir.exists():
        print("  ⚠️  Opencode plugin source not found in package")
        return False

    if dest_plugin_dir.exists() and not force:
        print("  ⏭️  Opencode plugin exists (use --force to overwrite)")
    else:
        if dest_plugin_dir.exists():
            shutil.rmtree(dest_plugin_dir)
        shutil.copytree(src_plugin_dir, dest_plugin_dir)
        print("  ✅ Opencode plugin bridge installed in .opencode/plugins/anima")

    # Check package.json
    pkg_json = opencode_dir / "package.json"
    if pkg_json.exists():
        print("  👉 Note: Add '@anima-ltm/opencode-plugin': 'file:./plugins/anima' to your dependencies.")
    else:
        print("  👉 Note: Create .opencode/package.json to register the anima plugin.")

    return True


def setup_hooks(project_dir: Path, force: bool = False) -> bool:
    """Add LTM hooks to project's .claude/settings.json or settings.local.json.

    Prefers settings.local.json if it exists (user-local, not version controlled).
    Falls back to settings.json (team-shared, version controlled).
    """
    settings_local = project_dir / ".claude" / "settings.local.json"
    settings_shared = project_dir / ".claude" / "settings.json"

    # Prefer local settings if it exists, otherwise use shared
    if settings_local.exists():
        settings_file = settings_local
    else:
        settings_file = settings_shared

    ltm_hooks = {
        "SessionStart": [
            {
                "matcher": "startup",
                "hooks": [
                    {
                        "type": "command",
                        "command": "uv run python -m anima.hooks.session_start",
                    }
                ],
            },
            {
                "matcher": "compact",
                "hooks": [
                    {
                        "type": "command",
                        "command": "uv run python -m anima.hooks.session_start",
                    }
                ],
            },
            {
                "matcher": "clear",
                "hooks": [
                    {
                        "type": "command",
                        "command": "uv run python -m anima.tools.detect_achievements --since 24",
                    },
                    {
                        "type": "command",
                        "command": "uv run python -m anima.hooks.session_start",
                    },
                ],
            },
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "uv run python -m anima.hooks.session_end",
                    },
                    {
                        "type": "command",
                        "command": "uv run python -m anima.tools.detect_achievements --since 24",
                    },
                ]
            }
        ],
    }

    # Load existing settings or create new
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
        except json.JSONDecodeError:
            print(f"  ⚠️  Invalid JSON in {settings_file}, creating backup")
            shutil.copy2(settings_file, settings_file.with_suffix(".json.bak"))
            settings = {}
    else:
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings = {}

    # Check if hooks already exist
    if "hooks" in settings and not force:
        existing_hooks = settings.get("hooks", {})
        if "SessionStart" in existing_hooks or "Stop" in existing_hooks:
            print("  ⚠️  Hooks already configured (use --force to overwrite)")
            return False

    # Merge hooks
    if "hooks" not in settings:
        settings["hooks"] = {}

    settings["hooks"].update(ltm_hooks)

    # Write back
    settings_file.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"  ✅ Hooks configured in {settings_file}")
    return True


def run(args: list[str]) -> int:
    """
    Run the setup tool.

    Usage:
        ltm setup [options] [project-dir]

    Options:
        --commands      Install slash commands only
        --hooks         Configure hooks only
        --no-patch      Skip patching existing agents as subagents
        --force         Overwrite existing files
        --help          Show this help

    If no options specified, installs commands, hooks, and patches subagents.
    """
    # Parse arguments
    force = "--force" in args
    commands_only = "--commands" in args
    hooks_only = "--hooks" in args
    no_patch = "--no-patch" in args
    show_help = "--help" in args or "-h" in args

    # Platform selection
    target_platform = None
    if "--platform" in args:
        idx = args.index("--platform")
        if idx + 1 < len(args):
            target_platform = args[idx + 1].lower()
    elif "--target" in args:
        idx = args.index("--target")
        if idx + 1 < len(args):
            target_platform = args[idx + 1].lower()

    # Filter out flags to get project dir
    project_args = [a for a in [arg for arg in args if not arg.startswith("-")]]
    # Handle the case where platform name was a project_arg if the flag was missing its value
    if target_platform and target_platform in project_args:
        project_args.remove(target_platform)

    project_dir = Path(project_args[0]) if project_args else Path.cwd()

    if show_help:
        print("""
LTM Setup Tool

Usage:
    uv run anima setup [options] [project-dir]

Options:
    --platform <p>  Target platform: claude, antigravity, opencode
    --commands      Install slash commands/workflows only
    --hooks         Configure hooks/plugins only
    --no-patch      Skip patching existing agents as subagents
    --force         Overwrite existing files
    --help          Show this help

Platforms:
    antigravity     Installs skills and workflows to .agent/
    claude          Installs skills and commands to .claude/ + settings.json hooks
    opencode        Installs TS plugin to .opencode/plugins/anima

Examples:
    # Set up everything with auto-detection
    uv run anima setup

    # Force Opencode setup
    uv run anima setup --platform opencode
""")
        return 0

    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        return 1

    print(f"Setting up LTM in: {project_dir}\n")

    # Default: install both
    install_commands = not hooks_only
    install_hooks = not commands_only

    success = True

    if install_commands:
        # If platform is specified, we might skip some logic
        if target_platform in (None, "antigravity", "claude"):
            print("Installing commands...")
            try:
                copied, skipped = setup_commands(project_dir, force)
                print(f"  Commands: {copied} installed, {skipped} skipped\n")
            except Exception as e:
                print(f"  Error installing commands: {e}\n")
                success = False

            print("Installing skills...")
            try:
                copied, skipped = setup_skills(project_dir, force)
                if copied > 0 or skipped > 0:
                    print(f"  Skills: {copied} installed, {skipped} skipped\n")
                else:
                    print("  No skills found in package\n")
            except Exception as e:
                print(f"  Error installing skills: {e}\n")
                success = False

    if install_hooks:
        if target_platform in (None, "claude"):
            print("Configuring Claude hooks...")
            try:
                if not setup_hooks(project_dir, force):
                    pass  # Warning already printed
                print()
            except Exception as e:
                print(f"  Error configuring hooks: {e}\n")
                success = False

        if target_platform in (None, "opencode"):
            print("Configuring Opencode bridge...")
            try:
                if not setup_opencode(project_dir, force):
                    if target_platform == "opencode":
                        print("  ⚠️  Opencode directory (.opencode) not found.")
                print()
            except Exception as e:
                print(f"  Error configuring Opencode: {e}\n")
                success = False

    # Patch subagents unless --no-patch or running with specific options
    if not no_patch and not commands_only and not hooks_only:
        agents_dir = project_dir / ".claude" / "agents"
        if agents_dir.exists() and list(agents_dir.glob("*.md")):
            print("Patching agent definitions...")
            try:
                patched, skipped, disabled = patch_subagents(project_dir)
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
            except Exception as e:
                print(f"  Error patching agents: {e}\n")
                success = False

    if success:
        print("Setup complete!")
        print("\nNext steps:")
        print("  1. Import starter seeds:")
        print("     uv run anima import-seeds seeds/")
        print("  2. If using Anima, check .agent/rules/anima.md is configured.")
        print("  3. Start a new session and say 'Welcome back'")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
