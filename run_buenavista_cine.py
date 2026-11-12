import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.engine import Engine
from microgames.buenavista_cine import BuenavistaCineMicrogame


def main() -> None:
    """Ejecuta directamente el microjuego ¡Silencio, que hay función! 🎬 en 1920x1080."""
    engine = Engine(title="BarranquillaWare - Nivel 2 Buenavista: ¡Silencio, que hay función! 🎬")

    def on_complete(won: bool) -> None:
        result = microgame.get_result_data()
        estado = "¡VICTORIA!" if won else "¡DERROTA!"
        print(
            f"[¡Silencio, que hay función!] {estado} | "
            f"Faltas: {result['strikes']}/2 | "
            f"Espectadores callados: {result['pacified_count']} | "
            f"Tiempo: {result['time_survived']:.1f}s"
        )

    microgame = BuenavistaCineMicrogame(
        character_id="char",
        on_complete_callback=on_complete
    )
    engine.state_machine.change_state(microgame)
    engine.run()


if __name__ == "__main__":
    main()
