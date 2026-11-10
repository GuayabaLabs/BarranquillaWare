import math
import random
import struct
import pygame
from typing import List, Tuple, Any

class GLPetal:
    """Partícula de pétalo de flor cayendo para el Menú Principal."""
    def __init__(self, screen_w: int = 1920, screen_h: int = 1080) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.x: float = 0.0
        self.y: float = 0.0
        self.speed_x: float = 0.0
        self.speed_y: float = 0.0
        self.size_w: float = 0.0
        self.size_h: float = 0.0
        self.rot_z: float = 0.0
        self.rot_z_speed: float = 0.0
        self.rot_y: float = 0.0
        self.rot_y_speed: float = 0.0
        self.phase: float = 0.0
        self.color: Tuple[float, float, float, float] = (1.0, 0.5, 0.7, 0.8)
        self.reset(random_y=True)

    def reset(self, random_y: bool = False) -> None:
        self.x = random.uniform(-50, self.screen_w + 50)
        self.y = random.uniform(-20, self.screen_h) if random_y else random.uniform(-60, -15)
        self.speed_y = random.uniform(50.0, 115.0)
        self.speed_x = random.uniform(30.0, 75.0)
        self.size_w = random.uniform(22.0, 38.0)
        self.size_h = self.size_w * random.uniform(0.5, 0.65)
        self.rot_z = random.uniform(0, math.pi * 2)
        self.rot_z_speed = random.uniform(-1.2, 1.2)
        self.rot_y = random.uniform(0, math.pi * 2)
        self.rot_y_speed = random.uniform(1.5, 3.5)
        self.phase = random.uniform(0, math.pi * 2)

        palettes = [
            (1.0, 0.42, 0.62, 0.88),  # Rosado vibrante
            (1.0, 0.55, 0.72, 0.85),  # Rosa pastel
            (0.96, 0.32, 0.58, 0.90), # Fucsia suave
            (1.0, 0.65, 0.78, 0.82),  # Flor clara
        ]
        self.color = random.choice(palettes)

    def update(self, dt: float) -> None:
        self.phase += 2.2 * dt
        self.x += (self.speed_x + math.sin(self.phase) * 50.0) * dt
        self.y += self.speed_y * dt
        self.rot_z += self.rot_z_speed * dt
        self.rot_y += self.rot_y_speed * dt

        if self.y > self.screen_h + 40 or self.x > self.screen_w + 60:
            self.reset(random_y=False)


class GLSparkle:
    """
    Partícula ambiental de punto blanco semi-transparente (estilo bokeh / polvo estelar suave).
    Asciende suavemente con oscilación lateral sin sobrecargar la escena.
    """
    def __init__(self, screen_w: int = 1920, screen_h: int = 1080) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.x: float = 0.0
        self.y: float = 0.0
        self.speed_x: float = 0.0
        self.speed_y: float = 0.0
        self.size_w: float = 0.0
        self.size_h: float = 0.0
        self.rot_z: float = 0.0
        self.rot_z_speed: float = 0.0
        self.rot_y: float = 0.0
        self.rot_y_speed: float = 0.0
        self.phase: float = 0.0
        self.color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 0.40)
        self.reset(random_y=True)

    def reset(self, random_y: bool = False) -> None:
        self.x = random.uniform(20, self.screen_w - 20)
        self.y = random.uniform(20, self.screen_h) if random_y else random.uniform(self.screen_h + 10, self.screen_h + 50)
        self.speed_y = random.uniform(-25.0, -65.0)  # Flota suavemente hacia arriba
        self.speed_x = random.uniform(-10.0, 10.0)
        self.size_w = random.uniform(10.0, 20.0)
        self.size_h = self.size_w  # Punto circular
        self.rot_z = random.uniform(0, math.pi * 2)
        self.rot_z_speed = random.uniform(-0.8, 0.8)
        self.rot_y = random.uniform(0, math.pi * 2)
        self.rot_y_speed = random.uniform(0.5, 1.5)
        self.phase = random.uniform(0, math.pi * 2)

        # Tonos blancos semi-transparentes suaves (25% a 55% de opacidad)
        alpha = random.uniform(0.25, 0.55)
        self.color = (1.0, 1.0, 1.0, alpha)

    def update(self, dt: float) -> None:
        self.phase += 1.8 * dt
        self.x += (self.speed_x + math.sin(self.phase) * 20.0) * dt
        self.y += self.speed_y * dt
        self.rot_z += self.rot_z_speed * dt
        self.rot_y += self.rot_y_speed * dt

        if self.y < -30 or self.x < -30 or self.x > self.screen_w + 30:
            self.reset(random_y=False)


class GLParticleSystem:
    """
    Sistema de partículas acelerado por GPU con Shaders ModernGL (1080p).
    Soporta:
    - 'petals': Pétalos rosados cayendo para el Menú Principal.
    - 'sparkles': Destellos dorados y bokeh de likes ascendentes para Selección de Personaje.
    """
    def __init__(
        self,
        count: int = 36,
        screen_w: int = 1920,
        screen_h: int = 1080,
        particle_type: str = "petals"
    ) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.particle_type = particle_type
        if particle_type == "sparkles":
            self.particles: List[Any] = [GLSparkle(screen_w, screen_h) for _ in range(count)]
        else:
            self.particles = [GLPetal(screen_w, screen_h) for _ in range(count)]
        self._buffer = bytearray(len(self.particles) * 40)

    @property
    def count(self) -> int:
        return len(self.particles)

    def update(self, dt: float) -> None:
        for p in self.particles:
            p.update(dt)

    def get_instance_bytes(self) -> bytes:
        """Empaqueta todas las partículas en formato binario continuo para el VBO (10 floats = 40 bytes)."""
        struct_format = "ffffffffff"
        offset = 0
        for p in self.particles:
            struct.pack_into(
                struct_format,
                self._buffer,
                offset,
                p.x, p.y,
                p.size_w, p.size_h,
                p.rot_z, p.rot_y,
                p.color[0], p.color[1], p.color[2], p.color[3]
            )
            offset += 40
        return bytes(self._buffer)

    def render_software(self, surface: pygame.Surface) -> None:
        """Fallback limpio para pruebas automatizadas o ejecución headless."""
        for p in self.particles:
            w = max(2, int(p.size_w * abs(math.cos(p.rot_y))))
            h = max(2, int(p.size_h))
            part_surf = pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)
            color_255 = (
                int(p.color[0] * 255),
                int(p.color[1] * 255),
                int(p.color[2] * 255),
                int(p.color[3] * 255)
            )
            pygame.draw.ellipse(part_surf, color_255, (w // 2, h // 2, w, h))
            rotated = pygame.transform.rotate(part_surf, math.degrees(p.rot_z))
            surface.blit(rotated, rotated.get_rect(center=(int(p.x), int(p.y))))
