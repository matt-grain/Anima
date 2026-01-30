# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Similarity functions for semantic search.

Provides cosine similarity and top-k retrieval.
"""

import math
from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar("T")


@dataclass
class SimilarityResult(Generic[T]):
    """Result from a similarity search."""

    item: T
    score: float


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        a: First embedding vector
        b: Second embedding vector

    Returns:
        Similarity score between -1 and 1 (1 = identical)
    """
    if len(a) != len(b):
        raise ValueError(f"Vector dimensions don't match: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def find_similar(
    query_embedding: list[float],
    candidates: list[tuple[T, list[float]]],
    top_k: int = 5,
    threshold: float = 0.0,
) -> list[SimilarityResult[T]]:
    """
    Find most similar items to a query embedding.

    Args:
        query_embedding: The embedding to search for
        candidates: List of (item, embedding) tuples to search through
        top_k: Maximum number of results to return
        threshold: Minimum similarity score to include

    Returns:
        List of SimilarityResult sorted by score descending
    """
    results: list[SimilarityResult[T]] = []

    for item, embedding in candidates:
        if embedding is None:
            continue

        score = cosine_similarity(query_embedding, embedding)
        if score >= threshold:
            results.append(SimilarityResult(item=item, score=score))

    # Sort by score descending
    results.sort(key=lambda r: r.score, reverse=True)

    return results[:top_k]


def batch_similarities(
    query_embedding: list[float],
    embeddings: list[list[float]],
) -> list[float]:
    """
    Calculate similarities between a query and multiple embeddings.

    Args:
        query_embedding: The query embedding
        embeddings: List of embeddings to compare against

    Returns:
        List of similarity scores in the same order as embeddings
    """
    return [
        cosine_similarity(query_embedding, emb) if emb else 0.0
        for emb in embeddings
    ]
