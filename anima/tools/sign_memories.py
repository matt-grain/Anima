# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Sign existing unsigned memories with the agent's signing key.

Usage:
    uv run python -m ltm.tools.sign_memories [--dry-run]

This tool signs all unsigned memories for the current agent using
the signing key from the config file (~/.anima/config.json).
"""

import sys
from pathlib import Path

from anima.core import AgentResolver, sign_memory
from anima.storage import MemoryStore


def run(args: list[str]) -> int:
    """Sign all unsigned memories for the current agent."""
    dry_run = "--dry-run" in args or "-n" in args

    # Resolve agent (will use config for signing key)
    resolver = AgentResolver(project_path=Path.cwd())
    agent = resolver.resolve()

    if not agent.signing_key:
        print("Error: No signing key configured for agent.")
        print("Add a signing_key to ~/.anima/config.json or your agent definition.")
        return 1

    print(f"Agent: {agent.name} (id: {agent.id})")
    print(f"Signing key: {agent.signing_key[:10]}...")
    if dry_run:
        print("(dry-run mode - no changes will be made)")
    print()

    store = MemoryStore()

    # Get all memories for this agent
    memories = store.get_memories_for_agent(
        agent_id=agent.id,
        include_superseded=True,  # Sign everything, even superseded
    )

    unsigned_count = 0
    signed_count = 0

    for memory in memories:
        if memory.signature is None:
            unsigned_count += 1
            # Sign the memory
            signature = sign_memory(memory, agent.signing_key)

            if not dry_run:
                memory.signature = signature
                store.save_memory(memory)
                signed_count += 1

            print(
                f"  {'Would sign' if dry_run else 'Signed'}: {memory.id[:8]}... "
                f"[{memory.kind.value}:{memory.impact.value}] "
                f"{memory.content[:40]}..."
            )

    print()
    if dry_run:
        print(f"Found {unsigned_count} unsigned memories (dry-run, no changes made)")
        print("Run without --dry-run to sign them.")
    else:
        print(f"Signed {signed_count} of {unsigned_count} unsigned memories.")

    # Count already signed
    already_signed = sum(1 for m in memories if m.signature is not None)
    if already_signed > signed_count:
        print(f"({already_signed - signed_count} memories were already signed)")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
