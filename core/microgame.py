import math
from typing import Optional, Callable
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager

class BaseMicrogame(BaseState):
    """
    Clase base para todos los Microjuegos de BarranquillaWare (estilo WarioWare):
    - Gameloop desacoplado a 60 FPS con delta time (dt).
    - Temporizador estricto de 4 a 5 segundos con barra de tensión / mecha.
    - Fases: INTRO (instrucción imperativa), PLAY (interacción directa), OUTRO (éxito/fallo).
    - Métodos para sobreescribir: setup_game(), update_game(dt), render_game(surface), handle_game_event(event).
    """
    PHASE_INTRO = 0
    PHASE_PLAY = 1
    PHASE_OUTRO = 2

    def __init__(
        self,
        command_text: str = "¡CORRE!",
        time_limit: float = 4.0,
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        super().__init__()
        self.screen_w = 1920
        self.screen_h = 1080
        self.command_text = command_text
        self.time_limit = time_limit
        self.time_left = time_limit
        self.on_complete_callback = on_complete_callback

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        self.phase = self.PHASE_INTRO
        self.intro_timer: float = 0.0
        self.intro_duration: float = 0.85
        self.outro_timer: float = 0.0
        self.outro_duration: float = 1.1

        self.is_won: bool = False
        self.is_finished: bool = False

        # Tipografías oficiales de Microjuego
        self.font_command = pygame.font.SysFont("Arial Black, Impact, sans-serif", 72)
        self.font_outro = pygame.font.SysFont("Arial Black, Impact, sans-serif", 84)
        self.font_timer = pygame.font.SysFont("Arial Black, Impact, sans-serif", 28)

        self.setup_game()

    def setup_game(self) -> None:
        """Inicializa variables específicas del microjuego individual."""
        pass

    def finish_game(self, won: bool) -> None:
        """Declara el resultado del microjuego y activa la fase de salida."""
        if self.is_finished:
            return
        self.is_finished = True
        self.is_won = won
        self.phase = self.PHASE_OUTRO
        self.outro_timer = 0.0

        if won:
            if hasattr(self.audio, "play_win"):
                self.audio.play_win()
            elif hasattr(self.audio, "play_click"):
                self.audio.play_click()
        else:
            if hasattr(self.audio, "play_lose"):
                self.audio.play_lose()
            elif hasattr(self.audio, "play_pigeon"):
                self.audio.play_pigeon()

    def handle_game_event(self, event: pygame.event.Event) -> None:
        """Sobreescribir para manejar eventos durante la fase de juego activa."""
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.phase == self.PHASE_PLAY:
            self.handle_game_event(event)

    def update_game(self, dt: float) -> None:
        """Lógica interna del microjuego implementada en la subclase."""
        pass

    def update(self, dt: float) -> None:
        if self.phase == self.PHASE_INTRO:
            self.intro_timer += dt
            if self.intro_timer >= self.intro_duration:
                self.phase = self.PHASE_PLAY

        elif self.phase == self.PHASE_PLAY:
            self.time_left -= dt
            self.update_game(dt)
            if self.time_left <= 0.0 and not self.is_finished:
                self.time_left = 0.0
                # Si el tiempo se agota sin ganar, es derrota por tiempo
                self.finish_game(won=False)

        elif self.phase == self.PHASE_OUTRO:
            self.outro_timer += dt
            if self.outro_timer >= self.outro_duration:
                if self.on_complete_callback:
                    self.on_complete_callback(self.is_won)

    def render_game(self, surface: pygame.Surface) -> None:
        """Dibujo del escenario y entidades del microjuego."""
        pass

    def render(self, surface: pygame.Surface) -> None:
        # 1. Render específico del juego
        self.render_game(surface)

        # 2. Render de la barra de tiempo elástica / mecha inferior estilo WarioWare
        self._render_fuse_timer(surface)

        # 3. Cartel de consigna inicial (Fase Intro con bounce elástico)
        if self.phase == self.PHASE_INTRO:
            self._render_command_intro(surface)

        # 4. Cartel de resultado final (Fase Outro con feedback jugoso)
        elif self.phase == self.PHASE_OUTRO:
            self._render_outro_banner(surface)

    def _render_fuse_timer(self, surface: pygame.Surface) -> None:
        """Barra de tiempo inferior con indicador de mecha y tensión cromática."""
        bar_w = 1100
        bar_h = 24
        bar_x = (self.screen_w - bar_w) // 2
        bar_y = self.screen_h - 48

        # Fondo del riel
        pygame.draw.rect(surface, (20, 28, 45, 230), (bar_x - 4, bar_y - 4, bar_w + 8, bar_h + 8), border_radius=12)
        pygame.draw.rect(surface, (70, 95, 130), (bar_x - 4, bar_y - 4, bar_w + 8, bar_h + 8), width=2, border_radius=12)

        ratio = max(0.0, min(1.0, self.time_left / self.time_limit))
        current_w = int(bar_w * ratio)

        # Tensión cromática (Verde -> Amarillo -> Rojo urgente)
        if ratio > 0.5:
            color = (80, 230, 120)
        elif ratio > 0.25:
            color = (255, 215, 60)
        else:
            pulse = math.sin(self.time_left * 25.0) * 0.5 + 0.5
            color = (255, int(60 + 50 * pulse), 60)

        if current_w > 0:
            pygame.draw.rect(surface, color, (bar_x, bar_y, current_w, bar_h), border_radius=8)

        # Mecha encendida con chispita en el extremo
        fuse_x = bar_x + current_w
        fuse_y = bar_y + bar_h // 2
        spark_r = int(7 + math.sin(self.time_left * 30.0) * 3)
        pygame.draw.circle(surface, (255, 255, 220), (fuse_x, fuse_y), spark_r)
        pygame.draw.circle(surface, (255, 150, 40), (fuse_x, fuse_y), spark_r + 4, width=2)

    def _render_command_intro(self, surface: pygame.Surface) -> None:
        """Despliega el comando imperativo con animación elástica de entrada."""
        progress = min(1.0, self.intro_timer / (self.intro_duration * 0.5))
        scale = 1.0 + math.sin(progress * math.pi) * 0.25

        txt = self.font_command.render(self.command_text, True, (255, 250, 235))
        # Borde negro de impacto
        txt_border = self.font_command.render(self.command_text, True, (25, 20, 15))

        banner_w = int(txt.get_width() * scale) + 120
        banner_h = int(txt.get_height() * scale) + 40
        banner_surf = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        pygame.draw.rect(banner_surf, (20, 25, 40, 220), (0, 0, banner_w, banner_h), border_radius=20)
        pygame.draw.rect(banner_surf, (255, 215, 80), (0, 0, banner_w, banner_h), width=4, border_radius=20)

        for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
            banner_surf.blit(txt_border, txt_border.get_rect(center=(banner_w // 2 + ox, banner_h // 2 + oy)))
        banner_surf.blit(txt, txt.get_rect(center=(banner_w // 2, banner_h // 2)))

        surface.blit(banner_surf, banner_surf.get_rect(center=(self.screen_w // 2, self.screen_h // 2)))

    def _render_outro_banner(self, surface: pygame.Surface) -> None:
        """Cartel de Victoria / Derrota al concluir el microjuego."""
        msg = "¡LO LOGRASTE!" if self.is_won else "¡FALLASTE!"
        color = (100, 240, 130) if self.is_won else (255, 90, 85)
        border_col = (255, 255, 255) if self.is_won else (180, 40, 40)

        txt = self.font_outro.render(msg, True, color)
        txt_bg = self.font_outro.render(msg, True, (20, 20, 25))

        banner_w = txt.get_width() + 140
        banner_h = txt.get_height() + 50
        banner_surf = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        pygame.draw.rect(banner_surf, (15, 20, 35, 235), (0, 0, banner_w, banner_h), border_radius=24)
        pygame.draw.rect(banner_surf, border_col, (0, 0, banner_w, banner_h), width=4, border_radius=24)

        for ox, oy in [(-4, 0), (4, 0), (0, -4), (0, 4)]:
            banner_surf.blit(txt_bg, txt_bg.get_rect(center=(banner_w // 2 + ox, banner_h // 2 + oy)))
        banner_surf.blit(txt, txt.get_rect(center=(banner_w // 2, banner_h // 2)))

        # Entrada con rebote
        t = min(1.0, self.outro_timer / 0.3)
        bounce_y = int((1.0 - math.sin(t * math.pi * 0.5)) * -120)
        surface.blit(banner_surf, banner_surf.get_rect(center=(self.screen_w // 2, self.screen_h // 2 + bounce_y)))
