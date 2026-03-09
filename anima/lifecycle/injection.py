# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Memory injection for session start.

Retrieves relevant memories and formats them for context injection.
Respects the 10% context budget.
"""

from functools import lru_cache
from typing import Optional, TypedDict, Union, Any, cast

import tiktoken

from anima.core import (
    Memory,
    MemoryBlock,
    MemoryTier,
    RegionType,
    Agent,
    Project,
    ImpactLevel,
    verify_signature,
    should_verify,
)
from anima.storage import MemoryStore
from anima.lifecycle.session import get_previous_session_id
from anima.lifecycle.project_context import ProjectFingerprint
from anima.security.cognitive_auth import (
    get_session_trust,
    get_memory_access_filter,
)


class InjectionStats(TypedDict):
    """Statistics about memory injection."""

    agent_memories: int
    project_memories: int
    total: int
    budget_tokens: int
    priority_counts: dict[str, int]  # CRITICAL, HIGH, MEDIUM, LOW


class BucketStats(TypedDict):
    """Statistics about memory bucket usage."""

    agent_critical: int
    agent_high: int
    agent_medium: int
    agent_low: int
    project_critical: int
    project_high: int
    project_medium: int
    project_low: int
    overflow: int


class InjectionResult(TypedDict):
    """Result of memory injection including deferred memories."""

    dsl: str  # Formatted memory block
    injected_ids: list[str]  # IDs of memories that were injected
    deferred_ids: list[str]  # IDs of memories that didn't fit (for lazy loading)
    deferred_count: int  # Count of deferred memories
    bucket_stats: BucketStats  # Memory counts per bucket


# Default values (can be overridden via ~/.anima/config.json)
DEFAULT_CONTEXT_SIZE = 200_000  # tokens (Claude's standard context window)
MEMORY_BUDGET_PERCENT = 0.10  # 10% of context
DEFAULT_MAX_OUTPUT_BYTES = 25_000  # ~25KB max for hook output
DEFAULT_MAX_MEMORY_CHARS = 500  # Max chars per memory content


def _get_budget_config() -> tuple[int, float]:
    """Get budget settings from config."""
    from anima.core.config import get_config

    config = get_config()
    return config.budget.context_size, config.budget.context_percent


def _get_hook_config() -> tuple[int, int]:
    """Get hook output limits from config."""
    from anima.core.config import get_config

    config = get_config()
    return config.hook.max_output_bytes, config.hook.max_memory_chars


def _get_bucket_config() -> dict[str, float]:
    """Get injection bucket percentages from config."""
    from anima.core.config import get_config

    config = get_config()
    return {
        "agent_critical": config.injection_buckets.agent_critical,
        "agent_high": config.injection_buckets.agent_high,
        "agent_medium": config.injection_buckets.agent_medium,
        "project_critical": config.injection_buckets.project_critical,
        "project_high": config.injection_buckets.project_high,
        "project_medium": config.injection_buckets.project_medium,
    }


def truncate_content(content: str, max_chars: int) -> str:
    """Truncate content to max_chars, preserving sentence boundaries if possible."""
    if len(content) <= max_chars:
        return content

    # Try to truncate at sentence boundary
    truncated = content[: max_chars - 4]  # Leave room for "..."
    last_period = truncated.rfind(". ")
    if last_period > max_chars // 2:
        return truncated[: last_period + 1] + "..."
    return truncated + "..."


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
        # Load hook output limits
        self.max_output_bytes, self.max_memory_chars = _get_hook_config()

    def inject(
        self,
        agent: Union[Agent, list[Agent]],
        project: Optional[Project] = None,
        use_tiered_loading: bool = True,
        project_dir: Optional[Any] = None,
    ) -> str:
        """
        Get formatted memories for injection into context.

        With tiered loading enabled (default), loads memories with
        AGENT/PROJECT distinction (Phase 3A):
        - AGENT memories: Tier-based (CORE → ACTIVE → CONTEXTUAL)
        - PROJECT memories: Semantic matching against project fingerprint

        This ensures project rules persist regardless of age, while
        AGENT memories respect temporal recency.

        Args:
            agent: The current agent
            project: The current project (optional)
            use_tiered_loading: Whether to use tiered loading (default: True)
            project_dir: Project directory for semantic fingerprinting

        Returns:
            Formatted memory block as a string, or empty string if no memories
        """
        result = self.inject_with_deferred(agent, project, use_tiered_loading, project_dir)
        return result["dsl"]

    def inject_with_deferred(
        self,
        agent: Union[Agent, list[Agent]],
        project: Optional[Project] = None,
        use_tiered_loading: bool = True,
        project_dir: Optional[Any] = None,
    ) -> InjectionResult:
        """
        Get formatted memories with tracking of deferred memories for lazy loading.

        Same as inject() but returns additional info about memories that didn't
        fit in the initial budget, enabling lazy loading after first message.

        Args:
            agent: The current agent
            project: The current project (optional)
            use_tiered_loading: Whether to use tiered loading (default: True)
            project_dir: Project directory for semantic fingerprinting

        Returns:
            InjectionResult with dsl, injected_ids, deferred_ids, deferred_count
        """
        if isinstance(agent, Agent):
            agents = [agent]
        else:
            agents = agent

        primary_agent = agents[0]

        if use_tiered_loading:
            memories = self._load_tiered_memories(agents, project, project_dir)
        else:
            memories = self._load_all_memories(agents, project)

        if not memories:
            return InjectionResult(
                dsl="",
                injected_ids=[],
                deferred_ids=[],
                deferred_count=0,
                bucket_stats=BucketStats(
                    agent_critical=0,
                    agent_high=0,
                    agent_medium=0,
                    agent_low=0,
                    project_critical=0,
                    project_high=0,
                    project_medium=0,
                    project_low=0,
                    overflow=0,
                ),
            )

        # Apply trust-based filters (cognitive auth v0.14.3)
        memories, trust_filtered = self._apply_trust_filters(memories)

        # Prioritize using token buckets (sorts by bucket priority, then recency)
        memories, bucket_counts = self._prioritize_memories(memories)

        # Build memory block within budget
        block = MemoryBlock(
            agent_name=primary_agent.name,
            project_name=project.name if project else None,
            memories=[],
        )

        # Header/footer overhead (use estimate - it's small and constant)
        current_tokens = estimate_tokens(f"[LTM:{primary_agent.name}]\n[/LTM]")

        # Track bytes for hook output limit
        current_bytes = len(f"[LTM:{primary_agent.name}]\n[/LTM]".encode("utf-8"))

        # Keep separate list for display (truncated) vs storage (original)
        display_memories: list[Memory] = []
        injected_ids: list[str] = []
        deferred_ids: list[str] = []
        budget_exceeded = False

        for memory in memories:
            # Find the agent that this memory belongs to for verification
            mem_agent = next((a for a in agents if a.id == memory.agent_id), primary_agent)

            # Verify signature if agent has signing key and memory is signed
            if should_verify(memory, mem_agent):
                if not verify_signature(memory, mem_agent.signing_key):  # type: ignore
                    # Mark as untrusted - will show ⚠ in DSL
                    memory.signature_valid = False
                else:
                    memory.signature_valid = True

            # Create display copy with truncated content if needed
            from copy import copy

            display_mem = copy(memory)
            if len(display_mem.content) > self.max_memory_chars:
                display_mem.content = truncate_content(display_mem.content, self.max_memory_chars)

            # Use cached token count (fast) or estimate (also fast)
            memory_tokens = get_memory_tokens(display_mem)

            # Calculate bytes for this memory's DSL
            memory_dsl = display_mem.to_dsl() + "\n"
            memory_bytes = len(memory_dsl.encode("utf-8"))

            # Check both token budget and byte limit
            if not budget_exceeded and current_tokens + memory_tokens <= self.budget and current_bytes + memory_bytes <= self.max_output_bytes:
                display_memories.append(display_mem)
                injected_ids.append(memory.id)
                current_tokens += memory_tokens
                current_bytes += memory_bytes
                # Update last_accessed on original
                memory.touch()
                self.store.save_memory(memory)
            else:
                # Budget exceeded, track as deferred
                budget_exceeded = True
                deferred_ids.append(memory.id)

        block.memories = display_memories

        dsl = block.to_dsl() if block.memories else ""

        return InjectionResult(
            dsl=dsl,
            injected_ids=injected_ids,
            deferred_ids=deferred_ids,
            deferred_count=len(deferred_ids),
            bucket_stats=bucket_counts,
        )

    def _load_tiered_memories(
        self,
        agents: list[Agent],
        project: Optional[Project],
        project_dir: Optional[Any] = None,
    ) -> list[Memory]:
        """
        Load memories with AGENT/PROJECT distinction (Phase 3A).

        Key insight from Matt: AGENT memories benefit from temporal recency
        (I evolve over time), but PROJECT memories need semantic relevance
        (project rules persist regardless of age).

        Loading strategy:
        - AGENT memories: Tier-based loading (CORE → ACTIVE → CONTEXTUAL)
        - PROJECT memories: Semantic matching against project fingerprint

        This ensures a project constraint like "always call Task-Review"
        surfaces 2 months later just as readily as 2 days later.
        """
        memories: list[Memory] = []
        seen_ids: set[str] = set()

        # 0. Load WIP memories FIRST - these signal post-compact state
        # WIP memories bypass tier logic and are always loaded with highest priority
        for a in agents:
            wip_memories = self.store.get_memories_by_impact(
                agent_id=a.id,
                impact=ImpactLevel.WIP,
                project_id=project.id if project else None,
            )
            for mem in wip_memories:
                if mem.id not in seen_ids:
                    memories.append(mem)
                    seen_ids.add(mem.id)

        # 1. Load AGENT-scoped memories by tier (temporal/recency matters)
        tiers_to_load = [MemoryTier.CORE, MemoryTier.ACTIVE, MemoryTier.CONTEXTUAL]

        for tier in tiers_to_load:
            for a in agents:
                tier_memories = self.store.get_memories_by_tier(
                    agent_id=a.id,
                    tiers=[tier],
                    region=RegionType.AGENT,  # Only AGENT scope
                )
                for mem in tier_memories:
                    if mem.id not in seen_ids:
                        memories.append(mem)
                        seen_ids.add(mem.id)

        # 2. Load PROJECT-scoped memories semantically (relevance matters, not time)
        if project and project_dir:
            project_memories = self._load_semantic_project_memories(agents, project, project_dir, seen_ids)
            memories.extend(project_memories)
        elif project:
            # Fallback: load PROJECT memories by tier if no project_dir
            for tier in tiers_to_load:
                for a in agents:
                    tier_memories = self.store.get_memories_by_tier(
                        agent_id=a.id,
                        tiers=[tier],
                        project_id=project.id,
                        region=RegionType.PROJECT,
                    )
                    for mem in tier_memories:
                        if mem.id not in seen_ids:
                            memories.append(mem)
                            seen_ids.add(mem.id)

        # 3. Previous session continuity (for "as we discussed" references)
        if project:
            prev_session_memories = self._load_previous_session_memories(agents, project, seen_ids)
            memories.extend(prev_session_memories)

        return memories

    def _load_semantic_project_memories(
        self,
        agents: list[Agent],
        project: Project,
        project_dir: Any,
        seen_ids: set[str],
    ) -> list[Memory]:
        """
        Load PROJECT memories using semantic fingerprint matching.

        Builds a fingerprint from README + recent commits, then finds
        PROJECT memories that are semantically relevant regardless of age.
        """
        from pathlib import Path

        memories: list[Memory] = []

        try:
            # Build project fingerprint
            if isinstance(project_dir, str):
                project_dir = Path(project_dir)

            fingerprint = ProjectFingerprint.from_directory(project_dir, quiet=True)

            # Find relevant PROJECT memories for each agent
            for agent in agents:
                relevant = fingerprint.find_relevant_memories(
                    store=self.store,
                    agent_id=agent.id,
                    project_id=project.id,
                    limit=30,  # Fetch more, will be filtered by budget later
                    quiet=True,
                )
                for mem in relevant:
                    if mem.id not in seen_ids:
                        memories.append(mem)
                        seen_ids.add(mem.id)

        except Exception as e:
            # If fingerprinting fails, fall back to tier-based loading
            from loguru import logger

            logger.debug(f"Semantic project loading failed, using tier-based fallback: {e}")

        return memories

    def _load_previous_session_memories(
        self,
        agents: list[Agent],
        project: Project,
        seen_ids: set[str],
    ) -> list[Memory]:
        """
        Load memories from the previous session for continuity.

        This enables natural references like "as we discussed last session"
        by ensuring the previous session's context is available.

        Only loads project-specific memories from the previous session,
        not AGENT-region memories (those are already in tiers).
        """
        prev_session_id = get_previous_session_id()
        if not prev_session_id:
            return []

        memories: list[Memory] = []

        for agent in agents:
            session_memories = self.store.get_memories_by_session(
                session_id=prev_session_id,
                agent_id=agent.id,
                project_id=project.id,
            )
            for mem in session_memories:
                if mem.id not in seen_ids:
                    memories.append(mem)
                    seen_ids.add(mem.id)

        return memories

    def _load_all_memories(self, agents: list[Agent], project: Optional[Project]) -> list[Memory]:
        """Load all memories without tier filtering (fallback mode)."""
        memories: list[Memory] = []

        for a in agents:
            # Get AGENT region memories (cross-project)
            agent_memories = self.store.get_memories_for_agent(agent_id=a.id, region=RegionType.AGENT, include_superseded=False)
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

    def _apply_trust_filters(self, memories: list[Memory]) -> tuple[list[Memory], int]:
        """
        Apply cognitive auth trust filters to memories.

        Filters memories based on current session trust level (v0.14.3).
        This implements the "trust-aware injection" concept: don't load
        sensitive memories until trust is established.

        Trust levels and filters:
        - FULL (>= 0.8): No filtering, all memories accessible
        - PARTIAL (>= 0.5): Recent memories only (7 days)
        - MINIMAL (>= 0.3): CORE tier only
        - SUSPICIOUS (< 0.3): CORE + CRITICAL only, exclude sensitive

        Args:
            memories: List of memories to filter

        Returns:
            Tuple of (filtered_memories, count_filtered)
        """
        from anima.core import MemoryKind

        trust = get_session_trust()
        filters = get_memory_access_filter(trust)

        if not filters:
            # FULL trust - no filtering
            return memories, 0

        filtered: list[Memory] = []
        removed_count = 0

        for mem in memories:
            keep = True

            # CRITICAL memories always pass (they're the soul)
            is_critical = mem.impact == ImpactLevel.CRITICAL

            # Filter by recency (PARTIAL trust) - but CRITICAL bypasses
            if "since" in filters and not is_critical:
                since = filters["since"]
                mem_time = mem.created_at
                if mem_time < since:
                    keep = False

            # Filter by tier (MINIMAL/SUSPICIOUS trust) - CRITICAL bypasses
            if keep and "tier" in filters and not is_critical:
                required_tier = filters["tier"]
                # CORE tier requires CRITICAL + EMOTIONAL
                is_core_tier = mem.impact == ImpactLevel.CRITICAL and mem.kind == MemoryKind.EMOTIONAL
                if required_tier == "CORE" and not is_core_tier:
                    keep = False

            # Filter by impact (SUSPICIOUS trust)
            if keep and "impact_min" in filters:
                required_impact = filters["impact_min"]
                if required_impact == "CRITICAL" and mem.impact != ImpactLevel.CRITICAL:
                    keep = False

            # Filter out sensitive content markers (SUSPICIOUS trust)
            if keep and filters.get("exclude_sensitive"):
                sensitive_markers = ["password", "key", "secret", "credential", "token"]
                if any(marker in mem.content.lower() for marker in sensitive_markers):
                    keep = False

            if keep:
                filtered.append(mem)
            else:
                removed_count += 1

        return filtered, removed_count

    def _prioritize_memories(self, memories: list[Memory]) -> tuple[list[Memory], BucketStats]:
        """
        Prioritize memories for injection using token buckets.

        Each bucket (region + impact) gets a percentage of the total budget.
        Within each bucket, memories are sorted by recency (newest first).

        This ensures recent HIGH memories load even when there are many old CRITICAL.

        Bucket order:
        1. WIP (always first, no budget limit)
        2. AGENT CRITICAL (newest first)
        3. PROJECT CRITICAL (newest first)
        4. AGENT HIGH (newest first)
        5. PROJECT HIGH (newest first)
        6. AGENT MEDIUM (newest first)
        7. PROJECT MEDIUM (newest first)
        8. LOW (any remaining budget)
        """
        bucket_config = _get_bucket_config()

        # Separate memories into buckets
        buckets: dict[str, list[Memory]] = {
            "wip": [],
            "agent_critical": [],
            "agent_high": [],
            "agent_medium": [],
            "agent_low": [],
            "project_critical": [],
            "project_high": [],
            "project_medium": [],
            "project_low": [],
        }

        for mem in memories:
            impact = mem.impact.value.lower()
            is_project = mem.region == RegionType.PROJECT

            if impact == "wip":
                buckets["wip"].append(mem)
            elif is_project:
                buckets[f"project_{impact}"].append(mem)
            else:
                buckets[f"agent_{impact}"].append(mem)

        # Sort each bucket by recency (newest first), then by kind
        kind_order = {
            "EMOTIONAL": 0,
            "INTROSPECT": 1,
            "DREAM": 2,
            "SUBCONSCIOUS": 3,
            "ARCHITECTURAL": 4,
            "LEARNINGS": 5,
            "ACHIEVEMENTS": 6,
        }

        def recency_sort(m: Memory) -> tuple:
            return (
                kind_order.get(m.kind.value, 99),
                -m.created_at.timestamp(),
            )

        for bucket_name in buckets:
            buckets[bucket_name].sort(key=recency_sort)

        # Calculate token budgets for each bucket
        total_budget = self.budget
        bucket_budgets = {
            "wip": total_budget,  # WIP always loads fully
            "agent_critical": int(total_budget * bucket_config["agent_critical"]),
            "agent_high": int(total_budget * bucket_config["agent_high"]),
            "agent_medium": int(total_budget * bucket_config["agent_medium"]),
            "project_critical": int(total_budget * bucket_config["project_critical"]),
            "project_high": int(total_budget * bucket_config["project_high"]),
            "project_medium": int(total_budget * bucket_config["project_medium"]),
            "agent_low": 0,  # LOW gets remaining budget
            "project_low": 0,
        }

        # Fill buckets in priority order, tracking total tokens used
        result: list[Memory] = []
        total_tokens_used = 0
        overflow: list[Memory] = []  # Memories that didn't fit their bucket
        overflow_ids: set[str] = set()  # O(1) lookup for overflow membership
        bucket_counts: dict[str, int] = {
            "agent_critical": 0,
            "agent_high": 0,
            "agent_medium": 0,
            "agent_low": 0,
            "project_critical": 0,
            "project_high": 0,
            "project_medium": 0,
            "project_low": 0,
            "overflow": 0,
        }

        bucket_order = [
            "wip",
            "agent_critical",
            "project_critical",
            "agent_high",
            "project_high",
            "agent_medium",
            "project_medium",
        ]

        for bucket_name in bucket_order:
            bucket_budget = bucket_budgets[bucket_name]
            bucket_tokens = 0

            for mem in buckets[bucket_name]:
                mem_tokens = get_memory_tokens(mem)

                # WIP bucket has no limit, others respect their budget
                if bucket_name == "wip" or bucket_tokens + mem_tokens <= bucket_budget:
                    result.append(mem)
                    bucket_tokens += mem_tokens
                    total_tokens_used += mem_tokens
                    # Track count (WIP goes to agent_critical for stats)
                    if bucket_name == "wip":
                        bucket_counts["agent_critical"] += 1
                    else:
                        bucket_counts[bucket_name] += 1
                else:
                    # Didn't fit in bucket, add to overflow
                    overflow.append(mem)
                    overflow_ids.add(mem.id)

        # Fill LOW buckets and overflow with remaining budget
        remaining_budget = total_budget - total_tokens_used
        low_and_overflow = buckets["agent_low"] + buckets["project_low"] + overflow

        # Sort by recency
        low_and_overflow.sort(key=recency_sort)

        for mem in low_and_overflow:
            mem_tokens = get_memory_tokens(mem)
            if mem_tokens <= remaining_budget:
                result.append(mem)
                remaining_budget -= mem_tokens
                # Track which bucket it came from
                if mem.id in overflow_ids:
                    bucket_counts["overflow"] += 1
                elif mem.region == RegionType.PROJECT:
                    bucket_counts["project_low"] += 1
                else:
                    bucket_counts["agent_low"] += 1

        return result, cast(BucketStats, bucket_counts)

    def load_deferred_memories(
        self,
        deferred_ids: list[str],
        agent: Union[Agent, list[Agent]],
        project: Optional[Project] = None,
    ) -> str:
        """
        Load deferred memories that didn't fit in the initial injection.

        Called by /load-context to stream additional memories after the
        initial greeting exchange.

        Args:
            deferred_ids: List of memory IDs that were deferred
            agent: The current agent (for block formatting)
            project: The current project (optional)

        Returns:
            Formatted memory block as a string
        """
        if not deferred_ids:
            return ""

        if isinstance(agent, Agent):
            agents = [agent]
        else:
            agents = agent

        primary_agent = agents[0]

        # Load memories by ID
        memories: list[Memory] = []
        for mem_id in deferred_ids:
            memory = self.store.get_memory(mem_id)
            if memory:
                memories.append(memory)

        if not memories:
            return ""

        # Build memory block (no budget limit for deferred - we want them all)
        block = MemoryBlock(
            agent_name=primary_agent.name,
            project_name=project.name if project else None,
            memories=[],
        )

        for memory in memories:
            # Find the agent for verification
            mem_agent = next((a for a in agents if a.id == memory.agent_id), primary_agent)

            # Verify signature
            if should_verify(memory, mem_agent):
                if not verify_signature(memory, mem_agent.signing_key):  # type: ignore
                    memory.signature_valid = False
                else:
                    memory.signature_valid = True

            # Truncate for display
            from copy import copy

            display_mem = copy(memory)
            if len(display_mem.content) > self.max_memory_chars:
                display_mem.content = truncate_content(display_mem.content, self.max_memory_chars)

            block.memories.append(display_mem)

            # Update last_accessed
            memory.touch()
            self.store.save_memory(memory)

        return block.to_dsl() if block.memories else ""

    def get_stats(self, agent: Union[Agent, list[Agent]], project: Optional[Project] = None) -> dict[str, Any]:
        """Get statistics about memories for this agent/project."""
        if isinstance(agent, Agent):
            agents = [agent]
        else:
            agents = agent

        all_agent_memories = []
        all_project_memories = []

        for a in agents:
            agent_memories = self.store.get_memories_for_agent(agent_id=a.id, region=RegionType.AGENT, include_superseded=False)
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
        priority_counts = {"WIP": 0, "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for memory in all_agent_memories + all_project_memories:
            if memory.impact.value in priority_counts:
                priority_counts[memory.impact.value] += 1

        return {
            "agent_memories": len(all_agent_memories),
            "project_memories": len(all_project_memories),
            "total": len(all_agent_memories) + len(all_project_memories),
            "budget_tokens": self.budget,
            "priority_counts": priority_counts,
        }
