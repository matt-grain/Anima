---
name: dream
description: Between-session memory processing - dream stages N2/N3/REM
---

# /dream - Memory Dream Processing

Run between-session memory processing inspired by human sleep stages.

## Stages

- **N2**: Memory consolidation (link discovery, impact adjustment)
- **N3**: Deep processing (gist extraction, contradiction detection)
- **REM**: Lucid dreaming (distant associations, questions, self-model)

## Usage

```bash
# Full dream cycle
uv run anima dream

# Specific stage
uv run anima dream --stage rem

# Preview without processing
uv run anima dream --dry-run

# Resume interrupted dream
uv run anima dream --resume
```

## Options

- `--stage STAGE`: n2, n3, rem, or all (default: all)
- `--lookback-days N`: Process memories from last N days (default: 7)
- `--dry-run`: Show what would happen
- `--resume`: Continue interrupted dream
- `--restart`: Abandon and start fresh

## After Dreaming

Run `uv run anima dream-wake` to save insights to long-term memory.
