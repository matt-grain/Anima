"""
Query Real Memories with FastEmbed

Tests semantic search against actual LTM memories.
Shows "waking up" message during model load!

Usage:
    uv run --with fastembed python prototype/query_real_memories.py
"""

import sqlite3
import time
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Globals
embedder = None
MODEL_NAME = "BAAI/bge-small-en-v1.5"


@dataclass
class Memory:
    id: str
    content: str
    kind: str
    impact: str
    embedding: Optional[list[float]] = None


def wake_up_message():
    """Show a fun waking up message during model load."""
    frames = [
        "☕ Anima is waking up",
        "☕ Anima is waking up.",
        "☕ Anima is waking up..",
        "☕ Anima is waking up...",
        "🧠 Loading semantic memory",
        "🧠 Loading semantic memory.",
        "🧠 Loading semantic memory..",
        "🧠 Loading semantic memory...",
    ]
    return frames


def get_embedder():
    """Load FastEmbed model with waking up animation."""
    global embedder
    if embedder is None:
        print("\n" + "=" * 50)
        print("☕ Anima is waking up... take a coffee!")
        print("=" * 50)

        start = time.time()
        from fastembed import TextEmbedding
        embedder = TextEmbedding(model_name=MODEL_NAME)
        load_time = time.time() - start

        print(f"🧠 Semantic memory online! ({load_time:.1f}s)")
        print("=" * 50 + "\n")
    return embedder


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts efficiently."""
    model = get_embedder()
    return [e.tolist() for e in model.embed(texts)]


def embed_text(text: str) -> list[float]:
    """Embed single text."""
    return embed_texts([text])[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def load_memories(db_path: Path) -> list[Memory]:
    """Load memories from the real database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        SELECT id, content, kind, impact
        FROM memories
        WHERE superseded_by IS NULL
        ORDER BY created_at DESC
    """)

    memories = []
    for row in cursor:
        memories.append(Memory(
            id=row[0][:8],  # Truncate ID for display
            content=row[1],
            kind=row[2],
            impact=row[3]
        ))

    conn.close()
    return memories


def semantic_search(memories: list[Memory], query: str, top_k: int = 5) -> list[tuple[Memory, float]]:
    """Search memories by semantic similarity."""
    query_emb = embed_text(query)

    results = []
    for mem in memories:
        if mem.embedding:
            sim = cosine_similarity(query_emb, mem.embedding)
            results.append((mem, sim))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def find_related(memories: list[Memory], source: Memory, top_k: int = 5) -> list[tuple[Memory, float]]:
    """Find memories related to a source memory."""
    if not source.embedding:
        return []

    results = []
    for mem in memories:
        if mem.id == source.id or not mem.embedding:
            continue
        sim = cosine_similarity(source.embedding, mem.embedding)
        results.append((mem, sim))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def interactive_mode(memories: list[Memory]):
    """Interactive query mode."""
    print("\n🔍 Interactive Semantic Search")
    print("   Type a query to search memories")
    print("   Type 'link <id>' to find related memories")
    print("   Type 'quit' to exit\n")

    while True:
        try:
            query = input("Query> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not query:
            continue
        if query.lower() == 'quit':
            break

        if query.lower().startswith('link '):
            # Find related to a specific memory
            mem_id = query[5:].strip()
            source = next((m for m in memories if m.id.startswith(mem_id)), None)
            if not source:
                print(f"  Memory not found: {mem_id}")
                continue

            print(f"\n  Related to: {source.content[:60]}...")
            results = find_related(memories, source, top_k=5)
            for mem, sim in results:
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "⚪"}.get(mem.impact, "⚪")
                print(f"  {icon} [{sim:.3f}] {mem.content[:70]}...")
            print()
        else:
            # Semantic search
            start = time.time()
            results = semantic_search(memories, query, top_k=5)
            search_time = time.time() - start

            print(f"\n  Results for \"{query}\" ({search_time:.3f}s):")
            for mem, sim in results:
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "⚪"}.get(mem.impact, "⚪")
                print(f"  {icon} [{sim:.3f}] [{mem.id}] {mem.content[:65]}...")
            print()


def main():
    db_path = Path(__file__).parent / "memories_copy.db"

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    print("=" * 60)
    print("SEMANTIC SEARCH ON REAL MEMORIES")
    print("=" * 60)

    # Load memories
    print(f"\nLoading memories from: {db_path}")
    memories = load_memories(db_path)
    print(f"Found {len(memories)} active memories")

    # Show breakdown by kind
    by_kind = {}
    for m in memories:
        by_kind[m.kind] = by_kind.get(m.kind, 0) + 1
    print(f"By kind: {by_kind}")

    # Embed all memories (batch)
    print(f"\nEmbedding {len(memories)} memories...")
    start = time.time()
    contents = [m.content for m in memories]
    embeddings = embed_texts(contents)
    embed_time = time.time() - start

    for mem, emb in zip(memories, embeddings):
        mem.embedding = emb

    print(f"Embedded in {embed_time:.2f}s ({embed_time/len(memories):.3f}s per memory)")

    # Run some test queries
    print("\n" + "=" * 60)
    print("TEST QUERIES")
    print("=" * 60)

    test_queries = [
        "What is Matt's personality and preferences?",
        "How does the LTM system work architecturally?",
        "What philosophical frameworks inform AI identity?",
        "What achievements has Anima accomplished?",
        "What is the relationship between Matt and Anima?",
        "How does memory decay work?",
        "What research has been done on AI introspection?",
    ]

    for query in test_queries:
        results = semantic_search(memories, query, top_k=3)
        print(f"\n📝 \"{query}\"")
        for mem, sim in results:
            icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "⚪"}.get(mem.impact, "⚪")
            # Truncate content smartly
            content = mem.content[:80].replace('\n', ' ')
            if len(mem.content) > 80:
                content += "..."
            print(f"   {icon} [{sim:.3f}] {content}")

    # Interactive mode
    print("\n" + "=" * 60)
    interactive_mode(memories)

    print("\n👋 Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
