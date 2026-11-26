import os
import sys
import pygame

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.engine import Engine
from microgames.punch_alert import PunchAlertMicrogame
from microgames.punch_alert.game import ensenanzasRiesgo

def test_punch_alert_standalone():
    """Valida la carga, renderizado y gameloop sin errores."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    pygame.font.init()
    pygame.display.set_mode((1920, 1080), pygame.NOFRAME)

    pygame.mixer.init()
    game = PunchAlertMicrogame(character_id="valdiri", time_limit=15.0)
    game.paloma_intro = None  # prueba del juego en sí, sin el diálogo de la Paloma (como en el Modo Historia)
    surface = pygame.Surface((1920, 1080))

    # Con tarjetas cada 0,8 s, 15 s alcanzan para el tope de 10 tarjetas
    assert game.total_wave_count == len(game.wave_queue) == 10
    assert len(game.safe_sprites) == 12  # 8 originales + nieve, foto antigua, hashtag y comentario
    assert len(game.trash_sprites) == 8
    assert game.wave_queue[0]["is_safe"] is False
    assert len(game.punch_voices) == 4

    # Ejecutar 60 ticks de simulación
    for _ in range(60):
        game.update(1.0 / 60.0)
        game.render(surface)

    # Simular 1er golpe al aire (whiff_streak debe guardarse en 1)
    event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE})
    game.phase = PunchAlertMicrogame.PHASE_PLAY
    game.etapa = "juego"
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

    riesgosa = next(n for n in game.wave_queue if not n["is_safe"])
    riesgosa["resultado"] = "publicada"
    game.mandarAlPost(riesgosa)
    game.actualizarPost(0.7)
    assert riesgosa["idea"]["texto"] in game.textosPost
    assert riesgosa["idea"]["codigo"] in game.riesgosPublicados

    buena = next(n for n in game.wave_queue if n["is_safe"])
    game.strikes = 1
    buena.update(spawned=True, state="falling", y=float(game.hit_zone_y_max + 30))
    game.update(1.0 / 60.0)
    assert game.strikes == 1  # dejar pasar una tarjeta segura ya no devuelve vidas (commit 1fdd621)
    assert buena["resultado"] == "publicada"

    game.empezarPublicacion(True)
    for _ in range(int(3.6 * 60)):
        game.update(1.0 / 60.0)
    assert game.is_finished
    assert game.lineasEnsenanza[0] in ensenanzasRiesgo.values()
    assert (riesgosa["idea"], "publicada") in game.repaso
    assert (buena["idea"], "publicada") in game.repaso
    game.render(surface)

    print("TEST STANDALONE PASSED: PunchAlertMicrogame funciona correctamente.")

if __name__ == "__main__":
    test_punch_alert_standalone()
