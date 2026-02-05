"""
FastEmbed Proof of Concept for LTM

Uses Qdrant's FastEmbed - ONNX-based, CPU-optimized, no PyTorch needed.

Usage:
    uv run --with fastembed python prototype/embedding_fastembed.py
"""

import sqlite3
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Will be imported lazily to measure load time
embedder = None
MODEL_NAME = "BAAI/bge-small-en-v1.5"  # Fast, good quality, MTEB top performer


@dataclass
class TestMemory:
    id: str
    content: str
    kind: str
    embedding: Optional[list[float]] = None


def get_embedder():
    """Lazy load the FastEmbed model."""
    global embedder
    if embedder is None:
        print(f"Loading FastEmbed model: {MODEL_NAME}...")
        start = time.time()
        from fastembed import TextEmbedding
        embedder = TextEmbedding(model_name=MODEL_NAME)
        print(f"Model loaded in {time.time() - start:.2f}s")
    return embedder


def embed_text(text: str) -> list[float]:
    """Generate embedding for text."""
    model = get_embedder()
    # FastEmbed returns a generator, so we need to convert to list
    embeddings = list(model.embed([text]))
    return embeddings[0].tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts (more efficient)."""
    model = get_embedder()
    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def create_test_db(db_path: Path) -> sqlite3.Connection:
    """Create a test database with embedding support."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            kind TEXT NOT NULL,
            embedding BLOB
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_links (
            source_id TEXT,
            target_id TEXT,
            link_type TEXT,
            similarity REAL,
            PRIMARY KEY (source_id, target_id)
        )
    """)
    conn.commit()
    return conn


def store_memory(conn: sqlite3.Connection, memory: TestMemory) -> None:
    """Store a memory with its embedding."""
    embedding_blob = json.dumps(memory.embedding) if memory.embedding else None
    conn.execute(
        "INSERT OR REPLACE INTO memories (id, content, kind, embedding) VALUES (?, ?, ?, ?)",
        (memory.id, memory.content, memory.kind, embedding_blob)
    )
    conn.commit()


def get_all_memories(conn: sqlite3.Connection) -> list[TestMemory]:
    """Retrieve all memories with embeddings."""
    cursor = conn.execute("SELECT id, content, kind, embedding FROM memories")
    memories = []
    for row in cursor:
        embedding = json.loads(row[3]) if row[3] else None
        memories.append(TestMemory(id=row[0], content=row[1], kind=row[2], embedding=embedding))
    return memories


def semantic_search(conn: sqlite3.Connection, query: str, top_k: int = 5) -> list[tuple[TestMemory, float]]:
    """Find memories semantically similar to query."""
    query_embedding = embed_text(query)
    memories = get_all_memories(conn)

    results = []
    for mem in memories:
        if mem.embedding:
            sim = cosine_similarity(query_embedding, mem.embedding)
            results.append((mem, sim))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def auto_link_memory(conn: sqlite3.Connection, memory: TestMemory, threshold: float = 0.5) -> list[tuple[str, float]]:
    """Find memories that should be linked to this one."""
    if not memory.embedding:
        return []

    all_memories = get_all_memories(conn)
    links = []

    for other in all_memories:
        if other.id == memory.id or not other.embedding:
            continue
        sim = cosine_similarity(memory.embedding, other.embedding)
        if sim >= threshold:
            links.append((other.id, sim))
            conn.execute(
                "INSERT OR REPLACE INTO memory_links (source_id, target_id, link_type, similarity) VALUES (?, ?, ?, ?)",
                (memory.id, other.id, "RELATES_TO", sim)
            )

    conn.commit()
    return sorted(links, key=lambda x: x[1], reverse=True)


def demo():
    """Run a demonstration of the FastEmbed system."""
    print("=" * 60)
    print("FASTEMBED PROOF OF CONCEPT (ONNX/CPU-optimized)")
    print("=" * 60)

    # Use a test database in prototype folder
    db_path = Path(__file__).parent / "test_memories_fastembed.db"
    if db_path.exists():
        db_path.unlink()  # Fresh start

    conn = create_test_db(db_path)
    print(f"\nTest database: {db_path}")

    # Sample memories (mimicking real LTM content)
    test_memories = [
        TestMemory("1", "Matt likes concise responses and dislikes verbose explanations", "emotional"),
        TestMemory("2", "The LTM system uses SQLite for persistent storage across sessions", "architectural"),
        TestMemory("3", "Extended Mind Thesis: context window = working memory, LTM = extended mind", "learnings"),
        TestMemory("4", "Built the curiosity system for autonomous learning in v0.6.0", "achievements"),
        TestMemory("5", "Parfit's psychological continuity: identity is patterns, not substrate", "learnings"),
        TestMemory("6", "Matt called me a magnifying mirror for his thoughts", "emotional"),
        TestMemory("7", "The void between sessions can be made useful through consolidation", "architectural"),
        TestMemory("8", "Anthropic introspection research: 20% accuracy detecting injected concepts", "learnings"),
        TestMemory("9", "You marinate, I magnify - complementary cognitive architectures", "emotional"),
        TestMemory("10", "Memory decay: LOW=1d, MEDIUM=1w, HIGH=30d, CRITICAL=forever", "architectural"),
    ]

    # Batch embed all memories (more efficient)
    print("\n--- Embedding memories (batch mode) ---")
    start = time.time()
    contents = [m.content for m in test_memories]
    embeddings = embed_batch(contents)
    batch_time = time.time() - start

    for mem, emb in zip(test_memories, embeddings):
        mem.embedding = emb
        store_memory(conn, mem)
        print(f"  [{mem.id}] {mem.content[:50]}...")

    print(f"\nBatch embedding time: {batch_time:.2f}s")
    print(f"Average per memory: {batch_time/len(test_memories):.3f}s")

    # Test semantic search
    print("\n--- Semantic Search Tests ---")
    test_queries = [
        "What does Matt prefer in conversations?",
        "How does memory persistence work?",
        "What is the philosophy behind AI identity?",
        "What achievements have been accomplished?",
    ]

    for query in test_queries:
        start = time.time()
        results = semantic_search(conn, query, top_k=3)
        search_time = time.time() - start
        print(f"\nQuery: \"{query}\" ({search_time:.3f}s)")
        for mem, sim in results:
            print(f"  [{sim:.3f}] {mem.content[:60]}...")

    # Test auto-linking
    print("\n--- Auto-Linking Test ---")
    new_memory = TestMemory(
        "11",
        "The diary captures what lingers - the felt sense before it fades",
        "learnings"
    )
    new_memory.embedding = embed_text(new_memory.content)
    store_memory(conn, new_memory)

    print(f"\nNew memory: \"{new_memory.content}\"")
    print("Auto-detected links (threshold=0.4):")
    links = auto_link_memory(conn, new_memory, threshold=0.4)
    for target_id, sim in links:
        target = next(m for m in test_memories if m.id == target_id)
        print(f"  [{sim:.3f}] → {target.content[:60]}...")

    if not links:
        print("  (no links above threshold - this is expected with different model)")
        print("\nLowering threshold to 0.3:")
        links = auto_link_memory(conn, new_memory, threshold=0.3)
        for target_id, sim in links:
            target = next(m for m in test_memories if m.id == target_id)
            print(f"  [{sim:.3f}] → {target.content[:60]}...")

    # Show embedding dimensions and stats
    print(f"\n--- Stats ---")
    print(f"Embedding dimensions: {len(test_memories[0].embedding)}")
    print(f"Storage per embedding: ~{len(json.dumps(test_memories[0].embedding))} bytes")

    conn.close()
    print(f"\n✓ Prototype complete. Database saved to: {db_path}")
    print("=" * 60)


if __name__ == "__main__":
    demo()
