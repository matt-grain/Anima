// turbo
---
description: Search long-term memories
---

# Recall

Search for memories matching the given query, or look up a specific memory by ID.

## Options

- `--full` or `-f`: Show full memory content instead of truncated
- `--kind` or `-k`: Filter by memory kind (EMOTIONAL, ARCHITECTURAL, LEARNINGS, ACHIEVEMENTS, INTROSPECT, DREAM)
- `--limit` or `-l`: Maximum results to return (default: 10)
- `--semantic` or `-s`: Use semantic (embedding) search
- `--id <id>` or `-i <id>`: Look up a specific memory by ID (partial IDs work)
- `--help` or `-h`: Show help

## Examples

```
/recall logging              # Search for memories mentioning "logging"
/recall --full architecture  # Full content for architecture memories
/recall --kind DREAM         # List dream insights
/recall --kind DREAM --full  # Full dream content
/recall --id f0087ff3        # Look up memory by ID (partial match)
```

$ARGUMENTS

```bash
uv run python -m anima.commands.recall $ARGUMENTS
```
