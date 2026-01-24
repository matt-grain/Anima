// turbo
---
description: Add question to research queue
---

# Curious

Add a question or topic to the research queue for later exploration.

## How It Works

Questions accumulate during sessions and are prioritized by recurrence.
If you ask the same question again, its priority automatically increases (like nagging thoughts!).

## Options

- `--region`, `-r`: Where to store (agent = cross-project, project = local)
- `--context`, `-c`: What triggered this curiosity
- `--help` or `-h`: Show help

## Examples

```
/curious Why does Python GIL affect async?
/curious "Latest LLM introspection research" --region agent
/curious "Why did pytest break?" --context "upgrade to 3.12"
```

$ARGUMENTS

```bash
uv run anima curious $ARGUMENTS
```
