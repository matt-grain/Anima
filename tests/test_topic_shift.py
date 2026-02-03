# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for topic shift detection (Phase 3C)."""

import pytest
from unittest.mock import patch, MagicMock

from anima.lifecycle.topic_shift import (
    TopicShift,
    TopicTracker,
    extract_topic_keywords,
    DEFAULT_SHIFT_THRESHOLD,
)


class TestTopicShift:
    """Tests for TopicShift dataclass."""

    def test_is_significant_no_previous(self):
        """First message is never a shift."""
        shift = TopicShift(
            current_topic="Hello",
            current_embedding=[0.1, 0.2, 0.3],
            previous_topic=None,
            previous_embedding=None,
            similarity=1.0,
        )
        assert not shift.is_significant

    def test_is_significant_same_topic(self):
        """Same topic (high similarity) is not significant."""
        shift = TopicShift(
            current_topic="Python coding",
            current_embedding=[0.1, 0.2, 0.3],
            previous_topic="Python programming",
            previous_embedding=[0.1, 0.2, 0.3],
            similarity=0.95,  # Very similar
            threshold=DEFAULT_SHIFT_THRESHOLD,
        )
        assert not shift.is_significant

    def test_is_significant_different_topic(self):
        """Different topic (low similarity) is significant."""
        shift = TopicShift(
            current_topic="Let's talk about cooking",
            current_embedding=[0.9, 0.8, 0.7],
            previous_topic="Python programming",
            previous_embedding=[0.1, 0.2, 0.3],
            similarity=0.3,  # Very different
            threshold=DEFAULT_SHIFT_THRESHOLD,
        )
        assert shift.is_significant

    def test_shift_magnitude(self):
        """Shift magnitude is inverse of similarity."""
        shift = TopicShift(
            current_topic="Topic A",
            current_embedding=[0.1, 0.2],
            similarity=0.7,
        )
        assert shift.shift_magnitude == pytest.approx(0.3)

    def test_custom_threshold(self):
        """Custom threshold is respected."""
        # With default threshold (0.6), this is not significant
        shift_default = TopicShift(
            current_topic="A",
            current_embedding=[0.1],
            previous_topic="B",
            previous_embedding=[0.2],
            similarity=0.65,
            threshold=DEFAULT_SHIFT_THRESHOLD,
        )
        assert not shift_default.is_significant

        # With higher threshold (0.8), this IS significant
        shift_strict = TopicShift(
            current_topic="A",
            current_embedding=[0.1],
            previous_topic="B",
            previous_embedding=[0.2],
            similarity=0.65,
            threshold=0.8,
        )
        assert shift_strict.is_significant


class TestTopicTracker:
    """Tests for TopicTracker."""

    @patch("anima.lifecycle.topic_shift.embed_text")
    def test_first_message_no_shift(self, mock_embed):
        """First message is never a shift."""
        mock_embed.return_value = [0.1, 0.2, 0.3]

        tracker = TopicTracker()
        shift = tracker.detect_shift("Hello world")

        assert not shift.is_significant
        assert shift.previous_topic is None
        assert shift.current_topic == "Hello world"

    @patch("anima.lifecycle.topic_shift.embed_text")
    @patch("anima.lifecycle.topic_shift.cosine_similarity")
    def test_similar_topics_no_shift(self, mock_sim, mock_embed):
        """Similar consecutive topics don't trigger shift."""
        mock_embed.return_value = [0.1, 0.2, 0.3]
        mock_sim.return_value = 0.9  # Very similar

        tracker = TopicTracker()
        tracker.detect_shift("Python programming")
        shift = tracker.detect_shift("Python coding tips")

        assert not shift.is_significant
        assert shift.similarity == 0.9

    @patch("anima.lifecycle.topic_shift.embed_text")
    @patch("anima.lifecycle.topic_shift.cosine_similarity")
    def test_different_topics_trigger_shift(self, mock_sim, mock_embed):
        """Different consecutive topics trigger shift."""
        mock_embed.return_value = [0.1, 0.2, 0.3]
        mock_sim.return_value = 0.3  # Very different

        tracker = TopicTracker()
        tracker.detect_shift("Python programming")
        shift = tracker.detect_shift("What's for dinner?")

        assert shift.is_significant
        assert shift.similarity == 0.3

    @patch("anima.lifecycle.topic_shift.embed_text")
    def test_reset_clears_state(self, mock_embed):
        """Reset clears previous topic."""
        mock_embed.return_value = [0.1, 0.2, 0.3]

        tracker = TopicTracker()
        tracker.detect_shift("Topic 1")
        tracker.reset()
        shift = tracker.detect_shift("Topic 2")

        # After reset, this is like first message
        assert not shift.is_significant
        assert shift.previous_topic is None

    @patch("anima.lifecycle.topic_shift.embed_text")
    def test_set_topic_initializes(self, mock_embed):
        """Set topic initializes without detecting shift."""
        mock_embed.return_value = [0.1, 0.2, 0.3]

        tracker = TopicTracker()
        tracker.set_topic("Initial context")

        assert tracker._previous_topic == "Initial context"
        assert tracker._previous_embedding == [0.1, 0.2, 0.3]

    def test_custom_threshold(self):
        """Custom threshold is applied."""
        tracker = TopicTracker(shift_threshold=0.9)
        assert tracker.shift_threshold == 0.9


