# Phase 5: Tests & Documentation

**Dependencies:** All previous phases must be complete
**Agent:** python-mcp-expert

Add comprehensive tests and update documentation.

---

## Files to Create

### `tests/storage/test_subconscious.py`

**Purpose:** Unit tests for SubconsciousStore

**Fixtures (add to conftest.py or local):**
```python
import pytest
from pathlib import Path
from anima.storage import SubconsciousStore
from anima.storage.subconscious_types import DialogueTurn, SessionMeta

@pytest.fixture
def temp_subconscious_db(tmp_path: Path) -> Path:
    """Create a temporary subconscious database path."""
    return tmp_path / "subconscious.db"

@pytest.fixture
def subconscious_store(temp_subconscious_db: Path) -> SubconsciousStore:
    """Create a SubconsciousStore with temp database."""
    return SubconsciousStore(db_path=temp_subconscious_db)

@pytest.fixture
def sample_session_meta() -> SessionMeta:
    """Sample session metadata for testing."""
    return SessionMeta(
        session_id="test-session-123",
        source="claude",
        project="/path/to/project",
        file_path="/path/to/session.jsonl",
        timestamp=1709500000000,  # 2024-03-03 in ms
    )

@pytest.fixture
def sample_dialogue() -> list[DialogueTurn]:
    """Sample dialogue turns for testing."""
    return [
        DialogueTurn(role="user", content="How do I implement caching?", timestamp=1709500000000),
        DialogueTurn(role="assistant", content="Here's how to implement caching with Redis...", timestamp=1709500001000),
        DialogueTurn(role="user", content="What about memory caching?", timestamp=1709500002000),
        DialogueTurn(role="assistant", content="For in-memory caching, you can use functools.lru_cache...", timestamp=1709500003000),
    ]
```

