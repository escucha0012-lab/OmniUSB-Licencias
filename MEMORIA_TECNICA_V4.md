# 🧠 Memoria Técnica — OmniUSB Proxy Farm v4.0 (Edición Final)

## 📦 Contenido de la Carpeta

| Archivo | Función |
|:--------|:--------|
| `START_APP.bat` | Arrancador principal — instala todo automáticamente |
| `app.py` | GUI principal (CustomTkinter) |
| `rotation_engine.py` | Motor de rotación de lotes y reconexión |
| `adb_manager.py` | Wrapper de ADB con reintentos y timeout |
| `gnirehtet_runner.py` | Watchdog del relay de Gnirehtet |
| `node_proxy.py` | Lanza procesos Node.js como proxy-chain local |
| `auto_repair.py` | Auto-descarga de ADB, Gnirehtet, Node deps |
| `run_proxy.js` | Script Node.js del proxy (se regenera automáticamente) |
| `config.json` | Configuración guardada (proxies, lotes, minutos) |
| `requirements.txt` | Dependencias Python: customtkinter, requests, psutil |
| `package.json` | Dependencias Node: proxy-chain |
| `gnirehtet.exe` / `.apk` | Herramienta de internet inverso (PC → móvil) |
| `platform-tools/` | ADB y herramientas Android |

---

## 🚀 Migración a Nueva PC (3 pasos)

### Requisitos previos:
1. **Python 3.10+** — [python.org](https://python.org) (marcar "Add to PATH")
2. **Node.js LTS** — [nodejs.org](https://nodejs.org)
3. **Drivers USB** de los móviles (Samsung, etc.)

### Proceso:
1. Copiar carpeta `InternetProxyFarm_V2` a la raíz del disco (ej: `C:\InternetProxyFarm_V2`)
2. Doble clic en `START_APP.bat`
3. El sistema detecta la migración automáticamente y reinstala todo

### ¿Qué hace START_APP.bat automáticamente?
- Detecta si cambió de PC/carpeta (`install_path.txt`)
- Purga `venv/` y `node_modules/` viejos
- Crea nuevo virtualenv de Python
- Instala dependencies pip (customtkinter, requests, psutil)
- Ejecuta `auto_repair.py` que descarga ADB y Gnirehtet si faltan
- Instala `proxy-chain` via npm
- Inicia servidor ADB
- Lanza la GUI

### ¿Rutas hardcodeadas? NO
Todos los archivos usan rutas relativas (`os.path.dirname(__file__)`, `%CD%`).
La carpeta puede estar en CUALQUIER ubicación.

---

## 🎛️ Funcionalidades de la GUI

### Panel de Control
| Botón | Función |
|:------|:--------|
| 📏 Compacto/Completo | Cambia entre vista grande (1200x900) y pocket (920x660) |
| 🔍 Escanear | Detecta dispositivos USB conectados |
| 📥 Instalar PKG | Instala Gnirehtet APK en dispositivos sin driver |
| 🎯 Asignar Proxys | Mapeo manual dispositivo ↔ proxy |
| 🚀 Crear Túnel | Inicia la granja con los dispositivos seleccionados |
| ⏸️ Pausar | Pausa el motor — permite escanear y agregar dispositivos |
| 🔧 Reparar Caídos | Reconecta dispositivos con conexión fallida |
| 🧹 Panic | Limpieza total — restaura WiFi en todos |

### Tarjetas de Dispositivos
- ✅ Checkbox para seleccionar cuáles conectar
- 🟢/🟡/🔴 Indicador de salud en tiempo real
- IP externa, timer de rotación, tráfico MB

### Tráfico en Vivo
- Vista de todos los dispositivos con consumo
- Ordenar por Serial (A→Z) o por Conexión (activos primero)

---

## ⚙️ Configuración de Rotación

| Parámetro | Qué hace |
|:----------|:---------|
| **Dispositivos encendidos** | Cuántos conectar a la vez por lote |
| **Minutos activos** | Tiempo antes de rotar al siguiente lote |
| **Rotar Infinito** | Vuelve al lote 1 al terminar todos |
| **Modo Sigilo** | Espaciado aleatorio entre conexiones |

### Ejemplos:
- 3 seleccionados, lote 3, 360 min → Los 3 siempre conectados, reconexión cada 6h
- 10 seleccionados, lote 2, 5 min → 5 lotes de 2, rotan cada 5 min
- 6 seleccionados, lote 6, 120 min → Los 6 conectados, reconexión cada 2h

---

## 🩺 Sistema de Salud

El monitoreo verifica cada 60 segundos:
1. **Túnel (tun0)**: ¿Existe la interfaz en el dispositivo?
2. **Proxy**: Desde la PC, prueba `api.ipify.org` a través del puerto proxy local
3. **Contador de fallos**: Solo marca warning después de 2+ fallos consecutivos

| Estado | Significado | Color tarjeta |
|:-------|:-----------|:-------------|
| 🟢 OK | Túnel + proxy funcionando | Verde |
| 🟡 Warning | Proxy sin respuesta (2+ fallos) | Amarillo |
| 🔴 Dead | Sin túnel (tun0 ausente) | Rojo |
| 💤 Inactivo | No está en el lote activo | Gris |

### Reparación automática (🔧 Reparar Caídos):
1. Para Gnirehtet del dispositivo
2. Limpia proxy y reverse tunnel
3. Reinicia Gnirehtet
4. Re-aplica proxy
5. Valida túnel + internet
6. Muestra diagnóstico detallado

---

## 🔄 Flujo de Agregar/Quitar Dispositivos en Caliente

```
Pausar → Escanear nuevos → Marcar/Desmarcar → Reanudar
```
No requiere Panic ni reiniciar la app. Al reanudar se aplican los cambios.

---

## 📁 Archivos que se auto-generan (NO incluir en backup):
- `venv/` — Se recrea automáticamente
- `node_modules/` — Se recrea automáticamente  
- `install_path.txt` — Se recrea al detectar nueva ubicación
- `CRASH_REPORT.txt` — Solo existe si hubo un crash
- `__pycache__/` — Cache de Python

## 📁 Archivos que SÍ incluir en backup:
- Todos los `.py`, `.bat`, `.md`, `.txt`
- `config.json` (tiene tus proxies y configuración guardada)
- `gnirehtet.exe`, `gnirehtet.apk`, `gnirehtet.zip`
- `platform-tools/` (contiene ADB)
- `package.json`, `package-lock.json`
- `requirements.txt`
