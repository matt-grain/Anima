# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/research command - Process curiosity queue and conduct research.

This command pops the top curiosity from the queue and prompts for research.
After research is complete, findings are saved as LEARNINGS memories.
"""

import argparse
import sys

from anima.core import AgentResolver
from anima.storage import (
    MemoryStore,
    CuriosityStore,
    CuriosityStatus,
    set_last_research,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the research command."""
    parser = argparse.ArgumentParser(
        prog="uv run anima research",
        description="Pop top curiosity from queue and conduct research.",
        epilog="After research, save findings with /remember.",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="Show the queue before researching",
    )
    parser.add_argument(
        "--topic",
        "-t",
        nargs="+",
        help="Research a specific topic (bypasses queue)",
    )
    parser.add_argument(
        "--complete",
        "-c",
        help="Mark a curiosity as researched by ID",
    )
    parser.add_argument(
        "--defer",
        "-d",
        action="store_true",
        help="Defer research to later (don't pop from queue)",
    )
    return parser


def format_curiosity_list(curiosities: list, show_details: bool = True) -> str:
    """Format a list of curiosities for display."""
    if not curiosities:
        return "No open questions in the research queue."

    lines = ["Research Queue (sorted by priority):", ""]

    for i, c in enumerate(curiosities, 1):
        priority = c.priority_score
        recurrence = f"x{c.recurrence_count}" if c.recurrence_count > 1 else ""
        days_ago = (c.last_seen.date() - c.first_seen.date()).days

        region_icon = "🌍" if c.region.value == "AGENT" else "📁"
        lines.append(f"{i}. [{c.id}] {region_icon} {c.question}")

        if show_details:
            details = f"   Priority: {priority}"
            if recurrence:
                details += f" | Recurred: {recurrence}"
            if days_ago > 0:
                details += f" | First asked: {days_ago}d ago"
            if c.context:
                details += f"\n   Context: {c.context}"
            lines.append(details)
            lines.append("")

    return "\n".join(lines)


def run(args: list[str]) -> int:
    """
    Run the research command.

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

    # Handle --complete flag (mark as researched)
    if parsed.complete:
        curiosity = curiosity_store.get_curiosity(parsed.complete)
        if not curiosity:
            print(f"Curiosity not found: {parsed.complete}")
            return 1
        curiosity_store.update_status(curiosity.id, CuriosityStatus.RESEARCHED)
        set_last_research()
        print(f"Marked as researched: {curiosity.question[:50]}...")
        return 0

    # Handle --topic flag (ad-hoc research)
    if parsed.topic:
        topic = " ".join(parsed.topic)
        set_last_research()
        print("=" * 60)
        print("RESEARCH MODE")
        print("=" * 60)
        print(f"\nTopic: {topic}")
        print("\nPlease research this topic and then save findings with:")
        print("  /remember <findings> --kind learnings")
        print("=" * 60)
        return 0

    # Get curiosities for current context
    curiosities = curiosity_store.get_curiosities(
        agent_id=agent.id,
        project_id=project.id,
        status=CuriosityStatus.OPEN,
    )

    # Handle --list flag
    if parsed.list:
        print(format_curiosity_list(curiosities))
        return 0

    # Get top curiosity
    if not curiosities:
        print("No open questions in the research queue!")
        print("\nAdd questions with: /curious <question>")
        return 0

    top = curiosities[0]

    # Handle --defer flag
    if parsed.defer:
        print(f"Deferred: {top.question}")
        print("Will ask again at next session start.")
        return 0

    # Display research prompt
    print("=" * 60)
    print("RESEARCH MODE")
    print("=" * 60)
    region_str = (
        "AGENT (cross-project)"
        if top.region.value == "AGENT"
        else f"PROJECT ({project.name})"
    )
    print(f"\nRegion: {region_str}")
    print(f"Priority: {top.priority_score} (asked {top.recurrence_count}x)")
    if top.context:
        print(f"Context: {top.context}")
    print(f"\nQuestion: {top.question}")
    print("\n" + "-" * 60)
    print("Research this topic, then:")
    print("  1. Save findings: /remember <findings> --kind learnings")
    print(f"  2. Mark complete: uv run anima research --complete {top.id}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
