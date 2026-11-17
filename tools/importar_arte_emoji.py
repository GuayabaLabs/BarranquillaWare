"""Importa el arte acuarela de Emoji Catch (fondo blanco) a assets/emoji_catch/.

Uso (desde la raíz):
    python tools/importar_arte_emoji.py artifacts/arte_recibido

Espera:
    21  balanza de dos platos (morado / azul)
    22  hoja con 4 manos moradas + 4 azules (arriba) y 6 emojis positivos (izquierda)
        y 6 negativos (derecha) en cuadrícula de 3 filas x 2 columnas.

Cada figura se separa por componentes conectados, se le quita el fondo blanco y se guarda en PNG.
Los nombres reemplazan a los recortes anteriores (mismos nombres que usa el juego) más dos emojis nuevos.
"""
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importar_arte_curramgram import buscar, quitar_fondo, tinta  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "assets" / "emoji_catch"

MANOS_MORADAS = ["mano_morada", "mano_morada_agarra", "mano_morada_puno", "mano_morada_atrapa"]
MANOS_AZULES = ["mano_azul_saluda", "mano_azul_der", "mano_azul_puno", "mano_azul_atrapa"]
POSITIVOS = ["emoji_sonriente", "emoji_estrellas", "emoji_pulgar_arriba", "emoji_cara_azul", "emoji_corazon", "emoji_angel"]
NEGATIVOS = ["emoji_enojado_rojo", "emoji_triste", "emoji_pulgar_abajo", "emoji_enojado_naranja", "emoji_vomito_1", "emoji_vomito_2"]


def componentes(mascara: np.ndarray, area_min: int):
    """Cajas (x0, y0, x1, y1) de los componentes 8-conectados con área >= area_min."""
    h, w = mascara.shape
    visto = np.zeros_like(mascara, bool)
    cajas = []
    ys, xs = np.nonzero(mascara)
    for y, x in zip(ys, xs):
        if visto[y, x]:
            continue
        cola = deque([(y, x)])
        visto[y, x] = True
        x0 = x1 = x
        y0 = y1 = y
        area = 0
        while cola:
            cy, cx = cola.popleft()
            area += 1
            x0, x1, y0, y1 = min(x0, cx), max(x1, cx), min(y0, cy), max(y1, cy)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and mascara[ny, nx] and not visto[ny, nx]:
                        visto[ny, nx] = True
                        cola.append((ny, nx))
        if area >= area_min:
            cajas.append((x0, y0, x1 + 1, y1 + 1))
    return cajas


def engrosar(m: np.ndarray, r: int) -> np.ndarray:
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(m, dy, axis=0), dx, axis=1)
    return out


def guardar(img: Image.Image, nombre: str) -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    img.save(DESTINO / f"{nombre}.png")
    print(f"  {nombre:28s} {img.size}")


def main(origen: Path) -> None:
    guardar(quitar_fondo(Image.open(buscar(origen, 21)).convert("RGB")), "balanza")

    hoja = Image.open(buscar(origen, 22)).convert("RGB")
    # Engrosar une los trazos sueltos de cada figura (p. ej. las líneas de movimiento de las manos).
    cajas = componentes(engrosar(tinta(hoja), 1), area_min=1500)
    centro = lambda c: ((c[0] + c[2]) / 2, (c[1] + c[3]) / 2)
    alto_manos = min(c[3] for c in cajas) + 120  # la fila de manos está arriba
    manos = sorted([c for c in cajas if centro(c)[1] < alto_manos and (c[3] - c[1]) > 60 and centro(c)[1] < 200],
                   key=lambda c: centro(c)[0])
    emojis = [c for c in cajas if c not in manos and centro(c)[1] >= 175]
    assert len(manos) == 8, f"Se esperaban 8 manos y salieron {len(manos)}: {manos}"
    assert len(emojis) == 12, f"Se esperaban 12 emojis y salieron {len(emojis)}: {emojis}"

    def recortar(c, pad=6):
        return quitar_fondo(hoja.crop((max(0, c[0] - pad), max(0, c[1] - pad), c[2] + pad, c[3] + pad)))

    for nombre, c in zip(MANOS_MORADAS + MANOS_AZULES, manos):
        guardar(recortar(c), nombre)
    for lado, nombres in ((lambda c: centro(c)[0] < hoja.width / 2, POSITIVOS),
                          (lambda c: centro(c)[0] >= hoja.width / 2, NEGATIVOS)):
        grupo = sorted([c for c in emojis if lado(c)], key=lambda c: (round(centro(c)[1] / 60), centro(c)[0]))
        assert len(grupo) == 6, f"Se esperaban 6 emojis por lado y salieron {len(grupo)}"
        for nombre, c in zip(nombres, grupo):
            guardar(recortar(c), nombre)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "artifacts" / "arte_recibido")
