import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.engine import Engine
from microgames.buenavista_trend import BuenavistaTrendMicrogame


def main() -> None:
    """Ejecuta directamente el microjuego 'El Trend en Buenavista' en 1920x1080."""
    engine = Engine(title="BarranquillaWare - Nivel Buenavista: El Trend en Buenavista")

    def start_round() -> None:
        def on_complete(won: bool) -> None:
            result = microgame.get_result_data()
            estado = "¡VICTORIA!" if won else "¡DERROTA!"
            print(
                f"[El Trend en Buenavista] {estado} | "
                f"Vidas: {result['lives_left']}/{result['max_lives']} | "
                f"Perfectos: {result['hits_perfect']} | "
                f"Bien: {result['hits_good']} | "
                f"Fallos: {result['misses']} | "
                f"Combo máx: {result['max_combo']} | "
                f"Tiempo: {result['time_survived']:.1f}s"
            )

        microgame = BuenavistaTrendMicrogame(
            character_id="westcol",
            on_complete_callback=on_complete
        )
        engine.state_machine.change_state(microgame)

    start_round()
    engine.run()


if __name__ == "__main__":
    main()
