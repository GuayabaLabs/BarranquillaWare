import os
import pygame

# Headless SDL video setup
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from core.settings import SettingsManager
from scenes.story_map import StoryMapScene
from scenes.story_map_data import trofeosMapa
from ui.social_hud import SocialHUD
from ui.side_drawer import SideNavDrawer


def test_achievements_catalog_and_trophies():
    """Verifica que existan los 4 logros oficiales según los requerimientos de la Tarea 002."""
    assert len(trofeosMapa) == 4, f"Se esperaban 4 logros oficiales, encontrados: {len(trofeosMapa)}"
    ids = [t["id"] for t in trofeosMapa]
    assert "vueltaVentana" in ids
    assert "vueltaAleta" in ids
    assert "charlaPaloma" in ids
    assert "despejarUninorte" in ids


def test_social_hud_logros_click():
    """Verifica que hacer clic en la píldora de Logros del HUD despacha el callback."""
    clicked = []
    hud = SocialHUD(1920, 1080, on_logros_click=lambda: clicked.append(True))
    
    # Simular clic dentro de la cápsula de logros (x: 1320, y: 28, w: 258, h: 86)
    click_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (1350, 50)})
    consumed = hud.handle_event(click_ev)
    assert consumed is True
    assert len(clicked) == 1, "El callback de clic en logros debió ser ejecutado"


def test_story_map_achievements_triggers():
    """Verifica el desbloqueo de logros por hablar con la Paloma y por despejar Uninorte."""
    settings = SettingsManager.get_instance()
    settings.reset_story_progress()
    settings.set("trofeosObtenidos", [])

    scene = StoryMapScene(character_id="westcol")
    assert scene.social_hud.pills["logros"].value_text == "0/4"

    # 1. Simular pulsar tecla 'L' para abrir el panel de trofeos
    l_key_ev = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_l})
    scene.handle_event(l_key_ev)
    assert scene.side_drawer.is_open is True
    assert scene.side_drawer.seccionActual == "trofeos"

    # 2. Desbloquear logro de Paloma al conversar con ella
    scene.open_paloma_dialog(["¡Hola viajero!", "Vamos a salvar la ciudad."])
    scene.advance_paloma_dialog()
    scene.advance_paloma_dialog()
    assert "charlaPaloma" in scene.leerTrofeosObtenidos()
    assert scene.social_hud.pills["logros"].value_text == "1/4"

    # 3. Desbloquear logro de Uninorte al completar el nivel
    scene.active_poi = "uninorte"
    scene.current_level_stage_idx = 0
    scene._on_microgame_complete(True)  # Ronda 1
    scene._on_microgame_complete(True)  # Ronda 2 (completa nivel)
    assert "despejarUninorte" in scene.leerTrofeosObtenidos()
    assert scene.social_hud.pills["logros"].value_text == "2/4"

    # 4. Renderizar drawer con los trofeos desbloqueados
    surf = pygame.Surface((1920, 1080))
    scene.side_drawer.anim_t = 1.0
    scene.side_drawer.render(surf)
