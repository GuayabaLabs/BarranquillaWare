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
