---
description: List all memories for current agent/project
---

# Memories

List all memories for the current agent and project.

## Options

- `--kind`, `-k`: Filter by type (emotional, architectural, learnings, achievements, introspect)
- `--region`, `-r`: Filter by region (agent, project)
- `--all`, `-a`: Include superseded memories
- `--help`, `-h`: Show help

## Examples

```
/memories                          # List all memories
/memories --kind achievements      # Only achievements
/memories --region agent           # Only agent-wide memories
/memories --all                    # Include superseded
```

$ARGUMENTS

```bash
uv run anima memories $ARGUMENTS
```
