import os
import subprocess

class NodeProxyManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.script_path = os.path.join(self.base_dir, "run_proxy.js")
        self.running_processes = {}
        
        js_code = """
const ProxyChain = require('proxy-chain');
const port = parseInt(process.argv[2]);
const upstreamProxy = process.argv[3]; // format: http://user:pass@ip:port

const server = new ProxyChain.Server({
    port: port,
    verbose: false,
    native: true, // Use native Node.js features for better performance
    prepareRequestFunction: () => {
        return {
            requestAuthentication: false,
            upstreamProxyUrl: (upstreamProxy === "DIRECT" || !upstreamProxy) ? null : upstreamProxy
        };
    },
});

// Optimization: increase max sockets
require('http').globalAgent.maxSockets = 100;
require('https').globalAgent.maxSockets = 100;

server.listen(() => {
    // console.log(`Proxy listening`);
});
"""
        with open(self.script_path, "w", encoding="utf-8") as f:
            f.write(js_code.strip())
            
    def download_if_missing(self):
        if not os.path.exists(os.path.join(self.base_dir, "node_modules", "proxy-chain")):
            print("[NodeProxy] Instalando proxy-chain...")
            npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
            subprocess.run([npm_cmd, "install", "proxy-chain"], cwd=self.base_dir, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True

    def start_proxy_node(self, local_port, remote_proxy_str):
        if local_port in self.running_processes:
            self.stop_proxy_node(local_port)
            
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        # Call Node
        cmd = ["node", self.script_path, str(local_port), f"http://{remote_proxy_str}"]
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
