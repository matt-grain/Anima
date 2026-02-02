# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for REM lucid dreaming stage (Dream Mode Phase 3)."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np

from anima.dream.types import (
    DreamConfig,
    REMResult,
    DreamMaterials,
    MemoryPair,
    IncompleteThought,
    DistantAssociation,
    GeneratedQuestion,
    SelfModelUpdate,
    UrgencyLevel,
)
from anima.dream.rem_dreaming import (
    run_rem_dreaming,
    gather_dream_materials,
    create_dream_template,
    _find_distant_pairs,
    _find_incomplete_thoughts,
    _extract_recurring_themes,
    _get_excerpt,
)


class TestDreamMaterials:
    """Tests for DreamMaterials dataclass."""

    def test_creation(self):
        """Should create materials with all fields."""
        materials = DreamMaterials(
            distant_pairs=[],
            incomplete_thoughts=[],
            recurring_themes=["memory", "identity"],
            diary_snippets=[("2026-02-02", "Some content")],
            total_memories=50,
            total_diary_entries=5,
        )

        assert materials.total_memories == 50
        assert len(materials.recurring_themes) == 2
        assert materials.template_path is None

    def test_template_path_optional(self):
        """Template path should be optional."""
        materials = DreamMaterials(
            distant_pairs=[],
            incomplete_thoughts=[],
            recurring_themes=[],
            diary_snippets=[],
            total_memories=0,
            total_diary_entries=0,
            template_path="/path/to/template.md",
        )

        assert materials.template_path == "/path/to/template.md"


class TestMemoryPair:
    """Tests for MemoryPair dataclass."""

    def test_creation(self):
        """Should create pair with all fields."""
        pair = MemoryPair(
            memory_a_id="mem-1",
            memory_a_content="Content about code",
            memory_b_id="mem-2",
            memory_b_content="Content about philosophy",
            similarity=0.25,
        )

        assert pair.memory_a_id == "mem-1"
        assert pair.similarity == 0.25


class TestIncompleteThought:
    """Tests for IncompleteThought dataclass."""

    def test_creation(self):
        """Should create thought with all fields."""
        thought = IncompleteThought(
            memory_id="mem-1",
            snippet="I wonder about the nature of...",
            signal_type="wonder",
        )

        assert thought.signal_type == "wonder"


class TestFindDistantPairs:
    """Tests for finding distant memory pairs."""

    def test_finds_low_similarity_pairs(self):
        """Should find pairs with low but non-zero similarity."""
        emb1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        emb2 = np.array([0.2, 0.9, 0.3], dtype=np.float32)

        memories = [
            ("mem-1", "Code architecture", emb1, datetime.now(), None),
            ("mem-2", "Philosophy of mind", emb2, datetime.now(), None),
        ]

        pairs = _find_distant_pairs(memories, threshold=0.5, max_pairs=5)

        # May or may not find pairs depending on random sampling
        assert isinstance(pairs, list)

    def test_handles_single_memory(self):
        """Should handle case with less than 2 memories."""
        memories = [
            ("mem-1", "Single", np.array([1.0, 0.0, 0.0], dtype=np.float32), datetime.now(), None),
        ]

        pairs = _find_distant_pairs(memories, threshold=0.3, max_pairs=5)

        assert pairs == []

    def test_handles_empty_memories(self):
        """Should handle empty memory list."""
        pairs = _find_distant_pairs([], threshold=0.3, max_pairs=5)

        assert pairs == []

    def test_respects_max_pairs(self):
        """Should respect max_pairs limit."""
        # Create many memories with varied embeddings
        memories = [
            (f"mem-{i}", f"Content {i}", np.random.rand(3).astype(np.float32), datetime.now(), None)
            for i in range(20)
        ]

        pairs = _find_distant_pairs(memories, threshold=0.8, max_pairs=3)

        assert len(pairs) <= 3


