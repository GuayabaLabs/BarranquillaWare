import os
import numpy as np
import pygame
from typing import Dict, Optional, List

try:
    import cv2
except ImportError:
    cv2 = None

# Fuente de cuento que usa el juego de la montaña rusa
rutaFuenteCuento = os.path.join("coaster_game", "fuenteLetra", "IndieFlower-Regular.ttf")
# Código del juego de la montaña rusa, para reutilizar sus dibujos (tarjeta, marco de cámara, nubes)
rutaCoaster = os.path.join("coaster_game", "Coaster.py")

# Puntos dentro de las asas y entre las hojas del trofeo donde también hay fondo blanco
# (en fracción del ancho y del alto de la imagen)
semillasTrofeo = (
    (0.2095, 0.3452), (0.7896, 0.3452),
    (0.2070, 0.7207), (0.7920, 0.7207),
    (0.2402, 0.7822), (0.7593, 0.7822),
    (0.2896, 0.8296), (0.7095, 0.8296),
)


def _flood_fill_fondo(fondo: np.ndarray, semillas) -> np.ndarray:
    """Flood-fill scanline conectado únicamente a los bordes/semillas en numpy puro."""
    from collections import deque

    h, w = fondo.shape
    visitado = np.zeros((h, w), dtype=bool)
    cola = deque()
    for sx, sy in semillas:
        if 0 <= sx < w and 0 <= sy < h and fondo[sy, sx] and not visitado[sy, sx]:
            cola.append((sx, sy))

    while cola:
        x, y = cola.popleft()
        if visitado[y, x] or not fondo[y, x]:
            continue
        fila = fondo[y]
        vis_fila = visitado[y]
        x0 = x
        while x0 > 0 and fila[x0 - 1] and not vis_fila[x0 - 1]:
            x0 -= 1
        x1 = x
        while x1 + 1 < w and fila[x1 + 1] and not vis_fila[x1 + 1]:
            x1 += 1
        vis_fila[x0:x1 + 1] = True
        for ny in (y - 1, y + 1):
            if 0 <= ny < h:
                nfila = fondo[ny]
                nvis = visitado[ny]
                en_tramo = False
                for nx in range(x0, x1 + 1):
                    if nfila[nx] and not nvis[nx]:
                        if not en_tramo:
                            cola.append((nx, ny))
                            en_tramo = True
                    else:
                        en_tramo = False
    return visitado


def borrarFondo(foto, fondo, borde, semillas=((0, 0),)):
    # Borra el fondo conectado con la orilla de la imagen (o con puntos semillas)
    # usando flood-fill conectado en numpy y suavizado de contorno sin perforar interiores.
    if foto.get_masks()[3] == 0:
        foto = foto.convert_alpha()
    fondo_hw = np.asarray(fondo, dtype=bool).T
    visitado = _flood_fill_fondo(fondo_hw, semillas)
    dibujo = (~visitado).astype(np.float32) * 255.0

    # Erosión 3x3 opcional (quita el filito claro de la orilla) + suavizado 3x3
    if borde >= 3:
        pad = np.pad(dibujo, 1, mode="edge")
        h, w = dibujo.shape
        dibujo = np.minimum.reduce([
            pad[dy:dy + h, dx:dx + w]
            for dy in range(3)
            for dx in range(3)
        ])

    pad = np.pad(dibujo, 1, mode="edge")
    h, w = dibujo.shape
    dibujo = (
        1.0 * pad[0:h, 0:w] + 2.0 * pad[0:h, 1:w + 1] + 1.0 * pad[0:h, 2:w + 2] +
        2.0 * pad[1:h + 1, 0:w] + 4.0 * pad[1:h + 1, 1:w + 1] + 2.0 * pad[1:h + 1, 2:w + 2] +
        1.0 * pad[2:h + 2, 0:w] + 2.0 * pad[2:h + 2, 1:w + 1] + 1.0 * pad[2:h + 2, 2:w + 2]
    ) / 16.0
    alfa_u8 = np.clip(dibujo, 0, 255).astype(np.uint8)

    alfa = pygame.surfarray.pixels_alpha(foto)
    alfa[:] = alfa_u8.T
    del alfa
    ys, xs = np.nonzero(alfa_u8 > 10)
    if len(xs) == 0 or len(ys) == 0:
        return foto.copy()
    caja = pygame.Rect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min()) + 1, int(ys.max() - ys.min()) + 1)
    return foto.subsurface(caja).copy()


