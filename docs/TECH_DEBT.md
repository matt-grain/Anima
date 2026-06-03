# Tech Debt Ledger

Known cleanup that's been **deliberately deferred** — captured here so it isn't
forgotten. Most of this came from a dead-code/duplication audit (2026-06); the
safe, high-value items were already fixed (see git history). What remains is
either risky-to-rush or low-value-for-now.

Status legend: 🔴 do next · 🟡 when convenient · 🟢 nice-to-have

---

## 1. Deferred duplication (risky refactors)

These touch the setup/command machinery that configures every user, and have
thin test coverage — they deserve a dedicated PR with tests, not a release rush.

| # | Item | Notes |
|---|---|---|
| 🔴 | **`setup_hooks` merge** (`platforms/claude.py` ↔ `gemini.py`) | ~120 lines of near-duplicate settings.json hook-building. NOT a trivial merge: Claude has an extra **global-install + HTTP-shim branch** Gemini lacks, and event names differ (`PreCompact` vs `PreCompress`). Extract a parametrized base helper. |
| 🟡 | **`BaseCommand` adoption** (`anima/commands/*.py`) | ~21 command files hand-roll `run(args)` arg-parsing + the `resolver/agent/project/store` boilerplate. The `BaseCommand` base was *deleted* (it was unused); to remove the duplication, reintroduce a base/shared helper and adopt it across commands — large, broad diff. |
| 🟡 | **`setup_extras`** (claude/gemini/antigravity) | Diverge per platform (not identical), so not hoisted. Revisit if they converge. |

---

## 2. Medium-confidence dead code (left in place)

The audit flagged these as having no production caller, but with **medium**
false-positive risk (they may be intended public API, or MCP-reachable). Verify
before removing — don't bulk-delete.

| Symbol | File | Risk |
|---|---|---|
| `detect_all_social_cues`, `requires_recall` | `lifecycle/social_cues.py` | test-only; plausible public API |
| `find_all_temporal_cues` | `lifecycle/temporal.py` | only `parse_temporal_cue` is used in prod |
| `get_project_relevant_memories` | `lifecycle/project_context.py` | no prod caller |
| `bridge_to_curiosity`, `refresh` | `lifecycle/curiosity_bridge.py` | test-only; maybe public |
| `get_session_start_time` | `lifecycle/session.py` | no prod caller |
| `suggest_link_type` | `graph/linker.py` | `LinkSuggester` is what's used |
| `batch_similarities` | `embeddings/similarity.py` | test-only util |
| `find_memories_near_commit` | `utils/git.py` | test-only |
| `log_error` | `logging.py` | no caller |
| `get_session`, `cleanup_old_sessions`, `deserialize_rem_result` | `storage/dream_state.py` | no prod caller / test-only |
| `get_open_scope_issues` | `storage/dissonance.py` | no prod caller |
| `set_thread`, `get_memories_by_thread`, `delete_links_for_memory` | `storage/sqlite.py` | "thread" feature appears unused; public store API |
| `get_project_by_path`, `update_confidence` | `storage/sqlite.py` + `storage/protocol.py` | declared in protocol **and** impl, never called — remove from both together |
| `get_display`, `get_daemon_client`, `get_daemon_server` | `eyes/__init__.py` | unused lazy getters (skipped earlier: `get_config` is interleaved, so delete carefully) |
| `set_random_look`, `set_random_blink`, `set_background_color` | `eyes/display.py`, `renderer.py` | UI API; may be intentional |
| `yellow`, `cyan`, `magenta`, `white` | `light/ibuddy.py` | hardware convenience methods; likely intentional |

> Tip: re-run `uv run --no-sync vulture anima/ --min-confidence 70` and
> cross-check each hit (FastMCP `@mcp.tool()` handlers, hook `run()`/`__main__`
> entrypoints, and Pydantic validators are **false positives**).

---

## 3. Scaling & architecture notes

| # | Item | Notes |
|---|---|---|
| 🟡 | **O(N) cosine scan on recall/linking** | `get_memories_with_embeddings` loads *all* embeddings and scores them in pure Python (`embeddings/similarity.py`). Fine at a few thousand memories (~tens of ms); at ~10k+ it becomes the bottleneck. Options: `sqlite-vss`, or prefilter candidates harder. See [RETRIEVAL.md](RETRIEVAL.md). |
| 🟡 | **`MemoryStore()` per MCP tool call** | Each `memory`/`curiosity`/… tool call constructs a new `MemoryStore`, which re-runs `_init_db` (schema `executescript` + `set_schema_version`) — an extra write per call. Consider a cached/shared store on the server. |
| 🟢 | **`server.py:run_server`** | Now reachable only via its `__main__` dev path (the `--server` CLI command was removed). Keep for `python -m anima.server`, or drop if that path is unneeded. |

---

## 4. Embodiment / `serve` caveats

- Embodiment (`--eyes/--tts/--light`) is wired into `anima serve`, but enabling
  it in **`--reload`** mode configures the globals in the reloader parent, not
  the worker — prefer running `serve` without `--reload` when using embodiment.
- The eyes client connects **lazily** on first `body()` use; the FastMCP
  lifespan pre-connect isn't run under the mounted HTTP app. Verify with real
  hardware before relying on pre-connection.

---

*Maintained as items are found/fixed. When you clear one, delete its row.*
