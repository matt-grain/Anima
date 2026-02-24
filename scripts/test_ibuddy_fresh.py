#!/usr/bin/env python3
"""
Test i-Buddy immediately after plugging in.
UNPLUG AND REPLUG THE DEVICE, THEN RUN THIS IMMEDIATELY.
"""

import hid
import time

VID = 0x1130
PID = 0x0001

print("Opening device...")
device = hid.device()
device.open(VID, PID)
print("Connected!")

# The exact command that worked: RED
print("Sending RED...")
device.write([0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, 0xE5])

print("Waiting 5 seconds - IS IT RED?")
time.sleep(5)

print("Sending GREEN...")
device.write([0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, 0xD5])

print("Waiting 5 seconds - IS IT GREEN?")
time.sleep(5)

print("OFF")
device.write([0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, 0xF5])

device.close()
print("Done!")
