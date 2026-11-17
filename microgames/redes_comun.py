"""Utilidades compartidas de los minijuegos de redes sociales (CurramGram Go! y Emoji Catch).

- Rutas y validación de sprites en `assets/curramgram/` y `assets/emoji_catch/`.
- Texto con la fuente del juego (IndieFlower, la misma del coaster y los carteles).
- Piezas acuarela de `assets/Interfaz/` (banner, barra, píldoras) reutilizadas por código.
- Audio vía AudioManager y teclas sostenidas que combinan teclado + mando.
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Optional

import numpy as np
import pygame

from core import input_state
from core.asset_manager import AssetManager, rutaFuenteCuento
from core.audio_manager import AudioManager

ANCHO, ALTO, FPS = 1920, 1080, 60
RAIZ = Path(__file__).resolve().parent.parent
CARPETAS = {"curramgram": "assets/curramgram", "emoji": "assets/emoji_catch"}
TOLERANTE = os.environ.get("JUEGOS_EXTRA_TOLERANTE") == "1"

_EMOJI_SPRITES = (
    "titulo", "tiempo", "tarjeta_mano_izq", "tarjeta_mano_der", "barra_negatividad",
    "barra_positividad", "mano_morada", "mano_azul_der", "emoji_enojado_naranja",
    "emoji_enojado_rojo", "emoji_triste", "emoji_vomito_1", "emoji_vomito_2",
    "emoji_corazon_roto", "emoji_pulgar_abajo", "emoji_sonriente", "emoji_cara_azul",
    "emoji_corazon", "emoji_pulgar_arriba", "emoji_bolsa_dinero", "emoji_estrellas", "emoji_angel",
    "balanza", "mano_morada_puno", "mano_azul_puno",
)
_CURRAM_SPRITES = (
    "titulo", "barranquilla", "aeropuerto", "gates_1_10", "hud_pildora", "zona_1",
    "zona_2", "zona_3", "puerta_embarque", "icono_camara", "reloj_grande", "policia",
    "bailarina_comparsa", "trabajador_carrito", "grupo_vendedor_letrero", "cami",
    "tamborero", "hombre_gorra", "turista_pasaporte", "pasajero_sentado_1",
    "joven_llorando", "senor_sentado", "senora_cava", "globito_clickbait",
    "dialogo_toma_foto", "dialogo_salto", "dialogo_confirma", "dialogo_privacidad",
    "dialogo_respeto", "dialogo_pelea", "dialogo_hielo", "cartel_policia",
    "cartel_comparsa", "alerta", "tecla_s_sigilo", "tecla_flash", "tecla_a", "tecla_d",
    "tecla_s", "tecla_space", "tecla_e", "tecla_camara", "tecla_p", "gate_7",
    "letrero_butifarras", "cami_idle", "cami_walk_1", "cami_walk_2", "cami_walk_3", "cami_walk_4", "cami_walk_5",
    "cami_agachar_1", "cami_agachar_2", "cami_cuclillas", "cami_arrodillada", "cami_foto_agachada", "cami_regreso",
)
ASSETS_REQUERIDOS = {
    "emoji_catch": ("assets/fondo_concentracion_microjuego.png",)
    + tuple(f"assets/emoji_catch/{n}.png" for n in _EMOJI_SPRITES),
    "curramgram_go": ("assets/curramgram/anclajes.json", "assets/curramgram/animaciones.json",
                      "assets/curramgram/anclajes_cami.json")
    + tuple(f"assets/curramgram/{n}.png" for n in _CURRAM_SPRITES),
}
_RECURSOS_VALIDOS = set()


class ErrorRecursos(RuntimeError):
    """Recurso requerido ausente o ilegible; incluye la ruta probada."""


def revisar_recursos(juego: str):
    """Devuelve la lista de errores; lanza ErrorRecursos si falta algo (salvo modo tolerante)."""
    if juego in _RECURSOS_VALIDOS:
        return []
    errores = [f"FALTA {rel} -> {RAIZ / rel}" for rel in ASSETS_REQUERIDOS[juego] if not (RAIZ / rel).is_file()]
    if errores and not TOLERANTE:
        raise ErrorRecursos("Recursos requeridos no disponibles:\n  - " + "\n  - ".join(errores))
    if errores:
        print("WARNING recursos ausentes:\n  - " + "\n  - ".join(errores))
    else:
        _RECURSOS_VALIDOS.add(juego)
    return errores


def limpiar_borde_blanco(imagen: pygame.Surface, umbral: int = 200) -> pygame.Surface:
    """Quita el halo blanco que deja un recorte mal hecho alrededor de la silueta.

    Los píxeles casi blancos del borde (los que tocan transparencia) se vuelven transparentes en
    varias pasadas, y el resto del borde se desatura del blanco para que no brille sobre fondos oscuros.
    """
    img = imagen.convert_alpha() if pygame.display.get_surface() else imagen.copy()
    rgb = pygame.surfarray.array3d(img).astype(np.int16)
    alpha = pygame.surfarray.array_alpha(img).astype(np.int16)
    def _vecinos(m):
        v = np.zeros_like(m)
        v[1:, :] |= m[:-1, :]
        v[:-1, :] |= m[1:, :]
        v[:, 1:] |= m[:, :-1]
        v[:, :-1] |= m[:, 1:]
        return v

    for _ in range(4):
        visible = alpha > 20
        # Transparencia conectada al exterior (los huecos internos, como la boca, no cuentan).
        vacio = ~visible
        exterior = np.zeros_like(vacio)
        exterior[0, :] = vacio[0, :]
        exterior[-1, :] = vacio[-1, :]
        exterior[:, 0] = vacio[:, 0]
        exterior[:, -1] = vacio[:, -1]
        while True:
            crecido = (exterior | _vecinos(exterior)) & vacio
            if (crecido == exterior).all():
                break
            exterior = crecido
        vecino_vacio = _vecinos(exterior)
        borde = visible & vecino_vacio
        blanco = (rgb.min(axis=2) >= umbral) & ((rgb.max(axis=2) - rgb.min(axis=2)) <= 40)
        quitar = borde & (blanco | (alpha < 200))
        if not quitar.any():
            break
        alpha[quitar] = 0
    out = img.copy()
    pygame.surfarray.pixels_alpha(out)[:] = alpha.clip(0, 255).astype(np.uint8)
    return out


@lru_cache(maxsize=256)
def _cargar_imagen_cache(ruta: str, alpha: bool, limpiar: bool):
    imagen = pygame.image.load(ruta)
    if pygame.display.get_surface():
        imagen = imagen.convert_alpha() if alpha else imagen.convert()
    if alpha and limpiar:
        imagen = limpiar_borde_blanco(imagen)
    return imagen


def cargar_imagen(nombre: str, tamano=None, alpha: bool = True, carpeta: str = "assets", limpiar: bool = False):
    """Carga el archivo exacto; falla con ErrorRecursos salvo modo tolerante."""
    ruta = RAIZ / carpeta / nombre
    try:
        if not ruta.is_file():
            raise FileNotFoundError(f"No existe el recurso: {nombre}; ruta probada: {ruta}")
        imagen = _cargar_imagen_cache(str(ruta), bool(alpha), bool(limpiar))
    except (OSError, pygame.error) as exc:
        if TOLERANTE:
            print(f"WARNING recurso de imagen omitido: {ruta}; {exc}")
            return None
        raise ErrorRecursos(f"No se pudo cargar {nombre}; ruta probada: {ruta}: {exc}") from exc
    return pygame.transform.smoothscale(imagen, tamano) if tamano else imagen


def cargar_sprite(nombre: str, grupo: str, limpiar: bool = True):
    """Carga un recorte del juego quitando el halo blanco del borde."""
    return cargar_imagen(nombre, carpeta=CARPETAS[grupo], limpiar=limpiar)


def sprite_opcional(nombre: str, grupo: str, semillas: tuple = ()) -> Optional[pygame.Surface]:
    """Sprite nuevo opcional (fondo blanco puro): si existe se le quita el fondo; si no, None.

    Permite ir agregando arte acuarela sin romper el juego: mientras falte, se usa el respaldo por código.
    """
    ruta = RAIZ / CARPETAS[grupo] / nombre
    if not ruta.is_file():
        return None
    try:
        rel = os.path.relpath(ruta, RAIZ / "assets")
        ancho = min(1200, pygame.image.load(str(ruta)).get_width())
        return AssetManager.get_instance().cargarSinFondo(rel, ancho, semillas)
    except (pygame.error, OSError):
        return None


def fuente(tamano: int = 28, negrita: bool = False) -> pygame.font.Font:
    """IndieFlower (fuente de los carteles y el coaster) para todo el texto de estos juegos."""
    tamano = int(round(tamano * 1.12))  # IndieFlower se ve más pequeña que Impact al mismo tamaño
    return _fuente_cache(tamano)


@lru_cache(maxsize=64)
def _fuente_cache(tamano: int) -> pygame.font.Font:
    ruta = RAIZ / rutaFuenteCuento
    try:
        return pygame.font.Font(str(ruta), tamano)
    except (OSError, pygame.error):
        return pygame.font.Font(None, tamano)


def texto(superficie, cadena, pos, tamano=28, color=(45, 42, 55), centro=False, negrita=False):
    imagen = fuente(tamano, negrita).render(str(cadena), True, color)
    rect = imagen.get_rect(center=pos) if centro else imagen.get_rect(topleft=pos)
    superficie.blit(imagen, rect)
    return rect


def texto_con_contorno(superficie, cadena, pos, tamano=28, color=(255, 255, 255), contorno=(28, 24, 38),
                       centro=False, grosor=3, negrita=False):
    """Texto legible encima de escenas con colores variables."""
    f = fuente(tamano, negrita)
    imagen = f.render(str(cadena), True, color)
    borde = f.render(str(cadena), True, contorno)
    rect = imagen.get_rect(center=pos) if centro else imagen.get_rect(topleft=pos)
    for dx in range(-grosor, grosor + 1):
        for dy in range(-grosor, grosor + 1):
            if dx * dx + dy * dy <= grosor * grosor and (dx or dy):
                superficie.blit(borde, (rect.x + dx, rect.y + dy))
    superficie.blit(imagen, rect)
    return rect


def panel(superficie, rect, color=(255, 247, 234), borde=(94, 66, 73), radio=18, ancho=3):
    pygame.draw.rect(superficie, color, rect, border_radius=radio)
    pygame.draw.rect(superficie, borde, rect, ancho, border_radius=radio)


# ---------------------------------------------------------------------------
# Piezas acuarela de la interfaz común (assets/Interfaz), escaladas y cacheadas
# ---------------------------------------------------------------------------

def _estirar(imagen: pygame.Surface, ancho: int, alto: int) -> pygame.Surface:
    """Estira una pieza horizontal conservando las puntas redondeadas."""
    escala = alto / imagen.get_height()
    img = pygame.transform.smoothscale(imagen, (max(1, int(imagen.get_width() * escala)), alto))
    punta = min(alto, img.get_width() // 2, ancho // 2)
    out = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    out.blit(img, (0, 0), (0, 0, punta, alto))
    medio = img.subsurface((punta, 0, img.get_width() - punta * 2, alto))
    if ancho - punta * 2 > 0:
        out.blit(pygame.transform.smoothscale(medio, (ancho - punta * 2, alto)), (punta, 0))
    out.blit(img, (ancho - punta, 0), (img.get_width() - punta, 0, punta, alto))
    return out


@lru_cache(maxsize=64)
def pieza_interfaz(nombre: str, ancho: int, alto: int) -> pygame.Surface:
    """`bannerUbicacion`, `barraTiempoRiel`, `barraTiempoRelleno`, `botonMorado`, `botonRojo`… a medida."""
    base = AssetManager.get_instance().cargarSinFondo(os.path.join("Interfaz", f"{nombre}.jpg"), 1200)
    return _estirar(base, ancho, alto)


def tenir(imagen: pygame.Surface, color) -> pygame.Surface:
    """Tiñe una pieza acuarela conservando su textura (luces y sombras)."""
    gris = pygame.transform.grayscale(imagen)
    capa = pygame.Surface(imagen.get_size(), pygame.SRCALPHA)
    capa.fill((*color, 255))
    gris.blit(capa, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    gris.blit(gris, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return gris


@lru_cache(maxsize=32)
def circulo_acuarela(diametro: int, color: Optional[tuple] = None) -> pygame.Surface:
    """Círculo acuarela hecho con la punta redonda de la píldora morada (opcionalmente teñido)."""
    base = AssetManager.get_instance().cargarSinFondo(os.path.join("Interfaz", "botonMorado.jpg"), 1200)
    alto = base.get_height()
    mitad = base.subsurface((0, 0, alto // 2, alto)).copy()
    circulo = pygame.Surface((alto // 2 * 2, alto), pygame.SRCALPHA)
    circulo.blit(mitad, (0, 0))
    circulo.blit(pygame.transform.flip(mitad, True, False), (alto // 2, 0))
    if color is not None:
        circulo = tenir(circulo, color)
    return pygame.transform.smoothscale(circulo, (diametro, diametro))


def barra_acuarela(superficie, rect: pygame.Rect, valor: float, color: Optional[tuple] = None) -> None:
    """Barra de progreso con el riel y el relleno verde acuarela de los demás minijuegos."""
    riel = pieza_interfaz("barraTiempoRiel", rect.width, rect.height)
    superficie.blit(riel, rect)
    alto_relleno = max(4, int(rect.height * 0.62))
    ancho_max = rect.width - int(rect.height * 0.36)
    ancho = int(ancho_max * max(0.0, min(1.0, valor)))
    if ancho >= alto_relleno:
        relleno = pieza_interfaz("barraTiempoRelleno", ancho, alto_relleno)
        if color is not None:
            relleno = tenir(relleno, color)
        superficie.blit(relleno, (rect.x + int(rect.height * 0.18), rect.centery - alto_relleno // 2))


TINTA = (92, 58, 48)


def cartel(s: pygame.Surface, mensaje: str, centro, ancho: int = 760, alto: int = 76,
           color: Optional[tuple] = None, tam: int = 30) -> pygame.Rect:
    """Cartel crema acuarela (como el de los demás minijuegos) con texto IndieFlower."""
    banner = pieza_interfaz("bannerUbicacion", ancho, alto)
    if color is not None:
        banner = tenir(banner, color)
    rect = banner.get_rect(center=centro)
    s.blit(banner, rect)
    if mensaje:
        txt = fuente(tam).render(mensaje, True, TINTA)
        if txt.get_width() > ancho - 60:
            txt = pygame.transform.smoothscale_by(txt, (ancho - 60) / txt.get_width())
        s.blit(txt, txt.get_rect(center=rect.center))
    return rect


# ---------------------------------------------------------------------------
# Audio y entrada
# ---------------------------------------------------------------------------

class ManagedSound:
    """Envuelve un pygame.mixer.Sound para que respete el volumen y el mute de AudioManager."""

    def __init__(self, sound: Optional[pygame.mixer.Sound], volume_scale: float = 1.0) -> None:
        self.sound = sound
        self.volume_scale = volume_scale

    def play(self):
        return AudioManager.get_instance().play_sfx(self.sound, self.volume_scale)

    def set_volume(self, _value: float) -> None:
        """El volumen lo decide AudioManager."""


def recortar_sonido(sonido: pygame.mixer.Sound, max_seg: Optional[float]) -> pygame.mixer.Sound:
    """Quita el silencio inicial y, si se pide, corta a `max_seg` con un desvanecido de salida.

    Los efectos de los juegos rápidos deben sonar al instante y no encimarse; el archivo original no cambia.
    """
    try:
        datos = pygame.sndarray.array(sonido)
        frec = pygame.mixer.get_init()[0]
        nivel = np.abs(datos.astype(np.int32)).reshape(len(datos), -1).max(axis=1)
        umbral = max(1, int(nivel.max() * 0.04))
        inicio = int(np.argmax(nivel > umbral))
        datos = datos[inicio:]
        if max_seg is not None and len(datos) > int(max_seg * frec):
            datos = datos[: int(max_seg * frec)].copy()
            n = min(len(datos), int(0.15 * frec))
            rampa = np.linspace(1.0, 0.0, n)
            datos[-n:] = (datos[-n:] * (rampa[:, None] if datos.ndim > 1 else rampa)).astype(datos.dtype)
        return pygame.sndarray.make_sound(np.ascontiguousarray(datos))
    except Exception:
        return sonido


def load_managed_sound(filename: str, volume_scale: float = 1.0, max_seg: Optional[float] = None) -> Optional[ManagedSound]:
    try:
        if not pygame.mixer.get_init():
            return None
        sonido = pygame.mixer.Sound(str(RAIZ / "assets" / filename))
        return ManagedSound(recortar_sonido(sonido, max_seg), volume_scale)
    except (pygame.error, OSError):
        return None


class HeldKeys:
    """Vector de teclas sostenidas con alias (p. ej. flechas -> A/D) y teclado + mando."""

    def __init__(self, aliases: Optional[Dict[int, tuple]] = None,
                 extra: Optional[Callable[[int], bool]] = None) -> None:
        self.aliases = aliases or {}
        self.extra = extra
        self._pressed = input_state.get_pressed()

    def refresh(self) -> "HeldKeys":
        self._pressed = input_state.get_pressed()
        return self

    def __getitem__(self, key: int) -> bool:
        if self._pressed[key]:
            return True
        for alias in self.aliases.get(key, ()):
            if self._pressed[alias]:
                return True
        return bool(self.extra and self.extra(key))
