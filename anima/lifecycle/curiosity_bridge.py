# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Curiosity Bridge - Phase 3D of Contextual Recall Triggers.

Bridges context switches to prior curiosity by detecting when the current
conversation topic matches an open question in the curiosity queue.

The key insight: when we return to a topic we've been curious about,
that's a natural moment to surface related research or remind about
the open question.

Usage:
    from anima.lifecycle.curiosity_bridge import CuriosityBridge

    bridge = CuriosityBridge(agent_id="anima")

    # On topic shift or new context
    matches = bridge.find_matching_curiosities(current_topic)
    if matches:
        # Surface the curiosity: "This reminds me - I was curious about X"
        for match in matches:
            print(f"Related curiosity: {match.curiosity.question}")
"""

from dataclasses import dataclass
from typing import Optional

from anima.embeddings import embed_text
from anima.embeddings.similarity import cosine_similarity
from anima.storage.curiosity import Curiosity, CuriosityStore, CuriosityStatus


# Minimum similarity for a curiosity to be considered a match
DEFAULT_MATCH_THRESHOLD = 0.5


@dataclass
class CuriosityMatch:
    """
    A curiosity that matches the current topic.

    Contains the curiosity and its similarity score to the current context.
    """

    curiosity: Curiosity
    similarity: float
    embedding: list[float]

    @property
    def is_strong_match(self) -> bool:
        """Check if this is a strong match (>70% similar)."""
        return self.similarity > 0.7

    def format_prompt(self) -> str:
        """
        Format this match as a prompt for the agent.

        Returns a string that can be injected into context to remind
        the agent about this curiosity.
        """
        strength = "strongly" if self.is_strong_match else "somewhat"
        recurrence = self.curiosity.recurrence_count

        lines = [
            f"# CURIOSITY BRIDGE: This topic {strength} relates to an open question!",
            f"# Question (asked {recurrence}x): {self.curiosity.question}",
        ]

        if self.curiosity.context:
            lines.append(f"# Original context: {self.curiosity.context}")

        lines.append("#")
        lines.append("# Consider: Is now a good time to explore this curiosity?")
        lines.append("# If so, run /research to dive deeper.")

        return "\n".join(lines)


@dataclass
class CuriosityBridge:
    """
    Bridges conversation context to open curiosities.

    Maintains embeddings for open curiosities and matches them against
    current conversation topics.
    """

    agent_id: str
    project_id: Optional[str] = None
    match_threshold: float = DEFAULT_MATCH_THRESHOLD
    _curiosity_embeddings: dict[str, list[float]] | None = None
    _store: CuriosityStore | None = None

    @property
    def store(self) -> CuriosityStore:
        """Lazy-load the curiosity store."""
        if self._store is None:
            self._store = CuriosityStore()
        return self._store

    def _ensure_embeddings(self, quiet: bool = True) -> dict[str, list[float]]:
        """
        Ensure curiosity embeddings are generated.

        Generates embeddings for all open curiosities if not already cached.
        Returns a dict mapping curiosity_id -> embedding.
        """
        if self._curiosity_embeddings is not None:
            return self._curiosity_embeddings

        self._curiosity_embeddings = {}

        # Get all open curiosities
        curiosities = self.store.get_curiosities(
            agent_id=self.agent_id,
            project_id=self.project_id,
            status=CuriosityStatus.OPEN,
        )

        # Generate embeddings for each
        for curiosity in curiosities:
            # Combine question and context for richer embedding
            text = curiosity.question
            if curiosity.context:
                text = f"{text} {curiosity.context}"

            embedding = embed_text(text, quiet=quiet)
            self._curiosity_embeddings[curiosity.id] = embedding

        return self._curiosity_embeddings

    def find_matching_curiosities(
        self,
        current_topic: str,
        limit: int = 3,
        quiet: bool = True,
    ) -> list[CuriosityMatch]:
        """
        Find open curiosities that match the current topic.

        Compares the current topic against all open curiosities using
        embedding similarity.

        Args:
            current_topic: The current conversation topic or context
            limit: Maximum matches to return
            quiet: Suppress embedding progress output

        Returns:
            List of CuriosityMatch objects, sorted by similarity (highest first)
        """
        # Generate embedding for current topic
        topic_embedding = embed_text(current_topic, quiet=quiet)

        # Ensure curiosity embeddings are ready
        curiosity_embeddings = self._ensure_embeddings(quiet=quiet)

        if not curiosity_embeddings:
            return []

        # Get curiosities for lookup
        curiosities = self.store.get_curiosities(
            agent_id=self.agent_id,
            project_id=self.project_id,
            status=CuriosityStatus.OPEN,
        )
        curiosity_lookup = {c.id: c for c in curiosities}

        # Calculate similarities
        matches: list[CuriosityMatch] = []

        for curiosity_id, embedding in curiosity_embeddings.items():
            similarity = cosine_similarity(topic_embedding, embedding)

            if similarity >= self.match_threshold:
                curiosity = curiosity_lookup.get(curiosity_id)
                if curiosity:
                    matches.append(
                        CuriosityMatch(
                            curiosity=curiosity,
                            similarity=similarity,
                            embedding=embedding,
                        )
                    )

        # Sort by similarity (highest first) and limit
        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:limit]

    def refresh(self) -> None:
        """
        Refresh the cached curiosity embeddings.

        Call this when curiosities are added/removed to update the cache.
        """
        self._curiosity_embeddings = None

    def check_and_format(
        self,
        current_topic: str,
        quiet: bool = True,
    ) -> Optional[str]:
        """
        Check for matching curiosities and format as a prompt.

        Convenience method that combines find_matching_curiosities
        with formatting.

        Args:
            current_topic: The current conversation topic
            quiet: Suppress embedding progress output

        Returns:
            Formatted prompt string if matches found, None otherwise
        """
        matches = self.find_matching_curiosities(current_topic, limit=1, quiet=quiet)

        if not matches:
            return None

        return matches[0].format_prompt()


def bridge_to_curiosity(
    agent_id: str,
    current_topic: str,
    project_id: Optional[str] = None,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    quiet: bool = True,
) -> Optional[str]:
    """
    Convenience function to check for curiosity matches.

    Creates a bridge, checks for matches, and returns a formatted prompt
    if any curiosities match the current topic.

    Args:
        agent_id: The agent ID to check curiosities for
        current_topic: The current conversation topic
        project_id: Optional project ID for scoping
        threshold: Minimum similarity threshold
        quiet: Suppress embedding progress output

    Returns:
        Formatted prompt string if matches found, None otherwise
    """
    bridge = CuriosityBridge(
        agent_id=agent_id,
        project_id=project_id,
        match_threshold=threshold,
    )

    return bridge.check_and_format(current_topic, quiet=quiet)
