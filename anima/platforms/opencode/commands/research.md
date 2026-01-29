---
description: Process research queue
---

Pop top curiosity from queue and explore it.

Workflow:
1. Run `/research` to see the top priority question
2. Use web search and other tools to explore the topic
3. Save findings with `/remember <findings> --kind learnings`
4. Mark complete with `/research --complete <id>`
5. (Optional) Capture deeper reflection with `/diary <topic>`

Optional flags:
-  -h, --help: show this help message and exit
-  --list, -l: Show the queue before researching
-  --topic, -t TOPIC: Research a specific topic (bypasses queue)
-  --complete, -c ID: Mark a curiosity as researched by ID
-  --defer, -d: Defer research to later

!`uv run anima research <parameters>`

Research mode activated.
