// turbo
---
description: Remove a memory by ID
---

# Forget

Remove a memory by its ID. Supports partial ID matching.

## Arguments

- `id`: Memory ID to remove (partial match supported)

## Examples

```
/forget abc123      # Remove memory with ID starting with abc123
```

$ARGUMENTS

```bash
uv run python -m anima.commands.forget $ARGUMENTS
```
