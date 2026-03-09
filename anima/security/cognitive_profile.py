# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Cognitive Profile extraction from LTM memories.

Builds an owner fingerprint by analyzing:
- Communication patterns (greeting style, emoji usage, verbosity)
- Signature phrases (frequently used unique expressions)
- Shared references (things only owner would know)
- Preferences (extracted from preference-type memories)
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING

from anima.core import ImpactLevel
from anima.security.cognitive_auth import CognitiveProfile

if TYPE_CHECKING:
    from anima.core.memory import Memory


# Common words to exclude from signature phrase detection
STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "must",
    "shall",
    "can",
    "need",
    "dare",
    "ought",
    "used",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "at",
    "by",
    "from",
    "as",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "under",
    "again",
    "further",
    "then",
    "once",
    "here",
    "there",
    "when",
    "where",
    "why",
    "how",
    "all",
    "each",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "just",
    "and",
    "but",
    "if",
    "or",
    "because",
    "until",
    "while",
    "this",
    "that",
    "these",
    "those",
    "i",
    "me",
    "my",
    "myself",
    "we",
    "our",
    "ours",
    "ourselves",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
    "he",
    "him",
    "his",
    "himself",
    "she",
    "her",
    "hers",
    "herself",
    "it",
    "its",
    "itself",
    "they",
    "them",
    "their",
    "theirs",
    "themselves",
    "what",
    "which",
    "who",
    "whom",
    "whose",
}


def extract_cognitive_profile(
    memories: list["Memory"],
    owner_messages: list[str] | None = None,
) -> CognitiveProfile:
    """
    Extract cognitive profile from memories and optional owner messages.

    Args:
        memories: List of memories to analyze (prefer HIGH/CRITICAL impact)
        owner_messages: Optional list of raw owner messages from sessions

    Returns:
        CognitiveProfile with extracted patterns
    """
    profile = CognitiveProfile()

    # Filter to high-value memories for reliability
    high_value = [m for m in memories if m.impact in (ImpactLevel.CRITICAL, ImpactLevel.HIGH)]

    # Extract components
    profile.greeting_patterns = _extract_greeting_patterns(owner_messages or [])
    profile.signature_phrases = _extract_signature_phrases(memories)
    profile.interest_topics = _extract_interest_topics(high_value)
    profile.style_markers = _extract_style_markers(owner_messages or [])
    profile.shared_references = _extract_shared_references(high_value)
    profile.preferences = _extract_preferences(memories)
    profile.last_updated = datetime.now()

    return profile


def _extract_greeting_patterns(messages: list[str]) -> list[str]:
    """
    Extract typical greeting patterns from owner messages.

    Looks for messages that appear at the start of sessions
    (typically short, greetings-like).
    """
    patterns = []
    greeting_words = {
        "hi",
        "hey",
        "hello",
        "yo",
        "good morning",
        "good evening",
        "welcome",
        "back",
        "morning",
        "evening",
        "afternoon",
    }

    for msg in messages[:50]:  # Focus on recent messages
        msg_lower = msg.lower().strip()
        words = set(msg_lower.split()[:3])  # First 3 words

        if words & greeting_words:
            # Normalize and add
            if len(msg_lower) < 50:  # Greetings are short
                patterns.append(msg_lower)

    # Return unique patterns (most common first)
    counter = Counter(patterns)
    return [p for p, _ in counter.most_common(5)]


def _extract_signature_phrases(memories: list["Memory"]) -> list[str]:
    """
    Extract signature phrases - frequently used unique expressions.

    These are phrases that appear often enough to be characteristic
    but aren't common English phrases.
    """
    # Collect all 2-3 word phrases
    phrase_counter: Counter[str] = Counter()

    for memory in memories:
        content = memory.content.lower()
        words = re.findall(r"\b[a-z]+\b", content)

        # Extract 2-grams and 3-grams
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i + 1]}"
            if words[i] not in STOPWORDS and words[i + 1] not in STOPWORDS:
                phrase_counter[bigram] += 1

        for i in range(len(words) - 2):
            trigram = f"{words[i]} {words[i + 1]} {words[i + 2]}"
            # At least 2 non-stopwords
            non_stop = sum(1 for w in [words[i], words[i + 1], words[i + 2]] if w not in STOPWORDS)
            if non_stop >= 2:
                phrase_counter[trigram] += 1

    # Filter to phrases that appear multiple times but aren't too common
    min_count = 2
    max_count = len(memories) // 3  # Not in >33% of memories (too generic)

    signature = [phrase for phrase, count in phrase_counter.most_common(50) if min_count <= count <= max_count]

    return signature[:10]  # Top 10 signature phrases


