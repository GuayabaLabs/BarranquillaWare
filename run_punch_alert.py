import os
import sys
import pygame

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.engine import Engine
from microgames.punch_alert import PunchAlertMicrogame

def main():
    """Ejecuta Punch-Alert directamente en ventana interactiva 1920x1080."""
    engine = Engine(title="BarranquillaWare - Punch-Alert (El Despachador de Notificaciones)")
    
    def on_complete(won: bool):
        print(f"Resultado del microjuego: {'¡VICTORIA!' if won else '¡DERROTA!'}")
        # Reiniciar tras 1.5 segundos o continuar
    
    microgame = PunchAlertMicrogame(
        command_text="¡DESPACHA EL SPAM!",
        time_limit=15.0,
        character_id="char",
        on_complete_callback=on_complete
    )
    engine.state_machine.change_state(microgame)
    engine.run()

if __name__ == "__main__":
    main()
