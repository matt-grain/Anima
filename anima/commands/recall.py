# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/recall command - Search memories in LTM.

This command searches memories by keyword and returns matches.
Supports social cue detection ("remember when we discussed X") and
temporal cue parsing ("last session", "yesterday") for natural queries.
"""

import sys
import time
from pathlib import Path
from typing import Any, Optional

from anima.core import AgentResolver, MemoryKind, Memory
from anima.embeddings import embed_text
from anima.embeddings.similarity import find_similar
from anima.lifecycle.social_cues import (
    detect_social_cue,
    extract_recall_query,
    should_search_subconscious,
)
from anima.lifecycle.temporal import parse_temporal_cue, TemporalCoordinate
from anima.storage import (
    MemoryStore,
    SubconsciousStore,
    FTS5NotSupportedError,
    SearchResult,
)
from anima.utils.terminal import safe_print, get_icon


def apply_temporal_filter(
    memories: list[Memory],
    coord: TemporalCoordinate,
) -> list[Memory]:
    """
    Filter memories by temporal coordinates.

    Applies filters for session, time range, and git context.
    """
    result = memories

    # Filter by session
    if coord.session_id:
        result = [m for m in result if m.session_id == coord.session_id]

    # Filter by time range
    if coord.start_time:
        result = [m for m in result if m.created_at >= coord.start_time]
    if coord.end_time:
        result = [m for m in result if m.created_at <= coord.end_time]

    # Filter by git commit (prefix match)
    if coord.git_commit:
        result = [m for m in result if m.git_commit and m.git_commit.startswith(coord.git_commit)]

    # Filter by git branch
    if coord.git_branch:
        result = [m for m in result if m.git_branch == coord.git_branch]

    return result


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
    if memory.platform or memory.model:
        spaceship_icon = {"claude": "🔵", "antigravity": "🟣", "opencode": "🟢"}.get(memory.platform or "", "🚀")
        platform_str = memory.platform or "unknown"
        model_str = f" ({memory.model})" if memory.model else ""
        print(f"Spaceship: {spaceship_icon} {platform_str}{model_str}")
    if memory.superseded_by:
        safe_print(f"{get_icon('⚠️', '[!]')}  Superseded by: {memory.superseded_by}")
    print()
    print("Content:")
    print("-" * 40)
    print(memory.content)
    print("-" * 40)

    return 0


def semantic_search(
    query: str,
    agent_id: str,
    project_id: str | None,
    show_full: bool,
    limit: int = 10,
    temporal_coord: Optional[TemporalCoordinate] = None,
) -> int:
    """
    Perform semantic search using embeddings.

    Args:
        query: Search query text
        agent_id: Agent ID to search within
        project_id: Project ID for scoping (or None for agent-wide)
        show_full: Whether to show full content
        limit: Maximum results to return
        temporal_coord: Optional temporal filters to apply

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
        print("No embedded memories found. Try --keyword for exact phrase search.")
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

    # Fetch extra results if we'll be filtering
    search_limit = limit * 2 if temporal_coord and temporal_coord.has_filters() else limit
    results = find_similar(query_embedding, candidates, top_k=search_limit, threshold=0.3)

    if not results:
        print(f'No semantically similar memories found for "{query}"')
        return 0

    # Get all memories once for full details
    all_memories = store.get_memories_for_agent(agent_id=agent_id, project_id=project_id)
    memory_lookup = {m.id: m for m in all_memories}

    # Build list of (result, memory) pairs for filtering
    result_memories: list[tuple[Any, Memory]] = []
    for result in results:
        mem_id = result.item
        memory = memory_lookup.get(mem_id)
        if memory:
            result_memories.append((result, memory))

    # Apply temporal filter if provided
    if temporal_coord and temporal_coord.has_filters():
        filtered_memories = apply_temporal_filter([m for _, m in result_memories], temporal_coord)
        filtered_ids = {m.id for m in filtered_memories}
        result_memories = [(r, m) for r, m in result_memories if m.id in filtered_ids]

    # Apply limit after filtering
    result_memories = result_memories[:limit]

    if not result_memories:
        print(f'No semantically similar memories found for "{query}" with temporal filters')
        return 0

    print(f'Found {len(result_memories)} semantically similar memories for "{query}":\n')

    for i, (result, memory) in enumerate(result_memories, 1):
        mem_id = result.item
        content = content_lookup.get(mem_id, "")
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


def _format_timestamp(ts_ms: int) -> str:
    """Format a millisecond epoch timestamp to a YYYY-MM-DD date string."""
    try:
        return time.strftime("%Y-%m-%d", time.localtime(float(ts_ms) / 1000))
    except (OSError, ValueError, TypeError):
        return "unknown"


def _resolve_project_path(project_id: str) -> str | None:
    """Resolve a project ID to its filesystem path string via MemoryStore."""
    mem_store = MemoryStore()
    project = mem_store.get_project(project_id)
    return str(project.path) if project else None


