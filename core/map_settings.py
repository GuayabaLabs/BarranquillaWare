from __future__ import annotations

from typing import Callable, Optional
import pygame
from core.state_machine import BaseState
from core.settings import SettingsManager
from core.audio_manager import AudioManager


class MapSettingsState(BaseState):
    """Panel provisional de ajustes, sin resolución ni cambio de ventana."""
    def __init__(self, on_calibrate: Optional[Callable[[], None]] = None) -> None:
        super().__init__()
        self.settings = SettingsManager.get_instance()
        self.audio = AudioManager.get_instance()
        self.on_calibrate = on_calibrate
        self.index = 0
        self.items = ["sound", "music", "brightness", "colorblind", "controller", "calibrate", "back"]
        self.modes = ["off", "protanopia", "deuteranopia", "tritanopia"]
        self.font = pygame.font.SysFont("Arial Black, Impact, sans-serif", 30)
        self.small = pygame.font.SysFont("Arial, sans-serif", 20, bold=True)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._close()
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.items)
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT) and self.items[self.index] in ("sound", "music", "brightness", "colorblind"):
                    self._adjust(1 if event.key == pygame.K_RIGHT else -1)
                else:
                    self._activate()
        elif event.type == pygame.JOYHATMOTION and event.value[1] != 0:
            self.index = (self.index - 1 if event.value[1] > 0 else self.index + 1) % len(self.items)
        elif event.type == pygame.JOYBUTTONDOWN and event.button == 0:
            self._activate()

    def _activate(self) -> None:
        item = self.items[self.index]
        if item == "back":
            self._close()
        elif item == "sound":
            self.audio.toggle_sound()
        elif item == "music":
            self.audio.toggle_music()
        elif item == "brightness":
            value = float(self.settings.get("brightness", 1.0))
            value += 0.1 if value < 1.5 else -0.9
            self.settings.set("brightness", round(value, 1))
        elif item == "colorblind":
            mode = self.settings.get("colorblind_mode", "off")
            self.settings.set("colorblind_mode", self.modes[(self.modes.index(mode) + 1) % len(self.modes)])
        elif item == "calibrate" and self.on_calibrate:
            self.on_calibrate()

    def _adjust(self, direction: int) -> None:
        item = self.items[self.index]
        if item == "music":
            self.audio.music_volume = max(0.0, min(1.0, self.audio.music_volume + direction * 0.05))
            self.settings.set("music_volume", round(self.audio.music_volume, 2))
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(self.audio.music_volume if self.audio.music_enabled else 0.0)
        elif item == "sound":
            self.audio.sfx_volume = max(0.0, min(1.0, self.audio.sfx_volume + direction * 0.05))
            self.settings.set("sfx_volume", round(self.audio.sfx_volume, 2))
            self.audio.play_click()
        elif item == "brightness":
            value = float(self.settings.get("brightness", 1.0)) + direction * 0.05
            self.settings.set("brightness", round(max(0.5, min(1.5, value)), 2))
        elif item == "colorblind":
            value = float(self.settings.get("colorblind_intensity", 0.0)) + direction * 0.1
            self.settings.set("colorblind_intensity", round(max(0.0, min(1.0, value)), 1))

    def _close(self) -> None:
        if self.state_machine:
            self.state_machine.pop_state()

    def update(self, dt: float) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((5, 10, 20, 170))
        surface.blit(shade, (0, 0))
        panel = pygame.Rect(520, 110, 880, 860)
        pygame.draw.rect(surface, (22, 32, 52), panel, border_radius=24)
        pygame.draw.rect(surface, (240, 195, 95), panel, 3, border_radius=24)
        surface.blit(self.font.render("AJUSTES", True, (255, 220, 100)), (panel.x + 55, panel.y + 38))
        values = {
            "sound": f"{'ACTIVADO' if self.audio.sound_enabled else 'SILENCIADO'} · {int(self.audio.sfx_volume * 100)}%",
            "music": f"{'ACTIVADA' if self.audio.music_enabled else 'SILENCIADA'} · {int(self.audio.music_volume * 100)}%",
            "brightness": f"{int(float(self.settings.get('brightness', 1.0)) * 100)}%",
            "colorblind": f"{str(self.settings.get('colorblind_mode', 'off')).upper()} · {int(float(self.settings.get('colorblind_intensity', 0.0)) * 100)}%",
            "controller": "MANDO COMPATIBLE · AUTOMÁTICO",
            "calibrate": "ABRIR CALIBRADOR",
            "back": "VOLVER",
        }
        labels = {"sound":"Sonido", "music":"Música", "brightness":"Brillo", "colorblind":"Daltonismo", "controller":"Mando", "calibrate":"Lapicero", "back":"Cerrar"}
        for i, item in enumerate(self.items):
            y = panel.y + 125 + i * 92
            selected = i == self.index
            rect = pygame.Rect(panel.x + 45, y, panel.w - 90, 62)
            pygame.draw.rect(surface, (55, 80, 115) if selected else (34, 48, 72), rect, border_radius=12)
            surface.blit(self.small.render(labels[item], True, (255, 255, 255)), (rect.x + 22, rect.y + 18))
            txt = self.small.render(values[item], True, (170, 220, 185))
            surface.blit(txt, (rect.right - txt.get_width() - 22, rect.y + 18))
            if item in ("sound", "music", "brightness", "colorblind"):
                if item == "sound":
                    value = self.audio.sfx_volume
                elif item == "music":
                    value = self.audio.music_volume
                elif item == "brightness":
                    value = (float(self.settings.get("brightness", 1.0)) - 0.5) / 1.0
                else:
                    value = float(self.settings.get("colorblind_intensity", 0.0))
                bar = pygame.Rect(rect.x + 22, rect.bottom - 9, rect.w - 44, 4)
                pygame.draw.rect(surface, (75, 95, 120), bar, border_radius=2)
                fill = pygame.Rect(bar.x, bar.y, int(bar.w * max(0.0, min(1.0, value))), bar.h)
                pygame.draw.rect(surface, (245, 195, 75), fill, border_radius=2)
        surface.blit(self.small.render("↑↓ seleccionar · ←→ intensidad · ENTER modo · ESC cerrar", True, (180, 195, 220)), (panel.x + 55, panel.bottom - 42))
