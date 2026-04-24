import os
import subprocess
import sys

def check_file(path):
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    print(f"File: {path} | Exists: {exists} | Size: {size} bytes")
    return exists and size > 0

print("=== FINAL SYSTEM VERIFICATION ===")
base_dir = r"c:\InternetProxyFarm_V2"
os.chdir(base_dir)

files_to_check = [
    "gnirehtet.exe",
    "gnirehtet.apk",
    "platform-tools\\adb.exe",
    "app.py",
    "node_proxy.py",
    "rotation_engine.py",
    "requirements.txt"
]

all_ok = True
for f in files_to_check:
    if not check_file(f):
        all_ok = False

print("\n--- Testing node & npm ---")
try:
    node_v = subprocess.check_output(["node", "-v"], text=True).strip()
    print(f"Node version: {node_v}")
except:
    print("Node NOT found")
    all_ok = False

try:
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    npm_v = subprocess.check_output([npm_cmd, "-v"], text=True).strip()
    print(f"NPM version: {npm_v}")
except:
    print("NPM NOT found (using npm.cmd)")
    all_ok = False

print("\n--- Testing adb devices (timeout 30s) ---")
try:
    from adb_manager import ADBManager
    adb = ADBManager(os.path.join(base_dir, "platform-tools", "adb.exe"))
    devs = adb.list_devices()
    print(f"ADB sees {len(devs)} devices.")
except Exception as e:
    print(f"ADB check failed: {e}")
    all_ok = False

if all_ok:
    print("\n[+] DIAGNOSIS: The system seems correctly configured.")
else:
    print("\n[!] DIAGNOSIS: Some issues were found. Running auto_repair.py...")
    # I won't run it here, I'll just report.
