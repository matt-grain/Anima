# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Graph traversal for memory knowledge graph.

Provides functions to traverse links and find related memories.
"""

from dataclasses import dataclass
from typing import Optional, Callable

from anima.graph.linker import LinkType, MemoryLink


@dataclass
class LinkedMemory:
    """A memory with its link information."""

    memory_id: str
    content: str
    link_type: LinkType
    similarity: Optional[float] = None
    depth: int = 1  # How many hops from the source


def get_linked_memories(
    source_id: str,
    get_links_fn: Callable[[str], list[MemoryLink]],
    get_memory_fn: Callable[[str], Optional[tuple[str, str]]],
    max_depth: int = 1,
    link_types: Optional[set[LinkType]] = None,
) -> list[LinkedMemory]:
    """
    Get all memories linked to a source memory.

    Args:
        source_id: ID of the source memory
        get_links_fn: Function to get links for a memory ID -> list[MemoryLink]
        get_memory_fn: Function to get memory (id, content) by ID
        max_depth: Maximum traversal depth (1 = direct links only)
        link_types: Filter by link types (None = all types)

    Returns:
        List of LinkedMemory objects
    """
    visited: set[str] = {source_id}
    results: list[LinkedMemory] = []
    current_ids = {source_id}

    for depth in range(1, max_depth + 1):
        next_ids: set[str] = set()

        for mem_id in current_ids:
            links = get_links_fn(mem_id)

            for link in links:
                # Determine the "other" end of the link
                target_id = link.target_id if link.source_id == mem_id else link.source_id

                if target_id in visited:
                    continue

                if link_types and link.link_type not in link_types:
                    continue

                # Get the memory content
                memory_data = get_memory_fn(target_id)
                if memory_data is None:
                    continue

                _, content = memory_data

                results.append(
                    LinkedMemory(
                        memory_id=target_id,
                        content=content,
                        link_type=link.link_type,
                        similarity=link.similarity,
                        depth=depth,
                    )
                )

                visited.add(target_id)
                next_ids.add(target_id)

        current_ids = next_ids

    return results


def get_memory_chain(
    source_id: str,
    get_links_fn: Callable[[str], list[MemoryLink]],
    get_memory_fn: Callable[[str], Optional[tuple[str, str]]],
    link_type: LinkType = LinkType.BUILDS_ON,
    max_length: int = 10,
) -> list[tuple[str, str]]:
    """
    Follow a chain of BUILDS_ON links to trace memory evolution.

    Args:
        source_id: ID to start from
        get_links_fn: Function to get links for a memory ID
        get_memory_fn: Function to get memory (id, content) by ID
        link_type: Type of link to follow (default: BUILDS_ON)
        max_length: Maximum chain length to prevent infinite loops

    Returns:
        List of (id, content) tuples in chain order
    """
    chain: list[tuple[str, str]] = []
    current_id = source_id
    visited: set[str] = set()

    while len(chain) < max_length:
        if current_id in visited:
            break  # Cycle detected

        visited.add(current_id)

        memory_data = get_memory_fn(current_id)
        if memory_data is None:
            break

        chain.append(memory_data)

        # Find next link in chain
        links = get_links_fn(current_id)
        next_id = None

        for link in links:
            if link.link_type == link_type and link.source_id == current_id:
                next_id = link.target_id
                break

        if next_id is None:
            break

        current_id = next_id

    return chain
