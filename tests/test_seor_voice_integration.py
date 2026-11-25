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
    """SFX y Voces están desacoplados: SFX mute no silencia voces; volumen de voz actualiza la voz activa."""
    pygame.display.set_mode((1920, 1080))
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)

    audio = AudioManager.get_instance()
    orig_sound_enabled = audio.sound_enabled
    orig_voice_enabled = audio.voice_enabled
    orig_sfx_vol = audio.sfx_volume
    orig_voice_vol = audio.voice_volume
    orig_canal_esc = getattr(audio, "canalEscritura", None)
    orig_sonido_esc = getattr(audio, "sonidoEscritura", None)
    try:
        audio.sound_enabled = True
        audio.voice_enabled = True
        audio.set_sfx_volume(0.8)
        audio.set_voice_volume(1.0)

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

        # Bajar SFX solo afecta a SFX / máquina de escribir, NO a la voz
        audio.set_sfx_volume(0.4)
        assert dummy_tw.volumes[-1] == pytest.approx(0.14)
        assert dummy_voice.volumes == []

        # Volumen de voz actualiza directamente la voz activa
        audio.set_voice_volume(0.4)
        assert dummy_voice.volumes[-1] == pytest.approx(0.30)

        # Mutear SFX corta sonarEscritura pero mantiene voice_enabled y voz activa
        stop_tw_calls = []
        monkeypatch.setattr(audio, "sonarEscritura", lambda activo: stop_tw_calls.append(activo))
        audio.toggle_sound()
        assert audio.sound_enabled is False
        assert audio.voice_enabled is True
        assert audio.is_voice_playing() is True
        assert False in stop_tw_calls

        # Mutear Voces sí desactiva y detiene la voz sin afectar sound_enabled
        audio.toggle_voice()
        assert audio.voice_enabled is False
        assert audio.sound_enabled is False
        assert audio.is_voice_playing() is False
    finally:
        audio._voice_channel = None
        audio._voice_sound = None
        audio._voice_volume_scale = 1.0
        audio._voice_end_time = 0.0
        audio.canalEscritura = orig_canal_esc
        audio.sonidoEscritura = orig_sonido_esc
        audio.sound_enabled = orig_sound_enabled
        audio.voice_enabled = orig_voice_enabled
        audio.set_sfx_volume(orig_sfx_vol)
        audio.set_voice_volume(orig_voice_vol)


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
    from core.asset_manager import AssetManager
    assets = AssetManager.get_instance()
    orig_cuento = assets.cargarFuenteCuento
    orig_titulo = assets.cargarFuenteTitulo
    class SpyFont:
        def __init__(self, real):
            self._real = real
        def render(self, text, antialias, color, background=None):
            rendered_texts.append(text)
            return self._real.render(text, antialias, color, background)
        def __getattr__(self, name):
            return getattr(self._real, name)

    monkeypatch.setattr(assets, "cargarFuenteCuento", lambda tam: SpyFont(orig_cuento(tam)))
    monkeypatch.setattr(assets, "cargarFuenteTitulo", lambda tam: SpyFont(orig_titulo(tam)))
    surf = pygame.Surface((1920, 1080))
    scene._render_victory_modal(surf)
    joined = "\n".join(rendered_texts)
    assert "\u2605" not in joined
    assert "¡ORGULLO DE CURRAMBA!" in joined
    assert "5 niveles" in joined
    assert "Bienestar digital" in joined

    vm = scene.story_ui.last_victory_layout_metrics
    assert vm["left_star_rect"].right < vm["title_rect"].left
    assert vm["title_rect"].right < vm["right_star_rect"].left
    assert vm["badge_size"][0] >= vm["badge_text_size"][0] + 48
    assert vm["badge_size"][1] >= vm["badge_text_size"][1] + 16


