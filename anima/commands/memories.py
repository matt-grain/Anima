# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/memories command - List all memories.

Shows all memories for the current agent/project with optional filters.
"""

import sys
from pathlib import Path
from typing import Optional, TypedDict

from anima.core import AgentResolver, MemoryKind, RegionType
from anima.storage import MemoryStore


class MemoriesFilterOptions(TypedDict):
    """Typed options for the memories command."""

    kind: Optional[str]
    region: Optional[str]
    all: bool


def parse_args(args: list[str]) -> MemoriesFilterOptions:
    """Parse command line arguments."""
    result: MemoriesFilterOptions = {"kind": None, "region": None, "all": False}

    i = 0
    while i < len(args):
        if args[i] == "--kind" and i + 1 < len(args):
            result["kind"] = args[i + 1].upper()
            i += 2
        elif args[i] == "--region" and i + 1 < len(args):
            result["region"] = args[i + 1].upper()
            i += 2
        elif args[i] == "--all":
            result["all"] = True
            i += 1
        else:
            i += 1

    return result


def run(args: list[str]) -> int:
    """
    Run the memories command.

    Args:
        args: Optional filters (--kind TYPE, --region REGION, --all)

    Returns:
        Exit code (0 for success)
    """
    options = parse_args(args)

    # Resolve agent and project
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()
    project = resolver.resolve_project()

    store = MemoryStore()

    # Build query parameters
    kind = None
    if options["kind"]:
        try:
            kind = MemoryKind(options["kind"])
        except ValueError:
            print(f"Invalid kind: {options['kind']}")
            print(f"Valid kinds: {', '.join(k.value for k in MemoryKind)}")
            return 1

    region = None
    if options["region"]:
        try:
            region = RegionType(options["region"])
        except ValueError:
            print(f"Invalid region: {options['region']}")
            print(f"Valid regions: {', '.join(r.value for r in RegionType)}")
            return 1

    # Get memories
    memories = store.get_memories_for_agent(
        agent_id=agent.id,
        region=region,
        project_id=project.id if region == RegionType.PROJECT or region is None else None,
        kind=kind,
        include_superseded=bool(options["all"]),
    )

    if not memories:
        print("No memories found")
        if kind or region:
            print("(Try removing filters or use --all to include superseded)")
        return 0

    # Group by kind for display
    by_kind: dict[MemoryKind, list] = {}
    for memory in memories:
        if memory.kind not in by_kind:
            by_kind[memory.kind] = []
        by_kind[memory.kind].append(memory)

    print(f"Memories for {agent.name} @ {project.name}")
    print(f"{'=' * 50}\n")

    for mem_kind in MemoryKind:
        if mem_kind not in by_kind:
            continue

        kind_memories = by_kind[mem_kind]
        print(f"## {mem_kind.value} ({len(kind_memories)})")
        print()

        for memory in kind_memories:
            # Status markers
            markers = []
            if memory.is_superseded():
                markers.append("SUPERSEDED")
            if memory.is_low_confidence():
                markers.append(f"confidence:{memory.confidence:.1f}")
            marker_str = f" [{', '.join(markers)}]" if markers else ""

            # Region indicator
            region_str = "🌐" if memory.region == RegionType.AGENT else "📁"

            # Format output
            date_str = memory.created_at.strftime("%Y-%m-%d")
            print(f"  {region_str} [{memory.impact.value}]{marker_str} {memory.content[:70]}")
            print(f"     ID: {memory.id[:8]} | {date_str}")
            print()

    # Summary
    total = len(memories)
    agent_count = sum(1 for m in memories if m.region == RegionType.AGENT)
    project_count = total - agent_count
    print(f"Total: {total} memories ({agent_count} agent 🌐, {project_count} project 📁)")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
