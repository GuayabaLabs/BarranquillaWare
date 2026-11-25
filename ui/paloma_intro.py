"""Diálogo de contexto de la Paloma de Curramba antes de un minijuego.

Reutiliza el mismo cuadro acuarela (`text_dialog.png` + `paloma_dialog.png`) y el mismo dibujo
(`StoryMapUI.render_paloma_dialog`) que el Modo Historia, para que los minijuegos sueltos
tengan el mismo contexto narrativo que los del mapa.

Avanzar: Espacio / Enter / clic / botón A del mando / pellizco o puño con la cámara.
Saltar todo: Esc o Start.
"""
from typing import List, Optional

import pygame

from core.asset_manager import AssetManager
from core.audio_manager import AudioManager


class PalomaIntro:
    ANIM_VEL = 7.0

    def __init__(self, pages: List[List[str]], badge: str = "") -> None:
        self.pages = pages
        self.badge = badge
        self.page = 0
        self.anim_t = 0.0
        self.closing = False
        self.done = not pages
        self.timer = 0.0
        self._assets_listos = False
        # La voz suena al entrar al minijuego (BaseMicrogame.enter), no al construirlo: en el Modo Historia
        # el diálogo se quita antes de entrar y así no corta la voz de SEOR entre rondas.

    @staticmethod
    def _play_voice() -> None:
        audio = AudioManager.get_instance()
        audio.play_voice("paloma_animo.ogg", fallback_sound=getattr(audio, "_pigeon_sound", None))

    def _cargar(self) -> None:
        if self._assets_listos:
            return
        assets = AssetManager.get_instance()
        try:
            raw_box = assets.load_surface("text_dialog.png", has_alpha=True)
            w = 1060
            self.box = pygame.transform.smoothscale(raw_box, (w, max(240, int(raw_box.get_height() * w / raw_box.get_width()))))
        except Exception:
            self.box = pygame.Surface((1060, 530), pygame.SRCALPHA)
            pygame.draw.rect(self.box, (255, 244, 218, 248), (20, 60, 1020, 420), border_radius=36)
        try:
            raw = assets.load_surface("paloma_dialog.png", has_alpha=True)
            rects = pygame.mask.from_surface(raw).get_bounding_rects()
            raw = raw.subsurface(rects[0]) if rects else raw
            h = 330
            self.portrait = pygame.transform.smoothscale(raw, (max(180, int(raw.get_width() * h / raw.get_height())), h))
        except Exception:
            self.portrait = pygame.Surface((220, 330), pygame.SRCALPHA)
        self.talk_frames = []
        try:
            raw = assets.load_surface("paloma_dialog.png", has_alpha=True)
            rects = pygame.mask.from_surface(raw).get_bounding_rects()
            crop = rects[0] if rects else raw.get_rect()
            for filename in ("paloma_dialog_habla_0.png", "paloma_dialog_habla_1.png",
                             "paloma_dialog_habla_2.png", "paloma_dialog_pestaneo.png"):
                frame = assets.load_surface(filename, has_alpha=True)
                self.talk_frames.append(pygame.transform.smoothscale(
                    frame.subsurface(crop), self.portrait.get_size()))
        except Exception:
            self.talk_frames = []
        self.font_speaker = assets.cargarFuenteTitulo(24)
        self.font_badge = assets.cargarFuenteTitulo(22)
        self.font_body = assets.cargarFuenteCuento(31)
        self.font_hint = pygame.font.SysFont("Trebuchet MS, Arial, sans-serif", 16, bold=True)
        self._assets_listos = True

    @property
    def active(self) -> bool:
        return not self.done

    def advance(self) -> None:
        if self.closing:
            return
        audio = AudioManager.get_instance()
        audio.play_click()
        if self.page + 1 < len(self.pages):
            self.page += 1
        else:
            audio.stop_voice(100)
            self.closing = True

    def skip(self) -> None:
        AudioManager.get_instance().stop_voice(100)
        self.closing = True

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.skip()
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e):
                self.advance()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.advance()

    def update(self, dt: float, camera=None) -> None:
        self.timer += dt
        AudioManager.get_instance().update(dt)
        if camera is not None and getattr(camera, "enabled", False):
            try:
                if camera.consume_fist() or camera.consume_click():
                    self.advance()
            except Exception:
                pass
        if self.closing:
            self.anim_t = max(0.0, self.anim_t - dt * self.ANIM_VEL)
            if self.anim_t <= 0.0:
                self.done = True
        else:
            self.anim_t = min(1.0, self.anim_t + dt * self.ANIM_VEL)

    def render(self, surface: pygame.Surface) -> None:
        if self.done:
            return
        self._cargar()
        from scenes.story_map.ui_dialogs import StoryMapUI

        StoryMapUI(surface.get_width(), surface.get_height()).render_paloma_dialog(
            surface=surface,
            anim_t=self.anim_t,
            pages=self.pages,
            page_idx=self.page,
            speaker="PALOMA DE CURRAMBA",
            badge=self.badge,
            timer=self.timer,
            portrait_surf=self.portrait,
            dialog_box_surf=self.box,
            font_speaker=self.font_speaker,
            font_badge=self.font_badge,
            font_body=self.font_body,
            font_hint=self.font_hint,
            talk_frames=self.talk_frames,
            is_talking=AudioManager.get_instance().is_voice_playing(),
        )
