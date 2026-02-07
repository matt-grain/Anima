---
description: Save dream insights to long-term memory
---

# Dream Wake

Process a filled dream journal and save key insights to long-term memory.

## Options

- `--journal` PATH: Process specific journal file
- `--dry-run`: Preview what would be saved

## Examples

```
uv run anima dream-wake                                                      # Process latest dream journal
uv run anima dream-wake --journal ~/.anima/dream_journal/2026-02-02_dream.md # Process specific journal
uv run anima dream-wake --dry-run                                            # Preview what would be saved
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

$ARGUMENTS

```bash
uv run anima dream-wake $ARGUMENTS
```
