# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Eyes daemon client - connects to the shared eyes daemon.

Used by MCP servers to control the eyes without owning the display.
"""

from __future__ import annotations

import json
import socket

from loguru import logger

from .daemon import DAEMON_PORT, is_daemon_running


class EyesDaemonClient:
    """Client for the eyes daemon TCP server."""

    def __init__(self, host: str = "127.0.0.1", port: int = DAEMON_PORT):
        self._host = host
        self._port = port
        self._socket: socket.socket | None = None
        self._connected = False

    def connect(self) -> bool:
        """Connect to the daemon."""
        if self._connected:
            return True

        if not is_daemon_running():
            logger.warning("Eyes daemon not running")
            return False

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(2.0)
            self._socket.connect((self._host, self._port))
            self._connected = True
            logger.debug(f"Connected to eyes daemon at {self._host}:{self._port}")
            return True

        except (socket.error, OSError) as e:
            logger.warning(f"Failed to connect to eyes daemon: {e}")
            self._socket = None
            return False

    def disconnect(self) -> None:
        """Disconnect from the daemon."""
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
        self._connected = False

    def is_connected(self) -> bool:
        """Check if connected to the daemon."""
        return self._connected

    def send_command(self, action: str, **kwargs) -> dict:
        """Send a command to the daemon."""
        if not self._connected:
            if not self.connect():
                return {"error": "Eyes daemon not running. Start with: anima eyes-daemon start"}

        cmd = {"action": action, **kwargs}
        try:
            assert self._socket is not None
            self._socket.sendall((json.dumps(cmd) + "\n").encode("utf-8"))

            # Read response
            buffer = ""
            while "\n" not in buffer:
                data = self._socket.recv(4096)
                if not data:
                    self._connected = False
                    return {"error": "Connection closed"}
                buffer += data.decode("utf-8")

            line = buffer.split("\n", 1)[0]
            return json.loads(line)

        except (socket.error, json.JSONDecodeError, OSError) as e:
            self._connected = False
            return {"error": str(e)}

    # Convenience methods matching EyesDisplay API

    def set_emotion(self, emotion: str) -> dict:
        """Set emotion."""
        return self.send_command("emotion", emotion=emotion)

    def look_at(self, x: float, y: float) -> dict:
        """Set look direction."""
        return self.send_command("look", x=x, y=y)

    def blink(self) -> dict:
        """Trigger blink."""
        return self.send_command("blink")

    def set_eye_color(self, r: int, g: int, b: int) -> dict:
        """Set eye color."""
        return self.send_command("color", r=r, g=g, b=b)

    def get_state(self) -> dict:
        """Get current state."""
        return self.send_command("state")

    def shutdown(self) -> dict:
        """Request daemon shutdown."""
        result = self.send_command("shutdown")
        self.disconnect()
        return result
