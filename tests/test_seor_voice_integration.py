import os
import pytest
import pygame

from core.audio_manager import AudioManager
from core.microgame import BaseMicrogame
from scenes.story_map.scene import StoryMapScene

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

pygame.init()
if not pygame.display.get_surface():
    pygame.display.set_mode((1920, 1080))

SEOR_VOICE_FILES = [
    "coronaste.ogg",
    "ombe_casi.ogg",
    "paloma_saludo.ogg",
    "paloma_animo.ogg",
    "paloma_victoria.ogg",
    "paloma_derrota.ogg",
]

PALOMA_WELCOME_VOICE_FILES = [
    "paloma_welcome_0.ogg",
    "paloma_welcome_1.ogg",
]

def test_seor_voice_files_exist_and_playable():
    """Verifica que los audios grabados por SEOR existan limpios en assets/voces/ y assets/ y sean reproducibles."""
    pygame.mixer.init()
    # 1. Voces de reacción cortas
    for filename in SEOR_VOICE_FILES:
        path_voces = os.path.join("assets", "voces", filename)
        path_assets = os.path.join("assets", filename)
        assert os.path.isfile(path_voces), f"Falta {path_voces}"
        assert os.path.isfile(path_assets), f"Falta {path_assets}"

        snd = pygame.mixer.Sound(path_voces)
        assert snd.get_length() > 1.0, f"Audio {filename} demasiado corto ({snd.get_length()}s)"
        assert snd.get_length() < 7.0, f"Audio {filename} demasiado largo ({snd.get_length()}s)"

    # 2. Diálogos completos de bienvenida de la Paloma
    for filename in PALOMA_WELCOME_VOICE_FILES:
        path_voces = os.path.join("assets", "voces", filename)
        path_assets = os.path.join("assets", filename)
        assert os.path.isfile(path_voces), f"Falta {path_voces}"
        assert os.path.isfile(path_assets), f"Falta {path_assets}"

        snd = pygame.mixer.Sound(path_voces)
        assert 15.0 <= snd.get_length() <= 25.0, f"Diálogo {filename} fuera de rango esperado ({snd.get_length()}s)"

def test_microgame_finish_game_plays_seor_voices():
    """Verifica que BaseMicrogame dispare coronaste.ogg al ganar y ombe_casi.ogg al perder."""
    audio = AudioManager.get_instance()
    played_voices = []

    orig_play_voice = audio.play_voice
    def mock_play_voice(clip_name, volume_scale=1.0, fallback_sound=None):
        played_voices.append(clip_name)
        return orig_play_voice(clip_name, volume_scale, fallback_sound)

    audio.play_voice = mock_play_voice

    class DummyGame(BaseMicrogame):
        pass

    try:
        # Ganar
        g_win = DummyGame()
        g_win.finish_game(won=True)
        assert "coronaste.ogg" in played_voices

        # Perder
        played_voices.clear()
        g_lose = DummyGame()
        g_lose.finish_game(won=False)
        assert "ombe_casi.ogg" in played_voices
    finally:
        audio.play_voice = orig_play_voice
        audio.stop_voice(fade_ms=0)

