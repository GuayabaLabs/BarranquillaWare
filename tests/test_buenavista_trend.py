import os
import sys
import pytest
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from microgames.buenavista_trend import BuenavistaTrendMicrogame, MusicalNoteEvent, EN_BARRANQUILLA_BEATMAP_DATA, IMITADORA_BEATMAP_DATA
from microgames.buenavista_trend.beatmap import BPM, beat


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pygame.init()
    pygame.font.init()
    pygame.display.set_mode((1920, 1080), pygame.NOFRAME)
    yield


def test_buenavista_trend_assets_and_geometry():
    """
    Valida criterios de aceptación 1 a 5:
    - Fondo de Buenavista cargado a 1920x1080.
    - Celular centrado ocupando ~85% de la altura (918 px) sin deformarse.
    - 4 carriles interiores alineados con las zonas dibujadas y línea de impacto proporcional.
    - 8 sprites extraídos en cuadrícula matemática uniforme 4x2 (4 normales + 4 activadas).
    - Rectángulo de clipping que impide atravesar bordes del celular o el encabezado REC.
    """
    game = BuenavistaTrendMicrogame(character_id="westcol")

    assert game.time_limit == 30.0
    assert game.lives == 5
    assert game.max_lives == 5

    # Celular centrado al 85% de 1080 = 918 px
    assert game.phone_rect.height == int(round(1080 * 0.85))
    assert game.phone_rect.centerx == 1920 // 2
    assert game.phone_rect.centery == 1080 // 2

    # 4 carriles de izquierda a derecha dentro del celular
    assert len(game.lane_rects) == 4
    assert len(game.lane_centers_x) == 4
    for i in range(4):
        assert game.phone_rect.left < game.lane_rects[i].left < game.lane_rects[i].right < game.phone_rect.right
        if i > 0:
            assert game.lane_centers_x[i] > game.lane_centers_x[i - 1]

    # El área jugable está estrictamente contenida debajo del encabezado REC y encima del borde inferior
    assert game.playable_clip_rect.top > game.phone_rect.top + 80
    assert game.playable_clip_rect.bottom < game.phone_rect.bottom - 20

    # Extracción 4x2 (4 teclas normales y 4 teclas activadas con brillo)
    assert len(game.normal_tile_sprites) == 4
    assert len(game.active_tile_sprites) == 4
    assert len(game.raw_grid_cells) == 2
    assert len(game.raw_grid_cells[0]) == 4
    assert len(game.raw_grid_cells[1]) == 4

    for spr in game.normal_tile_sprites + game.active_tile_sprites:
        assert spr.get_width() < min(r.width for r in game.lane_rects)

    game.cleanup()


def test_beatmap_progressive_difficulty_and_lane_balance():
    """
    Valida que el mapa de notas de 'En Barranquilla Me Quedo' cumpla con:
    - Progresión de dificultad en 3 tramos (0-10s, 10-20s, 20-30s).
    - Distribución equilibrada en los 4 carriles (0, 1, 2, 3).
    - Sin notas simultáneas imposibles en los primeros segundos.
    """
    game = BuenavistaTrendMicrogame(character_id="westcol")
    events = game.musical_events
    assert len(events) == len(IMITADORA_BEATMAP_DATA)
    assert len(events) >= 35

    phase1 = [e for e in events if e.impact_time < 10.0]
    phase2 = [e for e in events if 10.0 <= e.impact_time < 20.0]
    phase3 = [e for e in events if e.impact_time >= 20.0]

    assert len(phase1) > 0 and len(phase2) > len(phase1) and len(phase3) >= len(phase2)

    # Velocidad progresiva promedio mayor en cada fase
    avg_spd_1 = sum(e.fall_speed for e in phase1) / len(phase1)
    avg_spd_2 = sum(e.fall_speed for e in phase2) / len(phase2)
    avg_spd_3 = sum(e.fall_speed for e in phase3) / len(phase3)
    assert avg_spd_1 < avg_spd_2 < avg_spd_3

    # Todos los 4 carriles y los 4 tipos de sprites están representados de forma equilibrada
    lanes_used = {e.lane for e in events}
    sprites_used = {e.sprite_type for e in events}
    assert lanes_used == {0, 1, 2, 3}
    assert sprites_used == {0, 1, 2, 3}

    # Sin notas simultáneas en Fase 1
    for i in range(1, len(phase1)):
        assert phase1[i].impact_time - phase1[i - 1].impact_time >= 0.45

    game.cleanup()


