import os
import sys
import pygame

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from microgames.uninorte_concentrate import (
    UninorteConcentrateMicrogame,
    Distraction,
    Student
)


def test_uninorte_concentrate_components_and_loop() -> None:
    """Verifica empíricamente los 5 componentes y las reglas de diseño de '¡Concéntrate, llave!'."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    pygame.font.init()
    pygame.display.set_mode((1920, 1080), pygame.NOFRAME)

    game = UninorteConcentrateMicrogame(character_id="valdiri")
    game.paloma_intro = None  # prueba del juego en sí, sin el diálogo de la Paloma (como en el Modo Historia)
    surface = pygame.Surface((1920, 1080))

    # 1. Validar carga de las 6 nubes de redes sociales y duración de 25s
    assert game.time_limit == 25.0
    assert len(game.cloud_sprites) == 6
    assert len(game.student.study_frames) == 2
    assert game.student.is_studying is True

    # 2. Avanzar la fase INTRO hasta entrar en PHASE_PLAY
    for _ in range(120):
        game.update(1.0 / 60.0)
        game.render(surface)

    assert game.phase == UninorteConcentrateMicrogame.PHASE_PLAY
    initial_progress = game.progress_bar.progress
    assert initial_progress > 0.0

    # 3. Simular una nube que alcanza al estudiante -> se adhiere y detiene el progreso
    cloud = Distraction(
        network_idx=0,
        sprite=game.cloud_sprites[0],
        start_pos=(game.student.base_x, game.student.base_y - 20.0),
        target_pos=(game.student.base_x, game.student.base_y - 20.0),
        speed=250.0
    )
    game.clouds.append(cloud)
    game.update_game(1.0 / 60.0)

    assert cloud.state == Distraction.STATE_ATTACHED
    assert game.student.state == Student.STATE_DISTRACTED
    assert game.student.is_studying is False

    # Verificar que la barra de progreso NO retrocede ni avanza mientras está distraído
    frozen_progress = game.progress_bar.progress
    for _ in range(30):
        game.update_game(1.0 / 60.0)
    assert game.progress_bar.progress == frozen_progress

    # 4. Mover el cursor virtual sobre la nube adherida y presionar ESPACIO para reventarla
    game.cursor.x = cloud.x
    game.cursor.y = cloud.y
    space_event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE})
    game.handle_game_event(space_event)

    assert cloud.state == Distraction.STATE_POPPING
    assert game.student.is_studying is True
    assert game.score_manager.score >= 60
    assert game.score_manager.streak == 1

    # 5. Al recuperar el foco, el progreso vuelve a subir
    game.update_game(0.5)
    assert game.progress_bar.progress > frozen_progress

    # 6. Verificar condición de victoria instantánea al llegar al 100%
    game.progress_bar.progress = 99.5
    game.update_game(0.5)
    assert game.progress_bar.completed is True
    assert game.score_manager.task_bonus_awarded is True
    assert game.is_won is True
    assert game.phase == UninorteConcentrateMicrogame.PHASE_OUTRO

    res = game.get_result_data()
    assert res["task_progress"] == 100.0
    assert res["score"] >= 400


if __name__ == "__main__":
    test_uninorte_concentrate_components_and_loop()
    print("ALL TESTS PASSED!")
