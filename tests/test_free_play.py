import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from scenes.free_play import FreePlayScene
from scenes.arcade_mode import ArcadeModeScene
from microgames.coaster_launcher import CoasterLauncherState

def test_free_play_flow():
    print("Iniciando suite de verificación del Modo Libre (Catálogo de Minijuegos)...")
    scene = FreePlayScene(character_id="westcol")
    assert len(scene.games_data) == 7, "Deben haber 7 minijuegos en el catálogo de Modo Libre"
    assert len(scene.card_rects) == 7, "Deben haber 7 rectángulos de tarjetas en la cuadrícula"
    assert "coaster" in [g["id"] for g in scene.games_data], "Coaster debe estar disponible en Modo Libre"
    print("[OK] FreePlayScene inicializada con cuadrícula de 7 minijuegos (incluyendo Coaster).")

    # 1. Probar que cada tarjeta puede lanzar su minijuego
    for idx, g_data in enumerate(scene.games_data):
        mg = g_data["cls"](character_id="westcol", on_complete_callback=scene._on_game_complete)
        assert mg is not None
        if hasattr(mg, "cleanup"):
            mg.cleanup()
        print(f"[OK] Minijuego {idx+1}: '{g_data['title']}' ({g_data['district']}) instanciable correctamente.")

    # 2. Renderizar pantalla del catálogo
    test_screen = pygame.Surface((1920, 1080))
    scene.update(0.016)
    scene.render(test_screen)

    art_path = "render_free_play_catalog.png"
    pygame.image.save(test_screen, art_path)
    print(f"[OK] Snapshot del Catálogo Modo Libre guardado en: {art_path}")

    print("TODAS LAS PRUEBAS DEL MODO LIBRE PASARON SATISFACTORIAMENTE (EXIT 0).")


def test_free_play_launches_and_pauses_coaster():
    from core.state_machine import StateMachine
    from core.microgame_pause import MicrogamePauseState

    assert CoasterLauncherState not in ArcadeModeScene().microgame_pool

    scene = FreePlayScene(character_id="westcol")
    sm = StateMachine()
    sm.change_state(scene)

    coaster_idx = next(i for i, g in enumerate(scene.games_data) if g["id"] == "coaster")
    scene._launch_game(coaster_idx)
    coaster_state = sm.current_state
    assert isinstance(coaster_state, CoasterLauncherState)
    assert coaster_state.game is not None
    assert coaster_state.hide_return_to_map is True

    # Pausa con ESC y salida limpia de vuelta a Modo Libre
    coaster_state.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
    assert isinstance(sm.current_state, MicrogamePauseState)
    coaster_state.pause_menu_callback()
    assert sm.current_state is scene


if __name__ == "__main__":
    test_free_play_flow()
