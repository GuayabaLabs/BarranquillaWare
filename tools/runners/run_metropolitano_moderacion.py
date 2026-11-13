import sys
import pygame
from microgames.metropolitano_moderacion import MetropolitanoModeracionMicrogame

def main():
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080), pygame.DOUBLEBUF)
    pygame.display.set_caption("Microjuego: ¡Modera la Barra Brava! - Estadio Metropolitano")
    clock = pygame.time.Clock()

    def on_complete(won: bool):
        print(f"=== RESULTADO DEL MICROJUEGO: {'VICTORIA (META DE BANEOS ALCANZADA)' if won else 'DERROTA (TIEMPO AGOTADO)'} ===")

    game = MetropolitanoModeracionMicrogame(on_complete_callback=on_complete)
    game.enter()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        # Clampear dt grande para evitar teletransportes o desincronizaciones
        if dt > 0.1:
            dt = 0.1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                game.handle_event(event)

        game.update(dt)
        game.render(screen)
        pygame.display.flip()

        if game.is_finished and game.phase == game.PHASE_OUTRO and game.outro_timer >= game.outro_duration:
            print("Microjuego finalizado por completo. Cerrando.")
            running = False

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
