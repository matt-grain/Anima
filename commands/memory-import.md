---
description: Import memories from JSON
---

# Memory Import

Import memories from a previously exported JSON file.

## Options

- `--dry-run`: Show what would be imported without saving
- `--merge`: Skip existing memories instead of failing on duplicates
- `--remap-agent`: Assign all memories to current agent (useful when importing from another agent)
- `--help` or `-h`: Show help

## Examples

```
/memory-import backup.json                    # Import all memories
/memory-import backup.json --dry-run          # Preview import
/memory-import backup.json --merge            # Skip duplicates
/memory-import other-agent.json --remap-agent # Import as current agent
```

$ARGUMENTS

```bash
uv run python -m ltm.commands.import_memories $ARGUMENTS
```
