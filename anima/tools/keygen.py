# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Generate signing key for an agent."""

import re
import secrets
import sys
from pathlib import Path
from typing import Optional

from anima.storage import MemoryStore


def generate_key(length: int = 32) -> str:
    """Generate a cryptographically secure random key."""
    return secrets.token_hex(length)


def find_agent_file(agent_id: str) -> tuple[Optional[Path], bool]:
    """
    Find agent definition file.

    Checks in order:
    1. .agent/agents/{agent}.md (project-local)
    2. ~/.agent/agents/{agent}.md (user-global)
    3. Legacy .claude/agents/ paths

    Returns:
        Tuple of (path or None, is_global)
    """
    # Check project-local
    local_dirs = [Path.cwd() / ".agent" / "agents", Path.cwd() / ".claude" / "agents"]
    for d in local_dirs:
        local_file = d / f"{agent_id}.md"
        if local_file.exists():
            return local_file, False

    # Check user-global
    global_dirs = [
        Path.home() / ".agent" / "agents",
        Path.home() / ".claude" / "agents",
    ]
    for d in global_dirs:
        global_file = d / f"{agent_id}.md"
        if global_file.exists():
            return global_file, True

    return None, False


def get_key_from_agent_file(agent_file: Path) -> Optional[str]:
    """Extract signing_key from agent frontmatter (any format)."""
    content = agent_file.read_text()
    if not content.startswith("---"):
        return None

    # Find signing_key in frontmatter (works for both LTM and Claude formats)
    match = re.search(r'signing_key:\s*["\']?([^"\'\n]+)["\']?', content)
    if match:
        return match.group(1).strip()
    return None


def add_key_to_agent_file(agent_file: Path, key: str) -> None:
    """
    Add signing_key to existing agent markdown file.

    Handles both Claude Code format and LTM format frontmatter.
    """
    content = agent_file.read_text()

    if not content.startswith("---"):
        raise ValueError(f"Agent file {agent_file} has no frontmatter")

    # Find end of frontmatter
    end_match = re.search(r"\n---\n", content[3:])
    if not end_match:
        raise ValueError(f"Agent file {agent_file} has malformed frontmatter")

    frontmatter_end = end_match.end() + 3
    frontmatter = content[:frontmatter_end]
    rest = content[frontmatter_end:]

    # Add signing_key before the closing ---
    # Insert it as a top-level key in the frontmatter
    new_frontmatter = frontmatter.rstrip()
    if new_frontmatter.endswith("---"):
        new_frontmatter = new_frontmatter[:-3].rstrip()
    new_frontmatter += f'\nsigning_key: "{key}"\n---\n'

    agent_file.write_text(new_frontmatter + rest)


def run(args: list[str]) -> int:
    """
    Generate and save a signing key for an existing Anima agent.

    Usage: uv run anima keygen <agent_name>

    Looks for agent file in local and global directories.
    The agent file must already exist.
    Use 'uv run anima import-seeds' for the default Anima agent.
    """
    # Parse args
    if not args or args[0].startswith("-"):
        print("Usage: uv run anima keygen <agent_name>")
        print("")
        print("Add a signing key to an existing Anima agent.")
        print("")
        print("The agent file must exist in:")
        print("  .agent/agents/<agent>.md")
        print("  ~/.agent/agents/<agent>.md")
        print("")
        print("For the default Anima agent, use: uv run anima import-seeds")
        return 1

    agent_name = args[0]
    agent_id = agent_name.lower()
    agent_display = agent_name

    # Find the agent file
    agent_file, is_global = find_agent_file(agent_id)

    if not agent_file:
        print(f"❌ Agent '{agent_name}' not found.")
        print("")
        print("Looked in:")
        print(f"  {Path.cwd() / '.claude' / 'agents' / f'{agent_id}.md'}")
        print(f"  {Path.home() / '.claude' / 'agents' / f'{agent_id}.md'}")
        print("")
        print("Create the agent file first, then run keygen.")
        return 1

    # Check if key already exists
    existing_key = get_key_from_agent_file(agent_file)
    if existing_key:
        print(f"⚠️  Agent '{agent_display}' already has a signing key in:")
        print(f"   {agent_file}")
        print("   To regenerate, remove 'signing_key' from that file first.")
        return 1

    # Generate and add key
    key = generate_key()
    add_key_to_agent_file(agent_file, key)

    location = "global" if is_global else "project"
    print(f"✓ Generated signing key for agent '{agent_display}'")
    print(f"  Added to: {agent_file} ({location})")

    # Also update agent in database
    store = MemoryStore()
    agent = store.get_agent(agent_id)
    if agent:
        agent.signing_key = key
        store.save_agent(agent)
        print("  Updated agent in database")
    else:
        from anima.core import Agent

        agent = Agent(
            id=agent_id,
            name=agent_display,
            signing_key=key,
        )
        store.save_agent(agent)
        print("  Created agent in database")

    # Sign any existing unsigned memories for this agent
    from anima.core import sign_memory

    memories = store.get_memories_for_agent(agent_id=agent_id, include_superseded=True)
    unsigned = [m for m in memories if m.signature is None]

    if unsigned:
        print("")
        print(f"Signing {len(unsigned)} existing memories...")
        for memory in unsigned:
            memory.signature = sign_memory(memory, key)
            store.save_memory(memory)
        print(f"  ✓ Signed {len(unsigned)} memories")

    print("")
    print("🔐 Done! All memories are now signed.")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
