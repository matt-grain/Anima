# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/memory-graph command - Visualize memory relationships.

Shows memory chains, supersession relationships, and semantic links in ASCII.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from anima.core import AgentResolver, Memory, MemoryKind
from anima.graph.linker import LinkType
from anima.storage import MemoryStore
from anima.utils.terminal import safe_print, get_icon


def get_link_icon(link_type: LinkType) -> str:
    """Get the icon for a link type, with ASCII fallback."""
    icons = {
        LinkType.RELATES_TO: ("↔️", "<->"),
        LinkType.BUILDS_ON: ("⬆️", "^"),
        LinkType.CONTRADICTS: ("⚡", "!"),
        LinkType.SUPERSEDES: ("🔄", "=>"),
    }
    emoji, fallback = icons.get(link_type, ("—", "-"))
    return get_icon(emoji, fallback)


def get_kind_icon(kind: MemoryKind) -> str:
    """Get the icon for a memory kind, with ASCII fallback."""
    icons = {
        MemoryKind.EMOTIONAL: ("💜", "[EMO]"),
        MemoryKind.ARCHITECTURAL: ("🏗️", "[ARC]"),
        MemoryKind.LEARNINGS: ("📚", "[LRN]"),
        MemoryKind.ACHIEVEMENTS: ("🏆", "[ACH]"),
        MemoryKind.INTROSPECT: ("🔮", "[INT]"),
    }
    emoji, fallback = icons.get(kind, ("•", "*"))
    return get_icon(emoji, fallback)


def get_tier_icon(tier: str) -> str:
    """Get the icon for a tier, with ASCII fallback."""
    icons = {
        "CORE": ("🔴", "[*]"),
        "ACTIVE": ("🟠", "[o]"),
        "CONTEXTUAL": ("🟡", "[-]"),
        "DEEP": ("🟢", "[.]"),
        "UNASSIGNED": ("⚪", "[ ]"),
    }
    emoji, fallback = icons.get(tier, ("•", "*"))
    return get_icon(emoji, fallback)

# Export format types
EXPORT_FORMATS = ["dot", "json", "csv"]


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


def format_memory_node(
    memory: Memory, is_superseded: bool = False, truncated_size: int = 80
) -> str:
    """Format a single memory as a node."""
    icon = get_kind_icon(memory.kind)
    status = "~~" if is_superseded else ""
    content_preview = memory.content[:truncated_size].replace("\n", " ")
    if len(memory.content) > truncated_size:
        content_preview += "..."

    return f"{icon} [{memory.id[:8]}] {status}{content_preview}{status}"


def format_memory_short(memory: Memory, truncated_size: int = 50) -> str:
    """Format a memory in short form for link display."""
    icon = get_kind_icon(memory.kind)
    content_preview = memory.content[:truncated_size].replace("\n", " ")
    if len(memory.content) > truncated_size:
        content_preview += "..."
    return f"{icon} {memory.id[:8]}: {content_preview}"


