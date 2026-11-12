"""
Script de Compilación y Empaquetado Autónomo (Standalone Executable) para BarranquillaWare.
Uso:
    python build_standalone.py [--onefile]
"""

import os
import sys
import subprocess

def check_or_install_pyinstaller():
    try:
        import PyInstaller
        print(f"[OK] PyInstaller detectado versión: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("[AVISO] PyInstaller no está instalado en el entorno. Intentando instalar...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("[OK] PyInstaller instalado satisfactoriamente.")
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo instalar PyInstaller automáticamente: {e}")
            print("Instala manualmente ejecutando: pip install pyinstaller")
            return False

def build_executable(onefile: bool = False):
    print("=" * 70)
    print("INICIANDO COMPILACIÓN DE BARRANQUILLA WARE STANDALONE")
    print("=" * 70)

    if not check_or_install_pyinstaller():
        sys.exit(1)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    shaders_dir = os.path.join(base_dir, "shaders")

    # Separador de datos en Windows es ';'
    sep = ";" if sys.platform.startswith("win") else ":"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "BarranquillaWare",
        "--noconfirm",
        "--clean",
        "--windowed", # Sin ventana de consola negra
        f"--add-data={assets_dir}{sep}assets",
        f"--add-data={shaders_dir}{sep}shaders",
        "--hidden-import=pygame",
        "--hidden-import=moderngl",
        "--hidden-import=numpy",
        "--hidden-import=core",
        "--hidden-import=scenes",
        "--hidden-import=ui",
        "--hidden-import=microgames",
        "main.py"
    ]

    if onefile:
        cmd.append("--onefile")

    print(f"Ejecutando comando PyInstaller:\n{' '.join(cmd)}\n")
    ret = subprocess.call(cmd)

    if ret == 0:
        print("\n" + "=" * 70)
        dist_path = os.path.join(base_dir, "dist", "BarranquillaWare")
        print(f"[ÉXITO] Compilación completada con éxito.")
        print(f"Directorio de distribución: {dist_path}")
        print("=" * 70)
    else:
        print(f"\n[ERROR] La compilación falló con código de retorno: {ret}")

if __name__ == "__main__":
    is_onefile = "--onefile" in sys.argv
    build_executable(onefile=is_onefile)
