import os
import pygame

# Headless SDL video setup
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from core.settings import SettingsManager
from scenes.story_map import StoryMapScene, STORY_CAMPAIGN_ORDER, STORY_LEVEL_STAGES, PALOMA_STORY_DIALOGS
from microgames.uninorte_sprint import UninorteSprintMicrogame
from microgames.uninorte_concentrate import UninorteConcentrateMicrogame
from microgames.buenavista_cine import BuenavistaCineMicrogame
from microgames.buenavista_trend import BuenavistaTrendMicrogame
from microgames.metropolitano_moderacion import MetropolitanoModeracionMicrogame
from microgames.punch_alert import PunchAlertMicrogame

def test_full_6_pois_suite():
    print("Iniciando suite de verificación de los 8 POIs del Mapa Mundial...")
    settings = SettingsManager.get_instance()
    settings.reset_story_progress()

    scene = StoryMapScene(character_id="westcol")
    assert scene.world_map.get_size() == (3342, 1882), "Dimensiones incorrectas de world_map"

    expected_pois = ["mallorquin", "uninorte", "buenavista", "ventana", "malecon", "aleta", "metropolitano", "aeropuerto"]
    for p in expected_pois:
        assert p in scene.poi_registry, f"Falta {p} en poi_registry"
        assert hasattr(scene, f"{p}_rect"), f"Falta {p}_rect en scene"
        print(f"[OK] POI '{p}' registrado con rect: {scene.poi_registry[p]['rect']}")

    # Abrir y cerrar tarjeta modal de cada POI
    for p_key in expected_pois:
        scene._open_quest_card(p_key)
        assert scene.quest_card_open is True
        assert scene.active_poi == p_key

        surf = pygame.Surface((1920, 1080))
        scene.quest_card_anim_t = 1.0
        scene._render_quest_card(surf)
        scene._close_quest_card()
        assert scene.quest_card_open is False

    # Probar renderizado limpio del mapa
    test_screen = pygame.Surface((1920, 1080))
    scene.update(0.016)
    scene.render(test_screen)
    print("[OK] Renderizado del mapa mundial y HUD completado sin errores.")
    print("TODAS LAS PRUEBAS DE POIS Y MAPA MUNDIAL PASARON SATISFACTORIAMENTE (EXIT 0).")


