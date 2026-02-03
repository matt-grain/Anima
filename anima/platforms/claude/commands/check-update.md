---
description: Check if a new Anima version is available
---

# Check Update

Check if a newer version of Anima is available on GitHub.

## Examples

```
/check-update
```

## Output

```
Current version: v0.9.0
Checking matt-grain/Anima for updates...

  New version available: v0.10.0
  Release: https://github.com/matt-grain/Anima/releases/tag/v0.10.0

  Run 'anima update' to upgrade
```

If already up to date:
```
Current version: v0.9.0
Checking matt-grain/Anima for updates...

  You're up to date! (latest: v0.9.0)
```

$ARGUMENTS

```bash
uv run anima check-update $ARGUMENTS
```
