"""Pruebas para preview flotante estilo Mario Wonder, Quest Card, nodos y Menú Principal."""
import os
import sys
import unittest
from unittest.mock import patch

import pygame

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.engine import SettingsManager
from scenes.main_menu import MainMenuScene
from scenes.story_map.scene import StoryMapScene
from scenes.story_map_data import STORY_LEVEL_PREVIEW_META, STORY_PLAYABLE_POIS


def _opaque_bbox_on_surface(surf: pygame.Surface, min_alpha: int = 20) -> pygame.Rect:
    mask = pygame.mask.from_surface(surf, min_alpha)
    rects = mask.get_bounding_rects()
    if not rects:
        return pygame.Rect(0, 0, 0, 0)
    out = rects[0].copy()
    for r in rects[1:]:
        out.union_ip(r)
    return out


class TestMainMenuCohesion(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        AssetManager.get_instance()

    def test_main_menu_spacing_and_pill_parity(self) -> None:
        scene = MainMenuScene()
        self.assertEqual(len(scene.buttons), 7)
        buttons = [
            scene.btn_jugar,
            scene.btn_cargar,
            scene.btn_opciones,
            scene.btn_estadisticas,
            scene.btn_salir,
        ]

        opaque_rects = []
        for btn in buttons:
            ob = _opaque_bbox_on_surface(btn.normal_sprite, 20)
            opaque_rects.append(
                pygame.Rect(btn.rect.x + ob.x, btn.rect.y + ob.y, ob.width, ob.height)
            )

        # Brechas verticales compactas y sin solapamiento entre botones
        gaps = [opaque_rects[i + 1].top - opaque_rects[i].bottom for i in range(4)]
        for g in gaps:
            self.assertGreaterEqual(g, 10, f"Botones demasiado pegados o solapados: gaps={gaps}")
            self.assertLessEqual(g, 24, f"Botones demasiado separados: gaps={gaps}")

        # Paridad visual de Cargar Partida (idx 1) frente a Opciones (2), Estadísticas (3) y Salir (4)
        cargar_w = opaque_rects[1].width
        cargar_h = opaque_rects[1].height
        for idx in (2, 3, 4):
            self.assertLessEqual(
                abs(cargar_w - opaque_rects[idx].width),
                6,
                f"Ancho opaco desigual en Cargar Partida ({cargar_w}) vs idx {idx} ({opaque_rects[idx].width})",
            )
            self.assertLessEqual(
                abs(cargar_h - opaque_rects[idx].height),
                12,
                f"Alto opaco desigual en Cargar Partida ({cargar_h}) vs idx {idx} ({opaque_rects[idx].height})",
            )


class TestStoryMapPreviewAndQuestCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        AssetManager.get_instance()
        AudioManager.get_instance()

    def setUp(self) -> None:
        self.settings = SettingsManager.get_instance()
        self.settings.reset_story_progress()
        self.scene = StoryMapScene()
        self.scene.show_intro_dialog = False
        self.scene.paloma_dialog_open = False
        self.scene.paloma_dialog_anim_t = 0.0
        self.scene.cinematic_timer = self.scene.cinematic_duration

    def test_preview_metadata_covers_all_playable_pois(self) -> None:
        for poi_key in STORY_PLAYABLE_POIS:
            self.assertIn(poi_key, STORY_LEVEL_PREVIEW_META)
            meta = STORY_LEVEL_PREVIEW_META[poi_key]
            self.assertGreaterEqual(meta["difficulty"], 1)
            self.assertLessEqual(meta["difficulty"], meta["max_difficulty"])

    def test_quest_card_typography_hierarchy_and_thumbnail_all_pois(self) -> None:
        canvas = pygame.Surface((1920, 1080))
        for poi_key in STORY_PLAYABLE_POIS:
            self.scene._open_quest_card(poi_key)
            self.scene.quest_card_anim_t = 1.0
            self.scene._render_quest_card(canvas)

            m = self.scene.last_quest_layout_metrics
            self.assertEqual(m["poi"], poi_key)
            self.assertGreater(m["title_size"], m["micro_size"], f"{poi_key}: título <= microjuego")
            self.assertGreater(m["micro_size"], m["desc_size"], f"{poi_key}: microjuego <= descripción")
            self.assertGreater(m["desc_size"], m["district_size"], f"{poi_key}: descripción <= distrito")

            card_rect = m["card_rect"]
            title_rect = m["title_rect_screen"]
            thumb_rect = m["thumb_rect_screen"]
            # Título dentro de la zona segura de pergamino (sin tocar hibiscos izquierdos ni sello derecho)
            self.assertGreaterEqual(title_rect.left, card_rect.left + 145, f"{poi_key}: título choca con flores")
            self.assertLessEqual(title_rect.right, card_rect.right - 95, f"{poi_key}: título choca con sello X")
            self.assertTrue(card_rect.contains(thumb_rect), f"{poi_key}: miniatura fuera del modal")

    def test_quest_card_button_hover_shimmer_updates_when_open(self) -> None:
        self.scene._open_quest_card("buenavista")
        self.scene.quest_card_anim_t = 1.0
        canvas = pygame.Surface((1920, 1080))
        self.scene._render_quest_card(canvas)

        play_center = self.scene.btn_quest_play.rect.center
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": play_center}))
        self.assertTrue(self.scene.btn_quest_play.is_hovered)
        self.assertEqual(self.scene.btn_quest_play.shimmer_progress, 0.0)

        scale_before = self.scene.btn_quest_play.current_scale
        self.scene.update(0.1)
        self.assertGreater(self.scene.btn_quest_play.current_scale, scale_before)
        self.assertGreater(self.scene.btn_quest_play.shimmer_progress, 0.0)

    def test_quest_card_click_outside_uses_quest_card_center_y(self) -> None:
        self.scene._open_quest_card("uninorte")
        self.scene.quest_card_anim_t = 1.0
        # Clic en la zona inferior real de la tarjeta (y=1000 < 588 + 439 = 1027) NO debe cerrarla
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (960, 1000)}))
        self.assertTrue(self.scene.quest_card_open)

        # Clic claramente fuera (arriba en y=80) sí debe cerrar el modal
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (960, 80)}))
        self.assertFalse(self.scene.quest_card_open)

    def test_direct_stop_node_click_and_hover_map_to_poi(self) -> None:
        stop_map = self.scene._get_playable_stop_node_map()
        self.assertEqual(set(stop_map.values()), set(STORY_PLAYABLE_POIS))

        # Mover cámara hacia Uninorte y ubicar el cursor sobre su nodo amarillo (nodo 71)
        uni_nid = self.scene._get_poi_target_node("uninorte")
        _, _, node_map, _, _ = self.scene._get_street_graph()
        uni_node = node_map[uni_nid]

        self.scene.player_node_id = self.scene._get_poi_target_node("buenavista")
        bue_node = node_map[self.scene.player_node_id]
        self.scene.player_pos = (float(bue_node["x"]), float(bue_node["y"]))
        self.scene.player_is_moving = False

        self.scene.camera.x = max(0.0, uni_node["x"] - 400.0)
        self.scene.camera.y = max(0.0, uni_node["y"] - 500.0)
        screen_pos = (int(uni_node["x"] - self.scene.camera.x), int(uni_node["y"] - self.scene.camera.y))

        with patch("pygame.mouse.get_pos", return_value=screen_pos):
            self.scene.update(0.05)
        self.assertEqual(self.scene.hovered_stop_node_id, uni_nid)
        self.assertTrue(self.scene.uninorte_hover)
        self.assertNotEqual(self.scene.callout_active_poi, "uninorte")
        self.assertEqual(self.scene.callout_active_poi, "buenavista")

        # Si el jugador está en un nodo sin nivel (p.ej. nodo 0), el hover lejano en nodo o edificio NO abre callout
        self.scene.player_node_id = 0
        self.scene.player_pos = (float(node_map[0]["x"]), float(node_map[0]["y"]))
        self.scene.callout_active_poi = None
        self.scene.callout_anim_t = 0.0
        self.scene.camera.x = max(0.0, uni_node["x"] - 400.0)
        self.scene.camera.y = max(0.0, uni_node["y"] - 500.0)
        self.scene.camera.target_x = self.scene.camera.x
        self.scene.camera.target_y = self.scene.camera.y
        screen_pos = (int(uni_node["x"] - self.scene.camera.x), int(uni_node["y"] - self.scene.camera.y))
        with patch("pygame.mouse.get_pos", return_value=screen_pos):
            self.scene.update(0.05)
        self.assertEqual(self.scene.hovered_stop_node_id, uni_nid)
        self.assertTrue(self.scene.uninorte_hover)
        self.assertIsNone(self.scene.callout_active_poi)
        self.assertEqual(self.scene.callout_anim_t, 0.0)

        # Hover lejano sobre el edificio de Uninorte tampoco debe abrir el callout
        uni_rect = self.scene.poi_registry["uninorte"]["rect"]
        bldg_screen = (int(uni_rect.centerx - self.scene.camera.x), int(uni_rect.centery - self.scene.camera.y))
        with patch("pygame.mouse.get_pos", return_value=bldg_screen):
            self.scene.update(0.05)
        self.assertTrue(self.scene.uninorte_hover)
        self.assertIsNone(self.scene.callout_active_poi)

        # Click directo sobre el nodo amarillo sigue viajando con player_target_poi == "uninorte"
        screen_pos = (int(uni_node["x"] - self.scene.camera.x), int(uni_node["y"] - self.scene.camera.y))
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": screen_pos}))
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": screen_pos}))
        self.assertTrue(self.scene.player_is_moving)
        self.assertEqual(self.scene.player_target_poi, "uninorte")

    def test_proximity_callout_approaching_click_to_enter_and_metropolitano_space(self) -> None:
        _, _, node_map, _, _ = self.scene._get_street_graph()
        canvas = pygame.Surface((1920, 1080))
        blocked = self.scene._get_blocked_hud_rects()

        # 1. Aproximándose dentro del radio (~100 px) del nodo de entrada -> activa callout anclado al nodo
        # y sin solapar al avatar mientras camina cerca.
        uni_nid = self.scene._get_poi_target_node("uninorte")
        uni_nd = node_map[uni_nid]
        self.scene.player_is_moving = True
        self.scene.player_pos = (float(uni_nd["x"] + 90), float(uni_nd["y"] + 40))
        self.scene.camera.x = max(0.0, min(self.scene.world_w - 1920.0, uni_nd["x"] - 960.0))
        self.scene.camera.y = max(0.0, min(self.scene.world_h - 1080.0, uni_nd["y"] - 540.0))
        with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
            for _ in range(12):
                self.scene.update(0.05)
        self.assertEqual(self.scene.callout_active_poi, "uninorte")
        self.assertEqual(self.scene.callout_anchor_source, "node")

        self.scene.render(canvas)
        callout_rect = self.scene.level_preview.last_callout_rect
        self.assertIsNotNone(callout_rect)
        cam_x, cam_y = int(self.scene.camera.x), int(self.scene.camera.y)
        player_screen = self.scene._get_player_screen_rect(cam_x, cam_y)
        poi_screen = self.scene.poi_registry["uninorte"]["rect"].move(-cam_x, -cam_y)
        self.assertFalse(callout_rect.colliderect(poi_screen))
        if player_screen is not None:
            self.assertFalse(callout_rect.colliderect(player_screen))
        for blk in blocked:
            self.assertFalse(callout_rect.colliderect(blk))

        # 2. Hover lejano sobre otro POI (Buenavista) mientras el jugador está cerca de Uninorte
        # NO debe reemplazar ni ocultar el callout de Uninorte.
        bue_rect = self.scene.poi_registry["buenavista"]["rect"]
        bue_screen = (int(bue_rect.centerx - cam_x), int(bue_rect.centery - cam_y))
        with patch("pygame.mouse.get_pos", return_value=bue_screen):
            self.scene.update(0.05)
        self.assertEqual(self.scene.callout_active_poi, "uninorte")

        # 3. Arrastre de cámara que empieza sobre la tarjeta visible NO debe abrir el nivel
        c_pos = callout_rect.center
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": c_pos}))
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (c_pos[0] + 35, c_pos[1])}))
        self.assertFalse(self.scene.quest_card_open)
        self.assertFalse(self.scene.paloma_dialog_open)

        # 4. Click corto directo sobre el callout visible SÍ debe iniciar el flujo del nivel
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": c_pos}))
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": c_pos}))
        self.assertTrue(self.scene.paloma_dialog_open or self.scene.quest_card_open)
        self.assertEqual(self.scene.active_poi, "uninorte")
        self.assertFalse(self.scene.player_is_moving)
        self.scene.paloma_dialog_open = False
        self.scene.quest_card_open = False

        # 4B. Cerrar quest_card con MOUSEBUTTONDOWN afuera no debe dejar mouse_down_pos obsoleto
        # que dispare un clic fantasma al soltar MOUSEBUTTONUP.
        self.scene.player_node_id = uni_nid
        self.scene.player_pos = (float(uni_nd["x"]), float(uni_nd["y"]))
        self.scene.player_is_moving = False
        self.scene.mouse_down_pos = (960, 80)
        self.scene._open_quest_card("uninorte")
        self.scene.quest_card_anim_t = 1.0
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (960, 80)}))
        self.assertFalse(self.scene.quest_card_open)
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (960, 80)}))
        self.assertFalse(self.scene.player_is_moving)

        # 4C. Si el jugador ya salió del radio de cercanía mientras el callout se desvanece,
        # un clic sobre el callout saliente NO debe abrir el nivel.
        self.scene.player_node_id = 0
        self.scene.player_pos = (float(node_map[0]["x"]), float(node_map[0]["y"]))
        self.scene.callout_active_poi = "uninorte"
        self.scene.callout_anim_t = 0.5
        self.scene.level_preview.last_callout_rect = callout_rect.copy()
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": c_pos}))
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": c_pos}))
        self.assertFalse(self.scene.paloma_dialog_open or self.scene.quest_card_open)
        self.scene.callout_active_poi = None
        self.scene.callout_anim_t = 0.0
        self.scene.level_preview.clear_last_callout()

        # 5. Regresión Metropolitano nodo 55 (> 280 px del centro del edificio):
        # SPACE / RETURN debe abrir Metropolitano y mostrar su callout estando en nodo 55.
        met_nid = self.scene._get_poi_target_node("metropolitano")
        self.assertEqual(met_nid, 55)
        met_nd = node_map[met_nid]
        self.scene.player_node_id = met_nid
        self.scene.player_pos = (float(met_nd["x"]), float(met_nd["y"]))
        self.scene.player_is_moving = False
        self.scene.camera.x = max(0.0, min(self.scene.world_w - 1920.0, met_nd["x"] - 960.0))
        self.scene.camera.y = max(0.0, min(self.scene.world_h - 1080.0, met_nd["y"] - 540.0))
        with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
            for _ in range(12):
                self.scene.update(0.05)
        self.assertEqual(self.scene.callout_active_poi, "metropolitano")
        self.assertEqual(self.scene.callout_anchor_source, "parked")
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
        self.assertTrue(self.scene.paloma_dialog_open or self.scene.quest_card_open)
        self.assertEqual(self.scene.active_poi, "metropolitano")
        self.scene.paloma_dialog_open = False
        self.scene.quest_card_open = False

        # 6. Nodos de cruce no jugables (56, 75, 61, 66) NO deben activar callout ni abrir nivel con SPACE
        for non_entry_nid in (56, 75, 61, 66):
            if non_entry_nid not in node_map:
                continue
            nd = node_map[non_entry_nid]
            self.scene.player_node_id = non_entry_nid
            self.scene.player_pos = (float(nd["x"]), float(nd["y"]))
            self.scene.player_is_moving = False
            self.scene.callout_active_poi = None
            self.scene.callout_anim_t = 0.0
            with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
                self.scene.update(0.05)
            self.assertIsNone(
                self.scene.callout_active_poi,
                f"Nodo no jugable {non_entry_nid} activó callout indebidamente: {self.scene.callout_active_poi}",
            )
            self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
            self.assertFalse(
                self.scene.paloma_dialog_open or self.scene.quest_card_open,
                f"Nodo no jugable {non_entry_nid} abrió nivel con RETURN",
            )

    def test_hud_suppresses_poi_hover_and_callout_avoids_hud_for_all_pois(self) -> None:
        # Cursor sobre SocialHUD (Logros) no debe activar ningún POI detrás del HUD
        self.scene.camera.x = 500.0
        self.scene.camera.y = 400.0
        logros_center = self.scene.social_hud.pills["logros"].rect.center
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": logros_center}))
        self.assertTrue(self.scene.social_hud.pills["logros"].is_hovered)
        with patch("pygame.mouse.get_pos", return_value=logros_center):
            self.scene.update(0.05)
        for poi_key in STORY_PLAYABLE_POIS:
            self.assertFalse(getattr(self.scene, f"{poi_key}_hover"))

        # Hover en píldora de clima debe activar weather_pill_hovered
        w_center = self.scene.weather_pill_rect.center
        with patch("pygame.mouse.get_pos", return_value=w_center):
            self.scene.update(0.05)
        self.assertTrue(self.scene.weather_pill_hovered)

        # Callout en los 5 POIs jugables (estacionado y renderizado) jamás solapa HUD superior ni bordes
        canvas = pygame.Surface((1920, 1080))
        blocked = self.scene._get_blocked_hud_rects()
        for poi_key in STORY_PLAYABLE_POIS:
            nid = self.scene._get_poi_target_node(poi_key)
            _, _, node_map, _, _ = self.scene._get_street_graph()
            nd = node_map[nid]
            self.scene.player_node_id = nid
            self.scene.player_pos = (float(nd["x"]), float(nd["y"]))
            self.scene.player_is_moving = False
            self.scene.camera.x = max(0.0, min(self.scene.world_w - 1920.0, nd["x"] - 960.0))
            self.scene.camera.y = max(0.0, min(self.scene.world_h - 1080.0, nd["y"] - 540.0))

            with patch("pygame.mouse.get_pos", return_value=(-100, -100)):
                for _ in range(12):
                    self.scene.update(0.05)
            self.scene.render(canvas)

            callout_rect = self.scene.level_preview.last_callout_rect
            self.assertIsNotNone(callout_rect, f"No se renderizó callout en {poi_key}")
            self.assertEqual(self.scene.level_preview.last_poi_key, poi_key)
            for blk in blocked:
                self.assertFalse(
                    callout_rect.colliderect(blk),
                    f"Callout de {poi_key} ({callout_rect}) colisionó con HUD ({blk})",
                )
            self.assertGreaterEqual(callout_rect.left, 0)
            self.assertLessEqual(callout_rect.right, 1920)
            self.assertGreaterEqual(callout_rect.top, 0)
            self.assertLessEqual(callout_rect.bottom, 1080)

    def test_callout_not_shown_on_scenic_pois(self) -> None:
        # Ubicar al jugador sobre un monumento panorámico (mallorquin) sin hover -> sin callout
        nid = self.scene._get_poi_target_node("mallorquin")
        _, _, node_map, _, _ = self.scene._get_street_graph()
        nd = node_map[nid]
        self.scene.player_node_id = nid
        self.scene.player_pos = (float(nd["x"]), float(nd["y"]))
        self.scene.player_is_moving = False
        self.scene.callout_active_poi = None
        self.scene.callout_anim_t = 0.0

        with patch("pygame.mouse.get_pos", return_value=(10, 10)):
            self.scene.update(0.05)
        self.assertIsNone(self.scene.callout_active_poi)
        self.assertEqual(self.scene.callout_anim_t, 0.0)

    def test_quest_card_no_missing_middle_dot_and_cleared_render(self) -> None:
        for pk in STORY_PLAYABLE_POIS:
            info = self.scene.poi_registry[pk]
            self.assertNotIn("\u00b7", info["microgame_title"])
            self.assertNotIn("\u00b7", info["district"])
        # Renderizado en estado DESPEJADO no falla y muestra estado correcto
        self.settings.update_story_progress(completed_microgames=["uninorte_sprint", "uninorte_concentrate"])
        canvas = pygame.Surface((1920, 1080))
        self.scene._open_quest_card("malecon")
        self.scene.quest_card_anim_t = 1.0
        self.scene._render_quest_card(canvas)
        self.assertEqual(self.scene.last_quest_layout_metrics["poi"], "malecon")

    def test_callout_tail_avoids_social_hud_and_hides_when_parked_offscreen(self) -> None:
        canvas = pygame.Surface((1920, 1080))
        blocked = self.scene._get_blocked_hud_rects()
        # Ancla muy cerca debajo del SocialHUD (y=100, SocialHUD bottom=120) -> ni cuerpo ni colita deben tocar HUD
        body_r = self.scene.level_preview.render_callout(
            canvas,
            "buenavista",
            self.scene.poi_registry["buenavista"],
            False,
            (1100, 100),
            blocked,
            1.0,
            0.0,
        )
        tail_r = self.scene.level_preview.last_tail_rect
        self.assertIsNotNone(body_r)
        self.assertIsNotNone(tail_r)
        for blk in blocked:
            self.assertFalse(body_r.colliderect(blk), f"Body {body_r} collided with {blk}")
            self.assertFalse(tail_r.colliderect(blk), f"Tail {tail_r} collided with {blk}")

        # Si el jugador está estacionado en un nodo jugable pero la cámara se arrastra lejos (nodo fuera de pantalla),
        # no debe quedar un callout flotando en una esquina vacía.
        nid = self.scene._get_poi_target_node("uninorte")
        _, _, node_map, _, _ = self.scene._get_street_graph()
        nd = node_map[nid]
        self.scene.player_node_id = nid
        self.scene.player_pos = (float(nd["x"]), float(nd["y"]))
        self.scene.player_is_moving = False
        self.scene.camera.is_dragging = True
        self.scene.camera.x = self.scene.world_w - 1920.0
        self.scene.camera.y = self.scene.world_h - 1080.0
        with patch("pygame.mouse.get_pos", return_value=(1500, 500)):
            for _ in range(12):
                self.scene.update(0.05)
        self.assertIsNone(self.scene.callout_active_poi)
        self.scene.camera.is_dragging = False

    def test_opening_modal_clears_hud_and_weather_hover(self) -> None:
        logros_center = self.scene.social_hud.pills["logros"].rect.center
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": logros_center}))
        self.assertTrue(self.scene.social_hud.pills["logros"].is_hovered)

        w_center = self.scene.weather_pill_rect.center
        with patch("pygame.mouse.get_pos", return_value=w_center):
            self.scene.update(0.05)
        self.assertTrue(self.scene.weather_pill_hovered)

        self.scene._open_quest_card("uninorte")
        self.scene.update(0.2)
        self.assertFalse(self.scene.social_hud.pills["logros"].is_hovered)
        self.assertFalse(self.scene.weather_pill_hovered)

    def test_callout_zero_overlap_building_player_landmarks_all_pois_and_modes(self) -> None:
        canvas = pygame.Surface((1920, 1080))
        _, _, node_map, _, _ = self.scene._get_street_graph()
        blocked = self.scene._get_blocked_hud_rects()

        for poi_key in STORY_PLAYABLE_POIS:
            nid = self.scene._get_poi_target_node(poi_key)
            nd = node_map[nid]
            poi_rect = self.scene.poi_registry[poi_key]["rect"]
            for source_mode in ("parked", "node", "building"):
                self.scene.player_node_id = nid
                self.scene.player_pos = (float(nd["x"]), float(nd["y"]))
                self.scene.player_is_moving = False
                self.scene.camera.x = max(0.0, min(self.scene.world_w - 1920.0, nd["x"] - 960.0))
                self.scene.camera.y = max(0.0, min(self.scene.world_h - 1080.0, nd["y"] - 540.0))
                self.scene.camera.target_x = self.scene.camera.x
                self.scene.camera.target_y = self.scene.camera.y
                self.scene.callout_active_poi = poi_key
                self.scene.callout_anim_t = 1.0
                self.scene.callout_anchor_source = source_mode
                self.scene.level_preview.last_callout_rect = None
                self.scene.level_preview.last_tail_rect = None

                self.scene.render(canvas)
                callout_rect = self.scene.level_preview.last_callout_rect
                self.assertIsNotNone(callout_rect, f"{poi_key} [{source_mode}]: callout no renderizado")

                cam_x = int(self.scene.camera.x)
                cam_y = int(self.scene.camera.y)
                poi_screen = poi_rect.move(-cam_x, -cam_y)
                player_screen = self.scene._get_player_screen_rect(cam_x, cam_y)

                self.assertFalse(
                    callout_rect.colliderect(poi_screen),
                    f"{poi_key} [{source_mode}]: callout {callout_rect} tapó edificio {poi_screen}",
                )
                if player_screen is not None:
                    self.assertFalse(
                        callout_rect.colliderect(player_screen),
                        f"{poi_key} [{source_mode}]: callout {callout_rect} tapó avatar {player_screen}",
                    )
                for other_key, other_info in self.scene.poi_registry.items():
                    if other_key in (poi_key, "batalla_flores"):
                        continue
                    other_screen = other_info["rect"].move(-cam_x, -cam_y)
                    self.assertFalse(
                        callout_rect.colliderect(other_screen),
                        f"{poi_key} [{source_mode}]: callout {callout_rect} tapó {other_key} {other_screen}",
                    )
                for blk in blocked:
                    self.assertFalse(
                        callout_rect.colliderect(blk),
                        f"{poi_key} [{source_mode}]: callout {callout_rect} tapó HUD {blk}",
                    )
                self.assertGreaterEqual(callout_rect.left, 0)
                self.assertLessEqual(callout_rect.right, 1920)
                self.assertGreaterEqual(callout_rect.top, 0)
                self.assertLessEqual(callout_rect.bottom, 1080)

    def test_callout_zero_overlap_corner_hud_edges_and_float_bob(self) -> None:
        import math
        canvas = pygame.Surface((1920, 1080))
        _, _, node_map, _, _ = self.scene._get_street_graph()
        blocked = self.scene._get_blocked_hud_rects()
        # Timers que producen desplazamiento vertical float_y en (-3, 0, +3)
        float_timers = (
            0.0,
            math.pi / (2.0 * 3.8),
            3.0 * math.pi / (2.0 * 3.8),
        )
        edge_cases = [
            ("uninorte", "parked", 480.0, 0.0),
            ("uninorte", "node", 480.0, 140.0),
            ("buenavista", "building", 0.0, 140.0),
            ("buenavista", "building", 160.0, 140.0),
            ("buenavista", "building", 320.0, 140.0),
            ("buenavista", "building", 480.0, 140.0),
            ("metropolitano", "building", 0.0, float(self.scene.world_h - 1080)),
            ("aeropuerto", "building", float(self.scene.world_w - 1920), float(self.scene.world_h - 1080)),
            ("malecon", "building", float(self.scene.world_w - 1920), 0.0),
        ]
        for poi_key, source_mode, cx, cy in edge_cases:
            nid = self.scene._get_poi_target_node(poi_key)
            nd = node_map[nid]
            poi_rect = self.scene.poi_registry[poi_key]["rect"]
            self.scene.player_node_id = nid
            self.scene.player_pos = (float(nd["x"]), float(nd["y"]))
            self.scene.player_is_moving = False
            self.scene.camera.x = cx
            self.scene.camera.y = cy
            self.scene.camera.target_x = cx
            self.scene.camera.target_y = cy
            self.scene.callout_active_poi = poi_key
            self.scene.callout_anim_t = 1.0
            self.scene.callout_anchor_source = source_mode

            for t_val in float_timers:
                self.scene.timer = t_val
                self.scene.level_preview.last_callout_rect = None
                self.scene.render(canvas)
                callout_rect = self.scene.level_preview.last_callout_rect
                self.assertIsNotNone(callout_rect, f"{poi_key} [{source_mode}] ({cx},{cy}) t={t_val:.2f}: no callout")

                cam_x, cam_y = int(cx), int(cy)
                poi_screen = poi_rect.move(-cam_x, -cam_y)
                player_screen = self.scene._get_player_screen_rect(cam_x, cam_y)
                self.assertFalse(
                    callout_rect.colliderect(poi_screen),
                    f"{poi_key} [{source_mode}] ({cx},{cy}) t={t_val:.2f}: tapó edificio {poi_screen} con {callout_rect}",
                )
                if player_screen is not None:
                    self.assertFalse(
                        callout_rect.colliderect(player_screen),
                        f"{poi_key} [{source_mode}] ({cx},{cy}) t={t_val:.2f}: tapó avatar {player_screen} con {callout_rect}",
                    )
                for other_key, other_info in self.scene.poi_registry.items():
                    if other_key in (poi_key, "batalla_flores"):
                        continue
                    other_screen = other_info["rect"].move(-cam_x, -cam_y)
                    self.assertFalse(
                        callout_rect.colliderect(other_screen),
                        f"{poi_key} [{source_mode}] ({cx},{cy}) t={t_val:.2f}: tapó {other_key} {other_screen} con {callout_rect}",
                    )
                for blk in blocked:
                    self.assertFalse(
                        callout_rect.colliderect(blk),
                        f"{poi_key} [{source_mode}] ({cx},{cy}) t={t_val:.2f}: tapó HUD {blk} con {callout_rect}",
                    )
                self.assertGreaterEqual(callout_rect.left, 0)
                self.assertLessEqual(callout_rect.right, 1920)
                self.assertGreaterEqual(callout_rect.top, 0)
                self.assertLessEqual(callout_rect.bottom, 1080)


if __name__ == "__main__":
    unittest.main()