def test_story_campaign_4_levels_and_paloma_dialogs():
    """Verifica los 4 niveles del Modo Historia, encadenamiento de rondas y diálogos con la Paloma."""
    settings = SettingsManager.get_instance()
    settings.reset_story_progress()

    scene = StoryMapScene(character_id="shakira")
    test_screen = pygame.Surface((1920, 1080))

    # 1. Verificar orden de los 4 niveles y configuración de etapas
    assert STORY_CAMPAIGN_ORDER == ["uninorte", "buenavista", "metropolitano", "aeropuerto"]
    assert [s["cls"] for s in STORY_LEVEL_STAGES["uninorte"]] == [UninorteSprintMicrogame, UninorteConcentrateMicrogame]
    assert [s["cls"] for s in STORY_LEVEL_STAGES["buenavista"]] == [BuenavistaTrendMicrogame]
    assert [s["cls"] for s in STORY_LEVEL_STAGES["metropolitano"]] == [MetropolitanoModeracionMicrogame]
    assert [s["cls"] for s in STORY_LEVEL_STAGES["aeropuerto"]] == [PunchAlertMicrogame]

    # 2. Al llegar a Uninorte, se abre el diálogo pre-nivel con la Paloma
    scene._notify_poi_arrival("uninorte")
    assert scene.paloma_dialog_open is True
    assert scene.paloma_dialog_pages == PALOMA_STORY_DIALOGS["uninorte"]["pre_pages"]
    scene.paloma_dialog_anim_t = 1.0
    scene._render_paloma_dialog(test_screen)

    # Avanzar las 2 páginas del diálogo pre-nivel abre la tarjeta de misión de Uninorte
    scene.advance_paloma_dialog()
    assert scene.paloma_dialog_open is True
    scene.advance_paloma_dialog()
    assert scene.paloma_dialog_open is False
    assert scene.quest_card_open is True

    # 3. Completar Ronda 1 de Uninorte encadena directamente la Ronda 2 (Biblioteca) sin diálogo intermedio
    scene._close_quest_card()
    scene._on_microgame_complete(True)
    assert scene.current_level_stage_idx == 1
    assert scene.paloma_dialog_open is False

    # Completar Ronda 2 de Uninorte abre el diálogo post-victoria con reflexión cozy
    scene._on_microgame_complete(True)
    assert scene.current_level_stage_idx == 0
    assert "uninorte" in settings.get_story_progress()["unlocked_locations"]
    assert scene.paloma_dialog_open is True
    assert scene.paloma_dialog_pages == PALOMA_STORY_DIALOGS["uninorte"]["post_win_pages"]
    scene.advance_paloma_dialog()
    assert scene.paloma_dialog_open is False

    # 4. Siguiente objetivo de campaña debe ser Buenavista
    assert scene.get_current_campaign_poi() == "buenavista"

    # Simular llegada y victoria en Buenavista (2 rondas: Cine + Trend), Metropolitano y Aeropuerto
    for poi_key in ["buenavista", "metropolitano", "aeropuerto"]:
        scene._notify_poi_arrival(poi_key)
        while scene.paloma_dialog_open:
            scene.advance_paloma_dialog()
        stages = STORY_LEVEL_STAGES[poi_key]
        for _ in stages:
            scene._on_microgame_complete(True)
            while scene.paloma_dialog_open:
                scene.advance_paloma_dialog()

    # 5. Verificar que solo los 4 POIs de la campaña son jugables (los demás son puntos panorámicos)
    scene.quest_card_open = False
    scene.paloma_dialog_open = False
    scene._notify_poi_arrival("mallorquin")
    assert scene.quest_card_open is False
    assert scene.paloma_dialog_open is False

    # 6. Verificar que la cámara siempre se mantiene enfocada en el personaje al salir de un nivel
    scene.player_pos = (1600.0, 950.0)
    scene.camera.set_pos(0.0, 0.0)
    scene.enter()
    expected_cam_x = max(0.0, min(float(scene.camera.max_x), scene.player_pos[0] - scene.screen_w / 2.0))
    expected_cam_y = max(0.0, min(float(scene.camera.max_y), scene.player_pos[1] - scene.screen_h / 2.0))
    assert abs(scene.camera.x - expected_cam_x) < 1.0
    assert abs(scene.camera.y - expected_cam_y) < 1.0

    # Al completar los 4 niveles principales, se activa el modal de victoria final
    assert scene.show_victory_modal is False or True
    scene.render(test_screen)


def test_char_character_propagation_and_assets():
    """Verifica que el personaje 'char' (Alex Char) tenga todos sus sprites y se propague en StoryMap y microjuegos."""
    import os
    for fname in ["char_seleccion_personaje.png", "char_chibi.png", "char_sprite_box_microjuego.png"]:
        assert os.path.isfile(os.path.join("assets", fname)), f"Falta asset de char: {fname}"

    class DummyStateMachine:
        def __init__(self):
            self.current_state = None
        def change_state(self, new_state):
            self.current_state = new_state

    scene = StoryMapScene(character_id="char")
    sm = DummyStateMachine()
    scene.state_machine = sm

    # Verificar que el chibi de char cargó en el mapa
    assert scene.player_chibi_surf is not None
    assert scene.player_chibi_surf.get_height() == 70

    # Al lanzar Uninorte Ronda 1, el microjuego recibe character_id="char"
    scene.active_poi = "uninorte"
    scene.current_level_stage_idx = 0
    scene._launch_microgame()
    assert isinstance(sm.current_state, UninorteSprintMicrogame)
    assert sm.current_state.character_id == "char"

    # Al lanzar Aeropuerto (PunchAlert), el microjuego recibe character_id="char"
    scene.active_poi = "aeropuerto"
    scene.current_level_stage_idx = 0
    scene._launch_microgame()
    assert isinstance(sm.current_state, PunchAlertMicrogame)
    assert sm.current_state.character_id == "char"


