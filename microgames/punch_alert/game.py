import os
import math
import random
from typing import Optional, Callable, List, Tuple, Dict, Any
import pygame
import numpy as np

from core.microgame import BaseMicrogame
from core.camera_gestures import CameraGestureInput
from core.asset_manager import AssetManager, quitarBlanco

# Cachés compartidas a nivel de módulo para reutilizar sprites procesados y buffers de audio
_SURFACE_CACHE: Dict[Tuple[Any, ...], Any] = {}
_AUDIO_CACHE: Dict[Tuple[Any, ...], Any] = {}

escalaArbolito = 0.696
esquinaArbolito = (0.25802, 0.00352)
pasosTono = 12
segundosPorPaso = 1.2
realceTono = 1.9
estrellasExtra = 26
pausaFugaz = (2.5, 6.5)

ideasPublicacion = [
    ("ubicacion", "Estamos aquí ahorita", True),
    ("casa", "La dirección de la casa", True),
    ("viaje", "Mañana nos vamos de viaje", True),
    ("ninos", "Fotos de los niños sin permiso", True),
    ("regalos", "Los regalos caros que compramos", True),
    ("placa", "La placa del carro", True),
    ("tiquete", "El tiquete con su código", True),
    ("rutina", "Venimos todos los viernes a esta hora", True),
    ("lucecitas", "Filtro de lucecitas", False),
    ("arbolito", "¡Qué belleza de arbolito!", False),
    ("villancico", "Villancico de fondo", False),
    ("felicitacion", "¡Feliz Navidad, familia!", False),
    ("despues", "Publicarlo cuando ya se fueron", False),
    ("permiso", "Pedir permiso antes de etiquetar", False),
    ("cercanos", "Solo para familia y amigos", False),
    ("album", "Guardarla en el álbum familiar", False),
    # Tarjetas nuevas (inofensivas): cada una se aplica a la publicación si se deja caer
    ("nieve", "Filtro de nieve", False),
    ("recuerdo", "Filtro de foto antigua", False),
    ("hashtag", "Hashtag navideño", False),
    ("abuela", "Comentario de la abuela", False),
]
# Las tarjetas nuevas no están en Punch/tarjetas.png: se arman con la tarjeta vacía y su icono.
# Icono propio (acuarela, fondo blanco) en assets/Punch/iconos/<codigo>.png; si falta, uno dibujado por código.
tarjetasNuevas = ("nieve", "recuerdo", "hashtag", "abuela")
# Música que suena cuando la tarjeta del villancico llega a la publicación
musicaVillancico = ("Punch/villancico.mp3", "Punch/villancico.ogg")
comentarioAbuela = "Abuela: ¡Qué lindos mis muchachos!"
ensenanzasRiesgo = {
    "ninos": "Esa carita no decidió estar en internet. Decidiste tú por ella.",
    "casa": "Ahora medio mundo sabe dónde duermes.",
    "viaje": "Le contaste a medio mundo cuándo se queda sola tu casa.",
    "ubicacion": "Publicaste dónde estaban. Y alguien que no conoces ya va pa' allá.",
    "rutina": "Si siempre estás aquí a la misma hora, cualquiera puede esperarte.",
    "tiquete": "Ese código dice quién eres, a dónde vas y cuándo.",
    "regalos": "Mostraste lo que tienes. Alguien ya está pensando cómo quitártelo.",
    "placa": "Con una placa, cualquiera te encuentra en la calle.",
}
ordenGravedad = ["ninos", "casa", "viaje", "ubicacion", "rutina", "tiquete", "regalos", "placa"]
cierreEnsenanza = "Comparte el momento, no tu vida entera."
ensenanzaSegura = ["Subiste lo bonito y te guardaste lo tuyo.",
                   "Así sí, mi llave: los recuerdos se comparten, los datos se cuidan."]
ensenanzaVacia = ["Cuidar tus datos no es borrarlo todo.", "Lo bonito también se comparte, mi llave."]
destinoIdea = {
    "ubicacion": "descripcion", "casa": "descripcion", "viaje": "descripcion", "ninos": "descripcion",
    "regalos": "descripcion", "placa": "descripcion", "tiquete": "descripcion", "rutina": "descripcion",
    "arbolito": "descripcion", "felicitacion": "descripcion", "permiso": "descripcion",
    "lucecitas": "filtro", "villancico": "cancion", "despues": "hora", "cercanos": "publico", "album": "guardar",
    "nieve": "nieve", "recuerdo": "recuerdo", "hashtag": "descripcion", "abuela": "comentario",
}
textosDescripcion = {
    "ubicacion": "En la Ventana al Mundo ahorita mismo.",
    "casa": "Ya pa' la casa: calle 58 #43-21.",
    "viaje": "Mañana nos vamos de viaje toda la familia.",
    "ninos": "Con los niños, Sofi y Juanchito.",
    "regalos": "Ya compramos la tele y el celular nuevos.",
    "placa": "Llegamos en el carro, placa BAQ 284.",
    "tiquete": "Tiquete listo, código XJ7K2.",
    "rutina": "Aquí todos los viernes a las 7.",
    "arbolito": "¡Qué belleza de arbolito!",
    "felicitacion": "¡Feliz Navidad, familia!",
    "permiso": "Etiqueté a la familia con su permiso.",
    "hashtag": "#NavidadEnCurramba",
}
cancionPost = "Los peces en el río"
horaPost = "Se publica mañana, ya en la casa"
publicoPost = "Familia y amigos"
guardarPost = (1360, 1588, 60, 73)
puntosPost = (1359, 386, 66, 12)
letrasPorSegundo = 34.0
colorAcierto = (255, 214, 130)
colorPost = (255, 194, 214)
colorError = (206, 176, 255)
contornoTexto = (60, 36, 70)

tituloBuenas = "Buenas pa' compartir"
tituloMalas = "Mejor guárdatelas"
marcaPublicada = "la publicaste"
marcaBorrada = "la borraste"

cajaPost = (289, 227, 1262, 1850)
fotoPost = (405, 505, 1030, 1034)
avatarPost = (474, 393, 62)
usuarioPost = (578, 369, 330, 46)
likesPost = (415, 1712, 372, 54)
renglonesPost = (422, 1000, (1819, 1881, 1944))
altoPost = 700
esquinaPost = (52, 168)
rectFoto = (560, 100, 960, 960)
ladoFotoVista = 600
duracionPublicar = 3.4
velocidadCaida = (620.0, 760.0)
separacionTarjetas = 0.8


