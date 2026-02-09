# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
re-embed command - Refresh embeddings for memories whose semantic neighborhoods may have drifted.

Based on Dynamic Cueing Hypothesis research: memory engrams evolve over time,
so effective retrieval cues must align with the CURRENT state of the memory,
not just the originally encoded information.
"""

import argparse
import sys
import time
from datetime import datetime

from anima.core import AgentResolver
from anima.embeddings import embed_text, embed_batch
from anima.graph.linker import find_link_candidates, LinkType
from anima.storage import MemoryStore
from anima.utils.terminal import get_icon


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0

    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def compute_drift(old_embedding: list[float], new_embedding: list[float]) -> float:
    """
    Compute drift between old and new embeddings.

    Returns a value between 0 (no drift) and 1 (completely different).
    """
    similarity = cosine_similarity(old_embedding, new_embedding)
    return 1.0 - similarity


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the re-embed command."""
    parser = argparse.ArgumentParser(
        prog="uv run anima re-embed",
        description="Refresh embeddings for memories whose semantic neighborhoods may have drifted.",
        epilog="Based on Dynamic Cueing Hypothesis: memory engrams evolve over time.",
    )

    # Check mode
    parser.add_argument(
        "--outdated",
        action="store_true",
        help="Check only: report which memories have drifted and may need refresh (no changes made)",
    )

    # Filters
    parser.add_argument(
        "--all",
        action="store_true",
        help="Re-embed ALL memories (full refresh)",
    )
    parser.add_argument(
        "--older-than",
        type=int,
        metavar="DAYS",
        help="Re-embed memories with embeddings older than N days",
    )
    parser.add_argument(
        "--drift-threshold",
        type=float,
        default=0.1,
        metavar="FLOAT",
        help="Re-embed only if drift > threshold (default: 0.1)",
    )

    # Options
    parser.add_argument(
        "--update-links",
        action="store_true",
        help="Also refresh RELATES_TO links based on new embeddings",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be re-embedded without doing it",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output",
    )

    return parser


