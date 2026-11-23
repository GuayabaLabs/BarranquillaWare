"""
Opaque-box 4-Tier E2E Acceptance Test Suite for SEOR 3-Task Critical Polish (R1-R4).

Tiers:
- Tier 1 (21 tests): Feature coverage across R1 (6), R2 (5), R3 (5), R4 (5).
- Tier 2 (20 tests): Boundary & corner cases across R1 (5), R2 (5), R3 (5), R4 (5).
- Tier 3 (7 tests):  Pairwise cross-feature combinations.
- Tier 4 (6 tests):  Real-world end-to-end gameplay & verification scenarios.

Strictly opaque-box: uses only public constructors, lifecycle methods, events,
public attributes, and 1920x1080 rendered surface / SHA256 assertions.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import numpy as np
import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from core.audio_manager import AudioManager
from core.settings import SettingsManager
from core.state_machine import StateMachine
from microgames.buenavista_trend import (
    BuenavistaTrendMicrogame,
    EN_BARRANQUILLA_BEATMAP_DATA,
    IMITADORA_BEATMAP_DATA,
    MusicalNoteEvent,
)
from scenes.story_map.path_glow import (
    WatercolorRouteRenderer,
    build_route_polyline,
    compute_campaign_dijkstra_path,
)
from scenes.story_map.scene import StoryMapScene
from scenes.story_map_data import (
    PALOMA_STORY_DIALOGS,
    STORY_CAMPAIGN_ORDER,
    STORY_LEVEL_STAGES,
    STORY_PLAYABLE_POIS,
)


# ---------------------------------------------------------------------------
# Baseline SHA256 / Dimension Constants for R4 Protected Files
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

PROTECTED_CONFIG_HASHES: Dict[str, str] = {
    "settings.json": "3D73F11555CAA395797B6DB78AFC64D6641D02C9649C84F408F850AF8640FE76",
    "config/map_poi_layout.json": "CDFD110FCAA733EEC8A41636985F48E4B2099EC9E7DA3D0B03185C5263548281",
}

PROTECTED_AI_PNGS: Dict[str, Tuple[str, int, Tuple[int, int]]] = {
    "assets/spritesheet_teclas_costenas_piano.png": (
        "6B87B95A4DA77D60E5BFC1A9BBEC0E32D0BABA20BE1921528AEA12C173CD32B4",
        839080,
        (1280, 640),
    ),
    "assets/arbolito_navidad_dia.png": (
        "3A70B2A9EAA7B86A1E77D1CA0AF60336A3F8A77A576CE6C18A5D26F5ACE8F55F",
        96905,
        (209, 320),
    ),
    "assets/arbolito_navidad_noche.png": (
        "471AEA6D8D32E9E79508B1011F2FD12E392270EB846512B2B9E7B76B56B134E2",
        98814,
        (210, 320),
    ),
    "assets/alumbrado_poste_dia.png": (
        "5231449D77FADA07BE588F42C9DCB1763D02158538D9F7ABBB3225DECB2DC58E",
        27066,
        (51, 260),
    ),
    "assets/alumbrado_poste_noche.png": (
        "9F58D7519FB8668CC5831AD09E81A9881286ED021A2B9341EC3CA3B01CD29681",
        29812,
        (81, 260),
    ),
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _snapshot_assets_tree() -> List[str]:
    assets_dir = REPO_ROOT / "assets"
    return sorted(
        p.relative_to(REPO_ROOT).as_posix()
        for p in assets_dir.rglob("*")
        if p.is_file()
    )


def _load_layout_graph() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[int, Dict[str, Any]], Dict[Tuple[int, int], Dict[str, Any]]]:
    layout_path = REPO_ROOT / "config" / "map_poi_layout.json"
    data = json.loads(layout_path.read_text(encoding="utf-8"))
    net = data.get("street_network", {})
    nodes = list(net.get("nodes", []))
    edges = list(net.get("edges", []))
    node_map = {n["id"]: n for n in nodes}
    edge_map: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for e in edges:
        if not e.get("hidden", False):
            edge_map[(e["from"], e["to"])] = e
            edge_map[(e["to"], e["from"])] = e
    return nodes, edges, node_map, edge_map


def _build_public_poi_occluders(scene: StoryMapScene) -> List[Tuple[pygame.Surface, pygame.Rect]]:
    """Build POI mask surfaces via public POI_SPECS + poi_registry without calling private helpers."""
    from core.asset_manager import AssetManager

    assets = AssetManager.get_instance()
    occluders: List[Tuple[pygame.Surface, pygame.Rect]] = []
    for spec in scene.POI_SPECS:
        key, asset_name = spec[0], spec[1]
        info = scene.poi_registry.get(key)
        if not info:
            continue
        rect: pygame.Rect = info["rect"]
        try:
            raw = assets.load_surface(asset_name, has_alpha=True)
            scaled = pygame.transform.smoothscale(raw, (rect.width, rect.height))
            occluders.append((scaled, rect))
        except Exception:
            continue
    return occluders


def _advance_intro_to_play(game: BuenavistaTrendMicrogame, dt: float = 1.0 / 60.0) -> None:
    """Step naturally from PHASE_INTRO into PHASE_PLAY so first PLAY update initializes song_elapsed."""
    for _ in range(300):
        if game.phase != game.PHASE_INTRO:
            break
        game.update(dt)
    assert game.phase == game.PHASE_PLAY
    game.update(dt)


def _advance_game_until(game: BuenavistaTrendMicrogame, target_song_elapsed: float, dt: float = 1.0 / 60.0) -> None:
    """Advance naturally in 60 FPS ticks until song_elapsed >= target_song_elapsed."""
    max_steps = int((target_song_elapsed + 5.0) / dt) + 10
    for _ in range(max_steps):
        if game.song_elapsed >= target_song_elapsed or game.is_finished:
            break
        game.update(dt)


def _clamp_cam_for_world_point(scene: StoryMapScene, wx: float, wy: float) -> Tuple[int, int]:
    cam_x = max(0, min(int(scene.camera.max_x), int(round(wx - scene.screen_w / 2.0))))
    cam_y = max(0, min(int(scene.camera.max_y), int(round(wy - scene.screen_h / 2.0))))
    return cam_x, cam_y


def _render_scene_pinned(
    scene: StoryMapScene,
    surface: pygame.Surface,
    world_center: Tuple[float, float],
    dt: float = 0.016,
    clear_toast: bool = True,
) -> Tuple[int, int]:
    """Update scene, pin camera AFTER update (so player follow doesn't drift it), and render 1920x1080."""
    scene.show_intro_dialog = False
    scene.paloma_dialog_open = False
    if clear_toast:
        scene.toast_timer = 0.0
        scene.toast_msg = None
    if hasattr(scene, "cinematic_duration"):
        scene.cinematic_timer = scene.cinematic_duration

    with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
        scene.update(dt)

    cam_x, cam_y = _clamp_cam_for_world_point(scene, world_center[0], world_center[1])
    scene.camera.set_pos(float(cam_x), float(cam_y))
    scene.render(surface)
    return int(scene.camera.x), int(scene.camera.y)


def _pick_route_sample_points(
    scene: StoryMapScene,
    from_poi: str,
    to_poi: str,
    count: int = 3,
) -> List[Tuple[float, float]]:
    """Pick >=3 interior polyline points far from POIs, lamps, tree, and player."""
    nodes, edges, node_map, edge_map = _load_layout_graph()
    n_start = scene.POI_ENTRY_NODES[from_poi]
    n_goal = scene.POI_ENTRY_NODES[to_poi]
    node_path = compute_campaign_dijkstra_path(nodes, edges, n_start, n_goal)
    assert node_path and len(node_path) >= 2
    pts, _cum, _tot = build_route_polyline(node_map, edge_map, node_path, step_px=6)
    assert len(pts) >= 5

    poi_rects = [v["rect"].inflate(24, 24) for v in scene.poi_registry.values()]
    tx, ty = scene.holiday_tree_pos
    decor_pts = [(tx, ty)] + list(scene.street_lamp_positions)

    candidates: List[Tuple[float, float]] = []
    lo = max(2, int(len(pts) * 0.15))
    hi = min(len(pts) - 2, int(len(pts) * 0.85))
    for idx in range(lo, hi):
        wx, wy = pts[idx]
        if any(r.collidepoint(wx, wy) for r in poi_rects):
            continue
        if any(math.hypot(wx - dx, wy - dy) < 85.0 for dx, dy in decor_pts):
            continue
        if math.hypot(wx - scene.player_pos[0], wy - scene.player_pos[1]) < 95.0:
            continue
        candidates.append((wx, wy))

    if not candidates:
        mid = pts[len(pts) // 2]
        return [mid] * count

    if len(candidates) <= count:
        return candidates

    step = (len(candidates) - 1) / float(max(1, count - 1))
    return [candidates[int(round(i * step))] for i in range(count)]


def _surf_rgb(surface: pygame.Surface) -> np.ndarray:
    """Return (W, H, 3) uint8 RGB array view copy."""
    return pygame.surfarray.array3d(surface).copy()


def _patch_rgb(arr: np.ndarray, sx: int, sy: int, radius: int = 4) -> np.ndarray:
    w, h = arr.shape[0], arr.shape[1]
    x0 = max(0, sx - radius)
    x1 = min(w, sx + radius + 1)
    y0 = max(0, sy - radius)
    y1 = min(h, sy + radius + 1)
    return arr[x0:x1, y0:y1].astype(np.float32)


def _luma(patch: np.ndarray) -> float:
    return float(patch.mean(axis=(0, 1)).sum())


def _warmth(patch: np.ndarray) -> float:
    rgb = patch.mean(axis=(0, 1))
    return float(rgb[0] + rgb[1] - 2.0 * rgb[2])


def _place_player_at_poi_entry(scene: StoryMapScene, poi_key: str) -> None:
    """Place player publicly on a POI entry node without calling private navigation helpers."""
    nodes, _edges, node_map, _edge_map = _load_layout_graph()
    nid = scene.POI_ENTRY_NODES[poi_key]
    nd = node_map[nid]
    scene.player_is_moving = False
    scene.player_node_id = nid
    scene.player_pos = (float(nd["x"]), float(nd["y"]))


def _step_outro_to_callback(
    game: BuenavistaTrendMicrogame,
    dt: float = 0.25,
    max_steps: int = 120,
) -> None:
    """Advance OUTRO naturally (and skip via K_SPACE once allowed) until completion."""
    for i in range(max_steps):
        if game.phase != game.PHASE_OUTRO:
            break
        game.update(dt)
        if i == 18:
            game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))


# ---------------------------------------------------------------------------
# Global Isolation & Protected-File Safety Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def _headless_pygame_setup():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1920, 1080), pygame.NOFRAME)
    yield


