import subprocess
import os

class ADBManager:
    def __init__(self, adb_path="platform-tools\\adb.exe"):
        # Make path absolute if it's not
        if not os.path.isabs(adb_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            adb_path = os.path.join(base_dir, adb_path)
            
        self.adb_path = adb_path
        if not os.path.exists(self.adb_path):
            # Try to use global adb if local is not found
            self.adb_path = "adb"

    def run_command(self, cmd_args, device_serial=None, retries=2, timeout=12):
        base_cmd = [self.adb_path]
        if device_serial:
            base_cmd.extend(["-s", device_serial])
        base_cmd.extend(cmd_args)
        
        last_err = ""
        for attempt in range(retries):
            try:
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
 
                result = subprocess.run(base_cmd, capture_output=True, text=True, startupinfo=startupinfo, timeout=timeout)
                if result.returncode == 0:
                    return result.stdout.strip(), result.stderr.strip(), result.returncode
                
                last_err = result.stderr.strip()
                # If it's a "device not found" or "offline" error, we might want to wait a bit
                if "not found" in last_err or "offline" in last_err:
                    import time
                    time.sleep(1 * (attempt + 1))
            except subprocess.TimeoutExpired:
                last_err = "Timeout CMD"
            except Exception as e:
                last_err = str(e)
            
        return "", last_err, -1

    def list_devices(self):
        """Returns a list of dicts with device info: serial, state, is_wifi, model, pkg_ok"""
        stdout, _, _ = self.run_command(["devices", "-l"])
        devices = []
        raw_lines = stdout.split('\n')
        
        pre_list = []
        for line in raw_lines:
            if not line.strip() or line.startswith("List of devices"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]
                if state != "device": continue
                
                is_wifi = ":" in serial or "tcp" in line.lower()
                model = "Android Device"
                for p in parts:
                    if p.startswith("model:"):
                        model = p.replace("model:", "").replace("_", " ")
                        break
                pre_list.append({'serial': serial, 'state': state, 'is_wifi': is_wifi, 'model': model})

        # Parallel Package Check
        import threading
        threads = []
        sem = threading.Semaphore(10)
        
        def _check_pkg(dev_info):
            with sem:
                out, _, _ = self.run_command(["shell", "pm", "list", "packages", "com.genymobile.gnirehtet"], dev_info['serial'])
                dev_info['pkg_ok'] = ("package:com.genymobile.gnirehtet" in out)
                devices.append(dev_info)

        for dev in pre_list:
            t = threading.Thread(target=_check_pkg, args=(dev,))
            t.start()
            threads.append(t)
        
        for t in threads: t.join()
        return devices

    def install_apk(self, device_serial, apk_path):
        stdout, stderr, code = self.run_command(["install", "-r", apk_path], device_serial)
        return "Success" in stdout

    def is_package_installed(self, device_serial, package_name):
        stdout, _, _ = self.run_command(["shell", "pm", "list", "packages"], device_serial)
        return package_name in stdout

    def set_global_proxy(self, device_serial, proxy_ip, proxy_port):
        # proxy_ip:proxy_port like 192.168.1.5:8080
        cmd = ["shell", "settings", "put", "global", "http_proxy", f"{proxy_ip}:{proxy_port}"]
        _, _, code = self.run_command(cmd, device_serial)
        return code == 0

    def clear_global_proxy(self, device_serial):
        # Multiple clearing methods for Android 10-14 compatibility
        self.run_command(["shell", "settings", "delete", "global", "http_proxy"], device_serial)
        self.run_command(["shell", "settings", "delete", "global", "global_http_proxy_host"], device_serial)
        self.run_command(["shell", "settings", "delete", "global", "global_http_proxy_port"], device_serial)
        # Final fallback check
        self.run_command(["shell", "settings", "put", "global", "http_proxy", ":0"], device_serial)
        return True

    def boost_network_speed(self, device_serial):
        """Optimiza configuraciones de red para evitar latencia en túneles."""
        self.run_command(["shell", "settings", "put", "global", "captive_portal_mode", "0"], device_serial)
        self.run_command(["shell", "settings", "put", "global", "captive_portal_detection_enabled", "0"], device_serial)
        return True

    def get_real_ip(self, device_serial):
        stdout, _, _ = self.run_command(["shell", "settings", "get", "global", "http_proxy"], device_serial)
        proxy_val = stdout.strip()
        
        import requests
        proxies = None
        local_assignment = "Directo (:0)"
        if proxy_val and proxy_val != "null" and proxy_val != ":0" and ":" in proxy_val:
            proxies = {
                "http": f"http://{proxy_val}",
                "https": f"http://{proxy_val}"
            }
            local_assignment = f"Asignado Local: {proxy_val}"
            
        try:
            res = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=5)
            ip = res.json().get("ip", "")
            return local_assignment, f"🌍 {ip}"
        except Exception as e:
            if proxies:
                return local_assignment, "❌ PROXY MUERTO"
            return local_assignment, "❌ SIN CONEXIÓN"
