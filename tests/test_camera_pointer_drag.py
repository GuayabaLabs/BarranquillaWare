"""Pruebas de puntero óptico con arrastre/clic sostenido para Heladero y Fritanga."""
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


class _FakeDragCam:
    enabled = True

    def __init__(self, x: float = 0.5, y: float = 0.5) -> None:
        self.pos = (x, y)
        self.present = True
        self.pinching = False
        self._click_edge = False
        self.hand_raised = False

    def set_pinch(self, active: bool) -> None:
        if active and not self.pinching:
            self._click_edge = True
        self.pinching = active

    def is_hand_present(self) -> bool:
        return self.present

    def get_position(self):
        return self.pos

    def is_pinching(self) -> bool:
        return self.present and self.pinching

    def consume_click(self) -> bool:
        had = self._click_edge
        self._click_edge = False
        return had

    def consume_hand_raise(self) -> bool:
        had = self.hand_raised
        self.hand_raised = False
        return had


@pytest.fixture
def isolated_engine(tmp_path, monkeypatch):
    settings = SettingsManager(str(tmp_path / "settings.json"))
    monkeypatch.setattr(SettingsManager, "_instance", settings)
    monkeypatch.setattr(AudioManager, "_instance", None)
    monkeypatch.setattr(CameraGestureInput, "_instance", CameraGestureInput())
    pygame.init()
    pygame.display.set_mode((1920, 1080))
    engine = Engine(enable_gl=False)
    return engine


def _move_cam_to_px(engine: Engine, cam: _FakeDragCam, px: tuple[float, float], steps: int = 8, dt: float = 0.05) -> None:
    cam.pos = (px[0] / engine.VIRTUAL_WIDTH, px[1] / engine.VIRTUAL_HEIGHT)
    for _ in range(steps):
        engine._update_camera_cursor_interaction(dt)


def test_engine_camera_pointer_drag_lifecycle_and_flicker_grace(isolated_engine):
    engine = isolated_engine
    cam = _FakeDragCam()
    engine.camera_input = cam

    events = []

    class DragGame(BaseMicrogame):
        CAMERA_POINTER = True
        CAMERA_POINTER_DRAG = True
        CAMERA_DWELL_CLICK = False

        def handle_game_event(self, event):
            events.append((event.type, getattr(event, "pos", None), getattr(event, "buttons", None), getattr(event, "button", None)))

    game = DragGame()
    game.phase = BaseMicrogame.PHASE_PLAY
    engine.state_machine.change_state(game)

    _move_cam_to_px(engine, cam, (400, 300))
    events.clear()

    # Inicia pellizco -> MOUSEBUTTONDOWN
    cam.set_pinch(True)
    engine._update_camera_cursor_interaction(0.016)
    assert any(e[0] == pygame.MOUSEBUTTONDOWN and e[3] == 1 for e in events)

    # Movimiento con pellizco -> MOUSEMOTION con buttons=(1, 0, 0)
    events.clear()
    _move_cam_to_px(engine, cam, (600, 350), steps=3, dt=0.05)
    motions = [e for e in events if e[0] == pygame.MOUSEMOTION]
    assert motions and all(e[2] == (1, 0, 0) for e in motions)

    # Micro-parpadeo menor al release_delay (0.14s) NO debe soltar
    events.clear()
    cam.set_pinch(False)
    engine._update_camera_cursor_interaction(0.06)
    assert not any(e[0] == pygame.MOUSEBUTTONUP for e in events)

    # Recuperar pellizco reinicia gracia; soltar >= 0.14s emite MOUSEBUTTONUP
    cam.set_pinch(True)
    engine._update_camera_cursor_interaction(0.02)
    cam.set_pinch(False)
    engine._update_camera_cursor_interaction(0.08)
    engine._update_camera_cursor_interaction(0.08)
    assert any(e[0] == pygame.MOUSEBUTTONUP and e[3] == 1 for e in events)

    # Perder la mano durante el drag libera limpiamente con MOUSEBUTTONUP
    events.clear()
    engine.cam_click_cooldown = 0.0
    cam.set_pinch(True)
    engine._update_camera_cursor_interaction(0.016)
    assert any(e[0] == pygame.MOUSEBUTTONDOWN for e in events)
    events.clear()
    cam.present = False
    engine._update_camera_cursor_interaction(0.016)
    assert any(e[0] == pygame.MOUSEBUTTONUP for e in events)