def achicar(img, lado):
    # Trabajar con las imágenes en tamaño completo es lento; se achican antes de procesarlas
    mayor = max(img.get_size())
    if mayor <= lado:
        return img
    esc = lado / mayor
    return pygame.transform.smoothscale(img, (round(img.get_width() * esc), round(img.get_height() * esc)))


def quitarBlanco(foto, semillasExtra=()):
    # Borra el fondo blanco conectado a los 4 bordes exteriores (y semillasExtra);
    # si ya trae transparencia, solo se recorta.
    if foto.get_width() == 0 or foto.get_height() == 0:
        return foto.copy()
    if foto.get_at((0, 0)).a < 250:
        rect = foto.get_bounding_rect(min_alpha=10)
        return foto.subsurface(rect).copy() if rect.width > 0 and rect.height > 0 else foto.copy()
    w, h = foto.get_size()
    semillas = []
    for x in range(w):
        semillas.append((x, 0))
        semillas.append((x, h - 1))
    for y in range(h):
        semillas.append((0, y))
        semillas.append((w - 1, y))
    for fx, fy in semillasExtra:
        semillas.append((int(fx * w), int(fy * h)))
    rgb = pygame.surfarray.array3d(foto).astype(np.int16)
    fondo = ((rgb.max(axis=2) - rgb.min(axis=2)) <= 20) & (rgb.min(axis=2) >= 225)
    return borrarFondo(foto, fondo, 3, semillas)


