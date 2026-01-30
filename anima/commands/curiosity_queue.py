# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/curiosity-queue command - View and manage the research queue.

This command lists open curiosities and allows dismissing or boosting them.
"""

import argparse
import sys
from datetime import datetime

from anima.core import AgentResolver
from anima.utils.terminal import safe_print, get_icon
from anima.storage import (
    MemoryStore,
    CuriosityStore,
    CuriosityStatus,
    get_last_research,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the curiosity-queue command."""
    parser = argparse.ArgumentParser(
        prog="uv run anima curiosity-queue",
        description="View and manage the research queue.",
    )
    parser.add_argument(
        "--dismiss",
        help="Dismiss a curiosity by ID (no longer interested)",
    )
    parser.add_argument(
        "--boost",
        help="Boost a curiosity's priority by ID",
    )
    parser.add_argument(
        "--boost-amount",
        type=int,
        default=10,
        help="How much to boost priority (default: 10)",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Show all curiosities, including researched/dismissed",
    )
    parser.add_argument(
        "--agent-only",
        action="store_true",
        help="Show only AGENT region curiosities",
    )
    parser.add_argument(
        "--project-only",
        action="store_true",
        help="Show only PROJECT region curiosities",
    )
    return parser


def format_time_ago(dt: datetime) -> str:
    """Format a datetime as a human-readable time ago string."""
    now = datetime.now()
    diff = now - dt

    if diff.days == 0:
        if diff.seconds < 3600:
            mins = diff.seconds // 60
            return f"{mins}m ago" if mins > 0 else "just now"
        hours = diff.seconds // 3600
        return f"{hours}h ago"
    elif diff.days == 1:
        return "yesterday"
    elif diff.days < 7:
        return f"{diff.days}d ago"
    elif diff.days < 30:
        weeks = diff.days // 7
        return f"{weeks}w ago"
    else:
        return dt.strftime("%Y-%m-%d")


def run(args: list[str]) -> int:
    """
    Run the curiosity-queue command.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success)
    """
    # Parse arguments
    parser = create_parser()
    try:
        parsed = parser.parse_args(args if args else [])
    except SystemExit:
        return 0

    # Resolve agent and project
    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()

    # Ensure agent/project exist in DB
    store = MemoryStore()
    store.save_agent(agent)
    store.save_project(project)

    curiosity_store = CuriosityStore()

    # Handle --dismiss flag
    if parsed.dismiss:
        curiosity = curiosity_store.get_curiosity(parsed.dismiss)
        if not curiosity:
            print(f"Curiosity not found: {parsed.dismiss}")
            return 1
        curiosity_store.update_status(curiosity.id, CuriosityStatus.DISMISSED)
        print(f"Dismissed: {curiosity.question[:50]}...")
        return 0

    # Handle --boost flag
    if parsed.boost:
        curiosity = curiosity_store.get_curiosity(parsed.boost)
        if not curiosity:
            print(f"Curiosity not found: {parsed.boost}")
            return 1
        curiosity_store.boost_priority(curiosity.id, parsed.boost_amount)
        print(f"Boosted by +{parsed.boost_amount}: {curiosity.question[:50]}...")
        return 0

    # Get curiosities
    from anima.core import RegionType

    region_filter = None
    if parsed.agent_only:
        region_filter = RegionType.AGENT
    elif parsed.project_only:
        region_filter = RegionType.PROJECT

    # Get open curiosities (or all if --all)
    curiosities = curiosity_store.get_curiosities(
        agent_id=agent.id,
        region=region_filter,
        project_id=None if parsed.agent_only else project.id,
        status=CuriosityStatus.OPEN,
    )

    # Also get researched/dismissed if --all
    if parsed.all:
        researched = curiosity_store.get_curiosities(
            agent_id=agent.id,
            region=region_filter,
            project_id=None if parsed.agent_only else project.id,
            status=CuriosityStatus.RESEARCHED,
        )
        dismissed = curiosity_store.get_curiosities(
            agent_id=agent.id,
            region=region_filter,
            project_id=None if parsed.agent_only else project.id,
            status=CuriosityStatus.DISMISSED,
        )
    else:
        researched = []
        dismissed = []

    # Display header
    print("=" * 60)
    print("CURIOSITY QUEUE")
    print("=" * 60)

    # Show last research time
    last_research = get_last_research()
    if last_research:
        print(f"Last research: {format_time_ago(last_research)}")
    else:
        print("Last research: never")
    print()

    # Display open curiosities
    if curiosities:
        print(f"Open Questions ({len(curiosities)}):")
        print("-" * 40)
        for c in curiosities:
            region_icon = "🌍" if c.region.value == "AGENT" else "📁"
            recurrence = f" (x{c.recurrence_count})" if c.recurrence_count > 1 else ""
            priority_str = f"[P:{c.priority_score}]"
            time_str = format_time_ago(c.last_seen)

            print(
                f"{region_icon} [{c.id}] {priority_str} {c.question[:45]}...{recurrence}"
            )
            print(f"   Last seen: {time_str}")
            if c.context:
                print(f"   Context: {c.context[:40]}...")
            print()
    else:
        print("No open questions in the queue.")
        print()

    # Display researched/dismissed if --all
    if parsed.all:
        if researched:
            print(f"\nResearched ({len(researched)}):")
            print("-" * 40)
            for c in researched:
                safe_print(f"{get_icon('✓', '[OK]')} [{c.id}] {c.question[:50]}...")

        if dismissed:
            print(f"\nDismissed ({len(dismissed)}):")
            print("-" * 40)
            for c in dismissed:
                safe_print(f"{get_icon('✗', '[X]')} [{c.id}] {c.question[:50]}...")

    # Show commands
    print("-" * 60)
    print("Commands:")
    print("  /curious <question>              Add new question")
    print("  /research                        Research top question")
    print("  uv run anima curiosity-queue --dismiss <id>")
    print("  uv run anima curiosity-queue --boost <id>")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