def test_controls_hit_detection_and_anti_hold():
    """
    Valida controles D, F, J, K, ventana de acierto (Perfecto ±80ms / Bien ±150ms)
    y prohibición de aciertos repetidos al mantener una tecla pulsada.
    """
    game = BuenavistaTrendMicrogame(character_id="westcol")
    game.phase = game.PHASE_PLAY

    # Tomar la primera nota (carril 0 -> tecla D, impacto en 1.579s)
    first_note = game.musical_events[0]
    first_note.spawned = True
    first_note.state = "falling"

    # Posicionar el reloj musical dentro de la ventana Perfecto (+30ms del impacto)
    game.song_elapsed = first_note.impact_time + 0.030
    key_d = pygame.K_d

    ev_down = pygame.event.Event(pygame.KEYDOWN, key=key_d)
    game.handle_event(ev_down)

    assert first_note.state == "hit"
    assert game.hits_perfect == 1
    assert game.lives == 5
    assert len(game.like_particles) > 0

    # Intentar enviar otro KEYDOWN de la misma tecla D sin haberla soltado (simula mantener pulsada)
    second_note = game.musical_events[4]  # Otra nota en carril 0
    second_note.spawned = True
    second_note.state = "falling"
    game.song_elapsed = second_note.impact_time

    # Sin KEYUP previo, el evento sostenido es ignorado
    game.handle_event(ev_down)
    assert second_note.state == "falling"
    assert game.hits_perfect == 1

    # Al soltar la tecla (KEYUP) y volver a pulsar dentro de la ventana Bien (+110ms):
    game.handle_event(pygame.event.Event(pygame.KEYUP, key=key_d))
    game.song_elapsed = second_note.impact_time + 0.110
    game.handle_event(ev_down)

    assert second_note.state == "hit"
    assert game.hits_good == 1
    assert game.lives == 5

    game.cleanup()


def test_miss_penalties_no_duplicate_life_loss_and_game_over():
    """
    Valida que:
    - Una misma nota nunca produzca más de un fallo.
    - Las pulsaciones incorrectas descuenten 1 sola vida con intervalo de protección.
    - Al perder las 5 vidas antes de los 30s se declare la derrota y se notifique al callback.
    """
    results = []
    game = BuenavistaTrendMicrogame(character_id="westcol", on_complete_callback=lambda w: results.append(w))
    game.phase = game.PHASE_PLAY

    note = game.musical_events[0]
    note.spawned = True
    note.state = "falling"

    # 1. Pulsar demasiado pronto sobre la nota en su carril -> falla la nota (-1 vida)
    game.song_elapsed = note.impact_time - 0.30
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
    game.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_d))
    assert game.lives == 4
    assert note.penalized is True

    # Cuando el tiempo avanza y la nota cruza la zona de impacto, NO debe volver a restar otra vida
    game.song_elapsed = note.impact_time + 0.30
    game.update_game(0.016)
    assert game.lives == 4

    # 2. Pulsar un carril incorrecto (tecla K cuando no hay nota en carril 3) tras pasar el cooldown
    game.wrong_press_cooldown = 0.0
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k))
    game.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_k))
    assert game.lives == 3

    # Otra pulsación errónea inmediata dentro del intervalo de protección NO resta vida extra
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f))
    game.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_f))
    assert game.lives == 3

    for vidasEsperadas in (2, 1):
        game.wrong_press_cooldown = 0.0
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k))
        game.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_k))
        assert game.lives == vidasEsperadas

    # 3. Una nota atraviesa la zona de pulsación sin ser activada -> pierde la última vida -> DERROTA
    note2 = game.musical_events[1]
    note2.spawned = True
    note2.state = "falling"
    game.song_elapsed = note2.impact_time + 0.25
    game.update_game(0.016)

    assert game.lives == 0
    assert game.is_finished is True
    assert game.is_won is False
    assert game.phase == game.PHASE_OUTRO

    game.update(game.outro_duration + 0.1)
    assert results == [False]

    game.cleanup()


