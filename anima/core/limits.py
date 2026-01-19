# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Memory count limits for LTM.

Provides configurable limits on memory creation to prevent runaway processes
from exhausting storage.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MemoryLimits:
    """
    Configurable limits for memory operations.

    Attributes:
        max_memories_per_agent: Maximum total memories for an agent (None = unlimited)
        max_memories_per_project: Maximum memories per project (None = unlimited)
        max_memories_per_kind: Maximum memories of each kind (None = unlimited)
    """
    max_memories_per_agent: Optional[int] = None
    max_memories_per_project: Optional[int] = None
    max_memories_per_kind: Optional[int] = None


# Default limits - generous but prevents runaway creation
DEFAULT_LIMITS = MemoryLimits(
    max_memories_per_agent=10000,     # Very high limit - should never hit in normal use
    max_memories_per_project=5000,    # Per-project limit
    max_memories_per_kind=2000,       # Per-kind limit
)

# No limits - for testing or special cases
NO_LIMITS = MemoryLimits()


class MemoryLimitExceeded(Exception):
    """Raised when a memory limit would be exceeded."""

    def __init__(self, limit_type: str, current: int, limit: int):
        self.limit_type = limit_type
        self.current = current
        self.limit = limit
        super().__init__(
            f"Memory limit exceeded: {limit_type} "
            f"(current: {current}, limit: {limit})"
        )