@pytest.fixture(autouse=True)
def _isolated_protected_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Guarantee zero disk mutation of repo-root settings.json and config/map_poi_layout.json,
    isolate BARRANQUILLAWARE_SETTINGS_FILE to tmp_path, and snapshot/restore SettingsManager.
    """
    settings_path = REPO_ROOT / "settings.json"
    layout_path = REPO_ROOT / "config" / "map_poi_layout.json"
    disk_settings_before = _sha256_file(settings_path)
    disk_layout_before = _sha256_file(layout_path)

    tmp_settings = tmp_path / "settings.json"
    if settings_path.is_file():
        tmp_settings.write_bytes(settings_path.read_bytes())
    else:
        tmp_settings.write_text("{}", encoding="utf-8")

    monkeypatch.setenv("BARRANQUILLAWARE_SETTINGS_FILE", str(tmp_settings))
    import core.settings as settings_mod

    settings_mod.SettingsManager._instance = None
    mgr = SettingsManager.get_instance()
    assert Path(mgr.filepath).resolve() != settings_path.resolve()
    mem_snap = copy.deepcopy(mgr.data)

    audio = AudioManager.get_instance()
    audio.settings = mgr

    try:
        yield mgr
    finally:
        if hasattr(audio, "stop_voice"):
            audio.stop_voice(fade_ms=0)
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        mgr.data = copy.deepcopy(mem_snap)
        mgr.save()
        settings_mod.SettingsManager._instance = None
        assert _sha256_file(settings_path) == disk_settings_before
        assert _sha256_file(layout_path) == disk_layout_before


# ===========================================================================
# TIER 1: FEATURE COVERAGE (21 TESTS — R1: 6, R2: 5, R3: 5, R4: 5)
# ===========================================================================


# --- R1 (6 tests) ---


def test_t1_r1_costeno_spritesheet_slicing_and_visual_scale_balance():
    game = BuenavistaTrendMicrogame(character_id="westcol")
    try:
        assert game.spritesheet_name == "spritesheet_teclas_costenas_piano.png"
        assert len(game.normal_tile_sprites) == 4
        assert len(game.active_tile_sprites) == 4

        min_lane_w = min(r.width for r in game.lane_rects)
        fg_max_dims: List[int] = []
        surf = pygame.Surface((1920, 1080))
        surf.fill((20, 15, 30))

        for idx, (norm_spr, act_spr) in enumerate(
            zip(game.normal_tile_sprites, game.active_tile_sprites)
        ):
            na = pygame.surfarray.array_alpha(norm_spr)
            aa = pygame.surfarray.array_alpha(act_spr)
            assert int(na.max()) >= 200
            assert int(aa.max()) >= 200
            assert norm_spr.get_width() < min_lane_w
            assert act_spr.get_width() < min_lane_w

            bb = norm_spr.get_bounding_rect(min_alpha=20)
            assert bb.width > 0 and bb.height > 0
            fg_max_dims.append(max(bb.width, bb.height))
            surf.blit(norm_spr, (100 + idx * 160, 100))

        # Scale balance across all 4 coastal icons (Raspado, Sombrero, Marimonda, Tambor)
        ratio = max(fg_max_dims) / float(max(1, min(fg_max_dims)))
        assert ratio <= 1.25, f"Coastal icons scale imbalance: {fg_max_dims} (ratio={ratio:.3f})"
        assert min(fg_max_dims) >= 0.45 * game.tile_size

        # Raw 4x2 grid cells from disk must also be balanced vs 320px cell
        sheet = pygame.image.load(
            str(REPO_ROOT / "assets" / "spritesheet_teclas_costenas_piano.png")
        ).convert_alpha()
        sw, sh = sheet.get_size()
        cw, ch = sw // 4, sh // 2
        raw_dims = []
        for c in range(4):
            cell = sheet.subsurface((c * cw, 0, cw, ch))
            cbb = cell.get_bounding_rect(min_alpha=20)
            raw_dims.append(max(cbb.width, cbb.height))
        assert max(raw_dims) / float(min(raw_dims)) <= 1.25
        assert min(raw_dims) >= 0.45 * cw
    finally:
        game.cleanup()


def test_t1_r1_audio_track_contract_and_sfx_hooks():
    game = BuenavistaTrendMicrogame(character_id="westcol")
    try:
        assert game.music_track_name == "en_barranquilla_me_quedo_piano.ogg"
        _advance_intro_to_play(game)

        ev0 = game.musical_events[0]
        _advance_game_until(game, ev0.impact_time)
        assert ev0.state == "falling"

        hit_key = game.LANE_KEYS[ev0.lane]
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": hit_key}))
        game.handle_event(pygame.event.Event(pygame.KEYUP, {"key": hit_key}))
        assert game.hits_perfect == 1
        assert game.lives == 5

        # Advance 0.30s so cooldown clears, then press wrong lane far from any note
        _advance_game_until(game, game.song_elapsed + 0.30)
        wrong_lane = (ev0.lane + 1) % 4
        # Ensure no note in wrong_lane is currently within 0.5s of impact
        if any(
            ev.lane == wrong_lane and ev.state == "falling" and abs(ev.impact_time - game.song_elapsed) < 0.50
            for ev in game.musical_events
        ):
            wrong_lane = (ev0.lane + 3) % 4
        wrong_key = game.LANE_KEYS[wrong_lane]
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": wrong_key}))
        game.handle_event(pygame.event.Event(pygame.KEYUP, {"key": wrong_key}))
        assert game.misses_count == 1
        assert game.lives == 4
    finally:
        game.cleanup()


def test_t1_r1_paloma_buenavista_dialogs_all_phases():
    cfg = PALOMA_STORY_DIALOGS["buenavista"]
    for key in ("pre_pages", "post_win_pages", "post_lose_pages"):
        assert cfg.get(key) and len(cfg[key]) >= 1

    pre_text = " ".join(" ".join(p) for p in cfg["pre_pages"]).lower()
    win_text = " ".join(" ".join(p) for p in cfg["post_win_pages"]).lower()
    lose_text = " ".join(" ".join(p) for p in cfg["post_lose_pages"]).lower()

    assert "en barranquilla me quedo" in pre_text
    assert ("raspado" in pre_text) or ("salsa" in pre_text)
    for k_lbl in ("d", "f", "j", "k"):
        assert k_lbl in pre_text

    scene = StoryMapScene(character_id="westcol")
    poi_desc = " ".join(scene.poi_registry["buenavista"]["desc"]).lower()

    for txt in (pre_text, win_text, lose_text, poi_desc):
        assert "imitadora" not in txt
        assert "bachata" not in txt


def test_t1_r1_beatmap_114bpm_salsa_timing_and_lane_sprite_validity():
    assert EN_BARRANQUILLA_BEATMAP_DATA is IMITADORA_BEATMAP_DATA
    game = BuenavistaTrendMicrogame(character_id="westcol")
    try:
        events = game.musical_events
        assert len(events) >= 35
        assert len(events) == len(EN_BARRANQUILLA_BEATMAP_DATA)

        for i, ev in enumerate(events):
            assert isinstance(ev, MusicalNoteEvent)
            assert 0.0 <= ev.spawn_time < ev.impact_time < game.time_limit
            if i > 0:
                assert ev.impact_time > events[i - 1].impact_time

        assert {e.lane for e in events} == {0, 1, 2, 3}
        assert {e.sprite_type for e in events} == {0, 1, 2, 3}

        p1 = [e for e in events if e.impact_time < 10.0]
        p2 = [e for e in events if 10.0 <= e.impact_time < 20.0]
        p3 = [e for e in events if e.impact_time >= 20.0]
        assert len(p1) > 0 and len(p2) > len(p1) and len(p3) >= len(p2)

        avg1 = sum(e.fall_speed for e in p1) / len(p1)
        avg2 = sum(e.fall_speed for e in p2) / len(p2)
        avg3 = sum(e.fall_speed for e in p3) / len(p3)
        assert avg1 < avg2 < avg3

        for i in range(1, len(p1)):
            assert p1[i].impact_time - p1[i - 1].impact_time >= 0.45
        for phase_events in (p2, p3):
            for i in range(1, len(phase_events)):
                assert phase_events[i].impact_time - phase_events[i - 1].impact_time >= 0.12
    finally:
        game.cleanup()


def test_t1_r1_dt_animations_particles_and_cozy_hud_pixel_updates():
    game = BuenavistaTrendMicrogame(character_id="westcol")
    try:
        _advance_intro_to_play(game)
        ev0 = game.musical_events[0]
        _advance_game_until(game, ev0.impact_time)

        surf_before = pygame.Surface((1920, 1080))
        game.render(surf_before)

        hit_key = game.LANE_KEYS[ev0.lane]
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": hit_key}))
        game.handle_event(pygame.event.Event(pygame.KEYUP, {"key": hit_key}))
        for _ in range(3):
            game.update(0.016)
        assert game.hits_perfect == 1

        surf_hit = pygame.Surface((1920, 1080))
        game.render(surf_hit)

        arr_b = _surf_rgb(surf_before)
        arr_h = _surf_rgb(surf_hit)
        lane_r = game.lane_rects[ev0.lane]
        lane_zone = (slice(max(0, lane_r.left - 30), min(1920, lane_r.right + 30)),
                     slice(max(0, game.hit_line_y - 160), min(1080, game.hit_line_y + 80)))
        diff_lane = np.abs(arr_h[lane_zone].astype(np.int16) - arr_b[lane_zone].astype(np.int16)).max(axis=2)
        assert int(np.count_nonzero(diff_lane > 15)) > 500

        # Trigger a miss via wrong lane press
        _advance_game_until(game, game.song_elapsed + 0.30)
        wrong_lane = (ev0.lane + 1) % 4
        if any(
            ev.lane == wrong_lane and ev.state == "falling" and abs(ev.impact_time - game.song_elapsed) < 0.50
            for ev in game.musical_events
        ):
            wrong_lane = (ev0.lane + 3) % 4
        wk = game.LANE_KEYS[wrong_lane]
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": wk}))
        game.handle_event(pygame.event.Event(pygame.KEYUP, {"key": wk}))
        game.update(0.016)
        assert game.lives == 4

        surf_miss = pygame.Surface((1920, 1080))
        game.render(surf_miss)
        arr_m = _surf_rgb(surf_miss)
        hearts_diff = np.abs(
            arr_m[20:420, 15:130].astype(np.int16) - arr_h[20:420, 15:130].astype(np.int16)
        ).max(axis=2)
        assert int(np.count_nonzero(hearts_diff > 15)) > 100
    finally:
        game.cleanup()


def test_t1_r1_all_phases_render_within_1920x1080_viewport():
    game = BuenavistaTrendMicrogame(character_id="westcol")
    try:
        viewport = pygame.Rect(0, 0, 1920, 1080)
        assert viewport.contains(game.phone_rect)
        assert game.phone_rect.contains(game.playable_clip_rect)

        s_intro = pygame.Surface((1920, 1080))
        game.update(0.5)
        assert game.phase == game.PHASE_INTRO
        game.render(s_intro)

        _advance_intro_to_play(game)
        _advance_game_until(game, 2.65)
        s_play = pygame.Surface((1920, 1080))
        game.render(s_play)

        game.finish_game(True)
        game.update(0.5)
        assert game.phase == game.PHASE_OUTRO
        s_outro = pygame.Surface((1920, 1080))
        game.render(s_outro)

        for name, s in (("intro", s_intro), ("play", s_play), ("outro", s_outro)):
            arr = _surf_rgb(s)
            assert float(arr.std()) > 10.0, f"Blank render in phase {name}"
    finally:
        game.cleanup()


# --- R2 (5 tests) ---


def test_t1_r2_night_renders_glow_on_all_campaign_segments():
    scene = StoryMapScene(character_id="westcol")
    scene.set_weather("night")
    surf_night = pygame.Surface((1920, 1080))

    for src, dst in zip(STORY_CAMPAIGN_ORDER, STORY_CAMPAIGN_ORDER[1:]):
        samples = _pick_route_sample_points(scene, src, dst, count=3)
        bright_hits = 0
        for wx, wy in samples:
            cam_x, cam_y = _render_scene_pinned(scene, surf_night, (wx, wy))
            arr = _surf_rgb(surf_night)
            sx, sy = int(round(wx - cam_x)), int(round(wy - cam_y))
            route_patch = _patch_rgb(arr, sx, sy, radius=3)
            # Sample nearby dark off-road terrain (offset diagonally away from road)
            off_patches = []
            for ox, oy in ((32, 32), (-32, -32), (32, -32), (-32, 32)):
                ox_s = max(10, min(1909, sx + ox))
                oy_s = max(120, min(1060, sy + oy))
                off_patches.append(_patch_rgb(arr, ox_s, oy_s, radius=3))
            off_luma = min(_luma(p) for p in off_patches)
            r_mean, _g_mean, b_mean = route_patch.mean(axis=(0, 1))
            if _luma(route_patch) > off_luma + 12.0 and r_mean >= b_mean - 5.0:
                bright_hits += 1
        assert bright_hits >= 1, f"Night glow missing on segment {src} -> {dst}"


def test_t1_r2_day_sunset_rain_suppress_nocturnal_path_glow():
    mgr = SettingsManager.get_instance()
    mgr.update_story_progress(
        completed_microgames=["uninorte_sprint", "uninorte_concentrate"]
    )
    scene = StoryMapScene(character_id="westcol")
    samples = _pick_route_sample_points(scene, "uninorte", "ventana", count=3)
    anchor = samples[len(samples) // 2]

    mode_route_lumas: Dict[str, float] = {}
    mode_luma_lifts: Dict[str, float] = {}
    for mode in ("day", "sunset", "rain", "night"):
        scene.set_weather(mode)
        surf = pygame.Surface((1920, 1080))
        cam_x, cam_y = _render_scene_pinned(scene, surf, anchor)
        arr = _surf_rgb(surf)
        best_luma = -1.0
        best_lift = -999.0
        for wx, wy in samples:
            sx, sy = int(round(wx - cam_x)), int(round(wy - cam_y))
            if not (40 <= sx < 1880 and 110 <= sy < 1040):
                continue
            r_patch = _patch_rgb(arr, sx, sy, radius=3)
            r_luma = _luma(r_patch)
            off_luma = min(
                _luma(_patch_rgb(arr, sx + ox, sy + oy, radius=3))
                for ox, oy in ((34, 34), (-34, -34))
            )
            best_luma = max(best_luma, r_luma)
            best_lift = max(best_lift, r_luma - off_luma)
        mode_route_lumas[mode] = best_luma
        mode_luma_lifts[mode] = best_lift

    assert mode_luma_lifts["night"] > 50.0
    for non_night in ("day", "sunset", "rain"):
        assert mode_route_lumas["night"] > mode_route_lumas[non_night] + 40.0
        assert mode_luma_lifts["night"] > mode_luma_lifts[non_night] + 50.0


def test_t1_r2_night_path_glow_dt_animation_smoothness():
    scene = StoryMapScene(character_id="westcol")
    scene.set_weather("night")
    samples = _pick_route_sample_points(scene, "uninorte", "ventana", count=3)
    anchor = samples[len(samples) // 2]

    s0 = pygame.Surface((1920, 1080))
    cam_x, cam_y = _render_scene_pinned(scene, s0, anchor, dt=0.016)
    a0 = _surf_rgb(s0)

    # Single-frame dt step should remain bounded (no strobe jump)
    s_step = pygame.Surface((1920, 1080))
    _render_scene_pinned(scene, s_step, anchor, dt=0.016)
    a_step = _surf_rgb(s_step)

    for _ in range(20):
        with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
            scene.update(0.04)
    s1 = pygame.Surface((1920, 1080))
    _render_scene_pinned(scene, s1, anchor, dt=0.016)
    a1 = _surf_rgb(s1)

    step_diffs = []
    long_diffs = []
    for wx, wy in samples:
        sx, sy = int(round(wx - cam_x)), int(round(wy - cam_y))
        if 20 <= sx < 1900 and 110 <= sy < 1060:
            p0 = _patch_rgb(a0, sx, sy, radius=8)
            ps = _patch_rgb(a_step, sx, sy, radius=8)
            p1 = _patch_rgb(a1, sx, sy, radius=8)
            step_diffs.append(float(np.abs(ps - p0).mean()))
            long_diffs.append(float(np.abs(p1 - p0).max()))

    assert step_diffs and min(step_diffs) <= 25.0
    assert max(long_diffs) >= 2.0


def test_t1_r2_night_path_respects_poi_building_occlusion():
    scene = StoryMapScene(character_id="westcol")
    nodes, edges, node_map, edge_map = _load_layout_graph()
    occluders = _build_public_poi_occluders(scene)
    assert len(occluders) >= 6

    renderer = scene.path_glow_renderer
    for src, dst in zip(STORY_CAMPAIGN_ORDER, STORY_CAMPAIGN_ORDER[1:]):
        n_path = compute_campaign_dijkstra_path(
            nodes, edges, scene.POI_ENTRY_NODES[src], scene.POI_ENTRY_NODES[dst]
        )
        assert n_path and len(n_path) >= 2
        route_data = renderer.get_or_build_route(
            src, dst, n_path, node_map, edge_map, poi_occluders=occluders
        )
        assert route_data is not None

        # Render night glow onto black canvas and check zero pixel leakage onto opaque POI pixels
        bbox: pygame.Rect = route_data["bbox"]
        canvas = pygame.Surface((scene.world_w, scene.world_h))
        canvas.fill((0, 0, 0))
        renderer.render_night_glow_route(canvas, route_data, 0, 0, timer=0.4, unlocked=True)
        canvas_rgb = pygame.surfarray.array3d(canvas)

        for poi_surf, poi_rect in occluders:
            inter = poi_rect.clip(bbox)
            if inter.width <= 0 or inter.height <= 0:
                continue
            poi_a = pygame.surfarray.array_alpha(poi_surf)[
                inter.x - poi_rect.x : inter.x - poi_rect.x + inter.width,
                inter.y - poi_rect.y : inter.y - poi_rect.y + inter.height,
            ]
            sub_rgb = canvas_rgb[
                inter.x : inter.x + inter.width,
                inter.y : inter.y + inter.height,
            ]
            leaked = sub_rgb[poi_a >= 20]
            assert leaked.size == 0 or int(leaked.max()) == 0, f"Glow leaked onto POI in {src}->{dst}"

    # Full scene render on Buenavista in night stays non-blank and crisp
    scene.set_weather("night")
    b_rect = scene.poi_registry["buenavista"]["rect"]
    surf = pygame.Surface((1920, 1080))
    _render_scene_pinned(scene, surf, b_rect.center)
    assert float(_surf_rgb(surf).std()) > 10.0


def test_t1_r2_weather_transition_set_instant_and_cycle_dt_convergence():
    scene = StoryMapScene(character_id="westcol")
    anchor = (1600.0, 900.0)

    s_day = pygame.Surface((1920, 1080))
    scene.set_weather("day")
    _render_scene_pinned(scene, s_day, anchor, dt=0.016)

    s_night = pygame.Surface((1920, 1080))
    scene.set_weather("night")
    _render_scene_pinned(scene, s_night, anchor, dt=0.016)

    day_luma = float(_surf_rgb(s_day).mean())
    night_luma = float(_surf_rgb(s_night).mean())
    assert day_luma - night_luma > 25.0

    # Cycle across all 4 weather modes via weather_pill_rect clicks + dt convergence
    scene.set_weather("day")
    visited = [scene.current_weather]
    for _ in range(4):
        scene.handle_event(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {"button": 1, "pos": scene.weather_pill_rect.center},
            )
        )
        visited.append(scene.current_weather)
        for _ in range(30):
            with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
                scene.update(0.05)
        tmp_surf = pygame.Surface((1920, 1080))
        _render_scene_pinned(scene, tmp_surf, anchor, dt=0.016)
        assert float(_surf_rgb(tmp_surf).std()) > 8.0

    assert set(visited) == {"day", "sunset", "night", "rain"}
    assert scene.current_weather == "day"


# --- R3 (5 tests) ---


def test_t1_r3_day_decor_unlit_and_night_decor_multicolor_lights():
    scene = StoryMapScene(character_id="westcol")
    scene.player_pos = (100.0, 100.0)  # Keep player halo away from tree & lamps
    tx, ty = scene.holiday_tree_pos
    tw, th = scene.holiday_tree_day.get_size()

    s_day = pygame.Surface((1920, 1080))
    scene.set_weather("day")
    cam_x, cam_y = _render_scene_pinned(scene, s_day, (tx, ty - th * 0.5))

    s_night = pygame.Surface((1920, 1080))
    scene.set_weather("night")
    _render_scene_pinned(scene, s_night, (tx, ty - th * 0.5))

    day_arr = _surf_rgb(s_day).astype(np.int16)
    night_arr = _surf_rgb(s_night).astype(np.int16)

    sx, sy = tx - cam_x, ty - cam_y
    x0 = max(0, sx - tw // 2 - 20)
    x1 = min(1920, sx + tw // 2 + 20)
    y0 = max(0, sy - th - 20)
    y1 = min(1080, sy + 20)

    d_box = day_arr[x0:x1, y0:y1]
    n_box = night_arr[x0:x1, y0:y1]
    diff = n_box - d_box
    lit_mask = (diff[:, :, 0] >= 15) | (diff[:, :, 1] >= 15) | (diff[:, :, 2] >= 15)
    assert int(np.count_nonzero(lit_mask)) > 100

    # Check multiple chromatic hue families among lit night pixels
    nr, ng, nb = n_box[:, :, 0], n_box[:, :, 1], n_box[:, :, 2]
    warm_gold_red = int(np.count_nonzero(lit_mask & (nr > nb + 25)))
    cyan_blue = int(np.count_nonzero(lit_mask & (nb > nr + 15)))
    green_px = int(np.count_nonzero(lit_mask & (ng > nr + 10) & (ng > nb + 10)))
    magenta_px = int(np.count_nonzero(lit_mask & (nr > ng + 15) & (nb > ng + 15)))
    families_lit = sum(1 for c in (warm_gold_red, cyan_blue, green_px, magenta_px) if c > 20)
    assert families_lit >= 2, (
        f"Expected multicolor lights on night tree, counts: warm={warm_gold_red}, "
        f"cyan={cyan_blue}, green={green_px}, magenta={magenta_px}"
    )

    # Check 2 street lamps: night top region lights up brightly over night terrain
    lw, lh = scene.street_lamp_day.get_size()
    for lx, ly in scene.street_lamp_positions[:2]:
        ls_day = pygame.Surface((1920, 1080))
        scene.set_weather("day")
        lcx, lcy = _render_scene_pinned(scene, ls_day, (lx, ly - lh // 2))
        ls_night = pygame.Surface((1920, 1080))
        scene.set_weather("night")
        _render_scene_pinned(scene, ls_night, (lx, ly - lh // 2))

        la_day = _surf_rgb(ls_day).astype(np.int16)
        la_night = _surf_rgb(ls_night).astype(np.int16)
        lsx, lsy = lx - lcx, ly - lcy
        bx0 = max(0, lsx - lw // 2 - 20)
        bx1 = min(1920, lsx + lw // 2 + 20)
        by0 = max(0, lsy - lh - 20)
        by1 = min(1080, lsy + 10)
        lamp_lit = (la_night[bx0:bx1, by0:by1].sum(axis=2) - la_day[bx0:bx1, by0:by1].sum(axis=2)) > 30
        assert int(np.count_nonzero(lamp_lit)) > 50


def test_t1_r3_holiday_decor_full_bbox_clearance_and_world_bounds():
    scene = StoryMapScene(character_id="westcol")
    world_rect = pygame.Rect(0, 0, scene.world_w, scene.world_h)
    poi_rects = {k: v["rect"] for k, v in scene.poi_registry.items()}

    tree_rects = [
        scene.holiday_tree_day.get_rect(midbottom=scene.holiday_tree_pos),
        scene.holiday_tree_night.get_rect(midbottom=scene.holiday_tree_pos),
    ]
    for tr in tree_rects:
        assert world_rect.contains(tr)
        for p_key, p_rect in poi_rects.items():
            assert not tr.colliderect(p_rect), f"Holiday tree overlaps POI {p_key}"

    assert len(scene.street_lamp_positions) >= 4
    for pos in scene.street_lamp_positions:
        for spr in (scene.street_lamp_day, scene.street_lamp_night):
            lr = spr.get_rect(midbottom=pos)
            assert world_rect.contains(lr)
            for p_key, p_rect in poi_rects.items():
                assert not lr.colliderect(p_rect), f"Street lamp {pos} overlaps POI {p_key}"


def test_t1_r3_holiday_decor_diorama_scale_aspect_and_ground_shadow():
    scene = StoryMapScene(character_id="westcol")
    raw_tree = pygame.image.load(str(REPO_ROOT / "assets" / "arbolito_navidad_dia.png"))
    raw_lamp = pygame.image.load(str(REPO_ROOT / "assets" / "alumbrado_poste_dia.png"))

    tw, th = scene.holiday_tree_day.get_size()
    lw, lh = scene.street_lamp_day.get_size()
    raw_tw, raw_th = raw_tree.get_size()
    raw_lw, raw_lh = raw_lamp.get_size()

    tree_aspect = tw / float(th)
    raw_tree_aspect = raw_tw / float(raw_th)
    lamp_aspect = lw / float(lh)
    raw_lamp_aspect = raw_lw / float(raw_lh)

    assert abs(tree_aspect - raw_tree_aspect) / raw_tree_aspect <= 0.03
    assert abs(lamp_aspect - raw_lamp_aspect) / raw_lamp_aspect <= 0.03
    assert 80 <= th <= 220
    assert 50 <= lh <= 140
    assert th > lh

    # Verify subtle grounded shadow just below tree base vs adjacent terrain in day
    scene.player_pos = (100.0, 100.0)
    scene.set_weather("day")
    tx, ty = scene.holiday_tree_pos
    surf = pygame.Surface((1920, 1080))
    cam_x, cam_y = _render_scene_pinned(scene, surf, (tx, ty))
    arr = _surf_rgb(surf)
    sx, sy = tx - cam_x, ty - cam_y

    # Measure minimum luma right around pot/base contact shadow vs clear terrain 140px away
    base_band = arr[max(0, sx - 25):min(1920, sx + 25), max(0, sy - 2):min(1080, sy + 10)]
    clear_band = arr[max(0, sx - 160):min(1920, sx - 110), max(0, sy + 40):min(1080, sy + 80)]
    assert float(base_band.sum(axis=2).mean()) < float(clear_band.sum(axis=2).mean())


def test_t1_r3_no_punch_tree_asset_referenced_in_story_map():
    story_files = list((REPO_ROOT / "scenes" / "story_map").rglob("*.py")) + [
        REPO_ROOT / "scenes" / "story_map_data.py"
    ]
    assert len(story_files) >= 2
    for py_file in story_files:
        content = py_file.read_text(encoding="utf-8")
        assert "Punch/arbolito" not in content
        assert "Punch\\arbolito" not in content
        assert "assets/Punch" not in content

    scene = StoryMapScene(character_id="westcol")
    raw_tree_day = pygame.image.load(str(REPO_ROOT / "assets" / "arbolito_navidad_dia.png"))
    raw_tree_night = pygame.image.load(str(REPO_ROOT / "assets" / "arbolito_navidad_noche.png"))
    assert abs(
        (scene.holiday_tree_day.get_width() / scene.holiday_tree_day.get_height())
        - (raw_tree_day.get_width() / raw_tree_day.get_height())
    ) <= 0.03
    assert abs(
        (scene.holiday_tree_night.get_width() / scene.holiday_tree_night.get_height())
        - (raw_tree_night.get_width() / raw_tree_night.get_height())
    ) <= 0.03


def test_t1_r3_night_decor_dt_twinkle_and_cloud_layer_order():
    scene = StoryMapScene(character_id="westcol")
    scene.player_pos = (100.0, 100.0)
    scene.set_weather("night")
    tx, ty = scene.holiday_tree_pos
    tw, th = scene.holiday_tree_night.get_size()

    surf_a = pygame.Surface((1920, 1080))
    cam_x, cam_y = _render_scene_pinned(scene, surf_a, (tx, ty - th * 0.5), dt=0.016)
    arr_a = _surf_rgb(surf_a)

    for _ in range(3):
        with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
            scene.update(0.35)
    surf_b = pygame.Surface((1920, 1080))
    _render_scene_pinned(scene, surf_b, (tx, ty - th * 0.5), dt=0.016)
    arr_b = _surf_rgb(surf_b)

    sx, sy = tx - cam_x, ty - cam_y
    box_a = arr_a[max(0, sx - tw // 2 - 20):min(1920, sx + tw // 2 + 20),
                  max(0, sy - th - 20):min(1080, sy + 20)]
    box_b = arr_b[max(0, sx - tw // 2 - 20):min(1920, sx + tw // 2 + 20),
                  max(0, sy - th - 20):min(1080, sy + 20)]
    max_twinkle_diff = int(np.abs(box_b.astype(np.int16) - box_a.astype(np.int16)).max())
    assert max_twinkle_diff >= 1, "Expected dt-modulated twinkle/animation on night tree or scene"
    assert float(arr_a.std()) > 10.0 and float(arr_b.std()) > 10.0


# --- R4 (5 tests) ---


def test_t1_r4_protected_config_files_sha256_intact():
    for rel, expected_hash in PROTECTED_CONFIG_HASHES.items():
        fpath = REPO_ROOT / rel
        assert fpath.is_file(), f"Missing protected config file: {rel}"
        assert _sha256_file(fpath) == expected_hash
        parsed = json.loads(fpath.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict)


def test_t1_r4_five_ai_png_assets_exact_sha256_and_dimensions():
    for rel, (expected_hash, expected_bytes, expected_dims) in PROTECTED_AI_PNGS.items():
        fpath = REPO_ROOT / rel
        assert fpath.is_file(), f"Missing protected AI PNG: {rel}"
        raw = fpath.read_bytes()
        assert len(raw) == expected_bytes
        assert hashlib.sha256(raw).hexdigest().upper() == expected_hash
        surf = pygame.image.load(str(fpath))
        assert surf.get_size() == expected_dims


def test_t1_r4_no_code_generated_visual_assets_created():
    before = _snapshot_assets_tree()
    game = BuenavistaTrendMicrogame(character_id="westcol")
    _advance_intro_to_play(game)
    surf = pygame.Surface((1920, 1080))
    game.render(surf)
    game.cleanup()

    scene = StoryMapScene(character_id="westcol")
    scene.set_weather("night")
    _render_scene_pinned(scene, surf, scene.holiday_tree_pos)
    after = _snapshot_assets_tree()
    assert after == before


def test_t1_r4_git_scope_restricted_to_seor_tasks():
    if not (REPO_ROOT / ".git").exists():
        pytest.skip(".git directory not present")

    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    allowed_prefixes = (
        "microgames/buenavista_trend/",
        "microgames/heladero_metro.py",
        "scenes/story_map/",
        "scenes/story_map_data.py",
        "core/asset_manager.py",
        "assets/Estadio/",
        "assets/Fritanga/",
        "assets/puntito.png",
        "assets/cancion_triste_heladero.ogg",
        "assets/boton_voz_",
        "scratch/",
        "tests/",
        "artifacts/",
    )
    allowed_exact = set(PROTECTED_AI_PNGS.keys())
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        raw_path = line[3:].strip()
        if " -> " in raw_path:
            raw_path = raw_path.split(" -> ", 1)[1].strip()
        path_norm = raw_path.strip('"').replace("\\", "/")
        assert path_norm.startswith(allowed_prefixes) or path_norm in allowed_exact, (
            f"Out-of-scope modification in git status: {path_norm}"
        )


def test_t1_r4_headless_run_leaves_repo_root_settings_untouched():
    root_settings = REPO_ROOT / "settings.json"
    before = _sha256_file(root_settings)

    scene = StoryMapScene(character_id="westcol")
    scene.set_weather("night")
    scene.save_current_state(source="test")
    surf = pygame.Surface((1920, 1080))
    _render_scene_pinned(scene, surf, scene.holiday_tree_pos)

    game = BuenavistaTrendMicrogame(character_id="westcol")
    _advance_intro_to_play(game)
    game.render(surf)
    game.cleanup()

    assert _sha256_file(root_settings) == before


# ===========================================================================
# TIER 2: BOUNDARY & CORNER CASES (20 TESTS — R1: 5, R2: 5, R3: 5, R4: 5)
# ===========================================================================


# --- R1 Boundaries (5 tests) ---


def test_t2_r1_missing_ogg_and_mp3_audio_safe_dt_clock():
    orig_exists = os.path.exists

    def fake_exists(p: str) -> bool:
        norm = str(p).replace("\\", "/")
        if "en_barranquilla_me_quedo_piano." in norm:
            return False
        return orig_exists(p)

    with patch("os.path.exists", side_effect=fake_exists):
        game = BuenavistaTrendMicrogame(character_id="westcol")
        try:
            _advance_intro_to_play(game)
            start_elapsed = game.song_elapsed
            start_left = game.time_left
            surf = pygame.Surface((1920, 1080))
            for _ in range(60):
                game.update(1.0 / 60.0)
            game.render(surf)

            delta_elapsed = game.song_elapsed - start_elapsed
            delta_left = start_left - game.time_left
            assert 0.95 <= delta_elapsed <= 1.05
            assert 0.95 <= delta_left <= 1.05
        finally:
            game.cleanup()


def test_t2_r1_mp3_fallback_preferred_when_ogg_absent():
    orig_exists = os.path.exists
    loaded_paths: List[str] = []

    def fake_exists(p: str) -> bool:
        norm = str(p).replace("\\", "/")
        if norm.endswith("en_barranquilla_me_quedo_piano.ogg"):
            return False
        if norm.endswith("en_barranquilla_me_quedo_piano.mp3"):
            return True
        return orig_exists(p)

    game = BuenavistaTrendMicrogame(character_id="westcol")
    try:
        with patch("os.path.exists", side_effect=fake_exists), patch(
            "pygame.mixer.get_init", return_value=(44100, -16, 2)
        ), patch(
            "pygame.mixer.music.load", side_effect=lambda p: loaded_paths.append(str(p))
        ), patch("pygame.mixer.music.play"):
            _advance_intro_to_play(game)

        assert any(p.replace("\\", "/").endswith("assets/en_barranquilla_me_quedo_piano.mp3") for p in loaded_paths)
    finally:
        game.cleanup()


def test_t2_r1_zero_and_large_dt_stability():
    game = BuenavistaTrendMicrogame(character_id="westcol")
    try:
        _advance_intro_to_play(game)
        t_el = game.song_elapsed
        t_left = game.time_left
        for _ in range(5):
            game.update(0.0)
        assert game.song_elapsed == pytest.approx(t_el)
        assert game.time_left == pytest.approx(t_left)

        game.update(0.5)
        surf = pygame.Surface((1920, 1080))
        game.render(surf)
        assert all(math.isfinite(ev.y) for ev in game.musical_events)
        assert 0 <= game.lives <= 5
    finally:
        game.cleanup()


def test_t2_r1_note_at_hit_line_non_occlusion_of_key_badge_pixels():
    game = BuenavistaTrendMicrogame(character_id="westcol")
    try:
        _advance_intro_to_play(game)
        surf_idle = pygame.Surface((1920, 1080))
        game.render(surf_idle)

        ev0 = game.musical_events[0]
        _advance_game_until(game, ev0.impact_time)
        assert ev0.state == "falling"

        surf_at_hit = pygame.Surface((1920, 1080))
        game.render(surf_at_hit)

        arr_idle = _surf_rgb(surf_idle).astype(np.int16)
        arr_hit = _surf_rgb(surf_at_hit).astype(np.int16)

        cx0 = game.lane_centers_x[ev0.lane]
        hy = game.hit_line_y
        # 1. Falling note MUST be visibly drawn at the hit line
        receptor_diff = np.abs(
            arr_hit[cx0 - 35 : cx0 + 35, hy - 35 : hy + 35]
            - arr_idle[cx0 - 35 : cx0 + 35, hy - 35 : hy + 35]
        )
        assert int(np.count_nonzero(receptor_diff.max(axis=2) > 20)) > 200

        # 2. Key badge region separated below receptor / playable_clip_rect must NOT be occluded by the falling note
        badge_top = max(game.playable_clip_rect.bottom + 2, hy + (game.tile_size // 2) + 6)
        badge_bot = game.phone_rect.bottom - 10
        assert badge_bot > badge_top + 10
        badge_diff = np.abs(
            arr_hit[cx0 - 28 : cx0 + 28, badge_top:badge_bot]
            - arr_idle[cx0 - 28 : cx0 + 28, badge_top:badge_bot]
        )
        unchanged_ratio = float(np.mean(badge_diff.max(axis=2) <= 5))
        assert unchanged_ratio >= 0.95, (
            f"Falling note occluded key badge band below receptor (unchanged={unchanged_ratio:.2%})"
        )

        # Confirm the key dock badge is actually rendered in that band by checking KEYDOWN press highlight
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": game.LANE_KEYS[ev0.lane]}))
        surf_pressed = pygame.Surface((1920, 1080))
        game.render(surf_pressed)
        arr_press = _surf_rgb(surf_pressed).astype(np.int16)
        press_diff = np.abs(
            arr_press[cx0 - 28 : cx0 + 28, badge_top:badge_bot]
            - arr_hit[cx0 - 28 : cx0 + 28, badge_top:badge_bot]
        )
        assert int(np.count_nonzero(press_diff.max(axis=2) > 10)) > 20
    finally:
        game.cleanup()


def test_t2_r1_spritesheet_cell_borders_clean_and_key_hold_edge_rejection():
    game = BuenavistaTrendMicrogame(character_id="westcol")
    try:
        # Check raw 4x2 spritesheet cells on disk for clean transparent 1px perimeter
        sheet = pygame.image.load(
            str(REPO_ROOT / "assets" / "spritesheet_teclas_costenas_piano.png")
        ).convert_alpha()
        sw, sh = sheet.get_size()
        cw, ch = sw // 4, sh // 2
        for r in range(2):
            for c in range(4):
                cell = sheet.subsurface((c * cw, r * ch, cw, ch))
                alpha = pygame.surfarray.array_alpha(cell)
                border_max = max(
                    int(alpha[0, :].max()),
                    int(alpha[-1, :].max()),
                    int(alpha[:, 0].max()),
                    int(alpha[:, -1].max()),
                )
                assert border_max <= 10, f"Cell ({r},{c}) border bleed max_alpha={border_max}"

        # Also check raw_grid_cells dimensions & non-empty content
        assert len(game.raw_grid_cells) == 2 and len(game.raw_grid_cells[0]) == 4

        # Anti-hold & repeat=1 rejection
        _advance_intro_to_play(game)
        ev0 = game.musical_events[0]
        _advance_game_until(game, ev0.impact_time)
        key0 = game.LANE_KEYS[ev0.lane]

        # repeat=1 ignored
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": key0, "repeat": 1}))
        assert game.hits_perfect == 0

        # Valid press hits ev0
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": key0}))
        assert game.hits_perfect == 1

        # Hold same key (no KEYUP) until another note in same lane reaches impact_time
        next_same_lane = next(
            e for e in game.musical_events[1:] if e.lane == ev0.lane
        )
        _advance_game_until(game, next_same_lane.impact_time)
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": key0}))
        assert game.hits_perfect == 1
    finally:
        game.cleanup()


# --- R2 Boundaries (5 tests) ---


def test_t2_r2_rapid_weather_switching_and_extreme_dt():
    scene = StoryMapScene(character_id="westcol")
    samples = _pick_route_sample_points(scene, "uninorte", "ventana", count=3)
    anchor = samples[len(samples) // 2]

    s_ref_day = pygame.Surface((1920, 1080))
    scene.set_weather("day")
    _render_scene_pinned(scene, s_ref_day, anchor, dt=0.016)

    for _ in range(2):
        for mode in ("day", "sunset", "night", "rain", "day"):
            scene.set_weather(mode)
            with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
                scene.update(0.0)
                scene.update(0.35)

    assert scene.current_weather == "day"
    s_final = pygame.Surface((1920, 1080))
    cam_x, cam_y = _render_scene_pinned(scene, s_final, anchor, dt=0.016)
    a_ref = _surf_rgb(s_ref_day)
    a_fin = _surf_rgb(s_final)
    diffs = []
    for wx, wy in samples:
        sx, sy = int(round(wx - cam_x)), int(round(wy - cam_y))
        if 20 <= sx < 1900 and 110 <= sy < 1060:
            diffs.append(float(np.abs(_patch_rgb(a_fin, sx, sy, 4) - _patch_rgb(a_ref, sx, sy, 4)).mean()))
    assert diffs and min(diffs) < 12.0


def test_t2_r2_invalid_and_locked_campaign_routes_safe_handling():
    nodes, edges, _node_map, _edge_map = _load_layout_graph()
    assert compute_campaign_dijkstra_path(nodes, edges, 99999, 71) is None
    assert compute_campaign_dijkstra_path(nodes, edges, 71, 71) == [71]

    # Locked vs unlocked contrast driven publicly through SettingsManager
    mgr = SettingsManager.get_instance()
    mgr.update_story_progress(completed_microgames=[])
    sc_locked = StoryMapScene(character_id="westcol")
    sc_locked.set_weather("night")

    mgr.update_story_progress(completed_microgames=["uninorte_sprint", "uninorte_concentrate"])
    sc_unlocked = StoryMapScene(character_id="westcol")
    sc_unlocked.set_weather("night")

    samples = _pick_route_sample_points(sc_unlocked, "uninorte", "ventana", count=3)
    anchor = samples[len(samples) // 2]

    s_lock = pygame.Surface((1920, 1080))
    s_unlk = pygame.Surface((1920, 1080))
    cx, cy = _render_scene_pinned(sc_locked, s_lock, anchor)
    _render_scene_pinned(sc_unlocked, s_unlk, anchor)

    al = _surf_rgb(s_lock)
    au = _surf_rgb(s_unlk)
    luma_lock_vals = []
    luma_unlk_vals = []
    for wx, wy in samples:
        sx, sy = int(round(wx - cx)), int(round(wy - cy))
        if 20 <= sx < 1900 and 110 <= sy < 1060:
            luma_lock_vals.append(_luma(_patch_rgb(al, sx, sy, 3)))
            luma_unlk_vals.append(_luma(_patch_rgb(au, sx, sy, 3)))

    assert luma_lock_vals and max(luma_unlk_vals) >= min(luma_lock_vals) - 1.0


def test_t2_r2_camera_bounds_clipping_at_world_extremes():
    scene = StoryMapScene(character_id="westcol")
    scene.set_weather("night")
    surf = pygame.Surface((1920, 1080))

    for req_x, req_y in ((-500.0, -500.0), (99999.0, 99999.0)):
        with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
            scene.update(0.016)
        scene.camera.set_pos(req_x, req_y)
        assert 0.0 <= scene.camera.x <= scene.camera.max_x
        assert 0.0 <= scene.camera.y <= scene.camera.max_y
        scene.render(surf)
        assert float(_surf_rgb(surf).std()) > 8.0


def test_t2_r2_all_campaign_dijkstra_routes_exclude_hidden_edges():
    nodes, edges, _node_map, edge_map = _load_layout_graph()
    for src, dst in zip(STORY_CAMPAIGN_ORDER, STORY_CAMPAIGN_ORDER[1:]):
        n_start = StoryMapScene.POI_ENTRY_NODES[src]
        n_goal = StoryMapScene.POI_ENTRY_NODES[dst]
        path = compute_campaign_dijkstra_path(nodes, edges, n_start, n_goal)
        assert path is not None and len(path) >= 2
        for u, v in zip(path, path[1:]):
            edge = edge_map.get((u, v))
            assert edge is not None, f"Missing visible edge ({u}, {v}) in {src}->{dst}"
            assert edge.get("hidden", False) is False


def test_t2_r2_path_reveal_boundary_progress_zero_half_one_and_reverse():
    nodes, edges, node_map, edge_map = _load_layout_graph()
    n_path = compute_campaign_dijkstra_path(
        nodes, edges, StoryMapScene.POI_ENTRY_NODES["uninorte"], StoryMapScene.POI_ENTRY_NODES["ventana"]
    )
    assert n_path and len(n_path) >= 2
    renderer = WatercolorRouteRenderer(3342, 1882)
    route_data = renderer.get_or_build_route("uninorte", "ventana", n_path, node_map, edge_map)
    assert route_data is not None

    def _nz(p: float) -> int:
        s = renderer.get_revealed_surface(route_data, p)
        return int(np.count_nonzero(pygame.surfarray.array_alpha(s) > 10))

    nz0 = _nz(0.0)
    nz_001 = _nz(0.001)
    nz_999 = _nz(0.999)
    nz_100 = _nz(1.0)
    nz_back = _nz(0.25)

    assert nz0 <= nz_001 < nz_back < nz_999 <= nz_100
    assert nz_back < nz_100


# --- R3 Boundaries (5 tests) ---


def test_t2_r3_holiday_decor_offscreen_culling_at_corners():
    scene = StoryMapScene(character_id="westcol")
    surf = pygame.Surface((1920, 1080))
    for mode in ("day", "night"):
        scene.set_weather(mode)
        for cx, cy in ((0.0, 0.0), (float(scene.camera.max_x), float(scene.camera.max_y))):
            with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
                scene.update(0.016)
            scene.camera.set_pos(cx, cy)
            scene.render(surf)
            assert float(_surf_rgb(surf).std()) > 5.0


def test_t2_r3_holiday_decor_node_and_cloud_clearance():
    nodes, _edges, _node_map, _edge_map = _load_layout_graph()
    scene = StoryMapScene(character_id="westcol")
    poi_rects = [v["rect"] for v in scene.poi_registry.values()]

    decor_specs = [(scene.holiday_tree_pos, scene.holiday_tree_day)] + [
        (pos, scene.street_lamp_day) for pos in scene.street_lamp_positions
    ]
    for (px, py), spr in decor_specs:
        min_nd = min(math.hypot(px - n["x"], py - n["y"]) for n in nodes)
        assert min_nd >= 70.0, f"Decor at ({px},{py}) too close to street node ({min_nd:.1f}px)"
        full_rect = spr.get_rect(midbottom=(px, py))
        assert all(not full_rect.colliderect(pr) for pr in poi_rects)


def test_t2_r3_player_avatar_and_tree_ysort_visibility():
    scene = StoryMapScene(character_id="westcol")
    tx, ty = scene.holiday_tree_pos
    scene.player_is_moving = False

    for mode in ("day", "night"):
        scene.set_weather(mode)
        surf_n = pygame.Surface((1920, 1080))
        scene.player_pos = (float(tx), float(ty - 25))
        cam_x, cam_y = _render_scene_pinned(scene, surf_n, (tx, ty))

        surf_s = pygame.Surface((1920, 1080))
        scene.player_pos = (float(tx), float(ty + 25))
        _render_scene_pinned(scene, surf_s, (tx, ty))

        an = _surf_rgb(surf_n).astype(np.int16)
        as_ = _surf_rgb(surf_s).astype(np.int16)
        sx, sy = tx - cam_x, ty - cam_y
        patch_diff = np.abs(
            as_[max(0, sx - 45):min(1920, sx + 45), max(0, sy - 60):min(1080, sy + 50)]
            - an[max(0, sx - 45):min(1920, sx + 45), max(0, sy - 60):min(1080, sy + 50)]
        )
        assert int(np.count_nonzero(patch_diff.max(axis=2) > 15)) > 50


def test_t2_r3_decor_assets_clean_alpha_borders():
    for fname in (
        "arbolito_navidad_dia.png",
        "arbolito_navidad_noche.png",
        "alumbrado_poste_dia.png",
        "alumbrado_poste_noche.png",
    ):
        surf = pygame.image.load(str(REPO_ROOT / "assets" / fname)).convert_alpha()
        alpha = pygame.surfarray.array_alpha(surf)
        w, h = surf.get_size()
        corners = [
            int(alpha[0, 0]),
            int(alpha[w - 1, 0]),
            int(alpha[0, h - 1]),
            int(alpha[w - 1, h - 1]),
        ]
        assert max(corners) <= 10, f"{fname} opaque corners: {corners}"
        perim = np.concatenate([alpha[0, :], alpha[-1, :], alpha[:, 0], alpha[:, -1]])
        assert float(np.median(perim)) <= 10.0


def test_t2_r3_night_to_day_toggle_leaves_zero_residual_halos():
    scene = StoryMapScene(character_id="westcol")
    scene.player_pos = (100.0, 100.0)
    tx, ty = scene.holiday_tree_pos
    tw, th = scene.holiday_tree_day.get_size()

    s_fresh_day = pygame.Surface((1920, 1080))
    scene.set_weather("day")
    cam_x, cam_y = _render_scene_pinned(scene, s_fresh_day, (tx, ty - th // 2))

    s_night = pygame.Surface((1920, 1080))
    scene.set_weather("night")
    _render_scene_pinned(scene, s_night, (tx, ty - th // 2))

    s_after_night = pygame.Surface((1920, 1080))
    scene.set_weather("day")
    _render_scene_pinned(scene, s_after_night, (tx, ty - th // 2))

    sx, sy = tx - cam_x, ty - cam_y
    box = (
        slice(max(0, sx - tw // 2 - 20), min(1920, sx + tw // 2 + 20)),
        slice(max(0, sy - th - 20), min(1080, sy + 20)),
    )
    a_fresh = _surf_rgb(s_fresh_day)[box].astype(np.int16)
    a_after = _surf_rgb(s_after_night)[box].astype(np.int16)
    assert float(np.abs(a_after - a_fresh).mean()) < 10.0


# --- R4 Boundaries (5 tests) ---


def test_t2_r4_invalid_inputs_no_crash_and_no_settings_mutation():
    root_settings = REPO_ROOT / "settings.json"
    before = _sha256_file(root_settings)

    scene = StoryMapScene(character_id="westcol")
    scene.set_weather("hurricane")
    assert scene.current_weather in scene.weather_modes
    for evt in (
        pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 99}),
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_F12}),
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_z}),
    ):
        scene.handle_event(evt)

    game = BuenavistaTrendMicrogame(character_id="westcol")
    try:
        _advance_intro_to_play(game)
        for evt in (
            pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 99}),
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_F12}),
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_z}),
        ):
            game.handle_event(evt)
        assert game.lives == 5
    finally:
        game.cleanup()

    assert _sha256_file(root_settings) == before


def test_t2_r4_corrupt_settings_json_recovery_in_tmp_path(tmp_path: Path):
    root_settings = REPO_ROOT / "settings.json"
    before = _sha256_file(root_settings)

    bad_file = tmp_path / "bad_settings.json"
    bad_file.write_text("{corrupt_json", encoding="utf-8")
    mgr = SettingsManager(filepath=str(bad_file))
    assert isinstance(mgr.data, dict)
    assert mgr.get("window_width") == 1920
    assert isinstance(mgr.get_story_progress(), dict)
    assert _sha256_file(root_settings) == before


def test_t2_r4_buenavista_short_round_outro_duration_guard():
    results: List[bool] = []
    game = BuenavistaTrendMicrogame(
        character_id="westcol", on_complete_callback=lambda w: results.append(w)
    )
    try:
        _advance_intro_to_play(game)
        game.time_limit = 10.0
        game.time_left = 0.05
        game.update(0.10)
        assert game.is_finished is True
        assert game.is_won is True
        assert game.phase == game.PHASE_OUTRO

        # Short arcade round (< 20s) must finish outro promptly without 17s hang
        for _ in range(20):
            if results:
                break
            game.update(0.25)
        assert results == [True], f"Short-round outro did not complete promptly (outro_duration={game.outro_duration})"
    finally:
        game.cleanup()


def test_t2_r4_layout_json_readonly_under_map_navigation_stress():
    layout_path = REPO_ROOT / "config" / "map_poi_layout.json"
    before = _sha256_file(layout_path)

    scene = StoryMapScene(character_id="westcol")
    scene.show_intro_dialog = False
    scene.paloma_dialog_open = False
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (960, 540)}))
    scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (760, 440), "rel": (-200, -100), "buttons": (1, 0, 0)}))
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (760, 440)}))

    for key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_c, pygame.K_1, pygame.K_3):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": key}))
        with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
            scene.update(0.05)

    assert _sha256_file(layout_path) == before


def test_t2_r4_cleanup_and_exit_idempotency():
    for target_outro in (False, True):
        game = BuenavistaTrendMicrogame(character_id="westcol")
        if target_outro:
            _advance_intro_to_play(game)
            game.finish_game(True)
        game.cleanup()
        game.cleanup()
        game.exit()
        assert len(game.held_keys) == 0
        assert AudioManager.get_instance().current_track != game.music_track_name


# ===========================================================================
# TIER 3: PAIRWISE CROSS-FEATURE COMBINATIONS (7 TESTS)
# ===========================================================================


def test_t3_storymap_paloma_buenavista_launch_win_night_reveal_and_decor():
    mgr = SettingsManager.get_instance()
    mgr.update_story_progress(
        has_active_save=True,
        completed_microgames=["uninorte_sprint", "uninorte_concentrate", "punch_alert"],
        current_node_id=StoryMapScene.POI_ENTRY_NODES["buenavista"],
        weather="night",
    )
    sm = StateMachine()
    sc = StoryMapScene(character_id="westcol")
    sm.change_state(sc)
    _place_player_at_poi_entry(sc, "buenavista")
    sc.set_weather("night")
    assert sc.current_weather == "night"

    with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
        sm.update(0.05)
    # Enter Buenavista -> Paloma pre_pages
    sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    assert sc.paloma_dialog_open is True
    for _ in range(5):
        if not sc.paloma_dialog_open:
            break
        sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    assert sc.quest_card_open is True

    # Launch BuenavistaTrendMicrogame via quest card SPACE
    sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    mg = sm.current_state
    assert isinstance(mg, BuenavistaTrendMicrogame)
    try:
        _advance_intro_to_play(mg)
        mg.finish_game(True)
        _step_outro_to_callback(mg)
    finally:
        mg.cleanup()

    assert sm.current_state is sc
    assert sc.paloma_dialog_open is True

    # Advance post_win_pages -> triggers active_path_reveal for ("buenavista", "metropolitano")
    for _ in range(5):
        if not sc.paloma_dialog_open:
            break
        sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))

    with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
        sm.update(0.05)
    assert sc.active_path_reveal is not None
    assert sc.active_path_reveal["pair"] == ("buenavista", "metropolitano")

    for _ in range(120):
        if sc.active_path_reveal is None:
            break
        with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
            sm.update(0.05)
    assert sc.active_path_reveal is None

    surf = pygame.Surface((1920, 1080))
    _render_scene_pinned(sc, surf, sc.holiday_tree_pos)
    assert float(_surf_rgb(surf).std()) > 10.0


def test_t3_day_night_transition_camera_pan_over_decor_and_poi_occlusion():
    scene = StoryMapScene(character_id="westcol")
    scene.player_pos = (100.0, 100.0)
    targets = [
        scene.poi_registry["ventana"]["rect"].center,
        scene.holiday_tree_pos,
        scene.poi_registry["buenavista"]["rect"].center,
    ]
    for target in targets:
        s_day = pygame.Surface((1920, 1080))
        scene.set_weather("day")
        _render_scene_pinned(scene, s_day, target)

        s_night = pygame.Surface((1920, 1080))
        scene.set_weather("night")
        _render_scene_pinned(scene, s_night, target)

        assert float(_surf_rgb(s_day).mean()) > float(_surf_rgb(s_night).mean()) + 15.0


def test_t3_weather_cycle_unlocked_vs_locked_route_contrast_and_lamps():
    mgr = SettingsManager.get_instance()
    mgr.update_story_progress(
        completed_microgames=["uninorte_sprint", "uninorte_concentrate"]
    )
    scene = StoryMapScene(character_id="westcol")
    scene.set_weather("day")
    samples_unlk = _pick_route_sample_points(scene, "uninorte", "ventana", count=3)
    samples_lock = _pick_route_sample_points(scene, "ventana", "buenavista", count=3)

    visited = []
    for _ in range(4):
        mode = scene.cycle_weather()
        visited.append(mode)
        for _ in range(30):
            with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
                scene.update(0.05)

        surf_u = pygame.Surface((1920, 1080))
        cx_u, cy_u = _render_scene_pinned(scene, surf_u, samples_unlk[1])
        surf_l = pygame.Surface((1920, 1080))
        cx_l, cy_l = _render_scene_pinned(scene, surf_l, samples_lock[1])
        surf_lamp = pygame.Surface((1920, 1080))
        _render_scene_pinned(scene, surf_lamp, scene.street_lamp_positions[0])

        assert float(_surf_rgb(surf_lamp).std()) > 8.0
        if mode == "night":
            au = _surf_rgb(surf_u)
            al = _surf_rgb(surf_l)
            u_luma = max(
                _luma(_patch_rgb(au, int(round(wx - cx_u)), int(round(wy - cy_u)), 3))
                for wx, wy in samples_unlk
            )
            l_luma = min(
                _luma(_patch_rgb(al, int(round(wx - cx_l)), int(round(wy - cy_l)), 3))
                for wx, wy in samples_lock
            )
            assert u_luma >= l_luma

    assert set(visited) == {"sunset", "night", "rain", "day"}


def test_t3_gamepad_and_keyboard_mixed_input_beatmap_hud_combo_lives():
    # Inverse map: lane_idx -> gamepad button matching GAMEPAD_BUTTON_KEYS {2: K_d, 0: K_f, 3: K_j, 1: K_k}
    expected_btn_for_lane = {0: 2, 1: 0, 2: 3, 3: 1}
    game = BuenavistaTrendMicrogame(character_id="westcol")
    try:
        assert game.GAMEPAD_BUTTONS == {2: 0, 0: 1, 3: 2, 1: 3}
        _advance_intro_to_play(game)

        # Pick 2 notes from each of the 3 beatmap phases
        p1 = [e for e in game.musical_events if e.impact_time < 10.0][:2]
        p2 = [e for e in game.musical_events if 10.0 <= e.impact_time < 20.0][:2]
        p3 = [e for e in game.musical_events if e.impact_time >= 20.0][:2]
        targets = p1 + p2 + p3

        dt = 1.0 / 60.0
        target_set = set(id(e) for e in targets)
        t_idx = 0
        while t_idx < len(targets) and not game.is_finished:
            game.update(dt)
            # Keep non-target falling notes from causing accidental misses
            for ev in game.musical_events:
                if id(ev) not in target_set and ev.state == "falling" and abs(ev.impact_time - game.song_elapsed) <= 0.018:
                    k = game.LANE_KEYS[ev.lane]
                    game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": k}))
                    game.handle_event(pygame.event.Event(pygame.KEYUP, {"key": k}))

            cur = targets[t_idx]
            if cur.state == "falling" and abs(cur.impact_time - game.song_elapsed) <= 0.018:
                if t_idx % 2 == 0:
                    k = game.LANE_KEYS[cur.lane]
                    game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": k}))
                    game.handle_event(pygame.event.Event(pygame.KEYUP, {"key": k}))
                else:
                    btn = expected_btn_for_lane[cur.lane]
                    game.handle_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": btn}))
                    game.handle_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": btn}))
                t_idx += 1

        assert game.hits_perfect + game.hits_good >= 6
        assert game.combo >= 6
        assert game.lives == 5

        # Inject 1 deliberate miss and confirm combo resets to 0 and lives drops to 4
        _advance_game_until(game, game.song_elapsed + 0.30)
        wrong_lane = next(
            l for l in range(4)
            if not any(e.lane == l and e.state == "falling" and abs(e.impact_time - game.song_elapsed) < 0.50 for e in game.musical_events)
        )
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": game.LANE_KEYS[wrong_lane]}))
        game.handle_event(pygame.event.Event(pygame.KEYUP, {"key": game.LANE_KEYS[wrong_lane]}))
        assert game.combo == 0
        assert game.lives == 4
    finally:
        game.cleanup()


def test_t3_buenavista_loss_paloma_post_lose_and_progress_isolation():
    root_settings = REPO_ROOT / "settings.json"
    before = _sha256_file(root_settings)

    mgr = SettingsManager.get_instance()
    mgr.update_story_progress(
        has_active_save=True,
        completed_microgames=["uninorte_sprint", "uninorte_concentrate", "punch_alert"],
        current_node_id=StoryMapScene.POI_ENTRY_NODES["buenavista"],
    )
    sm = StateMachine()
    sc = StoryMapScene(character_id="westcol")
    sm.change_state(sc)
    _place_player_at_poi_entry(sc, "buenavista")

    with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
        sm.update(0.05)
    sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    for _ in range(5):
        if not sc.paloma_dialog_open:
            break
        sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    assert sc.quest_card_open is True

    sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    mg = sm.current_state
    assert isinstance(mg, BuenavistaTrendMicrogame)
    try:
        _advance_intro_to_play(mg)
        # Allow 5 notes to pass without pressing keys -> defeat
        for _ in range(700):
            if mg.is_finished:
                break
            mg.update(1.0 / 60.0)
        assert mg.is_finished is True
        assert mg.is_won is False
        assert mg.lives == 0
        _step_outro_to_callback(mg)
    finally:
        mg.cleanup()

    assert sm.current_state is sc
    assert sc.paloma_dialog_open is True
    assert sc.paloma_dialog_pages == PALOMA_STORY_DIALOGS["buenavista"]["post_lose_pages"]

    for _ in range(4):
        if not sc.paloma_dialog_open:
            break
        sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    for _ in range(5):
        with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
            sm.update(0.05)
    assert sc.active_path_reveal is None
    assert "buenavista_trend" not in mgr.get_story_progress()["completed_microgames"]
    assert _sha256_file(root_settings) == before


def test_t3_storymap_to_buenavista_audio_handover_and_return():
    mgr = SettingsManager.get_instance()
    mgr.update_story_progress(
        has_active_save=True,
        completed_microgames=["uninorte_sprint", "uninorte_concentrate", "punch_alert"],
        current_node_id=StoryMapScene.POI_ENTRY_NODES["buenavista"],
    )
    sm = StateMachine()
    sc = StoryMapScene(character_id="westcol")
    sm.change_state(sc)
    _place_player_at_poi_entry(sc, "buenavista")

    with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
        sm.update(0.05)
    sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    for _ in range(5):
        if not sc.paloma_dialog_open:
            break
        sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))

    mg = sm.current_state
    assert isinstance(mg, BuenavistaTrendMicrogame)
    _advance_intro_to_play(mg)
    mg.update(0.2)
    sm.change_state(sc)
    assert sm.current_state is sc
    surf = pygame.Surface((1920, 1080))
    _render_scene_pinned(sc, surf, sc.player_pos)
    assert float(_surf_rgb(surf).std()) > 8.0


def test_t3_1920x1080_night_callout_hud_weather_pill_and_decor_coexistence():
    scene = StoryMapScene(character_id="westcol")
    scene.set_weather("night")
    _place_player_at_poi_entry(scene, "buenavista")
    scene.show_intro_dialog = False
    scene.paloma_dialog_open = False
    scene.cinematic_timer = scene.cinematic_duration

    with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
        for _ in range(12):
            scene.update(0.02)

    surf = pygame.Surface((1920, 1080))
    scene.camera.set_pos(
        max(0.0, min(float(scene.camera.max_x), scene.player_pos[0] - 960.0)),
        max(0.0, min(float(scene.camera.max_y), scene.player_pos[1] - 540.0)),
    )
    scene.render(surf)

    viewport = pygame.Rect(0, 0, 1920, 1080)
    assert viewport.contains(scene.weather_pill_rect)
    arr = _surf_rgb(surf)
    assert float(arr.std()) > 12.0


# ===========================================================================
# TIER 4: REAL-WORLD END-TO-END GAMEPLAY SCENARIOS (6 TESTS)
# ===========================================================================


def test_t4_e2e_buenavista_full_headless_playthrough_victory():
    results: List[bool] = []
    game = BuenavistaTrendMicrogame(
        character_id="westcol", on_complete_callback=lambda w: results.append(w)
    )
    surf = pygame.Surface((1920, 1080))
    try:
        dt = 1.0 / 60.0
        for frame in range(2500):
            if game.phase == game.PHASE_OUTRO:
                break
            game.update(dt)
            if game.phase == game.PHASE_PLAY:
                for ev in game.musical_events:
                    if ev.state == "falling" and abs(ev.impact_time - game.song_elapsed) <= 0.015:
                        k = game.LANE_KEYS[ev.lane]
                        game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": k}))
                        game.handle_event(pygame.event.Event(pygame.KEYUP, {"key": k}))
            if frame % 30 == 0:
                game.render(surf)

        assert game.is_finished is True
        assert game.is_won is True
        assert game.lives == 5
        assert game.hits_perfect >= len(EN_BARRANQUILLA_BEATMAP_DATA) - 2
        assert game.max_combo >= 30

        res_data = game.get_result_data()
        assert res_data["won"] is True
        assert res_data["lives_left"] == 5

        _step_outro_to_callback(game)
        assert results == [True]
    finally:
        game.cleanup()


def test_t4_e2e_buenavista_full_headless_playthrough_game_over():
    results: List[bool] = []
    game = BuenavistaTrendMicrogame(
        character_id="valdiri", on_complete_callback=lambda w: results.append(w)
    )
    surf = pygame.Surface((1920, 1080))
    try:
        _advance_intro_to_play(game)
        dt = 1.0 / 60.0
        for frame in range(800):
            if game.is_finished:
                break
            game.update(dt)
            if frame % 30 == 0:
                game.render(surf)

        assert game.is_finished is True
        assert game.is_won is False
        assert game.misses_count == 5
        assert game.lives == 0
        assert game.combo == 0
        assert game.phase == game.PHASE_OUTRO
        game.render(surf)

        _step_outro_to_callback(game)
        assert results == [False]
    finally:
        game.cleanup()


def test_t4_e2e_storymap_multistep_campaign_day_and_night():
    mgr = SettingsManager.get_instance()
    mgr.reset_story_progress(character_id="westcol")
    sm = StateMachine()
    sc = StoryMapScene(character_id="westcol")
    sm.change_state(sc)

    # Dismiss welcome Paloma dialog if open on fresh story, and clear any trophy popup unlocked by chatting
    for _ in range(5):
        if not sc.paloma_dialog_open:
            break
        sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    for _ in range(15):
        sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
        with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
            sm.update(0.15)

    initial_likes = mgr.get_story_progress().get("likes", 0)

    for idx, poi_key in enumerate(STORY_CAMPAIGN_ORDER):
        sc.set_weather("day" if idx % 2 == 0 else "night")
        _place_player_at_poi_entry(sc, poi_key)
        with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
            sm.update(0.05)

        sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
        for _ in range(6):
            if not sc.paloma_dialog_open:
                break
            sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
        assert sc.quest_card_open is True

        sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))

        # Complete all chained stages for this POI
        stages = STORY_LEVEL_STAGES.get(poi_key, [])
        for _stage in stages:
            mg = sm.current_state
            assert mg is not sc
            try:
                mg.phase = mg.PHASE_PLAY
                mg.finish_game(True)
                for step in range(140):
                    if sm.current_state is not mg:
                        break
                    mg.update(0.25)
                    if step == 18:
                        mg.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
            finally:
                if hasattr(mg, "cleanup"):
                    mg.cleanup()

        assert sm.current_state is sc

        # Dismiss trophy modal if opened before Paloma's post-win dialog (e.g., Uninorte clear trophy)
        if not sc.paloma_dialog_open:
            for _ in range(15):
                if sc.paloma_dialog_open:
                    break
                sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
                with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
                    sm.update(0.15)

        # Advance post-win Paloma dialog
        for _ in range(6):
            if not sc.paloma_dialog_open:
                break
            sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))

        if idx < len(STORY_CAMPAIGN_ORDER) - 1:
            with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
                sm.update(0.05)
            for _ in range(120):
                if sc.active_path_reveal is None:
                    break
                with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
                    sm.update(0.05)

    assert sc.show_victory_modal is True
    prog = mgr.get_story_progress()
    for poi_key in STORY_CAMPAIGN_ORDER:
        for st in STORY_LEVEL_STAGES[poi_key]:
            assert st["id"] in prog["completed_microgames"]
    assert prog["likes"] > initial_likes


def test_t4_e2e_storymap_1920x1080_visual_tour_pois_and_holiday_decor():
    scene = StoryMapScene(character_id="westcol")
    tour_points: List[Tuple[str, Tuple[float, float]]] = [
        (f"poi:{k}", v["rect"].center) for k, v in scene.poi_registry.items()
    ]
    tour_points.append(("tree", scene.holiday_tree_pos))
    for i, pos in enumerate(scene.street_lamp_positions):
        tour_points.append((f"lamp:{i}", pos))

    s_day = pygame.Surface((1920, 1080))
    s_night = pygame.Surface((1920, 1080))
    for label, pt in tour_points:
        scene.set_weather("day")
        _render_scene_pinned(scene, s_day, pt)
        scene.set_weather("night")
        _render_scene_pinned(scene, s_night, pt)

        ad = _surf_rgb(s_day)
        an = _surf_rgb(s_night)
        assert float(ad.std()) > 10.0, f"Blank day render at {label}"
        assert float(an.std()) > 10.0, f"Blank night render at {label}"
        assert float(ad.mean()) > float(an.mean()) + 15.0, f"Night not darker globally at {label}"


def test_t4_e2e_paloma_to_buenavista_to_night_path_reveal_integration():
    mgr = SettingsManager.get_instance()
    mgr.update_story_progress(
        has_active_save=True,
        completed_microgames=["uninorte_sprint", "uninorte_concentrate", "punch_alert"],
        current_node_id=StoryMapScene.POI_ENTRY_NODES["buenavista"],
        weather="night",
    )
    sm = StateMachine()
    sc = StoryMapScene(character_id="char")
    sm.change_state(sc)
    _place_player_at_poi_entry(sc, "buenavista")
    sc.set_weather("night")

    with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
        sm.update(0.05)
    sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    for _ in range(5):
        if not sc.paloma_dialog_open:
            break
        sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    assert sc.quest_card_open is True

    sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    mg = sm.current_state
    assert isinstance(mg, BuenavistaTrendMicrogame)
    try:
        dt = 1.0 / 60.0
        for _ in range(2500):
            if mg.phase == mg.PHASE_OUTRO:
                break
            mg.update(dt)
            if mg.phase == mg.PHASE_PLAY:
                for ev in mg.musical_events:
                    if ev.state == "falling" and abs(ev.impact_time - mg.song_elapsed) <= 0.015:
                        k = mg.LANE_KEYS[ev.lane]
                        mg.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": k}))
                        mg.handle_event(pygame.event.Event(pygame.KEYUP, {"key": k}))
        assert mg.is_won is True
        _step_outro_to_callback(mg)
    finally:
        mg.cleanup()

    assert sm.current_state is sc
    assert sc.paloma_dialog_open is True
    for _ in range(5):
        if not sc.paloma_dialog_open:
            break
        sm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))

    with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
        sm.update(0.05)
    assert sc.active_path_reveal is not None
    assert sc.active_path_reveal["pair"] == ("buenavista", "metropolitano")

    surf = pygame.Surface((1920, 1080))
    for _ in range(120):
        if sc.active_path_reveal is None:
            break
        with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
            sm.update(0.05)
        sm.render(surf)
    assert sc.active_path_reveal is None

    samples = _pick_route_sample_points(sc, "buenavista", "metropolitano", count=3)
    cx, cy = _render_scene_pinned(sc, surf, samples[1])
    arr = _surf_rgb(surf)
    assert any(
        _luma(_patch_rgb(arr, int(round(wx - cx)), int(round(wy - cy)), 3)) > 480.0
        for wx, wy in samples
    )


def test_t4_e2e_verification_captures_pipeline_and_r4_integrity_audit():
    # Render all 3 1920x1080 visual verification views strictly in memory (never touch disk PNGs)
    game = BuenavistaTrendMicrogame(character_id="westcol")
    s_buenavista = pygame.Surface((1920, 1080))
    try:
        _advance_intro_to_play(game)
        _advance_game_until(game, 2.65)
        game.render(s_buenavista)
    finally:
        game.cleanup()

    scene = StoryMapScene(character_id="westcol")
    tx, ty = scene.holiday_tree_pos
    s_day = pygame.Surface((1920, 1080))
    scene.set_weather("day")
    _render_scene_pinned(scene, s_day, (tx, ty))

    s_night = pygame.Surface((1920, 1080))
    scene.set_weather("night")
    _render_scene_pinned(scene, s_night, (tx, ty))

    for s in (s_buenavista, s_day, s_night):
        assert s.get_size() == (1920, 1080)
        assert float(_surf_rgb(s).std()) > 12.0

    assert float(_surf_rgb(s_day).mean()) > float(_surf_rgb(s_night).mean()) + 20.0

    # R4 integrity audit: all 7 protected files must match exact baseline SHA256 hashes
    for rel, expected_hash in PROTECTED_CONFIG_HASHES.items():
        assert _sha256_file(REPO_ROOT / rel) == expected_hash
    for rel, (expected_hash, expected_bytes, expected_dims) in PROTECTED_AI_PNGS.items():
        fpath = REPO_ROOT / rel
        raw = fpath.read_bytes()
        assert len(raw) == expected_bytes
        assert hashlib.sha256(raw).hexdigest().upper() == expected_hash
        assert pygame.image.load(str(fpath)).get_size() == expected_dims
