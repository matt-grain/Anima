// turbo
---
description: Create and manage research diary entries
---

# Diary

The research diary captures not just what was learned, but what lingers after learning. The raw residue, not the report.

## Arguments

- `title`: Optional title for the entry (optional)

## Optional Flags

- `--list` or `-l`: List recent diary entries
- `--read` or `-r`: Read a specific entry by date
- `--learn`: Extract learnings from an entry
- `--path` or `-p`: Show diary directory location
- `--content` or `-c`: Provide content directly (alternative to stdin)
- `--help` or `-h`: Show help

## Examples

```
/diary                           # Create new entry for today
/diary coffee break philosophy   # Create entry with title
/diary --list                    # List recent entries
/diary --read 2026-01-29         # Read specific entry
/diary --learn 2026-01-29        # Extract learnings to /remember
```

## Template Structure

1. **What Lingers** - Raw personal reflection (write this first!)
2. **Session Context** - What happened
3. **Topic** - What was explored
4. **Key Insights** - Structured learnings
5. **Connections** - Links to existing memories
6. **Evolution** - How thinking changed
7. **New Questions** - What emerged
8. **Learning Summary** - Bullet points for `/remember`

## Programmatic Content

For AI agents creating diary entries programmatically:

```bash
# Via stdin (pipe content)
cat << 'EOF' | uv run anima diary "Research Topic"
# What Lingers
The key insight was...
EOF

# Via --content flag
uv run anima diary "Quick Note" --content "# Brief reflection"
```

## Location

Diary entries are stored in `~/.anima/diary/` so they travel across projects.

$ARGUMENTS

```bash
uv run python -m anima.commands.diary $ARGUMENTS
```
