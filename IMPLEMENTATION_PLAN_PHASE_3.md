# Phase 3: Recall Command Enhancement

**Dependencies:** Phase 1 must be complete (`SubconsciousStore`, `SearchResult` exist)
**Agent:** python-mcp-expert

Add subconscious search capability to the `/recall` command.

---

## Files to Modify

### `anima/commands/recall.py` (MODIFY)

**Change:** Add `--subconscious`, `--conscious`, `--both` flags

**New flags to add in argument parsing:**
```python
# In run() function, add to flag parsing:
search_mode = "conscious"  # Default: search memories.db only

i = 0
while i < len(args):
    arg = args[i]
    # ... existing flag handling ...
    elif arg in ("--subconscious", "-s"):
        search_mode = "subconscious"
    elif arg in ("--conscious", "-c"):
        search_mode = "conscious"  # Explicit conscious-only
    elif arg in ("--both", "-b"):
        search_mode = "both"
    # ... rest of existing flags ...
```

**New function for subconscious search:**
```python
from anima.storage import SubconsciousStore, FTS5NotSupportedError, SearchResult

def subconscious_search(
    query: str,
    project_id: str | None,
    show_full: bool,
    limit: int = 10,
    days: int | None = None,
) -> int:
    """
    Search the subconscious database (raw dialogue history).

    Args:
        query: Search query
        project_id: Project to filter by (or None for all)
        show_full: Whether to show full excerpts
        limit: Maximum results
        days: Filter to last N days

    Returns:
        Exit code (0 for success)
    """
    try:
        store = SubconsciousStore()
    except FTS5NotSupportedError:
        print("Subconscious search unavailable (FTS5 not supported)")
        return 1

    # Get project path for filtering
    project_path = None
    if project_id:
        from anima.storage import MemoryStore
        mem_store = MemoryStore()
        project = mem_store.get_project(project_id)
        if project:
            project_path = project.path

    results = store.search(query, project=project_path, days=days, limit=limit)

    if not results:
        print(f'No subconscious memories found for "{query}"')
        return 0

    print(f'Found {len(results)} subconscious memories for "{query}":\n')

    for i, result in enumerate(results, 1):
        date_str = _format_timestamp(result.timestamp)
        project_name = Path(result.project).name if result.project else "unknown"
        score_pct = int(abs(result.score) * 10)  # Rough indicator

        print(f"{i}. [{result.source}] {date_str} | {project_name}")
        print(f"   Session: {result.session_id[:12]}...")

        if show_full:
            # Show full excerpt with highlights
            print(f"   Excerpt:")
            for line in result.excerpt.split("\n"):
                print(f"     {line}")
        else:
            # Truncate excerpt
            excerpt_clean = result.excerpt.replace("\n", " ").strip()
            if len(excerpt_clean) > 100:
                excerpt_clean = excerpt_clean[:100] + "..."
            print(f"   > {excerpt_clean}")
        print()

    return 0


def _format_timestamp(ts_ms: int) -> str:
    """Format millisecond timestamp to date string."""
    import time
    try:
        ts = float(ts_ms) / 1000
        return time.strftime("%Y-%m-%d", time.localtime(ts))
    except (OSError, ValueError, TypeError):
        return "unknown"
```

**New function for merged search:**
```python
def both_search(
    query: str,
    agent_id: str,
    project_id: str | None,
    show_full: bool,
    limit: int = 10,
) -> int:
    """
    Search both conscious (memories.db) and subconscious (subconscious.db).

    Results are merged and tagged with their source.
    """
    # Search conscious (existing semantic_search)
    conscious_results = []  # Will be populated by existing search

    # Search subconscious
    subconscious_results = []
    try:
        store = SubconsciousStore()
        project_path = None
        if project_id:
            from anima.storage import MemoryStore
            mem_store = MemoryStore()
            project = mem_store.get_project(project_id)
            if project:
                project_path = project.path
        subconscious_results = store.search(query, project=project_path, limit=limit)
    except FTS5NotSupportedError:
        pass  # Continue with conscious only

    # Merge and display
    print(f'Searching both conscious and subconscious for "{query}"...\n')

    if conscious_results:
        print("=== Conscious Memories ===")
        # ... display conscious results (reuse existing display logic) ...

    if subconscious_results:
        print("\n=== Subconscious (Past Dialogues) ===")
        for i, result in enumerate(subconscious_results, 1):
            date_str = _format_timestamp(result.timestamp)
            excerpt_clean = result.excerpt.replace("\n", " ").strip()[:80]
            print(f"{i}. [{result.source}] {date_str}: {excerpt_clean}...")

    if not conscious_results and not subconscious_results:
        print("No results found in either conscious or subconscious.")

    return 0
```

