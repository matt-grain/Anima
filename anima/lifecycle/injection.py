# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Memory injection for session start.

Retrieves relevant memories and formats them for context injection.
Respects the 10% context budget.
"""

from functools import lru_cache
from typing import Optional, TypedDict, Union, Any

import tiktoken

from anima.core import (
    Memory,
    MemoryBlock,
    MemoryTier,
    RegionType,
    Agent,
    Project,
    verify_signature,
    should_verify,
)
from anima.storage import MemoryStore


class InjectionStats(TypedDict):
    """Statistics about memory injection."""

    agent_memories: int
    project_memories: int
    total: int
    budget_tokens: int
    priority_counts: dict[str, int]  # CRITICAL, HIGH, MEDIUM, LOW


# Default values (can be overridden via ~/.anima/config.json)
DEFAULT_CONTEXT_SIZE = 200_000  # tokens (Claude's standard context window)
MEMORY_BUDGET_PERCENT = 0.10  # 10% of context


def _get_budget_config() -> tuple[int, float]:
    """Get budget settings from config."""
    from anima.core.config import get_config

    config = get_config()
    return config.budget.context_size, config.budget.context_percent


@lru_cache(maxsize=4)
def _get_encoder(model: str):
    """Cache tiktoken encoders for reuse."""
    return tiktoken.get_encoding(model)


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens in text using tiktoken."""
    try:
        enc = _get_encoder(model)
        return len(enc.encode(text))
    except Exception:
        # Fallback: rough estimate of 4 chars per token
        return len(text) // 4


def estimate_tokens(text: str) -> int:
    """Fast approximate token count (~4 chars per token)."""
    return len(text) // 4


def get_memory_tokens(memory: Memory) -> int:
    """
    Get token count for a memory's DSL representation.

    Uses cached token_count if available, otherwise falls back to
    fast approximation. The accurate count is calculated on save.
    """
    if memory.token_count is not None:
        return memory.token_count
    # Fast fallback for memories without cached count
    return estimate_tokens(memory.to_dsl() + "\n")


def calculate_token_count(memory: Memory) -> int:
    """
    Calculate accurate token count for a memory using tiktoken.

    This should be called when saving a memory to cache the count.
    Returns the token count for the memory's DSL representation.
    """
    memory_dsl = memory.to_dsl() + "\n"
    return count_tokens(memory_dsl)


def ensure_token_count(memory: Memory) -> None:
    """
    Ensure a memory has its token_count cached.

    Calculates and sets token_count if not already set.
    Call this before saving a memory.
    """
    if memory.token_count is None:
        memory.token_count = calculate_token_count(memory)


def get_memory_budget(context_size: Optional[int] = None) -> int:
    """
    Calculate token budget for memories.

    Uses config values if context_size not specified.
    """
    if context_size is None:
        context_size, percent = _get_budget_config()
        return int(context_size * percent)
    # Fallback to default percent if only size specified
    return int(context_size * MEMORY_BUDGET_PERCENT)


