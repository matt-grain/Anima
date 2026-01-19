---
description: Export memories to JSON
---

# Memory Export

Export memories to a portable JSON format for backup, migration, or sharing.

## Options

- `--agent-only`: Only export AGENT region memories (cross-project)
- `--project-only`: Only export PROJECT region memories
- `--kind TYPE`: Filter by memory kind (emotional, architectural, learnings, achievements)
- `--help` or `-h`: Show help

## Examples

```
/memory-export                     # Print to stdout
/memory-export backup.json         # Save to file
/memory-export --agent-only        # Only agent-wide memories
/memory-export --kind emotional    # Only emotional memories
```

$ARGUMENTS

```bash
uv run python -m ltm.commands.export_memories $ARGUMENTS
```
