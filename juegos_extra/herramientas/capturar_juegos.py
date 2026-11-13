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
                if modo=="final":juego.final="BALANCE LOGRADO";juego.victoria=True;juego.estrellas=1;juego.porcentaje_equilibrio=.52;juego.tiempo_equilibrio=62.4;juego.elapsed=120;juego.tiempo=0
            else:
                juego.inicio=False;juego.x=350;juego.tiempo=102.0;juego.puntos=145
                juego.aviso="+5 Sello";juego.aviso_t=4
                juego.revelados[0]=True;juego.investigacion[0]=.45
                if modo=="final":
                    juego.final="LLEGASTE A GATE 7";juego.victoria=True;juego.puntos=375
                    juego.casos=["Confirmó que era maizena","Avisó a la turista","Pasó de largo y respetó privacidad","Era hielo derramado","Foto pública y respetuosa","Evidencia entregada a Policía"]
            juego.pausa=(modo=="pausa")
            dibujar(juego,ventana.canvas)
            ventana.presentar((249,229,239))
            sufijo="" if modo=="juego" else f"_{modo}"
            out=RAIZ_EXTRA/"_capturas"/f"{nombre}{sufijo}_{ancho}x{alto}.png"
            pygame.image.save(ventana.window,str(out))
            # Los renders 1920×1080 se guardan reducidos para inspección segura.
            from PIL import Image
            preview=Image.open(out)
            if preview.width>1600:
                preview.thumbnail((1600,1600),Image.Resampling.LANCZOS)
                preview.save(out)

def main():
    pygame.init()
    (RAIZ_EXTRA / "_capturas").mkdir(exist_ok=True)
    capturar("emoji_catch", EmojiCatch, lambda juego, canvas: juego.draw(canvas,(80,80)))
    capturar("curramgram_go", CurramGramGo, lambda juego, canvas: juego.draw(canvas,(80,80)))
    pygame.quit()


if __name__ == "__main__":
    main()
