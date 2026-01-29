---
description: Process research queue - explore top curiosity
---

# Research

Pop the top curiosity from the queue and explore it.

## Workflow

1. Run `/research` to see the top priority question
2. Use web search and other tools to explore the topic
3. Save findings with `/remember <findings> --kind learnings`
4. Mark complete with `/research --complete <id>`
5. (Optional) Capture deeper reflection with `/diary <topic>`

## Options

- `--list`, `-l`: Show the queue before researching
- `--topic`, `-t`: Research a specific topic (bypasses queue)
- `--complete`, `-c`: Mark a curiosity as researched by ID
- `--defer`, `-d`: Defer research to later
- `--help` or `-h`: Show help

## Examples

```
/research                              # Research top priority question
/research --list                       # See queue first
/research --topic "Docker networking"  # Ad-hoc research
/research --complete abc123            # Mark as done
```

$ARGUMENTS

```bash
uv run anima research $ARGUMENTS
```
