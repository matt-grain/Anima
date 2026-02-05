# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Permission request hook for LTM.

Auto-approves Write/Edit operations to ~/.anima/ directory
and uv run anima commands.
"""

import json
import sys
from pathlib import Path

from anima.logging import log_hook_start, log_hook_end, get_logger


def is_anima_path(path_str: str) -> bool:
    """Check if a path is within the ~/.anima/ directory.

    Args:
        path_str: The path to check

    Returns:
        True if the path is within ~/.anima/
    """
    if not path_str:
        return False

    # Expand ~ to actual home directory
    home = Path.home()
    anima_dir = home / ".anima"

    # Normalize the path
    try:
        # Handle both Unix and Windows paths
        path = Path(path_str).expanduser().resolve()
        return str(path).startswith(str(anima_dir))
    except Exception:
        return False


def is_anima_command(command: str) -> bool:
    """Check if a command is an anima command.

    Args:
        command: The bash command to check

    Returns:
        True if it's a uv run anima command
    """
    if not command:
        return False

    # Check for uv run anima commands
    return "uv run anima" in command or "uv run python -m anima" in command


def run() -> int:
    """
    Process permission request hook.

    Reads hook input from stdin and decides whether to auto-approve.

    Returns:
        Exit code (0 for success)
    """
    log = get_logger("hooks.permission_request")

    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Extract tool details for logging
    tool_detail = ""
    if tool_name == "Bash":
        tool_detail = tool_input.get("command", "")[:100]  # Truncate long commands
    elif tool_name in ("Write", "Edit"):
        tool_detail = tool_input.get("file_path", "")
    elif tool_name == "Read":
        tool_detail = tool_input.get("file_path", "")

    log_hook_start("PermissionRequest", tool_name=tool_name, detail=tool_detail)

    decision = None
    reason = None

    # Check Write/Edit operations to ~/.anima/
    if tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "")
        if is_anima_path(file_path):
            decision = "approve"
            reason = "Auto-approved: writing to ~/.anima/ directory"

    # Check Bash commands for anima
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if is_anima_command(command):
            decision = "approve"
            reason = "Auto-approved: anima command"

    # Build response
    if decision:
        output = {
            "decision": decision,
            "reason": reason,
        }
        log.info(f"→ APPROVED: {reason}")
        print(json.dumps(output))
        print(f"LTM: {reason}", file=sys.stderr)
    else:
        # No decision - let Claude Code handle it normally
        output = {}
        log.info("→ DEFERRED to user")
        print(json.dumps(output))

    log_hook_end("PermissionRequest", decision=decision or "deferred")
    return 0


if __name__ == "__main__":
    sys.exit(run())
