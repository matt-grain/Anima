# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/memory-export command - Export memories to a portable format.

Exports memories to JSON for backup, migration, or sharing between agents.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from anima.core import AgentResolver, RegionType
from anima.storage import MemoryStore


def run(args: list[str]) -> int:
    """
    Run the memory-export command.

    Args:
        args: Command line arguments
            [output_file] - Optional output file path (default: stdout)
            --agent-only - Only export AGENT region memories
            --project-only - Only export PROJECT region memories
            --kind TYPE - Filter by memory kind

    Returns:
        Exit code (0 for success)
    """
    # Parse args
    output_file: Optional[str] = None
    agent_only = False
    project_only = False
    filter_kind: Optional[str] = None

    if "--help" in args or "-h" in args:
        print("Usage: ltm memory-export [output_file] [options]")
        print()
        print("Export memories to JSON format.")
        print()
        print("Options:")
        print("  --agent-only     Only export AGENT region memories")
        print("  --project-only   Only export PROJECT region memories")
        print("  --kind TYPE      Filter by kind (emotional, architectural, etc.)")
        print("  --help, -h       Show this help message")
        print()
        print("Examples:")
        print("  ltm memory-export                    # Print to stdout")
        print("  ltm memory-export backup.json       # Save to file")
        print("  ltm memory-export --agent-only      # Only agent memories")
        return 0

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--agent-only":
            agent_only = True
        elif arg == "--project-only":
            project_only = True
        elif arg in ("--kind", "-k") and i + 1 < len(args):
            filter_kind = args[i + 1].upper()
            i += 1
        elif not arg.startswith("-"):
            output_file = arg
        i += 1

    # Resolve agent and project
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()
    project = resolver.resolve_project()

    store = MemoryStore()

    # Get all memories
    all_memories = store.get_memories_for_agent(
        agent_id=agent.id,
        project_id=project.id
    )

    # Apply filters
    if agent_only:
        all_memories = [m for m in all_memories if m.region == RegionType.AGENT]
    elif project_only:
        all_memories = [m for m in all_memories if m.region == RegionType.PROJECT]

    if filter_kind:
        from anima.core import MemoryKind
        try:
            kind = MemoryKind(filter_kind)
            all_memories = [m for m in all_memories if m.kind == kind]
        except ValueError:
            print(f"Unknown kind: {filter_kind}")
            return 1

    if not all_memories:
        print("No memories to export.", file=sys.stderr)
        return 0

    # Build export structure
    export_data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "agent": {
            "id": agent.id,
            "name": agent.name,
        },
        "project": {
            "id": project.id,
            "name": project.name,
        },
        "memories": []
    }

    for memory in all_memories:
        memory_data = {
            "id": memory.id,
            "region": memory.region.value,
            "kind": memory.kind.value,
            "content": memory.content,
            "impact": memory.impact.value,
            "confidence": memory.confidence,
            "created_at": memory.created_at.isoformat(),
            "last_accessed": memory.last_accessed.isoformat() if memory.last_accessed else None,
        }

        # Optional fields
        if memory.project_id:
            memory_data["project_id"] = memory.project_id
        if memory.original_content:
            memory_data["original_content"] = memory.original_content
        if memory.previous_memory_id:
            memory_data["previous_memory_id"] = memory.previous_memory_id
        if memory.superseded_by:
            memory_data["superseded_by"] = memory.superseded_by

        export_data["memories"].append(memory_data)

    # Output
    json_output = json.dumps(export_data, indent=2, ensure_ascii=False)

    if output_file:
        Path(output_file).write_text(json_output)
        print(f"Exported {len(all_memories)} memories to {output_file}")
    else:
        print(json_output)

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
