# 🚀 Guía de Migración: OmniUSB Proxy Farm (v4.0)

Esta guía te ayudará a mover toda la carpeta de la granja a una nueva PC y asegurar que funcione de inmediato con todas las mejoras de estabilidad (túneles paralelos, cronómetros de rotación y blindaje de procesos).

## 📋 Requisitos Previos en la Nueva PC
Antes de abrir la aplicación, asegúrate de tener instalados estos tres pilares:

1.  **Python (3.10+):** Descárgalo e instálalo desde [python.org](https://python.org/). **MUY IMPORTANTE:** Al instalarlo, marca la casilla ✅ "Add Python to PATH".
2.  **Node.js (LTS):** Descárgalo e instálalo desde [nodejs.org](https://nodejs.org/). Es vital para que los proxies funcionen.
3.  **Drivers ADB:** Si la PC es nueva, instala los drivers de tus móviles (ej. Samsung USB Drivers) para que Windows reconozca los 40 equipos.

---

## 📂 Pasos para la Migración

### 1. Copiar la Carpeta
Copia la carpeta completa `InternetProxyFarm_V2` a la raíz del disco (ejemplo: `C:\InternetProxyFarm_V2`). 
> **IMPORTANTE:** Evita ponerla en el Escritorio o Documentos para prevenir problemas de permisos de Windows.

### 2. Ejecutar el Arrancador Inteligente
No abras el código directamente. Haz doble clic en el archivo:
👉 `START_APP.bat`

Este archivo hará todo el trabajo sucio por ti:
*   Creará el entorno virtual de Python.
*   Instalará las librerías necesarias (`customtkinter`, `psutil`, etc.).
*   Verificará si faltan archivos como `adb.exe` o `gnirehtet.exe` y los descargará si es necesario.
*   Iniciará el servidor de Node.js.

### 3. Verificar en la Nueva PC
Una vez que abra la aplicación:
1.  Dale a **"1. Escanear Dispositivos"**. Si no aparecen, revisa los cables USB o los drivers.
2.  Verifica que todos tengan el check **✅ Driver OK**. Si alguno sale en rojo ❌, dale a **"2. Instalar PKG"**.
3.  Configura tus proxies y dale a **"🚀 3. CREAR TÚNEL CENTRAL"**.

---

## 🛠️ Preguntas Frecuentes (Troubleshooting)

| Problema | Solución |
| :--- | :--- |
| **"Error de Node/NPM"** | Asegúrate de que instalaste Node.js y reiniciaste la PC una vez para que Windows lo reconozca. |
| **"No se reconoce ningún dispositivo"** | Prueba cambiando de puerto USB en el HUB o verifica que el teléfono tenga la "Depuración USB" activa. |
| **"La ventana se queda pegada"** | Ahora puedes cerrarla con la [X] o el botón de confirmación; el sistema tiene un límite de 12 segundos para no colgarse. |
| **"Os Error 10048"** | Solucionado en esta versión. El sistema ahora limpia procesos "muertos" antes de iniciar un nuevo túnel. |

---

## 🧠 Memoria Técnica de Mejoras Realizadas
*   **Relay Centralizado:** Un solo servidor para los 40 equipos (evita choques de puertos).
*   **Paralelismo Seguro:** Operaciones de red en lotes de 10 (evita saturar el HUB USB).
*   **Mapeo Manual:** Puedes asignar proxies específicos a teléfonos específicos.
*   **Auto-Reparación:** El script `auto_repair.py` detecta y corrige fallos de archivos faltantes.

¡Tu granja ahora es portátil y mucho más inteligente! 🚀
