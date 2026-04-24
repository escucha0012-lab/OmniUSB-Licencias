"""
OmniUSB - Tunnel Health Logger
Registra eventos de salud del túnel en OmniUSB_log.txt
"""
import os
from datetime import datetime

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
LOG_FILE  = os.path.join(BASE_DIR, "OmniUSB_log.txt")
MAX_BYTES = 5 * 1024 * 1024  # 5 MB — rota automáticamente

_ICONS = {
    "WARN":     "⚠️ ",
    "RECONECT": "♻️ ",
    "OK":       "✅",
    "ERROR":    "❌",
    "INFO":     "ℹ️ ",
    "START":    "🚀",
    "STOP":     "🛑",
}

def log(event_type: str, serial: str, message: str, port=None, proxy=None):
    """
    Escribe una línea en OmniUSB_log.txt.

    Parámetros:
        event_type : WARN | RECONECT | OK | ERROR | INFO | START | STOP
        serial     : identificador del dispositivo Android
        message    : descripción del evento
        port       : puerto local asignado (opcional)
        proxy      : proxy remoto asignado (opcional, se ofusca la contraseña)
    """
    # ── Rotar si supera el límite ──
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_BYTES:
            old = LOG_FILE.replace(".txt", "_anterior.txt")
            if os.path.exists(old):
                os.remove(old)
            os.replace(LOG_FILE, old)
    except Exception:
        pass

    # ── Ofuscar contraseña del proxy ──
    proxy_part = ""
    if proxy:
        try:
            # formato user:pass@ip:port  →  mostrar solo ip:port
            visible = proxy.split("@")[-1] if "@" in proxy else proxy
        except Exception:
            visible = "***"
        proxy_part = f" | Proxy: {visible}"

    port_part = f" | Puerto: {port}" if port else ""

    icon = _ICONS.get(event_type.upper(), "  ")
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {icon} {event_type:<8} | {serial}{port_part}{proxy_part} | {message}\n"

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def log_session_start(devices: list, proxies: list):
    """Marca el inicio de una sesión de granja."""
    separator = "=" * 70 + "\n"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"{separator}"
        f"  SESIÓN INICIADA — {ts}\n"
        f"  Dispositivos: {len(devices)} | Proxies cargados: {len(proxies)}\n"
        f"{separator}"
    )
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(header)
    except Exception:
        pass


def log_session_end():
    """Marca el fin de una sesión."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"  SESIÓN TERMINADA — {ts}\n\n")
    except Exception:
        pass