class AssetManager:
    """
    Gestor centralizado de recursos gráficos y sprites.
    Carga, recorta y cachea superficies para garantizar rendimiento y consistencia visual sin deformación.
    """
    _instance: Optional['AssetManager'] = None

    def __init__(self, base_dir: str = "assets") -> None:
        self.base_dir = base_dir
        self._cache: Dict[str, pygame.Surface] = {}
        self._raw_cache: Dict[str, pygame.Surface] = {}
        self._audio_cache: Dict[int, List[pygame.Surface]] = {}
        self._font_cache: Dict[str, pygame.font.Font] = {}
        self.fonts_dir = os.path.join(self.base_dir, "fonts")

    @classmethod
    def get_instance(cls, base_dir: str = "assets") -> 'AssetManager':
        if cls._instance is None:
            cls._instance = AssetManager(base_dir)
        return cls._instance

    def _resolve_path(self, filename_fragment: str) -> str:
        """Encuentra la ruta del archivo tolerando variaciones de codificación UTF-8/ANSI."""
        direct_path = os.path.join(self.base_dir, filename_fragment)
        if os.path.exists(direct_path):
            return direct_path

        clean_fragment = filename_fragment.lower().replace("í", "i").replace("á", "a")
        for f in os.listdir(self.base_dir):
            clean_f = f.lower().replace("í", "i").replace("á", "a")
            if clean_fragment in clean_f or filename_fragment in f:
                return os.path.join(self.base_dir, f)

        raise FileNotFoundError(f"Asset no encontrado para fragmento: {filename_fragment}")

    def load_surface(self, filename_fragment: str, has_alpha: bool = True) -> pygame.Surface:
        if filename_fragment in self._raw_cache:
            return self._raw_cache[filename_fragment]

        path = self._resolve_path(filename_fragment)
        surf = pygame.image.load(path).convert_alpha() if has_alpha else pygame.image.load(path).convert()
        self._raw_cache[filename_fragment] = surf
        return surf

    def load_cropped_surface(self, filename_fragment: str, alpha_threshold: int = 0) -> pygame.Surface:
        """Carga y recorta la superficie a su caja visible real sin bordes transparentes sobrantes."""
        cache_key = f"cropped_{filename_fragment}_{alpha_threshold}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        raw = self.load_surface(filename_fragment, has_alpha=True)
        if alpha_threshold > 0:
            arr = pygame.surfarray.pixels_alpha(raw)
            mask = arr > alpha_threshold
            ys = mask.any(axis=0).nonzero()[0]
            xs = mask.any(axis=1).nonzero()[0]
            del arr
            if len(xs) > 0 and len(ys) > 0:
                rect = pygame.Rect(int(xs[0]), int(ys[0]), int(xs[-1] - xs[0] + 1), int(ys[-1] - ys[0] + 1))
            else:
                rect = raw.get_bounding_rect()
        else:
            rect = raw.get_bounding_rect()

        if rect.width <= 0 or rect.height <= 0:
            return raw

        cropped = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        cropped.blit(raw, (0, 0), rect)
        self._cache[cache_key] = cropped
        return cropped

    def get_scaled(self, filename_fragment: str, target_width: int, target_height: Optional[int] = None) -> pygame.Surface:
        """Obtiene un sprite recortado y reescalado proporcionalmente respetando aspect ratio."""
        cache_key = f"scaled_{filename_fragment}_{target_width}_{target_height}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        cropped = self.load_cropped_surface(filename_fragment)
        orig_w = cropped.get_width()
        orig_h = cropped.get_height()

        if target_height is None:
            scale_factor = target_width / max(1, orig_w)
            target_height = max(1, int(orig_h * scale_factor))

        scaled = pygame.transform.smoothscale(cropped, (target_width, target_height))
        self._cache[cache_key] = scaled
        return scaled

    def get_audio_button_frames(self, target_size: int = 58) -> List[pygame.Surface]:
        """
        Extrae los 4 frames del spritesheet de audio sin deformación (aspect ratio 1:1 exacto):
        0: Música ON, 1: Música OFF, 2: Sonido ON, 3: Sonido OFF
        """
        if target_size in self._audio_cache:
            return self._audio_cache[target_size]

        raw = self.load_surface("spritesheet_botones_sonido_y_musica_main_menu.png", has_alpha=True)
        frame_width = raw.get_width() // 4
        frame_height = raw.get_height()

        frames: List[pygame.Surface] = []
        for i in range(4):
            sub = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            sub.blit(raw, (0, 0), (i * frame_width, 0, frame_width, frame_height))

            # Segmentar máscara con umbral alfa > 35 para aislar silueta física real
            sub_arr = pygame.surfarray.pixels_alpha(sub)
            mask = sub_arr > 35
            del sub_arr

            cols = np.where(mask.any(axis=1))[0]
            rows = np.where(mask.any(axis=0))[0]

            if len(cols) > 0 and len(rows) > 0:
                min_x, max_x = cols[0], cols[-1]
                min_y, max_y = rows[0], rows[-1]
                bw = max_x - min_x + 1
                bh = max_y - min_y + 1

                side = max(bw, bh)
                cx = (min_x + max_x) // 2
                cy = (min_y + max_y) // 2

                crop_rect = pygame.Rect(cx - side // 2, cy - side // 2, side, side)
                square_surf = pygame.Surface((side, side), pygame.SRCALPHA)
                square_surf.blit(sub, (0, 0), crop_rect)
                scaled = pygame.transform.smoothscale(square_surf, (target_size, target_size))
            else:
                scaled = pygame.transform.smoothscale(sub, (target_size, target_size))

            frames.append(scaled)

        self._audio_cache[target_size] = frames
        return frames

    def get_font(self, font_name: str, size: int, bold: bool = False) -> pygame.font.Font:
        """
        Carga una fuente con fallback robusto:
        1. Intenta cargar archivo local empaquetado (.ttf) en assets/fonts/
        2. Intenta cargar mediante pygame.font.SysFont
        3. Fallback a pygame.font.Font(None, size)
        """
        cache_key = f"{font_name}_{size}_{bold}"
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        # Mapeo de nombres comunes a fuentes locales empaquetadas
        font_map = {
            "arial rounded": "arialrounded.ttf",
            "arialrounded": "arialrounded.ttf",
            "trebuchet": "trebucbd.ttf" if bold else "trebuc.ttf",
            "trebuchet ms": "trebucbd.ttf" if bold else "trebuc.ttf",
            "inkfree": "Inkfree.ttf",
            "ink free": "Inkfree.ttf",
            "segoeprint": "segoeprb.ttf" if bold else "segoepr.ttf",
            "segoe print": "segoeprb.ttf" if bold else "segoepr.ttf",
            "impact": "Impact.ttf",
            "arial black": "Impact.ttf",
            "arial": "ArialBold.ttf" if bold else "ArialBold.ttf",
        }

        # 1. Probar fuente local empaquetada
        font_obj: Optional[pygame.font.Font] = None
        for key, ttf_file in font_map.items():
            if key in font_name.lower():
                candidate_path = os.path.join(self.fonts_dir, ttf_file)
                if os.path.exists(candidate_path):
                    try:
                        font_obj = pygame.font.Font(candidate_path, size)
                        break
                    except Exception:
                        font_obj = None

        # 2. Probar SysFont
        if font_obj is None:
            try:
                font_obj = pygame.font.SysFont(font_name, size, bold=bold)
            except Exception:
                font_obj = None

        # 3. Fallback final por defecto
        if font_obj is None:
            font_obj = pygame.font.Font(None, size)

        self._font_cache[cache_key] = font_obj
        return font_obj

    def cargarSinFondo(self, nombreArchivo: str, ancho: int, semillasExtra: tuple = ()) -> pygame.Surface:
        """Carga una imagen con fondo blanco, le quita el fondo y la deja del ancho pedido."""
        clave = f"sinFondo_{nombreArchivo}_{ancho}"
        if clave in self._cache:
            return self._cache[clave]

        # El fondo se quita una sola vez por imagen, sin importar cuántos tamaños se pidan
        claveSinFondo = f"sinFondoOriginal_{nombreArchivo}"
        if claveSinFondo not in self._cache:
            original = pygame.image.load(self._resolve_path(nombreArchivo)).convert_alpha()
            self._cache[claveSinFondo] = quitarBlanco(achicar(original, 1200), semillasExtra)
        foto = self._cache[claveSinFondo]
        alto = max(1, int(foto.get_height() * ancho / float(foto.get_width())))
        imagen = pygame.transform.smoothscale(foto, (ancho, alto))
        self._cache[clave] = imagen
        return imagen

    def cargarTrofeo(self, ancho: int, enGris: bool = False) -> pygame.Surface:
        """Trofeo de los logros; en gris cuando todavía no se ha ganado."""
        clave = f"trofeo_{ancho}_{enGris}"
        if clave in self._cache:
            return self._cache[clave]

        trofeo = self.cargarSinFondo(os.path.join("Interfaz", "Trofeo.jpg"), ancho, semillasTrofeo)
        if enGris:
            trofeo = pygame.transform.grayscale(trofeo)
            trofeo.set_alpha(150)
        self._cache[clave] = trofeo
        return trofeo

    def cargarFuenteCuento(self, tam: int) -> pygame.font.Font:
        """Fuente escrita a mano del juego de la montaña rusa."""
        clave = f"cuento_{tam}"
        if clave in self._font_cache:
            return self._font_cache[clave]

        if os.path.exists(rutaFuenteCuento):
            fuente = pygame.font.Font(rutaFuenteCuento, tam)
        else:
            fuente = pygame.font.SysFont("trebuchetms,verdana,arial", tam, bold=True)
        self._font_cache[clave] = fuente
        return fuente

    def cargarCoaster(self):
        """Carga una sola vez el código del juego de la montaña rusa para usar sus dibujos.
        Devuelve None si la carpeta coaster_game no está."""
        if getattr(self, "moduloCoaster", None) is not None:
            return self.moduloCoaster
        self.moduloCoaster = None
        if os.path.exists(rutaCoaster):
            try:
                import importlib.util
                especificacion = importlib.util.spec_from_file_location("coasterDibujos", rutaCoaster)
                modulo = importlib.util.module_from_spec(especificacion)
                especificacion.loader.exec_module(modulo)
                self.moduloCoaster = modulo
            except Exception as e:
                print(f"Aviso: no se pudo cargar el juego de la montaña rusa: {e}")
        return self.moduloCoaster

