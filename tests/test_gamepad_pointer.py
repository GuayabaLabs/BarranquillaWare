"""Pruebas de puntero virtual controlado por joystick/gamepad en Engine, Heladero y Fritanga."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from core.engine import Engine
from core.microgame import BaseMicrogame
from core.settings import SettingsManager
from core.audio_manager import AudioManager
from core.camera_gestures import CameraGestureInput
from core import input_state


@pytest.fixture
def isolated_engine(tmp_path, monkeypatch):
    settings = SettingsManager(str(tmp_path / "settings.json"))
    monkeypatch.setattr(SettingsManager, "_instance", settings)
    monkeypatch.setattr(AudioManager, "_instance", None)
    monkeypatch.setattr(CameraGestureInput, "_instance", CameraGestureInput())
    pygame.init()
    pygame.display.set_mode((1920, 1080))
    engine = Engine(enable_gl=False)
    input_state.clear()
    return engine


def _move_joy_to_px(engine: Engine, target: tuple[float, float], update_game=None) -> None:
    """Mueve el cursor virtual del joystick hacia `target` emitiendo eventos reales de eje."""
    for _ in range(120):
        dx = target[0] - engine.joy_cursor_x
        dy = target[1] - engine.joy_cursor_y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 12.0:
            break
        ax = max(-1.0, min(1.0, dx / 250.0))
        ay = max(-1.0, min(1.0, dy / 250.0))
        if abs(ax) < 0.25 and abs(dx) >= 4.0:
            ax = 0.35 if dx > 0 else -0.35
        if abs(ay) < 0.25 and abs(dy) >= 4.0:
            ay = 0.35 if dy > 0 else -0.35
        engine._dispatch_input_event(pygame.event.Event(pygame.JOYAXISMOTION, {"axis": 0, "value": ax}))
        engine._dispatch_input_event(pygame.event.Event(pygame.JOYAXISMOTION, {"axis": 1, "value": ay}))
        engine._update_gamepad_cursor_interaction(0.05)
        if update_game is not None:
            update_game(0.05)
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYAXISMOTION, {"axis": 0, "value": 0.0}))
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYAXISMOTION, {"axis": 1, "value": 0.0}))
    engine._update_gamepad_cursor_interaction(0.016)


def test_engine_gamepad_pointer_lifecycle_and_outro_release(isolated_engine):
    engine = isolated_engine
    events = []

    class JoyPointerGame(BaseMicrogame):
        GAMEPAD_POINTER = True

        def handle_game_event(self, event):
            events.append((
                event.type,
                getattr(event, "pos", None),
                getattr(event, "buttons", None),
                getattr(event, "button", None),
                getattr(event, "gamepad_pointer", False),
            ))

    game = JoyPointerGame()
    game.phase = BaseMicrogame.PHASE_PLAY
    engine.state_machine.change_state(game)

    # Mover eje X/Y -> mueve el cursor y emite MOUSEMOTION con gamepad_pointer=True
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYAXISMOTION, {"axis": 0, "value": 0.9}))
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYAXISMOTION, {"axis": 1, "value": 0.0}))
    engine._update_gamepad_cursor_interaction(0.05)
    motions = [e for e in events if e[0] == pygame.MOUSEMOTION]
    assert motions and motions[-1][4] is True and motions[-1][2] == (0, 0, 0)
    assert input_state.is_gamepad_active()
    engine._render_gamepad_cursor(engine.virtual_surface)

    # Botón A presionado -> MOUSEBUTTONDOWN
    events.clear()
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0}))
    assert any(e[0] == pygame.MOUSEBUTTONDOWN and e[3] == 1 and e[4] is True for e in events)

    # Mover con A sostenido -> MOUSEMOTION con buttons=(1, 0, 0)
    events.clear()
    engine._update_gamepad_cursor_interaction(0.05)
    motions = [e for e in events if e[0] == pygame.MOUSEMOTION]
    assert motions and all(e[2] == (1, 0, 0) for e in motions)

    # Soltar A -> MOUSEBUTTONUP
    events.clear()
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": 0}))
    assert any(e[0] == pygame.MOUSEBUTTONUP and e[3] == 1 and e[4] is True for e in events)

    # Entrar a PHASE_OUTRO con A sostenido libera limpiamente el drag
    seen_outro = []
    orig_handle_event = game.handle_event
    game.handle_event = lambda ev: (seen_outro.append(ev), orig_handle_event(ev))
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0}))
    assert engine._joy_pointer_down is True
    game.phase = BaseMicrogame.PHASE_OUTRO
    engine._update_gamepad_cursor_interaction(0.016)
    assert engine._joy_pointer_down is False
    assert any(ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 for ev in seen_outro)


def test_heladero_gamepad_pointer_scrapes_serves_drops_and_delivers(isolated_engine):
    from microgames.heladero_metro import HeladeroMetroMicrogame

    engine = isolated_engine
    game = HeladeroMetroMicrogame()
    game.phase = BaseMicrogame.PHASE_PLAY
    game.introHecha = True
    game.escena = None
    game.decision = None
    game.postAbierto = None
    game.cualPost = 1
    game.desdeUltimoPost = 0.0
    game.cliente = {"tipo": 0, "pedido": [0], "estado": "esperando", "paciencia": 25.0, "t": 0.0, "esCompanero": False}
    engine.state_machine.change_state(game)

    # 1. Mover stick a tina 0, mantener A y mover stick para raspar
    tina0 = game.tinas[0]
    _move_joy_to_px(engine, (tina0.left + 25, tina0.centery))
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0}))
    assert game.raspando is True and game.sabor == 0
    _move_joy_to_px(engine, (tina0.right - 20, tina0.centery), update_game=game.update)
    assert game.vueltas >= 0.3

    # Soltar A -> sirve la bola al cono
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": 0}))
    for _ in range(25):
        game.update(0.05)
    assert len(game.cono) == 1

    # 2. Botón B (1) -> bota el cono (K_b)
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 1}))
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": 1}))
    assert game.cono == []

    # 3. Volver a servir bola y arrastrar cono con stick + A hasta el cliente
    _move_joy_to_px(engine, (tina0.left + 25, tina0.centery))
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0}))
    _move_joy_to_px(engine, (tina0.right - 20, tina0.centery), update_game=game.update)
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": 0}))
    for _ in range(25):
        game.update(0.05)
    assert len(game.cono) == 1

    _move_joy_to_px(engine, game.cajaCono().center)
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0}))
    assert game.arrastrandoCono is True
    _move_joy_to_px(engine, game.cajaCliente().center, update_game=game.update)
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": 0}))
    assert game.servidos == 1
    assert game.cono == []


def test_fritanga_gamepad_pointer_flips_spills_and_delivers(isolated_engine):
    from microgames.fritanga_84 import Fritanga84Microgame

    engine = isolated_engine
    game = Fritanga84Microgame(character_id="westcol")
    game.phase = BaseMicrogame.PHASE_PLAY
    game.tutorialPendiente = False
    game.tutorial = None
    game.escribiendo = 0.0
    game.trol["estado"] = "calma"
    game.cliente = {"cual": 0, "estado": "esperando", "tiempo": 0.0, "paciencia": 12.0}
    engine.state_machine.change_state(game)

    a_urgente, a_elegida = game.arepas[0], game.arepas[1]
    for a in game.arepas:
        a["entrada"] = 1.0
        a["volteo"] = 0.0
        a["sacando"] = 0.0
        a["quemada"] = 0.0
        a["seVuela"] = 0.0
        a["lado"] = 1
        a["coccion"] = 0.2
    a_urgente["coccion"] = 0.85
    a_elegida["coccion"] = 0.65

    # 1. Apuntar con stick a a_elegida (menos urgente) y pulsar A -> voltea solo esa arepa
    _move_joy_to_px(engine, (a_elegida["x"], a_elegida["y"]))
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0}))
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": 0}))
    assert a_elegida["lado"] == 2
    assert a_urgente["lado"] == 1

    # 2. Mantener A dentro de zonaServir() con leve movimiento -> sigue llenando y se riega
    game.llenado = 0.0
    game.estadoVaso = "listo"
    zona = game.zonaServir()
    _move_joy_to_px(engine, (zona.centerx - 15, zona.centery))
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0}))
    assert game.mouseServir is True
    for i in range(30):
        engine.joy_cursor_x = float(zona.centerx + (25 if i % 2 == 0 else -15))
        engine._update_gamepad_cursor_interaction(0.05)
        game.update(0.05)
        if game.estadoVaso == "regandose":
            break
    assert game.estadoVaso == "regandose"
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": 0}))

    # 3. Arrastrar vaso lleno con stick + A desde cajaVasoQuieto() hasta cajaCliente()
    game.llenado = 0.82
    game.estadoVaso = "listo"
    _move_joy_to_px(engine, game.cajaVasoQuieto().center)
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0}))
    assert game.estadoVaso == "arrastrando"
    _move_joy_to_px(engine, game.cajaCliente().center, update_game=game.update)
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": 0}))
    assert game.estadoVaso == "entregando"
    assert game.cliente["estado"] == "contento"


def test_fritanga_gamepad_keeps_standard_rules_even_with_camera_enabled(isolated_engine):
    from microgames.fritanga_84 import Fritanga84Microgame

    class _PassiveActiveCam:
        enabled = True
        def is_hand_present(self): return True
        def get_position(self): return (0.5, 0.5)
        def is_pinching(self): return False
        def consume_click(self): return False
        def consume_hand_raise(self): return False

    engine = isolated_engine
    cam = _PassiveActiveCam()
    engine.camera_input = cam

    game = Fritanga84Microgame(character_id="westcol")
    game.camara = cam
    game.phase = BaseMicrogame.PHASE_PLAY
    game.tutorialPendiente = False
    game.tutorial = None
    game.escribiendo = 0.0
    game.trol["estado"] = "calma"
    game.cliente = {"cual": 0, "estado": "esperando", "tiempo": 0.0, "paciencia": 12.0}
    engine.state_machine.change_state(game)

    # Aunque la cámara esté activa y haya mano de fondo, el puntero pasivo NO activa ayudas
    engine._update_camera_cursor_interaction(0.05)

    # Jugar con mando mantiene velocidad 1.0x de cocción (incluso si antes hubo interacción de cámara)
    game._control_camara_activo = True
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYAXISMOTION, {"axis": 0, "value": 0.4}))
    assert input_state.is_gamepad_active() is True
    assert game._camara_es_control_activo() is False

    a0 = game.arepas[0]
    a0["entrada"] = 1.0
    a0["volteo"] = 0.0
    a0["sacando"] = 0.0
    a0["quemada"] = 0.0
    a0["seVuela"] = 0.0
    a0["lado"] = 1
    a0["coccion"] = 1.05
    a0["velocidad"] = 0.20
    game.update_game(0.10)
    assert a0["coccion"] == pytest.approx(1.05 + 0.20 * 0.10, abs=1e-5)

    # Hitbox de arepa con mando sigue estricto (sin snap de cámara)
    a0["coccion"] = 0.85
    punto_desviado = (a0["x"] - 108, a0["y"])
    assert game.arepaEn(punto_desviado, es_camara=True) is a0
    engine.joy_cursor_x, engine.joy_cursor_y = punto_desviado
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0}))
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": 0}))
    assert a0["lado"] == 1

    # Llenado de patillazo con mando sobre 0.80 mantiene tasa normal 0.85/s (sin x0.55)
    game.llenado = 0.82
    game.estadoVaso = "listo"
    zona = game.zonaServir()
    engine.joy_cursor_x, engine.joy_cursor_y = zona.center
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0}))
    assert game.mouseServir is True and game._servir_por_camara is False
    antes = game.llenado
    game.update(0.10)
    assert game.llenado - antes == pytest.approx(0.85 * 0.10, abs=1e-4)
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": 0}))

    # Suelta con mando fuera de cajaCliente().inflate(120, 160) devuelve el vaso (sin zona amplia de cámara)
    game.llenado = 0.88
    game.estadoVaso = "listo"
    engine.joy_cursor_x, engine.joy_cursor_y = game.cajaVasoQuieto().center
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 0}))
    assert game.estadoVaso == "arrastrando" and game._arrastre_por_camara is False
    engine.joy_cursor_x, engine.joy_cursor_y = (1290.0, 200.0)
    engine._update_gamepad_cursor_interaction(0.016)
    engine._dispatch_input_event(pygame.event.Event(pygame.JOYBUTTONUP, {"button": 0}))
    assert game.estadoVaso == "volviendo"
    assert game.cliente["estado"] == "esperando"
