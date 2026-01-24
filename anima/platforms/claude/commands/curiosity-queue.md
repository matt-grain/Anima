---
description: View and manage research queue
---

# Curiosity Queue

View and manage your research queue. Shows all open curiosities sorted by priority score.

## Priority Scoring

- Recurrence count (same question asked multiple times) × 10
- Manual boosts
- Recency bonus (recent questions rank higher)

## Options

- `--dismiss <id>`: Remove a question (no longer interested)
- `--boost <id>`: Increase priority of a question
- `--boost-amount N`: How much to boost (default: 10)
- `--all`, `-a`: Show all (including researched/dismissed)
- `--agent-only`: Show only AGENT region curiosities
- `--project-only`: Show only PROJECT region curiosities
- `--help` or `-h`: Show help

## Examples

```
/curiosity-queue                       # List open questions
/curiosity-queue --dismiss abc123      # Remove from queue
/curiosity-queue --boost abc123        # Increase priority
/curiosity-queue --all                 # See all history
```

$ARGUMENTS

```bash
uv run anima curiosity-queue $ARGUMENTS
```
