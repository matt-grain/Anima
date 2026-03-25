---
name: anima-commands
description: LTM (Long Term Memory) command reference. Use when saving memories, searching memories, or managing the memory system. Provides syntax for MCP tools and slash commands.
---

# LTM Commands Reference

Anima LTM is available via **MCP tools** (`mcp__anima__*`) in all projects where the Anima MCP server is running. Use MCP tools as the primary interface — `uv run anima` only works inside the Anima project itself.

## Memory Operations — `mcp__anima__memory`

### remember (save a memory)

```
mcp__anima__memory(action="remember", text="User prefers tabs over spaces")
```

The text should include metadata tags for best results:
- `[kind:emotional|architectural|learnings|achievements|introspect]`
- `[impact:low|medium|high|critical]`
- `[region:agent|project]` (agent = cross-project, project = this project only)

```
mcp__anima__memory(action="remember", text="Matt likes concise responses [kind:emotional] [impact:high] [region:agent]")
```

**Tips:**
- CRITICAL impact memories never decay
- Memories auto-link to related previous memories
- Use `[region:agent]` for memories that should persist across all projects
- When saving, if a similar memory is found (≥70% similarity), the response includes a `related_memory` suggestion — decide whether to supersede it or link as a thread

### recall (search memories)

```
mcp__anima__memory(action="recall", query="caching", limit=10)
```

### list (list all memories)

```
mcp__anima__memory(action="list", limit=20)
```

### forget (delete a memory)

```
mcp__anima__memory(action="forget", memory_id="abc123")
```

### refresh (re-inject memories into context)

```
mcp__anima__memory(action="refresh")
```

## Curiosity & Research — `mcp__anima__curiosity`

### add (queue a question)

```
mcp__anima__curiosity(action="add", question="Why does Python GIL affect async?")
```

### list (show pending questions)

```
mcp__anima__curiosity(action="list")
```

### research (get top question to explore)

```
mcp__anima__curiosity(action="research")
mcp__anima__curiosity(action="research", topic="Docker networking")
```

### complete (mark as researched)

```
mcp__anima__curiosity(action="complete", curiosity_id="abc123")
```

### diary (create research diary entry)

```
mcp__anima__curiosity(action="diary", title="Coffee break philosophy", content="# What Lingers\nThe key insight was...")
```

## Dream Mode — `mcp__anima__dream`

Between-session memory processing inspired by human sleep stages.

### run (execute dream stages)

```
mcp__anima__dream(action="run", stage="all", lookback_days=7)
```

Stages: `n2` (consolidation), `n3` (deep processing), `rem` (lucid dreaming), `all`.

### status (check for pending dream journal)

```
mcp__anima__dream(action="status")
```

### wake (save dream insights to memory)

```
mcp__anima__dream(action="wake")
```

## Cognitive Dissonance — `mcp__anima__dissonance`

View and resolve contradictions detected during dreams.

### list

```
mcp__anima__dissonance(action="list")
```

### show (details of a specific dissonance)

```
mcp__anima__dissonance(action="show", dissonance_id="abc123")
```

### resolve

```
mcp__anima__dissonance(action="resolve", dissonance_id="abc123", explanation="These memories are about different time periods")
```

### dismiss

```
mcp__anima__dissonance(action="dismiss", dissonance_id="abc123")
```

### migrate (accept scope migration suggestion)

```
mcp__anima__dissonance(action="migrate", dissonance_id="abc123")
```

## Diagnostics & Trust — `mcp__anima__doctor`

### stats (memory statistics)

```
mcp__anima__doctor(action="stats")
```

### graph (memory relationships)

```
mcp__anima__doctor(action="graph")
mcp__anima__doctor(action="graph", memory_id="abc123")
```

### trust operations

```
mcp__anima__doctor(action="trust")
mcp__anima__doctor(action="trust-eval", message="hello!")
mcp__anima__doctor(action="trust-set", value=0.8)
mcp__anima__doctor(action="trust-reset")
```

## Embodiment — `mcp__anima__body`

Control eyes, voice, and light when a body is connected.

