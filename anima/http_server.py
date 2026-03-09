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

# Lock to serialize hook execution (hooks use os.chdir which is not thread-safe)
_hook_lock = asyncio.Lock()


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

    def _run_hook() -> str:
        """Run hook in thread - captures stdout."""
        with redirect_stdout(stdout_capture):
            run_session_start(args=["--format", "json"])
        return stdout_capture.getvalue()

    try:
        # Serialize hook execution (os.chdir is not thread-safe)
        async with _hook_lock:
            os.chdir(cwd)
            try:
                # Run blocking hook in thread pool to avoid blocking event loop
                output = await asyncio.to_thread(_run_hook)
            finally:
                os.chdir(original_cwd)

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

    def _run_hook() -> None:
        """Run hook in thread - this can block for integrity checks."""
        with redirect_stdout(stdout_capture), redirect_stderr(stdout_capture):
            run_session_end(args=["--format", "json"], hook_input=body)

    try:
        # Serialize hook execution (os.chdir is not thread-safe)
        async with _hook_lock:
            os.chdir(cwd)
            try:
                # Run blocking hook in thread pool to avoid blocking event loop
                await asyncio.to_thread(_run_hook)
            finally:
                os.chdir(original_cwd)

        return JSONResponse({"status": "ok", "event": "SessionEnd"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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

    def _run_hook() -> None:
        """Run hook in thread."""
        with redirect_stdout(stdout_capture), redirect_stderr(stdout_capture):
            run_pre_compact(args=[], hook_input=body)

    try:
        # Serialize hook execution (os.chdir is not thread-safe)
        async with _hook_lock:
            os.chdir(cwd)
            try:
                # Run blocking hook in thread pool to avoid blocking event loop
                await asyncio.to_thread(_run_hook)
            finally:
                os.chdir(original_cwd)

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

    # Count memories using raw SQL for global stats
    with store._connect() as conn:
        # Total and region counts
        row = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN project_id IS NULL THEN 1 ELSE 0 END) as agent_count,
                SUM(CASE WHEN project_id IS NOT NULL THEN 1 ELSE 0 END) as project_count
            FROM memories
            WHERE superseded_by IS NULL
        """).fetchone()
        total = row[0] if row else 0
        agent_count = row[1] if row else 0
        project_count = row[2] if row else 0

        # Impact level counts
        impact_rows = conn.execute("""
            SELECT impact, COUNT(*) as cnt
            FROM memories
            WHERE superseded_by IS NULL
            GROUP BY impact
        """).fetchall()
        by_impact = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for impact_row in impact_rows:
            impact_name = impact_row[0].upper() if impact_row[0] else "LOW"
            if impact_name in by_impact:
                by_impact[impact_name] = impact_row[1]

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
