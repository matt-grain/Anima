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

!`uv run anima remember <parameters> "text"`

Memory saved successfully.
