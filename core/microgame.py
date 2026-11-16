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
        self.show_outro_banner: bool = True
        self.outro_message: Optional[str] = None
        self.pause_return_callback: Optional[Callable[[], None]] = None
        self.pause_restart_callback: Optional[Callable[[], None]] = None

        # Sacudida de pantalla (Screenshake)
        self.shake_intensity: float = 0.0
        self.shake_duration: float = 0.0
        self.shake_timer: float = 0.0
        self.shake_offset_x: int = 0
        self.shake_offset_y: int = 0

        # Tipografías oficiales de Microjuego con fallback empaquetado
        self.font_command = self.assets.get_font("Arial Black, Impact, sans-serif", 72)
        self.font_outro = self.assets.get_font("Arial Black, Impact, sans-serif", 84)
        self.font_timer = self.assets.get_font("Arial Black, Impact, sans-serif", 28)
        self._outro_shader_cache: dict = {}

        self.setup_game()

    def setup_game(self) -> None:
        """Inicializa variables específicas del microjuego individual."""
        pass

    def trigger_screenshake(self, intensity: float = 10.0, duration: float = 0.2) -> None:
        """Activa sacudida de pantalla."""
        self.shake_intensity = intensity
        self.shake_duration = duration
        self.shake_timer = duration

    def evaluate(self, won: bool, delay: float = 0.8, message: str = "") -> None:
        """Declara el resultado y pasa a la fase de outro."""
        self.finish_game(won=won)

    def finish_game(self, won: bool) -> None:
        """Declara el resultado del microjuego y activa la fase de salida."""
        if self.is_finished:
            return
        self.is_finished = True
        self.is_won = won
        self.phase = self.PHASE_OUTRO
        self.outro_timer = 0.0

        if won:
            fallback = getattr(self.audio, "_win_sound", None)
            if hasattr(self.audio, "play_voice"):
                self.audio.play_voice("coronaste.ogg", volume_scale=1.0, fallback_sound=fallback)
            elif hasattr(self.audio, "play_win"):
                self.audio.play_win()
            elif hasattr(self.audio, "play_click"):
                self.audio.play_click()
        else:
            fallback = getattr(self.audio, "_lose_sound", None)
            if hasattr(self.audio, "play_voice"):
                self.audio.play_voice("ombe_casi.ogg", volume_scale=1.0, fallback_sound=fallback)
            elif hasattr(self.audio, "play_lose"):
                self.audio.play_lose()
            elif hasattr(self.audio, "play_pigeon"):
                self.audio.play_pigeon()

    def handle_game_event(self, event: pygame.event.Event) -> None:
        """Sobreescribir para manejar eventos durante la fase de juego activa."""
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.phase == self.PHASE_PLAY and getattr(self, "state_machine", None):
                from core.microgame_pause import MicrogamePauseState
                self.state_machine.push_state(
                    MicrogamePauseState(
                        previous=self,
                        return_callback=self.pause_return_callback,
                        restart_callback=self.pause_restart_callback
                    )
                )
                return
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
        if hasattr(self, "draw_game"):
            self.draw_game(surface)

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
        """
        Despliega el comando imperativo con animación suave y soporte multilínea (separado por \n):
        - Entrada elástica con escala.
        - Mantenimiento nítido.
        - Fade-out progresivo con alfa en el tramo final (evita corte abrupto).
        """
        fade_start = self.intro_duration * 0.65
        if self.intro_timer > fade_start:
            alpha_ratio = max(0.0, 1.0 - (self.intro_timer - fade_start) / (self.intro_duration - fade_start))
        else:
            alpha_ratio = 1.0

        if alpha_ratio <= 0.01:
            return

        alpha_int = int(255 * alpha_ratio)

        # Escala suave
        progress = min(1.0, self.intro_timer / (self.intro_duration * 0.4))
        scale = 1.0 + math.sin(progress * math.pi) * 0.16

        lines = self.command_text.split("\n")
        rendered_lines = []
        max_w = 0
        total_h = 0
        line_spacing = 8

        for line in lines:
            t = self.font_command.render(line, True, (255, 250, 235))
            tb = self.font_command.render(line, True, (25, 20, 15))
            rendered_lines.append((t, tb))
            max_w = max(max_w, t.get_width())
            total_h += t.get_height()

        total_h += line_spacing * (len(lines) - 1)

        banner_w = int(max_w * scale) + 120
        banner_h = int(total_h * scale) + 50
        banner_surf = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        bg_alpha = int(220 * alpha_ratio)
        border_alpha = int(255 * alpha_ratio)
        pygame.draw.rect(banner_surf, (20, 25, 40, bg_alpha), (0, 0, banner_w, banner_h), border_radius=20)
        pygame.draw.rect(banner_surf, (255, 215, 80, border_alpha), (0, 0, banner_w, banner_h), width=4, border_radius=20)

        # Renderizar cada línea centrada
        cur_y = (banner_h - total_h) // 2
        for t, tb in rendered_lines:
            line_cx = banner_w // 2
            line_cy = cur_y + t.get_height() // 2
            for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
                banner_surf.blit(tb, tb.get_rect(center=(line_cx + ox, line_cy + oy)))
            banner_surf.blit(t, t.get_rect(center=(line_cx, line_cy)))
            cur_y += t.get_height() + line_spacing

        if alpha_int < 250:
            banner_surf.fill((255, 255, 255, alpha_int), special_flags=pygame.BLEND_RGBA_MULT)

        surface.blit(banner_surf, banner_surf.get_rect(center=(self.screen_w // 2, self.screen_h // 2)))

    def _render_outro_banner(self, surface: pygame.Surface) -> None:
        """
        Texto de Victoria / Derrota al concluir el microjuego sin recuadro contenedor,
        utilizando un shader volumétrico de resplandor (bloom multicapa), barrido cromático
        y contorno profundo para máxima legibilidad sobre cualquier fondo.
        """
        if not getattr(self, "show_outro_banner", True):
            return

        if getattr(self, "outro_message", None):
            msg = self.outro_message
        else:
            msg = "¡LO LOGRASTE!" if self.is_won else "¡FALLASTE!"

        # Entrada elástica y pulso de escala suave
        t = min(1.0, self.outro_timer / 0.28)
        bounce_y = int((1.0 - math.sin(t * math.pi * 0.5)) * -90)
        pulse = math.sin(self.outro_timer * 7.5) * 0.5 + 0.5
        scale = 1.0 + math.sin(t * math.pi) * 0.14 + pulse * 0.03

        if self.is_won:
            # Gradiente dinámico / tinte cálido esmeralda-dorado en victoria
            main_col = (
                int(115 + 75 * pulse),
                255,
                int(145 + 65 * (1.0 - pulse))
            )
            glow_outer_col = (40, 225, 130)
            glow_inner_col = (255, 240, 120)
            outline_col = (14, 38, 26)
        else:
            main_col = (
                255,
                int(85 + 45 * pulse),
                int(85 + 35 * pulse)
            )
            glow_outer_col = (235, 35, 55)
            glow_inner_col = (255, 175, 95)
            outline_col = (42, 12, 18)

        txt_main = self.font_outro.render(msg, True, main_col)
        txt_outline = self.font_outro.render(msg, True, outline_col)
        txt_glow_outer = self.font_outro.render(msg, True, glow_outer_col)
        txt_glow_inner = self.font_outro.render(msg, True, glow_inner_col)
        txt_highlight = self.font_outro.render(msg, True, (255, 255, 245))

        cache_key = (msg, round(pulse, 1))
        shader_surf = self._outro_shader_cache.get(cache_key)
        if shader_surf is None:
            tw, th = txt_main.get_size()
            pad = 64
            canvas_w = tw + pad * 2
            canvas_h = th + pad * 2
            shader_surf = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
            cx, cy = canvas_w // 2, canvas_h // 2

            # 1. Halo / Bloom exterior difuso (shader de aura sin recuadro)
            txt_glow_outer.set_alpha(int(38 + 26 * pulse))
            for radius in (18, 13, 9):
                for angle_deg in range(0, 360, 45):
                    rad = math.radians(angle_deg)
                    ox = int(math.cos(rad) * radius)
                    oy = int(math.sin(rad) * radius)
                    shader_surf.blit(txt_glow_outer, txt_glow_outer.get_rect(center=(cx + ox, cy + oy)))

            # 2. Resplandor interior cálido
            txt_glow_inner.set_alpha(int(75 + 40 * pulse))
            for ox, oy in [(-6, 0), (6, 0), (0, -6), (0, 6), (-4, -4), (4, -4), (-4, 4), (4, 4)]:
                shader_surf.blit(txt_glow_inner, txt_glow_inner.get_rect(center=(cx + ox, cy + oy)))

            # 3. Sombra proyectada direccional suave
            txt_shadow = self.font_outro.render(msg, True, (8, 10, 18))
            txt_shadow.set_alpha(175)
            shader_surf.blit(txt_shadow, txt_shadow.get_rect(center=(cx + 4, cy + 7)))

            # 4. Contorno nítido de alto contraste
            for ox in (-4, -2, 0, 2, 4):
                for oy in (-4, -2, 0, 2, 4):
                    if ox == 0 and oy == 0:
                        continue
                    shader_surf.blit(txt_outline, txt_outline.get_rect(center=(cx + ox, cy + oy)))

            # 5. Cuerpo principal del texto + brillo especular superior
            shader_surf.blit(txt_main, txt_main.get_rect(center=(cx, cy)))
            txt_highlight.set_alpha(int(90 + 55 * pulse))
            shader_surf.blit(txt_highlight, txt_highlight.get_rect(center=(cx, cy - 2)))
            self._outro_shader_cache[cache_key] = shader_surf

        canvas_w, canvas_h = shader_surf.get_size()

        if abs(scale - 1.0) > 0.01:
            scaled_w = max(10, int(canvas_w * scale))
            scaled_h = max(10, int(canvas_h * scale))
            shader_surf = pygame.transform.smoothscale(shader_surf, (scaled_w, scaled_h))

        surface.blit(shader_surf, shader_surf.get_rect(center=(self.screen_w // 2, self.screen_h // 2 + bounce_y)))