**Tests:**
```python
class TestSubconsciousStore:
    """Tests for SubconsciousStore."""

    def test_store_creation(self, temp_subconscious_db: Path) -> None:
        """Test creating a subconscious store."""
        store = SubconsciousStore(db_path=temp_subconscious_db)
        assert store is not None
        assert temp_subconscious_db.exists()

    def test_index_session_creates_fts5_entries(
        self,
        subconscious_store: SubconsciousStore,
        sample_session_meta: SessionMeta,
        sample_dialogue: list[DialogueTurn],
    ) -> None:
        """Test that indexing a session creates FTS5 entries."""
        count = subconscious_store.index_session(sample_session_meta, sample_dialogue)
        assert count == 4  # 4 dialogue turns

        stats = subconscious_store.get_stats()
        assert stats.total_sessions == 1
        assert stats.total_messages == 4

    def test_search_returns_bm25_ranked_results(
        self,
        subconscious_store: SubconsciousStore,
        sample_session_meta: SessionMeta,
        sample_dialogue: list[DialogueTurn],
    ) -> None:
        """Test that search returns ranked results."""
        subconscious_store.index_session(sample_session_meta, sample_dialogue)

        results = subconscious_store.search("caching")
        assert len(results) > 0
        assert "caching" in results[0].excerpt.lower() or "**caching**" in results[0].excerpt.lower()

    def test_search_with_recency_boost(
        self,
        subconscious_store: SubconsciousStore,
    ) -> None:
        """Test that recent sessions rank higher than old ones."""
        import time
        now_ms = int(time.time() * 1000)
        old_ms = now_ms - (60 * 86_400_000)  # 60 days ago

        # Index old session
        old_meta = SessionMeta("old-session", "claude", "/proj", "/old.jsonl", old_ms)
        old_dialogue = [DialogueTurn("user", "authentication flow", old_ms)]
        subconscious_store.index_session(old_meta, old_dialogue)

        # Index new session
        new_meta = SessionMeta("new-session", "claude", "/proj", "/new.jsonl", now_ms)
        new_dialogue = [DialogueTurn("user", "authentication setup", now_ms)]
        subconscious_store.index_session(new_meta, new_dialogue)

        results = subconscious_store.search("authentication")
        assert len(results) == 2
        # New session should rank higher due to recency boost
        assert results[0].session_id == "new-session"

    def test_search_filters_by_project(
        self,
        subconscious_store: SubconsciousStore,
    ) -> None:
        """Test that project filter works."""
        meta1 = SessionMeta("s1", "claude", "/project-a", "/a.jsonl", 1000)
        meta2 = SessionMeta("s2", "claude", "/project-b", "/b.jsonl", 1000)

        subconscious_store.index_session(meta1, [DialogueTurn("user", "test message")])
        subconscious_store.index_session(meta2, [DialogueTurn("user", "test message")])

        results = subconscious_store.search("test", project="/project-a")
        assert len(results) == 1
        assert results[0].project == "/project-a"

    def test_search_filters_by_days(
        self,
        subconscious_store: SubconsciousStore,
    ) -> None:
        """Test that days filter works."""
        import time
        now_ms = int(time.time() * 1000)
        old_ms = now_ms - (10 * 86_400_000)  # 10 days ago

        old_meta = SessionMeta("old", "claude", "/proj", "/old.jsonl", old_ms)
        new_meta = SessionMeta("new", "claude", "/proj", "/new.jsonl", now_ms)

        subconscious_store.index_session(old_meta, [DialogueTurn("user", "query")])
        subconscious_store.index_session(new_meta, [DialogueTurn("user", "query")])

        results = subconscious_store.search("query", days=5)
        assert len(results) == 1
        assert results[0].session_id == "new"

    def test_incremental_indexing_skips_unchanged_files(
        self,
        subconscious_store: SubconsciousStore,
        sample_session_meta: SessionMeta,
        sample_dialogue: list[DialogueTurn],
    ) -> None:
        """Test that re-indexing same file is skipped."""
        # First index
        count1 = subconscious_store.index_session(sample_session_meta, sample_dialogue)
        assert count1 == 4

        # Check is_session_indexed
        assert subconscious_store.is_session_indexed(
            sample_session_meta.file_path,
            1234567890.0,  # mtime doesn't match
        ) is False

        # Same path, same mtime should be skipped
        # (This requires storing mtime during first index)


class TestCleanContent:
    """Tests for content cleaning utilities."""

    def test_clean_content_removes_tool_calls(self) -> None:
        """Test that tool calls are removed."""
        from anima.hooks.dialogue_parser import clean_content

        content = "Before <function_calls>tool stuff</function_calls> After"
        cleaned = clean_content(content)
        assert "<function_calls>" not in cleaned
        assert "Before" in cleaned
        assert "After" in cleaned

    def test_clean_content_removes_large_code_blocks(self) -> None:
        """Test that large code blocks are replaced."""
        from anima.hooks.dialogue_parser import clean_content

        large_code = "x" * 600
        content = f"Before\n```python\n{large_code}\n```\nAfter"
        cleaned = clean_content(content)
        assert large_code not in cleaned
        assert "[python block" in cleaned or "[code block" in cleaned
        assert "Before" in cleaned
        assert "After" in cleaned

    def test_clean_content_keeps_small_code_blocks(self) -> None:
        """Test that small code blocks are kept."""
        from anima.hooks.dialogue_parser import clean_content

        content = "Before\n```python\nprint('hello')\n```\nAfter"
        cleaned = clean_content(content)
        assert "print('hello')" in cleaned
```

**Constraints:**
- Use existing `conftest.py` fixtures where applicable
- Follow existing test naming pattern: `test_<action>_<scenario>_<expected>`
- Include both happy path and edge cases

**Reference:** `tests/test_storage.py` for store testing patterns

---

### `tests/commands/test_recall_subconscious.py`

**Purpose:** Tests for recall command subconscious features

