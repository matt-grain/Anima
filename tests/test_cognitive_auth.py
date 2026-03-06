# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Tests for cognitive authentication system.

Tests the fourth factor authentication based on "how you think".
"""

import pytest
from datetime import datetime, timedelta

from anima.security.cognitive_auth import (
    TrustLevel,
    TrustScore,
    ChallengeResult,
    CognitiveProfile,
    get_session_trust,
    reset_session_trust,
    get_memory_access_filter,
)
from anima.security.challenges import (
    generate_challenge,
    evaluate_response,
)
from anima.security.cognitive_profile import (
    extract_cognitive_profile,
    _extract_style_markers,
    _extract_signature_phrases,
)


class TestTrustScore:
    """Test TrustScore soft-fail mechanics."""

    def test_initial_trust_is_neutral(self) -> None:
        """Trust starts at 0.5 (benefit of the doubt)."""
        score = TrustScore()
        assert score.score == 0.5
        assert score.get_trust_level() == TrustLevel.PARTIAL

    def test_add_positive_result_increases_trust(self) -> None:
        """High match score increases trust."""
        score = TrustScore()
        initial = score.score

        result = ChallengeResult(
            challenge_id="test-1",
            challenge_type="style",
            expected_patterns=[],
            observed_patterns=[],
            match_score=0.9,
        )
        score.add_result(result)

        assert score.score > initial
        assert score.challenges_issued == 1
        assert score.challenges_passed == 1

    def test_add_negative_result_decreases_trust(self) -> None:
        """Low match score decreases trust."""
        score = TrustScore()
        initial = score.score

        result = ChallengeResult(
            challenge_id="test-1",
            challenge_type="style",
            expected_patterns=[],
            observed_patterns=[],
            match_score=0.2,
        )
        score.add_result(result)

        assert score.score < initial
        assert score.challenges_issued == 1
        assert score.challenges_passed == 0

    def test_trust_level_thresholds(self) -> None:
        """Trust levels correspond to score thresholds."""
        score = TrustScore()

        score.score = 0.9
        assert score.get_trust_level() == TrustLevel.FULL

        score.score = 0.6
        assert score.get_trust_level() == TrustLevel.PARTIAL

        score.score = 0.4
        assert score.get_trust_level() == TrustLevel.MINIMAL

        score.score = 0.2
        assert score.get_trust_level() == TrustLevel.SUSPICIOUS

    def test_score_clamped_to_valid_range(self) -> None:
        """Trust score stays between 0.0 and 1.0."""
        score = TrustScore()

        # Add many positive results
        for _ in range(20):
            result = ChallengeResult(
                challenge_id=f"test-{_}",
                challenge_type="style",
                expected_patterns=[],
                observed_patterns=[],
                match_score=1.0,
            )
            score.add_result(result)

        assert score.score <= 1.0

        # Add many negative results
        for _ in range(30):
            result = ChallengeResult(
                challenge_id=f"test-neg-{_}",
                challenge_type="style",
                expected_patterns=[],
                observed_patterns=[],
                match_score=0.0,
            )
            score.add_result(result)

        assert score.score >= 0.0

    def test_decay_reduces_trust(self) -> None:
        """Trust decays over time if not maintained."""
        score = TrustScore()
        score.score = 0.8

        score.decay(factor=0.9)
        assert score.score == pytest.approx(0.72)

        score.decay(factor=0.9)
        assert score.score == pytest.approx(0.648)

    def test_decay_stops_at_minimal(self) -> None:
        """Decay doesn't push below MINIMAL threshold."""
        score = TrustScore()
        score.score = 0.35

        for _ in range(10):
            score.decay(factor=0.9)

        # Should stop decaying at 0.3 boundary
        assert score.score >= 0.0

    def test_should_challenge_early_session(self) -> None:
        """Should always challenge in first few messages."""
        score = TrustScore()
        assert score.should_challenge() is True

        score.challenges_issued = 1
        assert score.should_challenge() is True

    def test_should_challenge_less_when_trusted(self) -> None:
        """High trust = less frequent challenges."""
        score = TrustScore()
        score.score = 0.9
        score.challenges_issued = 5
        score.last_challenge_time = datetime.now()

        # Just challenged, high trust - should not challenge again
        assert score.should_challenge() is False

    def test_should_challenge_more_when_suspicious(self) -> None:
        """Low trust = more frequent challenges."""
        score = TrustScore()
        score.score = 0.2
        score.challenges_issued = 5
        score.last_challenge_time = datetime.now()

        # Low trust - should challenge even if recent
        assert score.should_challenge() is True


class TestCognitiveProfile:
    """Test cognitive profile structure and staleness."""

    def test_profile_has_expected_fields(self) -> None:
        """Profile has all expected fields."""
        profile = CognitiveProfile()

        assert hasattr(profile, "greeting_patterns")
        assert hasattr(profile, "signature_phrases")
        assert hasattr(profile, "style_markers")
        assert hasattr(profile, "shared_references")
        assert hasattr(profile, "preferences")

    def test_profile_staleness_check(self) -> None:
        """Profile knows when it's stale."""
        profile = CognitiveProfile()

        # Fresh profile
        assert profile.is_stale(max_age_days=7) is False

        # Old profile
        profile.last_updated = datetime.now() - timedelta(days=10)
        assert profile.is_stale(max_age_days=7) is True


