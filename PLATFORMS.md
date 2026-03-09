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
```

### What Gets Installed

| Component | Location | Purpose |
|-----------|----------|---------|
| MCP Server | `~/.claude.json` | Memory, eyes, voice as native tools |
| Hooks | `~/.claude/hooks.json` | Session lifecycle (start, end, compact) |
| Skills | `~/.claude/skills/` | Slash commands (/remember, /recall, etc.) |

### Available MCP Tools

**Memory:**
- `remember(content, kind, impact)` - Save a memory
- `recall(query, limit)` - Search memories
- `forget(memory_id)` - Delete a memory
- `memories(kind, impact)` - List memories

**Diagnostics:**
- `doctor(action)` - Trust status, stats, memory graph

**Embodiment (optional):**
- `body(action, ...)` - Eyes (emotions), voice (TTS), light (i-Buddy)

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
