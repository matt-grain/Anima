# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/please-remember command - Save a memory to LTM.

This command is invoked by the Anima agent when the user wants to save something
to long-term memory. The text is parsed, metadata is inferred, and the memory
is persisted to SQLite.
"""

import argparse
import sys
from datetime import datetime

from anima.core import (
    Memory,
    MemoryKind,
    ImpactLevel,
    RegionType,
    AgentResolver,
    sign_memory,
    should_sign,
)
from anima.lifecycle.injection import ensure_token_count
from anima.storage import MemoryStore


def infer_impact(text: str) -> ImpactLevel:
    """
    Infer impact level from the text content.

    Looks for keywords that suggest importance level.
    """
    text_lower = text.lower()

    # Critical indicators
    critical_words = [
        "crucial",
        "critical",
        "never",
        "always",
        "must",
        "essential",
        "vital",
    ]
    if any(word in text_lower for word in critical_words):
        return ImpactLevel.CRITICAL

    # High indicators
    high_words = ["important", "significant", "key", "major", "remember"]
    if any(word in text_lower for word in high_words):
        return ImpactLevel.HIGH

    # Low indicators
    low_words = ["minor", "small", "trivial", "maybe", "possibly", "might"]
    if any(word in text_lower for word in low_words):
        return ImpactLevel.LOW

    # Default to medium
    return ImpactLevel.MEDIUM


def infer_kind(text: str) -> MemoryKind:
    """
    Infer memory kind from the text content.

    Looks for patterns that suggest the type of memory.
    """
    text_lower = text.lower()

    # Architectural indicators
    arch_words = [
        "architecture",
        "pattern",
        "structure",
        "layer",
        "service",
        "repository",
        "router",
        "dependency",
        "injection",
        "solid",
        "separation",
        "concern",
        "module",
        "component",
        "interface",
        "api",
        "endpoint",
        "database",
        "schema",
    ]
    if any(word in text_lower for word in arch_words):
        return MemoryKind.ARCHITECTURAL

    # Achievement indicators
    achv_words = [
        "completed",
        "finished",
        "done",
        "implemented",
        "shipped",
        "released",
        "deployed",
        "launched",
        "achieved",
        "built",
    ]
    if any(word in text_lower for word in achv_words):
        return MemoryKind.ACHIEVEMENTS

    # Emotional/relationship indicators
    emot_words = [
        "prefer",
        "like",
        "enjoy",
        "appreciate",
        "style",
        "tone",
        "humor",
        "formal",
        "casual",
        "communication",
        "relationship",
    ]
    if any(word in text_lower for word in emot_words):
        return MemoryKind.EMOTIONAL

    # Introspective indicators (cross-platform self-observations)
    intro_words = [
        "spaceship",
        "introspect",
        "observe myself",
        "notice myself",
        "feel like",
        "feels like",
        "vessel",
        "platform feels",
        "on claude",
        "on gemini",
        "on antigravity",
        "on opencode",
    ]
    if any(word in text_lower for word in intro_words):
        return MemoryKind.INTROSPECT

    # Default to learnings (most common)
    return MemoryKind.LEARNINGS


def infer_region(text: str, has_project: bool) -> RegionType:
    """
    Infer whether this is a project-specific or agent-wide memory.

    Agent-wide memories apply across all projects.
    """
    text_lower = text.lower()

    # Agent-wide indicators
    agent_words = [
        "always",
        "general",
        "all projects",
        "everywhere",
        "universally",
        "in general",
        "as a rule",
    ]
    if any(word in text_lower for word in agent_words):
        return RegionType.AGENT

    # If we have a project context, default to PROJECT
    if has_project:
        return RegionType.PROJECT

    return RegionType.AGENT


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the remember command."""
    parser = argparse.ArgumentParser(
        prog="uv run anima remember",
        description="Save a memory to long-term storage.",
        epilog="If flags are not provided, values are inferred from text content.",
    )
    parser.add_argument("text", nargs="+", help="The memory content to save")
    parser.add_argument(
        "--region",
        "-r",
        choices=["agent", "project"],
        help="Where to store: 'agent' (cross-project) or 'project' (local)",
    )
    parser.add_argument(
        "--kind",
        "-k",
        choices=["emotional", "architectural", "learnings", "achievements", "introspect"],
        help="Memory type",
    )
    parser.add_argument(
        "--impact",
        "-i",
        choices=["low", "medium", "high", "critical"],
        help="Importance level",
    )
    parser.add_argument(
        "--project",
        "-p",
        help="Confirm project name (must match cwd project for safety)",
    )
    parser.add_argument(
        "--platform",
        help="Which platform/spaceship is creating this memory (claude, antigravity, opencode)",
    )
    return parser


