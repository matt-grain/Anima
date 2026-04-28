# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
LTM setup tool.

Sets up LTM/Anima in a project by copying commands and configuring hooks.
Supports multiple platforms: Claude Code, Google Antigravity, Opencode, GitHub Copilot.

Now supports MCP vs SKILL mode selection for how Claude interacts with memory.
"""

import json
import sys
from pathlib import Path

from anima.tools.platforms import (
    PLATFORMS,
    get_platform,
    detect_platforms,
)
from anima.utils.terminal import safe_print, get_icon


# Interaction mode constants
MODE_MCP = "mcp"
MODE_SKILL = "skill"
MODE_BOTH = "both"


def get_anima_config_path() -> Path:
    """Get path to ~/.anima/config.json"""
    return Path.home() / ".anima" / "config.json"


def load_anima_config() -> dict:
    """Load or create ~/.anima/config.json"""
    config_path = get_anima_config_path()
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def save_anima_config(config: dict) -> None:
    """Save config to ~/.anima/config.json"""
    config_path = get_anima_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + "\n")


def prompt_mode_choice() -> str | None:
    """Prompt user to choose MCP/SKILL/Both mode.

    Returns:
        Selected mode ('mcp', 'skill', or 'both'), or None if cancelled
    """
    print("\nHow do you want to use Anima?")
    print()
    print("  1. MCP Server (Recommended)")
    print("     - Tools available implicitly: remember(), recall(), set_emotion()")
    print("     - Claude can use memory mid-thought without /commands")
    print("     - Requires MCP server configuration")
    print()
    print("  2. Skills/Commands")
    print("     - Use /remember, /recall slash commands")
    print("     - User-invoked, follows skill instructions")
    print("     - Current behavior (no MCP needed)")
    print()
    print("  3. Both (MCP + Skills as fallback)")
    print("     - MCP tools for implicit access")
    print("     - Skills available if MCP fails")
    print()
    print("  q. Cancel")
    print()

    try:
        choice = input("Select mode [1/2/3/q]: ").strip().lower()
        if choice == "1":
            return MODE_MCP
        elif choice == "2":
            return MODE_SKILL
        elif choice == "3":
            return MODE_BOTH
        elif choice in ("q", "quit", "exit", ""):
            print("Setup cancelled.")
            return None
        else:
            print(f"Invalid choice: {choice}")
            return None
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.")
        return None


def prompt_eyes_choice() -> bool:
    """Prompt user whether to enable eyes (visual expression).

    Returns:
        True if eyes should be enabled
    """
    print("\nEnable Anima Eyes (visual expression window)?")
    print("  Requires: pip install anima[eyes]")
    print()
    print("  y. Yes - Enable eyes window (pygame)")
    print("  n. No  - No visual display (default)")
    print()

    try:
        choice = input("Enable eyes? [y/N]: ").strip().lower()
        return choice in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def prompt_tts_choice() -> bool:
    """Prompt user whether to enable TTS (text-to-speech).

    Returns:
        True if TTS should be enabled
    """
    print("\nEnable Anima Voice (text-to-speech)?")
    print("  Requires: pip install anima[tts]")
    print()
    print("  y. Yes - Enable TTS with Piper voices")
    print("  n. No  - No voice output (default)")
    print()

    try:
        choice = input("Enable TTS? [y/N]: ").strip().lower()
        return choice in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


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


def setup_global_skills() -> tuple[int, int]:
    """Install skills to global ~/.claude/skills/ directory.

    Returns:
        Tuple of (copied_count, skipped_count)
    """
    import shutil
    from anima.tools.platforms.base import get_package_skills_dir
    from anima.utils.terminal import safe_print, get_icon

    try:
        src_dir = get_package_skills_dir()
    except FileNotFoundError as e:
        safe_print(f"  {get_icon('', '[!]')}  {e}")
        return (0, 0)

    dest_dir = Path.home() / ".claude" / "skills"
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


def setup_global_hooks() -> bool:
    """Set up global HTTP hooks for Claude Code.

    Creates shim scripts in ~/.claude/hooks/ that forward to the HTTP server.
    Installs skills to ~/.claude/skills/ for global availability.
    No per-project install needed - just run `anima serve` once.

    Returns:
        True if successful
    """
    from anima.utils.terminal import safe_print, get_icon

    hooks_dir = Path.home() / ".claude" / "hooks"
    settings_file = Path.home() / ".claude" / "settings.json"

    # Create hooks directory
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Create shim scripts
    shims = {
        "session-start.sh": """\
#!/bin/bash
# Anima SessionStart shim - forwards to centralized HTTP server
curl -s -X POST http://127.0.0.1:3741/hooks/session-start \\
  -H "Content-Type: application/json" \\
  -d "$(cat)"
