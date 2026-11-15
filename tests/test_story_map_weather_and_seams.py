import os
from pathlib import Path
import numpy as np
import pygame
import pytest

from scenes.story_map.scene import StoryMapScene


@pytest.fixture(autouse=True)
def _headless_pygame():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1920, 1080))
    yield


def test_story_map_seams_paper_shader_and_untouched_clouds():
    StoryMapScene._CACHED_WORLD_MAP = None
    StoryMapScene._CACHED_BASE_WORLD_MAP = None
    scene = StoryMapScene(character_id="westcol")

    assert scene.world_map.get_size() == (3342, 1882)
    assert scene.base_world_map.get_size() == (3342, 1882)
    assert len(scene.clouds) == 15
    assert hasattr(scene, "weather_pill_rect")


def test_story_map_quadrant_assets_dimensions_and_seam_integrity():
    assets_dir = Path("assets")
    for name in ("primer", "segundo", "tercer", "cuarto"):
        surf = pygame.image.load(str(assets_dir / f"{name}_cuadrante_mapa.png"))
        assert surf.get_size() == (1671, 941)

    StoryMapScene._CACHED_WORLD_MAP = None
    StoryMapScene._CACHED_BASE_WORLD_MAP = None
    scene = StoryMapScene(character_id="westcol")

    # base_world_map shape after surfarray -> (W, H, 3) -> transpose to (H, W, 3)
    base = pygame.surfarray.array3d(scene.base_world_map).transpose(1, 0, 2).astype(np.float32)

    # Continuidad real en las costuras X=1671 y Y=941 (sin cortes bruscos ni franjas vacias)
    dx_seam = np.abs(base[:, 1671] - base[:, 1670]).mean(axis=1)
    dy_seam = np.abs(base[941, :] - base[940, :]).mean(axis=1)
    assert float(dx_seam.mean()) < 20.0
    assert float(np.percentile(dx_seam, 95)) < 75.0
    assert float(dy_seam.mean()) < 20.0
    assert float(np.percentile(dy_seam, 95)) < 75.0

    # Nitidez conservada cerca de las costuras (sin desenfoque ancho / halo borroso)
    gx_seam = float(np.abs(np.diff(base[:, 1665:1677], axis=1)).mean())
    gx_away = float(np.abs(np.diff(base[:, 1620:1650], axis=1)).mean())
    gy_seam = float(np.abs(np.diff(base[935:947, :], axis=0)).mean())
    gy_away = float(np.abs(np.diff(base[890:920, :], axis=0)).mean())
    assert gx_seam >= gx_away * 0.75
    assert gy_seam >= gy_away * 0.75


def test_story_map_street_shader_excludes_hidden_edges_and_poi_bases_while_devtool_works():
    StoryMapScene._CACHED_WORLD_MAP = None
    StoryMapScene._CACHED_BASE_WORLD_MAP = None
    scene = StoryMapScene(character_id="westcol")

    hidden_edges = [e for e in scene.dev_tool.edges if e.get("hidden", False)]
    assert len(hidden_edges) > 0

    saved_world_map = scene.world_map
    try:
        # Aislamos exactamente lo que dibuja _render_street_shader sobre un lienzo negro
        probe = pygame.Surface((scene.world_w, scene.world_h))
        probe.fill((0, 0, 0))
        scene.world_map = probe
        scene._render_street_shader()

        arr = pygame.surfarray.array3d(probe)
        world_bounds = pygame.Rect(0, 0, scene.world_w, scene.world_h)

        # Ninguna arista visible o sombra del street_shader debe traslucir bajo monumentos
        for key, asset, dx, dy, dw, _dh, _scol, _soff in scene.POI_SPECS:
            if key not in ("ventana", "malecon", "aleta"):
                continue
            rot_surf, final_rect = scene._prepare_poi_transform(asset, key, dx, dy, dw)
            clip_r = final_rect.clip(world_bounds)
            ox = clip_r.x - final_rect.x
            oy = clip_r.y - final_rect.y
            poi_a = pygame.surfarray.pixels_alpha(rot_surf)[ox : ox + clip_r.width, oy : oy + clip_r.height]
            under_poi = arr[clip_r.x : clip_r.right, clip_r.y : clip_r.bottom][poi_a >= 6]
            del poi_a
            assert int(under_poi.max()) == 0, f"Street shader trasluce bajo monumento {key}"

        # Ninguna arista hidden=True debe renderizarse en el shader normal del mapa
        node_map = {n["id"]: n for n in scene.dev_tool.nodes}
        for edge in hidden_edges:
            p0 = node_map[edge["from"]]
            p1 = node_map[edge["to"]]
            cx = int(round(0.25 * p0["x"] + 0.5 * edge.get("ctrl_x", (p0["x"] + p1["x"]) / 2) + 0.25 * p1["x"]))
            cy = int(round(0.25 * p0["y"] + 0.5 * edge.get("ctrl_y", (p0["y"] + p1["y"]) / 2) + 0.25 * p1["y"]))
            assert tuple(int(c) for c in arr[cx, cy]) == (0, 0, 0)
    finally:
        scene.world_map = saved_world_map

    # DevTool sigue operativo sin errores al activarse y renderizarse
    surface = pygame.Surface((1920, 1080))
    scene.dev_tool.enabled = True
    scene.update(0.016)
    scene.render(surface)
    scene.dev_tool.enabled = False


def test_story_map_weather_cycle_and_render_all_modes():
    scene = StoryMapScene(character_id="westcol")
    surface = pygame.Surface((1920, 1080))

    seen = [scene.current_weather]
    for _ in range(3):
        seen.append(scene.cycle_weather())
    assert set(seen) == {"day", "sunset", "night", "rain"}

    # Click directo en la píldora de clima debe rotar al siguiente clima
    before = scene.current_weather
    ev = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        {"button": 1, "pos": scene.weather_pill_rect.center},
    )
    scene.handle_event(ev)
    assert scene.current_weather != before

    for mode in ("day", "sunset", "night", "rain"):
        scene.set_weather(mode)
        scene.update(0.016)
        scene.render(surface)
