import os
import sys
import pytest
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from microgames.buenavista_cine import BuenavistaCineMicrogame, SpectatorSeat, ShhAudioDetector


def test_buenavista_cine_initialization():
    """Valida carga limpia de estados, 4 personajes en escena y configuración inicial."""
    pygame.init()
    pygame.display.set_mode((1920, 1080))

    microgame = BuenavistaCineMicrogame(character_id="char")
    assert microgame.time_limit == 30.0
    assert microgame.time_left == 30.0
    assert microgame.strikes == 0
    assert microgame.max_strikes == 2
    assert len(microgame.spectators) == 4

    for spec in microgame.spectators:
        assert spec.state == SpectatorSeat.STATE_IDLE
        assert spec.rect_segment.width == 480

    microgame.cleanup()


def test_spectator_offense_and_shh_pacify():
    """Prueba que el evento 'SHHH' apacigüe al espectador activo inmediatamente."""
    pygame.init()
    pygame.display.set_mode((1920, 1080))

    microgame = BuenavistaCineMicrogame(character_id="char")
    microgame.phase = microgame.PHASE_PLAY

    spec = microgame.spectators[1]
    spec.start_offense("Chateando", 3.0)
    assert spec.state == SpectatorSeat.STATE_OFFENDING

    # Jugador emite un 'SHHH'
    microgame._on_player_shhed()
    assert spec.state == SpectatorSeat.STATE_PACIFIED
    assert microgame.pacified_count == 1
    assert spec.startle_jump_y < 0.0  # Salto reactivo de susto

    microgame.cleanup()


def test_spacebar_fallback():
    """Prueba que la tecla [ESPACIO] active el chistido sin micrófono."""
    pygame.init()
    pygame.display.set_mode((1920, 1080))

    microgame = BuenavistaCineMicrogame(character_id="char")
    microgame.phase = microgame.PHASE_PLAY

    spec = microgame.spectators[0]
    spec.start_offense("Selfie", 3.0)

    # Evento de barra espaciadora
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    microgame.handle_game_event(event)

    assert spec.state == SpectatorSeat.STATE_PACIFIED
    assert microgame.pacified_count == 1

    microgame.cleanup()


def test_strike_accumulation_and_game_over():
    """Prueba que 2 faltas generen derrota inmediata."""
    pygame.init()
    pygame.display.set_mode((1920, 1080))

    game_completed = []
    def on_done(won):
        game_completed.append(won)

    microgame = BuenavistaCineMicrogame(character_id="char", on_complete_callback=on_done)
    microgame.phase = microgame.PHASE_PLAY
    spec = microgame.spectators[2]

    # Infracción 1
    spec.start_offense("Grabando", 0.5)
    res1 = spec.update(0.6)
    assert res1 == "STRIKE"
    microgame._apply_strike("Omisión")
    assert microgame.strikes == 1
    assert not microgame.is_finished

    # Infracción 2
    spec.start_offense("Flash", 0.5)
    res2 = spec.update(0.6)
    assert res2 == "STRIKE"
    microgame._apply_strike("Omisión")
    assert microgame.strikes == 2
    assert microgame.is_finished
    assert not microgame.is_won

    microgame.update(microgame.outro_duration + 0.1)
    assert game_completed == [False]

    microgame.cleanup()


def test_victory_condition_at_30_seconds():
    """Prueba que al sobrevivir 30s sin llegar a 2 faltas se gane la partida."""
    pygame.init()
    pygame.display.set_mode((1920, 1080))

    game_completed = []
    def on_done(won):
        game_completed.append(won)

    microgame = BuenavistaCineMicrogame(character_id="char", on_complete_callback=on_done)
    microgame.phase = microgame.PHASE_PLAY
    microgame.time_left = 0.1
    microgame.strikes = 1

    microgame.update(0.2)
    assert microgame.is_finished
    assert microgame.is_won

    microgame.update(microgame.outro_duration + 0.1)
    assert game_completed == [True]

    microgame.cleanup()


def test_headless_shh_detector_does_not_open_microphone(monkeypatch):
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    detector = ShhAudioDetector()
    detector.start()
    assert detector.running is False
    assert detector._stream is None
