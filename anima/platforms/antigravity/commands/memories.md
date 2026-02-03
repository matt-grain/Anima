// turbo
---
description: List all memories for current agent/project
---

# Memories

List all memories for the current agent and project.

## Optional Flags

- `--kind` or `-k`: Filter by type (emotional|architectural|learnings|achievements|introspect)
- `--region` or `-r`: Filter by region (agent|project)
- `--all` or `-a`: Include superseded memories
- `--help` or `-h`: Show help

## Examples

```
/memories                          # List all memories
/memories --kind achievements      # Only achievements
/memories --region agent           # Only agent-wide memories
/memories --all                    # Include superseded
```

$ARGUMENTS

```bash
uv run python -m anima.commands.memories $ARGUMENTS
```
