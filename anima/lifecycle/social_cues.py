# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Social Cue Detection - Recognizing shared knowledge references.

Social cues are conversational patterns where the user references shared
knowledge, past discussions, or collaborative decisions. These are different
from temporal cues (which reference time) - social cues reference the
relationship and shared context.

Examples:
- "remember when we discussed caching?"
- "you mentioned something about API design"
- "as we agreed, the auth should use JWT"
- "like you said earlier about testing"

When detected, these cues trigger memory recall to provide continuity.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class SocialCueType(Enum):
    """Types of social cues that reference shared knowledge."""

    SHARED_DISCUSSION = auto()  # "we discussed", "we talked about"
    AGENT_STATEMENT = auto()  # "you mentioned", "you said"
    SHARED_DECISION = auto()  # "we agreed", "we decided"
    COLLABORATIVE_WORK = auto()  # "we built", "we implemented"
    SHARED_KNOWLEDGE = auto()  # "we know that", "as we understand"
    EXPLICIT_RECALL = auto()  # "remember when", "do you recall"


@dataclass
class SocialCue:
    """
    A detected social cue with context for memory recall.

    The topic field contains the subject being referenced, which can be
    used as a semantic search query to find related memories.
    """

    cue_type: SocialCueType
    original_text: str  # The matched text
    topic: Optional[str] = None  # Extracted topic for semantic search
    is_question: bool = False  # Whether this is a question about past context


# Patterns for detecting social cues
# Format: (pattern, cue_type, topic_group_index)
# topic_group_index is which regex group contains the topic (0 = no topic)
SOCIAL_PATTERNS: list[tuple[str, SocialCueType, int]] = [
    # Shared discussion patterns
    (
        r"as\s+we\s+discussed\s*,\s*(.+?)(?:\.|$)",
        SocialCueType.SHARED_DISCUSSION,
        1,
    ),
    (
        r"we\s+(?:discussed|talked\s+about|mentioned)\s+(\w+(?:\s+\w+){0,4})",
        SocialCueType.SHARED_DISCUSSION,
        1,
    ),
    (
        r"(?:when|where)\s+we\s+(?:discussed|talked\s+about)\s+(\w+(?:\s+\w+){0,4})",
        SocialCueType.SHARED_DISCUSSION,
        1,
    ),

    # Agent statement patterns (user refers to what I said)
    (
        r"you\s+(?:mentioned|said|suggested|recommended|noted)\s+(?:that\s+)?(.+?)(?:\.|,|$)",
        SocialCueType.AGENT_STATEMENT,
        1,
    ),
    (
        r"(?:like|as)\s+you\s+(?:said|mentioned|suggested)\s*(?:,\s*)?(.+?)(?:\.|$)",
        SocialCueType.AGENT_STATEMENT,
        1,
    ),
    (
        r"what\s+(?:did\s+)?you\s+(?:say|mention|suggest)\s+about\s+(.+?)(?:\?|$)",
        SocialCueType.AGENT_STATEMENT,
        1,
    ),

    # Shared decision patterns
    (
        r"we\s+(?:agreed|decided|determined)\s+(?:that\s+)?(.+?)(?:\.|,|$)",
        SocialCueType.SHARED_DECISION,
        1,
    ),
    (
        r"(?:our|the)\s+(?:decision|agreement)\s+(?:about|on|regarding)\s+(.+?)(?:\.|,|$)",
        SocialCueType.SHARED_DECISION,
        1,
    ),

    # Collaborative work patterns
    (
        r"we\s+(?:built|implemented|created|designed|fixed)\s+(.+?)(?:\.|,|$)",
        SocialCueType.COLLABORATIVE_WORK,
        1,
    ),
    (
        r"(?:when|where)\s+we\s+(?:built|implemented|worked\s+on)\s+(.+?)(?:\?|$)",
        SocialCueType.COLLABORATIVE_WORK,
        1,
    ),

    # Shared knowledge patterns
    (
        r"(?:as\s+)?we\s+(?:know|understand)\s+(?:that\s+)?(.+?)(?:\.|,|$)",
        SocialCueType.SHARED_KNOWLEDGE,
        1,
    ),

    # Explicit recall requests
    (
        r"(?:do\s+you\s+)?remember\s+(?:when\s+we\s+)?(.+?)(?:\?|$)",
        SocialCueType.EXPLICIT_RECALL,
        1,
    ),
    (
        r"do\s+you\s+recall\s+(.+?)(?:\?|$)",
        SocialCueType.EXPLICIT_RECALL,
        1,
    ),
    (
        r"can\s+you\s+remind\s+me\s+(?:about\s+)?(.+?)(?:\?|$)",
        SocialCueType.EXPLICIT_RECALL,
        1,
    ),
]


