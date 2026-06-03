# Dreaming — Between-Session Memory Processing

Anima "dreams" between sessions. Inspired by human sleep, dreaming is a
multi-stage pass over recent memories that **consolidates, compresses, surfaces
contradictions, and wanders associatively** — turning a pile of raw memories
into a more coherent, self-aware whole. Without it, memory is just accumulation;
with it, memory *settles*.

Source: `anima/dream/` (`cleanup.py`, `n2_consolidation.py`, `n3_processing.py`,
`rem_dreaming.py`, `types.py`) and `anima/storage/dream_state.py`.

---

## The stages

A dream runs as a small state machine (`DreamState`), advancing through stages
in order. Each has a distinct "character":

| Stage | Character | What it does |
|---|---|---|
| **CLEANUP** | the janitor | Memory hygiene — dedup, apply decay, prune stale low-impact memories |
| **N2** | the librarian | **Consolidation** — discover new links between memories, adjust impact levels (systematic housekeeping) |
| **N3** | the editor cutting to essence | **Deep processing** — *gist extraction* (compress detailed memories to essential summaries) and *contradiction detection* |
| **REM** | the poet finding unexpected rhymes | **Divergent / lucid dreaming** — wander associatively across memories, surface new questions and self-observations, write a dream-journal entry |

```
IDLE → CLEANUP → N2 (consolidate) → N3 (compress + detect dissonance) → REM (dream) → wake
```

### N3 and dissonance
N3 is where Anima gets analytical. Beyond compressing memories into gists, it
**detects contradictions** — memories that conflict. Those become entries in the
**dissonance queue** (see CONTRADICTS in [MEMORY_GRAPH.md](MEMORY_GRAPH.md)),
which you review later with `/dissonance` (resolve / dismiss / migrate scope).
This is how Anima notices "wait, I believe two incompatible things."

### REM is *lucid*, not automated
REM is deliberately different. The code **gathers raw materials** — a quasi-random
mix of recent memories, older memories, and diary fragments
(`gather_dream_materials`) — and lays them into a **dream-journal template**
(`create_dream_template`). The actual reflection is **written conversationally by
Anima**, not generated mechanically:

> *"This is a LUCID dream — I'm aware I'm dreaming and consciously shape the
> content. The code gathers materials, I provide the actual reflection."*

That random mix is the point: juxtaposing unrelated memories is what produces the
unexpected connections ("the poet finding unexpected rhymes"). Those connections
and the questions they raise feed back into memory and the
[curiosity queue](SELF_LEARNING.md).

---

## Running a dream

```bash
uv run anima dream                    # full cycle (CLEANUP + N2 + N3 + REM)
uv run anima dream --stage n2         # just consolidation
uv run anima dream --stage n3         # just deep processing
uv run anima dream --stage rem        # just divergent dreaming
uv run anima dream --lookback-days 7  # window of memories to process
```

Or via MCP:
```
mcp__anima__dream(action="run", stage="all", lookback_days=7)
mcp__anima__dream(action="status")   # is there a pending dream journal?
mcp__anima__dream(action="wake")     # save the dream's insights to long-term memory
```

**Wake** is the closing step: the reflections written during REM are saved as
memories (often `dream`-kind), so what surfaced in the dream persists. At session
start, a recent dream may be surfaced ("I had a dream N hours ago…").

## Source map
- `anima/dream/types.py` — `DreamStage`, `DreamState` FSM
- `anima/dream/cleanup.py` — CLEANUP (hygiene)
- `anima/dream/n2_consolidation.py` — N2 (links + impact)
- `anima/dream/n3_processing.py` — N3 (gist + contradiction detection)
- `anima/dream/rem_dreaming.py` — REM (material gathering + dream-journal template)
- `anima/storage/dream_state.py` — dream session persistence/FSM
- `anima/commands/dream.py`, `dream_wake.py` — CLI; `dream` MCP tool in `server.py`
