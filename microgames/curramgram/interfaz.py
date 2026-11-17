"""Interfaz acuarela de CurramGram Go!: botones, círculos de casos, avisos, barras y visor.

Todo se arma con las piezas acuarela de `assets/Interfaz/` (las mismas de los demás minijuegos) y
la fuente IndieFlower. Si existe un sprite propio en `assets/curramgram/` (ver ARTE_OPCIONAL), se usa
ese en su lugar; así se puede ir reemplazando el arte sin tocar código.
"""
from functools import lru_cache
from typing import Optional, Tuple

import pygame

from microgames.redes_comun import (
    barra_acuarela,
    cartel,
    circulo_acuarela,
    fuente,
    pieza_interfaz,
    sprite_opcional,
    tenir,
    texto_con_contorno,
)

TINTA = (92, 58, 48)
CREMA = (255, 247, 230)
VERDE = (88, 178, 104)
ROJO = (214, 82, 84)
GRIS = (118, 112, 124)  # Pendiente (teñido sobre el círculo crema)
AMARILLO = (242, 190, 64)
AZUL = (82, 150, 210)

# Sprites opcionales (fondo blanco puro; el código les quita el fondo). Nombre -> uso.
ARTE_OPCIONAL = {
    "visor_camara.png": "Marco del visor de la foto que sigue al puntero",
    "circulo_caso.png": "Círculo de los casos 1-6 (sin número; el número lo pone el código)",
    "boton_caminar.png": "Botón inferior A/D CAMINAR",
    "boton_saltar.png": "Botón inferior ESPACIO SALTAR",
    "boton_esconder.png": "Botón inferior S ESCONDER",
    "boton_avisar.png": "Botón inferior E AVISAR",
    "boton_foto.png": "Botón inferior FOTO",
    "boton_publicar.png": "Botón inferior P PUBLICAR",
    "fondo_pared_terminal.png": "Pared del terminal con ventanales (se repite horizontalmente)",
    "fondo_piso_terminal.png": "Piso del terminal (se repite horizontalmente)",
}

BOTONES = (
    ("caminar", "A/D", "Caminar"),
    ("saltar", "Esp", "Saltar"),
    ("esconder", "S", "Esconder"),
    ("avisar", "E", "Avisar"),
    ("foto", "F", "Foto"),
    ("publicar", "P", "Publicar"),
)


def _ajustar(img: pygame.Surface, ancho: int, alto: int) -> pygame.Surface:
    escala = min(ancho / img.get_width(), alto / img.get_height())
    return pygame.transform.smoothscale(img, (max(1, int(img.get_width() * escala)), max(1, int(img.get_height() * escala))))


@lru_cache(maxsize=32)
def tecla(etiqueta: str, diametro: int = 58, color: Tuple[int, int, int] = (150, 105, 205)) -> pygame.Surface:
    """Círculo acuarela con la tecla escrita (A/D, E, P…)."""
    base = circulo_acuarela(diametro, color).copy()
    f = fuente(int(diametro * (0.42 if len(etiqueta) > 1 else 0.6)))
    txt = f.render(etiqueta, True, CREMA)
    borde = f.render(etiqueta, True, TINTA)
    c = base.get_rect().center
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        base.blit(borde, borde.get_rect(center=(c[0] + dx, c[1] + dy)))
    base.blit(txt, txt.get_rect(center=c))
    return base


