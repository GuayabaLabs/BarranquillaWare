"""Genera capturas headless con el mismo escalado de la ventana de juego."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path
import sys
import pygame

RAIZ_EXTRA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_EXTRA))
from comun import VentanaVirtual
from emoji_catch import EmojiCatch
from curramgram_go import CurramGramGo


def capturar(nombre, tipo_juego, dibujar):
    ventana = VentanaVirtual(nombre)
    for ancho, alto in ((1280, 720), (1366, 768), (1920, 1080)):
        ventana.window_size = (ancho, alto)
        ventana.window = pygame.display.set_mode((ancho, alto), pygame.RESIZABLE)
        # Carga las imágenes después de abrir el tamaño de ventana para conservar alfa.
        juego = tipo_juego()
        if tipo_juego is EmojiCatch:
            juego.tiempo = 96.0
            juego.puntos = 120
            juego.negatividad, juego.positividad = 21, 18
            juego.items.clear()
            for tipo, x, y in (("emoji_enojado_naranja", 425, 465), ("emoji_corazon", 1030, 610), ("emoji_bolsa_dinero", 1510, 355)):
                juego._nuevo_item(tipo, x)
                juego.items[-1]["y"] = y
        else:
            juego.x = 1220
            juego.tiempo = 102.0
            juego.puntos = 145
            juego.aviso = "Explora con respeto y confirma antes de publicar."
            juego.aviso_t = 4
        dibujar(juego, ventana.canvas)
        ventana.presentar((249, 229, 239))
        pygame.image.save(ventana.window, str(RAIZ_EXTRA / "_capturas" / f"{nombre}_{ancho}x{alto}.png"))


def main():
    pygame.init()
    (RAIZ_EXTRA / "_capturas").mkdir(exist_ok=True)
    capturar("emoji_catch", EmojiCatch, lambda juego, canvas: juego.draw(canvas))
    capturar("curramgram_go", CurramGramGo, lambda juego, canvas: juego.draw(canvas))
    pygame.quit()


if __name__ == "__main__":
    main()
