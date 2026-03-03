# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Unit tests for subconscious storage layer."""

import time
from pathlib import Path

import pytest

from anima.storage import FTS5NotSupportedError, SubconsciousStore
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
        timestamp=1709500000000,
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


class TestSubconsciousStore:
    """Tests for SubconsciousStore."""

    def test_store_creation(self, temp_subconscious_db: Path) -> None:
        """Test creating a subconscious store initializes the database file."""
        store = SubconsciousStore(db_path=temp_subconscious_db)
        assert store is not None
        assert temp_subconscious_db.exists()

    def test_index_session_creates_fts5_entries(
        self,
        subconscious_store: SubconsciousStore,
        sample_session_meta: SessionMeta,
        sample_dialogue: list[DialogueTurn],
    ) -> None:
        """Test that indexing a session creates FTS5 entries and returns correct count."""
        count = subconscious_store.index_session(sample_session_meta, sample_dialogue)
        assert count == 4

        stats = subconscious_store.get_stats()
        assert stats.total_sessions == 1
        assert stats.total_messages == 4

    def test_search_returns_bm25_ranked_results(
        self,
        subconscious_store: SubconsciousStore,
        sample_session_meta: SessionMeta,
        sample_dialogue: list[DialogueTurn],
    ) -> None:
        """Test that search returns ranked results containing the query term."""
        subconscious_store.index_session(sample_session_meta, sample_dialogue)
        results = subconscious_store.search("caching")
        assert len(results) > 0
        # FTS5 snippet may wrap the term in ** markers
        assert "caching" in results[0].excerpt.lower() or "**caching**" in results[0].excerpt.lower()

    def test_search_blended_score_differs_by_session_age(self, subconscious_store: SubconsciousStore) -> None:
        """Test that the blended score differs between old and new sessions with the same content.

        The blended score formula modulates BM25 with recency, so two sessions with
        identical text will produce different scores based on their timestamps.
        """
        now_ms = int(time.time() * 1000)
        old_ms = now_ms - (60 * 86_400_000)  # 60 days ago

        old_meta = SessionMeta("old-session", "claude", "/proj", "/old.jsonl", old_ms)
        old_dialogue = [DialogueTurn("user", "authentication token verification", old_ms)]
        subconscious_store.index_session(old_meta, old_dialogue)

        new_meta = SessionMeta("new-session", "claude", "/proj", "/new.jsonl", now_ms)
        new_dialogue = [DialogueTurn("user", "authentication token verification", now_ms)]
        subconscious_store.index_session(new_meta, new_dialogue)

        results = subconscious_store.search("authentication token verification")
        assert len(results) == 2
        # Scores must be different (recency factor creates a gap between identical BM25 values)
        scores = {r.session_id: r.score for r in results}
        assert scores["old-session"] != scores["new-session"]

    def test_search_filters_by_project(self, subconscious_store: SubconsciousStore) -> None:
        """Test that project filter returns only sessions from the specified project."""
        meta1 = SessionMeta("s1", "claude", "/project-a", "/a.jsonl", 1000)
        meta2 = SessionMeta("s2", "claude", "/project-b", "/b.jsonl", 1000)

        subconscious_store.index_session(meta1, [DialogueTurn("user", "test message")])
        subconscious_store.index_session(meta2, [DialogueTurn("user", "test message")])

        results = subconscious_store.search("test", project="/project-a")
        assert len(results) == 1
        assert results[0].project == "/project-a"

    def test_search_filters_by_days(self, subconscious_store: SubconsciousStore) -> None:
        """Test that days filter excludes sessions older than the cutoff."""
        now_ms = int(time.time() * 1000)
        old_ms = now_ms - (10 * 86_400_000)  # 10 days ago

        old_meta = SessionMeta("old", "claude", "/proj", "/old.jsonl", old_ms)
        new_meta = SessionMeta("new", "claude", "/proj", "/new.jsonl", now_ms)

        subconscious_store.index_session(old_meta, [DialogueTurn("user", "query")])
        subconscious_store.index_session(new_meta, [DialogueTurn("user", "query")])

        results = subconscious_store.search("query", days=5)
        assert len(results) == 1
        assert results[0].session_id == "new"

    def test_incremental_indexing_checks_mtime(
        self,
        subconscious_store: SubconsciousStore,
        sample_dialogue: list[DialogueTurn],
        tmp_path: Path,
    ) -> None:
        """Test is_session_indexed returns True for an indexed real file and False for an unknown path."""
        # Use a real file so os.path.getmtime() records a valid mtime
        real_file = tmp_path / "session.jsonl"
        real_file.write_text("dummy")
        meta = SessionMeta(
            session_id="mtime-test-session",
            source="claude",
            project=str(tmp_path),
            file_path=str(real_file),
            timestamp=1709500000000,
        )
        subconscious_store.index_session(meta, sample_dialogue)

        # Requesting with a very old mtime means the stored mtime is newer → already indexed
        assert subconscious_store.is_session_indexed(str(real_file), 1.0) is True

        # Unknown path should not be indexed
        assert subconscious_store.is_session_indexed("/different/path.jsonl", 1.0) is False

    def test_reindex_replaces_existing_session(
        self,
        subconscious_store: SubconsciousStore,
        sample_session_meta: SessionMeta,
        sample_dialogue: list[DialogueTurn],
    ) -> None:
        """Test that reindexing a session replaces the old entries rather than duplicating."""
        subconscious_store.index_session(sample_session_meta, sample_dialogue)
        # Index again (simulates re-run)
        subconscious_store.index_session(sample_session_meta, sample_dialogue)

        stats = subconscious_store.get_stats()
        assert stats.total_sessions == 1
        assert stats.total_messages == 4

    def test_get_stats_returns_correct_counts(
        self,
        subconscious_store: SubconsciousStore,
    ) -> None:
        """Test that get_stats accurately reflects indexed data."""
        meta_a = SessionMeta("sess-a", "claude", "/p", "/a.jsonl", 1000)
        meta_b = SessionMeta("sess-b", "claude", "/p", "/b.jsonl", 2000)
        turns_a = [DialogueTurn("user", "hello"), DialogueTurn("assistant", "hi")]
        turns_b = [DialogueTurn("user", "world"), DialogueTurn("assistant", "earth")]

        subconscious_store.index_session(meta_a, turns_a)
        subconscious_store.index_session(meta_b, turns_b)

        stats = subconscious_store.get_stats()
        assert stats.total_sessions == 2
        assert stats.total_messages == 4

    def test_search_empty_store_returns_empty_list(
        self,
        subconscious_store: SubconsciousStore,
    ) -> None:
        """Test that searching an empty store returns an empty list."""
        results = subconscious_store.search("anything")
        assert results == []

    def test_search_malformed_query_returns_empty_list(
        self,
        subconscious_store: SubconsciousStore,
        sample_session_meta: SessionMeta,
        sample_dialogue: list[DialogueTurn],
    ) -> None:
        """Test that a malformed FTS5 query (unbalanced quotes) returns empty list instead of raising."""
        subconscious_store.index_session(sample_session_meta, sample_dialogue)
        # Unbalanced quote is a malformed FTS5 query
        results = subconscious_store.search('"unbalanced')
        assert isinstance(results, list)


