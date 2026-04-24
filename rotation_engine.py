import time
import threading
from node_proxy import NodeProxyManager
from tunnel_logger import log, log_session_start, log_session_end

def format_proxy(p_str):
    p_str = p_str.strip()
    if not p_str or p_str.startswith("#"):
        return None
    if "@" in p_str:
        return p_str
    
    parts = p_str.split(":")
    if len(parts) == 4:
        if "." in parts[0]:
            ip, port, user, pw = parts
            return f"{user}:{pw}@{ip}:{port}"
        elif "." in parts[2]:
            user, pw, ip, port = parts
            return f"{user}:{pw}@{ip}:{port}"
    return p_str

class RotationEngine:
    def __init__(self, adb_manager, runner, on_update_callback=None, app_instance=None):
        self.adb = adb_manager
        self.runner = runner
        self.on_update = on_update_callback
        self.app = app_instance
        self.pm = NodeProxyManager()
        
        self.running = False
        self.paused = False
        self.thread = None
        self._health_thread = None

        self.all_devices = []
        self.proxies = []
        self.batch_size = 10
        self.interval_minutes = 60
        self.infinite_loop = True

        self.current_batch_index = 0
        self.active_devices = []
        self.active_ports = {}
        self.next_rotation_time = 0
        self.base_port = 8000
        self.lock = threading.Lock()
        self.semaphore = threading.Semaphore(10)
        self.custom_mapping = {} # serial -> proxy_string

        # Monitor de salud — configuración
        self._HEALTH_INTERVAL = 60   # segundos entre chequeos
        self._HEALTH_THRESHOLD = 2   # fallos consecutivos antes de reconectar

    def start_rotation(self, devices, proxies, batch_size, interval_minutes, infinite_loop, stealth=False):
        self.pm.download_if_missing()
        
        self.all_devices = devices
        self.proxies = [format_proxy(p) for p in proxies if format_proxy(p)]
        self.batch_size = batch_size
        self.interval_minutes = interval_minutes
        self.infinite_loop = infinite_loop
        self.stealth = stealth

        self.running = True
        self.current_batch_index = 0

        log_session_start(devices, self.proxies)

        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

        # Arrancar monitor de salud
        self._health_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
        self._health_thread.start()

    def stop_rotation(self):
        self.running = False
        self.paused = False
        self._cleanup_batch(self.active_devices)
        self.pm.stop_all()
        self.active_devices = []
        self.active_ports = {}
        log_session_end()

    def _cleanup_batch(self, batch):
        if not batch: return
        threads = []
        def _clear_one(device):
            serial = device['serial']
            with self.semaphore:
                self.runner.stop(serial)
                self.adb.clear_global_proxy(serial)
                port = self.active_ports.get(serial)
                if port:
                    self.pm.stop_proxy_node(port)
                    self.adb.run_command(["reverse", "--remove", f"tcp:{port}"], serial)
                # Autorestore Wifi
                self.adb.run_command(["shell", "svc", "wifi", "enable"], serial)

        for device in batch:
            t = threading.Thread(target=_clear_one, args=(device,))
            t.start()
            threads.append(t)
        
        for t in threads: t.join()
        self.active_ports = {}

    def _apply_batch(self, batch):
        proxy_count = len(self.proxies)
        
        def _setup_one(i, device):
            serial = device['serial']
            success = False
            
            with self.semaphore:
                # 1. Start Gnirehtet Client
                self.runner.start(serial)
                self.adb.boost_network_speed(serial)
                time.sleep(1) # Wait for APK start
                
                # Proxy selection logic
                target_proxy = self.custom_mapping.get(serial)
                if not target_proxy and proxy_count > 0:
                    target_proxy = self.proxies[i % proxy_count]

                # Fallback to DIRECT mode if no proxy is assigned (enables navigation in "No Proxy" mode)
                effective_proxy = target_proxy if target_proxy else "DIRECT"

                local_port = self.base_port + i
                self.pm.start_proxy_node(local_port, effective_proxy)
                
                # 3. ADB Reverse Tunnel
                for _ in range(2):
                    self.adb.run_command(["reverse", f"tcp:{local_port}", f"tcp:{local_port}"], serial)
                
                self.adb.set_global_proxy(serial, "127.0.0.1", str(local_port))
                with self.lock:
                    self.active_ports[serial] = local_port
                    
                self.adb.run_command(["shell", "svc", "wifi", "disable"], serial)
                
                # Validation (Retry for up to 10 seconds for the tunnel to stabilize)
                for _ in range(10):
                    time.sleep(1)
                    # Check both 'tun0' (classic) and 'vpn' related interfaces
                    out, _, _ = self.adb.run_command(["shell", "ip addr show"], serial)
                    if "tun0" in out or "vpn" in out or "10.0.2.15" in out:
                        success = True
                        break
            
            if not success:
                msg = f"Falla de Túnel: {serial}. Red no establecida."
                print(f"[RotationEngine] {msg}")
                if self.app: self.app.log_msg(msg, "warn")
            else:
                msg = f"Túnel OK: {serial}."
                if self.app: self.app.log_msg(msg, "info")

        if self.stealth:
            import random
            for i, device in enumerate(batch):
                if i > 0:
                    time.sleep(random.randint(5, 25))
                _setup_one(i, device)
        else:
            threads = []
            for i, device in enumerate(batch):
                t = threading.Thread(target=_setup_one, args=(i, device))
                t.start()
                threads.append(t)
            for t in threads: t.join()
                
        self.active_devices = batch

    def _loop(self):
        while self.running:
            start_idx = self.current_batch_index * self.batch_size
            end_idx = start_idx + self.batch_size
            batch = self.all_devices[start_idx:end_idx]
            
            if not batch: # End of list
                if self.infinite_loop:
                    self.current_batch_index = 0
                    continue
                else:
                    self.stop_rotation()
                    if self.on_update: self.on_update("COMPLETED")
                    break
                
            self._cleanup_batch(self.active_devices)
            self._apply_batch(batch)
            
            self.next_rotation_time = time.time() + (self.interval_minutes * 60)
            
            while self.running and time.time() < self.next_rotation_time:
                if self.paused:
                    # Delay the rotation end time while paused
                    self.next_rotation_time += 1
                elif self.on_update: 
                    self.on_update("TICK")
                time.sleep(1)
                
            self.current_batch_index += 1

    def _health_monitor_loop(self):
        """
        Hilo de fondo que chequea cada 60 seg si el túnel de cada celular
        sigue activo. Si falla 2 veces seguidas, reconecta automáticamente.
        """
        fail_counts = {}  # serial -> int

        # Esperar a que los túneles terminen de establecerse antes del primer chequeo
        time.sleep(self._HEALTH_INTERVAL)

        while self.running:
            if self.paused:
                time.sleep(5)
                continue

            for device in list(self.active_devices):
                if not self.running:
                    break

                serial = device['serial']
                port   = self.active_ports.get(serial)
                proxy  = self.custom_mapping.get(serial) or (
                    self.proxies[list(self.active_ports.keys()).index(serial) % len(self.proxies)]
                    if self.proxies else None
                )

                # ── Chequeo: buscar interfaz tun0 en el celular ──
                try:
                    out, _, _ = self.adb.run_command(["shell", "ip addr show"], serial)
                    tunnel_ok = "tun0" in out or "vpn" in out or "10.0.2.15" in out
                except Exception:
                    tunnel_ok = False

                if tunnel_ok:
                    # Túnel sano — resetear contador
                    if fail_counts.get(serial, 0) > 0:
                        log("INFO", serial, "Túnel estable — contador reseteado", port, proxy)
                    fail_counts[serial] = 0
                else:
                    # Túnel caído — incrementar contador
                    fail_counts[serial] = fail_counts.get(serial, 0) + 1
                    count = fail_counts[serial]

                    log("WARN", serial,
                        f"tun0 no responde — falla {count}/{self._HEALTH_THRESHOLD}",
                        port, proxy)

                    if self.app:
                        self.app.log_msg(
                            f"⚠️  Túnel caído: {serial} "
                            f"(falla {count}/{self._HEALTH_THRESHOLD})", "warn")

                    if count >= self._HEALTH_THRESHOLD:
                        # ── Reconexión automática ──
                        log("RECONECT", serial,
                            "Iniciando reconexión automática...", port, proxy)

                        if self.app:
                            self.app.log_msg(f"♻️  Reconectando: {serial}...", "warn")

                        success, reason = self.reconnect_device(serial)
                        fail_counts[serial] = 0  # resetear tras intentar

                        if success:
                            log("OK", serial, f"Recuperado — {reason}", port, proxy)
                            if self.app:
                                self.app.log_msg(f"✅ {serial} reconectado: {reason}", "info")
                        else:
                            log("ERROR", serial,
                                f"Falla total tras reconexión — {reason}", port, proxy)
                            if self.app:
                                self.app.log_msg(
                                    f"❌ {serial} no se pudo reconectar: {reason}", "error")

            # Esperar hasta el próximo ciclo
            for _ in range(self._HEALTH_INTERVAL):
                if not self.running:
                    break
                time.sleep(1)

    def reconnect_device(self, serial):
        """Reconnect a single device without stopping others. Returns (success, reason)."""
        # 1. Find the device and its index in active_devices
        device = None
        dev_index = 0
        for i, d in enumerate(self.active_devices):
            if d['serial'] == serial:
                device = d
                dev_index = i
                break
        if not device:
            return False, "Dispositivo no está en el lote activo"

        # 2. Clean up this specific device
        self.runner.stop(serial)
        self.adb.clear_global_proxy(serial)
        port = self.active_ports.get(serial)
        if port:
            self.pm.stop_proxy_node(port)
            self.adb.run_command(["reverse", "--remove", f"tcp:{port}"], serial)
        time.sleep(1)

        # 3. Restart gnirehtet
        self.runner.start(serial)
        time.sleep(2)

        # 4. Re-apply proxy
        proxy_count = len(self.proxies)
        target_proxy = self.custom_mapping.get(serial)
        if not target_proxy and proxy_count > 0:
            target_proxy = self.proxies[dev_index % proxy_count]

        # Use DIRECT mode if no proxy is assigned
        effective_proxy = target_proxy if target_proxy else "DIRECT"

        local_port = self.base_port + dev_index
        self.pm.start_proxy_node(local_port, effective_proxy)
        time.sleep(1)
        for _ in range(2):
            self.adb.run_command(["reverse", f"tcp:{local_port}", f"tcp:{local_port}"], serial)
        self.adb.set_global_proxy(serial, "127.0.0.1", str(local_port))
        with self.lock:
            self.active_ports[serial] = local_port

        self.adb.run_command(["shell", "svc", "wifi", "disable"], serial)

        # 5. Validate tunnel
        for _ in range(8):
            time.sleep(1)
            out, _, _ = self.adb.run_command(["shell", "ip addr show"], serial)
            if "tun0" in out or "vpn" in out:
                # 6. Validate internet
                ip_out, _, _ = self.adb.run_command(["shell", "curl", "-s", "--max-time", "5", "ifconfig.me"], serial)
                if ip_out and "." in ip_out:
                    return True, f"Reconectado OK — IP: {ip_out.strip()}"
                else:
                    if target_proxy:
                        return False, f"Túnel OK pero proxy sin respuesta ({target_proxy.split('@')[-1] if '@' in target_proxy else 'directo'})"
                    return False, "Túnel OK pero sin internet"
        return False, "Túnel no se establece — Cable USB o Gnirehtet con fallo"
