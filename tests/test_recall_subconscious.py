# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for recall command subconscious features."""

from pathlib import Path

import pytest

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

    def test_recall_conscious_flag_searches_memories_db(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that --conscious flag (default) searches memories.db without error."""
        from anima.commands.recall import run

        exit_code = run(["--conscious", "nonexistent_query_xyz"])
        assert exit_code == 0

    def test_recall_social_cue_triggers_subconscious_search(self) -> None:
        """Test that 'do you remember when...' social cue triggers subconscious search."""
        from anima.lifecycle.social_cues import (
            detect_social_cue,
            should_search_subconscious,
        )

        cue = detect_social_cue("do you remember when we discussed caching?")
        assert cue is not None
        assert should_search_subconscious(cue) is True

    def test_recall_explicit_recall_patterns_trigger_subconscious(self) -> None:
        """Test that all explicit recall patterns trigger subconscious search."""
        from anima.lifecycle.social_cues import (
            detect_social_cue,
            should_search_subconscious,
        )

        patterns = [
            "do you remember when we talked about authentication?",
            "remember when we added the caching layer?",
            "do you recall the conversation about testing?",
        ]
        for pattern in patterns:
            cue = detect_social_cue(pattern)
            assert cue is not None, f"Failed to detect cue in: {pattern}"
            assert should_search_subconscious(cue) is True, (
                f"Expected subconscious trigger for: {pattern}"
            )

    def test_regular_queries_dont_trigger_subconscious(self) -> None:
        """Test that regular technical questions do not auto-trigger subconscious search."""
        from anima.lifecycle.social_cues import (
            detect_social_cue,
            should_search_subconscious,
        )

        cue = detect_social_cue("how do I implement caching?")
        if cue:
            assert should_search_subconscious(cue) is False

    def test_shared_discussion_cue_triggers_subconscious(self) -> None:
        """Test that shared discussion cues (we discussed X) trigger subconscious search."""
        from anima.lifecycle.social_cues import (
            detect_social_cue,
            should_search_subconscious,
        )

        cue = detect_social_cue("we discussed the architecture yesterday")
        assert cue is not None
        assert should_search_subconscious(cue) is True

    def test_agent_statement_cue_does_not_trigger_subconscious(self) -> None:
        """Test that agent statement cues (you mentioned X) do not trigger subconscious search."""
        from anima.lifecycle.social_cues import (
            detect_social_cue,
            should_search_subconscious,
        )

        cue = detect_social_cue("you mentioned the caching approach")
        assert cue is not None
        # AGENT_STATEMENT is not in the subconscious trigger set
        assert should_search_subconscious(cue) is False

    def test_subconscious_search_returns_zero_on_no_matches(
        self, tmp_path: Path
    ) -> None:
        """Test that subconscious search returns 0 exit code when no results found."""
        from unittest.mock import patch
        from anima.commands.recall import subconscious_search

        with patch("anima.commands.recall.SubconsciousStore") as MockStore:
            mock_store = MockStore.return_value
            mock_store.search.return_value = []

            result = subconscious_search(
                "totally_absent_term", project_id=None, show_full=False
            )
            assert result == 0