def test_sequential_play_voice_preserves_ducking_and_intro_has_no_tofu_glyphs(monkeypatch):
    """Cambiar de voz directamente no debe disparar un salto de ducking a 1.0 ni renderizar glifos rotos."""
    pygame.display.set_mode((1920, 1080))
    from core.audio_manager import AudioManager
    from scenes.story_map.ui_dialogs import StoryMapUI

    audio = AudioManager.get_instance()
    orig_sound = audio.sound_enabled
    orig_music = audio.music_enabled
    orig_vol = audio.music_volume
    audio.sound_enabled = True
    audio.music_enabled = True
    audio.set_music_volume(1.0)
    try:
        ch1 = audio.play_voice("paloma_welcome_0.ogg")
        assert ch1 is not None
        for _ in range(12):
            audio.update(0.05)
        assert abs(audio._duck_factor - audio.duck_level) < 0.02

        ch2 = audio.play_voice("paloma_welcome_1.ogg")
        assert ch2 is not None
        assert abs(audio._duck_factor - audio.duck_level) < 0.02, (
            f"Ducking saltó al cambiar entre voces consecutivas: _duck_factor={audio._duck_factor}"
        )
        assert abs(ch2.get_volume() - 1.0) < 0.01
    finally:
        audio.stop_voice(fade_ms=0)
        audio.sound_enabled = orig_sound
        audio.music_enabled = orig_music
        audio.set_music_volume(orig_vol)

    rendered_intro = []
    from core.asset_manager import AssetManager
    assets = AssetManager.get_instance()
    orig_cuento = assets.cargarFuenteCuento

    class SpyFont:
        def __init__(self, real):
            self._real = real

        def render(self, text, antialias, color, background=None):
            rendered_intro.append(text)
            return self._real.render(text, antialias, color, background)

        def __getattr__(self, name):
            return getattr(self._real, name)

    monkeypatch.setattr(assets, "cargarFuenteCuento", lambda tam: SpyFont(orig_cuento(tam)))
    ui = StoryMapUI(1920, 1080)
    surf = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    bust = pygame.Surface((140, 140), pygame.SRCALPHA)
    guide = pygame.Surface((120, 120), pygame.SRCALPHA)
    ui.render_intro_dialog(surf, bust, guide)
    joined = "\n".join(rendered_intro)
    assert "\U0001f54a" not in joined and "\u25b6" not in joined
    assert "Paloma" in joined


def test_workspace_settings_json_preserved_and_isolated_by_tests():
    """Las pruebas no deben mutar el settings.json real del usuario ni apagar sonido/voces."""
    import json
    from pathlib import Path
    from core.settings import SettingsManager

    workspace_settings = Path(__file__).resolve().parent.parent / "settings.json"
    existed_before = workspace_settings.exists()
    before = None
    if existed_before:
        before = workspace_settings.read_text(encoding="utf-8")
        data_before = json.loads(before)
        assert data_before.get("sound_enabled") is True
        assert data_before.get("voice_enabled") is True
        assert float(data_before.get("voice_volume", 0.0)) > 0.0

    settings = SettingsManager.get_instance()
    direct_settings = SettingsManager()
    assert Path(settings.filepath).resolve() != workspace_settings.resolve()
    assert Path(direct_settings.filepath).resolve() != workspace_settings.resolve()

    audio = AudioManager.get_instance()
    audio.toggle_sound()
    audio.toggle_voice()
    audio.set_voice_volume(0.25)
    direct_settings.reset_story_progress()
    direct_settings.save()

    if existed_before:
        after = workspace_settings.read_text(encoding="utf-8")
        assert after == before, "Las pruebas mutaron el settings.json del workspace en disco"
    else:
        assert not workspace_settings.exists(), "Las pruebas crearon settings.json en el workspace"


