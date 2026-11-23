"""Río y ciénaga animados del mapa (sin deformar nada fuera del agua).

1. Al cargar se calcula una máscara del agua: píxeles azules del mapa, rellenando los trazos blancos de
   ola que están dentro, y quedándose solo con las zonas conectadas grandes (el río Magdalena y la
   ciénaga). Así los techos morados o azules de los edificios nunca se animan.
2. Sobre el agua viajan trazos de ola acuarela (como los "~" pintados del mapa) que nacen, avanzan con la
   corriente ondulando y se desvanecen, más destellos de sol que titilan. Cada trazo solo nace donde
   TODO su recorrido es agua (se comprueba con la máscara), por eso nunca pisa la orilla ni el resto
   del mapa: el mapa no se deforma, solo se le pinta encima dentro del agua.
3. La intensidad depende de la luz del día (de noche se atenúa y los destellos son de luna).
4. Es barato: unos 100 trazos pequeños visibles por frame (< 1 ms).
"""
import math
import random
from typing import Optional, Tuple

import numpy as np
import pygame

FLUJO = (0.95, 0.31)         # Dirección de la corriente (el río baja hacia la derecha del mapa)
AREA_MIN_BLOQUES = 3000      # Zonas de agua más pequeñas que esto (en bloques de 4x4) no se animan
DENSIDAD_OLAS = 1 / 16000    # Olas animadas por px² de agua
DENSIDAD_BRILLOS = 1 / 16000


def _dilatar(m: np.ndarray, r: int) -> np.ndarray:
    out = m.copy()
    for _ in range(r):
        prev = out.copy()
        out[1:, :] |= prev[:-1, :]; out[:-1, :] |= prev[1:, :]
        out[:, 1:] |= prev[:, :-1]; out[:, :-1] |= prev[:, 1:]
    return out


def _erosionar(m: np.ndarray, r: int) -> np.ndarray:
    return ~_dilatar(~m, r)


