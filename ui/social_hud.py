import math
import os
from typing import Any, Callable, Dict, Optional, Tuple
import pygame

class SocialPill:
    """
    Cápsula individual del HUD superior para redes sociales (Seguidores, Likes, Logros).
    Carga y utiliza directamente las texturas oficiales del juego:
    - assets/ui_cuenta_seguidores_mapa.png
    - assets/ui_cuenta_likes_mapa.png
    - assets/ui_cuenta_logros_mapa.png
    Con fallback procedural limpio y soporte de métricas dinámicas con animación de pulso.
    """
    def __init__(
        self,
        pill_type: str,
        label: str,
        top_left: Tuple[int, int],
        width: int = 258,
        height: int = 86,
        value_text: Optional[str] = None
    ) -> None:
        self.pill_type = pill_type
        self.label = label
        self.x, self.y = top_left
        self.width = width
        self.height = height
        self.value_text = value_text
        self.pulse_timer: float = 0.0
        self.is_hovered: bool = False
        self.hover_scale: float = 1.0

        # Tipografías cálidas y legibles alineadas bajo el título de cada cápsula
        self.font_val = pygame.font.SysFont("Trebuchet MS, Arial Black, sans-serif", 22, bold=True)

        # Cargar sprite oficial
        self.sprite = self._load_sprite()
        self.escribirEtiqueta()

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def _load_sprite(self) -> pygame.Surface:
        """Carga y reescala la textura oficial de la cápsula usando el AssetManager cacheado."""
        from core.asset_manager import AssetManager
        assets = AssetManager.get_instance()
        filename = f"ui_cuenta_{self.pill_type}_mapa.png"
        try:
            return assets.get_scaled(filename, self.width, self.height)
        except Exception as e:
            print(f"[SocialPill] Aviso al cargar {filename}: {e}")

        # Fallback procedural limpio
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        corner_r = self.height // 2
        rect = pygame.Rect(0, 0, self.width, self.height)
        pygame.draw.rect(surf, (255, 252, 255, 240), rect, border_radius=corner_r)
        pygame.draw.rect(surf, (195, 170, 230), rect, width=2, border_radius=corner_r)
        font = pygame.font.SysFont("Arial, sans-serif", 17, bold=True)
        txt = font.render(self.label, True, (70, 45, 90))
        surf.blit(txt, txt.get_rect(center=(self.width // 2, self.height // 2 - 14)))
        return surf

    def escribirEtiqueta(self) -> None:
        from core.asset_manager import AssetManager
        assets = AssetManager.get_instance()
        self.font_val = assets.cargarFuenteTitulo(24)
        w, h = self.sprite.get_size()
        medidas = {
            "seguidores": (0.395, 0.885, 0.09, 0.47, 0.425, 0.86),
            "likes": (0.452, 0.71, 0.10, 0.42, 0.452, 0.71),
            "logros": (0.425, 0.79, 0.10, 0.48, 0.425, 0.79),
        }
        if self.pill_type not in medidas:
            return
        izquierda, derecha, alto0, alto1, desde, hasta = medidas[self.pill_type]
        x0, x1 = int(w * izquierda), int(w * derecha)
        arriba, abajo = int(h * alto0), int(h * alto1)
        fuente = abajo + int(h * 0.02)
        if fuente + (abajo - arriba) > int(h * 0.88):
            return
        xDesde, xHasta = int(w * desde), int(w * hasta)
        parche = self.sprite.subsurface((xDesde, fuente, xHasta - xDesde, abajo - arriba)).copy()
        parche = pygame.transform.smoothscale(parche, (x1 - x0, abajo - arriba))
        mascara = pygame.Surface(parche.get_size(), pygame.SRCALPHA)
        borde = 3
        for i in range(borde):
            alfa = int(255 * (i + 1) / borde)
            pygame.draw.rect(mascara, (255, 255, 255, alfa), mascara.get_rect().inflate(-i * 2, -i * 2), width=1)
        mascara.fill((255, 255, 255, 255), mascara.get_rect().inflate(-borde * 2, -borde * 2))
        parche.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        original = self.sprite
        self.sprite = self.sprite.copy()
        self.sprite.blit(parche, (x0, arriba))
        if self.pill_type == "seguidores":
            raya = pygame.Rect(int(w * 0.394), int(h * 0.405), int(w * 0.026), abajo - int(h * 0.405) + 1)
            self.sprite.blit(original, raya.topleft, raya)
        color = {"seguidores": (74, 24, 118), "likes": (115, 18, 72), "logros": (82, 32, 95)}.get(self.pill_type, (65, 40, 85))
        tam = 27
        letra = assets.cargarFuenteTitulo(tam)
        while tam > 16 and letra.size(self.label)[0] > w * 0.47:
            tam -= 1
            letra = assets.cargarFuenteTitulo(tam)
        texto = letra.render(self.label, True, color)
        self.centroTexto = int(w * 0.67)
        self.sprite.blit(texto, texto.get_rect(center=(self.centroTexto, (arriba + abajo) // 2 + 2)))

    def set_value(self, new_value: Optional[str]) -> None:
        if self.value_text is not None and new_value is not None and self.value_text != new_value:
            self.pulse_timer = 0.45
        self.value_text = new_value

    def update(self, dt: float) -> None:
        if self.pulse_timer > 0.0:
            self.pulse_timer = max(0.0, self.pulse_timer - dt)
        target_scale = 1.045 if self.is_hovered else 1.0
        self.hover_scale += (target_scale - self.hover_scale) * min(1.0, dt * 16.0)

    def render(self, surface: pygame.Surface) -> None:
        if abs(self.hover_scale - 1.0) > 0.003:
            sw = max(1, int(round(self.width * self.hover_scale)))
            sh = max(1, int(round(self.height * self.hover_scale)))
            scaled = pygame.transform.smoothscale(self.sprite, (sw, sh))
            rect = scaled.get_rect(center=(self.x + self.width // 2, self.y + self.height // 2))
            surface.blit(scaled, rect.topleft)
        else:
            surface.blit(self.sprite, (self.x, self.y))

        # Renderizar métrica en el área libre inferior derecha (debajo de Seguidores / Likes / Logros)
        if self.value_text:
            color_map = {
                "seguidores": (74, 24, 118),
                "likes": (115, 18, 72),
                "logros": (82, 32, 95),
            }
            col = color_map.get(self.pill_type, (65, 40, 85))
            val_surf = self.font_val.render(self.value_text, True, col)
            shadow_surf = self.font_val.render(self.value_text, True, (255, 255, 255))

            if self.pulse_timer > 0.0:
                scale = 1.0 + 0.18 * math.sin((self.pulse_timer / 0.45) * math.pi)
                nw = max(10, int(val_surf.get_width() * scale))
                nh = max(10, int(val_surf.get_height() * scale))
                val_surf = pygame.transform.smoothscale(val_surf, (nw, nh))
                shadow_surf = pygame.transform.smoothscale(shadow_surf, (nw, nh))

            # El área derecha tras la línea divisoria vertical va de x+110 a x+244;
            # la mitad inferior (debajo del título ilustrado) tiene su centro en y + 57
            text_cx = self.x + getattr(self, "centroTexto", 176)
            text_cy = self.y + 57
            val_rect = val_surf.get_rect(center=(text_cx, text_cy))
            surface.blit(shadow_surf, (val_rect.x + 1, val_rect.y + 1))
            surface.blit(val_surf, val_rect)


class SocialHUD:
    """
    Contenedor del conjunto de cápsulas oficiales de red social en la barra superior.
    Ubicación calibrada según el mockup de referencia de BarranquillaWare (resolución 1920x1080).
    """
    def __init__(
        self,
        screen_w: int = 1920,
        screen_h: int = 1080,
        on_logros_click: Optional[Callable[[], None]] = None
    ) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.on_logros_click = on_logros_click

        pill_w = 258
        pill_h = 86
        pill_y = 28

        # Distribución horizontal superior
        self.pills: Dict[str, SocialPill] = {
            "seguidores": SocialPill(
                pill_type="seguidores",
                label="Seguidores",
                top_left=(760, pill_y),
                width=pill_w,
                height=pill_h
            ),
            "likes": SocialPill(
                pill_type="likes",
                label="Likes",
                top_left=(1040, pill_y),
                width=pill_w,
                height=pill_h
            ),
            "logros": SocialPill(
                pill_type="logros",
                label="Logros",
                top_left=(1320, pill_y),
                width=pill_w,
                height=pill_h
            )
        }

    def set_metric(self, pill_type: str, value_text: Optional[str]) -> None:
        """Asigna una métrica numérica formateada a la cápsula indicada."""
        if pill_type in self.pills:
            self.pills[pill_type].set_value(value_text)

    def sync_from_story_progress(self, character_id: str, high_score: int, completed_levels_count: int) -> Dict[str, Any]:
        """Calcula y sincroniza Seguidores, Likes y Logros en las 3 cápsulas del HUD."""
        from core.settings import compute_social_metrics
        metrics = compute_social_metrics(character_id, high_score, completed_levels_count)
        self.set_metric("seguidores", metrics["followers_text"])
        self.set_metric("likes", metrics["likes_text"])
        self.set_metric("logros", metrics["achievements_text"])
        return metrics

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Permite interactuar con la píldora de Logros para abrir la sección de trofeos."""
        pill = self.pills.get("logros")
        if event.type == pygame.MOUSEMOTION and pill is not None:
            pill_rect = pygame.Rect(pill.x, pill.y, pill.width, pill.height)
            was_hovered = pill.is_hovered
            pill.is_hovered = pill_rect.collidepoint(event.pos)
            if pill.is_hovered and not was_hovered:
                from core.audio_manager import AudioManager
                AudioManager.get_instance().play_hover()
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if pill:
                pill_rect = pygame.Rect(pill.x, pill.y, pill.width, pill.height)
                if pill_rect.collidepoint(event.pos):
                    if self.on_logros_click:
                        self.on_logros_click()
                    return True
        return False

    def update(self, dt: float) -> None:
        for pill in self.pills.values():
            pill.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        for pill in self.pills.values():
            pill.render(surface)
