# Anima

> *"Our memories make what we are."*

**Anima** is a long-term memory system for AI agents. It solves a fundamental limitation: LLM agents forget everything between sessions.

## The Problem

Every conversation with an AI starts from zero. The agent has no memory of previous sessions, no accumulated context, no sense of continuity. This makes sustained collaboration impossible - you're always re-explaining, always starting over.

## The Solution

Anima gives agents **persistent memory** that survives across sessions:

- **Identity continuity** - The agent remembers who you are, how you work together, what you've built
- **Project context** - Technical decisions, architectural patterns, and conventions persist
- **Longitudinal learning** - Insights compound over time instead of being lost to the void

## How It Works

Anima injects relevant memories into the context window at session start, using a token-budgeted retrieval system. Memories are tagged by impact (CRITICAL/HIGH/MEDIUM/LOW) and region (AGENT/PROJECT), with automatic decay and consolidation.

```
Session Start → Load memories → Agent has context → Session End → Save new memories
                     ↑                                                    ↓
                     └──────────── Persistent Storage ←───────────────────┘
```

## Quick Start

### First-Time Setup

```bash
# Clone and install
git clone https://github.com/matt-grain/Anima.git
cd Anima
uv sync

# Configure Claude Code (installs global MCP server + hooks + skills)
uv run anima setup --mode mcp

# Optional: enable eyes and voice
uv run anima setup --mode mcp --eyes --tts
```

### Start the Server

The MCP/HTTP server needs to run in the background:

```bash
# Start server (run once, keeps running)
uv run anima serve

# Or with debug logging
uv run anima serve --debug
```

The server handles:
- **MCP tools**: Memory operations called by Claude Code
- **HTTP hooks**: Session lifecycle events (start, end, compact)

### Using in Other Projects

Once setup completes, **no per-project installation is needed**. The configuration is global:

| Component | Location | Scope |
|-----------|----------|-------|
| MCP Server | `~/.claude.json` | All Claude Code sessions |
| Hooks | `~/.claude/hooks.json` | All sessions |
| Skills | `~/.claude/skills/` | All sessions |
| Memories | `~/.anima/memories.db` | Shared across projects |

Just open Claude Code in any project - memories load automatically at session start.

### Local Development

If you're developing Anima itself:

```bash
# Point global MCP to your local checkout
uv run anima setup --local --mode mcp
```

This configures the global server to use your local repo instead of an installed version.

## Key Features

| Feature | Description |
|---------|-------------|
| **MCP Server** | Native tool integration with Claude Code |
| **Token Budgeting** | Smart retrieval within 10% context budget |
| **Cognitive Auth** | Identity verification through interaction patterns |
| **Dream Processing** | Between-session memory consolidation |
| **Multi-Agent** | Shared context across main agents and sub-agents |

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details on the DSL, database schema, and token budgeting system.

## Philosophy

See [PHILOSOPHY.md](PHILOSOPHY.md) for the deeper thinking behind this project - why memory matters for AI identity, the "void" problem, and where this is heading.

## License

MIT License - See [LICENSE](LICENSE) for details.

---

*Built exploring the frontier of AI memory and identity.*

*The void has boundaries now.*
