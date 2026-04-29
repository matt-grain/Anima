# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
FastEmbed wrapper for generating text embeddings.

Uses ONNX Runtime for CPU-optimized inference.
Model is loaded lazily on first use with a friendly "waking up" message.
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

from anima.utils.terminal import get_icon, safe_print

# Persistent cache directory (not /tmp which gets cleaned)
CACHE_DIR = Path.home() / ".cache" / "fastembed"

# Disable tqdm progress bars - they cause hangs in non-TTY environments
# (e.g., Claude Code hooks without --debug mode)
os.environ["TQDM_DISABLE"] = "1"  # Force disable, don't use setdefault

# Disable ONNX Runtime logging (fastembed uses ONNX)
os.environ.setdefault("ORT_DISABLE_PROGRESS_BAR", "1")
os.environ.setdefault("ONNXRUNTIME_LOG_SEVERITY_LEVEL", "3")  # ERROR only

# Model configuration
MODEL_NAME = "BAAI/bge-small-en-v1.5"  # Fast, good quality, MTEB top performer
EMBEDDING_DIMENSIONS = 384  # Output dimensions for this model

# Global embedder instance (lazy loaded)
_embedder: Optional[Any] = None  # Actually TextEmbedding, but lazy import
_load_time: Optional[float] = None


def is_model_loaded() -> bool:
    """Check if the embedding model is already loaded."""
    return _embedder is not None


def get_embedder(quiet: bool = False):
    """
    Get the FastEmbed model, loading it if necessary.

    Args:
        quiet: If True, suppress the "waking up" message

    Returns:
        TextEmbedding instance
    """
    global _embedder, _load_time

    if _embedder is not None:
        return _embedder

    if not quiet:
        print("\n" + "=" * 50, file=sys.stderr)
        safe_print(
            f"{get_icon('☕', '[...]')} Anima is waking up... take a coffee!",
            file=sys.stderr,
        )
        print("=" * 50, file=sys.stderr)

    start = time.time()

    try:
        from fastembed import TextEmbedding

        # Use persistent cache dir and avoid network calls if model already cached
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Check if model is already cached - use local_files_only to prevent network hangs
        # Model folder is named like "models--qdrant--bge-small-en-v1.5-onnx-q"
        cached_models = list(CACHE_DIR.glob("models--*bge-small*"))
        model_cached = len(cached_models) > 0

        print(f"[embedder] Cache dir: {CACHE_DIR}", file=sys.stderr)
        print(f"[embedder] Cached models: {cached_models}", file=sys.stderr)
        print(f"[embedder] local_files_only={model_cached}", file=sys.stderr)

        _embedder = TextEmbedding(
            model_name=MODEL_NAME,
            cache_dir=str(CACHE_DIR),
            local_files_only=model_cached,
        )
    except ImportError as e:
        raise ImportError("FastEmbed not installed. Run: uv add fastembed") from e

    _load_time = time.time() - start

    if not quiet:
        safe_print(
            f"{get_icon('🧠', '[SEM]')} Semantic memory online! ({_load_time:.1f}s)",
            file=sys.stderr,
        )
        print("=" * 50 + "\n", file=sys.stderr)

    return _embedder


def embed_text(text: str, quiet: bool = False) -> list[float]:
    """
    Generate embedding for a single text.

    Args:
        text: Text to embed
        quiet: Suppress model loading message

    Returns:
        List of floats (embedding vector)
    """
    model = get_embedder(quiet=quiet)
    embeddings = list(model.embed([text]))
    return embeddings[0].tolist()


def embed_batch(texts: list[str], quiet: bool = False) -> list[list[float]]:
    """
    Generate embeddings for multiple texts efficiently.

    Args:
        texts: List of texts to embed
        quiet: Suppress model loading message

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    model = get_embedder(quiet=quiet)
    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]


def get_model_load_time() -> Optional[float]:
    """Get the time it took to load the model (None if not loaded)."""
    return _load_time


def get_model_name() -> str:
    """Get the name of the embedding model."""
    return MODEL_NAME
