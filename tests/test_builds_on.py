# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for BUILDS_ON link detection (Phase 3: Evolutionary Links)."""

import pytest
from datetime import datetime, timedelta

from anima.graph.linker import (
    has_builds_on_pattern,
    suggest_link_type,
    find_builds_on_candidates,
    LinkType,
)


class TestBuildsOnPatterns:
    """Tests for BUILDS_ON pattern detection."""

    def test_direct_reference_as_i_mentioned(self):
        """Should detect 'as I mentioned' pattern."""
        assert has_builds_on_pattern("As I mentioned earlier, this is important")
        assert has_builds_on_pattern("as we discussed, the architecture should change")

    def test_direct_reference_building_on(self):
        """Should detect 'building on' pattern."""
        assert has_builds_on_pattern("Building on our previous discussion")
        assert has_builds_on_pattern("building on what we learned")

    def test_update_marker(self):
        """Should detect Update/Correction markers."""
        assert has_builds_on_pattern("Update: The API endpoint has changed")
        assert has_builds_on_pattern("Correction: The previous approach was wrong")
        assert has_builds_on_pattern("Evolution: My thinking has shifted")

    def test_continuation_markers(self):
        """Should detect continuation patterns."""
        assert has_builds_on_pattern("Furthermore, we should consider...")
        assert has_builds_on_pattern("Moreover, the tests revealed...")
        assert has_builds_on_pattern("This builds on the earlier implementation")

    def test_no_pattern(self):
        """Should return False for content without patterns."""
        assert not has_builds_on_pattern("The sky is blue")
        assert not has_builds_on_pattern("Implemented the new feature")
        assert not has_builds_on_pattern("Python is a programming language")


class TestSuggestLinkType:
    """Tests for link type suggestion."""

    def test_reference_pattern_triggers_builds_on(self):
        """Content with reference pattern should suggest BUILDS_ON."""
        result = suggest_link_type(
            source_content="As I mentioned, this is the fix",
            target_content="The bug exists in module X",
            similarity=0.5,
        )
        assert result == LinkType.BUILDS_ON

    def test_same_session_high_similarity_builds_on(self):
        """Same session + high similarity should suggest BUILDS_ON."""
        result = suggest_link_type(
            source_content="The implementation is complete",
            target_content="Starting the implementation now",
            similarity=0.7,
            same_session=True,
        )
        assert result == LinkType.BUILDS_ON

    def test_temporal_ordering_high_similarity_builds_on(self):
        """Newer memory + very high similarity should suggest BUILDS_ON."""
        result = suggest_link_type(
            source_content="Finalized the architecture design",
            target_content="Initial architecture thoughts",
            similarity=0.75,
            source_created=datetime(2026, 1, 30, 12, 0),
            target_created=datetime(2026, 1, 30, 10, 0),
        )
        assert result == LinkType.BUILDS_ON

    def test_default_relates_to(self):
        """Without special signals, should default to RELATES_TO."""
        result = suggest_link_type(
            source_content="Python is great",
            target_content="I like coding",
            similarity=0.5,
        )
        assert result == LinkType.RELATES_TO