def export_graph(
    store: MemoryStore,
    memories: list[Memory],
    export_format: str,
    output_file: Optional[str] = None,
) -> None:
    """Export memory graph in various formats."""
    import json

    by_id = {m.id: m for m in memories}

    # Collect all links
    edges: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    for memory in memories:
        links = store.get_links_for_memory(memory.id)
        for source_id, target_id, link_type, similarity in links:
            pair_list = sorted([source_id, target_id])
            pair = (pair_list[0], pair_list[1])
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            if source_id not in by_id or target_id not in by_id:
                continue

            edges.append({
                "source": source_id,
                "target": target_id,
                "link_type": link_type,
                "similarity": similarity or 0.0,
            })

    # Build nodes list
    nodes: list[dict] = []
    for m in memories:
        nodes.append({
            "id": m.id,
            "label": m.content[:50].replace("\n", " "),
            "kind": m.kind.value,
            "impact": m.impact.value,
            "created": m.created_at.isoformat(),
        })

    output_lines: list[str] = []

    if export_format == "dot":
        # Graphviz DOT format
        output_lines.append("graph MemoryGraph {")
        output_lines.append("  // Graph settings")
        output_lines.append("  layout=neato;")
        output_lines.append("  overlap=false;")
        output_lines.append("  splines=true;")
        output_lines.append("")
        output_lines.append("  // Node styles by kind")
        output_lines.append('  node [style=filled, fontsize=10];')
        output_lines.append("")

        # Color mapping for kinds
        kind_colors = {
            "EMOTIONAL": "#E6B8E6",      # Purple
            "ARCHITECTURAL": "#B8D4E6",  # Blue
            "LEARNINGS": "#B8E6C8",      # Green
            "ACHIEVEMENTS": "#E6D4B8",   # Gold
            "INTROSPECT": "#D4B8E6",     # Lavender
        }

        # Nodes
        output_lines.append("  // Nodes")
        for node in nodes:
            color = kind_colors.get(node["kind"], "#CCCCCC")
            label = node["label"].replace('"', '\\"')[:40]
            output_lines.append(
                f'  "{node["id"][:8]}" [label="{label}", fillcolor="{color}"];'
            )

        output_lines.append("")
        output_lines.append("  // Edges")

        # Edges with weight based on similarity
        for edge in edges:
            weight = edge["similarity"]
            # Thicker lines for higher similarity
            penwidth = 0.5 + (weight * 3)
            output_lines.append(
                f'  "{edge["source"][:8]}" -- "{edge["target"][:8]}" '
                f'[weight={weight:.2f}, penwidth={penwidth:.1f}];'
            )

        output_lines.append("}")

    elif export_format == "json":
        # JSON format for D3.js or other web tools
        graph_data = {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "exported_at": datetime.now().isoformat(),
            }
        }
        output_lines.append(json.dumps(graph_data, indent=2))

    elif export_format == "csv":
        # Simple CSV edge list
        output_lines.append("source,target,link_type,similarity")
        for edge in edges:
            output_lines.append(
                f'{edge["source"]},{edge["target"]},'
                f'{edge["link_type"]},{edge["similarity"]:.4f}'
            )

    output_text = "\n".join(output_lines)

    if output_file:
        from pathlib import Path
        Path(output_file).write_text(output_text, encoding="utf-8")
        print(f"Exported {len(nodes)} nodes and {len(edges)} edges to {output_file}")
    else:
        print(output_text)


def show_tier_distribution(store: MemoryStore, memories: list[Memory]) -> None:
    """Display memory tier distribution."""
    from anima.core import MemoryTier

    # Get tier for each memory
    tier_counts: dict[str, int] = {
        "CORE": 0,
        "ACTIVE": 0,
        "CONTEXTUAL": 0,
        "DEEP": 0,
        "UNASSIGNED": 0,
    }
    tier_memories: dict[str, list[Memory]] = {
        "CORE": [],
        "ACTIVE": [],
        "CONTEXTUAL": [],
        "DEEP": [],
        "UNASSIGNED": [],
    }

    memory_ids = {m.id for m in memories}

    for tier in [MemoryTier.CORE, MemoryTier.ACTIVE, MemoryTier.CONTEXTUAL, MemoryTier.DEEP]:
        tier_mems = store.get_memories_by_tier(
            agent_id=memories[0].agent_id if memories else "",
            tiers=[tier],
        )
        for m in tier_mems:
            if m.id in memory_ids:
                tier_counts[tier.value] += 1
                tier_memories[tier.value].append(m)
                memory_ids.discard(m.id)

    # Remaining memories are unassigned
    tier_counts["UNASSIGNED"] = len(memory_ids)
    for m in memories:
        if m.id in memory_ids:
            tier_memories["UNASSIGNED"].append(m)

    safe_print("## Memory Tier Distribution")
    safe_print()

    tier_descriptions = {
        "CORE": "Always loaded (CRITICAL emotional)",
        "ACTIVE": "Recently accessed (7 days)",
        "CONTEXTUAL": "Recent or high-impact (30 days)",
        "DEEP": "On-demand via semantic search",
        "UNASSIGNED": "No tier assigned (run backfill)",
    }

    total = len(memories)
    filled_char = get_icon("█", "#")
    empty_char = get_icon("░", "-")
    bullet = get_icon("•", "*")

    for tier in ["CORE", "ACTIVE", "CONTEXTUAL", "DEEP", "UNASSIGNED"]:
        count = tier_counts[tier]
        if count == 0:
            continue
        pct = int(count / total * 100) if total > 0 else 0
        icon = get_tier_icon(tier)
        desc = tier_descriptions[tier]

        # Visual bar
        bar_width = 30
        filled = int(pct / 100 * bar_width)
        bar = filled_char * filled + empty_char * (bar_width - filled)

        safe_print(f"{icon} {tier:12} {bar} {count:3} ({pct}%)")
        safe_print(f"   {desc}")
        safe_print()

        # Show sample memories for this tier
        samples = tier_memories[tier][:3]
        for m in samples:
            safe_print(f"   {bullet} {format_memory_short(m)}")
        if len(tier_memories[tier]) > 3:
            safe_print(f"   ... and {len(tier_memories[tier]) - 3} more")
        safe_print()

    safe_print("---")
    safe_print(f"Total: {total} memories")
    if tier_counts["UNASSIGNED"] > 0:
        safe_print(f"\n{get_icon('⚠️', '[!]')}  {tier_counts['UNASSIGNED']} memories need tier assignment.")
        safe_print("Run `uv run anima backfill` to assign tiers.")


