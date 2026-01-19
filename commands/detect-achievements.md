---
description: Auto-detect achievements from git commits
---

# Detect Achievements

Scan recent git commits and automatically create ACHIEVEMENT memories for significant work.

## How It Works

Scans commit messages for patterns indicating achievements:
- Feature completion ("add", "implement", "complete")
- Version releases (v1.0.0, milestone, release)
- Major fixes ("fix critical", "resolve")
- Refactoring and migrations
- Test milestones (100% coverage, tests passing)

Skips non-achievements: WIP, fixup, merge, revert, chore commits.

## Options

- `--since N`: Look back N hours (default: 24)
- `--dry-run`: Show what would be saved without saving
- `--help` or `-h`: Show help

## Examples

```
/detect-achievements                  # Scan last 24 hours
/detect-achievements --since 48       # Scan last 48 hours
/detect-achievements --dry-run        # Preview without saving
```

$ARGUMENTS

```bash
uv run python -m ltm.tools.detect_achievements $ARGUMENTS
```
