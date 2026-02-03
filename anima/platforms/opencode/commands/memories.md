---
description: List all memories for current agent/project
---

List all memories for the current agent and project.

Parameters:
-  --kind, -k  {emotional,architectural,learnings,achievements,introspect}  Filter by type
-  --region, -r  {agent,project}  Filter by region
-  --all, -a  Include superseded memories
-  --help, -h  Show help

Examples:
-  /memories                          # List all memories
-  /memories --kind achievements      # Only achievements
-  /memories --region agent           # Only agent-wide memories
-  /memories --all                    # Include superseded

!`uv run anima memories <parameters>`
