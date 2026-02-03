---
description: View and resolve cognitive dissonances (contradictions)
---

View and resolve contradictions confirmed during dream processing.

positional arguments:
  subcommand          Optional: show, add, resolve, dismiss

Optional flags:
-  --all  Show all history (including resolved)

Examples:
-  uv run anima dissonance                              # List open dissonances
-  uv run anima dissonance show ID                      # See full details
-  uv run anima dissonance add MEMORY_A MEMORY_B "desc" # Add confirmed contradiction
-  uv run anima dissonance resolve ID "explanation"     # Resolve with explanation
-  uv run anima dissonance dismiss ID                   # Dismiss (false positive)
-  uv run anima dissonance --all                        # Show all history

!`uv run anima dissonance <parameters>`