def calcular_mascara_agua(mundo: pygame.Surface) -> Tuple[Optional[np.ndarray], Optional[pygame.Rect]]:
    """Máscara booleana (forma (ancho, alto)) del agua grande del mapa y su rectángulo envolvente."""
    rgb = pygame.surfarray.array3d(mundo).astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    azul = (b > r + 45) & (b > g - 10) & (b > 120)
    w, h = azul.shape
    k = 4
    bloques = azul[: w // k * k, : h // k * k].reshape(w // k, k, h // k, k).mean(axis=(1, 3)) > 0.35

    sup = pygame.Surface(bloques.shape, pygame.SRCALPHA)
    pygame.surfarray.pixels_alpha(sup)[:] = (bloques * 255).astype(np.uint8)
    mascara = pygame.mask.from_surface(sup, 127)
    grandes = [c for c in mascara.connected_components() if c.count() >= AREA_MIN_BLOQUES]
    if not grandes:
        return None, None
    zona = pygame.Mask(bloques.shape)
    for c in grandes:
        zona.draw(c, (0, 0))
    sup_zona = zona.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    zona_arr = pygame.surfarray.array_alpha(sup_zona) > 0
    # Rellenar los huecos que dejan las olas blancas pintadas: cierre morfológico (dilatar y erosionar
    # 5 bloques = 20 px). A resolución completa solo cuentan píxeles azules o de espuma, así que la orilla
    # y lo que haya sobre el agua siguen fuera.
    zona_arr = _erosionar(_dilatar(zona_arr, 5), 5) | zona_arr

    # A resolución completa: dentro de la zona, solo píxeles de agua (azul o espuma blanca pintada).
    zona_full = np.zeros((w, h), bool)
    zona_full[: w // k * k, : h // k * k] = np.repeat(np.repeat(zona_arr, k, axis=0), k, axis=1)
    espuma = (rgb.min(axis=2) >= 200) & (b >= r - 5)
    agua = zona_full & (azul | espuma)
    xs = np.where(agua.any(axis=1))[0]
    ys = np.where(agua.any(axis=0))[0]
    caja = pygame.Rect(int(xs[0]), int(ys[0]), int(xs[-1] - xs[0] + 1), int(ys[-1] - ys[0] + 1))
    return agua, caja


def recortar_olas_pintadas(mundo: pygame.Surface, agua: np.ndarray, caja: pygame.Rect, maximo: int = 14):
    """Recorta del mapa las olas blancas pintadas dentro del agua para usarlas como trazos animados.

    Así las olas que se mueven tienen exactamente el mismo estilo acuarela que las del dibujo.
    Solo se mira la zona del agua (`caja`), no el mapa entero.
    """
    rgb = pygame.surfarray.array3d(mundo.subsurface(caja)).astype(np.int16)
    agua = agua[caja.left:caja.right, caja.top:caja.bottom]
    espuma = agua & (rgb.min(axis=2) >= 205)
    sup = pygame.Surface(espuma.shape, pygame.SRCALPHA)
    pygame.surfarray.pixels_alpha(sup)[:] = (espuma * 255).astype(np.uint8)
    comps = pygame.mask.from_surface(sup, 127).connected_components(minimum=120)
    candidatas = []
    for c in comps:
        caja = c.get_bounding_rects()[0]
        # Olas alargadas como "~": anchas y bajitas
        if 50 <= caja.width <= 260 and 8 <= caja.height <= 60 and caja.width >= caja.height * 2.4:
            candidatas.append((c.count(), caja))
    candidatas.sort(key=lambda x: -x[0])
    sprites = []
    for _, caja in candidatas[:maximo]:
        pad = 4
        zona = caja.inflate(pad * 2, pad * 2).clip(pygame.Rect(0, 0, *espuma.shape))
        alfa = espuma[zona.left:zona.right, zona.top:zona.bottom].astype(np.float32)
        # Borde suave: promedio con vecinos (como el borde de la pincelada)
        suave = alfa.copy()
        suave[1:, :] += alfa[:-1, :]; suave[:-1, :] += alfa[1:, :]
        suave[:, 1:] += alfa[:, :-1]; suave[:, :-1] += alfa[:, 1:]
        suave = np.clip(suave / 3.0, 0, 1)
        spr = pygame.Surface(zona.size, pygame.SRCALPHA)
        spr.fill((255, 255, 255, 0))
        pygame.surfarray.pixels3d(spr)[:] = np.clip(rgb[zona.left:zona.right, zona.top:zona.bottom] + 12, 0, 255).astype(np.uint8)
        pygame.surfarray.pixels_alpha(spr)[:] = (suave * 255).astype(np.uint8)
        sprites.append(spr)
    return sprites


def _sprite_ola(largo: int, rnd: random.Random) -> pygame.Surface:
    """Un trazo "~" acuarela: se pinta al doble y se reduce para que quede suave."""
    k = 2
    w, h = largo * k, int(largo * 0.42) * k
    sup = pygame.Surface((w + 8 * k, h + 8 * k), pygame.SRCALPHA)
    grosor = 3 * k
    mitad = pygame.Rect(4 * k, 4 * k, w // 2, h)
    pygame.draw.arc(sup, (255, 255, 255, 235), mitad, math.radians(15), math.radians(170), grosor)
    seg = mitad.move(w // 2 - 2 * k, int(h * 0.32))
    pygame.draw.arc(sup, (255, 255, 255, 200), seg, math.radians(195), math.radians(345), grosor - k)
    if rnd.random() < 0.5:
        sup = pygame.transform.flip(sup, True, False)
    return pygame.transform.smoothscale(sup, (sup.get_width() // k, sup.get_height() // k))


def _sprite_brillo(largo: int) -> pygame.Surface:
    sup = pygame.Surface((largo * 2 + 8, 10), pygame.SRCALPHA)
    pygame.draw.line(sup, (255, 255, 235, 230), (4, 5), (largo * 2 + 4, 5), 4)
    pygame.draw.circle(sup, (255, 255, 255, 255), (largo + 4, 5), 3)
    return pygame.transform.smoothscale(sup, (largo + 4, 5))


class RioAnimado:
    def __init__(self, mundo: pygame.Surface, semilla: int = 5, en_segundo_plano: bool = False) -> None:
        """Con `en_segundo_plano` la máscara y las olas se preparan en un hilo (el mapa no espera ~1 s);
        mientras tanto el río no se anima y luego aparece solo."""
        self.activo = False
        self.olas, self.brillos = [], []
        self.caja = None
        self._semilla = semilla
        if en_segundo_plano:
            import threading
            copia = mundo.copy()
            self._hilo = threading.Thread(target=self._preparar, args=(copia,), name="rio-mapa", daemon=True)
            self._hilo.start()
        else:
            self._preparar(mundo)

    def _preparar(self, mundo: pygame.Surface) -> None:
        semilla = self._semilla
        agua, caja = calcular_mascara_agua(mundo)
        if agua is None:
            return
        self.caja = caja
        self.agua = agua
        self.rnd = random.Random(semilla)
        # Olas animadas = copias de las olas pintadas del propio mapa (mismo estilo); respaldo por código.
        pintadas = recortar_olas_pintadas(mundo, agua, self.caja)
        self.sprites_ola = pintadas if len(pintadas) >= 4 else [_sprite_ola(l, self.rnd) for l in (34, 42, 50, 58, 66)]
        self.sprites_brillo = [_sprite_brillo(l) for l in (8, 12, 16, 22)]
        xs, ys = np.nonzero(agua)
        self._puntos = (xs, ys)
        area = len(xs)
        olas = [self._nueva_ola(inicial=True) for _ in range(int(area * DENSIDAD_OLAS))]
        brillos = [self._nuevo_brillo(inicial=True) for _ in range(int(area * DENSIDAD_BRILLOS))]
        self.olas, self.brillos = olas, brillos
        self.activo = True  # Se activa al final: el render nunca ve un estado a medias

    # --- utilidades de máscara -------------------------------------------------
    def es_agua(self, x: float, y: float) -> bool:
        xi, yi = int(x), int(y)
        return 0 <= xi < self.agua.shape[0] and 0 <= yi < self.agua.shape[1] and bool(self.agua[xi, yi])

    def _rect_en_agua(self, rect: pygame.Rect) -> bool:
        """True solo si TODO el rectángulo es agua (nada de orilla, palmeras ni edificios dentro)."""
        if rect.left < 0 or rect.top < 0 or rect.right > self.agua.shape[0] or rect.bottom > self.agua.shape[1]:
            return False
        return bool(self.agua[rect.left:rect.right, rect.top:rect.bottom].all())

    def _punto_al_azar(self) -> Tuple[int, int]:
        xs, ys = self._puntos
        i = self.rnd.randrange(len(xs))
        return int(xs[i]), int(ys[i])

    # --- partículas --------------------------------------------------------------
    def _nueva_ola(self, inicial: bool = False) -> dict:
        for _ in range(40):
            x, y = self._punto_al_azar()
            spr = self.rnd.randrange(len(self.sprites_ola))
            vida = self.rnd.uniform(3.5, 6.5)
            vel = self.rnd.uniform(16.0, 30.0)
            w, h = self.sprites_ola[spr].get_size()
            # Todo el recorrido (inicio, cuartos y final) debe caer dentro del agua, con margen para el vaivén.
            recorrido = [(x + FLUJO[0] * vel * vida * f, y + FLUJO[1] * vel * vida * f) for f in (0.0, 0.25, 0.5, 0.75, 1.0)]
            if all(self._rect_en_agua(pygame.Rect(int(px - w / 2 - 6), int(py - h / 2 - 6), w + 12, h + 12))
                   for px, py in recorrido):
                return {"x": float(x), "y": float(y), "spr": spr, "vida": vida, "vel": vel,
                        "t": self.rnd.uniform(0, vida) if inicial else 0.0, "fase": self.rnd.uniform(0, math.tau)}
        # Sin lugar válido en este intento: queda invisible y se reintenta pronto.
        return {"x": 0.0, "y": 0.0, "spr": 0, "vida": 0.5, "vel": 0.0, "t": 0.5, "fase": 0.0, "oculta": True}

    def _nuevo_brillo(self, inicial: bool = False) -> dict:
        for _ in range(30):
            x, y = self._punto_al_azar()
            spr = self.rnd.randrange(len(self.sprites_brillo))
            w, h = self.sprites_brillo[spr].get_size()
            if self._rect_en_agua(pygame.Rect(x - w // 2 - 4, y - h // 2 - 4, w + 8, h + 8)):
                vida = self.rnd.uniform(1.0, 2.4)
                return {"x": float(x), "y": float(y), "spr": spr, "vida": vida,
                        "t": self.rnd.uniform(0, vida) if inicial else 0.0}
        return {"x": 0.0, "y": 0.0, "spr": 0, "vida": 0.3, "t": 0.3, "oculta": True}

    def update(self, dt: float) -> None:
        if not self.activo:
            return
        for i, o in enumerate(self.olas):
            o["t"] += dt
            if o["t"] >= o["vida"]:
                self.olas[i] = self._nueva_ola()
        for i, b in enumerate(self.brillos):
            b["t"] += dt
            if b["t"] >= b["vida"]:
                self.brillos[i] = self._nuevo_brillo()

    def render(self, surface: pygame.Surface, cam_x: int, cam_y: int, t: float, luz: float = 1.0) -> None:
        """Dibuja olas y destellos visibles. `luz` 1 = mediodía, ~0.25 = noche cerrada."""
        if not self.activo:
            return
        sw, sh = surface.get_size()
        if not pygame.Rect(cam_x - 100, cam_y - 100, sw + 200, sh + 200).colliderect(self.caja):
            return
        luz = max(0.0, min(1.0, luz))
        fuerza_ola = 0.45 + 0.55 * luz
        for o in self.olas:
            if o.get("oculta"):
                continue
            avance = o["vel"] * o["t"]
            vaiven = math.sin(t * 1.6 + o["fase"]) * 3.0
            x = o["x"] + FLUJO[0] * avance - cam_x
            y = o["y"] + FLUJO[1] * avance + vaiven - cam_y
            if -80 < x < sw + 80 and -40 < y < sh + 40:
                f = o["t"] / o["vida"]
                aparece = min(1.0, f / 0.25) * min(1.0, (1.0 - f) / 0.3)   # nace y se desvanece suave
                spr = self.sprites_ola[o["spr"]]
                spr.set_alpha(int(215 * aparece * fuerza_ola))
                surface.blit(spr, spr.get_rect(center=(int(x), int(y))))
        color_luz = 0.3 + 0.7 * luz
        for b in self.brillos:
            if b.get("oculta"):
                continue
            x, y = b["x"] - cam_x, b["y"] - cam_y
            if -40 < x < sw + 40 and -20 < y < sh + 20:
                f = b["t"] / b["vida"]
                destello = math.sin(f * math.pi) ** 2
                spr = self.sprites_brillo[b["spr"]]
                spr.set_alpha(int(210 * destello * color_luz))
                surface.blit(spr, spr.get_rect(center=(int(x), int(y))))
