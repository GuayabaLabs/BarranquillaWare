import math
import random
from typing import Optional, Callable, Tuple
import pygame

from core.microgame import BaseMicrogame

class MallorquinPhotoMicrogame(BaseMicrogame):
    """
    Microjuego 3: '¡Fotografía al Flamenco!' (Ecorreserva Ciénaga de Mallorquín).
    - Consigna: ¡FOTOGRAFÍA AL FLAMENCO!
    - Mecánica: Un flamenco rosado del Caribe vuela/planea velozmente entre los manglares.
      Mueve el visor de la cámara con el mouse. Cuando el flamenco esté dentro del círculo
      central del visor, pulsa ESPACIO o haz CLICK para disparar el obturador.
    - Game Feel: Flash blanco de obturador, sonido de click de cámara, hit-stop y marco polaroid.
    """
    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡FOTOGRAFÍA AL FLAMENCO!",
            time_limit=4.0,
            on_complete_callback=on_complete_callback
        )

    def setup_game(self) -> None:
        # 1. Variables de juego
        self.photo_taken: bool = False
        self.shutter_flash_alpha: float = 0.0
        self.photo_success: bool = False
        self.polaroid_captured: Optional[pygame.Surface] = None
        self.polaroid_anim_t: float = 0.0

        # 2. Retícula / Visor de la cámara
        self.reticle_radius: int = 85
        self.reticle_x: float = float(self.screen_w // 2)
        self.reticle_y: float = float(self.screen_h // 2)

        # 3. Flamenco rosado del Caribe
        self.flamingo_x: float = -120.0
        self.flamingo_base_y: float = float(random.randint(320, 560))
        self.flamingo_speed: float = random.uniform(640.0, 780.0)
        self.flamingo_phase: float = random.uniform(0.0, math.pi * 2)
        self.flamingo_w: int = 140
        self.flamingo_h: int = 110

        # 4. Generar superficie del flamenco rosado (vectorial estilo cómic)
        self.flamingo_surf = self._create_flamingo_surface()

        # 5. Fondo escénico de Mallorquín (Ciénaga, manglares y agua reflectante)
        self.backdrop_surf = self._create_backdrop_surface()

        # 6. Sprite del personaje fotógrafo en la esquina inferior izquierda
        self._load_character_photographer()

    def _create_flamingo_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.flamingo_w, self.flamingo_h), pygame.SRCALPHA)
        # Sombra suave
        pygame.draw.ellipse(surf, (20, 45, 60, 60), (20, 92, 100, 16))
        # Cuerpo / Torso
        pygame.draw.ellipse(surf, (255, 115, 175), (40, 35, 65, 42))
        pygame.draw.ellipse(surf, (245, 80, 145), (40, 35, 65, 42), width=3)
        # Ala superior con plumaje
        pygame.draw.ellipse(surf, (255, 165, 205), (50, 20, 48, 30))
        pygame.draw.ellipse(surf, (240, 65, 135), (50, 20, 48, 30), width=2)
        # Cuello elegante en S
        pts_neck = [(90, 48), (105, 36), (115, 20), (120, 10), (126, 12), (122, 26), (110, 46), (95, 56)]
        pygame.draw.polygon(surf, (255, 135, 190), pts_neck)
        pygame.draw.polygon(surf, (245, 80, 145), pts_neck, width=2)
        # Cabeza
        pygame.draw.circle(surf, (255, 140, 195), (124, 14), 10)
        pygame.draw.circle(surf, (245, 80, 145), (124, 14), 10, width=2)
        # Ojo
        pygame.draw.circle(surf, (20, 20, 20), (127, 12), 2)
        # Pico característico curvado (negro en la punta, crema en la base)
        pts_beak = [(128, 14), (138, 20), (136, 26), (127, 20)]
        pygame.draw.polygon(surf, (255, 230, 180), pts_beak)
        pygame.draw.polygon(surf, (20, 20, 20), [(133, 17), (138, 20), (136, 26), (131, 23)])
        # Patas largas delgadas
        pygame.draw.line(surf, (245, 130, 80), (60, 65), (52, 98), 3)
        pygame.draw.line(surf, (245, 130, 80), (70, 65), (75, 96), 3)
        return surf

    def _create_backdrop_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.screen_w, self.screen_h))
        # Cielo crepuscular / atardecer caribeño en la ciénaga
        for y in range(self.screen_h):
            t = y / float(self.screen_h)
            r = int(120 * (1 - t) + 40 * t)
            g = int(195 * (1 - t) + 145 * t)
            b = int(240 * (1 - t) + 160 * t)
            surf.fill((r, g, b), (0, y, self.screen_w, 1))

        # Silueta de manglares al fondo
        for mx in range(0, self.screen_w, 90):
            mh = random.randint(140, 220)
            my = 480 - mh // 2
            pygame.draw.circle(surf, (30, 75, 55), (mx + 45, my + 30), mh // 2)
            pygame.draw.circle(surf, (45, 95, 70), (mx + 45, my + 15), mh // 2 - 8)

        # Agua de la Ciénaga de Mallorquín (plano medio e inferior)
        water_surf = pygame.Surface((self.screen_w, 520), pygame.SRCALPHA)
        for wy in range(520):
            t = wy / 520.0
            r = int(35 * (1 - t) + 18 * t)
            g = int(95 * (1 - t) + 60 * t)
            b = int(125 * (1 - t) + 95 * t)
            pygame.draw.line(water_surf, (r, g, b, 230), (0, wy), (self.screen_w, wy))

        surf.blit(water_surf, (0, 560))

        # Pasarela de madera / Muelle icónico de Mallorquín en la parte inferior
        pygame.draw.rect(surf, (140, 95, 55), (0, 960, self.screen_w, 120))
        pygame.draw.rect(surf, (85, 55, 30), (0, 960, self.screen_w, 12), border_radius=4)
        for plank_x in range(0, self.screen_w, 36):
            pygame.draw.line(surf, (90, 60, 35), (plank_x, 960), (plank_x, 1080), 2)

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

        # Disparador del obturador con ESPACIO o CLICK
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE) or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self._snap_photo()

    def _snap_photo(self) -> None:
        self.photo_taken = True
        self.shutter_flash_alpha = 255.0

        # Sonido de disparo de cámara si existe
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

        # Calcular distancia entre el centro del visor y el corazón del flamenco
        flamingo_center_x = self.flamingo_x + self.flamingo_w // 2
        flamingo_center_y = self.flamingo_y + self.flamingo_h // 2
        dist = math.hypot(self.reticle_x - flamingo_center_x, self.reticle_y - flamingo_center_y)

        # Rango de encuadre exitoso
        if dist <= self.reticle_radius + 45:
            self.photo_success = True
            self.trigger_screenshake(14.0, 0.22)
            self.evaluate(True, delay=1.1, message="¡FOTAZA!")
        else:
            self.photo_success = False
            self.trigger_screenshake(6.0, 0.15)
            self.evaluate(False, delay=1.1, message="¡DESENFOCADO!")

    def update_game(self, dt: float) -> None:
        if not self.photo_taken:
            # Control suave por teclado si no se usa mouse
            keys = pygame.key.get_pressed()
            speed = 900.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.reticle_x = max(100.0, self.reticle_x - speed * dt)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.reticle_x = min(self.screen_w - 100.0, self.reticle_x + speed * dt)
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.reticle_y = max(100.0, self.reticle_y - speed * dt)
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.reticle_y = min(self.screen_h - 150.0, self.reticle_y + speed * dt)

            # Vuelo del flamenco con sinusoide
            self.flamingo_x += self.flamingo_speed * dt
            self.flamingo_phase += dt * 4.8
            self.flamingo_y = self.flamingo_base_y + math.sin(self.flamingo_phase) * 36.0

            # Si el flamenco sale de pantalla por la derecha sin foto, falla por tiempo
            if self.flamingo_x > self.screen_w + 100:
                self.photo_taken = True
                self.evaluate(False, delay=0.8, message="¡SE ESCAPÓ!")

        # Flash de obturador desvaneciéndose
        if self.shutter_flash_alpha > 0.0:
            self.shutter_flash_alpha = max(0.0, self.shutter_flash_alpha - dt * 680.0)

        if self.photo_taken:
            self.polaroid_anim_t = min(1.0, self.polaroid_anim_t + dt * 3.0)

    def draw_game(self, screen: pygame.Surface) -> None:
        # 1. Fondo natural de la ciénaga
        screen.blit(self.backdrop_surf, (0, 0))

        # 2. Renderizar flamenco volando
        if self.flamingo_x < self.screen_w + 150:
            # Ligero aleteo vertical oscilante
            wing_tilt = math.sin(self.flamingo_phase) * 6.0
            tilted_surf = pygame.transform.rotate(self.flamingo_surf, wing_tilt)
            screen.blit(tilted_surf, (int(self.flamingo_x), int(self.flamingo_y)))

        # 3. Personaje fotógrafo en primer plano inferior
        screen.blit(self.photographer_sprite, (60, self.screen_h - 260))

        # 4. Renderizar Visor / Retícula de la Cámara
        self._draw_camera_viewfinder(screen)

        # 5. Efecto de Flash de Obturador
        if self.shutter_flash_alpha > 1.0:
            flash_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, int(self.shutter_flash_alpha)))
            screen.blit(flash_surf, (0, 0))

        # 6. Miniatura estilo Polaroid animada en la esquina si ya se tomó la foto
        if self.photo_taken and self.polaroid_anim_t > 0.05:
            self._draw_polaroid_card(screen)

    def _draw_camera_viewfinder(self, screen: pygame.Surface) -> None:
        rx, ry = int(self.reticle_x), int(self.reticle_y)
        r = self.reticle_radius

        # Oscurecimiento de viñeta periférica fuera del visor
        # Círculo central transparente
        col_cross = (255, 220, 60) if not self.photo_taken else (255, 90, 80)
        if self.photo_success:
            col_cross = (80, 245, 120)

        # Círculo del visor
        pygame.draw.circle(screen, col_cross, (rx, ry), r, width=3)
        pygame.draw.circle(screen, (255, 255, 255, 120), (rx, ry), r + 2, width=1)

        # Cruz y marcas de encuadre DSLR
        mark_len = 24
        # Marcas exteriores
        pygame.draw.line(screen, col_cross, (rx - r - mark_len, ry), (rx - r + 8, ry), 3)
        pygame.draw.line(screen, col_cross, (rx + r - 8, ry), (rx + r + mark_len, ry), 3)
        pygame.draw.line(screen, col_cross, (rx, ry - r - mark_len), (rx, ry - r + 8), 3)
        pygame.draw.line(screen, col_cross, (rx, ry + r - 8), (rx, ry + r + mark_len), 3)

        # Cuadrito central de enfoque
        box_size = 14
        pygame.draw.rect(screen, col_cross, (rx - box_size // 2, ry - box_size // 2, box_size, box_size), width=2)

        # HUD indicador de cámara (REC, ISO, Batería)
        font_hud = pygame.font.SysFont("Arial, sans-serif", 16, bold=True)
        txt_rec = font_hud.render("● REC 4K 60FPS", True, (255, 75, 75))
        screen.blit(txt_rec, (rx - 70, ry - r - 32))

    def _draw_polaroid_card(self, screen: pygame.Surface) -> None:
        pw, ph = 260, 310
        polaroid_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        # Marco blanco Polaroid
        pygame.draw.rect(polaroid_surf, (255, 255, 255), (0, 0, pw, ph), border_radius=14)
        pygame.draw.rect(polaroid_surf, (220, 215, 205), (0, 0, pw, ph), width=2, border_radius=14)
        # Foto interior
        photo_rect = pygame.Rect(16, 16, pw - 32, 220)
        if self.photo_success:
            pygame.draw.rect(polaroid_surf, (75, 165, 215), photo_rect)
            # Mini flamenco centrado
            mini_flamenco = pygame.transform.smoothscale(self.flamingo_surf, (110, 85))
            polaroid_surf.blit(mini_flamenco, (pw // 2 - 55, 75))
            badge_text = "★ FOTO PERFECTA"
            badge_col = (40, 140, 65)
        else:
            pygame.draw.rect(polaroid_surf, (90, 85, 95), photo_rect)
            badge_text = "✖ FUERA DE CUADRO"
            badge_col = (185, 45, 45)

        font_label = pygame.font.SysFont("Arial Black, sans-serif", 15)
        txt_b = font_label.render(badge_text, True, badge_col)
        polaroid_surf.blit(txt_b, txt_b.get_rect(center=(pw // 2, 268)))

        # Animación de salida deslizante desde la esquina inferior derecha
        dest_x = self.screen_w - pw - 40
        start_y = self.screen_h + 20
        target_y = self.screen_h - ph - 40
        cur_y = start_y + (target_y - start_y) * self.polaroid_anim_t

        screen.blit(polaroid_surf, (dest_x, int(cur_y)))