def partirTexto(texto: str, fuente: pygame.font.Font, ancho: int) -> List[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = (actual + " " + palabra).strip()
        if actual and fuente.size(prueba)[0] > ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    if actual:
        lineas.append(actual)
    return lineas


def iconoDibujado(codigo: str, lado: int) -> pygame.Surface:
    """Icono provisional dibujado por código (al doble y reducido, trazo de tinta suave)."""
    k = 3
    n = lado * k
    sup = pygame.Surface((n, n), pygame.SRCALPHA)
    tinta = (98, 70, 92)
    c = n // 2
    if codigo == "nieve":
        azul = (120, 170, 220)
        for i in range(6):
            a = math.radians(i * 60 + 90)
            fin = (c + math.cos(a) * n * 0.38, c - math.sin(a) * n * 0.38)
            pygame.draw.line(sup, azul, (c, c), fin, 5 * k)
            for lado_r in (-1, 1):
                b = a + lado_r * math.radians(40)
                medio = (c + math.cos(a) * n * 0.22, c - math.sin(a) * n * 0.22)
                pygame.draw.line(sup, azul, medio, (medio[0] + math.cos(b) * n * 0.11, medio[1] - math.sin(b) * n * 0.11), 4 * k)
        pygame.draw.circle(sup, (230, 242, 255), (c, c), n * 0.07)
        pygame.draw.circle(sup, azul, (c, c), n * 0.07, 2 * k)
    elif codigo == "recuerdo":
        foto = pygame.Rect(0, 0, int(n * 0.66), int(n * 0.6))
        foto.center = (c, c)
        pygame.draw.rect(sup, (250, 240, 222), foto, border_radius=4 * k)
        dentro = foto.inflate(-int(n * 0.1), -int(n * 0.16)).move(0, -int(n * 0.03))
        pygame.draw.rect(sup, (205, 160, 110), dentro)
        pygame.draw.circle(sup, (240, 205, 140), (dentro.x + dentro.w * 0.7, dentro.y + dentro.h * 0.32), n * 0.06)
        pygame.draw.polygon(sup, (150, 110, 74), [(dentro.x, dentro.bottom), (dentro.x + dentro.w * 0.42, dentro.y + dentro.h * 0.45),
                                                (dentro.right, dentro.bottom)])
        pygame.draw.rect(sup, tinta, foto, 3 * k, border_radius=4 * k)
    elif codigo == "hashtag":
        try:
            from core.asset_manager import AssetManager
            fuente = AssetManager.get_instance().cargarFuenteCuento(int(n * 0.8))
            letra = fuente.render("#", True, (214, 120, 150))
            sup.blit(letra, letra.get_rect(center=(c, c + n * 0.04)))
        except Exception:
            for d in (-0.13, 0.13):
                pygame.draw.line(sup, (214, 120, 150), (c + d * n - n * 0.05, c - n * 0.3), (c + d * n - n * 0.12, c + n * 0.3), 6 * k)
                pygame.draw.line(sup, (214, 120, 150), (c - n * 0.32, c + d * n), (c + n * 0.3, c + d * n), 6 * k)
    else:  # abuela: globo de comentario con corazón
        globo = pygame.Rect(0, 0, int(n * 0.72), int(n * 0.5))
        globo.center = (c, c - int(n * 0.06))
        pygame.draw.ellipse(sup, (255, 248, 238), globo)
        pygame.draw.polygon(sup, (255, 248, 238), [(globo.x + globo.w * 0.25, globo.bottom - 6 * k),
                                                  (globo.x + globo.w * 0.18, globo.bottom + n * 0.12),
                                                  (globo.x + globo.w * 0.42, globo.bottom - 4 * k)])
        pygame.draw.ellipse(sup, tinta, globo, 3 * k)
        r = n * 0.07
        hx, hy = globo.centerx, globo.centery
        pygame.draw.circle(sup, (226, 96, 110), (hx - r * 0.7, hy - r * 0.3), r)
        pygame.draw.circle(sup, (226, 96, 110), (hx + r * 0.7, hy - r * 0.3), r)
        pygame.draw.polygon(sup, (226, 96, 110), [(hx - r * 1.6, hy), (hx + r * 1.6, hy), (hx, hy + r * 1.8)])
    return pygame.transform.smoothscale(sup, (lado, lado))


def suavizar(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def prepararTono(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    maximo = rgb.max(axis=-1)
    minimo = rgb.min(axis=-1)
    rango = maximo - minimo
    seguro = np.where(rango == 0, 1.0, rango)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    tono = np.where(maximo == r, ((g - b) / seguro) % 6.0,
                    np.where(maximo == g, (b - r) / seguro + 2.0, (r - g) / seguro + 4.0)) * 60.0
    tono = np.where(rango == 0, 0.0, tono)
    saturacion = np.where(maximo == 0, 0.0, rango / np.where(maximo == 0, 1.0, maximo))
    peso = np.clip(1.0 - np.abs(tono - 185.0) / 45.0, 0.0, 1.0) * np.clip(saturacion / 0.12, 0.0, 1.0)
    return tono, saturacion, maximo, peso


def girarTono(rgb: np.ndarray, datos: Tuple[np.ndarray, ...], grados: float) -> np.ndarray:
    tono, saturacion, maximo, peso = datos
    nuevo = (tono + grados) % 360.0 / 60.0
    c = maximo * np.minimum(1.0, saturacion * realceTono)
    x = c * (1.0 - np.abs(nuevo % 2.0 - 1.0))
    m = maximo - c
    sector = nuevo.astype(int) % 6
    ceros = np.zeros_like(c)
    rr = np.choose(sector, [c, x, ceros, ceros, x, c])
    gg = np.choose(sector, [x, c, c, x, ceros, ceros])
    bb = np.choose(sector, [ceros, ceros, x, c, c, x])
    girado = np.stack([rr + m, gg + m, bb + m], axis=-1)
    return rgb * (1.0 - peso[..., None]) + girado * peso[..., None]


def brilloEstrella(lado: int) -> pygame.Surface:
    centro = (lado - 1) / 2.0
    ys, xs = np.mgrid[0:lado, 0:lado]
    dx, dy = xs - centro, ys - centro
    distancia = np.hypot(dx, dy)
    escala = lado / 25.0
    nucleo = np.exp(-(distancia / (1.6 * escala)) ** 2)
    halo = 0.35 * np.exp(-(distancia / (5.5 * escala)) ** 2)
    rayos = (np.exp(-(dx / (0.8 * escala)) ** 2) * np.exp(-np.abs(dy) / (4.0 * escala))
             + np.exp(-(dy / (0.8 * escala)) ** 2) * np.exp(-np.abs(dx) / (4.0 * escala)))
    alfa = np.clip(nucleo + halo + 0.45 * rayos, 0.0, 1.0)
    capa = pygame.Surface((lado, lado), pygame.SRCALPHA)
    capa.fill((236, 242, 255, 0))
    pixeles = pygame.surfarray.pixels_alpha(capa)
    pixeles[:] = (alfa.T * 255).astype(np.uint8)
    del pixeles
    return capa


def estelaFugaz(largo: int = 220, grueso: int = 17) -> pygame.Surface:
    ys, xs = np.mgrid[0:grueso, 0:largo]
    centro = (grueso - 1) / 2.0
    cruzado = np.exp(-((ys - centro) / 2.0) ** 2) + 0.35 * np.exp(-((ys - centro) / 5.0) ** 2)
    avance = (xs / float(largo)) ** 1.5
    cabeza = np.exp(-(((xs - (largo - 8)) / 5.0) ** 2 + ((ys - centro) / 3.2) ** 2))
    alfa = np.clip(cruzado * avance + 1.3 * cabeza, 0.0, 1.0)
    capa = pygame.Surface((largo, grueso), pygame.SRCALPHA)
    capa.fill((228, 236, 255, 0))
    pixeles = pygame.surfarray.pixels_alpha(capa)
    pixeles[:] = (alfa.T * 255).astype(np.uint8)
    del pixeles
    return capa

class PunchAlertMicrogame(BaseMicrogame):
    CAMERA_POINTER = False  # Usa la cámara directamente
    dialogoPaloma = [
        ["¡Qué foto tan bacana en la Ventana al Mundo!",
         "Ahora el celular sugiere ideas para tu post,",
         "pero ojo: no todo se debe contar en internet."],
        ["Cuando una tarjeta caiga en la caja,",
         "saca con ESPACIO (o puño) lo que exponga tus datos.",
         "¡Deja pasar solo los recuerdos seguros!"],
    ]
    """
    Minijuego Punch-Alert: El Despachador de Notificaciones (Estilo WarioWare / Béisbol).
    Compatible 100% con el sistema de niveles / escenas (StoryMap, ArcadeMode, FreePlay)
    con la misma firma `(character_id, on_complete_callback)` que `UninorteSprintMicrogame`.
    
    1. Voces Reactivas por Personaje al Golpear Notificaciones (`CHARACTER_PUNCH_VOICES`):
       - Arquitectura preparada para que cada personaje (`char`, `katherine`, `valdiri`, `westcol`)
         tenga su propio banco de audios al conectar un golpe.
       - Por ahora, todos los personajes utilizan como fallback activo las 4 voces de `char`
         (`char_audio_0_microjuego_puño.ogg` .. `char_audio_3_microjuego_puño.ogg`), pero tan pronto
         se agreguen los archivos de cada personaje (ej. `westcol_audio_0_microjuego_puño.ogg`),
         el sistema los detecta y reproduce automáticamente sin cambiar una sola línea de código.
    
    2. Recorte Quirúrgico y Limpieza de Componentes:
       - Notificaciones (`assets/notificaciones_microjuego.png` - 1774x887 RGBA):
         Extracción limpia sin residuos de filas adyacentes y preservando aspect ratio.
       - Personaje (`assets/*_sprite_box_microjuego.png`):
         Separación dinámica por valle de transparencia, con animación de respiración (idle bobbing),
         sombra elíptica suave bajo los pies e impulso ascendente al lanzar el uppercut.
       - HUD de Strikes (`assets/ui_strike_microjuegos.png`):
         Barra limpia con marcas 'X' dinámicas centradas en los 3 círculos vacíos (sin contador de alertas extra).
       - Reloj Contador Gráfico Oficial (`assets/contador_microjuegos.png`) en la esquina superior derecha.
    """

    # =========================================================================
    # MAPA DE VOCES POR PERSONAJE AL CONECTAR EL PUÑO (ESCALABLE POR NIVEL/PERSONAJE)
    # =========================================================================
    # Cada personaje tiene su propia lista de archivos de voz al golpear una notificación.
    # Si los archivos específicos de un personaje aún no están en `assets/`, el cargador
    # usa automáticamente las voces de `char` como fallback activo.
    ensenanzaFinal = {"gana": [cierreEnsenanza], "pierde": [cierreEnsenanza]}

    CHARACTER_PUNCH_VOICES: Dict[str, List[str]] = {
        "char": [
            "char_audio_0_microjuego_puño.ogg",
            "char_audio_1_microjuego_puño.ogg",
            "char_audio_2_microjuego_puño.ogg",
            "char_audio_3_microjuego_puño.ogg",
        ],
        "katherine": [
            "katherine_audio_0_microjuego_puño.ogg",
            "katherine_audio_1_microjuego_puño.ogg",
            "katherine_audio_2_microjuego_puño.ogg",
            "katherine_audio_3_microjuego_puño.ogg",
        ],
        "valdiri": [
            "valdiri_audio_0_microjuego_puño.ogg",
            "valdiri_audio_1_microjuego_puño.ogg",
            "valdiri_audio_2_microjuego_puño.ogg",
            "valdiri_audio_3_microjuego_puño.ogg",
        ],
        "westcol": [
            "westcol_audio_0_microjuego_puño.ogg",
            "westcol_audio_1_microjuego_puño.ogg",
            "westcol_audio_2_microjuego_puño.ogg",
            "westcol_audio_3_microjuego_puño.ogg",
        ],
    }

    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None,
        command_text: str = "¡Cuida tu publicación!\nGolpea lo que no debes compartir",
        time_limit: float = 48.0
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text=command_text,
            time_limit=time_limit,
            on_complete_callback=on_complete_callback
        )

    def _flush_camera_gestures(self) -> None:
        cam = getattr(self, "camera_input", None)
        if cam and getattr(cam, "enabled", False):
            cam.consume_punch()
            cam.consume_fist()
            cam.consume_click()

    def enter(self, params: Optional[dict] = None) -> None:
        self.villancicoSonando = False
        self.audio.fadeout_music(400)
        self._camera_resume_grace = 0.25
        self._flush_camera_gestures()

    def ponerMusica(self) -> None:
        # Si ya cayó el villancico, esa es la música de la publicación: no se vuelve a poner la del juego.
        if getattr(self, "villancicoSonando", False):
            return
        self.audio.play_bgm("PunchMusic.mp3", volume_scale=0.35)

    def ponerVillancico(self) -> bool:
        """La publicación ya tiene el villancico: suena "Los peces en el río" en lugar de la música del juego."""
        for nombre in musicaVillancico:
            if os.path.exists(os.path.join(self.audio.base_assets_dir, nombre)):
                self.villancicoSonando = True
                self.audio.stop_music()  # Apagar la música del juego antes de que entre el villancico
                self.audio.play_bgm(nombre, volume_scale=0.5)
                return True
        return False

    def _extract_tight_surface(self, surface: pygame.Surface, rect: pygame.Rect) -> pygame.Surface:
        """Extrae un subsurface y lo ajusta a su bounding box de píxeles no transparentes."""
        sub = surface.subsurface(rect)
        bbox = sub.get_bounding_rect(min_alpha=20)
        if bbox.width > 0 and bbox.height > 0:
            return sub.subsurface(bbox).copy()
        return sub.copy()

    def _extract_clean_card_surface(self, sheet: pygame.Surface, rect: pygame.Rect) -> pygame.Surface:
        """
        Extrae una tarjeta de notificación limpiando con NumPy vectorizado cualquier artefacto
        desconectado en los primeros píxeles superiores y ajustando a su bounding box real.
        """
        sub = sheet.subsurface(rect).copy()
        alpha_arr = pygame.surfarray.pixels_alpha(sub)
        w, h = sub.get_size()

        if w > 0 and h > 4:
            y_lim = min(25, h)
            top_active = (alpha_arr[:, 0] > 15) | (alpha_arr[:, 2] > 15)
            low_band = alpha_arr[:, 4:y_lim] < 15
            has_gap = top_active & low_band.any(axis=1)
            if has_gap.any():
                cols = np.flatnonzero(has_gap)
                ys = 4 + np.argmax(low_band[cols], axis=1)
                y_grid = np.arange(y_lim)[None, :]
                band_view = alpha_arr[cols, :y_lim]
                band_view[y_grid < ys[:, None]] = 0
                alpha_arr[cols, :y_lim] = band_view

        del alpha_arr

        bbox = sub.get_bounding_rect(min_alpha=25)
        if bbox.width > 0 and bbox.height > 0:
            return sub.subsurface(bbox).copy()
        return sub

    def cargarArbolito(self) -> None:
        clave = ("arbolito", self.screen_w, self.screen_h)
        if clave in _SURFACE_CACHE:
            self.arbolitos, self.posArbolito = _SURFACE_CACHE[clave]
            return
        self.arbolitos, self.posArbolito = [], (0, 0)
        try:
            hoja = self.assets.load_surface(os.path.join("Punch", "arbolito.png"), has_alpha=False)
        except Exception:
            _SURFACE_CACHE[clave] = (self.arbolitos, self.posArbolito)
            return
        luz = pygame.surfarray.array3d(hoja).max(axis=2)
        xs, ys = np.nonzero(luz > 8)
        if xs.size == 0:
            _SURFACE_CACHE[clave] = (self.arbolitos, self.posArbolito)
            return
        caja = pygame.Rect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
        escala = escalaArbolito * self.screen_w / float(hoja.get_width())
        medida = (max(1, round(caja.w * escala)), max(1, round(caja.h * escala)))
        pequeno = pygame.transform.smoothscale(hoja.subsurface(caja), medida)
        rgb = pygame.surfarray.array3d(pequeno).astype(np.float32) / 255.0
        alfa = np.clip(rgb.max(axis=2) / 0.3, 0.0, 1.0)
        limpio = rgb / np.maximum(alfa, 0.02)[..., None]
        datos = prepararTono(limpio)
        for paso in range(pasosTono):
            grados = paso * 360.0 / pasosTono
            color = np.clip(girarTono(limpio, datos, grados), 0.0, 1.0)
            capa = pygame.Surface(medida, pygame.SRCALPHA)
            pygame.surfarray.blit_array(capa, (color * 255).astype(np.uint8))
            pixeles = pygame.surfarray.pixels_alpha(capa)
            pixeles[:] = (alfa * 255).astype(np.uint8)
            del pixeles
            self.arbolitos.append(capa)
        self.posArbolito = (round(esquinaArbolito[0] * self.screen_w + caja.x * escala),
                            round(esquinaArbolito[1] * self.screen_h + caja.y * escala))
        _SURFACE_CACHE[clave] = (self.arbolitos, self.posArbolito)

    def cargarCielo(self) -> None:
        self.fugaces: List[dict] = []
        self.proximaFugaz = None
        clave = ("cielo", self.screen_w, self.screen_h)
        if clave in _SURFACE_CACHE:
            self.estrellasCielo, self.mascaraCielo, self.estelaCielo = _SURFACE_CACHE[clave]
            return
        w, h = self.screen_w, self.screen_h
        rgb = pygame.surfarray.array3d(self.bg_surface).astype(np.int16)
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        luz = rgb.mean(axis=2)
        cielo = (b > r + 35) & (b > g + 15) & (luz < 140)
        cielo[:, int(h * 0.58):] = False
        plano = pygame.Surface((w, h))
        pygame.surfarray.blit_array(plano, np.repeat((cielo * 255).astype(np.uint8)[..., None], 3, axis=2))
        borroso = pygame.transform.smoothscale(pygame.transform.smoothscale(plano, (w // 12, h // 12)), (w, h))
        mascara = np.clip((pygame.surfarray.array3d(borroso)[..., 0] / 255.0 - 0.6) / 0.3, 0.0, 1.0)
        plano = pygame.Surface((w, h))
        pygame.surfarray.blit_array(plano, np.repeat(luz.astype(np.uint8)[..., None], 3, axis=2))
        entorno = pygame.surfarray.array3d(pygame.transform.smoothscale(
            pygame.transform.smoothscale(plano, (w // 16, h // 16)), (w, h)))[..., 0].astype(np.int16)
        rango = rgb.max(axis=2) - rgb.min(axis=2)
        brillantes = (luz > 150) & (luz - entorno > 70) & (rango < 90) & (mascara > 0.95)
        xs, ys = np.nonzero(brillantes)
        orden = np.argsort(-luz[xs, ys])
        azar = random.Random(7)
        grande, chica = brilloEstrella(27), brilloEstrella(15)
        puntos: List[Tuple[int, int]] = []
        self.estrellasCielo = []
        for i in orden:
            x, y = int(xs[i]), int(ys[i])
            if all((x - px) ** 2 + (y - py) ** 2 > 144 for px, py in puntos):
                puntos.append((x, y))
                self.estrellasCielo.append((x, y, azar.uniform(0, math.tau), azar.uniform(0.35, 0.9), 1.0, grande))
        libres = np.argwhere(mascara > 0.97)
        intentos, limite = 0, len(puntos) + estrellasExtra
        while libres.size and len(puntos) < limite and intentos < 600:
            intentos += 1
            x, y = (int(v) for v in libres[azar.randrange(len(libres))])
            if all((x - px) ** 2 + (y - py) ** 2 > 1600 for px, py in puntos):
                puntos.append((x, y))
                self.estrellasCielo.append((x, y, azar.uniform(0, math.tau), azar.uniform(0.25, 0.7), 0.75, chica))
        self.mascaraCielo = mascara
        self.estelaCielo = estelaFugaz()
        _SURFACE_CACHE[clave] = (self.estrellasCielo, self.mascaraCielo, self.estelaCielo)

    def lanzarFugaz(self, t: float) -> None:
        angulo = random.uniform(16.0, 32.0)
        direccion = (-math.cos(math.radians(angulo)), math.sin(math.radians(angulo)))
        self.fugaces.append({
            "inicio": t,
            "vida": random.uniform(0.7, 1.0),
            "origen": (random.uniform(0.4, 0.98) * self.screen_w, random.uniform(0.02, 0.2) * self.screen_h),
            "direccion": direccion,
            "rapidez": random.uniform(650.0, 900.0),
            "imagen": pygame.transform.rotozoom(self.estelaCielo, 180.0 + angulo, 1.0),
        })

    def dibujarCielo(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        if not getattr(self, "estrellasCielo", None):
            return
        t = pygame.time.get_ticks() / 1000.0
        for x, y, fase, rapidez, fuerza, imagen in self.estrellasCielo:
            onda = 0.5 + 0.5 * math.sin(t * rapidez * math.tau + fase)
            intensidad = fuerza * onda ** 3
            if intensidad < 0.04:
                continue
            imagen.set_alpha(int(255 * intensidad))
            surface.blit(imagen, imagen.get_rect(center=(x + ox, y + oy)))
        if self.proximaFugaz is None:
            self.proximaFugaz = t + random.uniform(1.0, 2.5)
        if t >= self.proximaFugaz:
            self.lanzarFugaz(t)
            self.proximaFugaz = t + random.uniform(*pausaFugaz)
        vivas = []
        for fugaz in self.fugaces:
            edad = t - fugaz["inicio"]
            if edad > fugaz["vida"]:
                continue
            vivas.append(fugaz)
            avance = fugaz["rapidez"] * edad
            dx, dy = fugaz["direccion"]
            cabeza = (fugaz["origen"][0] + dx * avance, fugaz["origen"][1] + dy * avance)
            mitad = self.estelaCielo.get_width() / 2.0 - 7.0
            imagen = fugaz["imagen"]
            caja = imagen.get_rect(center=(round(cabeza[0] - dx * mitad), round(cabeza[1] - dy * mitad)))
            visible = caja.clip(pygame.Rect(0, 0, self.screen_w, self.screen_h))
            if visible.w <= 0 or visible.h <= 0:
                continue
            fuerza = min(1.0, edad / 0.12) * min(1.0, (fugaz["vida"] - edad) / 0.3)
            trozo = imagen.subsurface(visible.move(-caja.x, -caja.y)).copy()
            pixeles = pygame.surfarray.pixels_alpha(trozo)
            filtro = self.mascaraCielo[visible.x:visible.right, visible.y:visible.bottom]
            pixeles[:] = (pixeles * filtro * fuerza).astype(np.uint8)
            del pixeles
            surface.blit(trozo, (visible.x + ox, visible.y + oy))
        self.fugaces = vivas

    def dibujarArbolito(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        if not getattr(self, "arbolitos", None):
            return
        t = pygame.time.get_ticks() / 1000.0
        vuelta = (t / segundosPorPaso) % len(self.arbolitos)
        actual = int(vuelta) % len(self.arbolitos)
        siguiente = (actual + 1) % len(self.arbolitos)
        mezcla = vuelta - int(vuelta)
        punto = (self.posArbolito[0] + ox, self.posArbolito[1] + oy)
        surface.blit(self.arbolitos[actual], punto)
        if mezcla > 0:
            capa = self.arbolitos[siguiente]
            capa.set_alpha(int(255 * mezcla))
            surface.blit(capa, punto)
            capa.set_alpha(255)

    def tramosOcupados(self, valores, minimo: int = 50) -> List[Tuple[int, int]]:
        tramos, inicio = [], None
        for i, lleno in enumerate(list(valores) + [False]):
            if lleno and inicio is None:
                inicio = i
            elif not lleno and inicio is not None:
                if i - inicio > minimo:
                    tramos.append((inicio, i))
                inicio = None
        return tramos

    def escribirEnTarjeta(self, tarjeta: pygame.Surface, texto: str) -> None:
        w, h = tarjeta.get_size()
        zona = pygame.Rect(int(w * 0.46), int(h * 0.16), int(w * 0.47), int(h * 0.68))
        for tam in (34, 31, 28, 25, 22):
            fuente = self.assets.cargarFuenteCuento(tam)
            lineas = partirTexto(texto, fuente, zona.w)
            if len(lineas) <= 3 and len(lineas) * fuente.get_linesize() <= zona.h:
                break
        alto = fuente.get_linesize()
        y = zona.centery - alto * len(lineas) // 2
        for linea in lineas:
            letras = fuente.render(linea, True, (88, 52, 96))
            tarjeta.blit(letras, letras.get_rect(midtop=(zona.centerx, y)))
            y += alto

    def tarjetaVacia(self, hoja: pygame.Surface, columnas, filas, ancho: int, alto: int) -> pygame.Surface:
        """Tarjeta de la hoja original con el cuadro del icono vaciado (mismo papel, borde y brillo)."""
        n = [c for c, _, _ in ideasPublicacion].index("lucecitas")
        (x0, x1), (y0, y1) = columnas[n % 4], filas[n // 4]
        recorte = self._extract_tight_surface(hoja, pygame.Rect(x0, y0, x1 - x0, y1 - y0))
        base = pygame.transform.smoothscale(recorte, (ancho, alto))
        caja = self.cajaIcono(base)
        interior = caja.inflate(-round(caja.w * 0.16), -round(caja.h * 0.16))
        # Color del papel del cuadro: los píxeles más claros de adentro (el icono y el borde son más oscuros)
        zona = pygame.surfarray.array3d(base.subsurface(interior)).reshape(-1, 3).astype(np.int32)
        brillo = zona.sum(axis=1)
        claros = zona[brillo >= np.percentile(brillo, 70)]
        papel = tuple(int(v) for v in np.median(claros, axis=0))
        pygame.draw.rect(base, papel, interior, border_radius=round(interior.w * 0.18))
        return base

    def iconoTarjeta(self, codigo: str, lado: int) -> pygame.Surface:
        """Icono acuarela de assets/Punch/iconos/<codigo>.png (fondo blanco), o uno dibujado por código."""
        ruta = os.path.join("Punch", "iconos", f"{codigo}.png")
        if os.path.exists(os.path.join("assets", ruta)):
            try:
                icono = self.assets.cargarSinFondo(ruta, 600)
                escala = lado / float(max(icono.get_size()))
                return pygame.transform.smoothscale_by(icono, escala)
            except Exception:
                pass
        return iconoDibujado(codigo, lado)

    def tarjetaConIcono(self, plantilla: pygame.Surface, codigo: str) -> pygame.Surface:
        base = plantilla.copy()
        caja = self.cajaIcono(base)
        icono = self.iconoTarjeta(codigo, round(caja.w * 0.8))
        base.blit(icono, icono.get_rect(center=caja.center))
        return base

    def cajaIcono(self, tarjeta: pygame.Surface) -> pygame.Rect:
        w, h = tarjeta.get_size()
        rgb = pygame.surfarray.array3d(tarjeta).astype(np.int16)
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        marco = (r > 165) & (r < 220) & (g > 135) & (g < 182) & (b > 145) & (b < 192) & (r - g > 15)
        izquierda, derecha = int(w * 0.05), w // 2
        arriba, abajo = int(h * 0.07), int(h * 0.93)
        filas = [np.flatnonzero(marco[izquierda:derecha, y]) + izquierda for y in (h // 2 - 12, h // 2, h // 2 + 12)]
        filas = [f for f in filas if f.size >= 2]
        if not filas:
            lado = int(h * 0.7)
            return pygame.Rect(int(w * 0.07), (h - lado) // 2, lado, lado)
        x0 = int(np.median([f.min() for f in filas]))
        x1 = int(np.median([f.max() for f in filas]))
        columnas = [np.flatnonzero(marco[x, arriba:abajo]) + arriba for x in ((x0 + x1) // 2 - 12, (x0 + x1) // 2, (x0 + x1) // 2 + 12)]
        columnas = [c for c in columnas if c.size >= 2]
        if columnas:
            y0 = int(np.median([c.min() for c in columnas]))
            y1 = int(np.median([c.max() for c in columnas]))
        else:
            y0, y1 = h // 2 - (x1 - x0) // 2, h // 2 + (x1 - x0) // 2
        lado = max(x1 - x0, y1 - y0) + 1
        caja = pygame.Rect(0, 0, lado, lado)
        caja.center = ((x0 + x1 + 1) // 2, (y0 + y1 + 1) // 2)
        return caja

    def recortarIcono(self, tarjeta: pygame.Surface) -> pygame.Surface:
        w, h = tarjeta.get_size()
        rgb = pygame.surfarray.array3d(tarjeta).astype(np.int16)
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        marco = (r > 165) & (r < 220) & (g > 135) & (g < 182) & (b > 145) & (b < 192) & (r - g > 15)
        izquierda, derecha = int(w * 0.05), w // 2
        arriba, abajo = int(h * 0.07), int(h * 0.93)
        filas = [np.flatnonzero(marco[izquierda:derecha, y]) + izquierda for y in (h // 2 - 12, h // 2, h // 2 + 12)]
        filas = [f for f in filas if f.size >= 2]
        if not filas:
            lado = int(h * 0.7)
            caja = pygame.Rect(int(w * 0.07), (h - lado) // 2, lado, lado)
        else:
            x0 = int(np.median([f.min() for f in filas]))
            x1 = int(np.median([f.max() for f in filas]))
            columnas = [np.flatnonzero(marco[x, arriba:abajo]) + arriba for x in ((x0 + x1) // 2 - 12, (x0 + x1) // 2, (x0 + x1) // 2 + 12)]
            columnas = [c for c in columnas if c.size >= 2]
            if columnas:
                y0 = int(np.median([c.min() for c in columnas]))
                y1 = int(np.median([c.max() for c in columnas]))
            else:
                y0, y1 = h // 2 - (x1 - x0) // 2, h // 2 + (x1 - x0) // 2
            lado = max(x1 - x0, y1 - y0) + 1 + 8
            caja = pygame.Rect(0, 0, lado, lado)
            caja.center = ((x0 + x1 + 1) // 2, (y0 + y1 + 1) // 2)
        caja = caja.clip(tarjeta.get_rect())
        icono = tarjeta.subsurface(caja).copy()
        mascara = pygame.Surface(caja.size, pygame.SRCALPHA)
        pygame.draw.rect(mascara, (255, 255, 255, 255), mascara.get_rect(), border_radius=round(caja.w * 0.22))
        icono.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        return self.suavizarOrilla(icono)

    def cargarTarjetas(self, ancho: int, alto: int) -> None:
        clave = ("tarjetasPost", ancho, alto)
        if clave not in _SURFACE_CACHE:
            hoja = self.assets.load_surface(os.path.join("Punch", "tarjetas.png"))
            opaco = pygame.surfarray.array_alpha(hoja) > 120
            columnas = self.tramosOcupados(opaco.sum(axis=1) > 20)
            filas = self.tramosOcupados(opaco.sum(axis=0) > 20)
            ideas = []
            plantilla = None
            for n, (codigo, texto, riesgosa) in enumerate(ideasPublicacion):
                if codigo in tarjetasNuevas:
                    if plantilla is None:
                        plantilla = self.tarjetaVacia(hoja, columnas, filas, ancho, alto)
                    base = self.tarjetaConIcono(plantilla, codigo)
                    icono = self.recortarIcono(base)
                    tarjeta = base.copy()
                    self.escribirEnTarjeta(tarjeta, texto)
                    ideas.append({"codigo": codigo, "texto": texto, "riesgosa": riesgosa, "sprite": tarjeta, "icono": icono})
                    continue
                (x0, x1), (y0, y1) = columnas[n % 4], filas[n // 4]
                recorte = self._extract_tight_surface(hoja, pygame.Rect(x0, y0, x1 - x0, y1 - y0))
                base = pygame.transform.smoothscale(recorte, (ancho, alto))
                icono = self.recortarIcono(base)
                tarjeta = base.copy()
                self.escribirEnTarjeta(tarjeta, texto)
                ideas.append({"codigo": codigo, "texto": texto, "riesgosa": riesgosa, "sprite": tarjeta, "icono": icono})
            _SURFACE_CACHE[clave] = ideas
        self.ideas = _SURFACE_CACHE[clave]
        self.trash_sprites = [idea["sprite"] for idea in self.ideas if idea["riesgosa"]]
        self.safe_sprites = [idea["sprite"] for idea in self.ideas if not idea["riesgosa"]]

    def cargarPublicacion(self) -> None:
        clave = ("publicacion", altoPost)
        if clave not in _SURFACE_CACHE:
            hoja = self.assets.load_surface(os.path.join("Punch", "publicacion.png"), has_alpha=False)
            escala = altoPost / float(cajaPost[3])
            medida = (round(cajaPost[2] * escala), altoPost)
            plano = pygame.transform.smoothscale(hoja.subsurface(pygame.Rect(cajaPost)), medida).convert_alpha()
            limpio = quitarBlanco(plano)
            if limpio.get_size() != medida:
                lienzo = pygame.Surface(medida, pygame.SRCALPHA)
                lienzo.blit(limpio, ((medida[0] - limpio.get_width()) // 2, (medida[1] - limpio.get_height()) // 2))
                limpio = lienzo
            conBorde = self.ponerBordeFino(self.suavizarOrilla(limpio), (118, 92, 146), 2)
            margen = (conBorde.get_width() - medida[0]) // 2
            corazon = self.assets.cargarSinFondo(os.path.join("Piano", "corazonLleno.jpg"), 40)
            _SURFACE_CACHE[clave] = (conBorde, escala, margen, corazon)
        self.marcoPost, self.escalaPost, self.margenPost, self.corazonPost = _SURFACE_CACHE[clave]
        self.huecoPost = self.rectLocal(fotoPost)
        self.marcoListo: Optional[pygame.Surface] = None

    def puntoLocal(self, x: float, y: float) -> Tuple[int, int]:
        return (round((x - cajaPost[0]) * self.escalaPost) + self.margenPost,
                round((y - cajaPost[1]) * self.escalaPost) + self.margenPost)

    def rectLocal(self, caja) -> pygame.Rect:
        x, y = self.puntoLocal(caja[0], caja[1])
        return pygame.Rect(x, y, round(caja[2] * self.escalaPost), round(caja[3] * self.escalaPost))

    def cargarSonido(self, ruta: str) -> Optional[pygame.mixer.Sound]:
        if ruta not in _AUDIO_CACHE:
            sonido = None
            if pygame.mixer.get_init() and os.path.exists(ruta):
                try:
                    sonido = pygame.mixer.Sound(ruta)
                except pygame.error:
                    sonido = None
            _AUDIO_CACHE[ruta] = sonido
        return _AUDIO_CACHE[ruta]

    def cargarSonidosPost(self) -> None:
        self.sonidoMalo = self.cargarSonido(os.path.join("assets", "fail.mp3"))
        self.sonidoFoto = self.cargarSonido(os.path.join("assets", "Punch", "foto.mp3"))

    def armarMarco(self) -> pygame.Surface:
        marco = self.marcoPost.copy()
        e = self.escalaPost
        cx, cy, radio = avatarPost
        centro = self.puntoLocal(cx, cy)
        r = round(radio * e)
        anchoPj, altoPj = self.sprite_idle.get_size()
        lado = int(altoPj * 0.56)
        caja = pygame.Rect(anchoPj // 2 - lado // 2, int(altoPj * 0.02), lado, lado).clip(self.sprite_idle.get_rect())
        cara = self.sprite_idle.subsurface(caja).copy()
        cara = pygame.transform.smoothscale(cara, (r * 2, r * 2))
        circulo = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(circulo, (52, 62, 108, 255), (r, r), r)
        circulo.blit(cara, (0, 0))
        recorte = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(recorte, (255, 255, 255, 255), (r, r), r)
        circulo.blit(recorte, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        marco.blit(circulo, (centro[0] - r, centro[1] - r))
        pygame.draw.circle(marco, (60, 50, 56), centro, r, 2)
        barra = self.rectLocal(usuarioPost).inflate(6, 6)
        marco.blit(marco.subsurface(barra.move(round(345 * e), 0)).copy(), barra)
        barraLikes = self.rectLocal(likesPost).inflate(6, 6)
        self.parcheLikes = marco.subsurface(barraLikes.move(round(420 * e), 0)).copy()
        self.barraUsuario = barra
        return marco

    def avance(self, parte: str, duracion: float = 0.5) -> float:
        if parte not in self.partesPost:
            return 0.0
        return suavizar((self.relojPost - self.partesPost[parte]) / duracion)

    def textoDescripcion(self) -> str:
        visibles = []
        for texto, inicio in self.descripcion:
            letras = int(max(0.0, self.relojPost - inicio) * letrasPorSegundo)
            visibles.append(texto[:letras])
        return " ".join(parte for parte in visibles if parte)

    def componerPost(self, likes: Optional[int] = None) -> pygame.Surface:
        if self.marcoListo is None:
            self.marcoListo = self.armarMarco()
        lienzo = self.marcoListo.copy()
        hueco = self.huecoPost
        color = (70, 52, 60)
        if self.fotoEnPost is not None and self.etapa != "foto":
            lienzo.blit(self.fotoEnPost, hueco)
            recuerdo = self.avance("recuerdo", 0.9)
            if recuerdo > 0.0:
                # Foto antigua: tonos sepia y viñeta suave
                self.fotoRecuerdo.set_alpha(int(235 * recuerdo))
                lienzo.blit(self.fotoRecuerdo, hueco)
            filtro = self.avance("filtro", 0.9)
            if filtro > 0.0:
                if recuerdo <= 0.0:  # Con foto antigua se conserva el sepia y solo se suman las lucecitas
                    self.fotoCalida.set_alpha(int(255 * filtro))
                    lienzo.blit(self.fotoCalida, hueco)
                for x, y, fase, imagen in self.lucesFiltro:
                    brillo = filtro * (0.35 + 0.65 * (0.5 + 0.5 * math.sin(self.relojPost * 3.2 + fase)) ** 2)
                    imagen.set_alpha(int(255 * brillo))
                    lienzo.blit(imagen, imagen.get_rect(center=(hueco.x + x * hueco.w, hueco.y + y * hueco.h)))
            nieve = self.avance("nieve", 0.9)
            if nieve > 0.0:
                # Nieve que cae despacio sobre la foto (solo dentro del recuadro)
                capa = pygame.Surface(hueco.size, pygame.SRCALPHA)
                for x, v, fase, r in self.coposNieve:
                    py = ((self.relojPost * v + fase * hueco.h) % (hueco.h + 20)) - 10
                    px = x * hueco.w + math.sin(self.relojPost * 1.4 + fase * 6.0) * 6
                    pygame.draw.circle(capa, (255, 255, 255, int(220 * nieve)), (int(px), int(py)), r)
                lienzo.blit(capa, hueco)
        barra = self.barraUsuario
        cancion = self.avance("cancion")
        letras = self.assets.cargarFuenteCuento(22).render(self.nombreUsuario, True, color)
        lienzo.blit(letras, letras.get_rect(midleft=(barra.x + 2, round(barra.centery - 9 * cancion))))
        if cancion > 0.0:
            nota = self.fuenteNota.render("♪", True, color)
            tema = self.assets.cargarFuenteCuento(15).render(cancionPost, True, color)
            linea = pygame.Surface((nota.get_width() + 4 + tema.get_width(), max(nota.get_height(), tema.get_height())), pygame.SRCALPHA)
            linea.blit(nota, nota.get_rect(midleft=(0, linea.get_height() // 2)))
            linea.blit(tema, tema.get_rect(midleft=(nota.get_width() + 4, linea.get_height() // 2)))
            linea.set_alpha(int(255 * cancion))
            lienzo.blit(linea, linea.get_rect(midleft=(barra.x + 2, round(barra.centery + 12))))
        comentario = self.avance("comentario")
        if comentario > 0.0:
            # Comentario de la abuela: globito sobre la parte baja de la foto
            fuenteC = self.assets.cargarFuenteCuento(15)
            texto = fuenteC.render(comentarioAbuela, True, (70, 52, 60))
            globo = pygame.Surface((texto.get_width() + 22, texto.get_height() + 10), pygame.SRCALPHA)
            pygame.draw.rect(globo, (255, 248, 238, 240), globo.get_rect(), border_radius=globo.get_height() // 2)
            pygame.draw.rect(globo, (118, 92, 146), globo.get_rect(), 2, border_radius=globo.get_height() // 2)
            globo.blit(texto, texto.get_rect(center=globo.get_rect().center))
            globo.set_alpha(int(255 * comentario))
            sube = round(10 * (1.0 - comentario))
            lienzo.blit(globo, globo.get_rect(midbottom=(hueco.centerx, hueco.bottom - 10 + sube)))
        publico = self.avance("publico")
        if publico > 0.0:
            texto = self.assets.cargarFuenteCuento(14).render(publicoPost, True, (255, 255, 255))
            pastilla = pygame.Surface((texto.get_width() + 16, texto.get_height() + 4), pygame.SRCALPHA)
            pygame.draw.rect(pastilla, (118, 92, 146), pastilla.get_rect(), border_radius=pastilla.get_height() // 2)
            pastilla.blit(texto, texto.get_rect(center=pastilla.get_rect().center))
            pastilla.set_alpha(int(255 * publico))
            puntos = self.rectLocal(puntosPost)
            lienzo.blit(pastilla, pastilla.get_rect(midright=(puntos.x - 6, puntos.centery)))
        guardar = self.avance("guardar", 0.35)
        if guardar > 0.0:
            caja = self.rectLocal(guardarPost)
            forma = [caja.topleft, caja.topright, caja.bottomright, (caja.centerx, caja.bottom - caja.h * 0.3), caja.bottomleft]
            relleno = pygame.Surface(lienzo.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(relleno, (*color, int(255 * guardar)), forma)
            lienzo.blit(relleno, (0, 0))
        if likes is not None:
            barraLikes = self.rectLocal(likesPost).inflate(6, 6)
            lienzo.blit(self.parcheLikes, barraLikes)
            cifra = f"{likes:,}".replace(",", ".")
            letras = self.assets.cargarFuenteCuento(20).render(f"{cifra} me gusta", True, color)
            lienzo.blit(letras, letras.get_rect(midleft=(barraLikes.x + 2, barraLikes.centery)))
        descripcion = self.textoDescripcion()
        if descripcion:
            fuente = self.assets.cargarFuenteCuento(16)
            x0, anchoRenglon, ys = renglonesPost
            ancho = round(anchoRenglon * self.escalaPost)
            lineas = partirTexto(descripcion, fuente, ancho)
            if len(lineas) > len(ys):
                lineas = lineas[:len(ys)]
                while lineas[-1] and fuente.size(lineas[-1] + "…")[0] > ancho:
                    lineas[-1] = lineas[-1][:-1]
                lineas[-1] += "…"
            for linea, y in zip(lineas, ys):
                letras = fuente.render(linea, True, color)
                izquierda, base = self.puntoLocal(x0, y)
                lienzo.blit(letras, letras.get_rect(bottomleft=(izquierda, base - 1)))
        hora = self.avance("hora")
        if hora > 0.0:
            letras = self.assets.cargarFuenteCuento(14).render(horaPost, True, (140, 120, 128))
            letras.set_alpha(int(255 * hora))
            izquierda, base = self.puntoLocal(renglonesPost[0], 2016)
            lienzo.blit(letras, letras.get_rect(bottomleft=(izquierda, base)))
        return lienzo

    def capturarFoto(self, surface: pygame.Surface) -> None:
        self.foto = surface.subsurface(pygame.Rect(rectFoto)).copy()
        self.fotoEnPost = pygame.transform.smoothscale(self.foto, self.huecoPost.size)
        self.fotoCalida = self.fotoEnPost.copy()
        self.fotoCalida.fill((255, 232, 200), special_flags=pygame.BLEND_RGB_MULT)
        self.fotoCalida.fill((34, 20, 4), special_flags=pygame.BLEND_RGB_ADD)
        azar = random.Random(11)
        tamanos = (brilloEstrella(19), brilloEstrella(27), brilloEstrella(35))
        self.lucesFiltro = [(azar.uniform(0.05, 0.95), azar.uniform(0.04, 0.6), azar.uniform(0.0, math.tau),
                             azar.choice(tamanos).copy()) for _ in range(22)]
        # Foto antigua (sepia + viñeta) y copos para el filtro de nieve
        gris = pygame.transform.grayscale(self.fotoEnPost)
        gris.fill((255, 226, 178), special_flags=pygame.BLEND_RGB_MULT)
        gris.fill((28, 16, 4), special_flags=pygame.BLEND_RGB_ADD)
        w, h = gris.get_size()
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        oscuro = np.clip(1.0 - 0.45 * np.clip(d - 0.55, 0.0, 1.0) / 0.6, 0.55, 1.0)
        arr = pygame.surfarray.pixels3d(gris)
        arr[:] = (arr * oscuro.T[..., None]).astype(np.uint8)
        del arr
        self.fotoRecuerdo = gris
        self.coposNieve = [(azar.uniform(0.0, 1.0), azar.uniform(18.0, 42.0), azar.uniform(0.0, 1.0),
                            azar.choice((2, 2, 3, 3, 4))) for _ in range(70)]
        if self.sonidoFoto is not None:
            self._play_sfx(self.sonidoFoto)
        elif hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def mandarAlPost(self, notif: dict) -> None:
        self.vuelos.append({"idea": notif["idea"], "desde": (notif["x"], notif["y"]), "t": 0.0})

    def llegarAlPost(self, idea: dict) -> None:
        destino = destinoIdea[idea["codigo"]]
        self.textosPost.append(idea["texto"])
        if destino == "descripcion":
            inicio = self.relojPost
            if self.descripcion:
                anterior, desde = self.descripcion[-1]
                inicio = max(inicio, desde + len(anterior) / letrasPorSegundo)
            self.descripcion.append((textosDescripcion[idea["codigo"]], inicio))
        else:
            self.partesPost[destino] = self.relojPost
        if destino == "cancion":
            self.ponerVillancico()
        if idea["riesgosa"]:
            self.riesgosPublicados.append(idea["codigo"])
            self._play_sfx(self.sonidoMalo)

    def puntoHueco(self, pos: Tuple[float, float]) -> Tuple[float, float]:
        return (esquinaPost[0] - self.margenPost + self.huecoPost.x + pos[0] * self.huecoPost.w,
                esquinaPost[1] - self.margenPost + self.huecoPost.y + pos[1] * self.huecoPost.h)

    def puntoPantalla(self, x: float, y: float) -> Tuple[float, float]:
        lx, ly = self.puntoLocal(x, y)
        return (esquinaPost[0] - self.margenPost + lx, esquinaPost[1] - self.margenPost + ly)

    def destinoVuelo(self, idea: dict) -> Tuple[float, float]:
        destino = destinoIdea[idea["codigo"]]
        if destino in ("filtro", "nieve", "recuerdo"):
            return self.puntoHueco((0.5, 0.5))
        if destino == "comentario":
            return self.puntoHueco((0.5, 0.92))
        if destino == "cancion":
            return self.puntoPantalla(usuarioPost[0] + 160, 430)
        if destino == "publico":
            return self.puntoPantalla(puntosPost[0] - 120, puntosPost[1] + 6)
        if destino == "guardar":
            return self.puntoPantalla(guardarPost[0] + 30, guardarPost[1] + 36)
        if destino == "hora":
            return self.puntoPantalla(renglonesPost[0] + 260, 2005)
        return self.puntoPantalla(renglonesPost[0] + renglonesPost[1] / 2, renglonesPost[2][1])

    def actualizarPost(self, dt: float) -> None:
        self.relojPost += dt
        for vuelo in list(self.vuelos):
            vuelo["t"] += dt
            if vuelo["t"] >= 0.6:
                self.vuelos.remove(vuelo)
                self.llegarAlPost(vuelo["idea"])
        if self.etapa == "publicar":
            for corazon in list(self.corazones):
                corazon["t"] += dt
                if corazon["t"] > 1.4:
                    self.corazones.remove(corazon)
            if 0.9 <= self.tEtapa <= duracionPublicar - 0.4:
                self.esperaCorazon -= dt
                if self.esperaCorazon <= 0.0:
                    self.esperaCorazon = 0.17
                    self.corazones.append({"t": 0.0, "dx": random.uniform(-110.0, 110.0), "giro": random.uniform(-25.0, 25.0),
                                           "fase": random.uniform(0.0, math.tau)})

    def empezarPublicacion(self, gano: bool) -> None:
        if self.etapa == "publicar" or self.is_finished:
            return
        self.etapa = "publicar"
        self.tEtapa = 0.0
        self.ganoPublicacion = gano
        self.tiempoCongelado = max(self.time_left, 0.001)
        self.popups.clear()
        self.spark_particles.clear()
        self.shockwaves.clear()
        self.is_punching = False
        self.corazones: List[dict] = []
        self.esperaCorazon = 0.0
        for notif in self.wave_queue:
            if notif["spawned"] and notif["state"] == "falling":
                notif["state"] = "done"
        self.likesMeta = 180 + 140 * len(self.textosPost) + 650 * len(self.riesgosPublicados) + random.randint(0, 90)

    def dibujarPublicacion(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        if self.etapa == "foto":
            aparece = suavizar((self.tEtapa - 0.5 * self.fotoDuracion) / (0.3 * self.fotoDuracion))
            if aparece <= 0.0:
                return
        else:
            aparece = 1.0
        if self.etapa == "publicar":
            return
        post = self.componerPost()
        if aparece < 1.0:
            post.set_alpha(int(255 * aparece))
        surface.blit(post, (esquinaPost[0] - self.margenPost + ox, esquinaPost[1] - self.margenPost + oy))

    def dibujarVuelos(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        lado = round(self.huecoPost.w * 0.22)
        for vuelo in self.vuelos:
            p = suavizar(vuelo["t"] / 0.6)
            tarjeta = vuelo["idea"]["sprite"]
            destino = self.destinoVuelo(vuelo["idea"])
            desde = (vuelo["desde"][0] + tarjeta.get_width() / 2, vuelo["desde"][1] + tarjeta.get_height() / 2)
            centro = (desde[0] + (destino[0] - desde[0]) * p, desde[1] + (destino[1] - desde[1]) * p - math.sin(p * math.pi) * 120)
            escala = 1.0 + (lado / float(tarjeta.get_width()) - 1.0) * p
            imagen = pygame.transform.rotozoom(tarjeta, 0.0, escala)
            imagen.set_alpha(int(255 * (1.0 - suavizar((p - 0.65) / 0.35))))
            surface.blit(imagen, imagen.get_rect(center=(round(centro[0]) + ox, round(centro[1]) + oy)))

    def dibujarFoto(self, surface: pygame.Surface) -> None:
        if self.etapa != "foto" or self.foto is None:
            return
        t = self.tEtapa
        mostrar = 0.55 * self.fotoDuracion
        volar = 0.9 * self.fotoDuracion
        vuelo = suavizar((t - mostrar) / (volar - mostrar))
        velo = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        velo.fill((10, 8, 20, int(150 * (1.0 - vuelo))))
        surface.blit(velo, (0, 0))
        if t < volar:
            entrada = min(1.0, t / 0.35)
            rebote = 1.0 + 2.7 * (entrada - 1.0) ** 3 + 1.7 * (entrada - 1.0) ** 2
            centroVista = (self.screen_w / 2, self.screen_h / 2 - 30)
            destino = self.puntoHueco((0.5, 0.5))
            lado = ladoFotoVista * (0.8 + 0.2 * rebote) + (self.huecoPost.w - ladoFotoVista) * vuelo
            centro = (centroVista[0] + (destino[0] - centroVista[0]) * vuelo,
                      centroVista[1] + (destino[1] - centroVista[1]) * vuelo)
            margen = 16 * (1.0 - vuelo)
            foto = pygame.transform.smoothscale(self.foto, (max(1, round(lado)), max(1, round(lado))))
            marco = pygame.Surface((foto.get_width() + round(margen) * 2, foto.get_height() + round(margen) * 2), pygame.SRCALPHA)
            marco.fill((252, 248, 240, 255))
            marco.blit(foto, (round(margen), round(margen)))
            pygame.draw.rect(marco, (60, 50, 70), marco.get_rect(), 2)
            girada = pygame.transform.rotozoom(marco, -3.0 * (1.0 - vuelo), 1.0)
            surface.blit(girada, girada.get_rect(center=(round(centro[0]), round(centro[1]))))
        destello = max(0.0, 1.0 - t / 0.45)
        if destello > 0.0:
            flash = pygame.Surface((self.screen_w, self.screen_h))
            flash.fill((255, 255, 255))
            flash.set_alpha(int(255 * destello))
            surface.blit(flash, (0, 0))

    def dibujarPublicando(self, surface: pygame.Surface) -> None:
        if self.etapa != "publicar":
            return
        p = suavizar(self.tEtapa / 0.9)
        velo = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        velo.fill((10, 8, 20, int(165 * p)))
        surface.blit(velo, (0, 0))
        cuenta = suavizar((self.tEtapa - 0.9) / 1.6)
        post = self.componerPost(int(self.likesMeta * cuenta) if self.tEtapa >= 0.9 else None)
        escala = 1.0 + 0.3 * p
        medida = (round(post.get_width() * escala), round(post.get_height() * escala))
        post = pygame.transform.smoothscale(post, medida)
        inicio = (esquinaPost[0] - self.margenPost + self.marcoPost.get_width() / 2,
                  esquinaPost[1] - self.margenPost + self.marcoPost.get_height() / 2)
        destino = (self.screen_w / 2, self.screen_h / 2 - 20)
        centro = (inicio[0] + (destino[0] - inicio[0]) * p, inicio[1] + (destino[1] - inicio[1]) * p)
        caja = post.get_rect(center=(round(centro[0]), round(centro[1])))
        surface.blit(post, caja)
        corazonX, corazonY = self.puntoLocal(430, 1640)
        icono = (caja.x + corazonX * escala, caja.y + corazonY * escala)
        if self.is_finished:
            return
        for corazon in self.corazones:
            vida = corazon["t"] / 1.4
            imagen = pygame.transform.rotozoom(self.corazonPost, corazon["giro"], 0.6 + 0.5 * vida)
            imagen.set_alpha(int(255 * (1.0 - vida) ** 0.7))
            vaiven = math.sin(corazon["t"] * 6.0 + corazon["fase"]) * 14.0
            surface.blit(imagen, imagen.get_rect(center=(round(icono[0] + corazon["dx"] * vida + vaiven),
                                                         round(icono[1] - 280 * vida))))

    def armarEnsenanza(self, gano: bool) -> List[str]:
        graves = [codigo for codigo in ordenGravedad if codigo in self.riesgosPublicados][:2]
        if graves:
            return [ensenanzasRiesgo[codigo] for codigo in graves] + [cierreEnsenanza]
        return list(ensenanzaSegura) if gano else list(ensenanzaVacia)

    def finish_game(self, won: bool) -> None:
        yaTerminado = self.is_finished
        if not yaTerminado:
            self.lineasEnsenanza = self.armarEnsenanza(won)
            self.repaso = [(notif["idea"], notif["resultado"]) for notif in self.wave_queue if notif.get("resultado")]
        super().finish_game(won)
        if yaTerminado:
            return
        if getattr(self, "finLetrero", None):
            lectura = 3.0 + (5.5 if self.repaso else 0.0)
            self.outro_duration = max(self.outro_duration, self.finLetrero + self.horarioFinal()[-1] + lectura)

    def lineasFinales(self) -> List[Tuple[str, bool]]:
        if getattr(self, "fuenteFinal", None) is None:
            self.fuenteFinal = self.assets.cargarFuenteCuento(52 if getattr(self, "repaso", None) else 60)
        clave = tuple(self.lineasEnsenanza)
        if getattr(self, "claveFinal", None) != clave:
            self.claveFinal = clave
            self.lineasPartidas = []
            for i, frase in enumerate(self.lineasEnsenanza):
                dorada = i == len(self.lineasEnsenanza) - 1
                partes = partirTexto(frase, self.fuenteFinal, 1500)
                if len(partes) > 1 and ". " in frase:
                    corte = frase.index(". ") + 1
                    oraciones = [frase[:corte], frase[corte + 1:]]
                    if all(self.fuenteFinal.size(o)[0] <= 1500 for o in oraciones):
                        partes = oraciones
                for linea in partes:
                    self.lineasPartidas.append((linea, dorada))
        return self.lineasPartidas

    def horarioFinal(self) -> List[float]:
        horario, momento = [], 0.5
        lineas = self.lineasFinales()
        for i, (linea, dorada) in enumerate(lineas):
            if dorada and i > 0 and not lineas[i - 1][1]:
                momento += 0.5
            horario.append(momento)
            momento += len(linea) / 24.0 + 0.45
        horario.append(momento)
        return horario

    def dibujarEnsenanzaFinal(self, surface: pygame.Surface) -> None:
        inicio = getattr(self, "finLetrero", None)
        if not inicio or self.outro_timer < inicio or not self.lineasEnsenanza:
            return
        t = self.outro_timer - inicio
        if not getattr(self, "musicaApagada", False):
            self.musicaApagada = True
            self.audio.fadeout_music(700)
        lineas = self.lineasFinales()
        horario = self.horarioFinal()
        if hasattr(self.audio, "sonarEscritura"):
            self.audio.sonarEscritura(any(horario[i] <= t < horario[i] + len(linea) / 24.0
                                          for i, (linea, _) in enumerate(lineas)))
        if t < 0.3 and int(t * 20) % 2 == 0:
            return
        surface.fill((8, 6, 12))
        repaso = getattr(self, "repaso", None)
        alto = self.fuenteFinal.get_linesize() + (14 if repaso else 20)
        separacion = (36 if repaso else 50) if any(d for _, d in lineas) and not all(d for _, d in lineas) else 0
        altoTexto = alto * len(lineas) + separacion
        if repaso:
            columnas = self.armarRepaso()
            filas = max(len(filasColumna) for _, filasColumna in columnas)
            altoRepaso = 60 + filas * 58
            y = (self.screen_h - (altoTexto + 70 + altoRepaso)) // 2
        else:
            y = self.screen_h // 2 - altoTexto // 2
        for i, (linea, dorada) in enumerate(lineas):
            if dorada and i > 0 and not lineas[i - 1][1]:
                y += separacion
            letras = min(len(linea), int(max(0.0, t - horario[i]) * 24))
            if letras > 0:
                color = (255, 214, 120) if dorada else (255, 247, 230)
                texto = self.textoConBorde(self.fuenteFinal, linea[:letras], color, (60, 50, 70), 3)
                izquierda = self.screen_w // 2 - self.fuenteFinal.size(linea)[0] // 2
                surface.blit(texto, texto.get_rect(midleft=(izquierda, y + alto // 2)))
            y += alto
        if repaso:
            self.dibujarRepaso(surface, t - horario[-1], y + 70)
        fin = self.outro_duration - self.outro_timer
        if fin < 0.35:
            surface.fill([int(255 * max(0.0, fin) / 0.35)] * 3, special_flags=pygame.BLEND_RGB_MULT)

    def armarRepaso(self) -> List[Tuple[pygame.Surface, List[pygame.Surface]]]:
        if getattr(self, "columnasRepaso", None) is not None:
            return self.columnasRepaso
        rutaTitulos = os.path.join("assets", "Titulos.ttf")
        fuenteTitulo = pygame.font.Font(rutaTitulos, 40) if os.path.exists(rutaTitulos) else self.assets.cargarFuenteCuento(40)
        fuente = self.assets.cargarFuenteCuento(30)
        fuenteMarca = self.assets.cargarFuenteCuento(24)
        self.columnasRepaso = []
        for titulo, riesgosas, colorTitulo in ((tituloBuenas, False, colorAcierto), (tituloMalas, True, colorError)):
            pares = [par for par in self.repaso if par[0]["riesgosa"] == riesgosas]
            if not pares:
                continue
            filas = []
            for idea, resultado in pares:
                icono = pygame.transform.smoothscale_by(idea["icono"], 46.0 / idea["icono"].get_height())
                texto = self.textoConBorde(fuente, idea["texto"], (255, 247, 230), (40, 30, 46), 2)
                marca = None
                if resultado == ("publicada" if riesgosas else "borrada"):
                    marca = self.textoConBorde(fuenteMarca, marcaPublicada if riesgosas else marcaBorrada,
                                               colorPost, (40, 30, 46), 2)
                ancho = icono.get_width() + 16 + texto.get_width() + (12 + marca.get_width() if marca else 0)
                fila = pygame.Surface((ancho, 54), pygame.SRCALPHA)
                fila.blit(icono, icono.get_rect(midleft=(0, 27)))
                fila.blit(texto, texto.get_rect(midleft=(icono.get_width() + 16, 27)))
                if marca:
                    fila.blit(marca, marca.get_rect(midleft=(icono.get_width() + 28 + texto.get_width(), 29)))
                filas.append(fila)
            self.columnasRepaso.append((self.textoConBorde(fuenteTitulo, titulo, colorTitulo, (40, 30, 46), 3), filas))
        return self.columnasRepaso

    def dibujarRepaso(self, surface: pygame.Surface, t: float, arriba: int) -> None:
        if t <= 0.0:
            return
        columnas = self.armarRepaso()
        anchos = [max([titulo.get_width()] + [fila.get_width() for fila in filas]) for titulo, filas in columnas]
        espacio = 140
        izquierda = (self.screen_w - (sum(anchos) + espacio * (len(anchos) - 1))) // 2
        orden = 0
        for (titulo, filas), ancho in zip(columnas, anchos):
            aparece = suavizar((t - 0.2) / 0.4)
            if aparece > 0.0:
                titulo.set_alpha(int(255 * aparece))
                surface.blit(titulo, titulo.get_rect(bottomleft=(izquierda, arriba + 52)))
            y = arriba + 60
            for fila in filas:
                orden += 1
                aparece = suavizar((t - 0.35 - 0.12 * orden) / 0.4)
                if aparece > 0.0:
                    fila.set_alpha(int(255 * aparece))
                    surface.blit(fila, (izquierda, y))
                y += 58
            izquierda += ancho + espacio

    def _load_optional_ui(self, filename: str, target_h: int) -> Optional[pygame.Surface]:
        """Carga un elemento de UI opcional manteniendo su relación de aspecto."""
        cache_key = ("optional_ui", filename, target_h)
        if cache_key in _SURFACE_CACHE:
            return _SURFACE_CACHE[cache_key]
        try:
            raw = self.assets.load_surface(filename)
            bbox = raw.get_bounding_rect(min_alpha=15)
            cropped = raw.subsurface(bbox).copy() if (bbox.width > 0 and bbox.height > 0) else raw
            w, h = cropped.get_size()
            scale = target_h / float(max(1, h))
            res = pygame.transform.smoothscale(cropped, (int(w * scale), target_h))
            _SURFACE_CACHE[cache_key] = res
            return res
        except Exception:
            return None

    def _resolve_audio_file(self, filename: str) -> Optional[str]:
        """Busca un archivo de audio en assets/ tolerando diferencias de codificación UTF-8/ANSI en la ñ."""
        base_dir = "assets"
        direct = os.path.join(base_dir, filename)
        if os.path.exists(direct):
            return direct

        # Búsqueda flexible por prefijo (ej: 'char_audio_0_')
        prefix = "_".join(filename.split("_")[:3])
        if os.path.isdir(base_dir):
            for f in os.listdir(base_dir):
                if f.lower().startswith(prefix.lower()) and f.lower().endswith(".ogg"):
                    return os.path.join(base_dir, f)
        return None

    def _load_character_punch_voices(self) -> None:
        """
        Carga (o reutiliza desde caché) las líneas de voz del personaje seleccionado al pegarle a una notificación.
        """
        self.punch_voices: List[pygame.mixer.Sound] = []
        self.last_voice_idx: int = -1

        mixer_cfg = pygame.mixer.get_init()
        if not mixer_cfg:
            return

        sfx_vol = getattr(self.audio, "sfx_volume", 0.85)
        cache_key = ("punch_voices", self.character_id, mixer_cfg)
        cached_voices = _AUDIO_CACHE.get(cache_key)
        if cached_voices is not None:
            for snd in cached_voices:
                snd.set_volume(sfx_vol)
            self.punch_voices = list(cached_voices)
            return

        target_files = self.CHARACTER_PUNCH_VOICES.get(
            self.character_id,
            self.CHARACTER_PUNCH_VOICES["char"]
        )

        # Intentar cargar las voces propias del personaje actual
        for fname in target_files:
            resolved = self._resolve_audio_file(fname)
            if resolved:
                try:
                    snd = pygame.mixer.Sound(resolved)
                    snd.set_volume(sfx_vol)
                    self.punch_voices.append(snd)
                except Exception:
                    pass

        # Fallback a las voces de 'char' con modulación tímbrica por personaje si no tiene audios grabados propios
        if not self.punch_voices:
            pitch_profiles = {
                "valdiri": 1.32,    # Agudo y enérgico
                "katherine": 1.22,  # Tono femenino claro y dinámico
                "westcol": 0.94,    # Tono ligeramente más grave y raspado
                "char": 1.0,        # Tono nativo
            }
            pitch_shift = pitch_profiles.get(self.character_id, 1.0)

            for fname in self.CHARACTER_PUNCH_VOICES["char"]:
                resolved = self._resolve_audio_file(fname)
                if resolved:
                    try:
                        snd = pygame.mixer.Sound(resolved)
                        if abs(pitch_shift - 1.0) > 0.02 and hasattr(self.audio, "get_pitched_sound"):
                            snd = self.audio.get_pitched_sound(snd, pitch_shift)
                        snd.set_volume(sfx_vol)
                        self.punch_voices.append(snd)
                    except Exception:
                        pass

        if self.punch_voices:
            _AUDIO_CACHE[cache_key] = list(self.punch_voices)

    def _play_character_punch_voice(self) -> None:
        """Reproduce una voz aleatoria del personaje al conectar el golpe (evitando repetir la misma seguida)."""
        if not self.punch_voices:
            return
        if hasattr(self.audio, "sound_enabled") and not self.audio.sound_enabled:
            return

        if len(self.punch_voices) > 1:
            candidates = [i for i in range(len(self.punch_voices)) if i != self.last_voice_idx]
            idx = random.choice(candidates)
        else:
            idx = 0

        self.last_voice_idx = idx
        snd = self.punch_voices[idx]
        if hasattr(self.audio, "play_sfx"):
            self.audio.play_sfx(snd)
        else:
            vol = getattr(self.audio, "sfx_volume", 0.85)
            snd.set_volume(vol)
            snd.play()

    def _init_punch_sounds(self) -> None:
        """Genera (o reutiliza desde caché) los efectos de sonido procedurales de soporte."""
        self.snd_hit: Optional[pygame.mixer.Sound] = None
        self.snd_whiff: Optional[pygame.mixer.Sound] = None
        self.snd_safe: Optional[pygame.mixer.Sound] = None
        self.snd_strike: Optional[pygame.mixer.Sound] = None

        mixer_cfg = pygame.mixer.get_init()
        if not mixer_cfg:
            return

        cache_key = ("punch_sfx", mixer_cfg)
        cached_sfx = _AUDIO_CACHE.get(cache_key)
        if cached_sfx is not None:
            self.snd_hit, self.snd_whiff, self.snd_safe, self.snd_strike = cached_sfx
            return

        try:
            sr = 44100
            # 1. Hit Sound (¡CRACK! de bateo seco + armónico ascendente)
            dur_hit = 0.14
            t_hit = np.linspace(0, dur_hit, int(sr * dur_hit), False)
            noise = np.random.uniform(-1.0, 1.0, len(t_hit)) * np.exp(-t_hit * 45.0)
            tone = np.sin(2 * np.pi * np.geomspace(220, 680, len(t_hit)) * t_hit) * np.exp(-t_hit * 18.0)
            wave_hit = np.clip((noise * 0.55 + tone * 0.65) * 0.85, -1.0, 1.0)
            arr_hit = (wave_hit * 32767).astype(np.int16)
            self.snd_hit = pygame.sndarray.make_sound(np.column_stack((arr_hit, arr_hit)))

            # 2. Whiff / Swing Sound (Swoosh corto al lanzar el guante)
            dur_whiff = 0.08
            t_w = np.linspace(0, dur_whiff, int(sr * dur_whiff), False)
            freq_w = np.geomspace(340, 140, len(t_w))
            wave_w = np.clip(np.sin(2 * np.pi * freq_w * t_w) * np.sin(np.pi * t_w / dur_whiff) * 0.78, -1.0, 1.0)
            arr_w = (wave_w * 32767).astype(np.int16)
            self.snd_whiff = pygame.sndarray.make_sound(np.column_stack((arr_w, arr_w)))

            # 3. Safe Saved Sound (Doble campana cálida cuando entra una notificación prioritaria)
            dur_safe = 0.18
            t_s = np.linspace(0, dur_safe, int(sr * dur_safe), False)
            freq_s = np.where(t_s < dur_safe * 0.5, 587.33, 880.0)
            env_s = np.exp(-t_s * 12.0)
            wave_s = np.clip(np.sin(2 * np.pi * freq_s * t_s) * env_s * 0.82, -1.0, 1.0)
            arr_s = (wave_s * 32767).astype(np.int16)
            self.snd_safe = pygame.sndarray.make_sound(np.column_stack((arr_s, arr_s)))

            # 4. Strike Buzz (Zumbido doble de vibración de celular / error)
            dur_st = 0.24
            t_st = np.linspace(0, dur_st, int(sr * dur_st), False)
            buzz = np.sign(np.sin(2 * np.pi * 115.0 * t_st)) * 0.5 + np.sin(2 * np.pi * 170.0 * t_st) * 0.5
            env_st = np.where((t_st < 0.10) | (t_st > 0.13), 1.0, 0.1) * np.exp(-t_st * 4.0)
            wave_st = np.clip(buzz * env_st * 0.82, -1.0, 1.0)
            arr_st = (wave_st * 32767).astype(np.int16)
            self.snd_strike = pygame.sndarray.make_sound(np.column_stack((arr_st, arr_st)))

            _AUDIO_CACHE[cache_key] = (self.snd_hit, self.snd_whiff, self.snd_safe, self.snd_strike)
        except Exception:
            pass

    def _play_sfx(self, snd: Optional[pygame.mixer.Sound]) -> None:
        if snd is None:
            return
        if hasattr(self.audio, "play_sfx"):
            self.audio.play_sfx(snd)
            return
        if hasattr(self.audio, "sound_enabled") and not self.audio.sound_enabled:
            return
        vol = getattr(self.audio, "sfx_volume", 0.8)
        snd.set_volume(vol)
        snd.play()

    def setup_game(self) -> None:
        self.camera_input = CameraGestureInput.get_instance()
        if (
            os.environ.get("SDL_VIDEODRIVER") != "dummy"
            and self.camera_input.available
            and not self.camera_input.enabled
            and not self.camera_input.suspended
        ):
            self.camera_input.keep_alive(retry_interval=2.0)
        """Carga recursos oficiales, configura el reloj HUD, voces del personaje y la oleada."""
        self.assets = AssetManager.get_instance()
        try:
            self.spr_fist_hint = self.assets.cargarSinFondo(os.path.join("Interfaz", "mano_puno.png"), 108)
        except Exception:
            self.spr_fist_hint = None
        self._init_punch_sounds()
        self._load_character_punch_voices()

        # 1. Cargar fondo oficial provisto
        bg_key = ("bg", self.screen_w, self.screen_h)
        cached_bg = _SURFACE_CACHE.get(bg_key)
        if cached_bg is not None:
            self.bg_surface = cached_bg
        else:
            raw_bg = self.assets.load_surface(os.path.join("Punch", "fondo_punch.png"), has_alpha=False)
            if raw_bg:
                self.bg_surface = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))
                _SURFACE_CACHE[bg_key] = self.bg_surface
            else:
                self.bg_surface = pygame.Surface((self.screen_w, self.screen_h))
                self.bg_surface.fill((25, 25, 35))

        self.cargarArbolito()
        self.cargarCielo()

        # 2. Cargar contador gráfico oficial (igual que en UninorteSprint / Crossy Road)
        self.spr_counter = self._load_optional_ui("contador_microjuegos.png", target_h=96)

        # 3. Notificaciones con límites exactos del nuevo sheet (4 Filas x 4 Columnas)
        target_card_w = 430
        target_card_h = 223
        self.cargarTarjetas(target_card_w, target_card_h)
        self.cargarPublicacion()
        self.cargarSonidosPost()

        # 4. Personaje Boxeador con separación dinámica por valle de transparencia
        char_render_h = 540
        box_key = ("box_char", self.character_id, char_render_h)
        cached_box = _SURFACE_CACHE.get(box_key)
        if cached_box is not None:
            self.sprite_idle, self.sprite_punch = cached_box
        else:
            char_sheet_name = f"{self.character_id}_sprite_box_microjuego.png"
            try:
                box_sheet = self.assets.load_surface(char_sheet_name)
            except Exception:
                box_sheet = self.assets.load_surface("char_sprite_box_microjuego.png")

            if box_sheet:
                bw, bh = box_sheet.get_size()
                mask_arr = pygame.surfarray.array_alpha(box_sheet)
                x_start = int(bw * 0.40)
                x_end = int(bw * 0.53)
                col_sums = (mask_arr[x_start:x_end, :] > 20).sum(axis=1)
                zero_offsets = np.flatnonzero(col_sums == 0)
                if zero_offsets.size > 0:
                    split_x = int(x_start + zero_offsets[len(zero_offsets) // 2])
                else:
                    split_x = int(x_start + np.argmin(col_sums))

                idle_rect = pygame.Rect(0, 0, split_x, bh)
                punch_rect = pygame.Rect(split_x, 0, bw - split_x, bh)

                idle_tight = self._extract_tight_surface(box_sheet, idle_rect)
                punch_tight = self._extract_tight_surface(box_sheet, punch_rect)

                scale_idle = char_render_h / float(idle_tight.get_height())
                idle_w = int(idle_tight.get_width() * scale_idle)
                self.sprite_idle = pygame.transform.smoothscale(idle_tight, (idle_w, char_render_h))

                scale_punch = char_render_h / float(punch_tight.get_height())
                punch_w = int(punch_tight.get_width() * scale_punch)
                self.sprite_punch = pygame.transform.smoothscale(punch_tight, (punch_w, char_render_h))
                _SURFACE_CACHE[box_key] = (self.sprite_idle, self.sprite_punch)
            else:
                self.sprite_idle = pygame.Surface((400, char_render_h), pygame.SRCALPHA)
                self.sprite_idle.fill((60, 60, 160, 200))
                self.sprite_punch = pygame.Surface((440, char_render_h), pygame.SRCALPHA)
                self.sprite_punch.fill((220, 60, 60, 200))

        # 5. HUD Completo de Strikes (ui_strike_microjuegos.png con los 3 círculos vacíos)
        hud_bar_h = 115
        hud_key = ("strike_hud", hud_bar_h)
        cached_hud = _SURFACE_CACHE.get(hud_key)
        if cached_hud is not None:
            self.hud_bar_w, self.hud_bar_h, self.strike_hud_base = cached_hud
        else:
            strike_sheet = self.assets.load_surface("ui_strike_microjuegos.png")
            if strike_sheet:
                tight_bar = self._extract_tight_surface(strike_sheet, pygame.Rect(0, 0, strike_sheet.get_width(), strike_sheet.get_height()))
                aspect = float(tight_bar.get_width()) / float(tight_bar.get_height())
                self.hud_bar_w = int(hud_bar_h * aspect)
                self.hud_bar_h = hud_bar_h
                self.strike_hud_base = pygame.transform.smoothscale(tight_bar, (self.hud_bar_w, self.hud_bar_h))
                _SURFACE_CACHE[hud_key] = (self.hud_bar_w, self.hud_bar_h, self.strike_hud_base)
            else:
                self.hud_bar_w = 400
                self.hud_bar_h = hud_bar_h
                self.strike_hud_base = pygame.Surface((self.hud_bar_w, self.hud_bar_h), pygame.SRCALPHA)
                self.strike_hud_base.fill((160, 40, 40, 200))

        self.circle_rel_positions = [
            (0.510, 0.500),
            (0.676, 0.500),
            (0.849, 0.500)
        ]

        # 6. Geometría y Zona de Bateo Estricta ("Sweet Spot" Encajado en la Caja)
        self.lane_center_x = self.screen_w // 2
        self.char_base_y = self.screen_h - 35
        self.char_idle_pos = (
            self.lane_center_x - (self.sprite_idle.get_width() // 2),
            self.char_base_y - self.sprite_idle.get_height()
        )
        self.char_punch_pos = (
            self.lane_center_x - (self.sprite_punch.get_width() // 2),
            self.char_base_y - self.sprite_punch.get_height()
        )

        # El Sweet Spot exige que el centro de la tarjeta esté verdaderamente encajado en la caja (220px de alto)
        self.sweet_spot_center_y = self.screen_h - 430  # Y = 650
        self.hit_zone_y_min = self.sweet_spot_center_y - 95   # Y = 555 (debe haber entrado bien a la caja)
        self.hit_zone_y_max = self.sweet_spot_center_y + 95   # Y = 745 (antes de salirse por debajo)

        # 7. Estado del jugador, Anti-Spam (Castigo al Whiff) y Combo
        self.is_punching: bool = False
        self._camera_resume_grace: float = 0.25
        self.punch_timer: float = 0.0
        self.punch_duration: float = 0.22
        self.punch_cooldown: float = 0.28
        self.whiff_penalty_cooldown: float = 0.65  # Castigo de bloqueo si spameas ESPACIO al aire
        self.is_whiff_penalized: bool = False
        self.whiff_streak: int = 0
        self.cooldown_timer: float = 0.0
        self.pulse_clock: float = 0.0
        self.combo_streak: int = 0

        # 8. Reglas de Victoria / Derrota (Oleada Extendida de 11 Notificaciones en 15s)
        self.strikes: int = 0
        self.max_strikes: int = 3
        self.processed_count: int = 0

        # 9. Diseño de Curva de Pacing de la Oleada
        self.etapa = "foto"
        self.tEtapa = 0.0
        self.fotoDuracion = min(2.4, self.time_limit * 0.18)
        self.foto: Optional[pygame.Surface] = None
        self.fotoEnPost: Optional[pygame.Surface] = None
        self.partesPost: Dict[str, float] = {}
        self.descripcion: List[Tuple[str, float]] = []
        self.relojPost = 0.0
        self.textosPost: List[str] = []
        from core.settings import CHARACTER_DISPLAY_NAMES
        self.nombreUsuario = CHARACTER_DISPLAY_NAMES.get(self.character_id, self.character_id).lower().replace(" ", "")
        self.fuenteNota = pygame.font.SysFont("segoeuisymbol,seguisym,dejavusans,arial", 16)
        self.riesgosPublicados: List[str] = []
        self.vuelos: List[dict] = []
        self.ganoPublicacion = True
        self.tiempoCongelado = 0.0
        self.lineasEnsenanza: List[str] = []
        self.sonoFlash = False

        self.wave_queue: List[dict] = []
        inicio = self.fotoDuracion + 0.35
        fin = max(inicio, self.time_limit - 3.3)
        cantidad = max(1, min(10, int((fin - inicio) / separacionTarjetas) + 1))
        separacion = (fin - inicio) / max(1, cantidad - 1)
        riesgosas = [idea for idea in self.ideas if idea["riesgosa"]]
        seguras = [idea for idea in self.ideas if not idea["riesgosa"]]
        random.shuffle(riesgosas)
        random.shuffle(seguras)
        # El villancico siempre aparece (se pone de último en la pila para salir en la primera tarjeta segura)
        seguras.sort(key=lambda idea: idea["codigo"] == "villancico")
        cuantasRiesgosas = max(1, round(cantidad * 0.6))
        tipos = [True] + random.sample([True] * (cuantasRiesgosas - 1) + [False] * (cantidad - cuantasRiesgosas), cantidad - 1)
        wave_blueprint = []
        for i, riesgosa in enumerate(tipos):
            idea = riesgosas.pop() if riesgosa and riesgosas else seguras.pop()
            rapidez = velocidadCaida[0] + (velocidadCaida[1] - velocidadCaida[0]) * i / max(1, cantidad - 1)
            wave_blueprint.append((idea, inicio + i * separacion, rapidez))
        self.total_wave_count: int = len(wave_blueprint)

        for idea, sp_time, sp_speed in wave_blueprint:
            is_safe = not idea["riesgosa"]
            sprite = idea["sprite"]
            self.wave_queue.append({
                "idea": idea,
                "spawn_time": sp_time,
                "spawned": False,
                "is_safe": is_safe,
                "sprite": sprite,
                "x": float(self.lane_center_x - (target_card_w // 2)),
                "y": -float(target_card_h) - 40.0,
                "w": target_card_w,
                "h": target_card_h,
                "speed": sp_speed,
                "state": "falling",
                "in_sweet_spot": False,
                "fly_vx": 0.0,
                "fly_vy": 0.0,
                "fly_rot": 0.0,
                "fly_rot_speed": 0.0,
                "alpha": 255.0
            })

        # 10. Game Feel Polish (Trauma System, Hit-stop, Partículas, Anillos de Onda)
        self.trauma: float = 0.0
        self.max_shake_offset: float = 28.0
        self.hit_stop_timer: float = 0.0
        self.spark_particles: List[dict] = []
        self.shockwaves: List[dict] = []
        self.popups: List[dict] = []
        self.strike_flash_alpha: float = 0.0

        # Tipografías
        rutaTitulos = os.path.join("assets", "Titulos.ttf")
        if os.path.exists(rutaTitulos):
            self.font_juice = pygame.font.Font(rutaTitulos, 60)
            self.font_prompt = pygame.font.Font(rutaTitulos, 38)
        else:
            self.font_juice = pygame.font.SysFont("Impact, Arial Black, sans-serif", 58)
            self.font_prompt = pygame.font.SysFont("Impact, Arial Black, sans-serif", 34)
        self.font_strike_x = pygame.font.SysFont("Impact, Arial Black, sans-serif", 46)
        self.font_timer = pygame.font.SysFont("Arial Black, Impact, sans-serif", 32)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        """Maneja el disparo del golpe ascendente con ESPACIO."""
        if self.phase != self.PHASE_PLAY or self.is_finished:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.trigger_punch()

    def exit(self) -> None:
        # La cámara pertenece al motor y se comparte con el resto de escenas.
        if hasattr(self.audio, "sonarEscritura"):
            self.audio.sonarEscritura(False)
        super().exit()

    def add_trauma(self, amount: float) -> None:
        """Agrega trauma con clamp en 1.0."""
        self.trauma = min(1.0, self.trauma + amount)

    def spawn_impact_sparks(self, x: float, y: float, count: int = 18, color_base: Tuple[int, int, int] = (255, 220, 50)) -> None:
        """Emisor de chispas lineales limpias con desvanecimiento alfa y onda expansiva."""
        self.shockwaves.append({
            "x": x,
            "y": y,
            "radius": 24.0,
            "max_radius": 190.0,
            "life": 0.22,
            "max_life": 0.22,
            "color": color_base
        })
        for _ in range(count):
            angle = random.uniform(0.0, math.pi * 2)
            speed = random.uniform(260.0, 780.0)
            length = random.uniform(14.0, 34.0)
            life = random.uniform(0.2, 0.45)
            self.spark_particles.append({
                "x": x,
                "y": y,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "length": length,
                "life": life,
                "max_life": life,
                "color": color_base
            })

    def trigger_punch(self) -> None:
        """
        Ejecuta el golpe si no está en cooldown y evalúa el impacto estricto en el Sweet Spot.
        Penaliza el spam de tecla (whiff): si golpeas al aire cuando la notificación aún no ha
        encajado en la caja, aplica bloqueo extendido (0.65s) y si spameas 2 veces al aire -> +1 Strike.
        """
        if self.cooldown_timer > 0.0 or self.is_punching or self.etapa != "juego":
            return

        self.is_punching = True
        self.punch_timer = self.punch_duration
        self.cooldown_timer = self.punch_cooldown

        hit_connected = False
        for notif in self.wave_queue:
            if not notif["spawned"] or notif["state"] != "falling":
                continue

            notif_center_y = notif["y"] + (notif["h"] * 0.5)

            # Margen de gracia con cámara para absorber la latencia de captura
            cam_active = bool(
                getattr(self, "camera_input", None)
                and self.camera_input.enabled
                and self.camera_input.is_hand_present()
            )
            margin = 35.0 if cam_active else 0.0

            # Requisito de encaje: el centro de la tarjeta debe estar dentro de la caja (hit_zone_y_min..hit_zone_y_max)
            if (self.hit_zone_y_min - margin) <= notif_center_y <= (self.hit_zone_y_max + margin):
                hit_connected = True
                self.is_whiff_penalized = False
                # Reproducir la voz del personaje al pegarle a la notificación
                self._play_character_punch_voice()

                notif["resultado"] = "borrada"
                if notif["is_safe"]:
                    self.combo_streak = 0
                    self.on_strike("¡ESA NO TENÍA NADA DE MALO!")
                    notif["state"] = "hit_fly"
                    notif["fly_vx"] = random.choice([-550.0, 550.0])
                    notif["fly_vy"] = -850.0
                    notif["fly_rot_speed"] = random.uniform(-400.0, 400.0)
                    self.spawn_impact_sparks(self.lane_center_x, notif_center_y, 14, colorError)
                else:
                    self.on_successful_hit(notif)
                break

        if not hit_connected:
            # Penalización Anti-Spam acumulativa (NO se perdona al acertar: se guarda hasta el 2do fallo)
            self._play_sfx(self.snd_whiff)
            self.combo_streak = 0
            self.whiff_streak += 1
            self.is_whiff_penalized = True
            self.cooldown_timer = self.whiff_penalty_cooldown
            self.add_trauma(0.28)

            if self.whiff_streak >= 2:
                # 2do golpe al aire acumulado = +1 Strike directo y reinicia la cuenta de 2
                self.whiff_streak = 0
                self.on_strike("¡2 FALLOS AL AIRE!")
            else:
                self.popups.append({
                    "text": "¡FALLO AL AIRE (1/2)! ¡CUIDADO!",
                    "x": float(self.lane_center_x),
                    "y": float(self.hit_zone_y_min - 28),
                    "timer": 0.60,
                    "max_timer": 0.60,
                    "color": colorError
                })

    def on_successful_hit(self, notif: dict) -> None:
        """Impacto kinético sobre notificación basura con Game Feel refinado."""
        self._play_sfx(self.snd_hit)
        self.combo_streak += 1

        notif["state"] = "hit_fly"
        direction = -1.0 if random.random() < 0.5 else 1.0
        notif["fly_vx"] = direction * random.uniform(760.0, 1120.0)
        notif["fly_vy"] = -random.uniform(980.0, 1360.0)
        notif["fly_rot_speed"] = direction * random.uniform(440.0, 840.0)

        # Hit-stop de 4 frames (~0.066s)
        self.hit_stop_timer = 0.066
        self.add_trauma(0.55)

        impact_y = notif["y"] + (notif["h"] // 2)
        self.spawn_impact_sparks(self.lane_center_x, impact_y, count=24, color_base=colorAcierto)

        words = ["¡FUERA DEL POST!", "¡ESO NO SE PUBLICA!", "¡NI SIN CULPA!", "¡BORRADO!"]
        text = random.choice(words)
        if self.combo_streak >= 3:
            text = f"{text} x{self.combo_streak}"

        self.popups.append({
            "text": text,
            "x": float(self.lane_center_x + random.uniform(-45, 45)),
            "y": float(notif["y"] - 20),
            "timer": 0.65,
            "max_timer": 0.65,
            "color": colorAcierto
        })

        self.processed_count += 1
        self.check_wave_progress()

    def on_strike(self, reason: str) -> None:
        """Aplica +1 Strike, sonido de vibración, sacudida y flash de pantalla."""
        self._play_sfx(self.snd_strike)
        self.strikes += 1
        self.strike_flash_alpha = 190.0
        self.add_trauma(0.85)

        self.popups.append({
            "text": reason,
            "x": float(self.lane_center_x),
            "y": float(self.hit_zone_y_min - 30),
            "timer": 0.85,
            "max_timer": 0.85,
            "color": colorError
        })

        if self.strikes >= self.max_strikes:
            self.empezarPublicacion(False)

    def check_wave_progress(self) -> None:
        """Verifica victoria si se procesaron todas las notificaciones."""
        if self.strikes >= self.max_strikes:
            return

        if self.processed_count >= self.total_wave_count:
            self.empezarPublicacion(True)

    def update_game(self, dt: float) -> None:
        """Actualiza física, estado de Sweet Spot, ondas expansivas, trauma y partículas."""
        cam = getattr(self, "camera_input", None)
        if self._camera_resume_grace > 0.0:
            self._camera_resume_grace = max(0.0, self._camera_resume_grace - dt)
            if cam and cam.enabled:
                cam.consume_punch()
                cam.consume_fist()
        elif cam and cam.enabled and (cam.consume_punch() or cam.consume_fist()):
            if self.etapa == "juego":
                self.trigger_punch()
        self.pulse_clock += dt * 10.0
        self.tEtapa += dt
        self.actualizarPost(dt)
        if self.etapa == "foto" and self.tEtapa >= self.fotoDuracion:
            self.etapa = "juego"
            self.ponerMusica()
        if self.etapa == "publicar":
            self.time_left = self.tiempoCongelado
            self.trauma = max(0.0, self.trauma - dt * 1.6)
            self.strike_flash_alpha = max(0.0, self.strike_flash_alpha - dt * 320.0)
            if self.tEtapa >= duracionPublicar and not self.is_finished:
                self.finish_game(self.ganoPublicacion)
            return

        if self.hit_stop_timer > 0.0:
            self.hit_stop_timer -= dt
            return

        if self.trauma > 0.0:
            self.trauma = max(0.0, self.trauma - (dt * 1.6))

        if self.strike_flash_alpha > 0.0:
            self.strike_flash_alpha = max(0.0, self.strike_flash_alpha - (dt * 320.0))

        if self.cooldown_timer > 0.0:
            self.cooldown_timer = max(0.0, self.cooldown_timer - dt)
            if self.cooldown_timer <= 0.0:
                self.is_whiff_penalized = False

        if self.is_punching:
            self.punch_timer -= dt
            if self.punch_timer <= 0.0:
                self.is_punching = False

        elapsed = self.time_limit - self.time_left
        for notif in self.wave_queue:
            if not notif["spawned"] and elapsed >= notif["spawn_time"]:
                notif["spawned"] = True

            if not notif["spawned"]:
                continue

            if notif["state"] == "falling":
                notif["y"] += notif["speed"] * dt
                notif_center_y = notif["y"] + (notif["h"] * 0.5)

                # Solo se enciende el Sweet Spot cuando el centro de la tarjeta encaja dentro de la caja
                notif["in_sweet_spot"] = (self.hit_zone_y_min <= notif_center_y <= self.hit_zone_y_max)

                if notif_center_y > self.hit_zone_y_max + 20:
                    notif["state"] = "passed"
                    notif["in_sweet_spot"] = False
                    notif["resultado"] = "publicada"
                    self.mandarAlPost(notif)
                    if not notif["is_safe"]:
                        self.combo_streak = 0
                        self.on_strike("¡SE COLÓ EN TU POST!")
                    else:
                        self._play_sfx(self.snd_safe)
                        self.combo_streak += 1
                        self.popups.append({
                            "text": "¡A TU POST!",
                            "x": float(self.lane_center_x),
                            "y": float(self.hit_zone_y_max - 20),
                            "timer": 0.55,
                            "max_timer": 0.55,
                            "color": colorPost
                        })
                    self.processed_count += 1
                    self.check_wave_progress()

            elif notif["state"] == "hit_fly":
                notif["x"] += notif["fly_vx"] * dt
                notif["y"] += notif["fly_vy"] * dt
                notif["fly_vy"] += 2300.0 * dt
                notif["fly_rot"] += notif["fly_rot_speed"] * dt
                notif["alpha"] = max(0.0, notif["alpha"] - (dt * 240.0))
                if notif["alpha"] <= 0.0 or notif["y"] > self.screen_h + 300:
                    notif["state"] = "done"

        # Ondas de choque
        for sw in list(self.shockwaves):
            sw["life"] -= dt
            if sw["life"] <= 0.0:
                self.shockwaves.remove(sw)
            else:
                progress = 1.0 - (sw["life"] / sw["max_life"])
                sw["radius"] = 24.0 + (sw["max_radius"] - 24.0) * progress

        # Partículas
        for p in list(self.spark_particles):
            p["life"] -= dt
            if p["life"] <= 0.0:
                self.spark_particles.remove(p)
            else:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vy"] += 800.0 * dt

        # Popups
        for pop in list(self.popups):
            pop["timer"] -= dt
            pop["y"] -= 65.0 * dt
            if pop["timer"] <= 0.0:
                self.popups.remove(pop)

        if self.time_left <= 0.0 and not self.is_finished:
            self.empezarPublicacion(self.strikes < self.max_strikes)
            self.time_left = self.tiempoCongelado

    def _render_sweet_spot_guide(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        """Dibuja la guía visual de la Zona de Bateo ("Sweet Spot") con feedback de color y texto."""
        active_notif = None
        for notif in self.wave_queue:
            if notif["spawned"] and notif["state"] == "falling" and notif["in_sweet_spot"]:
                active_notif = notif
                break

        zone_w = 470
        zone_h = 220
        zone_x = self.lane_center_x - (zone_w // 2) + ox
        zone_y = self.sweet_spot_center_y - (zone_h // 2) + oy

        guide_surf = pygame.Surface((zone_w, zone_h), pygame.SRCALPHA)
        pulse = (math.sin(self.pulse_clock) + 1.0) * 0.5

        if self.is_whiff_penalized and self.cooldown_timer > 0.0:
            # Estado de bloqueo por spamear antes de tiempo (Castigo visual en rojo/naranja)
            border_color = (*colorError, 210)
            glow_color = (*colorError, 45)
            pygame.draw.rect(guide_surf, glow_color, (0, 0, zone_w, zone_h), border_radius=28)
            pygame.draw.rect(guide_surf, border_color, (0, 0, zone_w, zone_h), width=5, border_radius=28)

            prompt_surf = self.textoConBorde(self.font_prompt, "¡RECARGANDO GUANTE!", colorError, contornoTexto, 3)
            px = zone_x + zone_w + 18
            py = zone_y + (zone_h // 2) - (prompt_surf.get_height() // 2)
            surface.blit(prompt_surf, (px, py))
        elif active_notif is not None:
            if not active_notif["is_safe"]:
                border_color = (*colorAcierto, int(195 + 55 * pulse))
                glow_color = (*colorAcierto, int(45 + 35 * pulse))
                pygame.draw.rect(guide_surf, glow_color, (0, 0, zone_w, zone_h), border_radius=28)
                pygame.draw.rect(guide_surf, border_color, (0, 0, zone_w, zone_h), width=5, border_radius=28)

                prompt_surf = self.textoConBorde(self.font_prompt, "¡NO LA PUBLIQUES! [ESPACIO]", colorAcierto, contornoTexto, 3)
                px = zone_x + zone_w + 18
                py = zone_y + (zone_h // 2) - (prompt_surf.get_height() // 2)
                surface.blit(prompt_surf, (px, py))
            else:
                border_color = (*colorPost, int(165 + 50 * pulse))
                glow_color = (*colorPost, 32)
                pygame.draw.rect(guide_surf, glow_color, (0, 0, zone_w, zone_h), border_radius=28)
                pygame.draw.rect(guide_surf, border_color, (0, 0, zone_w, zone_h), width=4, border_radius=28)

                prompt_surf = self.textoConBorde(self.font_prompt, "¡DÉJALA PASAR!", colorPost, contornoTexto, 3)
                px = zone_x + zone_w + 18
                py = zone_y + (zone_h // 2) - (prompt_surf.get_height() // 2)
                surface.blit(prompt_surf, (px, py))
        else:
            bracket_color = (255, 255, 255, 115)
            b_len = 36
            b_thick = 4
            pygame.draw.line(guide_surf, bracket_color, (0, 0), (b_len, 0), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (0, 0), (0, b_len), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (zone_w - b_len, 0), (zone_w, 0), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (zone_w - 1, 0), (zone_w - 1, b_len), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (0, zone_h - 1), (b_len, zone_h - 1), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (0, zone_h - b_len), (0, zone_h), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (zone_w - b_len, zone_h - 1), (zone_w, zone_h - 1), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (zone_w - 1, zone_h - b_len), (zone_w - 1, zone_h), b_thick)

        surface.blit(guide_surf, (zone_x, zone_y))

    def _render_player_character(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        """
        Renderiza al personaje con sombra elíptica en el piso, respiración natural (idle bobbing)
        e impulso vertical elástico al ejecutar el Uppercut.
        """
        shadow_w = 220 if not self.is_punching else 185
        shadow_h = 34
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (25, 20, 15, 85), (0, 0, shadow_w, shadow_h))
        shadow_rect = shadow_surf.get_rect(center=(self.lane_center_x + ox, self.char_base_y - 8 + oy))
        surface.blit(shadow_surf, shadow_rect)

        if self.is_punching:
            punch_ratio = max(0.0, self.punch_timer / self.punch_duration)
            lunge_y = int(math.sin(punch_ratio * math.pi) * -28)
            surface.blit(
                self.sprite_punch,
                (self.char_punch_pos[0] + ox, self.char_punch_pos[1] + lunge_y + oy)
            )
        else:
            bob_y = int(math.sin(self.pulse_clock * 0.65) * 4.5)
            surface.blit(
                self.sprite_idle,
                (self.char_idle_pos[0] + ox, self.char_idle_pos[1] + bob_y + oy)
            )

    def _render_hud_overlay(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        """
        Renderiza el HUD limpio: las vidas como corazones de acuarela dentro del recuadro del juego del piano.
        """
        # 1. Barra de Strikes (Esquina superior izquierda)
        if self.dibujarVidas(surface, ox, oy):
            return
        hud_x = 55 + ox
        hud_y = 35 + oy
        surface.blit(self.strike_hud_base, (hud_x, hud_y))

        for s in range(min(self.strikes, len(self.circle_rel_positions))):
            rel_cx, rel_cy = self.circle_rel_positions[s]
            cx = hud_x + int(self.hud_bar_w * rel_cx)
            cy = hud_y + int(self.hud_bar_h * rel_cy)

            x_shadow = self.font_strike_x.render("X", True, (35, 10, 15))
            x_surf = self.font_strike_x.render("X", True, (235, 45, 45))

            rx = cx - (x_surf.get_width() // 2)
            ry = cy - (x_surf.get_height() // 2)

            surface.blit(x_shadow, (rx + 2, ry + 2))
            surface.blit(x_surf, (rx, ry))

        # 2. Reloj Contador Gráfico Oficial suprimido (se utiliza la barra de tiempo inferior)

    def cargarVidas(self) -> bool:
        clave = ("vidas", self.max_strikes)
        if clave not in _SURFACE_CACHE:
            try:
                lado, espacio = 60, 18
                lleno = self.assets.cargarSinFondo(os.path.join("Piano", "corazonLleno.jpg"), lado)
                vacio = self.assets.cargarSinFondo(os.path.join("Piano", "corazonVacio.jpg"), lado)
                panel = self.assets.cargarSinFondo(os.path.join("Piano", "panelCorazones.jpg"), 600)
                panel = pygame.transform.smoothscale_by(panel, 96 / float(panel.get_height()))
                panel = self.estirarCentro(panel, self.max_strikes * lado + (self.max_strikes - 1) * espacio + 84)
                _SURFACE_CACHE[clave] = (panel, lleno, vacio, lado + espacio)
            except Exception as e:
                print(f"[PunchAlert] Aviso: no se pudieron cargar los corazones: {e}")
                _SURFACE_CACHE[clave] = None
        self.imagenesVidas = _SURFACE_CACHE[clave]
        return self.imagenesVidas is not None

    def dibujarVidas(self, surface: pygame.Surface, ox: int, oy: int) -> bool:
        if getattr(self, "imagenesVidas", None) is None and not self.cargarVidas():
            return False
        panel, lleno, vacio, paso = self.imagenesVidas
        vidas = max(0, min(self.max_strikes, self.max_strikes - self.strikes))
        ahora = pygame.time.get_ticks() / 1000.0
        anteriores = getattr(self, "vidasMostradas", self.max_strikes)
        if vidas != anteriores:
            self.cambioVida = (min(vidas, anteriores), ahora)
            self.vidasMostradas = vidas
        caja = panel.get_rect(topleft=(48 + ox, 30 + oy))
        surface.blit(panel, caja)
        inicio = caja.centerx - paso * (self.max_strikes - 1) / 2.0
        indice, cuando = getattr(self, "cambioVida", (-1, -10.0))
        for i in range(self.max_strikes):
            imagen = lleno if i < vidas else vacio
            centro = (round(inicio + i * paso), caja.centery)
            if i == indice:
                p = min(1.0, (ahora - cuando) / 0.45)
                imagen = pygame.transform.rotozoom(imagen, math.sin(p * math.pi * 3) * 10 * (1 - p), 1.0 + 0.35 * (1 - p))
            surface.blit(imagen, imagen.get_rect(center=centro))
        return True

    def render_game(self, surface: pygame.Surface) -> None:
        """Renderizado completo con jerarquía de capas, ondas expansivas y HUD limpio."""
        shake_magnitude = (self.trauma ** 2) * self.max_shake_offset
        if shake_magnitude > 0.01:
            angle = random.uniform(0.0, math.pi * 2)
            ox = int(math.cos(angle) * shake_magnitude)
            oy = int(math.sin(angle) * shake_magnitude)
        else:
            ox, oy = 0, 0

        # 1. Fondo oficial
        surface.blit(self.bg_surface, (ox, oy))
        self.dibujarCielo(surface, ox, oy)
        self.dibujarArbolito(surface, ox, oy)

        # 2. Personaje con sombra elíptica, respiración y lunge de uppercut
        self._render_player_character(surface, ox, oy)
        if self.foto is None and self.phase == self.PHASE_PLAY:
            self.capturarFoto(surface)

        # 3. Retícula del "Sweet Spot" (Zona de Bateo) frente al personaje
        if self.etapa == "juego":
            self._render_sweet_spot_guide(surface, ox, oy)

        # 4. Ondas de choque de impacto (Shockwave Rings)
        for sw in self.shockwaves:
            ratio = max(0.0, sw["life"] / sw["max_life"])
            alpha = int(210 * ratio)
            r = int(sw["radius"])
            if r > 4:
                sw_surf = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(sw_surf, (*sw["color"], alpha), (r + 4, r + 4), r, width=max(2, int(6 * ratio)))
                surface.blit(sw_surf, (int(sw["x"] - r - 4) + ox, int(sw["y"] - r - 4) + oy))

        # 5. Notificaciones en primer plano (con pop de escala 1.07x en el Sweet Spot)
        for notif in self.wave_queue:
            if not notif["spawned"] or notif["state"] in ("passed", "done"):
                continue

            spr = notif["sprite"]
            if notif["state"] == "hit_fly":
                rotated = pygame.transform.rotate(spr, notif["fly_rot"])
                if notif["alpha"] < 255:
                    rotated.set_alpha(int(notif["alpha"]))
                rw, rh = rotated.get_size()
                draw_x = int(notif["x"] + (notif["w"] // 2) - (rw // 2)) + ox
                draw_y = int(notif["y"] + (notif["h"] // 2) - (rh // 2)) + oy
                surface.blit(rotated, (draw_x, draw_y))
            else:
                if notif["in_sweet_spot"] and not notif["is_safe"]:
                    pop_w = int(notif["w"] * 1.07)
                    pop_h = int(notif["h"] * 1.07)
                    scaled_pop = pygame.transform.smoothscale(spr, (pop_w, pop_h))
                    draw_x = int(notif["x"] - ((pop_w - notif["w"]) // 2)) + ox
                    draw_y = int(notif["y"] - ((pop_h - notif["h"]) // 2)) + oy
                    surface.blit(scaled_pop, (draw_x, draw_y))
                else:
                    surface.blit(spr, (int(notif["x"]) + ox, int(notif["y"]) + oy))

        self.dibujarPublicacion(surface, ox, oy)
        self.dibujarVuelos(surface, ox, oy)

        # 6. Partículas de impacto
        for p in self.spark_particles:
            ratio = max(0.0, p["life"] / p["max_life"])
            alpha = int(255 * ratio)
            color = (*p["color"], alpha)
            p_surf = pygame.Surface((int(p["length"] * 2), int(p["length"] * 2)), pygame.SRCALPHA)
            speed = math.hypot(p["vx"], p["vy"])
            if speed > 0:
                dx = (p["vx"] / speed) * p["length"]
                dy = (p["vy"] / speed) * p["length"]
                cx = p["length"]
                cy = p["length"]
                pygame.draw.line(p_surf, color, (cx - dx * 0.4, cy - dy * 0.4), (cx + dx * 0.6, cy + dy * 0.6), 3)
                surface.blit(p_surf, (int(p["x"] - cx) + ox, int(p["y"] - cy) + oy))

        # 7. Popups de impacto
        for pop in self.popups:
            if "imagen" not in pop:
                pop["imagen"] = self.textoConBorde(self.font_juice, pop["text"], pop["color"], contornoTexto, 4)
            rendered_text = pop["imagen"]
            rx = int(pop["x"] - (rendered_text.get_width() // 2)) + ox
            ry = int(pop["y"]) + oy
            surface.blit(rendered_text, (rx, ry))

        # 8. HUD Overlay Unificado (Solo Barra de Strikes + Reloj Contador Oficial)
        self._render_hud_overlay(surface, ox, oy)
        self.dibujarFoto(surface)
        self.dibujarPublicando(surface)

        # 9. Flash perimetral en Strike
        if self.strike_flash_alpha > 0.0:
            flash_overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            flash_overlay.fill((70, 34, 104, int(self.strike_flash_alpha * 0.6)))
            surface.blit(flash_overlay, (0, 0))

        # 10. Indicador visual de puño para cámara
        cam = getattr(self, "camera_input", None)
        if cam and cam.enabled and getattr(self, "spr_fist_hint", None) is not None:
            hx, hy = self.screen_w - 150, self.screen_h - 124
            card_w, card_h = 240, 196
            card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            pygame.draw.rect(card, (255, 249, 234, 232), (6, 6, card_w - 12, card_h - 12), border_radius=22)
            pygame.draw.rect(card, (126, 86, 56, 235), (6, 6, card_w - 12, card_h - 12), width=3, border_radius=22)
            card.blit(self.spr_fist_hint, self.spr_fist_hint.get_rect(center=(card_w // 2, 76)))
            font_hint = getattr(self, "font_hint", None) or pygame.font.SysFont("Arial, sans-serif", 18, bold=True)
            lbl = font_hint.render("PUÑO PARA GOLPEAR", True, (78, 51, 35))
            card.blit(lbl, lbl.get_rect(center=(card_w // 2, 162)))
            surface.blit(card, card.get_rect(center=(hx, hy)))
