# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Git utilities for temporal memory correlation.

These functions capture git context (commit, branch) when memories are created,
enabling temporal queries like "during the last commit" or "on branch X".
"""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class GitContext:
    """Current git context for a working directory."""

    commit: Optional[str] = None  # Current commit hash (short)
    branch: Optional[str] = None  # Current branch name
    is_dirty: bool = False  # Has uncommitted changes
    commit_time: Optional[datetime] = None  # When current commit was made


def get_git_context(cwd: Optional[Path] = None) -> GitContext:
    """
    Get current git context for the working directory.

    Returns a GitContext with available information, or empty context
    if not in a git repository or git is unavailable.

    Args:
        cwd: Working directory (defaults to current)

    Returns:
        GitContext with commit, branch, and status info
    """
    ctx = GitContext()

    try:
        # Get current commit hash (short)
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if result.returncode == 0:
            ctx.commit = result.stdout.strip()

        # Get current branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if result.returncode == 0:
            ctx.branch = result.stdout.strip()

        # Check if working directory is dirty
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if result.returncode == 0:
            ctx.is_dirty = bool(result.stdout.strip())

        # Get commit timestamp
        if ctx.commit:
            result = subprocess.run(
                ["git", "show", "-s", "--format=%ci", "HEAD"],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=5,
            )
            if result.returncode == 0:
                # Parse git date format: 2026-01-30 15:30:00 +0100
                date_str = result.stdout.strip()
                try:
                    # Remove timezone suffix for naive datetime
                    date_part = date_str.rsplit(" ", 1)[0]
                    ctx.commit_time = datetime.strptime(date_part, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # Git not available or timeout
        pass

    return ctx


def get_commit_info(commit_ref: str, cwd: Optional[Path] = None) -> Optional[dict]:
    """
    Get information about a specific commit.

    Args:
        commit_ref: Commit hash, branch name, or ref like "HEAD~1"
        cwd: Working directory

    Returns:
        Dict with commit info or None if not found
    """
    try:
        # Get commit hash and timestamp
        result = subprocess.run(
            ["git", "show", "-s", "--format=%H|%ci|%s", commit_ref],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        parts = result.stdout.strip().split("|", 2)
        if len(parts) < 3:
            return None

        full_hash, date_str, subject = parts

        # Parse date
        try:
            date_part = date_str.rsplit(" ", 1)[0]
            commit_time = datetime.strptime(date_part, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            commit_time = None

        return {
            "hash": full_hash[:8],
            "full_hash": full_hash,
            "time": commit_time,
            "subject": subject,
        }

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def get_recent_commits(count: int = 5, cwd: Optional[Path] = None) -> list[dict]:
    """
    Get recent commits for the repository.

    Args:
        count: Number of commits to retrieve
        cwd: Working directory

    Returns:
        List of commit info dicts, most recent first
    """
    commits = []

    try:
        result = subprocess.run(
            ["git", "log", f"-{count}", "--format=%H|%ci|%s"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=10,
        )
        if result.returncode != 0:
            return commits

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|", 2)
            if len(parts) < 3:
                continue

            full_hash, date_str, subject = parts

            try:
                date_part = date_str.rsplit(" ", 1)[0]
                commit_time = datetime.strptime(date_part, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                commit_time = None

            commits.append(
                {
                    "hash": full_hash[:8],
                    "full_hash": full_hash,
                    "time": commit_time,
                    "subject": subject,
                }
            )

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return commits


def find_memories_near_commit(
    commit_ref: str,
    memories: list,
    window_hours: int = 2,
    cwd: Optional[Path] = None,
) -> list:
    """
    Find memories created near a specific commit.

    This enables queries like "what did we discuss during the last commit?"

    Args:
        commit_ref: Commit hash or ref
        memories: List of Memory objects to filter
        window_hours: Time window around commit (before and after)
        cwd: Working directory for git commands

    Returns:
        Memories created within the time window of the commit
    """
    from datetime import timedelta

    commit_info = get_commit_info(commit_ref, cwd)
    if not commit_info or not commit_info["time"]:
        return []

    commit_time = commit_info["time"]
    window = timedelta(hours=window_hours)

    matching = []
    for memory in memories:
        created = memory.created_at
        # Normalize to naive datetime
        if created.tzinfo is not None:
            created = created.replace(tzinfo=None)

        if abs(created - commit_time) <= window:
            matching.append(memory)

    return matching
