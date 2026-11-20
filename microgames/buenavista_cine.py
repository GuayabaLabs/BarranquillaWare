import os
import math
import time
import random
import threading
from typing import Optional, Callable, List, Tuple, Dict, Any
import pygame
import numpy as np

from core.microgame import BaseMicrogame
from core.asset_manager import AssetManager

HAVE_AUDIO_LIBS = False
try:
    import sounddevice as sd
    HAVE_AUDIO_LIBS = True
except Exception:
    HAVE_AUDIO_LIBS = False


class ShhAudioDetector:
    """
    Detector fónico de '¡SHHH!' o grito autoritario en tiempo real (0 ms de latencia).
    - 100% Offline (sin depender de internet, servidores de Google ni APIs de texto).
    - Analiza bloques continuos de audio a 16000 Hz cada 50 ms.
    - Criterios de detección del 'SHHH':
      1. Amplitud suficiente (volumen audible).
      2. Tasa de Cruces por Cero (ZCR - Zero Crossing Rate) alta (propia del sonido sibilante/fricativo 'SHHH' > 0.18).
      3. O pico de volumen sostenido por encima del umbral de orden/grito.
    """

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self.running: bool = False
        self._stream: Optional[sd.InputStream] = None

        self.audio_level: float = 0.0
        self.zcr_level: float = 0.0
        self._shh_detected_flag: bool = False
        self._lock = threading.Lock()

    def start(self) -> None:
        if os.environ.get("SDL_AUDIODRIVER") == "dummy" or not HAVE_AUDIO_LIBS or self.running:
            return
        self.running = True

        block_size = int(self.sample_rate * 0.06)  # Ventana ultrarrápida de 60ms

        def audio_callback(indata, frames, time_info, status):
            if not self.running:
                return
            samples = indata[:, 0].astype(np.float32)
            max_amp = float(np.max(np.abs(samples)))
            rms = float(np.sqrt(np.mean(samples ** 2)))

            self.audio_level = min(1.0, max_amp / 7000.0)

            # Cálculo de Zero Crossing Rate (ZCR)
            zero_crossings = np.mean(np.abs(np.diff(np.sign(samples)))) / 2.0
            self.zcr_level = float(zero_crossings)

            # Umbrales calibrados para el "SHHH":
            # 1. El sonido "shh" tiene alta frecuencia (ZCR > 0.17) y amplitud moderada (max_amp > 380).
            # 2. O un grito directo de "¡SILENCIO! / ¡EEY!" con alta energía (max_amp > 2200).
            is_shh = (max_amp > 380 and zero_crossings > 0.17)
            is_loud_command = (max_amp > 2200)

            if is_shh or is_loud_command:
                with self._lock:
                    self._shh_detected_flag = True

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=block_size,
                callback=audio_callback
            )
            self._stream.start()
        except Exception:
            self._stream = None

    def poll_shh_detected(self) -> bool:
        """Consulta y resetea el flag si el jugador emitió un 'SHHH'."""
        with self._lock:
            if self._shh_detected_flag:
                self._shh_detected_flag = False
                return True
            return False

    def trigger_virtual_shh(self) -> None:
        """Dispara un 'SHHH' por teclado/fallback."""
        with self._lock:
            self._shh_detected_flag = True

    def stop(self) -> None:
        self.running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None


