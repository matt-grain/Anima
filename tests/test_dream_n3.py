# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for N3 deep processing stage (Dream Mode Phase 2)."""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from anima.dream.types import DreamConfig, N3Result, GistResult, Contradiction
from anima.dream.n3_processing import (
    run_n3_processing,
    _needs_gist,
    _extract_gist,
    _detect_contradiction,
    _split_sentences,
)
from anima.core.types import ImpactLevel
from anima.storage.dissonance import DissonanceStore, DissonanceStatus


class TestGistResult:
    """Tests for GistResult dataclass."""

    def test_compression_ratio(self):
        """Compression ratio should be gist/original length."""
        result = GistResult(
            memory_id="test",
            original_length=1000,
            gist="Short summary.",
            gist_length=14,
        )
        assert result.compression_ratio == 0.014

    def test_compression_ratio_zero_original(self):
        """Handle zero-length original gracefully."""
        result = GistResult(
            memory_id="test",
            original_length=0,
            gist="",
            gist_length=0,
        )
        assert result.compression_ratio == 1.0


class TestNeedsGist:
    """Tests for gist necessity detection."""

    def test_critical_never_needs_gist(self):
        """CRITICAL memories should never be gisted."""
        memory = MagicMock()
        memory.impact = ImpactLevel.CRITICAL
        memory.content = "A" * 1000  # Long content

        assert _needs_gist(memory, DreamConfig()) is False

    def test_short_content_no_gist(self):
        """Short content doesn't need gist."""
        memory = MagicMock()
        memory.impact = ImpactLevel.MEDIUM
        memory.content = "Short content."

        assert _needs_gist(memory, DreamConfig()) is False

    def test_long_content_needs_gist(self):
        """Long non-CRITICAL content needs gist."""
        memory = MagicMock()
        memory.impact = ImpactLevel.MEDIUM
        memory.content = "A" * 500  # Long enough

        assert _needs_gist(memory, DreamConfig()) is True

    def test_medium_content_no_gist(self):
        """Content that would compress to similar size doesn't need gist."""
        memory = MagicMock()
        memory.impact = ImpactLevel.MEDIUM
        # Target gist is 50 tokens * 4 chars = 200 chars
        # Content <= 400 chars doesn't benefit from gisting
        memory.content = "A" * 300

        assert _needs_gist(memory, DreamConfig()) is False


class TestExtractGist:
    """Tests for gist extraction."""

    def test_first_sentence_included(self):
        """First sentence should always be in gist."""
        memory = MagicMock()
        memory.content = "This is the main point. Secondary info here. More details follow."

        gist = _extract_gist(memory, DreamConfig())

        assert gist is not None
        assert gist.startswith("This is the main point")

    def test_key_insights_included(self):
        """Sentences with key signals should be included."""
        memory = MagicMock()
        memory.content = (
            "Introduction sentence. "
            "Some filler content. "
            "Key insight: this is important. "
            "More filler."
        )

        gist = _extract_gist(memory, DreamConfig())

        assert gist is not None
        assert "Key insight" in gist

    def test_gist_ends_with_period(self):
        """Gist should end with a period."""
        memory = MagicMock()
        memory.content = "Single sentence without ending"

        gist = _extract_gist(memory, DreamConfig())

        assert gist is not None
        assert gist.endswith(".")


class TestSplitSentences:
    """Tests for sentence splitting."""

    def test_basic_split(self):
        """Should split on periods."""
        text = "First sentence. Second sentence. Third sentence."
        sentences = _split_sentences(text)

        assert len(sentences) == 3

    def test_handles_abbreviations(self):
        """Should not split on e.g. or i.e."""
        text = "Use e.g. when giving examples. This is correct."
        sentences = _split_sentences(text)

        assert len(sentences) == 2

    def test_handles_empty(self):
        """Should handle empty string."""
        assert _split_sentences("") == []


class TestDetectContradiction:
    """Tests for contradiction detection."""

    def test_negation_contradiction(self):
        """Should detect negation-based contradiction."""
        result = _detect_contradiction(
            "mem-1",
            "The system always works correctly.",
            "mem-2",
            "The system doesn't work correctly.",
            similarity=0.8,
        )

        assert result is not None
        assert "Negation" in result.description

    def test_opposite_absolutes(self):
        """Should detect opposite absolute words."""
        result = _detect_contradiction(
            "mem-1",
            "This always happens in production.",
            "mem-2",
            "This never happens in production.",
            similarity=0.75,
        )

        assert result is not None
        assert "always" in result.description or "never" in result.description

    def test_no_contradiction_similar_content(self):
        """Should not flag similar content without contradiction signals."""
        result = _detect_contradiction(
            "mem-1",
            "The sky is blue.",
            "mem-2",
            "The sky is azure.",
            similarity=0.8,
        )

        assert result is None

    def test_low_similarity_no_flag(self):
        """Should not flag low-similarity pairs even with negation."""
        result = _detect_contradiction(
            "mem-1",
            "Python is not compiled.",
            "mem-2",
            "The weather is nice.",
            similarity=0.5,  # Below threshold
        )

        assert result is None


