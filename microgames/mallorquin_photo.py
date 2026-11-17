import math
import random
from typing import Optional, Callable
import pygame
from core import input_state

from core.microgame import BaseMicrogame

INK_DARK = (78, 51, 35)


class MallorquinPhotoMicrogame(BaseMicrogame):
    # Control por movimiento: gestos de cámara -> teclas del juego (ver BaseMicrogame).
    CAMERA_ACTIONS = {"eje_x": (pygame.K_LEFT, pygame.K_RIGHT), "eje_y": (pygame.K_UP, pygame.K_DOWN), "accion": pygame.K_SPACE}
    """
    Microjuego 3: '¡Fotografía al Flamenco!' (Ecorreserva Ciénaga de Mallorquín).
    - Temática social: Vive y observa el momento real sin filtros antes de postear por likes.
    - Mecánica: Encuadra al flamenco volando entre manglares con mouse/flechas y dispara con ESPACIO o CLICK.
    """

    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡ENCUADRA SIN FILTROS!",
            time_limit=4.0,
            on_complete_callback=on_complete_callback,
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("tranquilaMusic.mp3")

    def setup_game(self) -> None:
        self.photo_taken: bool = False
        self.shutter_flash_alpha: float = 0.0
        self.photo_success: bool = False
        self.polaroid_anim_t: float = 0.0

        self.reticle_radius: int = 85
        self.reticle_x: float = float(self.screen_w // 2)
        self.reticle_y: float = float(self.screen_h // 2)

        self.flamingo_x: float = -120.0
        self.flamingo_base_y: float = float(random.randint(320, 560))
        self.flamingo_speed: float = random.uniform(640.0, 780.0)
        self.flamingo_phase: float = random.uniform(0.0, math.pi * 2)
        self.flamingo_y: float = self.flamingo_base_y + math.sin(self.flamingo_phase) * 36.0
        self.flamingo_w: int = 140
        self.flamingo_h: int = 110

        self.font_hud = self.assets.cargarFuenteCuento(19)
        self.font_label = self.assets.cargarFuenteCuento(18)
        self.font_banner = self.assets.cargarFuenteCuento(23)

        self.flamingo_surf = self._create_flamingo_surface()
        self.backdrop_surf = self._create_backdrop_surface()
        self._load_character_photographer()

    def _create_flamingo_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.flamingo_w, self.flamingo_h), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (40, 65, 75, 55), (20, 92, 100, 16))
        pygame.draw.ellipse(surf, (248, 124, 174), (40, 35, 65, 42))
        pygame.draw.ellipse(surf, INK_DARK, (40, 35, 65, 42), width=2)
        pygame.draw.ellipse(surf, (255, 174, 206), (50, 20, 48, 30))
        pygame.draw.ellipse(surf, INK_DARK, (50, 20, 48, 30), width=2)
        pts_neck = [(90, 48), (105, 36), (115, 20), (120, 10), (126, 12), (122, 26), (110, 46), (95, 56)]
        pygame.draw.polygon(surf, (248, 138, 188), pts_neck)
        pygame.draw.polygon(surf, INK_DARK, pts_neck, width=2)
        pygame.draw.circle(surf, (248, 142, 192), (124, 14), 10)
        pygame.draw.circle(surf, INK_DARK, (124, 14), 10, width=2)
        pygame.draw.circle(surf, INK_DARK, (127, 12), 2)
        pts_beak = [(128, 14), (138, 20), (136, 26), (127, 20)]
        pygame.draw.polygon(surf, (255, 232, 186), pts_beak)
        pygame.draw.polygon(surf, INK_DARK, [(133, 17), (138, 20), (136, 26), (131, 23)])
        pygame.draw.line(surf, (238, 128, 76), (60, 65), (52, 98), 3)
        pygame.draw.line(surf, (238, 128, 76), (70, 65), (75, 96), 3)
        return surf

    def _create_backdrop_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.screen_w, self.screen_h))
        for y in range(0, self.screen_h, 8):
            t = y / float(self.screen_h)
            r = int(172 * (1 - t) + 110 * t)
            g = int(218 * (1 - t) + 188 * t)
            b = int(238 * (1 - t) + 188 * t)
            surf.fill((r, g, b), (0, y, self.screen_w, 8))

        # Sol cálido acuarela
        sun = pygame.Surface((260, 260), pygame.SRCALPHA)
        pygame.draw.circle(sun, (255, 232, 162, 140), (130, 130), 110)
        pygame.draw.circle(sun, (255, 246, 206, 210), (130, 130), 68)
        surf.blit(sun, (1480, 90))

        for mx in range(0, self.screen_w, 90):
            mh = random.randint(140, 220)
            my = 480 - mh // 2
            pygame.draw.circle(surf, (58, 114, 82), (mx + 45, my + 30), mh // 2)
            pygame.draw.circle(surf, (78, 138, 98), (mx + 45, my + 15), max(10, mh // 2 - 10))

        water_surf = pygame.Surface((self.screen_w, 520), pygame.SRCALPHA)
        for wy in range(0, 520, 6):
            t = wy / 520.0
            r = int(62 * (1 - t) + 38 * t)
            g = int(146 * (1 - t) + 110 * t)
            b = int(166 * (1 - t) + 136 * t)
            pygame.draw.rect(water_surf, (r, g, b, 232), (0, wy, self.screen_w, 6))
        surf.blit(water_surf, (0, 560))

        # Pasarela de madera de Mallorquín
        pygame.draw.rect(surf, (158, 108, 68), (0, 960, self.screen_w, 120))
        pygame.draw.rect(surf, INK_DARK, (0, 958, self.screen_w, 12), border_radius=4)
        for plank_x in range(0, self.screen_w, 36):
            pygame.draw.line(surf, (112, 74, 46), (plank_x, 960), (plank_x, 1080), 2)

        return surf

    def _load_character_photographer(self) -> None:
        sprite_filename = f"{self.character_id}_seleccion_personaje.png"
        try:
            raw_sprite = self.assets.load_surface(sprite_filename, has_alpha=True)
            mask = pygame.mask.from_surface(raw_sprite)
            rects = mask.get_bounding_rects()
            cropped = raw_sprite.subsurface(rects[0]) if rects else raw_sprite
            target_h = 240
            target_w = int(cropped.get_width() * (target_h / float(cropped.get_height())))
            self.photographer_sprite = pygame.transform.smoothscale(cropped, (target_w, target_h))
        except Exception:
            self.photographer_sprite = pygame.Surface((120, 240), pygame.SRCALPHA)
            pygame.draw.rect(self.photographer_sprite, (220, 160, 60), (0, 0, 120, 240), border_radius=18)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if self.photo_taken:
            return
        if event.type == pygame.MOUSEMOTION:
            self.reticle_x = float(event.pos[0])
            self.reticle_y = float(event.pos[1])
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE) or (
            event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
        ):
            self._snap_photo()

    def _snap_photo(self) -> None:
        self.photo_taken = True
        self.shutter_flash_alpha = 255.0
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

        flamingo_center_x = self.flamingo_x + self.flamingo_w // 2
        flamingo_center_y = self.flamingo_y + self.flamingo_h // 2
        dist = math.hypot(self.reticle_x - flamingo_center_x, self.reticle_y - flamingo_center_y)

        if dist <= self.reticle_radius + 45:
            self.photo_success = True
            self.outro_message = "¡MOMENTO REAL CAPTURADO!"
            self.trigger_screenshake(14.0, 0.22)
            self.evaluate(True, delay=1.1, message="¡MOMENTO REAL CAPTURADO!")
        else:
            self.photo_success = False
            self.outro_message = "¡DESENFOCADO!"
            self.trigger_screenshake(6.0, 0.15)
            self.evaluate(False, delay=1.1, message="¡DESENFOCADO!")

    def update_game(self, dt: float) -> None:
        if not self.photo_taken:
            # Control suave por teclado si no se usa mouse
            keys = input_state.get_pressed()
            speed = 900.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.reticle_x = max(100.0, self.reticle_x - speed * dt)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.reticle_x = min(self.screen_w - 100.0, self.reticle_x + speed * dt)
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.reticle_y = max(100.0, self.reticle_y - speed * dt)
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.reticle_y = min(self.screen_h - 150.0, self.reticle_y + speed * dt)

            self.flamingo_x += self.flamingo_speed * dt
            self.flamingo_phase += dt * 4.8
            self.flamingo_y = self.flamingo_base_y + math.sin(self.flamingo_phase) * 36.0

            if self.flamingo_x > self.screen_w + 100:
                self.photo_taken = True
                self.outro_message = "¡SE ESCAPÓ!"
                self.evaluate(False, delay=0.8, message="¡SE ESCAPÓ!")

        if self.shutter_flash_alpha > 0.0:
            self.shutter_flash_alpha = max(0.0, self.shutter_flash_alpha - dt * 680.0)

        if self.photo_taken:
            self.polaroid_anim_t = min(1.0, self.polaroid_anim_t + dt * 3.0)

    def draw_game(self, screen: pygame.Surface) -> None:
        screen.blit(self.backdrop_surf, (0, 0))

        # Banner superior acuarela
        top_pill = pygame.Rect(self.screen_w // 2 - 330, 26, 660, 48)
        pygame.draw.rect(screen, (252, 244, 228), top_pill, border_radius=20)
        pygame.draw.rect(screen, INK_DARK, top_pill, width=3, border_radius=20)
        txt_b = self.font_banner.render("CIÉNAGA DE MALLORQUÍN · VIVE EL MOMENTO SIN FILTROS", True, INK_DARK)
        screen.blit(txt_b, txt_b.get_rect(center=top_pill.center))

        if self.flamingo_x < self.screen_w + 150:
            wing_tilt = math.sin(self.flamingo_phase) * 6.0
            tilted_surf = pygame.transform.rotate(self.flamingo_surf, wing_tilt)
            screen.blit(tilted_surf, (int(self.flamingo_x), int(self.flamingo_y)))

        screen.blit(self.photographer_sprite, (60, self.screen_h - 260))
        self._draw_camera_viewfinder(screen)

        if self.shutter_flash_alpha > 1.0:
            flash_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            flash_surf.fill((255, 252, 244, int(self.shutter_flash_alpha)))
            screen.blit(flash_surf, (0, 0))

        if self.photo_taken and self.polaroid_anim_t > 0.05:
            self._draw_polaroid_card(screen)

    def _draw_camera_viewfinder(self, screen: pygame.Surface) -> None:
        rx, ry = int(self.reticle_x), int(self.reticle_y)
        r = self.reticle_radius

        col_cross = (252, 212, 68) if not self.photo_taken else (228, 76, 72)
        if self.photo_success:
            col_cross = (64, 214, 114)

        pygame.draw.circle(screen, col_cross, (rx, ry), r, width=4)
        pygame.draw.circle(screen, (255, 250, 240), (rx, ry), r + 3, width=1)

        mark_len = 24
        pygame.draw.line(screen, col_cross, (rx - r - mark_len, ry), (rx - r + 8, ry), 3)
        pygame.draw.line(screen, col_cross, (rx + r - 8, ry), (rx + r + mark_len, ry), 3)
        pygame.draw.line(screen, col_cross, (rx, ry - r - mark_len), (rx, ry - r + 8), 3)
        pygame.draw.line(screen, col_cross, (rx, ry + r - 8), (rx, ry + r + mark_len), 3)

        box_size = 14
        pygame.draw.rect(screen, col_cross, (rx - box_size // 2, ry - box_size // 2, box_size, box_size), width=2)

        pill = pygame.Rect(rx - 95, ry - r - 38, 190, 28)
        pygame.draw.rect(screen, (252, 244, 228), pill, border_radius=12)
        pygame.draw.rect(screen, INK_DARK, pill, width=2, border_radius=12)
        txt_rec = self.font_hud.render("SIN FILTROS · REAL", True, (186, 54, 52))
        screen.blit(txt_rec, txt_rec.get_rect(center=pill.center))

    def _draw_polaroid_card(self, screen: pygame.Surface) -> None:
        pw, ph = 276, 316
        polaroid_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(polaroid_surf, (254, 250, 242), (0, 0, pw, ph), border_radius=16)
        pygame.draw.rect(polaroid_surf, INK_DARK, (0, 0, pw, ph), width=3, border_radius=16)

        photo_rect = pygame.Rect(16, 16, pw - 32, 220)
        if self.photo_success:
            pygame.draw.rect(polaroid_surf, (108, 186, 222), photo_rect, border_radius=8)
            mini_flamenco = pygame.transform.smoothscale(self.flamingo_surf, (110, 85))
            polaroid_surf.blit(mini_flamenco, (pw // 2 - 55, 75))
            badge_text = "RECUERDO REAL"
            badge_col = (34, 128, 66)
        else:
            pygame.draw.rect(polaroid_surf, (120, 110, 114), photo_rect, border_radius=8)
            badge_text = "FUERA DE CUADRO"
            badge_col = (186, 52, 52)

        txt_b = self.font_label.render(badge_text, True, badge_col)
        polaroid_surf.blit(txt_b, txt_b.get_rect(center=(pw // 2, 272)))

        dest_x = self.screen_w - pw - 40
        start_y = self.screen_h + 20
        target_y = self.screen_h - ph - 40
        cur_y = start_y + (target_y - start_y) * self.polaroid_anim_t
        screen.blit(polaroid_surf, (dest_x, int(cur_y)))
