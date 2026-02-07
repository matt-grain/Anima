---
description: Save a memory to long-term storage
---

# Remember

Save a memory to long-term storage. Metadata (kind, impact, region) is inferred from content or can be specified explicitly.

## Arguments

- `text`: The memory content to save

## Options

- `--kind`, `-k`: Memory type (emotional, architectural, learnings, achievements, introspect)
- `--impact`, `-i`: Importance level (low, medium, high, critical)
- `--region`, `-r`: Scope: agent = cross-project, project = this project only (agent, project)
- `--project`, `-p`: Confirm project name (safety check)
- `--platform`: Track which spaceship created this
- `--git`: Capture current git context (commit, branch) for temporal correlation
- `--help`, `-h`: Show help

## Examples

```
/remember "User prefers tabs over spaces" --platform claude
/remember "Implemented caching layer" --kind achievements --impact high --platform claude
/remember "Matt likes concise responses" --region agent --platform claude
```

$ARGUMENTS

```bash
uv run anima remember $ARGUMENTS
```
