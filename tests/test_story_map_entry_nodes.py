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
        cls.scene = StoryMapScene(character_id="valdiri")

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

    def __init__(self, x, y, palm=True, fist=False, pinch=False, pointing=None):
        self.pos, self.palm, self.fist, self.pinch, self.pointing = (x, y), palm, fist, pinch, pointing

    def is_hand_present(self):
        return True

    def get_position(self):
        return self.pos

    def is_open_palm(self):
        return self.palm

    def is_pinching(self):
        return self.pinch

    def get_pointing_direction(self):
        return self.pointing

    def consume_fist(self):
        had, self.fist = self.fist, False
        return had


class TestStoryMapCameraWalk(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        SettingsManager.get_instance().reset_story_progress()
        cls.scene = StoryMapScene(character_id="valdiri")

    def test_camera_walk_and_pointer_disabled(self):
        from core.engine import Engine
        scene = self.scene
        self.assertFalse(hasattr(scene, "update_camera_walk"))
        self.assertFalse(hasattr(scene, "_cancel_camera_walk"))
        self.assertFalse(hasattr(scene, "_render_camera_walk_hint"))
        self.assertFalse(StoryMapScene.CAMERA_POINTER)
        self.assertFalse(StoryMapScene.CAMERA_DWELL_CLICK)

        engine = Engine(enable_gl=False)
        for cls_name in (
            "StoryMapScene",
            "MainMenuScene",
            "ModeSelectScene",
            "CharacterSelectScene",
            "LoadGameScene",
            "FreePlayScene",
            "ArcadeModeScene",
            "MapSettingsState",
        ):
            dummy_state = type(
                cls_name,
                (),
                {"enter": lambda self, params=None: None, "exit": lambda self: None},
            )()
            engine.state_machine.change_state(dummy_state)
            self.assertFalse(engine._camera_pointer_allowed(), f"Se permitió puntero en {cls_name}")

    def test_intermediate_stage_shows_fast_result_banner(self):
        from core.state_machine import StateMachine
        scene = self.scene
        scene.state_machine = StateMachine()
        scene.active_poi = "uninorte"
        scene.current_level_stage_idx = 0
        scene._launch_microgame()
        mg = scene.state_machine.current_state
        self.assertTrue(mg.show_outro_banner)
        self.assertFalse(getattr(mg, "skip_outro_story_card", False))
        self.assertAlmostEqual(mg.outro_duration, 1.25)
        mg.finish_game(True)
        self.assertIsNotNone(getattr(mg, "letreroResultado", None))
        self.assertGreaterEqual(mg.outro_duration, 4.0)


if __name__ == "__main__":
    unittest.main()
