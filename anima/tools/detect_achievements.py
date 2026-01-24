# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Auto-achievement detection from git commits.

Scans recent git commits and creates ACHIEVEMENT memories for significant work.
Can be run manually or integrated into session_end hook.
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from anima.core import Memory, MemoryKind, ImpactLevel, RegionType, AgentResolver
from anima.lifecycle.injection import ensure_token_count
from anima.storage import MemoryStore


# Patterns that suggest significant achievements
ACHIEVEMENT_PATTERNS = [
    # Feature completion - "Add X command", "Implement Y", etc.
    (r"^add\s+.*(command|feature|module|hook|test)", ImpactLevel.HIGH),
    (r"^add\s+/\w+", ImpactLevel.HIGH),  # "Add /memory-export" style
    (
        r"\b(implement|create|build)\b.*\b(feature|command|module|system|api)\b",
        ImpactLevel.HIGH,
    ),
    (r"\bcomplete[ds]?\b", ImpactLevel.HIGH),
    (r"\bfinish(ed|es)?\b", ImpactLevel.MEDIUM),
    # Major milestones
    (r"\b(v?\d+\.\d+(\.\d+)?)\b", ImpactLevel.HIGH),  # Version numbers
    (r"\bmilestone\b", ImpactLevel.HIGH),
    (r"\brelease\b", ImpactLevel.HIGH),
    (r"\blaunch(ed|es|ing)?\b", ImpactLevel.HIGH),
    # Significant fixes
    (r"\bfix(ed|es)?\b.*\b(critical|major|important)\b", ImpactLevel.HIGH),
    (r"\bresolve[ds]?\b", ImpactLevel.MEDIUM),
    # Refactoring achievements
    (r"\brefactor(ed|s|ing)?\b", ImpactLevel.MEDIUM),
    (r"\bmigrat(e|ed|ion)\b", ImpactLevel.HIGH),
    # Test achievements
    (r"\b(\d+)\s*(tests?|specs?)\s*(pass(ing|ed)?|green)\b", ImpactLevel.MEDIUM),
    (r"\b100%\s*(coverage|tests?)\b", ImpactLevel.HIGH),
    (r"^add\s+tests?\b", ImpactLevel.MEDIUM),  # "Add tests for X"
]

# Patterns to skip (not achievements)
SKIP_PATTERNS = [
    r"^wip\b",
    r"^fixup\b",
    r"^squash\b",
    r"^merge\b",
    r"^revert\b",
    r"^\[skip",
    r"^chore\b",
]


def get_recent_commits(
    since_hours: int = 24, repo_path: Optional[Path] = None
) -> list[dict]:
    """
    Get commits from the last N hours.

    Returns list of dicts with: hash, message, author, date
    """
    cwd = repo_path or Path.cwd()

    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"--since={since_hours} hours ago",
                "--format=%H|%s|%an|%aI",
                "--no-merges",
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) >= 4:
                commits.append(
                    {
                        "hash": parts[0],
                        "message": parts[1],
                        "author": parts[2],
                        "date": datetime.fromisoformat(parts[3].replace("Z", "+00:00")),
                    }
                )

        return commits

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def should_skip(message: str) -> bool:
    """Check if commit should be skipped."""
    message_lower = message.lower()
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, message_lower):
            return True
    return False


def detect_achievement(message: str) -> Optional[tuple[str, ImpactLevel]]:
    """
    Detect if a commit message represents an achievement.

    Returns (reason, impact_level) or None.
    """
    message_lower = message.lower()

    for pattern, impact in ACHIEVEMENT_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return (message, impact)

    return None


def run(args: list[str]) -> int:
    """
    Run the auto-achievement detection.

    Args:
        args: Command line arguments
            --since N: Look back N hours (default: 24)
            --dry-run: Show what would be saved without saving

    Returns:
        Exit code (0 for success)
    """
    # Parse args
    since_hours = 24
    dry_run = False

    if "--help" in args or "-h" in args:
        print("Usage: ltm detect-achievements [options]")
        print()
        print("Scan git commits and create ACHIEVEMENT memories.")
        print()
        print("Options:")
        print("  --since N    Look back N hours (default: 24)")
        print("  --dry-run    Show what would be saved without saving")
        print("  --help, -h   Show this help message")
        return 0

    for i, arg in enumerate(args):
        if arg == "--since" and i + 1 < len(args):
            try:
                since_hours = int(args[i + 1])
            except ValueError:
                print(f"Invalid hours: {args[i + 1]}")
                return 1
        elif arg == "--dry-run":
            dry_run = True

    # Get commits
    commits = get_recent_commits(since_hours)

    if not commits:
        print(f"No commits found in the last {since_hours} hours.")
        return 0

    print(f"Scanning {len(commits)} commits from the last {since_hours} hours...\n")

    # Resolve context
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()
    project = resolver.resolve_project()

    store = MemoryStore()

    if not dry_run:
        store.save_agent(agent)
        store.save_project(project)

    achievements_found = 0
    skipped = 0

    for commit in commits:
        message = commit["message"]

        # Skip non-achievement commits
        if should_skip(message):
            skipped += 1
            continue

        result = detect_achievement(message)
        if not result:
            continue

        achievement_text, impact = result

        # Check if we already have this achievement (by commit hash in content)
        # This prevents duplicates on re-runs
        existing = store.search_memories(
            query=commit["hash"][:8], agent_id=agent.id, project_id=project.id, limit=1
        )

        if existing:
            print(f"  ⏭️  Already recorded: {message[:50]}...")
            skipped += 1
            continue

        # Format achievement content
        content = f"{achievement_text} (commit: {commit['hash'][:8]})"

        if dry_run:
            print(f"  🏆 Would save [{impact.value}]: {content[:60]}...")
        else:
            memory = Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.ACHIEVEMENTS,
                content=content,
                impact=impact,
                created_at=commit["date"],
            )
            ensure_token_count(memory)
            store.save_memory(memory)
            print(f"  🏆 Saved [{impact.value}]: {content[:60]}...")

        achievements_found += 1

    # Summary (to stdout for terminal visibility)
    print()
    if dry_run:
        print(
            f"Dry run: {achievements_found} achievements would be saved, {skipped} skipped"
        )
    else:
        print(
            f"{achievements_found} achievements saved, {skipped} skipped after detect-achievements"
        )

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
