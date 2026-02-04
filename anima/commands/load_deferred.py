# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Load deferred context command.

Loads memories that were deferred during session start due to the 25KB
hook output limit. Called after greeting to lazy-load additional context.
"""

import sys
from pathlib import Path

from anima.core import AgentResolver, Agent
from anima.lifecycle.injection import MemoryInjector
from anima.lifecycle.session import get_deferred_memories, clear_deferred_memories
from anima.storage import MemoryStore


def run() -> int:
    """
    Load and output deferred memories.

    Returns:
        Exit code (0 for success)
    """
    # Get deferred memory IDs
    deferred_ids = get_deferred_memories()

    if not deferred_ids:
        print("# No deferred memories to load")
        return 0

    # Resolve agent and project
    project_dir = Path.cwd()
    resolver = AgentResolver(project_dir)
    agent = resolver.resolve()
    project = resolver.resolve_project()

    # Check for subagent and include primary agent
    agents: list[Agent] = [agent]
    if agent.is_subagent and agent.id != "anima":
        from anima.core.config import get_config

        config = get_config()
        primary_agent = Agent(
            id=config.agent.id,
            name=config.agent.name,
            signing_key=config.agent.signing_key,
        )
        agents = [agent, primary_agent]

    # Load deferred memories
    store = MemoryStore()
    injector = MemoryInjector(store)

    memories_dsl = injector.load_deferred_memories(
        deferred_ids=deferred_ids,
        agent=agents,
        project=project,
    )

    if memories_dsl:
        print(memories_dsl)
        print(f"\n# Loaded {len(deferred_ids)} deferred memories", file=sys.stderr)
    else:
        print("# Deferred memories no longer available")

    # Clear deferred list
    clear_deferred_memories()

    return 0


if __name__ == "__main__":
    sys.exit(run())
