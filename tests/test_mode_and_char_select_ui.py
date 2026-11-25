import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame
import pytest

from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.settings import SettingsManager
from core.state_machine import StateMachine
from scenes.character_select import CharacterSelectScene
from scenes.main_menu import MainMenuScene
from scenes.mode_select import ModeSelectScene
from scenes.story_map import StoryMapScene


@pytest.fixture(autouse=True)
def _init_pygame_and_reset_audio():
    pygame.init()
    pygame.display.set_mode((1920, 1080))
    audio = AudioManager.get_instance()
    prev_voice = audio.voice_enabled
    prev_music = audio.music_enabled
    prev_sound = audio.sound_enabled
    yield
    audio.voice_enabled = prev_voice
    audio.music_enabled = prev_music
    audio.sound_enabled = prev_sound


def _assert_centered_pill_text(btn_surf: pygame.Surface, assets: AssetManager, base_path: str, name: str, use_jpg: bool = False) -> None:
    if use_jpg:
        raw = assets.cargarSinFondo(base_path, 220)
    else:
        raw = assets.load_cropped_surface(base_path, alpha_threshold=20)
    bbox = raw.get_bounding_rect(min_alpha=20)
    clean = pygame.Surface((bbox.width, bbox.height), pygame.SRCALPHA)
    clean.blit(raw, (0, 0), bbox)
    base_scaled = pygame.transform.smoothscale(clean, btn_surf.get_size())

    vis_rect = base_scaled.get_bounding_rect(min_alpha=20)
    diff = np.abs(
        pygame.surfarray.array3d(btn_surf).astype(np.int16)
        - pygame.surfarray.array3d(base_scaled).astype(np.int16)
    ).max(axis=2)
    ys_cols = np.where(diff > 20)
    assert len(ys_cols[0]) > 20, f"No se detectó texto renderizado sobre {name}"
    ink_cx = (int(ys_cols[0].min()) + int(ys_cols[0].max())) / 2.0
    ink_cy = (int(ys_cols[1].min()) + int(ys_cols[1].max())) / 2.0
    assert abs(ink_cx - vis_rect.centerx) <= 2.0, f"{name} descentrado en X: {ink_cx} vs {vis_rect.centerx}"
    assert abs(ink_cy - vis_rect.centery) <= 2.0, f"{name} descentrado en Y: {ink_cy} vs {vis_rect.centery}"


def test_mode_select_separate_assets_uniform_size_and_layout():
    """ModeSelectScene compone tarjetas uniformes 470x360 desde base+icono separados y preserva contratos."""
    assets = AssetManager.get_instance()
    alpha_masks = []
    for mode in ("historia", "arcade", "libre"):
        bg_path = os.path.join("assets", f"fondo_boton_modo_{mode}.png")
        icon_path = os.path.join("assets", f"icono_modo_{mode}.png")
        assert os.path.exists(bg_path), f"Falta base de modo: {bg_path}"
        assert os.path.exists(icon_path), f"Falta icono de modo: {icon_path}"

        bg = assets.load_cropped_surface(f"fondo_boton_modo_{mode}.png", alpha_threshold=20)
        icon = assets.load_cropped_surface(f"icono_modo_{mode}.png", alpha_threshold=20)
        assert bg.get_size()[0] >= 470 and bg.get_size()[1] >= 360
        assert icon.get_width() >= 200 and icon.get_height() >= 120
        # Verificar transparencia real en las esquinas de ambos assets
        assert bg.get_at((0, 0)).a < 20
        assert icon.get_at((0, 0)).a < 20
        alpha_masks.append(pygame.surfarray.array_alpha(pygame.transform.smoothscale(bg, (470, 360))) > 20)

    # Silueta idéntica en las 3 tarjetas base
    assert np.array_equal(alpha_masks[0], alpha_masks[1])
    assert np.array_equal(alpha_masks[0], alpha_masks[2])

    scene = ModeSelectScene()
    assert len(scene.buttons) == 6
    assert hasattr(scene, "btn_voice")
    _assert_centered_pill_text(
        scene.btn_back.normal_sprite, assets, os.path.join("Interfaz", "botonMorado.jpg"), "mode_btn_back", use_jpg=True
    )
    for btn in (scene.btn_historia, scene.btn_arcade, scene.btn_libre):
        assert (btn.width, btn.height) == (470, 360)

    # Verificar no solapamiento entre título, botones superiores, tarjetas y paloma
    title_rect = scene.title_base.get_rect(center=(scene.title_center_x, scene.title_center_y))
    cards = [scene.btn_historia.rect, scene.btn_arcade.rect, scene.btn_libre.rect]
    top_btns = [scene.btn_back.rect, scene.btn_voice.rect, scene.btn_music.rect, scene.btn_sound.rect]

    for a, b in zip(cards, cards[1:]):
        assert not a.colliderect(b), f"Tarjetas de modo solapadas: {a} vs {b}"
    for tb in top_btns:
        assert not tb.colliderect(title_rect), f"Botón superior {tb} solapa título {title_rect}"
        for card in cards:
            assert not tb.colliderect(card), f"Botón superior {tb} solapa tarjeta {card}"
    for a, b in zip(top_btns, top_btns[1:]):
        assert not a.colliderect(b), f"Botones superiores solapados: {a} vs {b}"
    for card in cards:
        assert not card.colliderect(scene.paloma_rect), f"Tarjeta {card} solapa paloma {scene.paloma_rect}"

    # Verificar FocusNavigator alcanza todos los botones y btn_voice
    nav_items = scene.focus_nav._buttons()
    assert len(nav_items) == 7
    assert scene.btn_voice in nav_items
    scene.focus_nav.focus(scene.btn_music)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT}))
    assert scene.focus_nav.focused is scene.btn_voice
    before_voice = AudioManager.get_instance().voice_enabled
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    assert AudioManager.get_instance().voice_enabled is (not before_voice)

    # Verificar callbacks de clic en los 3 modos
    chosen_modes = []
    sm = StateMachine()
    scene.state_machine = sm
    sm.change_state(scene)
    scene.settings.reset_story_progress()
    for mode_btn, expected in (
        (scene.btn_arcade, "arcade"),
        (scene.btn_libre, "libre"),
        (scene.btn_historia, "historia"),
    ):
        sm.change_state(scene)
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": mode_btn.rect.center, "button": 1}))
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": mode_btn.rect.center, "button": 1}))
        chosen_modes.append(getattr(scene.character_select_scene, "chosen_mode", None))
    assert chosen_modes == ["arcade", "libre", "historia"]


