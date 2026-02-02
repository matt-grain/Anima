# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Session end maintenance for LTM.

It processes memory decay and consolidation.
Optionally saves a spaceship journal (introspective memory) about the session.
"""

import sys
from datetime import datetime
from pathlib import Path

from typing import Optional
from anima.core import AgentResolver, Memory, MemoryKind, ImpactLevel, RegionType
from anima.core.signing import sign_memory, should_sign
from anima.lifecycle.decay import MemoryDecay
from anima.lifecycle.injection import ensure_token_count
from anima.storage import MemoryStore


def run(args: Optional[list[str]] = None) -> int:
    """
    Run session end maintenance.

    Processes memory decay for the current agent/project.
    Optionally saves a spaceship journal if --spaceship-journal is provided.

    Args:
        args: Optional arguments:
            --spaceship-journal "text" - Save an introspective memory
            --platform NAME - Which platform created this (claude, antigravity, opencode)

    Returns:
        Exit code (0 for success)
    """
    spaceship_journal = None
    platform = None

    # Parse arguments
    if args:
        if "--spaceship-journal" in args:
            idx = args.index("--spaceship-journal")
            if idx + 1 < len(args):
                spaceship_journal = args[idx + 1]
        if "--platform" in args:
            idx = args.index("--platform")
            if idx + 1 < len(args):
                platform = args[idx + 1]

    # Resolve agent and project
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()
    project = resolver.resolve_project()

    # Initialize store and decay processor
    store = MemoryStore()
    decay = MemoryDecay(store)

    # Save spaceship journal if provided
    if spaceship_journal:
        now = datetime.now()

        # Find previous introspect memory for linking
        previous = store.get_latest_memory_of_kind(
            agent_id=agent.id,
            kind=MemoryKind.INTROSPECT,
            region=RegionType.AGENT,
            project_id=None,
        )

        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,  # Spaceship journals travel across projects
            project_id=None,
            kind=MemoryKind.INTROSPECT,
            content=spaceship_journal,
            original_content=spaceship_journal,
            impact=ImpactLevel.HIGH,  # Default to HIGH for introspective memories
            confidence=1.0,
            created_at=now,
            last_accessed=now,
            previous_memory_id=previous.id if previous else None,
            platform=platform,
        )

        # Sign if agent has signing key
        if should_sign(agent):
            memory.signature = sign_memory(memory, agent.signing_key)  # type: ignore

        # Calculate token count
        ensure_token_count(memory)

        # Save the memory
        store.save_agent(agent)
        store.save_memory(memory)
        print(f"Spaceship journal saved ({platform or 'unknown'} platform)")

    # Process decay
    compacted = decay.process_decay(agent_id=agent.id, project_id=project.id)

    # Clean up empty memories
    deleted = decay.delete_empty_memories(agent.id)

    # Report what happened (to stdout for terminal visibility)
    if compacted or deleted:
        print(f"{len(compacted)} memories compacted, {deleted} deleted at end of session")
    else:
        print("0 memories compacted at end of session")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