class MemoryInjector:
    """
    Handles memory retrieval and injection for session start.

    Retrieves memories for the current agent and project, formats them
    in the compact DSL, and respects token budget constraints.
    """

    def __init__(
        self,
        store: Optional[MemoryStore] = None,
        context_size: int = DEFAULT_CONTEXT_SIZE,
    ):
        self.store = store or MemoryStore()
        self.budget = get_memory_budget(context_size)

    def inject(
        self, agent: Union[Agent, list[Agent]], project: Optional[Project] = None,
        use_tiered_loading: bool = True
    ) -> str:
        """
        Get formatted memories for injection into context.

        With tiered loading enabled (default), loads memories by tier:
        1. CORE: Always loaded (CRITICAL emotional memories)
        2. ACTIVE: Recently accessed memories
        3. CONTEXTUAL: Project-specific memories
        4. DEEP: Not auto-loaded (available via semantic search)

        Without tiered loading, falls back to priority-based loading.

        Args:
            agent: The current agent
            project: The current project (optional)
            use_tiered_loading: Whether to use tiered loading (default: True)

        Returns:
            Formatted memory block as a string, or empty string if no memories
        """
        if isinstance(agent, Agent):
            agents = [agent]
        else:
            agents = agent

        primary_agent = agents[0]

        if use_tiered_loading:
            memories = self._load_tiered_memories(agents, project)
        else:
            memories = self._load_all_memories(agents, project)

        if not memories:
            return ""

        # Sort by importance: CRITICAL first, then by recency
        memories = self._prioritize_memories(memories)

        # Build memory block within budget
        block = MemoryBlock(
            agent_name=primary_agent.name,
            project_name=project.name if project else None,
            memories=[],
        )

        # Header/footer overhead (use estimate - it's small and constant)
        current_tokens = estimate_tokens(f"[LTM:{primary_agent.name}]\n[/LTM]")

        for memory in memories:
            # Find the agent that this memory belongs to for verification
            mem_agent = next(
                (a for a in agents if a.id == memory.agent_id), primary_agent
            )

            # Verify signature if agent has signing key and memory is signed
            if should_verify(memory, mem_agent):
                if not verify_signature(memory, mem_agent.signing_key):  # type: ignore
                    # Mark as untrusted - will show ⚠ in DSL
                    memory.signature_valid = False
                else:
                    memory.signature_valid = True

            # Use cached token count (fast) or estimate (also fast)
            memory_tokens = get_memory_tokens(memory)

            if current_tokens + memory_tokens <= self.budget:
                block.memories.append(memory)
                current_tokens += memory_tokens
                # Update last_accessed
                memory.touch()
                self.store.save_memory(memory)
            else:
                # Budget exceeded, stop adding memories
                break

        if not block.memories:
            return ""

        return block.to_dsl()

    def _load_tiered_memories(
        self, agents: list[Agent], project: Optional[Project]
    ) -> list[Memory]:
        """
        Load memories by tier: CORE -> ACTIVE -> CONTEXTUAL.

        DEEP tier is not auto-loaded (available via semantic search).
        """
        memories: list[Memory] = []
        seen_ids: set[str] = set()

        # Load tiers in order: CORE, ACTIVE, CONTEXTUAL
        # DEEP is not loaded automatically (on-demand via semantic search)
        tiers_to_load = [MemoryTier.CORE, MemoryTier.ACTIVE, MemoryTier.CONTEXTUAL]

        for tier in tiers_to_load:
            for a in agents:
                tier_memories = self.store.get_memories_by_tier(
                    agent_id=a.id,
                    tiers=[tier],
                    project_id=project.id if project else None,
                )
                for mem in tier_memories:
                    if mem.id not in seen_ids:
                        memories.append(mem)
                        seen_ids.add(mem.id)

        return memories

    def _load_all_memories(
        self, agents: list[Agent], project: Optional[Project]
    ) -> list[Memory]:
        """Load all memories without tier filtering (fallback mode)."""
        memories: list[Memory] = []

        for a in agents:
            # Get AGENT region memories (cross-project)
            agent_memories = self.store.get_memories_for_agent(
                agent_id=a.id, region=RegionType.AGENT, include_superseded=False
            )
            memories.extend(agent_memories)

            # Get PROJECT region memories (project-specific)
            if project:
                project_memories = self.store.get_memories_for_agent(
                    agent_id=a.id,
                    region=RegionType.PROJECT,
                    project_id=project.id,
                    include_superseded=False,
                )
                memories.extend(project_memories)

        return memories

    def _prioritize_memories(self, memories: list[Memory]) -> list[Memory]:
        """
        Prioritize memories for injection.

        Priority order:
        1. Impact level (CRITICAL > HIGH > MEDIUM > LOW)
        2. Recency (newer first within same impact)
        3. Kind (EMOTIONAL first, as it shapes interaction style)
        """
        impact_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        kind_order = {
            "EMOTIONAL": 0,  # Most important for interaction style
            "ARCHITECTURAL": 1,
            "LEARNINGS": 2,
            "ACHIEVEMENTS": 3,
        }

        def sort_key(m: Memory) -> tuple:
            return (
                impact_order.get(m.impact.value, 99),
                kind_order.get(m.kind.value, 99),
                -m.created_at.timestamp(),  # Negative for descending (newer first)
            )

        return sorted(memories, key=sort_key)

    def get_stats(
        self, agent: Union[Agent, list[Agent]], project: Optional[Project] = None
    ) -> dict[str, Any]:
        """Get statistics about memories for this agent/project."""
        if isinstance(agent, Agent):
            agents = [agent]
        else:
            agents = agent

        all_agent_memories = []
        all_project_memories = []

        for a in agents:
            agent_memories = self.store.get_memories_for_agent(
                agent_id=a.id, region=RegionType.AGENT, include_superseded=False
            )
            all_agent_memories.extend(agent_memories)

            if project:
                project_memories = self.store.get_memories_for_agent(
                    agent_id=a.id,
                    region=RegionType.PROJECT,
                    project_id=project.id,
                    include_superseded=False,
                )
                all_project_memories.extend(project_memories)

        # Count by priority
        priority_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for memory in all_agent_memories + all_project_memories:
            priority_counts[memory.impact.value] += 1

        return {
            "agent_memories": len(all_agent_memories),
            "project_memories": len(all_project_memories),
            "total": len(all_agent_memories) + len(all_project_memories),
            "budget_tokens": self.budget,
            "priority_counts": priority_counts,
        }
