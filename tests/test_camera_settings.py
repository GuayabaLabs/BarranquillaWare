"""Preferencia persistente de cámara, controles de Opciones y cobertura de juegos."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
import pytest
from core.settings import SettingsManager
from core.camera_gestures import CameraGestureInput
from core.map_settings import MapSettingsState
from core.engine import Engine
from core.audio_manager import AudioManager
from core import input_state


@pytest.fixture
def camera_settings(tmp_path, monkeypatch):
    settings = SettingsManager(str(tmp_path / "settings.json"))
    monkeypatch.setattr(SettingsManager, "_instance", settings)
    monkeypatch.setattr(AudioManager, "_instance", None)
    camera = CameraGestureInput()
    monkeypatch.setattr(CameraGestureInput, "_instance", camera)
    return settings, camera


def test_disabled_camera_is_saved_and_cannot_restart(camera_settings, monkeypatch):
    settings, camera = camera_settings
    camera.enabled = True
    camera.set_enabled(False)
    assert not camera.enabled
    assert camera.suspended
    assert SettingsManager(settings.filepath).get("camera_enabled") is False
    monkeypatch.delenv("SDL_VIDEODRIVER", raising=False)
    monkeypatch.setattr("core.camera_gestures.HAVE_CAMERA", True)
    monkeypatch.setattr("core.camera_gestures.threading.Thread", lambda **kw: pytest.fail("Cámara desactivada abrió un hilo"))
    assert camera.start() is False
    assert camera.resume() is False
    camera.keep_alive()
    assert camera._thread is None


def test_options_mouse_toggles_camera_and_help_is_clickable(camera_settings):
    settings, camera = camera_settings
    pygame.init()
    pygame.display.set_mode((1920, 1080))
    options = MapSettingsState()
    canvas = pygame.Surface((1920, 1080))
    options.render(canvas)
    for item in ("camera", "camera_help"):
        pos = options._row_rects[options.items.index(item)].center
        assert options.camera_dwell_target(pos) is not None
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            options.handle_event(pygame.event.Event(kind, {"pos": pos, "button": 1}))
    assert settings.get("camera_enabled") is False
    assert options.show_camera_help
    options.render(canvas)
    options.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT}))
    assert options.camera_help_page == 1
    options.render(canvas)
    options.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
    assert not options.show_camera_help


def test_controller_activation_is_not_delivered_twice(camera_settings):
    settings, camera = camera_settings
    engine = Engine(enable_gl=False)
    options = MapSettingsState()
    engine.state_machine.change_state(options)
    options.index = options.items.index("camera")
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0}))
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": 0}))
    assert settings.get("camera_enabled") is False
    index = options.index
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYHATMOTION, {"value": (0, -1)}))
    assert options.index == index + 1
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYHATMOTION, {"value": (0, 0)}))
    assert not input_state.VIRTUAL_KEYS


def test_camera_help_covers_every_arcade_game(camera_settings):
    from core.camera_controls import CAMERA_CONTROL_GUIDE
    from scenes.arcade_mode import ArcadeModeScene
    pygame.init()
    pygame.display.set_mode((1920, 1080))
    covered = {name for name, _, _ in CAMERA_CONTROL_GUIDE}
    scene = ArcadeModeScene()
    assert {cls.__name__ for cls in scene.microgame_pool} <= covered
    assert {"CoasterLauncherState", "BatallaFloresBossMicrogame"} <= covered


def test_curramgram_camera_can_move_hide_avisar_and_publish(camera_settings, monkeypatch):
    from types import SimpleNamespace
    from microgames.curramgram_go import CurramGramGoMicrogame
    game = CurramGramGoMicrogame()
    game.phase = game.PHASE_PLAY
    seen = []
    monkeypatch.setattr(game, "handle_game_event", lambda event: seen.append((event.type, event.key)))
    cam = SimpleNamespace(enabled=True, is_hand_present=lambda: True,
                          get_position=lambda: (0.95, 0.95), consume_fist=lambda: False,
                          consume_click=lambda: False, consume_finger=lambda index: index == 0)
    game.update_camera_actions(cam)
    assert (pygame.KEYDOWN, pygame.K_RIGHT) in seen
    assert (pygame.KEYDOWN, pygame.K_s) in seen
    assert (pygame.KEYDOWN, pygame.K_e) in seen
    cam.consume_finger = lambda index: index == 1
    game.update_camera_actions(cam)
    assert (pygame.KEYDOWN, pygame.K_p) in seen
    cam.enabled = False
    game.update_camera_actions(cam)
    assert (pygame.KEYUP, pygame.K_RIGHT) in seen
    assert (pygame.KEYUP, pygame.K_s) in seen
    input_state.clear()


def test_rapid_toggle_does_not_start_two_camera_threads(camera_settings, monkeypatch):
    from types import SimpleNamespace
    settings, camera = camera_settings
    worker = SimpleNamespace(is_alive=lambda: True, join=lambda **kw: None)
    camera._thread = worker
    camera.stop()
    assert camera._thread is worker
    monkeypatch.delenv("SDL_VIDEODRIVER", raising=False)
    monkeypatch.setattr("core.camera_gestures.HAVE_CAMERA", True)
    assert camera.start() is False
