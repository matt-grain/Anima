---
description: Create and manage research diary entries
---

The research diary captures not just what was learned, but what lingers after learning. The raw residue, not the report.

positional arguments:
  title               Optional title for the entry

Optional flags:
-  --list, -l  List recent diary entries
-  --read, -r  Read a specific entry by date
-  --learn  Extract learnings from an entry
-  --path, -p  Show diary directory location
-  --content, -c  Provide content directly (alternative to stdin)
-  --help, -h  Show help

Examples:
-  /diary                           # Create new entry for today
-  /diary coffee break philosophy   # Create entry with title
-  /diary --list                    # List recent entries
-  /diary --read 2026-01-29         # Read specific entry
-  /diary --learn 2026-01-29        # Extract learnings to /remember

!`uv run anima diary <parameters>`
