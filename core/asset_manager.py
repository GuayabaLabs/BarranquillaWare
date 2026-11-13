import os
import numpy as np
import pygame
from typing import Dict, Optional, List

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
