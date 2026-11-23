"""Faroles del mapa: luz de noche sobre los faroles pintados en el dibujo.

Las posiciones (centro de la linterna y pie del poste) están en config/faroles_mapa.json; se encontraron
con tools/detectar_faroles.py (búsqueda por plantilla, revisada a ojo). De noche cada farol enciende su
linterna, un halo cálido y un charco de luz en el piso, con luz aditiva para que se vea como luz y no como
una mancha. Cada uno se prende con un umbral de oscuridad distinto y titila apenas.
"""
import math
import random
from typing import List, Tuple

import numpy as np
import pygame


import json
import os

RUTA_FAROLES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                            "config", "faroles_mapa.json")


def cargar_faroles(ruta: str = RUTA_FAROLES) -> List[Tuple[int, int, int]]:
    """Posiciones verificadas de los faroles: (x linterna, y linterna, y pie). Las genera tools/detectar_faroles.py."""
    try:
        with open(ruta, encoding="utf-8") as f:
            return [tuple(int(v) for v in p) for p in json.load(f)["faroles"]]
    except (OSError, ValueError, KeyError):
        return []


def _halo(ancho: int, alto: int, color: Tuple[int, int, int], fuerza: float, potencia: float = 1.8) -> pygame.Surface:
    """Halo elíptico para mezcla aditiva (el negro no suma; el color decae suave hacia afuera)."""
    sup = pygame.Surface((ancho, alto))
    yy, xx = np.mgrid[0:alto, 0:ancho]
    d = np.sqrt(((xx - ancho / 2 + 0.5) / (ancho / 2)) ** 2 + ((yy - alto / 2 + 0.5) / (alto / 2)) ** 2)
    caida = np.clip(1.0 - d, 0.0, 1.0) ** potencia * fuerza
    arr = pygame.surfarray.pixels3d(sup)
    for c in range(3):
        arr[..., c] = np.clip(caida.T * color[c], 0, 255).astype(np.uint8)
    del arr
    if pygame.display.get_surface() is not None:
        sup = sup.convert()
    return sup


class Faroles:
    NIVELES = 12   # Intensidades precalculadas (la mezcla aditiva no usa transparencia)

    def __init__(self, puntos=None, semilla: int = 3) -> None:
        self.puntos = list(puntos) if puntos is not None else cargar_faroles()
        rnd = random.Random(semilla)
        # Cada farol se prende con un umbral de oscuridad un poco distinto (no todos de golpe) y titila a su ritmo.
        self.umbral = [rnd.uniform(0.30, 0.48) for _ in self.puntos]
        self.fase = [rnd.uniform(0, math.tau) for _ in self.puntos]
        n = self.NIVELES
        # Luz que el farol deja en el mapa de luz: un charco amplio en el piso alrededor del poste (elíptico,
        # porque el piso del mapa está en perspectiva) y luz cálida alrededor de la linterna.
        # Color ámbar: sumado a la noche azul (≈ 56, 70, 132) devuelve el color cálido real del piso
        # (≈ 255, 230, 200) sin quemarlo a blanco.
        self.charcos = [_halo(330, 190, (205, 162, 74), (i + 1) / n, 1.5) for i in range(n)]
        self.auras = [_halo(150, 150, (215, 172, 86), 0.9 * (i + 1) / n, 2.0) for i in range(n)]
        # Brillo de la bombilla que se suma encima de todo (resplandor pequeño y núcleo).
        self.bombillas = [_halo(64, 64, (255, 232, 160), 0.95 * (i + 1) / n, 2.2) for i in range(n)]

    def intensidad(self, i: int, oscuridad: float, t: float) -> float:
        """0 apagado … 1 encendido; se prende en ~0.15 de oscuridad y titila apenas."""
        base = max(0.0, min(1.0, (oscuridad - self.umbral[i]) / 0.15))
        if base <= 0.0:
            return 0.0
        titileo = 0.94 + 0.06 * math.sin(t * 7.0 + self.fase[i]) * math.sin(t * 2.3 + self.fase[i] * 1.7)
        return base * titileo

    def _visibles(self, tam, cam_x, cam_y, oscuridad, t):
        if oscuridad <= 0.28 or not self.puntos:
            return
        sw, sh = tam
        for i, (x, y, pie) in enumerate(self.puntos):
            sx, sy = x - cam_x, y - cam_y
            if not (-200 < sx < sw + 200 and -200 < sy < sh + 240):
                continue
            # Con poca oscuridad (crepúsculo) la luz se nota menos: escala con lo oscuro que esté.
            f = self.intensidad(i, oscuridad, t) * (0.35 + 0.65 * oscuridad)
            if f > 0.02:
                yield sx, sy, pie - cam_y, min(self.NIVELES - 1, int(f * self.NIVELES))

    def iluminar(self, lm: pygame.Surface, cam_x: int, cam_y: int, oscuridad: float, t: float) -> bool:
        """Suma la luz de los faroles encendidos al mapa de luz. Devuelve True si prendió alguno."""
        alguno = False
        aditivo = pygame.BLEND_RGB_ADD
        for sx, sy, spie, n in self._visibles(lm.get_size(), cam_x, cam_y, oscuridad, t):
            charco = self.charcos[n]
            lm.blit(charco, charco.get_rect(center=(sx, spie - 8)), special_flags=aditivo)
            aura = self.auras[n]
            lm.blit(aura, aura.get_rect(center=(sx, sy + 6)), special_flags=aditivo)
            alguno = True
        return alguno

    def render(self, surface: pygame.Surface, cam_x: int, cam_y: int, oscuridad: float, t: float) -> None:
        """Brillo de las bombillas encima de todo (después de aplicar el mapa de luz)."""
        aditivo = pygame.BLEND_RGB_ADD
        for sx, sy, _spie, n in self._visibles(surface.get_size(), cam_x, cam_y, oscuridad, t):
            b = self.bombillas[n]
            surface.blit(b, b.get_rect(center=(sx, sy)), special_flags=aditivo)