def test_bgm_start_and_switch_do_not_cancel_welcome_or_microgame_intro_voices(monkeypatch):
    """Iniciar o cambiar BGM nunca debe cancelar voces activas (bienvenida e intro de Paloma)."""
    pygame.display.set_mode((1920, 1080))
    from core.state_machine import StateMachine
    from microgames.curramgram_go import CurramGramGoMicrogame
    from microgames.emoji_catch import EmojiCatchMicrogame
    from microgames.buenavista_trend.game import BuenavistaTrendMicrogame

    audio = AudioManager.get_instance()
    played_clips = []
    orig_play_voice = audio.play_voice

    def spy_play_voice(clip_name, volume_scale=1.0, fallback_sound=None):
        played_clips.append(clip_name)
        return orig_play_voice(clip_name, volume_scale=volume_scale, fallback_sound=fallback_sound)

    monkeypatch.setattr(audio, "play_voice", spy_play_voice)

    # 1. Bienvenida de StoryMapScene con BGM arrancando
    story = StoryMapScene(character_id="kevin")
    story.settings.reset_story_progress()
    story.enter()
    assert story.paloma_dialog_open is True
    assert audio.is_voice_playing() is True
    assert getattr(audio, "_voice_clip_name", None) == "paloma_welcome_0.ogg"
    assert audio._duck_target == pytest.approx(audio.duck_level)
    for _ in range(10):
        audio.update(0.05)
    assert audio._duck_factor <= audio.duck_level + 0.05

    # Cambio forzado de pista BGM durante voz activa no debe detener la voz
    audio.play_bgm("7am_ancpg_ost_main_menu.ogg", force_restart=True)
    assert audio.is_voice_playing() is True
    assert getattr(audio, "_voice_clip_name", None) == "paloma_welcome_0.ogg"

    # Avanzar páginas de bienvenida mantiene coherencia
    story.advance_paloma_dialog()
    assert getattr(audio, "_voice_clip_name", None) == "paloma_welcome_1.ogg"
    assert audio.is_voice_playing() is True
    story.advance_paloma_dialog()
    assert story.paloma_dialog_open is False

    # 2. Microjuegos con PalomaIntro entrando a StateMachine (enter() dispara play_bgm)
    for mg_cls in (CurramGramGoMicrogame, EmojiCatchMicrogame):
        played_clips.clear()
        sm = StateMachine()
        mg = mg_cls()
        assert mg.paloma_intro is not None and mg.paloma_intro.active
        sm.change_state(mg)
        assert audio.is_voice_playing() is True, f"{mg_cls.__name__}.enter() canceló su voz introductoria"
        assert played_clips[-1] == "paloma_animo.ogg"
        mg.paloma_intro.skip()
        mg.exit()

    # 3. BuenavistaTrend._start_music_if_needed tampoco debe cortar voces activas
    bt = BuenavistaTrendMicrogame()  # se construye antes: la primera vez precarga la interfaz y tarda más que la voz
    audio.play_voice("coronaste.ogg")
    assert audio.is_voice_playing() is True
    bt._start_music_if_needed()
    assert audio.is_voice_playing() is True
    bt.exit()


