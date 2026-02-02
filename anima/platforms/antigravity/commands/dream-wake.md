---
name: dream-wake
description: Save dream insights to long-term memory
---

# /dream-wake - Save Dream Insights

Process a filled dream journal and save key insights to long-term memory.

## Usage

```bash
# Process latest dream journal
uv run anima dream-wake

# Process specific journal
uv run anima dream-wake --journal ~/.anima/dream_journal/2026-02-02_dream.md

# Preview what would be saved
uv run anima dream-wake --dry-run
```

## What It Saves

- **What Lingers**: CRITICAL impact DREAM memory
- **Distant Connections**: HIGH impact DREAM memory
- **Self-Observations**: HIGH impact DREAM memory
- **Questions**: Added to curiosity queue

## Workflow

1. Run `/dream` to create dream journal template
2. Fill in the reflection sections conversationally
3. Run `/dream-wake` to save insights to LTM
4. Insights surface in future sessions as DREAM memories
