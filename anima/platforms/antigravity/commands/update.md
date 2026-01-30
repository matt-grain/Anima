// turbo
---
description: Update Anima to the latest version
---

# Update

Update Anima to the latest version from GitHub releases.

## What It Does

1. Fetches the latest release from GitHub
2. Downloads and installs the wheel via `uv add --dev`
3. Runs `setup --force` to refresh hooks, commands, and skills

## Example

```
/update
```

$ARGUMENTS

```bash
uv run anima update $ARGUMENTS
```