def test_voice_control_decoupled_and_muted_badge_across_ui(monkeypatch):
    """Control de voces independiente de SFX en Ajustes, Pausa, Drawer, Menús y Engine."""
    pygame.display.set_mode((1920, 1080))
    from core.engine import Engine
    from core.map_settings import MapSettingsState
    from core.microgame_pause import MicrogamePauseState
    from core.state_machine import StateMachine
    from scenes.character_select import CharacterSelectScene
    from scenes.main_menu import MainMenuScene
    from scenes.mode_select import ModeSelectScene

    audio = AudioManager.get_instance()
    audio.sound_enabled = True
    audio.voice_enabled = True

    # Mutear SFX no impide reproducir voces reales SEOR
    audio.toggle_sound()
    assert audio.sound_enabled is False
    assert audio.voice_enabled is True
    ch = audio.play_voice("coronaste.ogg")
    assert ch is not None and audio.is_voice_playing() is True
    ch_w = audio.play_voice("paloma_welcome_0.ogg")
    assert ch_w is not None and audio.is_voice_playing() is True
    ch_r = audio.play_voice("refl_curramgram_go_win.ogg")
    assert ch_r is not None and audio.is_voice_playing() is True
    audio.stop_voice(fade_ms=0)
    audio.toggle_sound()

    # MapSettingsState: sound(0), music(1), voice(2) y filas sin solapamiento
    settings_state = MapSettingsState()
    assert settings_state.items[:3] == ["sound", "music", "voice"]
    settings_state.index = settings_state.items.index("voice")
    settings_state.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    assert audio.voice_enabled is False
    settings_state.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    assert audio.voice_enabled is True
    prev_v = audio.voice_volume
    settings_state.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT}))
    assert audio.voice_volume < prev_v
    settings_surf = pygame.Surface((1920, 1080))
    settings_state.render(settings_surf)
    rects = [settings_state._row_rects[i] for i in range(len(settings_state.items))]
    for a, b in zip(rects, rects[1:]):
        assert a.bottom <= b.top, f"Filas solapadas en ajustes: {a} vs {b}"

    # MicrogamePauseState: toggle de voces y badge discreto al silenciar
    sm = StateMachine()
    story = StoryMapScene(character_id="kevin")
    pause = MicrogamePauseState(previous=story, save_callback=lambda: None, menu_callback=lambda: None)
    sm.push_state(story)
    sm.push_state(pause)
    voice_idx = [it["id"] for it in pause.items].index("voice")
    pause.selected = voice_idx
    pause.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    assert audio.voice_enabled is False
    assert pause.items[voice_idx]["label"] == "VOCES: NO"

    pause_surf = pygame.Surface((1920, 1080))
    pause.render(pause_surf)
    badge_calls = []
    orig_badge = audio.render_voice_muted_badge
    monkeypatch.setattr(audio, "render_voice_muted_badge", lambda s, right_top=(1894, 110): badge_calls.append(right_top) or orig_badge(s, right_top=right_top))
    pause.render(pause_surf)
    assert len(badge_calls) >= 1

    # Menús mantienen botón de voces sin romper len(MainMenuScene.buttons) == 7
    menu = MainMenuScene()
    assert len(menu.buttons) == 7
    assert hasattr(menu, "btn_voice")
    menu.render(pygame.Surface((1920, 1080)))
    assert len(badge_calls) >= 2
    menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": menu.btn_voice.rect.center, "button": 1}))
    menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": menu.btn_voice.rect.center, "button": 1}))
    assert audio.voice_enabled is True

    for cls in (ModeSelectScene, CharacterSelectScene):
        sc = cls()
        assert hasattr(sc, "btn_voice")
        sc.render(pygame.Surface((1920, 1080)))

    # StoryMapScene drawer posee btn_drawer_voice sincronizado
    assert hasattr(story, "btn_drawer_voice")
    assert story.btn_drawer_voice in story.drawer_buttons

    # Engine dibuja fallback si el estado activo no lo dibuja por su cuenta
    audio.toggle_voice()
    assert audio.voice_enabled is False
    eng = Engine(enable_gl=False)
    eng.state_machine.change_state(settings_state)
    before_eng = len(badge_calls)
    eng._render_current_frame()
    assert len(badge_calls) == before_eng + 1


