# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/recall command - Search memories in LTM.

This command searches memories by keyword and returns matches.
For semantic search, the agent interprets the query and translates to lookups.
"""

import sys
from pathlib import Path

from anima.core import AgentResolver
from anima.embeddings import embed_text
from anima.embeddings.similarity import find_similar
from anima.storage import MemoryStore
from anima.utils.terminal import safe_print, get_icon


def lookup_by_id(memory_id: str) -> int:
    """
    Look up a specific memory by ID (full or partial).

    Args:
        memory_id: Full or partial memory ID

    Returns:
        Exit code (0 for success)
    """
    # Resolve agent to get their memories
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()
    project = resolver.resolve_project()

    store = MemoryStore()

    # Get all memories for this agent and search for matching ID
    all_memories = store.get_memories_for_agent(agent_id=agent.id, project_id=project.id)

    # Find memory with matching ID (partial match from start)
    matches = [m for m in all_memories if m.id.startswith(memory_id)]

    if not matches:
        print(f'No memory found with ID starting with "{memory_id}"')
        return 1

    if len(matches) > 1:
        print(f'Multiple memories match "{memory_id}":')
        for m in matches:
            print(f"  - {m.id[:8]}: {m.content[:50]}...")
        print("\nPlease provide a more specific ID.")
        return 1

    # Single match - show full details
    memory = matches[0]
    date_str = memory.created_at.strftime("%Y-%m-%d %H:%M")
    region_icon = "🌐" if memory.region.value == "AGENT" else "📁"

    print(f"Memory: {memory.id}")
    print(f"Type: {memory.kind.value} | Impact: {memory.impact.value}")
    print(f"Region: {region_icon} {memory.region.value}")
    print(f"Created: {date_str}")
    print(f"Confidence: {memory.confidence}")
    if memory.platform:
        spaceship_icon = {"claude": "🔵", "antigravity": "🟣", "opencode": "🟢"}.get(memory.platform, "🚀")
        print(f"Platform: {spaceship_icon} {memory.platform}")
    if memory.superseded_by:
        safe_print(f"{get_icon('⚠️', '[!]')}  Superseded by: {memory.superseded_by}")
    print()
    print("Content:")
    print("-" * 40)
    print(memory.content)
    print("-" * 40)

    return 0


def semantic_search(query: str, agent_id: str, project_id: str | None, show_full: bool, limit: int = 10) -> int:
    """
    Perform semantic search using embeddings.

    Args:
        query: Search query text
        agent_id: Agent ID to search within
        project_id: Project ID for scoping (or None for agent-wide)
        show_full: Whether to show full content
        limit: Maximum results to return

    Returns:
        Exit code (0 for success)
    """
    store = MemoryStore()

    # Get memories with embeddings: list of (id, content, embedding)
    candidate_memories = store.get_memories_with_embeddings(
        agent_id=agent_id,
        project_id=project_id,
    )

    if not candidate_memories:
        print("No embedded memories found. Try keyword search without --semantic.")
        return 0

    # Generate embedding for query
    safe_print(f"{get_icon('🧠', '[SEM]')} Searching semantically...")
    query_embedding = embed_text(query, quiet=True)

    # Build candidates as (memory_id, embedding) tuples for find_similar
    # Also keep a lookup dict for content
    content_lookup: dict[str, str] = {}
    candidates: list[tuple[str, list[float]]] = []
    for mem_id, content, emb in candidate_memories:
        if emb is not None:
            candidates.append((mem_id, emb))
            content_lookup[mem_id] = content

    results = find_similar(query_embedding, candidates, top_k=limit, threshold=0.3)

    if not results:
        print(f'No semantically similar memories found for "{query}"')
        return 0

    print(f'Found {len(results)} semantically similar memories for "{query}":\n')

    # Get all memories once for full details
    all_memories = store.get_memories_for_agent(agent_id=agent_id, project_id=project_id)
    memory_lookup = {m.id: m for m in all_memories}

    for i, result in enumerate(results, 1):
        mem_id = result.item  # The memory ID
        content = content_lookup.get(mem_id, "")
        memory = memory_lookup.get(mem_id)

        if memory:
            confidence_marker = "?" if memory.is_low_confidence() else ""
            date_str = memory.created_at.strftime("%Y-%m-%d")
            similarity_pct = int(result.score * 100)

            if show_full:
                print(f"{i}. [{memory.kind.value}:{memory.impact.value}{confidence_marker}] ({date_str}) [🎯 {similarity_pct}%]")
                print(f"   ID: {memory.id}")
                print(f"   Region: {memory.region.value}")
                print("   Content:")
                for line in memory.content.split("\n"):
                    print(f"   {line}")
                print()
            else:
                print(f"{i}. [{memory.kind.value}:{memory.impact.value}{confidence_marker}] {content[:70]}{'...' if len(content) > 70 else ''} ({date_str}) [🎯 {similarity_pct}%]")
                print(f"   ID: {mem_id[:8]}")
                print()

    return 0


def run(args: list[str]) -> int:
    """
    Run the recall command.

    Args:
        args: Search query words (optionally with --full or --id flag)

    Returns:
        Exit code (0 for success)
    """
    # Parse flags
    show_full = False
    lookup_id = None
    use_semantic = False
    query_words = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--full", "-f"):
            show_full = True
        elif arg in ("--semantic", "-s"):
            use_semantic = True
        elif arg in ("--id", "-i"):
            # Next argument is the memory ID
            if i + 1 < len(args):
                lookup_id = args[i + 1]
                i += 1
            else:
                print("Error: --id requires a memory ID")
                return 1
        elif arg in ("--help", "-h"):
            print("Usage: uv run anima recall [--full] [--semantic] <query>")
            print("       uv run anima recall --id <memory_id>")
            print()
            print("Search memories matching the query, or look up by ID.")
            print()
            print("Options:")
            print("  --full, -f      Show full memory content")
            print("  --semantic, -s  Use semantic (embedding) search")
            print("  --id, -i        Look up a specific memory by ID (full or partial)")
            print("  --help, -h      Show this help message")
            print()
            print("Example: uv run anima recall logging")
            print("Example: uv run anima recall --semantic how does memory decay work")
            print("Example: uv run anima recall --full architecture")
            print("Example: uv run anima recall --id f0087ff3")
            return 0
        elif not arg.startswith("-"):
            query_words.append(arg)
        i += 1

    # If --id was provided, do a direct lookup
    if lookup_id:
        return lookup_by_id(lookup_id)

    if not query_words:
        print("Usage: uv run anima recall [--full] [--semantic] <query>")
        print("       uv run anima recall --id <memory_id>")
        print("Example: uv run anima recall logging")
        print("Example: uv run anima recall --semantic how does memory decay work")
        return 1

    query = " ".join(query_words)

    # Resolve agent and project
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()
    project = resolver.resolve_project()

    # Use semantic search if requested
    if use_semantic:
        return semantic_search(query, agent.id, project.id, show_full)

    # Search memories using keyword search
    store = MemoryStore()
    memories = store.search_memories(agent_id=agent.id, query=query, project_id=project.id, limit=10)

    if not memories:
        print(f'No memories found matching "{query}"')
        return 0

    print(f'Found {len(memories)} memories matching "{query}":\n')

    for i, memory in enumerate(memories, 1):
        # Format: index. [TYPE:IMPACT] content (date)
        confidence_marker = "?" if memory.is_low_confidence() else ""
        date_str = memory.created_at.strftime("%Y-%m-%d")

        if show_full:
            # Full output: show complete content
            print(f"{i}. [{memory.kind.value}:{memory.impact.value}{confidence_marker}] ({date_str})")
            print(f"   ID: {memory.id}")
            print(f"   Region: {memory.region.value}")
            print("   Content:")
            for line in memory.content.split("\n"):
                print(f"   {line}")
            print()
        else:
            # Brief output: truncate content
            print(f"{i}. [{memory.kind.value}:{memory.impact.value}{confidence_marker}] {memory.content[:80]}{'...' if len(memory.content) > 80 else ''} ({date_str})")
            print(f"   ID: {memory.id[:8]}")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
