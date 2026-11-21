"""El clic cae donde se ve el botón, con cualquier tamaño de ventana (dibujo y mouse usan el mismo letterbox)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from core.engine import Engine


def _clic_en(engine, x, y):
    evt = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (x, y), "button": 1})
    return engine._map_mouse_event(evt).pos


def test_mouse_matches_letterboxed_drawing_in_any_window():
    engine = Engine(enable_gl=False)
    for ventana in ((1920, 1080), (1920, 1017), (1366, 768), (1280, 1024), (2560, 1080)):
        engine._client_size = lambda v=ventana: v
        escala, off_x, off_y, _, _ = engine._letterbox(*ventana)
        # Un botón dibujado en (960, 540) virtual aparece en pantalla en off + 960*escala.
        for vx, vy in ((960, 540), (100, 80), (1820, 1000)):
            sx, sy = off_x + vx * escala, off_y + vy * escala
            mx, my = _clic_en(engine, int(round(sx)), int(round(sy)))
            assert abs(mx - vx) <= 2 and abs(my - vy) <= 2, (ventana, (vx, vy), (mx, my))


def test_window_fits_desktop():
    w, h = Engine._fit_window_to_desktop(1920, 1080)
    sizes = pygame.display.get_desktop_sizes()
    if sizes:
        assert w <= sizes[0][0] and h <= sizes[0][1]
    assert abs(w / h - 16 / 9) < 0.01