def test_survival_victory_at_30_seconds_and_full_render():
    """
    Valida que al llegar a los 30 segundos conservando al menos 1 corazón el jugador gane,
    y verifica el renderizado limpio de las 4 capas sin excepciones.
    """
    results = []
    game = BuenavistaTrendMicrogame(character_id="westcol", on_complete_callback=lambda w: results.append(w))
    surface = pygame.Surface((1920, 1080))

    # Render en INTRO
    game.render(surface)

    # Pasar a PLAY con 1 corazón restante y 0.05s en el reloj
    game.phase = game.PHASE_PLAY
    game.lives = 1
    game.time_left = 0.05

    game.update(0.10)
    assert game.is_finished is True
    assert game.is_won is True
    assert game.phase == game.PHASE_OUTRO

    # Render en OUTRO (incluyendo banner y mensaje educativo)
    game.render(surface)

    game.update(game.outro_duration + 0.1)
    assert results == [True]

    game.cleanup()


def test_camera_mode_prevents_double_penalty_and_grants_invulnerability():
    """Valida despenalización de doble error y ventana de gracia de 0.35s con cámara activa."""
    from types import SimpleNamespace

    game = BuenavistaTrendMicrogame(character_id="westcol")
    game.phase = game.PHASE_PLAY
    game.camera_input = SimpleNamespace(
        enabled=True,
        is_hand_present=lambda: True,
        consume_finger=lambda _lane: False,
    )

    # 1. Nota ya marcada como missed en carril 0: un dedo activado poco después no resta 2da vida.
    note = game.musical_events[0]
    note.spawned = True
    note.state = "falling"
    game.song_elapsed = note.impact_time + game.good_window + 0.02
    game.update_game(0.016)
    assert note.state == "missed"
    assert game.lives == 4
    assert game.invulnerability_timer == pytest.approx(0.35, abs=0.02)

    # Incluso tras expirar la invulnerabilidad, una nota recién marcada missed en ese carril no doble-penaliza.
    game.invulnerability_timer = 0.0
    game.wrong_press_cooldown = 0.0
    game._process_lane_press(note.lane)
    assert game.lives == 4

    # 2. Pulsación errónea en otro carril activa cooldown ampliado (0.42s) e invulnerabilidad (0.35s).
    other_lane = (note.lane + 1) % 4
    game.musical_events = [ev for ev in game.musical_events if ev.lane != other_lane]
    game._process_lane_press(other_lane)
    assert game.lives == 3
    assert game.wrong_press_cooldown == pytest.approx(0.42, abs=0.01)
    assert game.invulnerability_timer == pytest.approx(0.35, abs=0.01)

    # Durante la ventana de invulnerabilidad, otra nota que se pase tampoco descuenta corazón.
    note2 = next(ev for ev in game.musical_events if ev is not note and ev.state != "missed")
    note2.spawned = True
    note2.state = "falling"
    game._mark_note_missed(note2, reason="¡SE PASÓ!")
    assert game.lives == 3

    game.cleanup()


