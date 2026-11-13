"""Comprueba existencia y decodificación de todos los recursos requeridos."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from comun import ASSETS_REQUERIDOS, RAIZ


def comprobar(relativo):
    ruta = RAIZ / relativo
    if not ruta.is_file():
        return False, "NO EXISTE", "—"
    try:
        ext = ruta.suffix.lower()
        if ext == ".png":
            recurso = pygame.image.load(str(ruta))
            detalle = f"{recurso.get_width()}x{recurso.get_height()} px"
        elif ext == ".ttf":
            pygame.font.Font(str(ruta), 16)
            detalle = f"{ruta.stat().st_size:,} bytes"
        elif ext in (".ogg", ".wav", ".mp3"):
            sonido = pygame.mixer.Sound(str(ruta))
            detalle = f"{sonido.get_length():.2f} s · {ruta.stat().st_size:,} bytes"
        elif ext == ".json":
            data = json.loads(ruta.read_text(encoding="utf-8-sig"))
            detalle = f"JSON válido · {len(data)} grupos/entradas"
        else:
            detalle = f"{ruta.stat().st_size:,} bytes"
        return True, "OK", detalle
    except (OSError, pygame.error, ValueError, json.JSONDecodeError) as exc:
        return False, f"ERROR DE CARGA: {exc}", "—"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--juego", choices=(*ASSETS_REQUERIDOS, "todos"), default="todos")
    args = parser.parse_args()
    pygame.init()
    pygame.font.init()
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    juegos = ASSETS_REQUERIDOS if args.juego == "todos" else {args.juego: ASSETS_REQUERIDOS[args.juego]}
    fallo = False
    for juego, recursos in juegos.items():
        print(f"\n[{juego}] {len(recursos)} recursos requeridos")
        for relativo in recursos:
            ok, estado, detalle = comprobar(relativo)
            print(f"{'OK ' if ok else 'FALTA'} | {estado:20} | {relativo} -> {RAIZ / relativo} | {detalle}")
            fallo |= not ok
    pygame.quit()
    return 1 if fallo else 0


if __name__ == "__main__":
    raise SystemExit(main())