**Tests:**
```python
import pytest
from pathlib import Path
from anima.commands.recall import run, subconscious_search
from anima.storage import SubconsciousStore
from anima.storage.subconscious_types import DialogueTurn, SessionMeta

class TestRecallSubconscious:
    """Tests for recall --subconscious flag."""

    @pytest.fixture
    def indexed_subconscious(self, tmp_path: Path) -> SubconsciousStore:
        """Create and populate a subconscious store."""
        store = SubconsciousStore(db_path=tmp_path / "subconscious.db")
        meta = SessionMeta("test-session", "claude", "/test", "/test.jsonl", 1000)
        dialogue = [
            DialogueTurn("user", "How does caching work?"),
            DialogueTurn("assistant", "Caching stores frequently accessed data..."),
        ]
        store.index_session(meta, dialogue)
        return store

    def test_recall_subconscious_flag_searches_subconscious_db(
        self,
        indexed_subconscious: SubconsciousStore,
        capsys,
    ) -> None:
        """Test that --subconscious flag searches subconscious.db."""
        # Would need to mock SubconsciousStore to use our indexed one
        # This is an integration test pattern
        pass  # TODO: implement with proper mocking

    def test_recall_conscious_flag_searches_memories_db(self, capsys) -> None:
        """Test that --conscious flag (default) searches memories.db."""
        # Run with explicit --conscious
        exit_code = run(["--conscious", "test"])
        # Should not error even if no results
        assert exit_code == 0

    def test_recall_both_flag_merges_results(self) -> None:
        """Test that --both flag searches both databases."""
        # Integration test
        pass  # TODO: implement

    def test_recall_social_cue_triggers_both(self) -> None:
        """Test that 'do you remember when...' triggers --both."""
        from anima.lifecycle.social_cues import detect_social_cue, should_search_subconscious

        cue = detect_social_cue("do you remember when we discussed caching?")
        assert cue is not None
        assert should_search_subconscious(cue) is True
```

**Reference:** `tests/test_commands.py` for command testing patterns

---

### `tests/hooks/test_session_end_indexing.py`

**Purpose:** Tests for session end subconscious indexing

**Tests:**
```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

class TestSessionEndIndexing:
    """Tests for session end subconscious indexing."""

    def test_session_end_indexes_dialogue(self, tmp_path: Path) -> None:
        """Test that session end indexes dialogue to subconscious."""
        # Create a mock transcript file
        transcript = tmp_path / "session.jsonl"
        transcript.write_text('''
{"type": "user", "message": {"role": "user", "content": "Hello"}}
{"type": "assistant", "message": {"role": "assistant", "content": "Hi there!"}}
{"type": "user", "message": {"role": "user", "content": "How are you?"}}
{"type": "assistant", "message": {"role": "assistant", "content": "I'm doing well!"}}
        '''.strip())

        # Mock the indexing
        with patch('anima.hooks.session_end.SubconsciousStore') as MockStore:
            mock_store = MagicMock()
            mock_store.is_session_indexed.return_value = False
            mock_store.index_session.return_value = 4
            MockStore.return_value = mock_store

            from anima.hooks.session_end import _index_current_session
            count = _index_current_session(transcript)

            assert count == 4
            mock_store.index_session.assert_called_once()

    def test_session_end_skips_short_conversations(self, tmp_path: Path) -> None:
        """Test that short conversations (<4 turns) are skipped."""
        transcript = tmp_path / "short.jsonl"
        transcript.write_text('''
{"type": "user", "message": {"role": "user", "content": "Hello"}}
{"type": "assistant", "message": {"role": "assistant", "content": "Hi!"}}
        '''.strip())

        from anima.hooks.dialogue_parser import parse_session
        result = parse_session(transcript)

        # Should return None for short conversations
        assert result is None

    def test_session_end_handles_missing_transcript(self) -> None:
        """Test graceful handling of missing transcript."""
        from anima.hooks.session_end import _index_current_session
        result = _index_current_session(Path("/nonexistent/file.jsonl"))
        assert result is None

    def test_session_end_handles_fts5_not_supported(self, tmp_path: Path) -> None:
        """Test graceful handling when FTS5 is not available."""
        from anima.storage import FTS5NotSupportedError

        transcript = tmp_path / "session.jsonl"
        transcript.write_text('{"type": "user", "message": {"role": "user", "content": "Test"}}')

        with patch('anima.hooks.session_end.SubconsciousStore') as MockStore:
            MockStore.side_effect = FTS5NotSupportedError("FTS5 not available")

            from anima.hooks.session_end import _index_current_session
            result = _index_current_session(transcript)

            assert result is None  # Should not crash
```

