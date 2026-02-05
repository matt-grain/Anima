# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Logging infrastructure for Anima.

Daily log files with automatic cleanup.
Enable via ~/.anima/config.json: {"logging": {"debug": true}}

Log files are created at ~/.anima/logs/anima_<date>.log
All hook calls append to the same daily file for easy monitoring.
"""

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from anima.core.config import get_config

# Session ID - generated once per process (for correlating log entries)
_session_id: Optional[str] = None
_configured: bool = False


def get_session_id() -> str:
    """Get or generate the current session ID."""
    global _session_id
    if _session_id is None:
        _session_id = uuid.uuid4().hex[:8]
    return _session_id


def get_log_dir() -> Path:
    """Get the log directory path."""
    return Path.home() / ".anima" / "logs"


def get_daily_log_path() -> Path:
    """Get the log file path for today."""
    log_dir = get_log_dir()
    today = datetime.now().strftime("%Y-%m-%d")
    return log_dir / f"anima_{today}.log"


def cleanup_old_logs(retention_count: int) -> int:
    """
    Remove old log files, keeping only the most recent N days.

    Args:
        retention_count: Number of daily log files to keep

    Returns:
        Number of files deleted
    """
    log_dir = get_log_dir()
    if not log_dir.exists():
        return 0

    # Get all daily log files sorted by modification time (newest first)
    log_files = sorted(
        log_dir.glob("anima_*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    # Also clean up old session-based logs from previous version
    old_session_logs = list(log_dir.glob("session_*.log"))
    for old_file in old_session_logs:
        try:
            old_file.unlink()
        except OSError:
            pass

    # Delete daily files beyond retention count
    deleted = 0
    for old_file in log_files[retention_count:]:
        try:
            old_file.unlink()
            deleted += 1
        except OSError:
            pass  # Ignore deletion errors

    return deleted + len(old_session_logs)


def configure_logging() -> None:
    """
    Configure loguru based on config settings.

    If debug is disabled, logging goes nowhere (null sink).
    If debug is enabled, logs append to daily file.
    """
    global _configured
    if _configured:
        return

    config = get_config()

    # Remove default stderr handler
    logger.remove()

    if config.logging.debug:
        # Ensure log directory exists
        log_dir = get_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)

        # Cleanup old logs
        cleanup_old_logs(config.logging.log_retention_count)

        # Get session ID for this process
        session_id = get_session_id()

        # Add file handler - append to daily log
        log_path = get_daily_log_path()
        logger.add(
            log_path,
            format="{time:HH:mm:ss} | {level: <7} | [" + session_id + "] {message}",
            level="DEBUG",
            rotation=None,  # No rotation - one file per day
            retention=None,  # We handle retention manually
        )

        # Also add stderr for immediate feedback (INFO level only)
        logger.add(
            sys.stderr,
            format="<dim>{time:HH:mm:ss}</dim> | <level>{level: <7}</level> | {message}",
            level="INFO",
            colorize=True,
        )

        logger.info("Anima process started")
        logger.debug(f"Log file: {log_path}")

    _configured = True


def get_logger(name: str = "anima"):
    """
    Get a configured logger instance.

    Automatically configures logging on first call.

    Args:
        name: Logger name (for filtering)

    Returns:
        Configured loguru logger
    """
    configure_logging()
    return logger.bind(name=name)


# Convenience functions for hook logging
def log_hook_start(hook_name: str, **context) -> None:
    """Log that a hook has started."""
    log = get_logger("hooks")
    log.info(f"{hook_name} hook fired")
    if context:
        log.debug(f"  → {context}")


def log_hook_end(hook_name: str, **results) -> None:
    """Log that a hook has completed."""
    log = get_logger("hooks")
    log.info(f"{hook_name} hook completed")
    if results:
        log.debug(f"  → {results}")


def log_memories_loaded(
    agent_count: int,
    project_count: int,
    deferred_count: int,
    kind_breakdown: Optional[dict] = None,
    impact_breakdown: Optional[dict] = None,
) -> None:
    """Log memory loading statistics."""
    log = get_logger("memories")
    log.info(f"Loaded {agent_count} AGENT + {project_count} PROJECT memories, {deferred_count} deferred")

    if kind_breakdown:
        log.debug(f"  Kind: {kind_breakdown}")
    if impact_breakdown:
        log.debug(f"  Impact: {impact_breakdown}")


def log_memories_injected(subagent_name: str, count: int, kind_breakdown: Optional[dict] = None) -> None:
    """Log memory injection to subagent."""
    log = get_logger("memories")
    log.info(f"Injected {count} memories to subagent '{subagent_name}'")

    if kind_breakdown:
        log.debug(f"  Kind: {kind_breakdown}")


def log_achievement_detected(description: str, commit_hash: Optional[str] = None) -> None:
    """Log an achievement detection."""
    log = get_logger("achievements")
    if commit_hash:
        log.info(f"Achievement [{commit_hash[:8]}]: {description[:100]}")
    else:
        log.info(f"Achievement: {description[:100]}")


def log_error(context: str, error: Exception) -> None:
    """Log an error with context."""
    log = get_logger("errors")
    log.error(f"{context}: {type(error).__name__}: {error}")


def log_warning(message: str) -> None:
    """Log a warning."""
    log = get_logger("warnings")
    log.warning(message)
