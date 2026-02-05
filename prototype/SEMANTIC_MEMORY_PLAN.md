# Semantic Memory Layer - Phases 2+3+4 Integration Plan

> "From impossible to possible" - The prototype proved it works.

## Overview

Merging three phases into one cohesive **Semantic Memory Layer**:
- **Phase 2**: Tiered Memory Loading (Core/Active/Contextual/Deep)
- **Phase 3**: Embeddings (semantic retrieval via FastEmbed)
- **Phase 4**: Memory Knowledge Graph (links between memories)

**Why merge?** They're deeply interlinked:
1. Embeddings power BOTH contextual retrieval AND auto-linking
2. Graph links inform tiered loading (load memory + its connections)
3. One schema migration instead of three

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SESSION START                               │
├─────────────────────────────────────────────────────────────────┤
│  ☕ "Anima is waking up..."                                      │
│  1. Pre-warm FastEmbed model (~9s, cached after first load)     │
│  2. Load Tier 1 (CORE): CRITICAL emotional/identity memories    │
│  3. Load Tier 2 (ACTIVE): HIGH impact + recent memories         │
│  4. Pre-compute embeddings for loaded memories (if missing)     │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT ACTIVATION                            │
│              (Future: hook or explicit /activate)                │
├─────────────────────────────────────────────────────────────────┤
│  When conversation context triggers retrieval:                   │
│  1. Embed the query/context                                     │
│  2. Semantic search → top-k from Tier 3 (CONTEXTUAL)            │
│  3. Traverse graph links → pull related memories                │
│  4. Inject relevant memories into context                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      /remember (enhanced)                        │
├─────────────────────────────────────────────────────────────────┤
│  On saving a new memory:                                        │
│  1. Generate embedding via FastEmbed                            │
│  2. Find similar existing memories (cosine similarity)          │
│  3. Auto-create graph links (RELATES_TO if sim > threshold)     │
│  4. Store memory + embedding + links                            │
│  5. Show discovered connections to user                         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      /recall (enhanced)                          │
├─────────────────────────────────────────────────────────────────┤
│  Search now uses semantic similarity:                           │
│  1. Embed the query                                             │
│  2. Find top-k by cosine similarity (not just keyword match)    │
│  3. Optionally show graph connections                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Schema Changes

### Migration: Add Embeddings + Graph

```sql
-- 1. Add embedding column to memories
ALTER TABLE memories ADD COLUMN embedding BLOB;

-- 2. Add tier column for tiered loading
ALTER TABLE memories ADD COLUMN tier TEXT DEFAULT 'CONTEXTUAL';

-- 3. Create links table for knowledge graph
CREATE TABLE IF NOT EXISTS memory_links (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    link_type TEXT NOT NULL,  -- RELATES_TO, BUILDS_ON, CONTRADICTS, SUPERSEDES
    similarity REAL,          -- Cosine similarity when auto-linked
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_id, target_id),
    FOREIGN KEY (source_id) REFERENCES memories(id),
    FOREIGN KEY (target_id) REFERENCES memories(id)
);

-- 4. Index for fast similarity lookups
CREATE INDEX IF NOT EXISTS idx_memory_links_source ON memory_links(source_id);
CREATE INDEX IF NOT EXISTS idx_memory_links_target ON memory_links(target_id);
CREATE INDEX IF NOT EXISTS idx_memories_tier ON memories(tier);
```

---

## Tier Assignment Logic

| Tier | Criteria | Loaded When | Token Budget |
|------|----------|-------------|--------------|
| **CORE** | CRITICAL impact OR (EMOTIONAL + HIGH+) | Always | 5% |
| **ACTIVE** | HIGH impact + created < 7 days | Always | 3% |
| **CONTEXTUAL** | MEDIUM+ impact | On semantic match | 2% (dynamic) |
| **DEEP** | LOW impact OR old | Only via /recall | 0% |

### Tier Assignment Algorithm

```python
def assign_tier(memory: Memory) -> str:
    # CORE: Identity and emotional foundation
    if memory.impact == "CRITICAL":
        return "CORE"
    if memory.kind == "EMOTIONAL" and memory.impact in ("HIGH", "CRITICAL"):
        return "CORE"

    # ACTIVE: Recent important memories
    days_old = (now() - memory.created_at).days
    if memory.impact == "HIGH" and days_old <= 7:
        return "ACTIVE"

    # DEEP: Old or low-impact
    if memory.impact == "LOW":
        return "DEEP"
    if days_old > 30 and memory.impact == "MEDIUM":
        return "DEEP"

    # Default: CONTEXTUAL
    return "CONTEXTUAL"
```

