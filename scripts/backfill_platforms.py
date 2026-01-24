#!/usr/bin/env python3
"""
One-time migration script to backfill platform data for existing memories.

Based on Matt's memory creation history:
- Before 2026-01-17: Created on Claude
- 2026-01-17 to 2026-01-23: Created on Antigravity
- 2026-01-24 onwards: Will be set via --platform flag

Run with: uv run python scripts/backfill_platforms.py
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def get_db_path() -> Path:
    """Get the default database path."""
    anima_dir = Path.home() / ".anima"
    return anima_dir / "memories.db"


def backfill_platforms(db_path: Path | None = None) -> None:
    """Backfill platform data for existing memories."""
    db_path = db_path or get_db_path()

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row

    # Check if platform column exists
    cursor = conn.execute("PRAGMA table_info(memories)")
    columns = [row["name"] for row in cursor.fetchall()]

    if "platform" not in columns:
        print("Platform column not found. Please run migrations first.")
        print("Start a new session or run: uv run anima load-context")
        conn.close()
        return

    # Count existing memories without platform
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM memories WHERE platform IS NULL")
    count = cursor.fetchone()["cnt"]
    print(f"Found {count} memories without platform data")

    if count == 0:
        print("All memories already have platform data. Nothing to do!")
        conn.close()
        return

    # Define date boundaries
    antigravity_start = datetime(2026, 1, 17)
    today = datetime(2026, 1, 24)

    # Update memories before 2026-01-17 to claude
    cursor = conn.execute(
        """
        UPDATE memories
        SET platform = 'claude'
        WHERE platform IS NULL
          AND created_at < ?
        """,
        (antigravity_start.isoformat(),),
    )
    claude_count = cursor.rowcount
    print(f"Set {claude_count} memories to platform='claude' (before {antigravity_start.date()})")

    # Update memories from 2026-01-17 to 2026-01-23 to antigravity
    cursor = conn.execute(
        """
        UPDATE memories
        SET platform = 'antigravity'
        WHERE platform IS NULL
          AND created_at >= ?
          AND created_at < ?
        """,
        (antigravity_start.isoformat(), today.isoformat()),
    )
    antigravity_count = cursor.rowcount
    print(f"Set {antigravity_count} memories to platform='antigravity' ({antigravity_start.date()} to {(today - timedelta(days=1)).date()})")

    # Today's memories stay NULL for now (will be set via --platform flag)
    cursor = conn.execute(
        """
        SELECT COUNT(*) as cnt FROM memories
        WHERE platform IS NULL AND created_at >= ?
        """,
        (today.isoformat(),),
    )
    today_count = cursor.fetchone()["cnt"]
    if today_count > 0:
        print(f"Left {today_count} memories from today without platform (use --platform flag)")

    conn.commit()
    conn.close()

    print("\nDone! Platform backfill complete.")


if __name__ == "__main__":
    backfill_platforms()
