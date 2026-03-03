# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""LTM CLI - Entry point for Long Term Memory commands."""

import sys


def _run_server(args: list[str]) -> int:
    """Start the MCP server."""
    # Parse server-specific arguments
    eyes_enabled = "--eyes" in args
    tts_enabled = "--tts" in args
    light_enabled = "--light" in args
    eyes_config = None

    # Extract --eyes-config value if provided
    for i, arg in enumerate(args):
        if arg == "--eyes-config" and i + 1 < len(args):
            eyes_config = args[i + 1]

    from anima.server import run_server

    run_server(
        eyes_enabled=eyes_enabled,
        tts_enabled=tts_enabled,
        light_enabled=light_enabled,
        eyes_config_path=eyes_config,
    )
    return 0


def main() -> int:
    """Main entry point for LTM CLI."""
    # Handle --server flag at any position
    if "--server" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--server"]
        return _run_server(args)

    if len(sys.argv) < 2 or "help" in sys.argv[1]:
        print("LTM - Long Term Memory for Anima")
        print("Usage: uv run anima <command> [args]")
        print("")
        print("Core Memory:")
        print("  remember <text>        Save a memory")
        print("  recall <query>         Search memories")
        print("  forget <id>            Remove a memory")
        print("  memories               List all memories")
        print("")
        print("Session:")
        print("  refresh-memories       Re-inject ALL memories into context")
        print("")
        print("Dream:")
        print("  dream                  Between-session memory processing (N2/N3/REM + reflection)")
        print("")
        print("Curiosity:")
        print("  curious <question>     Add question to research queue (shows queue summary)")
        print("  research               Process research queue (--list to view queue)")
        print("  diary [title]          Create/manage research diary entries")
        print("")
        print("Diagnostics:")
        print("  memory-stats           Show memory statistics")
        print("  memory-graph           Visualize memory relationships")
        print("  dissonance             View/resolve cognitive dissonances")
        print("  trust-status           Show cognitive auth trust level (debug)")
        print("")
        print("Import/Export:")
        print("  memory-export          Export memories to JSON")
        print("  memory-import          Import memories from JSON")
        print("")
        print("System:")
        print("  setup                  Set up LTM in current project")
        print("  server                 Start MCP server (also: --server flag)")
        print("  eyes-daemon            Manage the eyes display daemon (start/stop/status)")
        print("  version                Show installed version (includes update check)")
        print("  update                 Update to latest version from GitHub")
        print("")
        print("Internal (auto-triggered by hooks/agents):")
        print("  load-context, load-deferred, process-subconscious, save-subconscious,")
        print("  dream-wake, end-session, detect-achievements, sign-memories, backfill,")
        print("  keygen, generate-commands, check-update, import-seeds, curiosity-queue")
        return 0

    command = sys.argv[1]
    args = sys.argv[2:]

    match command:
        case "remember":
            from anima.commands.remember import run

            return run(args)
        case "recall":
            from anima.commands.recall import run

            return run(args)
        case "forget":
            from anima.commands.forget import run

            return run(args)
        case "memories":
            from anima.commands.memories import run

            return run(args)
        case "curious":
            from anima.commands.curious import run

            return run(args)
        case "research":
            from anima.commands.research import run

            return run(args)
        case "curiosity-queue":
            from anima.commands.curiosity_queue import run

            return run(args)
        case "diary":
            from anima.commands.diary import run

            return run(args)
        case "keygen":
            from anima.tools.keygen import run

            return run(args)
        case "import-seeds":
            from anima.tools.import_seeds import run

            return run(args)
        case "load-context":
            from anima.hooks.session_start import run

            # Load all memories by default (no deferred) when called from CLI
            # User can override with --no-all if they want tiered loading
            if "--no-all" not in args:
                args = ["--all"] + list(args)
            return run(args)
        case "load-deferred":
            from anima.commands.load_deferred import run

            return run()
        case "end-session":
            from anima.hooks.session_end import run

            return run(args)
        case "detect-achievements":
            from anima.tools.detect_achievements import run

            return run(args)
        case "setup":
            from anima.tools.setup import run

            return run(args)
        case "server":
            return _run_server(args)
        case "eyes-daemon":
            from anima.commands.eyes_daemon import run

            return run(args)
        case "memory-graph" | "graph":
            from anima.commands.graph import run

            return run(args)
        case "memory-stats" | "stats":
            from anima.commands.stats import run

            return run(args)
        case "memory-export" | "export-memories":
            from anima.commands.export_memories import run

            return run(args)
        case "memory-import" | "import-memories":
            from anima.commands.import_memories import run

            return run(args)
        case "sign-memories":
            from anima.tools.sign_memories import run

            return run(args)
        case "refresh-memories":
            from anima.hooks.session_start import run

            # Load all memories by default (no deferred) when called from CLI
            if "--no-all" not in args:
                args = ["--all"] + list(args)
            return run(args)
        case "backfill":
            from anima.commands.backfill import run

            return run(args)
        case "dream":
            from anima.commands.dream import run

            return run(args)
        case "dream-wake":
            from anima.commands.dream_wake import run

            return run(args)
        case "dissonance":
            from anima.commands.dissonance import run

            return run(args)
        case "trust-status" | "trust":
            from anima.commands.trust_status import run

            return run(args)
        case "re-embed":
            from anima.commands.re_embed import run

            return run(args)
        case "mirror-review" | "mirror":
            from anima.commands.mirror_review import run

            return run(args)
        case "version":
            from anima.tools.version import run_version

            return run_version(args)
        case "check-update":
            from anima.tools.version import run_check_update

            return run_check_update(args)
        case "update":
            from anima.tools.version import run_update

            return run_update(args)
        case "generate-commands":
            from anima.tools.generate import run

            return run(args)
        case _:
            print(f"Unknown command: {command}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
