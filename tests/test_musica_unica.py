"""Nunca suenan dos canciones a la vez; la música sigue en la pausa; voz del pregón del heladero."""
import os
import wave

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame


def _init():
    pygame.init()
    pygame.display.set_mode((1920, 1080))
    if not pygame.mixer.get_init():
        pygame.mixer.init(44100, -16, 2)


def _llamadas_musica(monkeypatch):
    registro = []
    for nombre in ("load", "play", "stop", "fadeout"):
        original = getattr(pygame.mixer.music, nombre)

        def envoltura(*a, _o=original, _n=nombre, **k):
            registro.append((_n, os.path.basename(str(a[0])) if a and _n == "load" else None))
            return _o(*a, **k)
        monkeypatch.setattr(pygame.mixer.music, nombre, envoltura)
    return registro


def test_villancico_reemplaza_la_musica_y_no_vuelve_la_del_juego(monkeypatch):
    _init()
    from core.audio_manager import AudioManager
    from microgames.punch_alert import PunchAlertMicrogame

    audio = AudioManager.get_instance()
    juego = PunchAlertMicrogame()
    juego.enter()
    juego.ponerMusica()
    assert audio.current_track == "PunchMusic.mp3"
    registro = _llamadas_musica(monkeypatch)
    assert juego.ponerVillancico()
    # Se detuvo la música del juego antes de cargar el villancico
    nombres = [n for n, _ in registro]
    assert "stop" in nombres and nombres.index("stop") < nombres.index("load")
    assert [arch for n, arch in registro if n == "load"] == ["villancico.mp3"]
    assert audio.current_track.endswith("villancico.mp3")
    # Nada vuelve a poner la música del Punch mientras suena el villancico
    registro.clear()
    juego.ponerMusica()
    assert not [n for n, _ in registro if n == "load"]
    assert audio.current_track.endswith("villancico.mp3")


def test_musica_sigue_en_la_pausa():
    _init()
    from core.audio_manager import AudioManager
    from core.microgame_pause import MicrogamePauseState
    from core.state_machine import StateMachine
    from microgames.punch_alert import PunchAlertMicrogame

    audio = AudioManager.get_instance()
    sm = StateMachine()
    juego = PunchAlertMicrogame()
    sm.change_state(juego)
    juego.ponerVillancico()
    pista = audio.current_track
    sm.push_state(MicrogamePauseState(previous=juego))
    s = pygame.Surface((1920, 1080))
    for _ in range(30):
        sm.update(1 / 60)
        sm.render(s)
    assert audio.current_track == pista
    sm.pop_state()
    assert audio.current_track == pista


def test_cancion_en_canal_se_apaga_si_entra_otra_musica():
    _init()
    from core.audio_manager import AudioManager

    audio = AudioManager.get_instance()
    datos = (np.sin(np.linspace(0, 2000, 44100 * 2)) * 8000).astype(np.int16)
    cancion = pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack([datos, datos])))
    canal = cancion.play(loops=-1)
    audio.registrar_cancion_en_canal(canal)
    assert canal.get_busy()
    audio.current_track = None
    audio.play_bgm("PunchMusic.mp3")
    assert not canal.get_busy(), "la canción del minijuego siguió sonando junto con la nueva música"


def test_fritanga_cancion_del_trol_sigue_en_pausa():
    _init()
    from microgames.fritanga_84 import Fritanga84Microgame

    juego = Fritanga84Microgame()
    juego.sonarCancionTrol()
    if juego.canalTrol is None:
        return  # sin dispositivo de audio en esta máquina
    juego.ultimoUpdate = pygame.time.get_ticks() - 1000  # como si llevara un rato en pausa
    juego.callarAceiteSiPausado()
    assert juego.canalTrol.get_busy()
    juego.exit()


def test_pregon_del_heladero_suena_al_aparecer(monkeypatch, tmp_path):
    _init()
    from core.audio_manager import AudioManager
    from microgames import heladero_metro as H

    # Voz de prueba (0.6 s) en lugar del archivo real
    ruta = tmp_path / "heladero_pregon.wav"
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes((np.sin(np.linspace(0, 900, 13230)) * 6000).astype(np.int16).tobytes())
    audio = AudioManager.get_instance()
    monkeypatch.setitem(H.vocesEscena, H.escenaIntro[2][1], (str(ruta),))
    monkeypatch.setattr(audio, "resolve_voice_path", lambda clip: clip if os.path.exists(clip) else None)
    sonadas = []
    original = audio.play_voice
    monkeypatch.setattr(audio, "play_voice", lambda clip, **k: sonadas.append(clip) or original(clip, **k))

    juego = H.HeladeroMetroMicrogame() if hasattr(H, "HeladeroMetroMicrogame") else next(
        v for v in vars(H).values() if isinstance(v, type) and v.__name__.lower().startswith("heladero"))()
    juego.phase = juego.PHASE_PLAY
    s = pygame.Surface((1920, 1080))
    for _ in range(60 * 20):
        juego.update(1 / 60)
        juego.render(s)
        if sonadas:
            break
    assert sonadas == [str(ruta)]
    # Justo cuando sonó, la línea en pantalla es la del pregón
    assert juego.escena is not None and juego.escena["lineas"][juego.escena["i"]][1] == H.escenaIntro[2][1]
