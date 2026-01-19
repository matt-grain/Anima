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

## Examples

```
/please-remember This is crucial: never use print() for logging
/please-remember --region agent Matt prefers concise responses
/please-remember -r agent -k emotional -i critical Our founding collaboration
```

$ARGUMENTS

```bash
uv run python -m ltm.commands.remember $ARGUMENTS
```
