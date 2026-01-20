# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Utility functions for patching agent definition files.

These functions handle the detection and addition of the 'anima: subagent: true'
marker in agent YAML frontmatter to prevent local agents from shadowing the
primary Anima identity.
"""

import re


def has_subagent_marker(content: str) -> bool:
    """
    Check if content already has anima: subagent: true in frontmatter.

    Args:
        content: The full content of an agent definition file

    Returns:
        True if the subagent marker is present, False otherwise
    """
    # Find frontmatter block
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False

    frontmatter = match.group(1)

    # Check for anima or ltm section with subagent: true
    in_section = False
    for line in frontmatter.split("\n"):
        stripped = line.strip()

        if stripped in ("anima:", "ltm:"):
            in_section = True
            continue

        if in_section:
            # Check if we've left the section (no indent)
            if stripped and not line.startswith(" ") and not line.startswith("\t"):
                in_section = False
                continue

            if "subagent:" in stripped:
                value = stripped.split(":", 1)[1].strip().lower()
                return value in ("true", "yes", "1")

    return False


def add_subagent_marker(content: str) -> str:
    """
    Add anima: subagent: true to frontmatter before closing ---.

    This function handles both Unix (\n) and Windows (\r\n) line endings.

    Args:
        content: The full content of an agent definition file

    Returns:
        Modified content with the subagent marker added, or original content
        if frontmatter structure is not recognized
    """
    if content.startswith("---\n"):
        end_idx = content.find("\n---", 4)
        if end_idx != -1:
            return content[:end_idx] + "\nanima:\n  subagent: true" + content[end_idx:]
    elif content.startswith("---\r\n"):
        end_idx = content.find("\r\n---", 5)
        if end_idx != -1:
            return content[:end_idx] + "\r\nanima:\r\n  subagent: true" + content[end_idx:]
    return content