def test_story_map_triggers_seor_paloma_voices():
    """Verifica que StoryMapScene mapee las voces de la Paloma según el contexto."""
    audio = AudioManager.get_instance()
    played_voices = []

    orig_play_voice = audio.play_voice
    def mock_play_voice(clip_name, volume_scale=1.0, fallback_sound=None):
        played_voices.append(clip_name)
        return orig_play_voice(clip_name, volume_scale, fallback_sound)

    audio.play_voice = mock_play_voice

    try:
        scene = StoryMapScene(character_id="westcol")

        # 1. Diálogo de bienvenida específico: Página 0 -> paloma_welcome_0.ogg
        played_voices.clear()
        scene.paloma_dialog_pages = ["Página 0", "Página 1"]
        scene.paloma_dialog_open = True
        scene.paloma_dialog_voice_prefix = "paloma_welcome"
        scene._trigger_dialog_voice(0)
        assert "paloma_welcome_0.ogg" in played_voices

        # 2. Diálogo de bienvenida específico: Página 1 -> paloma_welcome_1.ogg
        played_voices.clear()
        scene.advance_paloma_dialog()
        assert "paloma_welcome_1.ogg" in played_voices

        # 3. Fallback genérico de bienvenida si el clip específico no existe
        played_voices.clear()
        scene.paloma_dialog_voice_prefix = "paloma_welcome_generico"
        scene._trigger_dialog_voice(0)
        assert "paloma_saludo.ogg" in played_voices

        # 4. Diálogo específico de nivel -> paloma_uninorte_0.ogg / win_0 / lose_0
        played_voices.clear()
        scene.paloma_dialog_voice_prefix = "paloma_uninorte"
        scene._trigger_dialog_voice(0)
        assert "paloma_uninorte_0.ogg" in played_voices

        played_voices.clear()
        scene.paloma_dialog_voice_prefix = "paloma_uninorte_win"
        scene._trigger_dialog_voice(0)
        assert "paloma_uninorte_win_0.ogg" in played_voices

        played_voices.clear()
        scene.paloma_dialog_voice_prefix = "paloma_uninorte_lose"
        scene._trigger_dialog_voice(0)
        assert "paloma_uninorte_lose_0.ogg" in played_voices

        # 5. Fallback genérico si un POI no tiene clip específico
        played_voices.clear()
        scene.paloma_dialog_voice_prefix = "paloma_generico"
        scene._trigger_dialog_voice(0)
        assert "paloma_animo.ogg" in played_voices

        played_voices.clear()
        scene.paloma_dialog_voice_prefix = "paloma_generico_win"
        scene._trigger_dialog_voice(0)
        assert "paloma_victoria.ogg" in played_voices

        played_voices.clear()
        scene.paloma_dialog_voice_prefix = "paloma_generico_lose"
        scene._trigger_dialog_voice(0)
        assert "paloma_derrota.ogg" in played_voices
    finally:
        audio.play_voice = orig_play_voice
        audio.stop_voice(fade_ms=0)

def test_microgame_ensenanza_voice_trigger():
    """Verifica que al mostrarse el cartel de enseñanza se invoque la búsqueda de la voz reflexiva."""
    from microgames.uninorte_sprint import UninorteSprintMicrogame
    audio = AudioManager.get_instance()
    searched_clips = []

    orig_play_voice = audio.play_voice
    def mock_play_voice(clip_name, volume_scale=1.0, fallback_sound=None):
        searched_clips.append(clip_name)
        return None

    audio.play_voice = mock_play_voice
    try:
        game = UninorteSprintMicrogame()
        game.is_won = True
        game.finLetrero = 1.0
        game.outro_timer = 1.5
        surf = pygame.Surface((1920, 1080))
        game.dibujarEnsenanzaFinal(surf)

        assert any("refl_uninorte_sprint_win.ogg" in clip or "refl_sprint_win.ogg" in clip for clip in searched_clips)
    finally:
        audio.play_voice = orig_play_voice


REFL_VOICE_FILES = [
    "refl_uninorte_sprint_win.ogg",
    "refl_uninorte_sprint_lose.ogg",
    "refl_uninorte_concentrate_win.ogg",
    "refl_uninorte_concentrate_lose.ogg",
    "refl_fritanga_84_win.ogg",
    "refl_fritanga_84_lose.ogg",
    "refl_fritanga_rabia.ogg",
    "refl_fritanga_distraido.ogg",
    "refl_curramgram_go_win.ogg",
    "refl_curramgram_go_lose.ogg",
    "refl_emoji_catch_win.ogg",
    "refl_emoji_catch_lose.ogg",
]


def test_reflection_voice_files_exist_and_playable():
    """Verifica que los 12 audios reflexivos grabados por SEOR existan en assets/voces/ y assets/."""
    pygame.mixer.init()
    for filename in REFL_VOICE_FILES:
        path_voces = os.path.join("assets", "voces", filename)
        path_assets = os.path.join("assets", filename)
        assert os.path.isfile(path_voces), f"Falta {path_voces}"
        assert os.path.isfile(path_assets), f"Falta {path_assets}"
        snd = pygame.mixer.Sound(path_voces)
        assert 4.0 <= snd.get_length() <= 11.0, f"Audio {filename} fuera de rango ({snd.get_length()}s)"


