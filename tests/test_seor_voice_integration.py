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
