"""Controles unificados: foco de teclado/mando en menús, stick sin ráfagas, pausa con mando y lapicero visible."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from core import input_state
from core.engine import Engine
from core.microgame import BaseMicrogame
from scenes.main_menu import MainMenuScene


def _key(k):
    return pygame.event.Event(pygame.KEYDOWN, {"key": k, "unicode": "", "mod": 0})


def test_main_menu_keyboard_focus_and_activate():
    pygame.init()
    pygame.display.set_mode((1920, 1080))
    menu = MainMenuScene()
    calls = []
    menu.btn_logros.on_click = lambda: calls.append("logros")

    # Primera flecha: foco en "Jugar"; luego bajar hasta Logros (Jugar, Cargar, Opciones, Logros).
    for _ in range(4):
        menu.handle_event(_key(pygame.K_DOWN))
    assert menu.focus_nav.focused is menu.btn_logros
    assert menu.btn_logros.is_focused
    menu.handle_event(_key(pygame.K_RETURN))
    assert calls == ["logros"]

    # Arriba desde Logros vuelve a Opciones (vecino espacial, no salto aleatorio).
    menu.handle_event(_key(pygame.K_UP))
    assert menu.focus_nav.focused is menu.btn_opciones

    # El render con foco no falla.
    menu.update(0.05)
    menu.render(pygame.Surface((1920, 1080)))


def test_stick_is_edge_triggered_with_keyup():
    engine = Engine(enable_gl=False)
    input_state.clear()
    axis = lambda v: pygame.event.Event(pygame.JOYAXISMOTION, {"axis": 0, "value": v})

    first = engine._translate_joystick_event(axis(0.8))
    assert [(e.type, e.key) for e in first] == [(pygame.KEYDOWN, pygame.K_RIGHT)]
    assert pygame.K_RIGHT in input_state.VIRTUAL_KEYS
    assert input_state.get_pressed()[pygame.K_RIGHT]

    # Vibraciones del stick en la misma dirección no repiten KEYDOWN.
    assert engine._translate_joystick_event(axis(0.9)) == []
    assert engine._translate_joystick_event(axis(0.4)) == []  # histéresis

    released = engine._translate_joystick_event(axis(0.05))
    assert [(e.type, e.key) for e in released] == [(pygame.KEYUP, pygame.K_RIGHT)]
    assert not input_state.get_pressed()[pygame.K_RIGHT]


def test_gamepad_start_opens_microgame_pause_and_button_overrides():
    engine = Engine(enable_gl=False)

    class Dummy(BaseMicrogame):
        GAMEPAD_BUTTON_KEYS = {0: pygame.K_4}

    game = Dummy()
    opened = []
    game.open_pause_menu = lambda: opened.append(True)
    engine.state_machine.change_state(game)

    start = pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 7})
    for evt in engine._translate_joystick_event(start):
        engine._dispatch_event(evt)
    assert opened == [True]

    a_btn = pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0})
    assert [e.key for e in engine._translate_joystick_event(a_btn)] == [pygame.K_4]


class _FakeHand:
    enabled = True

    def __init__(self):
        self.clicks = 1

    def is_hand_present(self):
        return True

    def get_position(self):
        return (0.5, 0.5)

    def consume_click(self):
        had = self.clicks > 0
        self.clicks = 0
        return had


def test_camera_pencil_drawn_on_top_and_not_stealing_gestures():
    engine = Engine(enable_gl=False)
    engine.camera_input = _FakeHand()
    engine.cam_cursor_x, engine.cam_cursor_y = 960.0, 540.0
    engine.state_machine.change_state(MainMenuScene())

    engine._render_current_frame()
    # El halo amarillo del lapicero debe verse encima del menú.
    px = engine.virtual_surface.get_at((960 - 28, 540))
    assert px.r > 200 and px.g > 180, f"lapicero tapado por la escena: {px}"

    class CamGame(BaseMicrogame):
        CAMERA_POINTER = False

    engine.state_machine.change_state(CamGame())
    engine._update_camera_cursor_interaction(0.016)
    assert engine.camera_input.clicks == 1, "el motor robó el pellizco del microjuego"


class _FakeGestureCam:
    enabled = True

    def __init__(self, x=0.5, y=0.5, fist=False, finger=None):
        self.pos = (x, y)
        self.fist = fist
        self.finger = finger
        self.present = True

    def is_hand_present(self):
        return self.present

    def get_position(self):
        return self.pos

    def consume_fist(self):
        had, self.fist = self.fist, False
        return had

    def consume_click(self):
        return False

    def consume_finger(self, i):
        if self.finger == i:
            self.finger = None
            return True
        return False


def test_camera_gestures_drive_keyboard_only_microgames():
    from microgames.aeropuerto_aterrizaje import AeropuertoAterrizajeMicrogame
    from microgames.fritanga_84 import Fritanga84Microgame
    from microgames.ventana_colores import VentanaColoresMicrogame

    pygame.init()
    pygame.display.set_mode((1920, 1080))
    input_state.clear()

    def capture(game):
        seen = []
        original = game.handle_game_event
        game.handle_game_event = lambda e: (seen.append((e.type, e.key)), original(e))
        game.phase = BaseMicrogame.PHASE_PLAY
        return seen

    # Mano a la izquierda -> flecha izquierda sostenida; al volver al centro se suelta.
    plane = AeropuertoAterrizajeMicrogame()
    seen = capture(plane)
    cam = _FakeGestureCam(x=0.1)
    plane.update_camera_actions(cam)
    assert (pygame.KEYDOWN, pygame.K_LEFT) in seen
    assert input_state.get_pressed()[pygame.K_LEFT]
    cam.pos = (0.5, 0.5)
    plane.update_camera_actions(cam)
    assert (pygame.KEYUP, pygame.K_LEFT) in seen
    assert not input_state.get_pressed()[pygame.K_LEFT]

    # Fritanga lee sus gestos propios: el adaptador genérico no los consume.
    from types import SimpleNamespace
    arepa = Fritanga84Microgame()
    calls = []
    arepa.camara = SimpleNamespace(enabled=True, consume_click=lambda: True,
                                  consume_hand_raise=lambda: False)
    arepa.tocarArepa = lambda item: calls.append(item)
    arepa.revisarGestos()
    assert len(calls) == 1
    assert not arepa.CAMERA_ACTIONS

    # Doblar el dedo medio -> tecla 2 (amarillo) en Ventana al Mundo.
    ventana = VentanaColoresMicrogame()
    seen = capture(ventana)
    ventana.update_camera_actions(_FakeGestureCam(finger=1))
    assert (pygame.KEYDOWN, pygame.K_2) in seen

    # Si la mano desaparece, nada queda presionado.
    cam = _FakeGestureCam(x=0.95)
    plane.update_camera_actions(cam)
    cam.present = False
    plane.update_camera_actions(cam)
    assert not input_state.VIRTUAL_KEYS


def test_focused_button_does_not_draw_external_halo():
    from ui.button import UIButton
    pygame.init()
    sprite = pygame.Surface((80, 40), pygame.SRCALPHA)
    sprite.fill((120, 70, 50, 255))
    button = UIButton((100, 60), sprite)
    button.set_focus(True)
    button.shimmer_progress = 2.0
    canvas = pygame.Surface((200, 120), pygame.SRCALPHA)
    button.render(canvas)
    assert canvas.get_bounding_rect() == button.rect


def test_free_play_pagination_launches_new_games_with_keyboard(monkeypatch):
    from scenes.free_play import FreePlayScene
    scene = FreePlayScene()
    ids = [g["id"] for g in scene.games_data]
    # Modo Libre quedó con los 6 juegos principales + Coaster; sin repetidos
    assert len(ids) == len(set(ids)) == 7
    calls = []
    monkeypatch.setattr(scene, "_launch_game", calls.append)
    for game_id in ("punch_alert", "fritanga_84", "coaster"):
        idx = ids.index(game_id)
        scene.current_page = idx // scene.cards_per_page
        scene._rebuild_page_layout()
        scene.selected_card_pos = -1
        scene.handle_event(_key(pygame.K_DOWN))
        for _ in range(idx % scene.cards_per_page):
            scene.handle_event(_key(pygame.K_TAB))
        scene.handle_event(_key(pygame.K_RETURN))
        assert calls[-1] == idx
    scene.render(pygame.Surface((1920, 1080)))


def test_mouse_motion_releases_keyboard_focus():
    from ui.button import UIButton
    from ui.focus_nav import FocusNavigator
    sprite = pygame.Surface((80, 40), pygame.SRCALPHA)
    button = UIButton((100, 60), sprite)
    navigator = FocusNavigator(lambda: [button])
    navigator.handle_event(_key(pygame.K_DOWN))
    assert button.is_focused
    navigator.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (190, 110)}))
    assert not button.is_focused
    button.update(0.1)
    assert button.target_scale == 1.0


def test_curramgram_shows_actual_gamepad_bindings_and_switches_back(monkeypatch):
    from microgames.curramgram_go import CurramGramGoMicrogame
    from microgames.curramgram import interfaz
    engine = Engine(enable_gl=False)
    game = CurramGramGoMicrogame()
    engine.state_machine.change_state(game)
    shown = []
    original = interfaz.boton
    def record(*args, **kwargs):
        shown.append(kwargs.get("control"))
        return original(*args, **kwargs)
    monkeypatch.setattr(interfaz, "boton", record)
    event = pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 2})
    for translated in engine._translate_joystick_event(event):
        engine._dispatch_event(translated)
    game.render_game(pygame.Surface((1920, 1080)))
    assert shown == ["LS", "A", "ABAJO", "X", "B", "Y"]
    assert "[LS]" in game.command_text
    shown.clear()
    engine._dispatch_event(_key(pygame.K_d))
    game.render_game(pygame.Surface((1920, 1080)))
    assert shown == ["A/D", "Esp", "S", "E", "F", "P"]
    input_state.clear()
