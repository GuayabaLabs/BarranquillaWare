import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1920, 1080))

from microgames.fritanga_84 import Fritanga84Microgame
from microgames.troja_baile import TrojaBaileMicrogame

def test_folcloricos_microgames():
    print("Iniciando pruebas de los 2 nuevos microjuegos folclóricos...")

    # 1. Test Fritanga de la 84
    frit = Fritanga84Microgame(character_id="westcol")
    assert frit.time_limit == 4.0
    assert len(frit.arepas) == 3
    frit.phase = frit.PHASE_PLAY

    # Voltear las 3 arepas
    for a in frit.arepas:
        frit._flip_arepa(a)
    frit.update_game(0.1)
    assert frit.is_won is True
    assert frit.is_finished is True

    surf1 = pygame.Surface((1920, 1080))
    frit.render_game(surf1)
    print("[OK] Fritanga de la 84 (Arepa de Huevo) probado y verificado.")

    # 2. Test La Troja
    troja = TrojaBaileMicrogame(character_id="shakira")
    assert troja.time_limit == 4.0
    troja.phase = troja.PHASE_PLAY
    troja.time_left = 0.04
    troja.update_game(0.05)
    assert troja.is_won is True
    assert troja.is_finished is True

    surf2 = pygame.Surface((1920, 1080))
    troja.render_game(surf2)
    print("[OK] La Troja (Equilibrio Salsero) probado y verificado.")

    print("TODAS LAS PRUEBAS FOLCLÓRICAS PASARON SATISFACTORIAMENTE (EXIT 0).")

if __name__ == "__main__":
    test_folcloricos_microgames()
