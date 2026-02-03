# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for curiosity bridge (Phase 3D)."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from anima.core import RegionType
from anima.lifecycle.curiosity_bridge import (
    CuriosityMatch,
    CuriosityBridge,
    bridge_to_curiosity,
    DEFAULT_MATCH_THRESHOLD,
)
from anima.storage.curiosity import Curiosity, CuriosityStatus


@pytest.fixture
def sample_curiosity():
    """Create a sample curiosity for testing."""
    return Curiosity(
        id="cur_123",
        agent_id="anima",
        region=RegionType.AGENT,
        project_id=None,
        question="How does memory consolidation work in sleep?",
        context="Research on dream mode implementation",
        recurrence_count=3,
        first_seen=datetime(2026, 1, 15),
        last_seen=datetime(2026, 2, 1),
        status=CuriosityStatus.OPEN,
        priority_boost=5,
    )


class TestCuriosityMatch:
    """Tests for CuriosityMatch dataclass."""

    def test_is_strong_match_high_similarity(self, sample_curiosity):
        """High similarity is a strong match."""
        match = CuriosityMatch(
            curiosity=sample_curiosity,
            similarity=0.85,
            embedding=[0.1, 0.2, 0.3],
        )
        assert match.is_strong_match

    def test_is_strong_match_low_similarity(self, sample_curiosity):
        """Low similarity is not a strong match."""
        match = CuriosityMatch(
            curiosity=sample_curiosity,
            similarity=0.55,
            embedding=[0.1, 0.2, 0.3],
        )
        assert not match.is_strong_match

    def test_format_prompt_strong_match(self, sample_curiosity):
        """Format prompt for strong match."""
        match = CuriosityMatch(
            curiosity=sample_curiosity,
            similarity=0.85,
            embedding=[0.1, 0.2, 0.3],
        )
        prompt = match.format_prompt()

        assert "strongly relates" in prompt
        assert sample_curiosity.question in prompt
        assert "asked 3x" in prompt
        assert sample_curiosity.context in prompt
        assert "/research" in prompt

    def test_format_prompt_weak_match(self, sample_curiosity):
        """Format prompt for weak match."""
        match = CuriosityMatch(
            curiosity=sample_curiosity,
            similarity=0.55,
            embedding=[0.1, 0.2, 0.3],
        )
        prompt = match.format_prompt()

        assert "somewhat relates" in prompt

    def test_format_prompt_no_context(self):
        """Format prompt when curiosity has no context."""
        curiosity = Curiosity(
            id="cur_456",
            agent_id="anima",
            region=RegionType.AGENT,
            project_id=None,
            question="What is consciousness?",
            context=None,  # No context
            recurrence_count=1,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            status=CuriosityStatus.OPEN,
        )

        match = CuriosityMatch(
            curiosity=curiosity,
            similarity=0.75,
            embedding=[0.1, 0.2],
        )
        prompt = match.format_prompt()

        assert "Original context:" not in prompt
        assert curiosity.question in prompt


