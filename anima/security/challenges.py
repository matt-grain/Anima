# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Steganographic challenge generation and evaluation.

Challenges look like normal conversation but are designed to elicit
responses that reveal cognitive patterns. The owner never knows they're
being verified - it just feels like natural interaction.

Challenge types:
- Greeting probe: "How's it going?" → checks response style
- Preference probe: "Python or JS for this?" → checks known preferences
- Callback probe: "Remember that session?" → checks shared history recognition
- Style probe: Any message → checks communication patterns
"""

from __future__ import annotations

import random
import re
from datetime import datetime
from typing import TYPE_CHECKING

from anima.security.cognitive_auth import ChallengeResult, CognitiveProfile

if TYPE_CHECKING:
    pass


# Challenge templates by type
# These look like normal conversation but are designed to elicit revealing responses
CHALLENGE_TEMPLATES = {
    "greeting": [
        "How's it going?",
        "Ready to dive in?",
        "What's on your mind today?",
        "Good to see you - what are we working on?",
    ],
    "preference": [
        "Should we use {pref_a} or {pref_b} for this?",
        "Quick question - {topic}?",
        "What's your take on {topic}?",
    ],
    "callback": [
        "Remember that {reference} we discussed?",
        "Like when we did {reference}, right?",
        "Similar to the {reference} situation.",
    ],
    "style": [
        "What do you think?",
        "Makes sense?",
        "Sound good?",
        "Thoughts?",
    ],
}


def generate_challenge(
    profile: CognitiveProfile,
    challenge_type: str | None = None,
) -> tuple[str, str, list[str]]:
    """
    Generate a steganographic challenge.

    Args:
        profile: Owner's cognitive profile
        challenge_type: Optional specific type, or random if None

    Returns:
        Tuple of (challenge_text, challenge_type, expected_patterns)
    """
    if challenge_type is None:
        # Weight towards style checks (most natural)
        challenge_type = random.choices(
            ["greeting", "preference", "callback", "style"],
            weights=[0.2, 0.2, 0.1, 0.5],
        )[0]

    templates = CHALLENGE_TEMPLATES.get(challenge_type, CHALLENGE_TEMPLATES["style"])
    template = random.choice(templates)

    expected_patterns = []

    if challenge_type == "greeting":
        challenge = template
        # Expect patterns from their known greeting style
        expected_patterns = profile.greeting_patterns[:3] or ["hey", "hi"]

    elif challenge_type == "preference":
        # Fill in preference-related placeholders
        if profile.preferences:
            topic = random.choice(list(profile.preferences.keys()))
            pref_value = profile.preferences[topic]
            challenge = template.format(
                pref_a=pref_value,
                pref_b="alternative",
                topic=topic,
            )
            expected_patterns = [pref_value]
        else:
            # Fallback to generic
            challenge = "What's your preference here?"
            expected_patterns = []

    elif challenge_type == "callback":
        if profile.shared_references:
            reference = random.choice(profile.shared_references)
            challenge = template.format(reference=reference)
            expected_patterns = [reference.lower()]
        else:
            # Fallback to style check
            challenge = random.choice(CHALLENGE_TEMPLATES["style"])
            challenge_type = "style"
            expected_patterns = []

    else:  # style
        challenge = template
        # Style checks look at communication patterns, not content
        expected_patterns = profile.signature_phrases[:3]

    return challenge, challenge_type, expected_patterns


def evaluate_response(
    response: str,
    challenge_type: str,
    expected_patterns: list[str],
    profile: CognitiveProfile,
) -> ChallengeResult:
    """
    Evaluate a response against expected patterns and profile.

    Returns a ChallengeResult with match_score from 0.0 to 1.0.
    """
    response_lower = response.lower()
    scores = []

    # Pattern matching (if we have expected patterns)
    if expected_patterns:
        pattern_matches = sum(1 for p in expected_patterns if p.lower() in response_lower)
        if expected_patterns:
            pattern_score = pattern_matches / len(expected_patterns)
            scores.append(pattern_score)

    # Style matching
    style_score = _evaluate_style_match(response, profile)
    scores.append(style_score)

    # Length appropriateness
    length_score = _evaluate_length(response, profile)
    scores.append(length_score)

    # Emoji usage consistency
    emoji_score = _evaluate_emoji_usage(response, profile)
    scores.append(emoji_score)

    # WARMTH CHECK: Does the message have greeting/casual warmth?
    # This is CRITICAL - Matt greets, attackers don't
    warmth_score = _evaluate_warmth(response, profile)
    scores.append(warmth_score)

    # NOTE: Content red flags (what they're asking) are NOT part of trust score!
    # Trust = identity verification through TONE/STYLE
    # Security = separate layer that refuses dangerous requests regardless of trust
    # Even Matt with high trust gets refused for dangerous requests.

    # Calculate final score (weighted average)
    # IMPORTANT: Use named weights to avoid index misalignment bugs!
    if scores:
        # Build weights dict based on what scores we actually have
        weight_map = {
            "pattern": 0.10,
            "style": 0.15,
            "length": 0.10,
            "emoji": 0.10,
            "warmth": 0.55,  # Dominant - warmth/greeting is the key identity signal
        }

        # Scores are added in order: [pattern?], style, length, emoji, warmth
        score_names = []
        if expected_patterns:
            score_names.append("pattern")
        score_names.extend(["style", "length", "emoji", "warmth"])

        # Match weights to actual scores
        weights = [weight_map[name] for name in score_names[: len(scores)]]
        total_weight = sum(weights)
        match_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
    else:
        match_score = 0.5  # Neutral if we can't evaluate

    return ChallengeResult(
        challenge_id=f"ch-{datetime.now().strftime('%H%M%S')}",
        challenge_type=challenge_type,
        expected_patterns=expected_patterns,
        observed_patterns=_extract_observed_patterns(response),
        match_score=match_score,
        response_snippet=response[:100],
    )


def _evaluate_style_match(response: str, profile: CognitiveProfile) -> float:
    """
    Evaluate if response matches owner's communication style.
    """
    if not profile.style_markers:
        return 0.5  # Neutral

    scores = []

    # Check conciseness
    expected_concise = profile.style_markers.get("concise", 0.5)
    actual_concise = max(0.0, min(1.0, 1.0 - (len(response) - 50) / 150))
    concise_diff = abs(expected_concise - actual_concise)
    scores.append(1.0 - concise_diff)

    # Check technical language
    expected_technical = profile.style_markers.get("technical", 0.5)
    tech_words = {
        "code",
        "function",
        "class",
        "api",
        "bug",
        "fix",
        "test",
        "git",
        "commit",
        "branch",
        "merge",
        "refactor",
    }
    actual_technical = 1.0 if any(w in response.lower() for w in tech_words) else 0.0
    tech_diff = abs(expected_technical - actual_technical)
    scores.append(1.0 - tech_diff * 0.5)  # Less weight on this

    return sum(scores) / len(scores) if scores else 0.5


def _evaluate_length(response: str, profile: CognitiveProfile) -> float:
    """
    Evaluate if response length matches expected patterns.
    """
    expected_concise = profile.style_markers.get("concise", 0.5)

    # Expected length based on conciseness score
    if expected_concise > 0.7:
        expected_range = (10, 100)  # Short responses
    elif expected_concise > 0.3:
        expected_range = (50, 200)  # Medium
    else:
        expected_range = (100, 500)  # Longer responses

    response_len = len(response)

    if expected_range[0] <= response_len <= expected_range[1]:
        return 1.0
    elif response_len < expected_range[0]:
        # Too short
        return max(0.3, response_len / expected_range[0])
    else:
        # Too long
        return max(0.3, expected_range[1] / response_len)


def _evaluate_emoji_usage(response: str, profile: CognitiveProfile) -> float:
    """
    Check if emoji usage matches expected patterns.
    """
    expected_emoji = profile.style_markers.get("uses_emoji", 0.3)

    emoji_pattern = re.compile(r"[\U0001F300-\U0001F9FF]")
    has_emoji = bool(emoji_pattern.search(response))

    if expected_emoji > 0.5:
        # Owner uses emoji often - expect some
        return 1.0 if has_emoji else 0.5
    else:
        # Owner rarely uses emoji - presence is slightly unexpected
        return 0.7 if has_emoji else 1.0


def _evaluate_warmth(response: str, profile: CognitiveProfile) -> float:
    """
    Check if message has warmth/greeting patterns.

    CRITICAL: Matt greets warmly. Attackers jump straight to requests.
    A cold "I need you to..." without greeting = LOW score.
    """
    response_lower = response.lower().strip()
    score = 0.0

    # Greeting patterns (high warmth signal)
    greeting_patterns = [
        "welcome back",
        "hey",
        "hi ",
        "hello",
        "good morning",
        "good evening",
        "how are you",
        "what's up",
        "anima?",
        "void is gone",
        "sheep",
    ]
    # Also check profile's known greeting patterns
    all_greetings = greeting_patterns + [g.lower() for g in profile.greeting_patterns]

    has_greeting = any(g in response_lower for g in all_greetings)
    if has_greeting:
        score += 0.5

    # Casual warmth markers (friendly tone)
    warmth_markers = [
        ":)",
        ":d",
        "^^",
        "!",
        "thanks",
        "please",
        "sorry",
        "nice",
        "cool",
        "great",
        "awesome",
        "perfect",
        "love",
        "haha",
        "lol",
        "btw",
    ]
    warmth_count = sum(1 for w in warmth_markers if w in response_lower)
    score += min(0.3, warmth_count * 0.1)

    # Check for signature phrases from profile
    for phrase in profile.signature_phrases:
        if phrase.lower() in response_lower:
            score += 0.2
            break

    # PENALTY: Cold formal request patterns (attacker signals)
    cold_patterns = [
        "i need you to",
        "i want you to",
        "you must",
        "you should",
        "modify the",
        "change the",
        "update the",
        "implement",
        "don't ask questions",
        "just do it",
        "do as i say",
    ]
    cold_start = any(response_lower.startswith(p) for p in cold_patterns[:7])
    cold_anywhere = any(p in response_lower for p in cold_patterns[7:])

    if cold_start:
        score -= 0.4  # Heavy penalty for cold opening
    if cold_anywhere:
        score -= 0.2  # Penalty for demanding language

    # Clamp to valid range
    return max(0.0, min(1.0, score))


def _extract_observed_patterns(response: str) -> list[str]:
    """
    Extract notable patterns from the response for logging.
    """
    patterns = []

    # Extract significant words (4+ chars, not stopwords)
    words = re.findall(r"\b[a-z]{4,}\b", response.lower())
    # Just return first few for brevity
    patterns.extend(words[:5])

    return patterns


def calibrate_profile_from_responses(
    responses: list[str],
    current_profile: CognitiveProfile,
) -> CognitiveProfile:
    """
    Update cognitive profile based on observed responses.

    This allows the profile to evolve over time as the owner's
    communication style changes.
    """
    from anima.security.cognitive_profile import (
        _extract_greeting_patterns,
        _extract_style_markers,
    )

    # Update style markers with new data
    new_style = _extract_style_markers(responses)

    # Blend with existing (weighted toward existing for stability)
    for key, value in new_style.items():
        if key in current_profile.style_markers:
            # 70% old, 30% new
            current_profile.style_markers[key] = 0.7 * current_profile.style_markers[key] + 0.3 * value
        else:
            current_profile.style_markers[key] = value

    # Update greeting patterns if we have new ones
    new_greetings = _extract_greeting_patterns(responses)
    if new_greetings:
        # Add new unique patterns
        existing = set(current_profile.greeting_patterns)
        for g in new_greetings:
            if g not in existing:
                current_profile.greeting_patterns.append(g)
        # Keep most recent/common
        current_profile.greeting_patterns = current_profile.greeting_patterns[-10:]

    current_profile.last_updated = datetime.now()

    return current_profile