class TestFindBuildsOnCandidates:
    """Tests for finding BUILDS_ON candidates."""

    def test_finds_same_session_candidates(self):
        """Should prioritize candidates from the same session."""
        now = datetime.now()
        earlier = now - timedelta(hours=1)

        candidates = find_builds_on_candidates(
            source_content="Building on the earlier discussion",
            source_embedding=[0.5] * 384,
            source_session_id="session-1",
            source_created=now,
            candidate_memories=[
                ("mem-1", "Earlier discussion content", [0.5] * 384, earlier, "session-1"),
            ],
            similarity_threshold=0.3,
        )

        assert len(candidates) == 1
        assert candidates[0].memory_id == "mem-1"
        assert candidates[0].confidence > 0.5  # High confidence due to same session + pattern

    def test_excludes_future_memories(self):
        """Should not include memories newer than source."""
        now = datetime.now()
        future = now + timedelta(hours=1)

        candidates = find_builds_on_candidates(
            source_content="Current thought",
            source_embedding=[0.5] * 384,
            source_session_id="session-1",
            source_created=now,
            candidate_memories=[
                ("mem-1", "Future memory", [0.5] * 384, future, "session-1"),
            ],
            similarity_threshold=0.3,
        )

        assert len(candidates) == 0

    def test_excludes_outside_time_window(self):
        """Should not include memories outside the time window."""
        now = datetime.now()
        old = now - timedelta(hours=100)  # Way outside 48h window

        candidates = find_builds_on_candidates(
            source_content="Current thought",
            source_embedding=[0.5] * 384,
            source_session_id="session-1",
            source_created=now,
            candidate_memories=[
                ("mem-1", "Old memory", [0.5] * 384, old, "session-2"),
            ],
            similarity_threshold=0.3,
            time_window_hours=48,
        )

        assert len(candidates) == 0

    def test_reference_pattern_boosts_confidence(self):
        """Source with reference pattern should have higher confidence."""
        now = datetime.now()
        earlier = now - timedelta(hours=2)

        with_pattern = find_builds_on_candidates(
            source_content="As I mentioned earlier, this is important",
            source_embedding=[0.5] * 384,
            source_session_id="session-1",
            source_created=now,
            candidate_memories=[
                ("mem-1", "Earlier thought", [0.5] * 384, earlier, "session-2"),
            ],
            similarity_threshold=0.3,
        )

        without_pattern = find_builds_on_candidates(
            source_content="This is a new thought",
            source_embedding=[0.5] * 384,
            source_session_id="session-1",
            source_created=now,
            candidate_memories=[
                ("mem-1", "Earlier thought", [0.5] * 384, earlier, "session-2"),
            ],
            similarity_threshold=0.3,
        )

        # Pattern version should have higher confidence (or exist at all)
        assert len(with_pattern) >= len(without_pattern)
        if len(with_pattern) > 0 and len(without_pattern) > 0:
            assert with_pattern[0].confidence > without_pattern[0].confidence

    def test_respects_max_candidates(self):
        """Should not return more than max_candidates."""
        now = datetime.now()

        # Create 5 candidate memories
        memories = [
            (f"mem-{i}", "Content", [0.5] * 384, now - timedelta(hours=i + 1), f"session-{i}")
            for i in range(5)
        ]

        candidates = find_builds_on_candidates(
            source_content="Building on earlier work",
            source_embedding=[0.5] * 384,
            source_session_id="session-new",
            source_created=now,
            candidate_memories=memories,
            similarity_threshold=0.3,
            max_candidates=2,
        )

        assert len(candidates) <= 2


class TestLinkTypeIntegration:
    """Integration tests for link type detection."""

    def test_evolutionary_chain_detection(self):
        """Should detect a chain of related thoughts building on each other."""
        base_time = datetime(2026, 1, 30, 10, 0, 0)

        # Simulate a chain of thoughts
        thought1_time = base_time
        thought2_time = base_time + timedelta(hours=1)
        thought3_time = base_time + timedelta(hours=2)

        # Thought 2 builds on thought 1
        type_2_1 = suggest_link_type(
            source_content="Building on my initial observation, the pattern is clear",
            target_content="I noticed an interesting pattern in the code",
            similarity=0.7,
            source_created=thought2_time,
            target_created=thought1_time,
            same_session=True,
        )
        assert type_2_1 == LinkType.BUILDS_ON

        # Thought 3 builds on thought 2
        type_3_2 = suggest_link_type(
            source_content="Update: The pattern leads to a specific architecture",
            target_content="Building on my initial observation, the pattern is clear",
            similarity=0.65,
            source_created=thought3_time,
            target_created=thought2_time,
            same_session=True,
        )
        assert type_3_2 == LinkType.BUILDS_ON