---

## Link Types

| Type | Meaning | Auto-detected? |
|------|---------|----------------|
| `RELATES_TO` | General semantic similarity | Yes (sim > 0.5) |
| `BUILDS_ON` | This memory extends another | Manual or heuristic |
| `CONTRADICTS` | Conflicting information | Future: detect |
| `SUPERSEDES` | Newer version of old memory | Existing logic |

---

## New Module Structure

```
anima/
├── embeddings/           # NEW
│   ├── __init__.py
│   ├── embedder.py       # FastEmbed wrapper, lazy loading, caching
│   └── similarity.py     # Cosine similarity, top-k search
│
├── graph/                # NEW
│   ├── __init__.py
│   ├── linker.py         # Auto-linking on /remember
│   └── traverser.py      # Graph traversal for related memories
│
├── storage/
│   ├── sqlite.py         # MODIFY: Add embedding + link storage
│   └── migrations.py     # MODIFY: Add migration for new schema
│
├── lifecycle/
│   └── injection.py      # MODIFY: Tiered loading logic
│
├── hooks/
│   └── session_start.py  # MODIFY: Pre-warm embedder, tiered injection
│
└── commands/
    ├── remember.py       # MODIFY: Embed + auto-link on save
    └── recall.py         # MODIFY: Semantic search
```

---

## Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "tiktoken>=0.8.0",
    "fastembed>=0.4.0",  # NEW - ONNX-based, CPU-optimized
]
```

**Why FastEmbed?**
- 14x faster than sentence-transformers on CPU
- No PyTorch dependency (ONNX Runtime)
- Quantized models, small footprint
- Proven in prototype: 9s load, 7ms search

---

## Implementation Tasks

### Phase A: Foundation (Schema + Embeddings Module)

1. **Schema Migration**
   - Add `embedding` BLOB column to memories
   - Add `tier` TEXT column to memories
   - Create `memory_links` table
   - Add indexes

2. **Embeddings Module**
   - `embedder.py`: FastEmbed wrapper with lazy loading
   - `similarity.py`: Cosine similarity, batch operations
   - "Waking up" message during model load

3. **Storage Layer Updates**
   - Add embedding storage/retrieval to MemoryStore
   - Add link storage/retrieval methods

### Phase B: Integration (Commands + Hooks)

4. **Update /remember**
   - Generate embedding on save
   - Find similar memories (auto-link candidates)
   - Create RELATES_TO links for sim > threshold
   - Show discovered connections

5. **Update /recall**
   - Semantic search using embeddings
   - Fall back to keyword if no embeddings
   - Show similarity scores

6. **Update SessionStart Hook**
   - Pre-warm FastEmbed model
   - Implement tiered loading (CORE + ACTIVE only)
   - Generate embeddings for memories missing them

### Phase C: Graph + Polish

7. **Graph Module**
   - `linker.py`: Auto-linking logic with thresholds
   - `traverser.py`: Get related memories via links

8. **Backfill Existing Memories**
   - Migration script to embed all existing memories
   - Assign tiers based on criteria
   - Auto-link based on similarity

9. **Tests**
   - Unit tests for embeddings module
   - Unit tests for graph module
   - Integration tests for tiered loading
   - Test semantic search quality

10. **Documentation**
    - Update SKILL.md with new behavior
    - Update LTM_EVOLUTION_PLAN.md

---

## Success Criteria

- [ ] Model loads in <15s with "waking up" message
- [ ] Semantic search finds relevant memories (quality matches prototype)
- [ ] Auto-linking discovers meaningful connections
- [ ] Tiered loading reduces initial context injection
- [ ] /recall uses semantic search by default
- [ ] All existing tests still pass
- [ ] New tests cover embedding + graph functionality

---

## Rollout Strategy

1. **v0.8.0-alpha**: Schema migration + embeddings module (no behavior change)
2. **v0.8.0-beta**: /remember embeds, /recall searches semantically
3. **v0.8.0**: Full tiered loading + graph links
4. **v0.8.1**: Backfill script for existing installations

---

## Open Questions

1. **Embedding storage format**: JSON blob or binary? (JSON for debugging, binary for size)
2. **Link threshold**: 0.5 for RELATES_TO? Configurable?
3. **Context activation trigger**: Hook-based? Explicit command? Future phase?
4. **Backfill strategy**: On-demand or batch migration script?

---

*Plan created 2026-01-29*
*"Curiosity opens doors. From impossible to possible."*

💜 Anima + Matt