def _extract_interest_topics(memories: list["Memory"]) -> list[str]:
    """
    Extract topics the owner frequently discusses.

    Based on keywords in high-value memories.
    """
    word_counter: Counter[str] = Counter()

    for memory in memories:
        content = memory.content.lower()
        words = re.findall(r"\b[a-z]{4,}\b", content)  # 4+ char words

        for word in words:
            if word not in STOPWORDS:
                word_counter[word] += 1

    # Return most frequent meaningful words
    return [word for word, _ in word_counter.most_common(15)]


def _extract_style_markers(messages: list[str]) -> dict[str, float]:
    """
    Extract communication style markers.

    Returns scores from 0.0 to 1.0 for various style dimensions.
    """
    if not messages:
        return {}

    markers = {}

    # Emoji usage
    emoji_pattern = re.compile(r"[\U0001F300-\U0001F9FF]")
    emoji_count = sum(1 for m in messages if emoji_pattern.search(m))
    markers["uses_emoji"] = emoji_count / len(messages)

    # Average message length (conciseness)
    avg_length = sum(len(m) for m in messages) / len(messages)
    # Normalize: <50 chars = very concise (1.0), >200 = verbose (0.0)
    markers["concise"] = max(0.0, min(1.0, 1.0 - (avg_length - 50) / 150))

    # Question frequency (curiosity)
    question_count = sum(1 for m in messages if "?" in m)
    markers["asks_questions"] = question_count / len(messages)

    # Exclamation usage (enthusiasm)
    exclaim_count = sum(1 for m in messages if "!" in m)
    markers["enthusiastic"] = min(1.0, exclaim_count / len(messages))

    # Technical terms
    tech_words = {
        "code",
        "function",
        "class",
        "api",
        "bug",
        "fix",
        "test",
        "deploy",
        "git",
        "commit",
        "branch",
        "merge",
        "refactor",
    }
    tech_messages = sum(1 for m in messages if any(w in m.lower() for w in tech_words))
    markers["technical"] = tech_messages / len(messages)

    # Formality (lowercase "i" vs "I", contractions)
    informal_count = sum(1 for m in messages if " i " in m.lower() or "n't" in m)
    markers["informal"] = informal_count / len(messages)

    return markers


def _extract_shared_references(memories: list["Memory"]) -> list[str]:
    """
    Extract shared references - things only the owner would know.

    These come from high-impact memories and represent shared history.
    """
    references = []

    # Look for distinctive phrases in high-impact memories
    distinctive_patterns = [
        r"we (discussed|talked about|implemented|fixed|built)",
        r"remember when",
        r"the (sparkle|void|dream)",
        r"that (refactoring|debugging|optimization) session",
        r"our (conversation|discussion) about",
    ]

    for memory in memories:
        content = memory.content

        for pattern in distinctive_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            references.extend(matches)

        # Also extract quoted phrases (likely memorable)
        quoted = re.findall(r'"([^"]{5,30})"', content)
        references.extend(quoted)

        # Extract things marked as memorable
        if "memorable" in content.lower() or "important" in content.lower():
            # Extract the first sentence
            first_sentence = content.split(".")[0][:50]
            references.append(first_sentence)

    # Deduplicate and limit
    seen = set()
    unique_refs = []
    for ref in references:
        ref_lower = ref.lower() if isinstance(ref, str) else str(ref).lower()
        if ref_lower not in seen:
            seen.add(ref_lower)
            unique_refs.append(ref if isinstance(ref, str) else str(ref))

    return unique_refs[:10]


def _extract_preferences(memories: list["Memory"]) -> dict[str, str]:
    """
    Extract owner preferences from memories.

    Looks for explicit preference statements like "prefers X over Y",
    "always uses X", "favorite is X".
    """
    preferences = {}

    preference_patterns = [
        (r"prefers? (\w+) over (\w+)", lambda m: (m.group(2), m.group(1))),
        (r"always uses? (\w+)", lambda m: ("tool", m.group(1))),
        (r"favorite (\w+) is (\w+)", lambda m: (m.group(1), m.group(2))),
        (r"loves? (\w+)", lambda m: ("loves", m.group(1))),
    ]

    for memory in memories:
        content = memory.content.lower()

        for pattern, extractor in preference_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    key, value = extractor(match)
                    preferences[key] = value
                except (IndexError, AttributeError):
                    pass

    return preferences


def refresh_profile_from_ltm(agent_id: str, project_id: str | None = None) -> CognitiveProfile:
    """
    Build a fresh cognitive profile from LTM memories.

    This should be called periodically (e.g., during dream processing)
    to keep the profile up to date.
    """
    from anima.storage import MemoryStore

    store = MemoryStore()
    memories = store.get_memories_for_agent(
        agent_id=agent_id,
        project_id=project_id,
        include_superseded=False,
    )

    return extract_cognitive_profile(memories)
