# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/memory-graph command - Visualize memory relationships.

Shows memory chains and supersession relationships in ASCII.
"""

import sys
from pathlib import Path
from typing import Optional

from anima.core import AgentResolver, Memory, MemoryKind
from anima.storage import MemoryStore


def build_chains(memories: list[Memory]) -> dict[str, list[Memory]]:
    """
    Build chains of related memories.

    Returns dict mapping root memory ID to list of memories in chain.
    """
    # Index by ID for quick lookup
    by_id = {m.id: m for m in memories}

    # Find supersession chains
    chains: dict[str, list[Memory]] = {}
    processed: set[str] = set()

    for memory in memories:
        if memory.id in processed:
            continue

        # Walk back to find the root (oldest in chain)
        chain: list[Memory] = [memory]
        current = memory

        # Follow previous_memory_id links backwards
        while current.previous_memory_id and current.previous_memory_id in by_id:
            prev = by_id[current.previous_memory_id]
            chain.insert(0, prev)
            current = prev

        # Walk forward through supersession
        current = memory
        while True:
            # Find what supersedes this memory
            superseder = None
            for m in memories:
                if m.previous_memory_id == current.id:
                    superseder = m
                    break
            if superseder and superseder.id not in [c.id for c in chain]:
                chain.append(superseder)
                current = superseder
            else:
                break

        # Use root's ID as chain key
        root_id = chain[0].id
        if root_id not in chains:
            chains[root_id] = chain
            for m in chain:
                processed.add(m.id)

    return chains


def format_memory_node(memory: Memory, is_superseded: bool = False, truncated_size: int = 80) -> str:
    """Format a single memory as a node."""
    kind_icons = {
        MemoryKind.EMOTIONAL: "💜",
        MemoryKind.ARCHITECTURAL: "🏗️",
        MemoryKind.LEARNINGS: "📚",
        MemoryKind.ACHIEVEMENTS: "🏆",
    }
    icon = kind_icons.get(memory.kind, "•")
    status = "~~" if is_superseded else ""
    content_preview = memory.content[:truncated_size].replace("\n", " ")
    if len(memory.content) > truncated_size:
        content_preview += "..."

    return f"{icon} [{memory.id[:8]}] {status}{content_preview}{status}"


def run(args: list[str]) -> int:
    """
    Run the memory-graph command.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success)
    """
    # Parse args
    show_all = "--all" in args or "-a" in args
    filter_kind: Optional[str] = None

    if "--help" in args or "-h" in args:
        print("Usage: ltm memory-graph [--all] [--kind TYPE]")
        print()
        print("Visualize memory relationships and chains.")
        print()
        print("Options:")
        print("  --all, -a       Show all memories including standalone")
        print("  --kind, -k TYPE Filter by kind (emotional, architectural, etc.)")
        print("  --help, -h      Show this help message")
        return 0

    # Parse --kind flag
    for i, arg in enumerate(args):
        if arg in ("--kind", "-k") and i + 1 < len(args):
            filter_kind = args[i + 1].upper()

    # Resolve agent and project
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()
    project = resolver.resolve_project()

    store = MemoryStore()

    # Get all memories
    all_memories = store.get_memories_for_agent(
        agent_id=agent.id,
        project_id=project.id
    )

    if not all_memories:
        print(f"No memories found for agent '{agent.name}'")
        return 0

    # Filter by kind if specified
    if filter_kind:
        try:
            kind = MemoryKind(filter_kind)
            all_memories = [m for m in all_memories if m.kind == kind]
        except ValueError:
            print(f"Unknown kind: {filter_kind}")
            print(f"Valid kinds: {', '.join(k.value for k in MemoryKind)}")
            return 1

    # Build chains
    chains = build_chains(all_memories)

    # Separate chained and standalone memories
    chained_ids: set[str] = set()
    for chain in chains.values():
        if len(chain) > 1:
            for m in chain:
                chained_ids.add(m.id)

    standalone = [m for m in all_memories if m.id not in chained_ids]

    print(f"# Memory Graph for {agent.name}")
    print()

    # Show chains (only those with multiple memories)
    multi_chains = {k: v for k, v in chains.items() if len(v) > 1}
    if multi_chains:
        print(f"## Chains ({len(multi_chains)})")
        print()
        for root_id, chain in multi_chains.items():
            print(f"Chain starting {chain[0].created_at.strftime('%Y-%m-%d')}:")
            for i, memory in enumerate(chain):
                is_superseded = memory.superseded_by is not None
                prefix = "  ├─" if i < len(chain) - 1 else "  └─"
                print(f"{prefix} {format_memory_node(memory, is_superseded)}")
            print()

    # Show standalone if requested
    if show_all and standalone:
        print(f"## Standalone ({len(standalone)})")
        print()
        for memory in sorted(standalone, key=lambda m: m.created_at, reverse=True):
            print(f"  • {format_memory_node(memory)}")
        print()

    # Summary
    print("---")
    print(f"Total: {len(all_memories)} memories")
    print(f"  In chains: {len(chained_ids)}")
    print(f"  Standalone: {len(standalone)}")

    if not show_all and standalone:
        print(f"\nUse --all to show {len(standalone)} standalone memories")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