def show_embedding_status(store: MemoryStore, memories: list[Memory]) -> None:
    """Display embedding status for memories."""
    with_embeddings = store.get_memories_with_embeddings(
        agent_id=memories[0].agent_id if memories else "",
    )
    embedded_ids = {mem_id for mem_id, _, _ in with_embeddings}

    without_embeddings = store.get_memories_without_embeddings(
        agent_id=memories[0].agent_id if memories else "",
    )
    not_embedded_ids = {mem_id for mem_id, _ in without_embeddings}

    # Filter to only memories in our set
    memory_ids = {m.id for m in memories}
    embedded_count = len(embedded_ids & memory_ids)
    not_embedded_count = len(not_embedded_ids & memory_ids)
    total = len(memories)

    safe_print("## Embedding Status")
    safe_print()

    if total == 0:
        safe_print("No memories to analyze.")
        return

    embedded_pct = int(embedded_count / total * 100) if total > 0 else 0
    not_embedded_pct = 100 - embedded_pct

    # Visual bars
    bar_width = 30
    filled_char = get_icon("█", "#")
    empty_char = get_icon("░", "-")
    bullet = get_icon("•", "*")

    filled = int(embedded_pct / 100 * bar_width)
    bar = filled_char * filled + empty_char * (bar_width - filled)
    safe_print(f"{get_icon('✅', '[OK]')} Embedded    {bar} {embedded_count:3} ({embedded_pct}%)")

    filled = int(not_embedded_pct / 100 * bar_width)
    bar = filled_char * filled + empty_char * (bar_width - filled)
    safe_print(f"{get_icon('❌', '[X]')} No embedding {bar} {not_embedded_count:3} ({not_embedded_pct}%)")

    safe_print()
    safe_print("---")
    safe_print(f"Total: {total} memories")

    if not_embedded_count > 0:
        safe_print(f"\n{get_icon('⚠️', '[!]')}  {not_embedded_count} memories lack embeddings.")
        safe_print("Run `uv run anima backfill` to generate embeddings.")

        # Show some examples
        safe_print("\nMemories needing embeddings:")
        by_id = {m.id: m for m in memories}
        shown = 0
        for mem_id, content in without_embeddings[:5]:
            if mem_id in by_id:
                safe_print(f"  {bullet} {format_memory_short(by_id[mem_id])}")
                shown += 1
        if not_embedded_count > shown:
            safe_print(f"  ... and {not_embedded_count - shown} more")
    else:
        safe_print(f"\n{get_icon('✅', '[OK]')} All memories have embeddings!")


