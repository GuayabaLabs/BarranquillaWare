import os
import math
import random
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Tuple, Dict, Any, Set
import pygame

from core.microgame import BaseMicrogame
from core.asset_manager import AssetManager
from core.camera_gestures import CameraGestureInput
from microgames.buenavista_trend.beatmap import MusicalNoteEvent, IMITADORA_BEATMAP_DATA


class BuenavistaTrendMicrogame(BaseMicrogame):
    """
    Microjuego de ritmo y supervivencia: «El Trend en Buenavista» (Inspirado en Piano Tiles).
    - Ubicación: Centro Comercial Buenavista, Barranquilla.
    - Duración: 30 segundos.
    - Categoría: Supervivencia (5 corazones de vida).
    - Controles: D/F/J/K, o botones A/B/X/Y del mando (carriles 1–4).
    - Mensaje educativo: No necesitas seguir todas las tendencias para disfrutar de las redes sociales.
    """

    LANE_KEYS: Tuple[int, int, int, int] = (pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k)
    LANE_LABELS: Tuple[str, str, str, str] = ("D", "F", "J", "K")
    # SDL suele exponer A/B/X/Y como botones 0/1/2/3 en mandos XInput.
    GAMEPAD_BUTTONS: Dict[int, int] = {0: 0, 1: 1, 2: 2, 3: 3}

    # Ventanas temporales configurables (en segundos)
    DEFAULT_PERFECT_WINDOW: float = 0.080  # ±80 ms
    DEFAULT_GOOD_WINDOW: float = 0.150     # ±150 ms

    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None,
        perfect_window: float = DEFAULT_PERFECT_WINDOW,
        good_window: float = DEFAULT_GOOD_WINDOW,
    ) -> None:
        self.character_id = character_id
        self.perfect_window: float = perfect_window
        self.good_window: float = good_window
        super().__init__(
            command_text="¡SIGUE EL TREND!\n[D] [F] [J] [K]",
            time_limit=30.0,
            on_complete_callback=on_complete_callback
        )
        self.outro_duration = 1.65

    def setup_game(self) -> None:
        """Inicializa recursos gráficos, recorte 4x2, geometría proporcional del celular y mapa musical."""
        # Sistema de 5 vidas y contadores de desempeño
        self.max_lives: int = 5
        self.lives: int = 5
        self.hits_perfect: int = 0
        self.hits_good: int = 0
        self.misses_count: int = 0
        self.combo: int = 0
        self.max_combo: int = 0

        # Protección anti-repeat y cooldown de fallo por pulsación incorrecta
        self.held_keys: Set[int] = set()
        self.wrong_press_cooldown: float = 0.0
        self.wrong_press_protection_interval: float = 0.22  # Intervalo de protección para pulsaciones erróneas

        # Estado de reproducción musical sincronizada
        self.music_started: bool = False
        self.song_elapsed: float = 0.0
        self._last_mixer_pos_sec: float = 0.0
        self.music_track_name: str = "imitadora_ost_piano_tiles_microjuego.ogg"

        # Efectos visuales (Game Feel cozy)
        self.trauma: float = 0.0
        self.max_shake_offset: float = 16.0
        self.red_flash_alpha: float = 0.0
        self.yellow_glow_alpha: float = 0.0
        self.heart_loss_anims: List[Dict[str, Any]] = []
        self.like_particles: List[Dict[str, Any]] = []
        self.floating_feedbacks: List[Dict[str, Any]] = []
        self.celebration_particles: List[Dict[str, Any]] = []
        self.lane_press_timers: List[float] = [0.0, 0.0, 0.0, 0.0]
        self.camera_input = CameraGestureInput.get_instance()
        self.camera_input.start()

        # Tipografías
        self.font_keys = pygame.font.SysFont("Arial Black, Impact, sans-serif", 26)
        self.font_hud = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 20, bold=True)
        self.font_timer_num = pygame.font.SysFont("Segoe UI Black, Arial Black, Impact, sans-serif", 28)
        self.font_feedback = pygame.font.SysFont("Arial Black, Impact, sans-serif", 26)
        self.font_edu = pygame.font.SysFont("Arial, Helvetica, sans-serif", 22, bold=True)

        # 1. Cargar reloj contador oficial (contador_microjuegos.png) igual que en los demás minijuegos
        self.spr_counter: Optional[pygame.Surface] = None
        try:
            raw_cnt = self.assets.load_cropped_surface("contador_microjuegos.png", alpha_threshold=15)
            cnt_h = 92
            cnt_w = int(raw_cnt.get_width() * (cnt_h / float(max(1, raw_cnt.get_height()))))
            self.spr_counter = pygame.transform.smoothscale(raw_cnt, (cnt_w, cnt_h))
        except Exception:
            self.spr_counter = None

        # 2. Capa 1: Fondo de Buenavista con ligero oscurecimiento pastel
        self._load_background_layer()

        # 2. Capa 2: Celular PNG centrado ocupando ~85% de la altura disponible sin deformarse
        # y cálculo matemático proporcional de carriles y zona de impacto
        self._load_phone_and_compute_geometry()

        # 3. Capa 3: Recorte matemático uniforme 4x2 del spritesheet de teclas musicales
        self._load_and_slice_spritesheet()

        # 4. Capa 4: Recursos de interfaz adicional (corazones, barra musical y reloj)
        self._build_hud_surfaces()

        # 5. Construir lista de eventos musicales independientes del renderizado
        self._build_musical_events()

        self.iniciarPublico()

    def _load_background_layer(self) -> None:
        """Carga el fondo de Buenavista a resolución lógica y aplica un velo suave para destacar el celular."""
        try:
            raw_bg = self.assets.load_surface("fondo_piano_tiles_microjuego.png", has_alpha=False)
            scaled_bg = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))
        except Exception:
            scaled_bg = pygame.Surface((self.screen_w, self.screen_h))
            scaled_bg.fill((235, 205, 225))

        # Ligero oscurecimiento violáceo/pastel para destacar el celular sin perder la estética acuarela
        dim_overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        dim_overlay.fill((28, 18, 48, 72))
        scaled_bg.blit(dim_overlay, (0, 0))
        self.bg_surface: pygame.Surface = scaled_bg

    def _load_phone_and_compute_geometry(self) -> None:
        """
        Carga `telefono_piano_tiles_microjuego.png`, recorta sus márgenes transparentes externos,
        lo escala al 85% de la altura de la pantalla manteniendo su proporción exacta, y calcula
        las coordenadas de los 4 carriles, área interior jugable y línea de impacto de forma
        100% proporcional (independiente de la resolución).
        """
        try:
            raw_phone = self.assets.load_surface("telefono_piano_tiles_microjuego.png", has_alpha=True)
        except Exception:
            raw_phone = pygame.Surface((908, 1166), pygame.SRCALPHA)
            pygame.draw.rect(raw_phone, (90, 40, 140, 255), raw_phone.get_rect(), border_radius=40)

        raw_w, raw_h = raw_phone.get_size()
        bbox = raw_phone.get_bounding_rect(min_alpha=20)
        if bbox.width <= 0 or bbox.height <= 0:
            bbox = pygame.Rect(0, 0, raw_w, raw_h)

        cropped_phone = raw_phone.subsurface(bbox).copy()
        crop_w, crop_h = cropped_phone.get_size()

        # El celular ocupa el 85% de la altura disponible respetando su aspect ratio
        target_phone_h = int(round(self.screen_h * 0.85))
        scale_factor = target_phone_h / float(max(1, crop_h))
        target_phone_w = int(round(crop_w * scale_factor))

        self.phone_surface: pygame.Surface = pygame.transform.smoothscale(
            cropped_phone, (target_phone_w, target_phone_h)
        )
        self.phone_rect: pygame.Rect = self.phone_surface.get_rect(
            center=(self.screen_w // 2, self.screen_h // 2)
        )

        # Proporciones relativas medidas sobre la textura original (1312 x 1199) respecto al bbox del teléfono:
        # En la textura original:
        # - Bbox del teléfono: x=[199, 1107] (w=908), y=[15, 1181] (h=1166)
        # - Pantalla interior entre biseles: x=[238, 1068]
        # - Líneas divisorias blancas entre carriles: x = 437.5, 642.0, 850.0
        # - Centros de las 4 zonas de pulsación inferiores: x = 341.0, 541.5, 747.0, 956.5
        # - Borde inferior del encabezado REC: y = 172
        # - Centro de las 4 zonas luminosas inferiores: y = 1048
        # - Borde inferior de la pantalla interior (antes del bisel rosa inferior): y = 1138
        def rel_x(orig_x: float) -> int:
            norm_x = (orig_x - bbox.left) / float(max(1, crop_w))
            return int(round(self.phone_rect.left + norm_x * self.phone_rect.width))

        def rel_y(orig_y: float) -> int:
            norm_y = (orig_y - bbox.top) / float(max(1, crop_h))
            return int(round(self.phone_rect.top + norm_y * self.phone_rect.height))

        # Límites horizontales de cada uno de los 4 carriles dentro del celular
        lane_bounds_orig = [
            (238.0, 435.0),
            (440.0, 640.0),
            (644.0, 848.0),
            (852.0, 1066.0),
        ]
        self.lane_rects: List[pygame.Rect] = []
        self.lane_centers_x: List[int] = []

        play_top_y = rel_y(172.0)     # Justo debajo del encabezado oscuro REC
        play_bottom_y = rel_y(1136.0) # Justo encima del bisel rosa inferior
        play_h = max(10, play_bottom_y - play_top_y)

        for x0_orig, x1_orig in lane_bounds_orig:
            lx0 = rel_x(x0_orig)
            lx1 = rel_x(x1_orig)
            l_rect = pygame.Rect(lx0, play_top_y, max(10, lx1 - lx0), play_h)
            self.lane_rects.append(l_rect)
            self.lane_centers_x.append(l_rect.centerx)

        # Rectángulo de recorte (clipping) estricto del área jugable interior:
        # Garantiza que las teclas NUNCA atraviesen los bordes del celular ni aparezcan sobre el encabezado REC
        inner_left = self.lane_rects[0].left
        inner_right = self.lane_rects[-1].right
        self.playable_clip_rect = pygame.Rect(
            inner_left,
            play_top_y,
            inner_right - inner_left,
            play_h
        )

        # Línea de impacto centrada en las 4 zonas luminosas inferiores del PNG
        self.hit_line_y: int = rel_y(1048.0)
        self.hit_box_top_y: int = rel_y(1006.0)
        self.hit_box_bottom_y: int = rel_y(1090.0)

        # Punto de aparición en la parte superior del área jugable (entrando suavemente desde el borde del clip)
        min_lane_w = min(r.width for r in self.lane_rects)
        self.tile_size: int = int(round(min_lane_w * 0.78))  # Ligeramente menor que el ancho del carril
        self.spawn_y: float = float(play_top_y - self.tile_size * 0.45)
        self.fall_distance: float = float(self.hit_line_y) - self.spawn_y

    def _load_and_slice_spritesheet(self) -> None:
        """
        Extrae los 8 sprites de `spritesheet_teclas_piano_tiles_microjuego.png`
        mediante una cuadrícula matemática uniforme de 4 columnas × 2 filas (W/4 × H/2),
        manteniendo las proporciones de cada celda sin estirarlas ni deformarlas.
        - Fila 0 (índice 0): Teclas normales (Nota rosa, Fuego naranja, Tenis morado, Claqueta rosa).
        - Fila 1 (índice 1): Teclas activadas con brillo amarillo.
        """
        try:
            sheet = self.assets.load_surface("spritesheet_teclas_piano_tiles_microjuego.png", has_alpha=True)
        except Exception:
            sheet = pygame.Surface((800, 400), pygame.SRCALPHA)
            sheet.fill((255, 105, 180, 220))

        sheet_w, sheet_h = sheet.get_size()
        cols = 4
        rows = 2

        self.normal_tile_sprites: List[pygame.Surface] = []
        self.active_tile_sprites: List[pygame.Surface] = []
        self.raw_grid_cells: List[List[pygame.Surface]] = [[], []]

        for r in range(rows):
            y0 = int(round(r * (sheet_h / float(rows))))
            y1 = int(round((r + 1) * (sheet_h / float(rows))))
            cell_h = max(1, y1 - y0)

            for c in range(cols):
                x0 = int(round(c * (sheet_w / float(cols))))
                x1 = int(round((c + 1) * (sheet_w / float(cols))))
                cell_w = max(1, x1 - x0)

                cell_rect = pygame.Rect(x0, y0, cell_w, cell_h)
                cell_surf = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
                cell_surf.blit(sheet, (0, 0), cell_rect)
                self.raw_grid_cells[r].append(cell_surf)

                # Escalar manteniendo proporción (1:1 uniforme respecto a la celda cuadrada W/4 x H/2)
                aspect = cell_w / float(cell_h)
                if aspect >= 1.0:
                    target_w = self.tile_size
                    target_h = max(1, int(round(self.tile_size / aspect)))
                else:
                    target_h = self.tile_size
                    target_w = max(1, int(round(self.tile_size * aspect)))

                scaled_tile = pygame.transform.smoothscale(cell_surf, (target_w, target_h))
                if r == 0:
                    self.normal_tile_sprites.append(scaled_tile)
                else:
                    self.active_tile_sprites.append(scaled_tile)

    def _build_hud_surfaces(self) -> None:
        """Prepara los corazones de vida (estilo acuarela cozy) y elementos de progreso musical."""
        self.heart_full_surf = self._create_heart_surface(filled=True, size=56)
        self.heart_empty_surf = self._create_heart_surface(filled=False, size=56)
        self.mini_heart_surf = self._create_heart_surface(filled=True, size=24)

        try:
            self.heart_full_surf = self.assets.cargarSinFondo(os.path.join("Piano", "corazonLleno.jpg"), 56)
            self.heart_empty_surf = self.assets.cargarSinFondo(os.path.join("Piano", "corazonVacio.jpg"), 56)
            self.mini_heart_surf = self.assets.cargarSinFondo(os.path.join("Piano", "corazonLleno.jpg"), 24)
        except Exception as e:
            print(f"[BuenavistaTrend] Aviso: no se pudieron cargar los corazones pintados: {e}")

    def _create_heart_surface(self, filled: bool, size: int = 56) -> pygame.Surface:
        """Genera un corazón estilizado con borde acogedor coherente con la paleta de BarranquillaWare."""
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        r = int(size * 0.24)
        left_c = (cx - int(size * 0.17), cy - int(size * 0.08))
        right_c = (cx + int(size * 0.17), cy - int(size * 0.08))
        bottom_pt = (cx, cy + int(size * 0.36))

        main_col = (255, 85, 135) if filled else (95, 75, 115, 170)
        border_col = (65, 20, 48) if filled else (60, 45, 75, 200)

        # Sombra suave
        if filled:
            pygame.draw.circle(surf, (40, 15, 35, 90), (left_c[0] + 2, left_c[1] + 4), r + 2)
            pygame.draw.circle(surf, (40, 15, 35, 90), (right_c[0] + 2, right_c[1] + 4), r + 2)
            pygame.draw.polygon(
                surf,
                (40, 15, 35, 90),
                [
                    (left_c[0] - r + 2, left_c[1] + int(r * 0.35) + 4),
                    (right_c[0] + r + 2, right_c[1] + int(r * 0.35) + 4),
                    (bottom_pt[0] + 2, bottom_pt[1] + 4),
                ]
            )

        # Borde exterior
        pygame.draw.circle(surf, border_col, left_c, r + 3)
        pygame.draw.circle(surf, border_col, right_c, r + 3)
        pygame.draw.polygon(
            surf,
            border_col,
            [
                (left_c[0] - r - 2, left_c[1] + int(r * 0.35)),
                (right_c[0] + r + 2, right_c[1] + int(r * 0.35)),
                (bottom_pt[0], bottom_pt[1] + 3),
            ]
        )

        # Relleno interior
        pygame.draw.circle(surf, main_col, left_c, r)
        pygame.draw.circle(surf, main_col, right_c, r)
        pygame.draw.polygon(
            surf,
            main_col,
            [
                (left_c[0] - r + 1, left_c[1] + int(r * 0.35)),
                (right_c[0] + r - 1, right_c[1] + int(r * 0.35)),
                bottom_pt,
            ]
        )

        # Brillo superior acuarela
        if filled:
            hi_r = max(2, int(r * 0.42))
            pygame.draw.circle(surf, (255, 205, 225), (left_c[0] - int(r * 0.28), left_c[1] - int(r * 0.28)), hi_r)

        return surf

    def _build_musical_events(self) -> None:
        """
        Construye la lista estructurada de eventos musicales a partir del mapa de la canción,
        calculando el `spawn_time` exacto según la distancia real de recorrido y la velocidad de caída.
        """
        self.musical_events: List[MusicalNoteEvent] = []
        for impact_t, lane_idx, spr_type, speed in IMITADORA_BEATMAP_DATA:
            travel_time = self.fall_distance / max(1.0, speed)
            spawn_t = max(0.0, impact_t - travel_time)
            ev = MusicalNoteEvent(
                impact_time=impact_t,
                lane=lane_idx % 4,
                sprite_type=spr_type % 4,
                fall_speed=speed,
                spawn_time=spawn_t,
                y=self.spawn_y,
            )
            self.musical_events.append(ev)

    def _start_music_if_needed(self) -> None:
        """Inicia la pista instrumental 'Imitadora' al comenzar la fase de juego."""
        if self.music_started:
            return
        self.music_started = True
        self.song_elapsed = 0.0
        self._last_mixer_pos_sec = 0.0

        track_path = os.path.join("assets", self.music_track_name)
        if pygame.mixer.get_init() and os.path.exists(track_path):
            try:
                pygame.mixer.music.load(track_path)
                vol = getattr(self.audio, "music_volume", 0.75)
                pygame.mixer.music.set_volume(vol)
                if getattr(self.audio, "music_enabled", True):
                    pygame.mixer.music.play(loops=0, start=0.0)
                self.audio.current_track = self.music_track_name
            except Exception:
                pass

    def _stop_or_fade_music(self) -> None:
        """Detiene o atenúa suavemente la música al finalizar el microjuego."""
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.fadeout(450)
            except Exception:
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
        if hasattr(self.audio, "current_track") and self.audio.current_track == self.music_track_name:
            self.audio.current_track = None

    def cleanup(self) -> None:
        """Limpia recursos activos y detiene la pista musical al salir."""
        self._stop_or_fade_music()
        self.held_keys.clear()

    def exit(self) -> None:
        self.cleanup()
        if hasattr(self.audio, "sonarEscritura"):
            self.audio.sonarEscritura(False)
        # La cámara pertenece al motor y se comparte con el resto de escenas.

    def finish_game(self, won: bool) -> None:
        """Detiene la aparición de notas, atenúa la música, lanza celebración/fallo y comunica resultado."""
        if self.is_finished:
            return
        self._stop_or_fade_music()
        if won:
            self._spawn_victory_celebration()
        else:
            self.red_flash_alpha = 180.0
            self.trauma = 0.85
        super().finish_game(won=won)

        if getattr(self, "letreroResultado", None) is not None:
            self.finLetrero = 3.0
            self.inicioTendencias = 13.0
            self.outro_duration = max(self.outro_duration, 17.0 if won else 13.0)

    def _sync_audio_clock(self, dt: float) -> None:
        """
        Sincroniza el reloj musical (`self.song_elapsed`) con el tiempo real de reproducción
        de `pygame.mixer.music.get_pos()`, manteniendo continuidad con `dt` cuando el mixer
        opera en modo headless o entre actualizaciones de buffer.
        """
        self.song_elapsed += dt
        if pygame.mixer.get_init() and getattr(self.audio, "music_enabled", True):
            try:
                if pygame.mixer.music.get_busy():
                    pos_ms = pygame.mixer.music.get_pos()
                    if pos_ms >= 0:
                        mixer_sec = pos_ms / 1000.0
                        # Si el reloj de hardware avanzó de forma continua respecto al último sample,
                        # anclar suavemente para evitar drift sin pisar saltos manuales en tests.
                        if mixer_sec > self._last_mixer_pos_sec:
                            self._last_mixer_pos_sec = mixer_sec
                            if abs(mixer_sec - self.song_elapsed) < 0.35:
                                self.song_elapsed = 0.7 * self.song_elapsed + 0.3 * mixer_sec
            except Exception:
                pass

    def update(self, dt: float) -> None:
        """Ciclo principal de estados (INTRO -> PLAY -> OUTRO) con victoria de supervivencia a los 30s."""
        if self.phase == self.PHASE_INTRO:
            self.intro_timer += dt
            if self.intro_timer >= self.intro_duration:
                self.phase = self.PHASE_PLAY
                self._start_music_if_needed()

        elif self.phase == self.PHASE_PLAY:
            self._start_music_if_needed()
            self.time_left -= dt
            self.update_game(dt)
            if self.time_left <= 0.0 and not self.is_finished:
                self.time_left = 0.0
                # En supervivencia, llegar a los 30s conservando al menos 1 corazón es VICTORIA
                self.finish_game(won=(self.lives > 0))

        elif self.phase == self.PHASE_OUTRO:
            self.outro_timer += dt
            self._update_particles(dt)
            if self.outro_timer >= self.outro_duration:
                if self.on_complete_callback:
                    self.on_complete_callback(self.is_won)

    def update_game(self, dt: float) -> None:
        if self.is_finished:
            return

        self.actualizarPublico(dt)

        # Entrada opcional de MediaPipe: los cuatro dedos son los cuatro carriles.
        for lane in range(4):
            if self.camera_input.consume_finger(lane):
                self._process_lane_press(lane)

        # 1. Sincronizar tiempo musical con el audio real
        self._sync_audio_clock(dt)

        # 2. Actualizar temporizadores de protección y efectos
        if self.wrong_press_cooldown > 0.0:
            self.wrong_press_cooldown = max(0.0, self.wrong_press_cooldown - dt)

        for i in range(4):
            if self.lane_press_timers[i] > 0.0:
                self.lane_press_timers[i] = max(0.0, self.lane_press_timers[i] - dt)

        if self.trauma > 0.0:
            self.trauma = max(0.0, self.trauma - dt * 2.4)
        if self.red_flash_alpha > 0.0:
            self.red_flash_alpha = max(0.0, self.red_flash_alpha - dt * 360.0)
        if self.yellow_glow_alpha > 0.0:
            self.yellow_glow_alpha = max(0.0, self.yellow_glow_alpha - dt * 420.0)

        # 3. Actualizar eventos musicales y posición de teclas descendentes
        for ev in self.musical_events:
            if ev.state == "pending" and self.song_elapsed >= ev.spawn_time:
                ev.spawned = True
                ev.state = "falling"

            if ev.state == "falling":
                # Posición sincronizada con el reloj musical real y la velocidad de descenso
                time_to_impact = ev.impact_time - self.song_elapsed
                ev.y = float(self.hit_line_y) - time_to_impact * ev.fall_speed

                # Si la nota atraviesa la ventana de acierto sin ser activada -> FALLO
                if self.song_elapsed - ev.impact_time > self.good_window:
                    self._mark_note_missed(ev, reason="¡SE PASÓ!")

            elif ev.state == "hit":
                ev.hit_anim_timer -= dt
                if ev.hit_anim_timer <= 0.0:
                    ev.state = "done"

            elif ev.state == "missed":
                ev.y += ev.fall_speed * dt
                ev.miss_anim_timer -= dt
                if ev.miss_anim_timer <= 0.0 or ev.y > self.playable_clip_rect.bottom + self.tile_size:
                    ev.state = "done"

        # 4. Actualizar partículas de likes, corazones y celebración
        self._update_particles(dt)

    def _update_particles(self, dt: float) -> None:
        for p in self.like_particles[:]:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] -= 40.0 * dt  # Flotan suavemente hacia arriba como likes de live stream
            p["life"] -= dt
            if p["life"] <= 0.0:
                self.like_particles.remove(p)

        for hl in self.heart_loss_anims[:]:
            hl["y"] += hl["vy"] * dt
            hl["vy"] += 420.0 * dt
            hl["life"] -= dt
            if hl["life"] <= 0.0:
                self.heart_loss_anims.remove(hl)

        for fb in self.floating_feedbacks[:]:
            fb["y"] -= 55.0 * dt
            fb["life"] -= dt
            if fb["life"] <= 0.0:
                self.floating_feedbacks.remove(fb)

        for cp in self.celebration_particles[:]:
            cp["x"] += cp["vx"] * dt
            cp["y"] += cp["vy"] * dt
            cp["vy"] += 260.0 * dt
            cp["life"] -= dt
            if cp["life"] <= 0.0:
                self.celebration_particles.remove(cp)

    def handle_Event_key_up(self, key: int) -> None:
        self.held_keys.discard(key)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYUP:
            self.held_keys.discard(event.key)
            return
        if self.phase == self.PHASE_PLAY:
            self.handle_game_event(event)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        """
        Procesa pulsaciones individuales en los 4 carriles (D, F, J, K).
        Impide que mantener una tecla pulsada produzca aciertos o fallos repetidos.
        """
        if self.is_finished:
            return

        if event.type == pygame.KEYUP:
            self.held_keys.discard(event.key)
            return

        if event.type == pygame.KEYDOWN:
            # Ignorar auto-repeat del sistema operativo si la tecla ya está retenida
            if getattr(event, "repeat", 0) != 0 or event.key in self.held_keys:
                return
            self.held_keys.add(event.key)

            if event.key in self.LANE_KEYS:
                lane_idx = self.LANE_KEYS.index(event.key)
                self._process_lane_press(lane_idx)
        elif event.type == pygame.JOYBUTTONDOWN:
            lane_idx = self.GAMEPAD_BUTTONS.get(event.button)
            if lane_idx is not None:
                self._process_lane_press(lane_idx)

    def _process_lane_press(self, lane_idx: int) -> None:
        """
        Evalúa la pulsación del jugador en el carril `lane_idx` (0..3):
        - Si hay una nota dentro de la ventana de acierto (±80ms Perfecto, ±150ms Bien): Acierto.
        - Si pulsa un carril incorrecto o demasiado pronto/tarde: Fallo (-1 vida, con protección).
        """
        if self.is_finished:
            return

        self.lane_press_timers[lane_idx] = 0.14

        # Buscar la nota activa en este carril más cercana al momento actual
        lane_notes = [
            ev for ev in self.musical_events
            if ev.lane == lane_idx and ev.state == "falling"
        ]
        lane_notes.sort(key=lambda e: abs(e.impact_time - self.song_elapsed))

        if lane_notes:
            candidate = lane_notes[0]
            time_diff = abs(candidate.impact_time - self.song_elapsed)

            if time_diff <= self.perfect_window:
                self._register_note_hit(candidate, judgment="¡PERFECTO!")
                return
            elif time_diff <= self.good_window:
                self._register_note_hit(candidate, judgment="¡BIEN!")
                return

            # Si la nota ya está visible cerca de la parte media/baja del carril pero fuera de ventana
            # (pulsó demasiado pronto), la marcamos como fallada para que esa misma nota NO vuelva
            # a restar otra vida al cruzar la línea de impacto.
            if candidate.impact_time - self.song_elapsed < 0.42:
                self._mark_note_missed(candidate, reason="¡MUY PRONTO!")
                return

        # Si no había nota válida en ese carril (carril incorrecto o pulsación al vacío):
        self._apply_wrong_press_penalty(lane_idx, reason="¡CARRIL INCORRECTO!")

    def _register_note_hit(self, note: MusicalNoteEvent, judgment: str) -> None:
        """
        Ejecuta la secuencia de Acierto:
        1. La nota cambia brevemente a su versión iluminada (Fila 2 del spritesheet) con ligera expansión.
        2. Aparece animación de corazones y partículas de likes.
        3. Luego desaparece al concluir `hit_anim_timer`.
        4. Efecto visual satisfactorio y conservación de vidas.
        """
        note.state = "hit"
        note.judgment = judgment
        note.hit_anim_timer = 0.16  # Muestra el sprite iluminado brevemente antes de desaparecer
        note.y = float(self.hit_line_y)

        if "PERFECTO" in judgment:
            self.hits_perfect += 1
        else:
            self.hits_good += 1

        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        self.yellow_glow_alpha = 95.0

        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

        cx = float(self.lane_centers_x[note.lane])
        cy = float(self.hit_line_y)

        # Pequeña animación de corazones / partículas de likes
        self._spawn_like_and_heart_particles(cx, cy)

        col = (255, 235, 75) if "PERFECTO" in judgment else (120, 245, 165)
        self.floating_feedbacks.append({
            "text": judgment,
            "x": cx,
            "y": cy - 42.0,
            "color": col,
            "life": 0.50,
            "max_life": 0.50,
        })

    def _mark_note_missed(self, note: MusicalNoteEvent, reason: str = "¡FALLO!") -> None:
        """
        Marca una nota como fallida garantizando que una misma nota NUNCA produzca más de un fallo.
        """
        if note.penalized:
            return
        note.penalized = True
        note.state = "missed"
        note.judgment = "FALLO"
        note.miss_anim_timer = 0.18

        cx = float(self.lane_centers_x[note.lane])
        cy = float(min(self.hit_line_y, int(note.y)))
        self._deduct_single_life(feedback_text=reason, pos=(cx, cy))

    def _apply_wrong_press_penalty(self, lane_idx: int, reason: str) -> None:
        """
        Descuenta una vida por pulsar un carril incorrecto o fuera de tiempo,
        respetando el intervalo de protección para evitar penalizaciones múltiples injustas.
        """
        if self.wrong_press_cooldown > 0.0:
            return
        self.wrong_press_cooldown = self.wrong_press_protection_interval

        # Si hay una nota en OTRO carril exactamente dentro de la ventana de impacto en este instante,
        # la marcamos como penalizada para que el jugador no reciba doble castigo por equivocarse de tecla.
        for ev in self.musical_events:
            if ev.state == "falling" and not ev.penalized:
                if abs(ev.impact_time - self.song_elapsed) <= self.good_window:
                    ev.penalized = True
                    ev.state = "missed"
                    ev.miss_anim_timer = 0.15
                    break

        cx = float(self.lane_centers_x[lane_idx])
        cy = float(self.hit_line_y)
        self._deduct_single_life(feedback_text=reason, pos=(cx, cy))

    def _deduct_single_life(self, feedback_text: str, pos: Tuple[float, float]) -> None:
        """Descuenta exactamente 1 corazón, activa vibración visual, destello rojizo y verifica derrota."""
        if self.is_finished or self.lives <= 0:
            return

        lost_heart_idx = self.lives - 1
        self.lives -= 1
        self.misses_count += 1
        self.combo = 0

        self.publicoSeRie()

        # Efectos de fallo: pequeño destello rojizo, breve vibración visual y pérdida animada de corazón
        self.red_flash_alpha = 135.0
        self.trauma = min(1.0, self.trauma + 0.55)

        if hasattr(self.audio, "play_pigeon"):
            self.audio.play_pigeon()

        hx = 48 + lost_heart_idx * 68
        hy = 38
        self.heart_loss_anims.append({
            "x": float(hx),
            "y": float(hy),
            "vy": -110.0,
            "life": 0.55,
            "max_life": 0.55,
        })

        self.floating_feedbacks.append({
            "text": feedback_text,
            "x": pos[0],
            "y": pos[1] - 36.0,
            "color": (255, 95, 105),
            "life": 0.55,
            "max_life": 0.55,
        })

        if self.lives <= 0:
            self.finish_game(won=False)

    def _spawn_like_and_heart_particles(self, cx: float, cy: float) -> None:
        """Genera corazones pequeños y partículas de likes acogedoras alrededor de la zona de impacto."""
        palette = [
            (255, 105, 165),  # Rosa corazón
            (255, 225, 85),   # Brillo amarillo
            (185, 130, 255),  # Lila pastel
            (255, 155, 95),   # Coral cálido
        ]
        for i in range(9):
            angle = random.uniform(-math.pi * 0.90, -math.pi * 0.10)
            spd = random.uniform(75.0, 210.0)
            self.like_particles.append({
                "x": cx + random.uniform(-22.0, 22.0),
                "y": cy + random.uniform(-12.0, 12.0),
                "vx": math.cos(angle) * spd * 0.65,
                "vy": math.sin(angle) * spd,
                "color": palette[i % len(palette)],
                "is_heart": (i % 2 == 0),
                "size": random.uniform(5.0, 9.0),
                "life": random.uniform(0.32, 0.55),
                "max_life": 0.55,
            })

    def _spawn_victory_celebration(self) -> None:
        """Lanza lluvia festiva de corazones y destellos pastel al sobrevivir los 30s."""
        for _ in range(42):
            angle = random.uniform(0.0, math.pi * 2.0)
            spd = random.uniform(140.0, 420.0)
            self.celebration_particles.append({
                "x": float(self.screen_w // 2 + random.uniform(-160, 160)),
                "y": float(self.screen_h // 2 + random.uniform(-120, 80)),
                "vx": math.cos(angle) * spd,
                "vy": math.sin(angle) * spd - 120.0,
                "color": random.choice([(255, 225, 80), (255, 105, 175), (135, 235, 255), (145, 250, 170)]),
                "size": random.uniform(6.0, 11.0),
                "life": random.uniform(0.8, 1.5),
                "max_life": 1.5,
            })

    def render_game(self, surface: pygame.Surface) -> None:
        """
        Renderiza las 4 capas del microjuego en orden estricto:
        - Capa 1: Fondo de Buenavista con ligero oscurecimiento.
        - Capa 2: Celular centrado ocupando el 85% de la altura sin deformarse.
        - Capa 3: Teclas descendentes recortadas al área interior del celular + efectos suaves.
        - Capa 4: Interfaz exterior (3 corazones arriba a la izquierda, barra de progreso musical
          y tiempo restante dinámico arriba a la derecha).
        """
        # Vibración visual breve y sutil cuando ocurre un fallo (el fondo y el celular permanecen estables)
        shake_mag = (self.trauma ** 2) * self.max_shake_offset
        shake_x = int(random.uniform(-shake_mag, shake_mag)) if shake_mag > 0.2 else 0
        shake_y = int(random.uniform(-shake_mag, shake_mag)) if shake_mag > 0.2 else 0

        # ---------------------------------------------------------------------
        # CAPA 1 — Fondo de Buenavista
        # ---------------------------------------------------------------------
        surface.blit(self.bg_surface, (0, 0))

        # ---------------------------------------------------------------------
        # CAPA 2 — Celular PNG centrado (85% de la altura, proporción intacta)
        # ---------------------------------------------------------------------
        phone_draw_rect = self.phone_rect.move(shake_x, shake_y)
        surface.blit(self.phone_surface, phone_draw_rect)

        # Etiquetas discretas de controles [D] [F] [J] [K] en las 4 zonas de pulsación inferiores
        self._render_lane_key_indicators(surface, shake_x, shake_y)

        self.dibujarPantallaVivo(surface, shake_x, shake_y)

        # ---------------------------------------------------------------------
        # CAPA 3 — Teclas descendentes con clipping estricto al interior del celular
        # ---------------------------------------------------------------------
        prev_clip = surface.get_clip()
        clip_rect = self.playable_clip_rect.move(shake_x, shake_y)
        surface.set_clip(clip_rect)

        for ev in self.musical_events:
            if ev.state not in ("falling", "hit", "missed"):
                continue

            cx = self.lane_centers_x[ev.lane] + shake_x
            cy = int(round(ev.y)) + shake_y

            if ev.state == "falling":
                spr = self.normal_tile_sprites[ev.sprite_type]
                rect = spr.get_rect(center=(cx, cy))
                surface.blit(spr, rect)

            elif ev.state == "hit":
                # 1. Cambia a su versión iluminada (Fila 2) con ligera expansión
                active_spr = self.active_tile_sprites[ev.sprite_type]
                progress = 1.0 - max(0.0, ev.hit_anim_timer / 0.16)
                scale = 1.0 + math.sin(progress * math.pi) * 0.16
                tw = max(4, int(round(active_spr.get_width() * scale)))
                th = max(4, int(round(active_spr.get_height() * scale)))
                expanded = pygame.transform.smoothscale(active_spr, (tw, th))

                # Brillo amarillo suave detrás del sprite activado
                glow_r = int(max(tw, th) * 0.62)
                glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(
                    glow_surf,
                    (255, 240, 110, int(115 * (1.0 - progress))),
                    (glow_r, glow_r),
                    glow_r
                )
                surface.blit(glow_surf, (cx - glow_r, cy - glow_r))

                rect = expanded.get_rect(center=(cx, cy))
                surface.blit(expanded, rect)

            elif ev.state == "missed":
                # Se desvanece rápidamente con tinte rojizo suave al fallar
                spr = self.normal_tile_sprites[ev.sprite_type].copy()
                alpha = int(180 * max(0.0, ev.miss_anim_timer / 0.18))
                spr.set_alpha(alpha)
                rect = spr.get_rect(center=(cx, cy))
                surface.blit(spr, rect)

        # Restaurar clip de pantalla completa
        surface.set_clip(prev_clip)

        self.dibujarMarcoCelular(surface, shake_x, shake_y)

        # Partículas de likes y corazones pequeños (no ocultan los carriles)
        self._render_vfx_and_particles(surface, shake_x, shake_y)

        # ---------------------------------------------------------------------
        # CAPA 4 — Interfaz adicional fuera del celular (Corazones y Barra Musical)
        # ---------------------------------------------------------------------
        self._render_outer_hud(surface)

        self.dibujarPublico(surface)

    def _render_lane_key_indicators(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        """Muestra la referencia de teclas D, F, J, K en las zonas de pulsación inferiores."""
        for idx, label in enumerate(self.LANE_LABELS):
            cx = self.lane_centers_x[idx] + ox
            cy = self.hit_line_y + oy
            is_pressed = self.lane_press_timers[idx] > 0.0

            if is_pressed:
                # Pulso luminoso suave dentro de la cápsula de impacto al presionar la tecla
                pw = int(self.lane_rects[idx].width * 0.84)
                ph = max(24, self.hit_box_bottom_y - self.hit_box_top_y)
                press_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
                pygame.draw.rect(press_surf, (255, 235, 130, 75), (0, 0, pw, ph), border_radius=ph // 2)
                surface.blit(press_surf, press_surf.get_rect(center=(cx, cy)))

            col = (255, 245, 150) if is_pressed else (235, 210, 255)
            txt = self.font_keys.render(label, True, col)
            txt_bg = self.font_keys.render(label, True, (35, 15, 60))
            surface.blit(txt_bg, txt_bg.get_rect(center=(cx + 2, cy + 2)))
            surface.blit(txt, txt.get_rect(center=(cx, cy)))

    def _render_vfx_and_particles(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        """Dibuja corazones pequeños, likes flotantes y destellos sutiles de acierto/fallo."""
        # Destello perimetral suave en fallo o acierto sin tapar las notas
        if self.red_flash_alpha > 1.0:
            flash_s = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            pygame.draw.rect(
                flash_s,
                (255, 65, 85, int(min(110.0, self.red_flash_alpha))),
                (0, 0, self.screen_w, self.screen_h),
                width=18
            )
            surface.blit(flash_s, (0, 0))

        for p in self.like_particles:
            ratio = max(0.0, p["life"] / p["max_life"])
            px = int(p["x"]) + ox
            py = int(p["y"]) + oy
            if p["is_heart"]:
                hs = self.mini_heart_surf.copy()
                hs.set_alpha(int(235 * ratio))
                surface.blit(hs, hs.get_rect(center=(px, py)))
            else:
                r = max(2, int(p["size"] * ratio))
                ps = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(ps, (*p["color"], int(220 * ratio)), (r + 2, r + 2), r)
                surface.blit(ps, (px - r - 2, py - r - 2))

        for fb in self.floating_feedbacks:
            ratio = max(0.0, fb["life"] / fb["max_life"])
            txt = self.font_feedback.render(fb["text"], True, fb["color"])
            shd = self.font_feedback.render(fb["text"], True, (25, 12, 40))
            txt.set_alpha(int(255 * ratio))
            shd.set_alpha(int(255 * ratio))
            fx = int(fb["x"]) + ox
            fy = int(fb["y"]) + oy
            surface.blit(shd, shd.get_rect(center=(fx + 2, fy + 2)))
            surface.blit(txt, txt.get_rect(center=(fx, fy)))

        for cp in self.celebration_particles:
            ratio = max(0.0, cp["life"] / cp["max_life"])
            r = max(2, int(cp["size"] * ratio))
            cs = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(cs, (*cp["color"], int(245 * ratio)), (r + 2, r + 2), r)
            surface.blit(cs, (int(cp["x"]) - r, int(cp["y"]) - r))

    def _render_outer_hud(self, surface: pygame.Surface) -> None:
        """
        Capa 4 — Interfaz adicional fuera del celular:
        1. Tres corazones en la esquina superior izquierda (con pérdida animada al fallar).
        2. Reloj contador dinámico en la esquina superior derecha (sin el recuadro de progreso del trend).
        """
        # 1. Tres corazones en la esquina superior izquierda
        hearts_panel_w = 44 + (self.max_lives - 1) * 68 + 56
        hearts_panel_h = 80
        hearts_x = 34
        hearts_y = 26

        panel_surf = pygame.Surface((hearts_panel_w, hearts_panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (32, 18, 52, 210), (0, 0, hearts_panel_w, hearts_panel_h), border_radius=24)
        pygame.draw.rect(panel_surf, (235, 145, 210, 220), (0, 0, hearts_panel_w, hearts_panel_h), width=3, border_radius=24)
        if not self.dibujarPanelCorazones(surface, pygame.Rect(hearts_x, hearts_y, hearts_panel_w, hearts_panel_h)):
            surface.blit(panel_surf, (hearts_x, hearts_y))

        for i in range(self.max_lives):
            hx = hearts_x + 22 + i * 68
            hy = hearts_y + 12
            if i < self.lives:
                beat_pulse = 1.0 + math.sin(self.song_elapsed * 6.5 + i) * 0.04
                hw = int(self.heart_full_surf.get_width() * beat_pulse)
                hh = int(self.heart_full_surf.get_height() * beat_pulse)
                h_surf = pygame.transform.smoothscale(self.heart_full_surf, (hw, hh))
                surface.blit(h_surf, h_surf.get_rect(center=(hx + 28, hy + 28)))
            else:
                surface.blit(self.heart_empty_surf, (hx, hy))

        for hl in self.heart_loss_anims:
            ratio = max(0.0, hl["life"] / hl["max_life"])
            falling_h = self.heart_full_surf.copy()
            falling_h.set_alpha(int(240 * ratio))
            surface.blit(falling_h, (int(hl["x"]), int(hl["y"])))

        return

        # 2. Reloj contador dinámico en la esquina superior derecha
        counter_x = self.screen_w - 310
        counter_y = 20
        sec_left = max(0.0, self.time_left)
        time_display = f"0:{int(math.ceil(sec_left)):02d}"
        if self.spr_counter:
            surface.blit(self.spr_counter, (counter_x, counter_y))
            display_rect = pygame.Rect(counter_x + 77, counter_y + 18, 138, 70)
            col = (45, 45, 45) if sec_left > 5.0 else (225, 40, 40)
            txt_t = self.font_timer_num.render(time_display, True, col)
            surface.blit(txt_t, txt_t.get_rect(center=display_rect.center))
        else:
            col = (255, 235, 95) if sec_left > 5.0 else (255, 95, 95)
            txt_t = self.font_timer_num.render(time_display, True, col)
            surface.blit(txt_t, (self.screen_w - 160, 36))

    def _render_outro_banner(self, surface: pygame.Surface) -> None:
        """
        Muestra el resultado final y el mensaje educativo utilizando únicamente texto
        con shader de resplandor y contorno suave (sin recuadros contenedores).
        """
        super()._render_outro_banner(surface)

        if self.dibujarRevelacion(surface):
            return

        if not self.is_won:
            return

        if self.dibujarMensajeTendencias(surface):
            return

        edu_msg ="No necesitas seguir todas las tendencias para disfrutar de las redes sociales."
        pulse = math.sin(self.outro_timer * 6.0) * 0.5 + 0.5
        txt_edu = self.font_edu.render(edu_msg, True, (255, 248, 235))
        txt_glow = self.font_edu.render(edu_msg, True, (235, 130, 215))
        txt_outline = self.font_edu.render(edu_msg, True, (28, 14, 45))

        cx = self.screen_w // 2
        cy = self.screen_h // 2 + 88

        txt_glow.set_alpha(int(95 + 55 * pulse))
        for ox, oy in [(-5, 0), (5, 0), (0, -5), (0, 5), (-3, -3), (3, -3), (-3, 3), (3, 3)]:
            surface.blit(txt_glow, txt_glow.get_rect(center=(cx + ox, cy + oy)))

        for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2)]:
            surface.blit(txt_outline, txt_outline.get_rect(center=(cx + ox, cy + oy)))

        surface.blit(txt_edu, txt_edu.get_rect(center=(cx, cy)))

    def dibujarPanelCorazones(self, surface: pygame.Surface, caja: pygame.Rect) -> bool:
        if getattr(self, "panelCorazones", None) is None:
            try:
                panel = self.assets.cargarSinFondo(os.path.join("Piano", "panelCorazones.jpg"), 600)
                panel = pygame.transform.smoothscale_by(panel, 100 / float(panel.get_height()))
                self.panelCorazones = self.estirarCentro(panel, caja.width + 30)
            except Exception as e:
                print(f"[BuenavistaTrend] Aviso: no se pudo cargar el recuadro de los corazones: {e}")
                self.panelCorazones = False
        if not self.panelCorazones:
            return False
        surface.blit(self.panelCorazones, self.panelCorazones.get_rect(center=caja.center))
        return True

    def dibujarMensajeTendencias(self, surface: pygame.Surface) -> bool:
        if getattr(self, "letreroResultado", None) is None or not getattr(self, "finLetrero", None):
            return False
        if getattr(self, "bannerTendencias", None) is None:
            self.bannerTendencias = self.crearCartel(
                ["No necesitas seguir todas las tendencias", "para disfrutar de las redes sociales."])
        if not self.bannerTendencias:
            return False
        inicio = getattr(self, "inicioTendencias", self.finLetrero)
        if self.outro_timer < inicio:
            return True
        self.dibujarCartel(surface, self.bannerTendencias, inicio, self.outro_duration,
                           (self.screen_w // 2, self.screen_h // 2))
        return True

    def iniciarPublico(self) -> None:
        self.espectadores = 40.0
        self.temblorContador = 0.0
        self.vieronDeVerdad = random.randint(1, 3)
        self.comentarios = []
        self.comentariosEnFila = []
        self.esperaComentario = 2.0
        self.burlas = [
            "jajaja", "¿Qué fue eso?", "Se le fue el paso jaja", "Clip de eso",
            "Nooo jajaja", "Pena ajena", "Ese paso no era", "jajaja la cara",
        ]
        self.tibios = ["Ok", "Normal", "Meh", "Siguiente", "Ah, bueno", "Todos hacen ese trend"]
        self.fuenteComentario = self.assets.cargarFuenteCuento(38)
        self.fuenteEnVivo = self.assets.cargarFuenteCuento(40)
        self.fuenteRevelacion = self.assets.cargarFuenteCuento(64)
        self.fuenteSello = self.assets.cargarFuenteCuento(58)
        self.avatares = self.cargarAvatares()
        self.globosHechos = {}
        self.bannerPublico = None
        self.imagenRevelacion = None
        self.sonoApagon = False
        self.sonoSello = False

    def cargarAvatares(self) -> list:
        try:
            hoja = self.assets.cargarSinFondo(os.path.join("Piano", "avataresPublico.jpg"), 1200)
            globo = self.assets.cargarSinFondo(os.path.join("Piano", "globoComentario.jpg"), 900)
            self.globoComentario = pygame.transform.smoothscale_by(globo, 80 / float(globo.get_height()))
        except Exception as e:
            print(f"[BuenavistaTrend] Aviso: faltan las imágenes del chat en vivo: {e}")
            return []
        avatares = []
        anchoCelda = hoja.get_width() // 4
        altoCelda = hoja.get_height() // 2
        for fila in range(2):
            for columna in range(4):
                parte = hoja.subsurface((columna * anchoCelda, fila * altoCelda, anchoCelda, altoCelda))
                cajas = pygame.mask.from_surface(parte, 60).get_bounding_rects()
                if cajas:
                    parte = parte.subsurface(cajas[0].unionall(cajas[1:]))
                avatares.append(pygame.transform.smoothscale(parte, (84, 84)))
        return avatares

    def actualizarPublico(self, dt: float) -> None:
        self.espectadores += dt * 9.0
        self.temblorContador = max(0.0, self.temblorContador - dt)
        for comentario in self.comentarios:
            comentario["edad"] += dt
        if self.comentariosEnFila:
            self.comentariosEnFila[0][1] -= dt
            if self.comentariosEnFila[0][1] <= 0.0:
                self.agregarComentario(self.comentariosEnFila.pop(0)[0])
        self.esperaComentario -= dt
        if self.esperaComentario <= 0.0:
            self.esperaComentario = random.uniform(2.5, 4.0)
            self.agregarComentario(random.choice(self.tibios))

    def agregarComentario(self, texto: str) -> None:
        if not self.avatares:
            return
        self.comentarios.append({"texto": texto, "avatar": random.choice(self.avatares), "edad": 0.0})
        self.comentarios = self.comentarios[-5:]

    def publicoSeRie(self) -> None:
        if not hasattr(self, "espectadores"):
            return
        self.espectadores += random.randint(250, 600)
        self.temblorContador = 0.4
        for i in range(random.randint(2, 3)):
            self.comentariosEnFila.append([random.choice(self.burlas), 0.12 if i == 0 else 0.35])

    def globoConTexto(self, texto: str) -> pygame.Surface:
        if texto not in self.globosHechos:
            letras = self.fuenteComentario.render(texto, True, (80, 46, 92))
            ancho = letras.get_width() + 124
            globo = self.estirarCentro(self.globoComentario, max(ancho, self.globoComentario.get_height() * 2))
            globo.blit(letras, letras.get_rect(midleft=(80, globo.get_height() // 2)))
            self.globosHechos[texto] = globo
        return self.globosHechos[texto]

    def dibujarChat(self, surface: pygame.Surface) -> None:
        izquierda = 56
        abajo = 950
        for i, comentario in enumerate(reversed(self.comentarios)):
            y = abajo - i * 100
            entrada = min(1.0, comentario["edad"] / 0.25)
            x = izquierda - int((1.0 - entrada) * 60)
            globo = self.globoConTexto(comentario["texto"])
            alfa = int(255 * entrada * (1.0 if i < 4 else 0.55))
            globo.set_alpha(alfa)
            surface.blit(globo, globo.get_rect(midleft=(x + 34, y)))
            avatar = comentario["avatar"]
            avatar.set_alpha(alfa)
            surface.blit(avatar, avatar.get_rect(center=(x + 34, y)))
            avatar.set_alpha(255)

    def prepararPantallaVivo(self) -> bool:
        if getattr(self, "pantallaVivo", None) is not None:
            return bool(self.pantallaVivo)
        try:
            fondo = self.assets.load_surface(os.path.join("Piano", "pantallaVivo.jpg"), has_alpha=False)
        except Exception as e:
            print(f"[BuenavistaTrend] Aviso: falta la pantalla en vivo: {e}")
            self.pantallaVivo = False
            return False
        w, h = fondo.get_size()
        fondo = fondo.subsurface((int(w * 0.07), int(h * 0.055), int(w * 0.86), int(h * 0.89)))
        self.cajaPantalla = self.phone_rect.inflate(-36, -36)
        pantalla = pygame.transform.smoothscale(fondo, self.cajaPantalla.size).convert()
        alto = self.playable_clip_rect.top - self.cajaPantalla.top
        pantalla.fill((228, 212, 200), (0, 0, pantalla.get_width(), alto), special_flags=pygame.BLEND_RGB_MULT)
        linea = pygame.Surface((3, self.playable_clip_rect.height), pygame.SRCALPHA)
        linea.fill((255, 246, 230, 150))
        for i in range(3):
            x = (self.lane_rects[i].right + self.lane_rects[i + 1].left) // 2 - self.cajaPantalla.left
            pantalla.blit(linea, (x - 1, alto))
        pantalla = pantalla.convert_alpha()
        molde = pygame.Surface(pantalla.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(molde, (255, 255, 255, 255), molde.get_rect(), border_radius=70)
        pantalla.blit(molde, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.pantallaVivo = pantalla
        alto = max(24, self.hit_box_bottom_y - self.hit_box_top_y)
        ancho = int(self.lane_rects[0].width * 0.86)
        globo = pygame.transform.smoothscale_by(self.globoComentario, alto / float(self.globoComentario.get_height()))
        mitad = globo.subsurface((0, 0, ancho // 2, alto))
        capsula = pygame.Surface((ancho // 2 * 2, alto), pygame.SRCALPHA)
        capsula.blit(mitad, (0, 0))
        capsula.blit(pygame.transform.flip(mitad, True, False), (ancho // 2, 0))
        self.capsulaTecla = capsula
        self.capsulaPrendida = capsula.copy()
        self.capsulaPrendida.fill((40, 34, 0), special_flags=pygame.BLEND_RGB_ADD)
        self.fuenteTecla = self.assets.cargarFuenteCuento(54)
        return True

    def dibujarPantallaVivo(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        if not getattr(self, "avatares", None) or not self.prepararPantallaVivo():
            return
        surface.blit(self.pantallaVivo, self.cajaPantalla.move(ox, oy))

        for i, letra in enumerate(self.LANE_LABELS):
            centro = (self.lane_centers_x[i] + ox, self.hit_line_y + oy)
            prendida = self.lane_press_timers[i] > 0.0
            capsula = self.capsulaPrendida if prendida else self.capsulaTecla
            surface.blit(capsula, capsula.get_rect(center=centro))
            color = (190, 70, 40) if prendida else (92, 46, 118)
            texto = self.textoConBorde(self.fuenteTecla, letra, color, color, 2)
            surface.blit(texto, texto.get_rect(center=(centro[0], centro[1] - 2)))

        arriba = (self.cajaPantalla.top + self.playable_clip_rect.top) // 2 + oy + 6
        if self.cargarPastillasVivo():
            if getattr(self, "etiquetaPintada", None) is None:
                self.etiquetaPintada = self.armarEtiquetaEnVivo(58)
            etiqueta = self.etiquetaPintada.get_rect(midleft=(self.cajaPantalla.left + 62 + ox, arriba))
            surface.blit(self.etiquetaPintada, etiqueta)
            cifra = f"{int(self.espectadores):,}".replace(",", ".")
            temblor = int(math.sin(self.song_elapsed * 60.0) * 6 * (self.temblorContador / 0.4)) if self.temblorContador > 0 else 0
            color = (200, 50, 60) if self.temblorContador > 0.0 else (80, 46, 92)
            contador = self.armarContador(cifra, 58, color, self.fuenteEnVivo)
            surface.blit(contador, contador.get_rect(midleft=(etiqueta.right + 12 + temblor, arriba)))
            return
        if getattr(self, "etiquetaEnVivo", None) is None:
            self.etiquetaEnVivo = self.armarPastilla("En vivo", (80, 46, 92), self.fuenteEnVivo, 1.0)
        etiqueta = self.etiquetaEnVivo.get_rect(midleft=(self.cajaPantalla.left + 30 + ox, arriba))
        surface.blit(self.etiquetaEnVivo, etiqueta)
        cifra = f"{int(self.espectadores):,}".replace(",", ".")
        temblor = int(math.sin(self.song_elapsed * 60.0) * 6 * (self.temblorContador / 0.4)) if self.temblorContador > 0 else 0
        color = (200, 50, 60) if self.temblorContador > 0.0 else (80, 46, 92)
        viendo = self.armarPastilla(f"{cifra} viendo", color, self.fuenteEnVivo)
        surface.blit(viendo, viendo.get_rect(midleft=(etiqueta.right + 14 + temblor, arriba)))

    def dibujarMarcoCelular(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        if getattr(self, "marcoCelular", None) is None:
            try:
                marco = self.assets.cargarSinFondo(os.path.join("Piano", "marcoCelular.jpg"), 560, ((0.5, 0.5),))
                caja = self.phone_rect.inflate(6, 6)
                self.marcoCelular = self.armarMarco(marco, caja.width, caja.height, 1.0)
            except Exception as e:
                print(f"[BuenavistaTrend] Aviso: no se pudo cargar el marco del celular: {e}")
                self.marcoCelular = False
        if not self.marcoCelular:
            return
        surface.blit(self.marcoCelular, self.marcoCelular.get_rect(center=(self.phone_rect.centerx + ox + 4, self.phone_rect.centery + oy)))

    def armarMarco(self, imagen: pygame.Surface, ancho: int, alto: int, grosor: float) -> pygame.Surface:
        imagen = pygame.transform.smoothscale_by(imagen, grosor)
        w, h = imagen.get_size()
        c = int(w * 0.2)
        marco = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        marco.blit(imagen, (0, 0), (0, 0, c, c))
        marco.blit(imagen, (ancho - c, 0), (w - c, 0, c, c))
        marco.blit(imagen, (0, alto - c), (0, h - c, c, c))
        marco.blit(imagen, (ancho - c, alto - c), (w - c, h - c, c, c))
        arriba = imagen.subsurface((c, 0, w - c * 2, c))
        abajo = imagen.subsurface((c, h - c, w - c * 2, c))
        izquierda = imagen.subsurface((0, c, c, h - c * 2))
        derecha = imagen.subsurface((w - c, c, c, h - c * 2))
        marco.blit(pygame.transform.smoothscale(arriba, (ancho - c * 2, c)), (c, 0))
        marco.blit(pygame.transform.smoothscale(abajo, (ancho - c * 2, c)), (c, alto - c))
        marco.blit(pygame.transform.smoothscale(izquierda, (c, alto - c * 2)), (0, c))
        marco.blit(pygame.transform.smoothscale(derecha, (c, alto - c * 2)), (ancho - c, c))
        return marco

    def cargarPastillasVivo(self) -> bool:
        if getattr(self, "pastillasVivo", None) is not None:
            return self.pastillasVivo
        try:
            self.imagenEnVivo = self.assets.cargarSinFondo(os.path.join("Piano", "etiquetaEnVivo.jpg"), 600)
            self.imagenEspectadores = self.assets.cargarSinFondo(os.path.join("Piano", "pastillaEspectadores.jpg"), 700)
            self.imagenBotonRojo = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonRojo.jpg"), 600)
            self.pastillasVivo = True
        except Exception as e:
            print(f"[BuenavistaTrend] Aviso: faltan las pastillas de la transmisión: {e}")
            self.pastillasVivo = False
        return self.pastillasVivo

    def estirarConPunta(self, imagen: pygame.Surface, alto: int, ancho: int, puntaIzquierda: float) -> pygame.Surface:
        imagen = pygame.transform.smoothscale_by(imagen, alto / float(imagen.get_height()))
        w, h = imagen.get_size()
        izquierda = min(int(h * puntaIzquierda), w // 2)
        derecha = min(h, w // 2)
        ancho = max(ancho, izquierda + derecha + 2)
        resultado = pygame.Surface((ancho, h), pygame.SRCALPHA)
        resultado.blit(imagen, (0, 0), (0, 0, izquierda, h))
        centro = imagen.subsurface((izquierda, 0, w - izquierda - derecha, h))
        resultado.blit(pygame.transform.smoothscale(centro, (ancho - izquierda - derecha, h)), (izquierda, 0))
        resultado.blit(imagen, (ancho - derecha, 0), (w - derecha, 0, derecha, h))
        return resultado

    def armarEtiquetaEnVivo(self, alto: int) -> pygame.Surface:
        letras = self.textoConBorde(self.fuenteEnVivo, "En vivo", (255, 246, 236), (110, 24, 36), 2)
        inicio = int(alto * 0.95)
        etiqueta = self.estirarConPunta(self.imagenEnVivo, alto, inicio + letras.get_width() + int(alto * 0.55), 0.95)
        etiqueta.blit(letras, letras.get_rect(midleft=(inicio, alto // 2 - 2)))
        return etiqueta

    def armarContador(self, texto: str, alto: int, color, fuente, rojo: float = 0.0, ancho: int = 0) -> pygame.Surface:
        color = [int(a + (b - a) * rojo) for a, b in zip(color, (255, 246, 236))]
        if rojo > 0.0:
            letras = self.textoConBorde(fuente, texto, color, (110, 24, 36), max(1, int(3 * rojo)))
        else:
            letras = fuente.render(texto, True, color)
        inicio = int(alto * 1.3)
        pastilla = self.estirarConPunta(self.imagenEspectadores, alto, max(ancho, inicio + letras.get_width() + int(alto * 0.5)), 1.3)
        if rojo > 0.0:
            boton = self.estirarConPunta(self.imagenBotonRojo, pastilla.get_height(), pastilla.get_width(), 1.0)
            boton.set_alpha(int(255 * rojo))
            pastilla.blit(boton, (0, 0))
        if rojo >= 1.0:
            pastilla.blit(letras, letras.get_rect(center=(pastilla.get_width() // 2, alto // 2 - 2)))
        else:
            zona = pastilla.get_width() - inicio - int(alto * 0.35)
            pastilla.blit(letras, letras.get_rect(center=(inicio + zona // 2, alto // 2 - 2)))
        return pastilla

    def armarPastilla(self, texto: str, color, fuente=None, rojo: float = 0.0) -> pygame.Surface:
        fuente = fuente or self.fuenteEnVivo
        if rojo > 0.0:
            color = [int(a + (b - a) * rojo) for a, b in zip(color, (255, 246, 236))]
            letras = self.textoConBorde(fuente, texto, color, (110, 24, 36), max(1, int(3 * rojo)))
        else:
            letras = fuente.render(texto, True, color)
        pastilla = self.estirarCentro(self.globoComentario, letras.get_width() + 70)
        pastilla = pygame.transform.smoothscale_by(pastilla, letras.get_height() * 1.25 / pastilla.get_height())
        if rojo > 0.0:
            tinte = (255 - int(25 * rojo), 255 - int(155 * rojo), 255 - int(150 * rojo))
            pastilla.fill(tinte, special_flags=pygame.BLEND_RGB_MULT)
        pastilla.blit(letras, letras.get_rect(center=(pastilla.get_width() // 2, pastilla.get_height() // 2)))
        return self.ponerBorde(pastilla, (74, 34, 62), 4)

    def dibujarEnVivo(self, surface: pygame.Surface, texto: str, color, centro, fuente=None, rojo: float = 0.0) -> None:
        pastilla = self.armarPastilla(texto, color, fuente, rojo)
        surface.blit(pastilla, pastilla.get_rect(center=centro))

    def dibujarPublico(self, surface: pygame.Surface) -> None:
        if not hasattr(self, "espectadores") or self.is_finished or not self.avatares:
            return
        self.dibujarChat(surface)
        if getattr(self, "pantallaVivo", None):
            return
        cifra = f"{int(self.espectadores):,}".replace(",", ".")
        temblor = int(math.sin(self.song_elapsed * 60.0) * 6 * (self.temblorContador / 0.4)) if self.temblorContador > 0 else 0
        color = (200, 50, 60) if self.temblorContador > 0.0 else (80, 46, 92)
        centro = (self.phone_rect.centerx + 40 + temblor, self.phone_rect.top + int(self.phone_rect.height * 0.066))
        self.dibujarEnVivo(surface, f"En vivo · {cifra}", color, centro)

    def dibujarRevelacion(self, surface: pygame.Surface) -> bool:
        if not hasattr(self, "espectadores") or not getattr(self, "finLetrero", None) or not self.avatares:
            return False
        inicio = self.finLetrero
        fin = getattr(self, "inicioTendencias", inicio + 7.0)
        if self.outro_timer < inicio or self.outro_timer >= fin:
            return False
        t = self.outro_timer - inicio
        if self.imagenRevelacion is None:
            try:
                foto = self.assets.load_surface(os.path.join("Piano", "revelacionPublico.jpg"), has_alpha=False)
                self.imagenRevelacion = pygame.transform.smoothscale(foto, (2700, 1519))
            except Exception as e:
                print(f"[BuenavistaTrend] Aviso: falta la imagen de la revelación: {e}")
                self.imagenRevelacion = False

        if not self.sonoApagon:
            self.sonoApagon = True
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()
        if t < 0.3 and int(t * 20) % 2 == 0:
            return True
        surface.fill((8, 6, 12))

        pregunta = "¿Y toda esa gente que te estaba mirando?"
        if hasattr(self.audio, "sonarEscritura"):
            self.audio.sonarEscritura(0.4 <= t < 0.4 + len(pregunta) / 24.0)
        if t < 2.9:
            letras = min(len(pregunta), int(max(0.0, t - 0.4) * 24))
            if letras > 0:
                texto = self.textoConBorde(self.fuenteRevelacion, pregunta[:letras], (255, 247, 230), (60, 50, 70), 3)
                if t > 2.4:
                    texto.set_alpha(int(255 * (2.9 - t) / 0.5))
                surface.blit(texto, texto.get_rect(midleft=(self.screen_w // 2 - self.fuenteRevelacion.size(pregunta)[0] // 2, self.screen_h // 2)))
            return True

        if self.imagenRevelacion:
            avance = min(1.0, (t - 2.9) / 1.0)
            recorrido = min(1.0, (t - 2.9) / (fin - inicio - 2.9))
            recorrido = recorrido * recorrido * (3.0 - 2.0 * recorrido)
            sobra = self.imagenRevelacion.get_width() - self.screen_w
            surface.blit(self.imagenRevelacion, (-sobra + int(sobra * recorrido), -360))
            if avance < 1.0:
                radio = int(1150 * (1.0 - (1.0 - avance) ** 3))
                telon = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
                telon.fill((8, 6, 12, 255))
                pygame.draw.circle(telon, (0, 0, 0, 0), (self.screen_w // 2, self.screen_h // 2), radio)
                surface.blit(telon, (0, 0))

        if t >= 3.4:
            caida = min(1.0, (t - 3.4) / 1.3)
            cifra = int(self.espectadores + (self.vieronDeVerdad - self.espectadores) * (1.0 - (1.0 - caida) ** 3))
            if caida < 1.0 and self.cargarPastillasVivo():
                contador = self.armarContador(f"{cifra:,}".replace(",", "."), 96, (80, 46, 92), self.fuenteSello, caida, 520)
                surface.blit(contador, contador.get_rect(center=(self.screen_w // 2, 120)))
            elif caida < 1.0:
                texto = f"En vivo · {cifra:,}".replace(",", ".")
                self.dibujarEnVivo(surface, texto, (80, 46, 92), (self.screen_w // 2, 120), self.fuenteSello, caida)
            else:
                if not self.sonoSello:
                    self.sonoSello = True
                    if hasattr(self.audio, "play_drum"):
                        self.audio.play_drum()
                golpe = min(1.0, (t - 4.7) / 0.3)
                escala = 1.0 + 0.8 * (1.0 - golpe) ** 2
                temblor = int(math.sin(t * 70.0) * 10 * (1.0 - golpe))
                if getattr(self, "pastillaSello", None) is None and self.cargarPastillasVivo():
                    self.pastillaSello = self.armarContador(
                        f"Te prestaron atención: {self.vieronDeVerdad}", 96, (80, 46, 92), self.fuenteSello, 1.0)
                if getattr(self, "pastillaSello", None) is None:
                    self.pastillaSello = self.armarPastilla(
                        f"Te prestaron atención: {self.vieronDeVerdad}", (80, 46, 92), self.fuenteSello, 1.0)
                sello = pygame.transform.smoothscale_by(self.pastillaSello, escala)
                surface.blit(sello, sello.get_rect(center=(self.screen_w // 2 + temblor, 120)))

        if t >= 4.0:
            if self.bannerPublico is None:
                self.bannerPublico = self.crearCartel(
                    ["Muchos vieron tu video, pero de pasada,",
                     "mientras saltaban entre mil videos más.",
                     "Nadie le dio tantas vueltas a tu error como tú."])
            if self.bannerPublico:
                self.dibujarCartel(surface, self.bannerPublico, inicio + 4.0, fin, (self.screen_w // 2, self.screen_h - 200))
        if fin - self.outro_timer < 0.35:
            surface.fill([int(255 * (fin - self.outro_timer) / 0.35)] * 3, special_flags=pygame.BLEND_RGB_MULT)
        return True

    def get_result_data(self) -> Dict[str, Any]:
        """Retorna métricas completas de la partida para el sistema general."""
        return {
            "won": self.is_won,
            "lives_left": self.lives,
            "max_lives": self.max_lives,
            "hits_perfect": self.hits_perfect,
            "hits_good": self.hits_good,
            "misses": self.misses_count,
            "max_combo": self.max_combo,
            "time_survived": self.time_limit - max(0.0, self.time_left),
        }
