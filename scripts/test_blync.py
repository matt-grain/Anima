#!/usr/bin/env python3
"""Test script for i-Buddy / original Blync light cube.

Protocol from: https://github.com/tietomaakari/ibuddy-lkm

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

import time

import hid

# i-Buddy VID:PID
VID = 0x1130
PID = 0x0001

# Initial state (all off)
INITIAL = 0xF5

# Bit masks (XOR to toggle)
HEART = 0x80  # Bit 7
BLUE = 0x40  # Bit 6
GREEN = 0x20  # Bit 5
RED = 0x10  # Bit 4


class IBuddy:
    """Controller for i-Buddy USB device."""

    def __init__(self) -> None:
        self._device: hid.device | None = None
        self._state = INITIAL

    def open(self) -> bool:
        """Open connection to i-Buddy."""
        self._device = hid.device()
        try:
            self._device.open(VID, PID)
            # Send reset sequence
            self._send_raw(b"\x22\x09\x00\x02\x01\x00\x00\x00")
            return True
        except Exception as e:
            print(f"Failed to open i-Buddy: {e}")
            return False

    def close(self) -> None:
        """Close connection."""
        if self._device:
            self.off()
            self._device.close()
            self._device = None

    def _send_raw(self, data: bytes) -> None:
        """Send raw 8-byte packet."""
        if self._device:
            # HID write needs report ID prefix on Windows
            self._device.write(b"\x00" + data)

    def _send_cmd(self, cmd: int) -> None:
        """Send command byte."""
        packet = bytes([0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, cmd])
        self._send_raw(packet)
        self._state = cmd

    def off(self) -> None:
        """Turn all off."""
        self._send_cmd(INITIAL)

    def set_color(
        self,
        red: bool = False,
        green: bool = False,
        blue: bool = False,
        heart: bool = False,
    ) -> None:
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
        self._send_cmd(cmd)

    def red(self) -> None:
        """Set to red."""
        self.set_color(red=True)

    def green(self) -> None:
        """Set to green."""
        self.set_color(green=True)

    def blue(self) -> None:
        """Set to blue."""
        self.set_color(blue=True)

    def yellow(self) -> None:
        """Set to yellow (red + green)."""
        self.set_color(red=True, green=True)

    def cyan(self) -> None:
        """Set to cyan (green + blue)."""
        self.set_color(green=True, blue=True)

    def magenta(self) -> None:
        """Set to magenta (red + blue)."""
        self.set_color(red=True, blue=True)

    def white(self) -> None:
        """Set to white (all colors)."""
        self.set_color(red=True, green=True, blue=True)


def main() -> None:
    """Test the i-Buddy."""
    print("Opening i-Buddy...")
    buddy = IBuddy()

    if not buddy.open():
        print("No i-Buddy found! Make sure it's plugged in.")
        return

    print("Connected! Starting color test...")
    print()

    tests = [
        ("Red", buddy.red),
        ("Green", buddy.green),
        ("Blue", buddy.blue),
        ("Yellow", buddy.yellow),
        ("Cyan", buddy.cyan),
        ("Magenta", buddy.magenta),
        ("White", buddy.white),
        ("Heart only", lambda: buddy.set_color(heart=True)),
        ("Red + Heart", lambda: buddy.set_color(red=True, heart=True)),
    ]

    for name, func in tests:
        print(f"  {name}...")
        func()
        time.sleep(1.5)

    print()
    print("Turning off...")
    buddy.close()
    print("Done!")


if __name__ == "__main__":
    main()
