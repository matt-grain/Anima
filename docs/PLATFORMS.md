# Platform Integration

Anima integrates with AI coding assistants through their native extension mechanisms. This guide covers setup for each supported platform.

## Claude Code (Primary)

Claude Code is the primary development platform, using MCP (Model Context Protocol) for tool integration.

### Quick Setup

```bash
# Clone and install
git clone https://github.com/matt-grain/Anima.git
cd Anima
uv sync

# Setup MCP server + hooks
uv run anima setup --mode mcp

# Or with eyes and voice
uv run anima setup --mode mcp --eyes --tts

# Start the server (hosts MCP tools AND hooks in one process; keep it running)
uv run anima serve
```

Setup configures Claude Code to reach Anima over **streamable-HTTP** at
`http://127.0.0.1:3741/mcp`. (stdio transport hangs on Windows — the reply
never reaches the client even though the memory is written — so HTTP is the
default.) The server must be running for memory tools and hooks to work.

### What Gets Installed

| Component | Location | Purpose |
|-----------|----------|---------|
| MCP config | `~/.claude.json` | `{type: http, url: http://127.0.0.1:3741/mcp}` |
| Hooks | `~/.claude/settings.json` + `~/.claude/hooks/` | Session lifecycle (start, subagent, end, compact) |
| Skills | `~/.claude/skills/` | Slash commands (/remember, /recall, etc.) |

### Available MCP Tools

Tools are consolidated by domain — each takes an `action` argument (token-optimized):

**Memory** — `memory(action, ...)`:
- `action="remember"` (text) - Save a memory
- `action="recall"` (query, limit) - Search memories
- `action="forget"` (memory_id) - Delete a memory
- `action="list"` (limit) - List memories
- `action="refresh"` - Re-inject memories into context

**Curiosity & Research** — `curiosity(action, ...)`:
- `action="add"` / `"research"` / `"complete"` / `"diary"` / `"list"`

**Diagnostics:** `doctor(action)` - Trust status, stats, memory graph

**Embodiment (optional):** `body(action, ...)` - Eyes (emotions), voice (TTS), light (i-Buddy)

**Processing:**
- `dream(action)` - Run dream stages (N2/N3/REM)
- `dissonance(action)` - View/resolve contradictions

### Slash Commands

```
/remember <content>     Save a memory
/recall <query>         Search memories
/dream                  Run dream processing
/research               Explore curiosity queue
```

### Local Development

For developing Anima itself:

```bash
# Point global MCP to local repo
uv run anima setup --local --mode mcp
```

This configures the global MCP server to use your local Anima checkout instead of an installed version.

### Troubleshooting

**Windows Terminal stdin freeze:**
```bash
uv run anima setup --mode mcp --no-startup-hook
```
Then manually run `/load-context` at session start.

**MCP permission prompts:**
```bash
uv run anima setup --hooks
```

---

## Other Platforms

### Gemini (Antigravity)

Anima originated on Gemini/Antigravity and supports it through rules and skills:

```bash
uv run anima setup --platform antigravity
```

Installs:
- `.agent/rules/anima.md` - Memory loading instructions
- `.agent/skills/anima-expert/` - LTM interaction guide

### Opencode

Experimental TypeScript plugin bridge:

```bash
uv run anima setup --platform opencode
```

Installs plugin to `.opencode/plugins/anima/`.

### GitHub Copilot (Experimental)

Hooks-only integration (slash commands are not wired up yet):

```bash
uv run anima setup --platform copilot
```

Installs session hooks to `.github/hooks/anima.json`.

> Secondary-platform support is evolving. The authoritative list of what a
> platform installs is whatever `uv run anima setup --platform <name>` reports.

---

## Architecture

All platforms share the same core:

```
┌─────────────────────────────────────────────────┐
│                  AI Assistant                    │
│  (Claude Code / Gemini / Opencode)              │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│              Platform Adapter                    │
│  MCP Server / Rules+Skills / TS Plugin          │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│                 Anima Core                       │
│  Memory Store │ Injection │ Dream Processing    │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│               SQLite Database                    │
│  ~/.anima/memories.db                           │
└─────────────────────────────────────────────────┘
```

The platform adapter translates between the AI assistant's native mechanisms and Anima's core API. This allows the same memory system to work across different AI platforms.
