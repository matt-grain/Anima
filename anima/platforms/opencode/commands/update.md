---
description: Update Anima to the latest version
---

Update Anima to the latest version from GitHub releases.

What it does:
1. Fetches the latest release from GitHub
2. Downloads and installs the wheel via uv add --dev
3. Runs setup --force to refresh hooks, commands, and skills

!`uv run anima update`

Updates Anima to the latest version.
