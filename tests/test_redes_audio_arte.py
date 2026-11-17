"""Audio propio de CurramGram/Emoji Catch y arte acuarela de Emoji Catch."""
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

ROOT = Path(__file__).resolve().parents[1]


def _init():
    pygame.init()
    pygame.display.set_mode((1920, 1080))
    if not pygame.mixer.get_init():
        pygame.mixer.init()


def test_audio_files_exist_and_load_trimmed():
    _init()
    from microgames import curramgram_go, emoji_catch
    from microgames.curramgram.juego import SFX_SELLO
    from microgames.emojis.juego import SFX_BLOQUEO
    from microgames.redes_comun import load_managed_sound

    archivos = [curramgram_go.MUSIC_TRACK, emoji_catch.MUSIC_TRACK, SFX_SELLO, SFX_BLOQUEO]
    archivos += [f for f, _, _ in curramgram_go.SFX.values()] + [f for f, _, _ in emoji_catch.SFX.values()]
    for nombre in archivos:
        assert (ROOT / "assets" / nombre).is_file(), nombre
    for f, v, m in list(curramgram_go.SFX.values()) + list(emoji_catch.SFX.values()):
        sonido = load_managed_sound(f, v, m)
        assert sonido is not None, f
        if m is not None:
            assert sonido.sound.get_length() <= m + 0.05, f


def test_games_load_their_own_sfx():
    _init()
    from microgames.curramgram_go import CurramGramGoMicrogame
    from microgames.emoji_catch import EmojiCatchMicrogame

    for juego in (CurramGramGoMicrogame(), EmojiCatchMicrogame()):
        assert all(s is not None for s in juego.sfx.values()), type(juego).__name__


def test_emoji_watercolor_art_in_use():
    _init()
    from microgames.emojis.juego import POSITIVOS, EmojiCatch

    juego = EmojiCatch()
    assert "emoji_estrellas" in POSITIVOS and "emoji_angel" in POSITIVOS
    assert all(juego.sprites[n] is not None for n in POSITIVOS)
    assert all(p is not None for p in juego.puno)
    assert juego.mano_morada.get_height() == 270
    superficie = pygame.Surface((1920, 1080))
    juego.pulso = [0.2, 0.2]  # puños cerrados al atrapar
    juego.draw(superficie)
