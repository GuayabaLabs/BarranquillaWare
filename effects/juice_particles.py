import math
import random
from typing import List, Tuple
import pygame

class SparkParticle:
    def __init__(self, pos: Tuple[float, float]) -> None:
        self.x, self.y = pos
        angle = random.uniform(-math.pi * 0.9, -math.pi * 0.1)  # Hacia arriba
        speed = random.uniform(90.0, 190.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.gravity = 350.0
        self.life = 1.0
        self.decay = random.uniform(1.8, 2.6)
        self.size = random.uniform(5.0, 9.0)
        self.color = random.choice([
            (255, 230, 90),   # Amarillo destello
            (255, 180, 50),   # Naranja cálido
            (255, 255, 180),  # Blanco brillante
        ])

    def update(self, dt: float) -> bool:
        self.life -= self.decay * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        return self.life > 0.0

    def draw(self, surface: pygame.Surface) -> None:
        if self.life <= 0:
            return
        alpha = int(max(0, min(255, self.life * 255)))
        s = int(self.size * (0.4 + 0.6 * self.life))
        if s <= 1:
            return

        spark_surf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
        color_with_alpha = (*self.color, alpha)

        # Destello geométrico en forma de rombo / cruz de 4 puntas
        cx, cy = s, s
        points = [
            (cx, cy - s),
            (cx + s // 3, cy),
            (cx, cy + s),
            (cx - s // 3, cy)
        ]
        pygame.draw.polygon(spark_surf, color_with_alpha, points)
        points_h = [
            (cx - s, cy),
            (cx, cy + s // 3),
            (cx + s, cy),
            (cx, cy - s // 3)
        ]
        pygame.draw.polygon(spark_surf, color_with_alpha, points_h)

        surface.blit(spark_surf, spark_surf.get_rect(center=(int(self.x), int(self.y))))

class JuiceParticleManager:
    """Sistema liviano de micro-partículas para feedback táctil e impacto."""
    def __init__(self) -> None:
        self.particles: List[SparkParticle] = []

    def emit_sparks(self, pos: Tuple[float, float], count: int = 5) -> None:
        for _ in range(count):
            self.particles.append(SparkParticle(pos))

    def update(self, dt: float) -> None:
        self.particles = [p for p in self.particles if p.update(dt)]

    def render(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            p.draw(surface)


# Fuegos artificiales traídos del juego de la montaña rusa (coaster_game)

subidaFuego = 0.45             # segundos que tarda el cohete en subir
estallidoFuego = 1.5           # segundos que dura el estallido
cicloFuego = 3.0               # cada cuánto vuelve a salir un cohete
# cada fuego usa una sola familia de colores: oscuro, medio y claro
paletasFuego = {
    "rojo": ((200, 56, 52), (240, 96, 80), (255, 184, 168)),
    "dorado": ((214, 140, 36), (246, 192, 80), (255, 236, 170)),
    "azul": ((56, 104, 186), (104, 162, 232), (200, 226, 252)),
    "morado": ((132, 80, 180), (196, 122, 214), (240, 206, 246)),
    "turquesa": ((36, 140, 140), (80, 196, 186), (192, 242, 232)),
    "verde": ((56, 146, 76), (108, 200, 118), (204, 242, 200)),
    "rosa": ((196, 66, 128), (238, 128, 180), (255, 212, 232)),
}

almacenFuegos = {}


def interpolar(a, b, t):
    return a + (b - a) * t


def limitar(x, a, b):
    return max(a, min(b, x))


def mezclar(c1, c2, t):
    return tuple(int(interpolar(a, b, t)) for a, b in zip(c1, c2))


def temblorFijo(i, semilla=0.0):
    # número entre -1 y 1 que siempre es el mismo para el mismo i
    v = math.sin(i * 12.9898 + semilla * 78.233) * 43758.5453
    return (v - math.floor(v)) * 2 - 1


def brillo(color, r):
    # halo de luz suave, como pigmento claro que se corre en el papel mojado
    clave = ("brillo", color, r)
    if clave not in almacenFuegos:
        k = 3
        g = pygame.Surface((2 * r * k, 2 * r * k), pygame.SRCALPHA)
        g.fill((*color, 0))
        for i in range(r * k, 0, -2):
            pygame.draw.circle(g, (*color, int(200 * (1 - i / (r * k)) ** 1.6)), (r * k, r * k), i)
        almacenFuegos[clave] = pygame.transform.smoothscale(g, (2 * r, 2 * r))
    return almacenFuegos[clave]


def pegarBrillo(sup, centro, color, r, fuerza=1.0):
    luz = brillo(color, r)
    luz.set_alpha(int(255 * limitar(fuerza, 0, 1)))
    sup.blit(luz, (centro[0] - r, centro[1] - r))


def puntosFigura(forma):
    # dónde queda cada chispa al abrirse el fuego (entre -1 y 1) y de qué tipo es: 0 las grandes de afuera,
    # 1 las claras de adentro y 2 las bolitas pequeñas. Se calcula una vez por figura
    clave = ("figura", forma)
    if clave in almacenFuegos:
        return almacenFuegos[clave]
    pts = []
    if forma == "circulo":
        for anillo, n, r in ((0, 36, 1.0), (2, 28, 0.82), (1, 22, 0.64), (2, 16, 0.46), (1, 10, 0.28)):
            for k in range(n):
                a = (k + anillo * 0.5) * math.tau / n
                pts.append((math.cos(a) * r, math.sin(a) * r, anillo))
    elif forma == "corazon":
        for anillo, n, r in ((0, 48, 1.0), (2, 36, 0.8), (1, 26, 0.6), (2, 16, 0.4), (1, 8, 0.2)):
            for k in range(n):
                a = k * math.tau / n
                x = 16 * math.sin(a) ** 3
                y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
                pts.append((x / 17 * r, (y - 3) / 17 * r, anillo))
    almacenFuegos[clave] = pts
    return pts


def chispaLuz(color, r):
    # chispa encendida: halo de luz, gota de color y centro casi blanco (se guarda por color y tamaño)
    clave = ("chispa", color, r)
    if clave not in almacenFuegos:
        sup = pygame.Surface((6 * r, 6 * r), pygame.SRCALPHA)
        sup.blit(brillo(color, 3 * r), (0, 0))
        k = 4
        gota = pygame.Surface((2 * r * k, 2 * r * k), pygame.SRCALPHA)
        gota.fill((*color, 0))
        pygame.draw.circle(gota, color, (r * k, r * k), r * k)
        pygame.draw.circle(gota, mezclar(color, (255, 255, 255), 0.75), (r * k, r * k), r * k * 0.55)
        sup.blit(pygame.transform.smoothscale(gota, (2 * r, 2 * r)), (2 * r, 2 * r))
        almacenFuegos[clave] = sup
    return almacenFuegos[clave]


def pegarChispa(sup, punto, color, r, alfa=255):
    chispa = chispaLuz(color, r)
    chispa.set_alpha(int(limitar(alfa, 0, 255)))
    sup.blit(chispa, chispa.get_rect(center=(round(punto[0]), round(punto[1]))))


def dibujarFuego(sup, centro, figura, escala, t, paleta, desdeY, duracion=estallidoFuego, tamChispa=4,
                 detalle=False, chispitas=False):
    # fuego artificial: un cohete sube desde desdeY y estalla en chispas de luz que forman la figura.
    # t son los segundos desde que salió el cohete. Con detalle, las chispas de afuera dejan una estela
    # de bolitas y adentro titilan brillitos sueltos. Con chispitas, las de afuera vuelven a estallar
    cx, cy = centro
    oscuro, medio, claro = paleta
    if t < subidaFuego:
        f = t / subidaFuego
        y = interpolar(desdeY, cy, 1 - (1 - f) ** 2)
        pygame.draw.aaline(sup, medio, (cx, y + 40), (cx, y))
        pegarChispa(sup, (cx, y), claro, 5)
        return
    f = (t - subidaFuego) / duracion
    if f >= 1:
        return
    alcance = max(math.hypot(p[0], p[1]) for p in figura) * escala
    # resplandor grande al estallar que queda suave mientras duran las chispas
    pegarBrillo(sup, centro, medio, int(alcance * 1.3), 0.3 * (1 - f) + 0.7 * max(0.0, 1 - f / 0.25))
    abre = 1 - (1 - min(1.0, f / 0.35)) ** 3          # se abre rápido y se queda quieto para que se lea
    caida = 30 * max(0.0, (f - 0.55) / 0.45) ** 2     # al final las chispas bajan un poco
    alfa = 255 if f < 0.6 else 255 * (1 - (f - 0.6) / 0.4)
    if detalle and f > 0.25:
        # brillitos sueltos que se prenden y se apagan entre las chispas
        for k in range(26):
            a = (temblorFijo(k, cx) + 1) * math.pi
            d = (temblorFijo(k, cx + 1) + 1) / 2 * alcance * 0.85
            luz = alfa * max(0.0, math.sin(t * 18 + k * 2.3))
            if luz > 10:
                pegarChispa(sup, (cx + math.cos(a) * d, cy + math.sin(a) * d + caida), claro, 2, luz)
    for k, (dx, dy, anillo) in enumerate(figura):
        x, y = cx + dx * escala * abre, cy + dy * escala * abre + caida
        color = claro if anillo == 1 else medio
        if f < 0.35:
            cola = (cx + dx * escala * abre * 0.6, cy + dy * escala * abre * 0.6)
            pygame.draw.aaline(sup, oscuro, cola, (x, y))
        # al final las chispas titilan
        luz = alfa if f < 0.45 else alfa * (0.65 + 0.35 * math.sin(t * 28 + k * 1.9))
        r = max(2, tamChispa - anillo)
        if f > 0.6:
            r = max(2, round(r * (1 - 0.4 * (f - 0.6) / 0.4)))
        if detalle and anillo == 0 and f > 0.1:
            # estela de bolitas que quedan atrás de cada chispa de afuera y caen un poquito más
            for n, fuerza in ((1, 0.6), (2, 0.4), (3, 0.22)):
                atras = escala * abre * (1 - 0.08 * n)
                pegarChispa(sup, (cx + dx * atras, cy + dy * atras + caida * (1 + 0.3 * n)), medio, 2, luz * fuerza)
        pegarChispa(sup, (x, y), color, r, luz)
        if chispitas and anillo == 0 and k % 2 == 0 and f > 0.4:
            # una de cada dos chispas de afuera estalla otra vez en un circulito de bolitas mini
            g = (f - 0.4) / 0.6
            rr = 16 * (1 - (1 - g) ** 2)
            for n in range(6):
                b = n * math.tau / 6 + k
                pegarChispa(sup, (x + math.cos(b) * rr, y + math.sin(b) * rr + 6 * g * g), claro, 2, 240 * (1 - g))


class FuegosArtificiales:
    """Fuegos artificiales que estallan uno tras otro alrededor de un recuadro."""
    def __init__(self) -> None:
        self.fuegos: List[dict] = []
        self.encendidos: bool = False
        # Forma, tamaño y color con que sale cada uno de los seis fuegos
        self.disenos = [
            ("circulo", 150, "dorado"),
            ("circulo", 170, "rosa"),
            ("corazon", 140, "turquesa"),
            ("circulo", 160, "morado"),
            ("circulo", 150, "rojo"),
            ("corazon", 140, "verde"),
        ]

    def prepararBrillos(self) -> None:
        # El resplandor de cada fuego se pinta antes, así no se traba la primera vez que estalla
        for forma, escala, nombre in self.disenos:
            alcance = max(math.hypot(p[0], p[1]) for p in puntosFigura(forma)) * escala
            brillo(paletasFuego[nombre][1], int(alcance * 1.3))

    def lanzarAlrededor(self, caja: pygame.Rect) -> None:
        # Puntos alrededor del recuadro donde estalla cada fuego
        puntos = [
            (caja.left - 90, caja.top + 70),
            (caja.right + 110, caja.top + 90),
            (caja.left - 120, caja.bottom - 120),
            (caja.right + 120, caja.bottom - 120),
            (caja.left + caja.width // 4, caja.top - 90),
            (caja.right - caja.width // 3, caja.top - 90),
        ]
        self.fuegos = []
        for i, centro in enumerate(puntos):
            forma, escala, nombre = self.disenos[i]
            self.fuegos.append({
                "centro": centro,
                "forma": forma,
                "escala": escala,
                "paleta": nombre,
                "t": -i * 0.4,
                "desdeY": centro[1] + 320,
            })
        self.encendidos = True

    def apagar(self) -> None:
        # Los que ya salieron terminan de estallar, pero no sale ninguno nuevo
        self.encendidos = False

    def update(self, dt: float) -> None:
        for fuego in self.fuegos:
            fuego["t"] += dt
            if fuego["t"] >= cicloFuego and self.encendidos:
                fuego["t"] -= cicloFuego

    def render(self, surface: pygame.Surface) -> None:
        for fuego in self.fuegos:
            if fuego["t"] < 0.0:
                continue
            # Cada fuego conserva su color para no tener que pintar resplandores nuevos a cada rato
            paleta = paletasFuego[fuego["paleta"]]
            dibujarFuego(surface, fuego["centro"], puntosFigura(fuego["forma"]), fuego["escala"],
                         fuego["t"], paleta, fuego["desdeY"], tamChispa=5)
