#!/usr/bin/env python3
"""
Test different approaches to control i-Buddy.
Run each version separately by uncommenting.

Usage: uv run python scripts/test_ibuddy_versions.py
"""

import time
import hid

VID = 0x1130
PID = 0x0001
INITIAL = 0xF5  # All off


# =============================================================================
# VERSION 1: Direct write with list (worked in terminal)
# =============================================================================
def test_v1_direct_list():
    """Direct write using list - this worked before!"""
    print("\n=== VERSION 1: Direct list write ===")
    device = hid.device()
    device.open(VID, PID)

    packet = [0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, 0xE5]  # RED
    device.write(packet)
    print("Sent RED (list)")
    time.sleep(3)

    device.write([0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, INITIAL])  # OFF
    device.close()
    print("Done v1")


# =============================================================================
# VERSION 2: With report ID prefix (0x00)
# =============================================================================
def test_v2_with_report_id():
    """Write with report ID 0x00 prefix."""
    print("\n=== VERSION 2: With report ID 0x00 ===")
    device = hid.device()
    device.open(VID, PID)

    # Add 0x00 report ID prefix
    packet = [0x00, 0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, 0xE5]  # RED
    device.write(packet)
    print("Sent RED (with 0x00 prefix)")
    time.sleep(3)

    device.write([0x00, 0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, INITIAL])
    device.close()
    print("Done v2")


# =============================================================================
# VERSION 3: Using bytes instead of list
# =============================================================================
def test_v3_bytes():
    """Write using bytes object."""
    print("\n=== VERSION 3: Bytes object ===")
    device = hid.device()
    device.open(VID, PID)

    packet = bytes([0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, 0xE5])
    device.write(packet)
    print("Sent RED (bytes)")
    time.sleep(3)

    device.write(bytes([0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, INITIAL]))
    device.close()
    print("Done v3")


# =============================================================================
# VERSION 4: Interface 1 instead of default
# =============================================================================
def test_v4_interface1():
    """Try interface 1 instead of 0."""
    print("\n=== VERSION 4: Interface 1 ===")
    devices = hid.enumerate(VID, PID)

    # Find interface 1
    for d in devices:
        if d["interface_number"] == 1:
            device = hid.device()
            device.open_path(d["path"])

            packet = [0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, 0xE5]
            device.write(packet)
            print("Sent RED (interface 1)")
            time.sleep(3)

            device.write([0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, INITIAL])
            device.close()
            print("Done v4")
            return
    print("Interface 1 not found")


# =============================================================================
# VERSION 5: Feature report instead of output report
# =============================================================================
def test_v5_feature_report():
    """Send as feature report."""
    print("\n=== VERSION 5: Feature report ===")
    device = hid.device()
    device.open(VID, PID)

    packet = [0x00, 0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, 0xE5]
    device.send_feature_report(packet)
    print("Sent RED (feature report)")
    time.sleep(3)

    device.send_feature_report(
        [0x00, 0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, INITIAL]
    )
    device.close()
    print("Done v5")


# =============================================================================
# VERSION 6: Simple single-byte commands
# =============================================================================
def test_v6_simple():
    """Try simpler command format."""
    print("\n=== VERSION 6: Simple commands ===")
    device = hid.device()
    device.open(VID, PID)

    # Just the command byte repeated
    for cmd in [0xE5, 0xD5, 0xB5, INITIAL]:
        packet = [cmd] * 8
        device.write(packet)
        name = {0xE5: "RED", 0xD5: "GREEN", 0xB5: "BLUE", INITIAL: "OFF"}[cmd]
        print(f"Sent {name}")
        time.sleep(1.5)

    device.close()
    print("Done v6")


# =============================================================================
# VERSION 7: All zeros except command
# =============================================================================
def test_v7_zeros():
    """Zeros with command at different positions."""
    print("\n=== VERSION 7: Zeros + command ===")
    device = hid.device()
    device.open(VID, PID)

    # Try command at each position
    for pos in range(8):
        packet = [0x00] * 8
        packet[pos] = 0xE5  # RED command
        device.write(packet)
        print(f"RED at position {pos}")
        time.sleep(1)

    device.write([0x00] * 8)
    device.close()
    print("Done v7")


# =============================================================================
# VERSION 8: Original pybuddy style (SET_REPORT)
# =============================================================================
def test_v8_all_interfaces():
    """Try writing to all interfaces."""
    print("\n=== VERSION 8: All interfaces ===")

    for d in hid.enumerate(VID, PID):
        intf = d["interface_number"]
        print(f"\nInterface {intf}:")

        device = hid.device()
        device.open_path(d["path"])

        packet = [0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, 0xE5]
        device.write(packet)
        print("  Sent RED")
        time.sleep(2)

        device.write([0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, INITIAL])
        device.close()

    print("Done v8")


# =============================================================================
# MAIN - Uncomment the version you want to test
# =============================================================================
if __name__ == "__main__":
    print("i-Buddy Test Versions")
    print("=" * 50)

    # Uncomment ONE of these to test:

    test_v1_direct_list()  # <-- This worked in terminal before
    # test_v2_with_report_id()
    # test_v3_bytes()
    # test_v4_interface1()
    # test_v5_feature_report()
    # test_v6_simple()
    # test_v7_zeros()
    # test_v8_all_interfaces()

    print("\n" + "=" * 50)
    print("Test complete!")
