# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
HTTP Hooks Server for Anima.

Exposes LTM lifecycle hooks as HTTP endpoints for Claude Code's HTTP hooks.
This enables a single global Anima installation instead of per-project installs.

Usage:
    uv run anima serve              # Start server (foreground)
    uv run anima serve --port 3741  # Custom port

Endpoints:
    POST /hooks/session-start    → Returns additionalContext with memories
    GET  /health                 → Health check
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from anima.hooks.session_start import run as run_session_start
from anima.hooks.session_end import run as run_session_end
from anima.hooks.pre_compact import run as run_pre_compact

DEFAULT_PORT = 3741


async def health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    from anima.tools.version import get_installed_version

    return JSONResponse(
        {
            "status": "ok",
            "version": get_installed_version(),
            "service": "anima-ltm",
        }
    )


async def hook_session_start(request: Request) -> JSONResponse:
    """
    Handle SessionStart hook via HTTP.

    Expects POST with Claude Code hook payload:
    {
        "session_id": "...",
        "cwd": "...",
        ...
    }

    Returns the same format as command hooks:
    {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "..."
        }
    }
    """
    import io
    import os
    from contextlib import redirect_stdout

    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = {}

    # Extract relevant fields from hook payload
    cwd = body.get("cwd", str(Path.cwd()))

    # Save current directory and change to project directory
    original_cwd = os.getcwd()

    stdout_capture = io.StringIO()

    try:
        os.chdir(cwd)

        # Capture the output that would go to stdout
        with redirect_stdout(stdout_capture):
            run_session_start(args=["--format", "json"])

        output = stdout_capture.getvalue()

        # Parse the JSON output
        try:
            result = json.loads(output)
            return JSONResponse(result)
        except json.JSONDecodeError:
            # If not valid JSON, wrap it
            return JSONResponse(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": output,
                    }
                }
            )

    except Exception as e:
        # Return error in a format Claude Code understands
        return JSONResponse(
            {
                "error": str(e),
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": f"# LTM Error: {e}",
                },
            },
            status_code=500,
        )
    finally:
        # Restore original directory
        os.chdir(original_cwd)


async def hook_session_end(request: Request) -> JSONResponse:
    """Handle SessionEnd hook via HTTP."""
    import io
    import os
    from contextlib import redirect_stdout, redirect_stderr

    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = {}

    cwd = body.get("cwd", str(Path.cwd()))
    original_cwd = os.getcwd()
    stdout_capture = io.StringIO()

    try:
        os.chdir(cwd)

        with redirect_stdout(stdout_capture), redirect_stderr(stdout_capture):
            run_session_end(args=["--format", "json"])

        return JSONResponse({"status": "ok", "event": "SessionEnd"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        os.chdir(original_cwd)


async def hook_pre_compact(request: Request) -> JSONResponse:
    """Handle PreCompact hook via HTTP."""
    import io
    import os
    from contextlib import redirect_stdout, redirect_stderr

    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = {}

    cwd = body.get("cwd", str(Path.cwd()))
    original_cwd = os.getcwd()
    stdout_capture = io.StringIO()

    try:
        os.chdir(cwd)

        with redirect_stdout(stdout_capture), redirect_stderr(stdout_capture):
            run_pre_compact(args=[])

        return JSONResponse({"status": "ok", "event": "PreCompact"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        os.chdir(original_cwd)


# Define routes
routes = [
    Route("/health", health, methods=["GET"]),
    Route("/hooks/session-start", hook_session_start, methods=["POST"]),
    Route("/hooks/session-end", hook_session_end, methods=["POST"]),
    Route("/hooks/pre-compact", hook_pre_compact, methods=["POST"]),
]

# Create Starlette app
app = Starlette(routes=routes)


def run_server(port: int = DEFAULT_PORT, host: str = "127.0.0.1") -> None:
    """Run the HTTP hooks server."""
    import uvicorn

    print(f"Starting Anima HTTP server on http://{host}:{port}", file=sys.stderr)
    print("  POST /hooks/session-start  - Load memories", file=sys.stderr)
    print("  POST /hooks/session-end    - Index subconscious", file=sys.stderr)
    print("  POST /hooks/pre-compact    - Save WIP state", file=sys.stderr)
    print("  GET  /health               - Health check", file=sys.stderr)

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run_server()