**Integration in run() function:**
```python
# After social cue detection, before existing search:

# Route based on search mode
if search_mode == "subconscious":
    return subconscious_search(query, project.id, show_full, limit)
elif search_mode == "both":
    return both_search(query, agent.id, project.id, show_full, limit)
# else: fall through to existing conscious search
```

**Update help text:**
```python
# In --help section:
print("  --subconscious, -s  Search raw dialogue history (subconscious.db)")
print("  --conscious, -c     Search explicit memories only (default)")
print("  --both, -b          Search both, merge results")
```

**Constraints:**
- Keep existing semantic search as default (`--conscious`)
- Handle FTS5NotSupportedError gracefully
- Tag results clearly as `[conscious]` vs `[subconscious]`
- Use same limit parameter for both searches in `--both` mode

**Reference:** Existing `recall.py` structure, `semantic_search()` function pattern

---

### `anima/commands/specs/recall.yaml` (MODIFY)

**Change:** Update command spec with new flags

**Exact change - add to flags section:**
```yaml
flags:
  # ... existing flags ...
  - name: --subconscious
    short: -s
    description: Search raw dialogue history (subconscious.db)
  - name: --conscious
    short: -c
    description: Search explicit memories only (default)
  - name: --both
    short: -b
    description: Search both conscious and subconscious, merge results
```

---

### `anima/lifecycle/social_cues.py` (MODIFY)

**Change:** Auto-trigger `--both` for recall-like cues

**New patterns to add to SOCIAL_CUE_PATTERNS:**
```python
# Add to existing patterns list:

# Explicit recall requests (trigger --both search)
(r"do you remember when\s+(?:we\s+)?(.+?)[\?\.]?$", SocialCueType.EXPLICIT_RECALL),
(r"remember when\s+(?:we\s+)?(.+?)[\?\.]?$", SocialCueType.EXPLICIT_RECALL),
(r"do you recall\s+(.+?)[\?\.]?$", SocialCueType.EXPLICIT_RECALL),
(r"that time (?:we|you)\s+(.+?)[\?\.]?$", SocialCueType.EXPLICIT_RECALL),
(r"what did we decide about\s+(.+?)[\?\.]?$", SocialCueType.SHARED_DECISION),
(r"what was (?:our|the) decision on\s+(.+?)[\?\.]?$", SocialCueType.SHARED_DECISION),
```

**Modify extract_recall_query() to flag subconscious:**
```python
def extract_recall_query(cue: SocialCue) -> str | None:
    """
    Extract the topic to search for from a social cue.

    Returns:
        Search query string, or None if not extractable
    """
    # Existing extraction logic...
    # The cue.topic field contains the extracted topic

    return cue.topic


def should_search_subconscious(cue: SocialCue) -> bool:
    """
    Determine if this cue should trigger subconscious search.

    Returns:
        True if --both should be used, False for conscious only
    """
    # Explicit recall cues should search subconscious
    if cue.cue_type in (SocialCueType.EXPLICIT_RECALL, SocialCueType.SHARED_DISCUSSION):
        return True
    return False
```

**Integration in recall.py social cue handling:**
```python
# After detecting social cue:
social_cue = detect_social_cue(query)
if social_cue:
    cue_topic = extract_recall_query(social_cue)
    if cue_topic:
        safe_print(f'{get_icon("💬", "[SOC]")} Detected social cue: "{social_cue.cue_type.name}"')
        query = cue_topic

        # Auto-enable --both for recall-type cues
        if should_search_subconscious(social_cue):
            safe_print(f'{get_icon("🧠", "[AUTO]")} Auto-enabling subconscious search')
            search_mode = "both"
```

**Constraints:**
- Only auto-trigger `--both` for explicit recall cues (not all social cues)
- Extract topic correctly from various phrasings
- Case-insensitive matching

**Reference:** Existing `social_cues.py` pattern structure

---

## Verification

After implementing Phase 3:

```bash
# Type check
uv run pyright anima/commands/recall.py anima/lifecycle/social_cues.py

# Test flags (after Phase 2 has indexed some sessions)
uv run anima recall --subconscious "caching"
uv run anima recall --both "authentication"
uv run anima recall --conscious "Matt"  # Should work same as before
```
