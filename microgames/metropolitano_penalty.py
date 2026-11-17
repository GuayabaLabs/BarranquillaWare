import math
from typing import Optional, Callable
import pygame

from core.microgame import BaseMicrogame

INK_DARK = (78, 51, 35)


class MetropolitanoPenaltyMicrogame(BaseMicrogame):
    # Control por movimiento: gestos de cámara -> teclas del juego (ver BaseMicrogame).
    CAMERA_ACTIONS = {"accion": pygame.K_SPACE}
    """
    Microjuego 2: 'El Penal del Tiburón' (Estadio Metropolitano Roberto Meléndez).
    - Temática social: Ignora la presión de los comentarios en vivo y confía en tu tiro.
    - Mecánica: Mira oscilante sobre el arco; pulsa ESPACIO / CLICK para rematar.
    """

    LIVE_COMMENTS = (
        "@hater_99: ¡Seguro la botas!",
        "@en_vivo: 14.2K mirando...",
        "@troll_fut: ¡Presión total!",
    )

    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡IGNORA EL HATE Y PATEA!",
            time_limit=4.0,
            on_complete_callback=on_complete_callback,
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("PenalMusic.mp3")

    def setup_game(self) -> None:
        self.goal_x = 560
        self.goal_w = 800
        self.goal_y = 280
        self.goal_h = 360

        self.aim_x = float(self.goal_x + self.goal_w // 2)
        self.aim_speed = 780.0
        self.aim_dir = 1.0

        self.ball_x = float(self.screen_w // 2)
        self.ball_y = 860.0
        self.ball_target_x = self.ball_x
        self.ball_target_y = float(self.goal_y + self.goal_h // 2)
        self.ball_shot = False
        self.ball_flight_t = 0.0

        self.keeper_x = float(self.goal_x + self.goal_w // 2)
        self.keeper_dir = -1.0
        self.keeper_speed = 320.0
        self.elapsed_anim = 0.0

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

        self.font_stadium = self.assets.cargarFuenteCuento(24)
        self.font_small = self.assets.cargarFuenteCuento(18)
        self.backdrop_surf = self._build_backdrop_surface()

    def _build_backdrop_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.screen_w, self.screen_h))
        # Cielo atardecer barranquillero
        for y in range(0, 260, 8):
            t = y / 260.0
            r = int(112 * (1 - t) + 236 * t)
            g = int(156 * (1 - t) + 178 * t)
            b = int(206 * (1 - t) + 148 * t)
            surf.fill((r, g, b), (0, y, self.screen_w, 8))

        # Graderías rojiblancas acuarela del Metropolitano
        for r_y in range(80, 270, 26):
            col = (212, 68, 68) if (r_y // 26) % 2 == 0 else (248, 242, 232)
            pygame.draw.rect(surf, col, (0, r_y, self.screen_w, 24))
        pygame.draw.line(surf, INK_DARK, (0, 270), (self.screen_w, 270), 3)

        # Grama verde acuarela con franjas suaves
        grass_y = 520
        pygame.draw.rect(surf, (92, 168, 96), (0, grass_y, self.screen_w, self.screen_h - grass_y))
        for gx in range(0, self.screen_w, 160):
            if (gx // 160) % 2 == 0:
                pygame.draw.rect(surf, (82, 154, 88), (gx, grass_y, 160, self.screen_h - grass_y))
        pygame.draw.rect(surf, (78, 146, 84), (0, 270, self.screen_w, grass_y - 270))
        pygame.draw.line(surf, (250, 246, 236), (0, grass_y), (self.screen_w, grass_y), 5)

        # Área grande en perspectiva
        pygame.draw.polygon(
            surf,
            (250, 246, 236),
            [(460, grass_y), (1460, grass_y), (1680, 920), (240, 920)],
            width=4,
        )
        return surf

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if not self.ball_shot:
            if (event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_RETURN)) or (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            ):
                self.ball_shot = True
                self.ball_target_x = self.aim_x
                if hasattr(self.audio, "play_click"):
                    self.audio.play_click()

    def update_game(self, dt: float) -> None:
        self.elapsed_anim += dt
        if not self.ball_shot:
            self.aim_x += self.aim_speed * self.aim_dir * dt
            if self.aim_x > self.goal_x + self.goal_w - 40:
                self.aim_x = self.goal_x + self.goal_w - 40
                self.aim_dir = -1.0
            elif self.aim_x < self.goal_x + 40:
                self.aim_x = self.goal_x + 40
                self.aim_dir = 1.0

        self.keeper_x += self.keeper_speed * self.keeper_dir * dt
        if self.keeper_x > self.goal_x + self.goal_w - 180:
            self.keeper_x = self.goal_x + self.goal_w - 180
            self.keeper_dir = -1.0
        elif self.keeper_x < self.goal_x + 180:
            self.keeper_x = self.goal_x + 180
            self.keeper_dir = 1.0

        if self.ball_shot and not self.is_finished:
            self.ball_flight_t += dt * 3.5
            t = min(1.0, self.ball_flight_t)
            self.ball_x += (self.ball_target_x - self.ball_x) * min(1.0, dt * 14.0)
            self.ball_y = 860.0 + (self.ball_target_y - 860.0) * t - math.sin(t * math.pi) * 140.0

            if t >= 0.95:
                dist_to_keeper = abs(self.ball_x - self.keeper_x)
                if dist_to_keeper > 90.0 and (self.goal_x + 20 < self.ball_x < self.goal_x + self.goal_w - 20):
                    self.outro_message = "¡GOLAZO SIN PRESIÓN!"
                    self.finish_game(won=True)
                else:
                    self.outro_message = "¡TE GANÓ LA PRESIÓN!"
                    self.finish_game(won=False)

    def render_game(self, surface: pygame.Surface) -> None:
        surface.blit(self.backdrop_surf, (0, 0))

        # Arco de fútbol con red
        net_surf = pygame.Surface((self.goal_w, self.goal_h), pygame.SRCALPHA)
        net_surf.fill((252, 248, 240, 82))
        for nx in range(0, self.goal_w, 28):
            pygame.draw.line(net_surf, (220, 212, 198, 150), (nx, 0), (nx, self.goal_h), 1)
        for ny in range(0, self.goal_h, 28):
            pygame.draw.line(net_surf, (220, 212, 198, 150), (0, ny), (self.goal_w, ny), 1)
        surface.blit(net_surf, (self.goal_x, self.goal_y))

        pygame.draw.line(surface, (252, 248, 240), (self.goal_x, self.goal_y + self.goal_h), (self.goal_x, self.goal_y), 12)
        pygame.draw.line(surface, (252, 248, 240), (self.goal_x + self.goal_w, self.goal_y + self.goal_h), (self.goal_x + self.goal_w, self.goal_y), 12)
        pygame.draw.line(surface, (252, 248, 240), (self.goal_x, self.goal_y), (self.goal_x + self.goal_w, self.goal_y), 12)

        # Arquero rival
        kw, kh = 90, 160
        kx = int(self.keeper_x - kw // 2)
        ky = int(self.goal_y + self.goal_h - kh + 10)
        shadow = pygame.Surface((kw, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (30, 50, 30, 100), (0, 0, kw, 22))
        surface.blit(shadow, (kx, ky + kh - 12))
        pygame.draw.rect(surface, (245, 208, 62), (kx + 15, ky + 40, kw - 30, 80), border_radius=8)
        pygame.draw.rect(surface, INK_DARK, (kx + 15, ky + 40, kw - 30, 80), width=2, border_radius=8)
        pygame.draw.circle(surface, (246, 208, 174), (kx + kw // 2, ky + 25), 20)
        pygame.draw.circle(surface, INK_DARK, (kx + kw // 2, ky + 25), 20, width=2)
        pygame.draw.rect(surface, (52, 62, 82), (kx + 20, ky + 120, kw - 40, 40))
        pygame.draw.circle(surface, (238, 106, 52), (kx + 8, ky + 55), 14)
        pygame.draw.circle(surface, (238, 106, 52), (kx + kw - 8, ky + 55), 14)

        # Mira oscilante
        if not self.ball_shot:
            aim_y = self.goal_y + self.goal_h - 40
            pygame.draw.circle(surface, (252, 214, 68), (int(self.aim_x), aim_y), 24, 4)
            pygame.draw.circle(surface, (226, 62, 66), (int(self.aim_x), aim_y), 9)
            pygame.draw.line(surface, (252, 214, 68), (int(self.aim_x), aim_y - 36), (int(self.aim_x), aim_y - 12), 4)

        # Balón
        ball_scale = max(0.45, 1.0 - (self.ball_flight_t * 0.45))
        ball_r = int(24 * ball_scale)
        bx, by = int(self.ball_x), int(self.ball_y)
        pygame.draw.circle(surface, (252, 248, 240), (bx, by), ball_r)
        pygame.draw.circle(surface, INK_DARK, (bx, by), int(ball_r * 0.42))
        pygame.draw.circle(surface, INK_DARK, (bx, by), ball_r, width=2)

        if self.kicker_sprite:
            surface.blit(self.kicker_sprite, (320, 760))

        # Feed de presión en vivo (fenómeno redes sociales)
        for idx, msg in enumerate(self.LIVE_COMMENTS):
            bob = math.sin(self.elapsed_anim * 3.5 + idx) * 6.0
            pill = pygame.Rect(1510, int(330 + idx * 72 + bob), 350, 52)
            p_surf = pygame.Surface(pill.size, pygame.SRCALPHA)
            pygame.draw.rect(p_surf, (252, 244, 228, 226), (0, 0, pill.width, pill.height), border_radius=14)
            pygame.draw.rect(p_surf, (212, 68, 72, 210), (0, 0, pill.width, pill.height), width=2, border_radius=14)
            txt_c = self.font_small.render(msg, True, INK_DARK)
            p_surf.blit(txt_c, txt_c.get_rect(center=(pill.width // 2, pill.height // 2)))
            surface.blit(p_surf, pill)

        # Banner superior de temática social
        top_pill = pygame.Rect(self.screen_w // 2 - 350, 24, 700, 48)
        pygame.draw.rect(surface, (252, 244, 228), top_pill, border_radius=20)
        pygame.draw.rect(surface, INK_DARK, top_pill, width=3, border_radius=20)
        txt_top = self.font_stadium.render("IGNORA LA PRESIÓN EN VIVO · ¡CONFÍA EN TU TIRO!", True, INK_DARK)
        surface.blit(txt_top, txt_top.get_rect(center=top_pill.center))

        if self.phase == self.PHASE_PLAY and not self.ball_shot:
            tip_rect = pygame.Rect(self.screen_w // 2 - 310, 956, 620, 48)
            pygame.draw.rect(surface, (252, 244, 228), tip_rect, border_radius=22)
            pygame.draw.rect(surface, INK_DARK, tip_rect, width=3, border_radius=22)
            txt_tip = self.font_small.render("PULSA [ESPACIO] O CLICK PARA CLAVARLA AL ÁNGULO", True, INK_DARK)
            surface.blit(txt_tip, txt_tip.get_rect(center=tip_rect.center))
