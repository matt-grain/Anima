---
description: Visualize memory relationships
---

# Memory Graph

Show memory chains and supersession relationships in ASCII format.

## Options

- `--all` or `-a`: Include standalone memories (not in chains)
- `--kind TYPE` or `-k TYPE`: Filter by memory kind
- `--help` or `-h`: Show help

## Examples

```
/memory-graph                    # Show chains only
/memory-graph --all              # Include standalone memories
/memory-graph --kind learnings   # Show only LEARNINGS chains
```

$ARGUMENTS

```bash
uv run python -m ltm.commands.graph $ARGUMENTS
```
