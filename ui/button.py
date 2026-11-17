import math
from typing import Callable, Optional, Tuple
import pygame
from core.audio_manager import AudioManager

class UIButton:
    """
    Botón interactivo con física de escala elástica, retroalimentación táctil,
    cero sombras/escarchas/sprays exteriores y destello especular interno limpio (Shimmer Sweep).
    """
    def __init__(
        self,
        center_pos: Tuple[int, int],
        normal_sprite: pygame.Surface,
        on_click: Optional[Callable[[], None]] = None,
        alt_sprite: Optional[pygame.Surface] = None,
        is_toggle: bool = False,
        initial_toggle_state: bool = True
    ) -> None:
        self.center_x, self.center_y = center_pos
        self.normal_sprite = normal_sprite
        self.alt_sprite = alt_sprite
        self.on_click = on_click
        self.is_toggle = is_toggle
        self.toggle_state = initial_toggle_state

        self.width = normal_sprite.get_width()
        self.height = normal_sprite.get_height()
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.rect.center = (self.center_x, self.center_y)

        # Estados de interacción
        self.is_hovered: bool = False
        self.is_pressed: bool = False

        # Animación de escala (Game Feel)
        self.current_scale: float = 1.0
        self.target_scale: float = 1.0
        self.press_offset_y: float = 0.0

        # Barrido de brillito interno (Shimmer)
        self.shimmer_progress: float = 2.0  # Inactivo al inicio (> 1.2)

        self.audio = AudioManager.get_instance()

    def set_center(self, center_pos: Tuple[int, int]) -> None:
        """Actualiza la posición central del botón y su rectángulo de colisión."""
        self.center_x, self.center_y = center_pos
        self.rect.center = (self.center_x, self.center_y)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            if not was_hovered and self.is_hovered:
                self.audio.play_hover()
                self.shimmer_progress = 0.0  # Iniciar destello
            elif not self.is_hovered:
                self.is_pressed = False
            return self.is_hovered

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_pressed = True
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.is_pressed
            self.is_pressed = False
            if was_pressed and self.rect.collidepoint(event.pos):
                if self.is_toggle:
                    self.toggle_state = not self.toggle_state
                self.audio.play_click()
                self.shimmer_progress = 0.0
                if self.on_click:
                    self.on_click()
                return True

        return False

    def update(self, dt: float) -> None:
        # 1. Escala elástica limpia
        if self.is_pressed:
            self.target_scale = 0.94
            target_offset = 3.0
        elif self.is_hovered:
            self.target_scale = 1.05
            target_offset = -2.0
        else:
            self.target_scale = 1.0
            target_offset = 0.0

        blend_factor = 1.0 - math.exp(-24.0 * dt)
        self.current_scale += (self.target_scale - self.current_scale) * blend_factor
        self.press_offset_y += (target_offset - self.press_offset_y) * blend_factor

        # 2. Barrido de brillito a velocidad moderada y sedosa (duración ~0.85s)
        if self.shimmer_progress < 1.3:
            self.shimmer_progress += dt * 1.35

    def render(self, surface: pygame.Surface) -> None:
        base_surf = self.normal_sprite
        if self.is_toggle and not self.toggle_state and self.alt_sprite:
            base_surf = self.alt_sprite

        w = max(1, int(self.width * self.current_scale))
        h = max(1, int(self.height * self.current_scale))
        scaled_surf = pygame.transform.smoothscale(base_surf, (w, h))

        draw_y = self.center_y + self.press_offset_y
        dest_rect = scaled_surf.get_rect(center=(self.center_x, int(draw_y)))

        # 1. Aplicar destello interno DENTRO del botón (cero spray en los bordes)
        if self.shimmer_progress < 1.15:
            btn_draw = scaled_surf.copy()
            shimmer_overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            sweep_x = int(-0.4 * w + self.shimmer_progress * 1.8 * w)
            strip_w = max(16, int(w * 0.18))
            slant = int(h * 0.45)

            points = [
                (sweep_x, 0),
                (sweep_x + strip_w, 0),
                (sweep_x + strip_w - slant, h),
                (sweep_x - slant, h)
            ]

            # Opacidad en campana para desvanecimiento suave
            norm_progress = min(1.0, max(0.0, self.shimmer_progress / 1.15))
            alpha = int(115 * math.sin(norm_progress * math.pi))
            pygame.draw.polygon(shimmer_overlay, (255, 255, 255, alpha), points)

            # Confinar estrictamente a los píxeles visibles del botón
            shimmer_overlay.blit(scaled_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            # Sumar la luz ÚNICAMENTE al interior del botón copiado
            btn_draw.blit(shimmer_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

            # Dibujado estándar sobre la pantalla (respetando canal alfa original sin spray)
            surface.blit(btn_draw, dest_rect)
        else:
            # Renderizado directo sin shimmer
            surface.blit(scaled_surf, dest_rect)
