import os
import re
import subprocess
import pygame
import pytest


@pytest.fixture(autouse=True)
def _headless_sdl(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1920, 1080))
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)


class _DummyChannel:
    def __init__(self, busy: bool = True) -> None:
        self.busy = busy
        self.paused = False
        self.stopped = False
        self.volumes = []

    def get_busy(self) -> bool:
        return self.busy and not self.stopped

    def pause(self) -> None:
        self.paused = True

    def unpause(self) -> None:
        self.paused = False

    def stop(self) -> None:
        self.stopped = True
        self.busy = False

    def fadeout(self, _ms: int) -> None:
        self.stopped = True
        self.busy = False

    def set_volume(self, v: float) -> None:
        self.volumes.append(float(v))


def test_punch_alert_exit_stops_voice_and_typewriter(monkeypatch):
    from microgames.punch_alert.game import PunchAlertMicrogame

    game = PunchAlertMicrogame(character_id="westcol")
    stop_calls = []
    esc_calls = []
    monkeypatch.setattr(game.audio, "stop_voice", lambda fade_ms=80: stop_calls.append(fade_ms))
    monkeypatch.setattr(game.audio, "sonarEscritura", lambda active: esc_calls.append(active))

    game.exit()

    assert stop_calls == [80]
    assert esc_calls and all(v is False for v in esc_calls)


def test_buenavista_cine_exit_stops_shh_detector_and_voice(monkeypatch):
    from microgames.buenavista_cine import BuenavistaCineMicrogame

    game = BuenavistaCineMicrogame(character_id="westcol")
    stopped_mic = []

    class _DummyMic:
        def stop(self):
            stopped_mic.append(True)

    game.shh_detector = _DummyMic()
    stop_calls = []
    monkeypatch.setattr(game.audio, "stop_voice", lambda fade_ms=80: stop_calls.append(fade_ms))

    game.exit()

    assert stopped_mic == [True]
    assert stop_calls == [80]


def test_story_map_is_poi_cleared_multistage_uninorte_and_aleta():
    from scenes.story_map.scene import StoryMapScene

    scene = StoryMapScene("westcol")
    assert scene._is_poi_cleared("uninorte", []) is False
    assert scene._is_poi_cleared("uninorte", ["uninorte_sprint"]) is False
    assert scene._is_poi_cleared("uninorte", ["uninorte_sprint", "uninorte_concentrate"]) is True
    assert scene._is_poi_cleared("aleta", ["fritanga_84"]) is True
    assert scene._is_poi_cleared("aleta", ["aleta_campeones"]) is True


def test_fritanga_84_live_audio_mute_and_volume_sync(monkeypatch):
    from microgames.fritanga_84 import Fritanga84Microgame

    game = Fritanga84Microgame(character_id="westcol")
    orig_music_en = game.audio.music_enabled
    orig_music_vol = game.audio.music_volume
    orig_sound_en = game.audio.sound_enabled
    orig_sfx_vol = game.audio.sfx_volume
    orig_duck = game.audio._duck_factor

    try:
        ch_trol = _DummyChannel()
        ch_aceite = _DummyChannel()
        game.canalTrol = ch_trol
        game.canalAceite = ch_aceite
        game.sonidoAceite = game.sonidoAceite or object()

        game.audio.music_enabled = False
        game.audio.sound_enabled = False
        game.actualizarSonido()
        assert ch_trol.paused is True
        assert ch_aceite.paused is True
        assert ch_aceite.volumes[-1] == 0.0

        game.audio.music_enabled = True
        game.audio.music_volume = 0.42
        game.audio.sound_enabled = True
        game.audio.sfx_volume = 0.55
        game.actualizarSonido()
        assert ch_trol.paused is False
        assert ch_trol.volumes[-1] == pytest.approx(0.42, abs=1e-4)
        assert ch_aceite.paused is False
        assert ch_aceite.volumes[-1] > 0.0

        unpause_calls = []
        sync_calls = []
        monkeypatch.setattr(pygame.mixer.music, "unpause", lambda: unpause_calls.append(True))
        monkeypatch.setattr(game.audio, "sync_music_volume", lambda: sync_calls.append(True))

        game.musicaPausada = True
        game.audio.music_enabled = False
        game.reanudarMusica()
        assert unpause_calls == []

        game.musicaPausada = True
        game.audio.music_enabled = True
        game.reanudarMusica()
        assert unpause_calls == [True]
        assert sync_calls == [True]

        game.audio._duck_factor = 0.26
        sync_calls.clear()
        game.ajustarMusica(1.0)
        assert sync_calls == [True]
    finally:
        game.canalTrol = None
        game.canalAceite = None
        game.audio.music_enabled = orig_music_en
        game.audio.music_volume = orig_music_vol
        game.audio.sound_enabled = orig_sound_en
        game.audio.sfx_volume = orig_sfx_vol
        game.audio._duck_factor = orig_duck
        game.exit()


