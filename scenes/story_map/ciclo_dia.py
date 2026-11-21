"""Paso del tiempo en el mapa: reloj, luz del día y tinte de pantalla.

- El reloj avanza solo y rápido (un día completo en DURACION_DIA_SEG segundos reales).
- Cada nivel completado adelanta HORAS_POR_NIVEL horas, con una animación corta (no un salto brusco).
- La luz se calcula por franjas (alba, amanecer, día, hora dorada, atardecer, crepúsculo, noche) e
  interpola suave entre ellas. El oscurecimiento se hace MULTIPLICANDO los colores del mapa (como la luz
  real: lo blanco se vuelve azul de noche y naranja al atardecer), no tapándolo con un velo plano.
- `oscuridad` (0 de día … 1 de noche) decide cuándo se prenden los faroles y cuánto brilla el río.
- La lluvia es un estado aparte que puede caer a cualquier hora.
"""
from typing import Tuple

import pygame

DURACION_DIA_SEG = 360.0          # 24 h del mapa = 6 minutos reales
HORAS_POR_NIVEL = 3.0             # Al pasar un nivel el tiempo avanza 3 horas…
VEL_ADELANTO = 2.5                # …a 2.5 horas por segundo (≈ 1.2 s de "cámara rápida")
HORA_INICIAL = 7.5

# (hora, multiplicador RGB, luz cálida que se suma RGB, oscuridad 0..1)
FRANJAS = [
    (0.0,  (56, 70, 132),   (0, 0, 0),     1.00),
    (4.6,  (60, 73, 134),   (0, 0, 0),     1.00),
    (5.4,  (150, 118, 152), (22, 10, 14),  0.62),   # alba violeta
    (6.2,  (238, 192, 168), (26, 14, 4),   0.22),   # amanecer rosado
    (7.2,  (255, 246, 236), (6, 3, 0),     0.00),
    (8.0,  (255, 255, 255), (0, 0, 0),     0.00),   # día pleno
    (16.2, (255, 255, 255), (0, 0, 0),     0.00),
    (17.2, (255, 232, 198), (14, 8, 0),    0.00),   # hora dorada
    (18.2, (246, 178, 138), (22, 8, 0),    0.18),   # atardecer naranja
    (19.0, (168, 124, 156), (16, 4, 10),   0.52),   # crepúsculo morado
    (19.8, (96, 100, 160),  (2, 0, 8),     0.86),
    (20.6, (56, 70, 132),   (0, 0, 0),     1.00),   # noche
    (24.0, (56, 70, 132),   (0, 0, 0),     1.00),
]

# Hora representativa de cada clima (para elegir el clima a mano o restaurar partidas viejas)
HORA_DE_CLIMA = {"day": 11.0, "sunset": 18.2, "night": 22.0}
NOMBRE_FASE = {"day": "Día", "sunset": "Atardecer", "night": "Noche", "rain": "Lluvia"}