def detect_social_cue(text: str) -> Optional[SocialCue]:
    """
    Detect a social cue in user input.

    Scans the text for patterns that indicate reference to shared knowledge
    or past collaboration. Returns the first match found.

    Args:
        text: User message text

    Returns:
        SocialCue with type and extracted topic, or None if no cue found
    """
    text_lower = text.lower().strip()

    for pattern, cue_type, topic_group in SOCIAL_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            topic = None
            if topic_group > 0 and match.lastindex and match.lastindex >= topic_group:
                topic = match.group(topic_group).strip()
                # Clean up topic
                topic = _clean_topic(topic)

            return SocialCue(
                cue_type=cue_type,
                original_text=match.group(0),
                topic=topic if topic else None,
                is_question="?" in text,
            )

    return None


def detect_all_social_cues(text: str) -> list[SocialCue]:
    """
    Detect all social cues in user input.

    Useful when multiple references exist in a single message.

    Args:
        text: User message text

    Returns:
        List of all detected social cues
    """
    cues: list[SocialCue] = []
    text_lower = text.lower().strip()

    for pattern, cue_type, topic_group in SOCIAL_PATTERNS:
        for match in re.finditer(pattern, text_lower, re.IGNORECASE):
            topic = None
            if topic_group > 0 and match.lastindex and match.lastindex >= topic_group:
                topic = match.group(topic_group).strip()
                topic = _clean_topic(topic)

            cues.append(
                SocialCue(
                    cue_type=cue_type,
                    original_text=match.group(0),
                    topic=topic if topic else None,
                    is_question="?" in text,
                )
            )

    return cues


def _clean_topic(topic: str) -> str:
    """Clean up an extracted topic string."""
    # Remove trailing punctuation
    topic = topic.rstrip(".,;:!?")
    # Remove common filler words from start
    fillers = ["the", "a", "an", "that", "this", "some", "about"]
    words = topic.split()
    while words and words[0].lower() in fillers:
        words = words[1:]
    return " ".join(words)


def extract_recall_query(cue: SocialCue) -> Optional[str]:
    """
    Extract a search query from a social cue.

    Returns a query string suitable for semantic or keyword search
    to find related memories.

    Args:
        cue: The detected social cue

    Returns:
        Search query string, or None if no meaningful query could be extracted
    """
    if cue.topic:
        return cue.topic

    # If no specific topic, try to extract key concepts from the original text
    # This is a fallback - the topic extractor should catch most cases
    return None


def requires_recall(text: str) -> bool:
    """
    Quick check if text contains any social cue that might need memory recall.

    Faster than full detection for filtering messages that don't need recall.

    Args:
        text: User message text

    Returns:
        True if any social cue patterns are likely present
    """
    # Quick keyword check before expensive regex
    quick_keywords = [
        "we discussed",
        "we talked",
        "you mentioned",
        "you said",
        "you suggested",
        "we agreed",
        "we decided",
        "we built",
        "we implemented",
        "remember when",
        "do you recall",
        "remind me",
        "as we",
        "like you",
    ]
    text_lower = text.lower()
    return any(kw in text_lower for kw in quick_keywords)
