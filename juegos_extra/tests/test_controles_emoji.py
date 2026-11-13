"""Prueba de regresión de las teclas exclusivas de cada mano (modo headless)."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame
from emoji_catch import EmojiCatch
from comun import leer_entrada


class ControlesEmojiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def comprobar(self, tecla, mano_esperada, direccion):
        juego = EmojiCatch()
        antes = juego.manos[:]
        eventos = [pygame.event.Event(pygame.KEYDOWN, key=tecla)]
        acciones = leer_entrada(eventos)
        juego.mover_manos(acciones["teclas"], .1)
        cambio = (juego.manos[0] - antes[0], juego.manos[1] - antes[1])
        self.assertEqual(cambio[mano_esperada], direccion * 68)
        self.assertEqual(cambio[1 - mano_esperada], 0)

    def test_a_d_j_l_y_teclas_ajenas(self):
        for tecla, mano, direccion in (
            (pygame.K_a, 0, -1), (pygame.K_d, 0, 1),
            (pygame.K_j, 1, -1), (pygame.K_l, 1, 1),
        ):
            with self.subTest(tecla=tecla):
                self.comprobar(tecla, mano, direccion)
        for tecla in (pygame.K_s, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
            with self.subTest(tecla=tecla):
                juego = EmojiCatch()
                antes = juego.manos[:]
                juego.mover_manos({tecla}, .1)
                self.assertEqual(juego.manos, antes)


if __name__ == "__main__":
    unittest.main()
