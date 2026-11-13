"""Valida el catálogo y que los renders headless contengan los sprites visibles."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path
import sys
import unittest
import pygame

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(ROOT))

from comun import ASSETS_REQUERIDOS, revisar_recursos
from emoji_catch import EmojiCatch
from curramgram_go import CurramGramGo


def diferencias(superficie, base, rect):
    """Cuenta píxeles del recorte que difieren del fondo sin interfaz."""
    x, y, w, h = rect
    total = 0
    for py in range(y, y + h, 3):
        for px in range(x, x + w, 3):
            a = superficie.get_at((px, py)); b = base.get_at((px, py))
            if max(abs(a.r-b.r), abs(a.g-b.g), abs(a.b-b.b)) > 25:
                total += 1
    return total


class AssetsYPixelesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1920, 1080))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_catalogo_completo_y_sprites_instanciados(self):
        for juego in ASSETS_REQUERIDOS:
            self.assertEqual(revisar_recursos(juego), [])
        emoji = EmojiCatch()
        self.assertTrue(all(sprite is not None for sprite in emoji.sprites.values()))
        self.assertTrue(all(sprite is not None for sprite in emoji.decoracion.values()))
        curram = CurramGramGo()
        self.assertTrue(all(sprite is not None for sprite in curram.sprites.values()))

    def test_capturas_1920_muestran_sprites_en_regiones_clave(self):
        carpeta = ROOT / "_capturas"
        escala=5/6
        e = EmojiCatch(); ec = pygame.image.load(str(carpeta / "emoji_catch_1920x1080.png"))
        eb = pygame.Surface((1920,1080)); e._draw_fondo(eb); eb=pygame.transform.scale(eb,ec.get_size())
        for rect in ((48,24,680,80),(40,300,152,436),(1728,300,152,436),(390,690,340,340),(1190,690,340,340)):
            rect=tuple(round(v*escala) for v in rect)
            self.assertGreater(diferencias(ec,eb,rect),60, f"Región vacía de Emoji Catch: {rect}")
        c = CurramGramGo(); cc = pygame.image.load(str(carpeta / "curramgram_go_1920x1080.png"))
        cb = pygame.Surface((1920,1080)); c._dibujar_fondo(cb); cb=pygame.transform.scale(cb,cc.get_size())
        self.assertLessEqual(cc.get_width(),1600)
        # En la captura de referencia Cami está cerca del centro del pasillo.
        self.assertGreater(diferencias(cc,cb,tuple(round(v*escala) for v in (730,430,250,360))),90)
        self.assertGreater(diferencias(cc,cb,tuple(round(v*escala) for v in (35,15,580,150))),70)


if __name__ == "__main__":
    unittest.main()
