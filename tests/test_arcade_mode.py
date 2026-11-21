import os
import pygame
import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from core.settings import SettingsManager
from scenes.arcade_mode import ArcadeModeScene
from microgames.curramgram_go import CurramGramGoMicrogame
from microgames.emoji_catch import EmojiCatchMicrogame
from microgames.punch_alert import PunchAlertMicrogame

def test_arcade_mode_flow():
    print("Iniciando suite de verificación del Modo Arcade WarioWare...")
    settings = SettingsManager.get_instance()
    settings.data["arcade_high_score"] = 0
    settings.save()

    scene = ArcadeModeScene(character_id="westcol")
    assert scene.lives == 4, "Debe iniciar con 4 vidas"
    assert scene.score == 0, "Debe iniciar con score 0"
    assert scene.speed_multiplier == 1.0, "Velocidad inicial debe ser 1.0x"
    print("[OK] ArcadeModeScene inicializada con 4 vidas y velocidad 1.0x.")

    # 1. Simular victoria en 4 rondas consecutivas
    for r in range(1, 5):
        scene.phase = scene.STATE_INTERSTITIAL
        scene.phase_timer = 1.5
        scene.update(0.016)
        # Simular callback de victoria
        scene._on_microgame_result(won=True)
        assert scene.score == r
        print(f"[OK] Ronda {r} superada. Score acumulado: {scene.score}")

    # Verificar aumento de velocidad tras 4 victorias
    assert scene.speed_multiplier > 1.0, "La velocidad debió aumentar tras 4 victorias"
    assert scene.speed_just_increased is True
    print(f"[OK] Aumento de velocidad activado: {scene.speed_multiplier:.2f}x.")

    # 2. Simular pérdida de vidas sucesivas hasta Game Over
    assert scene.lives == 4
    for expected_lives in [3, 2, 1, 0]:
        scene._on_microgame_result(won=False)
        assert scene.lives == expected_lives
        print(f"[OK] Fallo registrado. Vidas restantes: {scene.lives}")

    # Transición al estado Game Over
    scene.phase = scene.STATE_RESULT
    scene.phase_timer = 1.0
    scene.update(0.016)
    assert scene.phase == scene.STATE_GAME_OVER
    print("[OK] Transición a STATE_GAME_OVER confirmada.")

    # Verificar que el récord se guardó en settings.json
    assert settings.get_arcade_high_score() == 4
    assert scene.is_new_record is True
    print("[OK] Récord histórico persistido en settings.json (+4 Racha).")

    # 3. Probar reinicio (Reintentar)
    scene._restart_arcade()
    assert scene.lives == 4
    assert scene.score == 0
    assert scene.speed_multiplier == 1.0
    assert scene.phase == scene.STATE_INTERSTITIAL
    print("[OK] Botón Reintentar resetea vidas a 4 y velocidad a 1.0x.")

    # 4. Probar lanzamiento de microjuego arcade
    from core.state_machine import StateMachine
    scene.state_machine = StateMachine()
    scene.round_num = 10
    scene._launch_next_microgame()
    assert scene.state_machine.current_state is not None
    assert type(scene.state_machine.current_state) in scene.microgame_pool
    print("[OK] Ronda 10: Lanzamiento confirmado de microjuego del catálogo arcade.")

    # 4. Renderizar frame de Game Over para evidencia
    scene._enter_game_over()
    test_screen = pygame.Surface((1920, 1080))
    scene.render(test_screen)
    art_path = "render_arcade_game_over.png"
    pygame.image.save(test_screen, art_path)
    print(f"[OK] Snapshot de Game Over guardado en: {art_path}")

    print("TODAS LAS PRUEBAS DEL MODO ARCADE PASARON SATISFACTORIAMENTE (EXIT 0).")

if __name__ == "__main__":
    test_arcade_mode_flow()


def test_arcade_result_survives_real_state_transition(monkeypatch):
    from core.microgame import BaseMicrogame
    from core.state_machine import StateMachine
    settings = SettingsManager.get_instance()
    monkeypatch.setitem(settings.data, "arcade_high_score", 0)
    monkeypatch.setattr(settings, "save", lambda: None)
    scene = ArcadeModeScene()
    machine = StateMachine()
    machine.change_state(scene)
    scene.score = 3
    scene.lives = 1
    scene.round_num = 5
    scene.speed_multiplier = 1.3
    class RoundGame(BaseMicrogame):
        def __init__(self, character_id="westcol", on_complete_callback=None):
            super().__init__(on_complete_callback=on_complete_callback)
    scene.microgame_pool = [RoundGame]
    scene._launch_next_microgame()
    game = machine.current_state
    game.phase = game.PHASE_PLAY
    game.time_left = 0.01
    machine.update(0.02)
    assert game.phase == game.PHASE_OUTRO
    machine.render(pygame.Surface((1920, 1080)))
    machine.update(game.outro_duration + 0.01)
    assert machine.current_state is scene
    assert scene.phase == scene.STATE_RESULT
    assert scene.score == 3
    assert scene.lives == 0
    assert scene.round_num == 6
    machine.update(scene.result_duration + 0.01)
    assert scene.phase == scene.STATE_GAME_OVER
    assert settings.get_arcade_high_score() == 3
    machine.render(pygame.Surface((1920, 1080)))
    exited = []
    scene.on_exit_callback = lambda: exited.append(True)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
    assert exited == [True]