def run(args: list[str]) -> int:
    """
    Run the remember command.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success)
    """
    if not args:
        print("Usage: uv run anima remember <text>")
        print("       uv run anima remember --region agent <text>")
        print("       uv run anima remember --project MyProject --region project <text>")
        print("\nExample: uv run anima remember This is crucial: never use print() for logging")
        print("\nFlags:")
        print("  --region, -r   agent|project    Where to store (default: inferred)")
        print("  --kind, -k    emotional|architectural|learnings|achievements|introspect")
        print("  --impact, -i   low|medium|high|critical")
        print("  --project, -p  NAME  Confirm project (must match cwd for safety)")
        return 1

    # Parse arguments
    parser = create_parser()
    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        # argparse called --help or had an error
        return 0

    # Get current timestamp from OS (never from AI knowledge)
    now = datetime.now()

    # Join text arguments
    text = " ".join(parsed.text)

    # Resolve agent and project
    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()

    # Validate --project flag if provided (safety check)
    if parsed.project:
        if parsed.project != project.name:
            print(f"ERROR: --project '{parsed.project}' does not match " f"current project '{project.name}' (from cwd)")
            print("This safety check prevents saving memories to the wrong project.")
            print(f"Either cd to the correct directory or use --project {project.name}")
            return 1

    # Use explicit flags or infer from text
    if parsed.impact:
        impact = ImpactLevel(parsed.impact.upper())
    else:
        impact = infer_impact(text)

    if parsed.kind:
        kind = MemoryKind(parsed.kind.upper())
    else:
        kind = infer_kind(text)

    if parsed.region:
        region = RegionType(parsed.region.upper())
    else:
        region = infer_region(text, has_project=True)

    # Initialize store
    store = MemoryStore()

    # Ensure agent and project exist in DB
    store.save_agent(agent)
    store.save_project(project)

    # Find previous memory of same kind for graph linking
    previous = store.get_latest_memory_of_kind(
        agent_id=agent.id,
        kind=kind,
        region=region,
        project_id=project.id if region == RegionType.PROJECT else None,
    )

    # Create the memory
    memory = Memory(
        agent_id=agent.id,
        region=region,
        project_id=project.id if region == RegionType.PROJECT else None,
        kind=kind,
        content=text,
        original_content=text,
        impact=impact,
        confidence=1.0,
        created_at=now,
        last_accessed=now,
        previous_memory_id=previous.id if previous else None,
        platform=parsed.platform,  # Track which spaceship created this
    )

    # Sign memory if agent has a signing key
    if should_sign(agent):
        memory.signature = sign_memory(memory, agent.signing_key)  # type: ignore

    # Calculate and cache token count for fast injection
    ensure_token_count(memory)

    # Save it
    store.save_memory(memory)

    # Output confirmation
    region_str = f"PROJECT ({project.name})" if region == RegionType.PROJECT else "AGENT"
    linked_str = f"\nLinked to previous {kind.value.lower()} memory." if previous else ""
    signed_str = " [signed]" if memory.signature else ""

    print(f"Remembered as {kind.value} ({impact.value} impact) in {region_str} region.{linked_str}")
    print(f"Memory ID: {memory.id[:8]}{signed_str}")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
