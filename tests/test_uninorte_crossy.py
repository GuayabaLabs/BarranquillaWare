import sys
import pygame
from core.engine import Engine
from microgames.uninorte_sprint import UninorteSprintMicrogame

def main() -> None:
    """
    Lanzador de prueba de UninorteSprintMicrogame usando el Engine oficial de BarranquillaWare:
    - Respeta la resolución de ventana configurada en settings.json (ej: 1668x945) y ventana redimensionable (RESIZABLE).
    - Presiona 'R' para reiniciar rápidamente el microjuego.
    """
    engine = Engine(title="Test - Microjuego Uninorte Sprint (Crossy Road)")

    def start_new_round() -> None:
        def on_complete(won: bool) -> None:
            print(f"=== RESULTADO DEL MICROJUEGO: {'VICTORIA (LLEGÓ AL SALÓN)' if won else 'DERROTA (CERRARON LA PUERTA)'} ===")
            # Reiniciar automáticamente tras terminar la fase outro para seguir probando
            start_new_round()

        game = UninorteSprintMicrogame(character_id="westcol", on_complete_callback=on_complete)
        engine.state_machine.change_state(game)

    start_new_round()
    engine.run()

if __name__ == "__main__":
    main()
