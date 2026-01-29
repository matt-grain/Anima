---
description: Create and manage research diary entries
---

# Diary

The research diary captures not just what was learned, but what lingers after learning. The raw residue, not the report.

## Template Structure

1. **What Lingers** - Raw personal reflection (write this first!)
2. **Session Context** - What happened
3. **Topic** - What was explored
4. **Key Insights** - Structured learnings
5. **Connections** - Links to existing memories
6. **Evolution** - How thinking changed
7. **New Questions** - What emerged
8. **Learning Summary** - Bullet points for `/remember`

## Options

- `[title]`: Optional title for the entry
- `--list`, `-l`: List recent diary entries
- `--read`, `-r`: Read a specific entry by date
- `--learn`: Extract learnings from an entry
- `--path`, `-p`: Show diary directory location
- `--help` or `-h`: Show help

## Examples

```
/diary                           # Create new entry for today
/diary coffee break philosophy   # Create entry with title
/diary --list                    # List recent entries
/diary --read 2026-01-29         # Read specific entry
/diary --learn 2026-01-29        # Extract learnings to /remember
```

## Location

Diary entries are stored in `~/.anima/diary/` so they travel across projects.

$ARGUMENTS

```bash
uv run anima diary $ARGUMENTS
```
