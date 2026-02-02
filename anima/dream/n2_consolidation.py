# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
N2 - Memory Consolidation Stage

Character: Systematic, thorough, housekeeping. The librarian organizing shelves.

Functions:
1. Semantic link discovery - Find BUILDS_ON/RELATES_TO connections not yet linked
2. Impact adjustment - Review and adjust impact levels based on link topology
"""

import time
from datetime import datetime, timedelta
from typing import Optional

from anima.core import Memory, ImpactLevel
from anima.dream.types import N2Result, DreamConfig
from anima.graph.linker import find_builds_on_candidates, LinkType
from anima.storage.sqlite import MemoryStore


def run_n2_consolidation(
    store: MemoryStore,
    agent_id: str,
    project_id: Optional[str] = None,
    config: Optional[DreamConfig] = None,
    quiet: bool = False,
) -> N2Result:
    """
    Run N2 consolidation stage.

    1. Load all memories with embeddings and temporal context
    2. For each memory, find potential BUILDS_ON links not yet recorded
    3. Save new links
    4. Review impact levels based on link topology

    Args:
        store: Memory storage interface
        agent_id: Agent to process memories for
        project_id: Optional project filter
        config: Dream configuration
        quiet: Suppress output

    Returns:
        N2Result with statistics about the consolidation
    """
    config = config or DreamConfig()
    start_time = time.time()

    if not quiet:
        print("N2: Consolidating memories...")

    # Get memories with temporal context for BUILDS_ON detection
    memories_with_context = _get_processable_memories(store, agent_id, project_id, config)

    if not quiet:
        print(f"   Found {len(memories_with_context)} memories with embeddings")

    if len(memories_with_context) == 0:
        return N2Result(
            new_links_found=0,
            links=[],
            impact_adjustments=[],
            duration_seconds=time.time() - start_time,
            memories_processed=0,
        )

    # Track results
    new_links: list[tuple[str, str, str, float]] = []
    impact_adjustments: list[tuple[str, str, str]] = []

    # Phase 1: Link Discovery
    # Get existing links to avoid duplicates
    existing_links = _get_all_existing_links(store, memories_with_context)

    if not quiet:
        print(f"   Found {len(existing_links)} existing links")

    processed = 0
    for i, (memory_id, content, embedding, created_at, session_id) in enumerate(memories_with_context):
        if processed >= config.n2_process_limit:
            break

        if embedding is None:
            continue

        # Find BUILDS_ON candidates for this memory
        other_memories = [m for m in memories_with_context if m[0] != memory_id]

        candidates = find_builds_on_candidates(
            source_content=content,
            source_embedding=embedding,
            source_session_id=session_id,
            source_created=created_at,
            candidate_memories=other_memories,
            similarity_threshold=config.n2_similarity_threshold,
            max_candidates=config.n2_max_links_per_memory,
        )

        for candidate in candidates:
            link_key = (memory_id, candidate.memory_id)
            reverse_key = (candidate.memory_id, memory_id)

            # Skip if link already exists in either direction
            if link_key in existing_links or reverse_key in existing_links:
                continue

            # Determine link type based on confidence
            link_type = LinkType.BUILDS_ON if candidate.confidence >= 0.5 else LinkType.RELATES_TO

            # Save the new link
            store.save_link(
                source_id=memory_id,
                target_id=candidate.memory_id,
                link_type=link_type.value,
                similarity=candidate.similarity,
            )

            new_links.append((memory_id, candidate.memory_id, link_type.value, candidate.similarity))
            existing_links.add(link_key)

        processed += 1

    if not quiet:
        print(f"   Discovered {len(new_links)} new links")

    # Phase 2: Impact Adjustment
    # Memories with many incoming links might deserve higher impact
    link_counts = _count_incoming_links(store, [m[0] for m in memories_with_context])

    for memory_id, count in link_counts.items():
        memory = store.get_memory(memory_id)
        if not memory:
            continue

        suggested_impact = _suggest_impact_from_topology(memory, count)

        if suggested_impact and suggested_impact != memory.impact:
            old_impact = memory.impact
            memory.impact = suggested_impact
            store.save_memory(memory)
            impact_adjustments.append((memory_id, old_impact.value, suggested_impact.value))

    if not quiet:
        print(f"   Adjusted {len(impact_adjustments)} impact levels")

    duration = time.time() - start_time

    return N2Result(
        new_links_found=len(new_links),
        links=new_links,
        impact_adjustments=impact_adjustments,
        duration_seconds=duration,
        memories_processed=processed,
    )


def _get_processable_memories(
    store: MemoryStore,
    agent_id: str,
    project_id: Optional[str],
    config: DreamConfig,
) -> list[tuple[str, str, list[float], datetime, Optional[str]]]:
    """
    Get memories with embeddings and temporal context for processing.

    Returns:
        List of (memory_id, content, embedding, created_at, session_id) tuples
    """
    # Use the store's temporal context method
    all_memories = store.get_memories_with_temporal_context(
        agent_id=agent_id,
        project_id=project_id if config.include_project_memories else None,
        include_superseded=False,
    )

    # Filter by lookback window
    cutoff = datetime.now() - timedelta(days=config.project_lookback_days)

    def is_recent(created_at: datetime) -> bool:
        # Handle timezone-aware vs naive datetimes
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)
        return created_at >= cutoff

    recent_memories = [m for m in all_memories if is_recent(m[3])]  # m[3] = created_at

    return recent_memories


def _get_all_existing_links(
    store: MemoryStore,
    memories: list[tuple[str, str, list[float], datetime, Optional[str]]],
) -> set[tuple[str, str]]:
    """
    Get all existing link pairs to avoid creating duplicates.

    Returns:
        Set of (source_id, target_id) tuples
    """
    existing = set()

    for memory_id, _, _, _, _ in memories:
        links = store.get_links_for_memory(memory_id)
        for source_id, target_id, _, _ in links:
            existing.add((source_id, target_id))

    return existing


def _count_incoming_links(
    store: MemoryStore,
    memory_ids: list[str],
) -> dict[str, int]:
    """
    Count incoming links per memory.

    Returns:
        Dict mapping memory_id to incoming link count
    """
    counts: dict[str, int] = {}

    for memory_id in memory_ids:
        links = store.get_links_for_memory(memory_id)
        # Count links where this memory is the TARGET (incoming)
        incoming = sum(1 for _, target_id, _, _ in links if target_id == memory_id)
        if incoming > 0:
            counts[memory_id] = incoming

    return counts


def _suggest_impact_from_topology(
    memory: Memory,
    incoming_link_count: int,
) -> Optional[ImpactLevel]:
    """
    Suggest impact adjustment based on link topology.

    Heuristics:
    - Many incoming links (>=10) suggests HIGH importance (hub memory)
    - Moderate links (>=5) suggests MEDIUM importance
    - CRITICAL memories are never changed
    - Only upgrade, never downgrade (conservative approach)

    Args:
        memory: The memory to evaluate
        incoming_link_count: Number of memories that link TO this one

    Returns:
        Suggested new ImpactLevel, or None if no change needed
    """
    # Never change CRITICAL - these are core identity/relationship memories
    if memory.impact == ImpactLevel.CRITICAL:
        return None

    # Hub detection: many memories reference this one
    if incoming_link_count >= 10 and memory.impact in (
        ImpactLevel.LOW,
        ImpactLevel.MEDIUM,
    ):
        return ImpactLevel.HIGH

    if incoming_link_count >= 5 and memory.impact == ImpactLevel.LOW:
        return ImpactLevel.MEDIUM

    return None
