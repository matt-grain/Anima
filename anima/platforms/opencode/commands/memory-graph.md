---
description: Visualize memory relationships
---

Show memory chains and supersession relationships in ASCII format.

Parameters:
-  --all, -a  Include standalone memories (not in chains)
-  --kind, -k TYPE  Filter by memory kind
-  --help, -h  Show help

Examples:
-  /memory-graph                    # Show chains only
-  /memory-graph --all              # Include standalone memories
-  /memory-graph --kind learnings   # Show only LEARNINGS chains

!`uv run anima memory-graph <parameters>`
