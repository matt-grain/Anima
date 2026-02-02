# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/memory-import command - Import memories from a JSON file.

Imports memories from a previously exported JSON file.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from anima.core import Memory, MemoryKind, ImpactLevel, RegionType, AgentResolver
from anima.lifecycle.injection import ensure_token_count
from anima.storage import MemoryStore


def run(args: list[str]) -> int:
    """
    Run the memory-import command.

    Args:
        args: Command line arguments
            <input_file> - JSON file to import
            --dry-run - Show what would be imported without saving
            --merge - Skip existing memories instead of failing
            --remap-agent - Remap to current agent instead of preserving original

    Returns:
        Exit code (0 for success)
    """
    # Parse args
    input_file: str | None = None
    dry_run = False
    merge = False
    remap_agent = False

    if "--help" in args or "-h" in args:
        print("Usage: ltm memory-import <input_file> [options]")
        print()
        print("Import memories from a JSON file.")
        print()
        print("Options:")
        print("  --dry-run       Show what would be imported without saving")
        print("  --merge         Skip existing memories instead of failing")
        print("  --remap-agent   Assign memories to current agent")
        print("  --help, -h      Show this help message")
        print()
        print("Examples:")
        print("  ltm memory-import backup.json")
        print("  ltm memory-import backup.json --dry-run")
        print("  ltm memory-import backup.json --merge --remap-agent")
        return 0

    for i, arg in enumerate(args):
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--merge":
            merge = True
        elif arg == "--remap-agent":
            remap_agent = True
        elif not arg.startswith("-"):
            input_file = arg

    if not input_file:
        print("Usage: ltm memory-import <input_file>")
        print("Example: ltm memory-import backup.json")
        return 1

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"File not found: {input_file}")
        return 1

    # Parse JSON
    try:
        data = json.loads(input_path.read_text())
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        return 1

    # Validate structure
    if "memories" not in data:
        print("Invalid export file: missing 'memories' key")
        return 1

    memories_data = data["memories"]
    if not memories_data:
        print("No memories to import.")
        return 0

    # Resolve current agent/project
    resolver = AgentResolver(Path.cwd())
    current_agent = resolver.resolve()
    current_project = resolver.resolve_project()

    store = MemoryStore()

    # Ensure agent and project exist
    if not dry_run:
        store.save_agent(current_agent)
        store.save_project(current_project)

    imported = 0
    skipped = 0
    errors = 0

    for mem_data in memories_data:
        try:
            # Check if already exists
            existing = store.get_memory(mem_data["id"])
            if existing:
                if merge:
                    skipped += 1
                    continue
                else:
                    print(f"Memory {mem_data['id'][:8]} already exists. Use --merge to skip.")
                    errors += 1
                    continue

            # Determine agent_id
            agent_id = current_agent.id if remap_agent else mem_data.get("agent_id", current_agent.id)

            # Determine project_id
            project_id = None
            if mem_data.get("region") == "PROJECT":
                project_id = current_project.id if remap_agent else mem_data.get("project_id", current_project.id)

            # Parse timestamps
            created_at = datetime.fromisoformat(mem_data["created_at"])
            last_accessed = None
            if mem_data.get("last_accessed"):
                last_accessed = datetime.fromisoformat(mem_data["last_accessed"])

            # Create memory
            memory = Memory(
                id=mem_data["id"],
                agent_id=agent_id,
                region=RegionType(mem_data["region"]),
                project_id=project_id,
                kind=MemoryKind(mem_data["kind"]),
                content=mem_data["content"],
                original_content=mem_data.get("original_content"),
                impact=ImpactLevel(mem_data["impact"]),
                confidence=mem_data.get("confidence", 1.0),
                created_at=created_at,
                last_accessed=last_accessed or created_at,
                previous_memory_id=mem_data.get("previous_memory_id"),
                superseded_by=mem_data.get("superseded_by"),
            )

            if dry_run:
                print(f"Would import: [{memory.kind.value}:{memory.impact.value}] {memory.content[:50]}...")
            else:
                ensure_token_count(memory)
                store.save_memory(memory)

            imported += 1

        except (KeyError, ValueError) as e:
            print(f"Error importing memory: {e}")
            errors += 1

    # Summary
    if dry_run:
        print(f"\nDry run complete: {imported} would be imported, {skipped} skipped, {errors} errors")
    else:
        print(f"\nImport complete: {imported} imported, {skipped} skipped, {errors} errors")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
