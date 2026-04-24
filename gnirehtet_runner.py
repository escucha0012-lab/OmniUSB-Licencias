import subprocess
import threading
import time
import psutil
import os

class GnirehtetRunner:
    def __init__(self, executable_path="gnirehtet.exe"):
        self.executable_path = executable_path
        self.running_serials = set()
        self.relay_proc = None
        self._stop_relay = False
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.env = os.environ.copy()
        self.env["ADB"] = os.path.abspath(os.path.join(self.base_dir, r"platform-tools\adb.exe"))
        
        # Kill any zombie gnirehtet relay before starting (Clean state)
        self.kill_all_gnirehtet()
        
        # We start a single relay watchdog
        self.relay_thread = threading.Thread(target=self._relay_watchdog, daemon=True)
        self.relay_thread.start()

    def _is_relay_running(self):
        # Check system-wide if a relay is already active
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                if 'gnirehtet' in proc.info['name'].lower():
                    cmd = proc.info.get('cmdline', [])
                    if cmd and 'relay' in cmd:
                        return True
            except: pass
        return False

    def _relay_watchdog(self):
        # Wait a bit on start to ensure cleanup worked
        time.sleep(1)
        while not self._stop_relay:
            # Check if relay is running locally in this object or elsewhere in the system
            local_died = self.relay_proc is not None and self.relay_proc.poll() is not None
            if local_died: self.relay_proc = None
            
            if self.relay_proc is None and not self._is_relay_running():
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                cmd = [self.executable_path, "relay"]
                try:
                    self.relay_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, env=self.env)
                except Exception as e:
                    print(f"[GnirehtetRunner] Relay Start Error: {e}")
            
            time.sleep(3)

    def is_running(self, serial):
        return serial in self.running_serials

    def start(self, serial):
        if self.is_running(serial):
            return 

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        cmd = [self.executable_path, "start", serial]
        try:
            # We allow 15 seconds for APK installation/start
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, env=self.env, timeout=15)
            self.running_serials.add(serial)
        except Exception as e:
            print(f"[GnirehtetRunner] Failed to start {serial}: {e}")

    def stop(self, serial):
        if serial in self.running_serials:
            self.running_serials.remove(serial)
        
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            subprocess.run([self.executable_path, "stop", serial], startupinfo=startupinfo, timeout=5, env=self.env)
        except:
            pass

    def stop_all(self):
        for s in list(self.running_serials):
            self.stop(s)
            
    def kill_all_gnirehtet(self):
        # Internal stop
        self._stop_relay = True
        if self.relay_proc:
            try: self.relay_proc.kill()
            except: pass
            self.relay_proc = None
            
        # Global system cleanup
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and 'gnirehtet' in proc.info['name'].lower():
                    proc.kill()
            except: pass
        
        self.running_serials.clear()
        self._stop_relay = False
        # Re-verify watchdog thread
        if not hasattr(self, 'relay_thread') or not self.relay_thread.is_alive():
            self.relay_thread = threading.Thread(target=self._relay_watchdog, daemon=True)
            self.relay_thread.start()