def test_heladero_camera_drag_scrapes_serves_drops_and_delivers(isolated_engine):
    from microgames.heladero_metro import HeladeroMetroMicrogame

    engine = isolated_engine
    cam = _FakeDragCam()
    engine.camera_input = cam

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

    # 1. Raspar en tina 0 (coco)
    tina0 = game.tinas[0]
    _move_cam_to_px(engine, cam, (tina0.left + 25, tina0.centery))
    cam.set_pinch(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.raspando is True
    assert game.sabor == 0

    for offset in (40, 85, 130, 175, 220):
        x = min(tina0.right - 15, tina0.left + offset)
        _move_cam_to_px(engine, cam, (x, tina0.centery), steps=3, dt=0.05)
        game.update(0.05)
    assert game.vueltas >= 0.3

    # Soltar para servir la bola al cono
    cam.set_pinch(False)
    engine._update_camera_cursor_interaction(0.08)
    engine._update_camera_cursor_interaction(0.08)
    assert game.raspando is False
    for _ in range(25):
        game.update(0.05)
    assert len(game.cono) == 1
    assert game.cono[0]["sabor"] == 0

    # 2. Botar cono apuntando a cajaBotar()
    engine.cam_click_cooldown = 0.0
    _move_cam_to_px(engine, cam, game.cajaBotar().center)
    cam.set_pinch(True)
    engine._update_camera_cursor_interaction(0.016)
    cam.set_pinch(False)
    engine._update_camera_cursor_interaction(0.08)
    engine._update_camera_cursor_interaction(0.08)
    assert len(game.cono) == 0

    # 3. Raspar en tina 1 (corozo) y entregar arrastrando el cono al cliente
    engine.cam_click_cooldown = 0.0
    tina1 = game.tinas[1]
    _move_cam_to_px(engine, cam, (tina1.left + 25, tina1.centery))
    cam.set_pinch(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.sabor == 1
    for offset in (40, 90, 140, 190):
        x = min(tina1.right - 15, tina1.left + offset)
        _move_cam_to_px(engine, cam, (x, tina1.centery), steps=3, dt=0.05)
        game.update(0.05)
    cam.set_pinch(False)
    engine._update_camera_cursor_interaction(0.08)
    engine._update_camera_cursor_interaction(0.08)
    for _ in range(25):
        game.update(0.05)
    assert len(game.cono) == 1
    assert game.cono[0]["sabor"] == 1

    # Arrastrar desde cajaCono() a cajaCliente()
    engine.cam_click_cooldown = 0.0
    _move_cam_to_px(engine, cam, game.cajaCono().center)
    cam.set_pinch(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.arrastrandoCono is True
    _move_cam_to_px(engine, cam, game.cajaCliente().center, steps=10, dt=0.05)
    cam.set_pinch(False)
    engine._update_camera_cursor_interaction(0.08)
    engine._update_camera_cursor_interaction(0.08)
    assert game.servidos == 1
    assert game.cono == []


def test_fritanga_camera_drag_flips_specific_arepa_pours_and_delivers(isolated_engine):
    from microgames.fritanga_84 import Fritanga84Microgame

    engine = isolated_engine
    cam = _FakeDragCam()
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

    # Preparar dos arepas libres listas para voltear: la 0 más urgente, la 1 menos urgente
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

    # 1. Apuntar exactamente a a_elegida y pellizcar: voltea esa arepa, no a_urgente
    _move_cam_to_px(engine, cam, (a_elegida["x"], a_elegida["y"]))
    cam.set_pinch(True)
    engine._update_camera_cursor_interaction(0.016)
    cam.set_pinch(False)
    engine._update_camera_cursor_interaction(0.08)
    engine._update_camera_cursor_interaction(0.08)
    assert a_elegida["lado"] == 2
    assert a_urgente["lado"] == 1

    # 2. Servir patillazo manteniendo pellizco en zonaServir() y detener al soltar
    engine.cam_click_cooldown = 0.0
    game.llenado = 0.0
    game.estadoVaso = "listo"
    _move_cam_to_px(engine, cam, game.zonaServir().center)
    cam.set_pinch(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.mouseServir is True
    for _ in range(10):
        game.update(0.05)
    assert game.llenado > 0.35

    cam.set_pinch(False)
    engine._update_camera_cursor_interaction(0.08)
    engine._update_camera_cursor_interaction(0.08)
    assert game.mouseServir is False
    llenado_al_soltar = game.llenado
    game.update(0.05)
    assert game.llenado == pytest.approx(llenado_al_soltar)

    # 3. Arrastrar vaso lleno desde cajaVasoQuieto() hasta cajaCliente()
    engine.cam_click_cooldown = 0.0
    game.llenado = 0.82
    game.estadoVaso = "listo"
    _move_cam_to_px(engine, cam, game.cajaVasoQuieto().center)
    cam.set_pinch(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.estadoVaso == "arrastrando"
    _move_cam_to_px(engine, cam, game.cajaCliente().center, steps=10, dt=0.05)
    cam.set_pinch(False)
    engine._update_camera_cursor_interaction(0.08)
    engine._update_camera_cursor_interaction(0.08)
    assert game.estadoVaso == "entregando"
    assert game.cliente["estado"] == "contento"


def test_fritanga_camera_pours_and_spills_without_auto_delivery(isolated_engine):
    from microgames.fritanga_84 import Fritanga84Microgame

    engine = isolated_engine
    cam = _FakeDragCam()
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

    # 1. Abrir la mano (hand_raise) con vaso lleno NO debe entregar automáticamente
    game.llenado = 0.85
    game.estadoVaso = "listo"
    cam.hand_raised = True
    game.update(0.05)
    assert game.estadoVaso == "listo"
    assert game.cliente["estado"] == "esperando"

    # 2. Mantener pellizco dentro de zonaServir() con jitter > 25px pasado 0.8 NO corta el chorro y SÍ riega el vaso
    game.llenado = 0.0
    game.estadoVaso = "listo"
    zona = game.zonaServir()
    _move_cam_to_px(engine, cam, (zona.centerx - 15, zona.centery))
    cam.set_pinch(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.mouseServir is True

    # Mover > 30 px dentro de zonaServir mientras se llena pasado 0.8 hasta derramar
    for i in range(30):
        dx = 32 if (i % 2 == 0) else -10
        _move_cam_to_px(engine, cam, (zona.centerx + dx, zona.centery), steps=2, dt=0.05)
        game.update(0.05)
        if game.estadoVaso == "regandose":
            break
    assert game.estadoVaso == "regandose"


def test_camera_pointer_does_not_skip_outro_early(isolated_engine):
    engine = isolated_engine
    game = BaseMicrogame()
    game.phase = BaseMicrogame.PHASE_OUTRO
    game.finLetrero = 1.0
    game.outro_timer = 1.7  # > finLetrero + 0.6 (mouse sí puede saltar), < finLetrero + 3.0 (cámara no)
    skipped = []
    game.skip_outro = lambda: skipped.append(True)

    # Clic de cámara temprano no debe volar el final
    game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (500, 500), "button": 1, "camera_pointer": True}))
    assert not skipped

    # Clic de mouse real sí conserva su comportamiento original
    game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (500, 500), "button": 1}))
    assert skipped == [True]
