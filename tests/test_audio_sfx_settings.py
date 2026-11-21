import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from types import SimpleNamespace
from unittest.mock import MagicMock
import numpy as np
import pygame
import pytest

from core.audio_manager import AudioManager
from core.map_settings import MapSettingsState
from core.settings import SettingsManager


@pytest.fixture(autouse=True)
def _pygame_and_restore_audio():
    pygame.init()
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)

    settings = SettingsManager.get_instance()
    audio = AudioManager.get_instance()
    orig_sound_enabled = audio.sound_enabled
    orig_music_enabled = audio.music_enabled
    orig_sfx_vol = audio.sfx_volume
    orig_music_vol = audio.music_volume
    orig_bgm_scale = audio._bgm_volume_scale

    yield

    audio._bgm_volume_scale = orig_bgm_scale
    audio.sound_enabled = orig_sound_enabled
    audio.music_enabled = orig_music_enabled
    audio.set_sfx_volume(orig_sfx_vol)
    audio.set_music_volume(orig_music_vol)
    settings.set("sound_enabled", orig_sound_enabled)
    settings.set("music_enabled", orig_music_enabled)


def test_audio_manager_procedural_sfx_peaks_and_multipliers():
    audio = AudioManager.get_instance()
    sound_attrs = [
        "_hover_sound",
        "_click_sound",
        "_iguana_sound",
        "_pigeon_sound",
        "_win_sound",
        "_lose_sound",
        "_drum_sound",
        "_whistle_sound",
        "_jump_sound",
        "_hit_sound",
        "_miss_sound",
    ]
    for attr in sound_attrs:
        snd = getattr(audio, attr)
        assert snd is not None, f"{attr} should be generated"
        arr = pygame.sndarray.array(snd).astype(np.float64) / 32767.0
        peak = float(np.max(np.abs(arr)))
        assert 0.50 <= peak <= 1.0, f"{attr} peak {peak:.3f} out of [0.50, 1.0]"

    audio.sound_enabled = True
    audio.set_sfx_volume(1.0)
    play_methods = [
        ("play_hover", "_hover_sound"),
        ("play_click", "_click_sound"),
        ("play_iguana", "_iguana_sound"),
        ("play_pigeon", "_pigeon_sound"),
        ("play_win", "_win_sound"),
        ("play_lose", "_lose_sound"),
        ("play_drum", "_drum_sound"),
        ("play_whistle", "_whistle_sound"),
        ("play_jump", "_jump_sound"),
        ("play_hit", "_hit_sound"),
        ("play_miss", "_miss_sound"),
    ]
    for method_name, attr in play_methods:
        mock_snd = MagicMock()
        orig = getattr(audio, attr)
        setattr(audio, attr, mock_snd)
        try:
            getattr(audio, method_name)()
            mock_snd.set_volume.assert_called_once()
            vol_used = mock_snd.set_volume.call_args[0][0]
            assert vol_used >= 0.50, f"{method_name} multiplier {vol_used} < 0.50"
            mock_snd.play.assert_called_once()
        finally:
            setattr(audio, attr, orig)


def test_audio_manager_play_sfx_respects_sound_enabled_and_dynamic_volume():
    audio = AudioManager.get_instance()
    mock_snd = MagicMock()

    audio.sound_enabled = False
    audio.set_sfx_volume(0.8)
    assert audio.play_sfx(mock_snd) is None
    mock_snd.play.assert_not_called()

    # Also all play_* methods must not play when sound_enabled=False
    for method_name, attr in [
        ("play_hover", "_hover_sound"),
        ("play_click", "_click_sound"),
        ("play_iguana", "_iguana_sound"),
        ("play_pigeon", "_pigeon_sound"),
        ("play_win", "_win_sound"),
        ("play_lose", "_lose_sound"),
        ("play_drum", "_drum_sound"),
        ("play_whistle", "_whistle_sound"),
        ("play_jump", "_jump_sound"),
        ("play_hit", "_hit_sound"),
        ("play_miss", "_miss_sound"),
    ]:
        spy = MagicMock()
        orig = getattr(audio, attr)
        setattr(audio, attr, spy)
        try:
            getattr(audio, method_name)()
            spy.play.assert_not_called()
        finally:
            setattr(audio, attr, orig)

    audio.sound_enabled = True
    for target_vol in (0.0, 0.25, 0.8, 1.0):
        mock_snd.reset_mock()
        audio.set_sfx_volume(target_vol)
        audio.play_sfx(mock_snd, volume_scale=1.0)
        mock_snd.set_volume.assert_called_once_with(pytest.approx(target_vol))
        mock_snd.play.assert_called_once()