def test_audio_mp3_fallback_and_preload(monkeypatch):
    """Valida ruta .ogg principal, fallback automático a .mp3 y ejecución segura sin archivo."""
    ogg_path = os.path.join("assets", "en_barranquilla_me_quedo_piano.ogg")
    mp3_path = os.path.join("assets", "en_barranquilla_me_quedo_piano.mp3")

    loaded_paths = []
    played_calls = []

    monkeypatch.setattr(pygame.mixer, "get_init", lambda: True)
    monkeypatch.setattr(pygame.mixer.music, "load", lambda p: loaded_paths.append(p))
    monkeypatch.setattr(pygame.mixer.music, "play", lambda **kw: played_calls.append(kw))

    real_exists = os.path.exists

    # Caso A: .ogg ausente y .mp3 presente -> precarga y reproduce .mp3 conservando track nominal
    def fake_exists_mp3(path):
        if os.path.normpath(path) == os.path.normpath(ogg_path):
            return False
        if os.path.normpath(path) == os.path.normpath(mp3_path):
            return True
        return real_exists(path)

    monkeypatch.setattr(os.path, "exists", fake_exists_mp3)
    game_a = BuenavistaTrendMicrogame(character_id="westcol")
    assert game_a.music_track_name == "en_barranquilla_me_quedo_piano.ogg"
    assert loaded_paths == [mp3_path]
    game_a._start_music_if_needed()
    assert game_a.audio.current_track == "en_barranquilla_me_quedo_piano.ogg"
    assert len(played_calls) == 1
    game_a.cleanup()

    # Caso B: ni .ogg ni .mp3 presentes -> silencio seguro y song_elapsed avanza con dt
    loaded_paths.clear()
    played_calls.clear()

    def fake_exists_none(path):
        if os.path.normpath(path) in (os.path.normpath(ogg_path), os.path.normpath(mp3_path)):
            return False
        if "imitadora_ost_piano_tiles_microjuego" in str(path):  # ni la canción de respaldo
            return False
        return real_exists(path)

    monkeypatch.setattr(os.path, "exists", fake_exists_none)
    game_b = BuenavistaTrendMicrogame(character_id="westcol")
    game_b.phase = game_b.PHASE_PLAY
    game_b._start_music_if_needed()
    assert loaded_paths == []
    game_b.update_game(0.05)
    assert game_b.song_elapsed == pytest.approx(0.05, abs=1e-4)
    game_b.cleanup()


def test_spritesheet_no_bleed_and_union_bbox_balance():
    """Valida ausencia de sangrado entre celdas 4x2 y proporciones equilibradas por caja unión."""
    sheet_path = os.path.join("assets", "spritesheet_teclas_costenas_piano.png")
    sheet = pygame.image.load(sheet_path).convert_alpha()
    sw, sh = sheet.get_size()
    cw, ch = sw // 4, sh // 2

    for r in range(2):
        for c in range(4):
            cell = sheet.subsurface((c * cw, r * ch, cw, ch))
            for x in range(cw):
                assert cell.get_at((x, 0)).a == 0
                assert cell.get_at((x, ch - 1)).a == 0
            for y in range(ch):
                assert cell.get_at((0, y)).a == 0
                assert cell.get_at((cw - 1, y)).a == 0

    game = BuenavistaTrendMicrogame(character_id="westcol")
    max_dims = []
    for i in range(4):
        n_spr = game.normal_tile_sprites[i]
        a_spr = game.active_tile_sprites[i]
        assert n_spr.get_size() == a_spr.get_size()
        bbox = n_spr.get_bounding_rect(min_alpha=80)
        assert bbox.width > 0 and bbox.height > 0
        max_dims.append(max(bbox.width, bbox.height))

    assert min(max_dims) >= 0.72 * max(max_dims)
    game.cleanup()


def test_beatmap_salsa_grid_spacing_and_lane_sprite_alignment():
    """Valida compás 4/4 a 114 BPM, alineación 1:1 carril==icono y sin repeticiones consecutivas."""
    assert BPM == 114.0
    assert callable(beat)

    game = BuenavistaTrendMicrogame(character_id="westcol")
    events = game.musical_events

    for i, ev in enumerate(events):
        assert ev.lane == ev.sprite_type
        eighth_pos = ev.impact_time * (BPM / 60.0) * 2.0
        assert abs(round(eighth_pos) - eighth_pos) < 0.02
        if i > 0:
            assert ev.impact_time - events[i - 1].impact_time >= 0.25
            assert ev.lane != events[i - 1].lane

    game.cleanup()


