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
    POST /hooks/subagent-start   → Returns lean additionalContext for subagents
    *    /mcp                    → MCP tools (memory/curiosity/dream/...) over streamable-HTTP
    GET  /health                 → Health check
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Callable

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount

from anima.hooks.session_start import run as run_session_start
from anima.hooks.session_end import run as run_session_end
from anima.hooks.pre_compact import run as run_pre_compact
from anima.hooks.subagent_start import run as run_subagent_start
from anima.embeddings.embedder import is_model_loaded, CACHE_DIR
from anima.server import mcp

# MCP tools (memory/curiosity/dream/...) served over streamable-HTTP at /mcp,
# co-hosted with the lifecycle hooks so a single `anima serve` does both.
# Calling streamable_http_app() also lazily creates mcp.session_manager.
_mcp_app = mcp.streamable_http_app()

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

    model_was_loaded = is_model_loaded()
    try:
        output = await _run_hook_in_thread(
            run_session_start,
            body,
            hook_args=["--format", "json"],
            capture_stdout=True,
        )

        # Log embedding model status
        if is_model_loaded():
            status = "already loaded" if model_was_loaded else "loaded now"
            print(f"[session-start] Embedding model {status} (cache: {CACHE_DIR})", file=sys.stderr)
        else:
            print(f"[session-start] Embedding model not loaded (cache: {CACHE_DIR})", file=sys.stderr)

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


async def hook_subagent_start(request: Request) -> JSONResponse:
    """
    Handle SubagentStart hook via HTTP.

    Injects a lean (CRITICAL-focused) memory set so subagents share Anima's
    context. Returns additionalContext, mirroring the SessionStart contract.
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = {}

    try:
        output = await _run_hook_in_thread(
            run_subagent_start,
            body,
            hook_args=[],
            capture_stdout=True,
            pass_hook_input=True,
        )
        # The capture buffer holds clean JSON followed by a stderr status line,
        # so decode just the leading JSON object and ignore the trailing text.
        result, _ = json.JSONDecoder().raw_decode(output.lstrip())
        return JSONResponse(result)

    except (json.JSONDecodeError, ValueError):
        return JSONResponse(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStart",
                    "additionalContext": "",
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            {
                "error": str(e),
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStart",
                    "additionalContext": "",
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
    Route("/hooks/subagent-start", hook_subagent_start, methods=["POST"]),
    Route("/hooks/session-end", hook_session_end, methods=["POST"]),
    Route("/hooks/pre-compact", hook_pre_compact, methods=["POST"]),
    # MCP tools endpoint (/mcp) — mounted last so explicit hook routes win.
    Mount("/", app=_mcp_app),
]


@asynccontextmanager
async def lifespan(app: Starlette) -> AsyncGenerator[None, None]:
    """Lifespan: run the MCP session manager and print stats on startup."""
    async with mcp.session_manager.run():
        try:
            _print_startup_stats()
        except Exception as e:
            print(f"  (Could not load stats: {e})", file=sys.stderr)
        yield


# Create Starlette app with lifespan
app = Starlette(routes=routes, lifespan=lifespan)


def _print_startup_stats() -> None:
    """Print memory statistics on server startup (like 'void is gone!' output)."""
    from datetime import datetime, UTC

    from anima.storage import MemoryStore, CuriosityStore
    from anima.storage.dissonance import DissonanceStore
    from anima.storage.dream_state import DreamStateStore
    from anima.storage.sqlite import get_default_db_path
    from anima.tools.version import get_installed_version, check_for_update_cached
    from anima.core.config import get_config

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

    # Get database size
    db_path = get_default_db_path()
    db_size_mb = db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0

    # Get config for agent ID
    config = get_config()
    agent_id = config.agent.id

    # Count open curiosities (research queue)
    try:
        curiosity_store = CuriosityStore()
        curiosity_count = curiosity_store.count_open(agent_id)
    except Exception:
        curiosity_count = 0

    # Count open dissonances
    try:
        dissonance_store = DissonanceStore()
        dissonance_count = dissonance_store.count_open(agent_id)
    except Exception:
        dissonance_count = 0

    # Get last dream time
    try:
        dream_store = DreamStateStore()
        last_dream = dream_store.get_last_completed_session(agent_id, None)
        if last_dream:
            dream_time = datetime.fromisoformat(last_dream.updated_at).replace(tzinfo=UTC)
            hours_ago = (datetime.now(UTC) - dream_time).total_seconds() / 3600
            if hours_ago < 24:
                dream_status = f"{hours_ago:.0f}h ago"
            else:
                days_ago = hours_ago / 24
                dream_status = f"{days_ago:.0f}d ago"
        else:
            dream_status = "never"
    except Exception:
        dream_status = "?"

    # Count unsigned memories
    try:
        unsigned_count = store.count_unvalidated_memories(agent_id)
    except Exception:
        unsigned_count = 0

    # Count backups
    try:
        backup_dir = Path.home() / ".anima" / "backups"
        backup_count = len(list(backup_dir.glob("*.db"))) if backup_dir.exists() else 0
    except Exception:
        backup_count = 0

    # Build the banner
    print("=" * 60, file=sys.stderr)
    version_line = f"  🧠 Anima LTM v{installed}"
    if latest and latest != installed:
        version_line += f"  (update: {latest})"
    print(version_line, file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Memory stats
    print(
        f"  📚 Memories: {total} ({agent_count} agent, {project_count} project)",
        file=sys.stderr,
    )
    print(
        f"     CRIT={by_impact['CRITICAL']} HIGH={by_impact['HIGH']} MED={by_impact['MEDIUM']} LOW={by_impact['LOW']}",
        file=sys.stderr,
    )

    # Database info
    print(f"  💾 Database: {db_size_mb:.1f} MB | {backup_count} backups", file=sys.stderr)

    # Activity stats
    activity_parts = []
    if curiosity_count > 0:
        activity_parts.append(f"🔬 {curiosity_count} curiosities")
    if dissonance_count > 0:
        activity_parts.append(f"⚡ {dissonance_count} dissonances")
    if unsigned_count > 0:
        activity_parts.append(f"🔓 {unsigned_count} unsigned")

    if activity_parts:
        print(f"  {' | '.join(activity_parts)}", file=sys.stderr)

    # Dream status
    print(f"  💭 Last dream: {dream_status}", file=sys.stderr)

    print("=" * 60, file=sys.stderr)


class _TidyNameFilter(logging.Filter):
    """Cosmetic: uvicorn logs lifecycle INFO messages under a logger literally
    named 'uvicorn.error' (not an error). Display it as plain 'uvicorn'.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name == "uvicorn.error":
            record.name = "uvicorn"
        return True


