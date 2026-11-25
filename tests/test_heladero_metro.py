import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame
import pytest

pygame.init()
pygame.display.set_mode((1920, 1080))

from microgames.heladero_metro import ALTURA_CLIENTE, HeladeroMetroMicrogame, archivosClientes, ordenCombos


@pytest.fixture
def game():
    return HeladeroMetroMicrogame()


def test_constructor_por_defecto_y_standalone(game):
    """Verifica el constructor por defecto (usado en __main__) y actualización inicial sin TypeError."""
    assert game.character_id == "westcol"
    game.update(0.016)
    surf = pygame.Surface((1920, 1080))
    game.render_game(surf)


def test_siete_clientes_unicos_y_secuencia_completa(game):
    """Verifica que una partida completa sirve exactamente 7 clientes únicos (0..6) y luego al compañero (-1)."""
    for _ in range(3):
        game.setup_game()
        assert len(game.ordenClientes) == 7
        assert len(set(game.ordenClientes)) == 7
        assert sorted(game.ordenClientes) == list(range(7))

        vistos = []
        for _ in range(7):
            game.nuevoCliente()
            assert game.cliente is not None
            assert game.cliente["esCompanero"] is False
            vistos.append(game.cliente["tipo"])
        assert len(set(vistos)) == 7
        assert sorted(vistos) == list(range(7))

        game.nuevoCliente()
        assert game.cliente is not None
        assert game.cliente["esCompanero"] is True
        assert game.cliente["tipo"] == -1
        assert "recreo del colegio" in game.cliente["frase"]


def test_transparencia_cargar_verde_sin_cajas_negras(game):
    """Verifica que cargarVerde() no sufre desbordamiento int16 y deja esquinas transparentes (alpha == 0)."""
    for archivo in ("hinchas.jpg", "companero.jpg", "companeroHelado.jpg", *archivosClientes):
        surf = game.cargarVerde(archivo)
        assert surf is not None, f"No se pudo cargar {archivo}"
        w, h = surf.get_size()
        for cx, cy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
            assert surf.get_at((cx, cy))[3] == 0, f"{archivo} esquina ({cx},{cy}) no es transparente"

    for i in range(7):
        for surf in [game.hinchas["espera"][i], game.hinchas["feliz"][i], *game.pedidosClientes[i]]:
            assert surf.get_at((0, 0))[3] == 0
    assert game.companeroImg["cliente"].get_at((0, 0))[3] == 0
    assert game.companeroHelado.get_at((0, 0))[3] == 0


def test_cliente_hincha_sin_triangulos_verde_oliva_en_cono(game):
    """Verifica que clienteHincha (_feliz.png y los 5 combos) no tiene triángulos verde oliva en el borde del cono."""
    estados = [("feliz", game.hinchas["feliz"][5])] + [
        (f"combo_{idx}", surf) for idx, surf in enumerate(game.pedidosClientes[5])
    ]
    for nombre, surf in estados:
        w, h = surf.get_size()
        rgb = pygame.surfarray.array3d(surf).transpose(1, 0, 2)
        alpha = pygame.surfarray.array_alpha(surf).transpose(1, 0)
        y0, y1 = int(h * 0.52), int(h * 0.63)
        x0, x1 = int(w * 0.30), int(w * 0.56)
        sub_rgb = rgb[y0:y1, x0:x1]
        sub_a = alpha[y0:y1, x0:x1]
        r = sub_rgb[..., 0].astype(np.int32)
        g = sub_rgb[..., 1].astype(np.int32)
        b = sub_rgb[..., 2].astype(np.int32)
        olive_mask = (
            (sub_a > 20)
            & (g >= r - 10)
            & (g > b + 25)
            & ~((r > 175) & (b > 130))
            & ~(r >= g + 8)
        )
        assert not olive_mask.any(), (
            f"clienteHincha {nombre}: detectados {int(olive_mask.sum())} píxeles verde oliva en borde del cono"
        )


