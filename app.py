import json
import os
import random
import subprocess
import customtkinter as ctk
import threading
import time
from tkinter import messagebox
import sys
import traceback

def crash_logger(ex_cls, ex, tb):
    with open("CRASH_REPORT.txt", "w", encoding="utf-8") as f:
        traceback.print_exception(ex_cls, ex, tb, file=f)
    sys.__excepthook__(ex_cls, ex, tb)
sys.excepthook = crash_logger
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from adb_manager import ADBManager
from gnirehtet_runner import GnirehtetRunner
from rotation_engine import RotationEngine
from proxy_tester import ProxyTester
from updater import check_for_updates_async, download_update, get_local_version

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

_ACCESS_PASSWORD = "Androide10"

class PasswordWindow(ctk.CTkToplevel):
    def __init__(self, master, on_success_callback):
        super().__init__(master)
        self.title("🔒 OmniUSB - Acceso")
        self.geometry("380x230")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.resizable(False, False)
        self.on_success = on_success_callback

        ctk.CTkLabel(self, text="OmniUSB ProxyFarm", font=("Arial", 20, "bold"), text_color="#3B82F6").pack(pady=(25, 5))
        ctk.CTkLabel(self, text="Introduce la contraseña para continuar:", font=("Arial", 12)).pack(pady=5)

        self.pwd_entry = ctk.CTkEntry(self, width=250, justify="center", show="*", placeholder_text="Contraseña")
        self.pwd_entry.pack(pady=8)
        self.pwd_entry.bind("<Return>", lambda e: self.do_verify())

        self.status_lbl = ctk.CTkLabel(self, text="", font=("Arial", 12))
        self.status_lbl.pack(pady=2)

        ctk.CTkButton(self, text="Entrar", fg_color="#10B981", height=36,
                      font=("Arial", 14, "bold"), command=self.do_verify).pack(pady=10, padx=40, fill="x")

    def on_close(self):
        import sys
        sys.exit(0)

    def do_verify(self):
        if self.pwd_entry.get().strip() == _ACCESS_PASSWORD:
            self.destroy()
            self.on_success()
        else:
            self.status_lbl.configure(text="❌ Contraseña incorrecta.", text_color="red")
            self.pwd_entry.delete(0, "end")


class ReporteGlobalWindow(ctk.CTkToplevel):
    def __init__(self, master, adb, engine):
        super().__init__(master)
        self.title("🩺 Diagnóstico Global del Lote Activo")
        self.geometry("500x400")
        self.attributes("-topmost", True)
        
        self.adb = adb
        self.engine = engine
        
        ctk.CTkLabel(self, text="Verificando Conexiones en Curso...", font=("Arial", 16, "bold")).pack(pady=10)
        
        self.log_box = ctk.CTkTextbox(self, width=450, height=300)
        self.log_box.pack(pady=10)
        
        threading.Thread(target=self.run_report, daemon=True).start()

    def run_report(self):
        activos = self.engine.active_devices.copy()
        if not activos:
            self.log_box.insert("end", "⚠️ No hay ningún celular activo en este momento.")
            return
            
        self.log_box.insert("end", f"[*] Escaneando salida de {len(activos)} celulares...\n\n")
        
        for dev in activos:
            s = dev['serial']
            cfg, ip = self.adb.get_real_ip(s)
            state = "🟢 OK" if "MUERTO" not in ip and "SIN" not in ip else "🔴 FALLA"
            self.log_box.insert("end", f"{state} | {s}\n   └─ {cfg}\n   └─ {ip}\n\n")
            self.log_box.see("end")

class ProxyTesterWindow(ctk.CTkToplevel):
    def __init__(self, master, proxies, callback_finish):
        super().__init__(master)
        self.title("🔍 Probador Láser de Proxies")
        self.geometry("600x450")
        self.attributes("-topmost", True)
        self.proxies = proxies
        self.callback_finish = callback_finish
        
        ctk.CTkLabel(self, text="Escaneando Proxies en Paralelo...", font=("Arial", 16, "bold")).pack(pady=10)
        self.progress = ctk.CTkProgressBar(self, width=500)
        self.progress.pack(pady=10)
        self.progress.set(0.0)
        
        self.status = ctk.CTkLabel(self, text="Verificando 0 / 0")
        self.status.pack(pady=5)
        
        self.log_box = ctk.CTkTextbox(self, width=550, height=250)
        self.log_box.pack(pady=10)
        
        threading.Thread(target=self.run_test, daemon=True).start()
        
    def add_log(self, text, color="white"):
        if not self.winfo_exists(): return
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def log_update(self, c, total, p, is_alive):
        if not self.winfo_exists(): return
        self.progress.set(c / total)
        self.status.configure(text=f"Verificados {c} de {total}")
        res = "🟢 VIVO" if is_alive else "🔴 MUERTO"
        self.add_log(f"{res} | {p}")
        
    def run_test(self):
        def _final(results):
            a = len(results["alive"])
            d = len(results["dead"])
            self.add_log(f"\n--- PRUEBA FINALIZADA ---")
            self.add_log(f"✅ Vivos: {a}")
            self.add_log(f"💥 Muertos: {d}")
            self.add_log("Limpiando lista automáticamente en 3 segundos...")
            time.sleep(3)
            self.callback_finish(results["alive"])
            self.destroy()
            
        ProxyTester.test_proxies_async(self.proxies, self.log_update, _final)

class PanicProgressWindow(ctk.CTkToplevel):
    def __init__(self, master, engine, runner, adb):
        super().__init__(master)
        self.title("🧹 Limpieza Global en Progreso...")
        self.geometry("550x450")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
        self.master = master
        self.engine = engine
        self.runner = runner
        self.adb = adb
        
        ctk.CTkLabel(self, text="EJECUTANDO PROTOCOLO PANIC", text_color="red", font=("Arial", 16, "bold")).pack(pady=10)
        
        self.progress = ctk.CTkProgressBar(self, width=400)
        self.progress.pack(pady=10)
        self.progress.set(0.0)
        
        self.status_box = ctk.CTkTextbox(self, width=450, height=200)
        self.status_box.pack(pady=10)
        self.status_box.insert("end", "[X] Escaneando procesos...\n")
        
        threading.Thread(target=self.run_cleanup, daemon=True).start()

    def log(self, text):
        if not self.winfo_exists(): return
        self.status_box.insert("end", text + "\n")
        self.status_box.see("end")

    def do_nothing(self): pass
        
    def run_cleanup(self):
        time.sleep(1)
        self.progress.set(0.2)
        
        self.log("[✓] Deteniendo motor rotante...")
        self.engine.stop_rotation()
        time.sleep(1)
        
        self.progress.set(0.4)
        self.log("[✓] Deteniendo todos los Gnirehtet del PC...")
        self.runner.kill_all_gnirehtet()
        
        try:
            self.log("[✓] Destruyendo servidores NodeProxy...")
            self.engine.pm.stop_all()
        except: pass
        self.progress.set(0.6)
        
        devices = self.adb.list_devices()
        total = len(devices)
        if total == 0:
            self.progress.set(0.9)
        else:
            self.log(f"[✓] Liberando red y reactivando Wi-Fi en {total} celulares...")
            for i, dev in enumerate(devices):
                s = dev['serial']
                self.adb.clear_global_proxy(s)
                self.adb.run_command(["reverse", "--remove-all"], s)
                self.adb.run_command(["shell", "svc", "wifi", "enable"], s) # Auto-wifi on para TODOS
                p = 0.6 + (0.3 * ((i+1)/total))
                self.progress.set(p)

        self.progress.set(1.0)
        self.log("\n✅ ¡PANIC COMPLETADO! Todos limpios y con Wi-Fi encendido.")
        self.master.log_msg("Procesos abortados y Wi-fi habilitado. Granja en estado original.", "warn")
        self.master.status_lbl.configure(text="Estado: LIMPIO 🧽")
        self.master.start_btn.configure(state="normal")
        self.master.pause_btn.configure(state="disabled", text="⏸️ PAUSAR")
        self.master.clean_btn.configure(state="normal")
        
        # Restore close button and auto-destroy after 3 seconds
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        btn = ctk.CTkButton(self, text="Cerrar Ventana", command=self.destroy, fg_color="#EF4444")
        btn.pack(pady=10)
        self.after(3000, self.destroy)