def test_map_settings_state_keyboard_joyhat_and_activate():
    pygame.display.set_mode((1920, 1080))
    audio = AudioManager.get_instance()
    settings = SettingsManager.get_instance()

    audio.sound_enabled = True
    audio.music_enabled = True
    audio.set_sfx_volume(0.50)
    audio.set_music_volume(0.50)

    state = MapSettingsState()
    state.index = 0  # "sound"

    # Keyboard right -> +0.05
    state.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    assert audio.sfx_volume == pytest.approx(0.55)
    assert settings.get("sfx_volume") == pytest.approx(0.55)

    # JOYHATMOTION horizontal left -> -0.05
    state.handle_event(pygame.event.Event(pygame.JOYHATMOTION, hat=0, value=(-1, 0)))
    assert audio.sfx_volume == pytest.approx(0.50)
    assert settings.get("sfx_volume") == pytest.approx(0.50)

    # JOYHATMOTION horizontal right -> +0.05
    state.handle_event(pygame.event.Event(pygame.JOYHATMOTION, hat=0, value=(1, 0)))
    assert audio.sfx_volume == pytest.approx(0.55)

    # Activate toggles sound
    state._activate()
    assert audio.sound_enabled is False
    assert settings.get("sound_enabled") is False
    state._activate()
    assert audio.sound_enabled is True

    # Move to "music" via JOYHATMOTION down
    state.handle_event(pygame.event.Event(pygame.JOYHATMOTION, hat=0, value=(0, -1)))
    assert state.items[state.index] == "music"
    state.handle_event(pygame.event.Event(pygame.JOYHATMOTION, hat=0, value=(1, 0)))
    assert audio.music_volume == pytest.approx(0.55)
    assert settings.get("music_volume") == pytest.approx(0.55)

    state._activate()
    assert audio.music_enabled is False
    assert settings.get("music_enabled") is False


def test_dynamic_sfx_volume_propagation_uninorte_sprint_and_punch_alert():
    pygame.display.set_mode((1920, 1080))
    audio = AudioManager.get_instance()
    audio.sound_enabled = True
    audio.set_sfx_volume(0.8)

    from microgames.uninorte_sprint import UninorteSprintMicrogame
    from microgames.punch_alert.game import PunchAlertMicrogame

    sprint = UninorteSprintMicrogame()
    mock_voice = MagicMock()
    sprint.hit_sounds = [mock_voice]

    for vol in (0.8, 0.2, 1.0):
        mock_voice.reset_mock()
        audio.set_sfx_volume(vol)
        sprint._play_random_pasillo_voice()
        mock_voice.set_volume.assert_called_once_with(pytest.approx(vol))
        mock_voice.play.assert_called_once()

    punch = PunchAlertMicrogame()
    mock_punch_voice = MagicMock()
    mock_hit_sfx = MagicMock()
    punch.punch_voices = [mock_punch_voice]

    for vol in (0.8, 0.2, 1.0):
        mock_punch_voice.reset_mock()
        mock_hit_sfx.reset_mock()
        audio.set_sfx_volume(vol)
        punch._play_character_punch_voice()
        punch._play_sfx(mock_hit_sfx)
        mock_punch_voice.set_volume.assert_called_once_with(pytest.approx(vol))
        mock_punch_voice.play.assert_called_once()
        mock_hit_sfx.set_volume.assert_called_once_with(pytest.approx(vol))
        mock_hit_sfx.play.assert_called_once()