def test_normalizacion_tamanos_cero_saltos(game):
    """
    Verifica altura canónica idéntica (ALTURA_CLIENTE) y consistencia de escala de cabeza (<= 3%)
    para los 7 clientes y el compañero en espera, feliz y las 5 combinaciones de helado.
    """
    assert game.hinchas is not None
    assert len(game.hinchas["espera"]) == 7
    assert len(game.hinchas["feliz"]) == 7
    assert game.pedidosClientes is not None
    assert len(game.pedidosClientes) == 7

    for tipo in range(7):
        espera = game.hinchas["espera"][tipo]
        feliz = game.hinchas["feliz"][tipo]
        combos = game.pedidosClientes[tipo]
        assert len(combos) == len(ordenCombos) == 5, f"Cliente {tipo} debe tener 5 combinaciones"

        estados = [espera, feliz, *combos]
        for idx, surf in enumerate(estados):
            assert surf.get_height() == ALTURA_CLIENTE, (
                f"Cliente {tipo} estado {idx}: altura {surf.get_height()} != {ALTURA_CLIENTE}"
            )

        heads = [game.anchoCabeza(s) for s in estados]
        delta_pct = (max(heads) - min(heads)) / float(min(heads))
        assert delta_pct <= 0.03, (
            f"Cliente {tipo}: salto de escala de cabeza {delta_pct:.2%} > 3% (heads={heads})"
        )

    comp_esp = game.companeroImg["cliente"]
    comp_hel = game.companeroHelado
    assert comp_esp.get_height() == ALTURA_CLIENTE
    assert comp_hel.get_height() == ALTURA_CLIENTE
    comp_heads = (game.anchoCabeza(comp_esp), game.anchoCabeza(comp_hel))
    comp_delta = (max(comp_heads) - min(comp_heads)) / float(min(comp_heads))
    assert comp_delta <= 0.03, f"Compañero: salto de escala {comp_delta:.2%} > 3%"


def test_cancion_triste_en_lagrimas_y_procedencia(game):
    """Verifica reproducción de canción triste en lágrimas, restauración al expirar/silenciar y metadata CC0."""
    game.ponerMusica()
    assert getattr(game.audio, "current_track", None) == "JuniorCancion.mp3"

    # Empezar lágrimas -> reproduce cancion_triste_heladero.ogg
    game.empezarLagrimas()
    assert game.lagrimas is not None
    assert getattr(game.audio, "current_track", None) == "cancion_triste_heladero.ogg"

    # Al expirar el temporizador de lágrimas, restaura JuniorCancion.mp3
    game.actualizarLagrimas(game.lagrimas["dur"] + 0.1)
    assert game.lagrimas is None
    assert getattr(game.audio, "current_track", None) == "JuniorCancion.mp3"

    # Silenciar también detiene lágrimas y restaura JuniorCancion.mp3
    game.empezarLagrimas()
    assert getattr(game.audio, "current_track", None) == "cancion_triste_heladero.ogg"
    game.decision = {"post": 0}
    game.silenciar()
    assert game.lagrimas is None
    assert getattr(game.audio, "current_track", None) == "JuniorCancion.mp3"

    # Procedencia real no sintética (JRPG2 Piano / Joth / CC0) en assets/ y assets/Estadio/
    ruta_root = os.path.join(game.assets.base_dir, "cancion_triste_heladero.ogg")
    ruta_estadio = os.path.join(game.assets.base_dir, "Estadio", "cancion_triste_heladero.ogg")
    assert os.path.exists(ruta_root) and os.path.exists(ruta_estadio)
    with open(ruta_root, "rb") as f:
        data_root = f.read()
    with open(ruta_estadio, "rb") as f:
        data_estadio = f.read()
    assert data_root == data_estadio
    header = data_root[:4096].decode("latin1", errors="ignore")
    assert "JRPG2 Piano" in header
    assert "Joth" in header
    assert "CC0" in header


def test_boton_voz_asset_png(game):
    """Verifica que get_voice_button_frames carga los assets ilustrados boton_voz_on.png y boton_voz_off.png."""
    assets = game.assets
    frames = assets.get_voice_button_frames(58)
    assert len(frames) == 2
    assert frames[0].get_size() == (58, 58)
    assert frames[1].get_size() == (58, 58)
    assert os.path.exists(os.path.join(assets.base_dir, "boton_voz_on.png"))
    assert os.path.exists(os.path.join(assets.base_dir, "boton_voz_off.png"))
