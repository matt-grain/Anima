# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Shared SQLite connection helper for all Anima stores.

One canonical context manager so every store opens connections identically:
a 5s busy timeout, `sqlite3.Row` rows, commit-on-success / rollback-on-error,
and a guaranteed close (the bare `with sqlite3.connect(...)` idiom commits but
never closes the connection).
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(db_path: Path | str, timeout: float = 5.0) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection with Anima's standard settings."""
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