def test_gameplay_sfx_triggers_across_microgames(monkeypatch):
    pygame.display.set_mode((1920, 1080))

    from microgames.metropolitano_moderacion import MetropolitanoModeracionMicrogame
    from microgames.troja_baile import TrojaBaileMicrogame
    from microgames.buenavista_cine import BuenavistaCineMicrogame
    from microgames.aeropuerto_aterrizaje import AeropuertoAterrizajeMicrogame
    from microgames.malecon_rueda import MaleconRuedaMicrogame
    from microgames.ventana_colores import VentanaColoresMicrogame
    from microgames.uninorte_concentrate.game import UninorteConcentrateMicrogame

    def _spy_audio(game):
        calls = []
        for name in ("play_click", "play_hit", "play_miss", "play_jump", "play_pigeon", "play_drum", "play_whistle"):
            monkeypatch.setattr(
                game.audio,
                name,
                lambda n=name: calls.append(n),
                raising=False,
            )
        return calls

    # 1. MetropolitanoModeracionMicrogame
    metro = MetropolitanoModeracionMicrogame()
    calls = _spy_audio(metro)
    toxic_slot = next(s for s in metro.slots if s["is_toxic"])
    healthy_slot = next(s for s in metro.slots if not s["is_toxic"])
    metro._on_hammer_strike(toxic_slot["rect"].center)
    metro._on_hammer_strike(healthy_slot["rect"].center)
    assert "play_click" in calls
    assert "play_hit" in calls
    assert "play_miss" in calls

    # 2. TrojaBaileMicrogame
    troja = TrojaBaileMicrogame()
    calls = _spy_audio(troja)
    troja.phase = troja.PHASE_PLAY
    troja.handle_game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
    assert "play_click" in calls
    troja._sfx_cooldown = 0.0
    troja.angular_vel = 0.0
    troja.angle = troja.max_safe_angle * 0.8
    troja.update_game(0.016)
    assert "play_miss" in calls

    # 3. BuenavistaCineMicrogame
    cine = BuenavistaCineMicrogame()
    try:
        calls = _spy_audio(cine)
        cine._spawn_next_offense(3.0)
        assert "play_pigeon" in calls
        cine._on_player_shhed()
        assert "play_hit" in calls
        cine._apply_strike("test")
        assert "play_miss" in calls
    finally:
        cine.cleanup()

    # 4. AeropuertoAterrizajeMicrogame
    aero = AeropuertoAterrizajeMicrogame()
    calls = _spy_audio(aero)
    aero.plane_x = aero.runway_cx + 500
    aero._evaluate_landing()
    assert "play_miss" in calls

    # 6. MaleconRuedaMicrogame
    rueda = MaleconRuedaMicrogame()
    calls = _spy_audio(rueda)
    rueda.wheel_angle = 0.0  # far from 3*pi/2
    rueda._brake_wheel()
    assert "play_miss" in calls

    # 7. VentanaColoresMicrogame
    ventana = VentanaColoresMicrogame()
    calls = _spy_audio(ventana)
    wrong_idx = (ventana.target_color_idx + 1) % 4
    ventana._check_choice(wrong_idx)
    assert "play_miss" in calls

    # 8. UninorteConcentrateMicrogame
    conc = UninorteConcentrateMicrogame()
    calls = _spy_audio(conc)
    conc.clouds = []
    conc._trigger_pop_action()
    assert "play_miss" in calls


def test_punch_alert_procedural_peaks_and_sprint_jump_and_bgm_scaling(monkeypatch):
    pygame.display.set_mode((1920, 1080))
    audio = AudioManager.get_instance()

    from microgames.punch_alert.game import PunchAlertMicrogame
    from microgames.uninorte_sprint import UninorteSprintMicrogame
    from microgames.metropolitano_moderacion import MetropolitanoModeracionMicrogame
    from microgames.uninorte_concentrate.game import UninorteConcentrateMicrogame

    punch = PunchAlertMicrogame()
    for attr in ("snd_hit", "snd_whiff", "snd_safe", "snd_strike"):
        snd = getattr(punch, attr)
        assert snd is not None, f"punch_alert.{attr} should be generated"
        arr = pygame.sndarray.array(snd).astype(np.float64) / 32767.0
        peak = float(np.max(np.abs(arr)))
        assert 0.50 <= peak <= 1.0, f"punch_alert.{attr} peak {peak:.3f} out of [0.50, 1.0]"

    sprint = UninorteSprintMicrogame()
    sprint.phase = sprint.PHASE_PLAY
    sprint.player_lane = 0
    sprint.player_is_jumping = False
    jump_calls = []
    monkeypatch.setattr(sprint.audio, "play_jump", lambda: jump_calls.append("jump"), raising=False)
    sprint._jump_forward()
    assert jump_calls == ["jump"]

    bgm_calls = []
    monkeypatch.setattr(
        audio,
        "play_bgm",
        lambda fn, force_restart=False, volume_scale=1.0: bgm_calls.append((fn, volume_scale)),
    )
    MetropolitanoModeracionMicrogame().enter()
    UninorteConcentrateMicrogame().enter()
    assert ("JuniorCancion.mp3", 0.45) in bgm_calls
    assert ("concentracionMusic.mp3", 0.65) in bgm_calls


def test_audio_manager_music_volume_scale_and_mute_restore(monkeypatch):
    audio = AudioManager.get_instance()
    set_vol_calls = []
    monkeypatch.setattr(pygame.mixer.music, "set_volume", lambda v: set_vol_calls.append(v))
    monkeypatch.setattr(pygame.mixer.music, "pause", lambda: None)
    monkeypatch.setattr(pygame.mixer.music, "unpause", lambda: None)
    monkeypatch.setattr(pygame.mixer.music, "get_busy", lambda: True)

    audio.music_enabled = True
    audio.current_track = "JuniorCancion.mp3"
    audio.play_bgm("JuniorCancion.mp3", force_restart=False, volume_scale=0.45)
    audio.set_music_volume(0.8)
    assert set_vol_calls[-1] == pytest.approx(0.36)

    # Mute -> adjust -> unmute should restore scaled volume
    audio.toggle_music()
    assert audio.music_enabled is False
    audio.set_music_volume(0.5)
    assert set_vol_calls[-1] == pytest.approx(0.0)
    audio.toggle_music()
    assert audio.music_enabled is True
    assert set_vol_calls[-1] == pytest.approx(0.225)