def _print_subconscious_result(i: int, result: SearchResult, show_full: bool) -> None:
    """Print a single subconscious search result."""
    date_str = _format_timestamp(result.timestamp)
    project_name = Path(result.project).name if result.project else "unknown"

    print(f"{i}. [subconscious:{result.source}] {date_str} | {project_name}")
    print(f"   Session: {result.session_id[:12]}...")

    if show_full:
        print("   Excerpt:")
        for line in result.excerpt.split("\n"):
            print(f"     {line}")
    else:
        excerpt_clean = result.excerpt.replace("\n", " ").strip()
        if len(excerpt_clean) > 100:
            excerpt_clean = excerpt_clean[:100] + "..."
        print(f"   > {excerpt_clean}")
    print()


def subconscious_search(
    query: str,
    project_id: str | None,
    show_full: bool,
    limit: int = 10,
    days: int | None = None,
) -> int:
    """Search the subconscious database (raw dialogue history)."""
    try:
        store = SubconsciousStore()
    except FTS5NotSupportedError:
        print("Subconscious search unavailable (FTS5 not supported)")
        return 1

    project_path = _resolve_project_path(project_id) if project_id else None
    results: list[SearchResult] = store.search(query, project=project_path, days=days, limit=limit)

    if not results:
        print(f'No subconscious memories found for "{query}"')
        return 0

    print(f'Found {len(results)} subconscious memories for "{query}":\n')
    for i, result in enumerate(results, 1):
        _print_subconscious_result(i, result, show_full)

    return 0


