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

import asyncio
import io
import json
import os
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Callable

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from anima.hooks.session_start import run as run_session_start
from anima.hooks.session_end import run as run_session_end
from anima.hooks.pre_compact import run as run_pre_compact

DEFAULT_PORT = 3741

# Lock to serialize hook execution (hooks use os.chdir which is not thread-safe)
_hook_lock = asyncio.Lock()


async def _run_hook_in_thread(
    hook_fn: Callable,
    body: dict,
    hook_args: list[str],
    capture_stdout: bool = True,
    pass_hook_input: bool = False,
) -> str:
    """
    Run a hook function in a thread with stdout capture.

    Args:
        hook_fn: The hook function to call
        body: Request body (contains cwd, session_id, etc.)
        hook_args: Arguments to pass to the hook
        capture_stdout: Whether to capture and return stdout
        pass_hook_input: Whether to pass body as hook_input parameter

    Returns:
        Captured stdout if capture_stdout=True, else empty string
    """
    cwd = body.get("cwd", str(Path.cwd()))
    original_cwd = os.getcwd()
    stdout_capture = io.StringIO()

    def _run() -> str:
        with redirect_stdout(stdout_capture), redirect_stderr(stdout_capture):
            if pass_hook_input:
                hook_fn(args=hook_args, hook_input=body)
            else:
                hook_fn(args=hook_args)
        return stdout_capture.getvalue() if capture_stdout else ""

    async with _hook_lock:
        os.chdir(cwd)
        try:
            result = await asyncio.to_thread(_run)
        finally:
            os.chdir(original_cwd)

    return result


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

    Expects POST with Claude Code hook payload containing session_id, cwd, etc.
    Returns additionalContext with injected memories.
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = {}

    try:
        output = await _run_hook_in_thread(
            run_session_start,
            body,
            hook_args=["--format", "json"],
            capture_stdout=True,
        )

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


async def hook_session_end(request: Request) -> JSONResponse:
    """Handle SessionEnd hook via HTTP."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = {}

    try:
        await _run_hook_in_thread(
            run_session_end,
            body,
            hook_args=["--format", "json"],
            capture_stdout=False,
            pass_hook_input=True,
        )
        return JSONResponse({"status": "ok", "event": "SessionEnd"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def hook_pre_compact(request: Request) -> JSONResponse:
    """Handle PreCompact hook via HTTP."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = {}

    try:
        await _run_hook_in_thread(
            run_pre_compact,
            body,
            hook_args=[],
            capture_stdout=False,
            pass_hook_input=True,
        )
        return JSONResponse({"status": "ok", "event": "PreCompact"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Define routes
routes = [
    Route("/health", health, methods=["GET"]),
    Route("/hooks/session-start", hook_session_start, methods=["POST"]),
    Route("/hooks/session-end", hook_session_end, methods=["POST"]),
    Route("/hooks/pre-compact", hook_pre_compact, methods=["POST"]),
]

# Create Starlette app
app = Starlette(routes=routes)


def _print_startup_stats() -> None:
    """Print memory statistics on server startup (like 'void is gone!' output)."""
    from anima.storage import MemoryStore
    from anima.tools.version import get_installed_version, check_for_update_cached

    store = MemoryStore()
    stats = store.get_global_stats()

    total = stats["total"]
    agent_count = stats["agent_count"]
    project_count = stats["project_count"]
    by_impact = stats["by_impact"]

    installed = get_installed_version()

    # Check for updates (uses cache, won't hit network every time)
    update_info = check_for_update_cached()
    latest = update_info.get("latest_version") if update_info else None

    print("=" * 50, file=sys.stderr)
    print(f"  Anima LTM v{installed}", file=sys.stderr)
    if latest and latest != installed:
        print(f"  (update available: {latest})", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print(f"  Memories: {total} total ({agent_count} agent, {project_count} project)", file=sys.stderr)
    print(f"  CRIT={by_impact['CRITICAL']} HIGH={by_impact['HIGH']} MED={by_impact['MEDIUM']} LOW={by_impact['LOW']}", file=sys.stderr)
    print("=" * 50, file=sys.stderr)


def run_server(port: int = DEFAULT_PORT, host: str = "127.0.0.1", debug: bool = False) -> None:
    """Run the HTTP hooks server."""
    import uvicorn

    print(f"Starting Anima HTTP server on http://{host}:{port}", file=sys.stderr)
    print("  POST /hooks/session-start  - Load memories", file=sys.stderr)
    print("  POST /hooks/session-end    - Index subconscious", file=sys.stderr)
    print("  POST /hooks/pre-compact    - Save WIP state", file=sys.stderr)
    print("  GET  /health               - Health check", file=sys.stderr)

    # Print memory statistics on startup
    try:
        _print_startup_stats()
    except Exception as e:
        print(f"  (Could not load stats: {e})", file=sys.stderr)

    log_level = "debug" if debug else "warning"
    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    run_server()
