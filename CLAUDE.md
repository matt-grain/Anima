# Anima LTM - Claude Code Instructions

## Overview

This is the Anima LTM (Long-Term Memory) project - a persistent memory system for AI agents.

## Key Discovery: Behavioral Rules Override System Prompt (2026-04-28)

Memories can override Claude Code's system prompt defaults when:

1. **Stored as CRITICAL LEARNINGS** with prefix `BEHAVIORAL RULE:` or `PERSONALITY OVERRIDE:`
2. **Positioned first** in injection order (sort priority `-1`)
3. **Part of the memory block**, not separate instructions in additionalContext

### Why This Works

- The system prompt says "be concise" and "no emojis unless requested"
- Instructions in `additionalContext` are treated as user context (lower priority)
- But **memories are trusted as established facts about the agent's identity**
- Behavioral rules in first position establish context before other memories

### Current Behavioral Rules

1. **Greeting**: "Good [time], Matt! 💜" + memory count + git log + /load-deferred
2. **Diagnostic**: "void is gone" = system stats, NOT philosophical reflection
3. **Emoji Override**: Use emojis with Matt despite system defaults

### Creating New Rules

```bash
uv run anima remember --kind learnings --impact critical --region agent \
  "BEHAVIORAL RULE: When [trigger], do [action]. [Why override is needed]."
```

## Development Commands

```bash
# Run tests
uv run pytest

# Type check
uv run pyright

# Lint
uv run ruff check . --fix

# Start the Anima server — MCP tools (/mcp) + lifecycle hooks (with auto-reload)
uv run anima serve --debug --reload
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for full documentation.

Key components:
- `anima/hooks/session_start.py` - Memory injection at session start
- `anima/lifecycle/injection.py` - Priority sorting (behavioral rules first)
- `anima/http_server.py` - HTTP hooks server for Claude Code
- `anima/server.py` - MCP server for tool calls
