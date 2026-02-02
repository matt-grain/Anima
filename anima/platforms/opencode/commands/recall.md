---
description: Recall recent memories
---

Query the memories to recall what was done in previous sessions.

Parameters:
-  --full, -f      Show full memory content
-  --kind, -k      Filter by memory kind (EMOTIONAL, ARCHITECTURAL, LEARNINGS, ACHIEVEMENTS, INTROSPECT, DREAM)
-  --limit, -l     Maximum results to return (default: 10)
-  --semantic, -s  Use semantic (embedding) search
-  --id, -i        Look up a specific memory by ID (full or partial)
-  --help, -h      Show this help message

Examples:
-  /recall logging              # Search for memories mentioning "logging"
-  /recall --kind DREAM         # List dream insights
-  /recall --kind DREAM --full  # Full dream content

!`uv run anima recall <parameters>`

Here are your recent memories.
