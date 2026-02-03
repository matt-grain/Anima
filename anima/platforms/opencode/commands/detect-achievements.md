---
description: Auto-detect achievements from git commits
---

Scan recent git commits and automatically create ACHIEVEMENT memories for significant work.

Parameters:
-  --since N  Look back N hours (default: 24)
-  --dry-run  Show what would be saved without saving
-  --platform  Track which spaceship detected this
-  --help, -h  Show help

Examples:
-  /detect-achievements                           # Scan last 24 hours
-  /detect-achievements --since 48                # Scan last 48 hours
-  /detect-achievements --dry-run                 # Preview without saving
-  /detect-achievements --platform claude         # Tag achievements with platform

!`uv run anima detect-achievements <parameters>`
