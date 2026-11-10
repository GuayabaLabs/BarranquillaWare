import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
from core.engine import Engine
from scenes.main_menu import MainMenuScene
from scenes.mode_select import ModeSelectScene
from scenes.slide_transition import SlideTransitionState
from core.settings import SettingsManager

def run_verification():
    print("Iniciando suite de verificación con Selección de Modo y Transición Panorámica...")

    # 1. Persistencia de settings
    settings = SettingsManager.get_instance()
    assert os.path.exists("settings.json"), "settings.json debió existir o generarse."
    print("[OK] Persistencia en settings.json verificada.")

    # 2. Inicializar motor en 1080p
    engine = Engine("BarranquillaWare Test 1080p", enable_gl=False)
    menu = MainMenuScene(screen_w=engine.width, screen_h=engine.height)
    engine.state_machine.change_state(menu)
    print("[OK] Motor y Escena de Menú inicializados en 1920x1080.")

    # 3. Transición: Click en JUGAR -> SlideTransitionState hacia ModeSelect
    jugar_pos = menu.btn_jugar.rect.center
    menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': jugar_pos, 'button': 1}))
    menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': jugar_pos, 'button': 1}))

    current_state = engine.state_machine.current_state
    assert isinstance(current_state, SlideTransitionState), f"Esperado SlideTransitionState, obtenido: {type(current_state)}"
    assert current_state.direction == "left", "La transición debe viajar hacia la derecha (direction=left)."
    assert engine.audio.current_track == "dodo_airlines_acnh_ost_seleccion_modo.ogg", "La música debió cambiar al OST de selección de modo."
    print("[OK] Disparo de transición de cámara a la derecha verificado (Música: Dodo Airlines OST).")

    # 4. Simular avance de transición (0.7 segundos)
    dt = 1.0 / 60.0
    for _ in range(45):
        engine.state_machine.update(dt)
        engine.state_machine.render(engine.virtual_surface)

    # Debe haber llegado a ModeSelectScene
    mode_scene = engine.state_machine.current_state
    assert isinstance(mode_scene, ModeSelectScene), f"Esperado ModeSelectScene al finalizar viaje, obtenido: {type(mode_scene)}"
    print("[OK] Llegada completa a ModeSelectScene verificada.")

    # 5. Probar elementos de ModeSelectScene
    assert len(mode_scene.buttons) >= 6, "ModeSelectScene debe tener botón volver, audio y 3 modos."
    assert mode_scene.btn_historia.width == 470, f"Botón Historia ancho esperado 470, obtenido {mode_scene.btn_historia.width}"
    assert mode_scene.btn_arcade.width == 470, f"Botón Arcade ancho esperado 470, obtenido {mode_scene.btn_arcade.width}"
    assert mode_scene.btn_libre.width == 470, f"Botón Libre ancho esperado 470, obtenido {mode_scene.btn_libre.width}"

    # Probar interacción de Paloma
    paloma_pos = mode_scene.paloma_rect.center
    mode_scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': paloma_pos, 'button': 1}))
    assert mode_scene.paloma_jump_vel < 0.0, "La paloma debió iniciar salto/aleteo."
    assert len(mode_scene.juice_particles.particles) > 0, "Debieron generarse partículas de Juice en la paloma."
    print("[OK] Interacción táctil de la paloma verificada.")

    # Probar navegación a Selección de Personaje tras pulsar un modo de juego
    arcade_pos = mode_scene.btn_arcade.rect.center
    mode_scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': arcade_pos, 'button': 1}))
    mode_scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': arcade_pos, 'button': 1}))
    
    char_trans = engine.state_machine.current_state
    assert isinstance(char_trans, SlideTransitionState), "Pulsar un modo de juego debe disparar SlideTransitionState a Selección de Personaje."
    assert char_trans.direction == "left", "La transición a Selección de Personaje debe deslizar a la izquierda."
    assert engine.audio.current_track == "dodo_airlines_acnh_ost_seleccion_modo.ogg", "La música de Selección de Modo debe continuar sin reiniciarse."
    print("[OK] Transición a Selección de Personaje activada con música continua (Dodo Airlines OST).")

    # Completar transición a CharacterSelectScene
    for _ in range(45):
        engine.state_machine.update(dt)
        engine.state_machine.render(engine.virtual_surface)

    char_scene = engine.state_machine.current_state
    from scenes.character_select import CharacterSelectScene
    assert isinstance(char_scene, CharacterSelectScene), "Debió arribar a CharacterSelectScene."
    assert char_scene.selected_index == 0, "Westcol debe ser el personaje seleccionado por defecto (index 0)."
    assert len(char_scene.cards) == 4, "Deben existir 4 tarjetas de personajes oficiales."
    assert engine.audio.current_track == "dodo_airlines_acnh_ost_seleccion_modo.ogg", "La música debe mantenerse continua en CharacterSelectScene."
    print("[OK] Arribo a CharacterSelectScene con música continua verificado.")

    # Simular navegación por teclado en CharacterSelectScene
    char_scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT}))
    assert char_scene.selected_index == 1, "Flecha derecha debió seleccionar a Alex Char."
    char_scene.handle_event(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_LEFT}))
    assert char_scene.selected_index == 0, "Flecha izquierda debió volver a Westcol."

    # Regresar de CharacterSelectScene a ModeSelectScene
    char_scene.btn_back.on_click()
    back_to_mode_trans = engine.state_machine.current_state
    assert isinstance(back_to_mode_trans, SlideTransitionState)
    assert back_to_mode_trans.direction == "right"
    assert engine.audio.current_track == "dodo_airlines_acnh_ost_seleccion_modo.ogg", "La música debe mantenerse continua al volver a ModeSelectScene."

    for _ in range(45):
        engine.state_machine.update(dt)
        engine.state_machine.render(engine.virtual_surface)

    mode_scene = engine.state_machine.current_state
    assert isinstance(mode_scene, ModeSelectScene)
    print("[OK] Retorno de Selección de Personajes a Selección de Modo con música continua verificado.")

    # 6. Probar Modo Historia -> StoryMapScene con Cámara 2D
    mode_scene._select_mode("historia")
    for _ in range(45):
        engine.state_machine.update(dt)
        engine.state_machine.render(engine.virtual_surface)

    char_scene = engine.state_machine.current_state
    assert isinstance(char_scene, CharacterSelectScene)
    # Confirmar personaje -> Entrar a StoryMapScene
    char_scene.btn_select.on_click()
    for _ in range(45):
        engine.state_machine.update(dt)
        engine.state_machine.render(engine.virtual_surface)

    from scenes.story_map import StoryMapScene
    story_map = engine.state_machine.current_state
    assert isinstance(story_map, StoryMapScene), "Debió arribar a StoryMapScene."
    assert story_map.world_w == 3342 and story_map.world_h == 1882, "El mapa mundial debe medir 3342x1882."
    
    # Probar arrastre de cámara y retorno con auto-guardado
    story_map.cinematic_timer = story_map.cinematic_duration
    story_map.camera.set_pos(400, 300)
    story_map.update(dt)
    story_map.render(engine.virtual_surface)
    story_map.request_exit()
    
    # Validar persistencia transparente en settings.json
    story_saved = settings.get_story_progress()
    assert story_saved["last_camera_x"] == 400.0 and story_saved["last_camera_y"] == 300.0, "La posición debe persistir automáticamente."
    assert story_saved["character_id"] == "westcol", "El personaje debe coincidir con el seleccionado."
    for _ in range(45):
        engine.state_machine.update(dt)
        engine.state_machine.render(engine.virtual_surface)

    char_scene = engine.state_machine.current_state
    assert isinstance(char_scene, CharacterSelectScene)
    char_scene.btn_back.on_click()
    for _ in range(45):
        engine.state_machine.update(dt)
        engine.state_machine.render(engine.virtual_surface)

    mode_scene = engine.state_machine.current_state
    assert isinstance(mode_scene, ModeSelectScene)
    print("[OK] Flujo completo de Modo Historia -> Mapa con Cámara y retorno verificado.")

    # 7. Probar Regreso de Selección de Modo a Menú Principal
    back_pos = mode_scene.btn_back.rect.center
    mode_scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': back_pos, 'button': 1}))
    mode_scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': back_pos, 'button': 1}))

    back_trans = engine.state_machine.current_state
    assert isinstance(back_trans, SlideTransitionState), "Debió activarse SlideTransitionState de retorno."
    assert back_trans.direction == "right", "La transición de regreso debe viajar hacia la izquierda (direction=right)."
    assert engine.audio.current_track == "7am_ancpg_ost_main_menu.ogg", "La música debió restaurarse al OST de Main Menu."
    print("[OK] Disparo de transición de retorno a Menú Principal verificado (Música: 7am Main Menu OST).")

    # 7. Simular avance de regreso al menú
    for _ in range(45):
        engine.state_machine.update(dt)
        engine.state_machine.render(engine.virtual_surface)

    final_scene = engine.state_machine.current_state
    assert isinstance(final_scene, MainMenuScene), f"Esperado MainMenuScene al volver, obtenido: {type(final_scene)}"
    print("[OK] Retorno exitoso a MainMenuScene verificado.")

    pygame.quit()
    print("TODAS LAS PRUEBAS DE MENÚ, MODO Y SELECCIÓN DE PERSONAJES PASARON SATISFACTORIAMENTE.")

if __name__ == "__main__":
    run_verification()
