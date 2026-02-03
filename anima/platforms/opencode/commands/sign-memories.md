---
description: Sign all unsigned memories with your signing key
---

Signs all existing unsigned memories using the agent's signing key from config.

Parameters:
-  --dry-run, -n  Show what would be signed without making changes

Examples:
-  /sign-memories --dry-run     # Preview what will be signed
-  /sign-memories               # Sign all unsigned memories

!`uv run anima sign-memories <parameters>`
