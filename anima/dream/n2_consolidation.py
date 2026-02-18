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

from typing import TypedDict

from anima.core import Memory, MemoryKind, ImpactLevel
from anima.dream.types import N2Result, DreamConfig, SubconsciousIntegration
from anima.graph.linker import find_builds_on_candidates, find_link_candidates, LinkType
from anima.storage.sqlite import MemoryStore


class SubconsciousResult(TypedDict):
    """Result of subconscious integration phase."""

    merged: int
    linked: int
    kept: int
    integrations: list[SubconsciousIntegration]


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

    # Phase 0: Subconscious Integration
    # Check for overlap between subconscious and conscious memories
    subconscious_result = _integrate_subconscious_memories(store, agent_id, project_id, config, quiet)

    # Phase 0b: Embedding Repair
    # Re-embed any memories that lost their embedding (e.g. after a merge in cleanup).
    # Must happen before link discovery, which relies on embeddings being current.
    _repair_missing_embeddings(store, agent_id, quiet)

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
            subconscious_merged=subconscious_result["merged"],
            subconscious_linked=subconscious_result["linked"],
            subconscious_kept=subconscious_result["kept"],
            subconscious_integrations=subconscious_result["integrations"],
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
        subconscious_merged=subconscious_result["merged"],
        subconscious_linked=subconscious_result["linked"],
        subconscious_kept=subconscious_result["kept"],
        subconscious_integrations=subconscious_result["integrations"],
    )


def _repair_missing_embeddings(store: MemoryStore, agent_id: str, quiet: bool) -> None:
    """
    Re-embed memories that have no embedding stored.

    This catches memories whose embedding was lost or never computed — for example
    after a content-changing merge in cleanup.  Must run before link discovery,
    which silently skips embedding-less memories and produces an incomplete link graph.
    """
    try:
        from anima.embeddings import embed_batch

        missing = store.get_memories_without_embeddings(agent_id)
        if not missing:
            return

        if not quiet:
            print(f"   Repairing {len(missing)} memories without embeddings...")

        texts = [content for _, content in missing]
        embeddings = embed_batch(texts, quiet=True)

        for (memory_id, _), embedding in zip(missing, embeddings):
            if embedding:
                store.save_embedding(memory_id, embedding)

        if not quiet:
            print(f"   Repaired {len(missing)} embeddings")

    except Exception:
        pass  # Non-critical — re-embed command can fix manually if needed


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


def _integrate_subconscious_memories(
    store: MemoryStore,
    agent_id: str,
    project_id: Optional[str],
    config: DreamConfig,
    quiet: bool,
) -> SubconsciousResult:
    """
    Phase 0: Integrate subconscious memories with conscious ones.

    Subconscious memories are extracted by Sonnet from conversation without
    explicit saving. They may overlap with consciously saved memories.

    Strategy:
    - similarity > 0.8: Merge (supersede subconscious, it's redundant)
    - similarity 0.5-0.8: Link (BUILDS_ON, subconscious adds nuance)
    - similarity < 0.5: Keep separate (unique insight from Sonnet)

    Returns:
        Dict with counts and integration details
    """
    merged = 0
    linked = 0
    kept = 0
    integrations: list[SubconsciousIntegration] = []

    # Get all SUBCONSCIOUS memories from lookback window
    cutoff = datetime.now() - timedelta(days=config.project_lookback_days)
    all_memories = store.get_memories_for_agent(
        agent_id=agent_id,
        project_id=project_id if config.include_project_memories else None,
        include_superseded=False,
    )

    def is_recent(created_at: datetime) -> bool:
        # Handle timezone-aware vs naive datetimes
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)
        return created_at >= cutoff

    subconscious_memories = [
        m
        for m in all_memories
        if m.kind == MemoryKind.SUBCONSCIOUS and is_recent(m.created_at) and not m.superseded_by  # Not already merged
    ]

    if not subconscious_memories:
        return {"merged": merged, "linked": linked, "kept": kept, "integrations": integrations}

    if not quiet:
        print(f"   Integrating {len(subconscious_memories)} subconscious memories...")

    # Get conscious memories with embeddings for comparison
    conscious_memories = store.get_memories_with_embeddings(
        agent_id=agent_id,
        project_id=project_id if config.include_project_memories else None,
    )

    # Filter out SUBCONSCIOUS kind from candidates
    conscious_candidates = [
        m
        for m in conscious_memories
        if store.get_memory(m[0]).kind != MemoryKind.SUBCONSCIOUS  # type: ignore
    ]

    if not conscious_candidates:
        # No conscious memories to compare against
        kept = len(subconscious_memories)
        return {"merged": merged, "linked": linked, "kept": kept, "integrations": integrations}

    for subconscious_mem in subconscious_memories:
        # Get embedding for this subconscious memory
        embedding = store.get_embedding(subconscious_mem.id)
        if not embedding:
            kept += 1
            continue

        # Find nearest conscious memory
        candidates = find_link_candidates(
            source_embedding=embedding,
            candidate_memories=conscious_candidates,
            threshold=0.0,  # Get all, we'll filter by similarity
            max_links=1,
            exclude_ids={subconscious_mem.id},
        )

        if not candidates:
            kept += 1
            integrations.append(
                SubconsciousIntegration(
                    subconscious_id=subconscious_mem.id,
                    conscious_id="",
                    similarity=0.0,
                    action="kept_separate",
                )
            )
            continue

        nearest = candidates[0]
        similarity = nearest.similarity

        if similarity > 0.8:
            # High overlap - merge (supersede subconscious)
            subconscious_mem.superseded_by = nearest.memory_id
            store.save_memory(subconscious_mem)
            merged += 1
            integrations.append(
                SubconsciousIntegration(
                    subconscious_id=subconscious_mem.id,
                    conscious_id=nearest.memory_id,
                    similarity=similarity,
                    action="merged",
                )
            )
        elif similarity > 0.5:
            # Moderate overlap - create BUILDS_ON link
            store.save_link(
                source_id=subconscious_mem.id,
                target_id=nearest.memory_id,
                link_type=LinkType.BUILDS_ON.value,
                similarity=similarity,
            )
            linked += 1
            integrations.append(
                SubconsciousIntegration(
                    subconscious_id=subconscious_mem.id,
                    conscious_id=nearest.memory_id,
                    similarity=similarity,
                    action="linked",
                )
            )
        else:
            # Low overlap - keep separate (unique insight)
            kept += 1
            integrations.append(
                SubconsciousIntegration(
                    subconscious_id=subconscious_mem.id,
                    conscious_id=nearest.memory_id,
                    similarity=similarity,
                    action="kept_separate",
                )
            )

    if not quiet:
        print(f"      Merged: {merged}, Linked: {linked}, Kept: {kept}")

    return {"merged": merged, "linked": linked, "kept": kept, "integrations": integrations}
