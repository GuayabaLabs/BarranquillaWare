import math
from typing import Optional, Callable, Dict
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager, bordeSuave, desenfoque_suave
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

    # Botones del mando que un microjuego quiere leer como teclas propias
    # (índices estilo Xbox: 0=A, 1=B, 2=X, 3=Y). Lo consulta core.engine; Start/Back siguen pausando.
    GAMEPAD_BUTTON_KEYS: Dict[int, int] = {}

    # False en microjuegos que leen la cámara por su cuenta (posición, pellizco, golpe...):
    # el motor no dibuja el lapicero ni consume gestos para no robarle la entrada al juego.
    CAMERA_POINTER: bool = True

    # Barra de tiempo acuarela: (centro_x, centro_y, ancho). None = abajo, centrada y ancha.
    TIME_BAR_LAYOUT: Optional[tuple] = None

    # Control por movimiento genérico: traduce gestos de la cámara a las teclas que el juego ya usa.
    #   "accion": tecla que se pulsa al cerrar el puño o pellizcar.
    #   "eje_x":  (izquierda, derecha) sostenidas según la mano esté a un lado u otro de la pantalla.
    #   "eje_y":  (arriba, abajo) sostenidas según la altura de la mano.
    #   "dedos":  teclas para doblar índice, medio, anular y meñique (como un piano).
    # Lo llama core.engine en cada frame; si se define, el lapicero de menú se apaga en el juego.
    CAMERA_ACTIONS: Dict[str, object] = {}

    # Contexto opcional de la Paloma antes de jugar: lista de páginas (cada una, lista de líneas).
    # Se muestra con el mismo cuadro de diálogo del Modo Historia (ui/paloma_intro.py).
    dialogoPaloma: Optional[list] = None
    CAMERA_DEADZONE: float = 0.12  # Zona muerta alrededor del centro para los ejes

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
        self._completion_reported = False

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        self.phase = self.PHASE_INTRO
        self.intro_timer: float = 0.0
        self.intro_duration: float = 1.6
        self.outro_timer: float = 0.0
        self.outro_duration: float = 1.1

        self.is_won: bool = False
        self.is_finished: bool = False
        self.show_outro_banner: bool = True
        self.outro_message: Optional[str] = None
        self.pause_return_callback: Optional[Callable[[], None]] = None
        self.pause_restart_callback: Optional[Callable[[], None]] = None
        self.pause_menu_callback: Optional[Callable[[], None]] = None

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

        self.paloma_intro = None
        if self.dialogoPaloma:
            from ui.paloma_intro import PalomaIntro
            self.paloma_intro = PalomaIntro(self.dialogoPaloma)

    def setup_game(self) -> None:
        """Inicializa variables específicas del microjuego individual."""
        pass

    def update_camera_actions(self, camera) -> None:
        """Convierte gestos en teclas virtuales según CAMERA_ACTIONS (solo en la fase de juego)."""
        from core import input_state

        acciones = self.CAMERA_ACTIONS
        held = getattr(self, "_camera_held", None)
        if held is None:
            held = self._camera_held = set()

        activo = bool(acciones) and self.phase == self.PHASE_PLAY and not self.is_finished
        presente = activo and camera is not None and camera.enabled and camera.is_hand_present()

        deseadas = set()
        if presente:
            x, y = camera.get_position()
            dz = self.CAMERA_DEADZONE
            for eje, valor in (("eje_x", x), ("eje_y", y)):
                teclas = acciones.get(eje)
                if not teclas:
                    continue
                if valor < 0.5 - dz:
                    deseadas.add(teclas[0])
                elif valor > 0.5 + dz:
                    deseadas.add(teclas[1])

        def evento(tipo, tecla):
            datos = {"key": tecla, "mod": 0, "scancode": 0, "camera_gesture": True}
            if tipo == pygame.KEYDOWN:
                datos["unicode"] = " " if tecla == pygame.K_SPACE else ""
            self.handle_game_event(pygame.event.Event(tipo, datos))

        for tecla in held - deseadas:
            input_state.VIRTUAL_KEYS.discard(tecla)
            evento(pygame.KEYUP, tecla)
        for tecla in deseadas - held:
            input_state.VIRTUAL_KEYS.add(tecla)
            evento(pygame.KEYDOWN, tecla)
        self._camera_held = deseadas

        if not presente:
            return
        tecla_accion = acciones.get("accion")
        if tecla_accion is not None and (camera.consume_fist() or camera.consume_click()):
            evento(pygame.KEYDOWN, tecla_accion)
            evento(pygame.KEYUP, tecla_accion)
            return  # Un puño no debe disparar también todos los dedos plegados.
        for i, tecla in enumerate(acciones.get("dedos", ()) or ()):
            if camera.consume_finger(i):
                evento(pygame.KEYDOWN, tecla)
                evento(pygame.KEYUP, tecla)

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

        if getattr(self, "skip_outro_story_card", False):
            self.letreroResultado = None
            self.fuegosLogro = None
            if not getattr(self, "outro_message", None):
                self.outro_message = "¡GANASTE!" if won else "¡PERDISTE!"
        else:
            if self.prepararLetreroResultado(won):
                self.outro_duration = max(self.outro_duration, 4.0)

            if getattr(self, "ensenanzaFinal", None) and getattr(self, "letreroResultado", None) is not None:
                self.finLetrero = 3.0
                self.outro_duration = max(self.outro_duration, 8.5)

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

    def reset_camera_motion(self) -> None:
        """Las subclases pueden cancelar un gesto pendiente al abrir la pausa."""
        pass

    def reset_binary_camera_choice(self) -> None:
        """Reinicia el progreso de elección binaria por cámara."""
        self._choice_hold_timers = [0.0, 0.0]
        self._choice_hold_progress = (0.0, 0.0)

    def poll_binary_camera_choice(self, camera, dt: float, hold_time: float = 0.55) -> Optional[int]:
        """Elección binaria compartida para avisos (celular/diálogos):
        - Opción 0 (Revisar / Aceptar): mantener pellizco o puño durante `hold_time`.
        - Opción 1 (Ignorar / Seguir): mantener palma abierta durante `hold_time`.
        """
        if not hasattr(self, "_choice_hold_timers"):
            self.reset_binary_camera_choice()
        if not camera or not getattr(camera, "enabled", False) or not camera.is_hand_present():
            self.reset_binary_camera_choice()
            return None
        pinch_or_fist = (
            (hasattr(camera, "is_pinching") and camera.is_pinching())
            or (hasattr(camera, "is_fist") and camera.is_fist())
        )
        open_palm = (
            camera.is_open_palm()
            if hasattr(camera, "is_open_palm")
            else bool(getattr(camera, "open_palm", False))
        )
        timers = self._choice_hold_timers
        if pinch_or_fist:
            timers[0] += dt
            timers[1] = 0.0
        elif open_palm:
            timers[1] += dt
            timers[0] = 0.0
        else:
            timers[0] = max(0.0, timers[0] - dt * 2.0)
            timers[1] = max(0.0, timers[1] - dt * 2.0)
        self._choice_hold_progress = (
            min(1.0, timers[0] / hold_time),
            min(1.0, timers[1] / hold_time),
        )
        if timers[0] >= hold_time:
            self.reset_binary_camera_choice()
            return 0
        if timers[1] >= hold_time:
            self.reset_binary_camera_choice()
            return 1
        return None

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.paloma_intro is not None and self.paloma_intro.active:
            self.paloma_intro.handle_event(event)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.phase == self.PHASE_PLAY and getattr(self, "state_machine", None):
                self.reset_camera_motion()
                from core.microgame_pause import MicrogamePauseState
                self.state_machine.push_state(
                    MicrogamePauseState(
                        previous=self,
                        return_callback=self.pause_return_callback,
                        restart_callback=self.pause_restart_callback,
                        menu_callback=self.pause_menu_callback,
                    )
                )
                return
        if self.phase == self.PHASE_PLAY:
            self.handle_game_event(event)

    def update_game(self, dt: float) -> None:
        """Lógica interna del microjuego implementada en la subclase."""
        pass

    def update(self, dt: float) -> None:
        if self.paloma_intro is not None and self.paloma_intro.active:
            from core.camera_gestures import CameraGestureInput
            self.paloma_intro.update(dt, CameraGestureInput.get_instance())
            return
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
                if self.on_complete_callback and not self._completion_reported:
                    self._completion_reported = True
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

        # 0. Contexto de la Paloma (antes de la consigna)
        if self.paloma_intro is not None and self.paloma_intro.active:
            self.paloma_intro.render(surface)
            return

        # 3. Cartel de consigna inicial (Fase Intro con bounce elástico)
        if self.phase == self.PHASE_INTRO:
            self._render_command_intro(surface)

        # 4. Cartel de resultado final (Fase Outro con feedback jugoso)
        elif self.phase == self.PHASE_OUTRO:
            self._render_outro_banner(surface)

    def _render_fuse_timer(self, surface: pygame.Surface) -> None:
        """Barra de tiempo inferior con indicador de mecha y tensión cromática."""
        if self.dibujarBarraTiempo(surface):
            return
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
        if self.dibujarPortadaInstruccion(surface):
            return

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

        if self.dibujarLetreroResultado(surface):
            self.dibujarEnsenanzaFinal(surface)
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

    def prepararLetreroResultado(self, ganado: bool) -> bool:
        try:
            import os
            from effects.juice_particles import FuegosArtificiales
            nombre = "letreroGanaste.jpg" if ganado else "letreroPerdiste.jpg"
            letrero = self.assets.cargarSinFondo(os.path.join("Interfaz", nombre), 1000)
            self.letreroResultado = self.suavizarColores(letrero)
            self.cajaLetrero = self.letreroResultado.get_rect(center=(self.screen_w // 2, self.screen_h // 2))
            self.finLetrero = None
            self.relojFuegos = 0.0
            self.fuegosLogro = None
            if ganado:
                self.fuegosLogro = FuegosArtificiales()
                self.fuegosLogro.lanzarAlrededor(self.cajaLetrero)
                for i, fuego in enumerate(self.fuegosLogro.fuegos):
                    fuego["t"] = 0.45 - i * 0.5
            return True
        except Exception as e:
            print(f"Aviso: no se pudo cargar el letrero de resultado: {e}")
            self.letreroResultado = None
            self.fuegosLogro = None
            return False

    def dibujarLetreroResultado(self, surface: pygame.Surface) -> bool:
        if getattr(self, "letreroResultado", None) is None:
            return False

        entrada = min(1.0, self.outro_timer / 0.55)
        finLetrero = getattr(self, "finLetrero", None) or self.outro_duration
        salida = min(1.0, max(0.0, (finLetrero - self.outro_timer) / 0.35))
        visible = min(entrada, salida)
        rebote = 1.0 + 2.7 * (entrada - 1.0) ** 3 + 1.7 * (entrada - 1.0) ** 2
        escala = max(0.05, 0.15 + 0.85 * rebote) + 0.02 * math.sin(self.outro_timer * 3.0) * entrada

        finTodo = min(1.0, max(0.0, (self.outro_duration - self.outro_timer) / 0.35))
        oscuro = min(entrada, finTodo)
        tono = [int(255 - (255 - c) * oscuro) for c in (150, 144, 160)]
        surface.fill(tono, special_flags=pygame.BLEND_RGB_MULT)

        if getattr(self, "fuegosLogro", None) is not None:
            paso = self.outro_timer - getattr(self, "relojFuegos", 0.0)
            self.relojFuegos = self.outro_timer
            if paso > 0.0:
                self.fuegosLogro.update(paso)
            self.fuegosLogro.render(surface)

        if visible <= 0.0:
            return True

        letrero = pygame.transform.smoothscale_by(self.letreroResultado, escala)
        if visible < 1.0:
            letrero.set_alpha(int(255 * visible))
        surface.blit(letrero, letrero.get_rect(center=self.cajaLetrero.center))
        return True

    def textoConBorde(self, fuente, texto: str, color, colorBorde, grosor: int = 3) -> pygame.Surface:
        cuerpo = fuente.render(texto, True, color)
        borde = fuente.render(texto, True, colorBorde)
        lienzo = pygame.Surface((cuerpo.get_width() + grosor * 2, cuerpo.get_height() + grosor * 2), pygame.SRCALPHA)
        for grados in range(0, 360, 20):
            dx = round(math.cos(math.radians(grados)) * grosor)
            dy = round(math.sin(math.radians(grados)) * grosor)
            lienzo.blit(borde, (grosor + dx, grosor + dy))
        lienzo.blit(cuerpo, (grosor, grosor))
        return lienzo

    def textoInstruccion(self, linea: str) -> str:
        if "[" in linea:
            return linea
        texto = linea.lower()
        for i, letra in enumerate(texto):
            if letra.isalpha():
                texto = texto[:i] + letra.upper() + texto[i + 1:]
                break
        for nombre in ("Troja",):
            texto = texto.replace(nombre.lower(), nombre)
        return texto

    def dibujarPortadaInstruccion(self, surface: pygame.Surface) -> bool:
        if getattr(self, "portadaIntro", None) is None:
            try:
                import os
                fondo = self.assets.cargarSinFondo(os.path.join("Interfaz", "fondoInstruccion.jpg"), 1150)
                lineas = self.command_text.split("\n")
                fuenteGrande = self.assets.cargarFuenteCuento(96)
                fuenteChica = self.assets.cargarFuenteCuento(52)
                textos = []
                for i, linea in enumerate(lineas):
                    fuente = fuenteGrande if i == 0 else fuenteChica
                    texto = self.textoConBorde(fuente, self.textoInstruccion(linea), (255, 247, 230), (96, 56, 30), 5 if i == 0 else 3)
                    if texto.get_width() > fondo.get_width() * 0.78:
                        texto = pygame.transform.smoothscale_by(texto, fondo.get_width() * 0.78 / texto.get_width())
                    textos.append(texto)
                portada = fondo.copy()
                alto = sum(t.get_height() for t in textos)
                y = int(portada.get_height() * 0.6) - alto // 2
                for texto in textos:
                    portada.blit(texto, texto.get_rect(midtop=(portada.get_width() // 2, y)))
                    y += texto.get_height()
                self.portadaIntro = portada
            except Exception as e:
                print(f"Aviso: no se pudo cargar el fondo de la instrucción: {e}")
                self.portadaIntro = False
        if not self.portadaIntro:
            return False

        entrada = min(1.0, self.intro_timer / 0.45)
        rebote = 1.0 + 2.7 * (entrada - 1.0) ** 3 + 1.7 * (entrada - 1.0) ** 2
        escala = max(0.05, 0.3 + 0.7 * rebote)
        inicioSalida = self.intro_duration - 0.35
        visible = 1.0
        if self.intro_timer > inicioSalida:
            visible = max(0.0, 1.0 - (self.intro_timer - inicioSalida) / 0.35)
        if visible <= 0.01:
            return True
        portada = pygame.transform.smoothscale_by(self.portadaIntro, escala)
        if visible < 1.0:
            portada.set_alpha(int(255 * visible))
        surface.blit(portada, portada.get_rect(center=(self.screen_w // 2, self.screen_h // 2)))
        return True

    def ponerBorde(self, imagen: pygame.Surface, color, grosor: int) -> pygame.Surface:
        conBorde = pygame.Surface((imagen.get_width() + grosor * 2, imagen.get_height() + grosor * 2), pygame.SRCALPHA)
        silueta = pygame.mask.from_surface(imagen, 100).to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
        for grados in range(0, 360, 15):
            dx = round(math.cos(math.radians(grados)) * grosor)
            dy = round(math.sin(math.radians(grados)) * grosor)
            conBorde.blit(silueta, (grosor + dx, grosor + dy))
        conBorde.blit(imagen, (grosor, grosor))
        return conBorde

    def ponerBordeFino(self, imagen: pygame.Surface, color, grosor: int = 2) -> pygame.Surface:
        return bordeSuave(imagen, color, grosor)

    def suavizarOrilla(self, imagen: pygame.Surface) -> pygame.Surface:
        suave = imagen.copy()
        alfa = desenfoque_suave(imagen)
        suave.blit(alfa, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        return suave

    def crearCartel(self, lineas: list):
        try:
            import os
            banner = self.assets.cargarSinFondo(os.path.join("Interfaz", "bannerUbicacion.jpg"), 1200)
            altoBanner = 70 + 60 * len(lineas)
            banner = pygame.transform.smoothscale(banner, (int(banner.get_width() * altoBanner / banner.get_height()), altoBanner))
            fuente = self.assets.cargarFuenteCuento(46)
            textos = [fuente.render(linea, True, (110, 68, 38)) for linea in lineas]
            ancho = max(t.get_width() for t in textos) + banner.get_height() * 2
            cartel = self.estirarCentro(banner, max(banner.get_width(), ancho))
            cartel = self.ponerBordeFino(self.suavizarOrilla(cartel), (128, 76, 40), 5)
            cartel = self.ponerBordeFino(cartel, (84, 46, 22), 2)
            alto = fuente.get_linesize()
            y = cartel.get_height() // 2 - (alto * len(textos)) // 2
            for texto in textos:
                cartel.blit(texto, texto.get_rect(midtop=(cartel.get_width() // 2, y)))
                y += alto
            return cartel
        except Exception as e:
            print(f"Aviso: no se pudo cargar el banner del mensaje: {e}")
            return False

    def dibujarCartel(self, surface: pygame.Surface, cartel: pygame.Surface, inicio: float, fin: float, centro) -> None:
        tiempo = self.outro_timer - inicio
        entrada = min(1.0, tiempo / 0.45)
        salida = min(1.0, max(0.0, (fin - self.outro_timer) / 0.35))
        rebote = 1.0 + 2.7 * (entrada - 1.0) ** 3 + 1.7 * (entrada - 1.0) ** 2
        escala = max(0.05, 0.2 + 0.8 * rebote)
        dibujo = pygame.transform.smoothscale_by(cartel, escala)
        visible = min(entrada, salida)
        if visible < 1.0:
            dibujo.set_alpha(int(255 * visible))
        surface.blit(dibujo, dibujo.get_rect(center=centro))

    def dibujarEnsenanzaFinal(self, surface: pygame.Surface) -> None:
        ensenanza = getattr(self, "ensenanzaFinal", None)
        if not ensenanza or not getattr(self, "finLetrero", None) or self.outro_timer < self.finLetrero:
            return
        if getattr(self, "cartelEnsenanza", None) is None:
            self.cartelEnsenanza = self.crearCartel(ensenanza["gana" if self.is_won else "pierde"])
            self._trigger_ensenanza_voice()
        if self.cartelEnsenanza:
            self.dibujarCartel(surface, self.cartelEnsenanza, self.finLetrero, self.outro_duration,
                               (self.screen_w // 2, self.screen_h // 2))

    def _trigger_ensenanza_voice(self) -> None:
        """Reproduce la locución reflexiva de SEOR para este minijuego si existe en assets/voces/."""
        if not hasattr(self.audio, "play_voice"):
            return
        import re
        raw_name = self.__class__.__name__
        s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', raw_name)
        snake = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        snake_name = snake.replace('_microgame', '').replace('microgame', '')
        mod_name = self.__module__.split('.')[-1]
        raw_short = raw_name.lower().replace("microgame", "")

        state_key = "win" if self.is_won else "lose"
        possible_keys = [
            f"refl_{snake_name}_{state_key}.ogg",
            f"refl_{mod_name}_{state_key}.ogg",
            f"refl_{raw_short}_{state_key}.ogg",
            f"refl_{getattr(self, 'microgame_id', snake_name)}_{state_key}.ogg",
        ]
        if hasattr(self, "secuencia") and getattr(self, "secuencia", "") == "derrota_rabia":
            possible_keys.insert(0, f"refl_{snake_name}_rabia.ogg")
            possible_keys.insert(0, "refl_fritanga_rabia.ogg")

        for key in possible_keys:
            chan = self.audio.play_voice(key, volume_scale=1.0)
            if chan is not None:
                break

    def suavizarColores(self, imagen: pygame.Surface) -> pygame.Surface:
        suave = imagen.copy()
        gris = pygame.transform.grayscale(imagen)
        gris.set_alpha(150)
        suave.blit(gris, (0, 0))
        suave.fill((40, 34, 24), special_flags=pygame.BLEND_RGB_ADD)
        return suave

    def estirarCentro(self, imagen: pygame.Surface, ancho: int) -> pygame.Surface:
        alto = imagen.get_height()
        punta = min(alto, imagen.get_width() // 2, ancho // 2)
        resultado = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        resultado.blit(imagen, (0, 0), (0, 0, punta, alto))
        centro = imagen.subsurface((punta, 0, imagen.get_width() - punta * 2, alto))
        if ancho - punta * 2 > 0:
            resultado.blit(pygame.transform.smoothscale(centro, (ancho - punta * 2, alto)), (punta, 0))
        resultado.blit(imagen, (ancho - punta, 0), (imagen.get_width() - punta, 0, punta, alto))
        return resultado

    def tenir(self, imagen: pygame.Surface, color) -> pygame.Surface:
        tenida = pygame.transform.grayscale(imagen)
        tenida.fill(color, special_flags=pygame.BLEND_RGB_MULT)
        tenida.fill((45, 40, 30), special_flags=pygame.BLEND_RGB_ADD)
        return tenida

    def dibujarBarraTiempo(self, surface: pygame.Surface) -> bool:
        if getattr(self, "barraLista", None) is None:
            try:
                import os
                riel = self.assets.cargarSinFondo(os.path.join("Interfaz", "barraTiempoRiel.jpg"), 300)
                riel = pygame.transform.smoothscale(riel, (int(riel.get_width() * 60 / riel.get_height()), 60))
                ancho_riel = self.TIME_BAR_LAYOUT[2] if self.TIME_BAR_LAYOUT else 1120
                self.rielBarra = self.estirarCentro(riel, ancho_riel)
                relleno = self.assets.cargarSinFondo(os.path.join("Interfaz", "barraTiempoRelleno.jpg"), 300)
                relleno = pygame.transform.smoothscale(relleno, (int(relleno.get_width() * 40 / relleno.get_height()), 40))
                self.rellenosBarra = {
                    "verde": relleno,
                    "amarillo": self.tenir(relleno, (255, 205, 70)),
                    "rojo": self.tenir(relleno, (255, 95, 80)),
                }
                self.barraLista = True
            except Exception as e:
                print(f"Aviso: no se pudo cargar la barra de tiempo: {e}")
                self.barraLista = False
        if not self.barraLista:
            return False

        centro = (self.TIME_BAR_LAYOUT[0], self.TIME_BAR_LAYOUT[1]) if self.TIME_BAR_LAYOUT else (self.screen_w // 2, self.screen_h - 44)
        riel = self.rielBarra.get_rect(center=centro)
        surface.blit(self.rielBarra, riel)

        ratio = max(0.0, min(1.0, self.time_left / self.time_limit))
        if ratio > 0.5:
            relleno = self.rellenosBarra["verde"]
        elif ratio > 0.25:
            relleno = self.rellenosBarra["amarillo"]
        else:
            relleno = self.rellenosBarra["rojo"]

        anchoMax = riel.width - 22
        ancho = int(anchoMax * ratio)
        if ancho >= 8:
            barra = self.estirarCentro(relleno, ancho)
            surface.blit(barra, (riel.x + 11, riel.centery - barra.get_height() // 2))
        return True