def test_arcade_win_keeps_score_when_returning(monkeypatch):
    from core.microgame import BaseMicrogame
    from core.state_machine import StateMachine
    scene = ArcadeModeScene()
    machine = StateMachine()
    machine.change_state(scene)
    class RoundGame(BaseMicrogame):
        def __init__(self, character_id="westcol", on_complete_callback=None):
            super().__init__(on_complete_callback=on_complete_callback)
    scene.microgame_pool = [RoundGame]
    scene._launch_next_microgame()
    game = machine.current_state
    game.finish_game(True)
    machine.update(game.outro_duration + 0.01)
    assert machine.current_state is scene
    assert scene.score == 1
    assert scene.round_num == 2
    assert scene.phase == scene.STATE_RESULT


def test_arcade_launches_and_renders_malecon_after_another_round():
    from core.microgame import BaseMicrogame
    from core.state_machine import StateMachine
    from microgames.malecon_rueda import MaleconRuedaMicrogame
    class FirstRound(BaseMicrogame):
        def __init__(self, character_id="westcol", on_complete_callback=None):
            super().__init__(on_complete_callback=on_complete_callback)
    scene = ArcadeModeScene()
    machine = StateMachine()
    machine.change_state(scene)
    scene.microgame_pool = [FirstRound]
    machine.update(scene.interstitial_duration + 0.01)
    first = machine.current_state
    first.finish_game(True)
    machine.update(first.outro_duration + 0.01)
    machine.update(scene.result_duration + 0.01)
    scene.microgame_pool = [MaleconRuedaMicrogame]
    machine.update(scene.interstitial_duration + 0.01)
    assert isinstance(machine.current_state, MaleconRuedaMicrogame)
    canvas = pygame.Surface((1920, 1080))
    machine.render(canvas)
    machine.current_state.phase = BaseMicrogame.PHASE_PLAY
    machine.update(0.1)
    machine.render(canvas)
    assert scene.score == 1 and scene.round_num == 2


def test_all_registered_arcade_games_render_on_entry():
    scene = ArcadeModeScene()
    canvas = pygame.Surface((1920, 1080))
    for cls in scene.microgame_pool:
        game = cls()
        game.render(canvas)
        game.phase = game.PHASE_PLAY
        if game.paloma_intro:
            game.paloma_intro.done = True
        game.render(canvas)
        if hasattr(game, "cleanup"):
            game.cleanup()


@pytest.mark.parametrize("game_class", [
    CurramGramGoMicrogame,
    EmojiCatchMicrogame,
    PunchAlertMicrogame,
])
def test_arcade_real_game_loss_reaches_score_screen(game_class, monkeypatch):
    from core.state_machine import StateMachine
    settings = SettingsManager.get_instance()
    monkeypatch.setitem(settings.data, "arcade_high_score", 0)
    monkeypatch.setattr(settings, "save", lambda: None)
    scene = ArcadeModeScene()
    assert game_class in scene.microgame_pool
    machine = StateMachine()
    machine.change_state(scene)
    scene.score = 2
    scene.lives = 1
    scene.microgame_pool = [game_class]
    scene._launch_next_microgame()
    game = machine.current_state
    assert isinstance(game, game_class)
    assert game.time_left == game.time_limit
    if hasattr(game, "game"):
        assert game.game.tiempo == game.time_limit
    if game.paloma_intro:
        game.paloma_intro.done = True
    canvas = pygame.Surface((1920, 1080))
    game.finish_game(False)
    machine.render(canvas)
    machine.update(game.outro_duration + 0.1)
    assert machine.current_state is scene
    assert scene.lives == 0 and scene.score == 2
    machine.render(canvas)
    machine.update(scene.result_duration + 0.1)
    assert scene.phase == scene.STATE_GAME_OVER
    assert settings.get_arcade_high_score() == 2
    machine.render(canvas)
    game.update(game.outro_duration + 0.1)
    assert scene.lives == 0 and scene.score == 2  # El callback no se repite.
    scene._restart_arcade()
    assert scene.lives == 4 and scene.score == 0
