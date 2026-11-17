"""CurramGram Go! y Emoji Catch corren como BaseMicrogame: pausa común, barra de tiempo, mando y cámara."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1920, 1080))

from core import input_state
from core.microgame import BaseMicrogame
from core.microgame_pause import MicrogamePauseState
from core.state_machine import StateMachine
from microgames.curramgram_go import CurramGramGoMicrogame
from microgames.emoji_catch import EmojiCatchMicrogame


def _to_play(game: BaseMicrogame) -> None:
    assert game.paloma_intro is not None and game.paloma_intro.active  # contexto de la Paloma
    game.paloma_intro.skip()
    for _ in range(60):
        game.update(1 / 30)
    assert game.phase == BaseMicrogame.PHASE_PLAY


def _key(etype, k):
    return pygame.event.Event(etype, {"key": k, "unicode": "", "mod": 0})


def test_both_games_use_shared_pause_menu():
    for cls in (CurramGramGoMicrogame, EmojiCatchMicrogame):
        sm = StateMachine()
        game = cls()
        sm.change_state(game)
        _to_play(game)
        game.handle_event(_key(pygame.KEYDOWN, pygame.K_ESCAPE))
        assert isinstance(sm.current_state, MicrogamePauseState), cls.__name__
        surf = pygame.Surface((1920, 1080))
        sm.current_state.render(surf)


def test_emoji_timer_sync_hands_and_finish():
    input_state.clear()
    game = EmojiCatchMicrogame()
    _to_play(game)

    # Teclado: flecha derecha mueve la mano morada; J mueve la azul (ambas vía teclas sostenidas del mando).
    start = list(game.game.manos)
    input_state.VIRTUAL_KEYS.update({pygame.K_RIGHT, pygame.K_j})
    for _ in range(10):
        game.update(1 / 30)
    input_state.clear()
    assert game.game.manos[0] > start[0]
    assert game.game.manos[1] < start[1]

    # La barra común sigue el reloj propio del juego.
    assert abs(game.time_left - game.game.tiempo) < 1e-6
    assert game.time_left < game.time_limit

    # Cámara: una mano a la izquierda guía la morada, otra a la derecha guía la azul.
    class FakeCam:
        enabled = True

        def is_hand_present(self):
            return True

        def get_hands(self):
            return [(0.05, 0.5), (0.95, 0.5)]

    game.camera_input = FakeCam()
    for _ in range(40):
        game.update(1 / 30)
    assert game.game.manos[0] < 260
    assert game.game.manos[1] > 1650

    # Al terminar el juego interno, el microjuego reporta el resultado.
    results = []
    game.on_complete_callback = results.append
    game.game.tiempo = 0.0
    game.game.final = "BALANCE LOGRADO"
    game.game.victoria = True
    game.update(1 / 30)
    assert game.is_finished and game.is_won
    for _ in range(300):
        game.update(1 / 30)
    # (BaseMicrogame repite el callback tras el outro; en el juego real la escena ya cambió.)
    assert results and set(results) == {True}
    game.render(pygame.Surface((1920, 1080)))


def test_curramgram_keyboard_gamepad_and_photo():
    input_state.clear()
    game = CurramGramGoMicrogame()
    _to_play(game)
    assert not game.game.inicio  # sin panel propio: la Paloma y la portada común dan el contexto

    x0 = game.game.x
    input_state.VIRTUAL_KEYS.add(pygame.K_RIGHT)
    for _ in range(15):
        game.update(1 / 30)
    input_state.clear()
    assert game.game.x > x0

    # Esconderse con ↓ (D-pad) y soltar.
    game.handle_event(_key(pygame.KEYDOWN, pygame.K_DOWN))
    assert game.game.ocultando
    game.handle_event(_key(pygame.KEYUP, pygame.K_DOWN))
    assert not game.game.ocultando

    # Foto sin mouse (F / botón B): apunta al caso más cercano.
    game.game.x = 1420.0  # Junto a la turista (caso 2)
    game.handle_event(_key(pygame.KEYDOWN, pygame.K_f))
    assert game.game.last_camera is not None

    assert CurramGramGoMicrogame.GAMEPAD_BUTTON_KEYS[1] == pygame.K_f
    game.render(pygame.Surface((1920, 1080)))


def test_curramgram_final_explains_social_media_phenomena():
    game = CurramGramGoMicrogame()
    _to_play(game)
    from microgames.curramgram_go import _curram

    fenomenos = [c[1] for c in _curram.CASOS]
    assert "Desinformación" in fenomenos and "Escrache digital" in fenomenos
    game.game.final = "VUELO PERDIDO"
    game.update(1 / 30)
    assert game.is_finished and not game.is_won
    game.render(pygame.Surface((1920, 1080)))


def test_paloma_context_advances_with_keys_and_blocks_play():
    game = EmojiCatchMicrogame()
    intro = game.paloma_intro
    assert intro.active and len(intro.pages) == 3
    for _ in range(10):
        game.update(1 / 30)
    assert game.phase == BaseMicrogame.PHASE_INTRO  # no arranca mientras habla la Paloma
    surf = pygame.Surface((1920, 1080))
    game.render(surf)
    for _ in range(3):
        game.handle_event(_key(pygame.KEYDOWN, pygame.K_SPACE))
    for _ in range(20):
        game.update(1 / 30)
    assert not intro.active
    for _ in range(60):
        game.update(1 / 30)
    assert game.phase == BaseMicrogame.PHASE_PLAY
