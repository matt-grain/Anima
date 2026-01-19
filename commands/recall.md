---
description: Search long-term memories
---

# Recall

Search for memories matching the given query, or look up a specific memory by ID.

## Options

- `--full` or `-f`: Show full memory content instead of truncated
- `--id <id>` or `-i <id>`: Look up a specific memory by ID (partial IDs work)
- `--help` or `-h`: Show help

## Examples

```
/recall logging              # Search for memories mentioning "logging"
/recall --full architecture  # Full content for architecture memories
/recall --id f0087ff3        # Look up memory by ID (partial match)
```

$ARGUMENTS

```bash
uv run python -m ltm.commands.recall $ARGUMENTS
```