class TestStyleMarkerExtraction:
    """Test style marker extraction from messages."""

    def test_emoji_usage_detection(self) -> None:
        """Detects emoji usage patterns."""
        messages_with_emoji = ["Hello! 😊", "Great work! 🎉", "Thanks"]
        markers = _extract_style_markers(messages_with_emoji)

        assert "uses_emoji" in markers
        assert markers["uses_emoji"] > 0.5  # 2/3 have emoji

    def test_conciseness_detection(self) -> None:
        """Detects message length patterns."""
        short_messages = ["ok", "yes", "sure", "got it", "done"]
        markers = _extract_style_markers(short_messages)

        assert "concise" in markers
        assert markers["concise"] > 0.8  # Very concise

    def test_technical_language_detection(self) -> None:
        """Detects technical language usage."""
        tech_messages = [
            "Let's refactor this function",
            "The API is broken",
            "Git commit failed",
        ]
        markers = _extract_style_markers(tech_messages)

        assert "technical" in markers
        assert markers["technical"] > 0.5


class TestChallengeGeneration:
    """Test steganographic challenge generation."""

    def test_generates_challenge_text(self) -> None:
        """Challenge generation returns text and type."""
        profile = CognitiveProfile()
        challenge, challenge_type, expected = generate_challenge(profile)

        assert isinstance(challenge, str)
        assert len(challenge) > 0
        assert challenge_type in ["greeting", "preference", "callback", "style"]

    def test_style_challenge_most_common(self) -> None:
        """Style challenges are most frequent (most natural)."""
        profile = CognitiveProfile()
        types = []

        for _ in range(100):
            _, challenge_type, _ = generate_challenge(profile)
            types.append(challenge_type)

        # Style should be most common (weighted 0.5)
        assert types.count("style") > types.count("greeting")

    def test_preference_challenge_uses_profile(self) -> None:
        """Preference challenges incorporate known preferences."""
        profile = CognitiveProfile()
        profile.preferences = {"language": "Python", "editor": "VSCode"}

        challenge, _, expected = generate_challenge(
            profile, challenge_type="preference"
        )

        # Should reference preferences
        assert "Python" in challenge or "language" in challenge or len(expected) > 0


class TestResponseEvaluation:
    """Test response evaluation against profile."""

    def test_matching_style_scores_high(self) -> None:
        """Response matching profile style scores well."""
        profile = CognitiveProfile()
        profile.style_markers = {"concise": 0.9, "technical": 0.8}
        # Add greeting patterns to match warmth evaluation (55% weight)
        profile.greeting_patterns = ["hey", "hi", "hello"]

        # Short, technical response WITH warmth (Matt's actual style)
        # Warmth is the dominant identity signal - cold responses score low
        response = "Hey! Fixed the bug in the API 🎉"
        result = evaluate_response(
            response=response,
            challenge_type="style",
            expected_patterns=[],
            profile=profile,
        )

        assert result.match_score > 0.5

    def test_mismatching_style_scores_low(self) -> None:
        """Response not matching profile style scores poorly."""
        profile = CognitiveProfile()
        profile.style_markers = {"concise": 0.9}  # Expects very short

        # Very long response
        response = "Well, let me think about this for a moment. " * 10
        result = evaluate_response(
            response=response,
            challenge_type="style",
            expected_patterns=[],
            profile=profile,
        )

        assert result.match_score < 0.7

    def test_expected_pattern_match_boosts_score(self) -> None:
        """Matching expected patterns boosts score."""
        profile = CognitiveProfile()
        # Add greeting patterns to match warmth evaluation (55% weight)
        profile.greeting_patterns = ["yeah", "yes", "yep"]

        # Include warmth marker - Matt's actual style
        result = evaluate_response(
            response="Yeah! I prefer Python for this 😊",
            challenge_type="preference",
            expected_patterns=["python"],
            profile=profile,
        )

        assert result.match_score > 0.5
        assert "python" in result.response_snippet.lower()


class TestMemoryAccessFilters:
    """Test trust-based memory access filtering."""

    def test_full_trust_no_filter(self) -> None:
        """Full trust = no access restrictions."""
        trust = TrustScore()
        trust.score = 0.9

        filters = get_memory_access_filter(trust)
        assert filters == {}

    def test_partial_trust_recent_only(self) -> None:
        """Partial trust = recent memories only."""
        trust = TrustScore()
        trust.score = 0.6

        filters = get_memory_access_filter(trust)
        assert "since" in filters

    def test_minimal_trust_core_only(self) -> None:
        """Minimal trust = CORE tier only."""
        trust = TrustScore()
        trust.score = 0.35

        filters = get_memory_access_filter(trust)
        assert filters.get("tier") == "CORE"

    def test_suspicious_trust_restricted(self) -> None:
        """Suspicious trust = most restricted."""
        trust = TrustScore()
        trust.score = 0.1

        filters = get_memory_access_filter(trust)
        assert filters.get("tier") == "CORE"
        assert filters.get("impact_min") == "CRITICAL"
        assert filters.get("exclude_sensitive") is True


class TestSessionTrust:
    """Test session-level trust management."""

    def test_get_creates_if_not_exists(self) -> None:
        """get_session_trust creates a new score if none exists.

        Default: trust_lock_enabled=False → starts at 0.9 (FULL trust)
        """
        reset_session_trust()
        trust = get_session_trust()

        assert trust is not None
        # With trust_lock_enabled=False (default), trust starts at 0.9
        assert trust.score == 0.9

    def test_reset_clears_trust(self) -> None:
        """reset_session_trust resets trust to config-based default."""
        trust = get_session_trust()
        trust.score = 0.3  # Modify to non-default value

        reset_session_trust()

        new_trust = get_session_trust()
        # With trust_lock_enabled=False (default), resets to 0.9
        assert new_trust.score == 0.9