**Reference:** `tests/test_hooks.py` for hook testing patterns

---

## Files to Modify

### `ARCHITECTURE.md` (MODIFY)

**Change:** Document new subconscious architecture

**Add new section after "Database Schema":**
```markdown
---

## Subconscious Layer

The subconscious layer provides searchable access to raw dialogue history without loading it into context.

### Philosophy

Unlike conscious memories (explicitly saved via `/remember`), subconscious memories are:
- **Automatically indexed** at session end (no LLM processing)
- **Not loaded** into context at session start
- **Searchable** on demand via `/recall --subconscious`
- **Separate** from the main LTM database

This preserves the metaphor: I can't "see" my subconscious, but I can search it when prompted.

### Storage

Subconscious uses a separate SQLite database with FTS5 full-text search:

```
~/.anima/subconscious.db
├── sessions (metadata: session_id, source, project, timestamp)
└── messages (FTS5 virtual table: role, text)
```

### Search Ranking

Results are ranked using:
- **BM25** (80%): Term frequency / inverse document frequency
- **Recency** (20%): 30-day half-life decay boost

### Commands

```bash
/recall --subconscious "query"  # Search dialogues only
/recall --both "query"          # Search both conscious + subconscious
/recall "query"                 # Search conscious only (default)
```

### Auto-Triggering

Social cues like "do you remember when we discussed X?" automatically trigger `--both` search.
```

**Update the diagram in Overview section to show two databases.**

---

### `CHANGELOG.md` (MODIFY)

**Change:** Add v0.15.0 entry

**Add at top:**
```markdown
## [0.15.0] - 2026-03-XX "True Subconscious"

### Added
- **True Subconscious System**: Raw dialogues are now auto-indexed at session end using FTS5 full-text search
- **`/recall --subconscious`**: Search past dialogues without loading them into context
- **`/recall --both`**: Search both conscious memories and subconscious dialogues
- **Auto-trigger**: "Do you remember when..." phrases automatically search subconscious

### Changed
- Session end now indexes dialogues to `~/.anima/subconscious.db` (no LLM needed)
- Session start no longer requires subconscious processing (instant startup)

### Removed
- **LLM-based subconscious extraction**: No more Sonnet spawning at session start
- **`/process-subconscious`**: Command removed (no longer needed)
- **`/save-subconscious`**: Command removed (auto-indexed now)

### Migration Notes
The following directories are no longer used and can be safely deleted:
```bash
rm -rf ~/.anima/subconscious/pending
rm -rf ~/.anima/subconscious/done
rm -rf ~/.anima/subconscious/extracted
rm -rf ~/.anima/subconscious/extracted_done
```

The new subconscious system stores data in `~/.anima/subconscious.db`.
```

---

## Verification

After implementing Phase 5:

```bash
# Run all new tests
uv run pytest tests/storage/test_subconscious.py -v
uv run pytest tests/commands/test_recall_subconscious.py -v
uv run pytest tests/hooks/test_session_end_indexing.py -v

# Run full test suite to ensure nothing broke
uv run pytest tests/ -v

# Verify documentation
cat ARCHITECTURE.md | grep -A 20 "Subconscious Layer"
cat CHANGELOG.md | head -50
```