def test_fritanga_triggers_specific_reflection_voices():
    """Verifica que Fritanga84Microgame dispare gana, pierde, rabia y distraido correctamente."""
    from microgames.fritanga_84 import Fritanga84Microgame
    audio = AudioManager.get_instance()
    played = []

    orig_play_voice = audio.play_voice
    def mock_play_voice(clip_name, volume_scale=1.0, fallback_sound=None):
        played.append(clip_name)
        return orig_play_voice(clip_name, volume_scale, fallback_sound)

    audio.play_voice = mock_play_voice
    try:
        surf = pygame.Surface((1920, 1080))

        # 1. Gana
        played.clear()
        g = Fritanga84Microgame()
        g.is_won = True
        g.finLetrero = 1.0
        g.outro_timer = 1.5
        g.dibujarEnsenanzaFinal(surf)
        assert "refl_fritanga_84_win.ogg" in played

        # 2. Pierde distraído
        played.clear()
        g = Fritanga84Microgame()
        g.is_won = False
        g.ensenanzaFinal = {"gana": Fritanga84Microgame.ensenanzaFinal["gana"], "pierde": g.ensenanzaDistraido}
        g.finLetrero = 1.0
        g.outro_timer = 1.5
        g.dibujarEnsenanzaFinal(surf)
        assert "refl_fritanga_distraido.ogg" in played

        # 3. Pierde por rabia
        played.clear()
        g = Fritanga84Microgame()
        g.is_won = False
        g.ensenanzaFinal = {"gana": Fritanga84Microgame.ensenanzaFinal["gana"], "pierde": g.ensenanzaRabia}
        g.finLetrero = 1.0
        g.outro_timer = 1.5
        g.dibujarEnsenanzaFinal(surf)
        assert "refl_fritanga_rabia.ogg" in played
    finally:
        audio.play_voice = orig_play_voice


PALOMA_POI_VOICE_FILES = [
    f"paloma_{poi}_{suffix}"
    for poi in ("uninorte", "buenavista", "metropolitano", "aeropuerto", "aleta", "malecon")
    for suffix in ("0.ogg", "1.ogg", "win_0.ogg", "lose_0.ogg")
]


def test_paloma_poi_voice_files_exist_and_playable():
    """Verifica que los 24 audios de las 6 paradas de la Paloma existan y sean reproducibles."""
    pygame.mixer.init()
    for filename in PALOMA_POI_VOICE_FILES:
        path_voces = os.path.join("assets", "voces", filename)
        path_assets = os.path.join("assets", filename)
        assert os.path.isfile(path_voces), f"Falta {path_voces}"
        assert os.path.isfile(path_assets), f"Falta {path_assets}"
        snd = pygame.mixer.Sound(path_voces)
        assert 7.0 <= snd.get_length() <= 22.0, f"Audio {filename} fuera de rango ({snd.get_length()}s)"


def test_all_44_voices_mirror_parity_and_mastering_consistency():
    """Verifica paridad binaria assets/voces vs assets/, uniformidad RMS y ausencia de clipping."""
    import numpy as np

    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
    all_44 = SEOR_VOICE_FILES + PALOMA_WELCOME_VOICE_FILES + REFL_VOICE_FILES + PALOMA_POI_VOICE_FILES
    assert len(all_44) == 44

    rms_vals = []
    for filename in all_44:
        p_voces = os.path.join("assets", "voces", filename)
        p_assets = os.path.join("assets", filename)
        with open(p_voces, "rb") as f1, open(p_assets, "rb") as f2:
            assert f1.read() == f2.read(), f"Espejo desincronizado en {filename}"
        arr = pygame.sndarray.array(pygame.mixer.Sound(p_voces)).astype(np.float32) / 32768.0
        rms_db = float(20.0 * np.log10(np.sqrt(np.mean(arr ** 2)) + 1e-12))
        peak = float(np.max(np.abs(arr)))
        assert peak < 0.99, f"Clipping detectado en {filename}: peak={peak:.3f}"
        rms_vals.append(rms_db)

    spread = max(rms_vals) - min(rms_vals)
    assert spread <= 2.5, f"Dispersión de volumen demasiado alta entre voces: {spread:.2f} dB"


def test_audio_manager_voice_channel_cache_no_overlap_and_ducking(monkeypatch):
    """Verifica canal único sin solapamiento, caché de voces y ducking suave sobre la música."""
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
    audio = AudioManager.get_instance()
    applied_vols = []
    monkeypatch.setattr(pygame.mixer.music, "set_volume", lambda v: applied_vols.append(float(v)))

    orig_enabled = audio.sound_enabled
    orig_music_enabled = audio.music_enabled
    orig_music_vol = audio.music_volume
    try:
        audio.sound_enabled = True
        audio.music_enabled = True
        audio.set_music_volume(0.8)
        audio._bgm_volume_scale = 1.0
        audio._duck_factor = 1.0

        ch1 = audio.play_voice("coronaste.ogg", volume_scale=1.0)
        assert ch1 is not None
        assert audio.is_voice_playing() is True

        # Repetir el mismo clip reutiliza el caché y no crea otro canal solapado
        cached_count = len(audio._voice_cache)
        ch2 = audio.play_voice("embe_inexistente.ogg", volume_scale=1.0, fallback_sound=audio._win_sound)
        ch3 = audio.play_voice("coronaste.ogg", volume_scale=1.0)
        assert len(audio._voice_cache) == cached_count
        assert ch3 == ch1

        # Ducking baja suavemente el BGM mientras la voz está activa
        for _ in range(15):
            audio.update(0.05)
        assert applied_vols[-1] < 0.50, f"El ducking de BGM debió bajar el volumen, obtuvo {applied_vols[-1]}"
        assert applied_vols[-1] == pytest.approx(0.8 * audio.duck_level, abs=0.05)

        # Al detener la voz, el volumen de música regresa suavemente a su valor base
        audio.stop_voice(fade_ms=80)
        assert audio.is_voice_playing() is False
        for _ in range(40):
            audio.update(0.05)
        assert applied_vols[-1] == pytest.approx(0.8, abs=0.01)
    finally:
        audio.stop_voice(fade_ms=0)
        audio.sound_enabled = orig_enabled
        audio.music_enabled = orig_music_enabled
        audio.set_music_volume(orig_music_vol)


