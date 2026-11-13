"""Utilidades aisladas para los juegos extra de BarranquillaWare."""
from pathlib import Path
import pygame

ANCHO, ALTO, FPS = 1920, 1080, 60
RAIZ = Path(__file__).resolve().parent.parent


def fuente(tamano=28, negrita=False):
    """Carga fuente del proyecto y cae a una fuente Pygame segura."""
    archivo = RAIZ / "assets" / "fonts" / ("ArialBold.ttf" if negrita else "Impact.ttf")
    try:
        return pygame.font.Font(str(archivo), tamano)
    except (OSError, pygame.error):
        return pygame.font.Font(None, tamano)


def cargar_imagen(nombre, tamano=None, alpha=True):
    """Carga un recurso existente sin modificarlo; devuelve None si falta."""
    try:
        imagen = pygame.image.load(str(RAIZ / "assets" / nombre))
        imagen = imagen.convert_alpha() if alpha else imagen.convert()
        if tamano:
            imagen = pygame.transform.smoothscale(imagen, tamano)
        return imagen
    except (OSError, pygame.error):
        return None


def texto(superficie, cadena, pos, tamano=28, color=(45, 42, 55), centro=False, negrita=False):
    imagen = fuente(tamano, negrita).render(str(cadena), True, color)
    rect = imagen.get_rect(center=pos) if centro else imagen.get_rect(topleft=pos)
    superficie.blit(imagen, rect)
    return rect


def panel(superficie, rect, color=(255, 247, 234), borde=(94, 66, 73), radio=18, ancho=3):
    pygame.draw.rect(superficie, color, rect, border_radius=radio)
    pygame.draw.rect(superficie, borde, rect, ancho, border_radius=radio)


def boton(superficie, rect, etiqueta, seleccionado=False, cursor=None):
    """Dibuja un botón con respuesta visual y reporta si el cursor lo cubre."""
    cursor = cursor if cursor is not None else pygame.mouse.get_pos()
    hover = rect.collidepoint(cursor)
    panel(superficie, rect, (228, 222, 250) if seleccionado or hover else (255, 255, 255), (105, 79, 135), 14, 2)
    texto(superficie, etiqueta, rect.center, 30, centro=True)
    return hover


def leer_entrada(eventos):
    """Traduce eventos de teclado y ratón en acciones simples."""
    acciones = {"pausa": False, "reiniciar": False, "salir": False, "click": None, "teclas": set(), "soltadas": set()}
    for evento in eventos:
        if evento.type == pygame.KEYDOWN:
            acciones["teclas"].add(evento.key)
            if evento.key == pygame.K_ESCAPE: acciones["pausa"] = True
            if evento.key == pygame.K_r: acciones["reiniciar"] = True
        elif evento.type == pygame.KEYUP:
            acciones["soltadas"].add(evento.key)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            acciones["click"] = evento.pos
        elif evento.type == pygame.QUIT:
            acciones["salir"] = True
    acciones["held"] = pygame.key.get_pressed()
    acciones["mouse"] = pygame.mouse.get_pos()
    return acciones


def menu_pausa(pantalla, opciones, seleccionado=0):
    """Dibuja menú de pausa en zona central y retorna rectángulos de opciones."""
    velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    velo.fill((22, 19, 36, 155)); pantalla.blit(velo, (0, 0))
    marco = pygame.Rect(570, 300, 780, 480); panel(pantalla, marco)
    texto(pantalla, "PAUSA", (960, 375), 56, centro=True)
    rects = []
    for i, opcion in enumerate(opciones):
        r = pygame.Rect(720, 455 + i * 90, 480, 68)
        boton(pantalla, r, opcion, seleccionado=(i == seleccionado))
        rects.append(r)
    return rects


def pantalla_final(pantalla, titulo, lineas, reinicio="R para reiniciar"):
    velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA); velo.fill((28, 24, 42, 190)); pantalla.blit(velo, (0, 0))
    panel(pantalla, pygame.Rect(350, 210, 1220, 660), (255, 247, 234), (99, 65, 75), 26, 5)
    texto(pantalla, titulo, (960, 300), 52, centro=True)
    for i, linea in enumerate(lineas): texto(pantalla, linea, (960, 405 + i * 66), 30, centro=True)
    texto(pantalla, reinicio, (960, 790), 28, (95, 75, 110), centro=True)


def sonido(nombre):
    """Carga sonido si el mixer y el recurso están disponibles."""
    try:
        return pygame.mixer.Sound(str(RAIZ / "assets" / nombre))
    except (pygame.error, OSError):
        return None
