---
description: Export memories to JSON
---

Export memories to a portable JSON format for backup, migration, or sharing.

positional arguments:
  file                Output file path (prints to stdout if not specified)

Optional flags:
-  --agent-only  Only export AGENT region memories (cross-project)
-  --project-only  Only export PROJECT region memories
-  --kind  {emotional,architectural,learnings,achievements,introspect} TYPE  Filter by memory kind
-  --help, -h  Show help

Examples:
-  /memory-export                     # Print to stdout
-  /memory-export backup.json         # Save to file
-  /memory-export --agent-only        # Only agent-wide memories
-  /memory-export --kind emotional    # Only emotional memories

!`uv run anima memory-export <parameters>`
