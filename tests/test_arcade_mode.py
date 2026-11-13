import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from core.settings import SettingsManager
from scenes.arcade_mode import ArcadeModeScene

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

    # 4. Probar activación de Boss Stage en ronda 10
    from core.state_machine import StateMachine
    from microgames.batalla_flores_boss import BatallaFloresBossMicrogame
    scene.state_machine = StateMachine()
    scene.round_num = 10
    scene._launch_next_microgame()
    assert isinstance(scene.state_machine.current_state, BatallaFloresBossMicrogame)
    print("[OK] Ronda 10: Activación confirmada de Batalla de Flores (Boss Stage).")

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
