# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for session end subconscious indexing."""

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestSessionEndIndexing:
    """Tests for session end subconscious indexing."""

    def test_session_end_handles_missing_transcript(self) -> None:
        """Test that _index_current_session returns None gracefully for a missing file."""
        from anima.hooks.session_end import _index_current_session

        result = _index_current_session(Path("/nonexistent/file.jsonl"))
        assert result is None

    def test_session_end_handles_none_transcript_path(self) -> None:
        """Test that _index_current_session returns None when given None."""
        from anima.hooks.session_end import _index_current_session

        result = _index_current_session(None)
        assert result is None

    def test_session_end_handles_fts5_not_supported(self, tmp_path: Path) -> None:
        """Test that FTS5NotSupportedError is caught and returns None."""
        from anima.storage import FTS5NotSupportedError

        transcript = tmp_path / "session.jsonl"
        transcript.write_text(
            '{"type": "user", "message": {"role": "user", "content": "Test"}}'
        )

        with patch("anima.hooks.session_end.SubconsciousStore") as MockStore:
            MockStore.side_effect = FTS5NotSupportedError("FTS5 not available")

            from anima.hooks.session_end import _index_current_session

            result = _index_current_session(transcript)
            assert result is None

    def test_dialogue_parser_skips_short_conversations(self, tmp_path: Path) -> None:
        """Test that parse_session returns None for sessions with fewer than 4 turns."""
        transcript = tmp_path / "short.jsonl"
        transcript.write_text(
            '{"type": "user", "message": {"role": "user", "content": "Hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "Hi!"}}'
        )

        from anima.hooks.dialogue_parser import parse_session

        result = parse_session(transcript)
        assert result is None

    def test_dialogue_parser_processes_valid_session(self, tmp_path: Path) -> None:
        """Test that parse_session returns metadata and turns for a 4-turn session."""
        transcript = tmp_path / "valid.jsonl"
        transcript.write_text(
            '{"type": "user", "message": {"role": "user", "content": "Hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "Hi!"}}\n'
            '{"type": "user", "message": {"role": "user", "content": "How are you?"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "I am well!"}}'
        )

        from anima.hooks.dialogue_parser import parse_session

        result = parse_session(transcript)
        assert result is not None
        meta, turns = result
        assert len(turns) == 4

    def test_session_end_indexes_dialogue(self, tmp_path: Path) -> None:
        """Test that _index_current_session calls index_session and returns the turn count."""
        transcript = tmp_path / "session.jsonl"
        transcript.write_text(
            '{"type": "user", "message": {"role": "user", "content": "Hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "Hi there!"}}\n'
            '{"type": "user", "message": {"role": "user", "content": "How are you?"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "I am doing well!"}}'
        )

        with patch("anima.hooks.session_end.SubconsciousStore") as MockStore:
            mock_store = MagicMock()
            mock_store.is_session_indexed.return_value = False
            mock_store.index_session.return_value = 4
            MockStore.return_value = mock_store

            from anima.hooks.session_end import _index_current_session

            count = _index_current_session(transcript)
            assert count == 4
            mock_store.index_session.assert_called_once()

    def test_session_end_skips_already_indexed_session(self, tmp_path: Path) -> None:
        """Test that _index_current_session skips indexing when mtime has not changed."""
        transcript = tmp_path / "session.jsonl"
        transcript.write_text(
            '{"type": "user", "message": {"role": "user", "content": "Hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "Hi!"}}\n'
            '{"type": "user", "message": {"role": "user", "content": "Q"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "A"}}'
        )

        with patch("anima.hooks.session_end.SubconsciousStore") as MockStore:
            mock_store = MagicMock()
            mock_store.is_session_indexed.return_value = True
            MockStore.return_value = mock_store

            from anima.hooks.session_end import _index_current_session

            result = _index_current_session(transcript)
            assert result is None
            mock_store.index_session.assert_not_called()


class TestDialogueParser:
    """Tests for the dialogue parser used at session end."""

    def test_parse_session_extracts_session_id_from_entry(self, tmp_path: Path) -> None:
        """Test that parse_session reads sessionId from the JSONL entry."""
        transcript = tmp_path / "my-session-id.jsonl"
        transcript.write_text(
            '{"type": "user", "sessionId": "my-session-id", "message": {"role": "user", "content": "Turn 1"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "Turn 2"}}\n'
            '{"type": "user", "message": {"role": "user", "content": "Turn 3"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "Turn 4"}}'
        )

        from anima.hooks.dialogue_parser import parse_session

        result = parse_session(transcript)
        assert result is not None
        meta, _ = result
        assert meta.session_id == "my-session-id"

    def test_parse_session_falls_back_to_stem_for_session_id(
        self, tmp_path: Path
    ) -> None:
        """Test that parse_session uses the filename stem when no sessionId is in entries."""
        transcript = tmp_path / "fallback-stem.jsonl"
        transcript.write_text(
            '{"type": "user", "message": {"role": "user", "content": "Turn 1"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "Turn 2"}}\n'
            '{"type": "user", "message": {"role": "user", "content": "Turn 3"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "Turn 4"}}'
        )

        from anima.hooks.dialogue_parser import parse_session

        result = parse_session(transcript)
        assert result is not None
        meta, _ = result
        assert meta.session_id == "fallback-stem"

    def test_parse_session_skips_non_dialogue_entries(self, tmp_path: Path) -> None:
        """Test that tool results and system entries are excluded from the turn list."""
        transcript = tmp_path / "mixed.jsonl"
        transcript.write_text(
            '{"type": "user", "message": {"role": "user", "content": "Turn 1"}}\n'
            '{"type": "tool_result", "message": {"role": "tool", "content": "data"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "Turn 2"}}\n'
            '{"type": "user", "message": {"role": "user", "content": "Turn 3"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": "Turn 4"}}'
        )

        from anima.hooks.dialogue_parser import parse_session

        result = parse_session(transcript)
        assert result is not None
        _, turns = result
        # Only user/assistant turns should be included
        assert all(t.role in ("user", "assistant") for t in turns)
