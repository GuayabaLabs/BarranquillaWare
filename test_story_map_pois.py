import os
import pygame

# Headless SDL video setup
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from core.settings import SettingsManager
from scenes.story_map import StoryMapScene

def test_full_6_pois_suite():
    print("Iniciando suite de verificación de los 8 POIs del Mapa Mundial...")
    settings = SettingsManager.get_instance()
    settings.reset_story_progress()

    scene = StoryMapScene(character_id="westcol")
    assert scene.world_map.get_size() == (3342, 1882), "Dimensiones incorrectas de world_map"

    expected_pois = ["mallorquin", "uninorte", "buenavista", "ventana", "malecon", "aleta", "metropolitano", "aeropuerto"]
    for p in expected_pois:
        assert p in scene.poi_registry, f"Falta {p} en poi_registry"
        assert hasattr(scene, f"{p}_rect"), f"Falta {p}_rect en scene"
        print(f"[OK] POI '{p}' registrado con rect: {scene.poi_registry[p]['rect']}")

    # Abrir y cerrar tarjeta modal de cada POI
    for p_key in expected_pois:
        scene._open_quest_card(p_key)
        assert scene.quest_card_open is True
        assert scene.active_poi == p_key

        surf = pygame.Surface((1920, 1080))
        scene.quest_card_anim_t = 1.0
        scene._render_quest_card(surf)
        scene._close_quest_card()
        assert scene.quest_card_open is False

    # Probar renderizado limpio del mapa
    test_screen = pygame.Surface((1920, 1080))
    scene.update(0.016)
    scene.render(test_screen)
    print("[OK] Renderizado del mapa mundial y HUD completado sin errores.")
    print("TODAS LAS PRUEBAS DE POIS Y MAPA MUNDIAL PASARON SATISFACTORIAMENTE (EXIT 0).")

if __name__ == "__main__":
    test_full_6_pois_suite()
