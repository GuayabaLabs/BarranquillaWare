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
            # Vecinos cercanos: SPACE no abre nada.
            for n in nodes:
                if n["id"] == entry["id"]:
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


if __name__ == "__main__":
    unittest.main()
