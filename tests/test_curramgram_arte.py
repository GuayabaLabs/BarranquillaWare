"""El arte acuarela importado de CurramGram existe, tiene transparencia y el juego lo usa."""
import os
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CARPETA = ROOT / "assets" / "curramgram"
CON_TRANSPARENCIA = (
    "visor_camara", "circulo_caso", "sello_pasaporte", "logo_curramgram",
    "boton_caminar", "boton_saltar", "boton_esconder", "boton_avisar", "boton_foto", "boton_publicar",
    "mostrador_checkin", "puesto_butifarras", "banca_espera", "pilar_palmera", "caseta_policia", "puerta_7",
    "acuarela_policia", "acuarela_viajero", "acuarela_turista", "acuarela_joven", "acuarela_tamborero",
    "acuarela_senora", "acuarela_comparsa", "acuarela_trabajador",
    "acuarela_cami_quieta", "acuarela_cami_camina_1", "acuarela_cami_camina_2", "acuarela_cami_camina_3",
    "acuarela_cami_camina_4", "acuarela_cami_agachada", "acuarela_cami_saltando", "acuarela_cami_foto",
)


class ArteCurramGramTest(unittest.TestCase):
    def test_recortes_sin_fondo_blanco(self):
        for nombre in CON_TRANSPARENCIA:
            with self.subTest(nombre=nombre):
                with Image.open(CARPETA / f"{nombre}.png") as img:
                    self.assertEqual(img.mode, "RGBA")
                    alpha = img.getchannel("A")
                    # Las esquinas del recorte son transparentes (no quedó el fondo blanco).
                    w, h = img.size
                    esquinas = [alpha.getpixel(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
                    self.assertLessEqual(min(esquinas), 10)

    def test_juego_usa_acuarela_y_renderiza(self):
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        from microgames.curramgram.juego import CurramGramGo, PUERTA_X

        juego = CurramGramGo()
        self.assertTrue(juego.acuarela)
        self.assertTrue(juego.animacion.defs["idle"]["frames"][0].startswith("acuarela_cami"))
        self.assertIn(("sello_pasaporte", 46), juego.props)
        superficie = pygame.Surface((1920, 1080))
        for x in (300, 3000, PUERTA_X - 200):
            juego.x = float(x)
            juego.draw(superficie)


if __name__ == "__main__":
    unittest.main()
