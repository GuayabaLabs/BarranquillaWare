import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from scenes.free_play import FreePlayScene

def test_free_play_flow():
    print("Iniciando suite de verificación del Modo Libre (Catálogo de Minijuegos)...")
    scene = FreePlayScene(character_id="westcol")
    assert len(scene.games_data) >= 8, "Deben haber al menos 8 minijuegos en el catálogo"
    assert len(scene.card_rects) == 8, "Deben haber 8 rectángulos de tarjetas en la cuadrícula"
    assert hasattr(scene, "boss_card_rect"), "Falta la tarjeta de la Etapa Jefe"
    print("[OK] FreePlayScene inicializada con cuadrícula de 8 minijuegos y Etapa Jefe dorada.")

    # 1. Probar que cada tarjeta puede lanzar su minijuego
    for idx, g_data in enumerate(scene.games_data):
        mg = g_data["cls"](character_id="westcol", on_complete_callback=scene._on_game_complete)
        assert mg is not None
        print(f"[OK] Minijuego {idx+1}: '{g_data['title']}' ({g_data['district']}) instanciable correctamente.")

    # 2. Renderizar pantalla del catálogo
    test_screen = pygame.Surface((1920, 1080))
    scene.update(0.016)
    scene.render(test_screen)

    art_path = "render_free_play_catalog.png"
    pygame.image.save(test_screen, art_path)
    print(f"[OK] Snapshot del Catálogo Modo Libre guardado en: {art_path}")

    print("TODAS LAS PRUEBAS DEL MODO LIBRE PASARON SATISFACTORIAMENTE (EXIT 0).")

if __name__ == "__main__":
    test_free_play_flow()
