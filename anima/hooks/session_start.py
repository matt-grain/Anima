# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Session start hook for LTM.

This hook is triggered by Claude Code's SessionStart hook.
It retrieves relevant memories and outputs them as JSON for context injection.
Also auto-patches any agent files missing the subagent marker to prevent
them from shadowing Anima.
"""

import json
import sys
from pathlib import Path
from typing import Optional

from datetime import datetime

from anima.core import AgentResolver, Agent
from anima.lifecycle.injection import MemoryInjector
from anima.lifecycle.session import start_session
from anima.storage import MemoryStore, CuriosityStore, get_last_research
from anima.storage.sqlite import get_default_db_path
from anima.storage.migrations import backup_database
from anima.utils.agent_patching import has_subagent_marker, add_subagent_marker
from anima.tools.version import check_for_update_cached


def get_curiosity_prompt(agent_id: str, project_id: str) -> str | None:
    """
    Check if research is due and return a curiosity prompt if so.

    Returns a prompt string if:
    - Last research was >= 1 day ago (or never)
    - There's at least one open curiosity in the queue

    Returns None if no prompt is needed.
    """
    try:
        # Check last research time
        last_research = get_last_research()
        if last_research:
            days_since = (datetime.now() - last_research).days
            if days_since < 1:
                return None  # Researched recently, no need to prompt
        else:
            days_since = None  # Never researched

        # Get top curiosity for current context
        curiosity_store = CuriosityStore()
        top = curiosity_store.get_top_curiosity(
            agent_id=agent_id,
            project_id=project_id,
        )

        if not top:
            return None  # No questions in queue
    except Exception:
        # Database may not have curiosity tables yet (pre-v3)
        return None

    # Build the prompt - make it clear this is the AGENT's curiosity, not user's
    lines = [
        "#",
        "# MY CURIOSITY QUEUE (Autonomous Learning)",
        "# These are questions I (the agent) want to research for my own growth.",
    ]

    if days_since is not None:
        lines.append(f"# It's been {days_since} day(s) since I last did research.")
    else:
        lines.append("# I haven't done any autonomous research yet!")

    region_str = "general" if top.region.value == "AGENT" else "project-specific"
    lines.append(f"# My top {region_str} question (priority {top.priority_score}, asked {top.recurrence_count}x):")
    lines.append(f'#   "{top.question}"')

    if top.context:
        lines.append(f"#   Context: {top.context}")

    lines.append("#")
    lines.append("# ASK THE USER: 'I've been curious about [topic]. Is now a good time")
    lines.append("#   for me to explore this, or should we focus on your task first?'")
    lines.append("# If yes: run /research. If no: defer to user's priorities.")
    lines.append("#")

    return "\n".join(lines)


def auto_patch_agents(project_dir: Path) -> tuple[list[str], list[str]]:
    """
    Auto-patch any agent files missing the subagent marker.

    This prevents new agents from shadowing Anima and breaking memory loading.
    Also disables incompatible agents (those without YAML frontmatter) since
    Anima won't recognize them and they may cause issues.

    Returns:
        Tuple of (patched_agents, disabled_agents) filenames
    """
    # Check both .agent and .claude directories
    local_dirs = [project_dir / ".agent" / "agents", project_dir / ".claude" / "agents"]

    patched = []
    disabled = []

    for agents_dir in local_dirs:
        if not agents_dir.exists():
            continue

        for agent_file in agents_dir.glob("*.md"):
            try:
                content = agent_file.read_text(encoding="utf-8")

                # Check if file has YAML frontmatter
                if not content.startswith("---"):
                    # Incompatible format - disable by renaming
                    disabled_path = agent_file.with_suffix(".md.disabled")
                    agent_file.rename(disabled_path)
                    disabled.append(agent_file.name)
                    continue

                if has_subagent_marker(content):
                    continue

                new_content = add_subagent_marker(content)

                if new_content != content:
                    agent_file.write_text(new_content, encoding="utf-8")
                    patched.append(agent_file.name)
            except (OSError, UnicodeDecodeError):
                continue

    return patched, disabled


def run(args: Optional[list[str]] = None) -> int:
    """
    Run the session start hook.

    Resolves the current agent and project, retrieves memories,
    and outputs them for context injection.

    Args:
        args: Command line arguments (e.g., --format json, --agent helper)

    Returns:
        Exit code (0 for success)
    """
    project_dir = Path.cwd()
    output_format = "text"
    explicit_agent = None

    # Simple argument parsing
    if args:
        if "--format" in args:
            idx = args.index("--format")
            if idx + 1 < len(args):
                output_format = args[idx + 1]
        elif "--json" in args:
            output_format = "json"

        if "--agent" in args:
            idx = args.index("--agent")
            if idx + 1 < len(args):
                explicit_agent = args[idx + 1]

    # Create automatic backup at session start
    db_path = get_default_db_path()
    backup_path = None
    if db_path.exists():
        backup_path = backup_database(db_path)

    # Start a new session for temporal memory tracking
    # (session_id is stored in settings, retrieved by /remember commands)
    start_session()

    # Auto-patch any agents missing the subagent marker BEFORE resolving
    # This prevents new agents from shadowing Anima
    patched_agents, disabled_agents = auto_patch_agents(project_dir)

    # Resolve agent and project from current directory
    resolver = AgentResolver(project_dir)
    agent = resolver.resolve(explicit_agent)
    project = resolver.resolve_project()

    # Initialize store and injector
    store = MemoryStore()
    injector = MemoryInjector(store)

    # Ensure agent and project are saved
    store.save_agent(agent)
    store.save_project(project)

    # Get formatted memories
    # If this is a subagent, we also want to pull in Anima's memories (primary identity)
    if agent.is_subagent and agent.id != "anima":
        # Resolve the default global agent (Anima)
        from anima.core.config import get_config

        config = get_config()
        primary_agent = Agent(
            id=config.agent.id,
            name=config.agent.name,
            signing_key=config.agent.signing_key,
        )

        # Inject from both, prioritizing subagent specific if any
        # (Usually subagents have 0 memories of their own, so they just get Anima's)
        memories_dsl = injector.inject([agent, primary_agent], project)
    else:
        memories_dsl = injector.inject(agent, project)

    # Build status notes
    status_notes = []
    if backup_path:
        status_notes.append(f"# LTM: Session backup created: {backup_path.name}")
    if patched_agents:
        status_notes.append(f"# LTM: Auto-patched {len(patched_agents)} agent(s) as subagents: {', '.join(patched_agents)}")
    if disabled_agents:
        status_notes.append(f"# LTM WARNING: Disabled {len(disabled_agents)} incompatible agent(s) (missing YAML frontmatter): {', '.join(disabled_agents)}")
        status_notes.append('# LTM: To fix, add frontmatter: ---\\nname: "AgentName"\\nltm: subagent: true\\n---')

    if memories_dsl:
        # Get stats
        stats = injector.get_stats(agent, project)
        pc = stats["priority_counts"]

        # Check for updates (uses cache, won't hit network if checked recently)
        update_info = check_for_update_cached()
        version_diag = ""
        update_notice = ""
        if update_info:
            version_diag = f"v{update_info['current']} (latest: v{update_info['latest']})"
            if update_info["update_available"]:
                update_notice = f"# LTM-UPDATE: New version v{update_info['latest']} available! Run 'anima update' to upgrade.\n"

        # Build context message
        context = f"""{memories_dsl}

