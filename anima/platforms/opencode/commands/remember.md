---
description: Remember a memory
---

Remember a memory to long-term storage.

positional arguments:
  text                  The memory content to save

Optional flags:
-  -h, --help: show this help message and exit
-  --region, -r {agent,project}: Where to store: 'agent' (cross-project) or 'project' (local)
  --kind, -k {emotional,architectural,learnings,achievements,introspect}: Memory type
  --impact, -i {low,medium,high,critical}: Importance level
  --project, -p PROJECT: Confirm project name (must match cwd project for safety)
  --platform: Track which spaceship created this (always use `opencode` for this platform)
  --git: Capture current git context (commit, branch) for temporal correlation

!`uv run anima remember <parameters> --platform opencode "text"`

Memory saved successfully.
