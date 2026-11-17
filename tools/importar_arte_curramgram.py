"""Importa el arte acuarela de CurramGram Go! (imágenes con fondo blanco) a assets/curramgram/.

Uso (desde la raíz):
    python tools/importar_arte_curramgram.py artifacts/arte_recibido

Espera en la carpeta de origen los archivos numerados tal como se recibieron:
     6 pared del terminal       7 piso                 8 visor de cámara      9 círculo de caso
    10-15 botones (caminar, saltar, esconder, avisar, foto, publicar)
    16 sello de pasaporte      17 logo                18 hoja de props (3x2)
    19 hoja de personajes      20 hoja de Cami

Qué hace:
- Quita el fondo blanco conectado al borde (no el blanco interno) y limpia el halo del recorte.
- En las hojas separa cada figura y descarta las etiquetas de texto de abajo.
- Guarda PNG con transparencia; los fondos (pared y piso) se recortan opacos.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "assets" / "curramgram"

BOTONES = ["caminar", "saltar", "esconder", "avisar", "foto", "publicar"]
PROPS = ["mostrador_checkin", "puesto_butifarras", "banca_espera", "pilar_palmera", "caseta_policia", "puerta_7"]
PERSONAJES = ["policia", "viajero", "turista", "joven", "tamborero", "senora", "comparsa", "trabajador"]
CAMI = ["quieta", "camina_1", "camina_2", "camina_3", "camina_4", "agachada", "saltando", "foto"]


def buscar(origen: Path, numero: int) -> Path:
    for ext in (".png", ".webp", ".jpg", ".jpeg"):
        p = origen / f"{numero}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(f"Falta la imagen {numero} en {origen}")


def es_fondo(rgb: np.ndarray, tol_min: int = 228, tol_chroma: int = 22) -> np.ndarray:
    return (rgb.min(axis=2) >= tol_min) & ((rgb.max(axis=2) - rgb.min(axis=2)) <= tol_chroma)


def _vecinos(m: np.ndarray) -> np.ndarray:
    v = np.zeros_like(m)
    v[1:, :] |= m[:-1, :]
    v[:-1, :] |= m[1:, :]
    v[:, 1:] |= m[:, :-1]
    v[:, :-1] |= m[:, 1:]
    return v


def inundar(fondo: np.ndarray, semillas: np.ndarray) -> np.ndarray:
    """Región de `fondo` conectada a las semillas (relleno por inundación con numpy)."""
    region = semillas & fondo
    while True:
        nueva = (region | _vecinos(region)) & fondo
        if (nueva == region).all():
            return region
        region = nueva


def quitar_fondo(img: Image.Image, semillas_extra=()) -> Image.Image:
    rgb = np.asarray(img.convert("RGB")).astype(np.int16)
    h, w = rgb.shape[:2]
    fondo = es_fondo(rgb)
    semillas = np.zeros((h, w), bool)
    semillas[0, :] = semillas[-1, :] = True
    semillas[:, 0] = semillas[:, -1] = True
    for fx, fy in semillas_extra:
        semillas[int(fy * (h - 1)), int(fx * (w - 1))] = True
    transparente = inundar(fondo, semillas)
    # Halo: píxeles claros pegados al fondo quitado.
    claro = (rgb.min(axis=2) >= 205) & ((rgb.max(axis=2) - rgb.min(axis=2)) <= 40)
    for _ in range(2):
        transparente |= _vecinos(transparente) & claro
    alpha = np.where(transparente, 0, 255).astype(np.uint8)
    # Borde suave de 1 px para que no se vea serrucho.
    borde = _vecinos(transparente) & ~transparente
    alpha[borde] = 170
    out = np.dstack([rgb.astype(np.uint8), alpha])
    res = Image.fromarray(out, "RGBA")
    caja = res.getbbox()
    return res.crop(caja) if caja else res


def bandas(perfil: np.ndarray, umbral: int = 2, hueco: int = 6):
    """Tramos consecutivos donde perfil > umbral, uniendo huecos pequeños."""
    tramos, inicio, ultimo = [], None, None
    for i, v in enumerate(perfil):
        if v > umbral:
            if inicio is None:
                inicio = i
            elif ultimo is not None and i - ultimo > hueco:
                tramos.append((inicio, ultimo + 1))
                inicio = i
            ultimo = i
    if inicio is not None:
        tramos.append((inicio, ultimo + 1))
    return tramos


def tinta(img: Image.Image) -> np.ndarray:
    rgb = np.asarray(img.convert("RGB")).astype(np.int16)
    return ~es_fondo(rgb, 215, 30)


def figuras_en_hoja(img: Image.Image, banda_figuras, hueco_columnas: int = 10):
    """Recorta cada figura de una fila: separa columnas por blanco y descarta etiquetas (bandas bajas)."""
    t = tinta(img)
    y0, y1 = banda_figuras
    columnas = bandas(t[y0:y1].sum(axis=0), umbral=1, hueco=hueco_columnas)
    piezas = []
    for x0, x1 in columnas:
        if x1 - x0 < 25:
            continue
        sub = t[:, x0:x1]
        filas = [b for b in bandas(sub.sum(axis=1), umbral=1, hueco=4) if b[1] > y0 and b[0] < y1]
        # La figura es la banda con más tinta; las etiquetas son bandas delgadas de texto.
        mejor = max(filas, key=lambda b: sub[b[0]:b[1]].sum())
        piezas.append(img.crop((max(0, x0 - 4), max(0, mejor[0] - 4), x1 + 4, mejor[1] + 4)))
    return piezas


def guardar(img: Image.Image, nombre: str) -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    ruta = DESTINO / nombre
    img.save(ruta)
    print(f"  {nombre:32s} {img.size}")


def main(origen: Path) -> None:
    abrir = lambda n: Image.open(buscar(origen, n)).convert("RGB")

    # Fondos: recorte opaco de la zona pintada.
    pared = abrir(6)
    caja = Image.fromarray((tinta(pared) * 255).astype(np.uint8)).getbbox()
    # La pared termina donde empieza el piso pintado (≈ 72 % del alto de la zona pintada).
    x0, y0, x1, y1 = caja
    guardar(pared.crop((x0 + 2, y0 + 2, x1 - 2, y0 + int((y1 - y0) * 0.78))), "fondo_pared_terminal.png")
    piso = abrir(7)
    w, h = piso.size
    guardar(piso.crop((int(w * 0.15), int(h * 0.30), int(w * 0.85), int(h * 0.80))), "fondo_piso_terminal.png")

    guardar(quitar_fondo(abrir(8), ((0.5, 0.5),)), "visor_camara.png")
    guardar(quitar_fondo(abrir(9)), "circulo_caso.png")
    for i, nombre in enumerate(BOTONES):
        guardar(quitar_fondo(abrir(10 + i)), f"boton_{nombre}.png")
    guardar(quitar_fondo(abrir(16)), "sello_pasaporte.png")
    guardar(quitar_fondo(abrir(17)), "logo_curramgram.png")

    hoja = abrir(18)
    filas = bandas(tinta(hoja).sum(axis=1), umbral=2, hueco=6)
    filas = [f for f in filas if f[1] - f[0] > 60]  # sin las bandas de etiquetas
    piezas = []
    for f in filas:
        piezas += figuras_en_hoja(hoja, f, hueco_columnas=30)
    assert len(piezas) == len(PROPS), f"Se esperaban {len(PROPS)} props y salieron {len(piezas)}"
    for nombre, pieza in zip(PROPS, piezas):
        guardar(quitar_fondo(pieza), f"{nombre}.png")

    # Hoja de Cami: los cuadros de caminar están casi pegados, por eso el hueco entre columnas es menor.
    for numero, nombres, prefijo, hueco in ((19, PERSONAJES, "acuarela_", 12), (20, CAMI, "acuarela_cami_", 6)):
        hoja = abrir(numero)
        fila = max(bandas(tinta(hoja).sum(axis=1), umbral=2, hueco=6), key=lambda b: b[1] - b[0])
        piezas = figuras_en_hoja(hoja, fila, hueco_columnas=hueco)
        assert len(piezas) == len(nombres), f"Hoja {numero}: se esperaban {len(nombres)} figuras y salieron {len(piezas)}"
        for nombre, pieza in zip(nombres, piezas):
            guardar(quitar_fondo(pieza), f"{prefijo}{nombre}.png")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "artifacts" / "arte_recibido")
