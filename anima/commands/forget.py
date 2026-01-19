# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/forget command - Mark a memory for removal.

Memories are append-only, so "forgetting" creates a superseding record
with reduced confidence, rather than deleting.
"""

import sys
from datetime import datetime
from pathlib import Path

from anima.core import Memory, AgentResolver
from anima.lifecycle.injection import ensure_token_count
from anima.storage import MemoryStore


def run(args: list[str]) -> int:
    """
    Run the forget command.

    Args:
        args: Memory ID (or partial ID) to forget

    Returns:
        Exit code (0 for success)
    """
    if not args:
        print("Usage: uv run anima forget <memory-id>")
        print("Example: uv run anima forget fa8382cf")
        print("\nUse 'uv run anima memories' to see memory IDs")
        return 1

    memory_id_prefix = args[0]

    # Resolve agent
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()

    store = MemoryStore()

    # Find memory by ID prefix
    memories = store.get_memories_for_agent(agent_id=agent.id, include_superseded=False)

    matching = [m for m in memories if m.id.startswith(memory_id_prefix)]

    if not matching:
        print(f"No memory found with ID starting with '{memory_id_prefix}'")
        return 1

    if len(matching) > 1:
        print(f"Multiple memories match '{memory_id_prefix}':")
        for m in matching:
            print(f"  {m.id[:8]}: {m.content[:50]}...")
        print("\nPlease provide a more specific ID")
        return 1

    memory = matching[0]

    # Create a correction memory that supersedes this one
    now = datetime.now()
    correction = Memory(
        agent_id=memory.agent_id,
        region=memory.region,
        project_id=memory.project_id,
        kind=memory.kind,
        content=f"[FORGOTTEN] {memory.content[:50]}...",
        original_content=f"Correction: User requested to forget memory {memory.id}",
        impact=memory.impact,
        confidence=0.0,  # Zero confidence = forgotten
        created_at=now,
        last_accessed=now,
        previous_memory_id=memory.id,
        version=1,
    )

    # Save the correction and mark old memory as superseded
    ensure_token_count(correction)
    store.save_memory(correction)
    store.supersede_memory(memory.id, correction.id)

    print(f"Memory marked for removal: {memory.id[:8]}")
    print(f"Content: {memory.content[:60]}...")
    print("\n(Memories are append-only - a correction note was added)")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
