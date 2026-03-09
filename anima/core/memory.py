# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Memory data model for LTM."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Final
import uuid

from anima.core.types import RegionType, MemoryKind, ImpactLevel


# DSL format abbreviations (module-level for efficiency)
_KIND_SHORT: Final[dict[MemoryKind, str]] = {
    MemoryKind.EMOTIONAL: "EMOT",
    MemoryKind.ARCHITECTURAL: "ARCH",
    MemoryKind.LEARNINGS: "LEARN",
    MemoryKind.ACHIEVEMENTS: "ACHV",
    MemoryKind.INTROSPECT: "INTRO",
    MemoryKind.DREAM: "DREAM",
    MemoryKind.SUBCONSCIOUS: "SUBC",
}

_IMPACT_SHORT: Final[dict[ImpactLevel, str]] = {
    ImpactLevel.LOW: "LOW",
    ImpactLevel.MEDIUM: "MED",
    ImpactLevel.HIGH: "HIGH",
    ImpactLevel.CRITICAL: "CRIT",
    ImpactLevel.WIP: "WIP",
}


@dataclass
class Memory:
    """
    A single memory unit in LTM.

    Memories are append-only - corrections create new memories that supersede old ones.
    They decay over time based on impact level, with content being compacted
    while original_content is preserved forever.
    """

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""

    # Location
    region: RegionType = RegionType.PROJECT
    project_id: str | None = None

    # Content
    kind: MemoryKind = MemoryKind.LEARNINGS
    content: str = ""  # Current (possibly compacted) content
    original_content: str = ""  # Original full content, never changes

    # Metadata
    impact: ImpactLevel = ImpactLevel.MEDIUM
    confidence: float = 1.0  # 0.0-1.0, decreases on contradiction

    # Timestamps (always from OS, never from AI knowledge)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Graph structure - linked list of memories by kind
    previous_memory_id: str | None = None

    # Append-only corrections
    version: int = 1
    superseded_by: str | None = None  # Points to correcting memory

    # Security
    signature: str | None = None  # Optional cryptographic signature
    signature_valid: bool | None = None  # Set during injection if verified

    # Performance optimization
    token_count: int | None = None  # Cached token count for injection budget

    # Platform tracking (spaceship journals)
    platform: str | None = None  # Which platform created this memory (claude, antigravity, opencode)
    model: str | None = None  # Which LLM model created this memory (e.g., claude-opus-4-5-20251101)

    # Session tracking (Phase 3: Temporal Infrastructure)
    session_id: str | None = None  # Groups memories by conversation session

    # Git event correlation (Phase 3: Temporal Infrastructure)
    git_commit: str | None = None  # Commit hash when memory was created
    git_branch: str | None = None  # Branch name when memory was created

    def __post_init__(self):
        """Ensure original_content is set if not provided."""
        if not self.original_content and self.content:
            self.original_content = self.content

    def is_superseded(self) -> bool:
        """Check if this memory has been superseded by a correction."""
        return self.superseded_by is not None

    def is_low_confidence(self) -> bool:
        """Check if this memory has low confidence (possibly contradicted)."""
        return self.confidence < 0.7

    def to_dsl(self) -> str:
        """
        Convert memory to compact DSL format for injection.

        Format: ~TYPE:IMPACT| content
        With ? after impact if low confidence.
        With ⚠ prefix if signature verification failed.
        """
        confidence_marker = "?" if self.is_low_confidence() else ""
        # Show warning if signature was checked and failed
        untrusted_marker = "⚠" if self.signature_valid is False else ""

        return f"{untrusted_marker}~{_KIND_SHORT[self.kind]}:{_IMPACT_SHORT[self.impact]}{confidence_marker}| {self.content}"

    def touch(self) -> None:
        """Update last_accessed to now."""
        self.last_accessed = datetime.now(UTC)


@dataclass
class MemoryBlock:
    """
    A block of memories formatted for injection into context.

    Represents all memories for a specific agent/project combination,
    formatted in the compact DSL.
    """

    agent_name: str
    project_name: str | None
    memories: list[Memory] = field(default_factory=list)

    def to_dsl(self) -> str:
        """
        Format all memories as a DSL block for context injection.

        Format:
        [LTM:agent_name@project_name]
        ~TYPE:IMPACT| content
        ...
        [/LTM]
        """
        if not self.memories:
            return ""

        header = f"[LTM:{self.agent_name}"
        if self.project_name:
            header += f"@{self.project_name}"
        header += "]"

        lines = [header]
        for memory in self.memories:
            if not memory.is_superseded():  # Skip superseded memories
                lines.append(memory.to_dsl())
        lines.append("[/LTM]")

        return "\n".join(lines)

    def token_estimate(self) -> int:
        """
        Estimate token count for this block.

        Uses a simple heuristic: ~4 characters per token on average.
        For accurate counting, use tiktoken externally.
        """
        content = self.to_dsl()
        return len(content) // 4
