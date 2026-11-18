"""
Lanzador de Demostración y Pruebas Rápidas (Dev Launcher) para BarranquillaWare.
Permite iniciar directamente en cualquier escena, modo o microjuego sin pasar por los menús.

Uso:
    python run_demo.py --game penalty
    python run_demo.py --game flamenco
    python run_demo.py --game sprint
    python run_demo.py --game ventana
    python run_demo.py --game rueda
    python run_demo.py --game aeropuerto
    python run_demo.py --scene story
    python run_demo.py --scene arcade
    python run_demo.py --scene freeplay
    python run_demo.py --scene character
"""

import argparse

from core.engine import Engine
from scenes.main_menu import MainMenuScene
from scenes.mode_select import ModeSelectScene
from scenes.character_select import CharacterSelectScene
from scenes.story_map import StoryMapScene
from scenes.arcade_mode import ArcadeModeScene
from scenes.free_play import FreePlayScene

from microgames.mallorquin_photo import MallorquinPhotoMicrogame
from microgames.uninorte_sprint import UninorteSprintMicrogame
from microgames.ventana_colores import VentanaColoresMicrogame
from microgames.malecon_rueda import MaleconRuedaMicrogame
from microgames.metropolitano_penalty import MetropolitanoPenaltyMicrogame
from microgames.aeropuerto_aterrizaje import AeropuertoAterrizajeMicrogame
from microgames.fritanga_84 import Fritanga84Microgame
from microgames.troja_baile import TrojaBaileMicrogame

def main():
    parser = argparse.ArgumentParser(description="BarranquillaWare Fast Play / Dev Launcher")
    parser.add_argument("--scene", choices=["main", "mode", "character", "story", "arcade", "freeplay"], default=None,
                        help="Escena inicial a cargar")
    parser.add_argument("--game", choices=["flamenco", "sprint", "ventana", "rueda", "penalty", "aeropuerto", "fritanga", "troja"], default=None,
                        help="Microjuego específico a probar directamente")
    parser.add_argument("--char", default="westcol", choices=["westcol", "char", "katherine", "shakira"],
                        help="Personaje activo a utilizar")
    parser.add_argument("--software", action="store_true", help="Forzar renderizado por software (sin ModernGL)")

    args = parser.parse_args()

    engine = Engine(title="BarranquillaWare - Fast Play Dev Launcher", enable_gl=not args.software)

    target_state = None

    if args.game:
        game_map = {
            "flamenco": MallorquinPhotoMicrogame,
            "sprint": UninorteSprintMicrogame,
            "ventana": VentanaColoresMicrogame,
            "rueda": MaleconRuedaMicrogame,
            "penalty": MetropolitanoPenaltyMicrogame,
            "aeropuerto": AeropuertoAterrizajeMicrogame,
            "fritanga": Fritanga84Microgame,
            "troja": TrojaBaileMicrogame
        }
        chosen_cls = game_map[args.game]
        target_state = chosen_cls(character_id=args.char, on_complete_callback=lambda won: print(f"Resultado: {'VICTORIA' if won else 'DERROTA'}"))

    elif args.scene:
        if args.scene == "main":
            target_state = MainMenuScene()
        elif args.scene == "mode":
            target_state = ModeSelectScene()
        elif args.scene == "character":
            target_state = CharacterSelectScene()
        elif args.scene == "story":
            target_state = StoryMapScene(character_id=args.char)
        elif args.scene == "arcade":
            target_state = ArcadeModeScene(character_id=args.char)
        elif args.scene == "freeplay":
            target_state = FreePlayScene(character_id=args.char)
    else:
        # Por defecto iniciar en el Menú Principal
        target_state = MainMenuScene()

    engine.state_machine.change_state(target_state)
    engine.run()

if __name__ == "__main__":
    main()
