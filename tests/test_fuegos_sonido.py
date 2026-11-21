"""El sonido de los fuegos suena al ESTALLAR (no al lanzar), uno por fuego, y baja si hay una voz sonando."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from effects import fuegos_sonido
from effects.fuegos_sonido import SUBIDA_FUEGO, SonidoFuegos
from effects.juice_particles import FuegosArtificiales, cicloFuego


def _sonido():
    pygame.init()
    if not pygame.mixer.get_init():
        pygame.mixer.init(44100, -16, 2)
    SonidoFuegos._instancia = None
    return SonidoFuegos.get()


def test_estallidos_separados_de_los_archivos():
    s = _sonido()
    assert len(s.estallidos) >= 6
    assert all(0.3 <= e.get_length() <= fuegos_sonido.DURACION_ESTALLIDO + 0.01 for e in s.estallidos)


def test_suena_al_estallar_no_al_lanzar(monkeypatch):
    s = _sonido()
    momentos = []
    reloj = {"t": 0.0}
    monkeypatch.setattr(s, "estallar", lambda: momentos.append(reloj["t"]))

    fuegos = FuegosArtificiales()
    fuegos.lanzarAlrededor(pygame.Rect(600, 300, 700, 400))
    dt = 1 / 60
    salidas = [-f["t"] for f in fuegos.fuegos]  # cuándo sale cada cohete
    while reloj["t"] < salidas[-1] + SUBIDA_FUEGO + 0.2:
        fuegos.update(dt)
        reloj["t"] += dt
    # Un sonido por fuego, cada uno justo cuando termina de subir (± un frame), nunca al salir.
    assert len(momentos) == len(fuegos.fuegos)
    for salida, momento in zip(salidas, momentos):
        assert abs(momento - (salida + SUBIDA_FUEGO)) <= 2 * dt + 1e-6

    # En la siguiente vuelta del ciclo vuelven a sonar una vez cada uno.
    momentos.clear()
    for _ in range(int(cicloFuego / dt)):
        fuegos.update(dt)
        reloj["t"] += dt
    assert len(momentos) == len(fuegos.fuegos)


def test_baja_el_volumen_si_hay_otro_audio(monkeypatch):
    s = _sonido()
    volumenes = []

    class CanalFalso:
        def get_busy(self):
            return False

        def set_volume(self, v):
            volumenes.append(v)

        def play(self, _sonido):
            pass

    s.canales = [CanalFalso()]
    monkeypatch.setattr(s, "_otro_audio_sonando", lambda: False)
    s.estallar()
    monkeypatch.setattr(s, "_otro_audio_sonando", lambda: True)
    s.estallar()
    assert len(volumenes) == 2 and volumenes[1] < volumenes[0] * 0.5