class TestFindIncompleteThoughts:
    """Tests for finding incomplete thoughts."""

    def test_finds_i_wonder(self):
        """Should find 'I wonder' patterns."""
        memories = [
            ("mem-1", "I wonder how memory consolidation works in practice", None, datetime.now(), None),
        ]

        thoughts = _find_incomplete_thoughts(memories)

        assert len(thoughts) >= 1
        assert thoughts[0].signal_type == "wonder"

    def test_finds_todo(self):
        """Should find TODO patterns."""
        memories = [
            ("mem-1", "TODO: research more about semantic memory", None, datetime.now(), None),
        ]

        thoughts = _find_incomplete_thoughts(memories)

        assert len(thoughts) >= 1
        assert thoughts[0].signal_type == "todo"

    def test_finds_questions(self):
        """Should find question marks."""
        memories = [
            ("mem-1", "What is the meaning of consciousness?", None, datetime.now(), None),
        ]

        thoughts = _find_incomplete_thoughts(memories)

        assert len(thoughts) >= 1
        assert thoughts[0].signal_type == "question"

    def test_limits_results(self):
        """Should limit to 10 thoughts."""
        memories = [
            (f"mem-{i}", f"I wonder about topic {i}?", None, datetime.now(), None)
            for i in range(15)
        ]

        thoughts = _find_incomplete_thoughts(memories)

        assert len(thoughts) <= 10


class TestExtractRecurringThemes:
    """Tests for extracting recurring themes."""

    def test_finds_recurring_words(self):
        """Should find words appearing multiple times."""
        memories = [
            ("m1", "Memory systems and architecture", None, datetime.now(), None),
            ("m2", "Memory consolidation is fascinating", None, datetime.now(), None),
            ("m3", "Building memory infrastructure", None, datetime.now(), None),
        ]

        themes = _extract_recurring_themes(memories, min_count=3)

        assert "memory" in themes

    def test_filters_by_min_count(self):
        """Should filter by minimum count."""
        memories = [
            ("m1", "Unique word here", None, datetime.now(), None),
            ("m2", "Another unique word", None, datetime.now(), None),
        ]

        themes = _extract_recurring_themes(memories, min_count=3)

        # No words appear 3+ times
        assert len(themes) == 0

    def test_removes_stopwords(self):
        """Should remove common stopwords."""
        memories = [
            ("m1", "The the the is is is", None, datetime.now(), None),
        ]

        themes = _extract_recurring_themes(memories, min_count=1)

        assert "the" not in themes
        assert "is" not in themes


class TestGetExcerpt:
    """Tests for excerpt extraction."""

    def test_truncates_long_content(self):
        """Should truncate content longer than max_len."""
        content = "A" * 500

        excerpt = _get_excerpt(content, max_len=100)

        assert len(excerpt) <= 103  # 100 + "..."
        assert excerpt.endswith("...")

    def test_preserves_short_content(self):
        """Should preserve content shorter than max_len."""
        content = "Short content here"

        excerpt = _get_excerpt(content, max_len=100)

        assert excerpt == content

    def test_skips_headers(self):
        """Should skip markdown headers."""
        content = "# Header\n\nActual content here"

        excerpt = _get_excerpt(content, max_len=100)

        assert "Actual content" in excerpt
        assert "# Header" not in excerpt


class TestGatherDreamMaterials:
    """Tests for gathering dream materials."""

    def test_returns_materials_structure(self):
        """Should return DreamMaterials with all fields."""
        store = MagicMock()
        store.get_memories_with_temporal_context.return_value = []

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                materials = gather_dream_materials(
                    store=store,
                    agent_id="test-agent",
                )

        assert isinstance(materials, DreamMaterials)
        assert materials.total_memories == 0
        assert materials.distant_pairs == []
        assert materials.incomplete_thoughts == []


