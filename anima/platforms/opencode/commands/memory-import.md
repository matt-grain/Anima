---
description: Import memories from JSON
---

Import memories from a previously exported JSON file.

positional arguments:
  file                JSON file to import

Optional flags:
-  --dry-run  Show what would be imported without saving
-  --merge  Skip existing memories instead of failing on duplicates
-  --remap-agent  Assign all memories to current agent (useful when importing from another agent)
-  --help, -h  Show help

Examples:
-  /memory-import backup.json                    # Import all memories
-  /memory-import backup.json --dry-run          # Preview import
-  /memory-import backup.json --merge            # Skip duplicates
-  /memory-import other-agent.json --remap-agent # Import as current agent

!`uv run anima memory-import <parameters>`
