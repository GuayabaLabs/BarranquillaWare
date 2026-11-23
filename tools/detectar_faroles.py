"""Encuentra los faroles pintados en el mapa y guarda sus posiciones en config/faroles_mapa.json.

Uso (desde la raíz):
    python tools/detectar_faroles.py [--umbral 0.55] [--muestra artifacts/faroles_candidatos.png]

Método: correlación normalizada (por FFT, a media resolución) contra plantillas de farol recortadas del
propio mapa, en escala de grises y en canal "amarillo" (la linterna). Se toman los picos por encima del
umbral, separados al menos 40 px. Guarda una hoja de contacto con cada candidato para revisarla a ojo;
los índices que no sean faroles se pueden excluir con --excluir 3,7.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
SALIDA = RAIZ / "config" / "faroles_mapa.json"
# Faroles de referencia (centro de la linterna en el mundo) usados como plantilla.
PLANTILLAS = [(1010, 452), (818, 1082)]
CAJA = (-22, -26, 22, 62)   # Recorte alrededor de la linterna: linterna + poste
# Faroles dibujados a otra escala (junto a la playa) que la plantilla no reconoce: (x, y linterna, y pie)
EXTRA = [(2084, 533, 568), (2267, 629, 658)]


def canales(img: np.ndarray) -> np.ndarray:
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    gris = 0.3 * r + 0.59 * g + 0.11 * b
    amarillo = np.clip((r + g) / 2 - b - 40, 0, 255)
    return np.stack([gris, amarillo], axis=-1)


def ncc(imagen: np.ndarray, plantilla: np.ndarray) -> np.ndarray:
    """Correlación cruzada normalizada (válida) con FFT. imagen/plantilla en 2D."""
    th, tw = plantilla.shape
    ih, iw = imagen.shape
    t = plantilla - plantilla.mean()
    t /= np.sqrt((t ** 2).sum()) + 1e-6
    fh, fw = ih + th, iw + tw
    F = np.fft.rfft2(imagen, (fh, fw))
    T = np.fft.rfft2(t[::-1, ::-1], (fh, fw))
    corr = np.fft.irfft2(F * T, (fh, fw))[th - 1:ih, tw - 1:iw]
    # Normalización local por la energía de la ventana (con imágenes integrales)
    def suma_ventana(a):
        c = np.cumsum(np.cumsum(np.pad(a, ((1, 0), (1, 0))), axis=0), axis=1)
        return c[th:, tw:] - c[:-th, tw:] - c[th:, :-tw] + c[:-th, :-tw]
    s1 = suma_ventana(imagen)
    s2 = suma_ventana(imagen ** 2)
    var = np.maximum(s2 - s1 ** 2 / (th * tw), 1e-6)
    return corr / np.sqrt(var)


def detectar(mundo_png: Path, umbral: float):
    img = np.asarray(Image.open(mundo_png).convert("RGB")).astype(np.float64)
    k = 2
    chica = img[: img.shape[0] // k * k, : img.shape[1] // k * k].reshape(img.shape[0] // k, k, img.shape[1] // k, k, 3).mean(axis=(1, 3))
    ch = canales(chica)
    puntaje = None
    for (px, py) in PLANTILLAS:
        x0, y0, x1, y1 = (px + CAJA[0]) // k, (py + CAJA[1]) // k, (px + CAJA[2]) // k, (py + CAJA[3]) // k
        total = 0
        for c in range(ch.shape[-1]):
            total = total + ncc(ch[..., c], ch[y0:y1, x0:x1, c])
        total = total / ch.shape[-1]
        puntaje = total if puntaje is None else np.maximum(puntaje, total)
    # Picos: máximos locales por encima del umbral, separados >= 40 px (20 a media resolución)
    picos = []
    orden = np.argsort(puntaje, axis=None)[::-1]
    ys, xs = np.unravel_index(orden, puntaje.shape)
    for y, x in zip(ys, xs):
        v = puntaje[y, x]
        if v < umbral:
            break
        if all(abs(x - qx) > 20 or abs(y - qy) > 20 for qx, qy, _ in picos):
            picos.append((x, y, float(v)))
    # Coordenadas del mundo: centro de la linterna y pie del poste (fin del tramo oscuro continuo)
    oscuro = img.max(axis=2) < 90
    faroles = []
    for x, y, v in picos:
        lx = int(x * k - CAJA[0])
        ly = int(y * k - CAJA[1])
        pie, hueco = ly + 12, 0
        for yy in range(ly + 12, min(img.shape[0], ly + 110)):
            if oscuro[yy, lx - 2:lx + 3].any():
                pie, hueco = yy, 0
            else:
                hueco += 1
                if hueco > 3:
                    break
        faroles.append({"x": lx, "y": ly, "pie": pie, "puntaje": round(v, 3)})
    return faroles


def hoja_contacto(mundo_png: Path, faroles, destino: Path) -> None:
    img = Image.open(mundo_png).convert("RGB")
    n = len(faroles)
    cols = 10
    filas = (n + cols - 1) // cols
    hoja = Image.new("RGB", (cols * 90, max(1, filas) * 130), (40, 40, 40))
    from PIL import ImageDraw
    d = ImageDraw.Draw(hoja)
    for i, f in enumerate(faroles):
        rec = img.crop((f["x"] - 35, f["y"] - 40, f["x"] + 35, f["y"] + 70)).resize((84, 120))
        hoja.paste(rec, ((i % cols) * 90 + 3, (i // cols) * 130 + 3))
        d.text(((i % cols) * 90 + 5, (i // cols) * 130 + 3), str(i), fill=(255, 0, 255))
    hoja.save(destino)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--mundo", default=str(RAIZ / "artifacts" / "mundo.png"),
                   help="Imagen del mapa mundial completo (se genera con el juego)")
    p.add_argument("--umbral", type=float, default=0.55)
    p.add_argument("--excluir", default="", help="Índices de candidatos que no son faroles, separados por coma")
    p.add_argument("--muestra", default=str(RAIZ / "artifacts" / "faroles_candidatos.png"))
    a = p.parse_args()
    faroles = detectar(Path(a.mundo), a.umbral)
    hoja_contacto(Path(a.mundo), faroles, Path(a.muestra))
    excluir = {int(i) for i in a.excluir.split(",") if i.strip()}
    finales = [f for i, f in enumerate(faroles) if i not in excluir]
    finales += [{"x": x, "y": y, "pie": pie} for x, y, pie in EXTRA]
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(json.dumps({"faroles": [[f["x"], f["y"], f["pie"]] for f in finales]}, indent=1), encoding="utf-8")
    print(f"{len(faroles)} candidatos, {len(finales)} guardados en {SALIDA}; hoja de contacto: {a.muestra}")


if __name__ == "__main__":
    main()
