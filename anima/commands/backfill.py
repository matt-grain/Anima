# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Backfill command - Generate embeddings and assign tiers for existing memories.

This command processes memories that don't have embeddings yet,
generates embeddings, assigns tiers, and creates semantic links.
"""

import sys
from datetime import datetime

from anima.core import (
    AgentResolver,
    ImpactLevel,
    MemoryKind,
    MemoryTier,
)
from anima.embeddings import embed_batch
from anima.graph.linker import find_link_candidates, LinkType
from anima.storage import MemoryStore
from anima.utils.terminal import safe_print, get_icon


def assign_tier(
    impact: ImpactLevel,
    kind: MemoryKind,
    last_accessed: datetime,
    created_at: datetime,
) -> MemoryTier:
    """
    Assign a tier to a memory based on its characteristics.

    Rules:
    - CORE: CRITICAL emotional memories (always loaded)
    - ACTIVE: Accessed in the last 7 days
    - CONTEXTUAL: Created in the last 30 days or HIGH impact
    - DEEP: Everything else (loaded on-demand via semantic search)
    """
    now = datetime.now()

    # Handle timezone-aware datetimes by making them naive
    if last_accessed.tzinfo is not None:
        last_accessed = last_accessed.replace(tzinfo=None)
    if created_at.tzinfo is not None:
        created_at = created_at.replace(tzinfo=None)

    days_since_access = (now - last_accessed).days
    days_since_creation = (now - created_at).days

    # CORE: CRITICAL emotional memories are always loaded
    if impact == ImpactLevel.CRITICAL and kind == MemoryKind.EMOTIONAL:
        return MemoryTier.CORE

    # ACTIVE: Recently accessed (within 7 days)
    if days_since_access <= 7:
        return MemoryTier.ACTIVE

    # CONTEXTUAL: Recent or high-impact memories
    if days_since_creation <= 30 or impact in (ImpactLevel.CRITICAL, ImpactLevel.HIGH):
        return MemoryTier.CONTEXTUAL

    # DEEP: Older, lower-impact memories (on-demand via semantic search)
    return MemoryTier.DEEP


def run(args: list[str]) -> int:
    """
    Run the backfill command.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success)
    """
    # Parse flags
    dry_run = False
    batch_size = 32
    skip_links = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--dry-run", "-n"):
            dry_run = True
        elif arg in ("--batch-size", "-b"):
            if i + 1 < len(args):
                batch_size = int(args[i + 1])
                i += 1
        elif arg in ("--skip-links",):
            skip_links = True
        elif arg in ("--help", "-h"):
            print("Usage: uv run anima backfill [OPTIONS]")
            print()
            print("Generate embeddings and assign tiers for existing memories.")
            print()
            print("Options:")
            print("  --dry-run, -n     Show what would be done without making changes")
            print("  --batch-size, -b  Number of memories to process at once (default: 32)")
            print("  --skip-links      Skip creating semantic links")
            print("  --help, -h        Show this help message")
            return 0
        i += 1

    # Resolve agent
    resolver = AgentResolver()
    agent = resolver.resolve()

    # Initialize store
    store = MemoryStore()

    # Get memories without embeddings
    memories_to_embed = store.get_memories_without_embeddings(agent_id=agent.id)

    if not memories_to_embed:
        print("No memories need embedding backfill.")
        return 0

    print(f"Found {len(memories_to_embed)} memories without embeddings.")

    if dry_run:
        print("\n[DRY RUN] Would process:")
        for mem_id, content in memories_to_embed[:10]:
            print(f"  - {mem_id[:8]}: {content[:50]}...")
        if len(memories_to_embed) > 10:
            print(f"  ... and {len(memories_to_embed) - 10} more")
        return 0

    # Process in batches
    safe_print(f"\n{get_icon('☕', '[...]')} Anima is waking up (loading embedding model)...")
    total_embedded = 0
    total_links = 0
    total_tiers_assigned = 0

    for batch_start in range(0, len(memories_to_embed), batch_size):
        batch = memories_to_embed[batch_start:batch_start + batch_size]
        texts = [content for _, content in batch]

        print(f"\nProcessing batch {batch_start // batch_size + 1}...")

        # Generate embeddings for batch
        embeddings = embed_batch(texts, quiet=True)

        # Save embeddings and assign tiers
        for (mem_id, content), embedding in zip(batch, embeddings):
            # Save embedding
            store.save_embedding(mem_id, embedding)
            total_embedded += 1

            # Get full memory to assign tier
            all_memories = store.get_memories_for_agent(agent_id=agent.id)
            memory = next((m for m in all_memories if m.id == mem_id), None)

            if memory:
                tier = assign_tier(
                    impact=memory.impact,
                    kind=memory.kind,
                    last_accessed=memory.last_accessed,
                    created_at=memory.created_at,
                )
                store.update_tier(mem_id, tier.value)
                total_tiers_assigned += 1

        # Create semantic links (if not skipped)
        if not skip_links:
            # Get all embedded memories for linking
            candidate_memories = store.get_memories_with_embeddings(agent_id=agent.id)

            for (mem_id, content), embedding in zip(batch, embeddings):
                candidates = find_link_candidates(
                    source_embedding=embedding,
                    candidate_memories=candidate_memories,
                    threshold=0.5,
                    max_links=5,
                    exclude_ids={mem_id},
                )

                for candidate in candidates:
                    store.save_link(
                        source_id=mem_id,
                        target_id=candidate.memory_id,
                        link_type=LinkType.RELATES_TO,
                        similarity=candidate.similarity,
                    )
                    total_links += 1

        safe_print(f"  {get_icon('✓', '[OK]')} Embedded {len(batch)} memories")

    safe_print(f"\n{get_icon('✅', '[OK]')} Backfill complete:")
    print(f"   - Embeddings generated: {total_embedded}")
    print(f"   - Tiers assigned: {total_tiers_assigned}")
    print(f"   - Semantic links created: {total_links}")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
