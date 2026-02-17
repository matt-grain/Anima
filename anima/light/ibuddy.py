# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
i-Buddy USB device controller.

Protocol reverse-engineered from:
https://github.com/tietomaakari/ibuddy-lkm

Bit layout (inverted - 0=on, 1=off):
- Bit 7: Heart
- Bit 6: Blue
- Bit 5: Green
- Bit 4: Red
- Bits 2-3: Wings (00=down, 01/10=flap, 11=up)
- Bits 0-1: Twist (00=left, 01/10=center, 11=right)

Initial value: 0xF5 (all off)
Command packet: [0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, <cmd>]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    import hid

# i-Buddy VID:PID
VID = 0x1130
PID = 0x0001

# Initial state (all off)
INITIAL = 0xF5

# Bit masks (XOR to toggle - bits are inverted)
HEART = 0x80  # Bit 7
BLUE = 0x40  # Bit 6
GREEN = 0x20  # Bit 5
RED = 0x10  # Bit 4

# Named colors as RGB tuples -> bit masks
COLOR_MAP: dict[str, int] = {
    "off": 0,
    "red": RED,
    "green": GREEN,
    "blue": BLUE,
    "yellow": RED | GREEN,
    "cyan": GREEN | BLUE,
    "magenta": RED | BLUE,
    "white": RED | GREEN | BLUE,
}


class IBuddy:
    """Controller for i-Buddy USB device(s). Broadcasts to ALL connected devices."""

    def __init__(self) -> None:
        self._devices: list[hid.device] = []
        self._state = INITIAL
        self._connected = False

    @property
    def connected(self) -> bool:
        """Check if any device is connected."""
        return self._connected

    @property
    def device_count(self) -> int:
        """Return number of connected devices."""
        return len(self._devices)

    def open(self) -> bool:
        """Open connection to ALL i-Buddy devices on interface 1."""
        try:
            import hid
        except ImportError:
            logger.error("hidapi not installed. Run: uv add hidapi")
            return False

        # Find ALL devices on interface 1
        devices = hid.enumerate(VID, PID)
        interface_1_paths = [dev["path"] for dev in devices if dev["interface_number"] == 1]

        if not interface_1_paths:
            logger.warning("No i-Buddy devices found on interface 1")
            return False

        # Open ALL devices
        self._devices = []
        for path in interface_1_paths:
            device = hid.device()
            try:
                device.open_path(path)
                self._devices.append(device)
                logger.debug(f"i-Buddy connected: {path}")
            except Exception as e:
                logger.warning(f"Failed to open i-Buddy at {path}: {e}")

        self._connected = len(self._devices) > 0
        logger.info(f"Connected to {len(self._devices)} i-Buddy device(s)")
        return self._connected

    def close(self) -> None:
        """Close all connections."""
        if self._devices:
            self.off()
            for device in self._devices:
                try:
                    device.close()
                except Exception:
                    pass
            self._devices = []
            self._connected = False
            logger.debug("All i-Buddy devices disconnected")

    def _send_cmd(self, cmd: int) -> bool:
        """Send command byte to ALL devices."""
        if not self._devices or not self._connected:
            return False

        success = False
        # Must use [0x00] prefix (report ID) + command packet
        packet = [0x00, 0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, cmd]

        for device in self._devices:
            try:
                device.write(packet)
                success = True
            except Exception as e:
                logger.error(f"Failed to send command to device: {e}")

        if success:
            self._state = cmd
        return success

    def off(self) -> bool:
        """Turn all off."""
        return self._send_cmd(INITIAL)

    def set_color(
        self,
        red: bool = False,
        green: bool = False,
        blue: bool = False,
        heart: bool = False,
    ) -> bool:
        """Set color by toggling bits."""
        cmd = INITIAL
        if red:
            cmd ^= RED
        if green:
            cmd ^= GREEN
        if blue:
            cmd ^= BLUE
        if heart:
            cmd ^= HEART
        return self._send_cmd(cmd)

    def set_color_by_name(self, name: str, heart: bool = False) -> bool:
        """Set color by name (red, green, blue, yellow, cyan, magenta, white, off)."""
        name = name.lower().strip()
        if name not in COLOR_MAP:
            logger.warning(f"Unknown color: {name}. Available: {list(COLOR_MAP.keys())}")
            return False

        mask = COLOR_MAP[name]
        cmd = INITIAL ^ mask
        if heart:
            cmd ^= HEART
        return self._send_cmd(cmd)

    def set_rgb(self, r: int, g: int, b: int, heart: bool = False) -> bool:
        """Set color from RGB values (thresholded to on/off)."""
        return self.set_color(
            red=r > 127,
            green=g > 127,
            blue=b > 127,
            heart=heart,
        )

    # Convenience methods
    def red(self) -> bool:
        return self.set_color(red=True)

    def green(self) -> bool:
        return self.set_color(green=True)

    def blue(self) -> bool:
        return self.set_color(blue=True)

    def yellow(self) -> bool:
        return self.set_color(red=True, green=True)

    def cyan(self) -> bool:
        return self.set_color(green=True, blue=True)

    def magenta(self) -> bool:
        return self.set_color(red=True, blue=True)

    def white(self) -> bool:
        return self.set_color(red=True, green=True, blue=True)


# Singleton instance
_instance: IBuddy | None = None


def get_ibuddy() -> IBuddy | None:
    """Get or create the i-Buddy singleton instance."""
    global _instance
    if _instance is None:
        _instance = IBuddy()
        if not _instance.open():
            _instance = None
    return _instance


def close_ibuddy() -> None:
    """Close the i-Buddy singleton instance."""
    global _instance
    if _instance:
        _instance.close()
        _instance = None
