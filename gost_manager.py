import os
import urllib.request
import zipfile
import subprocess
import shutil

class GostManager:
    def __init__(self, executable_name="gost.exe"):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.executable_path = os.path.join(self.base_dir, executable_name)
        self.running_processes = {}
        
    def download_if_missing(self):
        if os.path.exists(self.executable_path):
            return True
            
        print("[GostManager] Downloading GOST...")
        zip_path = os.path.join(self.base_dir, "gost_dl.zip")
        temp_dir = os.path.join(self.base_dir, "gost_temp")
        
        try:
            import requests
            url = "https://github.com/ginuerzh/gost/releases/download/v2.11.5/gost-windows-amd64-2.11.5.zip"
            r = requests.get(url, allow_redirects=True)
            with open(zip_path, 'wb') as f:
                f.write(r.content)
                
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(temp_dir)
            
            # Find the exe
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(".exe"):
                        os.rename(os.path.join(root, file), self.executable_path)
            
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            if os.path.exists(zip_path): os.remove(zip_path)
            return True
        except Exception as e:
            print("[GostManager] Error downloading GOST:", e)
            return False

    def start_proxy_node(self, local_port, remote_proxy_str):
        if local_port in self.running_processes:
            self.stop_proxy_node(local_port)
            
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        cmd = [self.executable_path, "-L", f"http://127.0.0.1:{local_port}", "-F", f"http://{remote_proxy_str}"]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo)
        self.running_processes[local_port] = proc
        return True

    def stop_proxy_node(self, local_port):
        if local_port in self.running_processes:
            try:
                self.running_processes[local_port].terminate()
            except:
                pass
            del self.running_processes[local_port]

    def stop_all(self):
        ports = list(self.running_processes.keys())
        for port in ports:
            self.stop_proxy_node(port)
