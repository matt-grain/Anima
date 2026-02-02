# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Curiosity queue storage for autonomous research."""

import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Iterator

from anima.core import RegionType
from anima.storage.sqlite import get_default_db_path


class CuriosityStatus(str, Enum):
    """Status of a curiosity item."""

    OPEN = "OPEN"  # Not yet researched
    RESEARCHED = "RESEARCHED"  # Research completed
    DISMISSED = "DISMISSED"  # User decided not to pursue


@dataclass
class Curiosity:
    """A question or topic in the research queue."""

    id: str
    agent_id: str
    region: RegionType
    project_id: Optional[str]
    question: str
    context: Optional[str]
    recurrence_count: int
    first_seen: datetime
    last_seen: datetime
    status: CuriosityStatus
    priority_boost: int = 0

    @property
    def priority_score(self) -> int:
        """Calculate priority score for sorting."""
        # Base score from recurrence
        score = self.recurrence_count * 10

        # Add priority boost
        score += self.priority_boost

        # Recency bonus: +5 if seen in last 7 days
        days_since = (datetime.now() - self.last_seen).days
        if days_since <= 7:
            score += 5

        return score


class CuriosityStore:
    """Storage operations for the curiosity queue."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_default_db_path()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def add_curiosity(
        self,
        agent_id: str,
        question: str,
        region: RegionType = RegionType.AGENT,
        project_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Curiosity:
        """
        Add a question to the curiosity queue.

        If a similar question already exists (same question text), bumps
        its recurrence count instead of creating a duplicate.

        Returns the created or updated Curiosity.
        """
        # Check for existing similar question
        existing = self.find_similar(agent_id, question, region, project_id)
        if existing:
            self.bump_recurrence(existing.id)
            return self.get_curiosity(existing.id)  # type: ignore

        # Create new curiosity
        now = datetime.now()
        curiosity = Curiosity(
            id=str(uuid.uuid4())[:8],
            agent_id=agent_id,
            region=region,
            project_id=project_id,
            question=question,
            context=context,
            recurrence_count=1,
            first_seen=now,
            last_seen=now,
            status=CuriosityStatus.OPEN,
            priority_boost=0,
        )

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO curiosity_queue (
                    id, agent_id, region, project_id, question, context,
                    recurrence_count, first_seen, last_seen, status, priority_boost
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    curiosity.id,
                    curiosity.agent_id,
                    curiosity.region.value,
                    curiosity.project_id,
                    curiosity.question,
                    curiosity.context,
                    curiosity.recurrence_count,
                    curiosity.first_seen.isoformat(),
                    curiosity.last_seen.isoformat(),
                    curiosity.status.value,
                    curiosity.priority_boost,
                ),
            )

        return curiosity

    def get_curiosity(self, curiosity_id: str) -> Optional[Curiosity]:
        """Get a curiosity by ID (supports partial ID matching)."""
        with self._connect() as conn:
            # Try exact match first
            row = conn.execute("SELECT * FROM curiosity_queue WHERE id = ?", (curiosity_id,)).fetchone()

            if not row:
                # Try prefix match
                row = conn.execute(
                    "SELECT * FROM curiosity_queue WHERE id LIKE ?",
                    (f"{curiosity_id}%",),
                ).fetchone()

            if not row:
                return None

            return self._row_to_curiosity(row)

    def get_curiosities(
        self,
        agent_id: str,
        region: Optional[RegionType] = None,
        project_id: Optional[str] = None,
        status: CuriosityStatus = CuriosityStatus.OPEN,
    ) -> list[Curiosity]:
        """
        Get curiosities for an agent with optional filters.

        Returns curiosities sorted by priority score (highest first).
        """
        query = "SELECT * FROM curiosity_queue WHERE agent_id = ? AND status = ?"
        params: list = [agent_id, status.value]

        if region:
            query += " AND region = ?"
            params.append(region.value)

        if project_id:
            # Include both project-specific AND agent-wide curiosities
            query += " AND (project_id = ? OR region = 'AGENT')"
            params.append(project_id)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            curiosities = [self._row_to_curiosity(row) for row in rows]

        # Sort by priority score descending
        return sorted(curiosities, key=lambda c: c.priority_score, reverse=True)

    def get_top_curiosity(
        self,
        agent_id: str,
        region: Optional[RegionType] = None,
        project_id: Optional[str] = None,
    ) -> Optional[Curiosity]:
        """Get the highest priority open curiosity."""
        curiosities = self.get_curiosities(
            agent_id=agent_id,
            region=region,
            project_id=project_id,
            status=CuriosityStatus.OPEN,
        )
        return curiosities[0] if curiosities else None

    def bump_recurrence(self, curiosity_id: str) -> None:
        """Increment recurrence count and update last_seen."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE curiosity_queue
                SET recurrence_count = recurrence_count + 1,
                    last_seen = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), curiosity_id),
            )

    def update_status(self, curiosity_id: str, status: CuriosityStatus) -> None:
        """Update the status of a curiosity."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE curiosity_queue SET status = ? WHERE id = ?",
                (status.value, curiosity_id),
            )

    def boost_priority(self, curiosity_id: str, boost: int = 10) -> None:
        """Add to a curiosity's priority boost."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE curiosity_queue SET priority_boost = priority_boost + ? WHERE id = ?",
                (boost, curiosity_id),
            )

    def find_similar(
        self,
        agent_id: str,
        question: str,
        region: Optional[RegionType] = None,
        project_id: Optional[str] = None,
    ) -> Optional[Curiosity]:
        """
        Find an existing curiosity with the same or very similar question.

        Uses exact match for now. Future: could use fuzzy matching.
        """
        query = """
            SELECT * FROM curiosity_queue
            WHERE agent_id = ? AND question = ? AND status = 'OPEN'
        """
        params: list = [agent_id, question]

        if region:
            query += " AND region = ?"
            params.append(region.value)

        if project_id:
            query += " AND (project_id = ? OR project_id IS NULL)"
            params.append(project_id)

        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
            if not row:
                return None
            return self._row_to_curiosity(row)

    def count_open(self, agent_id: str, project_id: Optional[str] = None) -> int:
        """Count open curiosities for an agent."""
        query = "SELECT COUNT(*) FROM curiosity_queue WHERE agent_id = ? AND status = 'OPEN'"
        params: list = [agent_id]

        if project_id:
            query += " AND (project_id = ? OR region = 'AGENT')"
            params.append(project_id)

        with self._connect() as conn:
            return conn.execute(query, params).fetchone()[0]

    def _row_to_curiosity(self, row: sqlite3.Row) -> Curiosity:
        """Convert a database row to a Curiosity object."""
        return Curiosity(
            id=row["id"],
            agent_id=row["agent_id"],
            region=RegionType(row["region"]),
            project_id=row["project_id"],
            question=row["question"],
            context=row["context"],
            recurrence_count=row["recurrence_count"],
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_seen=datetime.fromisoformat(row["last_seen"]),
            status=CuriosityStatus(row["status"]),
            priority_boost=row["priority_boost"],
        )


# --- Settings helpers for tracking last_research ---


def get_setting(key: str, db_path: Optional[Path] = None) -> Optional[str]:
    """Get a setting value."""
    db_path = db_path or get_default_db_path()
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        # Check if settings table exists (may not if database not migrated to v3)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        if not cursor.fetchone():
            return None  # Table doesn't exist yet

        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def set_setting(key: str, value: str, db_path: Optional[Path] = None) -> None:
    """Set a setting value."""
    db_path = db_path or get_default_db_path()
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        # Check if settings table exists (may not if database not migrated to v3)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        if not cursor.fetchone():
            # Create the table if it doesn't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_last_research() -> Optional[datetime]:
    """Get the timestamp of the last research session."""
    value = get_setting("last_research")
    if value:
        return datetime.fromisoformat(value)
    return None


def set_last_research(when: Optional[datetime] = None) -> None:
    """Record when research was last done."""
    when = when or datetime.now()
    set_setting("last_research", when.isoformat())
