from __future__ import annotations

from typing import Callable, Optional, List, Dict, Any
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.map_settings import MapSettingsState


class MicrogamePauseState(BaseState):
    """
    Menú de pausa unificado para minijuegos y mapa general.
    Utiliza los assets oficiales de recuadro y botones:
    - Continuar / Reanudar
    - Opciones / Ajustes (despliega MapSettingsState sin perder el estado pausado)
    - Reiniciar minijuego (si está disponible en el contexto)
    - Volver al mapa / Salir
    """
    def __init__(
        self,
        previous: BaseState,
        return_callback: Optional[Callable[[], None]] = None,
        restart_callback: Optional[Callable[[], None]] = None,
        menu_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.previous = previous
        self.return_callback = return_callback
        self.restart_callback = restart_callback
        self.menu_callback = menu_callback

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        self.selected = 0
        self.items: List[Dict[str, Any]] = [
            {"id": "resume", "label": "CONTINUAR", "asset": "boton_continuar_menu_pausa.png"},
            {"id": "options", "label": "OPCIONES", "asset": "boton_opciones_menu_pausa.png"},
        ]
        if self.restart_callback:
            self.items.append({"id": "restart", "label": "REINICIAR", "asset": "boton_reiniciar_menu_pausa.png"})
        if self.return_callback:
            self.items.append({"id": "map", "label": "VOLVER AL MAPA", "asset": None})
        if self.menu_callback:
            self.items.append({"id": "menu", "label": "SALIR AL MENÚ", "asset": "boton_salir_menu_pausa.png"})

        # Tipografías y geometría de la ventana
        self.font_item = pygame.font.SysFont("Arial Black, Impact, sans-serif", 24)
        self.font_hint = pygame.font.SysFont("Arial, sans-serif", 16, bold=True)

        self.box_w = 640
        self.box_h = 620
        self.btn_w = 400
        self.btn_h = 72

        # Cargar y pre-escalar texturas oficiales
        self.bg_box: Optional[pygame.Surface] = None
        self.button_surfs: Dict[str, pygame.Surface] = {}
        self._load_assets()

    def _load_assets(self) -> None:
        try:
            raw_box = self.assets.load_surface("recuadro_menu_pausa.png", has_alpha=True)
            self.bg_box = pygame.transform.smoothscale(raw_box, (self.box_w, self.box_h))
        except Exception:
            self.bg_box = None

        for it in self.items:
            if not it["asset"]:
                self.button_surfs[it["id"]] = None
                continue
            try:
                raw_btn = self.assets.load_surface(it["asset"], has_alpha=True)
                self.button_surfs[it["id"]] = pygame.transform.smoothscale(raw_btn, (self.btn_w, self.btn_h))
            except Exception:
                self.button_surfs[it["id"]] = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.items)
                self.audio.play_click()
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.items)
                self.audio.play_click()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._choose()
            elif event.key == pygame.K_ESCAPE:
                self._resume()

        elif event.type == pygame.MOUSEMOTION:
            # Detección de hover por cursor
            box_x = (1920 - self.box_w) // 2
            box_y = (1080 - self.box_h) // 2
            start_y = box_y + 90
            spacing = min(92, (self.box_h - 140) // max(1, len(self.items)))
            for i in range(len(self.items)):
                btn_rect = pygame.Rect((1920 - self.btn_w) // 2, start_y + i * spacing, self.btn_w, self.btn_h)
                if btn_rect.collidepoint(event.pos):
                    if self.selected != i:
                        self.selected = i
                        self.audio.play_click()
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            box_x = (1920 - self.box_w) // 2
            box_y = (1080 - self.box_h) // 2
            start_y = box_y + 90
            spacing = min(92, (self.box_h - 140) // max(1, len(self.items)))
            for i in range(len(self.items)):
                btn_rect = pygame.Rect((1920 - self.btn_w) // 2, start_y + i * spacing, self.btn_w, self.btn_h)
                if btn_rect.collidepoint(event.pos):
                    self.selected = i
                    self._choose()
                    break

        elif event.type == pygame.JOYHATMOTION and event.value[1] != 0:
            if event.value[1] > 0:
                self.selected = (self.selected - 1) % len(self.items)
            else:
                self.selected = (self.selected + 1) % len(self.items)
            self.audio.play_click()

        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0:  # Botón A
                self._choose()
            elif event.button in (1, 6, 7):  # Botón B o Start
                self._resume()

    def _resume(self) -> None:
        self.audio.play_click()
        if self.state_machine:
            self.state_machine.pop_state()

    def _open_options(self) -> None:
        self.audio.play_click()
        if self.state_machine:
            self.state_machine.push_state(MapSettingsState())

    def _choose(self) -> None:
        current_id = self.items[self.selected]["id"]
        if current_id == "resume":
            self._resume()
        elif current_id == "options":
            self._open_options()
        elif current_id == "restart":
            self.audio.play_click()
            if self.restart_callback:
                self.restart_callback()
        elif current_id == "map":
            self.audio.play_click()
            if self.return_callback:
                self.return_callback()
        elif current_id == "menu":
            self.audio.play_click()
            if self.menu_callback:
                self.menu_callback()

    def update(self, dt: float) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        # Renderiza el estado de fondo congelado
        self.previous.render(surface)

        # Cortina oscura translúcida
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((8, 12, 25, 185))
        surface.blit(veil, (0, 0))

        box_x = (surface.get_width() - self.box_w) // 2
        box_y = (surface.get_height() - self.box_h) // 2
        box_rect = pygame.Rect(box_x, box_y, self.box_w, self.box_h)

        if self.bg_box:
            surface.blit(self.bg_box, (box_x, box_y))
        else:
            pygame.draw.rect(surface, (20, 26, 44), box_rect, border_radius=24)
            pygame.draw.rect(surface, (245, 195, 75), box_rect, width=4, border_radius=24)

        start_y = box_y + 90
        spacing = min(92, (self.box_h - 140) // max(1, len(self.items)))

        for i, it in enumerate(self.items):
            item_id = it["id"]
            btn_x = (surface.get_width() - self.btn_w) // 2
            btn_y = start_y + i * spacing
            btn_rect = pygame.Rect(btn_x, btn_y, self.btn_w, self.btn_h)

            surf = self.button_surfs.get(item_id)
            if surf:
                if i == self.selected:
                    # Resaltado brillante para botón seleccionado
                    glow_rect = btn_rect.inflate(12, 12)
                    glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(glow_surf, (255, 230, 110, 140), (0, 0, glow_rect.width, glow_rect.height), border_radius=18)
                    surface.blit(glow_surf, glow_rect.topleft)

                surface.blit(surf, (btn_x, btn_y))
            else:
                # Fallback procedimental con buen contraste
                fill = (245, 195, 75) if i == self.selected else (45, 58, 85)
                color = (30, 30, 35) if i == self.selected else (240, 245, 255)
                pygame.draw.rect(surface, fill, btn_rect, border_radius=14)
                txt = self.font_item.render(it["label"], True, color)
                surface.blit(txt, txt.get_rect(center=btn_rect.center))

        hint = self.font_hint.render("↑ ↓ / CLICK ELEGIR  ·  ENTER/A ACEPTAR  ·  ESC REANUDAR", True, (240, 245, 255))
        surface.blit(hint, hint.get_rect(center=(surface.get_width() // 2, box_y + self.box_h - 38)))
