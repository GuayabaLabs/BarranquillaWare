import os
import pytest
import pygame

from core.audio_manager import AudioManager
from core.asset_manager import AssetManager
from scenes.story_map.scene import StoryMapScene
from scenes.story_map.ui_dialogs import StoryMapUI

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

pygame.init()
if not pygame.display.get_surface():
    pygame.display.set_mode((1920, 1080))

def test_paloma_frames_exist_and_valid():
    """Verifica que los 4 sprites de animación de la Paloma existan y tengan dimensiones válidas con canal alfa."""
    frames = [
        "assets/paloma_dialog_habla_0.png",
        "assets/paloma_dialog_habla_1.png",
        "assets/paloma_dialog_habla_2.png",
        "assets/paloma_dialog_pestaneo.png",
    ]
    for frame_path in frames:
        assert os.path.exists(frame_path), f"El frame {frame_path} no existe en disco."
        surf = pygame.image.load(frame_path)
        assert surf.get_width() > 100
        assert surf.get_height() > 100
        assert surf.get_masks()[3] != 0, f"El frame {frame_path} debe tener canal alfa."

def test_story_map_loads_talk_frames():
    """Verifica que StoryMapScene cargue los 4 frames de habla y gestione el ciclo de animación."""
    scene = StoryMapScene(character_id="westcol")
    assert hasattr(scene, "paloma_talk_frames")
    assert len(scene.paloma_talk_frames) == 4
    for f in scene.paloma_talk_frames:
        assert isinstance(f, pygame.Surface)
        assert f.get_size() == scene.paloma_dialog_portrait.get_size()

    # Si diálogo cerrado -> reposo (frame 0)
    scene.paloma_dialog_open = False
    assert scene.get_paloma_talk_portrait() == scene.paloma_talk_frames[0]

    # Si diálogo abierto -> modula según timer
    scene.paloma_dialog_open = True
    scene.timer = 1.0
    active = scene.get_paloma_talk_portrait()
    assert isinstance(active, pygame.Surface)

def test_paloma_dialog_ui_render_with_animation():
    """Verifica que render_paloma_dialog soporte talk_frames y renderice en superficie virtual 1920x1080."""
    ui = StoryMapUI(1920, 1080)
    surf = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    scene = StoryMapScene(character_id="westcol")

    pages = [["¡Cucu-rrucú! Hablando con la animación de la Paloma."]]
    font = pygame.font.Font(None, 24)

    ui.render_paloma_dialog(
        surface=surf,
        anim_t=1.0,
        pages=pages,
        page_idx=0,
        speaker="PALOMA DE CURRAMBA",
        badge="NIVEL DE PRUEBA",
        timer=2.5,
        portrait_surf=scene.paloma_dialog_portrait,
        dialog_box_surf=scene.dialog_box_surf,
        font_speaker=font,
        font_badge=font,
        font_body=font,
        font_hint=font,
        talk_frames=scene.paloma_talk_frames,
    )
    assert surf.get_bounding_rect().width > 0

def test_audio_manager_play_voice_fallback():
    """Verifica que AudioManager.play_voice no falle y recurra limpiamente a fallback_sound si no hay clip."""
    audio = AudioManager.get_instance()
    res = audio.play_voice("archivo_inexistente_12345.ogg", volume_scale=1.0, fallback_sound=None)
    assert res is None

    fallback = audio._win_sound
    audio.play_voice("archivo_inexistente_12345.ogg", volume_scale=1.0, fallback_sound=fallback)
    audio.stop_voice(fade_ms=0)


def test_paloma_mouth_rests_when_voice_stops_and_animates_while_speaking(monkeypatch):
    """Verifica que el pico de la Paloma solo se mueva mientras hay voz activa y descanse al terminar."""
    from ui.paloma_intro import PalomaIntro

    scene = StoryMapScene(character_id="westcol")
    audio = AudioManager.get_instance()
    speaking = [True]
    monkeypatch.setattr(audio, "is_voice_playing", lambda: speaking[0])

    scene.paloma_dialog_open = True
    # Con voz activa: alterna frames de habla y parpadea en 3.8s
    speaking[0] = True
    seen = set()
    for t in (0.20, 0.36, 0.52, 0.68):
        scene.timer = t
        p = scene.get_paloma_talk_portrait()
        for idx, frame in enumerate(scene.paloma_talk_frames):
            if p is frame:
                seen.add(idx)
    assert len(seen) >= 2, f"Con voz activa debe ciclar los frames de pico, vio: {seen}"
    scene.timer = 3.85
    assert scene.get_paloma_talk_portrait() is scene.paloma_talk_frames[3]

    # Sin voz activa: pico cerrado en reposo (frame 0), manteniendo pestañeo natural
    speaking[0] = False
    for t in (0.20, 0.36, 0.52, 0.68):
        scene.timer = t
        assert scene.get_paloma_talk_portrait() is scene.paloma_talk_frames[0]
    scene.timer = 3.85
    assert scene.get_paloma_talk_portrait() is scene.paloma_talk_frames[3]

    # Cerrar diálogo con ESC o saltar/finalizar PalomaIntro detiene la voz activa;
    # avanzar entre páginas intermedias NO reinicia el mismo clip repetidamente.
    stop_calls = []
    play_calls = []
    monkeypatch.setattr(audio, "stop_voice", lambda fade_ms=80: stop_calls.append(fade_ms))
    monkeypatch.setattr(
        audio,
        "play_voice",
        lambda clip_name, volume_scale=1.0, fallback_sound=None: play_calls.append(clip_name),
    )
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert scene.paloma_dialog_open is False
    assert stop_calls == [100]

    intro = PalomaIntro([["Línea 1", "Línea 2"], ["Línea 3"]])
    assert play_calls == ["paloma_animo.ogg"]
    intro.advance()
    assert intro.page == 1
    assert intro.closing is False
    assert play_calls == ["paloma_animo.ogg"]
    intro.skip()
    assert intro.closing is True
    assert stop_calls == [100, 100]

    intro_single = PalomaIntro([["Página final"]])
    intro_single.advance()
    assert intro_single.closing is True
    assert stop_calls == [100, 100, 100]