@lru_cache(maxsize=16)
def boton(id_boton: str, ancho: int = 270, alto: int = 88) -> pygame.Surface:
    """Sprite individual de un botón de la barra inferior (crema acuarela + tecla + texto)."""
    propio = sprite_opcional(f"boton_{id_boton}.png", "curramgram")
    _, letra, etiqueta = next(b for b in BOTONES if b[0] == id_boton)
    if propio is not None:
        # Píldora acuarela con icono (arte propio) + tecla en burbuja + texto debajo.
        pill = _ajustar(propio, ancho - 20, alto)
        alto_txt = int(alto * 0.42)
        surf = pygame.Surface((ancho, pill.get_height() + alto_txt), pygame.SRCALPHA)
        surf.blit(pill, pill.get_rect(midtop=(ancho // 2, 0)))
        icono = tecla(letra, int(pill.get_height() * 0.52))
        surf.blit(icono, icono.get_rect(center=(int(ancho * 0.16), pill.get_height() // 2)))
        f = fuente(int(alto * 0.34))
        txt, borde = f.render(etiqueta, True, CREMA), f.render(etiqueta, True, TINTA)
        c = (ancho // 2, pill.get_height() + alto_txt // 2 - 2)
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                if dx or dy:
                    surf.blit(borde, borde.get_rect(center=(c[0] + dx, c[1] + dy)))
        surf.blit(txt, txt.get_rect(center=c))
        return surf
    surf = pieza_interfaz("bannerUbicacion", ancho, alto).copy()
    icono = tecla(letra, int(alto * 0.7))
    surf.blit(icono, icono.get_rect(midleft=(int(alto * 0.22), alto // 2)))
    txt = fuente(int(alto * 0.36)).render(etiqueta, True, TINTA)
    zona_x = int(alto * 0.22) + icono.get_width()
    surf.blit(txt, txt.get_rect(center=((zona_x + ancho - int(alto * 0.2)) // 2, alto // 2)))
    return surf


@lru_cache(maxsize=32)
def circulo_caso(numero: str, color: Tuple[int, int, int], diametro: int = 52) -> pygame.Surface:
    propio = sprite_opcional("circulo_caso.png", "curramgram")
    if propio is not None:
        base = tenir(pygame.transform.smoothscale(propio, (diametro, diametro)), color)
    else:
        base = circulo_acuarela(diametro, color).copy()
    if numero:
        f = fuente(int(diametro * 0.55))
        txt = f.render(numero, True, CREMA)
        borde = f.render(numero, True, TINTA)
        c = base.get_rect().center
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            base.blit(borde, borde.get_rect(center=(c[0] + dx, c[1] + dy)))
        base.blit(txt, txt.get_rect(center=c))
    return base


def aviso(s: pygame.Surface, mensaje: str, centro, ancho: int = 760, alto: int = 76,
          color: Optional[Tuple[int, int, int]] = None, tam: int = 30) -> pygame.Rect:
    return cartel(s, mensaje, centro, ancho, alto, color, tam)


def barra(s: pygame.Surface, rect: pygame.Rect, valor: float, color=None) -> None:
    barra_acuarela(s, rect, valor, color)


def estrella(s: pygame.Surface, centro, r: int = 15, color=(255, 214, 92)) -> None:
    import math
    cx, cy = centro
    puntos = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        puntos.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    pygame.draw.polygon(s, color, puntos)
    pygame.draw.polygon(s, TINTA, puntos, 3)


@lru_cache(maxsize=4)
def _visor(tam: int) -> pygame.Surface:
    propio = sprite_opcional("visor_camara.png", "curramgram", ((0.5, 0.5),))  # el centro también es fondo
    if propio is not None:
        return _ajustar(propio, tam, tam)
    # Respaldo: esquinas de visor de cámara con trazo grueso de tinta + crema.
    surf = pygame.Surface((tam, tam), pygame.SRCALPHA)
    largo, g = tam // 4, 7
    for color, ancho in ((TINTA, g + 6), (CREMA, g)):
        for (x, y, dx, dy) in ((6, 6, 1, 1), (tam - 7, 6, -1, 1), (6, tam - 7, 1, -1), (tam - 7, tam - 7, -1, -1)):
            pygame.draw.line(surf, color, (x, y), (x + dx * largo, y), ancho)
            pygame.draw.line(surf, color, (x, y), (x, y + dy * largo), ancho)
    c = tam // 2
    pygame.draw.circle(surf, TINTA, (c, c), 11, 5)
    pygame.draw.circle(surf, CREMA, (c, c), 10, 3)
    return surf


def visor(s: pygame.Surface, centro, tam: int = 132) -> None:
    img = _visor(tam)
    s.blit(img, img.get_rect(center=centro))


@lru_cache(maxsize=4)
def capa_fondo(nombre: str, alto: int) -> Optional[pygame.Surface]:
    """Capa de fondo opcional (pared/piso) escalada al alto pedido, lista para repetirse."""
    # Los fondos se cargan tal cual (su blanco es cielo/luz, no fondo a quitar).
    from microgames.redes_comun import RAIZ, cargar_imagen
    if not (RAIZ / "assets" / "curramgram" / nombre).is_file():
        return None
    img = cargar_imagen(nombre, carpeta="assets/curramgram", alpha=False)
    ancho = max(1, int(img.get_width() * alto / img.get_height()))
    img = pygame.transform.smoothscale(img, (ancho, alto))
    # Copia + espejo: al repetirse, cada borde empalma consigo mismo y no se ve la costura.
    doble = pygame.Surface((ancho * 2, alto))
    doble.blit(img, (0, 0))
    doble.blit(pygame.transform.flip(img, True, False), (ancho, 0))
    return doble


def repetir(s: pygame.Surface, capa: pygame.Surface, y: int, desplazamiento: float) -> None:
    w = capa.get_width()
    x = -int(desplazamiento) % w - w
    while x < s.get_width():
        s.blit(capa, (x, y))
        x += w
