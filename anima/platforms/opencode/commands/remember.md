---
description: Save a memory to long-term storage
---

Save a memory to long-term storage. Metadata (kind, impact, region) is inferred from content or can be specified explicitly.

positional arguments:
  text                The memory content to save

Optional flags:
-  --kind, -k  {emotional,architectural,learnings,achievements,introspect}  Memory type
-  --impact, -i  {low,medium,high,critical}  Importance level
-  --region, -r  {agent,project}  Scope: agent = cross-project, project = this project only
-  --project, -p  Confirm project name (safety check)
-  --platform  Track which spaceship created this
-  --git  Capture current git context (commit, branch) for temporal correlation
-  --help, -h  Show help

Examples:
-  /remember "User prefers tabs over spaces" --platform opencode
-  /remember "Implemented caching layer" --kind achievements --impact high --platform opencode
-  /remember "Matt likes concise responses" --region agent --platform opencode

!`uv run anima remember <parameters>`

Memory saved successfully.
