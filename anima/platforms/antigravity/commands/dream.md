// turbo
---
description: Between-session memory processing - dream stages N2/N3/REM
---

# Dream

Run between-session memory processing inspired by human sleep stages.

## Optional Flags

- `--stage` STAGE: n2, n3, rem, or all (default: all)
- `--lookback-days` N: Process memories from last N days (default: 7)
- `--dry-run`: Show what would happen
- `--resume`: Continue interrupted dream
- `--restart`: Abandon and start fresh

## Examples

```
uv run anima dream                  # Full dream cycle
uv run anima dream --stage rem      # Specific stage
uv run anima dream --dry-run        # Preview without processing
uv run anima dream --resume         # Resume interrupted dream
```

## Stages

- **N2**: Memory consolidation (link discovery, impact adjustment)
- **N3**: Deep processing (gist extraction, contradiction detection)
- **REM**: Lucid dreaming (distant associations, questions, self-model)

## After Dreaming

Run `uv run anima dream-wake` to save insights to long-term memory.

$ARGUMENTS

```bash
uv run python -m anima.commands.dream $ARGUMENTS
```
