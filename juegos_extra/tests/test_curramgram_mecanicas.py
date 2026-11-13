"""Comprobaciones headless de las decisiones principales de CurramGram Go."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame
from curramgram_go import CurramGramGo, PUNTOS


class MecanicasCurramGramTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.juego = CurramGramGo()

    def foto_de_cerca(self, caso):
        self.juego.x = float(PUNTOS[caso])
        camara = self.juego._camara()
        self.juego._capturar_foto((int(PUNTOS[caso] - camara), 600))

    def test_interacciones_y_publicacion_publica(self):
        j = self.juego
        j.x = PUNTOS[0]; j.interactuar()
        self.assertEqual(j.puntos, 30)
        j.x = PUNTOS[2]; j.interactuar()
        self.assertEqual(j.puntos, 75)
        self.assertIn("Avisó", j.casos[2])
        j.x = PUNTOS[5]; self.foto_de_cerca(5); j.publicar()
        self.assertEqual(j.puntos, 110)
        self.assertEqual(j.likes, 120)

    def test_respeta_a_la_persona_vulnerable_al_pasarla(self):
        j = self.juego
        j.x = PUNTOS[3] - 100
        j.update(.05, pygame.key.get_pressed(), (0, 0))
        self.assertIsNone(j.casos[3])
        j.x = PUNTOS[3] - 80
        j.update(.05, pygame.key.get_pressed(), (0, 0))
        self.assertIn("Pasó de largo", j.casos[3])
        self.assertEqual(j.puntos, 20)

    def test_foto_sigilosa_se_entrega_y_flash_falla(self):
        j = self.juego
        j.x = PUNTOS[1]; j.ocultando = True; j.amenaza = False
        self.foto_de_cerca(1)
        self.assertTrue(j.evidencia)
        j.x = 100; j.interactuar()
        self.assertFalse(j.evidencia)
        self.assertEqual(j.puntos, 60)
        j.reiniciar(); j.x = PUNTOS[1]; j.ocultando = False; j.amenaza = False
        self.foto_de_cerca(1)
        self.assertIn("MISIÓN FALLIDA", j.final)

    def test_privacidad_carrito_y_meta(self):
        j = self.juego
        j.x = PUNTOS[2]; j.apunte_t = 1.1
        antes = j.tiempo; self.foto_de_cerca(2)
        self.assertEqual(j.tiempo, antes - 10)
        j.final = None; j.tiempo = 100; j.carrito = {"x": j.x, "hit": False}
        j.carrito_clock = 10; j.update(.05, pygame.key.get_pressed(), (0, 0))
        self.assertAlmostEqual(j.tiempo, 94.95)
        j.x = 5600; j.update(.01, pygame.key.get_pressed(), (0, 0))
        self.assertEqual(j.final, "LLEGASTE A GATE 7")


if __name__ == "__main__":
    unittest.main()
