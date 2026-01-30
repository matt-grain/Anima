# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Database migration system for LTM.

SQLite doesn't support altering CHECK constraints, so we need to
recreate tables when adding new enum values like INTROSPECT.
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


# Current schema version - increment when schema changes
SCHEMA_VERSION = 4

# Migration history:
# v1: Original schema (EMOTIONAL, ARCHITECTURAL, LEARNINGS, ACHIEVEMENTS)
# v2: Added INTROSPECT kind + platform column for spaceship tracking
# v3: Added curiosity_queue table + settings table for autonomous research
# v4: Semantic Memory Layer - embeddings, tiers, memory_links graph


def get_schema_version(db_path: Path) -> int:
    """Get current schema version from database, or 0 if not set."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.execute("PRAGMA user_version")
        version = cursor.fetchone()[0]
        conn.close()
        return version
    except Exception:
        return 0


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    """Set schema version in database."""
    conn.execute(f"PRAGMA user_version = {version}")


def backup_database(db_path: Path) -> Path:
    """Create a timestamped backup of the database in ~/.anima/backups/."""
    backup_dir = Path.home() / ".anima" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{db_path.stem}_backup_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    return backup_path


def migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    """
    Migrate from v1 to v2: Add INTROSPECT to memory kinds.

    SQLite doesn't support ALTER TABLE for CHECK constraints,
    so we recreate the memories table with the updated constraint.
    """
    # Create new table with updated CHECK constraint and platform column
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories_new (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            region TEXT NOT NULL CHECK (region IN ('AGENT', 'PROJECT')),
            project_id TEXT,
            kind TEXT NOT NULL CHECK (kind IN ('EMOTIONAL', 'ARCHITECTURAL', 'LEARNINGS', 'ACHIEVEMENTS', 'INTROSPECT')),
            content TEXT NOT NULL,
            original_content TEXT NOT NULL,
            impact TEXT NOT NULL CHECK (impact IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
            confidence REAL DEFAULT 1.0,
            created_at TIMESTAMP NOT NULL,
            last_accessed TIMESTAMP NOT NULL,
            previous_memory_id TEXT,
            version INTEGER DEFAULT 1,
            superseded_by TEXT,
            signature TEXT,
            token_count INTEGER,
            platform TEXT,

            FOREIGN KEY (agent_id) REFERENCES agents(id),
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (previous_memory_id) REFERENCES memories(id),
            FOREIGN KEY (superseded_by) REFERENCES memories(id),
            CHECK (region = 'AGENT' OR project_id IS NOT NULL)
        )
    """)

    # Copy data from old table (adding NULL for new platform column)
    conn.execute("""
        INSERT INTO memories_new (
            id, agent_id, region, project_id, kind, content, original_content,
            impact, confidence, created_at, last_accessed, previous_memory_id,
            version, superseded_by, signature, token_count, platform
        )
        SELECT
            id, agent_id, region, project_id, kind, content, original_content,
            impact, confidence, created_at, last_accessed, previous_memory_id,
            version, superseded_by, signature, token_count, NULL
        FROM memories
    """)

    # Drop old table and indexes
    conn.execute("DROP TABLE memories")

    # Rename new table
    conn.execute("ALTER TABLE memories_new RENAME TO memories")

    # Recreate indexes
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_agent_region ON memories(agent_id, region)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_id)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_impact ON memories(impact)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_superseded ON memories(superseded_by)"
    )


def migrate_v3_to_v4(conn: sqlite3.Connection) -> None:
    """
    Migrate from v3 to v4: Semantic Memory Layer.

    Adds:
    - embedding BLOB column to memories (for FastEmbed vectors)
    - tier TEXT column to memories (CORE/ACTIVE/CONTEXTUAL/DEEP)
    - memory_links table for knowledge graph
    """
    # Add embedding column (BLOB for JSON-encoded float array)
    try:
        conn.execute("ALTER TABLE memories ADD COLUMN embedding BLOB")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Add tier column with default CONTEXTUAL
    try:
        conn.execute(
            "ALTER TABLE memories ADD COLUMN tier TEXT DEFAULT 'CONTEXTUAL'"
        )
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Create memory_links table for knowledge graph
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_links (
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            link_type TEXT NOT NULL CHECK (link_type IN ('RELATES_TO', 'BUILDS_ON', 'CONTRADICTS', 'SUPERSEDES')),
            similarity REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (source_id, target_id),
            FOREIGN KEY (source_id) REFERENCES memories(id),
            FOREIGN KEY (target_id) REFERENCES memories(id)
        )
    """)

    # Create indexes for efficient lookups
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_links_source ON memory_links(source_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_links_target ON memory_links(target_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_links_type ON memory_links(link_type)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_tier ON memories(tier)")


def migrate_v2_to_v3(conn: sqlite3.Connection) -> None:
    """
    Migrate from v2 to v3: Add curiosity_queue and settings tables.

    These are new tables, so no data migration needed.
    """
    # Create curiosity queue table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS curiosity_queue (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            region TEXT NOT NULL CHECK (region IN ('AGENT', 'PROJECT')),
            project_id TEXT,
            question TEXT NOT NULL,
            context TEXT,
            recurrence_count INTEGER DEFAULT 1,
            first_seen TIMESTAMP NOT NULL,
            last_seen TIMESTAMP NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('OPEN', 'RESEARCHED', 'DISMISSED')),
            priority_boost INTEGER DEFAULT 0,

            FOREIGN KEY (agent_id) REFERENCES agents(id),
            FOREIGN KEY (project_id) REFERENCES projects(id),
            CHECK (region = 'AGENT' OR project_id IS NOT NULL)
        )
    """)

    # Create indexes for curiosity queue
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_curiosity_agent ON curiosity_queue(agent_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_curiosity_status ON curiosity_queue(status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_curiosity_last_seen ON curiosity_queue(last_seen DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_curiosity_region ON curiosity_queue(agent_id, region)"
    )

    # Create settings table for tracking last_research, etc.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def has_memories_table(db_path: Path) -> bool:
    """Check if the memories table exists in the database."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
        )
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception:
        return False


def run_migrations(
    db_path: Path, target_version: Optional[int] = None
) -> tuple[int, int, Optional[Path]]:
    """
    Run all pending migrations.

    Returns:
        Tuple of (old_version, new_version, backup_path or None)
    """
    if not db_path.exists():
        return (0, 0, None)  # Fresh database, schema.sql will handle it

    target = target_version or SCHEMA_VERSION
    current = get_schema_version(db_path)

    # If version is 0 but no tables exist, it's a fresh database
    # Let schema.sql create everything from scratch
    if current == 0 and not has_memories_table(db_path):
        return (0, 0, None)

    if current >= target:
        return (current, current, None)  # Already up to date

    # Create backup before migrations
    backup_path = backup_database(db_path)

    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        # Run migrations in order
        if current < 2 and target >= 2:
            migrate_v1_to_v2(conn)

        if current < 3 and target >= 3:
            migrate_v2_to_v3(conn)

        if current < 4 and target >= 4:
            migrate_v3_to_v4(conn)

        set_schema_version(conn, target)
        conn.commit()

        return (current, target, backup_path)

    except Exception as e:
        # Restore from backup on failure
        shutil.copy2(backup_path, db_path)
        raise RuntimeError(f"Migration failed, restored from backup: {e}") from e
    finally:
        conn.close()
