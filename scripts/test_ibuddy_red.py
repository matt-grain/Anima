import hid
import time

VID = 0x1130
PID = 0x0001

print('Replicating the EXACT test that worked...')
print('=' * 50)

reset = [0x22, 0x09, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00]
cmd_red = [0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, 0xE5]

for dev_info in hid.enumerate(VID, PID):
    intf = dev_info['interface_number']
    print(f'\\nTrying interface {intf}...')

    device = hid.device()
    device.open_path(dev_info['path'])

    # Sending reset with ALL methods
    print('  Sending reset...')
    device.write(reset)
    device.write([0x00] + reset)
    device.send_feature_report([0x00] + reset)

    time.sleep(0.5)

    # Sending RED with ALL methods
    print('  Sending RED...')
    device.write(cmd_red)
    device.write([0x00] + cmd_red)
    device.send_feature_report([0x00] + cmd_red)

    print('  >>> CHECK NOW - IS IT RED? <<<')
    time.sleep(3)

    device.close()

print('\\nDone!')