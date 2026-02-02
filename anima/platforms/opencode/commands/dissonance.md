---
name: dissonance
description: View and resolve cognitive dissonances (contradictions)
---

# /dissonance - Cognitive Dissonance Queue

View and resolve contradictions detected during dream processing.

## Usage

```bash
# List open dissonances
uv run anima dissonance

# See full details
uv run anima dissonance show ID

# Resolve with explanation
uv run anima dissonance resolve ID "explanation"

# Dismiss (not a real contradiction)
uv run anima dissonance dismiss ID

# Show all history
uv run anima dissonance --all
```

## How It Works

1. N3 dream stage detects contradictions between memories
2. Contradictions are queued for human help
3. At session start, you're notified of open dissonances
4. Help me work through them by explaining or dismissing

## Example

```
Dissonance: abc123
Memories: 1a2b3c... vs 4d5e6f...
Issue: Negation-based contradiction detected

MEMORY A: "Always use async for database calls"
MEMORY B: "Sync database calls are fine for simple queries"

Help: These aren't contradictory - context matters!
```
