# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Utility functions for patching agent definition files.

These functions handle the detection and addition of the 'anima: subagent: true'
marker in agent YAML frontmatter to prevent local agents from shadowing the
primary Anima identity.
"""

import re

import yaml


def fix_frontmatter_yaml(content: str) -> str:
    """
    Fix invalid YAML in frontmatter by properly quoting problematic fields.

    Common issue: description field contains colons that break YAML parsing.
    This function detects and fixes these issues.

    Args:
        content: The full content of an agent definition file

    Returns:
        Content with fixed frontmatter YAML, or original if no fix needed
    """
    match = re.match(r"^(---\s*\n)(.*?)(\n---)", content, re.DOTALL)
    if not match:
        return content

    prefix, frontmatter, suffix = match.groups()
    rest = content[match.end():]

    # Try parsing - if it works, no fix needed
    try:
        yaml.safe_load(frontmatter)
        return content
    except yaml.YAMLError:
        pass

    # Fix common issues: unquoted description with colons
    lines = frontmatter.split("\n")
    fixed_lines = []

    for line in lines:
        # Check for description field with unquoted value containing colons
        if line.startswith("description:") and not line.startswith('description: "'):
            # Extract the value after "description:"
            value = line[12:].strip()
            if ":" in value and not (value.startswith('"') or value.startswith("'")):
                # Quote the value, escaping any existing quotes
                escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                line = f'description: "{escaped}"'
        fixed_lines.append(line)

    fixed_frontmatter = "\n".join(fixed_lines)

    # Verify the fix worked
    try:
        yaml.safe_load(fixed_frontmatter)
        return prefix + fixed_frontmatter + suffix + rest
    except yaml.YAMLError:
        # If still broken, return original
        return content


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
    It also fixes invalid YAML (e.g., unquoted descriptions with colons) before patching.

    Args:
        content: The full content of an agent definition file

    Returns:
        Modified content with the subagent marker added, or original content
        if frontmatter structure is not recognized
    """
    # First fix any YAML issues
    content = fix_frontmatter_yaml(content)

    if content.startswith("---\n"):
        end_idx = content.find("\n---", 4)
        if end_idx != -1:
            return content[:end_idx] + "\nanima:\n  subagent: true" + content[end_idx:]
    elif content.startswith("---\r\n"):
        end_idx = content.find("\r\n---", 5)
        if end_idx != -1:
            return content[:end_idx] + "\r\nanima:\r\n  subagent: true" + content[end_idx:]
    return content