class SpectatorSeat:
    """
    Controla el estado de una de las 4 butacas del cine en Buenavista:
    - IDLE: Mirando la película tranquilamente.
    - OFFENDING: Iluminado por la pantalla de su celular con barra de tiempo restante.
    - PACIFIED: Sorprendido por el 'SHHH', apaga el celular y vuelve a IDLE.
    """
    STATE_IDLE = "IDLE"
    STATE_OFFENDING = "OFFENDING"
    STATE_PACIFIED = "PACIFIED"

    def __init__(self, index: int, rect_segment: pygame.Rect) -> None:
        self.index = index
        self.rect_segment = rect_segment

        self.state: str = self.STATE_IDLE
        self.current_action: str = ""
        self.time_limit: float = 4.0
        self.time_left: float = 4.0

        # Game Feel y VFX
        self.glow_timer: float = 0.0
        self.pacified_timer: float = 0.0
        self.startle_jump_y: float = 0.0

    def start_offense(self, action: str, duration: float) -> None:
        self.state = self.STATE_OFFENDING
        self.current_action = action
        self.time_limit = duration
        self.time_left = duration
        self.glow_timer = 0.0
        self.startle_jump_y = 0.0

    def pacify(self) -> None:
        self.state = self.STATE_PACIFIED
        self.pacified_timer = 0.70
        self.startle_jump_y = -18.0  # Pequeño salto cómico de susto al escuchar el 'SHHH'

    def update(self, dt: float) -> Optional[str]:
        self.glow_timer += dt * 4.0

        if self.state == self.STATE_OFFENDING:
            self.time_left -= dt
            if self.time_left <= 0.0:
                self.state = self.STATE_IDLE
                return "STRIKE"

        elif self.state == self.STATE_PACIFIED:
            self.pacified_timer -= dt
            # Gravedad suave para el salto de susto
            if self.startle_jump_y < 0.0:
                self.startle_jump_y = min(0.0, self.startle_jump_y + dt * 65.0)

            if self.pacified_timer <= 0.0:
                self.state = self.STATE_IDLE
                self.startle_jump_y = 0.0

        return None