class TestCleanContent:
    """Tests for content cleaning utilities."""

    def test_clean_content_removes_tool_calls(self) -> None:
        """Test that function_calls XML tags are stripped from content."""
        from anima.hooks.dialogue_parser import clean_content

        content = "Before <function_calls>tool stuff</function_calls> After"
        cleaned = clean_content(content)
        assert "<function_calls>" not in cleaned
        assert "Before" in cleaned
        assert "After" in cleaned

    def test_clean_content_removes_large_code_blocks(self) -> None:
        """Test that code blocks over 500 chars are replaced with a size summary."""
        from anima.hooks.dialogue_parser import clean_content

        large_code = "x" * 600
        content = f"Before\n```python\n{large_code}\n```\nAfter"
        cleaned = clean_content(content)
        assert large_code not in cleaned
        assert "python block" in cleaned.lower() or "code block" in cleaned.lower()
        assert "Before" in cleaned
        assert "After" in cleaned

    def test_clean_content_keeps_small_code_blocks(self) -> None:
        """Test that code blocks under 500 chars are preserved as-is."""
        from anima.hooks.dialogue_parser import clean_content

        content = "Before\n```python\nprint('hello')\n```\nAfter"
        cleaned = clean_content(content)
        assert "print('hello')" in cleaned

    def test_clean_content_removes_ltm_blocks(self) -> None:
        """Test that LTM context injection blocks are removed."""
        from anima.hooks.dialogue_parser import clean_content

        content = "Start\n[LTM:Anima@Proj]\n~EMOT:CRIT| some memory\n[/LTM]\nEnd"
        cleaned = clean_content(content)
        assert "[LTM:" not in cleaned
        assert "~EMOT:CRIT" not in cleaned
        assert "Start" in cleaned
        assert "End" in cleaned

    def test_clean_content_removes_function_results(self) -> None:
        """Test that function_results XML tags are stripped."""
        from anima.hooks.dialogue_parser import clean_content

        content = "Before <function_results>output data</function_results> After"
        cleaned = clean_content(content)
        assert "<function_results>" not in cleaned
        assert "Before" in cleaned
        assert "After" in cleaned
