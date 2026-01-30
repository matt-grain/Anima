# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for the graph module."""

from datetime import datetime

from anima.graph.linker import (
    LinkType,
    MemoryLink,
    find_link_candidates,
    create_links_for_memory,
    suggest_link_type,
)
from anima.graph.traverser import (
    LinkedMemory,
    get_linked_memories,
    get_memory_chain,
)


class TestLinkType:
    """Tests for LinkType enum."""

    def test_all_types_exist(self):
        """All expected link types should exist."""
        assert LinkType.RELATES_TO.value == "RELATES_TO"
        assert LinkType.BUILDS_ON.value == "BUILDS_ON"
        assert LinkType.CONTRADICTS.value == "CONTRADICTS"
        assert LinkType.SUPERSEDES.value == "SUPERSEDES"

    def test_is_string_enum(self):
        """LinkType should be a string enum."""
        assert isinstance(LinkType.RELATES_TO, str)
        assert LinkType.RELATES_TO == "RELATES_TO"


class TestMemoryLink:
    """Tests for MemoryLink dataclass."""

    def test_creation(self):
        """Should create link with all fields."""
        link = MemoryLink(
            source_id="src",
            target_id="tgt",
            link_type=LinkType.RELATES_TO,
            similarity=0.75,
            created_at=datetime.now(),
        )
        assert link.source_id == "src"
        assert link.target_id == "tgt"
        assert link.link_type == LinkType.RELATES_TO
        assert link.similarity == 0.75

    def test_optional_fields(self):
        """Optional fields should default to None."""
        link = MemoryLink(
            source_id="src",
            target_id="tgt",
            link_type=LinkType.BUILDS_ON,
        )
        assert link.similarity is None
        assert link.created_at is None


class TestFindLinkCandidates:
    """Tests for find_link_candidates function."""

    def test_finds_similar_candidates(self):
        """Should find candidates above threshold."""
        source = [1.0, 0.0, 0.0]
        candidates = [
            ("mem1", "content1", [1.0, 0.0, 0.0]),  # identical
            ("mem2", "content2", [0.9, 0.1, 0.0]),  # very similar
            ("mem3", "content3", [0.0, 1.0, 0.0]),  # orthogonal
        ]

        results = find_link_candidates(source, candidates, threshold=0.5)

        assert len(results) == 2
        assert results[0].memory_id == "mem1"
        assert results[1].memory_id == "mem2"

    def test_respects_threshold(self):
        """Should filter by threshold."""
        source = [1.0, 0.0, 0.0]
        candidates = [
            ("mem1", "content1", [0.6, 0.4, 0.0]),
        ]

        high_threshold = find_link_candidates(source, candidates, threshold=0.9)
        low_threshold = find_link_candidates(source, candidates, threshold=0.5)

        assert len(high_threshold) == 0
        assert len(low_threshold) == 1

    def test_respects_max_links(self):
        """Should limit number of results."""
        source = [1.0, 0.0, 0.0]
        candidates = [
            ("mem1", "c1", [1.0, 0.0, 0.0]),
            ("mem2", "c2", [0.9, 0.1, 0.0]),
            ("mem3", "c3", [0.8, 0.2, 0.0]),
            ("mem4", "c4", [0.7, 0.3, 0.0]),
        ]

        results = find_link_candidates(source, candidates, threshold=0.5, max_links=2)
        assert len(results) == 2

    def test_excludes_ids(self):
        """Should exclude specified IDs."""
        source = [1.0, 0.0, 0.0]
        candidates = [
            ("mem1", "content1", [1.0, 0.0, 0.0]),
            ("mem2", "content2", [0.9, 0.1, 0.0]),
        ]

        results = find_link_candidates(
            source, candidates, threshold=0.5, exclude_ids={"mem1"}
        )

        assert len(results) == 1
        assert results[0].memory_id == "mem2"

    def test_skips_none_embeddings(self):
        """Should skip candidates with None embeddings."""
        source = [1.0, 0.0, 0.0]
        candidates = [
            ("mem1", "content1", [1.0, 0.0, 0.0]),
            ("mem2", "content2", None),
        ]

        results = find_link_candidates(source, candidates, threshold=0.5)
        assert len(results) == 1

    def test_sorted_by_similarity(self):
        """Results should be sorted by similarity descending."""
        source = [1.0, 0.0, 0.0]
        candidates = [
            ("low", "low", [0.6, 0.4, 0.0]),
            ("high", "high", [0.95, 0.05, 0.0]),
            ("mid", "mid", [0.8, 0.2, 0.0]),
        ]

        results = find_link_candidates(source, candidates, threshold=0.5)

        assert results[0].memory_id == "high"
        assert results[1].memory_id == "mid"
        assert results[2].memory_id == "low"


class TestCreateLinksForMemory:
    """Tests for create_links_for_memory function."""

    def test_creates_relates_to_links(self):
        """Should create RELATES_TO links for similar memories."""
        source_id = "source"
        source_emb = [1.0, 0.0, 0.0]
        candidates = [
            ("target1", "content1", [0.9, 0.1, 0.0]),
            ("target2", "content2", [0.8, 0.2, 0.0]),
        ]

        links = create_links_for_memory(
            source_id, source_emb, candidates, threshold=0.5
        )

        assert len(links) == 2
        assert all(link.link_type == LinkType.RELATES_TO for link in links)
        assert all(link.source_id == "source" for link in links)

    def test_excludes_self(self):
        """Should not link to itself."""
        source_id = "source"
        source_emb = [1.0, 0.0, 0.0]
        candidates = [
            ("source", "same", [1.0, 0.0, 0.0]),  # Same ID
            ("other", "other", [0.9, 0.1, 0.0]),
        ]

        links = create_links_for_memory(
            source_id, source_emb, candidates, threshold=0.5
        )

        assert len(links) == 1
        assert links[0].target_id == "other"


