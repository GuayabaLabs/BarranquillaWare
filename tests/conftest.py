import copy
import json
import os
from pathlib import Path

import pygame
import pytest


@pytest.fixture(scope="session", autouse=True)
def isolate_workspace_settings(tmp_path_factory):
    """Aísla las pruebas del settings.json real del usuario en el workspace."""
    settings_dir = tmp_path_factory.mktemp("bw_test_settings")
    test_settings_path = Path(settings_dir) / "settings.json"
    test_settings_path.write_text("{}", encoding="utf-8")

    prev_env = os.environ.get("BARRANQUILLAWARE_SETTINGS_FILE")
    os.environ["BARRANQUILLAWARE_SETTINGS_FILE"] = str(test_settings_path)

    import core.settings as settings_mod
    from core.audio_manager import AudioManager

    settings_mod.SettingsManager._instance = None
    settings_inst = settings_mod.SettingsManager.get_instance()
    if AudioManager._instance is not None:
        AudioManager._instance.settings = settings_inst

    yield test_settings_path

    settings_mod.SettingsManager._instance = None
    if prev_env is None:
        os.environ.pop("BARRANQUILLAWARE_SETTINGS_FILE", None)
    else:
        os.environ["BARRANQUILLAWARE_SETTINGS_FILE"] = prev_env


@pytest.fixture(autouse=True)
def restore_audio_and_settings_between_tests(isolate_workspace_settings):
    """Evita que mutaciones de audio/ajustes de un test contaminen otros tests."""
    import core.settings as settings_mod
    from core.audio_manager import AudioManager

    test_settings_path: Path = isolate_workspace_settings
    if AudioManager._instance is not None:
        audio = AudioManager._instance
        if hasattr(audio, "stop_voice"):
            audio.stop_voice(fade_ms=0)
        if hasattr(audio, "sonarEscritura"):
            audio.sonarEscritura(False)

    yield

    # Restaura el archivo temporal aislado y el singleton de audio a defaults limpios
    try:
        test_settings_path.write_text(
            json.dumps(copy.deepcopy(settings_mod.DEFAULT_SETTINGS), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass

    settings_mod.SettingsManager._instance = None
    fresh_settings = settings_mod.SettingsManager(str(test_settings_path))
    settings_mod.SettingsManager._instance = fresh_settings

    if AudioManager._instance is not None:
        audio = AudioManager._instance
        audio.settings = fresh_settings
        audio.music_enabled = bool(fresh_settings.get("music_enabled", True))
        audio.sound_enabled = bool(fresh_settings.get("sound_enabled", True))
        audio.voice_enabled = bool(fresh_settings.get("voice_enabled", True))
        audio.music_volume = float(fresh_settings.get("music_volume", 0.65))
        audio.sfx_volume = float(fresh_settings.get("sfx_volume", 0.8))
        audio.voice_volume = float(fresh_settings.get("voice_volume", 1.0))
        audio.current_track = None
        audio._bgm_volume_scale = 1.0
        audio._voice_volume_scale = 1.0
        audio.duck_level = 0.26
        audio._duck_factor = 1.0
        audio._duck_target = 1.0
        if hasattr(audio, "stop_voice"):
            audio.stop_voice(fade_ms=0)
        if hasattr(audio, "sonarEscritura"):
            audio.sonarEscritura(False)
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass


@pytest.fixture(autouse=True)
def carga_inmediata(monkeypatch, request):
    """La pantalla de carga construye la escena en un hilo; en pruebas se construye al instante.

    Así `change_state(LoadingScene(build))` deja directamente la escena destino, como antes de
    que existiera la pantalla de carga. Para probar la propia pantalla: @pytest.mark.carga_real.
    """
    if request.node.get_closest_marker("carga_real"):
        yield
        return
    import scenes.loading_scene as carga

    monkeypatch.setattr(carga, "LoadingScene", lambda loader_fn, *a, **k: loader_fn())
    yield


def pytest_configure(config):
    config.addinivalue_line("markers", "carga_real: usa la pantalla de carga real (con hilo)")
