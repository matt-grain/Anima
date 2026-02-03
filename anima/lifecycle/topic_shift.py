# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Topic Shift Detection - Phase 3C of Contextual Recall Triggers.

Detects when conversation topic changes significantly and surfaces
relevant memories for the new topic. This creates the "Oh, this reminds
me of..." feeling that makes recall feel organic rather than mechanical.

The key insight: topic shifts are natural recall triggers in human
conversation. When someone changes subject, our minds automatically
surface related knowledge.

Usage:
    from anima.lifecycle.topic_shift import TopicTracker

    tracker = TopicTracker()

    # On each user message
    shift = tracker.detect_shift(user_message)
    if shift.is_significant:
        memories = shift.get_related_memories(store, agent_id, project_id)
        # Inject memories into context
"""

from dataclasses import dataclass, field
from typing import Optional

from anima.core import Memory
from anima.embeddings import embed_text
from anima.embeddings.similarity import cosine_similarity, find_similar
from anima.storage import MemoryStore


# Threshold for considering a topic shift "significant"
# Lower = more sensitive, Higher = only major shifts
DEFAULT_SHIFT_THRESHOLD = 0.6  # Topics must be < 60% similar to trigger


@dataclass
class TopicShift:
    """
    Result of topic shift detection.

    Contains information about whether a shift occurred and
    provides methods to retrieve related memories.
    """

    current_topic: str
    current_embedding: list[float]
    previous_topic: Optional[str] = None
    previous_embedding: Optional[list[float]] = None
    similarity: float = 1.0  # 1.0 = same topic, 0.0 = completely different
    threshold: float = DEFAULT_SHIFT_THRESHOLD

    @property
    def is_significant(self) -> bool:
        """Check if the topic shift is significant enough to trigger recall."""
        # No previous topic = first message, not a shift
        if self.previous_embedding is None:
            return False
        # Significant if similarity drops below threshold
        return self.similarity < self.threshold

    @property
    def shift_magnitude(self) -> float:
        """
        How much the topic shifted (0.0 = no shift, 1.0 = complete change).

        This is the inverse of similarity - useful for ranking or logging.
        """
        return 1.0 - self.similarity

    def get_related_memories(
        self,
        store: MemoryStore,
        agent_id: str,
        project_id: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.4,
    ) -> list[Memory]:
        """
        Retrieve memories related to the new topic.

        Uses semantic search to find memories that match the current
        topic embedding.

        Args:
            store: Memory store to search
            agent_id: Agent ID for scoping
            project_id: Optional project ID for scoping
            limit: Maximum memories to return
            similarity_threshold: Minimum similarity to include

        Returns:
            List of memories related to the new topic
        """
        # Get memories with embeddings
        candidate_memories = store.get_memories_with_embeddings(
            agent_id=agent_id,
            project_id=project_id,
        )

        if not candidate_memories:
            return []

        # Build candidates for similarity search
        candidates: list[tuple[str, list[float]]] = []
        memory_lookup: dict[str, str] = {}

        for mem_id, content, emb in candidate_memories:
            if emb is not None:
                candidates.append((mem_id, emb))
                memory_lookup[mem_id] = content

        if not candidates:
            return []

        # Find similar memories
        results = find_similar(
            self.current_embedding,
            candidates,
            top_k=limit,
            threshold=similarity_threshold,
        )

        if not results:
            return []

        # Fetch full memory objects
        result_ids = [r.item for r in results]
        all_memories = store.get_memories_for_agent(
            agent_id=agent_id,
            project_id=project_id,
        )

        return [m for m in all_memories if m.id in result_ids]


@dataclass
class TopicTracker:
    """
    Tracks conversation topics and detects significant shifts.

    Maintains state across messages to compare current topic with
    previous topics and detect when recall should be triggered.
    """

    shift_threshold: float = DEFAULT_SHIFT_THRESHOLD
    _previous_topic: Optional[str] = field(default=None, repr=False)
    _previous_embedding: Optional[list[float]] = field(default=None, repr=False)

    def detect_shift(
        self,
        current_text: str,
        quiet: bool = True,
    ) -> TopicShift:
        """
        Detect if the current message represents a topic shift.

        Compares the current message embedding with the previous
        topic embedding to determine if a significant shift occurred.

        Args:
            current_text: The current user message or context
            quiet: Suppress embedding progress output

        Returns:
            TopicShift with detection results and methods to get memories
        """
        # Generate embedding for current topic
        current_embedding = embed_text(current_text, quiet=quiet)

        # Calculate similarity with previous topic
        similarity = 1.0
        if self._previous_embedding is not None:
            similarity = cosine_similarity(current_embedding, self._previous_embedding)

        # Create result
        shift = TopicShift(
            current_topic=current_text,
            current_embedding=current_embedding,
            previous_topic=self._previous_topic,
            previous_embedding=self._previous_embedding,
            similarity=similarity,
            threshold=self.shift_threshold,
        )

        # Update state for next comparison
        self._previous_topic = current_text
        self._previous_embedding = current_embedding

        return shift

    def reset(self) -> None:
        """Reset the tracker, clearing previous topic state."""
        self._previous_topic = None
        self._previous_embedding = None

    def set_topic(self, text: str, quiet: bool = True) -> None:
        """
        Set the current topic without detecting a shift.

        Useful for initializing the tracker at session start
        with project context.

        Args:
            text: Topic text to set as current
            quiet: Suppress embedding progress output
        """
        self._previous_topic = text
        self._previous_embedding = embed_text(text, quiet=quiet)


def extract_topic_keywords(text: str, max_words: int = 10) -> str:
    """
    Extract key topic words from text for lightweight comparison.

    This is a fallback for when embedding generation is too expensive.
    Uses simple heuristics to extract meaningful words.

    Args:
        text: Input text
        max_words: Maximum words to include

    Returns:
        Space-separated topic keywords
    """
    # Common words to filter out
    stopwords = {
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
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "it",
        "its",
        "they",
        "them",
        "their",
        "what",
        "which",
        "who",
        "whom",
    }

    # Tokenize and filter
    words = text.lower().split()
    keywords = [w.strip(".,!?;:'\"()[]{}") for w in words if w.lower() not in stopwords]

    # Take first N meaningful words
    return " ".join(keywords[:max_words])
