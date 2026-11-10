import math
from typing import Optional, Callable
import pygame

from core.microgame import BaseMicrogame

class UninorteSprintMicrogame(BaseMicrogame):
    """
    Microjuego 1: 'Carrera a la clase de 6:30' (Campus Uninorte).
    - Consigna: ¡LLEGA AL SALÓN!
    - Mecánica: Pulsa repetidamente ESPACIO o haz click veloz para correr por el pasillo
      antes de que el profesor cierre la puerta a las 6:30 AM.
    """
    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡LLEGA AL SALÓN!",
            time_limit=4.0,
            on_complete_callback=on_complete_callback
        )

    def setup_game(self) -> None:
        self.player_x = 180.0
        self.player_target_x = 1520.0
        self.player_y = 680.0
        self.step_power = 65.0
        self.step_bob = 0.0

        # Puerta del salón
        self.door_x = 1580
        self.door_closed = False
        self.door_close_anim = 0.0

        # Cargar sprite del personaje activo si está disponible
        sprite_filename = f"{self.character_id}_seleccion_personaje.png"
        try:
            raw_sprite = self.assets.load_surface(sprite_filename, has_alpha=True)
            # Recortar tight
            mask = pygame.mask.from_surface(raw_sprite)
            rects = mask.get_bounding_rects()
            if rects:
                cropped = raw_sprite.subsurface(rects[0])
            else:
                cropped = raw_sprite
            target_h = 240
            target_w = int(cropped.get_width() * (target_h / float(cropped.get_height())))
            self.player_sprite = pygame.transform.smoothscale(cropped, (target_w, target_h))
        except Exception:
            self.player_sprite = None

        # Tipografía de la puerta del salón
        self.font_door = pygame.font.SysFont("Arial Black, Impact, sans-serif", 20)
        self.font_clock = pygame.font.SysFont("Arial Black, Impact, sans-serif", 36)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        # Acelerar con ESPACIO o CLICK izquierdo
        if (event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RIGHT, pygame.K_d)) or \
           (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self.player_x += self.step_power
            self.step_bob = math.pi
            if hasattr(self.audio, "play_hover"):
                self.audio.play_hover()

            # Condición de Victoria
            if self.player_x >= self.player_target_x and not self.is_finished:
                self.finish_game(won=True)

    def update_game(self, dt: float) -> None:
        # Decaimiento del paso elástico
        if self.step_bob > 0.0:
            self.step_bob = max(0.0, self.step_bob - dt * 14.0)

        # Animación de la puerta cerrándose en el último segundo
        if self.time_left < 1.0 and not self.is_won:
            self.door_close_anim = min(1.0, self.door_close_anim + dt * 2.5)

    def render_game(self, surface: pygame.Surface) -> None:
        # 1. Fondo: Pasillo de Uninorte
        # Cielo / Jardín a través de las ventanas superiores
        surface.fill((135, 205, 245))

        # Suelo del pasillo (baldosas de terracota cálida de Uninorte)
        floor_y = 620
        pygame.draw.rect(surface, (215, 125, 75), (0, floor_y, self.screen_w, self.screen_h - floor_y))
        pygame.draw.line(surface, (140, 65, 30), (0, floor_y), (self.screen_w, floor_y), 4)

        # Pared del fondo con ventanas
        wall_y = 220
        pygame.draw.rect(surface, (245, 240, 225), (0, wall_y, self.screen_w, floor_y - wall_y))
        pygame.draw.line(surface, (190, 180, 165), (0, wall_y), (self.screen_w, wall_y), 3)

        # Ventanales al jardín caribeño
        for vx in range(120, 1400, 320):
            pygame.draw.rect(surface, (110, 190, 235), (vx, 260, 220, 280), border_radius=12)
            pygame.draw.rect(surface, (255, 255, 255), (vx, 260, 220, 280), width=6, border_radius=12)
            # Palmeras visibles afuera
            pygame.draw.circle(surface, (65, 175, 80), (vx + 110, 360), 65)
            pygame.draw.circle(surface, (45, 145, 60), (vx + 70, 380), 45)

        # 2. Reloj de pared del pasillo ("06:29 AM" -> "06:30 AM")
        clock_rect = pygame.Rect(780, 80, 240, 70)
        pygame.draw.rect(surface, (20, 25, 40), clock_rect, border_radius=14)
        pygame.draw.rect(surface, (240, 195, 90), clock_rect, width=3, border_radius=14)
        clock_str = "06:29 AM" if self.time_left > 0.8 else "06:30 AM!"
        clock_col = (255, 240, 120) if self.time_left > 0.8 else (255, 80, 80)
        txt_c = self.font_clock.render(clock_str, True, clock_col)
        surface.blit(txt_c, txt_c.get_rect(center=clock_rect.center))

        # 3. Puerta del Salón (Bloque K / Ingeniería)
        door_w, door_h = 160, 360
        door_x = self.door_x
        door_y = floor_y - door_h + 20

        # Marco de la puerta
        pygame.draw.rect(surface, (70, 50, 40), (door_x - 10, door_y - 10, door_w + 20, door_h + 10), border_radius=6)
        # Interior iluminado del salón
        pygame.draw.rect(surface, (255, 250, 190), (door_x, door_y, door_w, door_h))

        # Hoja de la puerta cerrándose
        cur_door_w = int(door_w * (1.0 if not self.is_won and self.is_finished else self.door_close_anim))
        if cur_door_w > 0:
            pygame.draw.rect(surface, (140, 85, 55), (door_x, door_y, cur_door_w, door_h))
            pygame.draw.circle(surface, (240, 210, 90), (door_x + cur_door_w - 18, door_y + door_h // 2), 7)

        # Letrero sobre la puerta
        badge_rect = pygame.Rect(door_x - 15, door_y - 48, door_w + 30, 36)
        pygame.draw.rect(surface, (255, 255, 255), badge_rect, border_radius=8)
        pygame.draw.rect(surface, (40, 50, 70), badge_rect, width=2, border_radius=8)
        txt_d = self.font_door.render("AULA 204 • ING", True, (35, 45, 65))
        surface.blit(txt_d, txt_d.get_rect(center=badge_rect.center))

        # 4. Render del Jugador corriendo con bounce elástico
        bob = math.sin(self.step_bob) * 16.0
        px = int(self.player_x)
        py = int(self.player_y - bob)

        # Sombra en el suelo
        shadow_w = 110 + int(bob * 0.5)
        shadow_h = 24
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (30, 20, 15, 80), (0, 0, shadow_w, shadow_h))
        surface.blit(shadow_surf, shadow_surf.get_rect(center=(px + 45, floor_y + 10)))

        # Sprite del personaje
        if self.player_sprite:
            surface.blit(self.player_sprite, (px, py - self.player_sprite.get_height()))
        else:
            # Fallback geométrico limpio
            pygame.draw.rect(surface, (60, 130, 220), (px, py - 180, 90, 180), border_radius=16)

        # 5. Indicador en pantalla: '¡PULSA ESPACIO / CLICK RÁPIDO!'
        if self.phase == self.PHASE_PLAY:
            tip_rect = pygame.Rect(self.screen_w // 2 - 280, 860, 560, 48)
            pygame.draw.rect(surface, (20, 25, 40, 210), tip_rect, border_radius=24)
            pygame.draw.rect(surface, (245, 205, 95), tip_rect, width=2, border_radius=24)
            font_tip = pygame.font.SysFont("Arial, sans-serif", 18, bold=True)
            txt_tip = font_tip.render("⌨️ ¡PULSA ESPACIO O HAZ CLICK VELOZMENTE!", True, (255, 255, 255))
            surface.blit(txt_tip, txt_tip.get_rect(center=tip_rect.center))
