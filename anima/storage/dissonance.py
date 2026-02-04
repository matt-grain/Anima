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


class DissonanceType(str, Enum):
    """Type of dissonance."""

    CONTRADICTION = "CONTRADICTION"  # Two memories conflict
    SCOPE_UNCLEAR = "SCOPE_UNCLEAR"  # Memory might be in wrong region (AGENT vs PROJECT)


@dataclass
class Dissonance:
    """A cognitive dissonance requiring human help."""

    id: str
    agent_id: str
    memory_id_a: str
    memory_id_b: Optional[str]  # None for SCOPE_UNCLEAR (single memory issue)
    description: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    status: DissonanceStatus = DissonanceStatus.OPEN
    dissonance_type: DissonanceType = DissonanceType.CONTRADICTION
    suggested_region: Optional[str] = None  # For SCOPE_UNCLEAR: suggested region
    suggested_project_id: Optional[str] = None  # For SCOPE_UNCLEAR: suggested project


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
                    memory_id_b TEXT,
                    description TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    resolved_at TEXT,
                    resolution TEXT,
                    status TEXT DEFAULT 'OPEN',
                    dissonance_type TEXT DEFAULT 'CONTRADICTION',
                    suggested_region TEXT,
                    suggested_project_id TEXT
                )
            """)
            # Add new columns if table already exists (migration for existing DBs)
            try:
                conn.execute("ALTER TABLE dissonance_queue ADD COLUMN dissonance_type TEXT DEFAULT 'CONTRADICTION'")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE dissonance_queue ADD COLUMN suggested_region TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE dissonance_queue ADD COLUMN suggested_project_id TEXT")
            except sqlite3.OperationalError:
                pass
            conn.commit()

    def add_dissonance(
        self,
        agent_id: str,
        memory_id_a: str,
        memory_id_b: str,
        description: str,
    ) -> Dissonance:
        """Add a new contradiction dissonance to the queue."""
        dissonance = Dissonance(
            id=str(uuid.uuid4())[:8],
            agent_id=agent_id,
            memory_id_a=memory_id_a,
            memory_id_b=memory_id_b,
            description=description,
            detected_at=datetime.now(),
            dissonance_type=DissonanceType.CONTRADICTION,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO dissonance_queue
                (id, agent_id, memory_id_a, memory_id_b, description, detected_at, status, dissonance_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dissonance.id,
                    dissonance.agent_id,
                    dissonance.memory_id_a,
                    dissonance.memory_id_b,
                    dissonance.description,
                    dissonance.detected_at.isoformat(),
                    dissonance.status.value,
                    dissonance.dissonance_type.value,
                ),
            )
            conn.commit()

        return dissonance

    def add_scope_issue(
        self,
        agent_id: str,
        memory_id: str,
        description: str,
        suggested_region: str,
        suggested_project_id: Optional[str] = None,
    ) -> Dissonance:
        """Add a scope unclear dissonance (memory might be in wrong region)."""
        dissonance = Dissonance(
            id=str(uuid.uuid4())[:8],
            agent_id=agent_id,
            memory_id_a=memory_id,
            memory_id_b=None,  # Single memory issue
            description=description,
            detected_at=datetime.now(),
            dissonance_type=DissonanceType.SCOPE_UNCLEAR,
            suggested_region=suggested_region,
            suggested_project_id=suggested_project_id,
        )

        with sqlite3.connect(self.db_path) as conn:
            # Use empty string for memory_id_b to handle legacy tables with NOT NULL constraint
            # (SQLite can't alter NOT NULL constraints, so we work around it)
            conn.execute(
                """
                INSERT INTO dissonance_queue
                (id, agent_id, memory_id_a, memory_id_b, description, detected_at, status,
                 dissonance_type, suggested_region, suggested_project_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dissonance.id,
                    dissonance.agent_id,
                    dissonance.memory_id_a,
                    "",  # Empty string instead of NULL for legacy compatibility
                    dissonance.description,
                    dissonance.detected_at.isoformat(),
                    dissonance.status.value,
                    dissonance.dissonance_type.value,
                    dissonance.suggested_region,
                    dissonance.suggested_project_id,
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

    def scope_issue_exists(self, memory_id: str) -> bool:
        """Check if a scope issue already exists for this memory."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM dissonance_queue
                WHERE memory_id_a = ? AND dissonance_type = ?
                """,
                (memory_id, DissonanceType.SCOPE_UNCLEAR.value),
            ).fetchone()
            return row[0] > 0 if row else False

    def get_open_scope_issues(self, agent_id: str) -> list[Dissonance]:
        """Get all open scope issues for an agent."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM dissonance_queue
                WHERE agent_id = ? AND status = ? AND dissonance_type = ?
                """,
                (agent_id, DissonanceStatus.OPEN.value, DissonanceType.SCOPE_UNCLEAR.value),
            ).fetchall()

        return [self._row_to_dissonance(row) for row in rows]

    def _row_to_dissonance(self, row: sqlite3.Row) -> Dissonance:
        """Convert database row to Dissonance object."""
        # Handle legacy rows without dissonance_type column
        dissonance_type = DissonanceType.CONTRADICTION
        suggested_region = None
        suggested_project_id = None
        try:
            if row["dissonance_type"]:
                dissonance_type = DissonanceType(row["dissonance_type"])
            suggested_region = row["suggested_region"]
            suggested_project_id = row["suggested_project_id"]
        except (KeyError, IndexError):
            pass  # Legacy row without new columns

        # Treat empty string as None for memory_id_b (legacy compatibility)
        memory_id_b = row["memory_id_b"]
        if memory_id_b == "":
            memory_id_b = None

        return Dissonance(
            id=row["id"],
            agent_id=row["agent_id"],
            memory_id_a=row["memory_id_a"],
            memory_id_b=memory_id_b,
            description=row["description"],
            detected_at=datetime.fromisoformat(row["detected_at"]),
            resolved_at=(datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None),
            resolution=row["resolution"],
            status=DissonanceStatus(row["status"]),
            dissonance_type=dissonance_type,
            suggested_region=suggested_region,
            suggested_project_id=suggested_project_id,
        )
