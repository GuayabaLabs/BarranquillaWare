import os
import sys
from pathlib import Path

# Asegurar que el directorio raíz esté en sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def _prefer_project_python() -> None:
    """Usa el entorno del juego sin cambiar las dependencias del Python global."""
    root = Path(__file__).resolve().parent
    environment = root / ".venv"
    executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if executable.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        os.execv(str(executable), [str(executable), str(root / "main.py"), *sys.argv[1:]])

def main() -> None:
    _prefer_project_python()
    from core.engine import Engine
    from scenes.main_menu import MainMenuScene

    # Al ejecutar el juego, limpiar el modo dummy heredado de pruebas.
    for driver in ("SDL_AUDIODRIVER", "SDL_VIDEODRIVER"):
        if os.environ.get(driver) == "dummy":
            del os.environ[driver]
    engine = Engine(title="BarranquillaWare")
    menu_scene = MainMenuScene(screen_w=engine.VIRTUAL_WIDTH, screen_h=engine.VIRTUAL_HEIGHT)
    engine.state_machine.change_state(menu_scene)
    engine.run()

if __name__ == "__main__":
    main()
