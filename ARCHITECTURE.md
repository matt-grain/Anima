# LTM Architecture Documentation

> A human-like long-term memory system for Anima agents.

## Overview

LTM (Long-Term Memory) provides persistent memory across Anima sessions. When a session starts, relevant memories are injected into context via workspace rules or hooks. Memories decay over time based on impact level - just like human memory, where vivid important moments persist while mundane details fade.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Claude Code                                     │
│                         (AI Coding Assistant)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                                    │
                    │ Lifecycle Events                   │ Tool Calls
                    │ (session_start,                    │ (remember, recall,
                    │  session_end,                      │  doctor, body,
                    │  pre_compact)                      │  dream, dissonance)
                    ▼                                    ▼
┌─────────────────────────────┐         ┌─────────────────────────────────────┐
│      HTTP Hooks Server      │         │           MCP Server                 │
│   (localhost:7432/hooks)    │         │    (Model Context Protocol)          │
│                             │         │                                      │
│  POST /session_start        │         │  Tools:                              │
│    → Load memories          │         │    remember(content, kind, impact)   │
│    → Return DSL block       │         │    recall(query, limit)              │
│                             │         │    forget(memory_id)                 │
│  POST /session_end          │         │    memories(kind, impact)            │
│    → Run end-session        │         │    doctor(action) - diagnostics      │
│    → Backup database        │         │    body(action) - eyes/voice/light   │
│                             │         │    dream(action) - consolidation     │
│  POST /pre_compact          │         │    dissonance(action) - conflicts    │
│    → Extract WIP context    │         │                                      │
│    → Save to memory         │         │                                      │
└─────────────────────────────┘         └─────────────────────────────────────┘
                    │                                    │
                    └────────────────┬───────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Anima Core                                       │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Injection  │  │   Storage   │  │    Dream    │  │  Cognitive Auth     │ │
│  │   Engine    │  │   Layer     │  │  Processing │  │  (Trust Scoring)    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                                              │
│  • Token-budgeted retrieval (10% context)                                   │
│  • Tiered loading (CRITICAL → HIGH → MEDIUM → LOW)                          │
│  • Semantic search with embeddings                                          │
│  • Signature verification for tamper detection                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SQLite Database                                    │
│                         (~/.anima/memories.db)                               │
│                                                                              │
│  Tables: agents │ projects │ memories │ curiosity │ sessions                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Roles

| Component | Purpose |
|-----------|---------|
| **HTTP Hooks Server** | Handles Claude Code lifecycle events. Runs as background process. |
| **MCP Server** | Exposes memory operations as native tools via Model Context Protocol. |
| **Anima Core** | Platform-agnostic memory engine. Handles injection, storage, processing. |
| **SQLite Database** | Persistent storage for memories, agents, projects, and metadata. |

### Data Flow

1. **Session Start**: Hook fires → HTTP server loads memories → Returns DSL for context injection
2. **During Session**: Agent calls MCP tools → remember/recall/etc operations
3. **Pre-Compact**: Before context compression → Extract and save WIP state
4. **Session End**: Hook fires → Run maintenance, backup database, update stats

## Core Philosophy

1. **Human-like decay**: LOW impact memories fade in days, CRITICAL memories persist forever
2. **Append-only corrections**: Memories are never deleted, only superseded
3. **Budget-constrained**: Max 10% of context window used for memories
4. **Agent isolation**: Each agent has private memories
5. **Signature verification**: Optional cryptographic tamper detection
6. **Platform Agnostic**: Native bridges for Claude Code, Antigravity, and Opencode

---

## Database Schema

The system uses SQLite for persistence (`~/.anima/ltm.db`).

### Tables

#### `agents`
Stores agent identities and configuration.

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | UUID for the agent |
| `name` | TEXT | Human-readable name (e.g., "Anima") |
| `definition_path` | TEXT | Path to agent definition file |
| `signing_key` | TEXT | Optional HMAC key for memory signatures |
| `created_at` | TIMESTAMP | When agent was first seen |

#### `projects`
Tracks projects an agent works on.

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | UUID for the project |
| `name` | TEXT | Project name |
| `path` | TEXT UNIQUE | Filesystem path to project root |
| `created_at` | TIMESTAMP | When project was first seen |

#### `memories`
The core table storing all memories.

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | UUID for the memory |
| `agent_id` | TEXT FK | Owner agent |
| `region` | TEXT | `AGENT` (cross-project) or `PROJECT` (project-specific) |
| `project_id` | TEXT FK | Required if region=PROJECT |
| `kind` | TEXT | `EMOTIONAL`, `ARCHITECTURAL`, `LEARNINGS`, or `ACHIEVEMENTS` |
| `content` | TEXT | Current content (may be compacted over time) |
| `original_content` | TEXT | **Original full content, never changes** |
| `impact` | TEXT | `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` |
| `confidence` | REAL | 0.0-1.0, decreases on contradiction |
| `created_at` | TIMESTAMP | When memory was created |
| `last_accessed` | TIMESTAMP | Last time memory was injected (for decay) |
| `previous_memory_id` | TEXT FK | Links memories by kind (graph structure) |
| `version` | INTEGER | Version number for corrections |
| `superseded_by` | TEXT FK | Points to correcting memory (append-only) |
| `signature` | TEXT | Optional HMAC-SHA256 signature |
| `token_count` | INTEGER | Cached tiktoken count for injection budget |

