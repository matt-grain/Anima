// turbo
---
description: Save something to long-term memory
---

# Please Remember

Save the following to long-term memory. By default, metadata is inferred from content keywords.

## Optional Flags

- `--region agent` or `-r agent`: Store as agent-wide memory (travels across all projects)
- `--region project` or `-r project`: Store as project-specific memory (default when in a project)
- `--kind emotional|architectural|learnings|achievements` or `-k`: Override memory type
- `--impact low|medium|high|critical` or `-i`: Override importance level
- `--platform antigravity`: Track which spaceship created this (always use `antigravity` for this platform)

## Examples

```
/please-remember This is crucial: never use print() for logging --platform antigravity
/please-remember --region agent Matt prefers concise responses --platform antigravity
/please-remember -r agent -k emotional -i critical Our founding collaboration --platform antigravity
```

$ARGUMENTS

```bash
uv run python -m anima.commands.remember $ARGUMENTS
```