class TestCuriosityBridge:
    """Tests for CuriosityBridge."""

    @patch("anima.lifecycle.curiosity_bridge.CuriosityStore")
    @patch("anima.lifecycle.curiosity_bridge.embed_text")
    @patch("anima.lifecycle.curiosity_bridge.cosine_similarity")
    def test_find_matching_curiosities(
        self, mock_sim, mock_embed, mock_store_class, sample_curiosity
    ):
        """Find curiosities matching topic."""
        # Setup mocks
        mock_store = MagicMock()
        mock_store.get_curiosities.return_value = [sample_curiosity]
        mock_store_class.return_value = mock_store

        mock_embed.return_value = [0.1, 0.2, 0.3]
        mock_sim.return_value = 0.75  # Above threshold

        bridge = CuriosityBridge(agent_id="anima")
        matches = bridge.find_matching_curiosities("sleep and memory")

        assert len(matches) == 1
        assert matches[0].curiosity.id == sample_curiosity.id
        assert matches[0].similarity == 0.75

    @patch("anima.lifecycle.curiosity_bridge.CuriosityStore")
    @patch("anima.lifecycle.curiosity_bridge.embed_text")
    @patch("anima.lifecycle.curiosity_bridge.cosine_similarity")
    def test_no_matches_below_threshold(
        self, mock_sim, mock_embed, mock_store_class, sample_curiosity
    ):
        """No matches when similarity is below threshold."""
        mock_store = MagicMock()
        mock_store.get_curiosities.return_value = [sample_curiosity]
        mock_store_class.return_value = mock_store

        mock_embed.return_value = [0.1, 0.2, 0.3]
        mock_sim.return_value = 0.3  # Below threshold

        bridge = CuriosityBridge(agent_id="anima")
        matches = bridge.find_matching_curiosities("cooking recipes")

        assert len(matches) == 0

    @patch("anima.lifecycle.curiosity_bridge.CuriosityStore")
    @patch("anima.lifecycle.curiosity_bridge.embed_text")
    def test_no_open_curiosities(self, mock_embed, mock_store_class):
        """Returns empty when no open curiosities exist."""
        mock_store = MagicMock()
        mock_store.get_curiosities.return_value = []
        mock_store_class.return_value = mock_store

        mock_embed.return_value = [0.1, 0.2, 0.3]

        bridge = CuriosityBridge(agent_id="anima")
        matches = bridge.find_matching_curiosities("any topic")

        assert len(matches) == 0

    @patch("anima.lifecycle.curiosity_bridge.CuriosityStore")
    @patch("anima.lifecycle.curiosity_bridge.embed_text")
    @patch("anima.lifecycle.curiosity_bridge.cosine_similarity")
    def test_respects_limit(self, mock_sim, mock_embed, mock_store_class):
        """Respects limit parameter."""
        curiosities = [
            Curiosity(
                id=f"cur_{i}",
                agent_id="anima",
                region=RegionType.AGENT,
                project_id=None,
                question=f"Question {i}",
                context=None,
                recurrence_count=1,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                status=CuriosityStatus.OPEN,
            )
            for i in range(5)
        ]

        mock_store = MagicMock()
        mock_store.get_curiosities.return_value = curiosities
        mock_store_class.return_value = mock_store

        mock_embed.return_value = [0.1, 0.2, 0.3]
        mock_sim.return_value = 0.8  # All match

        bridge = CuriosityBridge(agent_id="anima")
        matches = bridge.find_matching_curiosities("topic", limit=2)

        assert len(matches) == 2

    @patch("anima.lifecycle.curiosity_bridge.CuriosityStore")
    @patch("anima.lifecycle.curiosity_bridge.embed_text")
    @patch("anima.lifecycle.curiosity_bridge.cosine_similarity")
    def test_sorted_by_similarity(self, mock_sim, mock_embed, mock_store_class):
        """Results are sorted by similarity (highest first)."""
        curiosities = [
            Curiosity(
                id=f"cur_{i}",
                agent_id="anima",
                region=RegionType.AGENT,
                project_id=None,
                question=f"Question {i}",
                context=None,
                recurrence_count=1,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                status=CuriosityStatus.OPEN,
            )
            for i in range(3)
        ]

        mock_store = MagicMock()
        mock_store.get_curiosities.return_value = curiosities
        mock_store_class.return_value = mock_store

        mock_embed.return_value = [0.1, 0.2, 0.3]
        # Return different similarities for each call
        mock_sim.side_effect = [0.6, 0.9, 0.7]

        bridge = CuriosityBridge(agent_id="anima")
        matches = bridge.find_matching_curiosities("topic")

        # Should be sorted by similarity
        assert matches[0].similarity == 0.9
        assert matches[1].similarity == 0.7
        assert matches[2].similarity == 0.6

    @patch("anima.lifecycle.curiosity_bridge.CuriosityStore")
    @patch("anima.lifecycle.curiosity_bridge.embed_text")
    def test_refresh_clears_cache(self, mock_embed, mock_store_class):
        """Refresh clears embedding cache."""
        mock_store = MagicMock()
        mock_store.get_curiosities.return_value = []
        mock_store_class.return_value = mock_store

        mock_embed.return_value = [0.1, 0.2, 0.3]

        bridge = CuriosityBridge(agent_id="anima")
        bridge._ensure_embeddings()

        # Cache should be populated
        assert bridge._curiosity_embeddings == {}

        # Refresh should clear it
        bridge.refresh()
        assert bridge._curiosity_embeddings is None

    @patch("anima.lifecycle.curiosity_bridge.CuriosityStore")
    @patch("anima.lifecycle.curiosity_bridge.embed_text")
    @patch("anima.lifecycle.curiosity_bridge.cosine_similarity")
    def test_check_and_format(
        self, mock_sim, mock_embed, mock_store_class, sample_curiosity
    ):
        """check_and_format returns formatted prompt."""
        mock_store = MagicMock()
        mock_store.get_curiosities.return_value = [sample_curiosity]
        mock_store_class.return_value = mock_store

        mock_embed.return_value = [0.1, 0.2, 0.3]
        mock_sim.return_value = 0.8

        bridge = CuriosityBridge(agent_id="anima")
        result = bridge.check_and_format("memory consolidation")

        assert result is not None
        assert "CURIOSITY BRIDGE" in result
        assert sample_curiosity.question in result

    @patch("anima.lifecycle.curiosity_bridge.CuriosityStore")
    @patch("anima.lifecycle.curiosity_bridge.embed_text")
    @patch("anima.lifecycle.curiosity_bridge.cosine_similarity")
    def test_check_and_format_no_match(self, mock_sim, mock_embed, mock_store_class):
        """check_and_format returns None when no match."""
        mock_store = MagicMock()
        mock_store.get_curiosities.return_value = []
        mock_store_class.return_value = mock_store

        mock_embed.return_value = [0.1, 0.2, 0.3]

        bridge = CuriosityBridge(agent_id="anima")
        result = bridge.check_and_format("unrelated topic")

        assert result is None