class TestExtractTopicKeywords:
    """Tests for keyword extraction."""

    def test_removes_stopwords(self):
        """Stopwords are removed."""
        result = extract_topic_keywords("the quick brown fox")
        assert "the" not in result
        assert "quick" in result
        assert "brown" in result
        assert "fox" in result

    def test_respects_max_words(self):
        """Max words limit is respected."""
        result = extract_topic_keywords(
            "one two three four five six seven eight nine ten eleven",
            max_words=5,
        )
        words = result.split()
        assert len(words) <= 5

    def test_handles_punctuation(self):
        """Punctuation is stripped."""
        result = extract_topic_keywords("Hello, world! How are you?")
        assert "hello" in result.lower()
        assert "world" in result.lower()
        # Punctuation should be stripped
        assert "," not in result
        assert "!" not in result
        assert "?" not in result

    def test_empty_input(self):
        """Empty input returns empty string."""
        result = extract_topic_keywords("")
        assert result == ""

    def test_only_stopwords(self):
        """Input with only stopwords returns empty."""
        result = extract_topic_keywords("the a an is are")
        assert result == ""


class TestGetRelatedMemories:
    """Tests for TopicShift.get_related_memories."""

    @patch("anima.lifecycle.topic_shift.find_similar")
    def test_returns_memories(self, mock_find_similar):
        """Returns memories matching the topic."""
        # Setup mock store
        mock_store = MagicMock()
        mock_store.get_memories_with_embeddings.return_value = [
            ("mem1", "Memory about Python", [0.1, 0.2, 0.3]),
            ("mem2", "Memory about cooking", [0.9, 0.8, 0.7]),
        ]

        mock_memory = MagicMock()
        mock_memory.id = "mem1"
        mock_store.get_memories_for_agent.return_value = [mock_memory]

        # Setup mock similarity results
        mock_result = MagicMock()
        mock_result.item = "mem1"
        mock_find_similar.return_value = [mock_result]

        shift = TopicShift(
            current_topic="Python programming",
            current_embedding=[0.1, 0.2, 0.3],
        )

        memories = shift.get_related_memories(
            store=mock_store,
            agent_id="test_agent",
            project_id="test_project",
        )

        assert len(memories) == 1
        assert memories[0].id == "mem1"

    def test_returns_empty_when_no_embeddings(self):
        """Returns empty when no embedded memories exist."""
        mock_store = MagicMock()
        mock_store.get_memories_with_embeddings.return_value = []

        shift = TopicShift(
            current_topic="Python programming",
            current_embedding=[0.1, 0.2, 0.3],
        )

        memories = shift.get_related_memories(
            store=mock_store,
            agent_id="test_agent",
        )

        assert memories == []
