# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Memory decay and compaction for LTM.

Implements human-like memory decay where older memories are compacted
(summarized to their essence) based on their impact level.
"""

from datetime import datetime, timedelta
from typing import Optional

from anima.core import Memory, ImpactLevel
from anima.storage import MemoryStore


def _get_decay_thresholds() -> dict[ImpactLevel, Optional[timedelta]]:
    """Get decay thresholds from config."""
    from anima.core.config import get_config

    config = get_config()
    return {
        ImpactLevel.LOW: timedelta(days=config.decay.low_days),
        ImpactLevel.MEDIUM: timedelta(days=config.decay.medium_days),
        ImpactLevel.HIGH: timedelta(days=config.decay.high_days),
        ImpactLevel.CRITICAL: None,  # Never decay (not configurable)
    }


# Default decay thresholds (can be overridden via ~/.anima/config.json)
DECAY_THRESHOLDS = {
    ImpactLevel.LOW: timedelta(days=1),  # Aggressive decay after 1 day
    ImpactLevel.MEDIUM: timedelta(weeks=1),  # Moderate decay after 1 week
    ImpactLevel.HIGH: timedelta(days=30),  # Gentle decay after 1 month
    ImpactLevel.CRITICAL: None,  # Never decay
}

# Minimum content length after compaction (characters)
MIN_CONTENT_LENGTH = 20


class MemoryDecay:
    """
    Handles memory decay and compaction.

    Memories are compacted (summarized) based on age and impact level.
    Critical memories never decay. The original content is always preserved.
    """

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()

    def should_compact(self, memory: Memory, now: Optional[datetime] = None) -> bool:
        """
        Check if a memory should be compacted based on age and impact.

        Args:
            memory: The memory to check
            now: Current time (defaults to datetime.now())

        Returns:
            True if the memory should be compacted
        """
        if memory.impact == ImpactLevel.CRITICAL:
            return False

        now = now or datetime.now()
        thresholds = _get_decay_thresholds()
        threshold = thresholds.get(memory.impact)

        if threshold is None:
            return False

        # Normalize both datetimes to naive for comparison
        # (handles mixed timezone-aware and naive datetimes in database)
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        created_naive = memory.created_at.replace(tzinfo=None) if memory.created_at.tzinfo else memory.created_at

        age = now_naive - created_naive
        return age > threshold

    def compact_content(self, memory: Memory) -> str:
        """
        Compact a memory's content to its essence.

        This is a simple rule-based compaction. In production, this would
        call the agent to intelligently summarize while preserving key information.

        Different memory types have different compaction strategies:
        - ARCHITECTURAL: Preserve exact terminology, remove rationale
        - LEARNINGS: Keep lesson and refs, remove discovery process
        - ACHIEVEMENTS: Keep what/when, remove implementation details
        - EMOTIONAL: Generalize to patterns

        Args:
            memory: The memory to compact

        Returns:
            Compacted content string
        """
        content = memory.content

        # If already very short, don't compact further
        if len(content) <= MIN_CONTENT_LENGTH:
            return content

        # Simple heuristic compaction (would be AI-powered in production)
        # Remove common filler phrases
        fillers = [
            "I think ",
            "I believe ",
            "We discussed ",
            "It turns out ",
            "After investigation ",
            "Spent time ",
            "Was frustrating ",
            "Learned that ",
        ]
        for filler in fillers:
            content = content.replace(filler, "")

        # Truncate if still too long (crude fallback)
        if len(content) > 200:
            # Try to cut at a sentence boundary
            sentences = content.split(". ")
            if len(sentences) > 1:
                # Keep first and last sentence
                content = f"{sentences[0]}. [...] {sentences[-1]}"
            else:
                content = content[:200] + "..."

        return content.strip()

    def process_decay(self, agent_id: str, project_id: Optional[str] = None, dry_run: bool = False) -> list[tuple[Memory, str]]:
        """
        Process decay for all memories of an agent.

        Args:
            agent_id: The agent whose memories to process
            project_id: Optional project filter
            dry_run: If True, don't actually update memories

        Returns:
            List of (memory, new_content) tuples that were/would be compacted
        """
        now = datetime.now()
        compacted: list[tuple[Memory, str]] = []

        # Get all non-superseded memories
        memories = self.store.get_memories_for_agent(agent_id=agent_id, project_id=project_id, include_superseded=False)

        for memory in memories:
            if self.should_compact(memory, now):
                new_content = self.compact_content(memory)

                # Only compact if content actually changed
                if new_content != memory.content:
                    compacted.append((memory, new_content))

                    if not dry_run:
                        memory.content = new_content
                        memory.version += 1
                        self.store.save_memory(memory)

        return compacted

    def delete_empty_memories(self, agent_id: str) -> int:
        """
        Delete memories that have been compacted to nothing.

        Returns:
            Number of memories deleted
        """
        memories = self.store.get_memories_for_agent(
            agent_id=agent_id,
            include_superseded=True,  # Include superseded to clean up
        )

        deleted = 0
        for memory in memories:
            # Delete if content is essentially empty or superseded and very old
            if len(memory.content.strip()) < MIN_CONTENT_LENGTH:
                if memory.is_superseded():
                    self.store.delete_memory(memory.id)
                    deleted += 1

        return deleted