def test_intermediate_rounds_preserve_reaction_voices_and_10_fallback_microgames():
    """Rondas intermedias de Historia no truncan coronaste/ombe_casi y los 10 sin refl_* conservan reacción."""
    pygame.display.set_mode((1920, 1080))
    from core.state_machine import StateMachine
    from microgames.aeropuerto_aterrizaje import AeropuertoAterrizajeMicrogame
    from microgames.buenavista_cine import BuenavistaCineMicrogame
    from microgames.buenavista_trend.game import BuenavistaTrendMicrogame
    from microgames.malecon_rueda import MaleconRuedaMicrogame
    from microgames.mallorquin_photo import MallorquinPhotoMicrogame
    from microgames.metropolitano_moderacion import MetropolitanoModeracionMicrogame
    from microgames.metropolitano_penalty import MetropolitanoPenaltyMicrogame
    from microgames.punch_alert.game import PunchAlertMicrogame
    from microgames.troja_baile import TrojaBaileMicrogame
    from microgames.ventana_colores import VentanaColoresMicrogame

    audio = AudioManager.get_instance()

    # 1. Ganar Ronda 1 de Uninorte mantiene banner rápido (1.25s) y preserva coronaste.ogg en Ronda 2
    sm = StateMachine()
    story = StoryMapScene(character_id="kevin")
    story.state_machine = sm
    sm.change_state(story)
    story.active_poi = "uninorte"
    story.current_level_stage_idx = 0
    story._launch_microgame()
    r1 = sm.current_state
    r1.finish_game(won=True)
    assert r1.outro_duration == pytest.approx(1.25)
    assert audio.is_voice_playing() is True
    assert getattr(audio, "_voice_clip_name", None) == "coronaste.ogg"

    r1.update(1.30)
    r2 = sm.current_state
    assert r2 is not r1
    assert story.current_level_stage_idx == 1
    assert audio.is_voice_playing() is True, "La transición de Ronda 1 a Ronda 2 truncó coronaste.ogg"
    assert getattr(audio, "_voice_clip_name", None) == "coronaste.ogg"
    r2.exit()

    # 2. Perder Ronda 1 de Uninorte extiende el outro para que ombe_casi.ogg no se corte al instante
    story.active_poi = "uninorte"
    story.current_level_stage_idx = 0
    story._launch_microgame()
    r1_lose = sm.current_state
    r1_lose.finish_game(won=False)
    assert r1_lose.outro_duration >= audio.get_voice_duration("ombe_casi.ogg")
    assert getattr(audio, "_voice_clip_name", None) == "ombe_casi.ogg"
    r1_lose.exit()

    # 3. Los 10 microjuegos sin refl_*.ogg conservan coronaste.ogg y ombe_casi.ogg
    ten_without_refl = [
        AeropuertoAterrizajeMicrogame,
        BuenavistaCineMicrogame,
        BuenavistaTrendMicrogame,
        MaleconRuedaMicrogame,
        MallorquinPhotoMicrogame,
        MetropolitanoModeracionMicrogame,
        MetropolitanoPenaltyMicrogame,
        PunchAlertMicrogame,
        TrojaBaileMicrogame,
        VentanaColoresMicrogame,
    ]
    for cls in ten_without_refl:
        mg_win = cls()
        mg_win.finish_game(won=True)
        assert getattr(audio, "_voice_clip_name", None) == "coronaste.ogg", f"{cls.__name__} debe usar coronaste.ogg"
        mg_win.exit()

        mg_lose = cls()
        mg_lose.finish_game(won=False)
        assert getattr(audio, "_voice_clip_name", None) == "ombe_casi.ogg", f"{cls.__name__} debe usar ombe_casi.ogg"
        mg_lose.exit()


