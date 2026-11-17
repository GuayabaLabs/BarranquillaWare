"""Cada nivel del mapa solo se abre desde su nodo amarillo oficial, nunca desde un vecino."""
import math
import os
import sys
import unittest

import pygame

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from core.settings import SettingsManager
from scenes.story_map.scene import StoryMapScene
from scenes.story_map_data import STORY_PLAYABLE_POIS


class TestStoryMapEntryNodes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        SettingsManager.get_instance().reset_story_progress()
        cls.scene = StoryMapScene(character_id="shakira")

    def _park(self, nid: int) -> None:
        _, _, node_map, _, _ = self.scene._get_street_graph()
        nd = node_map[nid]
        self.scene.player_node_id = nid
        self.scene.player_pos = (float(nd["x"]), float(nd["y"]))
        self.scene.player_is_moving = False
        self.scene.paloma_dialog_open = False
        self.scene.quest_card_open = False
        self.scene.active_poi = None

    def test_fixed_entry_nodes_are_yellow_and_unique(self) -> None:
        stop_map = self.scene._get_playable_stop_node_map()
        for poi in STORY_PLAYABLE_POIS:
            nid = self.scene._get_poi_target_node(poi)
            self.assertEqual(nid, StoryMapScene.POI_ENTRY_NODES[poi], poi)
            self.assertEqual(stop_map.get(nid), poi)
        self.assertEqual(len(stop_map), len(STORY_PLAYABLE_POIS))

    def test_only_official_node_opens_level(self) -> None:
        nodes, _, node_map, _, _ = self.scene._get_street_graph()
        for poi in STORY_PLAYABLE_POIS:
            entry = node_map[self.scene._get_poi_target_node(poi)]
            # Nodo oficial: SPACE abre el nivel.
            self._park(entry["id"])
            self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
            self.assertEqual(self.scene.active_poi, poi, f"{poi}: no abrió desde su nodo")
            # Vecinos sin entrada propia: SPACE no abre nada.
            for n in nodes:
                if n["id"] in self.scene._get_playable_stop_node_map():
                    continue
                if math.hypot(n["x"] - entry["x"], n["y"] - entry["y"]) > 250:
                    continue
                self._park(n["id"])
                self.assertIsNone(self.scene._get_active_entry_poi(), f"{poi}: nodo {n['id']} activa entrada")
                self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
                self.assertFalse(
                    self.scene.paloma_dialog_open or self.scene.quest_card_open,
                    f"{poi}: nodo vecino {n['id']} abrió el nivel",
                )



class _PalmCam:
    enabled = True

    def __init__(self, x, y, palm=True, fist=False):
        self.pos, self.palm, self.fist = (x, y), palm, fist

    def is_hand_present(self):
        return True

    def get_position(self):
        return self.pos

    def is_open_palm(self):
        return self.palm

    def consume_fist(self):
        had, self.fist = self.fist, False
        return had


class TestStoryMapCameraWalk(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        SettingsManager.get_instance().reset_story_progress()
        cls.scene = StoryMapScene(character_id="shakira")

    def test_open_palm_walks_one_node_and_fist_enters(self):
        scene = self.scene
        _, _, node_map, adj, _ = scene._get_street_graph()
        start = scene._get_poi_target_node("metropolitano")
        nd = node_map[start]
        scene.player_node_id, scene.player_pos, scene.player_is_moving = start, (float(nd["x"]), float(nd["y"])), False
        scene.quest_card_open = scene.paloma_dialog_open = scene.menu_open = False

        # Mano quieta en el centro o con el índice (sin palma): no camina.
        scene.update_camera_walk(_PalmCam(0.5, 0.5), 1.0)
        scene.update_camera_walk(_PalmCam(0.95, 0.5, palm=False), 1.0)
        self.assertFalse(scene.player_is_moving)

        # Puño sobre el nodo amarillo: entra al nivel.
        scene.update_camera_walk(_PalmCam(0.5, 0.5, palm=False, fist=True), 0.016)
        self.assertEqual(scene.active_poi, "metropolitano")
        scene.quest_card_open = scene.paloma_dialog_open = False

        # Palma abierta hacia un lado, sostenida: inicia viaje a un nodo vecino.
        moved = False
        for cam in (_PalmCam(0.95, 0.5), _PalmCam(0.05, 0.5), _PalmCam(0.5, 0.95), _PalmCam(0.5, 0.05)):
            scene.player_is_moving = False
            scene._cam_walk_t = 0.0
            scene.update_camera_walk(cam, 0.2)
            self.assertFalse(scene.player_is_moving, "no debe avanzar antes de sostener la palma")
            scene.update_camera_walk(cam, 0.3)
            if scene.player_is_moving:
                moved = True
                break
        self.assertTrue(moved)
        self.assertFalse(StoryMapScene.CAMERA_DWELL_CLICK)


if __name__ == "__main__":
    unittest.main()
