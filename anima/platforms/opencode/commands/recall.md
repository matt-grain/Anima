---
description: Recall recent memories
---

Search for memories matching the given query, or look up a specific memory by ID.

positional arguments:
  query               Search term to match against memories

Optional flags:
-  --full, -f  Show full memory content instead of truncated
-  --kind, -k  {EMOTIONAL,ARCHITECTURAL,LEARNINGS,ACHIEVEMENTS,INTROSPECT,DREAM}  Filter by memory kind
-  --limit, -l  Maximum results to return (default: 10)
-  --semantic, -s  Use semantic (embedding) search
-  --id, -i <id>  Look up a specific memory by ID (partial IDs work)
-  --help, -h  Show help

Examples:
-  /recall logging              # Search for memories mentioning "logging"
-  /recall --full architecture  # Full content for architecture memories
-  /recall --kind DREAM         # List dream insights
-  /recall --kind DREAM --full  # Full dream content
-  /recall --id f0087ff3        # Look up memory by ID (partial match)

!`uv run anima recall <parameters>`

Here are your recent memories.
