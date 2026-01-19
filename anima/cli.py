# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""LTM CLI - Entry point for Long Term Memory commands."""

import sys


def main() -> int:
    """Main entry point for LTM CLI."""
    if len(sys.argv) < 2:
        print("LTM - Long Term Memory for Anima")
        print("Usage: uv run anima <command> [args]")
        print("")
        print("Commands:")
        print("  remember <text>   Save a memory")
        print("  recall <query>    Search memories")
        print("  forget <id>       Remove a memory")
        print("  memories          List all memories")
        print("  keygen <agent>    Add signing key to Anima agent")
        print("  import-seeds <dir> Import seed memories")
        print("  load-context      Load memories for current session")
        print("  end-session       Process memory decay and stats")
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
        case _:
            print(f"Unknown command: {command}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
