"""
Pruebas de integridad de assets IA acuarela, camino iluminado en Modo Historia
(Dijkstra real, oclusión sobre edificios, revelación 0..1, disparo con ESC y paneo de cámara)
y mejoras de interacción en modales simplificados.
"""
import copy
import hashlib
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
from microgames.buenavista_trend import (
    BuenavistaTrendMicrogame,
    EN_BARRANQUILLA_BEATMAP_DATA,
    IMITADORA_BEATMAP_DATA,
)
from scenes.main_menu import MainMenuScene
from scenes.story_map.path_glow import build_route_polyline, compute_campaign_dijkstra_path
from scenes.story_map.scene import StoryMapScene
from scenes.story_map_data import PALOMA_STORY_DIALOGS, STORY_CAMPAIGN_ORDER
from tools.map_dev_tool import get_bezier_points


@pytest.fixture(autouse=True)
def _headless_and_preserve_settings(tmp_path):
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1920, 1080))
    workspace_settings = Path(__file__).resolve().parent.parent / "settings.json"
    orig_bytes = workspace_settings.read_bytes() if workspace_settings.exists() else None
    orig_sha = hashlib.sha256(orig_bytes).hexdigest() if orig_bytes is not None else None

    settings = SettingsManager.get_instance()
    orig_filepath = settings.filepath
    if Path(orig_filepath).resolve() == workspace_settings.resolve():
        iso_file = tmp_path / "settings.json"
        if orig_bytes is not None:
            iso_file.write_bytes(orig_bytes)
        settings.filepath = str(iso_file)
        settings.load()

    snap = copy.deepcopy(settings.data)
    audio = AudioManager.get_instance()
    try:
        yield settings
    finally:
        audio.stop_voice(fade_ms=0)
        settings.data = snap
        settings.save()
        settings.filepath = orig_filepath
        if orig_sha is not None and workspace_settings.exists():
            assert hashlib.sha256(workspace_settings.read_bytes()).hexdigest() == orig_sha


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
        "assets/spritesheet_teclas_costenas_piano.png",
        "assets/arbolito_navidad_dia.png",
        "assets/arbolito_navidad_noche.png",
        "assets/alumbrado_poste_dia.png",
        "assets/alumbrado_poste_noche.png",
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


def test_buenavista_costeno_piano_spritesheet_beatmap_and_dialogs():
    game = BuenavistaTrendMicrogame(character_id="westcol")
    assert game.spritesheet_name == "spritesheet_teclas_costenas_piano.png"
    # Sin "en_barranquilla_me_quedo_piano" en assets se usa la canción de respaldo del piano
    assert game.music_track_name in ("en_barranquilla_me_quedo_piano.ogg", "imitadora_ost_piano_tiles_microjuego.ogg")
    assert EN_BARRANQUILLA_BEATMAP_DATA is IMITADORA_BEATMAP_DATA
    assert len(game.musical_events) == len(EN_BARRANQUILLA_BEATMAP_DATA)
    assert len(game.normal_tile_sprites) == 4
    assert len(game.active_tile_sprites) == 4

    # Audio ausente en disco no debe crashear al iniciar PLAY
    game.phase = game.PHASE_PLAY
    game._start_music_if_needed()
    game.update(0.05)
    game.cleanup()

    # Diálogo de la Paloma y metadata de Buenavista actualizados a sabor costeño
    pre_text = " ".join(" ".join(p) for p in PALOMA_STORY_DIALOGS["buenavista"]["pre_pages"]).lower()
    assert "en barranquilla me quedo" in pre_text
    assert "imitadora" not in pre_text
    assert "bachata" not in pre_text

    scene = StoryMapScene(character_id="westcol")
    b_desc = " ".join(scene.poi_registry["buenavista"]["desc"]).lower()
    assert "en barranquilla me quedo" in b_desc
    assert "bachata" not in b_desc


