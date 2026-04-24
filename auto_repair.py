import os
import ssl
import urllib.request
import zipfile
import shutil
import subprocess

# SSL fix: some Windows/Python installs lack proper CA certificates
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def download_and_extract(url, zip_name, target_dir=None, flatten=False):
    print(f"[*] Descargando {zip_name} desde {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "OmniUSB/4.0"})
    with urllib.request.urlopen(req, context=ssl_ctx) as resp, open(zip_name, "wb") as f:
        f.write(resp.read())
    print(f"[*] Extrayendo {zip_name} ...")
    
    extract_path = target_dir if target_dir else "temp_extract"
    os.makedirs(extract_path, exist_ok=True)
    
    with zipfile.ZipFile(zip_name, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
        
    if flatten:
        # Move all files from subfolders to the root of the app
        for root, dirs, files in os.walk(extract_path):
            for file in files:
                source_file = os.path.join(root, file)
                dest_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), file)
                # Don't overwrite if not needed, or force overwrite
                shutil.move(source_file, dest_file)
        shutil.rmtree(extract_path, ignore_errors=True)
        
    if os.path.exists(zip_name):
        os.remove(zip_name)
    print(f"[+] Completado: {zip_name}")

def verify_system_integrity():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    print("=== AIDX Proxy Farm V3 : VERIFICANDO INTEGRIDAD ===")
    
    # 1. Check Gnirehtet
    if not os.path.exists("gnirehtet.exe") or not os.path.exists("gnirehtet.apk"):
        print("[!] Gnirehtet faltante. Iniciando Auto-Reparación...")
        gnirehtet_url = "https://github.com/Genymobile/gnirehtet/releases/download/v2.5.3/gnirehtet-rust-win64-v2.5.3.zip"
        # Since v2.5.3 contains a folder `gnirehtet-rust-win64-2.5.3`, we use flatten=True
        try:
            download_and_extract(gnirehtet_url, "gnirehtet_dl.zip", flatten=True)
        except Exception as e:
            print("[X] Fallo al descargar Gnirehtet:", e)

    # 2. Check ADB (Platform-tools)
    if not os.path.exists(os.path.join("platform-tools", "adb.exe")):
        print("[!] ADB (Platform Tools) faltante. Iniciando Auto-Reparación...")
        adb_url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
        try:
            # This extracts a `platform-tools` folder natively
            download_and_extract(adb_url, "platform_tools_dl.zip", target_dir=base_dir, flatten=False)
        except Exception as e:
            print("[X] Fallo al descargar ADB:", e)

    # 3. Check scrcpy (Screen Mirror)
    scrcpy_dir = os.path.join(base_dir, "scrcpy")
    if not os.path.exists(os.path.join(scrcpy_dir, "scrcpy.exe")):
        print("[!] scrcpy (Screen Mirror) faltante. Iniciando Auto-Reparación...")
        scrcpy_url = "https://github.com/Genymobile/scrcpy/releases/download/v3.2/scrcpy-win64-v3.2.zip"
        try:
            download_and_extract(scrcpy_url, "scrcpy_dl.zip", target_dir=base_dir, flatten=False)
            # Rename extracted folder to 'scrcpy'
            for item in os.listdir(base_dir):
                if item.startswith("scrcpy-win64") and os.path.isdir(os.path.join(base_dir, item)):
                    os.rename(os.path.join(base_dir, item), scrcpy_dir)
                    break
        except Exception as e:
            print("[X] Fallo al descargar scrcpy:", e)

    # 3. Check NodeJS — auto-descarga portable si no está en el sistema
    local_node = os.path.join(base_dir, "node", "node.exe")
    node_ok = False

    try:
        subprocess.run(["node", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        node_ok = True
    except Exception:
        if os.path.exists(local_node):
            node_ok = True
            print("[+] Usando NodeJS portable local.")

    if not node_ok:
        print("[!] NodeJS no encontrado. Descargando versión portable (~30MB)...")
        node_url = "https://nodejs.org/dist/v20.18.3/node-v20.18.3-win-x64.zip"
        node_temp = os.path.join(base_dir, "_node_temp")
        node_dest = os.path.join(base_dir, "node")
        try:
            download_and_extract(node_url, "_node_dl.zip", target_dir=node_temp, flatten=False)
            for item in os.listdir(node_temp):
                item_path = os.path.join(node_temp, item)
                if os.path.isdir(item_path) and item.startswith("node-"):
                    shutil.move(item_path, node_dest)
                    break
            shutil.rmtree(node_temp, ignore_errors=True)
            print("[+] NodeJS portable instalado en ./node/")
        except Exception as e:
            print(f"[X] No se pudo descargar NodeJS: {e}")
            print("[X] Instálalo manualmente desde nodejs.org y reinicia la app.")
            input("Presiona ENTER para salir...")
            exit(1)

    # 4. Ensure Node dependencies are present now, not during run
    if not os.path.exists(os.path.join(base_dir, "node_modules", "proxy-chain")):
        print("[*] Instalando dependencias de Node (proxy-chain)... Esto solo ocurre una vez.")
        npm_exe = os.path.join(base_dir, "node", "npm.cmd") if os.path.exists(local_node) else ("npm.cmd" if os.name == "nt" else "npm")
        subprocess.run([npm_exe, "install", "proxy-chain"], cwd=base_dir, shell=True)

    # 5. Check Python Requirements (Self-Heal Venv)
    if os.path.exists("requirements.txt"):
        print("[*] Verificando librerías de Python... (psutil, customtkinter, etc.)")
        try:
            # We use the current python executable to install requirements
            subprocess.run([os.sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            print("[!] Aviso: No se pudieron actualizar las librerías automáticamente.")

    # 6. Pre-start ADB server to avoid timeouts on first scan
    print("[*] Sincronizando con el motor ADB...")
    adb_exe = os.path.join(base_dir, "platform-tools", "adb.exe")
    if os.path.exists(adb_exe):
        subprocess.run([adb_exe, "start-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("=== SISTEMA 100% LISTO Y OPERATIVO ===")

if __name__ == "__main__":
    verify_system_integrity()
