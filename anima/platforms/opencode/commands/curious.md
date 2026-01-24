---
description: Add question to research queue
---

Add a question or topic to the research queue for later exploration.

positional arguments:
  question              The question or topic to research

Optional flags:
-  -h, --help: show this help message and exit
-  --region, -r {agent,project}: Where to store: 'agent' (cross-project) or 'project' (local)
-  --context, -c CONTEXT: What triggered this curiosity

!`uv run anima curious <parameters> "question"`

Question added to research queue.
