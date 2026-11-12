import os
import sys
import pygame

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.engine import Engine
from microgames.punch_alert import PunchAlertMicrogame

def test_punch_alert_standalone():
    """Valida la carga, renderizado y gameloop sin errores."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    pygame.font.init()
    pygame.display.set_mode((1920, 1080), pygame.NOFRAME)

    pygame.mixer.init()
    game = PunchAlertMicrogame(character_id="westcol", time_limit=15.0)
    surface = pygame.Surface((1920, 1080))

    assert game.total_wave_count == 11
    assert len(game.safe_sprites) == 5
    assert len(game.trash_sprites) == 11
    assert len(game.punch_voices) == 4

    # Ejecutar 60 ticks de simulación
    for _ in range(60):
        game.update(1.0 / 60.0)
        game.render(surface)

    # Simular 1er golpe al aire (whiff_streak debe guardarse en 1)
    event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE})
    game.phase = PunchAlertMicrogame.PHASE_PLAY
    game.cooldown_timer = 0.0
    game.is_punching = False
    game.handle_game_event(event)
    assert game.is_punching is True
    assert game.whiff_streak == 1

    # Incluso si acierta una notificación después, whiff_streak NO se borra (sigue en 1)
    game.on_successful_hit(game.wave_queue[0])
    assert game.whiff_streak == 1

    # Al fallar por 2da vez al aire, recibe +1 Strike y reinicia la cuenta a 0
    game.cooldown_timer = 0.0
    game.is_punching = False
    prev_strikes = game.strikes
    game.handle_game_event(event)
    assert game.strikes == prev_strikes + 1
    assert game.whiff_streak == 0

    # Simular otros 30 ticks con el golpe activo
    for _ in range(30):
        game.update(1.0 / 60.0)
        game.render(surface)

    print("TEST STANDALONE PASSED: PunchAlertMicrogame funciona correctamente.")

if __name__ == "__main__":
    test_punch_alert_standalone()
