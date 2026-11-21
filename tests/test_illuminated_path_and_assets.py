"""
Pruebas de integridad de assets IA acuarela, camino iluminado en Modo Historia
(Dijkstra real, oclusión sobre edificios, revelación 0..1, disparo con ESC y paneo de cámara)
y mejoras de interacción en modales simplificados.
"""
import copy
import math
import os
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from core.audio_manager import AudioManager
from core.settings import SettingsManager
from scenes.main_menu import MainMenuScene
from scenes.story_map.path_glow import compute_campaign_dijkstra_path
from scenes.story_map.scene import StoryMapScene
from scenes.story_map_data import STORY_CAMPAIGN_ORDER


@pytest.fixture(autouse=True)
def _headless_and_preserve_settings():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1920, 1080))
    settings = SettingsManager.get_instance()
    snap = copy.deepcopy(settings.data)
    audio = AudioManager.get_instance()
    try:
        yield settings
    finally:
        audio.stop_voice(fade_ms=0)
        settings.data = snap
        settings.save()


def test_new_ia_watercolor_assets_exist_and_have_clean_alpha():
    expected = [
        "assets/pin_nivel_mapa.png",
        "assets/mapa_camino_pincelada.png",
        "assets/mapa_destello_ruta.png",
        "assets/mapa_faro_destino.png",
        "assets/Interfaz/modal_victoria_carnaval.png",
        "assets/Interfaz/mascara_marimonda_vida.png",
        "assets/Interfaz/mascara_marimonda_rota.png",
        "assets/Interfaz/pildora_clima_acuarela.png",
        "assets/Interfaz/icono_clima_day.png",
        "assets/Interfaz/icono_clima_sunset.png",
        "assets/Interfaz/icono_clima_night.png",
        "assets/Interfaz/icono_clima_rain.png",
        "assets/Interfaz/icono_voz_silenciada.png",
    ]
    for rel in expected:
        p = Path(rel)
        assert p.is_file(), f"Falta asset IA convertido: {rel}"
        surf = pygame.image.load(str(p)).convert_alpha()
        w, h = surf.get_size()
        assert w >= 32 and h >= 32
        alpha = pygame.surfarray.array_alpha(surf)
        assert int(alpha.max()) >= 200, f"{rel} sin píxeles opacos"
        # Al menos las esquinas exteriores deben tener transparencia limpia
        corner_min = min(
            int(alpha[0, 0]),
            int(alpha[w - 1, 0]),
            int(alpha[0, h - 1]),
            int(alpha[w - 1, h - 1]),
        )
        assert corner_min <= 10, f"{rel} conserva fondo opaco en esquinas: {corner_min}"

    # El pergamino interior de modal_victoria_carnaval.png debe permanecer 100% opaco
    vic = pygame.image.load("assets/Interfaz/modal_victoria_carnaval.png").convert_alpha()
    vw, vh = vic.get_size()
    center_alpha = pygame.surfarray.array_alpha(vic)[vw // 2 - 40 : vw // 2 + 40, vh // 2 - 40 : vh // 2 + 40]
    assert int(center_alpha.min()) == 255


def test_dijkstra_campaign_routes_pixel_distance_and_poi_occlusion():
    scene = StoryMapScene(character_id="westcol")
    nodes, edges, _node_map, _adj, _edge_map = scene._get_street_graph()

    # Uninorte (71) -> Buenavista (76) debe ir por el bulevar sur directo (~1673 px) sin aristas ocultas
    n_uni = scene._get_poi_target_node("uninorte")
    n_bue = scene._get_poi_target_node("buenavista")
    path_ub = compute_campaign_dijkstra_path(nodes, edges, n_uni, n_bue)
    assert path_ub == [71, 70, 48, 39, 74, 75, 76]

    # Todas las transiciones consecutivas de la campaña deben resolver y no tapar ningún monumento
    occluders = scene._get_poi_occluders()
    for a, b in zip(STORY_CAMPAIGN_ORDER, STORY_CAMPAIGN_ORDER[1:]):
        route = scene._build_campaign_route(a, b)
        assert route is not None, f"No se pudo construir ruta {a} -> {b}"
        assert route["total_dist"] > 300.0
        full_surf: pygame.Surface = route["full_surf"]
        bbox: pygame.Rect = route["bbox"]
        route_alpha = pygame.surfarray.array_alpha(full_surf)
        assert int(route_alpha.max()) > 100

        for poi_surf, poi_rect in occluders:
            inter = poi_rect.clip(bbox)
            if inter.width <= 0 or inter.height <= 0:
                continue
            px0, py0 = inter.x - poi_rect.x, inter.y - poi_rect.y
            rx0, ry0 = inter.x - bbox.x, inter.y - bbox.y
            poi_a = pygame.surfarray.pixels_alpha(poi_surf)[px0 : px0 + inter.width, py0 : py0 + inter.height]
            rt_a = route_alpha[rx0 : rx0 + inter.width, ry0 : ry0 + inter.height]
            leaked = rt_a[poi_a >= 6]
            del poi_a
            assert leaked.size == 0 or int(leaked.max()) == 0, f"Ruta {a}->{b} tapó monumento en {inter}"


def test_illuminated_path_reveal_progress_esc_trigger_and_camera_pan():
    settings = SettingsManager.get_instance()
    settings.reset_story_progress()
    scene = StoryMapScene(character_id="westcol")
    scene.show_intro_dialog = False
    scene.paloma_dialog_open = False
    scene.paloma_dialog_anim_t = 0.0
    scene.cinematic_timer = scene.cinematic_duration

    # Completar Uninorte (Ronda 1 + Ronda 2) -> abre avisoTrofeo y encola palomaPendiente + _pending_path_reveal
    scene.active_poi = "uninorte"
    scene.current_level_stage_idx = 0
    scene._on_microgame_complete(True)
    scene._on_microgame_complete(True)
    assert scene._pending_path_reveal == ("uninorte", "ventana")

    # Cerrar avisoTrofeo -> abre diálogo post-victoria de la Paloma
    if scene.avisoTrofeo.estaOcupado():
        scene.avisoTrofeo.cerrar()
        scene.avisoTrofeo.vuelo = -1.0
        scene.update(0.05)
    assert scene.paloma_dialog_open is True
    assert scene.active_path_reveal is None, "No debe revelar mientras paloma_dialog_open esté abierto"

    # Saltar el diálogo de la Paloma con ESC también debe disparar el camino iluminado en update()
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
    assert scene.paloma_dialog_open is False
    with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
        scene.update(0.02)

    assert scene.active_path_reveal is not None
    assert scene.active_path_reveal["pair"] == ("uninorte", "ventana")
    assert scene.active_path_reveal["controls_camera"] is True

    # Verificar progresión 0 -> 0.5 -> 1.0 y cambio de pixels en superficie revelada
    surf = pygame.Surface((1920, 1080))
    route_data = scene.active_path_reveal["route"]
    rev_0 = scene.path_glow_renderer.get_revealed_surface(route_data, 0.0)
    nz_0 = int(np.count_nonzero(pygame.surfarray.array_alpha(rev_0) > 10))
    rev_mid = scene.path_glow_renderer.get_revealed_surface(route_data, 0.5)
    nz_mid = int(np.count_nonzero(pygame.surfarray.array_alpha(rev_mid) > 10))
    rev_full = scene.path_glow_renderer.get_revealed_surface(route_data, 1.0)
    nz_full = int(np.count_nonzero(pygame.surfarray.array_alpha(rev_full) > 10))
    assert nz_0 < nz_mid < nz_full

    # Resetear last_progress para avanzar la simulación real de escena hasta completar paneo y volver al jugador
    route_data["last_progress"] = -1.0
    with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
        for _ in range(90):
            scene.update(0.05)
            scene.render(surf)

    assert scene.active_path_reveal is None
    assert ("uninorte", "ventana") in scene._unlocked_path_pairs
    expected_cx = max(0.0, min(float(scene.camera.max_x), scene.player_pos[0] - scene.screen_w / 2.0))
    expected_cy = max(0.0, min(float(scene.camera.max_y), scene.player_pos[1] - scene.screen_h / 2.0))
    assert math.hypot(scene.camera.x - expected_cx, scene.camera.y - expected_cy) < 40.0


def test_main_menu_logros_modal_close_x_hitbox():
    menu = MainMenuScene()
    menu._open_modal("logros")
    menu.modal_alpha = 255.0

    # Clic dentro del cuerpo del modal (fuera de X) NO cierra el modal
    menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (960, 540)}))
    assert menu.active_modal == "logros"

    # Clic exacto en el botón X sí cierra el modal
    menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": menu._modal_close_rect.center}))
    assert menu.active_modal is None
