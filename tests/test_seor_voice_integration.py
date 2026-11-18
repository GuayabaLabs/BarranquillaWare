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

def test_seor_voice_files_exist_and_playable():
    """Verifica que los 6 audios grabados por SEOR existan limpios en assets/voces/ y assets/ y sean reproducibles."""
    pygame.mixer.init()
    for filename in SEOR_VOICE_FILES:
        path_voces = os.path.join("assets", "voces", filename)
        path_assets = os.path.join("assets", filename)
        assert os.path.isfile(path_voces), f"Falta {path_voces}"
        assert os.path.isfile(path_assets), f"Falta {path_assets}"

        snd = pygame.mixer.Sound(path_voces)
        assert snd.get_length() > 1.0, f"Audio {filename} demasiado corto ({snd.get_length()}s)"
        assert snd.get_length() < 7.0, f"Audio {filename} demasiado largo ({snd.get_length()}s)"

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

        # 1. Diálogo de bienvenida -> paloma_saludo.ogg
        played_voices.clear()
        scene.paloma_dialog_voice_prefix = "paloma_welcome"
        scene._trigger_dialog_voice(0)
        assert "paloma_saludo.ogg" in played_voices

        # 2. Diálogo previo al reto (ánimo) -> paloma_animo.ogg
        played_voices.clear()
        scene.paloma_dialog_voice_prefix = "paloma_uninorte"
        scene._trigger_dialog_voice(0)
        assert "paloma_animo.ogg" in played_voices

        # 3. Diálogo de victoria de nivel -> paloma_victoria.ogg
        played_voices.clear()
        scene.paloma_dialog_voice_prefix = "paloma_uninorte_win"
        scene._trigger_dialog_voice(0)
        assert "paloma_victoria.ogg" in played_voices

        # 4. Diálogo de derrota de nivel -> paloma_derrota.ogg
        played_voices.clear()
        scene.paloma_dialog_voice_prefix = "paloma_uninorte_lose"
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