def test_reflection_outro_duration_never_cuts_voices_and_clean_skip():
    """Verifica que los outros duren lo suficiente para cada refl_*.ogg y puedan saltarse limpio."""
    from microgames.uninorte_sprint import UninorteSprintMicrogame
    from microgames.uninorte_concentrate.game import UninorteConcentrateMicrogame
    from microgames.fritanga_84 import Fritanga84Microgame
    from microgames.curramgram_go import CurramGramGoMicrogame
    from microgames.emoji_catch import EmojiCatchMicrogame

    audio = AudioManager.get_instance()
    orig_sound_enabled = audio.sound_enabled
    audio.sound_enabled = True
    try:
        cases = [
            (UninorteSprintMicrogame, True, "refl_uninorte_sprint_win.ogg"),
            (UninorteSprintMicrogame, False, "refl_uninorte_sprint_lose.ogg"),
            (UninorteConcentrateMicrogame, True, "refl_uninorte_concentrate_win.ogg"),
            (UninorteConcentrateMicrogame, False, "refl_uninorte_concentrate_lose.ogg"),
            (Fritanga84Microgame, True, "refl_fritanga_84_win.ogg"),
            (Fritanga84Microgame, False, "refl_fritanga_84_lose.ogg"),
            (CurramGramGoMicrogame, True, "refl_curramgram_go_win.ogg"),
            (CurramGramGoMicrogame, False, "refl_curramgram_go_lose.ogg"),
            (EmojiCatchMicrogame, True, "refl_emoji_catch_win.ogg"),
            (EmojiCatchMicrogame, False, "refl_emoji_catch_lose.ogg"),
        ]
        for cls, won, clip_name in cases:
            g = cls()
            try:
                g.finish_game(won=won)
                dur = audio.get_voice_duration(clip_name)
                assert dur > 4.0
                assert g.outro_duration >= g.finLetrero + dur + 0.5, (
                    f"{cls.__name__} ({clip_name}): outro_duration={g.outro_duration:.2f}s < "
                    f"{g.finLetrero:.2f}s + {dur:.2f}s + 0.5s"
                )
            finally:
                g.exit()

        # Fritanga variantes rabia / distraido
        for attr, expected in (("ensenanzaRabia", "refl_fritanga_rabia.ogg"), ("ensenanzaDistraido", "refl_fritanga_distraido.ogg")):
            fg = Fritanga84Microgame()
            try:
                fg.ensenanzaFinal = {"gana": Fritanga84Microgame.ensenanzaFinal["gana"], "pierde": getattr(fg, attr)}
                fg.finish_game(won=False)
                dur = audio.get_voice_duration(expected)
                assert fg.outro_duration >= fg.finLetrero + dur + 0.5
            finally:
                fg.exit()

        # Verificar skip limpio en PHASE_OUTRO
        completed = []
        g_skip = UninorteSprintMicrogame(on_complete_callback=lambda w: completed.append(w))
        try:
            g_skip.finish_game(won=True)
            assert g_skip.can_skip_outro() is False
            g_skip.update(0.1)
            g_skip.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
            assert not completed

            # Avanzar hasta pasada la aparición del cartel de reflexión
            g_skip.outro_timer = g_skip.finLetrero + 0.65
            assert g_skip.can_skip_outro() is True
            g_skip.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
            assert completed == [True]
            assert audio.is_voice_playing() is False
        finally:
            g_skip.exit()
    finally:
        audio.stop_voice(fade_ms=0)
        audio.sound_enabled = orig_sound_enabled


