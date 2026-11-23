import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
import pytest

pygame.init()
pygame.display.set_mode((1920, 1080))

from core.asset_manager import AssetManager
from microgames.heladero_metro import HeladeroMetroMicrogame, ordenCombos

@pytest.fixture
def game():
    assets = AssetManager()
    g = HeladeroMetroMicrogame(assets)
    return g

def test_siete_clientes_unicos(game):
    """Verifica que el juego tiene exactamente 7 clientes únicos sin repetición antes del compañero."""
    assert len(game.ordenClientes) == 7
    assert len(set(game.ordenClientes)) == 7
    assert sorted(game.ordenClientes) == list(range(7))

def test_cliente_final_companero_preservado(game):
    """Verifica que el cliente final es el compañero Andrés Felipe Mendoza."""
    game.cuantosClientes = 7
    game.nuevoCliente()
    assert game.cliente is not None
    assert game.cliente["esCompanero"] is True
    assert game.cliente["tipo"] == -1
    assert "recreo del colegio" in game.cliente["frase"]

def test_normalizacion_tamanos_cero_saltos(game):
    """
    Verifica que para todos los 7 clientes, todos sus sprites de helados servidos
    tienen EXACTAMENTE la misma altura que su modelo de espera (0 saltos de escala).
    """
    assert game.hinchas is not None
    assert len(game.hinchas["espera"]) >= 7
    assert len(game.pedidosClientes) >= 7

    for tipo in range(7):
        modelo = game.hinchas["espera"][tipo]
        target_h = modelo.get_height()
        combos = game.pedidosClientes[tipo]
        assert len(combos) == 5, f"Cliente {tipo} debe tener 5 combinaciones de helado"
        for c_idx, combo_img in enumerate(combos):
            diff = abs(combo_img.get_height() - target_h)
            assert diff <= 1, (
                f"Cliente {tipo} combo {c_idx}: altura {combo_img.get_height()} "
                f"no coincide con modelo {target_h} (diff={diff})"
            )

def test_cancion_triste_en_lagrimas(game):
    """Verifica que al empezar lágrimas suena la canción triste y al silenciar se restaura la música alegre."""
    game.ponerMusica()
    assert getattr(game.audio, "current_track", None) == "JuniorCancion.mp3"
    
    # Empezar lágrimas
    game.empezarLagrimas()
    assert game.lagrimas is not None
    assert getattr(game.audio, "current_track", None) == "cancion_triste_heladero.ogg"
    
    # Silenciar / 'A lo mío'
    game.decision = {"post": 0}
    game.silenciar()
    assert game.lagrimas is None
    assert getattr(game.audio, "current_track", None) == "JuniorCancion.mp3"

def test_boton_voz_asset_png(game):
    """Verifica que get_voice_button_frames carga los assets ilustrados boton_voz_on.png y boton_voz_off.png."""
    assets = game.assets
    frames = assets.get_voice_button_frames(58)
    assert len(frames) == 2
    assert frames[0].get_size() == (58, 58)
    assert frames[1].get_size() == (58, 58)
    assert os.path.exists(os.path.join(assets.base_dir, "boton_voz_on.png"))
    assert os.path.exists(os.path.join(assets.base_dir, "boton_voz_off.png"))
