"""Acceso al mapa por permanencia y mando, sin cámara física."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
import pytest
from core.engine import Engine
from core.settings import SettingsManager
from scenes.story_map import StoryMapScene


class PointerHand:
    enabled = True
    def __init__(self, pos):
        self.pos = pos
    def get_position(self):
        return self.pos[0] / 1920, self.pos[1] / 1080
    def is_hand_present(self):
        return True
    def is_open_palm(self):
        return False
    def consume_fist(self):
        return False
    def consume_click(self):
        return False


@pytest.fixture
def map_engine(monkeypatch):
    monkeypatch.setattr(SettingsManager.get_instance(), "save", lambda: None)
    engine = Engine(enable_gl=False)
    scene = StoryMapScene()
    engine.state_machine.change_state(scene)
    scene.show_intro_dialog = scene.paloma_dialog_open = scene.show_victory_modal = False
    scene.quest_card_open = scene.menu_open = False
    scene.cinematic_timer = scene.cinematic_duration
    return engine, scene


def hover(engine, scene, pos, frames=9):
    engine.camera_input = PointerHand(pos)
    engine.cam_cursor_x, engine.cam_cursor_y = pos
    for _ in range(frames):
        engine._update_camera_cursor_interaction(0.1)
        scene.update(0.1)


def gamepad(engine, button):
    for event_type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
        for event in engine._translate_joystick_event(pygame.event.Event(event_type, {"button": button})):
            engine._dispatch_event(event)


def test_camera_pointer_disabled_in_story_map(map_engine, monkeypatch):
    engine, scene = map_engine
    assert not engine._camera_pointer_allowed()
    clicks = []
    original = scene.handle_event
    def record(event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            clicks.append(event.pos)
        original(event)
    monkeypatch.setattr(scene, "handle_event", record)
    hover(engine, scene, scene.side_drawer._get_tab_rect().center, frames=12)
    assert not scene.side_drawer.is_open
    assert clicks == []
    assert engine.cam_hover_time == 0


@pytest.mark.parametrize("button", [4, 6])
def test_controller_opens_navigates_and_closes_left_drawer(map_engine, button):
    engine, scene = map_engine
    original_node = scene.player_node_id
    gamepad(engine, button)
    assert scene.side_drawer.is_open
    for value in ((0, -1), (0, 0)):
        for event in engine._translate_joystick_event(pygame.event.Event(pygame.JOYHATMOTION, {"value": value})):
            engine._dispatch_event(event)
    gamepad(engine, 0)
    assert scene.side_drawer.seccionActual == "mensajes"
    gamepad(engine, 1)
    assert scene.side_drawer.seccionActual == "botones"
    gamepad(engine, 1)
    assert not scene.side_drawer.is_open
    assert not scene.menu_open
    assert scene.player_node_id == original_node
    assert not scene.player_is_moving


def test_empty_terrain_does_not_accumulate_camera_clicks(map_engine, monkeypatch):
    engine, scene = map_engine
    point = next((x, y) for x in range(550, 1500, 100) for y in range(350, 950, 100)
                 if scene.camera_dwell_target((x, y)) is None)
    clicks = []
    original = scene.handle_event
    def record(event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            clicks.append(event.pos)
        original(event)
    monkeypatch.setattr(scene, "handle_event", record)
    hover(engine, scene, point, frames=20)
    assert clicks == []
    assert engine.cam_hover_time == 0


def test_achievement_popup_closes_with_gamepad(map_engine):
    engine, scene = map_engine
    # Mando: botón X / A / B cierra el aviso.
    scene.avisoTrofeo.abrir("Logro", (24, 584))
    assert scene.avisoTrofeo.abierto
    scene.handle_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 2}))
    assert not scene.avisoTrofeo.abierto


def test_piano_renders_gamepad_button_prompts():
    from microgames.buenavista_trend.game import BuenavistaTrendMicrogame
    game = BuenavistaTrendMicrogame()
    game.phase = game.PHASE_PLAY
    surface = pygame.Surface((1920, 1080))
    game.render(surface)
    assert hasattr(game, "fuenteMando")
