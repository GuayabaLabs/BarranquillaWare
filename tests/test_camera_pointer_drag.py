"""Pruebas de puntero óptico con arrastre/clic sostenido para Heladero y Fritanga."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from typing import Optional
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
        self.palm_pos: Optional[tuple[float, float]] = None
        self.present = True
        self.pinching = False
        self._click_edge = False
        self.fist = False
        self._fist_edge = False
        self.hand_raised = False

    def set_pinch(self, active: bool) -> None:
        if active and not self.pinching:
            self._click_edge = True
        self.pinching = active

    def set_fist(self, active: bool) -> None:
        if active and not self.fist:
            self._fist_edge = True
        self.fist = active

    def is_hand_present(self) -> bool:
        return self.present

    def get_position(self):
        return self.pos

    def get_palm_position(self):
        return self.pos if self.palm_pos is None else self.palm_pos

    def is_pinching(self) -> bool:
        return self.present and self.pinching

    def is_fist(self) -> bool:
        return self.present and self.fist

    def consume_click(self) -> bool:
        had = self._click_edge
        self._click_edge = False
        return had

    def consume_fist(self) -> bool:
        had = self._fist_edge
        self._fist_edge = False
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
    current = engine.state_machine.current_state
    margin = max(0.0, min(0.25, float(getattr(current, "CAMERA_POINTER_MARGIN", 0.0))))
    nx = px[0] / engine.VIRTUAL_WIDTH
    ny = px[1] / engine.VIRTUAL_HEIGHT
    if margin > 0.0:
        nx = margin + nx * (1.0 - 2.0 * margin)
        ny = margin + ny * (1.0 - 2.0 * margin)
    cam.pos = (nx, ny)
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

    assert HeladeroMetroMicrogame.CAMERA_POINTER_ANCHOR == "palm"
    assert HeladeroMetroMicrogame.CAMERA_POINTER_GESTURE == "fist"
    assert HeladeroMetroMicrogame.CAMERA_POINTER_RING_RADIUS == 84
    assert HeladeroMetroMicrogame.CAMERA_POINTER_MARGIN == pytest.approx(0.20)

    # 1. Rango ampliado + indicador AoE + raspar en tina 0 (coco) con puño cerrado
    tina0 = game.tinas[0]
    assert game.camera_has_target(tina0.center) is True
    assert game.camera_has_target((200, 200)) is False
    borde_tina0 = (tina0.left - 25, tina0.centery)
    assert game.tinaEn(borde_tina0, es_camara=False) is None
    assert game.tinaEn(borde_tina0, es_camara=True) == 0

    _move_cam_to_px(engine, cam, (tina0.left + 25, tina0.centery))
    cam.set_fist(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.raspando is True
    assert game.sabor == 0

    for offset in (40, 85, 130, 175, 220):
        x = min(tina0.right - 15, tina0.left + offset)
        _move_cam_to_px(engine, cam, (x, tina0.centery), steps=3, dt=0.05)
        game.update(0.05)
    assert game.vueltas >= 0.3

    # Abrir mano -> sirve la bola al cono
    cam.set_fist(False)
    engine._update_camera_cursor_interaction(0.05)
    engine._update_camera_cursor_interaction(0.05)
    assert game.raspando is False
    for _ in range(25):
        game.update(0.05)
    assert len(game.cono) == 1
    assert game.cono[0]["sabor"] == 0

    # 2. Botar cono apuntando a cajaBotar() con puño
    engine.cam_click_cooldown = 0.0
    _move_cam_to_px(engine, cam, game.cajaBotar().center)
    cam.set_fist(True)
    engine._update_camera_cursor_interaction(0.016)
    cam.set_fist(False)
    engine._update_camera_cursor_interaction(0.05)
    engine._update_camera_cursor_interaction(0.05)
    assert len(game.cono) == 0

    # 3. Raspar en tina 1 (corozo) y entregar arrastrando el cono al cliente con puño
    engine.cam_click_cooldown = 0.0
    tina1 = game.tinas[1]
    _move_cam_to_px(engine, cam, (tina1.left + 25, tina1.centery))
    cam.set_fist(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.sabor == 1
    for offset in (40, 90, 140, 190):
        x = min(tina1.right - 15, tina1.left + offset)
        _move_cam_to_px(engine, cam, (x, tina1.centery), steps=3, dt=0.05)
        game.update(0.05)
    cam.set_fist(False)
    engine._update_camera_cursor_interaction(0.05)
    engine._update_camera_cursor_interaction(0.05)
    for _ in range(25):
        game.update(0.05)
    assert len(game.cono) == 1
    assert game.cono[0]["sabor"] == 1

    # Arrastrar desde cajaCono() a cajaCliente()
    engine.cam_click_cooldown = 0.0
    _move_cam_to_px(engine, cam, game.cajaCono().center)
    cam.set_fist(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.arrastrandoCono is True
    _move_cam_to_px(engine, cam, game.cajaCliente().center, steps=10, dt=0.05)
    cam.set_fist(False)
    engine._update_camera_cursor_interaction(0.05)
    engine._update_camera_cursor_interaction(0.05)
    assert game.servidos == 1
    assert game.cono == []

    # 4. Entrega directa cerrando el puño sobre el cliente con cono listo
    engine.cam_click_cooldown = 0.0
    game.cono = [{"sabor": 0, "calidad": 1.0}]
    game.cliente = {"tipo": 0, "pedido": [0], "estado": "esperando", "paciencia": 25.0, "t": 0.0, "esCompanero": False}
    assert game.camera_has_target(game.cajaCliente().center) is True
    _move_cam_to_px(engine, cam, game.cajaCliente().center)
    cam.set_fist(True)
    engine._update_camera_cursor_interaction(0.016)
    cam.set_fist(False)
    engine._update_camera_cursor_interaction(0.05)
    engine._update_camera_cursor_interaction(0.05)
    for _ in range(15):
        game.update(0.05)
    assert game.servidos == 2
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

    # 1. Apuntar exactamente a a_elegida y cerrar puño: voltea esa arepa, no a_urgente
    _move_cam_to_px(engine, cam, (a_elegida["x"], a_elegida["y"]))
    cam.set_fist(True)
    engine._update_camera_cursor_interaction(0.016)
    cam.set_fist(False)
    engine._update_camera_cursor_interaction(0.05)
    engine._update_camera_cursor_interaction(0.05)
    assert a_elegida["lado"] == 2
    assert a_urgente["lado"] == 1

    # 2. Servir patillazo manteniendo puño en zonaServir() y detener al abrir mano
    engine.cam_click_cooldown = 0.0
    game.llenado = 0.0
    game.estadoVaso = "listo"
    _move_cam_to_px(engine, cam, game.zonaServir().center)
    cam.set_fist(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.mouseServir is True
    for _ in range(10):
        game.update(0.05)
    assert game.llenado > 0.35

    cam.set_fist(False)
    engine._update_camera_cursor_interaction(0.05)
    engine._update_camera_cursor_interaction(0.05)
    assert game.mouseServir is False
    llenado_al_soltar = game.llenado
    game.update(0.05)
    assert game.llenado == pytest.approx(llenado_al_soltar)

    # 3. Arrastrar vaso lleno desde cajaVasoQuieto() hasta cajaCliente()
    engine.cam_click_cooldown = 0.0
    game.llenado = 0.82
    game.estadoVaso = "listo"
    _move_cam_to_px(engine, cam, game.cajaVasoQuieto().center)
    cam.set_fist(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.estadoVaso == "arrastrando"
    _move_cam_to_px(engine, cam, game.cajaCliente().center, steps=10, dt=0.05)
    cam.set_fist(False)
    engine._update_camera_cursor_interaction(0.05)
    engine._update_camera_cursor_interaction(0.05)
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

    # 2. Mantener puño dentro de zonaServir() con jitter > 25px pasado 0.8 NO corta el chorro y SÍ riega el vaso
    game.llenado = 0.0
    game.estadoVaso = "listo"
    zona = game.zonaServir()
    _move_cam_to_px(engine, cam, (zona.centerx - 15, zona.centery))
    cam.set_fist(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.mouseServir is True

    # Mover > 30 px dentro de zonaServir mientras se llena pasado 0.8 hasta derramar
    for i in range(40):
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


def test_fritanga_camera_option_c_accessibility_and_margins(isolated_engine):
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

    # 1. Margen útil ampliado (0.20), ancla palma/muñeca + puño, aro AoE y fluidez en Fritanga
    assert Fritanga84Microgame.CAMERA_POINTER_MARGIN == pytest.approx(0.20)
    assert Fritanga84Microgame.CAMERA_POINTER_FLUID is True
    assert Fritanga84Microgame.CAMERA_POINTER_ANCHOR == "palm"
    assert Fritanga84Microgame.CAMERA_POINTER_GESTURE == "fist"
    assert Fritanga84Microgame.CAMERA_POINTER_RING_RADIUS == 84

    # Ancla en palma/muñeca evita que el cursor baje si el índice (get_position) cae al cerrar la mano
    cam.palm_pos = (0.50, 0.50)
    cam.pos = (0.50, 0.65)
    for _ in range(12):
        engine._update_camera_cursor_interaction(0.05)
    assert abs(engine.cam_cursor_x - 960.0) < 15.0
    assert abs(engine.cam_cursor_y - 540.0) < 15.0
    cam.palm_pos = None

    cam.pos = (0.80, 0.80)
    for _ in range(12):
        engine._update_camera_cursor_interaction(0.05)
    assert engine.cam_cursor_x >= 1880.0 and engine.cam_cursor_y >= 1040.0

    cam.pos = (0.20, 0.20)
    for _ in range(12):
        engine._update_camera_cursor_interaction(0.05)
    assert engine.cam_cursor_x <= 40.0 and engine.cam_cursor_y <= 40.0

    # Fluidez adaptativa sin frenado de puño: barrido amplio avanza mucho más rápido en 16ms que jitter corto
    # y un arrastre corto/rápido tras cerrar puño no se frena (anchor_mode == "palm")
    _move_cam_to_px(engine, cam, (400.0, 400.0), steps=12, dt=0.05)
    engine.cam_cursor_x, engine.cam_cursor_y = 400.0, 400.0
    _move_cam_to_px(engine, cam, (405.0, 400.0), steps=1, dt=0.016)
    jitter_step = engine.cam_cursor_x - 400.0

    engine.cam_cursor_x, engine.cam_cursor_y = 400.0, 400.0
    _move_cam_to_px(engine, cam, (1000.0, 400.0), steps=1, dt=0.016)
    sweep_step = engine.cam_cursor_x - 400.0
    assert sweep_step > jitter_step * 35.0

    engine.cam_cursor_x, engine.cam_cursor_y = 400.0, 400.0
    engine._cam_pointer_down = True
    engine._cam_pointer_down_time = 0.02
    _move_cam_to_px(engine, cam, (430.0, 400.0), steps=1, dt=0.016)
    assert engine.cam_cursor_x - 400.0 >= 7.0
    engine._cam_pointer_down = False
    engine._cam_pointer_down_time = 0.0

    # 2. Corte instantáneo (0 ms) al abrir el puño + zona dulce x0.55 en [0.80, 1.08]
    game.llenado = 0.0
    game.estadoVaso = "listo"
    _move_cam_to_px(engine, cam, game.zonaServir().center)
    cam.set_fist(True)
    engine._update_camera_cursor_interaction(0.016)
    assert game.mouseServir is True and game._servir_por_camara is True

    # Llenar hasta entrar en la zona dulce (>= 0.80) y verificar tasa x0.55 mientras mantiene puño
    for _ in range(20):
        game.update(0.05)
    assert 0.80 <= game.llenado < 1.0
    antes = game.llenado
    game.update(0.10)
    assert game.llenado - antes == pytest.approx(0.85 * 0.55 * 0.10, abs=1e-4)

    # Al abrir la mano, incluso dentro de la gracia de 0.08s del motor, deja de llenar al instante
    cam.set_fist(False)
    engine._update_camera_cursor_interaction(0.04)  # < 0.08s (engine aún no emite MOUSEBUTTONUP)
    llenado_corte = game.llenado
    game.update(0.10)
    assert game.llenado == pytest.approx(llenado_corte)
    engine._update_camera_cursor_interaction(0.06)  # termina de soltar drag en motor

    # 3. Snap ampliado (1.70x) de arepaEn + camera_has_target + renderizado del aro AoE
    a0, a1 = game.arepas[0], game.arepas[1]
    for a in game.arepas:
        a["entrada"] = 1.0
        a["volteo"] = 0.0
        a["sacando"] = 0.0
        a["quemada"] = 0.0
        a["seVuela"] = 0.0
        a["lado"] = 1
        a["coccion"] = 0.2
    a1["coccion"] = 0.85
    # Punto fuera de la elipse estricta de a1 (dy=82 > 55*sqrt(1.3)=62.7) pero dentro de 1.70x
    punto_desviado = (a1["x"], a1["y"] + 82)
    assert game.arepaEn(punto_desviado, es_camara=False) is None
    assert game.arepaEn(punto_desviado, es_camara=True) is a1

    assert game.camera_has_target(punto_desviado) is True
    assert game.camera_has_target(game.zonaServir().center) is True
    assert game.camera_has_target((100, 100)) is False
    engine._render_camera_cursor(engine.virtual_surface)
    _move_cam_to_px(engine, cam, punto_desviado)
    engine._render_camera_cursor(engine.virtual_surface)
    cam.set_fist(True)
    engine._update_camera_cursor_interaction(0.016)
    engine._render_camera_cursor(engine.virtual_surface)
    cam.set_fist(False)
    engine._update_camera_cursor_interaction(0.05)
    engine._update_camera_cursor_interaction(0.05)

    # 4. Entrega directa cerrando el puño al cliente con vaso lleno
    engine.cam_click_cooldown = 0.0
    game.llenado = 0.88
    game.estadoVaso = "listo"
    assert game.camera_has_target(game.cajaCliente().center) is True
    _move_cam_to_px(engine, cam, game.cajaCliente().center)
    cam.set_fist(True)
    engine._update_camera_cursor_interaction(0.016)
    cam.set_fist(False)
    engine._update_camera_cursor_interaction(0.05)
    engine._update_camera_cursor_interaction(0.05)
    assert game.estadoVaso == "entregando"
    assert game.cliente["estado"] == "contento"

    # 5. Entrega por zona amplia al soltar arrastre (pos[0] >= 1280 and pos[1] <= 860)
    game.llenado = 0.88
    game.estadoVaso = "listo"
    game.cliente = {"cual": 0, "estado": "esperando", "tiempo": 0.0, "paciencia": 12.0}
    game.agarrarVaso(game.cajaVasoQuieto().center, es_camara=True)
    game.soltarVaso((1290, 420), es_camara=True)
    assert game.estadoVaso == "entregando"

    # 6. Compensación de cocción activa solo tras interacción de cámara
    a0["coccion"] = 0.40
    a0["velocidad"] = 0.20
    game.estadoVaso = "listo"
    game.mouseServir = False
    game.teclaServir = False
    game.gestoServir = False
    game.update_game(0.10)
    assert a0["coccion"] == pytest.approx(0.40 + 0.20 * 0.10 * 0.80, abs=1e-5)

    # Con coccion >= 1.0 y sirviendo por cámara, aplica x0.65 adicional
    a0["coccion"] = 1.05
    cam.set_fist(True)
    game.mouseServir = True
    game._servir_por_camara = True
    game.update_game(0.10)
    assert a0["coccion"] == pytest.approx(1.05 + 0.20 * 0.10 * 0.80 * 0.65, abs=1e-5)
