# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""SQLite storage layer for LTM."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Iterator

from anima.core import (
    Memory,
    Agent,
    Project,
    RegionType,
    MemoryKind,
    ImpactLevel,
    MemoryLimits,
    MemoryLimitExceeded,
    DEFAULT_LIMITS,
)
from anima.storage.protocol import MemoryStoreProtocol
from anima.storage.migrations import run_migrations, SCHEMA_VERSION, set_schema_version


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
    return pattern.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class MemoryStore(MemoryStoreProtocol):
    """
    SQLite-based persistent storage for LTM memories.

    Implements the MemoryStoreProtocol interface.
    Handles all CRUD operations for memories, agents, and projects.
    """

    def __init__(
        self, db_path: Optional[Path] = None, limits: Optional[MemoryLimits] = None
    ):
        self.db_path = db_path or get_default_db_path()
        self.limits = limits if limits is not None else DEFAULT_LIMITS
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with schema, running migrations if needed."""
        # Run migrations on existing databases
        old_ver, new_ver, backup = run_migrations(self.db_path)
        if backup:
            print(
                f"  Migrated database from v{old_ver} to v{new_ver} (backup: {backup.name})"
            )

        # Apply schema (CREATE IF NOT EXISTS is safe for existing tables)
        schema_path = Path(__file__).parent / "schema.sql"
        schema = schema_path.read_text()

        with self._connect() as conn:
            conn.executescript(schema)
            # Set version for fresh databases
            set_schema_version(conn, SCHEMA_VERSION)

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
                    agent.created_at or datetime.now().isoformat(),
                ),
            )

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM agents WHERE id = ?", (agent_id,)
            ).fetchone()

            if not row:
                return None

            return Agent(
                id=row["id"],
                name=row["name"],
                definition_path=Path(row["definition_path"])
                if row["definition_path"]
                else None,
                signing_key=row["signing_key"],
                created_at=row["created_at"],
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
                (str(project.path), project.id),
            ).fetchone()

            if existing:
                # Update the existing project (keep its original id)
                conn.execute(
                    "UPDATE projects SET name = ? WHERE path = ?",
                    (project.name, str(project.path)),
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
                        project.created_at or datetime.now().isoformat(),
                    ),
                )

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()

            if not row:
                return None

            return Project(
                id=row["id"],
                name=row["name"],
                path=Path(row["path"]),
                created_at=row["created_at"],
            )

    def get_project_by_path(self, path: Path) -> Optional[Project]:
        """Get a project by its path."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE path = ?", (str(path),)
            ).fetchone()

            if not row:
                return None

            return Project(
                id=row["id"],
                name=row["name"],
                path=Path(row["path"]),
                created_at=row["created_at"],
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
                    "agent total", current, self.limits.max_memories_per_agent
                )

        # Check per-project limit
        if self.limits.max_memories_per_project is not None and memory.project_id:
            current = self.count_memories(memory.agent_id, memory.project_id)
            if current >= self.limits.max_memories_per_project:
                raise MemoryLimitExceeded(
                    f"project '{memory.project_id}'",
                    current,
                    self.limits.max_memories_per_project,
                )

        # Check per-kind limit
        if self.limits.max_memories_per_kind is not None:
            current = self.count_memories_by_kind(
                memory.agent_id, memory.kind, memory.project_id
            )
            if current >= self.limits.max_memories_per_kind:
                raise MemoryLimitExceeded(
                    f"kind '{memory.kind.value}'",
                    current,
                    self.limits.max_memories_per_kind,
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
                    version, superseded_by, signature, token_count, platform,
                    session_id, git_commit, git_branch
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    confidence = excluded.confidence,
                    last_accessed = excluded.last_accessed,
                    version = excluded.version,
                    superseded_by = excluded.superseded_by,
                    signature = excluded.signature,
                    token_count = excluded.token_count,
                    platform = excluded.platform,
                    session_id = excluded.session_id,
                    git_commit = excluded.git_commit,
                    git_branch = excluded.git_branch
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
                    memory.token_count,
                    memory.platform,
                    memory.session_id,
                    memory.git_commit,
                    memory.git_branch,
                ),
            )

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a memory by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
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
        limit: Optional[int] = None,
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
        project_id: Optional[str] = None,
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
                (new_memory_id, old_memory_id),
            )

    def update_confidence(self, memory_id: str, confidence: float) -> None:
        """Update the confidence score of a memory."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE memories SET confidence = ? WHERE id = ?",
                (confidence, memory_id),
            )

    def delete_memory(self, memory_id: str) -> None:
        """Delete a memory (use sparingly - prefer superseding)."""
        with self._connect() as conn:
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

    # --- Session-based queries (Phase 3: Temporal Infrastructure) ---

    def get_memories_by_session(
        self,
        session_id: str,
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> list[Memory]:
        """
        Get all memories from a specific session.

        This enables temporal queries like "what did we discuss last session?"

        Args:
            session_id: The session ID to query
            agent_id: Optional filter by agent
            project_id: Optional filter by project

        Returns:
            List of memories from that session, ordered by creation time
        """
        query = "SELECT * FROM memories WHERE session_id = ?"
        params: list = [session_id]

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        query += " ORDER BY created_at ASC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_memory(row) for row in rows]

    def get_distinct_sessions(
        self,
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[str]:
        """
        Get the most recent distinct session IDs.

        Useful for queries like "last N sessions" or finding the previous session.

        Args:
            agent_id: Optional filter by agent
            project_id: Optional filter by project
            limit: Maximum number of sessions to return

        Returns:
            List of session IDs, most recent first
        """
        query = """
            SELECT DISTINCT session_id FROM memories
            WHERE session_id IS NOT NULL
        """
        params: list = []

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [row[0] for row in rows]

    def get_memories_by_git_commit(
        self,
        commit: str,
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> list[Memory]:
        """
        Get all memories associated with a specific git commit.

        This enables temporal queries like "what did we discuss during that commit?"
        Matches partial commit hashes (prefix matching).

        Args:
            commit: Full or partial commit hash
            agent_id: Optional filter by agent
            project_id: Optional filter by project

        Returns:
            List of memories from that commit, ordered by creation time
        """
        # Use LIKE for prefix matching (e.g., "abc123" matches "abc123def...")
        query = "SELECT * FROM memories WHERE git_commit LIKE ?"
        params: list = [f"{commit}%"]

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        query += " ORDER BY created_at ASC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_memory(row) for row in rows]

    def get_memories_by_git_branch(
        self,
        branch: str,
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[Memory]:
        """
        Get memories created on a specific git branch.

        This enables queries like "what did we work on in the feature branch?"

        Args:
            branch: Branch name (exact match)
            agent_id: Optional filter by agent
            project_id: Optional filter by project
            limit: Maximum number of memories to return

        Returns:
            List of memories from that branch, most recent first
        """
        query = "SELECT * FROM memories WHERE git_branch = ?"
        params: list = [branch]

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_memory(row) for row in rows]

    def search_memories(
        self,
        agent_id: str,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 10,
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
        query = (
            "SELECT COUNT(*) FROM memories WHERE agent_id = ? AND superseded_by IS NULL"
        )
        params: list = [agent_id]

        if project_id:
            query += " AND (project_id = ? OR region = 'AGENT')"
            params.append(project_id)

        with self._connect() as conn:
            return conn.execute(query, params).fetchone()[0]

    def count_memories_by_kind(
        self, agent_id: str, kind: MemoryKind, project_id: Optional[str] = None
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
            token_count=row["token_count"],
            platform=row["platform"] if "platform" in row.keys() else None,
            session_id=row["session_id"] if "session_id" in row.keys() else None,
            git_commit=row["git_commit"] if "git_commit" in row.keys() else None,
            git_branch=row["git_branch"] if "git_branch" in row.keys() else None,
        )

    # --- Embedding operations ---

    def save_embedding(self, memory_id: str, embedding: list[float]) -> None:
        """Save an embedding for a memory."""
        embedding_json = json.dumps(embedding)
        with self._connect() as conn:
            conn.execute(
                "UPDATE memories SET embedding = ? WHERE id = ?",
                (embedding_json, memory_id),
            )

    def get_embedding(self, memory_id: str) -> Optional[list[float]]:
        """Get the embedding for a memory."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT embedding FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            if not row or not row["embedding"]:
                return None
            return json.loads(row["embedding"])

    def get_memories_with_embeddings(
        self,
        agent_id: str,
        project_id: Optional[str] = None,
        include_superseded: bool = False,
    ) -> list[tuple[str, str, list[float]]]:
        """
        Get all memories with their embeddings for semantic search.

        Returns:
            List of (memory_id, content, embedding) tuples
        """
        query = """
            SELECT id, content, embedding FROM memories
            WHERE agent_id = ? AND embedding IS NOT NULL
        """
        params: list = [agent_id]

        if project_id:
            query += " AND (project_id = ? OR region = 'AGENT')"
            params.append(project_id)

        if not include_superseded:
            query += " AND superseded_by IS NULL"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                (row["id"], row["content"], json.loads(row["embedding"]))
                for row in rows
            ]

    def get_memories_with_temporal_context(
        self,
        agent_id: str,
        project_id: Optional[str] = None,
        include_superseded: bool = False,
    ) -> list[tuple[str, str, list[float], datetime, Optional[str]]]:
        """
        Get memories with embeddings and temporal context for BUILDS_ON detection.

        Returns:
            List of (memory_id, content, embedding, created_at, session_id) tuples
        """
        query = """
            SELECT id, content, embedding, created_at, session_id FROM memories
            WHERE agent_id = ? AND embedding IS NOT NULL
        """
        params: list = [agent_id]

        if project_id:
            query += " AND (project_id = ? OR region = 'AGENT')"
            params.append(project_id)

        if not include_superseded:
            query += " AND superseded_by IS NULL"

        query += " ORDER BY created_at DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            result = []
            for row in rows:
                embedding = json.loads(row["embedding"]) if row["embedding"] else None
                created_at = datetime.fromisoformat(row["created_at"])
                session_id = row["session_id"] if "session_id" in row.keys() else None
                result.append((
                    row["id"],
                    row["content"],
                    embedding,
                    created_at,
                    session_id,
                ))
            return result

    def get_memories_without_embeddings(
        self,
        agent_id: str,
        limit: Optional[int] = None,
    ) -> list[tuple[str, str]]:
        """
        Get memories that don't have embeddings yet.

        Returns:
            List of (memory_id, content) tuples
        """
        query = """
            SELECT id, content FROM memories
            WHERE agent_id = ? AND embedding IS NULL AND superseded_by IS NULL
        """
        params: list = [agent_id]

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [(row["id"], row["content"]) for row in rows]

    # --- Tier operations ---

    def update_tier(self, memory_id: str, tier: str) -> None:
        """Update the tier for a memory."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE memories SET tier = ? WHERE id = ?",
                (tier, memory_id),
            )

    def get_memories_by_tier(
        self,
        agent_id: str,
        tiers: list[str],
        project_id: Optional[str] = None,
    ) -> list[Memory]:
        """Get memories by tier(s)."""
        if not tiers:
            return []

        placeholders = ",".join("?" * len(tiers))
        query = f"""
            SELECT * FROM memories
            WHERE agent_id = ? AND tier IN ({placeholders})
            AND superseded_by IS NULL
        """
        params: list = [agent_id, *tiers]

        if project_id:
            query += " AND (project_id = ? OR region = 'AGENT')"
            params.append(project_id)

        query += " ORDER BY created_at DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_memory(row) for row in rows]

    # --- Link operations ---

    def save_link(
        self,
        source_id: str,
        target_id: str,
        link_type: str,
        similarity: Optional[float] = None,
    ) -> None:
        """Save a link between two memories."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memory_links (source_id, target_id, link_type, similarity, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id) DO UPDATE SET
                    link_type = excluded.link_type,
                    similarity = excluded.similarity
                """,
                (source_id, target_id, link_type, similarity, datetime.now().isoformat()),
            )

    def get_links_for_memory(self, memory_id: str) -> list[tuple[str, str, str, Optional[float]]]:
        """
        Get all links for a memory (both as source and target).

        Returns:
            List of (source_id, target_id, link_type, similarity) tuples
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT source_id, target_id, link_type, similarity
                FROM memory_links
                WHERE source_id = ? OR target_id = ?
                """,
                (memory_id, memory_id),
            ).fetchall()
            return [
                (row["source_id"], row["target_id"], row["link_type"], row["similarity"])
                for row in rows
            ]

    def get_linked_memory_ids(
        self,
        memory_id: str,
        link_type: Optional[str] = None,
    ) -> list[str]:
        """Get IDs of memories linked to a given memory."""
        query = """
            SELECT CASE
                WHEN source_id = ? THEN target_id
                ELSE source_id
            END as linked_id
            FROM memory_links
            WHERE source_id = ? OR target_id = ?
        """
        params: list = [memory_id, memory_id, memory_id]

        if link_type:
            query += " AND link_type = ?"
            params.append(link_type)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [row["linked_id"] for row in rows]

    def delete_links_for_memory(self, memory_id: str) -> None:
        """Delete all links for a memory."""
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM memory_links WHERE source_id = ? OR target_id = ?",
                (memory_id, memory_id),
            )
