import time
import os
from gnirehtet_runner import GnirehtetRunner
from adb_manager import ADBManager

base_dir = r"c:\InternetProxyFarm_V2"
os.chdir(base_dir)

print("--- MULTI-DEVICE GNIREHTET TEST ---")
adb = ADBManager(os.path.join(base_dir, "platform-tools", "adb.exe"))
runner = GnirehtetRunner(executable_path=os.path.join(base_dir, "gnirehtet.exe"))

# Use two random devices from the list
devs = adb.list_devices()
if len(devs) < 2:
    print("Need at least 2 devices for this test.")
    exit(1)

s1 = devs[0]['serial']
s2 = devs[1]['serial']

print(f"Starting {s1}...")
runner.start(s1)
print(f"Starting {s2}...")
runner.start(s2)

print("Waiting 10s for stability...")
time.sleep(10)

print(f"Checking {s1}...")
out1, _, _ = adb.run_command(["shell", "ip addr show"], s1)
print(f"[{s1}] tun0 found: {'tun0' in out1 or 'vpn' in out1}")

print(f"Checking {s2}...")
out2, _, _ = adb.run_command(["shell", "ip addr show"], s2)
print(f"[{s2}] tun0 found: {'tun0' in out2 or 'vpn' in out2}")

print("Cleaning up...")
runner.stop_all()
runner.kill_all_gnirehtet()
print("Test finished.")