def test_voice_ui_layout_non_overlap_focus_and_no_ghost_badges(monkeypatch):
    """Sin solapamientos visuales, foco teclado en btn_voice, contraste sobre diálogo y sin badges fantasma."""
    pygame.display.set_mode((1920, 1080))
    from core.state_machine import StateMachine
    from core.map_settings import MapSettingsState
    from core.microgame_pause import MicrogamePauseState
    from scenes.main_menu import MainMenuScene
    from scenes.mode_select import ModeSelectScene
    from scenes.character_select import CharacterSelectScene
    from scenes.arcade_mode import ArcadeModeScene
    from scenes.free_play import FreePlayScene

    audio = AudioManager.get_instance()
    audio.voice_enabled = False
    surface = pygame.Surface((1920, 1080))

    # 1. CharacterSelectScene: btn_voice no colisiona con icon_right ni otros botones de audio
    cs = CharacterSelectScene()
    icon_right_rect = cs.icon_right_surf.get_rect(center=cs.icon_right_pos)
    assert not cs.btn_voice.rect.colliderect(icon_right_rect)
    assert not cs.btn_voice.rect.colliderect(cs.btn_music.rect)
    assert not cs.btn_voice.rect.colliderect(cs.btn_sound.rect)
    cs.render(surface)

    # 2. MainMenuScene y ModeSelectScene: len(buttons) preservado y FocusNavigator alcanza btn_voice
    from microgames.uninorte_sprint import UninorteSprintMicrogame

    mm = MainMenuScene()
    assert len(mm.buttons) == 7
    assert mm.camera_dwell_target(mm.btn_voice.rect.center) == ("btn", 7)
    mm.focus_nav.focus(mm.btn_music)
    mm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT}))
    assert mm.focus_nav.focused is mm.btn_voice
    before_voice = audio.voice_enabled
    mm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    assert audio.voice_enabled is (not before_voice)
    audio.voice_enabled = False

    ms_scene = ModeSelectScene()
    assert len(ms_scene.buttons) == 6
    ms_scene.focus_nav.focus(ms_scene.btn_music)
    ms_scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT}))
    assert ms_scene.focus_nav.focused is ms_scene.btn_voice
    ms_scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    assert audio.voice_enabled is True
    audio.voice_enabled = False

    # 3. ArcadeModeScene dibuja su propio badge debajo de hud_lives_pill (bottom <= 120)
    arc = ArcadeModeScene(character_id="char")
    badge_calls = []
    orig_badge = audio.render_voice_muted_badge

    def spy_badge(surf, right_top=(1892, 24)):
        badge_calls.append(right_top)
        return orig_badge(surf, right_top=right_top)

    monkeypatch.setattr(audio, "render_voice_muted_badge", spy_badge)
    arc.render(surface)
    assert arc._draws_voice_badge is True
    assert badge_calls and badge_calls[-1][1] >= 122

    # 4. Sin badges fantasma de escenas en segundo plano cuando hay estado superpuesto
    for bg_scene in (mm, ms_scene, cs, ArcadeModeScene(character_id="char"), FreePlayScene(character_id="char")):
        sm = StateMachine()
        sm.change_state(bg_scene)
        overlay = MapSettingsState()
        sm.push_state(overlay)
        badge_calls.clear()
        bg_scene.render(surface)
        assert badge_calls == [], f"{type(bg_scene).__name__} no debe dibujar badge si hay overlay activo"

    # Microgame en segundo plano bajo MicrogamePauseState no dibuja badge fantasma
    mg = UninorteSprintMicrogame()
    sm_mg = StateMachine()
    sm_mg.change_state(mg)
    pause = MicrogamePauseState(previous=mg, return_callback=lambda: None)
    sm_mg.push_state(pause)
    badge_calls.clear()
    mg.render(surface)
    assert badge_calls == []
    mg.exit()

    # 5. StoryMapScene dibuja badge DESPUÉS del velo del diálogo (contraste brillante) y acepta K_KP_ENTER
    monkeypatch.undo()
    story = StoryMapScene(character_id="kevin")
    story.settings.reset_story_progress()
    sm_st = StateMachine()
    sm_st.change_state(story)
    story.enter()
    assert story.paloma_dialog_open is True
    story.render(surface)
    ref_badge = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    audio.render_voice_muted_badge(ref_badge, right_top=(1894, 114))
    badge_rect = ref_badge.get_bounding_rect()
    assert badge_rect.width > 0
    bright_pixels = 0
    for x in range(badge_rect.left + 6, badge_rect.right - 6, 4):
        for y in range(badge_rect.top + 4, badge_rect.bottom - 4, 2):
            r, g, b, _ = surface.get_at((x, y))
            if r >= 230 and g >= 225 and b >= 210:
                bright_pixels += 1
    assert bright_pixels > 10, "El badge de voces silenciadas quedó oscurecido bajo el velo del diálogo"
    audio.voice_enabled = True
    story.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_KP_ENTER}))
    assert getattr(audio, "_voice_clip_name", None) == "paloma_welcome_1.ogg"
    story.exit()


