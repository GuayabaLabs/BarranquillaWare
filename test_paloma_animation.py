import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from scenes.mode_select import ModeSelectScene

def test_paloma_state_flow():
    scene = ModeSelectScene()
    assert scene.paloma_state == "descanso", f"Estado inicial debe ser 'descanso', obtenido: {scene.paloma_state}"
    assert scene.paloma_hd == scene.paloma_hd_descanso

    # 1. Primer clic en la paloma
    click_pos = scene.paloma_rect.center
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': click_pos, 'button': 1}))
    assert scene.paloma_state == "parada", f"Tras el primer clic debe pasar a 'parada', obtenido: {scene.paloma_state}"
    assert scene.paloma_hd == scene.paloma_hd_parada
    assert scene.paloma_jump_vel < 0.0, "Debe tener velocidad vertical negativa de salto."
    assert scene.paloma_squash < 0.0, "Debe iniciar con deformación de impulso (squash)."

    # 2. Clics sucesivos para elevarla hasta superar el umbral de vuelo (-150 px)
    dt = 1.0 / 60.0
    for _ in range(5):
        scene.update(dt)

    # Segundo y tercer clic mientras asciende
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': scene.paloma_rect.center, 'button': 1}))
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': scene.paloma_rect.center, 'button': 1}))

    # Simular tiempo hasta que suba a zona aérea
    for _ in range(20):
        scene.update(dt)

    assert scene.paloma_state == "volando", f"Al subir en el aire debe cambiar a 'volando', obtenido: {scene.paloma_state}"
    assert scene.paloma_hd == scene.paloma_hd_volando

    # 3. Render en estado volando (prueba que el aleteo, inclinación y transformación no rompan)
    virtual_surface = pygame.Surface((1920, 1080))
    scene.render(virtual_surface)

    # 4. Simular caída libre hasta aterrizar
    # Dejamos pasar suficientes frames sin clics para que la gravedad la baje al suelo
    for _ in range(120):
        scene.update(dt)
        scene.render(virtual_surface)

    assert scene.paloma_jump_y == 0.0, f"Debe haber aterrizado en el suelo (jump_y=0.0), obtenido: {scene.paloma_jump_y}"
    assert scene.paloma_state == "parada", f"Al aterrizar debe quedar en 'parada', obtenido: {scene.paloma_state}"
    assert scene.paloma_hd == scene.paloma_hd_parada

    # 5. Esperar 5 segundos de inactividad para que vuelva a 'descanso'
    for _ in range(320):  # > 5.0 segundos a 60 FPS
        scene.update(dt)

    assert scene.paloma_state == "descanso", f"Tras inactividad debe relajarse a 'descanso', obtenido: {scene.paloma_state}"
    assert scene.paloma_hd == scene.paloma_hd_descanso
    print("TODAS LAS PRUEBAS DE ANIMACION Y ESTADOS DE LA PALOMA PASARON EXITOSAMENTE.")

if __name__ == "__main__":
    test_paloma_state_flow()
