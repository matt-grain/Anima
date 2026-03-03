# Phase 2: Session End Indexing

**Dependencies:** Phase 1 must be complete (`SubconsciousStore`, `DialogueTurn`, `SessionMeta` exist)
**Agent:** python-mcp-expert

Automatically index dialogues at session end without LLM involvement.

---

## Files to Create

### `anima/hooks/dialogue_parser.py`

**Purpose:** Shared utilities for parsing dialogue from session transcript files

**Dependencies:** json, re, pathlib
**Imports from Phase 1:** `DialogueTurn`, `SessionMeta`

**Functions:**
```python
from pathlib import Path
from typing import Literal

from anima.storage.subconscious_types import DialogueTurn, SessionMeta

def detect_format(path: Path) -> Literal["claude", "antigravity", "opencode", "gemini"]:
    """
    Detect the transcript format from file content.

    Detection rules:
    - "parentUuid" or "message" in entry → claude
    - "record_type": "state" or "type": "session_meta" → codex/antigravity
    - Default to claude if unclear
    """

def parse_claude_session(path: Path) -> tuple[SessionMeta, list[DialogueTurn]] | None:
    """
    Parse a Claude Code session JSONL file.

    Returns:
        Tuple of (metadata, dialogue turns) or None if file is invalid/empty

    Behavior:
    - Extract session_id from first entry or filename
    - Extract project from entry.cwd or environment_context
    - Skip entries where type not in ('user', 'assistant')
    - Extract content from entry.message.content
    - Handle content as string or list of blocks
    - Clean content with clean_content()
    - Skip if fewer than 4 turns
    """

def parse_antigravity_session(path: Path) -> tuple[SessionMeta, list[DialogueTurn]] | None:
    """
    Parse an Antigravity/Codex session JSONL file.

    Same return signature as parse_claude_session.
    """

def parse_session(path: Path) -> tuple[SessionMeta, list[DialogueTurn]] | None:
    """
    Auto-detect format and parse session.

    Dispatches to parse_claude_session or parse_antigravity_session
    based on detect_format() result.
    """

def clean_content(content: str) -> str:
    """
    Remove noise from dialogue content before indexing.

    Removes:
    - XML-style tags: <command-message>, <system-reminder>, <function_calls>, <function_results>
    - LTM injection blocks: [LTM:...[/LTM]
    - Code blocks over 500 characters (replace with "[code block - N chars]")
    - Multiple consecutive newlines (collapse to 2)

    Returns:
        Cleaned content string
    """

def extract_text_from_content(content: str | list) -> str:
    """
    Extract plain text from message content.

    Handles both string content and list-of-blocks format:
    - If string: return as-is
    - If list: extract 'text' from blocks where type in ('text', 'input_text', 'output_text')
    """
```

**Regex Patterns for clean_content:**
```python
# Tag patterns to remove entirely
TAG_PATTERNS = [
    r"<command-message>.*?</command-message>",
    r"<command-name>.*?</command-name>",
    r"<system-reminder>.*?</system-reminder>",
    r"<function_results>.*?</function_results>",
    r"<function_calls>.*?</function_calls>",
]

# LTM block pattern
LTM_PATTERN = r"\[LTM:.*?\[/LTM\]"

# Large code block pattern (capture for size check)
CODE_BLOCK_PATTERN = r"```(\w*)\n(.*?)```"
```

**Constraints:**
- Extract logic from existing `subconscious_extract.py` (that file will be deleted in Phase 4)
- Minimum 4 dialogue turns to be worth indexing
- Maximum 100KB content per session (truncate with "[... truncated ...]")
- Handle both Claude Code and Antigravity/Codex formats

**Reference:** `anima/hooks/subconscious_extract.py` for existing parsing logic to extract

---

## Files to Modify

### `anima/hooks/session_end.py` (MODIFY)

**Change:** Add subconscious indexing after decay processing

**Existing behavior (keep):**
1. Clean up pre-compact WIP memory
2. Save spaceship journal if provided
3. Process decay
4. Check memory integrity

**New behavior (add after decay, before integrity):**
```python
# --- NEW: Index dialogue to subconscious ---
from anima.storage import SubconsciousStore, FTS5NotSupportedError
from anima.hooks.dialogue_parser import parse_session
import os

def _index_current_session(transcript_path: Path | None) -> int | None:
    """
    Index the current session's dialogue to subconscious.db.

    Args:
        transcript_path: Path to session JSONL (from hook input or detected)

    Returns:
        Number of messages indexed, or None if skipped/failed
    """
    if not transcript_path or not transcript_path.exists():
        log.debug("No transcript path provided or file missing")
        return None

    try:
        store = SubconsciousStore()
    except FTS5NotSupportedError:
        log.warning("FTS5 not supported - subconscious indexing disabled")
        return None

    # Check if already indexed
    mtime = transcript_path.stat().st_mtime
    if store.is_session_indexed(str(transcript_path), mtime):
        log.debug(f"Session already indexed: {transcript_path.name}")
        return None

    # Parse dialogue
    result = parse_session(transcript_path)
    if result is None:
        log.debug(f"No dialogue to index from {transcript_path.name}")
        return None

    meta, dialogue = result

    # Index
    count = store.index_session(meta, dialogue)
    log.info(f"Indexed {count} messages to subconscious from {transcript_path.name}")
    return count
```

**Transcript Path Detection:**

For Claude Code hooks, the transcript path comes from stdin JSON:
```python
# In run() function, after parsing args:

# Get transcript path from hook input (Claude Code provides this)
transcript_path = None
hook_input = os.environ.get("CLAUDE_HOOK_INPUT")
if hook_input:
    try:
        import json
        data = json.loads(hook_input)
        if "transcript_path" in data:
            transcript_path = Path(data["transcript_path"])
    except (json.JSONDecodeError, KeyError):
        pass

# Alternative: detect from session ID if available
if not transcript_path:
    # Try to find from Claude's project sessions directory
    session_id = get_current_session_id()
    if session_id:
        claude_dir = Path.home() / ".claude" / "projects"
        # Search for matching JSONL (expensive but fallback)
        for jsonl in claude_dir.rglob("*.jsonl"):
            if session_id in jsonl.stem:
                transcript_path = jsonl
                break
```

**Integration point in run():**
```python
# After: compacted = decay.process_decay(...)
# Before: deleted = decay.delete_empty_memories(...)

# Index current session to subconscious
indexed_count = _index_current_session(transcript_path)
if indexed_count:
    print(f"Indexed {indexed_count} messages to subconscious")
```

**Constraints:**
- Don't fail session_end if indexing fails - log and continue
- Skip if FTS5 not supported (graceful degradation)
- Skip if already indexed (incremental)
- Log indexing results

**Reference:** Existing `session_end.py` structure for where to add code

---

## Verification

After implementing Phase 2:

```bash
# Type check
uv run pyright anima/hooks/dialogue_parser.py anima/hooks/session_end.py

# Manual test: run session_end with a test transcript
uv run anima end-session

# Check database was created
ls -la ~/.anima/subconscious.db
```
