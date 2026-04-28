#!/usr/bin/env python3
"""Test the fixed IBuddy module."""

import time
from anima.light.ibuddy import get_ibuddy, close_ibuddy


def main():
    print("Testing IBuddy module...")

    buddy = get_ibuddy()
    if not buddy:
        print("Failed to connect!")
        return

    print("Connected! Running color test...")

    tests = [
        ("RED", buddy.red),
        ("GREEN", buddy.green),
        ("BLUE", buddy.blue),
        ("YELLOW", buddy.yellow),
        ("CYAN", buddy.cyan),
        ("MAGENTA", buddy.magenta),
        ("WHITE", buddy.white),
    ]

    for name, func in tests:
        print(f"  {name}...")
        func()
        time.sleep(1.5)

    print("OFF")
    close_ibuddy()
    print("Done!")


if __name__ == "__main__":
    main()