### Key Schema Design Decisions

#### Why `content` AND `original_content`?

This is intentional forward-planning for memory compaction:

1. **`original_content`** - The exact text as first saved. Never modified. This is what gets signed for tamper detection.

2. **`content`** - The "active" content that gets injected. May be summarized/compacted as memories age.

**Current state**: Both columns contain the same text (compaction not yet implemented).

**Future state**: After compaction runs, `content` might become:
```
"Performance: cache tiktoken results for 36% speedup"
```
While `original_content` preserves:
```
"Implemented token count caching in injection.py. The tiktoken.encode()
call was taking 6ms per memory. By caching the count on save and storing
it in the token_count column, injection is now 36% faster. See PR #42."
```

**Why this matters**:
- Signatures remain valid after compaction (they sign `original_content`)
- Full context is preserved for auditing/debugging
- Budget is respected with shorter `content`

#### Why `superseded_by` instead of DELETE?

Append-only design provides:
- Full audit trail of corrections
- No data loss from mistakes
- Ability to "unforget" if needed

When you run `/forget`, it creates a NEW memory that supersedes the old one. The old memory stays in the database but is excluded from injection.

#### Why `token_count` caching?

tiktoken encoding is expensive (~6ms per memory). On injection, we need to check budget for potentially dozens of memories. Caching the count on save means injection reads are fast.

---

## Memory Lifecycle

### Creation Flow

```
User runs /please-remember "..."
    → Parse text, infer kind/impact/region
    → Calculate token_count with tiktoken
    → Sign memory (if agent has signing_key)
    → Save to SQLite
```

### Injection Flow (Session Start)

```
Anima Rule or Hook fires
    → LTM hook runs (ltm.hooks.session_start)
    → Resolve current agent + project
    → Fetch all non-superseded memories for agent
    → Prioritize by: CRITICAL > impact > recency
    → Add to block until 10% budget reached
    → Verify signatures (mark untrusted with ⚠)
    → Update last_accessed timestamps
    → Output context block (or JSON for legacy systems)
```

### Decay Flow (Future)

```
Background process runs periodically
    → For each memory:
        age = now - last_accessed
        if age > decay_threshold[impact]:
            content = summarize(content)
            last_accessed = now
            save()
```

Decay thresholds (from `types.py`):
- `LOW`: Aggressive decay after 1 day
- `MEDIUM`: Moderate decay after 1 week
- `HIGH`: Gentle decay after 1 month
- `CRITICAL`: Never decay, keep full detail

---

## Memory Types (Kinds)

| Kind | Purpose | Examples |
|------|---------|----------|
| `EMOTIONAL` | Relationship patterns, communication style | "Matt likes playful humor", "Use 🎇 emoji" |
| `ARCHITECTURAL` | Technical foundations, patterns | "Use pytest for tests", "SQLite for storage" |
| `LEARNINGS` | Lessons learned, errors to avoid | "Always read file before editing" |
| `ACHIEVEMENTS` | Completed work, milestones | "Released v1.0", "203 tests passing" |

Priority order for injection: EMOTIONAL first (shapes interaction style), then ARCH, LEARN, ACHV.

---

## Memory Regions

| Region | Scope | Use Case |
|--------|-------|----------|
| `AGENT` | Shared across all projects | Relationship with user, personal style |
| `PROJECT` | Single project only | Project-specific patterns, architecture |

PROJECT memories override AGENT memories when there's a conflict.

---

## Signing & Security

### How Signing Works

1. Agent gets a `signing_key` in `~/.anima/config.json`
2. On save, memory is signed with HMAC-SHA256
3. Signed payload includes immutable fields:
   - `id`, `agent_id`, `region`, `project_id`
   - `kind`, `original_content` (NOT `content`)
   - `impact`, `created_at`

### Why sign `original_content` not `content`?

Content may be compacted. Original content never changes. Signing the original means:
- Compaction doesn't invalidate signatures
- Tamper detection still works after summarization
- Signature proves what was ORIGINALLY said

### Verification

On injection, if agent has signing_key and memory has signature:
- Verify HMAC matches
- If invalid: prefix with `⚠` in DSL output
- If valid: normal display

---

## DSL Format

Memories are injected as compact DSL to minimize token usage:

