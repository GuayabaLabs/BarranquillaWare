import math
from typing import Optional, Callable
import pygame

from core.microgame import BaseMicrogame

class MetropolitanoPenaltyMicrogame(BaseMicrogame):
    """
    Microjuego 2: 'El Penal del Tiburón' (Estadio Metropolitano Roberto Meléndez).
    - Consigna: ¡PATEA AL ARCO!
    - Mecánica: Una mira oscilante se mueve horizontalmente a lo largo de los postes.
      Pulsa ESPACIO o haz click para rematar cuando la flecha esté dentro de la red
      para vencer al arquero rival antes de que se agote el tiempo.
    """
    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡PATEA AL ARCO!",
            time_limit=4.0,
            on_complete_callback=on_complete_callback
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("PenalMusic.mp3")

    def setup_game(self) -> None:
        self.goal_x = 560
        self.goal_w = 800
        self.goal_y = 280
        self.goal_h = 360

        # Mira oscilante
        self.aim_x = float(self.goal_x + self.goal_w // 2)
        self.aim_speed = 780.0
        self.aim_dir = 1.0

        # Balón de fútbol
        self.ball_x = float(self.screen_w // 2)
        self.ball_y = 860.0
        self.ball_target_x = self.ball_x
        self.ball_target_y = float(self.goal_y + self.goal_h // 2)
        self.ball_shot = False
        self.ball_flight_t = 0.0

        # Arquero
        self.keeper_x = float(self.goal_x + self.goal_w // 2)
        self.keeper_dir = -1.0
        self.keeper_speed = 320.0

        # Cargar sprite del personaje tirador
        sprite_filename = f"{self.character_id}_seleccion_personaje.png"
        try:
            raw_sprite = self.assets.load_surface(sprite_filename, has_alpha=True)
            mask = pygame.mask.from_surface(raw_sprite)
            rects = mask.get_bounding_rects()
            cropped = raw_sprite.subsurface(rects[0]) if rects else raw_sprite
            target_h = 230
            target_w = int(cropped.get_width() * (target_h / float(cropped.get_height())))
            self.kicker_sprite = pygame.transform.smoothscale(cropped, (target_w, target_h))
        except Exception:
            self.kicker_sprite = None

        self.font_stadium = pygame.font.SysFont("Arial Black, Impact, sans-serif", 32)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        # Disparo con ESPACIO o CLICK izquierdo
        if not self.ball_shot:
            if (event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_RETURN)) or \
               (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                self.ball_shot = True
                self.ball_target_x = self.aim_x
                if hasattr(self.audio, "play_click"):
                    self.audio.play_click()

    def update_game(self, dt: float) -> None:
        # 1. Oscilación de la mira mientras no se haya pateado
        if not self.ball_shot:
            self.aim_x += self.aim_speed * self.aim_dir * dt
            if self.aim_x > self.goal_x + self.goal_w - 40:
                self.aim_x = self.goal_x + self.goal_w - 40
                self.aim_dir = -1.0
            elif self.aim_x < self.goal_x + 40:
                self.aim_x = self.goal_x + 40
                self.aim_dir = 1.0

        # 2. Desplazamiento del arquero
        self.keeper_x += self.keeper_speed * self.keeper_dir * dt
        if self.keeper_x > self.goal_x + self.goal_w - 180:
            self.keeper_x = self.goal_x + self.goal_w - 180
            self.keeper_dir = -1.0
        elif self.keeper_x < self.goal_x + 180:
            self.keeper_x = self.goal_x + 180
            self.keeper_dir = 1.0

        # 3. Trayectoria del balón en el aire
        if self.ball_shot and not self.is_finished:
            self.ball_flight_t += dt * 3.5
            t = min(1.0, self.ball_flight_t)
            self.ball_x += (self.ball_target_x - self.ball_x) * min(1.0, dt * 14.0)
            self.ball_y = 860.0 + (self.ball_target_y - 860.0) * t - math.sin(t * math.pi) * 140.0

            if t >= 0.95:
                # Evaluar si el arquero tapó el balón (distancia horizontal)
                dist_to_keeper = abs(self.ball_x - self.keeper_x)
                # Si está lejos del arquero y dentro de los postes, es GOL
                if dist_to_keeper > 90.0 and (self.goal_x + 20 < self.ball_x < self.goal_x + self.goal_w - 20):
                    self.finish_game(won=True)
                else:
                    self.finish_game(won=False)

    def render_game(self, surface: pygame.Surface) -> None:
        # 1. Graderías del Estadio Metropolitano (Franjas rojiblancas del Junior)
        surface.fill((45, 60, 95))
        for r_y in range(0, 260, 26):
            col = (215, 45, 45) if (r_y // 26) % 2 == 0 else (245, 245, 250)
            pygame.draw.rect(surface, col, (0, r_y, self.screen_w, 24))

        # Cancha de grama verde tropical
        grass_y = 520
        pygame.draw.rect(surface, (60, 165, 75), (0, grass_y, self.screen_w, self.screen_h - grass_y))
        pygame.draw.line(surface, (255, 255, 255), (0, grass_y), (self.screen_w, grass_y), 4)

        # 2. Arco de fútbol con red
        # Red
        net_surf = pygame.Surface((self.goal_w, self.goal_h), pygame.SRCALPHA)
        net_surf.fill((250, 250, 250, 75))
        for nx in range(0, self.goal_w, 28):
            pygame.draw.line(net_surf, (220, 220, 220, 140), (nx, 0), (nx, self.goal_h), 1)
        for ny in range(0, self.goal_h, 28):
            pygame.draw.line(net_surf, (220, 220, 220, 140), (0, ny), (self.goal_w, ny), 1)
        surface.blit(net_surf, (self.goal_x, self.goal_y))

        # Postes y travesaño blanco grueso
        pygame.draw.line(surface, (255, 255, 255), (self.goal_x, self.goal_y + self.goal_h), (self.goal_x, self.goal_y), 12)
        pygame.draw.line(surface, (255, 255, 255), (self.goal_x + self.goal_w, self.goal_y + self.goal_h), (self.goal_x + self.goal_w, self.goal_y), 12)
        pygame.draw.line(surface, (255, 255, 255), (self.goal_x, self.goal_y), (self.goal_x + self.goal_w, self.goal_y), 12)

        # 3. Arquero rival (Buzo amarillo neón)
        kw, kh = 90, 160
        kx = int(self.keeper_x - kw // 2)
        ky = int(self.goal_y + self.goal_h - kh + 10)
        # Sombra del arquero
        pygame.draw.ellipse(surface, (25, 45, 25, 100), (kx, ky + kh - 12, kw, 20))
        # Cuerpo y guantes
        pygame.draw.rect(surface, (235, 245, 40), (kx + 15, ky + 40, kw - 30, 80), border_radius=8)
        pygame.draw.circle(surface, (255, 220, 180), (kx + kw // 2, ky + 25), 20) # Cabeza
        pygame.draw.rect(surface, (40, 50, 70), (kx + 20, ky + 120, kw - 40, 40)) # Pantaloneta
        # Guantes extendidos
        pygame.draw.circle(surface, (255, 120, 30), (kx + 8, ky + 55), 14)
        pygame.draw.circle(surface, (255, 120, 30), (kx + kw - 8, ky + 55), 14)

        # 4. Mira oscilante de puntería (si el balón no ha salido)
        if not self.ball_shot:
            aim_y = self.goal_y + self.goal_h - 40
            pygame.draw.circle(surface, (255, 230, 60), (int(self.aim_x), aim_y), 24, 3)
            pygame.draw.circle(surface, (255, 60, 60), (int(self.aim_x), aim_y), 8)
            # Flecha vertical
            pygame.draw.line(surface, (255, 230, 60), (int(self.aim_x), aim_y - 35), (int(self.aim_x), aim_y - 12), 4)

        # 5. Balón de fútbol (con escala que se reduce en la lejanía)
        ball_scale = max(0.45, 1.0 - (self.ball_flight_t * 0.45))
        ball_r = int(24 * ball_scale)
        bx, by = int(self.ball_x), int(self.ball_y)
        pygame.draw.circle(surface, (20, 35, 20, 80), (bx, by + ball_r + 4), int(ball_r * 1.1)) # Sombra
        pygame.draw.circle(surface, (255, 255, 255), (bx, by), ball_r)
        pygame.draw.circle(surface, (25, 25, 25), (bx, by), int(ball_r * 0.45))
        pygame.draw.circle(surface, (20, 20, 20), (bx, by), ball_r, width=2)

        # 6. Personaje pateador en la parte inferior izquierda
        if self.kicker_sprite:
            surface.blit(self.kicker_sprite, (320, 760))

        # Indicador inferior
        if self.phase == self.PHASE_PLAY and not self.ball_shot:
            tip_rect = pygame.Rect(self.screen_w // 2 - 270, 960, 540, 48)
            pygame.draw.rect(surface, (20, 25, 40, 220), tip_rect, border_radius=24)
            pygame.draw.rect(surface, (245, 205, 95), tip_rect, width=2, border_radius=24)
            font_tip = pygame.font.SysFont("Arial, sans-serif", 18, bold=True)
            txt_tip = font_tip.render("⚽ ¡PULSA ESPACIO PARA CLAVARLA AL ÁNGULO!", True, (255, 255, 255))
            surface.blit(txt_tip, txt_tip.get_rect(center=tip_rect.center))