def _suave(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _mezclar(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


class CicloDia:
    def __init__(self, hora: float = HORA_INICIAL, lluvia: bool = False) -> None:
        self.hora = float(hora) % 24.0
        self.lluvia = bool(lluvia)
        self.adelanto_pendiente = 0.0   # horas por recorrer en "cámara rápida"
        self.corriendo = True

    # --- reloj -------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if self.adelanto_pendiente > 0.0:
            paso = min(self.adelanto_pendiente, VEL_ADELANTO * dt)
            self.adelanto_pendiente -= paso
            self.hora = (self.hora + paso) % 24.0
        elif self.corriendo:
            self.hora = (self.hora + dt * 24.0 / DURACION_DIA_SEG) % 24.0

    def adelantar(self, horas: float = HORAS_POR_NIVEL) -> None:
        """El tiempo avanza (p. ej. al completar un nivel), con animación corta."""
        self.adelanto_pendiente += max(0.0, horas)

    def hora_destino(self) -> float:
        """Hora a la que se llega al terminar el adelanto en curso (la que se guarda en la partida)."""
        return (self.hora + self.adelanto_pendiente) % 24.0

    @property
    def adelantando(self) -> bool:
        return self.adelanto_pendiente > 0.0

    def reloj(self) -> str:
        h = int(self.hora) % 24
        m = int((self.hora - int(self.hora)) * 60)
        return f"{h:02d}:{m:02d}"

    # --- luz -----------------------------------------------------------------------
    def _franja(self):
        h = self.hora % 24.0
        for (h0, m0, c0, o0), (h1, m1, c1, o1) in zip(FRANJAS, FRANJAS[1:]):
            if h0 <= h <= h1:
                t = 0.0 if h1 == h0 else _suave((h - h0) / (h1 - h0))
                return _mezclar(m0, m1, t), _mezclar(c0, c1, t), o0 + (o1 - o0) * t
        return FRANJAS[0][1], FRANJAS[0][2], FRANJAS[0][3]

    def multiplicador(self) -> Tuple[int, int, int]:
        m, _, _ = self._franja()
        if self.lluvia:
            m = _mezclar(m, (m[0] * 0.78, m[1] * 0.84, m[2] * 0.95), 1.0)  # Lluvia: más gris y fresca
        return m

    def calidez(self) -> Tuple[int, int, int]:
        return self._franja()[1]

    def oscuridad(self) -> float:
        o = self._franja()[2]
        return min(1.0, o + (0.12 if self.lluvia else 0.0))

    def luz(self) -> float:
        return 1.0 - self.oscuridad()

    def fase(self) -> str:
        """'day', 'sunset' (alba o atardecer) o 'night', según la hora."""
        h = self.hora % 24.0
        if 7.2 <= h < 17.2:
            return "day"
        if 17.2 <= h < 19.8 or 4.6 <= h < 7.2:
            return "sunset"
        return "night"

    def clima(self) -> str:
        return "rain" if self.lluvia else self.fase()

    def poner_clima(self, clima: str) -> None:
        """Compatibilidad con los 4 climas: 'rain' activa lluvia; los demás llevan el reloj a esa hora."""
        if clima == "rain":
            self.lluvia = True
            return
        self.lluvia = False
        if clima in HORA_DE_CLIMA and self.fase() != clima:
            self.hora = HORA_DE_CLIMA[clima]
        self.adelanto_pendiente = 0.0

    # --- dibujo --------------------------------------------------------------------
    # Se usa un "mapa de luz": una superficie del color de la hora a la que se le SUMAN las zonas
    # iluminadas (faroles, Cami, niveles). Luego el mundo se MULTIPLICA por ese mapa en un solo paso:
    # donde no llega luz queda el color de la noche/atardecer; bajo un farol se ven los colores reales.
    # (Pegar con mezcla es ~20 veces más rápido que rellenar la pantalla con mezcla.)
    def mapa_luz(self, tam: Tuple[int, int]) -> pygame.Surface:
        lm = getattr(self, "_lm", None)
        if lm is None or lm.get_size() != tam:
            lm = pygame.Surface(tam)
            if pygame.display.get_surface() is not None:
                lm = lm.convert()
            self._lm = lm
        lm.fill(self.multiplicador())
        return lm

    def aplicar(self, surface: pygame.Surface, lm: pygame.Surface) -> None:
        """Multiplica lo dibujado del mundo por el mapa de luz y suma la calidez del cielo."""
        if self.multiplicador() != (255, 255, 255) or getattr(self, "_hubo_luces", False):
            surface.blit(lm, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        c = self.calidez()
        if any(c):
            capa = getattr(self, "_calor", None)
            if capa is None or capa.get_size() != surface.get_size():
                capa = pygame.Surface(surface.get_size())
                if pygame.display.get_surface() is not None:
                    capa = capa.convert()
                self._calor = capa
            capa.fill(c)
            surface.blit(capa, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def aplicar_tinte(self, surface: pygame.Surface) -> None:
        """Atajo sin luces extra: solo el color de la hora."""
        self.aplicar(surface, self.mapa_luz(surface.get_size()))
