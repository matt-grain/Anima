# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/supersede command - Mark a memory as superseded by another.

Used when a newer memory replaces or completes an older one
(e.g., a cliffhanger resolved, a pending state completed).
"""

from __future__ import annotations

import sys
from pathlib import Path

from anima.core import AgentResolver
from anima.storage import MemoryStore


def _find_memory_by_prefix(store: MemoryStore, agent_id: str, prefix: str):
    """Find a memory by ID prefix, returning (memory, error_message)."""
    memories = store.get_memories_for_agent(agent_id=agent_id, include_superseded=True)
    matching = [m for m in memories if m.id.startswith(prefix)]

    if not matching:
        return None, f"No memory found with ID starting with '{prefix}'"

    if len(matching) > 1:
        lines = [f"Multiple memories match '{prefix}':"]
        for m in matching:
            content_preview = m.content[:50].replace("\n", " ")
            lines.append(f"  {m.id[:8]}: {content_preview}...")
        lines.append("\nPlease provide a more specific ID")
        return None, "\n".join(lines)

    return matching[0], None


def run(args: list[str]) -> int:
    """
    Run the supersede command.

    Args:
        args: [old_memory_id, new_memory_id] or [old_id, --by, new_id]

    Returns:
        Exit code (0 for success)
    """
    if len(args) < 2:
        print("Usage: uv run anima supersede <old-id> --by <new-id>")
        print("       uv run anima supersede <old-id> <new-id>")
        print()
        print("Marks <old-id> as superseded by <new-id>.")
        print("The old memory will no longer load at session start.")
        print()
        print("Example: uv run anima supersede c9d26055 --by 03d8d76e")
        print()
        print("Use 'uv run anima memories' to see memory IDs")
        return 1

    # Parse arguments
    old_prefix = args[0]
    if "--by" in args:
        by_index = args.index("--by")
        if by_index + 1 >= len(args):
            print("Error: --by requires a memory ID")
            return 1
        new_prefix = args[by_index + 1]
    else:
        new_prefix = args[1]

    # Resolve agent
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()

    store = MemoryStore()

    # Find old memory
    old_memory, error = _find_memory_by_prefix(store, agent.id, old_prefix)
    if error or old_memory is None:
        print(error or f"Memory not found: {old_prefix}")
        return 1

    # Find new memory
    new_memory, error = _find_memory_by_prefix(store, agent.id, new_prefix)
    if error or new_memory is None:
        print(error or f"Memory not found: {new_prefix}")
        return 1

    # Type narrowing: both are guaranteed to be Memory at this point
    assert old_memory is not None  # Already checked above

    # Validate
    if old_memory.id == new_memory.id:
        print("Error: A memory cannot supersede itself")
        return 1

    if old_memory.superseded_by:
        print(f"Warning: Memory {old_prefix} is already superseded by {old_memory.superseded_by[:8]}")
        print("Updating supersession...")

    # Perform supersession
    success = store.supersede_memory(old_memory.id, new_memory.id)
    if not success:
        print("Error: Failed to supersede memory")
        return 1

    print("Memory superseded successfully!")
    print()
    print(f"OLD (superseded): {old_memory.id[:8]}")
    old_preview = old_memory.content[:60].replace("\n", " ")
    print(f"  > {old_preview}...")
    print()
    print(f"NEW (supersedes): {new_memory.id[:8]}")
    new_preview = new_memory.content[:60].replace("\n", " ")
    print(f"  > {new_preview}...")
    print()
    print("The old memory will no longer load at session start.")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
