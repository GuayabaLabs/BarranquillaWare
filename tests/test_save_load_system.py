import copy
import os
import sys
import pygame
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.asset_manager import AssetManager, rutaFuenteCuento
from core.microgame_pause import MicrogamePauseState
from core.settings import SettingsManager
from core.state_machine import StateMachine
from scenes.load_game import LoadGameScene, StorySaveModalPanel
from scenes.main_menu import MainMenuScene
from scenes.mode_select import ModeSelectScene
from scenes.story_map import StoryMapScene


@pytest.fixture(autouse=True)
def _preserve_settings_state():
    """Preserva settings.json y el singleton SettingsManager entre pruebas."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1920, 1080))

    settings = SettingsManager.get_instance()
    snapshot_data = copy.deepcopy(settings.data)
    try:
        yield settings
    finally:
        settings.data = snapshot_data
        settings.save()


def test_settings_save_load_summary_and_clean_reset():
    settings = SettingsManager.get_instance()
    settings.set("music_enabled", False)
    settings.set("arcade_high_score", 14)
    settings.set("calibration", {"screen_pts": [[10, 10]]})

    settings.update_story_progress(
        has_active_save=True,
        character_id="shakira",
        high_score=200,
        completed_microgames=["uninorte_sprint", "uninorte_concentrate"],
        unlocked_locations=["uninorte", "buenavista"],
        current_node_id=5,
        weather="sunset",
        save_source="manual",
    )
    settings.set("trofeosObtenidos", ["despejarUninorte"])
    settings.set("achievements_progress", {"legacy_key": True})

    assert settings.has_saved_story() is True
    summary = settings.get_story_save_summary()
    assert summary["has_save"] is True
    assert summary["character_id"] == "shakira"
    assert summary["character_name"] == "Shakira"
    assert summary["levels_cleared"] == 1
    assert summary["total_levels"] == 5
    assert summary["next_district"] == "C.C. Buenavista"
    assert summary["trophies_count"] == 1
    assert summary["weather"] == "sunset"
    assert summary["weather_label"] == "Atardecer"
    assert summary["save_source_label"] == "Guardado manual"
    assert summary["saved_at"] != ""

    # Reinicio limpio de Nueva Partida: limpia historia/trofeos pero conserva ajustes
    settings.reset_story_progress(character_id="katherine")
    assert settings.has_saved_story() is False
    assert settings.get("trofeosObtenidos") == []
    assert "achievements_progress" not in settings.data
    assert settings.get_story_progress()["character_id"] == "katherine"
    assert settings.get_story_progress()["unlocked_achievements"] == []
    assert settings.get("music_enabled") is False
    assert settings.get_arcade_high_score() == 14
    assert settings.get("calibration") == {"screen_pts": [[10, 10]]}

    # Borrado explícito también preserva preferencias
    settings.update_story_progress(has_active_save=True, character_id="char", high_score=100)
    assert settings.has_saved_story() is True
    settings.delete_story_save()
    assert settings.has_saved_story() is False
    assert settings.get("music_enabled") is False
    assert settings.get_arcade_high_score() == 14


def test_main_menu_load_game_button_modal_and_scene_flow():
    settings = SettingsManager.get_instance()
    settings.reset_story_progress()

    sm = StateMachine()
    menu = MainMenuScene()
    sm.change_state(menu)

    assert menu.btn_cargar in menu.buttons
    assert isinstance(menu.load_game_scene, LoadGameScene)

    # Verificar que los 5 botones centrales no se traslapan verticalmente
    stack = [menu.btn_jugar, menu.btn_cargar, menu.btn_opciones, menu.btn_estadisticas, menu.btn_salir]
    for a, b in zip(stack, stack[1:]):
        assert a.rect.bottom <= b.rect.top + 8

    screen = pygame.Surface((1920, 1080))
    menu.render(screen)

    # Modal de estadísticas con marco acuarela (sin errores de llaves ni parámetros)
    menu._open_modal("estadisticas")
    menu.update(0.1)
    menu.render(screen)
    menu.active_modal = None

    # Entrar a Cargar Partida desde el menú principal (sin partida guardada)
    menu._on_load_game_clicked()
    for _ in range(10):
        sm.update(0.1)
    assert sm.current_state is menu.load_game_scene
    menu.load_game_scene.render(screen)

    # Ahora simular una partida guardada rica y probar render + borrado en 2 pasos
    settings.update_story_progress(
        has_active_save=True,
        character_id="char",
        high_score=300,
        completed_microgames=["uninorte_sprint", "uninorte_concentrate", "buenavista_trend"],
        unlocked_locations=["uninorte", "buenavista", "metropolitano"],
        current_node_id=4,
        weather="rain",
        save_source="manual",
    )
    menu.load_game_scene.enter()
    menu.load_game_scene.render(screen)

    panel = menu.load_game_scene.panel
    assert panel.btn_delete is not None
    # Primer clic arma confirmación
    panel._handle_delete()
    assert panel.delete_confirm_timer > 0.0
    assert settings.has_saved_story() is True
    # Segundo clic elimina la partida
    panel._handle_delete()
    assert settings.has_saved_story() is False
    assert menu.load_game_scene.toast_msg is not None


def test_mode_select_watercolor_save_modal_bounds():
    settings = SettingsManager.get_instance()
    settings.update_story_progress(
        has_active_save=True,
        character_id="westcol",
        high_score=200,
        completed_microgames=["uninorte_sprint", "uninorte_concentrate"],
        unlocked_locations=["uninorte", "buenavista"],
        current_node_id=2,
    )

    sm = StateMachine()
    mode_select = ModeSelectScene()
    sm.change_state(mode_select)
    mode_select._select_mode("historia")

    assert mode_select.story_save_modal_open is True
    panel = mode_select.story_save_panel
    assert isinstance(panel, StorySaveModalPanel)
    assert mode_select.modal_rect == panel.frame_rect
    assert panel.frame_rect.size == (1320, 820)

    # Verificar que los botones quedan dentro del marco y no invaden la ficha superior ni el borde inferior
    for btn in mode_select.modal_buttons:
        assert panel.frame_rect.contains(btn.rect)
        if btn is not panel.btn_close:
            assert not btn.rect.colliderect(panel.slot_rect)
            assert btn.rect.bottom <= panel.frame_rect.top + 680

    # Verificar tamaño idéntico en fila horizontal (3 botones), botón X amplio, margen floral y tarjeta ampliada
    action_btns = [b for b in panel.buttons if b is not panel.btn_close]
    assert len(action_btns) == 3
    assert len({b.rect.size for b in action_btns}) == 1
    assert len({b.rect.centery for b in action_btns}) == 1
    assert panel.slot_rect.left >= panel.frame_rect.left + 190
    assert panel.slot_rect.width >= 880
    assert panel.slot_rect.height >= 300
    for i, a in enumerate(action_btns):
        assert a.rect.right <= panel.frame_rect.left + 995
        for b in action_btns[i + 1:]:
            assert not a.rect.colliderect(b.rect)
    assert panel.btn_close.rect.width >= 90

    # Verificar retrato ampliado (> 230 px de alto) para los personajes del catálogo y respaldo seguro
    for cid in ("westcol", "char", "katherine", "shakira", "mujer"):
        portrait = panel._get_portrait(cid, True)
        assert portrait.get_bounding_rect().width > 160
        assert portrait.get_bounding_rect().height > 230

    empty_paloma = panel._get_portrait("", False)
    assert empty_paloma.get_bounding_rect().width >= 200
    assert empty_paloma.get_bounding_rect().height >= 160

    screen = pygame.Surface((1920, 1080))
    mode_select.render(screen)

    # Toast acuarela en ModeSelectScene (sin cajas oscuras procedimentales)
    mode_select.toast_msg = "¡AVISO DE PRUEBA ACUARELA!"
    mode_select.toast_timer = 2.5
    assert mode_select.toast_msg == "¡AVISO DE PRUEBA ACUARELA!"
    mode_select.render(screen)

    # Iniciar Nueva Partida desde el modal limpia el guardado y va a selección de personaje
    mode_select._on_new_story_clicked()
    assert mode_select.story_save_modal_open is False
    assert settings.has_saved_story() is False


def test_load_game_scene_equal_button_grids_and_cuento_font():
    settings = SettingsManager.get_instance()
    settings.update_story_progress(
        has_active_save=True,
        character_id="katherine",
        high_score=250,
        completed_microgames=["uninorte_sprint"],
        unlocked_locations=["uninorte", "buenavista"],
        current_node_id=2,
    )

    assert os.path.exists(rutaFuenteCuento)
    assert os.path.basename(rutaFuenteCuento) == "IndieFlower-Regular.ttf"

    sm = StateMachine()
    load_saved = LoadGameScene()
    sm.change_state(load_saved)
    p_saved = load_saved.panel
    assert p_saved.frame_rect.size == (1320, 820)
    saved_actions = [b for b in p_saved.buttons if b is not p_saved.btn_close]
    assert len(saved_actions) == 4
    assert len({b.rect.size for b in saved_actions}) == 1
    assert len({b.rect.centery for b in saved_actions}) == 2
    assert len({b.rect.centerx for b in saved_actions}) == 2
    for idx, a in enumerate(saved_actions):
        assert p_saved.frame_rect.contains(a.rect)
        assert not a.rect.colliderect(p_saved.slot_rect)
        assert a.rect.bottom <= p_saved.frame_rect.top + 682
        assert a.rect.right <= p_saved.frame_rect.left + 940
        for b in saved_actions[idx + 1:]:
            assert not a.rect.colliderect(b.rect)

    # Primer clic en Borrar Partida activa confirmación inline "¿Confirmar?" y renderiza limpio
    screen = pygame.Surface((1920, 1080))
    p_saved._handle_delete()
    assert p_saved.delete_confirm_timer > 0.0
    load_saved.render(screen)

    # Verificar que los textos de cabecera y botones caen sobre crema limpia (0 solape floral/borde)
    assets = AssetManager.get_instance()
    raw_frame = assets.load_cropped_surface("recuadro_partida_guardada.png")
    scaled_frame = pygame.transform.smoothscale(raw_frame, (1320, 820))
    def _is_cream(col):
        return col.a > 200 and col.r >= 238 and col.g >= 225 and col.b >= 190 and (col.r - col.b) <= 55

    t_surf = assets.cargarFuenteCuento(42).render("PARTIDA GUARDADA ENCONTRADA", True, (84, 52, 112))
    t_bb = t_surf.get_bounding_rect()
    t_rect = t_surf.get_rect(center=(690, 160))
    for ty in range(t_bb.top, t_bb.bottom):
        for tx in range(t_bb.left, t_bb.right):
            if t_surf.get_at((tx, ty)).a > 30:
                assert _is_cream(scaled_frame.get_at((t_rect.x + tx, t_rect.y + ty)))

    settings.reset_story_progress()
    load_empty = LoadGameScene()
    sm.change_state(load_empty)
    p_empty = load_empty.panel
    empty_actions = [b for b in p_empty.buttons if b is not p_empty.btn_close]
    assert len(empty_actions) == 2
    assert len({b.rect.size for b in empty_actions}) == 1
    assert len({b.rect.centery for b in empty_actions}) == 1
    assert not empty_actions[0].rect.colliderect(empty_actions[1].rect)
    empty_center_x = (empty_actions[0].rect.centerx + empty_actions[1].rect.centerx) // 2
    assert abs(empty_center_x - p_empty.slot_rect.centerx) <= 2


def test_story_map_weather_restore_drawer_and_pause_save_feedback():
    settings = SettingsManager.get_instance()
    settings.reset_story_progress()

    sm = StateMachine()
    exited = {"called": False}
    story_map = StoryMapScene(
        character_id="westcol",
        on_main_menu_callback=lambda _scene=None: exited.__setitem__("called", True),
    )
    sm.change_state(story_map)

    story_map.set_weather("night")
    story_map._on_save_clicked()
    story_map.menu_open = True
    story_map.menu_anim_t = 1.0

    progress = settings.get_story_progress()
    assert progress["has_active_save"] is True
    assert progress["weather"] == "night"
    assert progress["save_source"] == "manual"
    assert story_map.save_feedback_timer > 0.0
    assert story_map.toast_msg and "Partida guardada" in story_map.toast_msg

    screen = pygame.Surface((1920, 1080))
    story_map.render(screen)

    # Al completar un microjuego se actualiza el auto-guardado con el clima vigente
    story_map.active_poi = "uninorte"
    story_map.current_level_stage_idx = 0
    story_map._on_microgame_complete(True)
    assert settings.get_story_progress()["save_source"] == "auto"
    assert settings.get_story_progress()["weather"] == "night"

    # Al recargar desde partida guardada, el clima guardado también se restaura
    resumed_map = StoryMapScene(character_id="westcol")
    assert resumed_map.current_weather == "night"

    # Menú de pausa unificado desde el mapa: Opciones conserva on_calibrate y Guardar da feedback
    story_map._open_pause_menu()
    pause = sm.current_state
    assert isinstance(pause, MicrogamePauseState)
    assert any(it["id"] == "menu" for it in pause.items)
    assert not any(it["id"] == "map" for it in pause.items)

    save_idx = next(i for i, it in enumerate(pause.items) if it["id"] == "save")
    pause.selected = save_idx
    pause._choose()
    assert pause.save_feedback_timer > 0.0
    pause.render(screen)

    pause._open_options()
    options_state = sm.current_state
    assert getattr(options_state, "on_calibrate", None) is not None
    sm.pop_state()  # cierra MapSettingsState

    # Calibrar desde pausa no debe duplicar StoryMapScene en la pila de StateMachine
    from microgames.coaster_launcher import CoasterCalibrationState
    story_map._on_calibrate_pointer()
    assert len(sm._states) == 1
    assert isinstance(sm.current_state, CoasterCalibrationState)
    sm.current_state.on_complete_callback(True)
    assert len(sm._states) == 1
    assert sm.current_state is story_map

    # Reabrir pausa y salir al menú limpiamente
    story_map._open_pause_menu()
    assert len(sm._states) == 2
    story_map._on_exit_from_pause()
    assert exited["called"] is True
    assert len(sm._states) == 1
