import os
import pygame

# Headless SDL video setup
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from scenes.story_map import StoryMapScene

def test_devtool_scale_and_rotation_suite():
    print("Iniciando suite de verificación de DevTool (Escala universal + Rotación)...")
    scene = StoryMapScene(character_id="westcol")
    dev = scene.dev_tool

    # 1. Habilitar DevTool
    dev.enabled = True
    dev.active_poi_key = "aeropuerto"
    initial_w = dev.layout_data["pois"]["aeropuerto"]["width"]
    initial_angle = dev.layout_data["pois"]["aeropuerto"]["angle"]

    # 2. Prueba tecla universal '+' (K_PLUS o K_e)
    event_plus = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_e, "mod": 0})
    consumed = dev.handle_event(event_plus, (0, 0))
    assert consumed is True, "Tecla E no consumida por DevTool"
    assert dev.layout_data["pois"]["aeropuerto"]["width"] == initial_w + 5, "Fallo al incrementar ancho con E"
    print(f"[OK] Escala con tecla 'E': ancho {initial_w} -> {dev.layout_data['pois']['aeropuerto']['width']}")

    # 3. Prueba tecla universal '-' (K_q)
    event_minus = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_q, "mod": 0})
    consumed = dev.handle_event(event_minus, (0, 0))
    assert consumed is True, "Tecla Q no consumida por DevTool"
    assert dev.layout_data["pois"]["aeropuerto"]["width"] == initial_w, "Fallo al decrementar ancho con Q"
    print(f"[OK] Escala con tecla 'Q': ancho restablecido a {initial_w}")

    # 4. Prueba rueda del ratón (MOUSEWHEEL)
    event_wheel_up = pygame.event.Event(pygame.MOUSEWHEEL, {"y": 1, "x": 0, "flipped": False})
    dev.handle_event(event_wheel_up, (0, 0))
    assert dev.layout_data["pois"]["aeropuerto"]["width"] == initial_w + 5, "Fallo rueda ratón zoom in"

    event_wheel_down = pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1, "x": 0, "flipped": False})
    dev.handle_event(event_wheel_down, (0, 0))
    assert dev.layout_data["pois"]["aeropuerto"]["width"] == initial_w, "Fallo rueda ratón zoom out"
    print("[OK] Escala por rueda de ratón (MOUSEWHEEL) verificado.")

    # 5. Prueba rotación tecla R (+5 grados horario)
    event_rot_cw = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_r, "mod": 0})
    dev.handle_event(event_rot_cw, (0, 0))
    assert dev.layout_data["pois"]["aeropuerto"]["angle"] == 5.0, f"Fallo rotación R: {dev.layout_data['pois']['aeropuerto']['angle']}"

    # Prueba rotación tecla T (-5 grados antihorario)
    event_rot_ccw = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_t, "mod": 0})
    dev.handle_event(event_rot_ccw, (0, 0))
    assert dev.layout_data["pois"]["aeropuerto"]["angle"] == 0.0, "Fallo rotación T"
    print("[OK] Rotación por teclado (R / T) verificado.")

    # 6. Prueba rotación por Ctrl + Rueda del ratón
    # Simulamos KMOD_CTRL activo
    pygame.key.set_mods(pygame.KMOD_CTRL)
    event_ctrl_wheel = pygame.event.Event(pygame.MOUSEWHEEL, {"y": 1, "x": 0, "flipped": False})
    dev.handle_event(event_ctrl_wheel, (0, 0))
    assert dev.layout_data["pois"]["aeropuerto"]["angle"] == 5.0, "Fallo rotación Ctrl + MOUSEWHEEL"
    pygame.key.set_mods(0)
    print("[OK] Rotación por Ctrl + MOUSEWHEEL verificado.")

    # 7. Prueba botones de panel UI (Click en [0° Reset])
    click_reset = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": dev.rot_reset_btn_rect.center})
    dev.handle_event(click_reset, (0, 0))
    assert dev.layout_data["pois"]["aeropuerto"]["angle"] == 0.0, "Fallo click botón 0° Reset"

    # Click en botón [↻ +5°]
    click_cw = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": dev.rot_inc_btn_rect.center})
    dev.handle_event(click_cw, (0, 0))
    assert dev.layout_data["pois"]["aeropuerto"]["angle"] == 5.0, "Fallo click botón [↻ +5°]"

    # Click en botón [↺ -5°]
    click_ccw = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": dev.rot_dec_btn_rect.center})
    dev.handle_event(click_ccw, (0, 0))
    assert dev.layout_data["pois"]["aeropuerto"]["angle"] == 0.0, "Fallo click botón [↺ -5°]"

    # Click en botón [+] de ancho
    click_w_inc = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": dev.scale_inc_btn_rect.center})
    dev.handle_event(click_w_inc, (0, 0))
    assert dev.layout_data["pois"]["aeropuerto"]["width"] == initial_w + 10, "Fallo click botón [+] ancho"

    # Click en botón [-] de ancho
    click_w_dec = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": dev.scale_dec_btn_rect.center})
    dev.handle_event(click_w_dec, (0, 0))
    assert dev.layout_data["pois"]["aeropuerto"]["width"] == initial_w, "Fallo click botón [-] ancho"
    print("[OK] Botones interactivos del panel UI ([-], [+], [rot-], [rot+], [0 deg]) verificados.")

    # 8. Prueba renderizado de POI rotado (25 grados) en el mapa sin alterar estabilidad
    dev.layout_data["pois"]["aeropuerto"]["angle"] = 25.0
    scene._on_devtool_layout_changed()
    test_screen = pygame.Surface((1920, 1080))
    scene.render(test_screen)
    print(f"[OK] Estampado y renderizado con rotación 25° completado: rect={scene.aeropuerto_rect}")

    # Restablecer y guardar
    dev.layout_data["pois"]["aeropuerto"]["angle"] = 0.0
    dev.layout_data["pois"]["aeropuerto"]["width"] = initial_w
    save_ok = dev.save_layout()
    assert save_ok is True, "Fallo al guardar layout"
    scene._on_devtool_layout_changed()
    print("[OK] Guardado persistente en config/map_poi_layout.json verificado.")

    print("\nTODAS LAS PRUEBAS DE LA DEVTOOL MEJORADA PASARON SATISFACTORIAMENTE (EXIT 0).")

if __name__ == "__main__":
    test_devtool_scale_and_rotation_suite()