def test_audio_manager_live_sfx_volume_and_mute_stops_typewriter(monkeypatch):
    """Cambiar volumen SFX o silenciar en vivo actualiza la voz activa y corta sonarEscritura."""
    pygame.display.set_mode((1920, 1080))
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)

    audio = AudioManager.get_instance()
    orig_sound_enabled = audio.sound_enabled
    orig_sfx_vol = audio.sfx_volume
    orig_canal_esc = getattr(audio, "canalEscritura", None)
    orig_sonido_esc = getattr(audio, "sonidoEscritura", None)
    try:
        audio.sound_enabled = True
        audio.set_sfx_volume(0.8)

        class DummyVoiceSound:
            def __init__(self):
                self.volumes = []
            def set_volume(self, v):
                self.volumes.append(round(v, 2))
            def get_length(self):
                return 2.0

        class DummyChan:
            def get_busy(self):
                return True
            def stop(self):
                pass
            def fadeout(self, ms):
                pass

        class DummyTypewriterSound:
            def __init__(self):
                self.volumes = []
            def set_volume(self, v):
                self.volumes.append(round(v, 2))

        dummy_voice = DummyVoiceSound()
        dummy_tw = DummyTypewriterSound()
        audio._voice_channel = DummyChan()
        audio._voice_sound = dummy_voice
        audio._voice_volume_scale = 0.75
        audio._voice_end_time = float("inf")
        audio.canalEscritura = DummyChan()
        audio.sonidoEscritura = dummy_tw

        audio.set_sfx_volume(0.4)
        assert dummy_voice.volumes[-1] == pytest.approx(0.30)
        assert dummy_tw.volumes[-1] == pytest.approx(0.14)

        stop_tw_calls = []
        monkeypatch.setattr(audio, "sonarEscritura", lambda activo: stop_tw_calls.append(activo))
        audio.toggle_sound()
        assert audio.sound_enabled is False
        assert False in stop_tw_calls
    finally:
        audio._voice_channel = None
        audio._voice_sound = None
        audio._voice_volume_scale = 1.0
        audio._voice_end_time = 0.0
        audio.canalEscritura = orig_canal_esc
        audio.sonidoEscritura = orig_sonido_esc
        audio.sound_enabled = orig_sound_enabled
        audio.set_sfx_volume(orig_sfx_vol)


def test_fritanga_finish_stops_oil_and_troll_channels_and_aleta_story_consistency(monkeypatch):
    """Fritanga detiene aceite/trol al terminar y StoryMap alinea MICROGAME_MAP['aleta'] y modal de 5 niveles."""
    pygame.display.set_mode((1920, 1080))
    from microgames.fritanga_84 import Fritanga84Microgame
    from scenes.story_map.scene import MICROGAME_MAP, StoryMapScene

    class FakeChannel:
        def __init__(self):
            self.stopped = False
        def stop(self):
            self.stopped = True

    fg = Fritanga84Microgame()
    try:
        aceite_ch = FakeChannel()
        trol_ch = FakeChannel()
        fg.canalAceite = aceite_ch
        fg.canalTrol = trol_ch
        fg.finish_game(won=True)
        assert aceite_ch.stopped is True
        assert trol_ch.stopped is True
        assert fg.canalAceite is None
        assert fg.canalTrol is None
    finally:
        fg.exit()

    assert MICROGAME_MAP["aleta"] is Fritanga84Microgame
    assert MICROGAME_MAP["aleta_campeones"] is Fritanga84Microgame

    scene = StoryMapScene()
    assert scene._is_poi_cleared("aleta", ["fritanga_84"]) is True
    assert scene._is_poi_cleared("aleta", ["aleta_campeones"]) is True
    assert scene._is_poi_cleared("aleta", []) is False

    rendered_texts = []
    orig_sysfont = pygame.font.SysFont
    class SpyFont:
        def __init__(self, real):
            self._real = real
        def render(self, text, antialias, color, background=None):
            rendered_texts.append(text)
            return self._real.render(text, antialias, color, background)
        def __getattr__(self, name):
            return getattr(self._real, name)

    monkeypatch.setattr(pygame.font, "SysFont", lambda name, size, bold=False, italic=False: SpyFont(orig_sysfont(name, size, bold, italic)))
    surf = pygame.Surface((1920, 1080))
    scene._render_victory_modal(surf)
    joined = "\n".join(rendered_texts)
    assert "5 NIVELES" in joined
    assert "Aleta del Tiburón" in joined
    assert "Uninorte" in joined and "Buenavista" in joined and "Metropolitano" in joined and "Cortissoz" in joined
