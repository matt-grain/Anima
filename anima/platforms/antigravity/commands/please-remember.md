// turbo
---
description: Save something to long-term memory
---

# Please Remember

Save a memory to long-term storage. Metadata (kind, impact, region) is inferred from content or can be specified explicitly.

## Arguments

- `text`: The memory content to save

## Optional Flags

- `--kind` or `-k`: Memory type (emotional|architectural|learnings|achievements|introspect)
- `--impact` or `-i`: Importance level (low|medium|high|critical)
- `--region` or `-r`: Scope: agent = cross-project, project = this project only (agent|project)
- `--project` or `-p`: Confirm project name (safety check)
- `--platform`: Track which spaceship created this
- `--git`: Capture current git context (commit, branch) for temporal correlation
- `--help` or `-h`: Show help

## Examples

```
/remember "User prefers tabs over spaces" --platform antigravity
/remember "Implemented caching layer" --kind achievements --impact high --platform antigravity
/remember "Matt likes concise responses" --region agent --platform antigravity
```

$ARGUMENTS

```bash
uv run python -m anima.commands.remember $ARGUMENTS
```
