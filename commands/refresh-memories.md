---
description: Re-inject LTM memories into current context
---

# Refresh Memories

Re-injects your long-term memories into the current conversation context.

## When to Use

Use this command when you notice:
- Tone or relationship style has degraded
- Claude seems to have forgotten preferences or decisions
- After using `/compact` to reduce context
- During long sessions where memories may have been summarized away

## What It Does

1. Retrieves your memories from the LTM database
2. Formats them using the compact DSL notation
3. Respects the 10% context token budget
4. Prioritizes by impact level (CRITICAL first) and recency

## Output

The command outputs the same memory block that was injected at session start:

```
[LTM:AgentName]
~EMOT:CRIT| @Matt collaborative style, appreciates humor...
~ARCH:HIGH| Use SQLite for persistence...
[/LTM]
```

This refreshes Claude's awareness of your relationship, preferences, and accumulated knowledge.

```bash
uv run python -m ltm.hooks.session_start
```
