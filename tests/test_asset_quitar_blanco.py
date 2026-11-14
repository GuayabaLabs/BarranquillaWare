import os
import pygame
import pytest

from core.asset_manager import AssetManager, quitarBlanco


@pytest.fixture(autouse=True)
def _pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((64, 64))
    yield


def test_quitar_blanco_preserves_enclosed_white_interior():
    surf = pygame.Surface((120, 120), pygame.SRCALPHA)
    surf.fill((255, 255, 255, 255))
    # Marco oscuro cerrado con interior blanco/crema
    pygame.draw.rect(surf, (40, 30, 20, 255), (20, 20, 80, 80), width=6)
    pygame.draw.rect(surf, (252, 248, 240, 255), (26, 26, 68, 68))

    cleaned = quitarBlanco(surf)
    cw, ch = cleaned.get_size()
    assert cw <= 85 and ch <= 85
    assert cleaned.get_at((cw // 2, ch // 2)).a == 255


@pytest.mark.parametrize(
    "rel_path",
    [
        os.path.join("Interfaz", "ventanaMenuPausa.jpg"),
        os.path.join("Interfaz", "VentanaAviso.jpg"),
        os.path.join("Interfaz", "Trofeo.jpg"),
        os.path.join("Interfaz", "botonX.jpg"),
    ],
)
def test_cargar_sin_fondo_no_interior_perforation(rel_path):
    assets = AssetManager.get_instance()
    raw = pygame.image.load(assets._resolve_path(rel_path)).convert_alpha()
    cleaned_raw = quitarBlanco(raw)
    rw, rh = cleaned_raw.get_size()
    assert cleaned_raw.get_at((rw // 2, rh // 2)).a == 255

    surf = assets.cargarSinFondo(rel_path, 400)
    w, h = surf.get_size()
    assert w == 400 and h > 0
    # El centro del pergamino / trofeo / botón debe mantenerse opaco (smoothscale redondea 255 -> 252..255)
    assert surf.get_at((w // 2, h // 2)).a >= 250
    # Las esquinas exteriores tras el recorte ajustado deben quedar transparentes
    assert surf.get_at((0, 0)).a == 0
    assert surf.get_at((w - 1, 0)).a == 0


def test_quitar_blanco_handles_24bit_rgb_surface_without_alpha():
    surf = pygame.Surface((60, 60))
    surf.fill((255, 255, 255))
    pygame.draw.rect(surf, (30, 30, 30), (15, 15, 30, 30), width=4)
    pygame.draw.rect(surf, (250, 246, 238), (19, 19, 22, 22))

    cleaned = quitarBlanco(surf)
    cw, ch = cleaned.get_size()
    assert cw <= 34 and ch <= 34
    assert cleaned.get_at((cw // 2, ch // 2)).a == 255


def test_cargar_trofeo_clears_handle_seeds_and_preserves_center():
    assets = AssetManager.get_instance()
    trofeo = assets.cargarTrofeo(400)
    w, h = trofeo.get_size()
    assert w == 400 and h > 0
    assert trofeo.get_at((w // 2, h // 2)).a >= 250
    assert trofeo.get_at((int(0.2095 * w), int(0.3452 * h))).a == 0
    assert trofeo.get_at((int(0.7896 * w), int(0.3452 * h))).a == 0