def test_note_at_hit_line_does_not_overlap_key_badges():
    """Valida separación vertical entre notas en hit_line_y y los badges [D][F][J][K]/(X)(A)(Y)(B)."""
    game = BuenavistaTrendMicrogame(character_id="westcol")
    assert hasattr(game, "key_badge_rects")
    assert len(game.key_badge_rects) == 4

    for i in range(4):
        badge_r = game.key_badge_rects[i]
        assert game.phone_rect.contains(badge_r)
        spr_size = game.normal_tile_sprites[i].get_size()
        note_rect = pygame.Rect(0, 0, spr_size[0], spr_size[1])
        note_rect.center = (game.lane_centers_x[i], game.hit_line_y)
        assert not note_rect.colliderect(badge_r)
        assert note_rect.bottom <= badge_r.top

    game.cleanup()


def test_dt_animations_lane_glow_and_squash_stretch():
    """Valida decaimiento con dt de yellow_glow_alpha, lane_press_timers y hit_anim_timer + render."""
    game = BuenavistaTrendMicrogame(character_id="westcol")
    surface = pygame.Surface((1920, 1080))
    game.phase = game.PHASE_PLAY

    ev = game.musical_events[0]
    ev.spawned = True
    ev.state = "falling"
    game.song_elapsed = ev.impact_time
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))

    assert ev.state == "hit"
    assert game.yellow_glow_alpha > 0.0
    assert game.lane_press_timers[0] > 0.0
    assert ev.hit_anim_timer > 0.0

    initial_glow = game.yellow_glow_alpha
    game.update_game(0.08)
    game.render(surface)
    assert 0.0 < game.yellow_glow_alpha < initial_glow

    game.update_game(0.20)
    game.render(surface)
    assert game.yellow_glow_alpha == 0.0
    assert game.lane_press_timers[0] == 0.0
    assert ev.state == "done"

    game.cleanup()


def test_gamepad_buttons_parity_with_gamepad_button_keys():
    """Valida paridad exacta entre GAMEPAD_BUTTONS, GAMEPAD_BUTTON_KEYS y eventos JOYBUTTONDOWN."""
    assert set(BuenavistaTrendMicrogame.GAMEPAD_BUTTONS.keys()) == set(BuenavistaTrendMicrogame.GAMEPAD_BUTTON_KEYS.keys())
    for btn, key in BuenavistaTrendMicrogame.GAMEPAD_BUTTON_KEYS.items():
        lane = BuenavistaTrendMicrogame.GAMEPAD_BUTTONS[btn]
        assert BuenavistaTrendMicrogame.LANE_KEYS[lane] == key

    game = BuenavistaTrendMicrogame(character_id="westcol")
    game.phase = game.PHASE_PLAY
    ev = game.musical_events[0]  # Carril 0 -> D -> botón X (2)
    ev.spawned = True
    ev.state = "falling"
    game.song_elapsed = ev.impact_time

    game.handle_event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=2))
    assert ev.state == "hit"
    assert game.hits_perfect == 1

    game.cleanup()


def test_arcade_short_time_limit_keeps_snappy_outro():
    """Valida que en Modo Arcade (time_limit < 20s) no se fuerce outro largo de 17s."""
    game = BuenavistaTrendMicrogame(character_id="westcol")
    game.time_limit = 6.5
    game.time_left = 6.5
    game.phase = game.PHASE_PLAY

    game.update(6.6)
    assert game.is_finished is True
    assert game.phase == game.PHASE_OUTRO
    assert game.outro_duration <= 3.0

    game.cleanup()


@pytest.fixture(autouse=True)
def _trend_sin_dialogo_paloma(monkeypatch):
    """Estas pruebas son del juego en sí: arrancan sin el diálogo de la Paloma (como en el Modo Historia)."""
    from microgames.buenavista_trend import BuenavistaTrendMicrogame as _Trend
    monkeypatch.setattr(_Trend, "dialogoPaloma", None)