def test_uninorte_sprint_aviso_tictac_respects_live_sound_settings():
    from microgames.uninorte_sprint import UninorteSprintMicrogame

    game = UninorteSprintMicrogame(character_id="westcol")
    orig_sound_en = game.audio.sound_enabled
    orig_sfx_vol = game.audio.sfx_volume
    try:
        game.phase = game.PHASE_PLAY
        game.avisoAbierto = True
        ch_tic = _DummyChannel()
        game.canalTictac = ch_tic

        game.audio.sound_enabled = True
        game.audio.sfx_volume = 0.44
        game.revisarGestosAviso = lambda _dt: None
        game.update(0.016)
        assert ch_tic.paused is False
        assert ch_tic.volumes[-1] == pytest.approx(0.44, abs=1e-4)

        game.audio.sound_enabled = False
        game.update(0.016)
        assert ch_tic.stopped is True
        assert game.canalTictac is None
    finally:
        game.audio.sound_enabled = orig_sound_en
        game.audio.sfx_volume = orig_sfx_vol
        game.exit()


def test_audio_manager_live_escritura_ducking_and_stop_voice_cleanup(monkeypatch):
    from core.audio_manager import AudioManager

    audio = AudioManager.get_instance()
    orig_sound_en = audio.sound_enabled
    orig_sfx_vol = audio.sfx_volume
    orig_canal = getattr(audio, "canalEscritura", None)
    orig_sonido = getattr(audio, "sonidoEscritura", None)

    class _DummySound:
        def __init__(self, vol=0.5):
            self.vol = vol

        def get_volume(self):
            return self.vol

        def set_volume(self, v):
            self.vol = float(v)

    try:
        audio.sound_enabled = True
        audio.sfx_volume = 0.8
        audio.canalEscritura = _DummyChannel(busy=True)
        audio.sonidoEscritura = _DummySound(vol=0.8 * 0.7)

        monkeypatch.setattr(audio, "is_voice_playing", lambda: True)
        audio.update(0.05)
        assert audio.sonidoEscritura.vol == pytest.approx(0.8 * 0.35, abs=0.01)

        monkeypatch.setattr(audio, "is_voice_playing", lambda: False)
        audio.update(0.05)
        assert audio.sonidoEscritura.vol == pytest.approx(0.8 * 0.7, abs=0.01)

        audio._voice_sound = _DummySound()
        audio.stop_voice(fade_ms=0)
        assert audio._voice_sound is None
    finally:
        audio.sound_enabled = orig_sound_en
        audio.sfx_volume = orig_sfx_vol
        audio.canalEscritura = orig_canal
        audio.sonidoEscritura = orig_sonido
        audio.stop_voice(fade_ms=0)


def test_coaster_audio_respects_audio_manager_music_toggle(monkeypatch):
    from core.audio_manager import AudioManager
    import coaster_game.Coaster as coaster

    audio = AudioManager.get_instance()
    orig_music_en = audio.music_enabled
    bgm_calls = []
    unpause_calls = []
    sync_calls = []

    try:
        monkeypatch.setattr(audio, "play_bgm", lambda name, **kw: bgm_calls.append(name))
        monkeypatch.setattr(audio, "sync_music_volume", lambda: sync_calls.append(True))
        monkeypatch.setattr(pygame.mixer.music, "unpause", lambda: unpause_calls.append(True))

        coaster.ponerMusica()
        assert bgm_calls == ["tranquilaMusic.mp3"]

        coaster.almacen["musicaCallada"] = True
        audio.music_enabled = False
        coaster.volverMusica()
        assert unpause_calls == []

        coaster.almacen["musicaCallada"] = True
        audio.music_enabled = True
        coaster.volverMusica()
        assert unpause_calls == [True]
        assert sync_calls == [True]
    finally:
        coaster.almacen.pop("musicaCallada", None)
        audio.music_enabled = orig_music_en


def test_remastered_non_voice_sfx_and_bgm_healthy_levels():
    checked = [
        "assets/JuniorCancion.mp3",
        "assets/concentracionMusic.mp3",
        "assets/emoji_musica.mp3",
        "assets/Fritanga/trol.mp3",
        "assets/Uninorte/tictac.mp3",
        "assets/escribir.mp3",
        "assets/emoji_bloqueo.mp3",
        "assets/emoji_positivo.mp3",
        "assets/curramgram_sello.mp3",
        "assets/curramgram_caso_bien.mp3",
        "assets/curramgram_caso_mal.mp3",
    ]
    for path in checked:
        assert os.path.exists(path), f"Falta {path}"
        snd = pygame.mixer.Sound(path)
        assert snd.get_length() > 0.1
        res = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true,volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stderr
        max_m = re.findall(r"max_volume:\s*([-\d.]+)\s*dB", res)
        tp_m = re.findall(r"Peak:\s*([-\d.]+)\s*dBFS", res)
        max_db = float(max_m[-1])
        tp_db = float(tp_m[-1])
        il_m = re.findall(r"I:\s*([-\d.]+)\s*LUFS", res)
        il_val = float(il_m[-1])
        assert tp_db <= -0.8, f"Clipping en {path}: TP={tp_db} dBFS"
        assert max_db >= -8.0, f"Nivel pico demasiado bajo en {path}: max={max_db} dB"
        if path == "assets/Uninorte/tictac.mp3":
            assert il_val >= -26.0, f"tictac demasiado bajo: I={il_val} LUFS"
        elif path == "assets/JuniorCancion.mp3":
            assert -16.0 <= il_val <= -11.5, f"JuniorCancion fuera de rango saludable: I={il_val} LUFS"
