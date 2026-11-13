import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.engine import Engine
from microgames.uninorte_concentrate import UninorteConcentrateMicrogame


def main() -> None:
    """Ejecuta el microjuego '¡Concéntrate, llave!' directamente en ventana 1920x1080."""
    engine = Engine(title="BarranquillaWare - Nivel 1 Uninorte: ¡Concéntrate, llave!")

    def on_complete(won: bool) -> None:
        result = microgame.get_result_data()
        estado = "¡VICTORIA!" if won else "¡DERROTA!"
        print(
            f"[¡Concéntrate, llave!] {estado} | "
            f"Puntos: {result['score']} | "
            f"Racha máx: {result['max_streak']} | "
            f"Progreso: {result['task_progress']:.1f}%"
        )

    microgame = UninorteConcentrateMicrogame(
        character_id="westcol",
        on_complete_callback=on_complete
    )
    engine.state_machine.change_state(microgame)
    engine.run()


if __name__ == "__main__":
    main()