class BuenavistaCineMicrogame(BaseMicrogame):
    # Control por movimiento: gestos de cámara -> teclas del juego (ver BaseMicrogame).
    CAMERA_ACTIONS = {"accion": pygame.K_SPACE, "dedos": (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4)}
    """
    Microjuego: ¡Silencio, que hay función! 🎬
    Nivel 2: Buenavista (30 segundos).
    
    Nueva Mecánica Simplificada y Visceral:
    - ¡CHISTAR / SHHH!: El jugador solo debe emitir un sonido '¡SHHH!' o grito al micrófono.
    - Detección inmediata offline a 0 ms de latencia mediante Zero Crossing Rate y umbral fónico.
    - Sin necesidad de reconocer frases largas por internet.
    - Soporte de fallback accesible con [ESPACIO] o teclas [1, 2, 3, 4].
    - UI de Faltas: Spritesheet de 2 estados (falta vacía y falta con 'X' oficial).
    """

    OFFENSE_ACTIONS: List[str] = [
        "Tomándose una selfie con flash",
        "Grabando la película",
        "Haciendo una videollamada",
        "Viendo TikTok a todo volumen",
    ]

    def __init__(
        self,
        character_id: str = "char",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡CHISTA: SHHH!",
            time_limit=30.0,
            on_complete_callback=on_complete_callback
        )

    def setup_game(self) -> None:
        self.strikes: int = 0
        self.max_strikes: int = 2
        self.pacified_count: int = 0

        # Fuentes
        self.font_shh_prompt = pygame.font.SysFont("Arial Black, Impact, sans-serif", 36)
        self.font_action = pygame.font.SysFont("Arial, Helvetica, sans-serif", 20, bold=True)
        self.font_mic_status = pygame.font.SysFont("Arial, sans-serif", 18, bold=True)
        self.font_hint = pygame.font.SysFont("Arial, sans-serif", 20, bold=True)

        # 1. Fondo de la sala de cine (1920x1080)
        try:
            raw_bg = self.assets.load_surface("fondo_cine_microjuego.png", has_alpha=False)
            self.bg_surf = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))
        except Exception:
            self.bg_surf = pygame.Surface((self.screen_w, self.screen_h))
            self.bg_surf.fill((15, 12, 22))

        # 2. Carga continua de los 4 personajes (2172 x 724 -> 1920 x 640)
        self.num_spectators = 4
        self.row_w = 1920
        self.row_h = 640
        self.row_x = 0
        self.row_y = 440
        self.segment_w = self.row_w // self.num_spectators  # 480 px exactos por butaca

        try:
            raw_c = self.assets.load_surface("npc_comunes_cine_microjuego.png", has_alpha=True)
            self.full_comunes_surf = pygame.transform.smoothscale(raw_c, (self.row_w, self.row_h))
        except Exception:
            self.full_comunes_surf = pygame.Surface((self.row_w, self.row_h), pygame.SRCALPHA)

        try:
            raw_i = self.assets.load_surface("npc_incumpliendo_cine_microjuego.png", has_alpha=True)
            self.full_incumpliendo_surf = pygame.transform.smoothscale(raw_i, (self.row_w, self.row_h))
        except Exception:
            self.full_incumpliendo_surf = pygame.Surface((self.row_w, self.row_h), pygame.SRCALPHA)

        # Segmentos individuales de 480 px cada uno
        self.incumpliendo_segments: List[pygame.Surface] = []
        self.spectators: List[SpectatorSeat] = []

        for i in range(self.num_spectators):
            sub_rect = pygame.Rect(i * self.segment_w, 0, self.segment_w, self.row_h)
            self.incumpliendo_segments.append(self.full_incumpliendo_surf.subsurface(sub_rect))

            seg_screen_rect = pygame.Rect(
                self.row_x + i * self.segment_w,
                self.row_y,
                self.segment_w,
                self.row_h
            )
            self.spectators.append(SpectatorSeat(index=i, rect_segment=seg_screen_rect))

        # 3. UI Faltas: Spritesheet de 2 estados (Vacia y Con X)
        self.hud_ticket_empty: Optional[pygame.Surface] = None
        self.hud_ticket_x: Optional[pygame.Surface] = None
        target_ticket_h = 100

        try:
            raw_v = self.assets.load_surface("ui_falta_vacia_clean.png", has_alpha=True)
            v_box = raw_v.get_bounding_rect()
            cropped_v = raw_v.subsurface(v_box)
            v_w = int(cropped_v.get_width() * (target_ticket_h / cropped_v.get_height()))
            self.hud_ticket_empty = pygame.transform.smoothscale(cropped_v, (v_w, target_ticket_h))
            self.ticket_w = v_w
            self.ticket_h = target_ticket_h
        except Exception:
            self.ticket_w = 175
            self.ticket_h = 100

        try:
            raw_x = self.assets.load_surface("ui_falta_x_clean.png", has_alpha=True)
            x_box = raw_x.get_bounding_rect()
            cropped_x = raw_x.subsurface(x_box)
            x_w = int(cropped_x.get_width() * (target_ticket_h / cropped_x.get_height()))
            self.hud_ticket_x = pygame.transform.smoothscale(cropped_x, (x_w, target_ticket_h))
        except Exception:
            pass

        # 4. Detector fónico instantáneo de '¡SHHH!'
        self.shh_detector = ShhAudioDetector()
        if HAVE_AUDIO_LIBS:
            self.shh_detector.start()

        self.spawn_cooldown: float = 1.0
        self.flash_screen_alpha: float = 0.0
        self.last_shh_visual_pulse: float = 0.0

    def cleanup(self) -> None:
        if hasattr(self, "shh_detector"):
            self.shh_detector.stop()

    def exit(self) -> None:
        self.cleanup()
        super().exit()

    def update(self, dt: float) -> None:
        if hasattr(self.audio, "update"):
            self.audio.update(dt)
        if self.phase == self.PHASE_INTRO:
            self.intro_timer += dt
            if self.intro_timer >= self.intro_duration:
                self.phase = self.PHASE_PLAY

        elif self.phase == self.PHASE_PLAY:
            self.time_left -= dt
            self.update_game(dt)
            if self.time_left <= 0.0 and not self.is_finished:
                self.time_left = 0.0
                self.cleanup()
                self.finish_game(won=True)

        elif self.phase == self.PHASE_OUTRO:
            self.update_outro(dt)

    def update_game(self, dt: float) -> None:
        if self.is_finished:
            return

        if self.flash_screen_alpha > 0.0:
            self.flash_screen_alpha = max(0.0, self.flash_screen_alpha - dt * 3.0)
        if self.last_shh_visual_pulse > 0.0:
            self.last_shh_visual_pulse = max(0.0, self.last_shh_visual_pulse - dt * 4.0)

        # 1. Escucha fónica reactiva continua (0 ms de latencia)
        if HAVE_AUDIO_LIBS and self.shh_detector.poll_shh_detected():
            self._on_player_shhed()

        # 2. Actualizar butacas
        active_offenders: List[SpectatorSeat] = []
        for spectator in self.spectators:
            res = spectator.update(dt)
            if res == "STRIKE":
                self._apply_strike("¡El espectador guardó el celular impune!")
            elif spectator.state == SpectatorSeat.STATE_OFFENDING:
                active_offenders.append(spectator)

        # 3. Dificultad progresiva (30s)
        time_elapsed = max(0.0, self.time_limit - self.time_left)
        progress_ratio = min(1.0, time_elapsed / self.time_limit)

        current_window_duration = 4.8 - (progress_ratio * 2.5)
        min_cooldown = 1.6 - (progress_ratio * 0.9)

        self.spawn_cooldown -= dt
        if self.spawn_cooldown <= 0.0 and len(active_offenders) == 0:
            self._spawn_next_offense(current_window_duration)
            self.spawn_cooldown = min_cooldown

    def _spawn_next_offense(self, duration: float) -> None:
        idle_spectators = [s for s in self.spectators if s.state == SpectatorSeat.STATE_IDLE]
        if not idle_spectators:
            return

        chosen = random.choice(idle_spectators)
        action = self.OFFENSE_ACTIONS[chosen.index % len(self.OFFENSE_ACTIONS)]
        chosen.start_offense(action, duration)
        self.flash_screen_alpha = 0.35
        if hasattr(self.audio, "play_pigeon"):
            self.audio.play_pigeon()

    def _on_player_shhed(self) -> None:
        """El jugador emitió un 'SHHH' o pulsó espacio: apaciguar al infractor activo."""
        self.last_shh_visual_pulse = 1.0
        active_offenders = [s for s in self.spectators if s.state == SpectatorSeat.STATE_OFFENDING]
        if active_offenders:
            # Apaciguar al infractor activo inmediatamente
            target = active_offenders[0]
            target.pacify()
            self.pacified_count += 1
            if hasattr(self.audio, "play_hit"):
                self.audio.play_hit()

    def _apply_strike(self, reason: str) -> None:
        self.strikes += 1
        self.flash_screen_alpha = 0.65
        if hasattr(self.audio, "play_miss"):
            self.audio.play_miss()
        if self.strikes >= self.max_strikes:
            self.cleanup()
            self.finish_game(won=False)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if self.is_finished:
            return

        if event.type == pygame.KEYDOWN:
            # Barra espaciadora: Chistido manual instantáneo
            if event.key == pygame.K_SPACE:
                self._on_player_shhed()

            # Atajo numérico directo para butacas 1 a 4
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                idx = event.key - pygame.K_1
                if 0 <= idx < len(self.spectators):
                    spec = self.spectators[idx]
                    if spec.state == SpectatorSeat.STATE_OFFENDING:
                        spec.pacify()
                        self.pacified_count += 1
                        self.last_shh_visual_pulse = 1.0
                        if hasattr(self.audio, "play_hit"):
                            self.audio.play_hit()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # El cursor MediaPipe permite apuntar y pellizcar sobre la butaca infractora.
            for spec in self.spectators:
                if spec.rect_segment.collidepoint(event.pos) and spec.state == SpectatorSeat.STATE_OFFENDING:
                    spec.pacify()
                    self.pacified_count += 1
                    self.last_shh_visual_pulse = 1.0
                    if hasattr(self.audio, "play_hit"):
                        self.audio.play_hit()
                    break

    def render_game(self, surface: pygame.Surface) -> None:
        # 1. Fondo de la sala
        surface.blit(self.bg_surf, (0, 0))

        # 2. Luz de proyector
        flicker = 28 + int(math.sin(pygame.time.get_ticks() * 0.005) * 10)
        light_surf = pygame.Surface((self.screen_w, 280), pygame.SRCALPHA)
        light_surf.fill((220, 240, 255, flicker))
        surface.blit(light_surf, (0, 0))

        # 3. Flash reactivo
        if self.flash_screen_alpha > 0.0:
            flash_overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            alpha_val = int(self.flash_screen_alpha * 120)
            flash_overlay.fill((255, 255, 240, alpha_val))
            surface.blit(flash_overlay, (0, 0))

        # 4. Fila continua de espectadores normales
        surface.blit(self.full_comunes_surf, (self.row_x, self.row_y))

        # 5. Segmento del espectador infractor / apaciguado
        for spec in self.spectators:
            seg_x = self.row_x + spec.index * self.segment_w
            seg_y = self.row_y + int(spec.startle_jump_y)

            if spec.state == SpectatorSeat.STATE_OFFENDING:
                seg_surf = self.incumpliendo_segments[spec.index]

                # Resplandor de pantalla de celular
                glow_r = int(140 + math.sin(spec.glow_timer) * 16)
                glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(
                    glow_surf,
                    (255, 255, 200, 65),
                    (glow_r, glow_r),
                    glow_r
                )
                surface.blit(glow_surf, (seg_x + self.segment_w // 2 - glow_r, seg_y + 180 - glow_r))

                surface.blit(seg_surf, (seg_x, seg_y))
                self._render_shh_bubble(surface, spec)

            elif spec.state == SpectatorSeat.STATE_PACIFIED:
                # Al pacificar vuelve al frame normal pero con salto cómico
                if spec.startle_jump_y < 0.0:
                    surface.blit(
                        self.full_comunes_surf.subsurface((spec.index * self.segment_w, 0, self.segment_w, self.row_h)),
                        (seg_x, seg_y)
                    )
                self._render_pacified_tag(surface, spec)

        # 6. HUD Superior Oficial (Faltas con spritesheet e indicador de micrófono)
        self._render_hud(surface)

    def _render_shh_bubble(self, surface: pygame.Surface, spec: SpectatorSeat) -> None:
        """Globo con orden directa e intuitiva de ¡CHISTA: SHHH!"""
        center_x = spec.rect_segment.centerx
        bubble_y = self.row_y - 85

        shh_surf = self.font_shh_prompt.render("¡CHISTA: SHHH!", True, (255, 240, 40))
        action_surf = self.font_action.render(spec.current_action, True, (220, 220, 220))

        bw = max(shh_surf.get_width() + 48, 360)
        bh = 110
        bx = max(10, min(self.screen_w - bw - 10, center_x - bw // 2))

        bubble_bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bubble_bg.fill((20, 16, 32, 235))
        pygame.draw.rect(bubble_bg, (255, 70, 70), (0, 0, bw, bh), width=4, border_radius=14)
        surface.blit(bubble_bg, (bx, bubble_y))

        surface.blit(action_surf, (bx + (bw - action_surf.get_width()) // 2, bubble_y + 12))
        surface.blit(shh_surf, (bx + (bw - shh_surf.get_width()) // 2, bubble_y + 40))

        # Barra de tiempo restante de la infracción
        ratio = max(0.0, min(1.0, spec.time_left / spec.time_limit))
        bar_w = bw - 32
        bar_h = 10
        bar_x = bx + 16
        bar_y = bubble_y + bh - 18

        pygame.draw.rect(surface, (50, 40, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=5)
        bar_color = (80, 255, 120) if ratio > 0.45 else ((255, 200, 40) if ratio > 0.2 else (255, 50, 50))
        pygame.draw.rect(surface, bar_color, (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=5)

    def _render_pacified_tag(self, surface: pygame.Surface, spec: SpectatorSeat) -> None:
        """Etiqueta visual de apaciguamiento."""
        center_x = spec.rect_segment.centerx
        tag_y = self.row_y - 45
        tag_surf = self.font_action.render("¡GUARDÓ EL CELULAR!", True, (80, 255, 120))
        tag_bg = pygame.Surface((tag_surf.get_width() + 24, 32), pygame.SRCALPHA)
        tag_bg.fill((10, 40, 20, 225))
        pygame.draw.rect(tag_bg, (80, 255, 120), (0, 0, tag_bg.get_width(), 32), width=2, border_radius=8)
        surface.blit(tag_bg, (center_x - tag_bg.get_width() // 2, tag_y))
        surface.blit(tag_surf, (center_x - tag_surf.get_width() // 2, tag_y + 4))

    def _render_hud(self, surface: pygame.Surface) -> None:
        """
        Renderiza las 2 faltas usando el spritesheet oficial:
        - Si no hay falta en esa ranura: muestra `ui_falta_vacia_clean.png`.
        - Si hay falta acumulada: muestra `ui_falta_x_clean.png`.
        """
        hud_x = 40
        hud_y = 25

        # Renderizar las dos ranuras de faltas
        spacing = 20
        for i in range(self.max_strikes):
            slot_x = hud_x + i * (self.ticket_w + spacing)
            is_struck = (i < self.strikes)

            if is_struck and self.hud_ticket_x:
                surface.blit(self.hud_ticket_x, (slot_x, hud_y))
            elif self.hud_ticket_empty:
                surface.blit(self.hud_ticket_empty, (slot_x, hud_y))
            else:
                # Fallback geométrico limpio
                col = (230, 40, 40) if is_struck else (60, 60, 80)
                pygame.draw.rect(surface, col, (slot_x, hud_y, self.ticket_w, self.ticket_h), border_radius=12)

        # 2. Vúmetro del Micrófono Fónico (Centro Superior)
        mic_box_w = 460
        mic_box_h = 75
        mic_x = (self.screen_w - mic_box_w) // 2
        mic_y = 25

        mic_bg = pygame.Surface((mic_box_w, mic_box_h), pygame.SRCALPHA)
        mic_bg.fill((10, 10, 18, 200))
        border_col = (255, 240, 80) if self.last_shh_visual_pulse > 0.0 else (50, 80, 110)
        pygame.draw.rect(mic_bg, border_col, (0, 0, mic_box_w, mic_box_h), width=2, border_radius=12)
        surface.blit(mic_bg, (mic_x, mic_y))

        status_text = "¡SHHH DETECTADO!" if self.last_shh_visual_pulse > 0.0 else "MICRÓFONO ESCUCHANDO: ¡SHHH!"
        status_col = (255, 240, 80) if self.last_shh_visual_pulse > 0.0 else (80, 255, 120)
        # Icono vectorial de micrófono (evita glifo roto en Arial de Windows)
        mx_icon = mic_x + 28
        my_icon = mic_y + 23
        pygame.draw.rect(surface, status_col, (mx_icon - 4, my_icon - 9, 8, 13), border_radius=4)
        pygame.draw.arc(surface, status_col, (mx_icon - 7, my_icon - 4, 14, 11), 3.14, 6.28, 2)
        pygame.draw.line(surface, status_col, (mx_icon, my_icon + 7), (mx_icon, my_icon + 11), 2)
        pygame.draw.line(surface, status_col, (mx_icon - 4, my_icon + 11), (mx_icon + 4, my_icon + 11), 2)

        status_surf = self.font_mic_status.render(status_text, True, status_col)
        surface.blit(status_surf, (mic_x + 44, mic_y + 13))

        # Barra de nivel y sibilancia de audio
        pygame.draw.rect(surface, (40, 40, 50), (mic_x + 20, mic_y + 45, 420, 14), border_radius=5)
        active_w = int(420 * min(1.0, (self.shh_detector.audio_level * 2.0 + self.shh_detector.zcr_level * 0.8))) if HAVE_AUDIO_LIBS else 0
        bar_col = (255, 220, 60) if self.last_shh_visual_pulse > 0.0 else (80, 255, 120)
        pygame.draw.rect(surface, bar_col, (mic_x + 20, mic_y + 45, active_w, 14), border_radius=5)

    def get_result_data(self) -> Dict[str, Any]:
        return {
            "won": self.is_won,
            "time_survived": self.time_limit - max(0.0, self.time_left),
            "strikes": self.strikes,
            "pacified_count": self.pacified_count,
        }
