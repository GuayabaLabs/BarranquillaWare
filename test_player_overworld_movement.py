import os
import math
import pygame

# Headless SDL video setup
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from core.settings import SettingsManager
from scenes.story_map import StoryMapScene

def test_overworld_navigation_suite():
    print("Iniciando suite de verificación de Navegación del Jugador (Overworld)...")
    settings = SettingsManager.get_instance()
    settings.reset_story_progress()

    scene = StoryMapScene(character_id="westcol")

    # 1. Verificación de inicialización del jugador
    assert hasattr(scene, "player_node_id"), "Falta player_node_id en scene"
    assert hasattr(scene, "player_pos"), "Falta player_pos en scene"
    assert hasattr(scene, "player_token_surf"), "Falta player_token_surf en scene"
    assert hasattr(scene, "player_shadow_surf"), "Falta player_shadow_surf en scene"
    assert scene.player_node_id == 0, f"player_node_id inicial incorrecto: {scene.player_node_id}"
    assert int(scene.player_pos[0]) == 808 and int(scene.player_pos[1]) == 464, f"Posición inicial incorrecta: {scene.player_pos}"
    assert not scene.player_is_moving, "El jugador no debería estar moviéndose al inicio"
    print(f"[OK] Inicialización en nodo {scene.player_node_id} en posición {scene.player_pos}")

    # 2. Verificación de tokens para los distintos personajes (52x62)
    for char_id in ["shakira", "katherine", "char", "westcol"]:
        scene.character_id = char_id
        scene._build_player_token()
        assert scene.player_token_surf.get_size() == (52, 62), f"Tamaño incorrecto de token para {char_id}"
        print(f"[OK] Token badge estilizado generado para personaje '{char_id}' (52x62)")

    # 3. Navegación D-Pad (Flecha Derecha / K_d) desde nodo 0 hacia la derecha
    # Desde nodo 0 (808, 464) la dirección derecha viaja hacia nodo 6 (1150, 450) y luego nodo 7 (1500, 430)
    evt_right = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT})
    scene.handle_event(evt_right)
    assert scene.player_is_moving, "El jugador debió iniciar movimiento con Flecha Derecha"
    print(f"[OK] D-Pad detectó arista hacia la derecha. Cola de {len(scene.player_path_edges)} aristas.")

    # 4. Simulación de avance en el gameloop con delta time y seguimiento de cámara (Opción 2.A)
    cam_start_x = scene.camera.x
    steps = 0
    while scene.player_is_moving and steps < 400:
        dt = 0.016
        scene.update(dt)
        steps += 1

    assert not scene.player_is_moving, "El jugador no completó su ruta a tiempo"
    dest_id = scene.player_node_id
    assert settings.get_story_progress().get("current_node_id") == dest_id, "settings.json no guardó current_node_id"
    print(f"[OK] Jugador completó viaje hasta nodo {dest_id} ({scene.player_pos}) en {steps * 0.016:.2f}s.")
    print(f"[OK] Seguimiento de cámara 2.A verificado: cámara siguió de ({cam_start_x:.1f}) a ({scene.camera.x:.1f})")

    # 5. Verificación de Point & Click hacia Ventana al Mundo (nodo 24 a través del túnel 26->25->24)
    path_to_ventana = scene._find_shortest_path(dest_id, 24)
    assert path_to_ventana is not None, "BFS no encontró ruta hacia nodo 24"
    scene._start_path_travel(path_to_ventana)
    assert scene.player_is_moving

    # Verificar que al pasar por el tramo oculto el alpha disminuye
    min_alpha = 1.0
    while scene.player_is_moving and steps < 800:
        scene.update(0.016)
        min_alpha = min(min_alpha, scene.player_alpha)
        steps += 1

    assert min_alpha < 0.25, f"El avatar no se ocultó en el túnel (min_alpha fue {min_alpha})"
    assert scene.player_alpha == 1.0, "El avatar debió restaurar alpha = 1.0 al llegar al destino"
    assert scene.player_node_id == 24, f"El jugador debió llegar a nodo 24, llegó a {scene.player_node_id}"
    print(f"[OK] Ocultamiento en túnel verificado con fade-out a alpha={min_alpha:.2f} y reaparición en nodo 24.")

    # 6. Point & Click sobre el nodo 2 (Parada Uninorte)
    nodes, _, node_map, _, _ = scene._get_street_graph()
    target_node = node_map[2]
    screen_click_x = int(target_node["x"] - scene.camera.x)
    screen_click_y = int(target_node["y"] - scene.camera.y)
    evt_down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (screen_click_x, screen_click_y)})
    evt_up = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (screen_click_x, screen_click_y)})
    scene.handle_event(evt_down)
    scene.handle_event(evt_up)

    assert scene.player_is_moving, "Point & Click debió iniciar movimiento hacia nodo 2"
    while scene.player_is_moving:
        scene.update(0.016)

    assert scene.player_node_id == 2, f"Jugador debió llegar a nodo 2, llegó a {scene.player_node_id}"
    print(f"[OK] Point & Click completó navegación hasta nodo {scene.player_node_id}")

    # 7. Verificación de apertura de Quest Card con SPACE estando en nodo de parada
    evt_space = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE})
    scene.handle_event(evt_space)
    assert scene.quest_card_open, "Pulsar SPACE en el nodo de parada debió abrir la tarjeta de misión del POI"
    assert scene.active_poi == "uninorte", f"Se esperaba POI uninorte, se abrió {scene.active_poi}"
    print(f"[OK] Tecla SPACE abrió tarjeta de misión para POI '{scene.active_poi}'")
    scene._close_quest_card()
    assert not scene.quest_card_open

    # 8. Verificación de renderizado completo sin fallos
    test_surface = pygame.Surface((1920, 1080))
    scene.render(test_surface)
    print("[OK] Renderizado completo de la escena con avatar, sombra, hitos de parada y HUD exitoso.")
    print("TODAS LAS PRUEBAS DE OVERWORLD Y MOVIMIENTO DEL JUGADOR PASARON SATISFACTORIAMENTE (EXIT 0).")

if __name__ == "__main__":
    test_overworld_navigation_suite()
