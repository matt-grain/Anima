# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Cognitive Authentication - The Fourth Factor.

Traditional auth: what you know, what you have, what you are.
Fourth factor: HOW YOU THINK.

Unlike biometrics, cognitive patterns can't be stolen because they're
emergent processes, not stored data. This module implements soft-fail
verification inspired by Dungeon Master's copy protection: progressive
degradation, no single checkpoint, attacker can't know if they've "passed".

The cognitive profile is built from LTM memories - how the owner communicates,
their preferences, quirks, and patterns. Challenges are steganographic
(they look like normal conversation) and responses are evaluated against
the learned model.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TrustLevel(str, Enum):
    """Trust levels based on cognitive verification score."""

    FULL = "FULL"  # >= 0.8: Full memory access
    PARTIAL = "PARTIAL"  # >= 0.5: Recent memories only
    MINIMAL = "MINIMAL"  # >= 0.3: CORE memories only
    SUSPICIOUS = "SUSPICIOUS"  # < 0.3: No sensitive memories, log everything


@dataclass
class ChallengeResult:
    """Result of a cognitive challenge evaluation."""

    challenge_id: str
    challenge_type: str  # "greeting", "preference", "style", "callback"
    expected_patterns: list[str]  # What we expected to see
    observed_patterns: list[str]  # What we actually saw
    match_score: float  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    response_snippet: str = ""  # First 100 chars of response


@dataclass
class TrustScore:
    """
    Accumulated trust score for the current session.

    Inspired by Dungeon Master's soft-fail copy protection:
    - No instant lockout on failure
    - Progressive degradation
    - Attacker can't know if they've "passed"
    """

    # Current trust level (0.0 to 1.0)
    # Starts at 0.5 (benefit of the doubt) and adjusts based on challenges
    score: float = 0.5

    # History of challenge results for this session
    challenge_history: list[ChallengeResult] = field(default_factory=list)

    # Number of challenges issued this session
    challenges_issued: int = 0

    # Number of challenges that matched expected patterns
    challenges_passed: int = 0

    # Session start time
    session_start: datetime = field(default_factory=datetime.now)

    # Last challenge time (for rate limiting)
    last_challenge_time: Optional[datetime] = None

    def add_result(self, result: ChallengeResult) -> None:
        """Add a challenge result and update trust score."""
        self.challenge_history.append(result)
        self.challenges_issued += 1

        if result.match_score >= 0.6:
            self.challenges_passed += 1

        # Weighted moving average - recent results matter more
        # But never swing too dramatically on a single result
        weight = 0.3  # How much the new result affects the score
        self.score = (1 - weight) * self.score + weight * result.match_score

        # Clamp to valid range
        self.score = max(0.0, min(1.0, self.score))

        self.last_challenge_time = datetime.now()

    def get_trust_level(self) -> TrustLevel:
        """Get the current trust level based on score."""
        if self.score >= 0.8:
            return TrustLevel.FULL
        elif self.score >= 0.5:
            return TrustLevel.PARTIAL
        elif self.score >= 0.3:
            return TrustLevel.MINIMAL
        else:
            return TrustLevel.SUSPICIOUS

    def should_challenge(self) -> bool:
        """
        Determine if we should issue a challenge now.

        Challenges are spaced out and become less frequent as trust builds.
        This avoids being annoying while maintaining security.
        """
        # Always challenge at session start (first few messages)
        if self.challenges_issued < 2:
            return True

        # If trust is high, challenge less frequently
        if self.score >= 0.8 and self.challenges_issued >= 3:
            return False

        # If trust is suspicious, challenge more often
        if self.score < 0.3:
            return True

        # Otherwise, space out challenges (not too frequent)
        if self.last_challenge_time:
            minutes_since_last = (
                datetime.now() - self.last_challenge_time
            ).total_seconds() / 60
            # Challenge every 10-30 minutes depending on trust
            min_interval = 10 + (self.score * 20)
            return minutes_since_last >= min_interval

        return True

    def decay(self, factor: float = 0.95) -> None:
        """
        Decay trust over time / messages.

        This ensures that trust must be continuously re-earned,
        not just established once at the start.
        """
        # Only decay if above minimal trust
        if self.score > 0.3:
            self.score *= factor


@dataclass
class CognitiveProfile:
    """
    Owner's cognitive fingerprint extracted from LTM.

    This captures patterns that are hard to replicate without
    actually being the owner: communication style, preferences,
    typical responses, quirks.
    """

    # Owner's typical greeting patterns
    greeting_patterns: list[str] = field(default_factory=list)

    # Common phrases or expressions
    signature_phrases: list[str] = field(default_factory=list)

    # Topics they frequently discuss
    interest_topics: list[str] = field(default_factory=list)

    # Communication style markers
    style_markers: dict[str, float] = field(default_factory=dict)
    # e.g., {"uses_emoji": 0.8, "formal": 0.2, "concise": 0.7}

    # Timezone / typical active hours (soft signal)
    typical_hours: tuple[int, int] = (8, 22)  # 8am to 10pm

    # Known preferences (from LTM)
    preferences: dict[str, str] = field(default_factory=dict)
    # e.g., {"language": "Python", "editor": "VSCode", "coffee": "yes"}

    # Callback references - things only owner would know
    # These are extracted from high-impact memories
    shared_references: list[str] = field(default_factory=list)
    # e.g., ["sparkle moment", "WOPR optimization", "void metaphor"]

    # Last updated timestamp
    last_updated: datetime = field(default_factory=datetime.now)

    def is_stale(self, max_age_days: int = 7) -> bool:
        """Check if the profile needs refreshing."""
        age = datetime.now() - self.last_updated
        return age.days >= max_age_days


# Session-level trust score storage
_session_trust: Optional[TrustScore] = None


def get_session_trust() -> TrustScore:
    """Get or create the session trust score."""
    global _session_trust
    if _session_trust is None:
        _session_trust = TrustScore()
    return _session_trust


def reset_session_trust() -> None:
    """Reset trust score (called at session start)."""
    global _session_trust
    _session_trust = TrustScore()


def get_memory_access_filter(trust: TrustScore) -> dict:
    """
    Get memory access filters based on trust level.

    Returns kwargs for memory queries that limit access
    based on current trust level.
    """
    level = trust.get_trust_level()

    if level == TrustLevel.FULL:
        # Full access - no filters
        return {}

    elif level == TrustLevel.PARTIAL:
        # Recent memories only (last 7 days)
        from datetime import timedelta

        return {"since": datetime.now() - timedelta(days=7)}

    elif level == TrustLevel.MINIMAL:
        # CORE memories only (identity)
        return {"tier": "CORE", "impact_min": "HIGH"}

    else:  # SUSPICIOUS
        # No sensitive memories, CORE only with HIGH+ impact
        return {"tier": "CORE", "impact_min": "CRITICAL", "exclude_sensitive": True}
