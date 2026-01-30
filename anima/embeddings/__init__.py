# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Embeddings module for semantic memory.

Provides FastEmbed-based text embedding with lazy loading and caching.
"""

from anima.embeddings.embedder import (
    get_embedder,
    embed_text,
    embed_batch,
    is_model_loaded,
    EMBEDDING_DIMENSIONS,
)
from anima.embeddings.similarity import (
    cosine_similarity,
    find_similar,
)

__all__ = [
    "get_embedder",
    "embed_text",
    "embed_batch",
    "is_model_loaded",
    "cosine_similarity",
    "find_similar",
    "EMBEDDING_DIMENSIONS",
]