def test_character_select_centered_pill_buttons_and_navigation():
    """CharacterSelectScene centra ópticamente 'Volver' y 'Seleccionar' en sus bases acuarela."""
    assets = AssetManager.get_instance()
    chosen = []
    backed = []
    scene = CharacterSelectScene(
        on_character_chosen=lambda cid: chosen.append(cid),
        on_back_callback=lambda: backed.append(True),
    )

    assert len(scene.buttons) == 4
    assert hasattr(scene, "btn_voice")

    # Comparar centro óptico de la tinta del texto añadido vs centro visual alfa del botón
    _assert_centered_pill_text(
        scene.btn_back.normal_sprite, assets, os.path.join("Interfaz", "botonMorado.jpg"), "btn_back", use_jpg=True
    )
    _assert_centered_pill_text(
        scene.btn_select.normal_sprite, assets, "boton_jugar_modal.png", "btn_select", use_jpg=False
    )

    # No colisiones con iconos de cabecera, tarjetas ni botones de audio
    icon_left_rect = scene.icon_left_surf.get_rect(center=scene.icon_left_pos)
    icon_right_rect = scene.icon_right_surf.get_rect(center=scene.icon_right_pos)
    assert not scene.btn_back.rect.colliderect(icon_left_rect)
    assert not scene.btn_voice.rect.colliderect(icon_right_rect)
    assert not scene.btn_voice.rect.colliderect(scene.btn_music.rect)
    assert not scene.btn_voice.rect.colliderect(scene.btn_sound.rect)
    for card in scene.cards:
        assert not scene.btn_select.rect.colliderect(card.rect)
        assert not scene.btn_back.rect.colliderect(card.rect)

    # Navegación por teclado y clics
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT}))
    assert scene.selected_index == 1
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT}))
    assert scene.selected_index == 0

    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": scene.btn_back.rect.center, "button": 1}))
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": scene.btn_back.rect.center, "button": 1}))
    assert backed == [True]

    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": scene.btn_select.rect.center, "button": 1}))
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": scene.btn_select.rect.center, "button": 1}))
    for _ in range(25):
        if chosen:
            break
        scene.update(0.1)
    assert chosen == ["westcol"]


