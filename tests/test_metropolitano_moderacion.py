import os
import pytest
import pygame

# Ejecución en modo headless
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

from microgames.metropolitano_moderacion import MetropolitanoModeracionMicrogame

@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pygame.init()
    pygame.font.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1920, 1080))
    yield

def test_keyboard_arrow_navigation():
    game = MetropolitanoModeracionMicrogame()
    game.enter()
    game.phase = game.PHASE_PLAY
    assert game.grid_row == 1
    assert game.grid_col == 1

    # Mover a la derecha
    ev_right = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    game.handle_event(ev_right)
    assert game.grid_col == 2

    # Mover arriba
    ev_up = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)
    game.handle_event(ev_up)
    assert game.grid_row == 0
    assert game.grid_col == 2

    # Mover a la izquierda dos veces
    ev_left = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
    game.handle_event(ev_left)
    game.handle_event(ev_left)
    assert game.grid_col == 0

def test_spritesheet_classification_toxic_and_healthy():
    game = MetropolitanoModeracionMicrogame()
    game.enter()
    # 5 filas x 8 columnas = 40 celdas
    # Filas 0..2 (3 filas x 8 cols = 24 hinchas sanos)
    # Filas 3..4 (2 filas x 8 cols = 16 barras bravas tóxicos)
    assert len(game.healthy_sprites) == 24
    assert len(game.toxic_sprites) == 16

def test_hammer_strike_toxic_bans():
    game = MetropolitanoModeracionMicrogame()
    game.enter()
    game.phase = game.PHASE_PLAY

    # Forzar un slot tóxico
    slot = game.slots[0]
    slot["is_toxic"] = True
    slot["banned_anim"] = 0.0

    # Click dentro del slot
    click_pos = (slot["rect"].centerx, slot["rect"].centery)
    game._on_hammer_strike(click_pos)

    assert game.bans_count == 1
    assert slot["banned_anim"] > 0.0

def test_hammer_strike_innocent_stuns_and_decreases_progress():
    game = MetropolitanoModeracionMicrogame()
    game.enter()
    game.phase = game.PHASE_PLAY
    game.bans_count = 3  # Tenía 3 gemas llenas

    # Forzar un slot sano
    slot = game.slots[1]
    slot["is_toxic"] = False
    slot["banned_anim"] = 0.0

    click_pos = (slot["rect"].centerx, slot["rect"].centery)
    game._on_hammer_strike(click_pos)

    # Resta de progreso verificada
    assert game.bans_count == 2
    assert game.innocent_hits == 1
    assert game.hammer_stun_timer > 0.0  # Martillo aturdido

def test_toxic_population_between_2_and_3():
    game = MetropolitanoModeracionMicrogame()
    game.enter()
    game.phase = game.PHASE_PLAY

    # Verificar que el spawner mantiene entre 2 y 3 barras bravas activos
    game.update(0.1)
    toxic_count = sum(1 for s in game.slots if s["is_toxic"] and s["banned_anim"] <= 0.0)
    assert 2 <= toxic_count <= 3

def test_toxic_does_not_respawn_in_same_slot_after_ban():
    game = MetropolitanoModeracionMicrogame()
    game.enter()
    game.phase = game.PHASE_PLAY

    slot = game.slots[0]
    slot["is_toxic"] = True
    slot["banned_anim"] = 0.0

    # Martillar
    game._on_hammer_strike((slot["rect"].centerx, slot["rect"].centery))
    assert slot["banned_anim"] > 0.0
    assert slot["just_banned"] is True

    # Consumir el hit_stop de 40ms
    game.update_game(0.05)

    # Avanzar tiempo para que termine la animación de ban
    slot["banned_anim"] = 0.01
    game.update_game(0.02)

    # Al reaparecer en esa misma casilla, NO puede ser barra brava
    assert slot["is_toxic"] is False

def test_victory_condition():
    won_result = [False]
    def on_done(res):
        won_result[0] = res

    game = MetropolitanoModeracionMicrogame(on_complete_callback=on_done)
    game.enter()
    game.phase = game.PHASE_PLAY

    # Simular 10 baneos
    game.bans_count = 10
    game.update_game(0.016)

    assert game.is_won is True
    assert game.phase == game.PHASE_OUTRO

def test_timeout_defeat_condition():
    won_result = [None]
    def on_done(res):
        won_result[0] = res

    game = MetropolitanoModeracionMicrogame(on_complete_callback=on_done)
    game.enter()
    game.phase = game.PHASE_PLAY
    game.bans_count = 5  # No alcanzó los 10

    # Agotar los 20 segundos
    game.update(20.5)

    assert game.is_won is False
    assert game.phase == game.PHASE_OUTRO

    # Avanzar el outro timer para disparar el callback
    game.update(game.outro_duration + 0.1)
    assert won_result[0] is False

def test_render_no_crash():
    game = MetropolitanoModeracionMicrogame()
    game.enter()
    surf = pygame.Surface((1920, 1080))
    game.render(surf)
    # Sin excepciones durante el render de todas las capas
    assert surf.get_size() == (1920, 1080)
