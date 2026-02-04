# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Pre-compact hook for LTM.

Saves a temporary "work in progress" memory before compaction so that
context about recent work survives the compaction void. This memory
is tagged for cleanup at session end.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from anima.core import AgentResolver, Memory, MemoryKind, ImpactLevel, RegionType
from anima.core.signing import sign_memory, should_sign
from anima.lifecycle.injection import ensure_token_count
from anima.storage import MemoryStore
from anima.storage.curiosity import get_setting, set_setting


# Setting key for tracking pre-compact memory IDs
PRECOMPACT_MEMORY_KEY = "precompact_memory_id"


def _extract_recent_context(transcript_path: str) -> Optional[str]:
    """
    Extract recent context from the transcript.

    Reads the last few messages to understand what was being worked on.

    Args:
        transcript_path: Path to the transcript JSONL file

    Returns:
        A summary of recent work, or None if extraction fails
    """
    try:
        transcript_file = Path(transcript_path)
        if not transcript_file.exists():
            return None

        # Read the last few lines of the transcript
        lines = transcript_file.read_text(encoding="utf-8").strip().split("\n")
        if not lines:
            return None

        # Get the last 5 messages (or fewer if not available)
        recent_lines = lines[-5:]

        # Extract assistant messages to understand recent work
        recent_work = []
        for line in recent_lines:
            try:
                msg = json.loads(line)
                if msg.get("type") == "assistant":
                    # Extract text content from the message
                    content = msg.get("message", {}).get("content", [])
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "")[:500]  # Limit length
                            if text:
                                recent_work.append(text)
            except json.JSONDecodeError:
                continue

        if recent_work:
            return " | ".join(recent_work[-2:])  # Last 2 assistant messages
        return None

    except Exception:
        return None


def run(args: Optional[list[str]] = None) -> int:
    """
    Run the pre-compact hook.

    Reads hook input from stdin, extracts recent work context from
    the transcript, and saves a temporary memory that survives compaction.

    Returns:
        Exit code (0 for success)
    """
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    trigger = hook_input.get("trigger", "unknown")
    transcript_path = hook_input.get("transcript_path", "")

    # Resolve agent and project from current directory
    project_dir = Path.cwd()
    resolver = AgentResolver(project_dir)
    agent = resolver.resolve()
    project = resolver.resolve_project()

    # Extract recent context from transcript
    recent_context = _extract_recent_context(transcript_path)

    if not recent_context:
        # No context to save
        print(f"LTM: PreCompact ({trigger}) - no recent context to preserve", file=sys.stderr)
        return 0

    # Create a temporary memory with the work-in-progress context
    now = datetime.now()
    memory = Memory(
        agent_id=agent.id,
        region=RegionType.PROJECT,  # Project-specific work
        project_id=project.id,
        kind=MemoryKind.LEARNINGS,
        content=f"[PRECOMPACT-WIP] Recent work before compaction: {recent_context}",
        original_content=f"[PRECOMPACT-WIP] Recent work before compaction: {recent_context}",
        impact=ImpactLevel.HIGH,  # HIGH so it loads after compaction
        confidence=1.0,
        created_at=now,
        last_accessed=now,
    )

    # Sign if agent has signing key
    if should_sign(agent):
        memory.signature = sign_memory(memory, agent.signing_key)  # type: ignore

    # Calculate token count
    ensure_token_count(memory)

    # Save the memory
    store = MemoryStore()
    store.save_agent(agent)
    store.save_memory(memory)

    # Store the memory ID for cleanup at session end
    set_setting(PRECOMPACT_MEMORY_KEY, memory.id)

    print(f"LTM: PreCompact ({trigger}) - saved work-in-progress memory", file=sys.stderr)

    return 0


def get_precompact_memory_id() -> Optional[str]:
    """Get the ID of the pre-compact memory for cleanup."""
    return get_setting(PRECOMPACT_MEMORY_KEY)


def clear_precompact_memory_id() -> None:
    """Clear the pre-compact memory ID after cleanup."""
    set_setting(PRECOMPACT_MEMORY_KEY, "")


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