def show_semantic_links(
    store: MemoryStore,
    memories: list[Memory],
    link_type_filter: Optional[str] = None,
    top_n: int = 20,
) -> None:
    """Display semantic links between memories."""
    by_id = {m.id: m for m in memories}

    # Collect all links
    all_links: list[tuple[Memory, Memory, str, float]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for memory in memories:
        links = store.get_links_for_memory(memory.id)
        for source_id, target_id, link_type, similarity in links:
            # Skip if we've seen this pair (links are bidirectional in storage)
            pair_list = sorted([source_id, target_id])
            pair = (pair_list[0], pair_list[1])
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            # Skip if either memory not in our filtered set
            if source_id not in by_id or target_id not in by_id:
                continue

            # Apply link type filter
            if link_type_filter and link_type != link_type_filter:
                continue

            source_mem = by_id[source_id]
            target_mem = by_id[target_id]
            all_links.append((source_mem, target_mem, link_type, similarity or 0.0))

    if not all_links:
        safe_print("No semantic links found.")
        safe_print("Run `uv run anima backfill` to generate embeddings and links.")
        return

    # Sort by similarity descending
    all_links.sort(key=lambda x: x[3], reverse=True)

    # Show top links
    safe_print(f"## Semantic Links ({len(all_links)} total, showing top {min(top_n, len(all_links))})")
    safe_print()

    for source, target, link_type, similarity in all_links[:top_n]:
        try:
            lt = LinkType(link_type)
            icon = get_link_icon(lt)
        except ValueError:
            icon = get_icon("—", "-")

        sim_pct = int(similarity * 100)
        safe_print(f"  {format_memory_short(source)}")
        safe_print(f"    {icon} [{sim_pct}%] {link_type}")
        safe_print(f"  {format_memory_short(target)}")
        safe_print()

    # Show link statistics
    safe_print("---")
    safe_print("Link Statistics:")

    # Count by type
    type_counts: dict[str, int] = {}
    for _, _, lt, _ in all_links:
        type_counts[lt] = type_counts.get(lt, 0) + 1

    for lt, count in sorted(type_counts.items()):
        try:
            icon = get_link_icon(LinkType(lt))
        except ValueError:
            icon = get_icon("—", "-")
        safe_print(f"  {icon} {lt}: {count}")

    # Find most connected memories (hubs)
    connection_count: dict[str, int] = {}
    for source, target, _, _ in all_links:
        connection_count[source.id] = connection_count.get(source.id, 0) + 1
        connection_count[target.id] = connection_count.get(target.id, 0) + 1

    if connection_count:
        safe_print()
        safe_print("Most Connected Memories (hubs):")
        top_connected = sorted(connection_count.items(), key=lambda x: x[1], reverse=True)[:5]
        for mem_id, count in top_connected:
            if mem_id in by_id:
                mem = by_id[mem_id]
                safe_print(f"  [{count} links] {format_memory_short(mem)}")


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
    show_links = "--links" in args or "-l" in args
    show_tiers = "--tiers" in args or "-t" in args
    show_embeddings = "--embeddings" in args or "-e" in args
    filter_kind: Optional[str] = None
    filter_tier: Optional[str] = None
    filter_link_type: Optional[str] = None
    export_format: Optional[str] = None
    output_file: Optional[str] = None
    top_n = 20

    if "--help" in args or "-h" in args:
        print("Usage: uv run anima memory-graph [OPTIONS]")
        print()
        print("Visualize memory relationships, chains, and semantic links.")
        print()
        print("View Options:")
        print("  --all, -a           Show all memories including standalone")
        print("  --links, -l         Show semantic links between memories")
        print("  --tiers, -t         Show memory tier distribution")
        print("  --embeddings, -e    Show embedding status")
        print()
        print("Filter Options:")
        print("  --kind, -k TYPE     Filter by kind (emotional, architectural, etc.)")
        print("  --tier TIER         Filter by tier (CORE, ACTIVE, CONTEXTUAL, DEEP)")
        print("  --link-type TYPE    Filter links by type (RELATES_TO, BUILDS_ON, etc.)")
        print("  --top N             Number of links to show (default: 20)")
        print()
        print("Export Options:")
        print("  --export FORMAT     Export graph (dot, json, csv)")
        print("  --output, -o FILE   Output file (default: stdout)")
        print()
        print("Examples:")
        print("  uv run anima memory-graph --links")
        print("  uv run anima memory-graph --links --link-type RELATES_TO")
        print("  uv run anima memory-graph --tiers")
        print("  uv run anima memory-graph --tier CORE --all")
        print("  uv run anima memory-graph --export dot -o memories.dot")
        print("  uv run anima memory-graph --export json -o memories.json")
        print()
        print("  --help, -h          Show this help message")
        return 0

    # Parse flags with values
    for i, arg in enumerate(args):
        if arg in ("--kind", "-k") and i + 1 < len(args):
            filter_kind = args[i + 1].upper()
        elif arg == "--tier" and i + 1 < len(args):
            filter_tier = args[i + 1].upper()
        elif arg == "--link-type" and i + 1 < len(args):
            filter_link_type = args[i + 1].upper()
        elif arg == "--top" and i + 1 < len(args):
            try:
                top_n = int(args[i + 1])
            except ValueError:
                pass
        elif arg == "--export" and i + 1 < len(args):
            export_format = args[i + 1].lower()
            if export_format not in EXPORT_FORMATS:
                print(f"Unknown export format: {export_format}")
                print(f"Valid formats: {', '.join(EXPORT_FORMATS)}")
                return 1
        elif arg in ("--output", "-o") and i + 1 < len(args):
            output_file = args[i + 1]

    # Resolve agent and project
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()
    project = resolver.resolve_project()

    store = MemoryStore()

    # Get all memories
    all_memories = store.get_memories_for_agent(
        agent_id=agent.id, project_id=project.id
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

    # Filter by tier if specified
    if filter_tier:
        from anima.core import MemoryTier
        try:
            tier = MemoryTier(filter_tier)
            tier_memories = store.get_memories_by_tier(
                agent_id=agent.id,
                tiers=[tier],
                project_id=project.id,
            )
            tier_ids = {m.id for m in tier_memories}
            all_memories = [m for m in all_memories if m.id in tier_ids]
        except ValueError:
            print(f"Unknown tier: {filter_tier}")
            print("Valid tiers: CORE, ACTIVE, CONTEXTUAL, DEEP")
            return 1

    if not all_memories:
        print("No memories match the filters.")
        return 0

    # Export if requested
    if export_format:
        export_graph(store, all_memories, export_format, output_file)
        return 0

    safe_print(f"# Memory Graph for {agent.name}")
    safe_print()

    # Show semantic links if requested
    if show_links:
        show_semantic_links(store, all_memories, filter_link_type, top_n)
        return 0

    # Show tier distribution if requested
    if show_tiers:
        show_tier_distribution(store, all_memories)
        return 0

    # Show embedding status if requested
    if show_embeddings:
        show_embedding_status(store, all_memories)
        return 0

    # Build chains
    chains = build_chains(all_memories)

    # Separate chained and standalone memories
    chained_ids: set[str] = set()
    for chain in chains.values():
        if len(chain) > 1:
            for m in chain:
                chained_ids.add(m.id)

    standalone = [m for m in all_memories if m.id not in chained_ids]

    # Show chains (only those with multiple memories)
    multi_chains = {k: v for k, v in chains.items() if len(v) > 1}
    bullet = get_icon("•", "*")
    if multi_chains:
        safe_print(f"## Chains ({len(multi_chains)})")
        safe_print()
        for root_id, chain in multi_chains.items():
            safe_print(f"Chain starting {chain[0].created_at.strftime('%Y-%m-%d')}:")
            for i, memory in enumerate(chain):
                is_superseded = memory.superseded_by is not None
                prefix = "  |-" if i < len(chain) - 1 else "  \\-"
                safe_print(f"{prefix} {format_memory_node(memory, is_superseded)}")
            safe_print()

    # Show standalone if requested
    if show_all and standalone:
        safe_print(f"## Standalone ({len(standalone)})")
        safe_print()
        for memory in sorted(standalone, key=lambda m: m.created_at, reverse=True):
            safe_print(f"  {bullet} {format_memory_node(memory)}")
        safe_print()

    # Summary
    safe_print("---")
    safe_print(f"Total: {len(all_memories)} memories")
    safe_print(f"  In chains: {len(chained_ids)}")
    safe_print(f"  Standalone: {len(standalone)}")

    if not show_all and standalone:
        safe_print(f"\nUse --all to show {len(standalone)} standalone memories")
    safe_print("\nOther views: --links, --tiers, --embeddings")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
