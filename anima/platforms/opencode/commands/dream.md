---
description: Between-session memory processing - dream stages N2/N3/REM
---

Run between-session memory processing inspired by human sleep stages.

Parameters:
-  --stage STAGE  n2, n3, rem, or all (default: all)
-  --lookback-days N  Process memories from last N days (default: 7)
-  --dry-run  Show what would happen
-  --resume  Continue interrupted dream
-  --restart  Abandon and start fresh

Examples:
-  uv run anima dream                  # Full dream cycle
-  uv run anima dream --stage rem      # Specific stage
-  uv run anima dream --dry-run        # Preview without processing
-  uv run anima dream --resume         # Resume interrupted dream

!`uv run anima dream <parameters>`