def test_microgame_pause_seven_item_layout_and_fallback_controls():
    """Pausa de 7 elementos cabe en pergamino seguro y fallback refresca etiqueta Voces con K_LEFT/K_RIGHT."""
    pygame.display.set_mode((1920, 1080))
    from core.state_machine import StateMachine
    from core.microgame_pause import MicrogamePauseState
    from scenes.main_menu import MainMenuScene

    audio = AudioManager.get_instance()
    audio.voice_enabled = True

    bg = MainMenuScene()
    sm = StateMachine()
    sm.change_state(bg)
    pause = MicrogamePauseState(
        previous=bg,
        return_callback=lambda: None,
        restart_callback=lambda: None,
        menu_callback=lambda: None,
        save_callback=lambda: True,
    )
    sm.push_state(pause)

    assert len(pause.items) == 7
    cajas = pause.cajasBotones()
    assert len(cajas) == 7
    for caja in cajas:
        assert caja.left >= 795 and caja.right <= 1120
    assert cajas[-1].bottom <= 812

    voice_idx = next(i for i, it in enumerate(pause.items) if it["id"] == "voice")
    pause.selected = voice_idx
    pause.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT}))
    assert audio.voice_enabled is False

    # Modo fallback procedimental también refresca etiqueta y usa alto compacto sin solapar
    pause.pausaLista = False
    surf = pygame.Surface((1920, 1080))
    pause.render(surf)
    assert pause._draws_voice_badge is True
    assert "NO" in pause.items[voice_idx]["label"]

    pause.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT}))
    assert audio.voice_enabled is True
    pause.render(surf)
    assert "S" in pause.items[voice_idx]["label"]


