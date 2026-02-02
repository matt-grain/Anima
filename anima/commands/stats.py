# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/memory-stats command - Show memory statistics.

Displays counts and health metrics for the agent's memories.
"""

import sys
from collections import Counter
from pathlib import Path

from anima.core import AgentResolver, MemoryKind, ImpactLevel, RegionType
from anima.storage import MemoryStore
from anima.utils.terminal import safe_print, get_icon


def run(args: list[str]) -> int:
    """
    Run the memory-stats command.

    Args:
        args: Command line arguments (unused)

    Returns:
        Exit code (0 for success)
    """
    # Handle help
    if args and args[0] in ("--help", "-h"):
        print("Usage: uv run anima memory-stats")
        print()
        print("Show memory statistics for the current agent.")
        print()
        print("Displays:")
        print("  - Total memory count")
        print("  - Breakdown by region (AGENT vs PROJECT)")
        print("  - Breakdown by kind (EMOTIONAL, ARCHITECTURAL, etc.)")
        print("  - Breakdown by impact level")
        print("  - Health indicators (superseded, low confidence)")
        return 0

    # Resolve agent and project
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()
    project = resolver.resolve_project()

    store = MemoryStore()

    # Get all memories for this agent
    all_memories = store.get_memories_for_agent(agent_id=agent.id, project_id=project.id)

    if not all_memories:
        print(f"No memories found for agent '{agent.name}'")
        return 0

    # Count by various dimensions
    by_region: Counter[str] = Counter()
    by_kind: Counter[str] = Counter()
    by_impact: Counter[str] = Counter()
    superseded_count = 0
    low_confidence_count = 0

    for memory in all_memories:
        by_region[memory.region.value] += 1
        by_kind[memory.kind.value] += 1
        by_impact[memory.impact.value] += 1

        if memory.superseded_by:
            superseded_count += 1
        if memory.is_low_confidence():
            low_confidence_count += 1

    # Display stats
    print(f"# Memory Statistics for {agent.name}")
    print(f"Project: {project.name}")
    print()

    print(f"**Total Memories:** {len(all_memories)}")
    print()

    # By Region
    print("## By Region")
    for region in RegionType:
        count = by_region.get(region.value, 0)
        icon = "🌐" if region == RegionType.AGENT else "📁"
        print(f"  {icon} {region.value}: {count}")
    print()

    # By Kind
    print("## By Kind")
    kind_icons = {
        MemoryKind.EMOTIONAL: "💜",
        MemoryKind.ARCHITECTURAL: "🏗️",
        MemoryKind.LEARNINGS: "📚",
        MemoryKind.ACHIEVEMENTS: "🏆",
    }
    for kind in MemoryKind:
        count = by_kind.get(kind.value, 0)
        icon = kind_icons.get(kind, "•")
        print(f"  {icon} {kind.value}: {count}")
    print()

    # By Impact
    print("## By Impact")
    impact_icons = {
        ImpactLevel.CRITICAL: "🔴",
        ImpactLevel.HIGH: "🟠",
        ImpactLevel.MEDIUM: "🟡",
        ImpactLevel.LOW: "🟢",
    }
    for impact in ImpactLevel:
        count = by_impact.get(impact.value, 0)
        icon = impact_icons.get(impact, "•")
        print(f"  {icon} {impact.value}: {count}")
    print()

    # Health
    print("## Health")
    active_count = len(all_memories) - superseded_count
    safe_print(f"  {get_icon('✅', '[OK]')} Active: {active_count}")
    safe_print(f"  {get_icon('⚠️', '[!]')}  Superseded: {superseded_count}")
    safe_print(f"  {get_icon('❓', '[?]')} Low confidence: {low_confidence_count}")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