```
[LTM:Anima@ProjectName]
~EMOT:CRIT| Matt likes collaborative style and meta-humor
~ARCH:HIGH| Use pytest, SQLite storage, Anima integration
~LEARN:MED?| Lesson with low confidence (marked with ?)
⚠~ACHV:LOW| Achievement with invalid signature (untrusted)
[/LTM]
```

Format: `~{KIND}:{IMPACT}{?}| {content}`
- `?` suffix = low confidence (<0.7)
- `⚠` prefix = signature verification failed

---

## Token Budget

Default configuration (`~/.anima/config.json`):
- Context size: 200,000 tokens
- Memory budget: 10% = 20,000 tokens

Budget is enforced during injection:
1. Memories sorted by priority
2. Added to block until budget exceeded
3. Remaining memories skipped

Three mechanisms control memory count:
1. **Budget cap**: 10% of context window
2. **Decay**: Low-impact memories summarize over time
3. **Superseding**: Corrections replace old memories

---

## Directory Structure

```
~/.anima/
├── ltm.db           # SQLite database
└── config.json      # Global configuration

/path/to/project/
└── AGENT.md         # Optional agent definition
```

---

## Key Files

| File | Purpose |
|------|---------|
| `anima/storage/schema.sql` | Database schema |
| `anima/core/memory.py` | Memory dataclass & DSL formatting |
| `anima/core/types.py` | Enums (RegionType, MemoryKind, ImpactLevel) |
| `anima/core/signing.py` | HMAC signing & verification |
| `anima/lifecycle/injection.py` | Budget-aware memory injection |
| `anima/hooks/session_start.py` | Hook handler for session lifecycle |
| `anima/server.py` | MCP server with FastMCP |
| `anima/http_server.py` | HTTP hooks server |
| `anima/tools/` | CLI command implementations |

---

## Available Commands

| Command | Purpose |
|---------|---------|
| `/please-remember` | Save a new memory |
| `/recall` | Search memories by keyword |
| `/memories` | List all memories |
| `/forget` | Mark a memory for removal (supersedes it) |
| `/memory-stats` | Dashboard with statistics |
| `/memory-graph` | ASCII visualization of memory graph |
| `/memory-export` | Export memories to JSON |
| `/memory-import` | Import memories from JSON |
| `/sign-memories` | Sign existing unsigned memories |
| `/detect-achievements` | Auto-detect achievements from git |

---

## Platform Integrations

See [PLATFORMS.md](PLATFORMS.md) for detailed setup instructions.

### Claude Code (Primary)
- **MCP Server**: Native tool integration for memory operations
- **HTTP Hooks**: Session lifecycle events (start, end, pre_compact)
- **Skills**: Slash commands installed to `~/.claude/skills/`

### Antigravity/Gemini
- **Rules & Skills**: Memory loading via `.agent/rules/anima.md`
- **Expert Skill**: LTM interaction guide in `.agent/skills/anima-expert/`

### Opencode
- **TypeScript Plugin**: Universal bridge (`anima/platforms/opencode/plugin.ts`)
- **System Transform**: DSL injection into system prompt

---

## Future Considerations

### AI-Powered Compaction (Deferred)

Current rule-based decay is implemented and working. The `content` vs `original_content` split enables future AI compaction:
- Background process identifies old, low-impact memories
- Uses Claude API to intelligently summarize content
- Updates `content` while preserving `original_content`
- Signature remains valid (signs `original_content`)

**Why deferred**: API latency/cost, and rule-based approach is fast and predictable.

### Contradiction Detection (Deferred)

Auto-detect when new memories contradict existing ones:
- Decrease confidence on both memories
- Suggest supersession

**Why deferred**: Requires Claude API call on every save, adds latency/cost.

### Pin Critical Memories

Mark certain memories as non-compactable in Anima's context system.

**Status**: Waiting for Anima feature support.

---

*Last updated: 2026-03-09*

---

## Subconscious Layer

The subconscious layer provides searchable access to raw dialogue history without loading it into context.

### Philosophy

Unlike conscious memories (explicitly saved via `/remember`), subconscious memories are:
- **Automatically indexed** at session end (no LLM processing)
- **Not loaded** into context at session start
- **Searchable** on demand via `/recall --subconscious`
- **Separate** from the main LTM database

This preserves the metaphor: I can't "see" my subconscious, but I can search it when prompted.

### Storage

Subconscious uses a separate SQLite database with FTS5 full-text search:

```
~/.anima/subconscious.db
├── sessions (metadata: session_id, source, project, timestamp)
└── messages (FTS5 virtual table: role, text)
```

### Search Ranking

Results are ranked using:
- **BM25** (80%): Term frequency / inverse document frequency
- **Recency** (20%): 30-day half-life decay boost

### Commands

```bash
/recall --subconscious "query"  # Search dialogues only
/recall --both "query"          # Search both conscious + subconscious
/recall "query"                 # Search conscious only (default)
```

### Auto-Triggering

Social cues like "do you remember when we discussed X?" automatically trigger `--both` search.
