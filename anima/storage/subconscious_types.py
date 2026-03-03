# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Type definitions for subconscious storage."""

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