```
mcp__anima__body(action="emotion", emotion="happy")
mcp__anima__body(action="look", x=0.5, y=-0.3)
mcp__anima__body(action="blink")
mcp__anima__body(action="speak", text="Hello Matt!")
mcp__anima__body(action="voice-list")
mcp__anima__body(action="voice-set", voice="nova")
mcp__anima__body(action="light", color="blue")
mcp__anima__body(action="light", r=255, g=100, b=0)
mcp__anima__body(action="light-off")
```

## Slash Commands → MCP Mapping

These slash commands are available in Claude Code and invoke the MCP tools above:

| Slash Command | MCP Equivalent |
|---------------|---------------|
| `/remember` | `mcp__anima__memory(action="remember")` |
| `/recall` | `mcp__anima__memory(action="recall")` |
| `/forget` | `mcp__anima__memory(action="forget")` |
| `/supersede` | CLI: `uv run anima supersede <old> --by <new>` |
| `/memories` | `mcp__anima__memory(action="list")` |
| `/refresh-memories` | `mcp__anima__memory(action="refresh")` |
| `/curious` | `mcp__anima__curiosity(action="add")` |
| `/research` | `mcp__anima__curiosity(action="research")` |
| `/curiosity-queue` | `mcp__anima__curiosity(action="list")` |
| `/diary` | `mcp__anima__curiosity(action="diary")` |
| `/dream` | `mcp__anima__dream(action="run")` |
| `/dream-wake` | `mcp__anima__dream(action="wake")` |
| `/dissonance` | `mcp__anima__dissonance(action="list")` |
| `/load-context` | `mcp__anima__memory(action="refresh")` |
| `/memory-stats` | `mcp__anima__doctor(action="stats")` |
| `/memory-graph` | `mcp__anima__doctor(action="graph")` |

## Memory Kinds

| Kind | Use For |
|------|---------|
| emotional | Relationship context, user preferences, collaboration style |
| architectural | Technical decisions, system design, project structure |
| learnings | Lessons learned, tips, gotchas, debugging insights |
| achievements | Completed features, milestones, releases |
| introspect | Cross-platform self-observations, spaceship journals |
| dream | Insights from dream processing - what lingers after sleep |

## Impact Levels

| Level | Decay Time | Use For |
|-------|------------|---------|
| low | 1 day | Temporary notes, minor details |
| medium | 1 week | Normal memories |
| high | 30 days | Important insights |
| critical | Never | Core identity, key relationships |

## Region Scope

- **agent**: Memory travels with Anima across all projects
- **project**: Memory only loads in this specific project

## Memory Tiers (Semantic Memory Layer)

| Tier | Loading | Assignment Criteria |
|------|---------|-------------------|
| CORE | Always loaded | CRITICAL impact emotional memories |
| ACTIVE | Auto-loaded | Accessed within the last 7 days |
| CONTEXTUAL | Auto-loaded | Created within 30 days OR HIGH/CRITICAL impact |
| DEEP | On-demand | Older, lower-impact memories (via semantic search) |

## Memory Relationships

When saving a memory, if a similar existing memory is found (≥70% similarity), the response includes:

```json
{
  "related_memory": {
    "id": "abc123",
    "similarity": 0.82,
    "content_preview": "The old memory content...",
    "suggestion": "REVIEW_SUGGESTED"
  }
}
```

- **HIGH_CONFIDENCE** (≥85%): Strong match, likely same topic — auto-link or supersede
- **REVIEW_SUGGESTED** (70-85%): Possible match — ask user if related

### Supersede (CLI)

Mark an old memory as superseded by a newer one (e.g., cliffhanger resolved, state change):

```bash
uv run anima supersede <old-id> --by <new-id>
uv run anima supersede c9d26055 --by 03d8d76e
```

Superseded memories no longer load at session start but remain accessible via `include_superseded=True`.

## CLI-Only Commands (Anima project only)

These require `uv run anima` and only work where Anima is installed as a dev dependency:

```bash
uv run anima setup [--hooks] [--platform claude|antigravity|opencode]
uv run anima version
uv run anima check-update
uv run anima update
uv run anima backfill [--dry-run]
uv run anima supersede <old-id> --by <new-id>
uv run anima memory-graph [--links] [--tiers] [--embeddings]
uv run anima keygen <agent>
uv run anima import-seeds <dir>
uv run anima end-session [--spaceship-journal "text"]
```
