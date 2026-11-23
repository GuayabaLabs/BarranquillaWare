"""Iluminación nocturna de los lugares emblemáticos y luces rojas de guía del aeropuerto.

- Edificios: la silueta de cada lugar (su sprite estampado en el mapa) se usa como "reflector": en el mapa
  de luz se suma la silueta en color cálido (el edificio se ve casi con sus colores reales) más un resplandor
  suave alrededor. Las calles y zonas sin nada siguen con la oscuridad normal de la noche.
- Estrellas/pines de cada nivel: dan luz a su alrededor y brillan encima.
- Aeropuerto: luces rojas de borde de pista que corren hacia la cabecera (guía de despegue), barras rojas
  en ambas cabeceras y una baliza roja que parpadea en la torre de control. Coordenadas relativas al
  sprite del aeropuerto (540 px de ancho), así siguen al edificio si se mueve o escala.
"""
import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pygame

COLOR_EDIFICIO = (190, 160, 82)     # Se suma al azul de la noche (≈ 56, 70, 132) → colores cálidos casi reales
COLOR_RESPLANDOR = (120, 96, 46)
MARGEN = 46                         # px de resplandor alrededor de la silueta
# Intensidad por lugar (1 = como el resto). El aeropuerto queda más tenue para que resalten sus luces rojas.
INTENSIDAD_LUGAR = {"aeropuerto": 0.62}


def _convertir(sup: pygame.Surface) -> pygame.Surface:
    return sup.convert() if pygame.display.get_surface() is not None else sup


