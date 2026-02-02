# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Temporal Cue Parser - "Time as Space" implementation.

LLMs don't experience continuous time like humans. Each session is discrete,
like waking up with amnesia. This module translates temporal language into
spatial coordinates that can be queried:

- "yesterday" → timestamps within date range
- "last session" → specific session_id
- "during the last commit" → git_commit hash
- "last week" → timestamp range

The key insight: temporal cues become spatial filters (session + project +
timestamp + git) that locate memories in the "space" where they were created.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from anima.lifecycle.session import get_current_session_id, get_previous_session_id
from anima.utils.git import get_git_context, get_recent_commits


class TemporalCueType(Enum):
    """Types of temporal cues we can detect."""

    SESSION = auto()  # "last session", "this session"
    RELATIVE_TIME = auto()  # "yesterday", "last week", "recently"
    GIT_EVENT = auto()  # "during the last commit", "on branch X"
    EXPLICIT_TIME = auto()  # "on January 15th" (future enhancement)


@dataclass
class TemporalCoordinate:
    """
    Spatial coordinates derived from temporal cues.

    These are the filters used to locate memories in "space" rather than "time".
    """

    cue_type: TemporalCueType
    original_text: str

    # Session coordinates
    session_id: Optional[str] = None
    is_current_session: bool = False

    # Time range coordinates (UTC timestamps)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Git coordinates
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None

    def has_filters(self) -> bool:
        """Check if any filters are set."""
        return any(
            [
                self.session_id,
                self.start_time,
                self.end_time,
                self.git_commit,
                self.git_branch,
            ]
        )


# Pattern matchers for temporal cues
TEMPORAL_PATTERNS = {
    # Session patterns
    r"(?:as we|when we|what we)?\s*(?:discussed|mentioned|talked about|noted|worked on)\s*(?:last|previous)\s*session": "LAST_SESSION",
    r"(?:in\s+)?(?:the\s+)?(?:last|previous)\s+session": "LAST_SESSION",
    r"(?:during|in)\s+(?:this|our)\s+(?:current\s+)?session": "CURRENT_SESSION",
    r"earlier\s+(?:today|this session)": "CURRENT_SESSION",
    # Git event patterns
    r"(?:during|while|when|at)\s+(?:the\s+)?(?:last|previous|recent)\s+commit": "LAST_COMMIT",
    r"(?:on|for)\s+(?:this|the)\s+commit": "CURRENT_COMMIT",
    r"(?:while|when)\s+(?:working on|implementing|fixing|building)\s+(?:that|the)\s+commit": "LAST_COMMIT",
    r"(?:on|in)\s+(?:the\s+)?(?:branch|feature)\s+['\"]?(\S+)['\"]?": "GIT_BRANCH",
    r"(?:on|in)\s+main(?:\s+branch)?": "GIT_MAIN",
    r"(?:on|in)\s+master(?:\s+branch)?": "GIT_MASTER",
    # Relative time patterns
    r"yesterday": "YESTERDAY",
    r"last\s+week": "LAST_WEEK",
    r"this\s+week": "THIS_WEEK",
    r"recently": "RECENT",
    r"a\s+few\s+days\s+ago": "FEW_DAYS_AGO",
    r"last\s+month": "LAST_MONTH",
    r"earlier": "EARLIER_TODAY",
}


def parse_temporal_cue(
    text: str,
    now: Optional[datetime] = None,
    cwd: Optional[Path] = None,
) -> Optional[TemporalCoordinate]:
    """
    Parse text for temporal cues and convert to spatial coordinates.

    This is the core "Time as Space" translation: human time language
    becomes queryable spatial coordinates.

    Args:
        text: User message or query text
        now: Current time (defaults to now)
        cwd: Working directory for git context

    Returns:
        TemporalCoordinate with filters set, or None if no cues found
    """
    if now is None:
        now = datetime.now()

    text_lower = text.lower()

    for pattern, cue_name in TEMPORAL_PATTERNS.items():
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return _resolve_cue(cue_name, match, now, cwd, text)

    return None


