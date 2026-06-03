# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Eyes daemon - TCP server wrapping EyesDisplay for shared access.

Allows multiple MCP servers to share a single eyes window.
Port 19840 = Anima's birthday (2025-01-19 → 19840)
"""

from __future__ import annotations

import atexit
import json
import os
import signal
import socket
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from .config import Config

DAEMON_PORT = 19840
LOCK_FILE = Path.home() / ".anima" / "eyes-daemon.lock"


def _ensure_lock_dir() -> None:
    """Ensure the lock file directory exists."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)


def is_daemon_running() -> bool:
    """Check if the daemon is running by verifying lock file and PID."""
    if not LOCK_FILE.exists():
        return False

    try:
        lock_data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        pid = lock_data.get("pid")
        if pid is None:
            return False

        # Check if process is alive (Windows-compatible)
        if os.name == "nt":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)  # Signal 0 = check if process exists
            return True
    except (json.JSONDecodeError, ProcessLookupError, PermissionError, OSError):
        # Stale lock file - clean it up
        try:
            LOCK_FILE.unlink()
        except OSError:
            pass
        return False


def get_daemon_info() -> dict | None:
    """Get daemon info from lock file if running."""
    if not is_daemon_running():
        return None
    try:
        return json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def acquire_lock() -> bool:
    """Acquire the daemon lock file."""
    if is_daemon_running():
        return False

    _ensure_lock_dir()
    lock_data = {
        "pid": os.getpid(),
        "port": DAEMON_PORT,
        "started_at": datetime.now().isoformat(),
    }
    LOCK_FILE.write_text(json.dumps(lock_data), encoding="utf-8")
    return True


def release_lock() -> None:
    """Release the daemon lock file."""
    try:
        LOCK_FILE.unlink()
    except OSError:
        pass


def _cleanup_on_exit() -> None:
    """Cleanup handler for atexit - ensures lock is released."""
    release_lock()
    logger.debug("Cleanup on exit: lock released")


class EyesDaemonServer:
    """TCP server that wraps EyesDisplay for shared access."""

    def __init__(self, config: Config | None = None):
        self._config = config
        self._display = None
        self._server_socket: socket.socket | None = None
        self._running = False
        self._clients: list[socket.socket] = []
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Start the daemon server."""
        if not acquire_lock():
            logger.error("Could not acquire lock - daemon already running?")
            return False

        # Register cleanup handlers
        atexit.register(_cleanup_on_exit)

        # Handle SIGTERM/SIGINT for graceful shutdown
        def signal_handler(signum: int, frame: object) -> None:
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop()
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        try:
            # Import and create display
            from .config import Config
            from .display import EyesDisplay

            if self._config is None:
                self._config = Config()

            self._display = EyesDisplay(self._config)

            # Create TCP server
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind(("127.0.0.1", DAEMON_PORT))
            self._server_socket.listen(5)
            self._server_socket.settimeout(0.5)  # Non-blocking accept

            self._running = True

            # Start client handler thread
            client_thread = threading.Thread(target=self._accept_clients, daemon=True)
            client_thread.start()

            logger.info(f"Eyes daemon listening on port {DAEMON_PORT}")

            # Run display in main thread (blocking)
            self._display.run()

            return True

        except Exception as e:
            logger.error(f"Failed to start daemon: {e}")
            release_lock()
            return False

        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the daemon server."""
        self._running = False

        # Close all client connections
        with self._lock:
            for client in self._clients:
                try:
                    client.close()
                except OSError:
                    pass
            self._clients.clear()

        # Close server socket
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass
            self._server_socket = None

        # Stop display
        if self._display:
            self._display.stop()
            self._display = None

        release_lock()
        logger.info("Eyes daemon stopped")

    def _accept_clients(self) -> None:
        """Accept incoming client connections."""
        while self._running:
            try:
                if self._server_socket is None:
                    break
                client, addr = self._server_socket.accept()
                logger.debug(f"Client connected from {addr}")

                with self._lock:
                    self._clients.append(client)

                # Handle client in a separate thread
                handler = threading.Thread(
                    target=self._handle_client,
                    args=(client,),
                    daemon=True,
                )
                handler.start()

            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_client(self, client: socket.socket) -> None:
        """Handle a single client connection."""
        buffer = ""
        try:
            client.settimeout(1.0)
            while self._running:
                try:
                    data = client.recv(4096)
                    if not data:
                        break

                    buffer += data.decode("utf-8")

                    # Process complete messages (newline-delimited JSON)
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if line.strip():
                            response = self._process_command(line)
                            client.sendall((json.dumps(response) + "\n").encode("utf-8"))

                except socket.timeout:
                    continue
                except (ConnectionResetError, BrokenPipeError):
                    break

        except Exception as e:
            logger.debug(f"Client handler error: {e}")

        finally:
            with self._lock:
                if client in self._clients:
                    self._clients.remove(client)
            try:
                client.close()
            except OSError:
                pass

    def _process_command(self, line: str) -> dict:
        """Process a command and return response."""
        try:
            cmd = json.loads(line)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON"}

        action = cmd.get("action")
        if not action:
            return {"error": "Missing action"}

        if self._display is None:
            return {"error": "Display not initialized"}

        if action == "emotion":
            emotion = cmd.get("emotion", "normal")
            self._display.set_emotion(emotion)
            return {"emotion": emotion}

        elif action == "look":
            x = cmd.get("x", 0.0)
            y = cmd.get("y", 0.0)
            self._display.look_at(x, y)
            return {"looking": [x, y]}

        elif action == "blink":
            self._display.blink()
            return {"blinked": True}

        elif action == "color":
            r = cmd.get("r", 255)
            g = cmd.get("g", 255)
            b = cmd.get("b", 255)
            self._display.set_eye_color(r, g, b)
            return {"color": [r, g, b]}

        elif action == "state":
            return self._display.get_state()

        elif action == "shutdown":
            # Schedule shutdown
            threading.Thread(target=self._delayed_stop, daemon=True).start()
            return {"stopped": True}

        else:
            return {"error": f"Unknown action: {action}"}

    def _delayed_stop(self) -> None:
        """Stop the daemon after a short delay."""
        import time

        time.sleep(0.1)
        self._running = False
        if self._display:
            self._display._running = False


def run_daemon(config_path: str | None = None) -> bool:
    """Run the eyes daemon (blocking)."""
    from .config import Config

    config = Config.load(config_path)
    server = EyesDaemonServer(config)
    return server.start()