def both_search(
    query: str,
    agent_id: str,
    project_id: str | None,
    show_full: bool,
    limit: int = 10,
) -> int:
    """Search both conscious and subconscious stores and display merged results."""
    print(f'Searching conscious and subconscious memories for "{query}":\n')

    # --- Conscious section ---
    print("=== Conscious Memories ===")
    conscious_result = semantic_search(query, agent_id, project_id, show_full, limit)

    # --- Subconscious section ---
    print("=== Subconscious Memories ===")
    subconscious_search(query, project_id, show_full, limit)

    return conscious_result


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
    use_semantic = True  # Semantic search by default (multi-word queries work!)
    kind_filter: MemoryKind | None = None
    limit = 10
    search_mode = "conscious"  # Default: search explicit memories only
    query_words = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--full", "-f"):
            show_full = True
        elif arg in ("--keyword", "--exact"):
            use_semantic = False  # Fall back to exact phrase LIKE search
        elif arg in ("--kind", "-k"):
            # Next argument is the memory kind
            if i + 1 < len(args):
                kind_str = args[i + 1].upper()
                try:
                    kind_filter = MemoryKind(kind_str)
                except ValueError:
                    print(f"Invalid kind: {kind_str}")
                    print(f"Valid kinds: {', '.join(k.value for k in MemoryKind)}")
                    return 1
                i += 1
            else:
                print("Error: --kind requires a memory kind (EMOTIONAL, ARCHITECTURAL, LEARNINGS, ACHIEVEMENTS, INTROSPECT, DREAM)")
                return 1
        elif arg in ("--limit", "-l"):
            # Next argument is the limit
            if i + 1 < len(args):
                try:
                    limit = int(args[i + 1])
                except ValueError:
                    print("Error: --limit requires a number")
                    return 1
                i += 1
            else:
                print("Error: --limit requires a number")
                return 1
        elif arg in ("--id", "-i"):
            # Next argument is the memory ID
            if i + 1 < len(args):
                lookup_id = args[i + 1]
                i += 1
            else:
                print("Error: --id requires a memory ID")
                return 1
        elif arg in ("--subconscious", "-s"):
            search_mode = "subconscious"
        elif arg in ("--conscious", "-c"):
            search_mode = "conscious"
        elif arg in ("--both", "-b"):
            search_mode = "both"
        elif arg in ("--help", "-h"):
            print("Usage: uv run anima recall [--full] [--keyword] [--kind KIND] [--limit N] <query>")
            print("       uv run anima recall --kind DREAM")
            print("       uv run anima recall --id <memory_id>")
            print()
            print("Search memories matching the query, or look up by ID.")
            print("Uses semantic (embedding) search by default for natural language queries.")
            print()
            print("Options:")
            print("  --full, -f          Show full memory content")
            print("  --keyword           Use exact phrase LIKE search (default: semantic)")
            print("  --kind, -k          Filter by memory kind (EMOTIONAL, ARCHITECTURAL, LEARNINGS, ACHIEVEMENTS, INTROSPECT, DREAM)")
            print("  --limit, -l         Maximum results to return (default: 10)")
            print("  --id, -i            Look up a specific memory by ID (full or partial)")
            print("  --subconscious, -s  Search raw dialogue history (subconscious.db)")
            print("  --conscious, -c     Search explicit memories only (default)")
            print("  --both, -b          Search both, merge results")
            print("  --help, -h          Show this help message")
            print()
            print("Examples:")
            print("  uv run anima recall how does memory decay work")
            print("  uv run anima recall schneier security AI")
            print("  uv run anima recall --keyword logging             # Exact phrase match")
            print("  uv run anima recall --kind DREAM                  # List recent dream memories")
            print("  uv run anima recall --id f0087ff3")
            print("  uv run anima recall --subconscious warmth         # Search raw dialogue history")
            print("  uv run anima recall --both cognitive auth          # Search conscious + subconscious")
            return 0
        elif not arg.startswith("-"):
            query_words.append(arg)
        i += 1

    # If --id was provided, do a direct lookup
    if lookup_id:
        return lookup_by_id(lookup_id)

    # Resolve agent and project (needed for all paths below)
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()
    project = resolver.resolve_project()
    store = MemoryStore()

    # If --kind provided without query, list memories of that kind
    if kind_filter and not query_words:
        # Get both agent-wide and project-specific memories
        memories = store.get_memories_for_agent(
            agent_id=agent.id,
            kind=kind_filter,
            project_id=project.id,  # This gets both agent + project memories
        )
        # Sort by created_at descending and limit
        memories.sort(key=lambda m: m.created_at, reverse=True)
        memories = memories[:limit]

        if not memories:
            print(f"No {kind_filter.value} memories found")
            return 0

        print(f"Found {len(memories)} {kind_filter.value} memories:\n")

        for i, memory in enumerate(memories, 1):
            confidence_marker = "?" if memory.is_low_confidence() else ""
            date_str = memory.created_at.strftime("%Y-%m-%d")

            if show_full:
                print(f"{i}. [{memory.kind.value}:{memory.impact.value}{confidence_marker}] ({date_str})")
                print(f"   ID: {memory.id}")
                print(f"   Region: {memory.region.value}")
                print("   Content:")
                for line in memory.content.split("\n"):
                    print(f"   {line}")
                print()
            else:
                print(f"{i}. [{memory.kind.value}:{memory.impact.value}{confidence_marker}] {memory.content[:80]}{'...' if len(memory.content) > 80 else ''} ({date_str})")
                print(f"   ID: {memory.id[:8]}")
                print()

        return 0

    if not query_words:
        print("Usage: uv run anima recall [--full] [--keyword] [--kind KIND] [--limit N] <query>")
        print("       uv run anima recall --kind DREAM")
        print("       uv run anima recall --id <memory_id>")
        print("Example: uv run anima recall how does memory decay work")
        print("Example: uv run anima recall --kind DREAM --full")
        print("Example: uv run anima recall --keyword logging   # exact phrase match")
        return 1

    query = " ".join(query_words)

    # Detect social cues ("remember when we discussed X", "you mentioned Y")
    social_cue = detect_social_cue(query)
    if social_cue:
        # Extract the topic from social cue for search
        cue_topic = extract_recall_query(social_cue)
        if cue_topic:
            safe_print(f'{get_icon("💬", "[SOC]")} Detected social cue: "{social_cue.cue_type.name}" → topic: "{cue_topic}"')
            query = cue_topic  # Use extracted topic as the actual search query
            # Social cues imply wanting contextual search - auto-enable semantic
            if not use_semantic:
                safe_print(f"{get_icon('🔄', '[AUTO]')} Auto-enabling semantic search for natural language query")
                use_semantic = True
        # Explicit recall cues ("remember when", "do you recall") → also search subconscious
        if search_mode == "conscious" and should_search_subconscious(social_cue):
            search_mode = "both"

    # Route based on search_mode before falling through to conscious search
    if search_mode == "subconscious":
        return subconscious_search(query, project.id if project else None, show_full, limit)
    if search_mode == "both":
        return both_search(query, agent.id, project.id if project else None, show_full, limit)

    # Parse temporal cues ("last session", "yesterday", "during the last commit")
    temporal_coord = parse_temporal_cue(query)
    if temporal_coord and temporal_coord.has_filters():
        filter_desc = []
        if temporal_coord.session_id:
            filter_desc.append(f"session={temporal_coord.session_id[:8]}...")
        if temporal_coord.start_time:
            filter_desc.append(f"from={temporal_coord.start_time.strftime('%Y-%m-%d')}")
        if temporal_coord.end_time:
            filter_desc.append(f"to={temporal_coord.end_time.strftime('%Y-%m-%d')}")
        if temporal_coord.git_commit:
            filter_desc.append(f"commit={temporal_coord.git_commit[:8]}...")
        if temporal_coord.git_branch:
            filter_desc.append(f"branch={temporal_coord.git_branch}")
        safe_print(f"{get_icon('⏰', '[TIME]')} Temporal filter: {', '.join(filter_desc)}")

    # Use semantic search if requested or auto-enabled
    if use_semantic:
        result = semantic_search(query, agent.id, project.id, show_full, limit, temporal_coord)
        return result

    # Search memories using keyword search
    memories = store.search_memories(agent_id=agent.id, query=query, project_id=project.id, limit=limit * 2)  # Fetch extra for post-filtering

    # Apply temporal filter if detected
    if temporal_coord and temporal_coord.has_filters():
        memories = apply_temporal_filter(memories, temporal_coord)

    # Apply kind filter if provided
    if kind_filter:
        memories = [m for m in memories if m.kind == kind_filter]

    # Apply limit after all filtering
    memories = memories[:limit]

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
