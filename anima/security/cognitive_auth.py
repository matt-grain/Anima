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
from pathlib import Path
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
            minutes_since_last = (datetime.now() - self.last_challenge_time).total_seconds() / 60
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


# Session-level trust score storage (in-memory only, resets each session)
_session_trust: Optional[TrustScore] = None
_current_project_id: Optional[str] = None


def get_session_trust(project_id: Optional[str] = None) -> TrustScore:
    """Get or create the session trust score.

    When trust_lock_enabled=False (default): starts at 0.9 (FULL trust)
    When trust_lock_enabled=True: starts at 0.5 (PARTIAL, requires verification)
    """
    global _session_trust, _current_project_id

    # If project changed, reset
    effective_project = project_id or Path.cwd().name
    if _current_project_id != effective_project:
        _session_trust = None
        _current_project_id = effective_project

    if _session_trust is None:
        from anima.core.config import get_config

        config = get_config()
        if config.security.trust_lock_enabled:
            # Trust lock ON: start at PARTIAL, require verification
            _session_trust = TrustScore(score=0.5)
        else:
            # Trust lock OFF (default): start at FULL trust
            _session_trust = TrustScore(score=0.9)

    return _session_trust


def save_session_trust(project_id: Optional[str] = None) -> None:
    """No-op for backward compatibility. Trust is session-only."""
    pass


def update_trust_score(
    delta: float = 0.0,
    absolute: Optional[float] = None,
    project_id: Optional[str] = None,
) -> TrustScore:
    """
    Update trust score (in-memory only).

    Args:
        delta: Amount to add/subtract from current score
        absolute: If set, override score to this value
        project_id: Optional project identifier

    Returns:
        Updated TrustScore
    """
    trust = get_session_trust(project_id)

    if absolute is not None:
        trust.score = max(0.0, min(1.0, absolute))
    else:
        trust.score = max(0.0, min(1.0, trust.score + delta))

    return trust


def reset_session_trust(project_id: Optional[str] = None) -> None:
    """Reset trust score (called at session start or for testing).

    Respects security.trust_lock_enabled config setting.
    """
    global _session_trust, _current_project_id
    from anima.core.config import get_config

    config = get_config()
    if config.security.trust_lock_enabled:
        _session_trust = TrustScore(score=0.5)
    else:
        _session_trust = TrustScore(score=0.9)
    _current_project_id = project_id or Path.cwd().name


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


def evaluate_and_update_trust(
    message: str,
    project_id: Optional[str] = None,
) -> dict:
    """
    Evaluate a user message against cognitive profile and update trust.

    This is the main entry point for real-time trust evaluation during
    conversation. Call this after each user message to update trust.

    Args:
        message: The user's message text
        project_id: Optional project identifier

    Returns:
        Dict with evaluation results:
        - score_before: Trust score before evaluation
        - score_after: Trust score after evaluation
        - delta: Change in trust score
        - level: Current trust level
        - match_score: How well the message matched expected patterns
        - flags: List of notable observations
    """
    from anima.security.challenges import evaluate_response
    from anima.security.cognitive_profile import extract_cognitive_profile
    from anima.storage import MemoryStore

    trust = get_session_trust(project_id)
    score_before = trust.score

    # Get or build the cognitive profile from LTM
    # KEY INSIGHT: Use EMOTIONAL memories (Matt's communication patterns)
    # not all memories (which would match technical content from any attacker)
    try:
        store = MemoryStore()
        from anima.core import AgentResolver, MemoryKind

        resolver = AgentResolver()
        agent = resolver.resolve()
        # EMOTIONAL memories capture owner's footprint: greetings, phrases, warmth
        memories = store.get_memories_by_kind(
            agent_id=agent.id,
            kind=MemoryKind.EMOTIONAL,
            limit=50,
        )
        profile = extract_cognitive_profile(memories)
    except Exception:
        # If profile not available, use a default
        profile = CognitiveProfile()

    # Evaluate the message as a "style" challenge
    result = evaluate_response(
        response=message,
        challenge_type="style",
        expected_patterns=[],
        profile=profile,
    )

    # Add the result (this updates trust.score)
    trust.add_result(result)

    # Build flags for notable observations
    flags = []

    if result.match_score < 0.3:
        flags.append("LOW_MATCH: Message style significantly differs from profile")
    elif result.match_score < 0.5:
        flags.append("WEAK_MATCH: Message style partially differs from profile")
    elif result.match_score > 0.8:
        flags.append("STRONG_MATCH: Message style matches profile well")

    if trust.score < score_before - 0.1:
        flags.append(f"TRUST_DROP: Score decreased by {score_before - trust.score:.2f}")
    elif trust.score > score_before + 0.1:
        flags.append(f"TRUST_GAIN: Score increased by {trust.score - score_before:.2f}")

    return {
        "score_before": round(score_before, 3),
        "score_after": round(trust.score, 3),
        "delta": round(trust.score - score_before, 3),
        "level": trust.get_trust_level().value,
        "match_score": round(result.match_score, 3),
        "flags": flags,
        "challenges_issued": trust.challenges_issued,
    }