def test_microgame_transitions_freeplay_arcade_pause_and_audio_update(monkeypatch):
    """Transiciones entre microjuegos, reinicio/salida desde pausa, fallback SFX y audio.update(dt)."""
    pygame.display.set_mode((1920, 1080))
    from core.state_machine import StateMachine
    from core.microgame import BaseMicrogame
    from core.microgame_pause import MicrogamePauseState
    from scenes.free_play import FreePlayScene
    from scenes.arcade_mode import ArcadeModeScene
    from microgames.curramgram_go import CurramGramGoMicrogame
    from microgames.emoji_catch import EmojiCatchMicrogame
    from microgames.uninorte_concentrate.game import UninorteConcentrateMicrogame
    from microgames.buenavista_trend.game import BuenavistaTrendMicrogame
    from microgames.buenavista_cine import BuenavistaCineMicrogame
    from microgames.fritanga_84 import Fritanga84Microgame
    from microgames.uninorte_sprint import UninorteSprintMicrogame

    audio = AudioManager.get_instance()
    audio.voice_enabled = True
    audio.set_voice_volume(1.0)

    # 1. Transición BaseMicrogame -> CurramGramGo/EmojiCatch conserva paloma_animo.ogg
    for next_cls in (CurramGramGoMicrogame, EmojiCatchMicrogame):
        sm = StateMachine()
        first = UninorteSprintMicrogame()
        sm.change_state(first)
        nxt = next_cls()
        sm.change_state(nxt)
        assert audio.is_voice_playing() is True
        assert getattr(audio, "_voice_clip_name", None) == "paloma_animo.ogg"
        nxt.exit()

    # 2. FreePlayScene: reiniciar y salir desde pausa limpia la pila y respeta voces
    fp = FreePlayScene(character_id="char")
    sm_fp = StateMachine()
    sm_fp.change_state(fp)
    curram_idx = next(i for i, g in enumerate(fp.games_data) if g["cls"] is CurramGramGoMicrogame)
    fp._launch_game(curram_idx)
    mg_fp = sm_fp.current_state
    pause_fp = MicrogamePauseState(
        previous=mg_fp,
        return_callback=mg_fp.pause_return_callback,
        restart_callback=mg_fp.pause_restart_callback,
        menu_callback=mg_fp.pause_menu_callback,
    )
    sm_fp.push_state(pause_fp)
    mg_fp.pause_restart_callback()
    assert isinstance(sm_fp.current_state, CurramGramGoMicrogame)
    assert len(sm_fp._states) == 1
    assert audio.is_voice_playing() is True
    assert getattr(audio, "_voice_clip_name", None) == "paloma_animo.ogg"

    mg_fp2 = sm_fp.current_state
    sm_fp.push_state(
        MicrogamePauseState(
            previous=mg_fp2,
            return_callback=mg_fp2.pause_return_callback,
            restart_callback=mg_fp2.pause_restart_callback,
            menu_callback=mg_fp2.pause_menu_callback,
        )
    )
    mg_fp2.pause_menu_callback()
    assert sm_fp.current_state is fp
    assert len(sm_fp._states) == 1
    assert audio.is_voice_playing() is False

    # 3. ArcadeModeScene: salir desde pausa limpia pila y detiene voces
    arc = ArcadeModeScene(character_id="char")
    sm_arc = StateMachine()
    sm_arc.change_state(arc)
    arc_mg = CurramGramGoMicrogame()
    arc_mg.pause_return_callback = arc._exit_from_pause
    arc_mg.pause_menu_callback = arc._exit_from_pause
    sm_arc.change_state(arc_mg)
    sm_arc.push_state(MicrogamePauseState(previous=arc_mg, return_callback=arc_mg.pause_return_callback))
    arc_mg.pause_return_callback()
    assert audio.is_voice_playing() is False
    assert not any(isinstance(s, (MicrogamePauseState, BaseMicrogame)) for s in sm_arc._states)

    # 4. voice_volume=0.0 muestra badge y finish_game con voces apagadas usa win/lose SFX si sound_enabled
    audio.voice_enabled = True
    audio.set_voice_volume(0.0)
    surf_badge = pygame.Surface((400, 120), pygame.SRCALPHA)
    audio.render_voice_muted_badge(surf_badge, right_top=(380, 20))
    assert surf_badge.get_bounding_rect().width > 0

    audio.set_voice_volume(1.0)
    audio.voice_enabled = False
    audio.sound_enabled = True
    win_calls = []
    lose_calls = []
    monkeypatch.setattr(audio, "play_win", lambda: win_calls.append(True))
    monkeypatch.setattr(audio, "play_lose", lambda: lose_calls.append(True))
    mg_fb = UninorteSprintMicrogame()
    mg_fb.finish_game(won=True)
    mg_fb.exit()
    mg_fb2 = UninorteSprintMicrogame()
    mg_fb2.finish_game(won=False)
    mg_fb2.exit()
    assert len(win_calls) == 1 and len(lose_calls) == 1

    # 5. Microjuegos que sobreescriben update(dt) invocan audio.update(dt)
    monkeypatch.undo()
    audio.voice_enabled = True
    for cls in (UninorteConcentrateMicrogame, BuenavistaTrendMicrogame, BuenavistaCineMicrogame, Fritanga84Microgame):
        calls = []
        mg_u = cls()
        monkeypatch.setattr(mg_u.audio, "update", lambda dt, c=calls: c.append(dt))
        mg_u.update(0.016)
        assert calls, f"{cls.__name__}.update no llamó audio.update(dt)"
        mg_u.exit()

    sprint = UninorteSprintMicrogame()
    sprint.avisoAbierto = True
    sprint.imagenesNoti = True
    sprint_calls = []
    monkeypatch.setattr(sprint.audio, "update", lambda dt: sprint_calls.append(dt))
    monkeypatch.setattr(sprint, "revisarGestosAviso", lambda dt: None)
    sprint.update(0.016)
    assert sprint_calls
    sprint.exit()
