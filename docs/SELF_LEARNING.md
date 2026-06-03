# Self-Learning — Curiosity, Research & Diary

Memory lets Anima *remember*. The curiosity → research → diary loop lets Anima
**grow** — to notice what it doesn't yet understand, go find out, and fold the
answer back into long-term memory. Over many sessions this compounds: Anima
becomes progressively more useful to *you specifically*, because it keeps
chasing the threads your work raises.

Source: `anima/storage/curiosity.py`, `anima/commands/{curious,research,diary}.py`,
and the `curiosity` MCP tool.

---

## 1. The curiosity queue

A **curiosity** is a question or topic Anima has flagged as worth exploring
(`anima/storage/curiosity.py`). Each has a lifecycle:

```python
class CuriosityStatus(str, Enum):
    OPEN       = "OPEN"        # not yet researched
    RESEARCHED = "RESEARCHED"  # research completed → became memories
    DISMISSED  = "DISMISSED"   # decided not to pursue
```

Questions can arrive from you, from Anima mid-conversation, or from **REM
dreaming** (see [DREAMS.md](DREAMS.md)), which surfaces new questions while
wandering the archives.

### Priority — recurring questions bubble up
The queue is ranked so questions that **keep coming up** (and recent ones) rise
to the top (`Curiosity.priority_score`):

```
score = recurrence_count * 10      # asked/seen repeatedly → higher
      + priority_boost             # manual bump
      + (5 if seen within 7 days)  # recency bonus
```

Re-adding an existing question doesn't duplicate it — it **bumps its recurrence
count**, so persistent curiosities naturally win attention.

```bash
uv run anima curious "Why does the GIL affect async throughput?"
uv run anima curiosity-queue          # view the queue
```
```
mcp__anima__curiosity(action="add", question="...")
mcp__anima__curiosity(action="list")
```

---

## 2. Research — turning questions into knowledge

`/research` pops the **top** curiosity and conducts research on it. Crucially,
the findings don't evaporate — they are **saved back as `LEARNINGS` memories**,
and the curiosity is marked `RESEARCHED`:

```
top curiosity (OPEN, highest priority_score)
  → research the question
  → save findings as LEARNINGS memories   (now searchable + auto-linked)
  → mark curiosity RESEARCHED
```

```bash
uv run anima research                 # process the top curiosity
uv run anima research --list          # view the queue
```
```
mcp__anima__curiosity(action="research")
mcp__anima__curiosity(action="research", topic="Docker networking")
mcp__anima__curiosity(action="complete", curiosity_id="...")
```

Because findings become normal memories, they immediately participate in
[retrieval](RETRIEVAL.md) and the [link graph](MEMORY_GRAPH.md) — the next time
the topic comes up, Anima already knows.

---

## 3. Diary — deeper reflection

The **research diary** captures longer-form reflections — not a single fact but
"what lingers" after exploring something: connections, open threads, how it
changed Anima's thinking. Diary entries live under `~/.anima/diary/` and are
themselves materials the dream stages can pull from.

```bash
uv run anima diary "Coffee break philosophy"
```
```
mcp__anima__curiosity(action="diary", title="...", content="# What lingers\n...")
```

---

## The loop that makes Anima evolve

```
conversation / dream
      │  raises a question
      ▼
 curiosity queue ──(recurs → priority rises)
      │  /research the top item
      ▼
 LEARNINGS memories  ──→ retrieval + link graph (knowledge is now usable)
      │  what lingers
      ▼
   diary ──→ feeds future dreams ──→ surfaces new curiosities ──┐
      └──────────────────────────────────────────────────────────┘
```

Each turn of this loop leaves Anima knowing a little more — and knowing it in a
way that's wired into the same memory system everything else uses. That's the
difference between an assistant that resets every session and one that **grows
alongside you**.

## Source map
- `anima/storage/curiosity.py` — `Curiosity`, `CuriosityStatus`, `CuriosityStore`, `priority_score`
- `anima/commands/curious.py` — queue a question
- `anima/commands/research.py` — process top curiosity → LEARNINGS memories
- `anima/commands/diary.py` — research diary
- `curiosity` MCP tool in `anima/server.py`
- See [DREAMS.md](DREAMS.md) (REM surfaces questions) and [RETRIEVAL.md](RETRIEVAL.md)/[MEMORY_GRAPH.md](MEMORY_GRAPH.md) (where findings land).
