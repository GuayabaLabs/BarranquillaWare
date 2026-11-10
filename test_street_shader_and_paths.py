import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from scenes.story_map import StoryMapScene
from tools.map_dev_tool import MapDevTool, get_bezier_points

def test_bezier_and_street_shader_suite():
    print("Iniciando suite de verificación: Curvas Bézier, Tramos Ocultos y Shader de Calle...")
    scene = StoryMapScene(character_id="westcol")
    dev = scene.dev_tool

    # 1. Habilitar DevTool y pasar a Modo Caminos (Tecla P)
    dev.enabled = True
    event_p = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_p, "mod": 0})
    dev.handle_event(event_p, (0, 0))
    assert dev.mode == "paths", f"Fallo al cambiar a modo paths: {dev.mode}"
    print("[OK] Modo Caminos (P) activado.")

    # 2. Agregar puntos de prueba
    dev.custom_paths.clear()

    # Punto 1: Inicio
    click1 = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (600, 300)})
    dev.handle_event(click1, (0, 0))
    up1 = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (600, 300)})
    dev.handle_event(up1, (0, 0))
    assert len(dev.custom_paths) == 1, "Fallo al agregar punto 1"

    # Punto 2: Con curva Bézier
    click2 = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (900, 500)})
    dev.handle_event(click2, (0, 0))
    up2 = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (900, 500)})
    dev.handle_event(up2, (0, 0))
    assert len(dev.custom_paths) == 2, "Fallo al agregar punto 2"
    p2 = dev.custom_paths[1]
    assert p2["ctrl_x"] == (600 + 900) // 2
    assert p2["ctrl_y"] == (300 + 500) // 2
    print(f"[OK] Curva Bézier inicial creada: P0=(600, 300), Pc=({p2['ctrl_x']}, {p2['ctrl_y']}), P1=(900, 500)")

    # 3. Mover la manija Bézier (Control Handle)
    dev.selected_waypoint_idx = 1
    dev.is_dragging_ctrl = True
    motion_ctrl = pygame.event.Event(pygame.MOUSEMOTION, {"pos": (750, 250)})
    dev.handle_event(motion_ctrl, (0, 0))
    dev.is_dragging_ctrl = False
    assert dev.custom_paths[1]["ctrl_x"] == 750
    assert dev.custom_paths[1]["ctrl_y"] == 250
    print("[OK] Deformación de curvatura Bézier con manija manual verificada.")

    # 4. Probar tramo oculto / túnel (Tecla H)
    event_h = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_h, "mod": 0})
    dev.handle_event(event_h, (0, 0))
    assert dev.custom_paths[1]["hidden"] is True, "Fallo al marcar tramo como oculto con H"
    assert scene.is_segment_hidden(1) is True, "Fallo en helper scene.is_segment_hidden()"
    print("[OK] Marcado de tramo oculto (túnel sin Y-sort) verificado.")

    # 5. Probar parada / nivel (Tecla L)
    event_l = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_l, "mod": 0})
    dev.handle_event(event_l, (0, 0))
    assert dev.custom_paths[1]["is_stop"] is True, "Fallo al marcar parada de nivel con L"
    print("[OK] Marcado de parada de nivel (is_stop) verificado.")

    # 6. Probar Shader de Calle (Ajuste de ancho, opacidad y paleta)
    initial_w = dev.street_shader["width"]
    click_inc_w = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": dev.shader_w_inc_rect.center})
    dev.handle_event(click_inc_w, (0, 0))
    assert dev.street_shader["width"] == initial_w + 2, "Fallo botón ancho shader"

    initial_a = dev.street_shader["alpha"]
    click_inc_a = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": dev.shader_a_inc_rect.center})
    dev.handle_event(click_inc_a, (0, 0))
    assert dev.street_shader["alpha"] == initial_a + 15, "Fallo botón alpha shader"

    # Seleccionar paleta Turquesa
    turq_rect = dev.palette_btn_rects[1][0]
    click_pal = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": turq_rect.center})
    dev.handle_event(click_pal, (0, 0))
    assert dev.street_shader["color"] == [45, 195, 205], "Fallo al seleccionar color turquesa"
    print(f"[OK] Shader de calle interactivo verificado: Ancho={dev.street_shader['width']}, Alpha={dev.street_shader['alpha']}, Color={dev.street_shader['color']}")

    # 7. Renderizar en StoryMapScene (verificar que dibuja sobre world_map sin errores)
    scene._on_devtool_layout_changed()
    test_surf = pygame.Surface((1920, 1080))
    scene.render(test_surf)
    print("[OK] Estampado y renderizado del shader de calle en world_map completado.")

    # 8. Guardar y verificar persistencia en JSON
    save_ok = dev.save_layout()
    assert save_ok is True, "Fallo al guardar en config/map_poi_layout.json"
    reloaded = dev.load_layout()
    assert len(reloaded["custom_paths"]) == 2, "Fallo al recargar caminos"
    assert reloaded["custom_paths"][1]["hidden"] is True
    assert reloaded["custom_paths"][1]["is_stop"] is True
    assert reloaded["street_shader"]["color"] == [45, 195, 205]
    print("[OK] Persistencia completa de caminos, curvas Bézier, túneles y shader en JSON verificada.")

    print("\nTODAS LAS PRUEBAS DE CAMINOS, BÉZIER Y SHADER PASARON EXITOSAMENTE (EXIT 0).")

if __name__ == "__main__":
    test_bezier_and_street_shader_suite()