class TestDissonanceStore:
    """Tests for dissonance queue storage."""

    def test_add_and_retrieve(self):
        """Should add and retrieve dissonances."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = DissonanceStore(db_path)

            dissonance = store.add_dissonance(
                agent_id="test-agent",
                memory_id_a="mem-1",
                memory_id_b="mem-2",
                description="Test contradiction",
            )

            retrieved = store.get_dissonance(dissonance.id)

            assert retrieved is not None
            assert retrieved.agent_id == "test-agent"
            assert retrieved.memory_id_a == "mem-1"
            assert retrieved.status == DissonanceStatus.OPEN

    def test_get_open_dissonances(self):
        """Should return only open dissonances."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = DissonanceStore(db_path)

            d1 = store.add_dissonance("agent", "m1", "m2", "desc1")
            d2 = store.add_dissonance("agent", "m3", "m4", "desc2")

            store.resolve_dissonance(d1.id, "resolved it")

            open_list = store.get_open_dissonances("agent")

            assert len(open_list) == 1
            assert open_list[0].id == d2.id

    def test_resolve_dissonance(self):
        """Should mark dissonance as resolved."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = DissonanceStore(db_path)

            d = store.add_dissonance("agent", "m1", "m2", "desc")
            store.resolve_dissonance(d.id, "The answer is X")

            retrieved = store.get_dissonance(d.id)

            assert retrieved is not None
            assert retrieved.status == DissonanceStatus.RESOLVED
            assert retrieved.resolution == "The answer is X"
            assert retrieved.resolved_at is not None

    def test_dismiss_dissonance(self):
        """Should mark dissonance as dismissed."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = DissonanceStore(db_path)

            d = store.add_dissonance("agent", "m1", "m2", "desc")
            store.dismiss_dissonance(d.id)

            retrieved = store.get_dissonance(d.id)

            assert retrieved is not None
            assert retrieved.status == DissonanceStatus.DISMISSED

    def test_exists_check(self):
        """Should detect existing dissonance pairs."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = DissonanceStore(db_path)

            store.add_dissonance("agent", "m1", "m2", "desc")

            # Both orderings should match
            assert store.exists("m1", "m2") is True
            assert store.exists("m2", "m1") is True
            assert store.exists("m1", "m3") is False

    def test_count_open(self):
        """Should count open dissonances."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = DissonanceStore(db_path)

            store.add_dissonance("agent", "m1", "m2", "desc1")
            store.add_dissonance("agent", "m3", "m4", "desc2")
            d3 = store.add_dissonance("agent", "m5", "m6", "desc3")
            store.dismiss_dissonance(d3.id)

            assert store.count_open("agent") == 2


class TestN3Processing:
    """Tests for the main N3 processing function."""

    def test_empty_memories_returns_zero_result(self):
        """Should handle empty memory set gracefully."""
        store = MagicMock()
        store.get_memories_for_agent.return_value = []
        store.get_memories_with_temporal_context.return_value = []

        result = run_n3_processing(
            store=store,
            agent_id="test-agent",
            quiet=True,
        )

        assert result.gists_created == 0
        assert result.contradictions_found == 0
        assert result.memories_processed == 0

    def test_result_structure(self):
        """N3Result should have correct structure."""
        result = N3Result(
            gists_created=3,
            gist_results=[
                GistResult("m1", 100, "gist1", 20),
            ],
            contradictions_found=1,
            contradictions=[
                Contradiction("m1", "m2", "c1", "c2", "desc", 0.8),
            ],
            dissonance_queue_additions=1,
            duration_seconds=1.5,
            memories_processed=10,
        )

        assert result.gists_created == 3
        assert len(result.gist_results) == 1
        assert result.contradictions_found == 1
        assert result.dissonance_queue_additions == 1


class TestN3CommandIntegration:
    """Tests for N3 integration with dream command."""

    def test_command_accepts_n3_stage(self):
        """Parser should accept --stage n3."""
        from anima.commands.dream import create_parser

        parser = create_parser()
        args = parser.parse_args(["--stage", "n3"])

        assert args.stage == "n3"
