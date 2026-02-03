---
description: Process research queue - explore top curiosity
---

Pop the top curiosity from the queue and explore it.

Parameters:
-  --list, -l  Show the queue before researching
-  --topic, -t  Research a specific topic (bypasses queue)
-  --complete, -c  Mark a curiosity as researched by ID
-  --defer, -d  Defer research to later
-  --help, -h  Show help

Examples:
-  /research                              # Research top priority question
-  /research --list                       # See queue first
-  /research --topic "Docker networking"  # Ad-hoc research
-  /research --complete abc123            # Mark as done

!`uv run anima research <parameters>`
