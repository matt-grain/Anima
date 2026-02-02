# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Dissonance Queue - Contradictions needing human resolution.

When N3 detects contradictions that can't be easily resolved,
they're queued here for the human to help work through.
Matt as Eliza: "help me work through this cognitive dissonance."
"""

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class DissonanceStatus(str, Enum):
    """Status of a dissonance item."""

    OPEN = "OPEN"  # Awaiting human resolution
    RESOLVED = "RESOLVED"  # Human helped resolve
    DISMISSED = "DISMISSED"  # Not actually a contradiction


@dataclass
class Dissonance:
    """A cognitive dissonance requiring human help."""

    id: str
    agent_id: str
    memory_id_a: str
    memory_id_b: str
    description: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    status: DissonanceStatus = DissonanceStatus.OPEN


class DissonanceStore:
    """Storage for dissonance queue (uses same DB as memories)."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize dissonance store."""
        if db_path is None:
            from anima.storage.sqlite import get_default_db_path

            db_path = get_default_db_path()
        self.db_path = db_path
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create dissonance table if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dissonance_queue (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    memory_id_a TEXT NOT NULL,
                    memory_id_b TEXT NOT NULL,
                    description TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    resolved_at TEXT,
                    resolution TEXT,
                    status TEXT DEFAULT 'OPEN'
                )
            """)
            conn.commit()

    def add_dissonance(
        self,
        agent_id: str,
        memory_id_a: str,
        memory_id_b: str,
        description: str,
    ) -> Dissonance:
        """Add a new dissonance to the queue."""
        dissonance = Dissonance(
            id=str(uuid.uuid4())[:8],
            agent_id=agent_id,
            memory_id_a=memory_id_a,
            memory_id_b=memory_id_b,
            description=description,
            detected_at=datetime.now(),
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO dissonance_queue
                (id, agent_id, memory_id_a, memory_id_b, description, detected_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dissonance.id,
                    dissonance.agent_id,
                    dissonance.memory_id_a,
                    dissonance.memory_id_b,
                    dissonance.description,
                    dissonance.detected_at.isoformat(),
                    dissonance.status.value,
                ),
            )
            conn.commit()

        return dissonance

    def get_open_dissonances(self, agent_id: str) -> list[Dissonance]:
        """Get all open dissonances for an agent."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM dissonance_queue WHERE agent_id = ? AND status = ?",
                (agent_id, DissonanceStatus.OPEN.value),
            ).fetchall()

        return [self._row_to_dissonance(row) for row in rows]

    def get_dissonance(self, dissonance_id: str) -> Optional[Dissonance]:
        """Get a specific dissonance by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM dissonance_queue WHERE id = ?",
                (dissonance_id,),
            ).fetchone()

        if row:
            return self._row_to_dissonance(row)
        return None

    def resolve_dissonance(
        self,
        dissonance_id: str,
        resolution: str,
    ) -> None:
        """Mark a dissonance as resolved."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE dissonance_queue
                SET status = ?, resolution = ?, resolved_at = ?
                WHERE id = ?
                """,
                (
                    DissonanceStatus.RESOLVED.value,
                    resolution,
                    datetime.now().isoformat(),
                    dissonance_id,
                ),
            )
            conn.commit()

    def dismiss_dissonance(self, dissonance_id: str) -> None:
        """Mark a dissonance as dismissed (not actually a contradiction)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE dissonance_queue
                SET status = ?, resolved_at = ?
                WHERE id = ?
                """,
                (
                    DissonanceStatus.DISMISSED.value,
                    datetime.now().isoformat(),
                    dissonance_id,
                ),
            )
            conn.commit()

    def count_open(self, agent_id: str) -> int:
        """Count open dissonances for an agent."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM dissonance_queue WHERE agent_id = ? AND status = ?",
                (agent_id, DissonanceStatus.OPEN.value),
            ).fetchone()
            return row[0] if row else 0

    def exists(self, memory_id_a: str, memory_id_b: str) -> bool:
        """Check if a dissonance already exists for this memory pair."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM dissonance_queue
                WHERE (memory_id_a = ? AND memory_id_b = ?)
                   OR (memory_id_a = ? AND memory_id_b = ?)
                """,
                (memory_id_a, memory_id_b, memory_id_b, memory_id_a),
            ).fetchone()
            return row[0] > 0 if row else False

    def _row_to_dissonance(self, row: sqlite3.Row) -> Dissonance:
        """Convert database row to Dissonance object."""
        return Dissonance(
            id=row["id"],
            agent_id=row["agent_id"],
            memory_id_a=row["memory_id_a"],
            memory_id_b=row["memory_id_b"],
            description=row["description"],
            detected_at=datetime.fromisoformat(row["detected_at"]),
            resolved_at=(datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None),
            resolution=row["resolution"],
            status=DissonanceStatus(row["status"]),
        )
