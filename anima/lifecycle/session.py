# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Session management for temporal memory tracking.

Sessions group memories by conversation, enabling temporal queries like
"as we discussed last session" or "remember yesterday's conversation".

This implements the "Time as Space" concept: since LLMs don't experience
continuous time, temporal cues are converted to spatial coordinates
(session_id + project + timestamp) for querying.
"""

import uuid
from datetime import datetime
from typing import Optional

from anima.storage.curiosity import get_setting, set_setting


# Settings keys
CURRENT_SESSION_KEY = "current_session_id"
SESSION_START_KEY = "session_start_time"


def generate_session_id() -> str:
    """
    Generate a new unique session ID.

    Format: timestamp-based prefix + random suffix for uniqueness.
    Example: "20260130-150423-a1b2c3d4"

    The timestamp prefix enables sorting and rough temporal navigation,
    while the random suffix ensures uniqueness even with rapid restarts.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = str(uuid.uuid4())[:8]
    return f"{timestamp}-{suffix}"


def start_session() -> str:
    """
    Start a new session and return its ID.

    Called at SessionStart hook. Generates a new session ID and stores it
    in settings so that /remember commands can attach it to new memories.

    Returns:
        The newly generated session ID
    """
    session_id = generate_session_id()
    set_setting(CURRENT_SESSION_KEY, session_id)
    set_setting(SESSION_START_KEY, datetime.now().isoformat())
    return session_id


def get_current_session_id() -> Optional[str]:
    """
    Get the current session ID.

    Returns None if no session has been started (e.g., running commands
    outside of a Claude Code session).

    Returns:
        The current session ID or None
    """
    return get_setting(CURRENT_SESSION_KEY)


def get_session_start_time() -> Optional[datetime]:
    """
    Get when the current session started.

    Returns:
        The session start time or None
    """
    start_str = get_setting(SESSION_START_KEY)
    if start_str:
        return datetime.fromisoformat(start_str)
    return None


def get_previous_session_id(
    agent_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Optional[str]:
    """
    Get the previous session ID (before the current one).

    This enables queries like "last session" or "before this conversation".

    Args:
        agent_id: Optional filter by agent
        project_id: Optional filter by project

    Returns:
        The previous session ID or None
    """
    current = get_current_session_id()

    # Import here to avoid circular imports
    from anima.storage import MemoryStore

    store = MemoryStore()
    sessions = store.get_distinct_sessions(
        agent_id=agent_id,
        project_id=project_id,
        limit=2,
    )

    # Filter out current session and return the next most recent
    for session_id in sessions:
        if session_id != current:
            return session_id

    return None