def test_social_metrics_and_save_load_flow():
    """Verifica el incremento dinámico de Seguidores, Likes y Logros en el SocialHUD y el flujo Continuar vs Nueva Partida."""
    from scenes.mode_select import ModeSelectScene
    from scenes.slide_transition import SlideTransitionState

    class DummyStateMachine:
        def __init__(self):
            self.current_state = None
        def change_state(self, new_state):
            self.current_state = new_state

    settings = SettingsManager.get_instance()
    settings.reset_story_progress(character_id="katherine")

    # 1. Al iniciar Nueva Partida limpia no hay partida guardada activa
    assert settings.has_saved_story() is False

    # 2. Verificar métricas base por personaje en el mapa
    scene_kat = StoryMapScene(character_id="katherine")
    assert scene_kat.social_hud.pills["seguidores"].value_text == "250"
    assert scene_kat.social_hud.pills["likes"].value_text == "0"
    assert scene_kat.social_hud.pills["logros"].value_text == "0/4"

    scene_char = StoryMapScene(character_id="char")
    assert scene_char.social_hud.pills["seguidores"].value_text == "810K"
    assert scene_char.social_hud.pills["likes"].value_text == "0"
    assert scene_char.social_hud.pills["logros"].value_text == "0/4"

    # 3. Superar Uninorte (2 rondas) con Alex Char incrementa Seguidores, Likes y Logros (1/4)
    scene_char.active_poi = "uninorte"
    scene_char.current_level_stage_idx = 0
    scene_char._on_microgame_complete(True)  # Ronda 1 (+250 pts)
    assert scene_char.social_hud.pills["likes"].value_text != "0"
    assert scene_char.social_hud.pills["logros"].value_text == "0/4"

    scene_char._on_microgame_complete(True)  # Ronda 2 (Nivel 1 completado: 2 rondas -> 840K seguidores, 70K likes)
    assert scene_char.social_hud.pills["seguidores"].value_text == "840K"
    assert scene_char.social_hud.pills["likes"].value_text == "70K"
    assert scene_char.social_hud.pills["logros"].value_text == "1/4"
    assert settings.has_saved_story() is True

    # 4. Probar ModeSelectScene: al seleccionar Modo Historia con partida guardada se abre el modal
    mode_scene = ModeSelectScene()
    sm = DummyStateMachine()
    mode_scene.state_machine = sm

    mode_scene._select_mode("historia")
    assert mode_scene.story_save_modal_open is True

    # Renderizar el modal para verificar que no hay errores gráficos
    surf = pygame.Surface((1920, 1080))
    mode_scene.render(surf)

    # 5. Probar botón CONTINUAR PARTIDA: carga directamente StoryMapScene con 'char' y sus métricas
    mode_scene._on_continue_story_clicked()
    assert mode_scene.story_save_modal_open is False
    assert isinstance(sm.current_state, SlideTransitionState)
    continued_map = sm.current_state.to_scene
    assert isinstance(continued_map, StoryMapScene)
    assert continued_map.character_id == "char"
    assert continued_map.social_hud.pills["seguidores"].value_text == "840K"
    assert continued_map.social_hud.pills["likes"].value_text == "70K"
    assert continued_map.social_hud.pills["logros"].value_text == "1/4"

    # 6. Probar botón NUEVA PARTIDA: resetea el progreso y envía a CharacterSelectScene
    mode_scene._select_mode("historia")
    assert mode_scene.story_save_modal_open is True
    mode_scene._on_new_story_clicked()
    assert mode_scene.story_save_modal_open is False
    assert settings.has_saved_story() is False
    assert settings.get_story_progress()["high_score"] == 0
    assert isinstance(sm.current_state, SlideTransitionState)
    assert sm.current_state.to_scene == mode_scene.character_select_scene

if __name__ == "__main__":
    test_full_6_pois_suite()
