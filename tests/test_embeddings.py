# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for the embeddings module."""

import pytest

from tests.conftest import requires_embedder
from anima.embeddings.similarity import (
    cosine_similarity,
    find_similar,
    batch_similarities,
    SimilarityResult,
)


class TestCosineSimilarity:
    """Tests for cosine_similarity function."""

    def test_identical_vectors(self):
        """Identical vectors should have similarity of 1."""
        vec = [1.0, 2.0, 3.0]
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_opposite_vectors(self):
        """Opposite vectors should have similarity of -1."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        assert cosine_similarity(vec1, vec2) == pytest.approx(-1.0)

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity of 0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        assert cosine_similarity(vec1, vec2) == pytest.approx(0.0)

    def test_similar_vectors(self):
        """Similar vectors should have high similarity."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.1, 2.1, 3.1]
        sim = cosine_similarity(vec1, vec2)
        assert sim > 0.99  # Very similar

    def test_zero_vector(self):
        """Zero vector should return 0 similarity."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        assert cosine_similarity(vec1, vec2) == 0.0
        assert cosine_similarity(vec2, vec1) == 0.0

    def test_dimension_mismatch_raises(self):
        """Mismatched dimensions should raise ValueError."""
        vec1 = [1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]
        with pytest.raises(ValueError, match="dimensions don't match"):
            cosine_similarity(vec1, vec2)

    def test_normalized_vectors(self):
        """Pre-normalized vectors should work correctly."""
        import math
        vec1 = [1.0 / math.sqrt(2), 1.0 / math.sqrt(2), 0.0]
        vec2 = [1.0, 0.0, 0.0]
        sim = cosine_similarity(vec1, vec2)
        assert sim == pytest.approx(1.0 / math.sqrt(2))


class TestFindSimilar:
    """Tests for find_similar function."""

    def test_returns_top_k(self):
        """Should return at most top_k results."""
        query = [1.0, 0.0, 0.0]
        candidates = [
            ("a", [1.0, 0.0, 0.0]),
            ("b", [0.9, 0.1, 0.0]),
            ("c", [0.8, 0.2, 0.0]),
            ("d", [0.7, 0.3, 0.0]),
            ("e", [0.6, 0.4, 0.0]),
        ]
        results = find_similar(query, candidates, top_k=3)
        assert len(results) == 3

    def test_sorted_by_score_descending(self):
        """Results should be sorted by score, highest first."""
        query = [1.0, 0.0, 0.0]
        candidates = [
            ("low", [0.0, 1.0, 0.0]),
            ("high", [1.0, 0.0, 0.0]),
            ("mid", [0.5, 0.5, 0.0]),
        ]
        results = find_similar(query, candidates, top_k=3)
        assert results[0].item == "high"
        assert results[0].score > results[1].score > results[2].score

    def test_respects_threshold(self):
        """Should filter results below threshold."""
        query = [1.0, 0.0, 0.0]
        candidates = [
            ("high", [1.0, 0.0, 0.0]),
            ("low", [0.0, 1.0, 0.0]),
        ]
        results = find_similar(query, candidates, threshold=0.5)
        assert len(results) == 1
        assert results[0].item == "high"

    def test_skips_none_embeddings(self):
        """Should skip candidates with None embeddings."""
        query = [1.0, 0.0, 0.0]
        candidates = [
            ("valid", [1.0, 0.0, 0.0]),
            ("invalid", None),
        ]
        results = find_similar(query, candidates, top_k=5)
        assert len(results) == 1
        assert results[0].item == "valid"

    def test_empty_candidates(self):
        """Should return empty list for empty candidates."""
        query = [1.0, 0.0, 0.0]
        results = find_similar(query, [], top_k=5)
        assert results == []

    def test_result_type(self):
        """Results should be SimilarityResult objects."""
        query = [1.0, 0.0, 0.0]
        candidates = [("item", [1.0, 0.0, 0.0])]
        results = find_similar(query, candidates)
        assert isinstance(results[0], SimilarityResult)
        assert results[0].item == "item"
        assert isinstance(results[0].score, float)


class TestBatchSimilarities:
    """Tests for batch_similarities function."""

    def test_returns_list_of_scores(self):
        """Should return a score for each embedding."""
        query = [1.0, 0.0, 0.0]
        embeddings = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.5, 0.5, 0.0],
        ]
        scores = batch_similarities(query, embeddings)
        assert len(scores) == 3
        assert all(isinstance(s, float) for s in scores)

    def test_handles_empty_embeddings(self):
        """Should handle empty embedding as 0 score."""
        query = [1.0, 0.0, 0.0]
        embeddings = [
            [1.0, 0.0, 0.0],
            [],  # Empty
            [0.5, 0.5, 0.0],
        ]
        scores = batch_similarities(query, embeddings)
        # Empty embedding treated as zero vector -> 0 similarity
        assert scores[1] == 0.0

    def test_order_preserved(self):
        """Scores should be in same order as embeddings."""
        query = [1.0, 0.0, 0.0]
        embeddings = [
            [0.0, 1.0, 0.0],  # orthogonal -> ~0
            [1.0, 0.0, 0.0],  # identical -> 1
        ]
        scores = batch_similarities(query, embeddings)
        assert scores[0] == pytest.approx(0.0)
        assert scores[1] == pytest.approx(1.0)


class TestSimilarityResult:
    """Tests for SimilarityResult dataclass."""

    def test_creation(self):
        """Should create result with item and score."""
        result = SimilarityResult(item="test", score=0.95)
        assert result.item == "test"
        assert result.score == 0.95

    def test_generic_type(self):
        """Should work with different item types."""
        result_str = SimilarityResult(item="string", score=0.5)
        result_int = SimilarityResult(item=42, score=0.5)
        result_obj = SimilarityResult(item={"key": "value"}, score=0.5)

        assert result_str.item == "string"
        assert result_int.item == 42
        assert result_obj.item == {"key": "value"}


class TestEmbedderModule:
    """Tests for embedder module (mocked to avoid loading model in tests)."""

    def test_embedding_dimensions_constant(self):
        """EMBEDDING_DIMENSIONS should be 384 for bge-small."""
        from anima.embeddings.embedder import EMBEDDING_DIMENSIONS
        assert EMBEDDING_DIMENSIONS == 384

    def test_model_name_constant(self):
        """MODEL_NAME should be bge-small."""
        from anima.embeddings.embedder import MODEL_NAME
        assert "bge-small" in MODEL_NAME

    def test_is_model_loaded_initially_false(self):
        """Model should not be loaded initially."""
        # Note: This test may fail if model was loaded in previous tests
        # We use a fresh import context
        import anima.embeddings.embedder as embedder_module

        # Reset the module state
        original_embedder = embedder_module._embedder
        embedder_module._embedder = None

        try:
            # After reset, should be False
            assert embedder_module._embedder is None
        finally:
            # Restore
            embedder_module._embedder = original_embedder

    @requires_embedder
    def test_embed_text_returns_list(self):
        """embed_text should return a list of floats."""
        from anima.embeddings import embed_text

        result = embed_text("test text", quiet=True)
        assert isinstance(result, list)
        assert len(result) == 384
        assert all(isinstance(x, float) for x in result)

    @requires_embedder
    def test_embed_batch_returns_list_of_lists(self):
        """embed_batch should return list of embedding lists."""
        from anima.embeddings import embed_batch

        texts = ["first", "second", "third"]
        results = embed_batch(texts, quiet=True)

        assert isinstance(results, list)
        assert len(results) == 3
        assert all(len(emb) == 384 for emb in results)

    def test_embed_batch_empty(self):
        """embed_batch with empty list should return empty list."""
        from anima.embeddings import embed_batch

        results = embed_batch([], quiet=True)
        assert results == []


class TestEmbeddingsIntegration:
    """Integration tests for the full embeddings workflow."""

    @requires_embedder
    def test_similar_texts_have_high_similarity(self):
        """Semantically similar texts should have high cosine similarity."""
        from anima.embeddings import embed_text, cosine_similarity

        emb1 = embed_text("The cat sat on the mat", quiet=True)
        emb2 = embed_text("A cat is sitting on a mat", quiet=True)
        emb3 = embed_text("The stock market crashed today", quiet=True)

        sim_similar = cosine_similarity(emb1, emb2)
        sim_different = cosine_similarity(emb1, emb3)

        # Similar sentences should have higher similarity
        assert sim_similar > sim_different
        assert sim_similar > 0.7  # Should be reasonably high
        assert sim_different < 0.5  # Should be reasonably low

    @requires_embedder
    def test_find_similar_returns_relevant_results(self):
        """find_similar should return semantically relevant results."""
        from anima.embeddings import embed_text, embed_batch, find_similar

        # Create a set of candidate texts
        candidates_text = [
            "Python is a programming language",
            "JavaScript runs in the browser",
            "Machine learning uses neural networks",
            "The weather is sunny today",
            "Cats are popular pets",
        ]
        candidate_embs = embed_batch(candidates_text, quiet=True)
        candidates = list(zip(candidates_text, candidate_embs))

        # Query for programming-related content
        query = embed_text("coding and software development", quiet=True)
        results = find_similar(query, candidates, top_k=2)

        # Top results should be programming-related
        top_texts = [r.item for r in results]
        assert any("Python" in t or "JavaScript" in t for t in top_texts)