def run(args: list[str]) -> int:
    """Run the re-embed command."""
    parser = create_parser()

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        return 0

    # Initialize
    store = MemoryStore()
    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()

    # Get all memories with embeddings
    all_memories = store.get_memories_for_agent(
        agent_id=agent.id,
        project_id=project.id,
        include_superseded=False,
    )

    # Track stats
    total_memories = len(all_memories)
    with_embeddings = 0
    missing_embeddings = 0
    outdated_memories = []

    if parsed.outdated:
        # Check mode: analyze all memories and report drift
        if not parsed.quiet:
            print("Checking memory embedding freshness...\n")

        for memory in all_memories:
            old_embedding = store.get_embedding(memory.id)

            if not old_embedding:
                missing_embeddings += 1
                continue

            with_embeddings += 1

            # Generate fresh embedding and compare
            new_embedding = embed_text(memory.content, quiet=True)
            drift = compute_drift(old_embedding, new_embedding)

            # Calculate age in days (handle timezone-aware datetimes)
            now = datetime.now()
            created = memory.created_at
            if created.tzinfo is not None:
                created = created.replace(tzinfo=None)
            age_days = (now - created).days

            if drift > parsed.drift_threshold:
                outdated_memories.append(
                    {
                        "id": memory.id[:8],
                        "content": memory.content[:50] + "..." if len(memory.content) > 50 else memory.content,
                        "drift": drift,
                        "age": age_days,
                    }
                )

        # Report
        if outdated_memories:
            print(f"Outdated embeddings (drift > {parsed.drift_threshold}):")
            for m in sorted(outdated_memories, key=lambda x: -x["drift"]):
                icon = get_icon("🔴", "[!]") if m["drift"] > 0.2 else get_icon("🟡", "[~]")
                print(f"  {icon} {m['id']}: {m['content']} (drift: {m['drift']:.2f}, age: {m['age']}d)")
            print()

        print("Summary:")
        print(f"  Total memories: {total_memories}")
        print(f"  With embeddings: {with_embeddings}")
        print(f"  Missing embeddings: {missing_embeddings}")
        print(f"  Outdated (drift > {parsed.drift_threshold}): {len(outdated_memories)}")
        print(f"  Fresh: {with_embeddings - len(outdated_memories)}")

        if outdated_memories or missing_embeddings:
            print()
            if missing_embeddings:
                print(f"Recommendation: Run 'uv run anima re-embed --all' to embed {missing_embeddings} memories without embeddings.")
            elif outdated_memories:
                print(f"Recommendation: Run 'uv run anima re-embed --drift-threshold {parsed.drift_threshold}' to refresh {len(outdated_memories)} memories.")

        return 0

    # Re-embed mode: apply filters and refresh
    memories_to_process = []

    for memory in all_memories:
        old_embedding = store.get_embedding(memory.id)

        # Apply filters
        if parsed.all:
            memories_to_process.append((memory, old_embedding))
        elif parsed.older_than:
            now = datetime.now()
            created = memory.created_at
            if created.tzinfo is not None:
                created = created.replace(tzinfo=None)
            age_days = (now - created).days
            if age_days >= parsed.older_than:
                memories_to_process.append((memory, old_embedding))
        elif old_embedding:
            # Default: check drift for memories with embeddings
            new_embedding = embed_text(memory.content, quiet=True)
            drift = compute_drift(old_embedding, new_embedding)
            if drift > parsed.drift_threshold:
                memories_to_process.append((memory, old_embedding))
        else:
            # No embedding yet - include if --all or default behavior
            memories_to_process.append((memory, None))

    if not memories_to_process:
        if not parsed.quiet:
            print("No memories need re-embedding.")
        return 0

    if parsed.dry_run:
        print(f"Would re-embed {len(memories_to_process)} memories:")
        for memory, _ in memories_to_process[:10]:
            print(f"  - {memory.id[:8]}: {memory.content[:50]}...")
        if len(memories_to_process) > 10:
            print(f"  ... and {len(memories_to_process) - 10} more")
        return 0

    # Actually re-embed
    if not parsed.quiet:
        print(f"Re-embedding {len(memories_to_process)} memories...")

    start_time = time.time()
    re_embedded = 0
    drift_detected = 0
    links_added = 0
    links_removed = 0

    # Batch embed for efficiency
    texts = [m.content for m, _ in memories_to_process]
    new_embeddings = embed_batch(texts, quiet=parsed.quiet)

    for i, (memory, old_embedding) in enumerate(memories_to_process):
        new_embedding = new_embeddings[i]

        # Calculate drift if we had an old embedding
        if old_embedding:
            drift = compute_drift(old_embedding, new_embedding)
            if drift > parsed.drift_threshold:
                drift_detected += 1

        # Save new embedding
        store.save_embedding(memory.id, new_embedding)
        re_embedded += 1

        # Update links if requested
        if parsed.update_links:
            # Get all memories with embeddings for link candidates
            candidate_memories = store.get_memories_with_embeddings(
                agent_id=agent.id,
                project_id=project.id if memory.region.value == "PROJECT" else None,
            )

            if candidate_memories:
                # Find new links
                candidates = find_link_candidates(
                    source_embedding=new_embedding,
                    candidate_memories=candidate_memories,
                    threshold=0.5,
                    max_links=5,
                    exclude_ids={memory.id},
                )

                # Get existing links (returns list of (source_id, target_id, link_type, similarity) tuples)
                existing_links = store.get_links_for_memory(memory.id)
                # Filter to RELATES_TO links where this memory is the source
                existing_targets = {target_id for source_id, target_id, link_type, _ in existing_links if source_id == memory.id and link_type == LinkType.RELATES_TO.value}
                new_targets = {c.memory_id for c in candidates}

                # Remove old links that are no longer relevant
                for target_id in existing_targets - new_targets:
                    store.delete_link(memory.id, target_id)
                    links_removed += 1

                # Add new links
                for candidate in candidates:
                    if candidate.memory_id not in existing_targets:
                        store.save_link(
                            source_id=memory.id,
                            target_id=candidate.memory_id,
                            link_type=LinkType.RELATES_TO,
                            similarity=candidate.similarity,
                        )
                        links_added += 1

    elapsed = time.time() - start_time

    # Report
    if not parsed.quiet:
        print()
        print("Re-embedding complete!")
        print(f"  Processed: {re_embedded} memories")
        print(f"  Drift detected: {drift_detected} memories had significant drift (>{parsed.drift_threshold})")
        if parsed.update_links:
            print(f"  Links updated: {links_added} new, {links_removed} removed")
        print(f"  Time: {elapsed:.1f}s")

        if drift_detected > 0:
            print()
            print("Top drifted memories were refreshed. Their semantic neighborhoods may have evolved.")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
