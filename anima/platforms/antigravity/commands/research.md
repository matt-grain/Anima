// turbo
---
description: Process research queue - explore top curiosity
---

# Research

Pop the top curiosity from the queue and explore it.

## Optional Flags

- `--list` or `-l`: Show the queue before researching
- `--topic` or `-t`: Research a specific topic (bypasses queue)
- `--complete` or `-c`: Mark a curiosity as researched by ID
- `--defer` or `-d`: Defer research to later
- `--help` or `-h`: Show help

## Examples

```
/research                              # Research top priority question
/research --list                       # See queue first
/research --topic "Docker networking"  # Ad-hoc research
/research --complete abc123            # Mark as done
```

## Workflow

1. Run `/research` to see the top priority question
2. Use web search and other tools to explore the topic
3. Save findings with `/remember <findings> --kind learnings`
4. Mark complete with `/research --complete <id>`
5. (Optional) Capture deeper reflection with `/diary <topic>`

$ARGUMENTS

```bash
uv run python -m anima.commands.research $ARGUMENTS
```