def test_night_campaign_path_glow_and_holiday_decor_placement():
    scene = StoryMapScene(character_id="westcol")
    scene.show_intro_dialog = False
    scene.paloma_dialog_open = False
    scene._unlocked_path_pairs = [("uninorte", "ventana")]

    # Verificar que arbolito y alumbrados no solapan POI_SPECS, nodos ni nubes
    nodes, _edges, _nmap, _adj, _emap = scene._get_street_graph()
    poi_rects = [v["rect"] for v in scene.poi_registry.values()]
    cloud_rects = [
        pygame.Rect(int(c["x"]), int(c["y"]), c["surf"].get_width(), c["surf"].get_height())
        for c in scene.clouds
    ]
    decor_points = [scene.holiday_tree_pos] + list(scene.street_lamp_positions)
    for px, py in decor_points:
        assert all(not r.collidepoint(px, py) for r in poi_rects), f"Decor ({px},{py}) solapa POI"
        assert all(not cr.collidepoint(px, py) for cr in cloud_rects), f"Decor ({px},{py}) solapa nube"
        assert min(math.hypot(px - n["x"], py - n["y"]) for n in nodes) >= 90.0

    # Verificar que en noche todos los tramos de campaña brillan por encima de weather_overlays["night"]
    route_locked = scene._build_campaign_route("ventana", "buenavista")
    assert route_locked is not None
    wx, wy = scene.path_glow_renderer.sample_point_at_progress(route_locked, 0.5)
    cam_x = max(0, min(scene.camera.max_x, int(wx - scene.screen_w // 2)))
    cam_y = max(0, min(scene.camera.max_y, int(wy - scene.screen_h // 2)))
    sx, sy = int(round(wx - cam_x)), int(round(wy - cam_y))

    dark_canvas = pygame.Surface((scene.screen_w, scene.screen_h))
    dark_canvas.fill((30, 35, 50))
    dark_canvas.blit(scene.weather_overlays["night"], (0, 0))
    base_luma = sum(dark_canvas.get_at((sx, sy))[:3])

    scene._render_night_campaign_paths(dark_canvas, cam_x, cam_y)
    glow_luma = sum(dark_canvas.get_at((sx, sy))[:3])
    assert glow_luma > base_luma + 20

    # Render completo en día y noche sobre el arbolito sin errores y con cambio de luminancia
    tx, ty = scene.holiday_tree_pos
    scene.camera.set_pos(max(0, tx - scene.screen_w // 2), max(0, ty - scene.screen_h // 2))
    surf_day = pygame.Surface((scene.screen_w, scene.screen_h))
    surf_night = pygame.Surface((scene.screen_w, scene.screen_h))
    scene.set_weather("day")
    scene.update(0.016)
    scene.render(surf_day)
    scene.set_weather("night")
    scene.update(0.016)
    scene.render(surf_night)
    assert surf_day.get_at((960, 540))[:3] != surf_night.get_at((960, 540))[:3]


def _sample_visible_road_points(scene: StoryMapScene) -> np.ndarray:
    nodes, edges, _nmap, _adj, _emap = scene._get_street_graph()
    node_map = {n["id"]: n for n in nodes}
    road_pts = []
    for edge in edges:
        if edge.get("hidden", False):
            continue
        u, v = edge.get("from"), edge.get("to")
        if u not in node_map or v not in node_map:
            continue
        nu, nv = node_map[u], node_map[v]
        p0 = (nu["x"], nu["y"])
        p1 = (nv["x"], nv["y"])
        pc = (edge.get("ctrl_x", (p0[0] + p1[0]) // 2), edge.get("ctrl_y", (p0[1] + p1[1]) // 2))
        road_pts.extend(get_bezier_points(p0, pc, p1, step_px=4))
    return np.array(road_pts, dtype=np.float32)


def _point_to_rect_dist(pts: np.ndarray, rect: pygame.Rect) -> float:
    dx = np.maximum(0.0, np.maximum(rect.left - pts[:, 0], pts[:, 0] - rect.right))
    dy = np.maximum(0.0, np.maximum(rect.top - pts[:, 1], pts[:, 1] - rect.bottom))
    return float(np.sqrt(dx * dx + dy * dy).min())


def test_holiday_decor_full_bbox_clearance_and_diorama_scale():
    scene = StoryMapScene(character_id="westcol")

    assert 140 <= scene.holiday_tree_day.get_height() <= 165
    assert scene.holiday_tree_night.get_height() == scene.holiday_tree_day.get_height()
    assert 74 <= scene.street_lamp_day.get_height() <= 92
    assert scene.street_lamp_night.get_height() == scene.street_lamp_day.get_height()

    scene_src = Path("scenes/story_map/scene.py").read_text(encoding="utf-8")
    glow_src = Path("scenes/story_map/path_glow.py").read_text(encoding="utf-8")
    for forbidden in ("Punch/arbolito.png", "Punch\\arbolito.png"):
        assert forbidden not in scene_src
        assert forbidden not in glow_src

    nodes, _edges, _nmap, _adj, _emap = scene._get_street_graph()
    poi_rects = [v["rect"] for v in scene.poi_registry.values()]
    cloud_rects = [
        pygame.Rect(int(c["x"]), int(c["y"]), c["surf"].get_width(), c["surf"].get_height())
        for c in scene.clouds
    ]
    road_pts = _sample_visible_road_points(scene)

    tree_w = max(scene.holiday_tree_day.get_width(), scene.holiday_tree_night.get_width())
    tree_h = max(scene.holiday_tree_day.get_height(), scene.holiday_tree_night.get_height())
    lamp_w = max(scene.street_lamp_day.get_width(), scene.street_lamp_night.get_width())
    lamp_h = max(scene.street_lamp_day.get_height(), scene.street_lamp_night.get_height())

    tx, ty = scene.holiday_tree_pos
    tree_rect = pygame.Rect(0, 0, tree_w, tree_h)
    tree_rect.midbottom = (tx, ty)
    assert min(math.hypot(tx - n["x"], ty - n["y"]) for n in nodes) >= 90.0
    assert all(not r.colliderect(tree_rect) for r in poi_rects), "Arbolito solapa POI"
    assert all(not cr.colliderect(tree_rect) for cr in cloud_rects), "Arbolito solapa nube"
    assert _point_to_rect_dist(road_pts, tree_rect) >= 14.0
    tr, tg, tb = scene.base_world_map.get_at((tx, ty))[:3]
    assert tg > tr + 15 and tg > tb + 20, f"Arbolito no está sobre pasto verde: {(tr, tg, tb)}"

    for idx, (lx, ly) in enumerate(scene.street_lamp_positions):
        lamp_rect = pygame.Rect(0, 0, lamp_w, lamp_h)
        lamp_rect.midbottom = (lx, ly)
        assert min(math.hypot(lx - n["x"], ly - n["y"]) for n in nodes) >= 90.0, f"Lamp {idx} muy cerca de nodo"
        assert all(not r.colliderect(lamp_rect) for r in poi_rects), f"Lamp {idx} solapa POI"
        assert all(not cr.colliderect(lamp_rect) for cr in cloud_rects), f"Lamp {idx} solapa nube"
        assert _point_to_rect_dist(road_pts, lamp_rect) >= 14.0, f"Lamp {idx} muy cerca de vía"
        lr, lg, lb = scene.base_world_map.get_at((lx, ly))[:3]
        assert lr > 180 and lg > 130 and lb > 95 and (lr - lb) > 20, f"Lamp {idx} no está sobre acera: {(lr, lg, lb)}"


def test_day_mode_zero_night_glow_and_unlit_decor():
    scene = StoryMapScene(character_id="westcol")
    scene.show_intro_dialog = False
    scene.paloma_dialog_open = False
    scene.set_weather("day")
    scene.update(0.016)
    assert scene.night_mix == 0.0

    surf = pygame.Surface((scene.screen_w, scene.screen_h))
    with patch.object(scene, "_render_night_campaign_paths", wraps=scene._render_night_campaign_paths) as mock_night_paths:
        scene.render(surf)
        mock_night_paths.assert_not_called()

    # Verificar que de día el decorado no emite halos exteriores y de noche sí
    tx, ty = scene.holiday_tree_pos
    cam_x = max(0, min(scene.camera.max_x, tx - scene.screen_w // 2))
    cam_y = max(0, min(scene.camera.max_y, ty - scene.screen_h // 2))

    probe_day = pygame.Surface((scene.screen_w, scene.screen_h))
    probe_day.fill((10, 12, 24))
    scene._render_single_tree(probe_day, cam_x, cam_y, tx, ty, night_mix=0.0)
    sx, sy = tx - cam_x, ty - cam_y
    star_rect = scene.holiday_tree_day.get_rect(midbottom=(sx, sy))
    day_arr = pygame.surfarray.array3d(probe_day)
    tree_a = pygame.surfarray.array_alpha(scene.holiday_tree_day)
    # Fuera de la silueta opaca del árbol y encima de la copa (sin sombras del suelo)
    ring_x0, ring_y0 = star_rect.x, star_rect.y
    patch_day = day_arr[ring_x0 : ring_x0 + star_rect.w, ring_y0 : ring_y0 + int(star_rect.h * 0.78)]
    mask_ext = tree_a[:, : int(star_rect.h * 0.78)] == 0
    ext_diff_day = np.abs(patch_day[mask_ext].astype(np.int32) - np.array([10, 12, 24])).max()
    assert int(ext_diff_day) == 0, "En día no debe haber halo luminoso exterior en el arbolito"

    probe_night = pygame.Surface((scene.screen_w, scene.screen_h))
    probe_night.fill((10, 12, 24))
    scene._render_single_tree(probe_night, cam_x, cam_y, tx, ty, night_mix=1.0)
    night_arr = pygame.surfarray.array3d(probe_night)
    patch_night = night_arr[ring_x0 : ring_x0 + star_rect.w, ring_y0 : ring_y0 + int(star_rect.h * 0.78)]
    ext_luma_gain = patch_night[mask_ext].sum(axis=1).mean() - (10 + 12 + 24)
    assert float(ext_luma_gain) > 25.0 or int(patch_night[mask_ext].sum(axis=1).max()) > (10 + 12 + 24 + 45)


def test_night_path_glow_zero_poi_occlusion_all_campaign_pairs():
    scene = StoryMapScene(character_id="westcol")
    occluders = scene._get_poi_occluders()
    for a, b in zip(STORY_CAMPAIGN_ORDER, STORY_CAMPAIGN_ORDER[1:]):
        route = scene._build_campaign_route(a, b)
        assert route is not None
        bbox: pygame.Rect = route["bbox"]
        for tier in ("active", "completed", "locked"):
            probe = pygame.Surface((bbox.width, bbox.height))
            probe.fill((0, 0, 0))
            scene.path_glow_renderer.render_night_glow_route(
                probe,
                route,
                bbox.x,
                bbox.y,
                timer=0.4,
                unlocked=(tier != "locked"),
                tier=tier,
                intensity=1.0,
            )
            arr = pygame.surfarray.array3d(probe)
            for poi_surf, poi_rect in occluders:
                inter = poi_rect.clip(bbox)
                if inter.width <= 0 or inter.height <= 0:
                    continue
                px0, py0 = inter.x - poi_rect.x, inter.y - poi_rect.y
                rx0, ry0 = inter.x - bbox.x, inter.y - bbox.y
                poi_a = pygame.surfarray.pixels_alpha(poi_surf)[px0 : px0 + inter.width, py0 : py0 + inter.height]
                under = arr[rx0 : rx0 + inter.width, ry0 : ry0 + inter.height][poi_a >= 6]
                del poi_a
                assert under.size == 0 or int(under.max()) == 0, f"Brillo nocturno {a}->{b} ({tier}) tapó POI"


def test_night_decor_multicolor_halos_and_lamp_warm_flame():
    scene = StoryMapScene(character_id="westcol")
    scene.timer = 0.25

    tx, ty = scene.holiday_tree_pos
    cam_x = max(0, min(scene.camera.max_x, tx - scene.screen_w // 2))
    cam_y = max(0, min(scene.camera.max_y, ty - scene.screen_h // 2))
    sx, sy = tx - cam_x, ty - cam_y

    tree_probe = pygame.Surface((scene.screen_w, scene.screen_h))
    tree_probe.fill((0, 0, 0))
    scene._render_single_tree(tree_probe, cam_x, cam_y, tx, ty, night_mix=1.0)
    t_rect = scene.holiday_tree_night.get_rect(midbottom=(sx, sy))
    t_arr = pygame.surfarray.array3d(tree_probe)[
        t_rect.x : t_rect.right, t_rect.y : t_rect.y + int(t_rect.height * 0.80)
    ]
    has_gold = np.any((t_arr[:, :, 0] > 200) & (t_arr[:, :, 1] > 160))
    has_cyan = np.any((t_arr[:, :, 2] > 160) & (t_arr[:, :, 1] > 140))
    has_warm_coral_or_magenta = np.any((t_arr[:, :, 0] > 170) & (t_arr[:, :, 1] < 165))
    assert has_gold and has_cyan and has_warm_coral_or_magenta

    lx, ly = scene.street_lamp_positions[5]
    lcam_x = max(0, min(scene.camera.max_x, lx - scene.screen_w // 2))
    lcam_y = max(0, min(scene.camera.max_y, ly - scene.screen_h // 2))
    lsx, lsy = lx - lcam_x, ly - lcam_y
    lamp_probe = pygame.Surface((scene.screen_w, scene.screen_h))
    lamp_probe.fill((0, 0, 0))
    scene._render_single_lamp(lamp_probe, lcam_x, lcam_y, 5, lx, ly, night_mix=1.0)
    l_rect = scene.street_lamp_night.get_rect(midbottom=(lsx, lsy))
    l_arr = pygame.surfarray.array3d(lamp_probe)[l_rect.x : l_rect.right, l_rect.y : l_rect.bottom]
    lh = l_rect.height
    lantern_band = l_arr[:, int(lh * 0.12) : int(lh * 0.30)]
    lit_mask = lantern_band.sum(axis=2) > 40
    assert np.any(lit_mask)
    mean_r = float(lantern_band[lit_mask][:, 0].mean())
    mean_b = float(lantern_band[lit_mask][:, 2].mean())
    assert mean_r > mean_b + 40.0, f"Linterna del alumbrado debe ser ámbar cálido: R={mean_r}, B={mean_b}"
    shaft_band = l_arr[:, int(lh * 0.32) : int(lh * 0.88)]
    assert int(shaft_band.max()) > 40


def test_entity_y_sorting_player_tree_and_lamps():
    scene = StoryMapScene(character_id="westcol")
    scene.show_intro_dialog = False
    scene.paloma_dialog_open = False
    scene.cinematic_timer = scene.cinematic_duration

    probe_player = pygame.Surface((40, 60), pygame.SRCALPHA)
    probe_player.fill((255, 0, 255, 255))
    scene.player_chibi_surf = probe_player
    scene.player_alpha = 1.0

    def _is_magenta_dominant(col):
        r, g, b = col[:3]
        return r > 110 and b > 120 and g < 60

    tx, ty = scene.holiday_tree_pos
    cam_x = max(0, min(scene.camera.max_x, tx - scene.screen_w // 2))
    cam_y = max(0, min(scene.camera.max_y, ty - scene.screen_h // 2))
    scene.camera.set_pos(cam_x, cam_y)
    surf = pygame.Surface((scene.screen_w, scene.screen_h))

    for mode in ("day", "night"):
        scene.set_weather(mode)
        scene.player_pos = (float(tx), float(ty - 14))
        scene.update(0.016)
        scene.render(surf)
        col_north = surf.get_at((tx - cam_x, ty - cam_y - 12))
        assert not _is_magenta_dominant(col_north), f"{mode}: árbol debe tapar al jugador al norte: {col_north}"

        scene.player_pos = (float(tx), float(ty + 14))
        scene.update(0.016)
        scene.render(surf)
        col_south = surf.get_at((tx - cam_x, ty - cam_y - 12))
        assert _is_magenta_dominant(col_south), f"{mode}: jugador al sur debe verse delante del árbol: {col_south}"

    lx, ly = scene.street_lamp_positions[5]
    lcam_x = max(0, min(scene.camera.max_x, lx - scene.screen_w // 2))
    lcam_y = max(0, min(scene.camera.max_y, ly - scene.screen_h // 2))
    scene.camera.set_pos(lcam_x, lcam_y)
    for mode in ("day", "night"):
        scene.set_weather(mode)
        scene.player_pos = (float(lx), float(ly - 10))
        scene.update(0.016)
        scene.render(surf)
        col_north = surf.get_at((lx - lcam_x, ly - lcam_y - 12))
        assert not _is_magenta_dominant(col_north), f"{mode}: farol debe tapar al jugador al norte: {col_north}"

        scene.player_pos = (float(lx), float(ly + 10))
        scene.update(0.016)
        scene.render(surf)
        col_south = surf.get_at((lx - lcam_x, ly - lcam_y - 12))
        assert _is_magenta_dominant(col_south), f"{mode}: jugador al sur debe verse delante del farol: {col_south}"


def test_weather_cycle_smooth_dt_vs_set_weather_instant():
    scene = StoryMapScene(character_id="westcol")
    scene.set_weather("day")
    assert scene.night_mix == 0.0
    scene.set_weather("night")
    assert scene.night_mix == 1.0

    scene.set_weather("day")
    while scene.current_weather != "night":
        scene.cycle_weather()
    assert scene.current_weather == "night"
    assert 0.0 <= scene.night_mix < 1.0

    scene.update(0.05)
    m1 = scene.night_mix
    scene.update(0.05)
    m2 = scene.night_mix
    assert 0.0 < m1 < m2 < 1.0

    for _ in range(30):
        scene.update(0.05)
    assert scene.night_mix >= 0.99

    scene.cycle_weather()
    assert scene.current_weather == "rain"
    assert scene.night_mix > 0.5
    for _ in range(30):
        scene.update(0.05)
    assert scene.night_mix < 0.05


def test_route_polyline_fillet_smoothness_and_node_55_z_order():
    scene = StoryMapScene(character_id="westcol")
    scene.show_intro_dialog = False
    scene.paloma_dialog_open = False
    scene.cinematic_timer = scene.cinematic_duration

    nodes, edges, node_map, _adj, edge_map = scene._get_street_graph()
    n_bue = scene._get_poi_target_node("buenavista")
    n_met = scene._get_poi_target_node("metropolitano")
    node_path = compute_campaign_dijkstra_path(nodes, edges, n_bue, n_met)
    assert node_path is not None and 75 in node_path

    pts, cum_dists, total_dist = build_route_polyline(node_map, edge_map, node_path, step_px=6, fillet_px=18.0)
    assert total_dist > 300.0
    assert all(cum_dists[i] > cum_dists[i - 1] for i in range(1, len(cum_dists)))

    max_angle_deg = 0.0
    for j in range(1, len(pts) - 1):
        v1 = (pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1])
        v2 = (pts[j + 1][0] - pts[j][0], pts[j + 1][1] - pts[j][1])
        l1 = math.hypot(*v1)
        l2 = math.hypot(*v2)
        if l1 > 1e-4 and l2 > 1e-4:
            cos_a = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)))
            max_angle_deg = max(max_angle_deg, math.degrees(math.acos(cos_a)))
    assert max_angle_deg < 35.0, f"Ángulo máximo tras fileteado demasiado agudo: {max_angle_deg:.1f}°"

    # Verificar que el círculo amarillo de parada en Nodo 55 (Metropolitano) queda encima del brillo nocturno
    n55 = node_map[n_met]
    cam_x = max(0, min(scene.camera.max_x, int(n55["x"] - scene.screen_w // 2)))
    cam_y = max(0, min(scene.camera.max_y, int(n55["y"] - scene.screen_h // 2)))
    scene.player_pos = (808.0, 464.0)  # Alejar jugador del Nodo 55
    scene.set_weather("night")
    scene.update(0.016)
    scene.camera.set_pos(cam_x, cam_y)
    surf = pygame.Surface((scene.screen_w, scene.screen_h))
    scene.render(surf)
    sx, sy = int(n55["x"] - cam_x), int(n55["y"] - cam_y)
    rim_col = surf.get_at((sx + 7, sy))[:3]
    assert rim_col[0] > 210 and rim_col[1] > 170 and rim_col[2] < 120, f"Parada Nodo 55 tapada por brillo: {rim_col}"


def test_night_path_glow_three_tier_hierarchy_and_dt_flow_beads():
    scene = StoryMapScene(character_id="westcol")
    route = scene._build_campaign_route("uninorte", "ventana")
    assert route is not None
    bbox: pygame.Rect = route["bbox"]
    occluders = scene._get_poi_occluders()

    means = {}
    probes = {}
    for tier in ("active", "completed", "locked"):
        p = pygame.Surface((bbox.width, bbox.height))
        p.fill((0, 0, 0))
        scene.path_glow_renderer.render_night_glow_route(
            p,
            route,
            bbox.x,
            bbox.y,
            timer=0.0,
            unlocked=(tier != "locked"),
            tier=tier,
            intensity=1.0,
        )
        arr = pygame.surfarray.array3d(p)
        means[tier] = float(arr.mean())
        probes[tier] = arr

    assert means["active"] > means["completed"] > means["locked"] > 0.0

    # Avanzar timer con dt debe mover las cuentas luminosas direccionales sin invadir POIs
    p2 = pygame.Surface((bbox.width, bbox.height))
    p2.fill((0, 0, 0))
    scene.path_glow_renderer.render_night_glow_route(
        p2,
        route,
        bbox.x,
        bbox.y,
        timer=0.35,
        unlocked=True,
        tier="active",
        intensity=1.0,
    )
    arr2 = pygame.surfarray.array3d(p2)
    assert int(np.abs(arr2.astype(np.int32) - probes["active"].astype(np.int32)).sum()) > 1000

    for poi_surf, poi_rect in occluders:
        inter = poi_rect.clip(bbox)
        if inter.width <= 0 or inter.height <= 0:
            continue
        px0, py0 = inter.x - poi_rect.x, inter.y - poi_rect.y
        rx0, ry0 = inter.x - bbox.x, inter.y - bbox.y
        poi_a = pygame.surfarray.pixels_alpha(poi_surf)[px0 : px0 + inter.width, py0 : py0 + inter.height]
        under = arr2[rx0 : rx0 + inter.width, ry0 : ry0 + inter.height][poi_a >= 6]
        del poi_a
        assert under.size == 0 or int(under.max()) == 0
