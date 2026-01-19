# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""SQLite storage layer for LTM."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Iterator

from anima.core import (
    Memory, Agent, Project,
    RegionType, MemoryKind, ImpactLevel,
    MemoryLimits, MemoryLimitExceeded, DEFAULT_LIMITS
)
from anima.storage.protocol import MemoryStoreProtocol


def get_default_db_path() -> Path:
    """Get the default database path (~/.anima/memories.db)."""
    anima_dir = Path.home() / ".anima"
    ltm_dir = Path.home() / ".ltm"

    # Migration: if .ltm exists but .anima does not, rename it
    if ltm_dir.exists() and not anima_dir.exists():
        try:
            ltm_dir.rename(anima_dir)
            print(f"  Migration: Moved memories from {ltm_dir} to {anima_dir}")
        except Exception as e:
            # If rename fails (e.g. cross-device), fall back to keeping .ltm for now
            # but usually this is just in the home dir
            print(f"  Warning: Could not automatically migrate .ltm to .anima: {e}")
            return ltm_dir / "memories.db"

    anima_dir.mkdir(parents=True, exist_ok=True)
    return anima_dir / "memories.db"


def escape_like_pattern(pattern: str) -> str:
    """
    Escape special characters for SQL LIKE queries.

    Prevents LIKE injection where user input containing % or _ could
    manipulate search behavior.
    """
    return (
        pattern
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


class MemoryStore(MemoryStoreProtocol):
    """
    SQLite-based persistent storage for LTM memories.

    Implements the MemoryStoreProtocol interface.
    Handles all CRUD operations for memories, agents, and projects.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        limits: Optional[MemoryLimits] = None
    ):
        self.db_path = db_path or get_default_db_path()
        self.limits = limits if limits is not None else DEFAULT_LIMITS
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with schema."""
        schema_path = Path(__file__).parent / "schema.sql"
        schema = schema_path.read_text()

        with self._connect() as conn:
            conn.executescript(schema)

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

    # --- Agent operations ---

    def save_agent(self, agent: Agent) -> None:
        """Save or update an agent."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agents (id, name, definition_path, signing_key, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    definition_path = excluded.definition_path,
                    signing_key = excluded.signing_key
                """,
                (
                    agent.id,
                    agent.name,
                    str(agent.definition_path) if agent.definition_path else None,
                    agent.signing_key,
                    agent.created_at or datetime.now().isoformat()
                )
            )

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM agents WHERE id = ?",
                (agent_id,)
            ).fetchone()

            if not row:
                return None

            return Agent(
                id=row["id"],
                name=row["name"],
                definition_path=Path(row["definition_path"]) if row["definition_path"] else None,
                signing_key=row["signing_key"],
                created_at=row["created_at"]
            )

    # --- Project operations ---

    def save_project(self, project: Project) -> None:
        """
        Save or update a project.

        Handles conflicts on both id AND path (both have UNIQUE constraints).
        If a project with the same path exists but different id, we update
        that existing project rather than failing.
        """
        with self._connect() as conn:
            # Check if a project with this path already exists (with different id)
            existing = conn.execute(
                "SELECT id FROM projects WHERE path = ? AND id != ?",
                (str(project.path), project.id)
            ).fetchone()

            if existing:
                # Update the existing project (keep its original id)
                conn.execute(
                    "UPDATE projects SET name = ? WHERE path = ?",
                    (project.name, str(project.path))
                )
            else:
                # Normal upsert by id
                conn.execute(
                    """
                    INSERT INTO projects (id, name, path, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        path = excluded.path
                    """,
                    (
                        project.id,
                        project.name,
                        str(project.path),
                        project.created_at or datetime.now().isoformat()
                    )
                )

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,)
            ).fetchone()

            if not row:
                return None

            return Project(
                id=row["id"],
                name=row["name"],
                path=Path(row["path"]),
                created_at=row["created_at"]
            )

    def get_project_by_path(self, path: Path) -> Optional[Project]:
        """Get a project by its path."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE path = ?",
                (str(path),)
            ).fetchone()

            if not row:
                return None

            return Project(
                id=row["id"],
                name=row["name"],
                path=Path(row["path"]),
                created_at=row["created_at"]
            )

    # --- Memory operations ---

    def _check_limits(self, memory: Memory) -> None:
        """
        Check if saving a memory would exceed any configured limits.

        Only checks for new memories (not updates). Raises MemoryLimitExceeded
        if a limit would be exceeded.
        """
        # Check if this is a new memory (not an update)
        existing = self.get_memory(memory.id)
        if existing is not None:
            return  # Updates don't count against limits

        # Check agent-wide limit
        if self.limits.max_memories_per_agent is not None:
            current = self.count_memories(memory.agent_id)
            if current >= self.limits.max_memories_per_agent:
                raise MemoryLimitExceeded(
                    "agent total",
                    current,
                    self.limits.max_memories_per_agent
                )

        # Check per-project limit
        if self.limits.max_memories_per_project is not None and memory.project_id:
            current = self.count_memories(memory.agent_id, memory.project_id)
            if current >= self.limits.max_memories_per_project:
                raise MemoryLimitExceeded(
                    f"project '{memory.project_id}'",
                    current,
                    self.limits.max_memories_per_project
                )

        # Check per-kind limit
        if self.limits.max_memories_per_kind is not None:
            current = self.count_memories_by_kind(
                memory.agent_id,
                memory.kind,
                memory.project_id
            )
            if current >= self.limits.max_memories_per_kind:
                raise MemoryLimitExceeded(
                    f"kind '{memory.kind.value}'",
                    current,
                    self.limits.max_memories_per_kind
                )

    def save_memory(self, memory: Memory) -> None:
        """
        Save or update a memory.

        Raises:
            MemoryLimitExceeded: If saving would exceed configured limits
        """
        # Check limits before saving
        self._check_limits(memory)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (
                    id, agent_id, region, project_id, kind,
                    content, original_content, impact, confidence,
                    created_at, last_accessed, previous_memory_id,
                    version, superseded_by, signature, token_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    confidence = excluded.confidence,
                    last_accessed = excluded.last_accessed,
                    version = excluded.version,
                    superseded_by = excluded.superseded_by,
                    signature = excluded.signature,
                    token_count = excluded.token_count
                """,
                (
                    memory.id,
                    memory.agent_id,
                    memory.region.value,
                    memory.project_id,
                    memory.kind.value,
                    memory.content,
                    memory.original_content,
                    memory.impact.value,
                    memory.confidence,
                    memory.created_at.isoformat(),
                    memory.last_accessed.isoformat(),
                    memory.previous_memory_id,
                    memory.version,
                    memory.superseded_by,
                    memory.signature,
                    memory.token_count
                )
            )

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a memory by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_memory(row)

    def get_memories_for_agent(
        self,
        agent_id: str,
        region: Optional[RegionType] = None,
        project_id: Optional[str] = None,
        kind: Optional[MemoryKind] = None,
        include_superseded: bool = False,
        limit: Optional[int] = None
    ) -> list[Memory]:
        """
        Get memories for an agent with optional filters.

        Args:
            agent_id: The agent ID
            region: Filter by region (AGENT or PROJECT)
            project_id: Filter by project ID
            kind: Filter by memory kind
            include_superseded: Include superseded memories
            limit: Maximum number of memories to return

        Returns:
            List of memories, ordered by created_at DESC
        """
        query = "SELECT * FROM memories WHERE agent_id = ?"
        params: list = [agent_id]

        if region:
            query += " AND region = ?"
            params.append(region.value)

        if project_id:
            # Include both project-specific memories AND agent-wide memories
            query += " AND (project_id = ? OR region = 'AGENT')"
            params.append(project_id)

        if kind:
            query += " AND kind = ?"
            params.append(kind.value)

        if not include_superseded:
            query += " AND superseded_by IS NULL"

        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_memory(row) for row in rows]

    def get_latest_memory_of_kind(
        self,
        agent_id: str,
        kind: MemoryKind,
        region: RegionType,
        project_id: Optional[str] = None
    ) -> Optional[Memory]:
        """Get the most recent non-superseded memory of a specific kind."""
        query = """
            SELECT * FROM memories
            WHERE agent_id = ? AND kind = ? AND region = ?
            AND superseded_by IS NULL
        """
        params: list = [agent_id, kind.value, region.value]

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        query += " ORDER BY created_at DESC LIMIT 1"

        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
            if not row:
                return None
            return self._row_to_memory(row)

    def supersede_memory(self, old_memory_id: str, new_memory_id: str) -> None:
        """Mark a memory as superseded by another."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE memories SET superseded_by = ? WHERE id = ?",
                (new_memory_id, old_memory_id)
            )

    def update_confidence(self, memory_id: str, confidence: float) -> None:
        """Update the confidence score of a memory."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE memories SET confidence = ? WHERE id = ?",
                (confidence, memory_id)
            )

    def delete_memory(self, memory_id: str) -> None:
        """Delete a memory (use sparingly - prefer superseding)."""
        with self._connect() as conn:
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

    def search_memories(
        self,
        agent_id: str,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 10
    ) -> list[Memory]:
        """
        Search memories by content (simple LIKE search).

        For semantic search, Claude interprets the query externally.
        """
        # Escape LIKE special characters to prevent injection
        escaped_query = escape_like_pattern(query)

        sql = """
            SELECT * FROM memories
            WHERE agent_id = ?
            AND (content LIKE ? ESCAPE '\\' OR original_content LIKE ? ESCAPE '\\')
            AND superseded_by IS NULL
        """
        params: list = [agent_id, f"%{escaped_query}%", f"%{escaped_query}%"]

        if project_id:
            sql += " AND (project_id = ? OR region = 'AGENT')"
            params.append(project_id)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_memory(row) for row in rows]

    def count_memories(self, agent_id: str, project_id: Optional[str] = None) -> int:
        """Count non-superseded memories for an agent."""
        query = "SELECT COUNT(*) FROM memories WHERE agent_id = ? AND superseded_by IS NULL"
        params: list = [agent_id]

        if project_id:
            query += " AND (project_id = ? OR region = 'AGENT')"
            params.append(project_id)

        with self._connect() as conn:
            return conn.execute(query, params).fetchone()[0]

    def count_memories_by_kind(
        self,
        agent_id: str,
        kind: MemoryKind,
        project_id: Optional[str] = None
    ) -> int:
        """Count non-superseded memories of a specific kind for an agent."""
        query = """
            SELECT COUNT(*) FROM memories
            WHERE agent_id = ? AND kind = ? AND superseded_by IS NULL
        """
        params: list = [agent_id, kind.value]

        if project_id:
            query += " AND (project_id = ? OR region = 'AGENT')"
            params.append(project_id)

        with self._connect() as conn:
            return conn.execute(query, params).fetchone()[0]

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        """Convert a database row to a Memory object."""
        return Memory(
            id=row["id"],
            agent_id=row["agent_id"],
            region=RegionType(row["region"]),
            project_id=row["project_id"],
            kind=MemoryKind(row["kind"]),
            content=row["content"],
            original_content=row["original_content"],
            impact=ImpactLevel(row["impact"]),
            confidence=row["confidence"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"]),
            previous_memory_id=row["previous_memory_id"],
            version=row["version"],
            superseded_by=row["superseded_by"],
            signature=row["signature"],
            token_count=row["token_count"]
        )