class ScanProgressWindow(ctk.CTkToplevel):
    def __init__(self, master, adb_manager, finish_cb):
        super().__init__(master)
        self.title("🔍 Escaneando Dispositivos")
        self.geometry("500x350")
        self.attributes("-topmost", True)
        
        self.master = master
        self.adb = adb_manager
        self.finish_cb = finish_cb
        
        ctk.CTkLabel(self, text="RECONOCIENDO HARDWARE", text_color="#F59E0B", font=("Arial", 16, "bold")).pack(pady=15)
        self.progress = ctk.CTkProgressBar(self, width=400)
        self.progress.set(0.1)
        self.progress.pack(pady=10)
        
        self.status_lbl = ctk.CTkLabel(self, text="Enviando señales ADB...")
        self.status_lbl.pack(pady=5)
        
        self.tip_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=10)
        self.tip_frame.pack(fill="x", padx=25, pady=20)
        self.tip_lbl = ctk.CTkLabel(self.tip_frame, text=self.master.tips[0], wraplength=450)
        self.tip_lbl.pack(pady=10)
        
        threading.Thread(target=self.run_scan, daemon=True).start()

    def run_scan(self):
        self.progress.set(0.3)
        self.after(500, lambda: self.status_lbl.configure(text="Esperando respuesta de hubs USB..."))
        devs = self.adb.list_devices() # This also fetches models now
        self.progress.set(0.8)
        self.after(500, lambda: self.status_lbl.configure(text=f"¡Encontrados {len(devs)} teléfonos!"))
        time.sleep(1)
        self.after(0, self.finish_cb, devs)
        self.destroy()

