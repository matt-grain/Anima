// turbo
---
description: Sign all unsigned memories with your signing key
---

# Sign Memories

Signs all existing unsigned memories using the agent's signing key from config.

## When to Use

Use this command when you:
- Add a signing key to an existing LTM installation
- Import unsigned memories from another source
- Want to authenticate your memory history

## Prerequisites

You must have a signing key configured in `~/.anima/config.json`:

```json
{
  "agent": {
    "signing_key": "your-secret-key-here"
  }
}
```

## Options

- `--dry-run` or `-n`: Show what would be signed without making changes

## Examples

```
/sign-memories --dry-run     # Preview what will be signed
/sign-memories               # Sign all unsigned memories
```

$ARGUMENTS

```bash
uv run python -m anima.tools.sign_memories $ARGUMENTS
```
