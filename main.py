import os
import sys

# Asegurar que el directorio raíz esté en sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.engine import Engine
from scenes.main_menu import MainMenuScene

def main() -> None:
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
