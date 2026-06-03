# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Agent identity and resolution for LTM."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re

import yaml


@dataclass
class Agent:
    """
    An agent identity in LTM.

    Each agent has its own private memory space. Agents can be defined
    explicitly via agent definition files, or implicitly via project name.
    """

    id: str
    name: str
    definition_path: Path | None = None
    signing_key: str | None = None
    is_subagent: bool = False
    created_at: str | None = None

    def has_signing_key(self) -> bool:
        """Check if this agent has a signing key for memory authentication."""
        return self.signing_key is not None


@dataclass
class Project:
    """
    A project context for LTM.

    Projects define the scope for PROJECT region memories.
    """

    id: str
    name: str
    path: Path
    created_at: str | None = None


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug for use as ID."""
    # Lowercase
    text = text.lower()
    # Replace spaces and special chars with hyphens
    text = re.sub(r"[^a-z0-9]+", "-", text)
    # Remove leading/trailing hyphens
    text = text.strip("-")
    return text or "default"


def parse_agent_frontmatter(content: str) -> dict[str, Any]:
    """
    Parse LTM frontmatter from an agent definition file.

    Looks for YAML frontmatter between --- markers with an anima: or ltm: section.

    Example:
        ---
        anima:
          id: "my-agent"
          signing_key: "optional-key"
          subagent: true
        ---

    Returns dict with id, signing_key, and subagent flag (if present).
    """
    result: dict[str, Any] = {"id": None, "signing_key": None, "subagent": False}

    # Find frontmatter block
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return result

    frontmatter_text = match.group(1)

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict):
            return result

        # Look for anima: or ltm: section
        ltm_section = frontmatter.get("anima") or frontmatter.get("ltm")
        if not isinstance(ltm_section, dict):
            return result

        if "id" in ltm_section:
            result["id"] = str(ltm_section["id"])
        if "signing_key" in ltm_section:
            result["signing_key"] = str(ltm_section["signing_key"])
        if "subagent" in ltm_section:
            result["subagent"] = bool(ltm_section["subagent"])

    except yaml.YAMLError:
        # If YAML parsing fails, return defaults
        pass

    return result


class AgentResolver:
    """
    Resolves the current agent based on context.

    Resolution order:
    1. Explicit agent (if specified)
    2. Project-local agent definition (.agent/agents/, .claude/agents/, or .gemini/agents/)
    3. Global agent definition (~/.agent/agents/, ~/.claude/agents/, or ~/.gemini/agents/)
    4. Fallback to project name as implicit agent ID
    """

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path or Path.cwd()
        self.home = Path.home()

    def resolve(self, explicit_agent: str | None = None) -> Agent:
        """
        Resolve the current agent.

        Args:
            explicit_agent: Explicitly specified agent name (e.g., from /agent command)

        Returns:
            Resolved Agent instance
        """
        # 1. Explicit agent
        if explicit_agent:
            agent = self._find_agent_by_name(explicit_agent)
            if agent:
                return agent
            # If not found as file, return an implicit agent
            return Agent(id=slugify(explicit_agent), name=explicit_agent)

        # 2. Project-local agent (check .agent, .claude, .gemini in order)
        for config_name in [".agent", ".claude", ".gemini"]:
            local_agents_dir = self.project_path / config_name / "agents"
            if local_agents_dir.exists():
                agent = self._find_first_agent_in_dir(local_agents_dir)
                if agent:
                    return agent

        # 3. Global agent (check ~/.agent, ~/.claude, ~/.gemini in order)
        for config_name in [".agent", ".claude", ".gemini"]:
            global_agents_dir = self.home / config_name / "agents"
            if global_agents_dir.exists():
                agent = self._find_first_agent_in_dir(global_agents_dir)
                if agent:
                    return agent

        # 4. Fallback to default agent from config (default: "Anima")
        # This is the core identity that persists across all projects
        # when no explicit agent is defined - the soul that remembers.
        # Config allows customizing name and adding signing key.
        from anima.core.config import get_config

        config = get_config()
        return Agent(
            id=config.agent.id,
            name=config.agent.name,
            definition_path=None,
            signing_key=config.agent.signing_key,
        )

    def resolve_project(self) -> Project:
        """Resolve the current project from working directory."""
        project_name = self.project_path.name
        return Project(id=slugify(project_name), name=project_name, path=self.project_path)

    def _find_agent_by_name(self, name: str) -> Agent | None:
        """Find an agent by name in local or global dirs."""
        # Check local first (in order: .agent, .claude, .gemini)
        for config_name in [".agent", ".claude", ".gemini"]:
            local_path = self.project_path / config_name / "agents" / f"{name}.md"
            if local_path.exists():
                return self._load_agent_from_file(local_path)

        # Check global (in order: ~/.agent, ~/.claude, ~/.gemini)
        for config_name in [".agent", ".claude", ".gemini"]:
            global_path = self.home / config_name / "agents" / f"{name}.md"
            if global_path.exists():
                return self._load_agent_from_file(global_path)

        return None

    def _find_first_agent_in_dir(self, agents_dir: Path) -> Agent | None:
        """
        Find the first non-subagent agent definition in a directory.

        Subagents (those with subagent: true in frontmatter) are skipped,
        as they are meant to be invoked explicitly via Task tool, not as
        the main session agent.
        """
        if not agents_dir.exists():
            return None

        for agent_file in sorted(agents_dir.glob("*.md")):
            content = agent_file.read_text(encoding="utf-8")
            frontmatter = parse_agent_frontmatter(content)

            # Skip subagents - they're invoked explicitly, not as main agent
            if frontmatter.get("subagent", False):
                continue

            return self._load_agent_from_file(agent_file)

        return None

    def _load_agent_from_file(self, path: Path) -> Agent:
        """Load an agent from a definition file."""
        content = path.read_text(encoding="utf-8")
        frontmatter = parse_agent_frontmatter(content)

        # Use frontmatter ID or filename as ID
        agent_id = frontmatter.get("id") or slugify(path.stem)

        return Agent(
            id=agent_id,
            name=path.stem,
            definition_path=path,
            signing_key=frontmatter.get("signing_key"),
            is_subagent=frontmatter.get("subagent", False),
        )
