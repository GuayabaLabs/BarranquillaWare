"""Ajusta un POI acuarela pálido al estilo caricatura del mapa (color vivo + tinta + contorno).

Uso (desde la raíz):
    python tools/estilizar_poi.py assets/metropolitano_mapa.png [--sat 1.5] [--contraste 1.25] [--contorno 9]

Guarda una copia del original en artifacts/poi_originales/ la primera vez y
sobrescribe el asset con la versión estilizada. Conserva dimensiones y transparencia.
"""
import argparse
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

RAIZ = Path(__file__).resolve().parent.parent
TINTA = (58, 38, 40)


def estilizar(img: Image.Image, sat: float, contraste: float, contorno: int, tinta: float) -> Image.Image:
    img = img.convert("RGBA")
    alpha = img.getchannel("A")
    rgb = img.convert("RGB")

    # 1. Color y contraste como el resto del mapa.
    rgb = ImageEnhance.Color(rgb).enhance(sat)
    rgb = ImageEnhance.Contrast(rgb).enhance(contraste)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.6)

    # 2. Líneas de tinta internas a partir de los bordes de luminancia.
    gris = rgb.convert("L").filter(ImageFilter.GaussianBlur(1.2))
    bordes = np.asarray(gris.filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    lineas = np.clip((bordes - 10.0) / 30.0, 0.0, 1.0) * tinta
    base = np.asarray(rgb, dtype=np.float32)
    tinta_rgb = np.array(TINTA, dtype=np.float32)
    base = base * (1 - lineas[..., None]) + tinta_rgb * lineas[..., None]

    # 3. Contorno exterior oscuro alrededor de la silueta.
    a = np.asarray(alpha, dtype=np.float32) / 255.0
    sil = Image.fromarray(((a > 0.35) * 255).astype(np.uint8))
    dil = np.asarray(sil.filter(ImageFilter.MaxFilter(contorno * 2 + 1)), dtype=np.float32) / 255.0
    dil = np.asarray(Image.fromarray((dil * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0)),
                     dtype=np.float32) / 255.0

    out_a = np.maximum(a, dil)
    peso_img = np.where(out_a > 0, a / np.maximum(out_a, 1e-6), 0.0)[..., None]
    out_rgb = base * peso_img + tinta_rgb * (1 - peso_img)

    res = np.dstack([np.clip(out_rgb, 0, 255), out_a * 255]).astype(np.uint8)
    return Image.fromarray(res, "RGBA")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("asset")
    p.add_argument("--sat", type=float, default=1.5)
    p.add_argument("--contraste", type=float, default=1.25)
    p.add_argument("--contorno", type=int, default=9)
    p.add_argument("--tinta", type=float, default=0.55)
    p.add_argument("--salida", default=None, help="Ruta de salida (por defecto sobrescribe el asset)")
    args = p.parse_args()

    ruta = (RAIZ / args.asset).resolve()
    respaldo = RAIZ / "artifacts" / "poi_originales" / ruta.name
    respaldo.parent.mkdir(parents=True, exist_ok=True)
    if not respaldo.exists():
        shutil.copy2(ruta, respaldo)

    # Siempre parte del original para que el script sea repetible.
    resultado = estilizar(Image.open(respaldo), args.sat, args.contraste, args.contorno, args.tinta)
    destino = Path(args.salida) if args.salida else ruta
    resultado.save(destino)
    print(f"{ruta.name}: {resultado.size} -> {destino}")


if __name__ == "__main__":
    main()
