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
    (RAIZ_EXTRA / "_capturas").mkdir(exist_ok=True)
    for ancho, alto in ((1280, 720), (1920, 1080)):
        ventana = VentanaVirtual(nombre)
        ventana.window_size=(ancho,alto)
        ventana.window=pygame.display.set_mode((ancho,alto),pygame.RESIZABLE)
        for modo in ("juego","pausa","final"):
            juego=tipo_juego()
            if tipo_juego is EmojiCatch:
                juego.tiempo=96.0;juego.puntos=120;juego.negatividad,juego.positividad=45,43
                juego.items.clear()
                for tipo,x,y in (("emoji_enojado_naranja",425,465),("emoji_corazon",1230,610),("emoji_bolsa_dinero",1510,355)):
                    juego._nuevo_item(tipo,x);juego.items[-1]["y"]=y
                if modo=="final":juego.final="BALANCE LOGRADO";juego.victoria=True;juego.estrellas=2;juego.porcentaje_equilibrio=.52;juego.tiempo_equilibrio=62.4;juego.elapsed=120;juego.tiempo=0
            else:
                juego.x=1220;juego.tiempo=102.0;juego.puntos=145
                juego.aviso="Explora con respeto y confirma antes de publicar.";juego.aviso_t=4
                if modo=="final":juego.final="LLEGASTE A GATE 7";juego.victoria=True;juego.casos=["Verificado","Evidencia entregada","Avisó","Respetó","Comprobó","Foto pública"]
            juego.pausa=(modo=="pausa")
            dibujar(juego,ventana.canvas)
            ventana.presentar((249,229,239))
            out=RAIZ_EXTRA/"_capturas"/f"{nombre}_{modo}_{ancho}x{alto}.png"
            pygame.image.save(ventana.window,str(out))
            # Preview para inspección visual segura (ancho máximo 1600 px).
            from PIL import Image
            preview=Image.open(out)
            if preview.width>1600:
                preview.thumbnail((1600,1600),Image.Resampling.LANCZOS)
                preview.save(out.with_name(out.stem+"_preview.png"))

def main():
    pygame.init()
    (RAIZ_EXTRA / "_capturas").mkdir(exist_ok=True)
    capturar("emoji_catch", EmojiCatch, lambda juego, canvas: juego.draw(canvas))
    capturar("curramgram_go", CurramGramGo, lambda juego, canvas: juego.draw(canvas))
    pygame.quit()


if __name__ == "__main__":
    main()
