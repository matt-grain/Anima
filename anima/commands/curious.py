# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/curious command - Add a question to the research queue.

This command is invoked when the agent or user wants to save a question
or topic for later research. Questions that recur get priority bumps.
"""

import argparse
import sys

from anima.core import AgentResolver, RegionType
from anima.storage import MemoryStore, CuriosityStore


def infer_region(text: str, has_project: bool) -> RegionType:
    """
    Infer whether this is a project-specific or agent-wide curiosity.

    Agent-wide curiosities are about general topics.
    Project curiosities are about project-specific issues.
    """
    text_lower = text.lower()

    # Agent-wide indicators (general knowledge topics)
    agent_words = [
        "general",
        "always",
        "in general",
        "research shows",
        "studies",
        "llm",
        "ai ",
        "anthropic",
        "openai",
        "best practice",
        "industry",
        "how does",
        "why does",
        "what is",
    ]
    if any(word in text_lower for word in agent_words):
        return RegionType.AGENT

    # Project-specific indicators
    project_words = [
        "this project",
        "this codebase",
        "this file",
        "this function",
        "our",
        "here",
        "error",
        "bug",
        "issue",
        "failing",
        "broken",
    ]
    if any(word in text_lower for word in project_words):
        return RegionType.PROJECT

    # If we have a project context, default to PROJECT
    if has_project:
        return RegionType.PROJECT

    return RegionType.AGENT


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the curious command."""
    parser = argparse.ArgumentParser(
        prog="uv run anima curious",
        description="Add a question or topic to the research queue.",
        epilog="Questions that recur get automatic priority bumps.",
    )
    parser.add_argument("question", nargs="+", help="The question or topic to research")
    parser.add_argument(
        "--region",
        "-r",
        choices=["agent", "project"],
        help="Where to store: 'agent' (cross-project) or 'project' (local)",
    )
    parser.add_argument(
        "--context",
        "-c",
        help="Additional context about what triggered this curiosity",
    )
    return parser


def run(args: list[str]) -> int:
    """
    Run the curious command.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success)
    """
    if not args:
        print("Usage: uv run anima curious <question>")
        print("       uv run anima curious --region agent <question>")
        print("       uv run anima curious --context 'while debugging' <question>")
        print("\nExample: uv run anima curious Why does Docker need PRAGMA synchronous?")
        print("\nFlags:")
        print("  --region, -r   agent|project    Where to store (default: inferred)")
        print("  --context, -c  TEXT  What triggered this curiosity")
        return 1

    # Parse arguments
    parser = create_parser()
    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        return 0

    # Join question arguments
    question = " ".join(parsed.question)

    # Resolve agent and project
    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()

    # Ensure agent/project exist in DB
    store = MemoryStore()
    store.save_agent(agent)
    store.save_project(project)

    # Determine region
    if parsed.region:
        region = RegionType(parsed.region.upper())
    else:
        region = infer_region(question, has_project=True)

    # Add to curiosity queue
    curiosity_store = CuriosityStore()
    curiosity = curiosity_store.add_curiosity(
        agent_id=agent.id,
        question=question,
        region=region,
        project_id=project.id if region == RegionType.PROJECT else None,
        context=parsed.context,
    )

    # Check if this was a recurrence bump
    if curiosity.recurrence_count > 1:
        print(f"This question came up again! (#{curiosity.recurrence_count})")
        print(f"Priority boosted. First asked: {curiosity.first_seen.strftime('%Y-%m-%d')}")
    else:
        region_str = f"PROJECT ({project.name})" if region == RegionType.PROJECT else "AGENT"
        print(f"Added to research queue ({region_str})")

    print(f"Curiosity ID: {curiosity.id}")
    print(f"Question: {question}")

    # Show queue size
    open_count = curiosity_store.count_open(agent.id, project.id)
    print(f"\nResearch queue: {open_count} open {'question' if open_count == 1 else 'questions'}")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
