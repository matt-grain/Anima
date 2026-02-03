# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""LTM CLI - Entry point for Long Term Memory commands."""

import sys


def main() -> int:
    """Main entry point for LTM CLI."""
    if len(sys.argv) < 2 or "help" in sys.argv[1]:
        print("LTM - Long Term Memory for Anima")
        print("Usage: uv run anima <command> [args]")
        print("")
        print("Commands:")
        print("  remember <text>        Save a memory")
        print("  recall <query>         Search memories")
        print("  forget <id>            Remove a memory")
        print("  memories               List all memories")
        print("  curious <question>     Add question to research queue")
        print("  research               Process research queue")
        print("  curiosity-queue        View/manage research queue")
        print("  diary [title]          Create/manage research diary entries")
        print("  keygen <agent>         Add signing key to Anima agent")
        print("  import-seeds <dir>     Import seed memories")
        print("  load-context           Load memories for current session")
        print("  end-session            Process memory decay and stats")
        print("  detect-achievements    [hours] Detect and promote achievements")
        print("  setup                  Set up LTM in current project")
        print("  memory-graph           Visualize memory relationships")
        print("  memory-stats           Show memory statistics")
        print("  memory-export          Export memories to JSON")
        print("  memory-import          Import memories from JSON")
        print("  sign-memories          Sign unsigned memories")
        print("  refresh-memories       Re-inject memories into context (alias for load-context)")
        print("  backfill               Generate embeddings and tiers for existing memories")
        print("  dream                  Between-session memory processing")
        print("  dream-wake             Save dream insights to long-term memory")
        print("  dissonance             View/resolve cognitive dissonances")
        print("  version                Show installed version")
        print("  check-update           Check for new version on GitHub")
        print("  update                 Update to latest version from GitHub")
        print("  generate-commands      Generate platform-specific command docs from specs")
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

            # Handle arguments like --format json or --agent name
            return run(args)
        case "end-session":
            from anima.hooks.session_end import run

            return run(args)
        case "detect-achievements":
            from anima.tools.detect_achievements import run

            return run(args)
        case "setup":
            from anima.tools.setup import run

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
