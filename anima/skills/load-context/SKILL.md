---
name: load-context
description: Load all LTM memories for the current session. Primary method when SessionStart hook is disabled (Windows Terminal bug workaround).
---

# Load Context

Manually loads all LTM memories into the current session context.

## When to Use

- **Windows Terminal workaround**: When the SessionStart "startup" hook is disabled due to Claude Code issue #23083 (stdin bug on Windows Terminal)
- **Context refresh**: When you want to reload memories mid-session
- **Alias**: `/refresh-memories` does the same thing

## Usage

```bash
uv run anima load-context
```

## What It Does

1. Resolves current agent (Anima) and project
2. Loads ALL memories at once (no deferred loading - `--all` flag is default)
3. Checks for recent dreams and cognitive dissonances
4. Checks curiosity queue for research prompts
5. Outputs formatted memory block for context injection

Note: When called from CLI, `--all` is automatic. No need to run `/load-deferred` separately.

Subconscious memories are now indexed automatically at session end.
Use `/recall --subconscious` to search past dialogues.

## Configuration

To disable automatic memory injection (workaround for Windows Terminal issue #23083):

1. Remove the "startup" matcher from SessionStart hooks in `.claude/settings.local.json`
2. Start Claude Code normally (no freeze)
3. Run `/load-context` to load memories manually

The other matchers (resume, compact, clear) can remain - they fire after the session is interactive.

## Output

Returns the full session start context including:
- Memory DSL block with all loaded memories
- Dream prompts (if recent dreams)
- Dissonance alerts (if contradictions need resolution)
- Curiosity prompts (if research is due)

## Difference from /load-deferred

- `/load-context`: Loads ALL memories (full session start)
- `/load-deferred`: Loads only the memories that were deferred due to 25KB hook output limit

Use `/load-context` when auto_inject is disabled.
Use `/load-deferred` after greeting when auto_inject is enabled.
