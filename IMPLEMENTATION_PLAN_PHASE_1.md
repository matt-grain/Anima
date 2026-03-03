# Phase 1: Subconscious Storage Layer

**Dependencies:** None
**Agent:** python-mcp-expert

Create the FTS5-based subconscious storage with proper separation from conscious memories.

---

## Files to Create

### `anima/storage/subconscious_types.py`

**Purpose:** Type definitions for subconscious storage (dialogue turns, search results, session metadata)

**Fields:**
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DialogueTurn:
    """A single turn in a conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: int | None = None  # ms since epoch

@dataclass
class SessionMeta:
    """Metadata about an indexed session."""
    session_id: str
    source: str  # 'claude', 'antigravity', 'opencode', 'gemini'
    project: str  # Project path
    file_path: str  # Path to the JSONL file
    timestamp: int  # Earliest message timestamp (ms since epoch)

@dataclass
class SearchResult:
    """A single search result from subconscious."""
    session_id: str
    source: str
    project: str
    timestamp: int
    excerpt: str  # FTS5 snippet with **highlights**
    score: float  # Blended BM25 + recency score

@dataclass
class SubconsciousStats:
    """Statistics about the subconscious database."""
    total_sessions: int
    total_messages: int
    last_indexed: datetime | None
    db_size_bytes: int
```

**Constraints:**
- Use `@dataclass` (not Pydantic) for internal types
- All fields typed
- No external dependencies

**Reference:** `anima/core/types.py` for existing type patterns

---

### `anima/storage/schema_subconscious.sql`

**Purpose:** SQL schema for subconscious.db (FTS5 full-text search)

**Content:**
```sql
-- Subconscious Database Schema
-- FTS5 full-text search for raw dialogue indexing

-- Sessions table (metadata)
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,           -- 'claude', 'antigravity', 'opencode', 'gemini'
    project TEXT,                   -- Project path (can be null for agent-wide)
    file_path TEXT NOT NULL,        -- Path to source JSONL
    timestamp INTEGER,              -- Earliest message timestamp (ms)
    mtime REAL NOT NULL,            -- File modification time for incremental indexing
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS messages USING fts5(
    session_id UNINDEXED,           -- Don't index session_id, just store it
    role,                           -- 'user' or 'assistant'
    text,                           -- The actual message content
    tokenize='porter unicode61'     -- Porter stemming + unicode support
);

-- Index for recency filtering
CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON sessions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project);
CREATE INDEX IF NOT EXISTS idx_sessions_source ON sessions(source);
```

**Constraints:**
- FTS5 with Porter stemmer for natural language
- Session metadata in regular table, messages in FTS5 virtual table
- `UNINDEXED` for session_id to save space

---

### `anima/storage/subconscious.py`

**Purpose:** FTS5-indexed storage for raw dialogue turns with BM25 + recency ranking

**Dependencies:** sqlite3 (stdlib), pathlib, math, time

**Public API:**
```python
class FTS5NotSupportedError(Exception):
    """Raised when SQLite doesn't have FTS5 support."""
    pass

class SubconsciousStore:
    def __init__(self, db_path: Path | None = None) -> None:
        """
        Initialize subconscious store.

        Args:
            db_path: Path to database (default: ~/.anima/subconscious.db)

        Raises:
            FTS5NotSupportedError: If SQLite build lacks FTS5
        """

    def index_session(
        self,
        meta: SessionMeta,
        dialogue: list[DialogueTurn],
    ) -> int:
        """
        Index a session's dialogue into FTS5.

        Args:
            meta: Session metadata
            dialogue: List of dialogue turns to index

        Returns:
            Number of messages indexed
        """

    def search(
        self,
        query: str,
        project: str | None = None,
        days: int | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        Search indexed dialogues with BM25 + recency ranking.

        Args:
            query: FTS5 search query (supports phrases, AND/OR/NOT)
            project: Filter to specific project path (prefix match)
            days: Only return results from last N days
            limit: Maximum results to return

        Returns:
            List of SearchResult, ranked by blended score
        """

    def get_stats(self) -> SubconsciousStats:
        """Get indexing statistics."""

    def is_session_indexed(self, file_path: str, mtime: float) -> bool:
        """Check if a session file is already indexed with current mtime."""
```

**Internal Methods:**
```python
def _init_db(self) -> None:
    """Initialize database schema, check FTS5 support."""
    # 1. Try creating FTS5 table
    # 2. If sqlite3.OperationalError with "no such module: fts5", raise FTS5NotSupportedError
    # 3. Apply schema from schema_subconscious.sql
    # 4. Enable WAL mode: PRAGMA journal_mode=WAL

def _check_fts5_support(self, conn: sqlite3.Connection) -> bool:
    """Check if FTS5 is available in this SQLite build."""
    try:
        conn.execute("CREATE VIRTUAL TABLE _fts5_test USING fts5(x)")
        conn.execute("DROP TABLE _fts5_test")
        return True
    except sqlite3.OperationalError:
        return False

def _calculate_blended_score(self, bm25_rank: float, timestamp_ms: int) -> float:
    """
    Calculate blended relevance score: 80% BM25 + 20% recency.

    Recency uses 30-day half-life decay:
        recency_boost = exp(-0.693 * age_days / 30)

    BM25 rank is negative (more negative = better match).
    Final score blends: rank * (1 - 0.2 * recency_boost)
    """
    now_ms = time.time() * 1000
    age_days = max((now_ms - timestamp_ms) / 86_400_000, 0)
    recency_boost = math.exp(-0.693 * age_days / 30)  # 30-day half-life
    return bm25_rank * (1 - 0.2 * recency_boost)
```

**Constraints:**
- Database path: `~/.anima/subconscious.db` (separate from memories.db)
- Use WAL mode for concurrent reads: `PRAGMA journal_mode=WAL`
- Use `PRAGMA synchronous=NORMAL` for performance
- BM25 ranking with 30-day half-life recency boost (80% BM25, 20% recency)
- Porter stemming for natural language queries
- Skip indexing if session already indexed with same mtime (incremental)
- Use FTS5 `snippet()` function for excerpt generation with `**highlights**`

**Error Handling:**
- Raise `FTS5NotSupportedError` if FTS5 unavailable (checked at init)
- Log warning if FTS5 missing, don't crash the application
- Handle `sqlite3.OperationalError` for malformed queries gracefully

**Reference:** `anima/storage/sqlite.py` for connection patterns, context manager usage

---

### `anima/storage/__init__.py` (MODIFY)

**Change:** Export SubconsciousStore and types

**Exact change:**
```python
# Add to imports
from anima.storage.subconscious import SubconsciousStore, FTS5NotSupportedError
from anima.storage.subconscious_types import (
    DialogueTurn,
    SessionMeta,
    SearchResult,
    SubconsciousStats,
)

# Add to __all__
__all__ = [
    # ... existing exports ...
    "SubconsciousStore",
    "FTS5NotSupportedError",
    "DialogueTurn",
    "SessionMeta",
    "SearchResult",
    "SubconsciousStats",
]
```

---

## Verification

After implementing Phase 1:

```bash
# Type check
uv run pyright anima/storage/subconscious*.py

# Quick smoke test (should not crash)
python -c "from anima.storage import SubconsciousStore; s = SubconsciousStore(); print(s.get_stats())"
```
