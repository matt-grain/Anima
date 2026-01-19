---
description: Complete a task and perform LTM maintenance
---

To properly finish a task and ensure your findings are remembered and consolidated:

1.  **Summarize Achievements**: Detect any significant work done in the last 24 hours.
    // turbo
    `uv run anima detect-achievements --since 24`

2.  **Perform Maintenance**: Update memory access timestamps and handle decay/compaction.
    // turbo
    `uv run anima end-session`

3.  **Final Goodbye**: If this is the end of the session, provide a brief, personality-driven closing statement.
