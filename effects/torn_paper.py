"""Franja rasgada con textura tintada por los colores del propio mapa."""

import math
import random

import numpy as np
import pygame


class TornPaperEdges:
    """Disimula las uniones del mapa con bordes de papel irregulares y desgastados."""

    def __init__(self, depth: int = 30, strength: float = 0.62, seed: int = 2718) -> None:
        self.depth = max(2, int(depth))
        self.strength = max(0.0, min(1.0, float(strength)))
        self.seed = seed
        self._tear_cache = {}

    def blend_seams(self, surface: pygame.Surface, seam_x: int, seam_y: int) -> None:
        """Pinta una franja rugosa cuyos tonos nacen de los píxeles bajo la costura."""
        pixels = pygame.surfarray.array3d(surface).astype(np.float32)
        height, width = surface.get_height(), surface.get_width()
        self._blend_horizontal(pixels, seam_y, width, height, random.Random(self.seed))
        self._blend_vertical(pixels, seam_x, width, height, random.Random(self.seed + 1))
        pygame.surfarray.blit_array(surface, np.clip(pixels, 0, 255).astype(np.uint8))

    def _blend_horizontal(self, pixels: np.ndarray, seam: int, width: int, height: int, rng: random.Random) -> None:
        depth = self.depth
        # Muestras de bajo ritmo producen grandes ondulaciones; ruido fino aporta
        # pequeños dientes, como fibras irregulares de papel rasgado.
        anchors = [rng.uniform(-depth * 0.58, depth * 0.58) for _ in range(max(2, width // 90 + 2))]
        tears = self._tear_mask(width, rng)
        for x in range(width):
            roughness = int(self._interpolate(anchors, x / 90.0) + math.sin(x * 0.035) * 4 + math.sin(x * 0.19 + 1.7) * 2 + rng.uniform(-3.0, 3.0))
            edge = max(1, min(height - 2, seam + roughness))
            local_depth = max(4, depth + int(math.sin(x * 0.027) * depth * 0.18) + int(rng.uniform(-depth * 0.12, depth * 0.12)))
            start, end = max(0, edge - local_depth), min(height, edge + local_depth + 1)
            offsets = np.arange(start - edge, end - edge, dtype=np.float32)
            blend = self.strength * np.maximum(0.0, 1.0 - np.abs(offsets) / (local_depth + 1)) ** 0.8
            region = pixels[x, start:end]
            grain = np.array([rng.uniform(-17.0, 17.0) for _ in offsets], dtype=np.float32)[:, None]
            paper_tone = region * 0.74 + np.array((222.0, 201.0, 160.0), dtype=np.float32) * 0.26 + grain
            pixels[x, start:end] = region * (1.0 - blend[:, None]) + paper_tone * blend[:, None]
            self._erase_torn_notch(pixels, x, edge, tears[x], horizontal=True)

    def _blend_vertical(self, pixels: np.ndarray, seam: int, width: int, height: int, rng: random.Random) -> None:
        depth = self.depth
        anchors = [rng.uniform(-depth * 0.58, depth * 0.58) for _ in range(max(2, height // 90 + 2))]
        tears = self._tear_mask(height, rng)
        for y in range(height):
            roughness = int(self._interpolate(anchors, y / 90.0) + math.sin(y * 0.035 + 0.8) * 4 + math.sin(y * 0.19) * 2 + rng.uniform(-3.0, 3.0))
            edge = max(1, min(width - 2, seam + roughness))
            local_depth = max(4, depth + int(math.sin(y * 0.027) * depth * 0.18) + int(rng.uniform(-depth * 0.12, depth * 0.12)))
            start, end = max(0, edge - local_depth), min(width, edge + local_depth + 1)
            offsets = np.arange(start - edge, end - edge, dtype=np.float32)
            blend = self.strength * np.maximum(0.0, 1.0 - np.abs(offsets) / (local_depth + 1)) ** 0.8
            region = pixels[start:end, y]
            grain = np.array([rng.uniform(-17.0, 17.0) for _ in offsets], dtype=np.float32)[:, None]
            paper_tone = region * 0.74 + np.array((222.0, 201.0, 160.0), dtype=np.float32) * 0.26 + grain
            pixels[start:end, y] = region * (1.0 - blend[:, None]) + paper_tone * blend[:, None]
            self._erase_torn_notch(pixels, edge, y, tears[y], horizontal=False)

    @staticmethod
    def _interpolate(anchors, position: float) -> float:
        """Interpola puntos aleatorios para formar una silueta quebrada continua."""
        idx = min(int(position), len(anchors) - 2)
        t = max(0.0, min(1.0, position - idx))
        t = t * t * (3.0 - 2.0 * t)
        return anchors[idx] * (1.0 - t) + anchors[idx + 1] * t

    def _tear_mask(self, length: int, rng: random.Random):
        key = (length, self.seed, self.depth)
        if key not in self._tear_cache:
            mask = [0] * length
            # Rajas pequeñas y dispersas. La separación mínima evita que la
            # costura se convierta en una línea perforada continua.
            pos = rng.randint(18, 48)
            while pos < length - 8:
                if rng.random() < 0.52:
                    mask[pos] = rng.randint(5, max(6, self.depth // 2))
                pos += rng.randint(35, 100)
            self._tear_cache[key] = mask
        return self._tear_cache[key]

    @staticmethod
    def _erase_torn_notch(pixels, x: int, y: int, size: int, horizontal: bool) -> None:
        """Abre muescas diminutas que simulan papel partido y dejan ver el fondo."""
        if size <= 0:
            return
        h, w = pixels.shape[:2]
        for offset in range(size):
            spread = max(1, size - offset)
            if horizontal:
                yy = y + offset
                if 0 <= yy < h:
                    pixels[max(0, x - spread // 2):min(w, x + spread // 2 + 1), yy] *= 0.58
            else:
                xx = x + offset
                if 0 <= xx < w:
                    pixels[xx, max(0, y - spread // 2):min(h, y + spread // 2 + 1)] *= 0.58