""",
        "session-end.sh": """\
#!/bin/bash
# Anima SessionEnd shim - forwards to centralized HTTP server
curl -s -X POST http://127.0.0.1:3741/hooks/session-end \\
  -H "Content-Type: application/json" \\
  -d "$(cat)"
""",
        "pre-compact.sh": """\
#!/bin/bash
# Anima PreCompact shim - forwards to centralized HTTP server
curl -s -X POST http://127.0.0.1:3741/hooks/pre-compact \\
  -H "Content-Type: application/json" \\
  -d "$(cat)"
""",
    }

    for filename, content in shims.items():
        shim_path = hooks_dir / filename
        shim_path.write_text(content)
        safe_print(f"  {get_icon('', '[+]')} Created {shim_path}")

    # Update global settings.json
    settings = {}
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
        except json.JSONDecodeError:
            pass

    if "hooks" not in settings:
        settings["hooks"] = {}

    # Add HTTP shim hooks
    settings["hooks"]["SessionStart"] = [
        {
            "matcher": "startup",
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.claude/hooks/session-start.sh",
                    "timeout": 15000,
                }
            ],
        },
        {
            "matcher": "resume",
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.claude/hooks/session-start.sh",
                    "timeout": 15000,
                }
            ],
        },
        {
            "matcher": "compact",
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.claude/hooks/session-start.sh",
                    "timeout": 15000,
                }
            ],
        },
    ]
    settings["hooks"]["SessionEnd"] = [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.claude/hooks/session-end.sh",
                    "timeout": 30000,
                }
            ],
        }
    ]
    settings["hooks"]["PreCompact"] = [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.claude/hooks/pre-compact.sh",
                    "timeout": 10000,
                }
            ],
        }
    ]

    settings_file.write_text(json.dumps(settings, indent=2) + "\n")
    safe_print(f"  {get_icon('', '[+]')} Updated {settings_file}")

    # Install skills globally
    print()
    print("Installing global skills...")
    copied, _ = setup_global_skills()
    print(f"  Skills: {copied} installed")

    print()
    safe_print(f"{get_icon('', '[!]')} Global setup complete!")
    safe_print("    Start the HTTP server: anima serve")
    safe_print("    Works with ANY project - no per-project install needed")

    return True


def run(args: list[str]) -> int:
    """
    Run the setup tool.

    Usage:
        ltm setup [options] [project-dir]

    Options:
        --local             Set up for local Anima development (MCP with --directory)
        --hooks             Configure hooks only (HTTP mode by default, local if --local)
        --platform <p>      Target platform: claude, antigravity, opencode, copilot
        --mode <m>          Interaction mode: mcp, skill, or both (prompts if not specified)
        --eyes              Enable eyes (visual expression window)
        --tts               Enable TTS (text-to-speech with Piper)
        --light             Enable i-Buddy USB light control
        --commands          Install slash commands only
        --no-patch          Skip patching existing agents as subagents
        --no-startup-hook   Disable SessionStart 'startup' hook (Windows Terminal workaround)
        --force             Overwrite existing files
        --help              Show this help

    By default, sets up HTTP hooks for use with `anima serve`.
    Use --local for Anima development repos where MCP server needs --directory.
    """
    # Parse arguments
    force = "--force" in args
    commands_only = "--commands" in args
    hooks_only = "--hooks" in args
    no_patch = "--no-patch" in args
    no_startup_hook = "--no-startup-hook" in args  # Windows Terminal bug workaround
    show_help = "--help" in args or "-h" in args
    eyes_enabled = "--eyes" in args
    tts_enabled = "--tts" in args
    light_enabled = "--light" in args
    local_mode = "--local" in args

    # Default behavior (no --local): Set up global HTTP hooks
    # This enables centralized Anima server without per-project installs
    if not local_mode and not commands_only and not hooks_only and "--platform" not in args:
        print("Setting up global HTTP hooks for Claude Code...")
        print("(Use --local for Anima development with MCP server)")
        print()
        if setup_global_hooks():
            return 0
        return 1

    # Mode selection
    selected_mode = None
    if "--mode" in args:
        idx = args.index("--mode")
        if idx + 1 < len(args):
            mode_arg = args[idx + 1].lower()
            if mode_arg in (MODE_MCP, MODE_SKILL, MODE_BOTH):
                selected_mode = mode_arg
            else:
                print(f"Error: Invalid mode '{mode_arg}'. Use: mcp, skill, or both")
                return 1

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
        "--no-startup-hook",
        "--help",
        "-h",
        "--platform",
        "--target",
        "--mode",
        "--eyes",
        "--tts",
        "--light",
        "--local",
    }
    project_args = []
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg in ("--platform", "--target", "--mode"):
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

Default Behavior:
    Without --local, sets up global HTTP hooks for use with `anima serve`.
    This enables centralized Anima without per-project installs.

Options:
    --local             Set up for local Anima development:
                        - Configures MCP server with --directory to current repo
                        - Installs local hooks (uv run python -m anima.hooks.*)
                        - Required when working ON Anima itself
    --platform <p>      Target platform (see list below)
    --mode <m>          Interaction mode: mcp, skill, or both
                        - mcp:   MCP server tools (remember(), recall(), etc.)
                        - skill: Slash commands (/remember, /recall)
                        - both:  MCP tools + skills as fallback
    --eyes              Enable eyes (visual expression window)
    --tts               Enable TTS (text-to-speech with Piper voices)
    --light             Enable i-Buddy USB light control
    --commands          Install slash commands/workflows only
    --hooks             Configure hooks/plugins only
    --no-patch          Skip patching existing agents as subagents
    --no-startup-hook   Disable SessionStart 'startup' hook (Windows Terminal workaround)
    --force             Overwrite existing files
    --help              Show this help

Platforms:
{platforms_help}

Examples:
    # Default: Set up global HTTP hooks (for any project)
    uv run anima setup

    # Local development: Configure MCP with --directory to this repo
    uv run anima setup --local --mode mcp --eyes --tts

    # MCP mode with eyes and TTS (requires --local for MCP)
    uv run anima setup --local --mode mcp --eyes --tts

    # Force specific platform setup
    uv run anima setup --local --platform claude

    # Install only hooks (HTTP mode)
    uv run anima setup --hooks
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
            platform.setup_hooks(project_dir, force, with_startup_hook=not no_startup_hook)
            if no_startup_hook:
                safe_print(f"  {get_icon('', '[!]')} SessionStart 'startup' hook DISABLED (Windows Terminal workaround)")
                safe_print("      Use /load-context to manually load memories at session start")
            print()
        except Exception as e:
            print(f"  Error configuring hooks: {e}\n")
            success = False
    else:
        # Full setup - prompt for mode if not specified
        if selected_mode is None and target_platform == "claude":
            # Claude supports MCP mode, prompt for choice
            selected_mode = prompt_mode_choice()
            if selected_mode is None:
                return 1  # User cancelled

            # If MCP mode, ask about eyes and TTS separately
            if selected_mode in (MODE_MCP, MODE_BOTH):
                if not eyes_enabled:
                    eyes_enabled = prompt_eyes_choice()
                if not tts_enabled:
                    tts_enabled = prompt_tts_choice()

        # Default to skill mode for non-Claude platforms (they don't support MCP)
        if selected_mode is None:
            selected_mode = MODE_SKILL

        # Save mode choice to config
        config = load_anima_config()
        config["mode"] = selected_mode
        config["eyes_enabled"] = eyes_enabled
        config["tts_enabled"] = tts_enabled
        config["light_enabled"] = light_enabled
        save_anima_config(config)
        safe_print(f"{get_icon('', '[OK]')} Saved mode '{selected_mode}' to ~/.anima/config.json")
        if eyes_enabled:
            safe_print(f"{get_icon('', '[OK]')} Eyes enabled (visual expression)")
        if tts_enabled:
            safe_print(f"{get_icon('', '[OK]')} TTS enabled (text-to-speech)")
        if light_enabled:
            safe_print(f"{get_icon('', '[OK]')} Light enabled (i-Buddy USB)")
        print()

        # Run full setup
        success = platform.run_full_setup(
            project_dir,
            force,
            no_patch,
            with_startup_hook=not no_startup_hook,
            mode=selected_mode,
            eyes_enabled=eyes_enabled,
            tts_enabled=tts_enabled,
            light_enabled=light_enabled,
            local_mode=local_mode,
        )

    if success:
        print("Setup complete!")
        print("\nNext steps:")
        if selected_mode in (MODE_MCP, MODE_BOTH):
            print("  1. Restart Claude Code to load MCP server")
            print("  2. Memory tools (remember, recall) are now available implicitly")
            if eyes_enabled or tts_enabled:
                deps = []
                if eyes_enabled:
                    deps.append("eyes")
                if tts_enabled:
                    deps.append("tts")
                print(f"  3. Install dependencies: pip install anima[{','.join(deps)}]")
                if eyes_enabled:
                    print("  4. Eyes window will appear on next session")
                if tts_enabled:
                    print(f"  {'5' if eyes_enabled else '4'}. Voice will activate on next session")
        else:
            print("  1. Import starter seeds:")
            print("     uv run anima import-seeds seeds/")
            print("  2. If using Anima, check your platform's rules/agent file is configured.")
            print("  3. Start a new session and say 'Welcome back'")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