def luz_de_silueta(sprite: pygame.Surface) -> pygame.Surface:
    """Superficie RGB (para sumar) con la silueta del sprite iluminada y un resplandor suave alrededor."""
    w, h = sprite.get_size()
    alfa = pygame.surfarray.array_alpha(sprite).astype(np.float32) / 255.0
    lienzo = np.zeros((w + 2 * MARGEN, h + 2 * MARGEN), np.float32)
    lienzo[MARGEN:MARGEN + w, MARGEN:MARGEN + h] = (alfa > 0.15).astype(np.float32)

    # Resplandor: la silueta reducida, ensanchada y suavizada (con smoothscale, rápido).
    W, H = lienzo.shape
    chico = pygame.Surface((W, H))
    v = (lienzo * 255).astype(np.uint8)
    pygame.surfarray.pixels3d(chico)[:] = v[..., None]
    for factor in (8, 4):
        chico = pygame.transform.smoothscale(chico, (max(1, W // factor), max(1, H // factor)))
        chico = pygame.transform.smoothscale(chico, (W, H))
    resplandor = pygame.surfarray.array3d(chico)[..., 0].astype(np.float32) / 255.0
    resplandor = np.clip(resplandor * 1.8, 0.0, 1.0)

    salida = np.zeros((W, H, 3), np.float32)
    for c in range(3):
        salida[..., c] = np.maximum(lienzo * COLOR_EDIFICIO[c], resplandor * COLOR_RESPLANDOR[c])
    sup = pygame.Surface((W, H))
    pygame.surfarray.pixels3d(sup)[:] = np.clip(salida, 0, 255).astype(np.uint8)
    return _convertir(sup)


def halo(diam_x: int, diam_y: int, color, fuerza: float, potencia: float = 1.8) -> pygame.Surface:
    yy, xx = np.mgrid[0:diam_y, 0:diam_x]
    d = np.sqrt(((xx - diam_x / 2 + 0.5) / (diam_x / 2)) ** 2 + ((yy - diam_y / 2 + 0.5) / (diam_y / 2)) ** 2)
    caida = np.clip(1.0 - d, 0.0, 1.0) ** potencia * fuerza
    sup = pygame.Surface((diam_x, diam_y))
    arr = pygame.surfarray.pixels3d(sup)
    for c in range(3):
        arr[..., c] = np.clip(caida.T * color[c], 0, 255).astype(np.uint8)
    del arr
    return _convertir(sup)


# --- Aeropuerto (coordenadas en el sprite de 540 px de ancho) -------------------------------------
BORDE_A = ((186, 304), (478, 129))   # Borde superior de la pista (cabecera baja → cabecera alta)
BORDE_B = ((224, 326), (514, 151))   # Borde inferior de la pista
CABECERA_BAJA = ((193, 310), (219, 323))
CABECERA_ALTA = ((472, 133), (505, 148))
TORRE = (446, 6)
ANCHO_REF = 540.0
N_LUCES_BORDE = 12


class LucesLugares:
    NIVELES = 12

    def __init__(self, siluetas: Dict[str, Tuple[pygame.Surface, pygame.Rect]]) -> None:
        """`siluetas`: clave del lugar → (sprite estampado, rect en el mundo)."""
        self.luces: Dict[str, Tuple[pygame.Surface, Tuple[int, int]]] = {}
        for clave, (sprite, rect) in siluetas.items():
            try:
                luz = luz_de_silueta(sprite)
                k = INTENSIDAD_LUGAR.get(clave, 1.0)
                if k < 1.0:
                    v = int(255 * k)
                    luz.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
                self.luces[clave] = (luz, (rect.x - MARGEN, rect.y - MARGEN))
            except (pygame.error, ValueError):
                pass
        self._tmp: Optional[pygame.Surface] = None
        n = self.NIVELES
        self.halos_estrella = [halo(210, 170, (230, 200, 120), (i + 1) / n, 1.7) for i in range(n)]
        self.brillo_estrella = halo(70, 70, (255, 225, 140), 0.9, 2.0)
        self.halo_rojo = halo(34, 34, (200, 12, 6), 0.8, 2.2)
        self.baliza = halo(110, 110, (255, 30, 20), 1.0, 1.8)

    # --- edificios y estrellas (en el mapa de luz) -----------------------------------------------------
    def _luz_a_nivel(self, clave: str, luz: pygame.Surface, nivel: int) -> pygame.Surface:
        """Luz del lugar atenuada a `nivel` (1..NIVELES). Se guarda la última por lugar: al encenderse
        al anochecer cambia de nivel unas pocas veces, no en cada cuadro."""
        if nivel >= self.NIVELES:
            return luz
        guardada = self._cache_nivel.get(clave)
        if guardada is not None and guardada[0] == nivel:
            return guardada[1]
        # Un solo lugar se recalcula por cuadro (los demás usan su nivel anterior un instante): sin tirones.
        if self._recalculado_este_cuadro and guardada is not None:
            return guardada[1]
        self._recalculado_este_cuadro = True
        atenuada = luz.copy()
        v = int(255 * nivel / self.NIVELES)
        atenuada.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
        self._cache_nivel[clave] = (nivel, atenuada)
        return atenuada

    def iluminar(self, lm: pygame.Surface, cam_x: int, cam_y: int, fuerza: float) -> bool:
        if fuerza <= 0.02 or not self.luces:
            return False
        if not hasattr(self, "_cache_nivel"):
            self._cache_nivel = {}
        self._recalculado_este_cuadro = False
        sw, sh = lm.get_size()
        nivel = max(1, min(self.NIVELES, int(round(fuerza * self.NIVELES))))
        alguno = False
        for clave, (luz, (wx, wy)) in self.luces.items():
            x, y = wx - cam_x, wy - cam_y
            if x > sw or y > sh or x + luz.get_width() < 0 or y + luz.get_height() < 0:
                continue
            lm.blit(self._luz_a_nivel(clave, luz, nivel), (x, y), special_flags=pygame.BLEND_RGB_ADD)
            alguno = True
        return alguno

    def iluminar_estrellas(self, lm: pygame.Surface, pines: List[Tuple[int, int, bool]], fuerza: float) -> None:
        """`pines`: (x, y en pantalla, completado). Las estrellas doradas alumbran más que los pines."""
        aditivo = pygame.BLEND_RGB_ADD
        for x, y, hecho in pines:
            k = fuerza * (1.0 if hecho else 0.7)
            h = self.halos_estrella[max(0, min(self.NIVELES - 1, int(k * self.NIVELES)))]
            lm.blit(h, h.get_rect(center=(x, y + 30)), special_flags=aditivo)

    def brillar_estrellas(self, surface: pygame.Surface, pines: List[Tuple[int, int, bool]], fuerza: float, t: float) -> None:
        """Destello de luz propia encima de cada estrella/pin (después del mapa de luz)."""
        if fuerza <= 0.05:
            return
        for x, y, hecho in pines:
            pulso = 0.75 + 0.25 * math.sin(t * 2.6 + x * 0.013)
            b = self.brillo_estrella.copy() if (fuerza * pulso) < 0.99 else self.brillo_estrella
            if b is not self.brillo_estrella:
                v = int(255 * fuerza * pulso * (1.0 if hecho else 0.75))
                b.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
            surface.blit(b, b.get_rect(center=(x, y)), special_flags=pygame.BLEND_RGB_ADD)

    # --- aeropuerto --------------------------------------------------------------------------------
    @staticmethod
    def _a_pantalla(p, rect: pygame.Rect, cam_x: int, cam_y: int) -> Tuple[int, int]:
        e = rect.width / ANCHO_REF
        return int(rect.x + p[0] * e - cam_x), int(rect.y + p[1] * e - cam_y)

    def luces_aeropuerto(self, surface: pygame.Surface, rect: pygame.Rect, cam_x: int, cam_y: int,
                         oscuridad: float, t: float) -> None:
        """Luces rojas de guía (siempre encendidas; de día tenues, de noche intensas)."""
        sw, sh = surface.get_size()
        if rect.right - cam_x < -50 or rect.x - cam_x > sw + 50 or rect.bottom - cam_y < -50 or rect.y - cam_y > sh + 50:
            return
        base = 0.3 + 0.7 * min(1.0, oscuridad / 0.7)
        aditivo = pygame.BLEND_RGB_ADD
        halo_r = self.halo_rojo.copy()

        def encender(pos, k):
            """Bombillo rojo nítido (sólido, no se aclara sobre fondos claros) + halo rojo pequeño."""
            if k <= 0.03:
                return
            k = min(1.0, k)
            v = int(255 * k)
            halo_r.blit(self.halo_rojo, (0, 0))
            halo_r.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
            surface.blit(halo_r, halo_r.get_rect(center=pos), special_flags=aditivo)
            r = 2 if k < 0.6 else 3
            rojo = (int(120 + 135 * k), int(10 + 30 * k), int(8 + 20 * k))
            pygame.draw.circle(surface, (60, 8, 6), pos, r + 1)
            pygame.draw.circle(surface, rojo, pos, r)
            if k > 0.75:
                pygame.draw.circle(surface, (255, 190, 170), pos, 1)

        # Bordes de pista: tenues siempre + "conejo" que corre hacia la cabecera alta (dirección de despegue).
        ciclo = 1.6
        fase = (t % ciclo) / ciclo
        for (a, b) in (BORDE_A, BORDE_B):
            for i in range(N_LUCES_BORDE):
                f = i / (N_LUCES_BORDE - 1)
                p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
                d = (fase - f) % 1.0
                corredor = max(0.0, 1.0 - d / 0.12)
                encender(self._a_pantalla(p, rect, cam_x, cam_y), base * (0.38 + 0.62 * corredor))
        # Barras de cabecera: parpadeo lento al unísono.
        barra = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(t * 3.0))
        for (a, b) in (CABECERA_BAJA, CABECERA_ALTA):
            for i in range(4):
                f = i / 3
                p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
                encender(self._a_pantalla(p, rect, cam_x, cam_y), base * barra)
        # Baliza de la torre: destello corto cada 1.2 s.
        destello = max(0.0, 1.0 - ((t % 1.2) / 0.25))
        if destello > 0:
            v = int(255 * destello * (0.45 + 0.55 * base))
            bz = self.baliza.copy()
            bz.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
            surface.blit(bz, bz.get_rect(center=self._a_pantalla(TORRE, rect, cam_x, cam_y)), special_flags=aditivo)
            encender(self._a_pantalla(TORRE, rect, cam_x, cam_y), destello)
