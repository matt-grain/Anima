# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""FTS5-indexed storage for raw dialogue turns with BM25 + recency ranking."""

import math
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from anima.storage.subconscious_types import (
    DialogueTurn,
    SearchResult,
    SessionMeta,
    SubconsciousStats,
)
from anima.storage._connection import connect


def _get_default_subconscious_db_path() -> Path:
    """Get the default subconscious database path (~/.anima/subconscious.db)."""
    anima_dir = Path.home() / ".anima"
    anima_dir.mkdir(parents=True, exist_ok=True)
    return anima_dir / "subconscious.db"


class FTS5NotSupportedError(Exception):
    """Raised when the SQLite build does not include FTS5 support."""


class SubconsciousStore:
    """
    FTS5-indexed storage for raw conversation dialogue.

    Indexes JSONL session files for full-text search across all past
    conversations. Uses BM25 ranking blended with recency decay for
    relevance scoring.

    Stored separately from memories.db to keep the LTM store clean.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or _get_default_subconscious_db_path()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize schema and verify FTS5 support."""
        with self._connect() as conn:
            self._check_fts5_support(conn)
            schema_path = Path(__file__).parent / "schema_subconscious.sql"
            conn.executescript(schema_path.read_text(encoding="utf-8"))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")

    def _check_fts5_support(self, conn: sqlite3.Connection) -> None:
        """
        Verify FTS5 is available in this SQLite build.

        Raises FTS5NotSupportedError if unavailable. FTS5 is included in
        most standard SQLite builds but may be absent in minimal builds.
        """
        try:
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe USING fts5(x)")
            conn.execute("DROP TABLE IF EXISTS _fts5_probe")
        except sqlite3.OperationalError as e:
            raise FTS5NotSupportedError("FTS5 is not available in this SQLite build. Subconscious search requires FTS5 support.") from e

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open a connection with Anima's standard settings (see _connection.connect)."""
        with connect(self.db_path) as conn:
            yield conn

    def is_session_indexed(self, file_path: str, mtime: float) -> bool:
        """
        Check whether a file is already indexed at the given mtime.

        Used for incremental indexing: skip files that haven't changed
        since last index.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT mtime FROM sessions WHERE file_path = ?",
                (file_path,),
            ).fetchone()
            if not row:
                return False
            return float(row["mtime"]) >= mtime

    def index_session(self, meta: SessionMeta, dialogue: list[DialogueTurn]) -> int:
        """
        Index a session's dialogue turns into FTS5.

        Replaces any existing index entry for this session (upsert by
        session_id). Returns the number of turns indexed.

        Args:
            meta: Session metadata (source, project, file path, timestamp).
            dialogue: Ordered list of dialogue turns to index.

        Returns:
            Number of turns indexed.
        """
        file_mtime = os.path.getmtime(meta.file_path) if os.path.exists(meta.file_path) else 0.0

        with self._connect() as conn:
            # Remove existing entries for this session (full reindex)
            conn.execute("DELETE FROM messages WHERE session_id = ?", (meta.session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (meta.session_id,))

            # Insert session metadata
            conn.execute(
                """
                INSERT INTO sessions (session_id, source, project, file_path, timestamp, mtime)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    meta.session_id,
                    meta.source,
                    meta.project,
                    meta.file_path,
                    meta.timestamp,
                    file_mtime,
                ),
            )

            # Bulk insert dialogue turns into FTS5
            conn.executemany(
                "INSERT INTO messages (session_id, role, text) VALUES (?, ?, ?)",
                [(meta.session_id, turn.role, turn.content) for turn in dialogue],
            )

        return len(dialogue)

    def search(
        self,
        query: str,
        project: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        Full-text search across indexed dialogue turns.

        Uses FTS5 BM25 ranking blended with a 30-day half-life recency
        boost (80% relevance, 20% recency).

        Args:
            query: FTS5 query string (supports AND, OR, phrase quotes, etc.).
            project: Optional project path filter.
            days: Optional recency filter — only sessions within N days.
            limit: Maximum number of results to return.

        Returns:
            List of SearchResult ordered by blended score (best first).
        """
        sql = """
            SELECT
                s.session_id,
                s.source,
                s.project,
                s.timestamp,
                snippet(messages, 2, '**', '**', '...', 16) AS excerpt,
                bm25(messages) AS bm25_rank
            FROM messages
            JOIN sessions s ON messages.session_id = s.session_id
            WHERE messages MATCH ?
        """
        params: list[object] = [query]

        if project is not None:
            sql += " AND s.project = ?"
            params.append(project)

        if days is not None:
            cutoff_ms = int((time.time() - days * 86_400) * 1000)
            sql += " AND s.timestamp >= ?"
            params.append(cutoff_ms)

        # Fetch more than limit to allow reranking after blended score
        sql += f" ORDER BY bm25_rank LIMIT {limit * 3}"

        try:
            with self._connect() as conn:
                rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            # Malformed FTS5 query (e.g. unbalanced quotes) — return empty
            return []

        results: list[SearchResult] = []
        for row in rows:
            blended = self._calculate_blended_score(
                bm25_rank=float(row["bm25_rank"]),
                timestamp_ms=int(row["timestamp"] or 0),
            )
            results.append(
                SearchResult(
                    session_id=row["session_id"],
                    source=row["source"],
                    project=row["project"] or "",
                    timestamp=int(row["timestamp"] or 0),
                    excerpt=row["excerpt"] or "",
                    score=blended,
                )
            )

        # Sort by blended score (lower = better, matches BM25 negative convention)
        results.sort(key=lambda r: r.score)
        return results[:limit]

    def get_stats(self) -> SubconsciousStats:
        """Return statistics about the subconscious database."""
        with self._connect() as conn:
            total_sessions: int = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            total_messages: int = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            last_row = conn.execute("SELECT MAX(indexed_at) FROM sessions").fetchone()

        last_indexed: datetime | None = None
        if last_row and last_row[0]:
            last_indexed = datetime.fromisoformat(last_row[0])

        db_size = int(os.path.getsize(self.db_path)) if self.db_path.exists() else 0

        return SubconsciousStats(
            total_sessions=total_sessions,
            total_messages=total_messages,
            last_indexed=last_indexed,
            db_size_bytes=db_size,
        )

    def _calculate_blended_score(self, bm25_rank: float, timestamp_ms: int) -> float:
        """
        Calculate blended relevance score: 80% BM25 + 20% recency.

        BM25 rank is negative (more negative = better match).
        Recency uses 30-day half-life decay.
        """
        now_ms = time.time() * 1000
        age_days = max((now_ms - timestamp_ms) / 86_400_000, 0)
        recency_boost = math.exp(-0.693 * age_days / 30)  # 30-day half-life
        return bm25_rank * (1 - 0.2 * recency_boost)
