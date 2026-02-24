#!/usr/bin/env python3
"""
Isolate which HID write method actually works for i-Buddy.
Run this and tell me which step makes it light up!

Usage: uv run python scripts/test_ibuddy_isolate.py
"""

import hid
import time

VID = 0x1130
PID = 0x0001

# Commands
RESET = [0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, 0xF5]  # All off
RED = [0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, 0xE5]    # Red on

def get_devices():
    """Get all i-Buddy interfaces."""
    return hid.enumerate(VID, PID)

def test_method(device, method_name, method_func):
    """Test a single method and wait for user observation."""
    print(f"\n>>> TEST: {method_name}")
    print("    Sending RED...")
    try:
        method_func()
        print("    Command sent! IS IT RED? (waiting 5 seconds)")
        time.sleep(5)
    except Exception as e:
        print(f"    ERROR: {e}")

    print("    Sending OFF...")
    try:
        # Always try basic write for OFF
        device.write(RESET)
    except:
        pass
    time.sleep(1)

def main():
    devices = get_devices()
    print(f"Found {len(devices)} i-Buddy interface(s)")

    for i, dev_info in enumerate(devices):
        intf = dev_info['interface_number']
        print(f"\n{'='*60}")
        print(f"INTERFACE {intf} (device {i})")
        print(f"{'='*60}")

        device = hid.device()
        device.open_path(dev_info['path'])

        # Test 1: Basic write (list)
        test_method(device, f"Interface {intf} - write(list)",
                   lambda: device.write(RED))

        # Test 2: Write with 0x00 prefix
        test_method(device, f"Interface {intf} - write([0x00] + list)",
                   lambda: device.write([0x00] + RED))

        # Test 3: Feature report
        test_method(device, f"Interface {intf} - send_feature_report",
                   lambda: device.send_feature_report([0x00] + RED))

        # Test 4: Bytes instead of list
        test_method(device, f"Interface {intf} - write(bytes)",
                   lambda: device.write(bytes(RED)))

        # Test 5: Bytes with 0x00 prefix
        test_method(device, f"Interface {intf} - write(bytes with 0x00)",
                   lambda: device.write(bytes([0x00] + RED)))

        device.close()

    print("\n" + "="*60)
    print("ALL TESTS COMPLETE")
    print("Which test number made it turn RED?")

if __name__ == "__main__":
    main()
