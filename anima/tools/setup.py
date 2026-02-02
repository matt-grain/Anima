# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
LTM setup tool.

Sets up LTM/Anima in a project by copying commands and configuring hooks.
Supports multiple platforms: Claude Code, Google Antigravity, Opencode, GitHub Copilot.
"""

import sys
from pathlib import Path

from anima.tools.platforms import (
    PLATFORMS,
    get_platform,
    detect_platforms,
)
from anima.utils.terminal import safe_print, get_icon


def prompt_platform_choice(found_configs: list[str]) -> str | None:
    """Prompt user to choose a platform when auto-detection is ambiguous.

    Args:
        found_configs: List of detected config directories (may be empty or multiple)

    Returns:
        Selected platform name, or None if user cancels
    """
    safe_print(f"\n{get_icon('', '[!]')}  Platform auto-detection failed.")

    if len(found_configs) == 0:
        print("   No platform config directory found")
    else:
        print(f"   Multiple configs found: {', '.join(found_configs)}")

    print("\nWhich platform are you setting up?")

    # Build menu from registered platforms
    platform_list = list(PLATFORMS.keys())
    for i, name in enumerate(platform_list, 1):
        platform = get_platform(name)
        print(f"  {i}. {name:12} ({platform.display_name} - {platform.config_dir}/)")

    print("  q. Cancel")

    try:
        choice = input(f"\nEnter choice [1-{len(platform_list)}/q]: ").strip().lower()
        if choice.isdigit() and 1 <= int(choice) <= len(platform_list):
            return platform_list[int(choice) - 1]
        elif choice in ("q", "quit", "exit", ""):
            print("Setup cancelled.")
            return None
        else:
            print(f"Invalid choice: {choice}")
            return None
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.")
        return None


def run(args: list[str]) -> int:
    """
    Run the setup tool.

    Usage:
        ltm setup [options] [project-dir]

    Options:
        --platform <p>  Target platform: claude, antigravity, opencode, copilot
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
    flag_args = {
        "--force",
        "--commands",
        "--hooks",
        "--no-patch",
        "--help",
        "-h",
        "--platform",
        "--target",
    }
    project_args = []
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg in ("--platform", "--target"):
            skip_next = True
            continue
        if arg not in flag_args:
            project_args.append(arg)

    project_dir = Path(project_args[0]) if project_args else Path.cwd()

    if show_help:
        platforms_help = "\n".join(f"    {name:12} {get_platform(name).display_name} ({get_platform(name).config_dir}/)" for name in PLATFORMS)
        print(f"""
LTM Setup Tool

Usage:
    uv run anima setup [options] [project-dir]

Options:
    --platform <p>  Target platform (see list below)
    --commands      Install slash commands/workflows only
    --hooks         Configure hooks/plugins only
    --no-patch      Skip patching existing agents as subagents
    --force         Overwrite existing files
    --help          Show this help

Platforms:
{platforms_help}

Examples:
    # Set up everything with auto-detection
    uv run anima setup

    # Force Copilot setup
    uv run anima setup --platform copilot

    # Install only commands for Claude
    uv run anima setup --platform claude --commands
""")
        return 0

    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        return 1

    # Auto-detect platform if not specified
    if not target_platform:
        found = detect_platforms(project_dir)
        if len(found) == 1:
            target_platform = found[0]
            print(f"Setting up LTM in: {project_dir}")
            print(f"Detected platform: {target_platform}\n")
        else:
            # Ambiguous - prompt user
            target_platform = prompt_platform_choice(found)
            if not target_platform:
                return 1  # User cancelled
            print(f"\nSetting up LTM in: {project_dir}")
            print(f"Selected platform: {target_platform}\n")
    else:
        # Validate platform name
        if target_platform not in PLATFORMS:
            print(f"Error: Unknown platform '{target_platform}'")
            print(f"Supported platforms: {', '.join(PLATFORMS.keys())}")
            return 1
        print(f"Setting up LTM in: {project_dir}")
        print(f"Target platform: {target_platform}\n")

    # Get the platform setup instance
    platform = get_platform(target_platform)
    success = True

    # Handle specific options
    if commands_only:
        print(f"Installing commands ({target_platform})...")
        try:
            copied, skipped = platform.setup_commands(project_dir, force)
            print(f"  Commands: {copied} installed, {skipped} skipped\n")
        except Exception as e:
            print(f"  Error installing commands: {e}\n")
            success = False
    elif hooks_only:
        print(f"Configuring {platform.display_name} hooks...")
        try:
            platform.setup_hooks(project_dir, force)
            print()
        except Exception as e:
            print(f"  Error configuring hooks: {e}\n")
            success = False
    else:
        # Full setup
        success = platform.run_full_setup(project_dir, force, no_patch)

    if success:
        print("Setup complete!")
        print("\nNext steps:")
        print("  1. Import starter seeds:")
        print("     uv run anima import-seeds seeds/")
        print("  2. If using Anima, check your platform's rules/agent file is configured.")
        print("  3. Start a new session and say 'Welcome back'")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
