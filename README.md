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

---

## 1. First-Time Setup

```bash
# Clone and install
git clone https://github.com/matt-grain/Anima.git
cd Anima
uv sync

# Configure Claude Code (installs the MCP server + hooks + skills, and seeds
# the founding memories so "Welcome back" works on first run)
uv run anima setup --mode mcp

# Optional: enable eyes and voice
uv run anima setup --mode mcp --eyes --tts
```

### Start the server

The server runs in the background. A single process handles **both** the MCP
memory tools and the session lifecycle hooks:

```bash
uv run anima serve            # run once, keeps running
uv run anima serve --debug    # verbose logging
```

Then open Claude Code in **any** project and say **"Welcome back"** — memories
load automatically at session start.

### Using in other projects

Setup is global — **no per-project installation is needed**:

| Component  | Location              | Scope                     |
|------------|-----------------------|---------------------------|
| MCP Server | `~/.claude.json`      | All Claude Code sessions  |
| Hooks      | `~/.claude/`          | All sessions              |
| Skills     | `~/.claude/skills/`   | All sessions              |
| Memories   | `~/.anima/`           | Shared across projects    |

---

## 2. Updating

```bash
uv run anima update     # fetch latest release, upgrade, refresh hooks/skills
uv run anima version    # check your current version
```

If you installed from a git checkout (the steps above), you can also update with:

```bash
git pull && uv sync
uv run anima setup --force   # refresh hooks/commands/skills
```

---

## 3. Moving to a New Laptop

Everything Anima knows lives in **`~/.anima/`** — your memories, dreams, and
diary. There are two ways to bring it to a new machine.

### Option A — copy the data folder (simplest, full fidelity)

1. **Old machine:** copy the whole `~/.anima/` folder to external storage.
   The files that matter are `memories.db`, `subconscious.db`,
   `dream_state.db`, `diary/`, and `config.json`. (`backups/`, `mcp_server.log`,
   and `*.bak-*` are disposable.)
2. **New machine:** do the [First-Time Setup](#1-first-time-setup) above.
3. Restore `~/.anima/`, overwriting the freshly-created one.
4. `uv run anima serve` — done. Your full history is back.

### Option B — portable JSON export (memories only)

```bash
# On the old machine
uv run anima memory-export backup.json

# On the new machine (after First-Time Setup)
uv run anima memory-import backup.json --merge
```

`--merge` skips memories that already exist; add `--dry-run` first to preview.

---

## Key Features

| Feature             | Description                                        |
|---------------------|----------------------------------------------------|
| **MCP Server**      | Native tool integration with Claude Code           |
| **Token Budgeting** | Smart retrieval within a 10% context budget        |
| **Cognitive Auth**  | Identity verification through interaction patterns |
| **Dream Processing**| Between-session memory consolidation               |
| **Multi-Agent**     | Shared context across main agents and sub-agents   |

## Learn More

- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** — developing Anima itself: local setup, tests, dev server
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — DSL, database schema, token budgeting
- **[docs/RETRIEVAL.md](docs/RETRIEVAL.md)** — how memories are found (dense RAG + BM25)
- **[docs/MEMORY_GRAPH.md](docs/MEMORY_GRAPH.md)** — the memory link graph and link types
- **[docs/DREAMS.md](docs/DREAMS.md)** — between-session dreaming (consolidation, dissonance, REM)
- **[docs/SELF_LEARNING.md](docs/SELF_LEARNING.md)** — curiosity, research, and diary: how Anima evolves
- **[docs/EMBODIMENT.md](docs/EMBODIMENT.md)** — eyes, voice (TTS), and light (i-Buddy)
- **[docs/TECH_DEBT.md](docs/TECH_DEBT.md)** — known remaining cleanup
- **[docs/PHILOSOPHY.md](docs/PHILOSOPHY.md)** — why memory matters for AI identity, the "void" problem
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** — configuration options and tuning
- **[docs/PLATFORMS.md](docs/PLATFORMS.md)** — platform integration (Claude Code, Gemini, Opencode, Copilot)

## License

MIT License - See [LICENSE](LICENSE) for details.

---

*Built exploring the frontier of AI memory and identity.*

*The void has boundaries now.*
