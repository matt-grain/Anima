---
description: Add question to research queue for autonomous learning
---

# Curious

Add a question or topic to your research queue for later exploration. Questions that recur get automatic priority bumps.

## Arguments

- `question`: The question or topic to add to the research queue

## Options

- `--region`, `-r`: Where to store (agent = cross-project, project = local) (agent, project)
- `--context`, `-c`: What triggered this curiosity
- `--help`, `-h`: Show help

## Examples

```
/curious "Why does Python GIL affect async?"
/curious "Latest LLM introspection research" --region agent
/curious "Why did pytest break?" --context "upgrade to 3.12"
```

$ARGUMENTS

```bash
uv run anima curious $ARGUMENTS
```
