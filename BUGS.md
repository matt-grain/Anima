# Anima Bugs & Issues

## BUG-001: Post-compact WIP detection fails to trigger auto-deferred loading

**Date:** 2026-02-05
**Severity:** Medium
**Status:** Open

### Symptom

After automated context compaction, the 35 deferred memories were not loaded. The session output showed `# GREETING BEHAVIOR:` and `# LTM-DEFERRED: 35 additional memories available. Run /load-deferred after greeting.` instead of `# POST-COMPACT BEHAVIOR:` and `# LTM-POSTCOMPACT:` status.

### Expected Behavior

When a WIP memory exists at SessionStart (signal from PreCompact), the system should:
1. Set `is_post_compact = True`
2. Auto-load all deferred memories inline
3. Output `# LTM-POSTCOMPACT: Context restored automatically`
4. Use `# POST-COMPACT BEHAVIOR:` instead of `# GREETING BEHAVIOR:`

### Actual Behavior

The WIP memory (`1deb0ab8`) was saved by PreCompact and later cleaned up by SessionEnd, but the SessionStart detection gate never fired. No "WIP detected... POST-COMPACT mode" log line appeared.

### Log Evidence

```
22:35:44 | INFO  | [2e459f73] Saved WIP memory 1deb0ab8 for post-compact recovery
22:36:43 | INFO  | [bce7c060] Injected 58 memories, deferred 35      <-- no WIP detection
22:36:43 | INFO  | [bce7c060] SessionStart hook completed
22:38:35 | DEBUG | [a8f145fb] Cleaned up pre-compact WIP memory 1deb0ab8  <-- SessionEnd found it
```

### Root Cause Analysis

The detection gate in `session_start.py:314-374` has two conditions:
1. `wip_id = get_precompact_memory_id()` - retrieves WIP ID from settings
2. `if wip_id in injected_ids` - checks if the WIP was actually injected

Possible failure points:
- **Settings read issue:** `get_precompact_memory_id()` returned `None` during SessionStart (but SessionEnd's `clear_precompact_memory_id()` found it fine)
- **Injection miss:** WIP memory was not in `injected_ids` despite having highest priority (`ImpactLevel.WIP = -1`). Could be a project_id mismatch between PreCompact save and SessionStart injection query
- **Race condition:** The WIP memory was saved ~1 minute before SessionStart; unlikely but possible file/DB timing issue

### Investigation Steps

1. Add `DEBUG` logging to the WIP detection branch:
   - Log `wip_id` value from `get_precompact_memory_id()`
   - Log whether `wip_id` is in `injected_ids`
   - Log the project_id used during WIP save vs injection query
2. Check settings storage mechanism for read-after-write consistency
3. Verify `get_memories_by_impact(impact=ImpactLevel.WIP)` query returns the WIP memory

### Files Involved

- `anima/hooks/session_start.py` (lines 314-374) - WIP detection logic
- `anima/hooks/pre_compact.py` (lines 120-151) - WIP memory creation
- `anima/lifecycle/injection.py` (lines 338-349) - WIP priority loading
- `anima/core/types.py` - `ImpactLevel.WIP` enum