class SetupProgressWindow(ctk.CTkToplevel):
    def __init__(self, master, devices, proxies, b_size, mins):
        super().__init__(master)
        self.title("🚀 Iniciando Granja de Proxies")
        self.geometry("600x480")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
        self.master = master
        self.devices = devices
        self.proxies = proxies
        self.b_size = b_size
        self.mins = mins
        
        ctk.CTkLabel(self, text="MODO ARRANQUE ACTIVO", text_color="#3B82F6", font=("Arial", 18, "bold")).pack(pady=15)
        
        self.progress = ctk.CTkProgressBar(self, width=500)
        self.progress.pack(pady=10)
        self.progress.set(0.05)
        
        self.status_lbl = ctk.CTkLabel(self, text="Inicializando componentes...", font=("Arial", 12, "italic"))
        self.status_lbl.pack(pady=5)
        
        self.log_box = ctk.CTkTextbox(self, width=550, height=200)
        self.log_box.pack(pady=10)
        
        self.tip_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=10)
        self.tip_frame.pack(fill="x", padx=25, pady=10)
        self.tip_lbl = ctk.CTkLabel(self.tip_frame, text=self.master.tips[0], wraplength=500)
        self.tip_lbl.pack(pady=10)
        
        self.disable_master_buttons()
        threading.Thread(target=self.run_setup, daemon=True).start()
        threading.Thread(target=self.rotate_tips, daemon=True).start()

    def do_nothing(self): pass

    def log(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def disable_master_buttons(self):
        self.master.start_btn.configure(state="disabled")
        self.master.scan_btn.configure(state="disabled")
        self.master.install_btn.configure(state="disabled")
        self.master.clean_btn.configure(state="disabled")

    def enable_master_buttons(self):
        self.master.start_btn.configure(state="disabled") # starts stays off while running
        self.master.pause_btn.configure(state="normal")
        self.master.scan_btn.configure(state="normal") 
        self.master.clean_btn.configure(state="normal")

    def rotate_tips(self):
        while self.winfo_exists():
            time.sleep(6)
            if self.winfo_exists():
                self.after(0, lambda: self.tip_lbl.configure(text=random.choice(self.master.tips)))

    def run_setup(self):
        self.log("[*] Paso 1: Asegurando integridad de dependencias...")
        self.status_lbl.configure(text="Verificando Node/NPM...")
        self.master.engine.pm.download_if_missing()
        self.progress.set(0.2)
        time.sleep(1)
        
        self.log("[*] Paso 2: Ejecutando Candado Maestro (Wi-Fi Disable)...")
        threads = []
        total = len(self.devices)
        for i, d in enumerate(self.devices):
            def _kill():
                self.master.adb.run_command(["shell", "svc", "wifi", "disable"], d['serial'])
            t = threading.Thread(target=_kill)
            t.start()
            threads.append(t)
            self.progress.set(0.2 + (0.3 * ((i+1)/total)))
            self.status_lbl.configure(text=f"Bloqueando Wi-Fi... {i+1}/{total}")
        
        for t in threads: t.join()
        self.log("[✓] Wi-Fi bloqueado en todos.")
        
        self.log("[*] Paso 3: Lanzando Motor de Rotación...")
        self.status_lbl.configure(text="Sincronizando teléfonos con proxies...")
        self.progress.set(0.6)
        
        # Start rotation on main thread via after
        self.after(0, lambda: self.master.engine.start_rotation(
            self.devices, self.proxies, self.b_size, self.mins, 
            self.master.infinite_var.get(), self.master.stealth_var.get()
        ))
        
        self.progress.set(0.9)
        time.sleep(2)
        self.progress.set(1.0)
        self.log("\n✅ ¡SISTEMA OPERATIVO Y PROTEGIDO!")
        self.status_lbl.configure(text="Lanzamiento completado con éxito.")
        
        self.enable_master_buttons()
        # Restore close button and add button
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        btn = ctk.CTkButton(self, text="Perfecto, Continuar", command=self.destroy, fg_color="#10B981")
        btn.pack(pady=10)
        self.after(4000, self.destroy)

class ProxyAssignmentWindow(ctk.CTkToplevel):
    def __init__(self, master, devices, proxies):
        super().__init__(master)
        self.title("🎯 Mapeado Manual de Proxies")
        self.geometry("800x600")
        self.attributes("-topmost", True)
        
        self.master = master
        self.devices = devices
        self.proxies = proxies # Formatted list
        self.entries = {} # serial -> StringVar
        
        ctk.CTkLabel(self, text="ASIGNACIÓN DISPOSITIVO <-> PROXY", font=("Arial", 20, "bold"), text_color="#3B82F6").pack(pady=20)
        
        # Scrollable area
        self.scroll = ctk.CTkScrollableFrame(self, width=750, height=400)
        self.scroll.pack(padx=20, pady=10, fill="both", expand=True)
        
        for dev in self.devices:
            s = dev['serial']
            row = ctk.CTkFrame(self.scroll, fg_color="#1E1E1E", corner_radius=5)
            row.pack(fill="x", pady=2, padx=5)
            
            ctk.CTkLabel(row, text=f"{dev.get('model','Phone')} ({s})", width=250, anchor="w").pack(side="left", padx=10)
            
            p_var = ctk.StringVar(value=self.master.engine.custom_mapping.get(s, ""))
            self.entries[s] = p_var
            
            combo = ctk.CTkComboBox(row, values=["(Automático)"] + self.proxies, variable=p_var, width=400)
            combo.pack(side="left", padx=10, pady=5)

        # Buttons
        btn_fr = ctk.CTkFrame(self, fg_color="transparent")
        btn_fr.pack(pady=20)
        
        ctk.CTkButton(btn_fr, text="🎲 Mapeado Automático (1 a 1)", command=self.auto_map, fg_color="#6366F1").pack(side="left", padx=10)
        ctk.CTkButton(btn_fr, text="💾 Guardar Mapeado", command=self.save_map, fg_color="#10B981").pack(side="left", padx=10)
        ctk.CTkButton(btn_fr, text="❌ Limpiar Todo", command=self.clear_map, fg_color="#EF4444").pack(side="left", padx=10)

    def auto_map(self):
        for i, s in enumerate(self.entries.keys()):
            if i < len(self.proxies):
                self.entries[s].set(self.proxies[i])
            else:
                self.entries[s].set("(Automático)")

    def clear_map(self):
        for var in self.entries.values():
            var.set("(Automático)")

    def save_map(self):
        new_map = {}
        for s, var in self.entries.items():
            val = var.get()
            if val and val != "(Automático)":
                new_map[s] = val
        self.master.engine.custom_mapping = new_map
        self.master.log_msg(f"🎯 Mapeado guardado: {len(new_map)} dispositivos asignados manualmente.")
        self.destroy()

class ProxyFarmApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OmniUSB Director 🌍 [Stealth Proxy Edition]")
        self.geometry("1200x900")
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.adb = ADBManager(os.path.join(base_dir, "platform-tools", "adb.exe"))
        self.runner = GnirehtetRunner(executable_path=os.path.join(base_dir, "gnirehtet.exe"))
        self.engine = RotationEngine(self.adb, self.runner, self.on_engine_update, app_instance=self)
        
        self.no_proxy_strikes = 0
        self.scanned_devices = []  # Stores last scan results
        self.device_selections = {}  # serial -> BooleanVar (checkbox state)
        self.is_compact = False  # Compact mode state

        # Handle window close: cleanup all processes
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=5, padx=10)
        title = ctk.CTkLabel(self.header_frame, text="🛸 OmniUSB Panel Central", font=("Arial", 22, "bold"))
        title.pack(side="left", padx=10)
        self.compact_btn = ctk.CTkButton(self.header_frame, text="📏 Compacto", width=100, height=28, command=self.toggle_compact, fg_color="#374151", hover_color="#4B5563")
        self.compact_btn.pack(side="left", padx=10)
        self.status_lbl = ctk.CTkLabel(self.header_frame, text="Estado: ESPERANDO... 🌙", text_color="yellow")
        self.status_lbl.pack(side="right", padx=10)
        
        self.tabview = ctk.CTkTabview(self, width=1150, height=800)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
        self.tab_ctrl = self.tabview.add("🎛️ Panel de Control")
        self.tab_traf = self.tabview.add("📊 Tráfico de Datos en Vivo")
        
        self.batch_size_sync_id = None
        self.tips = [
            "💡 Consejo: Activa 'Modo Sigilo (Goteo)' si usas proxies móviles para evitar baneos simultáneos.",
            "💡 Consejo: Revisa la luz de salud. Si está Naranja, el sistema se estabilizará solo.",
            "💡 Consejo: Entra a WhatsApp o Instagram directo desde el celular usando SCRCPY ('Pantalla')."
        ]

        self.last_ip_check = {}
        self.device_health = {}
        self.health_fail_count = {}

        # Ocultar ventana principal hasta que la licencia se valide
        self.withdraw()
        self.check_saved_license_and_boot()

    def check_saved_license_and_boot(self):
        try:
            with open("config.json", "r") as f:
                data = json.load(f)
                already_verified = data.get("verified", False)
        except:
            already_verified = False

        if already_verified:
            self._finalize_boot()
        else:
            PasswordWindow(self, self._on_password_ok)

    def _on_password_ok(self):
        try:
            doc = {}
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    doc = json.load(f)
            doc["verified"] = True
            with open("config.json", "w") as f:
                json.dump(doc, f)
        except:
            pass
        self._finalize_boot()

    def _finalize_boot(self):
        self.build_control_tab()
        self.build_traffic_tab()

        self.deiconify()
        self.log_msg("✅ Sistema iniciado. Bienvenido.")
        
        self.load_config()
        self.tips = [
            "💡 TIP: Asegúrate de usar cables USB de buena calidad para los 40 móviles.",
            "💡 TIP: Si un teléfono falla, revisa que no tenga un aviso de 'Permitir depuración' en pantalla.",
            "💡 TIP: El icono de llave 🔑 debe aparecer en la barra de estado de los celulares.",
            "💡 TIP: No desconectes el HUB USB mientras el túnel esté activo.",
            "💡 TIP: Puedes ver el consumo de cada móvil en la pestaña 'Tráfico en Vivo'."
        ]
        
        self.device_ui_map = {} # serial -> {ip_lbl, timer_lbl, traffic_lbl, health_lbl}
        self.device_health = {} # serial -> {status: "ok"|"warning"|"dead"|"offline", reason: str}
        self.health_fail_count = {} # serial -> consecutive failure count
        self.last_ip_check = {} # serial -> timestamp
        self.update_bar = None  # Update notification bar
        self.update_timer()
        self.update_traffic()
        self._check_updates()

    def toggle_compact(self):
        """Alterna entre modo completo y modo bolsillo (solo controles)."""
        if self.is_compact:
            # Restaurar modo completo
            self.is_compact = False
            ctk.set_widget_scaling(1.0)
            self.geometry("1200x900")
            self.compact_btn.configure(text="📏 Bolsillo")
            self._right_container.grid(row=1, column=1, pady=10, padx=10, sticky="nsew")
            self.log_frame.grid(row=2, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
            self.proxy_textbox.configure(height=120)
            self.tab_ctrl.grid_columnconfigure(1, weight=2)
        else:
            # Modo bolsillo: solo columna de controles, sin log ni tarjetas
            self.is_compact = True
            ctk.set_widget_scaling(0.77)
            self.geometry("480x700")
            self.compact_btn.configure(text="📐 Completo")
            self._right_container.grid_remove()
            self.log_frame.grid_remove()
            self.proxy_textbox.configure(height=50)
            self.tab_ctrl.grid_columnconfigure(1, weight=0)

    def _check_updates(self):
        """Check for updates in background on startup."""
        def _on_result(has_update, remote_info):
            if has_update and remote_info:
                self.after(0, self._show_update_bar, remote_info)
        check_for_updates_async(_on_result)

    def _show_update_bar(self, remote_info):
        """Show a subtle update notification bar at the top."""
        local = get_local_version()
        self.update_bar = ctk.CTkFrame(self, fg_color="#065F46", corner_radius=0, height=36)
        self.update_bar.pack(fill="x", before=self.tabview)
        ctk.CTkLabel(self.update_bar, text=f"🆕 Nueva versión {remote_info.get('version', '?')} disponible (actual: {local.get('version', '?')})", font=("Arial", 12, "bold")).pack(side="left", padx=15)
        download_url = remote_info.get("download_url", "")
        if download_url:
            ctk.CTkButton(self.update_bar, text="⬇️ Actualizar", width=120, height=26, fg_color="#10B981",
                          command=lambda: self._do_update(download_url)).pack(side="right", padx=10, pady=5)
        ctk.CTkButton(self.update_bar, text="✕", width=30, height=26, fg_color="transparent",
                      command=self.update_bar.destroy).pack(side="right", padx=5, pady=5)

    def _do_update(self, url):
        """Download and install update."""
        self.log_msg("⬇️ Descargando actualización...", "warn")
        def _progress(msg):
            self.after(0, lambda: self.log_msg(f"  {msg}"))
        def _done(success, msg):
            if success:
                self.after(0, lambda: self.log_msg(f"✅ {msg}"))
                self.after(0, lambda: messagebox.showinfo("Actualización", f"{msg}\nCierra y vuelve a abrir START_APP.bat"))
            else:
                self.after(0, lambda: self.log_msg(f"❌ {msg}", "error"))
        download_update(url, _progress, _done)

    def on_close(self):
        """Clean up all child processes before closing the window."""
        try:
            self.engine.stop_rotation()
            self.runner.kill_all_gnirehtet()
            self.engine.pm.stop_all()
        except Exception:
            pass
        self.destroy()

    def build_control_tab(self):
        self.tab_ctrl.grid_columnconfigure(0, weight=1)
        self.tab_ctrl.grid_columnconfigure(1, weight=2)
        self.tab_ctrl.grid_rowconfigure(1, weight=1)

        # left controls
        frame = ctk.CTkFrame(self.tab_ctrl)
        frame.grid(row=1, column=0, pady=10, padx=10, sticky="nsew")

        ctk.CTkLabel(frame, text="⏱️ Dinámica de Rotación", font=("Arial", 14, "bold")).pack(pady=5)
        
        ctk.CTkLabel(frame, text="Dispositivos Encendidos a la vez:", font=("Arial", 11)).pack()
        self.batch_entry = ctk.CTkEntry(frame, placeholder_text="Ej: 10")
        self.batch_entry.pack(pady=2, padx=10, fill="x")
        self.batch_entry.insert(0, "10")
        
        ctk.CTkLabel(frame, text="Minutos activos antes de apagar WiFi y Rotar:", font=("Arial", 11)).pack(pady=(10,0))
        self.mins_entry = ctk.CTkEntry(frame, placeholder_text="Ej: 360 para 6 horas")
        self.mins_entry.pack(pady=2, padx=10, fill="x")
        self.mins_entry.insert(0, "360")
        
        checks_frame = ctk.CTkFrame(frame, fg_color="transparent")
        checks_frame.pack(pady=10)
        self.infinite_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(checks_frame, text="🔄 Rotar Infinito", variable=self.infinite_var).pack(side="left", padx=5)
        self.stealth_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(checks_frame, text="🕵️ Modo Sigilo (Goteo)", variable=self.stealth_var).pack(side="left", padx=5)
        
        # Proxies
        prx_frame = ctk.CTkFrame(frame, fg_color="transparent")
        prx_frame.pack(fill="x", pady=(10, 5))
        
        self.no_proxy_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(prx_frame, text="🔌 Modo Sin Proxy (Internet del PC)", variable=self.no_proxy_var, font=("Arial", 11, "bold"), text_color="#10B981").pack(side="left", padx=10)
        
        self.test_btn = ctk.CTkButton(prx_frame, text="🧪 Probador", width=80, fg_color="#3B82F6", command=self.test_proxies)
        self.test_btn.pack(side="right", padx=10)

        self.proxy_textbox = ctk.CTkTextbox(frame, height=120)
        self.proxy_textbox.pack(pady=5, padx=10, fill="x")
        self.proxy_textbox.insert("1.0", "# IP:PORT:USER:PASS o similar\n")
        
        # Actions
        ctk.CTkLabel(frame, text="⚙️ Controles de Mando", font=("Arial", 14, "bold")).pack(pady=(15, 5))
        self.scan_btn = ctk.CTkButton(frame, text="🔍 1. Escanear Dispositivos", command=self.scan_devices)
        self.scan_btn.pack(pady=5, padx=10, fill="x")
        
        self.install_btn = ctk.CTkButton(frame, text="📥 2. Instalar PKG (Gnirehtet)", command=self.install_gnirehtet, fg_color="green")
        self.install_btn.pack(pady=5, padx=10, fill="x")

        self.assign_btn = ctk.CTkButton(frame, text="🎯 ASIGNAR PROXYS MANUAL", command=self.assign_proxies, fg_color="#6366F1", font=("Arial", 13, "bold"))
        self.assign_btn.pack(pady=5, padx=10, fill="x")

        self.start_btn = ctk.CTkButton(frame, text="🚀 3. CREAR TÚNEL CENTRAL", command=self.attempt_start, height=40)
        self.start_btn.pack(pady=10, padx=10, fill="x")
        
        self.pause_btn = ctk.CTkButton(frame, text="⏸️ PAUSAR (Editar Num/Hora)", command=self.toggle_pause, state="disabled", fg_color="#F59E0B")
        self.pause_btn.pack(pady=5, padx=10, fill="x")

        self.repair_btn = ctk.CTkButton(frame, text="🔧 REPARAR CAÍDOS", command=self.repair_failed_devices, state="disabled", fg_color="#8B5CF6", font=("Arial", 12, "bold"))
        self.repair_btn.pack(pady=5, padx=10, fill="x")
        
        self.clean_btn = ctk.CTkButton(frame, text="🧹 PANIC: LIMPIEZA TOTAL (40 Disp)", command=self.panic_clean, fg_color="darkred")
        self.clean_btn.pack(pady=20, padx=10, fill="x")

        # Right Cards
        self._right_container = ctk.CTkFrame(self.tab_ctrl, fg_color="transparent")
        self._right_container.grid(row=1, column=1, pady=10, padx=10, sticky="nsew")

        btn = ctk.CTkButton(self._right_container, text="🩺 Obtener Diagnóstico Global", height=30, command=self.run_global_report, fg_color="#059669")
        btn.pack(fill="x", pady=(0, 5))

        # Device selection toolbar
        sel_frame = ctk.CTkFrame(self._right_container, fg_color="#1A1A2E", corner_radius=8)
        sel_frame.pack(fill="x", pady=(0, 5))
        ctk.CTkButton(sel_frame, text="☑️ Todos", width=90, height=28, command=self.select_all_devices, fg_color="#10B981").pack(side="left", padx=5, pady=5)
        ctk.CTkButton(sel_frame, text="☐ Ninguno", width=90, height=28, command=self.deselect_all_devices, fg_color="#6B7280").pack(side="left", padx=5, pady=5)
        self.selection_count_lbl = ctk.CTkLabel(sel_frame, text="0 de 0 seleccionados", font=("Arial", 11, "bold"), text_color="#60A5FA")
        self.selection_count_lbl.pack(side="right", padx=10, pady=5)

        self.dev_frame = ctk.CTkScrollableFrame(self._right_container, label_text="Tarjetas de Dispositivos 📱")
        self.dev_frame.pack(fill="both", expand=True)
        self.device_widgets = []
        
        # Log
        self.log_frame = ctk.CTkTextbox(self.tab_ctrl, height=100)
        self.log_frame.grid(row=2, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
        self.log_frame.configure(state="disabled")

    def build_traffic_tab(self):
        # Toolbar with sorting buttons
        toolbar = ctk.CTkFrame(self.tab_traf, fg_color="#1A1A2E", corner_radius=8)
        toolbar.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(toolbar, text="Ordenar:", font=("Arial", 11), text_color="#94A3B8").pack(side="left", padx=(10, 5), pady=5)
        ctk.CTkButton(toolbar, text="🔤 Por Serial", width=120, height=28, command=lambda: self.sort_traffic("serial"), fg_color="#3B82F6").pack(side="left", padx=5, pady=5)
        ctk.CTkButton(toolbar, text="🟢 Por Conexión", width=130, height=28, command=lambda: self.sort_traffic("connection"), fg_color="#10B981").pack(side="left", padx=5, pady=5)
        self.traf_sort_lbl = ctk.CTkLabel(toolbar, text="Sin ordenar", font=("Arial", 10), text_color="#64748B")
        self.traf_sort_lbl.pack(side="right", padx=10, pady=5)

        self.traf_frame = ctk.CTkScrollableFrame(self.tab_traf)
        self.traf_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        title = ctk.CTkLabel(self.traf_frame, text="Semáforo de Consumo en Tiempo Real", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        self.traf_widgets = {}  # serial -> label widget
        self.traf_data = {}  # serial -> {is_active, rx, tx, ip, text, color}
        self.traf_sort_mode = None  # None, "serial", "connection"

    def log_msg(self, msg, type="info"):
        self.log_frame.configure(state="normal")
        sym = "🟢" if type == "info" else "🔴"
        if type == "warn": sym = "🟡"
        self.log_frame.insert("end", f"{sym} {msg}\n")
        self.log_frame.see("end")
        self.log_frame.configure(state="disabled")

    def scan_devices(self):
        self.scan_btn.configure(state="disabled", text="🔍 Escaneando... (Espera)")
        ScanProgressWindow(self, self.adb, self._finish_scan)

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                data = json.load(f)
                self.batch_entry.delete(0, "end")
                self.batch_entry.insert(0, data.get("batch", "10"))
                self.mins_entry.delete(0, "end")
                self.mins_entry.insert(0, data.get("mins", "360"))
                
                if "proxies" in data:
                    self.proxy_textbox.delete("1.0", "end")
                    self.proxy_textbox.insert("1.0", data["proxies"].strip() + "\n")
                    
                self.infinite_var.set(data.get("infinite", True))
                self.stealth_var.set(data.get("stealth", True))
                self.no_proxy_var.set(data.get("no_proxy", False))
        except:
            pass

    def save_config(self):
        try:
            data = {
                "batch": self.batch_entry.get(),
                "mins": self.mins_entry.get(),
                "infinite": self.infinite_var.get(),
                "stealth": self.stealth_var.get(),
                "no_proxy": self.no_proxy_var.get(),
                "proxies": self.proxy_textbox.get("1.0", "end").strip()
            }
            import os
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"), "w") as f:
                json.dump(data, f)
        except:
            pass

    def _finish_scan(self, devices):
        self.scanned_devices = devices
        pkg_missing = len([d for d in devices if not d.get('pkg_ok')])
        msg = f"Escaner completado: {len(devices)} conectados."
        if pkg_missing > 0:
            msg += f" ⚠️ {pkg_missing} requieren instalación de driver."
        else:
            msg += " ✅ Todos con driver OK."
        
        self.log_msg(msg)
        for w in self.device_widgets:
            w.destroy()
        self.device_widgets = []
        self.device_selections = {}
        for dev in devices:
            var = ctk.BooleanVar(value=True)
            var.trace_add("write", lambda *_: self.update_selection_count())
            self.device_selections[dev['serial']] = var
            self.create_device_card(dev)
        self.update_selection_count()
        self.scan_btn.configure(state="normal", text="🔍 1. Escanear Dispositivos")

    def create_device_card(self, dev):
        card = ctk.CTkFrame(self.dev_frame, fg_color="#1E1E1E", corner_radius=10, border_width=1, border_color="#333333")
        card.pack(fill="x", pady=8, padx=5)
        conn_type = "📶 WiFi" if dev['is_wifi'] else "🔌 USB"
        
        # Checkbox for device selection
        check_fr = ctk.CTkFrame(card, fg_color="transparent", width=40)
        check_fr.pack(side="left", padx=(10, 0), pady=10)
        sel_var = self.device_selections.get(dev['serial'])
        if sel_var:
            cb = ctk.CTkCheckBox(check_fr, text="", variable=sel_var, width=24, checkbox_width=22, checkbox_height=22)
            cb.pack()
        
        left_fr = ctk.CTkFrame(card, fg_color="transparent")
        left_fr.pack(side="left", padx=5, pady=10, fill="y")
        model_name = dev.get('model', 'Phone')
        title = ctk.CTkLabel(left_fr, text=f"{model_name}", font=("Arial", 16, "bold"))
        title.pack(anchor="w")
        # Driver status on left
        pkg_ok = dev.get('pkg_ok', False)
        status_color = "#10B981" if pkg_ok else "#EF4444"
        status_txt = "✅ Driver OK" if pkg_ok else "❌ Sin Driver"
        ctk.CTkLabel(left_fr, text=status_txt, text_color=status_color, font=("Arial", 11, "bold")).pack(anchor="w")
        ctk.CTkLabel(left_fr, text=f"{conn_type}", text_color="gray").pack(anchor="w")
        
        mid_fr = ctk.CTkFrame(card, fg_color="transparent")
        mid_fr.pack(side="left", padx=20, pady=10, fill="y", expand=True)
        # Timer
        timer_lbl = ctk.CTkLabel(mid_fr, text="⏳ Esperando...", font=("Arial", 11), text_color="#94A3B8")
        timer_lbl.pack(anchor="w")
        # IP Display
        ctk.CTkLabel(mid_fr, text="IP EXTERNA:", font=("Arial", 10), text_color="gray").pack(anchor="w")
        ip_val_lbl = ctk.CTkLabel(mid_fr, text="Detectando...", text_color="#22D3EE", font=("Arial", 15, "bold"))
        ip_val_lbl.pack(anchor="w")
        
        # Traffic on right
        right_info = ctk.CTkFrame(card, fg_color="transparent")
        right_info.pack(side="right", padx=15)
        traffic_lbl = ctk.CTkLabel(right_info, text="MB: 0.0↓ 0.0↑", font=("Courier New", 12))
        traffic_lbl.pack()
        # Health status indicator
        health_lbl = ctk.CTkLabel(right_info, text="⭕ Sin estado", font=("Arial", 10), text_color="#64748B")
        health_lbl.pack(pady=(5, 0))

        # Interaction buttons row
        actions_fr = ctk.CTkFrame(right_info, fg_color="transparent")
        actions_fr.pack(pady=(5, 0))
        serial = dev['serial']
        ctk.CTkButton(actions_fr, text="👁️", width=36, height=26, fg_color="#3B82F6",
                      command=lambda s=serial: self.launch_scrcpy(s),
                      font=("Arial", 13)).pack(side="left", padx=2)
        focus_btn = ctk.CTkButton(actions_fr, text="🎯", width=36, height=26, fg_color="#8B5CF6",
                      command=lambda s=serial: self.toggle_focus(s),
                      font=("Arial", 13))
        focus_btn.pack(side="left", padx=2)
        ctk.CTkButton(actions_fr, text="📋", width=36, height=26, fg_color="#059669",
                      command=lambda s=serial: self.paste_to_device(s),
                      font=("Arial", 13)).pack(side="left", padx=2)

        self.device_ui_map[dev['serial']] = {
            "card": card,
            "timer": timer_lbl,
            "ip": ip_val_lbl,
            "traffic": traffic_lbl,
            "health": health_lbl,
            "focus_btn": focus_btn
        }
        self.device_widgets.append(card)

    def select_all_devices(self):
        for var in self.device_selections.values():
            var.set(True)

    def deselect_all_devices(self):
        for var in self.device_selections.values():
            var.set(False)

    def update_selection_count(self):
        total = len(self.device_selections)
        selected = sum(1 for v in self.device_selections.values() if v.get())
        # Show count and hint about batch vs selected
        try:
            batch = int(self.batch_entry.get())
        except ValueError:
            batch = selected
        if selected > 0 and batch > selected:
            self.selection_count_lbl.configure(text=f"{selected} de {total} sel. (lote {batch} > sel., se usarán {selected})")
        elif selected > 0 and batch < selected:
            lotes = -(-selected // batch)  # ceil division
            self.selection_count_lbl.configure(text=f"{selected} de {total} sel. → {lotes} lotes de {batch}")
        else:
            self.selection_count_lbl.configure(text=f"{selected} de {total} seleccionados")

    def get_selected_devices(self):
        """Returns only the scanned devices whose checkbox is checked."""
        return [d for d in self.scanned_devices if self.device_selections.get(d['serial'], ctk.BooleanVar(value=False)).get()]

    def launch_scrcpy(self, serial):
        """Launch scrcpy to mirror device screen."""
        base = os.path.dirname(os.path.abspath(__file__))
        scrcpy_exe = os.path.join(base, "scrcpy", "scrcpy.exe")
        if not os.path.exists(scrcpy_exe):
            messagebox.showerror("scrcpy no encontrado",
                "scrcpy no está instalado.\n\nCierra la app y ejecuta START_APP.bat para que se descargue automáticamente.")
            return
        try:
            subprocess.Popen([scrcpy_exe, "-s", serial, "--window-title", f"📱 {serial}"],
                             cwd=os.path.join(base, "scrcpy"))
            self.log_msg(f"👁️ Pantalla abierta: {serial}")
        except Exception as e:
            self.log_msg(f"❌ Error al abrir pantalla: {e}", "error")

    def toggle_focus(self, serial):
        """Give full bandwidth to one device by pausing all others."""
        if not self.engine.running:
            messagebox.showinfo("Info", "El túnel debe estar activo para usar Focus.")
            return

        ui = self.device_ui_map.get(serial, {})
        focus_btn = ui.get("focus_btn")

        # Check if already in focus mode for this device
        if hasattr(self, '_focus_serial') and self._focus_serial == serial:
            # Restore all paused devices
            self.log_msg(f"↩️ Restaurando todos los dispositivos...")
            for paused_serial in self._focus_paused:
                self.runner.start(paused_serial)
            self._focus_serial = None
            self._focus_paused = []
            if focus_btn:
                focus_btn.configure(text="🎯", fg_color="#8B5CF6")
            self.log_msg(f"✅ Todos los dispositivos restaurados.")
            return

        # Enter focus mode: pause gnirehtet on all OTHER active devices
        active_serials = [d['serial'] for d in self.engine.active_devices]
        if serial not in active_serials:
            messagebox.showinfo("Info", f"El dispositivo {serial[-4:]} no está en el lote activo.")
            return

        others = [s for s in active_serials if s != serial]
        if not others:
            messagebox.showinfo("Info", "Solo hay 1 dispositivo activo, ya tiene todo el tráfico.")
            return

        self._focus_serial = serial
        self._focus_paused = others
        self.log_msg(f"🎯 FOCUS → {serial[-4:]} | Pausando {len(others)} dispositivo(s)...", "warn")

        def _do_focus():
            for other in others:
                self.runner.stop(other)
            self.after(0, lambda: self.log_msg(f"🎯 {serial[-4:]} tiene todo el ancho de banda. Clic 🎯 de nuevo para restaurar."))

        threading.Thread(target=_do_focus, daemon=True).start()
        if focus_btn:
            focus_btn.configure(text="↩️", fg_color="#EF4444")

    def paste_to_device(self, serial):
        """Open dialog to paste text to device via ADB."""
        dialog = ctk.CTkInputDialog(text=f"Texto a pegar en {serial[-8:]}:", title="📋 Pegar en Dispositivo")
        text = dialog.get_input()
        if text and text.strip():
            # Escape special characters for ADB shell input
            safe_text = text.replace("\\", "\\\\").replace("\"", "\\\"").replace("'", "\\'")
            safe_text = safe_text.replace(" ", "%s").replace("&", "\\&").replace(";", "\\;")
            safe_text = safe_text.replace("(", "\\(").replace(")", "\\)").replace("|", "\\|")

            def _paste():
                # Method 1: Try clipboard broadcast (needs Clipper or similar)
                self.adb.run_command(["shell", "input", "text", safe_text], serial)
                self.after(0, lambda: self.log_msg(f"📋 Texto enviado a {serial[-4:]}: \"{text[:30]}...\"" if len(text) > 30 else f"📋 Texto enviado a {serial[-4:]}: \"{text}\""))

            threading.Thread(target=_paste, daemon=True).start()

    def run_global_report(self):
        ReporteGlobalWindow(self, self.adb, self.engine)

    def test_proxies(self):
        raw_proxies = self.proxy_textbox.get("1.0", "end").strip().split('\n')
        proxies = [from_engine for from_engine in [p.strip() for p in raw_proxies if p.strip() and not p.startswith("#")] if from_engine]
        from rotation_engine import format_proxy
        formatted = [format_proxy(p) for p in proxies if format_proxy(p)]
        if not formatted:
            messagebox.showwarning("Vacío", "Pega proxies para probarlos primero.")
            return

        def _on_test_finish(alive_list):
            self.proxy_textbox.delete("1.0", "end")
            self.proxy_textbox.insert("end", "# Proxies Testeados (Limpios)\n")
            for p in alive_list:
                self.proxy_textbox.insert("end", p + "\n")
            self.log_msg(f"Test finalizado. {len(alive_list)} proxies guardados y limpios.")
            self.save_config()

        ProxyTesterWindow(self, formatted, _on_test_finish)

    def install_gnirehtet(self):
        devices = self.adb.list_devices()
        missing = [d for d in devices if not d.get('pkg_ok')]
        if not missing:
            messagebox.showinfo("Listo", "Todos los dispositivos ya tienen el driver instalado.")
            return
            
        def _installer():
            total = len(missing)
            self.log_msg(f"⚙️ Instalando driver en {total} dispositivos faltantes...", "warn")
            for i, dev in enumerate(missing):
                s = dev['serial']
                self.log_msg(f"📦 Instalando en {dev['model']} ({s})...")
                self.adb.install_apk(s, "gnirehtet.apk")
            self.log_msg(f"✅ ¡Instalación completada en {total} equipos!", "info")
            self.after(0, self.scan_devices) # Refresh to show green checks
            
        threading.Thread(target=_installer, daemon=True).start()

    def parse_inputs(self):
        try:
            b_size = int(self.batch_entry.get())
            mins = float(self.mins_entry.get())
            return b_size, mins
        except ValueError:
            messagebox.showerror("Error", "Lotes y minutos numéricos.")
            return None, None

    def attempt_start(self):
        # Check that devices are selected
        selected = self.get_selected_devices()
        if not selected:
            messagebox.showerror("⛔ Sin Dispositivos", "No hay dispositivos seleccionados.\nEscanea y marca los que quieras usar.")
            return

        raw_proxies = self.proxy_textbox.get("1.0", "end").strip().split('\n')
        proxies = [p.strip() for p in raw_proxies if p.strip() and not p.startswith("#")]
        
        if not proxies:
            if self.no_proxy_var.get():
                self.save_config()
                self.start_farm([])
            else:
                self.no_proxy_strikes += 1
                if self.no_proxy_strikes >= 3:
                    if messagebox.askyesno("Info", f"Iniciando {len(selected)} dispositivos sin proxies. ¿Seguro?"): self.start_farm([])
                else:
                    messagebox.showerror("⛔ Faltan Proxies", "No ingresaste los Proxies.\n\n(O marca la casilla 'Modo Sin Proxy' si quieres usar internet del PC)")
        else:
            self.save_config()
            self.start_farm(proxies)

    def assign_proxies(self):
        devices = self.adb.list_devices()
        if not devices:
            messagebox.showwarning("Vacío", "Escanea dispositivos primero para poder mapearlos.")
            return
        raw_proxies = self.proxy_textbox.get("1.0", "end").strip().split('\n')
        from rotation_engine import format_proxy
        proxies = [format_proxy(p) for p in raw_proxies if format_proxy(p)]
        if not proxies:
            messagebox.showwarning("Vacío", "Pega proxies en la lista primero.")
            return
            
        ProxyAssignmentWindow(self, devices, proxies)

    def start_farm(self, proxies):
        devices = self.get_selected_devices()
        b_size, mins = self.parse_inputs()
        
        if b_size is None:
            return
            
        if not devices:
            messagebox.showerror("Falla Fatal", "No hay dispositivos seleccionados. Escanea y marca los que quieras usar.")
            self.log_msg("Intento de inicio abortado: 0 celulares seleccionados.", "warn")
            self.start_btn.configure(state="normal")
            return
            
        self.save_config()
        self.log_msg(f"▶️ Iniciando Secuencia con {len(devices)} dispositivos seleccionados...")
        SetupProgressWindow(self, devices, proxies, b_size, mins)
        self.no_proxy_strikes = 0
        self.batch_entry.configure(state="disabled")
        self.mins_entry.configure(state="disabled")

    def repair_failed_devices(self):
        """Find devices with failed health and attempt reconnection."""
        failed = [s for s, h in self.device_health.items() if h.get("status") in ("dead", "warning")]
        if not failed:
            messagebox.showinfo("Sin Fallos", "No hay dispositivos caídos para reparar.")
            return

        self.repair_btn.configure(state="disabled", text="🔧 Reparando...")
        self.log_msg(f"🔧 Iniciando reparación de {len(failed)} dispositivo(s)...", "warn")

        def _repair_thread():
            results = {"fixed": 0, "still_broken": 0}
            for serial in failed:
                self.log_msg(f"  🔄 Reconectando {serial}...")
                success, reason = self.engine.reconnect_device(serial)
                if success:
                    results["fixed"] += 1
                    self.log_msg(f"  ✅ {serial}: {reason}")
                    self.device_health[serial] = {"status": "ok", "reason": reason}
                    self.last_ip_check[serial] = 0  # Force fresh IP check on next cycle
                else:
                    results["still_broken"] += 1
                    self.log_msg(f"  ❌ {serial}: {reason}", "error")
                    self.device_health[serial] = {"status": "dead", "reason": reason}

            # Summary
            summary = f"🔧 Resultado: {results['fixed']} reparados"
            if results["still_broken"] > 0:
                summary += f", {results['still_broken']} siguen fallando"
                self.log_msg(summary, "warn")
            else:
                self.log_msg(summary)

            self.after(0, lambda: self.repair_btn.configure(state="normal", text="🔧 REPARAR CAÍDOS"))

        threading.Thread(target=_repair_thread, daemon=True).start()

    def panic_clean(self):
        PanicProgressWindow(self, self.engine, self.runner, self.adb)

    def toggle_pause(self):
        if not self.engine.running: return
        if not self.engine.paused:
            self.engine.paused = True
            self.pause_btn.configure(text="▶️ REANUDAR TÚNEL", fg_color="green")
            self.status_lbl.configure(text="Estado: PAUSADO ⏸️ — Puedes Escanear/Agregar dispositivos", text_color="orange")
            self.batch_entry.configure(state="normal")
            self.mins_entry.configure(state="normal")
            self.scan_btn.configure(state="normal")
            self.log_msg("⏸️ Túnel en Pausa. Puedes escanear, agregar/quitar dispositivos y editar configuraciones.", "warn")
        else:
            selected = self.get_selected_devices()
            if not selected:
                messagebox.showwarning("⚠️ Sin Selección", "No hay dispositivos seleccionados.\nMarca al menos uno antes de reanudar.")
                return

            b_size, mins = self.parse_inputs()
            if b_size is None: return

            # Re-read proxies in case user edited them during pause
            raw_proxies = self.proxy_textbox.get("1.0", "end").strip().split('\n')
            from rotation_engine import format_proxy
            new_proxies = [format_proxy(p) for p in raw_proxies if p.strip() and not p.startswith("#") and format_proxy(p)]

            # Update engine with new device list and config
            self.engine.all_devices = selected
            self.engine.batch_size = b_size
            self.engine.interval_minutes = mins
            if new_proxies:
                self.engine.proxies = new_proxies
            self.engine.current_batch_index = 0
            self.engine.next_rotation_time = 0  # Force immediate re-batch

            self.engine.paused = False
            self.pause_btn.configure(text="⏸️ PAUSAR (Editar Num/Hora)", fg_color="#F59E0B")
            self.batch_entry.configure(state="disabled")
            self.mins_entry.configure(state="disabled")
            self.save_config()
            self.log_msg(f"▶️ Reanudado con {len(selected)} dispositivos seleccionados. Aplicando cambios...")

    def on_engine_update(self, event_type):
        if event_type == "COMPLETED":
            self.log_msg("✅ Ciclo completado. Granja terminada.")
            self.start_btn.configure(state="normal")
            self.pause_btn.configure(state="disabled")
            self.status_lbl.configure(text="Estado: COMPLETADO 🏁")

    def update_timer(self):
        if self.engine.running and not self.engine.paused:
            rem = int(self.engine.next_rotation_time - time.time())
            if rem > 0:
                m = rem // 60
                s = rem % 60
                self.status_lbl.configure(text=f"🔄 Lote {self.engine.current_batch_index + 1} ACTIVO | Cambio en: {m}m {s}s", text_color="lightgreen")
            else:
                self.status_lbl.configure(text="🔄 Cambiando de lote u Operando Stealth...", text_color="yellow")
        self.after(1000, self.update_timer)

    def update_traffic(self):
        if self.engine.running:
            devices = self.engine.all_devices.copy()
            active_serials = [d['serial'] for d in self.engine.active_devices]
            
            def _fetch():
                updates = {}
                threads = []
                
                def _fetch_one(serial, is_active):
                    rx_mb, tx_mb = 0.0, 0.0
                    external_ip = "---"
                    health = "offline"
                    health_reason = ""
                    if is_active:
                        # 1. Check tunnel interface (tun0 or vpn only, NOT rmnet)
                        has_tunnel = False
                        stdout, _, _ = self.adb.run_command(["shell", "cat", "/proc/net/dev"], serial)
                        for line in stdout.split('\n'):
                            if 'tun0:' in line or 'vpn' in line:
                                has_tunnel = True
                            # Traffic: collect from tun0, vpn, or rmnet
                            if 'tun0:' in line or 'vpn' in line or 'rmnet' in line:
                                try:
                                    p = line.split(':')[1].split()
                                    rx_mb += float(p[0]) / (1024 * 1024)
                                    tx_mb += float(p[8]) / (1024 * 1024)
                                except: pass
                        
                        if not has_tunnel:
                            health = "dead"
                            health_reason = "Sin túnel (tun0 ausente)"
                        
                        # 2. IP check from PC through local proxy port (every 60s)
                        last = self.last_ip_check.get(serial, 0)
                        if (time.time() - last) > 60:
                            port = self.engine.active_ports.get(serial)
                            if port:
                                try:
                                    import requests
                                    px = {"http": f"http://127.0.0.1:{port}", "https": f"http://127.0.0.1:{port}"}
                                    res = requests.get("https://api.ipify.org?format=json", proxies=px, timeout=6)
                                    ip = res.json().get("ip", "")
                                    if ip:
                                        external_ip = ip
                                        self.last_ip_check[serial] = time.time()
                                        health = "ok"
                                        health_reason = "Conexión OK"
                                        self.health_fail_count[serial] = 0
                                    else:
                                        raise Exception("empty")
                                except Exception:
                                    fails = self.health_fail_count.get(serial, 0) + 1
                                    self.health_fail_count[serial] = fails
                                    if fails >= 2:
                                        external_ip = "Sin respuesta"
                                        if has_tunnel:
                                            health = "warning"
                                            health_reason = "Proxy sin respuesta"
                                        else:
                                            health = "dead"
                                            health_reason = "Sin túnel ni internet"
                                    else:
                                        # First failure: keep previous state, don't alarm yet
                                        prev = self.device_health.get(serial, {})
                                        health = prev.get("status", "ok" if has_tunnel else "dead")
                                        health_reason = prev.get("reason", "Verificando...")
                                        ui = self.device_ui_map.get(serial)
                                        if ui: external_ip = ui['ip'].cget("text")
                                        self.last_ip_check[serial] = time.time()
                            else:
                                # No proxy port assigned: tunnel-only mode
                                if has_tunnel:
                                    health = "ok"
                                    health_reason = "Túnel directo (sin proxy)"
                                    external_ip = "Directo"
                                self.last_ip_check[serial] = time.time()
                        else:
                            # Between checks: keep current state
                            ui = self.device_ui_map.get(serial)
                            if ui: external_ip = ui['ip'].cget("text")
                            prev = self.device_health.get(serial, {})
                            if prev:
                                health = prev.get("status", "ok" if has_tunnel else "dead")
                                health_reason = prev.get("reason", "")
                            elif has_tunnel:
                                health = "ok"
                                health_reason = "Túnel activo"
                    
                    self.device_health[serial] = {"status": health, "reason": health_reason}
                    updates[serial] = (is_active, rx_mb, tx_mb, external_ip, health, health_reason)

                for dev in devices:
                    t = threading.Thread(target=_fetch_one, args=(dev['serial'], dev['serial'] in active_serials))
                    t.start()
                    threads.append(t)
                
                for t in threads: t.join()
                self.after(0, self._apply_traffic_updates, updates)
                
            threading.Thread(target=_fetch, daemon=True).start()
        self.after(5000, self.update_traffic)

    def _apply_traffic_updates(self, updates):
        now = time.time()
        rem_sec = max(0, int(self.engine.next_rotation_time - now))
        mins = rem_sec // 60
        secs = rem_sec % 60
        timer_text = f"⏳ Rotación: {mins:02d}:{secs:02d}"

        has_failed = False
        for serial, (is_active, rx, tx, ip, health, health_reason) in updates.items():
            ui = self.device_ui_map.get(serial)
            if ui:
                # 1. Update Timer & IP labels
                if is_active:
                    ui['timer'].configure(text=timer_text, text_color="#FCD34D")
                    if ip != "---":
                        ui['ip'].configure(text=ip)
                else:
                    ui['timer'].configure(text="🕒 En Espera...", text_color="#64748B")
                    ui['ip'].configure(text="Túnel Cerrado")
                
                # 2. Update Traffic info
                ui['traffic'].configure(text=f"MB: {rx:.1f}↓ {tx:.1f}↑")
                
                # 3. Health status display
                if is_active:
                    if health == "ok":
                        ui['health'].configure(text="🟢 OK", text_color="#10B981")
                        bg_color = "#064E3B"
                    elif health == "warning":
                        ui['health'].configure(text=f"🟡 {health_reason}", text_color="#F59E0B")
                        bg_color = "#78350F"
                        has_failed = True
                    elif health == "dead":
                        ui['health'].configure(text=f"🔴 {health_reason}", text_color="#EF4444")
                        bg_color = "#7F1D1D"
                        has_failed = True
                    else:
                        ui['health'].configure(text="⭕ Verificando...", text_color="#64748B")
                        bg_color = "#064E3B"
                else:
                    ui['health'].configure(text="💤 Inactivo", text_color="#475569")
                    bg_color = "#1E1E1E"
                
                ui['card'].configure(fg_color=bg_color)
            
            # 4. Global traffic list update
            if health == "ok":
                color = "#10B981"
                estado_txt = "🟢 OK"
            elif health == "warning":
                color = "#F59E0B"
                estado_txt = "🟡 LENTO"
            elif health == "dead" and is_active:
                color = "#EF4444"
                estado_txt = "🔴 CAÍDO"
            elif is_active:
                color = "#94A3B8"
                estado_txt = "⏳ CHECK"
            else:
                color = "gray"
                estado_txt = "🌙"
            text_disp = f"{estado_txt} │📱 {serial} │ {rx:.1f}MB↓ {tx:.1f}MB↑ │ IP: {ip}"

            self.traf_data[serial] = {
                "is_active": is_active, "rx": rx, "tx": tx, "ip": ip,
                "text": text_disp, "color": color
            }
            
            if serial not in self.traf_widgets:
                fr = ctk.CTkFrame(self.traf_frame)
                fr.pack(fill="x", pady=2)
                lbl = ctk.CTkLabel(fr, text=text_disp, font=("Arial", 12), text_color=color)
                lbl.pack(anchor="w", padx=5)
                self.traf_widgets[serial] = {"frame": fr, "label": lbl}
            else:
                self.traf_widgets[serial]["label"].configure(text=text_disp, text_color=color)

        # Enable repair button if there are failures
        if has_failed:
            self.repair_btn.configure(state="normal")
        else:
            self.repair_btn.configure(state="disabled")

        # Auto-apply current sort if one is active
        if self.traf_sort_mode:
            self.sort_traffic(self.traf_sort_mode)

    def sort_traffic(self, mode):
        """Reorder traffic widgets by serial or connection status."""
        self.traf_sort_mode = mode
        if not self.traf_data:
            return

        serials = list(self.traf_data.keys())
        if mode == "serial":
            serials.sort()
            self.traf_sort_lbl.configure(text="Ordenado: A → Z (Serial)")
        elif mode == "connection":
            serials.sort(key=lambda s: (not self.traf_data[s]["is_active"], s))
            self.traf_sort_lbl.configure(text="Ordenado: Activos primero")

        for serial in serials:
            w = self.traf_widgets.get(serial)
            if w:
                w["frame"].pack_forget()
                w["frame"].pack(fill="x", pady=2)

if __name__ == "__main__":
    app = ProxyFarmApp()
    app.mainloop()