class TestSuggestLinkType:
    """Tests for suggest_link_type function."""

    def test_returns_relates_to(self):
        """Currently always returns RELATES_TO."""
        result = suggest_link_type("source content", "target content", 0.8)
        assert result == LinkType.RELATES_TO


class TestLinkedMemory:
    """Tests for LinkedMemory dataclass."""

    def test_creation(self):
        """Should create with all fields."""
        lm = LinkedMemory(
            memory_id="mem1",
            content="content",
            link_type=LinkType.RELATES_TO,
            similarity=0.75,
            depth=2,
        )
        assert lm.memory_id == "mem1"
        assert lm.depth == 2

    def test_default_depth(self):
        """Default depth should be 1."""
        lm = LinkedMemory(
            memory_id="mem1",
            content="content",
            link_type=LinkType.RELATES_TO,
        )
        assert lm.depth == 1


class TestGetLinkedMemories:
    """Tests for get_linked_memories function."""

    def test_gets_direct_links(self):
        """Should get directly linked memories."""
        # Mock functions
        def get_links(mem_id):
            if mem_id == "source":
                return [
                    MemoryLink("source", "target1", LinkType.RELATES_TO, 0.8),
                    MemoryLink("source", "target2", LinkType.RELATES_TO, 0.7),
                ]
            return []

        def get_memory(mem_id):
            memories = {
                "source": ("source", "Source content"),
                "target1": ("target1", "Target 1 content"),
                "target2": ("target2", "Target 2 content"),
            }
            return memories.get(mem_id)

        results = get_linked_memories("source", get_links, get_memory)

        assert len(results) == 2
        assert all(r.depth == 1 for r in results)

    def test_respects_max_depth(self):
        """Should not traverse beyond max_depth."""
        def get_links(mem_id):
            links = {
                "a": [MemoryLink("a", "b", LinkType.RELATES_TO)],
                "b": [MemoryLink("b", "c", LinkType.RELATES_TO)],
                "c": [MemoryLink("c", "d", LinkType.RELATES_TO)],
            }
            return links.get(mem_id, [])

        def get_memory(mem_id):
            return (mem_id, f"Content of {mem_id}")

        depth_1 = get_linked_memories("a", get_links, get_memory, max_depth=1)
        depth_2 = get_linked_memories("a", get_links, get_memory, max_depth=2)

        assert len(depth_1) == 1  # Only b
        assert len(depth_2) == 2  # b and c

    def test_filters_by_link_type(self):
        """Should filter by link type if specified."""
        def get_links(mem_id):
            if mem_id == "source":
                return [
                    MemoryLink("source", "t1", LinkType.RELATES_TO),
                    MemoryLink("source", "t2", LinkType.BUILDS_ON),
                ]
            return []

        def get_memory(mem_id):
            return (mem_id, f"Content of {mem_id}")

        results = get_linked_memories(
            "source", get_links, get_memory,
            link_types={LinkType.BUILDS_ON}
        )

        assert len(results) == 1
        assert results[0].link_type == LinkType.BUILDS_ON


class TestGetMemoryChain:
    """Tests for get_memory_chain function."""

    def test_follows_chain(self):
        """Should follow a chain of links."""
        def get_links(mem_id):
            chains = {
                "a": [MemoryLink("a", "b", LinkType.BUILDS_ON)],
                "b": [MemoryLink("b", "c", LinkType.BUILDS_ON)],
            }
            return chains.get(mem_id, [])

        def get_memory(mem_id):
            return (mem_id, f"Content of {mem_id}")

        chain = get_memory_chain("a", get_links, get_memory)

        assert len(chain) == 3
        assert chain[0] == ("a", "Content of a")
        assert chain[1] == ("b", "Content of b")
        assert chain[2] == ("c", "Content of c")

    def test_stops_at_max_length(self):
        """Should stop at max_length to prevent infinite loops."""
        def get_links(mem_id):
            # Infinite chain
            return [MemoryLink(mem_id, f"next_{mem_id}", LinkType.BUILDS_ON)]

        def get_memory(mem_id):
            return (mem_id, f"Content of {mem_id}")

        chain = get_memory_chain("start", get_links, get_memory, max_length=3)

        assert len(chain) == 3

    def test_detects_cycles(self):
        """Should detect and stop on cycles."""
        def get_links(mem_id):
            cycles = {
                "a": [MemoryLink("a", "b", LinkType.BUILDS_ON)],
                "b": [MemoryLink("b", "a", LinkType.BUILDS_ON)],  # Cycle!
            }
            return cycles.get(mem_id, [])

        def get_memory(mem_id):
            return (mem_id, f"Content of {mem_id}")

        chain = get_memory_chain("a", get_links, get_memory)

        assert len(chain) == 2  # Stops at cycle
