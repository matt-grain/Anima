# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Claude Code platform setup."""

import json
import shutil
from pathlib import Path

from anima.tools.platforms.base import BasePlatformSetup
from anima.utils.agent_patching import has_subagent_marker, add_subagent_marker
from anima.utils.terminal import safe_print, get_icon


def get_global_claude_settings_path() -> Path:
    """Get the global Claude settings path (~/.claude.json)."""
    return Path.home() / ".claude.json"


class ClaudeSetup(BasePlatformSetup):
    """Setup implementation for Claude Code."""

    name = "claude"
    config_dir = ".claude"
    commands_subdir = "commands"

    @property
    def display_name(self) -> str:
        return "Claude Code"

    def setup_hooks(self, project_dir: Path, force: bool = False, with_startup_hook: bool = True) -> bool:
        """Add LTM hooks to Claude's settings.json or settings.local.json.

        Args:
            project_dir: Target project directory
            force: Overwrite existing files
            with_startup_hook: Include SessionStart "startup" matcher.
                              Set to False for Windows Terminal bug workaround (issue #23083).
        """
        config_dir = self.get_config_path(project_dir)
        if not config_dir:
            safe_print(f"  {get_icon('', '[!]')}  No .claude directory found (checked current and parent dir)")
            return False

        settings_local = config_dir / "settings.local.json"
        settings_shared = config_dir / "settings.json"

        # Prefer local settings if it exists, otherwise use shared
        settings_file = settings_local if settings_local.exists() else settings_shared

        # Get monorepo command prefix if needed
        cmd_prefix = self.get_monorepo_cmd_prefix(project_dir)
        if cmd_prefix:
            safe_print(f"  {get_icon('', '[D]')} Monorepo detected: hooks will cd to {project_dir.name}/ first")

        # Check if user previously disabled startup hook (preserve their choice)
        if settings_file.exists():
            try:
                existing = json.loads(settings_file.read_text())
                existing_session_start = existing.get("hooks", {}).get("SessionStart", [])
                if existing_session_start:  # Has SessionStart hooks
                    has_startup = any(m.get("matcher") == "startup" for m in existing_session_start)
                    if not has_startup:
                        safe_print(f"  {get_icon('', '[D]')} Detected: 'startup' hook was previously disabled in {settings_file}, preserving choice")
            except (json.JSONDecodeError, OSError):
                pass

        # Build SessionStart matchers - startup is optional (Windows Terminal bug workaround)
        session_start_matchers = []
        if with_startup_hook:
            session_start_matchers.append(
                {
                    "matcher": "startup",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.session_start",
                        }
                    ],
                }
            )

        session_start_matchers.extend(
            [
                {
                    "matcher": "resume",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.session_start",
                        }
                    ],
                },
                {
                    "matcher": "compact",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.session_start",
                        }
                    ],
                },
                {
                    "matcher": "clear",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.tools.detect_achievements --since 24",
                        },
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.session_start",
                        },
                    ],
                },
            ]
        )

        ltm_hooks = {
            "SessionStart": session_start_matchers,
            "SubagentStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.subagent_start",
                        }
                    ],
                }
            ],
            "PreCompact": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.pre_compact",
                        }
                    ],
                }
            ],
            "SessionEnd": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.session_end",
                        },
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.tools.detect_achievements --since 24",
                        },
                    ]
                }
            ],
            "PermissionRequest": [
                {
                    "matcher": "Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.permission_request",
                        }
                    ],
                },
                {
                    "matcher": "Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.permission_request",
                        }
                    ],
                },
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{cmd_prefix}uv run python -m anima.hooks.permission_request",
                        }
                    ],
                },
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

        # Always clean up deprecated hooks (Stop was renamed to SessionEnd in v0.12.4)
        if "Stop" in settings["hooks"]:
            del settings["hooks"]["Stop"]
            safe_print(f"  {get_icon('', '[D]')} Removed deprecated 'Stop' hook (replaced by 'SessionEnd')")

        # Always update hooks to latest configuration
        settings["hooks"].update(ltm_hooks)

        # Add required permissions for Anima operations
        if "permissions" not in settings:
            settings["permissions"] = {}
        if "allow" not in settings["permissions"]:
            settings["permissions"]["allow"] = []

        # Permissions needed for Anima to work without prompts
        required_permissions = [
            "Bash(uv run anima:*)",  # All anima commands (diary, dream, etc.)
            "Write(~/.anima/**)",  # Write diary/dream files to ~/.anima/
            "Edit(~/.anima/**)",  # Edit existing files in ~/.anima/
        ]

        added_permissions = []
        for perm in required_permissions:
            if perm not in settings["permissions"]["allow"]:
                settings["permissions"]["allow"].append(perm)
                added_permissions.append(perm)

        if added_permissions:
            safe_print(f"  {get_icon('', '[OK]')} Added permissions: {', '.join(added_permissions)}")

        # Write back
        settings_file.write_text(json.dumps(settings, indent=2) + "\n")
        safe_print(f"  {get_icon('', '[OK]')} Hooks configured in {settings_file}")
        return True

    def setup_extras(self, project_dir: Path, force: bool = False) -> bool:
        """Patch agent definition files to add subagent marker."""
        config_dir = self.get_config_path(project_dir)
        if not config_dir:
            return True  # No config dir, nothing to patch

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

    def _patch_global_agents(self) -> tuple[int, int]:
        """Patch global agent definitions (~/.claude/agents/) to add subagent marker.

        Global agents without subagent: true will override the primary agent (anima)
        in ALL projects, which breaks curiosity queue, memories, etc.

        Returns:
            Tuple of (patched_count, skipped_count)
        """
        global_agents_dir = Path.home() / ".claude" / "agents"
        if not global_agents_dir.exists():
            return (0, 0)

        patched = 0
        skipped = 0

        for agent_file in sorted(global_agents_dir.glob("*.md")):
            try:
                content = agent_file.read_text(encoding="utf-8")

                # Check if it already has ltm: subagent: true
                if has_subagent_marker(content):
                    skipped += 1
                    continue

                # Check if it has frontmatter at all
                if not content.startswith("---"):
                    skipped += 1
                    continue

                # Add ltm: subagent: true after the opening ---
                new_content = add_subagent_marker(content)

                if new_content != content:
                    agent_file.write_text(new_content, encoding="utf-8")
                    safe_print(f"  {get_icon('', '[OK]')} ~/.claude/agents/{agent_file.name} (marked as subagent)")
                    patched += 1
                else:
                    skipped += 1
            except (OSError, UnicodeDecodeError):
                skipped += 1
                continue

        return (patched, skipped)

    def setup_mcp_server(
        self,
        eyes_enabled: bool = False,
        tts_enabled: bool = False,
        light_enabled: bool = False,
    ) -> bool:
        """Configure Anima MCP server in global Claude settings (~/.claude.json).

        Args:
            eyes_enabled: Whether to enable eyes (visual expression)
            tts_enabled: Whether to enable TTS (text-to-speech)
            light_enabled: Whether to enable i-Buddy USB light

        Returns:
            True if successful
        """
        settings_path = get_global_claude_settings_path()

        # Load existing settings or create new
        settings = {}
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text())
            except json.JSONDecodeError:
                safe_print(f"  {get_icon('', '[!]')}  Invalid JSON in {settings_path}, creating backup")
                shutil.copy2(settings_path, settings_path.with_suffix(".json.bak"))
                settings = {}

        # Ensure mcpServers section exists
        if "mcpServers" not in settings:
            settings["mcpServers"] = {}

        # Find the uv executable path
        uv_path = shutil.which("uv") or "uv"

        # Build server arguments
        server_args = ["run", "anima", "--server"]
        if eyes_enabled:
            server_args.append("--eyes")
        if tts_enabled:
            server_args.append("--tts")
        if light_enabled:
            server_args.append("--light")

        # Configure Anima MCP server
        # OPENBLAS_NUM_THREADS=1 fixes scipy hang on Windows with Python 3.13
        # See: https://github.com/scipy/scipy/issues/20294
        settings["mcpServers"]["anima"] = {
            "type": "stdio",
            "command": uv_path,
            "args": server_args,
            "env": {
                "OPENBLAS_NUM_THREADS": "1",
            },
        }

        # Add MCP tool permissions to avoid authorization prompts
        if "permissions" not in settings:
            settings["permissions"] = {}
        if "allow" not in settings["permissions"]:
            settings["permissions"]["allow"] = []

        # MCP tool permissions use format: mcp__<server>__<tool>
        # Consolidated tools (token-optimized - see Anthropic MCP best practices)
        mcp_permissions = [
            "mcp__anima__memory",  # remember|recall|forget|list|refresh
            "mcp__anima__curiosity",  # add|research|complete|diary|list
        ]

        # Eyes tool (visual expression)
        if eyes_enabled:
            mcp_permissions.append("mcp__anima__eyes")  # emotion|look|blink|color|state|list

        # Voice tool (TTS)
        if tts_enabled:
            mcp_permissions.append("mcp__anima__voice")  # speak|set|list

        # Light tool (i-Buddy USB)
        if light_enabled:
            mcp_permissions.append("mcp__anima__light")  # color|rgb|off|list

        added_permissions = []
        for perm in mcp_permissions:
            if perm not in settings["permissions"]["allow"]:
                settings["permissions"]["allow"].append(perm)
                added_permissions.append(perm)

        # Write back
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        safe_print(f"  {get_icon('', '[OK]')} MCP server configured in {settings_path}")

        if added_permissions:
            safe_print(f"  {get_icon('', '[OK]')} Added {len(added_permissions)} MCP tool permissions")

        if eyes_enabled:
            safe_print(f"  {get_icon('', '[OK]')} Eyes enabled (visual expression)")
        if tts_enabled:
            safe_print(f"  {get_icon('', '[OK]')} TTS enabled (text-to-speech)")

        return True

    def run_full_setup(
        self,
        project_dir: Path,
        force: bool = False,
        no_patch: bool = False,
        with_startup_hook: bool = True,
        mode: str = "skill",
        eyes_enabled: bool = False,
        tts_enabled: bool = False,
        light_enabled: bool = False,
    ) -> bool:
        """Run the complete setup for Claude Code.

        Extends base setup to handle MCP server configuration.
        """
        success = True

        # If MCP mode, configure MCP server first
        if mode in ("mcp", "both"):
            print("Configuring MCP server...")
            try:
                if not self.setup_mcp_server(eyes_enabled, tts_enabled, light_enabled):
                    success = False
                print()
            except Exception as e:
                print(f"  Error configuring MCP server: {e}\n")
                success = False

        # Commands - always install (needed as fallback even in MCP mode,
        # and some commands like /refresh-memories are essential at startup)
        print(f"Installing commands ({self.name})...")
        try:
            copied, skipped = self.setup_commands(project_dir, force)
            print(f"  Commands: {copied} installed, {skipped} skipped\n")
        except Exception as e:
            print(f"  Error installing commands: {e}\n")
            success = False

        # Skills - always install (many skills like /dream, /curious
        # don't have MCP equivalents, so they're needed even in MCP mode)
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

        # Hooks (always configure)
        print(f"Configuring {self.display_name} hooks...")
        try:
            if not self.setup_hooks(project_dir, force, with_startup_hook):
                pass  # Warning already printed
            if not with_startup_hook:
                safe_print(f"  {get_icon('', '[!]')} SessionStart 'startup' hook DISABLED (Windows Terminal workaround)")
                safe_print("      Use /load-context to manually load memories at session start")
            print()
        except Exception as e:
            print(f"  Error configuring hooks: {e}\n")
            success = False

        # Patch global agents (~/.claude/agents/) to prevent them overriding anima
        if not no_patch:
            try:
                patched, skipped = self._patch_global_agents()
                if patched > 0:
                    print(f"Patched {patched} global agent(s) as subagents\n")
            except Exception as e:
                print(f"  Error patching global agents: {e}\n")

        # Extras (local agent patching, only if SKILL or BOTH mode)
        if mode in ("skill", "both") and not no_patch:
            try:
                if not self.setup_extras(project_dir, force):
                    pass  # Warning already printed
            except Exception as e:
                print(f"  Error in platform extras: {e}\n")
                success = False

        # Write setup version marker for update detection
        if success:
            self.write_setup_version_marker(project_dir)

        return success
