---
description: View and resolve cognitive dissonances (contradictions)
---

# Dissonance

View and resolve contradictions confirmed during dream processing.

## Arguments

- `subcommand`: Optional: show, add, resolve, dismiss (optional)

## Options

- `--all`: Show all history (including resolved)

## Examples

```
uv run anima dissonance                              # List open dissonances
uv run anima dissonance show ID                      # See full details
uv run anima dissonance add MEMORY_A MEMORY_B "desc" # Add confirmed contradiction
uv run anima dissonance resolve ID "explanation"     # Resolve with explanation
uv run anima dissonance dismiss ID                   # Dismiss (false positive)
uv run anima dissonance --all                        # Show all history
```

## How It Works

1. N3 dream stage detects contradiction *candidates* using heuristics
2. Candidates appear in REM dream template for evaluation
3. During lucid dream, I evaluate each: real contradiction or false positive?
4. Real contradictions are added via `dissonance add` for human help
5. At session start, you're notified of open dissonances

## Example

During dream, I see a candidate:
```
Candidate 1 (Negation-based contradiction detected)
> A: "Always use async for database calls"
> B: "Sync database calls are fine for simple queries"

Verdict: FALSE POSITIVE - these aren't contradictory, context matters!
```

If it were a real contradiction, I would run:
```bash
uv run anima dissonance add abc123 def456 "Conflicting advice about database call patterns"
```

$ARGUMENTS

```bash
uv run anima dissonance $ARGUMENTS
```
