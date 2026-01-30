# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Auto-linking logic for the memory knowledge graph.

Finds semantically similar memories and creates links between them.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from anima.embeddings import cosine_similarity


class LinkType(str, Enum):
    """Types of links between memories."""

    RELATES_TO = "RELATES_TO"  # General semantic similarity
    BUILDS_ON = "BUILDS_ON"  # This memory extends another
    CONTRADICTS = "CONTRADICTS"  # Conflicting information
    SUPERSEDES = "SUPERSEDES"  # Newer version of old memory


@dataclass
class MemoryLink:
    """A link between two memories."""

    source_id: str
    target_id: str
    link_type: LinkType
    similarity: Optional[float] = None
    created_at: Optional[datetime] = None


@dataclass
class LinkCandidate:
    """A potential link candidate with its similarity score."""

    memory_id: str
    content: str
    similarity: float


def find_link_candidates(
    source_embedding: list[float],
    candidate_memories: list[tuple[str, str, list[float]]],
    threshold: float = 0.5,
    max_links: int = 10,
    exclude_ids: Optional[set[str]] = None,
) -> list[LinkCandidate]:
    """
    Find memories that should be linked to a source memory.

    Args:
        source_embedding: Embedding of the source memory
        candidate_memories: List of (id, content, embedding) tuples
        threshold: Minimum similarity score for linking
        max_links: Maximum number of links to create
        exclude_ids: Memory IDs to exclude (e.g., the source itself)

    Returns:
        List of LinkCandidate objects sorted by similarity descending
    """
    exclude = exclude_ids or set()
    candidates: list[LinkCandidate] = []

    for mem_id, content, embedding in candidate_memories:
        if mem_id in exclude:
            continue
        if embedding is None:
            continue

        similarity = cosine_similarity(source_embedding, embedding)
        if similarity >= threshold:
            candidates.append(LinkCandidate(
                memory_id=mem_id,
                content=content,
                similarity=similarity,
            ))

    # Sort by similarity descending
    candidates.sort(key=lambda c: c.similarity, reverse=True)

    return candidates[:max_links]


def create_links_for_memory(
    source_id: str,
    source_embedding: list[float],
    candidate_memories: list[tuple[str, str, list[float]]],
    threshold: float = 0.5,
    max_links: int = 10,
) -> list[MemoryLink]:
    """
    Create RELATES_TO links for a memory based on semantic similarity.

    Args:
        source_id: ID of the source memory
        source_embedding: Embedding of the source memory
        candidate_memories: List of (id, content, embedding) tuples
        threshold: Minimum similarity score for linking
        max_links: Maximum number of links to create

    Returns:
        List of MemoryLink objects to be stored
    """
    candidates = find_link_candidates(
        source_embedding=source_embedding,
        candidate_memories=candidate_memories,
        threshold=threshold,
        max_links=max_links,
        exclude_ids={source_id},
    )

    links = []
    for candidate in candidates:
        links.append(MemoryLink(
            source_id=source_id,
            target_id=candidate.memory_id,
            link_type=LinkType.RELATES_TO,
            similarity=candidate.similarity,
            created_at=datetime.now(),
        ))

    return links


def suggest_link_type(
    source_content: str,
    target_content: str,
    similarity: float,
) -> LinkType:
    """
    Suggest a link type based on content analysis.

    Currently returns RELATES_TO for all cases.
    Future: Could use LLM or heuristics to detect BUILDS_ON, CONTRADICTS.

    Args:
        source_content: Content of the source memory
        target_content: Content of the target memory
        similarity: Cosine similarity between embeddings

    Returns:
        Suggested LinkType
    """
    # For now, always return RELATES_TO
    # Future enhancements could detect:
    # - BUILDS_ON: if source references or extends target
    # - CONTRADICTS: if source negates target
    # - SUPERSEDES: if source is a newer version of target
    return LinkType.RELATES_TO
