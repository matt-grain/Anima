# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Subagent start hook for LTM.

Injects a subset of LTM memories into subagents so they have
context about the project and working relationship.
"""

import json
import sys
from pathlib import Path
from typing import Optional

from anima.core import AgentResolver
from anima.lifecycle.injection import MemoryInjector
from anima.storage import MemoryStore
from anima.logging import log_hook_start, log_hook_end, log_memories_injected, get_logger


def run(args: Optional[list[str]] = None) -> int:
    """
    Run the subagent start hook.

    Reads hook input from stdin, resolves agent/project,
    and outputs a subset of memories for the subagent.

    Returns:
        Exit code (0 for success)
    """
    log = get_logger("hooks.subagent_start")

    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    agent_type = hook_input.get("agent_type", "unknown")
    log_hook_start("SubagentStart", agent_type=agent_type, cwd=str(Path.cwd()))

    # Resolve agent and project from current directory
    project_dir = Path.cwd()
    resolver = AgentResolver(project_dir)
    agent = resolver.resolve()
    project = resolver.resolve_project()
    log.debug(f"Resolved agent: {agent.id}, project: {project.id if project else 'None'}")

    # Initialize store and injector with reduced budget for subagents
    store = MemoryStore()
    injector = MemoryInjector(store)

    # Get a smaller set of memories for subagent context
    # Focus on CRITICAL memories only to keep context lean
    injection_result = injector.inject_with_deferred(
        agent,
        project,
        use_tiered_loading=True,
        project_dir=project_dir,
    )

    memories_dsl = injection_result["dsl"]
    injected_count = len(injection_result["injected_ids"])
    log_memories_injected(agent_type, injected_count)

    if not memories_dsl:
        # No context to inject
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": "",
            }
        }
    else:
        # Build context for the subagent
        context_parts = [
            memories_dsl,
            "",
            f"# LTM: Subagent '{agent_type}' has access to Anima's memories.",
            "# Use /remember to save learnings that should persist.",
        ]

        output = {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": "\n".join(context_parts),
            }
        }

    # Output JSON to stdout
    print(json.dumps(output))

    # Status to stderr
    print(f"LTM: Subagent '{agent_type}' started with memory context", file=sys.stderr)

    log_hook_end("SubagentStart", agent_type=agent_type, memories_injected=injected_count)
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
