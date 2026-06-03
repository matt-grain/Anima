# Retrieval — How Anima Finds Memories

Anima has **two independent retrieval systems**, each tuned to a different kind
of data:

| System | Data | Method | Used for |
|---|---|---|---|
| **Dense (RAG)** | Compacted **memories** (`~/.anima/memories.db`) | Embedding cosine similarity | `/recall`, auto-linking, "do I know X?" |
| **BM25** | Raw **dialogue turns** (`~/.anima/subconscious.db`) | FTS5 BM25 + recency | `/recall --subconscious`, "what did we *say* about X?" |

They are separate on purpose: memories are distilled, semantic, and few;
dialogue is verbatim, lexical, and voluminous. Dense search excels at meaning
("find memories *about* caching"); BM25 excels at exact words and phrases
("find where we literally said `OPENBLAS_NUM_THREADS`").

---

## 1. Dense retrieval (memories)

### The embedding model
- **`BAAI/bge-small-en-v1.5`** via FastEmbed / ONNX Runtime (CPU).
- **384-dimensional** vectors (`anima/embeddings/embedder.py`).
- Stored per memory as a packed binary blob in `memories.embedding`
  (`struct.pack("{n}f", *vec)`, `anima/storage/sqlite.py:save_embedding`).

### The search path (`anima/commands/recall.py:semantic_search`)
```
query text
  → embed_text(query)                      # 384-dim query vector
  → get_memories_with_embeddings(...)      # load candidate (id, content, vec)
  → find_similar(query_vec, candidates, top_k, threshold=0.3)
  → results ranked by cosine, highest first
```

`find_similar` (`anima/embeddings/similarity.py`) computes **cosine similarity**

```
cos(a, b) = (a · b) / (‖a‖ · ‖b‖)      # range [-1, 1], 1 = identical
```

against every candidate, keeps those `≥ threshold` (0.3 for recall), and
returns the top-k sorted descending. The `🎯 NN%` you see in `/recall` output
is `score * 100`.

### Characteristics & limits
- **Exact, brute-force** cosine over all candidate embeddings — a pure-Python
  O(N) scan (`get_memories_with_embeddings` loads them all). At a few thousand
  memories this is ~tens of ms; it is the scaling ceiling, not vector quality.
- Candidates are pre-filtered by **region/project** before scoring, so a recall
  in project X doesn't pay for unrelated project memories.
- **Keyword fallback:** `store.search_memories` (`sqlite.py:736`) does a SQL
  `LIKE` match for when you want a literal substring rather than meaning.

---

## 2. BM25 retrieval (subconscious / dialogue)

The **subconscious** is an FTS5-indexed store of raw conversation turns
(`anima/storage/subconscious.py`). It answers temporal/lexical questions like
"what did we discuss last Tuesday?" that distilled memories can't.

### Ranking — BM25 blended with recency
SQLite's FTS5 provides `bm25(messages)` (Okapi BM25; **more negative = better
match**). Anima blends that with a recency boost so a slightly-weaker but recent
turn can outrank an older exact match:

```python
recency_boost = exp(-0.693 * age_days / 30)      # 30-day half-life
blended       = bm25_rank * (1 - 0.2 * recency_boost)   # 80% relevance / 20% recency
```
(`_calculate_blended_score`, subconscious.py:242)

### The search path
```
FTS5 MATCH query (supports AND / OR / "phrases")
  → ORDER BY bm25_rank LIMIT k*3        # over-fetch
  → re-score each row with blended score
  → sort ascending (lower = better), return top k
```
Optional filters: `project` and `days` (recency window). A malformed FTS5 query
(e.g. unbalanced quotes) returns empty rather than raising.

---

## Which one runs?
- `/recall <query>` → **dense** memory search (semantic).
- `/recall --subconscious <query>` → **BM25** dialogue search.
- Saving a memory (`remember`) → **dense** similarity to auto-link (see
  [MEMORY_GRAPH.md](MEMORY_GRAPH.md)).

## Source map
- `anima/embeddings/embedder.py` — model + embedding generation
- `anima/embeddings/similarity.py` — `cosine_similarity`, `find_similar`
- `anima/commands/recall.py` — `semantic_search` + the recall CLI
- `anima/storage/sqlite.py` — `get_memories_with_embeddings`, `search_memories`, `save_embedding`
- `anima/storage/subconscious.py` — FTS5 BM25 + recency blend
