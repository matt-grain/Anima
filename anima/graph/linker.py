# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Auto-linking logic for the memory knowledge graph.

Finds semantically similar memories and creates links between them.
Supports two types of relationships:
- RELATES_TO: Semantic similarity (creates cluster/web topology)
- BUILDS_ON: Causal/evolutionary (creates tree/chain topology)

The distinction matters for recall:
- "What topics cluster together?" -> RELATES_TO
- "How did my thinking evolve?" -> BUILDS_ON
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from anima.embeddings import cosine_similarity


# Patterns that suggest one memory BUILDS_ON another
BUILDS_ON_PATTERNS = [
    # Direct reference patterns
    r"\bas (?:I|we) (?:mentioned|discussed|noted|observed|said)",
    r"\bbuilding on\b",
    r"\bfollowing up on\b",
    r"\bextending\b.*\b(?:earlier|previous)",
    r"\b(?:as|per) (?:our|the) (?:earlier|previous|last) (?:discussion|conversation|session)",
    # Update/evolution markers
    r"^(?:Update|Correction|Evolution|Revision|Addendum):",
    r"\bupdate(?:d|ing)?\b.*\b(?:earlier|previous|my)\b",
    r"\b(?:now|actually)\b.*\brealiz(?:e|ed)\b",
    r"\bon (?:second|further) thought\b",
    # Continuation markers
    r"\bcontinuing\b.*\bthought",
    r"\b(?:furthermore|moreover|additionally)\b",
    r"\bthis (?:builds|extends|adds) (?:on|to)\b",
]

# Compile patterns for efficiency
BUILDS_ON_COMPILED = [re.compile(p, re.IGNORECASE) for p in BUILDS_ON_PATTERNS]


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


def has_builds_on_pattern(content: str) -> bool:
    """
    Check if content contains patterns suggesting it builds on earlier thoughts.

    Args:
        content: The memory content to analyze

    Returns:
        True if BUILDS_ON patterns are detected
    """
    for pattern in BUILDS_ON_COMPILED:
        if pattern.search(content):
            return True
    return False


def suggest_link_type(
    source_content: str,
    target_content: str,
    similarity: float,
    source_created: Optional[datetime] = None,
    target_created: Optional[datetime] = None,
    same_session: bool = False,
) -> LinkType:
    """
    Suggest a link type based on content and temporal analysis.

    BUILDS_ON is suggested when:
    1. Source has reference patterns ("as I mentioned", "building on", etc.)
    2. High semantic similarity (>0.6) AND source is newer than target
    3. Same session AND high similarity

    Args:
        source_content: Content of the source (newer) memory
        target_content: Content of the target (older) memory
        similarity: Cosine similarity between embeddings
        source_created: When source was created
        target_created: When target was created
        same_session: Whether both memories are from the same session

    Returns:
        Suggested LinkType
    """
    # Check for explicit BUILDS_ON patterns in source
    if has_builds_on_pattern(source_content):
        return LinkType.BUILDS_ON

    # High similarity + same session suggests evolution of thought
    if same_session and similarity >= 0.6:
        return LinkType.BUILDS_ON

    # High similarity + source is newer suggests building on earlier work
    if source_created and target_created:
        if source_created > target_created and similarity >= 0.7:
            # Very high similarity with temporal ordering = likely evolution
            return LinkType.BUILDS_ON

    # Default to semantic relationship
    return LinkType.RELATES_TO


@dataclass
class BuildsOnCandidate:
    """A candidate for BUILDS_ON relationship."""

    memory_id: str
    content: str
    similarity: float
    created_at: datetime
    session_id: Optional[str] = None
    confidence: float = 0.0  # How confident we are this is a BUILDS_ON


def find_builds_on_candidates(
    source_content: str,
    source_embedding: list[float],
    source_session_id: Optional[str],
    source_created: datetime,
    candidate_memories: list[tuple[str, str, list[float], datetime, Optional[str]]],
    similarity_threshold: float = 0.5,
    time_window_hours: int = 48,
    max_candidates: int = 3,
) -> list[BuildsOnCandidate]:
    """
    Find memories that the source memory likely BUILDS_ON.

    Unlike RELATES_TO (symmetric similarity), BUILDS_ON is directional:
    source BUILDS_ON target means target is older and source extends it.

    Detection signals (additive confidence):
    - Temporal proximity within time window: +0.3
    - Same session: +0.4
    - Reference patterns in source: +0.5
    - High semantic similarity: +0.2 per 0.1 above threshold

    Args:
        source_content: Content of the new memory
        source_embedding: Embedding of the new memory
        source_session_id: Session ID of the new memory
        source_created: Creation time of the new memory
        candidate_memories: List of (id, content, embedding, created_at, session_id)
        similarity_threshold: Minimum similarity to consider
        time_window_hours: Only consider memories within this window
        max_candidates: Maximum BUILDS_ON links to create

    Returns:
        List of BuildsOnCandidate sorted by confidence descending
    """
    candidates: list[BuildsOnCandidate] = []
    time_window = timedelta(hours=time_window_hours)
    has_reference = has_builds_on_pattern(source_content)

    for mem_id, content, embedding, created_at, session_id in candidate_memories:
        # Skip if no embedding
        if embedding is None:
            continue

        # Skip if newer than source (can't build on future)
        if created_at >= source_created:
            continue

        # Skip if outside time window
        if source_created - created_at > time_window:
            continue

        # Calculate similarity
        similarity = cosine_similarity(source_embedding, embedding)
        if similarity < similarity_threshold:
            continue

        # Calculate confidence score
        confidence = 0.0

        # Temporal proximity boost
        hours_apart = (source_created - created_at).total_seconds() / 3600
        if hours_apart <= 24:
            confidence += 0.3
        elif hours_apart <= 48:
            confidence += 0.15

        # Same session boost
        same_session = (
            source_session_id is not None
            and session_id is not None
            and source_session_id == session_id
        )
        if same_session:
            confidence += 0.4

        # Reference pattern boost
        if has_reference:
            confidence += 0.5

        # Similarity boost (0.2 per 0.1 above threshold)
        similarity_boost = (similarity - similarity_threshold) * 2.0
        confidence += max(0, similarity_boost)

        # Only include if confidence is meaningful
        if confidence >= 0.3:
            candidates.append(BuildsOnCandidate(
                memory_id=mem_id,
                content=content,
                similarity=similarity,
                created_at=created_at,
                session_id=session_id,
                confidence=confidence,
            ))

    # Sort by confidence descending
    candidates.sort(key=lambda c: c.confidence, reverse=True)

    return candidates[:max_candidates]
