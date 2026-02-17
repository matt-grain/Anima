# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
CLI commands for eyes daemon management.

Usage:
    anima eyes-daemon start [--foreground] [--config PATH]
    anima eyes-daemon stop
    anima eyes-daemon status
"""

from __future__ import annotations

import subprocess
import sys

from loguru import logger


def run(args: list[str]) -> int:
    """Run eyes-daemon command."""
    if not args:
        _print_usage()
        return 1

    subcommand = args[0]
    remaining = args[1:]

    if subcommand == "start":
        return _start(remaining)
    elif subcommand == "stop":
        return _stop()
    elif subcommand == "status":
        return _status()
    else:
        print(f"Unknown subcommand: {subcommand}")
        _print_usage()
        return 1


def _print_usage() -> None:
    """Print usage information."""
    print("Usage: anima eyes-daemon <command>")
    print()
    print("Commands:")
    print("  start       Start the eyes daemon")
    print("  stop        Stop the eyes daemon")
    print("  status      Show daemon status")
    print()
    print("Options for start:")
    print("  --foreground    Run in foreground (don't detach)")
    print("  --config PATH   Path to eyes config file")


def _spawn_windowless_win32(cmd: list[str]) -> None:
    """Spawn a Python subprocess on Windows without any console window.

    Uses a temporary VBScript to launch the process via WScript.Shell.Run
    with window style 0 (hidden). This is the only reliable way to prevent
    a console flash when the Python interpreter is a console subsystem binary
    (python.exe in venvs where pythonw.exe doesn't exist).
    """
    import tempfile
    from pathlib import Path

    # Build the command string for VBScript, escaping double quotes
    cmd_str = " ".join(f'"""{c}"""' if " " in c else c for c in cmd)
    # WScript.Shell.Run args: command, windowStyle (0=hidden), waitOnReturn (False)
    vbs_content = f'CreateObject("WScript.Shell").Run "{cmd_str}", 0, False\n'

    vbs_path = Path(tempfile.gettempdir()) / "anima_eyes_launch.vbs"
    vbs_path.write_text(vbs_content, encoding="utf-8")

    try:
        # wscript.exe is a GUI subsystem executable -- it never creates a console
        subprocess.Popen(
            ["wscript.exe", str(vbs_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    except Exception:
        # Fallback: use CREATE_NO_WINDOW (may flash briefly)
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(
            cmd,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )


def _start(args: list[str]) -> int:
    """Start the daemon."""
    from anima.eyes.daemon import DAEMON_PORT, is_daemon_running

    if is_daemon_running():
        print(f"Eyes daemon already running on port {DAEMON_PORT}")
        return 0

    foreground = "--foreground" in args
    config_path = None

    # Parse --config
    for i, arg in enumerate(args):
        if arg == "--config" and i + 1 < len(args):
            config_path = args[i + 1]
            break

    if foreground:
        # Run in foreground (blocking)
        print(f"Starting eyes daemon on port {DAEMON_PORT}...")
        from anima.eyes.daemon import run_daemon

        run_daemon(config_path)
        # Explicitly exit to kill any lingering threads
        sys.exit(0)
    else:
        # Spawn detached process
        cmd = [sys.executable, "-m", "anima", "eyes-daemon", "start", "--foreground"]

        if config_path:
            cmd.extend(["--config", config_path])

        try:
            if sys.platform == "win32":
                _spawn_windowless_win32(cmd)
            else:
                # Unix: double-fork via nohup
                subprocess.Popen(
                    ["nohup"] + cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )

            print(f"Eyes daemon starting on port {DAEMON_PORT}...")

            # Wait and verify (pygame can take a few seconds to initialize)
            import time

            for _ in range(50):  # Wait up to 5 seconds
                time.sleep(0.1)
                if is_daemon_running():
                    print("Eyes daemon started successfully")
                    return 0

            print("Warning: Daemon may not have started properly")
            return 1

        except Exception as e:
            logger.error(f"Failed to start daemon: {e}")
            print(f"Failed to start daemon: {e}")
            return 1


def _stop() -> int:
    """Stop the daemon."""
    from anima.eyes.daemon import is_daemon_running

    if not is_daemon_running():
        print("Eyes daemon not running")
        return 0

    from anima.eyes.client import EyesDaemonClient

    client = EyesDaemonClient()
    if client.connect():
        result = client.shutdown()
        if "error" in result:
            print(f"Error stopping daemon: {result['error']}")
            return 1
        print("Eyes daemon stopped")
        return 0
    else:
        print("Could not connect to daemon")
        return 1


def _status() -> int:
    """Show daemon status."""
    from anima.eyes.daemon import DAEMON_PORT, get_daemon_info, is_daemon_running

    if not is_daemon_running():
        print("Eyes daemon: not running")
        return 1

    info = get_daemon_info()
    if info:
        print("Eyes daemon: running")
        print(f"  PID: {info.get('pid')}")
        print(f"  Port: {info.get('port', DAEMON_PORT)}")
        print(f"  Started: {info.get('started_at', 'unknown')}")

        # Try to get state
        from anima.eyes.client import EyesDaemonClient

        client = EyesDaemonClient()
        if client.connect():
            state = client.get_state()
            if "error" not in state:
                print(f"  Emotion: {state.get('emotion', 'unknown')}")
                print(f"  Looking: {state.get('look_target', [0, 0])}")
            client.disconnect()
    else:
        print("Eyes daemon: running (no info available)")

    return 0
