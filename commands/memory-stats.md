---
description: Show memory statistics
---

# Memory Stats

Display statistics about stored memories for the current agent.

## What It Shows

- Total memory count
- Breakdown by region (AGENT vs PROJECT)
- Breakdown by kind (EMOTIONAL, ARCHITECTURAL, LEARNINGS, ACHIEVEMENTS)
- Breakdown by impact level (CRITICAL, HIGH, MEDIUM, LOW)
- Health indicators (active, superseded, low confidence)

## Example

```
/memory-stats
```

$ARGUMENTS

```bash
uv run python -m ltm.commands.stats $ARGUMENTS
```