def test_btn_voice_visual_and_toggle_parity_across_scenes():
    """btn_voice mantiene dimensiones idénticas a btn_music/btn_sound y estado sincronizado en las 4 escenas."""
    audio = AudioManager.get_instance()
    audio.voice_enabled = True

    mm = MainMenuScene()
    ms = ModeSelectScene()
    cs = CharacterSelectScene()
    st = StoryMapScene(character_id="westcol")

    for scene in (mm, ms, cs):
        assert scene.btn_voice.normal_sprite.get_size() == scene.btn_music.normal_sprite.get_size()
        assert scene.btn_voice.normal_sprite.get_size() == scene.btn_sound.normal_sprite.get_size()
        assert scene.btn_voice.alt_sprite.get_size() == scene.btn_music.alt_sprite.get_size()

    assert st.btn_drawer_voice.normal_sprite.get_size() == st.btn_drawer_music.normal_sprite.get_size()
    assert st.btn_voice.normal_sprite.get_size() == (64, 64)

    # Toggle desde StoryMap HUD sincroniza en todas las escenas al sincronizar sus botones
    st.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": st.btn_voice.rect.center, "button": 1}))
    st.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": st.btn_voice.rect.center, "button": 1}))
    assert audio.voice_enabled is False
    for scene in (mm, ms, cs):
        scene.sync_audio_buttons()
        assert scene.btn_voice.toggle_state is False
    st._sync_voice_buttons()
    assert st.btn_voice.toggle_state is False
    assert st.btn_drawer_voice.toggle_state is False
    st.exit()


def test_crop_alpha_square_and_scale_preserves_even_full_span_edges():
    """_crop_alpha_square_and_scale no recorta el borde derecho/inferior en dimensiones pares ni en audio_frame_2."""
    import os

    am = AssetManager.get_instance()

    # 1. Superficie 100x100 de ancho completo (min_x=0, max_x=99, bw=100) con marcador verde en (99, 50)
    surf_w = pygame.Surface((100, 100), pygame.SRCALPHA)
    surf_w.fill((255, 0, 0, 255), (0, 40, 100, 20))
    surf_w.set_at((99, 50), (0, 255, 0, 255))
    out_w = am._crop_alpha_square_and_scale(surf_w, 100, 35)
    assert out_w.get_at((99, 50)).g > 200, f"Se recortó el píxel (99, 50): {out_w.get_at((99, 50))}"

    # 2. Superficie 100x100 de alto completo (min_y=0, max_y=99, bh=100) con marcador verde en (50, 99)
    surf_h = pygame.Surface((100, 100), pygame.SRCALPHA)
    surf_h.fill((255, 0, 0, 255), (40, 0, 20, 100))
    surf_h.set_at((50, 99), (0, 255, 0, 255))
    out_h = am._crop_alpha_square_and_scale(surf_h, 100, 35)
    assert out_h.get_at((50, 99)).g > 200, f"Se recortó el píxel (50, 99): {out_h.get_at((50, 99))}"

    # 3. audio_frame_2 (Sound ON) de spritesheet_botones_sonido_y_musica_main_menu.png conserva su borde derecho
    raw = am.load_surface("spritesheet_botones_sonido_y_musica_main_menu.png", has_alpha=True)
    fw = raw.get_width() // 4
    fh = raw.get_height()
    frame_2 = raw.subsurface(pygame.Rect(2 * fw, 0, fw, fh)).copy()
    alpha = pygame.surfarray.array_alpha(frame_2)
    mask = alpha > 35
    cols = np.where(mask.any(axis=1))[0]
    rows = np.where(mask.any(axis=0))[0]
    min_x, max_x = int(cols[0]), int(cols[-1])
    min_y, max_y = int(rows[0]), int(rows[-1])
    bw = max_x - min_x + 1
    bh = max_y - min_y + 1
    side = max(bw, bh)
    out_f2 = am._crop_alpha_square_and_scale(frame_2, side, 35)
    out_alpha = pygame.surfarray.array_alpha(out_f2)
    # Si bw == side, tanto x=0 como x=side-1 deben conservar píxeles opacos (> 35)
    if bw == side:
        assert (out_alpha[0, :] > 35).any(), "Se recortó el borde izquierdo de audio_frame_2"
        assert (out_alpha[side - 1, :] > 35).any(), "Se recortó el borde derecho (x=max_x) de audio_frame_2"
    if bh == side:
        assert (out_alpha[:, 0] > 35).any(), "Se recortó el borde superior de audio_frame_2"
        assert (out_alpha[:, side - 1] > 35).any(), "Se recortó el borde inferior (y=max_y) de audio_frame_2"
    # Validar también tamaño real usado en UI sin pérdida de cobertura
    assert os.path.isfile(os.path.join("assets", "spritesheet_botones_sonido_y_musica_main_menu.png"))
    assert am.get_audio_button_frames(86)[2].get_size() == (86, 86)