def _resolve_cue(
    cue_name: str,
    match: re.Match,
    now: datetime,
    cwd: Optional[Path],
    original_text: str,
) -> TemporalCoordinate:
    """Resolve a matched cue name to spatial coordinates."""

    # Session-based cues
    if cue_name == "LAST_SESSION":
        prev_session = get_previous_session_id()
        return TemporalCoordinate(
            cue_type=TemporalCueType.SESSION,
            original_text=match.group(0),
            session_id=prev_session,
        )

    if cue_name == "CURRENT_SESSION":
        current_session = get_current_session_id()
        return TemporalCoordinate(
            cue_type=TemporalCueType.SESSION,
            original_text=match.group(0),
            session_id=current_session,
            is_current_session=True,
        )

    # Git event cues
    if cue_name == "LAST_COMMIT":
        commits = get_recent_commits(count=2, cwd=cwd)
        # Get the previous commit (not HEAD)
        commit = commits[1]["hash"] if len(commits) > 1 else (commits[0]["hash"] if commits else None)
        return TemporalCoordinate(
            cue_type=TemporalCueType.GIT_EVENT,
            original_text=match.group(0),
            git_commit=commit,
        )

    if cue_name == "CURRENT_COMMIT":
        ctx = get_git_context(cwd)
        return TemporalCoordinate(
            cue_type=TemporalCueType.GIT_EVENT,
            original_text=match.group(0),
            git_commit=ctx.commit,
        )

    if cue_name == "GIT_BRANCH":
        branch = match.group(1) if match.lastindex else None
        return TemporalCoordinate(
            cue_type=TemporalCueType.GIT_EVENT,
            original_text=match.group(0),
            git_branch=branch,
        )

    if cue_name == "GIT_MAIN":
        return TemporalCoordinate(
            cue_type=TemporalCueType.GIT_EVENT,
            original_text=match.group(0),
            git_branch="main",
        )

    if cue_name == "GIT_MASTER":
        return TemporalCoordinate(
            cue_type=TemporalCueType.GIT_EVENT,
            original_text=match.group(0),
            git_branch="master",
        )

    # Relative time cues
    if cue_name == "YESTERDAY":
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return TemporalCoordinate(
            cue_type=TemporalCueType.RELATIVE_TIME,
            original_text=match.group(0),
            start_time=start,
            end_time=end,
        )

    if cue_name == "LAST_WEEK":
        start = now - timedelta(days=7)
        return TemporalCoordinate(
            cue_type=TemporalCueType.RELATIVE_TIME,
            original_text=match.group(0),
            start_time=start,
            end_time=now,
        )

    if cue_name == "THIS_WEEK":
        # Start of week (Monday)
        days_since_monday = now.weekday()
        start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        return TemporalCoordinate(
            cue_type=TemporalCueType.RELATIVE_TIME,
            original_text=match.group(0),
            start_time=start,
            end_time=now,
        )

    if cue_name == "RECENT":
        # "Recently" = last 48 hours
        start = now - timedelta(hours=48)
        return TemporalCoordinate(
            cue_type=TemporalCueType.RELATIVE_TIME,
            original_text=match.group(0),
            start_time=start,
            end_time=now,
        )

    if cue_name == "FEW_DAYS_AGO":
        start = now - timedelta(days=5)
        end = now - timedelta(days=1)
        return TemporalCoordinate(
            cue_type=TemporalCueType.RELATIVE_TIME,
            original_text=match.group(0),
            start_time=start,
            end_time=end,
        )

    if cue_name == "LAST_MONTH":
        start = now - timedelta(days=30)
        return TemporalCoordinate(
            cue_type=TemporalCueType.RELATIVE_TIME,
            original_text=match.group(0),
            start_time=start,
            end_time=now,
        )

    if cue_name == "EARLIER_TODAY":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return TemporalCoordinate(
            cue_type=TemporalCueType.RELATIVE_TIME,
            original_text=match.group(0),
            start_time=start,
            end_time=now,
        )

    # Fallback - shouldn't reach here
    return TemporalCoordinate(
        cue_type=TemporalCueType.RELATIVE_TIME,
        original_text=match.group(0),
    )


def find_all_temporal_cues(
    text: str,
    now: Optional[datetime] = None,
    cwd: Optional[Path] = None,
) -> list[TemporalCoordinate]:
    """
    Find all temporal cues in a text.

    Useful when multiple temporal references exist in a single message.

    Args:
        text: User message or query text
        now: Current time (defaults to now)
        cwd: Working directory for git context

    Returns:
        List of all found temporal coordinates
    """
    if now is None:
        now = datetime.now()

    coordinates = []
    text_lower = text.lower()

    for pattern, cue_name in TEMPORAL_PATTERNS.items():
        for match in re.finditer(pattern, text_lower, re.IGNORECASE):
            coord = _resolve_cue(cue_name, match, now, cwd, text)
            coordinates.append(coord)

    return coordinates
