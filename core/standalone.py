"""Ejecutar un minijuego solo, sin pasar por el menú: `python microgames/<juego>.py`.

El archivo del minijuego debe agregar la raíz del proyecto a sys.path antes de importar `core`
(ver el bloque `if __name__ == "__main__"` al inicio de microgames/curramgram_go.py).
"""
from typing import Type

from core.engine import Engine


def ejecutar_minijuego(cls: Type, titulo: str = "BarranquillaWare") -> None:
    """Abre la ventana del juego con este minijuego; al terminar o reiniciar vuelve a empezar."""
    engine = Engine(title=titulo)

    def lanzar(_ganado: bool = False) -> None:
        juego = cls(on_complete_callback=lanzar)
        juego.pause_restart_callback = lanzar
        juego.pause_menu_callback = salir
        engine.state_machine.change_state(juego)

    def salir() -> None:
        engine.is_running = False

    lanzar()
    engine.run()
