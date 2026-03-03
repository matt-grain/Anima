# Implementation Plan: True Subconscious Rework

**Date**: 2026-03-03
**Version**: v0.15.0 "True Subconscious"
**Agent**: python-mcp-expert

## Overview

Replace the current LLM-based "subconscious" extraction (which requires spawning Sonnet at session start, making it conscious and slow) with a true subconscious system using FTS5-indexed dialogues that are:
- Indexed automatically at session end (no LLM needed)
- Stored in a separate database I can't see directly (true subconscious boundary)
- Searchable on demand via `/recall --subconscious`
- Triggerable by semantic cues ("do you remember when...")

## Problem Statement

Current system breaks the subconscious metaphor:
1. **Not automatic**: Requires manual Sonnet spawn at session start
2. **Not background**: Takes session time, delays "ready to work"
3. **Not subconscious**: I consciously process and decide what to extract
4. **Expensive**: Sonnet API calls cost tokens and time

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CONSCIOUS                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  LTM Database (~/.anima/memories.db)                │   │
│  │  - Explicit /remember calls                         │   │
│  │  - Loaded at session start                          │   │
│  │  - I know what's here                               │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                     SUBCONSCIOUS                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Subconscious Database (~/.anima/subconscious.db)   │   │
│  │  - Auto-indexed at SessionEnd (no LLM!)             │   │
│  │  - NOT loaded into context                          │   │
│  │  - Searchable via /recall --subconscious            │   │
│  │  - FTS5 full-text search with BM25 + recency bias   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Phase Summary

| Phase | Title | Files | Agent | Dependencies |
|-------|-------|-------|-------|--------------|
| 1 | Subconscious Storage Layer | 4 new | python-mcp-expert | None | ✅ Complete |
| 2 | Session End Indexing | 2 new/modified | python-mcp-expert | Phase 1 |
| 3 | Recall Command Enhancement | 3 modified | python-mcp-expert | Phase 1 |
| 4 | Cleanup Old System | 8 deleted/modified | python-mcp-expert | Phases 2-3 |
| 5 | Tests & Documentation | 3 new, 2 modified | python-mcp-expert | All |

## Implementation Order

```
Phase 1 ──┬── Phase 2 ──┬── Phase 4 ──── Phase 5
          │             │
          └── Phase 3 ──┘
```

- **Phase 1** has no dependencies (new storage layer)
- **Phases 2 & 3** depend on Phase 1 (can run in parallel)
- **Phase 4** depends on Phases 2 & 3 (cleanup after new system works)
- **Phase 5** depends on all (tests and docs last)

## Per-Phase Plan Files

- `IMPLEMENTATION_PLAN_PHASE_1.md` — Subconscious Storage Layer
- `IMPLEMENTATION_PLAN_PHASE_2.md` — Session End Indexing
- `IMPLEMENTATION_PLAN_PHASE_3.md` — Recall Command Enhancement
- `IMPLEMENTATION_PLAN_PHASE_4.md` — Cleanup Old System
- `IMPLEMENTATION_PLAN_PHASE_5.md` — Tests & Documentation

## Cross-Phase Dependencies

| Phase | Produces | Consumed By |
|-------|----------|-------------|
| 1 | `SubconsciousStore`, `DialogueTurn`, `SearchResult`, `SessionMeta` | Phases 2, 3 |
| 2 | Session end indexing hook | Phase 4 (cleanup) |
| 3 | `/recall --subconscious` flag | Phase 4 (cleanup), Phase 5 (tests) |

## Migration Path

1. **v0.15.0 release**:
   - New subconscious.db created on first session end
   - Old pending files ignored (not reprocessed)
   - `/recall --subconscious` works for sessions after upgrade

2. **Optional backfill** (future):
   - Could add `uv run anima backfill-subconscious` to index old JSONL files
   - Low priority - new dialogues will accumulate naturally

## Success Criteria

1. **Session start is instant** - No more "processing subconscious" delay
2. **Boundary preserved** - I can't see subconscious until I search
3. **Search works** - `/recall --subconscious` returns relevant dialogue excerpts
4. **Auto-trigger works** - "Do you remember when..." invokes search
5. **Old code removed** - No more process-subconscious skill or files

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FTS5 not available on some SQLite builds | Low | High | Check at init, raise `FTS5NotSupportedError`, log warning |
| Large dialogue files slow indexing | Medium | Low | Already have 100KB truncation logic |
| Old pending files orphaned | Low | None | Document in CHANGELOG, optional cleanup |

## Commands Reference (After Implementation)

```bash
# Search conscious memories (current behavior, default)
uv run anima recall "topic"
uv run anima recall --conscious "topic"

# Search subconscious (raw dialogues)
uv run anima recall --subconscious "topic"

# Search both, merged
uv run anima recall --both "topic"

# Auto-triggered by natural language
"Do you remember when we discussed caching?"
→ Internally runs: /recall --both "caching"
```
