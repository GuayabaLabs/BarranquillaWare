"""
BarranquillaWare - Pantalla de Carga Ligera (Cozy Loading / Splash)
Evita que la ventana parezca congelada ('No responde') al iniciar el juego
o al instanciar escenas pesadas como StoryMapScene.
"""
from __future__ import annotations

import math
from typing import Callable, Optional
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager


class LoadingScene(BaseState):
    """
    Escena de carga instantánea (< 0.1 s de inicialización):
    1. Renderiza al menos 2 frames visibles con el logo oficial y barra animada.
    2. Ejecuta `loader_fn()` para construir la escena destino y transiciona a ella.
    """

    def __init__(
        self,
        loader_fn: Callable[[], BaseState],
        message: str = "Cargando BarranquillaWare...",
        screen_w: int = 1920,
        screen_h: int = 1080,
    ) -> None:
        super().__init__()
        self.loader_fn = loader_fn
        self.message = message
        self.screen_w = screen_w
        self.screen_h = screen_h

        self.assets = AssetManager.get_instance()
        self.timer: float = 0.0
        self._frames_rendered: int = 0
        self._loaded: bool = False

        # Carga mínima y rápida para mostrar el primer frame de inmediato
        try:
            raw_bg = self.assets.load_surface("fondo_main_menu.png", has_alpha=False)
            self.background: Optional[pygame.Surface] = pygame.transform.smoothscale(
                raw_bg, (self.screen_w, self.screen_h)
            )
        except Exception:
            self.background = None

        try:
            self.logo: Optional[pygame.Surface] = self.assets.get_scaled(
                "titulo_main_menu.png", target_width=760
            )
        except Exception:
            self.logo = None

        self.font_msg = self.assets.cargarFuenteCuento(34)

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        self.timer += dt
        if self._loaded or self._frames_rendered < 2:
            return

        self._loaded = True
        try:
            pygame.event.pump()
        except Exception:
            pass

        next_state = self.loader_fn()
        if next_state is not None and self.state_machine is not None:
            self.state_machine.change_state(next_state)

    def render(self, surface: pygame.Surface) -> None:
        self._frames_rendered += 1

        if self.background is not None:
            surface.blit(self.background, (0, 0))
            veil = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            veil.fill((255, 248, 232, 110))
            surface.blit(veil, (0, 0))
        else:
            surface.fill((255, 248, 232))

        cx = self.screen_w // 2
        if self.logo is not None:
            bob = math.sin(self.timer * 3.0) * 5.0
            surface.blit(self.logo, self.logo.get_rect(center=(cx, int(360 + bob))))

        # Tarjeta crema cozy con barra de progreso animada
        card_w, card_h = 680, 148
        card_rect = pygame.Rect(cx - card_w // 2, 620, card_w, card_h)
        card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        pygame.draw.rect(card, (255, 250, 238, 235), (0, 0, card_w, card_h), border_radius=32)
        pygame.draw.rect(card, (126, 86, 56, 235), (0, 0, card_w, card_h), width=4, border_radius=32)
        surface.blit(card, card_rect.topleft)

        dots = "." * (int(self.timer * 3.0) % 4)
        base_msg = self.message.rstrip(".")
        txt = self.font_msg.render(f"{base_msg}{dots}", True, (78, 51, 35))
        surface.blit(txt, txt.get_rect(center=(cx, card_rect.top + 52)))

        # Barra de progreso indeterminada suave
        bar_w, bar_h = 540, 24
        bar_x = cx - bar_w // 2
        bar_y = card_rect.top + 96
        pygame.draw.rect(surface, (230, 216, 194), (bar_x, bar_y, bar_w, bar_h), border_radius=12)
        seg_w = 160
        pos_norm = 0.5 + 0.5 * math.sin(self.timer * 3.4 - math.pi / 2.0)
        seg_x = int(bar_x + pos_norm * (bar_w - seg_w))
        pygame.draw.rect(surface, (245, 185, 55), (seg_x, bar_y + 2, seg_w, bar_h - 4), border_radius=10)
        pygame.draw.rect(surface, (126, 86, 56), (bar_x, bar_y, bar_w, bar_h), width=2, border_radius=12)
