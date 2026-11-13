import os
import sys

# Asegurar que el directorio raíz esté en sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.engine import Engine
from scenes.story_map.scene import StoryMapScene

def main() -> None:
    engine = Engine(title="BarranquillaWare - Verificacion Modal")
    # Iniciar directo en el mapa de historia
    map_scene = StoryMapScene(character_id="sofia")
    # Abrir directamente la tarjeta de misión de Uninorte
    map_scene._open_quest_card("uninorte")
    map_scene.quest_card_anim_t = 1.0
    
    engine.state_machine.change_state(map_scene)
    engine.run()

if __name__ == "__main__":
    main()
