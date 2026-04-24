from adb_manager import ADBManager
import os

adb = ADBManager()
print(f"ADB Path: {adb.adb_path}")
devices = adb.list_devices()
print(f"Found {len(devices)} devices:")
for d in devices:
    print(d)
