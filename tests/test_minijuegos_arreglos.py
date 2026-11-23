"""Coaster sin juego visible tras la intro negra, túnel de Sprint que se cierra al chocar y tarjetas nuevas del Punch."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame


def _init():
    pygame.init()
    pygame.display.set_mode((1920, 1080))


def test_coaster_intro_negra_desde_el_primer_cuadro():
    _init()
    from microgames.coaster_launcher import CoasterLauncherState

    estado = CoasterLauncherState()
    estado.enter()
    assert estado.game is not None and estado.game.estado == "intro"
    s = pygame.Surface((1920, 1080))
    for _ in range(25):  # incluye el parpadeo inicial (primeros 0.3 s)
        estado.update(1 / 60)
        estado.render(s)
        claros = (pygame.surfarray.array3d(s).max(axis=2) > 60).mean()
        assert claros < 0.02, "se alcanzó a ver el juego detrás de la pantalla negra"
    estado.exit()


def test_sprint_vision_se_reduce_con_cada_choque_mirando_el_celular():
    _init()
    from microgames.uninorte_sprint import UninorteSprintMicrogame

    juego = UninorteSprintMicrogame()
    juego.phase = juego.PHASE_PLAY
    juego.update(1 / 60)
    juego.tiempoDistraido = juego.duracionDistraccion - 0.5
    s = pygame.Surface((1920, 1080))
    visibles = []
    for choque in range(3):
        if choque:
            juego.stun_timer = 0.0
            juego._on_player_hit()
        juego.tiempoDistraido = juego.duracionDistraccion - 0.5
        juego.render(s)
        visibles.append((pygame.surfarray.array3d(s).max(axis=2) > 45).mean())
    assert visibles[0] > visibles[1] > visibles[2]
    # Al soltar el celular el túnel vuelve a su tamaño normal
    juego.tiempoDistraido = 0.01
    juego.actualizarDistraccion(0.1)
    assert juego.choquesDistraido == 0


def test_punch_tarjetas_nuevas_y_villancico(monkeypatch):
    _init()
    from microgames.punch_alert import PunchAlertMicrogame
    from microgames.punch_alert import game as punch

    juego = PunchAlertMicrogame()
    ideas = {i["codigo"]: i for i in juego.ideas}
    for codigo in punch.tarjetasNuevas:
        assert codigo in ideas and not ideas[codigo]["riesgosa"]
        assert ideas[codigo]["sprite"].get_size() == ideas["lucecitas"]["sprite"].get_size()
    # El villancico siempre viene en la ola
    assert any(n["idea"]["codigo"] == "villancico" for n in juego.wave_queue)
    # Al llegar a la publicación: suena el villancico y se aplican los efectos
    llamadas = []
    monkeypatch.setattr(juego.audio, "play_bgm", lambda nombre, **kw: llamadas.append(nombre))
    monkeypatch.setattr(punch.os.path, "exists", lambda ruta, _orig=punch.os.path.exists: True if "villancico" in str(ruta) else _orig(ruta))
    juego.capturarFoto(pygame.Surface((1920, 1080)))
    for codigo in ("villancico", "nieve", "recuerdo", "abuela", "hashtag"):
        juego.llegarAlPost(ideas[codigo])
    assert llamadas and "villancico" in llamadas[-1]
    assert {"cancion", "nieve", "recuerdo", "comentario"} <= set(juego.partesPost)
    juego.relojPost += 2.0
    juego.componerPost(likes=10)