def _build_log_config(debug: bool) -> dict:
    """One unified log format for uvicorn and the MCP SDK.

    Without this, uvicorn's loggers use uvicorn's own format while the MCP SDK
    logs propagate to a stray RichHandler (installed when anima.server imports
    FastMCP), producing two clashing styles in the console.
    """
    level = "DEBUG" if debug else "INFO"
    fmt = {"format": "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s", "datefmt": "%H:%M:%S"}
    logger_cfg = {"handlers": ["default"], "level": level, "propagate": False}
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"anima": fmt},
        "filters": {"tidy_name": {"()": _TidyNameFilter}},
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "formatter": "anima",
                "filters": ["tidy_name"],
            },
        },
        "loggers": {name: logger_cfg for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "mcp")},
        "root": {"handlers": ["default"], "level": level},
    }


def run_server(
    port: int = DEFAULT_PORT,
    host: str = "127.0.0.1",
    debug: bool = False,
    reload: bool = False,
) -> None:
    """Run the HTTP hooks server."""
    import uvicorn

    print(f"Starting Anima HTTP server on http://{host}:{port}", file=sys.stderr)
    print("  POST /hooks/session-start  - Load memories", file=sys.stderr)
    print("  POST /hooks/subagent-start - Load lean memories for subagents", file=sys.stderr)
    print("  POST /hooks/session-end    - Index subconscious", file=sys.stderr)
    print("  POST /hooks/pre-compact    - Save WIP state", file=sys.stderr)
    print("  *    /mcp                  - MCP tools (memory/curiosity/dream/...)", file=sys.stderr)
    print("  GET  /health               - Health check", file=sys.stderr)
    if debug:
        print("  🐛 Debug mode enabled (verbose logging)", file=sys.stderr)
    if reload:
        print("  🔄 Auto-reload enabled (watching anima/ for changes)", file=sys.stderr)

    # One log format for uvicorn AND the MCP SDK (works with --reload)
    log_config = _build_log_config(debug)

    if reload:
        # Use string reference for reload mode (uvicorn reimports the module)
        uvicorn.run(
            "anima.http_server:app",
            host=host,
            port=port,
            log_config=log_config,
            reload=True,
            reload_dirs=["anima"],
        )
    else:
        uvicorn.run(app, host=host, port=port, log_config=log_config)


if __name__ == "__main__":
    run_server()