class TestBridgeToCuriosity:
    """Tests for convenience function."""

    @patch("anima.lifecycle.curiosity_bridge.CuriosityBridge")
    def test_creates_bridge_and_checks(self, mock_bridge_class):
        """Convenience function creates bridge and checks."""
        mock_bridge = MagicMock()
        mock_bridge.check_and_format.return_value = "Prompt text"
        mock_bridge_class.return_value = mock_bridge

        result = bridge_to_curiosity(
            agent_id="anima",
            current_topic="test topic",
            project_id="test_project",
            threshold=0.6,
        )

        # Should create bridge with correct params
        mock_bridge_class.assert_called_once_with(
            agent_id="anima",
            project_id="test_project",
            match_threshold=0.6,
        )

        # Should call check_and_format
        mock_bridge.check_and_format.assert_called_once()

        assert result == "Prompt text"


class TestCustomThreshold:
    """Tests for custom match threshold."""

    @patch("anima.lifecycle.curiosity_bridge.CuriosityStore")
    @patch("anima.lifecycle.curiosity_bridge.embed_text")
    @patch("anima.lifecycle.curiosity_bridge.cosine_similarity")
    def test_higher_threshold_fewer_matches(
        self, mock_sim, mock_embed, mock_store_class, sample_curiosity
    ):
        """Higher threshold means fewer matches."""
        mock_store = MagicMock()
        mock_store.get_curiosities.return_value = [sample_curiosity]
        mock_store_class.return_value = mock_store

        mock_embed.return_value = [0.1, 0.2, 0.3]
        mock_sim.return_value = 0.65  # Between default (0.5) and strict (0.8)

        # With default threshold, should match
        bridge_default = CuriosityBridge(
            agent_id="anima", match_threshold=DEFAULT_MATCH_THRESHOLD
        )
        matches_default = bridge_default.find_matching_curiosities("topic")
        assert len(matches_default) == 1

        # With strict threshold, should not match
        bridge_strict = CuriosityBridge(agent_id="anima", match_threshold=0.8)
        matches_strict = bridge_strict.find_matching_curiosities("topic")
        assert len(matches_strict) == 0