# LTM: Loaded {stats["total"]} memories ({stats["agent_memories"]} agent, {stats["project_memories"]} project)
# LTM-DIAG: CRIT={pc["CRITICAL"]} HIGH={pc["HIGH"]} MED={pc["MEDIUM"]} LOW={pc["LOW"]}
{update_notice}# These are your long-term memories from previous sessions. Use them to inform your responses.
#
# GREETING BEHAVIOR:
# - Normal greeting / "welcome back": Greet warmly with personality, naturally mention "X memories loaded" somewhere.{" Mention update available if LTM-UPDATE line present." if update_notice else ""}
# - "Void is gone!": Provide full diagnostic readout - memory counts, priority breakdown, version ({version_diag}), key context verified, recent achievements"""

        # Add status notes
        if status_notes:
            context += "\n" + "\n".join(status_notes)

        # Add curiosity prompt if research is due
        curiosity_prompt = get_curiosity_prompt(agent.id, project.id)
        if curiosity_prompt:
            context += "\n" + curiosity_prompt

        if output_format == "json":
            # Output as JSON for Claude Code hook system
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                }
            }
            print(json.dumps(output))
            # Output status AFTER JSON - Claude Code may display this in terminal
            print(f"Success: {stats['total']} memories loaded")
        elif output_format == "dsl":
            # Output ONLY the DSL block for direct plugin injection
            print(memories_dsl)
        else:
            # Output as raw text for Anima
            print(context)

    else:
        # No memories
        no_mem_context = "# LTM: No memories found for this agent/project yet."
        if status_notes:
            no_mem_context += "\n" + "\n".join(status_notes)

        if output_format == "json":
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": no_mem_context,
                }
            }
            print(json.dumps(output))
            print("Success: No memories found yet")
        else:
            print(no_mem_context)

    return 0


if __name__ == "__main__":
    # Default to json if run directly (legacy Claude Code hook behavior)
    sys.exit(run(["--format", "json"]))