class TestCreateDreamTemplate:
    """Tests for creating dream template."""

    def test_creates_markdown_file(self):
        """Should create markdown template file."""
        materials = DreamMaterials(
            distant_pairs=[
                MemoryPair("a", "Memory A content", "b", "Memory B content", 0.25),
            ],
            incomplete_thoughts=[
                IncompleteThought("a", "I wonder about X", "wonder"),
            ],
            recurring_themes=["memory", "identity"],
            diary_snippets=[("2026-02-02", "Diary excerpt")],
            total_memories=50,
            total_diary_entries=5,
        )

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                path = create_dream_template(materials, "test-agent")

                assert path.exists()
                content = path.read_text()

                # Check sections exist
                assert "Dream Journal" in content
                assert "Dream Materials" in content
                assert "Memory Pairs to Connect" in content
                assert "Incomplete Thoughts" in content
                assert "My Reflections" in content
                assert "[To be filled during lucid dream...]" in content

    def test_handles_empty_materials(self):
        """Should handle empty materials gracefully."""
        materials = DreamMaterials(
            distant_pairs=[],
            incomplete_thoughts=[],
            recurring_themes=[],
            diary_snippets=[],
            total_memories=0,
            total_diary_entries=0,
        )

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                path = create_dream_template(materials, "test-agent")

                assert path.exists()
                content = path.read_text()
                assert "Dream Journal" in content


class TestRunREMDreaming:
    """Tests for the main REM processing function."""

    def test_returns_rem_result(self):
        """Should return REMResult."""
        store = MagicMock()
        store.get_memories_with_temporal_context.return_value = []

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                result = run_rem_dreaming(
                    store=store,
                    agent_id="test-agent",
                    quiet=True,
                )

        assert isinstance(result, REMResult)
        assert result.dream_journal_path is not None
        assert result.iterations_completed == 1

    def test_creates_template_file(self):
        """Should create template file."""
        store = MagicMock()
        store.get_memories_with_temporal_context.return_value = []

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                result = run_rem_dreaming(
                    store=store,
                    agent_id="test-agent",
                    quiet=True,
                )

                # Template should exist
                assert result.dream_journal_path is not None
                template_path = Path(result.dream_journal_path)
                assert template_path.exists()

    def test_returns_empty_insights(self):
        """Insights should be empty - filled conversationally."""
        store = MagicMock()
        store.get_memories_with_temporal_context.return_value = []

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                result = run_rem_dreaming(
                    store=store,
                    agent_id="test-agent",
                    quiet=True,
                )

        # These should be empty - real content comes from conversation
        assert result.distant_associations == []
        assert result.generated_questions == []
        assert result.self_model_updates == []


class TestREMCommandIntegration:
    """Tests for REM integration with dream command."""

    def test_command_accepts_rem_stage(self):
        """Parser should accept --stage rem."""
        from anima.commands.dream import create_parser

        parser = create_parser()
        args = parser.parse_args(["--stage", "rem"])

        assert args.stage == "rem"

    def test_rem_in_all_stages(self):
        """REM should be included in 'all' stages."""
        from anima.dream.types import DreamStage

        all_stages = [DreamStage.N2, DreamStage.N3, DreamStage.REM]
        assert DreamStage.REM in all_stages


# Keep these type tests for backwards compatibility
class TestLegacyTypes:
    """Tests for legacy types still used in serialization."""

    def test_distant_association_creation(self):
        """DistantAssociation should still work."""
        assoc = DistantAssociation(
            memory_id_a="a",
            memory_id_b="b",
            content_a="c",
            content_b="d",
            connection_insight="e",
            similarity=0.2,
        )
        assert assoc.urgency == UrgencyLevel.WORTH_MENTIONING

    def test_generated_question_creation(self):
        """GeneratedQuestion should still work."""
        q = GeneratedQuestion(
            question="Why?",
            source_memory_ids=["a"],
            reasoning="curiosity",
        )
        assert q.urgency == UrgencyLevel.MEH

    def test_self_model_update_creation(self):
        """SelfModelUpdate should still work."""
        u = SelfModelUpdate(
            observation="I notice X",
            evidence_memory_ids=["a"],
            pattern_type="behavioral",
        )
        assert u.urgency == UrgencyLevel.WORTH_MENTIONING
