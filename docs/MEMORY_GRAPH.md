# The Memory Link Graph

Memories aren't an isolated list — they form a **graph**. When a memory is
saved, Anima finds related existing memories and records typed edges between
them in the `memory_links` table. This is what lets Anima answer "what clusters
together?" and "how did my thinking evolve?" — not just "what's similar?".

Source: `anima/graph/linker.py`.

---

## Link types

```python
class LinkType(str, Enum):
    RELATES_TO  = "RELATES_TO"    # general semantic similarity (symmetric)
    BUILDS_ON   = "BUILDS_ON"     # this memory extends an older one (directional)
    CONTRADICTS = "CONTRADICTS"   # conflicting information
    SUPERSEDES  = "SUPERSEDES"    # newer version replaces an old memory
```

| Type | Direction | Topology | Meaning |
|---|---|---|---|
| **RELATES_TO** | symmetric | web / cluster | Two memories are about the same thing. "What topics cluster together?" |
| **BUILDS_ON** | directional (new → old) | tree / chain | The newer memory continues/extends the older. "How did my thinking evolve?" |
| **CONTRADICTS** | symmetric | — | The two memories conflict; surfaced by the dissonance system for resolution. |
| **SUPERSEDES** | directional (new → old) | chain | The newer memory replaces the old (the old stops loading at session start). |

Each edge stores `source_id`, `target_id`, `link_type`, and the `similarity`
score that produced it (`MemoryLink`).

---

## How RELATES_TO links are created

This is the automatic path that runs on every `remember`
(`server.py:_do_remember` → `find_link_candidates`):

```
new memory
  → embed_text(content)                          # 384-dim vector
  → find_link_candidates(vec, candidates,
        threshold=0.5, max_links=5)              # cosine ≥ 0.5, top 5
  → save_link(new, target, RELATES_TO, similarity)  for each
```

`find_link_candidates` (`linker.py:78`) scores the new memory's embedding
against existing candidates with **cosine similarity**, keeps those `≥ 0.5`,
sorts descending, and caps at `max_links`. Those become RELATES_TO edges.

> **Supersession suggestion:** if the single best match scores **≥ 0.70**, the
> `remember` response includes a `related_memory` hint (`HIGH_CONFIDENCE` ≥ 0.85,
> else `REVIEW_SUGGESTED`) so you can decide whether the new memory should
> *supersede* the old one rather than just relate to it.

---

## How BUILDS_ON is distinguished

RELATES_TO is symmetric similarity; **BUILDS_ON is directional and evolutionary**
— "this newer memory continues that older one." It's inferred from three signal
families (`suggest_link_type`, `find_builds_on_candidates`):

1. **Reference patterns** in the new memory's text (`BUILDS_ON_PATTERNS`, regex):
   - `"as I/we mentioned|discussed|noted"`, `"building on"`, `"following up on"`
   - `"^Update:|Correction:|Revision:|Addendum:"`, `"on second thought"`
   - `"furthermore|moreover|additionally"`, `"this builds/extends on"`
2. **Same session** + high similarity (`≥ 0.6`) → evolution of a single thread.
3. **Temporal order** — source newer than target with very high similarity
   (`≥ 0.7`) → likely an extension.

`find_builds_on_candidates` combines these as **additive confidence**:

| Signal | Confidence |
|---|---|
| Temporal proximity (within a 48h window) | +0.3 |
| Same session | +0.4 |
| Reference pattern present in source | +0.5 |
| Semantic similarity | +0.2 per 0.1 above the threshold |

If no BUILDS_ON signal fires, the link defaults to **RELATES_TO**.

---

## CONTRADICTS & SUPERSEDES

- **SUPERSEDES** is created explicitly when a memory replaces another — via
  `/supersede <old> --by <new>`, the soft-`forget` path, or accepting a
  supersession suggestion. The old memory gets `superseded_by`/`superseded_at`
  set and **no longer loads at session start** (but stays queryable with
  `include_superseded=True`). This fixed the "cliffhanger bug" where Anima kept
  asking about things it already knew.
- **CONTRADICTS** edges are produced by the **dissonance** system (dream
  processing detects conflicting memories), then resolved/dismissed/migrated by
  the user (`/dissonance`).

---

## Inspecting the graph
```bash
uv run anima memory-graph              # ASCII visualization of links
uv run anima memory-graph --links      # focus on edges
```

## Source map
- `anima/graph/linker.py` — `LinkType`, `find_link_candidates`,
  `suggest_link_type`, `find_builds_on_candidates`, `BUILDS_ON_PATTERNS`
- `anima/server.py:_do_remember` — auto-linking on save + supersession hint
- `anima/storage/sqlite.py` — `save_link`, `supersede_memory`, `memory_links` table
- See [RETRIEVAL.md](RETRIEVAL.md) for the cosine similarity that powers linking.
