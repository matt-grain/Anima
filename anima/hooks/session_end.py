# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Session end maintenance for LTM.

It processes memory decay and consolidation.
"""

import sys
from pathlib import Path

from typing import Optional
from anima.core import AgentResolver
from anima.lifecycle.decay import MemoryDecay
from anima.storage import MemoryStore


def run(args: Optional[list[str]] = None) -> int:
    """
    Run session end maintenance.

    Processes memory decay for the current agent/project.

    Returns:
        Exit code (0 for success)
    """
    # Resolve agent and project
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()
    project = resolver.resolve_project()

    # Initialize decay processor
    store = MemoryStore()
    decay = MemoryDecay(store)

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
    sys.exit(run())
