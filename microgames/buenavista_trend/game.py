import os
import math
import random
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Tuple, Dict, Any, Set
import pygame

from core.microgame import BaseMicrogame
from core.asset_manager import AssetManager, desenfoque_suave
from core.camera_gestures import CameraGestureInput
from microgames.buenavista_trend.beatmap import MusicalNoteEvent, EN_BARRANQUILLA_BEATMAP_DATA


class BuenavistaTrendMicrogame(BaseMicrogame):
    CAMERA_POINTER = False  # Usa la cámara directamente
    TIME_BAR_LAYOUT = (960, 1044, 724)  # Margen limpio bajo marcoCelular.bottom (1002) sin mover phone_rect
    # Carriles de izquierda a derecha con el mando: X, A, Y, B.
    GAMEPAD_BUTTON_KEYS = {2: pygame.K_d, 0: pygame.K_f, 3: pygame.K_j, 1: pygame.K_k}
    dialogoPaloma = [
        ["¡Llegamos a Buenavista! Todos graban",
         "el trend viral para ganar likes,",
         "pero tú bailas por gozártela, no por el algoritmo."],
        ["Sigue el ritmo con las teclas D, F, J y K",
         "(o los botones X, A, Y, B del mando).",
         "¡Cada 5 aciertos seguidos recuperas +1 corazón!"],
    ]
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
    # SDL expone A/B/X/Y como 0/1/2/3 en mandos XInput: X(2)->D(0), A(0)->F(1), Y(3)->J(2), B(1)->K(3).
    GAMEPAD_BUTTONS: Dict[int, int] = {2: 0, 0: 1, 3: 2, 1: 3}

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
        self.held_gamepad_buttons: Set[int] = set()
        self.lane_held_states: List[bool] = [False, False, False, False]
        self.wrong_press_cooldown: float = 0.0
        self.wrong_press_protection_interval: float = 0.22  # Intervalo de protección para pulsaciones erróneas
        self.camera_wrong_press_protection_interval: float = 0.42  # Cooldown ampliado en modo cámara
        self.invulnerability_timer: float = 0.0
        self.camera_invulnerability_duration: float = 0.35  # Ventana de gracia tras perder corazón con cámara

        # Estado de reproducción musical sincronizada
        self.music_started: bool = False
        self.song_elapsed: float = 0.0
        self._last_mixer_pos_sec: float = 0.0
        self.audio_offset_sec: float = 0.0
        self._music_track_path: Optional[str] = None
        self._music_preloaded: bool = False
        self._music_started_own_track: bool = False
        self.music_track_name: str = (
            "en_barranquilla_me_quedo_piano.ogg"
            if os.path.exists(os.path.join("assets", "en_barranquilla_me_quedo_piano.ogg"))
            else "imitadora_ost_piano_tiles_microjuego.ogg"
        )
        self.spritesheet_name: str = "spritesheet_teclas_costenas_piano.png"

        # Escala de diseño respecto al lienzo virtual 1920x1080
        self._ui_scale: float = min(self.screen_w / 1920.0, self.screen_h / 1080.0)
        s = self._ui_scale

        # Efectos visuales (Game Feel cozy)
        self.trauma: float = 0.0
        self.max_shake_offset: float = 16.0 * s
        self.red_flash_alpha: float = 0.0
        self.yellow_glow_alpha: float = 0.0
        self.last_hit_lane: int = 0
        self.lane_hit_flash: List[float] = [0.0, 0.0, 0.0, 0.0]
        self.combo_pop_timer: float = 0.0
        self.paloma_cheer_timer: float = 0.0
        self.blink_timer: float = 0.0
        self.heart_loss_anims: List[Dict[str, Any]] = []
        self.like_particles: List[Dict[str, Any]] = []
        self.floating_feedbacks: List[Dict[str, Any]] = []
        self.celebration_particles: List[Dict[str, Any]] = []
        self.lane_press_timers: List[float] = [0.0, 0.0, 0.0, 0.0]
        self._feedback_surf_cache: Dict[Tuple[str, Tuple[int, int, int]], pygame.Surface] = {}
        self._key_label_cache: Dict[Tuple[str, bool], pygame.Surface] = {}
        self._mando_label_cache: Dict[str, pygame.Surface] = {}
        self._contador_cache: Dict[Tuple[Any, ...], pygame.Surface] = {}
        self.camera_input = CameraGestureInput.get_instance()
        self.camera_input.start()

        # Tipografías
        self.font_keys = pygame.font.SysFont("Arial Black, Impact, sans-serif", max(14, int(round(26 * s))))
        self.font_hud = pygame.font.SysFont("Segoe UI, Arial, sans-serif", max(12, int(round(20 * s))), bold=True)
        self.font_timer_num = self.assets.cargarFuenteTitulo(max(16, int(round(28 * s))))
        self.font_feedback = self.assets.cargarFuenteTitulo(max(18, int(round(30 * s))))
        self.font_edu = pygame.font.SysFont("Arial, Helvetica, sans-serif", max(14, int(round(22 * s))), bold=True)
        self.fuenteMando = self.assets.get_font("Arial Black, Impact, sans-serif", max(13, int(round(22 * s))), bold=True)

        # 1. Cargar reloj contador oficial (contador_microjuegos.png) igual que en los demás minijuegos
        self.spr_counter: Optional[pygame.Surface] = None
        try:
            raw_cnt = self.assets.load_cropped_surface("contador_microjuegos.png", alpha_threshold=15)
            cnt_h = max(48, int(round(92 * s)))
            cnt_w = int(raw_cnt.get_width() * (cnt_h / float(max(1, raw_cnt.get_height()))))
            self.spr_counter = pygame.transform.smoothscale(raw_cnt, (cnt_w, cnt_h))
        except Exception:
            self.spr_counter = None

        # 2. Capa 1: Fondo de Buenavista con ligero oscurecimiento pastel
        self._load_background_layer()

        # 2. Capa 2: Celular PNG centrado ocupando ~85% de la altura disponible sin deformarse
        # y cálculo matemático proporcional de carriles y zona de impacto
        self._load_phone_and_compute_geometry()
        self.TIME_BAR_LAYOUT = (
            self.screen_w // 2,
            int(round(self.screen_h * 0.9667)),
            int(round(self.phone_rect.width * 1.012)),
        )

        # 3. Capa 3: Recorte matemático uniforme 4x2 del spritesheet de teclas musicales
        self._load_and_slice_spritesheet()

        # 4. Capa 4: Recursos de interfaz adicional (corazones, barra musical, reloj y tarjeta Paloma)
        self._build_hud_surfaces()

        # 5. Construir lista de eventos musicales independientes del renderizado
        self._build_musical_events()

        self.iniciarPublico()
        self._preload_music_track()

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
        play_bottom_y = rel_y(1062.0) # Encima de la barra frontal de teclas D/F/J/K y mando
        play_h = max(10, play_bottom_y - play_top_y)

        for x0_orig, x1_orig in lane_bounds_orig:
            lx0 = rel_x(x0_orig)
            lx1 = rel_x(x1_orig)
            l_rect = pygame.Rect(lx0, play_top_y, max(10, lx1 - lx0), play_h)
            self.lane_rects.append(l_rect)
            self.lane_centers_x.append(l_rect.centerx)

        # Rectángulo de recorte (clipping) estricto del área jugable interior:
        # Garantiza que las teclas NUNCA atraviesen los bordes del celular ni cubran la barra de teclas
        inner_left = self.lane_rects[0].left
        inner_right = self.lane_rects[-1].right
        self.playable_clip_rect = pygame.Rect(
            inner_left,
            play_top_y,
            inner_right - inner_left,
            play_h
        )

        # Línea de impacto elevada con anillos objetivo dedicados arriba de los badges de teclado/mando
        self.hit_line_y: int = rel_y(974.0)
        self.hit_box_top_y: int = rel_y(932.0)
        self.hit_box_bottom_y: int = rel_y(1016.0)

        # Punto de aparición en la parte superior del área jugable (entrando suavemente desde el borde del clip)
        min_lane_w = min(r.width for r in self.lane_rects)
        self.tile_size: int = int(round(min_lane_w * 0.78))  # Ligeramente menor que el ancho del carril
        self.spawn_y: float = float(play_top_y - self.tile_size * 0.45)
        self.fall_distance: float = float(self.hit_line_y) - self.spawn_y

        # Rectángulos de dock frontal para [D][F][J][K] y (X)(A)(Y)(B), estrictamente bajo hit_line_y + sprite/2
        s = getattr(self, "_ui_scale", min(self.screen_w / 1920.0, self.screen_h / 1080.0))
        pad = max(6, int(round(10 * s)))
        max_sprite_h = int(round(min_lane_w * 0.70)) + pad * 2
        dock_top = max(play_bottom_y - 1, self.hit_line_y + (max_sprite_h // 2) + max(2, int(round(4 * s))))
        dock_bottom = rel_y(1134.0)
        dock_h = max(int(round(36 * s)), dock_bottom - dock_top)
        self.key_badge_rects: List[pygame.Rect] = []
        for i, l_rect in enumerate(self.lane_rects):
            bw = int(l_rect.width * 0.86)
            badge_r = pygame.Rect(0, 0, bw, dock_h)
            badge_r.midtop = (self.lane_centers_x[i], dock_top)
            self.key_badge_rects.append(badge_r)

        # Superficies pre-alocadas para destello vertical de carril (yellow_glow_alpha, cero alocaciones por frame)
        self._lane_glow_surfs: List[pygame.Surface] = []
        for l_rect in self.lane_rects:
            gs = pygame.Surface((l_rect.width, play_h), pygame.SRCALPHA)
            band_step = max(4, play_h // 28)
            for y_pos in range(0, play_h, band_step):
                t_norm = y_pos / float(max(1, play_h - 1))
                # Más intenso cerca de la zona inferior de impacto, suave hacia arriba
                band_alpha = int(215 * (t_norm ** 1.65))
                if band_alpha > 0:
                    pygame.draw.rect(
                        gs,
                        (255, 228, 110, band_alpha),
                        (0, y_pos, l_rect.width, min(band_step, play_h - y_pos)),
                    )
            self._lane_glow_surfs.append(gs)

    def _load_and_slice_spritesheet(self) -> None:
        """
        Extrae los 8 sprites de `spritesheet_teclas_costenas_piano.png`
        mediante una cuadrícula matemática uniforme de 4 columnas × 2 filas (W/4 × H/2),
        calcula la caja envolvente unión por columna entre Fila 0 y Fila 1 (`alpha > 12`)
        y pre-hornea sombra acuarela (Fila 0), tinte de fallo y halo dorado (Fila 1).
        """
        sheet = None
        for candidate in (
            getattr(self, "spritesheet_name", "spritesheet_teclas_costenas_piano.png"),
            "spritesheet_teclas_piano_tiles_microjuego.png",
        ):
            try:
                sheet = self.assets.load_surface(candidate, has_alpha=True)
                self.spritesheet_name = candidate
                break
            except Exception:
                sheet = None
        if sheet is None:
            sheet = pygame.Surface((800, 400), pygame.SRCALPHA)
            sheet.fill((255, 105, 180, 220))

        sheet_w, sheet_h = sheet.get_size()
        cols = 4
        rows = 2

        self.normal_tile_sprites: List[pygame.Surface] = []
        self.active_tile_sprites: List[pygame.Surface] = []
        self.missed_tile_sprites: List[pygame.Surface] = []
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

        s = getattr(self, "_ui_scale", min(self.screen_w / 1920.0, self.screen_h / 1080.0))
        min_lane_w = min(r.width for r in self.lane_rects)
        pad = max(6, int(round(10 * s)))
        max_w = int(round(min_lane_w * 0.735))
        max_clip_h = max(24, (self.playable_clip_rect.bottom - self.hit_line_y - pad) * 2)
        max_h = min(int(round(min_lane_w * 0.70)), max_clip_h)

        for c in range(cols):
            cell0 = self.raw_grid_cells[0][c]
            cell1 = self.raw_grid_cells[1][c]
            bbox0 = cell0.get_bounding_rect(min_alpha=12)
            bbox1 = cell1.get_bounding_rect(min_alpha=12)
            if bbox0.width <= 0 or bbox0.height <= 0:
                bbox0 = cell0.get_rect()
            if bbox1.width <= 0 or bbox1.height <= 0:
                bbox1 = cell1.get_rect()
            union_rect = bbox0.union(bbox1)

            # Normalización por aspecto: elementos horizontales anchos (ej. sombrero vueltiao aspect > 1.3)
            # aprovechan hasta el 86% del ancho del carril para equiparar presencia visual con raspado/marimonda
            col_max_w = int(round(min_lane_w * 0.86)) if union_rect.width > union_rect.height * 1.3 else max_w
            col_max_h = max_h
            scale = min(
                col_max_w / float(max(1, union_rect.width)),
                col_max_h / float(max(1, union_rect.height)),
            )
            tw = max(8, int(round(union_rect.width * scale)))
            th = max(8, int(round(union_rect.height * scale)))
            cw = tw + pad * 2
            ch = th + pad * 2

            crop0 = cell0.subsurface(union_rect)
            crop1 = cell1.subsurface(union_rect)
            scaled_0 = pygame.transform.smoothscale(crop0, (tw, th))
            scaled_1 = pygame.transform.smoothscale(crop1, (tw, th))

            # Fila 0: sombra acuarela suave pre-horneada
            norm_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            try:
                shadow_sil = pygame.mask.from_surface(scaled_0, 32).to_surface(
                    setcolor=(58, 32, 26, 72),
                    unsetcolor=(0, 0, 0, 0),
                )
                shadow_soft = desenfoque_suave(shadow_sil)
                norm_surf.blit(shadow_soft, (pad, pad + 4))
            except Exception:
                pass
            norm_surf.blit(scaled_0, (pad, pad))
            self.normal_tile_sprites.append(norm_surf)

            # Tinte cálido pre-horneado para notas falladas (cero .copy() por frame)
            miss_surf = norm_surf.copy()
            miss_surf.fill((235, 130, 130, 210), special_flags=pygame.BLEND_RGBA_MULT)
            self.missed_tile_sprites.append(miss_surf)

            # Fila 1: halo radial dorado-ámbar pre-horneado
            act_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            outer_r = max(tw, th) // 2 + 9
            center_pt = (cw // 2, ch // 2)
            for frac, alpha_val in ((1.0, 18), (0.82, 30), (0.64, 44), (0.46, 58)):
                rad = max(4, int(round(outer_r * frac)))
                pygame.draw.circle(act_surf, (255, 220, 95, alpha_val), center_pt, rad)
            act_surf.blit(scaled_1, (pad, pad))
            self.active_tile_sprites.append(act_surf)

    def _build_hud_surfaces(self) -> None:
        """Prepara los corazones de vida (estilo acuarela cozy), cachés de pulso y tarjeta de ritmo."""
        s = getattr(self, "_ui_scale", min(self.screen_w / 1920.0, self.screen_h / 1080.0))
        heart_sz = max(32, int(round(56 * s)))
        mini_sz = max(14, int(round(24 * s)))
        self._hearts_x = max(16, int(round(34 * s)))
        self._hearts_y = max(12, int(round(26 * s)))
        self._heart_pad_x = max(12, int(round(22 * s)))
        self._heart_step = max(38, int(round(68 * s)))
        self._heart_sz = heart_sz

        self.heart_full_surf = self._create_heart_surface(filled=True, size=heart_sz)
        self.heart_empty_surf = self._create_heart_surface(filled=False, size=heart_sz)
        self.mini_heart_surf = self._create_heart_surface(filled=True, size=mini_sz)

        try:
            self.heart_full_surf = self.assets.cargarSinFondo(os.path.join("Piano", "corazonLleno.jpg"), heart_sz)
            self.heart_empty_surf = self.assets.cargarSinFondo(os.path.join("Piano", "corazonVacio.jpg"), heart_sz)
            self.mini_heart_surf = self.assets.cargarSinFondo(os.path.join("Piano", "corazonLleno.jpg"), mini_sz)
        except Exception as e:
            print(f"[BuenavistaTrend] Aviso: no se pudieron cargar los corazones pintados: {e}")

        # Pre-cachear 5 escalas discretas de latido de corazón (0.96..1.04) para evitar smoothscale por frame
        self._heart_pulse_cache: List[pygame.Surface] = []
        bw, bh = self.heart_full_surf.get_size()
        for scale in (0.96, 0.98, 1.00, 1.02, 1.04):
            self._heart_pulse_cache.append(
                pygame.transform.smoothscale(
                    self.heart_full_surf,
                    (max(8, int(round(bw * scale))), max(8, int(round(bh * scale)))),
                )
            )

        # Marco de destello perimetral pre-alocado para fallos
        self._red_flash_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        pygame.draw.rect(
            self._red_flash_surf,
            (255, 65, 85, 255),
            (0, 0, self.screen_w, self.screen_h),
            width=max(8, int(round(18 * s))),
        )

        # Tarjeta acuarela derecha: Canción / Combo / Precisión / Paloma compañera
        self._build_rhythm_card_assets()

    def _build_rhythm_card_assets(self) -> None:
        """Pre-hornea el marco acuarela de la tarjeta derecha y carga sprites de Paloma (cero PNGs nuevos)."""
        s = getattr(self, "_ui_scale", min(self.screen_w / 1920.0, self.screen_h / 1080.0))
        gap_x = max(16, int(round(48 * s)))
        margin_r = max(16, int(round(58 * s)))
        avail_w = max(220, self.screen_w - (self.phone_rect.right + gap_x) - margin_r)
        cw = min(int(round(496 * s)), avail_w)
        cs = cw / 496.0
        ch = int(round(485 * cs))
        card_x = min(self.screen_w - cw - 8, self.phone_rect.right + gap_x)
        card_y = min(
            int(round(self.screen_h * (210.0 / 1080.0))),
            max(8, self.screen_h - ch - 12),
        )
        self.rhythm_card_rect = pygame.Rect(card_x, card_y, cw, ch)
        self._card_scale = cs

        def sc(val: float) -> int:
            return int(round(val * cs))

        pad_x = max(4, sc(6))
        pad_top = max(3, sc(4))
        pad_shadow = max(6, sc(10))
        rad_outer = max(14, sc(28))
        rad_inner = max(11, sc(22))
        rad_pill = max(10, sc(18))

        card_surf = pygame.Surface((cw + pad_x * 2, ch + max(8, sc(14))), pygame.SRCALPHA)
        # Sombra cálida suave
        pygame.draw.rect(card_surf, (56, 30, 24, 58), (pad_x, pad_shadow, cw, ch), border_radius=rad_outer)
        # Cuerpo pergamino crema
        body_rect = pygame.Rect(pad_x, pad_top, cw, ch)
        pygame.draw.rect(card_surf, (255, 247, 232, 236), body_rect, border_radius=rad_outer)

        # Franja superior coral-dorado acuarela recortada al radio superior
        banner_h = max(48, sc(112))
        banner = pygame.Surface((cw, ch), pygame.SRCALPHA)
        pygame.draw.rect(banner, (248, 210, 150, 128), (0, 0, cw, banner_h))
        mask_s = pygame.Surface((cw, ch), pygame.SRCALPHA)
        pygame.draw.rect(mask_s, (255, 255, 255, 255), (0, 0, cw, ch), border_radius=rad_outer)
        banner.blit(mask_s, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        card_surf.blit(banner, (pad_x, pad_top))

        # Doble borde tinta acuarela
        pygame.draw.rect(card_surf, (112, 62, 46, 235), body_rect, width=max(2, sc(4)), border_radius=rad_outer)
        pygame.draw.rect(
            card_surf,
            (224, 164, 78, 225),
            body_rect.inflate(-max(6, sc(12)), -max(6, sc(12))),
            width=max(1, sc(2)),
            border_radius=rad_inner,
        )

        # Línea divisoria entre encabezado de canción y métricas
        div1_y = sc(118)
        div2_y = sc(294)
        line_x0 = pad_x + sc(24)
        line_x1 = pad_x + cw - sc(24)
        pygame.draw.line(card_surf, (190, 138, 96, 145), (line_x0, div1_y), (line_x1, div1_y), max(1, sc(2)))
        # Línea divisoria sutil sobre la franja de Paloma
        pygame.draw.line(card_surf, (190, 138, 96, 120), (line_x0, div2_y), (line_x1, div2_y), max(1, sc(2)))

        # Pastillas crema suaves para Combo y Precisión
        pill_l = pygame.Rect(pad_x + sc(22), sc(132), sc(212), sc(118))
        pill_r = pygame.Rect(pad_x + sc(262), sc(132), sc(212), sc(118))
        for pr in (pill_l, pill_r):
            pygame.draw.rect(card_surf, (255, 252, 244, 215), pr, border_radius=rad_pill)
            pygame.draw.rect(card_surf, (214, 168, 116, 190), pr, width=max(1, sc(2)), border_radius=rad_pill)

        # Tipografías de la tarjeta
        self.font_card_tag = self.assets.cargarFuenteCuento(max(13, sc(22)))
        self.font_card_title = self.assets.cargarFuenteTitulo(max(15, sc(26)))
        self.font_card_metric = self.assets.cargarFuenteTitulo(max(22, sc(42)))
        self.font_card_sub = self.assets.cargarFuenteCuento(max(13, sc(22)))
        self.font_card_paloma = self.assets.cargarFuenteCuento(max(13, sc(23)))

        tag_s = self.font_card_tag.render("SONANDO EN BUENAVISTA", True, (166, 72, 54))
        card_surf.blit(tag_s, tag_s.get_rect(midtop=(pad_x + cw // 2, sc(18))))

        song_s = self.font_card_title.render("En Barranquilla Me Quedo", True, (82, 42, 34))
        max_song_w = cw - sc(74)
        if song_s.get_width() > max_song_w:
            sr = max_song_w / float(max(1, song_s.get_width()))
            song_s = pygame.transform.smoothscale(song_s, (max_song_w, max(10, int(round(song_s.get_height() * sr)))))
        card_surf.blit(song_s, song_s.get_rect(midleft=(pad_x + sc(56), sc(78))))

        lbl_combo = self.font_card_tag.render("COMBO", True, (148, 86, 64))
        lbl_prec = self.font_card_tag.render("PRECISIÓN", True, (58, 112, 92))
        card_surf.blit(lbl_combo, lbl_combo.get_rect(midtop=(pill_l.centerx, pill_l.top + sc(12))))
        card_surf.blit(lbl_prec, lbl_prec.get_rect(midtop=(pill_r.centerx, pill_r.top + sc(12))))

        self._card_pad = (pad_x, pad_top)
        self.rhythm_card_bg: pygame.Surface = card_surf

        # Sprites de Paloma pre-escalados proporcionalmente (reutilizando assets existentes)
        self.paloma_card_sprites: Dict[str, pygame.Surface] = {}
        for key, fname in (
            ("idle", "paloma_dialog.png"),
            ("cheer", "paloma_dialog_habla_0.png"),
            ("blink", "paloma_dialog_pestaneo.png"),
        ):
            try:
                raw_p = self.assets.load_cropped_surface(fname, alpha_threshold=15)
                target_h = max(72, sc(148))
                target_w = max(16, int(round(raw_p.get_width() * (target_h / float(max(1, raw_p.get_height()))))))
                self.paloma_card_sprites[key] = pygame.transform.smoothscale(raw_p, (target_w, target_h))
            except Exception:
                pass

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
        for impact_t, lane_idx, spr_type, speed in EN_BARRANQUILLA_BEATMAP_DATA:
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

    def _resolve_music_track_path(self) -> Optional[str]:
        """Resuelve la ruta de la pista musical (.ogg prioritario, con fallback automático a .mp3)."""
        track_path = os.path.join("assets", self.music_track_name)
        if os.path.exists(track_path):
            return track_path
        if self.music_track_name.lower().endswith(".ogg"):
            mp3_candidate = os.path.splitext(track_path)[0] + ".mp3"
            if os.path.exists(mp3_candidate):
                return mp3_candidate
        return None

    def _preload_music_track(self) -> None:
        """Precarga la pista musical en `setup_game()` para evitar tirones de I/O al iniciar PLAY."""
        self._music_track_path = self._resolve_music_track_path()
        self._music_preloaded = False
        if pygame.mixer.get_init() and self._music_track_path:
            try:
                pygame.mixer.music.load(self._music_track_path)
                self._music_preloaded = True
            except Exception:
                self._music_preloaded = False

    def _start_music_if_needed(self) -> None:
        """Inicia la pista 'En Barranquilla Me Quedo' al comenzar la fase de juego (con fallback .mp3 o silencio seguro)."""
        if self.music_started:
            return
        self.music_started = True
        self.song_elapsed = 0.0
        self._last_mixer_pos_sec = 0.0
        self._music_started_own_track = False

        track_path = self._music_track_path if (self._music_preloaded and self._music_track_path and os.path.exists(self._music_track_path)) else self._resolve_music_track_path()
        if pygame.mixer.get_init() and track_path and os.path.exists(track_path):
            try:
                if not self._music_preloaded or track_path != self._music_track_path:
                    pygame.mixer.music.load(track_path)
                    self._music_track_path = track_path
                    self._music_preloaded = True
                self.audio._bgm_volume_scale = 1.0
                if hasattr(self.audio, "sync_music_volume"):
                    self.audio.sync_music_volume()
                else:
                    vol = getattr(self.audio, "music_volume", 0.75)
                    pygame.mixer.music.set_volume(vol if getattr(self.audio, "music_enabled", True) else 0.0)
                if getattr(self.audio, "music_enabled", True):
                    pygame.mixer.music.play(loops=0, start=0.0)
                self.audio.current_track = self.music_track_name
                self._music_started_own_track = True
                return
            except Exception:
                self._music_started_own_track = False

        # Sin pista propia disponible: detener cualquier BGM previa del menú/mapa para evitar desincronía
        if hasattr(self.audio, "stop_music"):
            try:
                self.audio.stop_music()
            except Exception:
                pass
        elif pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        if hasattr(self.audio, "current_track"):
            self.audio.current_track = None

    def _stop_or_fade_music(self) -> None:
        """Detiene o atenúa suavemente la música al finalizar el microjuego."""
        self._music_started_own_track = False
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
        if hasattr(self, "held_gamepad_buttons"):
            self.held_gamepad_buttons.clear()
        if hasattr(self, "lane_held_states"):
            self.lane_held_states = [False, False, False, False]

    def exit(self) -> None:
        self.cleanup()
        if hasattr(self.audio, "sonarEscritura"):
            self.audio.sonarEscritura(False)
        super().exit()
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
            if self.time_limit < 20.0:
                # Modo Arcade (rondas rápidas de 5.5–8.5s): mantener outro ágil sin revelación larga
                self.finLetrero = None
                self.outro_duration = 1.8
            else:
                self.finLetrero = 3.0
                self.inicioTendencias = 13.0
                self.outro_duration = max(self.outro_duration, 17.0 if won else 13.0)

    def _sync_audio_clock(self, dt: float) -> None:
        """
        Sincroniza el reloj musical (`self.song_elapsed`) con el tiempo real de reproducción
        de `pygame.mixer.music.get_pos()`, aplicando `self.audio_offset_sec` y manteniendo
        continuidad con `dt` cuando el mixer opera en modo headless o entre buffers.
        Solo lee `get_pos()` si se inició la pista propia de este minijuego.
        """
        self.song_elapsed += dt
        if (
            self._music_started_own_track
            and getattr(self.audio, "current_track", None) == self.music_track_name
            and pygame.mixer.get_init()
            and getattr(self.audio, "music_enabled", True)
        ):
            try:
                if pygame.mixer.music.get_busy():
                    pos_ms = pygame.mixer.music.get_pos()
                    if pos_ms >= 0:
                        mixer_sec = pos_ms / 1000.0
                        target_sec = mixer_sec + self.audio_offset_sec
                        # Si el reloj de hardware avanzó de forma continua respecto al último sample,
                        # anclar suavemente para evitar drift sin pisar saltos manuales en tests.
                        if mixer_sec > self._last_mixer_pos_sec:
                            self._last_mixer_pos_sec = mixer_sec
                            if abs(target_sec - self.song_elapsed) < 0.35:
                                self.song_elapsed = 0.7 * self.song_elapsed + 0.3 * target_sec
            except Exception:
                pass

    def update(self, dt: float) -> None:
        """Ciclo principal de estados (INTRO -> PLAY -> OUTRO) con victoria de supervivencia a los 30s."""
        if self.paloma_intro is not None and self.paloma_intro.active:
            super().update(dt)
            return
        if hasattr(self.audio, "update"):
            self.audio.update(dt)
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
            self._update_particles(dt)
            self.update_outro(dt)

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
        if self.invulnerability_timer > 0.0:
            self.invulnerability_timer = max(0.0, self.invulnerability_timer - dt)

        for i in range(4):
            if self.lane_press_timers[i] > 0.0:
                self.lane_press_timers[i] = max(0.0, self.lane_press_timers[i] - dt)
            if self.lane_hit_flash[i] > 0.0:
                self.lane_hit_flash[i] = max(0.0, self.lane_hit_flash[i] - dt)

        if self.combo_pop_timer > 0.0:
            self.combo_pop_timer = max(0.0, self.combo_pop_timer - dt)
        if self.paloma_cheer_timer > 0.0:
            self.paloma_cheer_timer = max(0.0, self.paloma_cheer_timer - dt)
        self.blink_timer = (self.blink_timer + dt) % 3.4

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

    def handles_raw_gamepad(self, event: pygame.event.Event) -> bool:
        """Evita doble despacho en Engine: los botones X/A/Y/B de carril se manejan directo."""
        return (
            event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP)
            and getattr(event, "button", None) in self.GAMEPAD_BUTTONS
        )

    def handle_Event_key_up(self, key: int) -> None:
        self.held_keys.discard(key)
        if key in self.LANE_KEYS:
            lane_idx = self.LANE_KEYS.index(key)
            self.lane_held_states[lane_idx] = any(
                btn for btn, l_idx in self.GAMEPAD_BUTTONS.items()
                if l_idx == lane_idx and btn in self.held_gamepad_buttons
            )

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYUP:
            self.handle_Event_key_up(event.key)
            return
        if event.type == pygame.JOYBUTTONUP:
            btn = getattr(event, "button", None)
            if btn in self.GAMEPAD_BUTTONS:
                self.held_gamepad_buttons.discard(btn)
                lane_idx = self.GAMEPAD_BUTTONS[btn]
                self.lane_held_states[lane_idx] = (self.LANE_KEYS[lane_idx] in self.held_keys)
                return
        if self.phase == self.PHASE_PLAY:
            self.handle_game_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                super().handle_event(event)
        else:
            super().handle_event(event)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        """
        Procesa pulsaciones individuales en los 4 carriles (D, F, J, K) y mando (X, A, Y, B).
        Impide que mantener una tecla o botón pulsado produzca aciertos o fallos repetidos.
        """
        if self.is_finished:
            return

        if event.type == pygame.KEYUP:
            self.handle_Event_key_up(event.key)
            return

        if event.type == pygame.JOYBUTTONUP:
            btn = getattr(event, "button", None)
            lane_idx = self.GAMEPAD_BUTTONS.get(btn)
            if lane_idx is not None:
                from core import input_state
                input_state.set_input_device("gamepad")
                self.held_gamepad_buttons.discard(btn)
                self.lane_held_states[lane_idx] = (self.LANE_KEYS[lane_idx] in self.held_keys)
            return

        if event.type == pygame.KEYDOWN:
            # Ignorar auto-repeat del sistema operativo si la tecla ya está retenida
            if getattr(event, "repeat", 0) != 0 or event.key in self.held_keys:
                return
            self.held_keys.add(event.key)

            if event.key in self.LANE_KEYS:
                lane_idx = self.LANE_KEYS.index(event.key)
                self.lane_held_states[lane_idx] = True
                self._process_lane_press(lane_idx)
        elif event.type == pygame.JOYBUTTONDOWN:
            btn = getattr(event, "button", None)
            lane_idx = self.GAMEPAD_BUTTONS.get(btn)
            if lane_idx is not None:
                from core import input_state
                input_state.set_input_device("gamepad")
                if btn in self.held_gamepad_buttons:
                    return
                self.held_gamepad_buttons.add(btn)
                self.lane_held_states[lane_idx] = True
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

        if self._is_camera_hand_active():
            recently_missed = any(
                ev.lane == lane_idx
                and ev.penalized
                and (
                    ev.state == "missed"
                    or (
                        ev.state == "done"
                        and 0.0 <= (self.song_elapsed - ev.impact_time) <= (self.good_window + 0.35)
                    )
                )
                for ev in self.musical_events
            )
            if recently_missed:
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
        if self.lives < self.max_lives and self.combo % 5 == 0:
            self.lives += 1
            judgment = "¡+1 CORAZÓN!"
        self.yellow_glow_alpha = 95.0
        self.last_hit_lane = note.lane
        self.lane_hit_flash[note.lane] = 0.22
        self.combo_pop_timer = 0.18
        self.paloma_cheer_timer = 0.65

        if hasattr(self.audio, "play_drum"):
            self.audio.play_drum()
        elif hasattr(self.audio, "play_hit"):
            self.audio.play_hit()

        cx = float(self.lane_centers_x[note.lane])
        cy = float(self.hit_line_y)

        # Pequeña animación de corazones / partículas de likes
        self._spawn_like_and_heart_particles(cx, cy)

        col = (255, 235, 75) if "PERFECTO" in judgment else (120, 245, 165)
        fb_surf = self._get_feedback_surface(judgment, col)
        half_w = fb_surf.get_width() // 2
        min_x = float(self.playable_clip_rect.left + half_w + 6)
        max_x = float(self.playable_clip_rect.right - half_w - 6)
        clamped_x = max(min_x, min(cx, max_x)) if min_x <= max_x else cx
        self.floating_feedbacks.append({
            "text": judgment,
            "x": clamped_x,
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

    def _is_camera_hand_active(self) -> bool:
        """Indica si el control por dedos con cámara MediaPipe está activo y detectando mano."""
        cam = getattr(self, "camera_input", None)
        return bool(cam is not None and getattr(cam, "enabled", False) and cam.is_hand_present())

    def _apply_wrong_press_penalty(self, lane_idx: int, reason: str) -> None:
        """
        Descuenta una vida por pulsar un carril incorrecto o fuera de tiempo,
        respetando el intervalo de protección para evitar penalizaciones múltiples injustas.
        """
        camera_active = self._is_camera_hand_active()
        if self.wrong_press_cooldown > 0.0:
            return
        if camera_active and self.invulnerability_timer > 0.0:
            return
        self.wrong_press_cooldown = (
            self.camera_wrong_press_protection_interval
            if camera_active
            else self.wrong_press_protection_interval
        )

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
        if self._is_camera_hand_active() and self.invulnerability_timer > 0.0:
            return

        lost_heart_idx = self.lives - 1
        self.lives -= 1
        if self._is_camera_hand_active():
            self.invulnerability_timer = self.camera_invulnerability_duration
        self.misses_count += 1
        self.combo = 0

        self.publicoSeRie()

        # Efectos de fallo: pequeño destello rojizo, breve vibración visual y pérdida animada de corazón
        self.red_flash_alpha = 135.0
        self.trauma = min(1.0, self.trauma + 0.55)

        if hasattr(self.audio, "play_miss"):
            self.audio.play_miss()
        elif hasattr(self.audio, "play_lose"):
            self.audio.play_lose()

        hearts_x = getattr(self, "_hearts_x", 34)
        hearts_y = getattr(self, "_hearts_y", 26)
        heart_pad_x = getattr(self, "_heart_pad_x", 22)
        heart_step = getattr(self, "_heart_step", 68)
        hx = hearts_x + heart_pad_x + lost_heart_idx * heart_step
        hy = hearts_y + max(6, int(round(12 * getattr(self, "_ui_scale", 1.0))))
        self.heart_loss_anims.append({
            "x": float(hx),
            "y": float(hy),
            "vy": -110.0,
            "life": 0.55,
            "max_life": 0.55,
        })

        fb_col = (255, 95, 105)
        fb_surf = self._get_feedback_surface(feedback_text, fb_col)
        half_w = fb_surf.get_width() // 2
        min_x = float(self.playable_clip_rect.left + half_w + 6)
        max_x = float(self.playable_clip_rect.right - half_w - 6)
        clamped_x = max(min_x, min(float(pos[0]), max_x)) if min_x <= max_x else float(pos[0])
        self.floating_feedbacks.append({
            "text": feedback_text,
            "x": clamped_x,
            "y": pos[1] - 36.0,
            "color": fb_col,
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
        - Capa 2: Pantalla acuarela en vivo + línea/anillos receptores (o celular fallback).
        - Capa 3: Teclas descendentes recortadas al área jugable + dock frontal D/F/J/K + marco celular.
        - Capa 4: Interfaz exterior (5 corazones arriba izquierda, reloj arriba derecha, tarjeta Paloma).
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
        # CAPA 2 — Pantalla interior acuarela y receptores (o fallback sin assets)
        # ---------------------------------------------------------------------
        has_watercolor_phone = bool(getattr(self, "avatares", None) and self.prepararPantallaVivo())
        if not has_watercolor_phone:
            phone_draw_rect = self.phone_rect.move(shake_x, shake_y)
            surface.blit(self.phone_surface, phone_draw_rect)
            self._render_fallback_receptors(surface, shake_x, shake_y)
        else:
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
                # 1. Squash & stretch con overshoot en 2 etapas guiado por dt + anillo expansivo dorado
                active_spr = self.active_tile_sprites[ev.sprite_type]
                p = 1.0 - max(0.0, ev.hit_anim_timer / 0.16)
                p = max(0.0, min(1.0, p))
                if p < 0.35:
                    u = p / 0.35
                    sx = 1.0 + 0.24 * math.sin(u * math.pi * 0.5)
                    sy = 1.0 - 0.22 * math.sin(u * math.pi * 0.5)
                else:
                    u = (p - 0.35) / 0.65
                    sx = 1.24 - 0.32 * u
                    sy = 0.78 + 0.34 * math.sin(u * math.pi * 0.65)

                tw = max(4, int(round(active_spr.get_width() * sx)))
                th = max(4, int(round(active_spr.get_height() * sy)))
                expanded = pygame.transform.smoothscale(active_spr, (tw, th))
                if p > 0.60:
                    fade = max(0.0, 1.0 - (p - 0.60) / 0.40)
                    expanded.set_alpha(int(255 * fade))

                # Anillo dorado expansivo directo en surface (cero alocación de Surface)
                ring_r = max(12, int(round(self.tile_size * (0.42 + 0.42 * p))))
                ring_col = (255, 224, 96) if p < 0.5 else (255, 240, 160)
                ring_w = max(1, int(round(4 * (1.0 - p * 0.65))))
                pygame.draw.circle(surface, ring_col, (cx, cy), ring_r, width=ring_w)

                rect = expanded.get_rect(center=(cx, cy))
                surface.blit(expanded, rect)

            elif ev.state == "missed":
                # Sprite pre-horneado con tinte cálido rojizo (cero .copy() por frame)
                spr = self.missed_tile_sprites[ev.sprite_type]
                alpha = int(180 * max(0.0, ev.miss_anim_timer / 0.18))
                spr.set_alpha(alpha)
                rect = spr.get_rect(center=(cx, cy))
                surface.blit(spr, rect)
                spr.set_alpha(255)

        # Restaurar clip de pantalla completa antes de dibujar dock frontal y marco
        surface.set_clip(prev_clip)

        # Capa 3B — Dock frontal [D][F][J][K] y (X)(A)(Y)(B) nunca tapado por las notas
        self._render_key_dock_badges(surface, shake_x, shake_y)

        self.dibujarMarcoCelular(surface, shake_x, shake_y)

        # Partículas de likes y corazones pequeños (no ocultan los carriles)
        self._render_vfx_and_particles(surface, shake_x, shake_y)

        # ---------------------------------------------------------------------
        # CAPA 4 — Interfaz adicional fuera del celular (Corazones, Reloj, Tarjeta Paloma)
        # ---------------------------------------------------------------------
        self._render_outer_hud(surface)

        self.dibujarPublico(surface)

    def _get_feedback_surface(self, text: str, color: Tuple[int, int, int]) -> pygame.Surface:
        """Cachea los textos de feedback con borde acuarela (textoConBorde) para cero renders por frame."""
        key = (text, color)
        if key not in self._feedback_surf_cache:
            self._feedback_surf_cache[key] = self.textoConBorde(
                self.font_feedback,
                text,
                color,
                (48, 22, 34),
                3,
            )
        return self._feedback_surf_cache[key]

    def _render_vfx_and_particles(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        """Dibuja corazones pequeños, likes flotantes y destellos sutiles de acierto/fallo."""
        # Destello perimetral suave en fallo sin tapar las notas (superficie pre-alocada)
        if self.red_flash_alpha > 1.0 and getattr(self, "_red_flash_surf", None) is not None:
            self._red_flash_surf.set_alpha(int(min(110.0, self.red_flash_alpha)))
            surface.blit(self._red_flash_surf, (0, 0))

        for p in self.like_particles:
            ratio = max(0.0, p["life"] / p["max_life"])
            px = int(p["x"]) + ox
            py = int(p["y"]) + oy
            if p["is_heart"]:
                self.mini_heart_surf.set_alpha(int(235 * ratio))
                surface.blit(self.mini_heart_surf, self.mini_heart_surf.get_rect(center=(px, py)))
                self.mini_heart_surf.set_alpha(255)
            else:
                r = max(2, int(p["size"] * ratio))
                pygame.draw.circle(surface, p["color"], (px, py), r)

        for fb in self.floating_feedbacks:
            ratio = max(0.0, fb["life"] / fb["max_life"])
            base_surf = self._get_feedback_surface(fb["text"], fb["color"])
            elapsed_frac = 1.0 - ratio
            if elapsed_frac < 0.25:
                pop_scale = 1.18 - 0.18 * (elapsed_frac / 0.25)
                sw = max(4, int(round(base_surf.get_width() * pop_scale)))
                sh = max(4, int(round(base_surf.get_height() * pop_scale)))
                draw_surf = pygame.transform.smoothscale(base_surf, (sw, sh))
            else:
                draw_surf = base_surf
            draw_surf.set_alpha(int(255 * min(1.0, ratio * 1.25)))
            half_w = draw_surf.get_width() // 2
            min_fx = self.playable_clip_rect.left + half_w + 6 + ox
            max_fx = self.playable_clip_rect.right - half_w - 6 + ox
            fx = int(fb["x"]) + ox
            if min_fx <= max_fx:
                fx = max(min_fx, min(fx, max_fx))
            fy = int(fb["y"]) + oy
            surface.blit(draw_surf, draw_surf.get_rect(center=(fx, fy)))
            draw_surf.set_alpha(255)

        for cp in self.celebration_particles:
            ratio = max(0.0, cp["life"] / cp["max_life"])
            r = max(2, int(cp["size"] * ratio))
            pygame.draw.circle(surface, cp["color"], (int(cp["x"]), int(cp["y"])), r)

    def _render_outer_hud(self, surface: pygame.Surface) -> None:
        """
        Capa 4 — Interfaz adicional fuera del celular:
        1. Cinco corazones en la esquina superior izquierda (con latido al ritmo 1.9 Hz y pérdida animada).
        2. Reloj contador dinámico oficial (`contador_microjuegos.png`) arriba a la derecha.
        3. Tarjeta acuarela derecha de Canción / Combo / Precisión / Paloma compañera.
        """
        s = getattr(self, "_ui_scale", min(self.screen_w / 1920.0, self.screen_h / 1080.0))
        hearts_x = getattr(self, "_hearts_x", max(16, int(round(34 * s))))
        hearts_y = getattr(self, "_hearts_y", max(12, int(round(26 * s))))
        heart_pad_x = getattr(self, "_heart_pad_x", max(12, int(round(22 * s))))
        heart_step = getattr(self, "_heart_step", max(38, int(round(68 * s))))
        heart_sz = getattr(self, "_heart_sz", max(32, int(round(56 * s))))

        # 1. Cinco corazones en la esquina superior izquierda
        hearts_panel_w = heart_pad_x * 2 + (self.max_lives - 1) * heart_step + heart_sz
        hearts_panel_h = max(46, int(round(80 * s)))

        if not self.dibujarPanelCorazones(surface, pygame.Rect(hearts_x, hearts_y, hearts_panel_w, hearts_panel_h)):
            panel_surf = pygame.Surface((hearts_panel_w, hearts_panel_h), pygame.SRCALPHA)
            rad = max(14, int(round(24 * s)))
            pygame.draw.rect(panel_surf, (32, 18, 52, 210), (0, 0, hearts_panel_w, hearts_panel_h), border_radius=rad)
            pygame.draw.rect(panel_surf, (235, 145, 210, 220), (0, 0, hearts_panel_w, hearts_panel_h), width=max(2, int(round(3 * s))), border_radius=rad)
            surface.blit(panel_surf, (hearts_x, hearts_y))

        omega_114 = 2.0 * math.pi * 1.9  # 114 BPM = 1.9 Hz
        cache = getattr(self, "_heart_pulse_cache", None)
        hy_off = max(6, int(round(12 * s)))
        for i in range(self.max_lives):
            hx = hearts_x + heart_pad_x + i * heart_step
            hy = hearts_y + hy_off
            if i < self.lives:
                pulse_norm = 0.5 + 0.5 * math.sin(self.song_elapsed * omega_114 + i * 0.6)
                if cache:
                    idx = min(len(cache) - 1, max(0, int(round(pulse_norm * (len(cache) - 1)))))
                    h_surf = cache[idx]
                else:
                    h_surf = self.heart_full_surf
                surface.blit(h_surf, h_surf.get_rect(center=(hx + heart_sz // 2, hy + heart_sz // 2)))
            else:
                surface.blit(self.heart_empty_surf, (hx, hy))

        for hl in self.heart_loss_anims:
            ratio = max(0.0, hl["life"] / hl["max_life"])
            self.heart_full_surf.set_alpha(int(240 * ratio))
            surface.blit(self.heart_full_surf, (int(hl["x"]), int(hl["y"])))
            self.heart_full_surf.set_alpha(255)

        # 3. Tarjeta acuarela derecha: Canción / Combo / Precisión / Paloma
        self._render_rhythm_card(surface)

    def _render_rhythm_card(self, surface: pygame.Surface) -> None:
        """Dibuja la tarjeta derecha estilo acuarela caribeña con estado rítmico y Paloma al compás."""
        if getattr(self, "rhythm_card_bg", None) is None:
            return
        card_r = self.rhythm_card_rect
        cs = getattr(self, "_card_scale", 1.0)
        pad_x, pad_top = getattr(self, "_card_pad", (6, 4))

        def sc(val: float) -> int:
            return int(round(val * cs))

        surface.blit(self.rhythm_card_bg, (card_r.x - pad_x, card_r.y - pad_top))

        omega_114 = 2.0 * math.pi * 1.9
        beat_pulse = 0.5 + 0.5 * math.sin(self.song_elapsed * omega_114)

        # Punto musical dorado pulsante junto al título "En Barranquilla Me Quedo"
        dot_cx = card_r.x + sc(36)
        dot_cy = card_r.y + sc(74)
        dot_r = max(4, int(round((7 + 3 * beat_pulse) * cs)))
        pygame.draw.circle(surface, (230, 126, 48), (dot_cx, dot_cy), dot_r + max(2, sc(3)))
        pygame.draw.circle(surface, (255, 224, 102), (dot_cx, dot_cy), dot_r)

        # COMBO con pop de overshoot
        combo_cx = card_r.x + sc(128)
        combo_cy = card_r.y + sc(194)
        combo_col = (212, 84, 52) if self.combo >= 5 else (92, 46, 118)
        combo_txt = self.font_card_metric.render(f"x{self.combo}", True, combo_col)
        if self.combo_pop_timer > 0.0:
            p = 1.0 - self.combo_pop_timer / 0.18
            pop_s = 1.0 + 0.22 * math.sin(p * math.pi)
            cw = max(8, int(round(combo_txt.get_width() * pop_s)))
            ch = max(8, int(round(combo_txt.get_height() * pop_s)))
            combo_txt = pygame.transform.smoothscale(combo_txt, (cw, ch))
        surface.blit(combo_txt, combo_txt.get_rect(center=(combo_cx, combo_cy)))

        # PRECISIÓN
        total_judged = self.hits_perfect + self.hits_good + self.misses_count
        acc = 100 if total_judged == 0 else int(round(100.0 * (self.hits_perfect + 0.65 * self.hits_good) / total_judged))
        prec_cx = card_r.x + sc(368)
        prec_cy = card_r.y + sc(194)
        prec_txt = self.font_card_metric.render(f"{acc}%", True, (42, 132, 98))
        surface.blit(prec_txt, prec_txt.get_rect(center=(prec_cx, prec_cy)))

        # Sub-línea de desglose Perfecto / Bien (limpiamente debajo de las pastillas y sobre el divisor)
        sub_txt = self.font_card_sub.render(f"Perfecto: {self.hits_perfect}   ·   Bien: {self.hits_good}", True, (108, 68, 58))
        surface.blit(sub_txt, sub_txt.get_rect(midtop=(card_r.centerx, card_r.y + sc(254))))

        # Franja inferior de Paloma con baile suave a 1.9 Hz y globo contextual
        bob_y = int(round(math.sin(self.song_elapsed * omega_114) * 4.5 * cs))
        paloma_key = "idle"
        if self.paloma_cheer_timer > 0.0 or self.combo >= 3:
            paloma_key = "cheer"
        elif 3.22 <= self.blink_timer < 3.36:
            paloma_key = "blink"
        pal_spr = self.paloma_card_sprites.get(paloma_key) or self.paloma_card_sprites.get("idle")
        if pal_spr is not None:
            pal_rect = pal_spr.get_rect(midbottom=(card_r.x + sc(104), card_r.bottom - sc(14) + bob_y))
            surface.blit(pal_spr, pal_rect)

        if self.combo >= 8:
            pal_msg = "¡Cipote sabor, sigue así!"
        elif self.combo >= 3:
            pal_msg = "¡Al compás de Curramba!"
        elif self.misses_count > 0 and self.combo == 0:
            pal_msg = "¡Tranqui, coge el paso!"
        else:
            pal_msg = "¡D F J K al ritmo!"

        bubble_rect = pygame.Rect(card_r.x + sc(186), card_r.y + sc(332), sc(282), sc(86))
        rad_b = max(10, sc(18))
        pygame.draw.rect(surface, (255, 253, 248, 240), bubble_rect, border_radius=rad_b)
        pygame.draw.rect(surface, (182, 120, 86, 210), bubble_rect, width=max(1, sc(2)), border_radius=rad_b)
        msg_s = self.font_card_paloma.render(pal_msg, True, (84, 46, 36))
        max_msg_w = max(40, bubble_rect.width - sc(20))
        if msg_s.get_width() > max_msg_w:
            ratio_s = max_msg_w / float(msg_s.get_width())
            msg_s = pygame.transform.smoothscale(msg_s, (max_msg_w, max(10, int(round(msg_s.get_height() * ratio_s)))))
        surface.blit(msg_s, msg_s.get_rect(center=bubble_rect.center))

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
                s = getattr(self, "_ui_scale", min(self.screen_w / 1920.0, self.screen_h / 1080.0))
                panel = self.assets.cargarSinFondo(os.path.join("Piano", "panelCorazones.jpg"), 600)
                target_h = max(56, int(round(100 * s)))
                panel = pygame.transform.smoothscale_by(panel, target_h / float(panel.get_height()))
                self.panelCorazones = self.estirarCentro(panel, caja.width + max(16, int(round(30 * s))))
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
        self.esperaComentario = 0.8
        self.hype_costeno = [
            "¡Cipote flow!",
            "¡Pura salsa!",
            "¡Así es en Curramba!",
            "¡Qué sabrosura!",
            "¡Con raspado y todo!",
            "¡En Barranquilla me quedo!",
        ]
        self.burlas = [
            "¡Se cayó el raspado!",
            "¡Epa, el compás!",
            "¡Cuidado el tambor!",
            "¡Jajaja ese paso!",
            "¡Agua, se enredó!",
            "¡Casi casi!",
        ]
        self.tibios = [
            "¿En Buenavista?",
            "¡Pónganle salsa!",
            "Ahí coge ritmo",
            "¡Dale con sabor!",
            "¡Sube el volumen!",
            "¡Qué buen parche!",
        ]
        s = getattr(self, "_ui_scale", min(self.screen_w / 1920.0, self.screen_h / 1080.0))
        self.fuenteComentario = self.assets.cargarFuenteCuento(max(16, int(round(30 * s))))
        self.fuenteEnVivo = self.assets.cargarFuenteCuento(max(22, int(round(40 * s))))
        self.fuenteRevelacion = self.assets.cargarFuenteCuento(max(36, int(round(64 * s))))
        self.fuenteSello = self.assets.cargarFuenteCuento(max(32, int(round(58 * s))))
        self.avatares = self.cargarAvatares()
        self.globosHechos = {}
        self.bannerPublico = None
        self.imagenRevelacion = None
        self.sonoApagon = False
        self.sonoSello = False

    def cargarAvatares(self) -> list:
        s = getattr(self, "_ui_scale", min(self.screen_w / 1920.0, self.screen_h / 1080.0))
        try:
            hoja = self.assets.cargarSinFondo(os.path.join("Piano", "avataresPublico.jpg"), 1200)
            globo = self.assets.cargarSinFondo(os.path.join("Piano", "globoComentario.jpg"), 900)
            globo_h = max(44, int(round(80 * s)))
            self.globoComentario = pygame.transform.smoothscale_by(globo, globo_h / float(globo.get_height()))
        except Exception as e:
            print(f"[BuenavistaTrend] Aviso: faltan las imágenes del chat en vivo: {e}")
            return []
        avatares = []
        av_sz = max(44, int(round(84 * s)))
        anchoCelda = hoja.get_width() // 4
        altoCelda = hoja.get_height() // 2
        for fila in range(2):
            for columna in range(4):
                parte = hoja.subsurface((columna * anchoCelda, fila * altoCelda, anchoCelda, altoCelda))
                cajas = pygame.mask.from_surface(parte, 60).get_bounding_rects()
                if cajas:
                    parte = parte.subsurface(cajas[0].unionall(cajas[1:]))
                avatares.append(pygame.transform.smoothscale(parte, (av_sz, av_sz)))
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
            self.esperaComentario = random.uniform(2.2, 3.6)
            pool = self.hype_costeno if getattr(self, "combo", 0) >= 3 else self.tibios
            self.agregarComentario(random.choice(pool))

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
            max_bubble_w = max(200, self.phone_rect.left - 108)
            if letras.get_width() + 116 > max_bubble_w:
                target_tw = max(40, max_bubble_w - 116)
                scale_r = target_tw / float(max(1, letras.get_width()))
                letras = pygame.transform.smoothscale(
                    letras,
                    (target_tw, max(12, int(round(letras.get_height() * scale_r)))),
                )
            ancho = min(max_bubble_w, max(letras.get_width() + 116, self.globoComentario.get_height() * 2))
            globo = self.estirarCentro(self.globoComentario, ancho)
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
        fondo = fondo.subsurface((int(w * 0.095), int(h * 0.085), int(w * 0.81), int(h * 0.83)))
        self.cajaPantalla = self.phone_rect.inflate(-32, -32)
        pantalla = pygame.transform.smoothscale(fondo, self.cajaPantalla.size).convert()
        alto_hdr = self.playable_clip_rect.top - self.cajaPantalla.top
        pantalla.fill((228, 212, 200), (0, 0, pantalla.get_width(), alto_hdr), special_flags=pygame.BLEND_RGB_MULT)

        # Tinte sutil alternado en carriles 1 y 3 para lectura instantánea
        lane_wash = pygame.Surface((1, 1), pygame.SRCALPHA)
        for idx in (1, 3):
            lr = self.lane_rects[idx].move(-self.cajaPantalla.left, -self.cajaPantalla.top)
            wash = pygame.Surface(lr.size, pygame.SRCALPHA)
            wash.fill((140, 88, 66, 14))
            pantalla.blit(wash, lr.topleft)

        # Divisores acuarela nítidos (tinta sepia 2px + brillo pergamino 1px)
        linea_tinta = pygame.Surface((2, self.playable_clip_rect.height), pygame.SRCALPHA)
        linea_tinta.fill((118, 72, 56, 115))
        linea_luz = pygame.Surface((1, self.playable_clip_rect.height), pygame.SRCALPHA)
        linea_luz.fill((255, 248, 235, 110))
        for i in range(3):
            x = (self.lane_rects[i].right + self.lane_rects[i + 1].left) // 2 - self.cajaPantalla.left
            pantalla.blit(linea_tinta, (x - 1, alto_hdr))
            pantalla.blit(linea_luz, (x + 1, alto_hdr))

        pantalla = pantalla.convert_alpha()
        molde = pygame.Surface(pantalla.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(molde, (255, 255, 255, 255), molde.get_rect(), border_radius=58)
        pantalla.blit(molde, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.pantallaVivo = pantalla

        # Pre-hornear anillos objetivo de impacto (normal y encendido) para evitar alocaciones por frame
        min_lane_w = min(r.width for r in self.lane_rects)
        rw = int(round(min_lane_w * 0.74))
        rh = int(round(min_lane_w * 0.56))
        self._receptor_ring_idle = pygame.Surface((rw, rh), pygame.SRCALPHA)
        pygame.draw.rect(self._receptor_ring_idle, (255, 246, 228, 92), (0, 0, rw, rh), border_radius=26)
        pygame.draw.rect(self._receptor_ring_idle, (128, 74, 52, 190), (0, 0, rw, rh), width=3, border_radius=26)
        pygame.draw.rect(self._receptor_ring_idle, (255, 252, 242, 130), (4, 4, rw - 8, rh - 8), width=1, border_radius=22)

        self._receptor_ring_active = pygame.Surface((rw, rh), pygame.SRCALPHA)
        pygame.draw.rect(self._receptor_ring_active, (255, 232, 130, 165), (0, 0, rw, rh), border_radius=26)
        pygame.draw.rect(self._receptor_ring_active, (196, 98, 42, 230), (0, 0, rw, rh), width=3, border_radius=26)
        pygame.draw.rect(self._receptor_ring_active, (255, 250, 220, 195), (4, 4, rw - 8, rh - 8), width=2, border_radius=22)

        # Pre-hornear franja translúcida de dock frontal inferior para teclas y mando
        dock_top = self.key_badge_rects[0].top - 6
        dock_h = max(48, (self.cajaPantalla.bottom - 4) - dock_top)
        self._dock_strip_surf = pygame.Surface((self.playable_clip_rect.width, dock_h), pygame.SRCALPHA)
        pygame.draw.rect(
            self._dock_strip_surf,
            (252, 240, 222, 195),
            (0, 0, self.playable_clip_rect.width, dock_h),
            border_radius=18,
        )
        pygame.draw.line(
            self._dock_strip_surf,
            (132, 82, 60, 150),
            (8, 1),
            (self.playable_clip_rect.width - 8, 1),
            2,
        )

        # Cápsulas compactas de tecla (altura 40 px dentro del dock frontal)
        alto_cap = 40
        ancho_cap = int(self.lane_rects[0].width * 0.80)
        globo = pygame.transform.smoothscale_by(self.globoComentario, alto_cap / float(self.globoComentario.get_height()))
        half_w = min(globo.get_width(), ancho_cap // 2)
        mitad = globo.subsurface((0, 0, half_w, alto_cap))
        capsula = pygame.Surface((half_w * 2, alto_cap), pygame.SRCALPHA)
        capsula.blit(mitad, (0, 0))
        capsula.blit(pygame.transform.flip(mitad, True, False), (half_w, 0))
        self.capsulaTecla = capsula
        self.capsulaPrendida = capsula.copy()
        self.capsulaPrendida.fill((48, 38, 0), special_flags=pygame.BLEND_RGB_ADD)
        self.fuenteTecla = self.assets.cargarFuenteCuento(36)
        return True

    def _render_fallback_receptors(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        """Dibuja divisores de carril y línea de impacto cuando falta pantallaVivo.jpg."""
        clip_r = self.playable_clip_rect.move(ox, oy)
        hy = self.hit_line_y + oy
        pygame.draw.line(surface, (118, 66, 48), (clip_r.left, hy), (clip_r.right, hy), 3)
        for i in range(4):
            cx = self.lane_centers_x[i] + ox
            pygame.draw.circle(surface, (255, 232, 130) if self.lane_press_timers[i] > 0.0 else (235, 210, 255), (cx, hy), 36, width=3)

    def dibujarPantallaVivo(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        if not getattr(self, "avatares", None) or not self.prepararPantallaVivo():
            return
        surface.blit(self.pantallaVivo, self.cajaPantalla.move(ox, oy))

        omega_114 = 2.0 * math.pi * 1.9
        beat_phase = 0.5 + 0.5 * math.sin(self.song_elapsed * omega_114)

        # Destello vertical de carril al acertar (yellow_glow_alpha) bajo las notas
        if self.yellow_glow_alpha > 1.0 and 0 <= self.last_hit_lane < len(self._lane_glow_surfs):
            glow_s = self._lane_glow_surfs[self.last_hit_lane]
            glow_s.set_alpha(int(min(255.0, self.yellow_glow_alpha * 1.35)))
            surface.blit(glow_s, self.lane_rects[self.last_hit_lane].move(ox, oy))

        # Línea horizontal de impacto acuarela
        clip_r = self.playable_clip_rect.move(ox, oy)
        hy = self.hit_line_y + oy
        pygame.draw.line(surface, (118, 66, 48), (clip_r.left + 4, hy), (clip_r.right - 4, hy), 3)
        pygame.draw.line(surface, (255, 248, 232), (clip_r.left + 4, hy), (clip_r.right - 4, hy), 1)

        # Anillos objetivo de impacto (debajo de CAPA 3) con squash & stretch por dt y pulso 1.9 Hz
        for i in range(4):
            centro = (self.lane_centers_x[i] + ox, hy)
            t_rem = self.lane_press_timers[i]
            hit_rem = self.lane_hit_flash[i]
            is_active = t_rem > 0.0 or hit_rem > 0.0
            base_ring = self._receptor_ring_active if is_active else self._receptor_ring_idle

            if t_rem > 0.0:
                p = 1.0 - max(0.0, min(1.0, t_rem / 0.14))
                sx = 1.0 + 0.18 * math.sin(p * math.pi) - 0.06 * math.sin(p * math.pi * 2.0)
                sy = 1.0 - 0.16 * math.sin(p * math.pi) + 0.06 * math.sin(p * math.pi * 2.0)
                rw = max(12, int(round(base_ring.get_width() * sx)))
                rh = max(12, int(round(base_ring.get_height() * sy)))
                ring_draw = pygame.transform.smoothscale(base_ring, (rw, rh))
            else:
                pulse_s = 1.0 + 0.02 * beat_phase
                if abs(pulse_s - 1.0) > 0.012:
                    rw = int(round(base_ring.get_width() * pulse_s))
                    rh = int(round(base_ring.get_height() * pulse_s))
                    ring_draw = pygame.transform.smoothscale(base_ring, (rw, rh))
                else:
                    ring_draw = base_ring
            surface.blit(ring_draw, ring_draw.get_rect(center=centro))

        arriba = (self.cajaPantalla.top + self.playable_clip_rect.top) // 2 + oy + 6
        if self.cargarPastillasVivo():
            if getattr(self, "etiquetaPintada", None) is None:
                self.etiquetaPintada = self.armarEtiquetaEnVivo(58)
            etiqueta = self.etiquetaPintada.get_rect(midleft=(self.cajaPantalla.left + 62 + ox, arriba))
            surface.blit(self.etiquetaPintada, etiqueta)
            # Punto coral pulsante de transmisión en vivo al compás de 1.9 Hz
            dot_x = etiqueta.left + int(etiqueta.height * 0.42)
            dot_y = arriba - 1
            dot_r = int(round(3 + 1.8 * beat_phase))
            pygame.draw.circle(surface, (255, 225, 220), (dot_x, dot_y), dot_r + 1)
            pygame.draw.circle(surface, (224, 54, 64), (dot_x, dot_y), dot_r)

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

    def _render_key_dock_badges(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        """
        Capa 3B (después de CAPA 3 y antes de marcoCelular):
        Dibuja el dock frontal con [D][F][J][K] y (X)(A)(Y)(B) debajo de hit_line_y
        para que ninguna nota descendente tape jamás los controles.
        """
        if getattr(self, "fuenteMando", None) is None:
            self.fuenteMando = self.assets.get_font("Arial Black, Impact, sans-serif", 22, bold=True)

        if getattr(self, "_dock_strip_surf", None) is not None and self.key_badge_rects:
            strip_pos = (self.playable_clip_rect.left + ox, self.key_badge_rects[0].top - 6 + oy)
            surface.blit(self._dock_strip_surf, strip_pos)

        gamepad_badges = (
            ("X", (64, 152, 232)),
            ("A", (74, 186, 108)),
            ("Y", (234, 192, 54)),
            ("B", (224, 78, 86)),
        )
        has_capsules = getattr(self, "capsulaTecla", None) is not None and getattr(self, "fuenteTecla", None) is not None

        for i, letra in enumerate(self.LANE_LABELS):
            badge_r = self.key_badge_rects[i].move(ox, oy)
            t_rem = self.lane_press_timers[i]
            prendida = t_rem > 0.0

            if t_rem > 0.0:
                p = 1.0 - max(0.0, min(1.0, t_rem / 0.14))
                sx = 1.0 + 0.14 * math.sin(p * math.pi)
                sy = 1.0 - 0.12 * math.sin(p * math.pi)
            else:
                sx, sy = 1.0, 1.0

            cy_key = badge_r.top + 19
            if has_capsules:
                capsula = self.capsulaPrendida if prendida else self.capsulaTecla
                if abs(sx - 1.0) > 0.01 or abs(sy - 1.0) > 0.01:
                    cw = max(8, int(round(capsula.get_width() * sx)))
                    ch = max(8, int(round(capsula.get_height() * sy)))
                    capsula = pygame.transform.smoothscale(capsula, (cw, ch))
                surface.blit(capsula, capsula.get_rect(center=(badge_r.centerx, cy_key)))
                color = (190, 70, 40) if prendida else (92, 46, 118)
                texto = self.textoConBorde(self.fuenteTecla, letra, color, (255, 248, 236), 2)
                surface.blit(texto, texto.get_rect(center=(badge_r.centerx, cy_key - 1)))
            else:
                pill_r = pygame.Rect(0, 0, badge_r.width, 34)
                pill_r.center = (badge_r.centerx, cy_key)
                pygame.draw.rect(surface, (255, 235, 130) if prendida else (245, 230, 215), pill_r, border_radius=14)
                pygame.draw.rect(surface, (112, 62, 46), pill_r, width=2, border_radius=14)
                col = (190, 70, 40) if prendida else (92, 46, 118)
                txt = self.font_keys.render(letra, True, col)
                surface.blit(txt, txt.get_rect(center=pill_r.center))

            btn_lbl, btn_col = gamepad_badges[i]
            bx, by = badge_r.centerx, badge_r.bottom - 12
            r = 14 if prendida else 12
            pygame.draw.circle(surface, (255, 248, 236), (bx, by), r + 2)
            pygame.draw.circle(surface, btn_col, (bx, by), r)
            btn_txt = self.fuenteMando.render(btn_lbl, True, (255, 255, 255))
            surface.blit(btn_txt, btn_txt.get_rect(center=(bx, by - 1)))

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
        surface.blit(self.marcoCelular, self.marcoCelular.get_rect(center=(self.phone_rect.centerx + ox + 2, self.phone_rect.centery + oy)))

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
