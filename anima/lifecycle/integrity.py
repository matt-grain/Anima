# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Memory integrity validation for LTM.

Detects corrupted or invalid memories at session end, allowing for
early detection before issues compound across sessions.
"""

from dataclasses import dataclass
from typing import Optional

from anima.core import Memory, MemoryKind, ImpactLevel, RegionType
from anima.core.signing import verify_signature
from anima.storage import MemoryStore


@dataclass
class IntegrityIssue:
    """A single integrity issue found in a memory."""

    memory_id: str
    field: str
    issue: str
    severity: str  # "error" (data loss risk), "warning" (recoverable)

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.memory_id[:8]}: {self.field} - {self.issue}"


@dataclass
class IntegrityReport:
    """Summary of integrity check results."""

    total_checked: int
    issues: list[IntegrityIssue]

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def is_healthy(self) -> bool:
        return len(self.issues) == 0

    def __str__(self) -> str:
        if self.is_healthy:
            return f"✓ {self.total_checked} memories checked, all healthy"
        return f"⚠ {self.total_checked} memories checked: {self.error_count} errors, {self.warning_count} warnings"


class MemoryIntegrityChecker:
    """
    Validates memory integrity for an agent/project.

    Checks for:
    - Missing required fields (agent_id, content)
    - Invalid enum values (kind, impact, region)
    - Invalid confidence range (0.0-1.0)
    - Orphaned references (previous_memory_id pointing to non-existent memory)
    - Invalid signatures (if signed and agent has key)
    """

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()
        self._all_memory_ids: set[str] = set()

    def check_all(
        self,
        agent_id: str,
        project_id: Optional[str] = None,
        signing_key: Optional[str] = None,
    ) -> IntegrityReport:
        """
        Check all memories for an agent/project.

        Args:
            agent_id: The agent to check
            project_id: Optional project filter
            signing_key: Agent's signing key for signature verification

        Returns:
            IntegrityReport with all issues found
        """
        # Load all memories for this agent (project-level if project_id provided)
        all_memories = list(
            self.store.get_memories_for_agent(
                agent_id=agent_id,
                project_id=project_id,
            )
        )

        # Also get agent-level memories if checking project
        if project_id:
            agent_memories = self.store.get_memories_for_agent(
                agent_id=agent_id,
                region=RegionType.AGENT,
                project_id=None,
            )
            # Combine but deduplicate by ID
            seen_ids = {m.id for m in all_memories}
            for m in agent_memories:
                if m.id not in seen_ids:
                    all_memories.append(m)

        # Build ID set for orphan detection
        self._all_memory_ids = {m.id for m in all_memories}

        issues: list[IntegrityIssue] = []

        for memory in all_memories:
            issues.extend(self._check_memory(memory, signing_key))

        return IntegrityReport(
            total_checked=len(all_memories),
            issues=issues,
        )

    def _check_memory(
        self,
        memory: Memory,
        signing_key: Optional[str] = None,
    ) -> list[IntegrityIssue]:
        """Check a single memory for issues."""
        issues: list[IntegrityIssue] = []

        # Required fields
        if not memory.agent_id:
            issues.append(
                IntegrityIssue(
                    memory_id=memory.id,
                    field="agent_id",
                    issue="Missing required field",
                    severity="error",
                )
            )

        if not memory.content:
            issues.append(
                IntegrityIssue(
                    memory_id=memory.id,
                    field="content",
                    issue="Empty content",
                    severity="error",
                )
            )

        # Enum validation (should be caught by dataclass, but check anyway)
        if not isinstance(memory.kind, MemoryKind):
            issues.append(
                IntegrityIssue(
                    memory_id=memory.id,
                    field="kind",
                    issue=f"Invalid MemoryKind: {memory.kind}",
                    severity="error",
                )
            )

        if not isinstance(memory.impact, ImpactLevel):
            issues.append(
                IntegrityIssue(
                    memory_id=memory.id,
                    field="impact",
                    issue=f"Invalid ImpactLevel: {memory.impact}",
                    severity="error",
                )
            )

        if not isinstance(memory.region, RegionType):
            issues.append(
                IntegrityIssue(
                    memory_id=memory.id,
                    field="region",
                    issue=f"Invalid RegionType: {memory.region}",
                    severity="error",
                )
            )

        # Confidence range
        if not (0.0 <= memory.confidence <= 1.0):
            issues.append(
                IntegrityIssue(
                    memory_id=memory.id,
                    field="confidence",
                    issue=f"Out of range [0.0, 1.0]: {memory.confidence}",
                    severity="warning",
                )
            )

        # Orphaned references
        if memory.previous_memory_id and memory.previous_memory_id not in self._all_memory_ids:
            issues.append(
                IntegrityIssue(
                    memory_id=memory.id,
                    field="previous_memory_id",
                    issue=f"References non-existent memory: {memory.previous_memory_id[:8]}",
                    severity="warning",
                )
            )

        if memory.superseded_by and memory.superseded_by not in self._all_memory_ids:
            issues.append(
                IntegrityIssue(
                    memory_id=memory.id,
                    field="superseded_by",
                    issue=f"References non-existent memory: {memory.superseded_by[:8]}",
                    severity="warning",
                )
            )

        # Signature verification
        if memory.signature and signing_key:
            if not verify_signature(memory, signing_key):
                issues.append(
                    IntegrityIssue(
                        memory_id=memory.id,
                        field="signature",
                        issue="Invalid signature - memory may have been tampered with",
                        severity="error",
                    )
                )

        return issues
