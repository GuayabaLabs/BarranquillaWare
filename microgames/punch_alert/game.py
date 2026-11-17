import os
import math
import random
from typing import Optional, Callable, List, Tuple, Dict, Any
import pygame
import numpy as np

from core.microgame import BaseMicrogame
from core.camera_gestures import CameraGestureInput
from core.asset_manager import AssetManager

# Cachés compartidas a nivel de módulo para reutilizar sprites procesados y buffers de audio
_SURFACE_CACHE: Dict[Tuple[Any, ...], Any] = {}
_AUDIO_CACHE: Dict[Tuple[Any, ...], Any] = {}

class PunchAlertMicrogame(BaseMicrogame):
    CAMERA_POINTER = False  # Usa la cámara directamente
    """
    Minijuego Punch-Alert: El Despachador de Notificaciones (Estilo WarioWare / Béisbol).
    Compatible 100% con el sistema de niveles / escenas (StoryMap, ArcadeMode, FreePlay)
    con la misma firma `(character_id, on_complete_callback)` que `UninorteSprintMicrogame`.
    
    1. Voces Reactivas por Personaje al Golpear Notificaciones (`CHARACTER_PUNCH_VOICES`):
       - Arquitectura preparada para que cada personaje (`char`, `katherine`, `shakira`, `westcol`)
         tenga su propio banco de audios al conectar un golpe.
       - Por ahora, todos los personajes utilizan como fallback activo las 4 voces de `char`
         (`char_audio_0_microjuego_puño.ogg` .. `char_audio_3_microjuego_puño.ogg`), pero tan pronto
         se agreguen los archivos de cada personaje (ej. `westcol_audio_0_microjuego_puño.ogg`),
         el sistema los detecta y reproduce automáticamente sin cambiar una sola línea de código.
    
    2. Recorte Quirúrgico y Limpieza de Componentes:
       - Notificaciones (`assets/notificaciones_microjuego.png` - 1774x887 RGBA):
         Extracción limpia sin residuos de filas adyacentes y preservando aspect ratio.
       - Personaje (`assets/*_sprite_box_microjuego.png`):
         Separación dinámica por valle de transparencia, con animación de respiración (idle bobbing),
         sombra elíptica suave bajo los pies e impulso ascendente al lanzar el uppercut.
       - HUD de Strikes (`assets/ui_strike_microjuegos.png`):
         Barra limpia con marcas 'X' dinámicas centradas en los 3 círculos vacíos (sin contador de alertas extra).
       - Reloj Contador Gráfico Oficial (`assets/contador_microjuegos.png`) en la esquina superior derecha.
    """

    # =========================================================================
    # MAPA DE VOCES POR PERSONAJE AL CONECTAR EL PUÑO (ESCALABLE POR NIVEL/PERSONAJE)
    # =========================================================================
    # Cada personaje tiene su propia lista de archivos de voz al golpear una notificación.
    # Si los archivos específicos de un personaje aún no están en `assets/`, el cargador
    # usa automáticamente las voces de `char` como fallback activo.
    CHARACTER_PUNCH_VOICES: Dict[str, List[str]] = {
        "char": [
            "char_audio_0_microjuego_puño.ogg",
            "char_audio_1_microjuego_puño.ogg",
            "char_audio_2_microjuego_puño.ogg",
            "char_audio_3_microjuego_puño.ogg",
        ],
        "katherine": [
            "katherine_audio_0_microjuego_puño.ogg",
            "katherine_audio_1_microjuego_puño.ogg",
            "katherine_audio_2_microjuego_puño.ogg",
            "katherine_audio_3_microjuego_puño.ogg",
        ],
        "shakira": [
            "shakira_audio_0_microjuego_puño.ogg",
            "shakira_audio_1_microjuego_puño.ogg",
            "shakira_audio_2_microjuego_puño.ogg",
            "shakira_audio_3_microjuego_puño.ogg",
        ],
        "westcol": [
            "westcol_audio_0_microjuego_puño.ogg",
            "westcol_audio_1_microjuego_puño.ogg",
            "westcol_audio_2_microjuego_puño.ogg",
            "westcol_audio_3_microjuego_puño.ogg",
        ],
    }

    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None,
        command_text: str = "¡DESPACHA EL SPAM!",
        time_limit: float = 15.0
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text=command_text,
            time_limit=time_limit,
            on_complete_callback=on_complete_callback
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("PunchMusic.mp3", volume_scale=0.35)

    def _extract_tight_surface(self, surface: pygame.Surface, rect: pygame.Rect) -> pygame.Surface:
        """Extrae un subsurface y lo ajusta a su bounding box de píxeles no transparentes."""
        sub = surface.subsurface(rect)
        bbox = sub.get_bounding_rect(min_alpha=20)
        if bbox.width > 0 and bbox.height > 0:
            return sub.subsurface(bbox).copy()
        return sub.copy()

    def _extract_clean_card_surface(self, sheet: pygame.Surface, rect: pygame.Rect) -> pygame.Surface:
        """
        Extrae una tarjeta de notificación limpiando con NumPy vectorizado cualquier artefacto
        desconectado en los primeros píxeles superiores y ajustando a su bounding box real.
        """
        sub = sheet.subsurface(rect).copy()
        alpha_arr = pygame.surfarray.pixels_alpha(sub)
        w, h = sub.get_size()

        if w > 0 and h > 4:
            y_lim = min(25, h)
            top_active = (alpha_arr[:, 0] > 15) | (alpha_arr[:, 2] > 15)
            low_band = alpha_arr[:, 4:y_lim] < 15
            has_gap = top_active & low_band.any(axis=1)
            if has_gap.any():
                cols = np.flatnonzero(has_gap)
                ys = 4 + np.argmax(low_band[cols], axis=1)
                y_grid = np.arange(y_lim)[None, :]
                band_view = alpha_arr[cols, :y_lim]
                band_view[y_grid < ys[:, None]] = 0
                alpha_arr[cols, :y_lim] = band_view

        del alpha_arr

        bbox = sub.get_bounding_rect(min_alpha=25)
        if bbox.width > 0 and bbox.height > 0:
            return sub.subsurface(bbox).copy()
        return sub

    def _load_optional_ui(self, filename: str, target_h: int) -> Optional[pygame.Surface]:
        """Carga un elemento de UI opcional manteniendo su relación de aspecto."""
        cache_key = ("optional_ui", filename, target_h)
        if cache_key in _SURFACE_CACHE:
            return _SURFACE_CACHE[cache_key]
        try:
            raw = self.assets.load_surface(filename)
            bbox = raw.get_bounding_rect(min_alpha=15)
            cropped = raw.subsurface(bbox).copy() if (bbox.width > 0 and bbox.height > 0) else raw
            w, h = cropped.get_size()
            scale = target_h / float(max(1, h))
            res = pygame.transform.smoothscale(cropped, (int(w * scale), target_h))
            _SURFACE_CACHE[cache_key] = res
            return res
        except Exception:
            return None

    def _resolve_audio_file(self, filename: str) -> Optional[str]:
        """Busca un archivo de audio en assets/ tolerando diferencias de codificación UTF-8/ANSI en la ñ."""
        base_dir = "assets"
        direct = os.path.join(base_dir, filename)
        if os.path.exists(direct):
            return direct

        # Búsqueda flexible por prefijo (ej: 'char_audio_0_')
        prefix = "_".join(filename.split("_")[:3])
        if os.path.isdir(base_dir):
            for f in os.listdir(base_dir):
                if f.lower().startswith(prefix.lower()) and f.lower().endswith(".ogg"):
                    return os.path.join(base_dir, f)
        return None

    def _load_character_punch_voices(self) -> None:
        """
        Carga (o reutiliza desde caché) las líneas de voz del personaje seleccionado al pegarle a una notificación.
        """
        self.punch_voices: List[pygame.mixer.Sound] = []
        self.last_voice_idx: int = -1

        mixer_cfg = pygame.mixer.get_init()
        if not mixer_cfg:
            return

        sfx_vol = getattr(self.audio, "sfx_volume", 0.85)
        cache_key = ("punch_voices", self.character_id, mixer_cfg)
        cached_voices = _AUDIO_CACHE.get(cache_key)
        if cached_voices is not None:
            for snd in cached_voices:
                snd.set_volume(sfx_vol)
            self.punch_voices = list(cached_voices)
            return

        target_files = self.CHARACTER_PUNCH_VOICES.get(
            self.character_id,
            self.CHARACTER_PUNCH_VOICES["char"]
        )

        # Intentar cargar las voces propias del personaje actual
        for fname in target_files:
            resolved = self._resolve_audio_file(fname)
            if resolved:
                try:
                    snd = pygame.mixer.Sound(resolved)
                    snd.set_volume(sfx_vol)
                    self.punch_voices.append(snd)
                except Exception:
                    pass

        # Fallback a las voces de 'char' con modulación tímbrica por personaje si no tiene audios grabados propios
        if not self.punch_voices:
            pitch_profiles = {
                "shakira": 1.32,    # Agudo y enérgico
                "katherine": 1.22,  # Tono femenino claro y dinámico
                "westcol": 0.94,    # Tono ligeramente más grave y raspado
                "char": 1.0,        # Tono nativo
            }
            pitch_shift = pitch_profiles.get(self.character_id, 1.0)

            for fname in self.CHARACTER_PUNCH_VOICES["char"]:
                resolved = self._resolve_audio_file(fname)
                if resolved:
                    try:
                        snd = pygame.mixer.Sound(resolved)
                        if abs(pitch_shift - 1.0) > 0.02 and hasattr(self.audio, "get_pitched_sound"):
                            snd = self.audio.get_pitched_sound(snd, pitch_shift)
                        snd.set_volume(sfx_vol)
                        self.punch_voices.append(snd)
                    except Exception:
                        pass

        if self.punch_voices:
            _AUDIO_CACHE[cache_key] = list(self.punch_voices)

    def _play_character_punch_voice(self) -> None:
        """Reproduce una voz aleatoria del personaje al conectar el golpe (evitando repetir la misma seguida)."""
        if not self.punch_voices:
            return
        if hasattr(self.audio, "sound_enabled") and not self.audio.sound_enabled:
            return

        if len(self.punch_voices) > 1:
            candidates = [i for i in range(len(self.punch_voices)) if i != self.last_voice_idx]
            idx = random.choice(candidates)
        else:
            idx = 0

        self.last_voice_idx = idx
        snd = self.punch_voices[idx]
        if hasattr(self.audio, "play_sfx"):
            self.audio.play_sfx(snd)
        else:
            vol = getattr(self.audio, "sfx_volume", 0.85)
            snd.set_volume(vol)
            snd.play()

    def _init_punch_sounds(self) -> None:
        """Genera (o reutiliza desde caché) los efectos de sonido procedurales de soporte."""
        self.snd_hit: Optional[pygame.mixer.Sound] = None
        self.snd_whiff: Optional[pygame.mixer.Sound] = None
        self.snd_safe: Optional[pygame.mixer.Sound] = None
        self.snd_strike: Optional[pygame.mixer.Sound] = None

        mixer_cfg = pygame.mixer.get_init()
        if not mixer_cfg:
            return

        cache_key = ("punch_sfx", mixer_cfg)
        cached_sfx = _AUDIO_CACHE.get(cache_key)
        if cached_sfx is not None:
            self.snd_hit, self.snd_whiff, self.snd_safe, self.snd_strike = cached_sfx
            return

        try:
            sr = 44100
            # 1. Hit Sound (¡CRACK! de bateo seco + armónico ascendente)
            dur_hit = 0.14
            t_hit = np.linspace(0, dur_hit, int(sr * dur_hit), False)
            noise = np.random.uniform(-1.0, 1.0, len(t_hit)) * np.exp(-t_hit * 45.0)
            tone = np.sin(2 * np.pi * np.geomspace(220, 680, len(t_hit)) * t_hit) * np.exp(-t_hit * 18.0)
            wave_hit = np.clip((noise * 0.55 + tone * 0.65) * 0.85, -1.0, 1.0)
            arr_hit = (wave_hit * 32767).astype(np.int16)
            self.snd_hit = pygame.sndarray.make_sound(np.column_stack((arr_hit, arr_hit)))

            # 2. Whiff / Swing Sound (Swoosh corto al lanzar el guante)
            dur_whiff = 0.08
            t_w = np.linspace(0, dur_whiff, int(sr * dur_whiff), False)
            freq_w = np.geomspace(340, 140, len(t_w))
            wave_w = np.clip(np.sin(2 * np.pi * freq_w * t_w) * np.sin(np.pi * t_w / dur_whiff) * 0.78, -1.0, 1.0)
            arr_w = (wave_w * 32767).astype(np.int16)
            self.snd_whiff = pygame.sndarray.make_sound(np.column_stack((arr_w, arr_w)))

            # 3. Safe Saved Sound (Doble campana cálida cuando entra una notificación prioritaria)
            dur_safe = 0.18
            t_s = np.linspace(0, dur_safe, int(sr * dur_safe), False)
            freq_s = np.where(t_s < dur_safe * 0.5, 587.33, 880.0)
            env_s = np.exp(-t_s * 12.0)
            wave_s = np.clip(np.sin(2 * np.pi * freq_s * t_s) * env_s * 0.82, -1.0, 1.0)
            arr_s = (wave_s * 32767).astype(np.int16)
            self.snd_safe = pygame.sndarray.make_sound(np.column_stack((arr_s, arr_s)))

            # 4. Strike Buzz (Zumbido doble de vibración de celular / error)
            dur_st = 0.24
            t_st = np.linspace(0, dur_st, int(sr * dur_st), False)
            buzz = np.sign(np.sin(2 * np.pi * 115.0 * t_st)) * 0.5 + np.sin(2 * np.pi * 170.0 * t_st) * 0.5
            env_st = np.where((t_st < 0.10) | (t_st > 0.13), 1.0, 0.1) * np.exp(-t_st * 4.0)
            wave_st = np.clip(buzz * env_st * 0.82, -1.0, 1.0)
            arr_st = (wave_st * 32767).astype(np.int16)
            self.snd_strike = pygame.sndarray.make_sound(np.column_stack((arr_st, arr_st)))

            _AUDIO_CACHE[cache_key] = (self.snd_hit, self.snd_whiff, self.snd_safe, self.snd_strike)
        except Exception:
            pass

    def _play_sfx(self, snd: Optional[pygame.mixer.Sound]) -> None:
        if snd is None:
            return
        if hasattr(self.audio, "play_sfx"):
            self.audio.play_sfx(snd)
            return
        if hasattr(self.audio, "sound_enabled") and not self.audio.sound_enabled:
            return
        vol = getattr(self.audio, "sfx_volume", 0.8)
        snd.set_volume(vol)
        snd.play()

    def setup_game(self) -> None:
        self.camera_input = CameraGestureInput.get_instance()
        if (
            os.environ.get("SDL_VIDEODRIVER") != "dummy"
            and self.camera_input.available
            and not self.camera_input.enabled
            and not self.camera_input.suspended
        ):
            self.camera_input.keep_alive(retry_interval=2.0)
        """Carga recursos oficiales, configura el reloj HUD, voces del personaje y la oleada."""
        self.assets = AssetManager.get_instance()
        self._init_punch_sounds()
        self._load_character_punch_voices()

        # 1. Cargar fondo oficial provisto
        bg_key = ("bg", self.screen_w, self.screen_h)
        cached_bg = _SURFACE_CACHE.get(bg_key)
        if cached_bg is not None:
            self.bg_surface = cached_bg
        else:
            raw_bg = self.assets.load_surface("fondo_box_microjuego.png")
            if raw_bg:
                self.bg_surface = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))
                _SURFACE_CACHE[bg_key] = self.bg_surface
            else:
                self.bg_surface = pygame.Surface((self.screen_w, self.screen_h))
                self.bg_surface.fill((25, 25, 35))

        # 2. Cargar contador gráfico oficial (igual que en UninorteSprint / Crossy Road)
        self.spr_counter = self._load_optional_ui("contador_microjuegos.png", target_h=96)

        # 3. Notificaciones con límites exactos del nuevo sheet (4 Filas x 4 Columnas)
        target_card_w = 430
        target_card_h = 205
        notif_key = ("notif_cards", target_card_w, target_card_h)
        cached_notifs = _SURFACE_CACHE.get(notif_key)
        if cached_notifs is not None:
            safe_tuple, trash_tuple = cached_notifs
            self.safe_sprites = list(safe_tuple)
            self.trash_sprites = list(trash_tuple)
        else:
            notif_sheet = self.assets.load_surface("notificaciones_microjuego.png")
            self.safe_sprites = []
            self.trash_sprites = []

            row_intervals = [(10, 248), (246, 463), (462, 661), (660, 868)]
            col_intervals = [(0, 439), (441, 883), (886, 1328), (1331, 1773)]
            safe_cells = {(2, 0), (2, 1), (2, 2), (2, 3), (1, 2)}

            if notif_sheet:
                for r_idx, (y1, y2) in enumerate(row_intervals):
                    for c_idx, (x1, x2) in enumerate(col_intervals):
                        cell_rect = pygame.Rect(x1, y1, x2 - x1, y2 - y1)
                        clean_card = self._extract_clean_card_surface(notif_sheet, cell_rect)
                        cw, ch = clean_card.get_size()
                        scale = min(target_card_w / float(cw), target_card_h / float(ch))
                        final_w = int(cw * scale)
                        final_h = int(ch * scale)
                        scaled_inner = pygame.transform.smoothscale(clean_card, (final_w, final_h))

                        card_canvas = pygame.Surface((target_card_w, target_card_h), pygame.SRCALPHA)
                        card_x = (target_card_w - final_w) // 2
                        card_y = (target_card_h - final_h) // 2
                        card_canvas.blit(scaled_inner, (card_x, card_y))

                        if (r_idx, c_idx) in safe_cells:
                            self.safe_sprites.append(card_canvas)
                        else:
                            self.trash_sprites.append(card_canvas)
                _SURFACE_CACHE[notif_key] = (tuple(self.safe_sprites), tuple(self.trash_sprites))
            else:
                ph_trash = pygame.Surface((target_card_w, target_card_h), pygame.SRCALPHA)
                ph_trash.fill((220, 50, 50, 220))
                self.trash_sprites.append(ph_trash)
                ph_safe = pygame.Surface((target_card_w, target_card_h), pygame.SRCALPHA)
                ph_safe.fill((50, 220, 50, 220))
                self.safe_sprites.append(ph_safe)

        # 4. Personaje Boxeador con separación dinámica por valle de transparencia
        char_render_h = 540
        box_key = ("box_char", self.character_id, char_render_h)
        cached_box = _SURFACE_CACHE.get(box_key)
        if cached_box is not None:
            self.sprite_idle, self.sprite_punch = cached_box
        else:
            char_sheet_name = f"{self.character_id}_sprite_box_microjuego.png"
            try:
                box_sheet = self.assets.load_surface(char_sheet_name)
            except Exception:
                box_sheet = self.assets.load_surface("char_sprite_box_microjuego.png")

            if box_sheet:
                bw, bh = box_sheet.get_size()
                mask_arr = pygame.surfarray.array_alpha(box_sheet)
                x_start = int(bw * 0.40)
                x_end = int(bw * 0.53)
                col_sums = (mask_arr[x_start:x_end, :] > 20).sum(axis=1)
                zero_offsets = np.flatnonzero(col_sums == 0)
                if zero_offsets.size > 0:
                    split_x = int(x_start + zero_offsets[len(zero_offsets) // 2])
                else:
                    split_x = int(x_start + np.argmin(col_sums))

                idle_rect = pygame.Rect(0, 0, split_x, bh)
                punch_rect = pygame.Rect(split_x, 0, bw - split_x, bh)

                idle_tight = self._extract_tight_surface(box_sheet, idle_rect)
                punch_tight = self._extract_tight_surface(box_sheet, punch_rect)

                scale_idle = char_render_h / float(idle_tight.get_height())
                idle_w = int(idle_tight.get_width() * scale_idle)
                self.sprite_idle = pygame.transform.smoothscale(idle_tight, (idle_w, char_render_h))

                scale_punch = char_render_h / float(punch_tight.get_height())
                punch_w = int(punch_tight.get_width() * scale_punch)
                self.sprite_punch = pygame.transform.smoothscale(punch_tight, (punch_w, char_render_h))
                _SURFACE_CACHE[box_key] = (self.sprite_idle, self.sprite_punch)
            else:
                self.sprite_idle = pygame.Surface((400, char_render_h), pygame.SRCALPHA)
                self.sprite_idle.fill((60, 60, 160, 200))
                self.sprite_punch = pygame.Surface((440, char_render_h), pygame.SRCALPHA)
                self.sprite_punch.fill((220, 60, 60, 200))

        # 5. HUD Completo de Strikes (ui_strike_microjuegos.png con los 3 círculos vacíos)
        hud_bar_h = 115
        hud_key = ("strike_hud", hud_bar_h)
        cached_hud = _SURFACE_CACHE.get(hud_key)
        if cached_hud is not None:
            self.hud_bar_w, self.hud_bar_h, self.strike_hud_base = cached_hud
        else:
            strike_sheet = self.assets.load_surface("ui_strike_microjuegos.png")
            if strike_sheet:
                tight_bar = self._extract_tight_surface(strike_sheet, pygame.Rect(0, 0, strike_sheet.get_width(), strike_sheet.get_height()))
                aspect = float(tight_bar.get_width()) / float(tight_bar.get_height())
                self.hud_bar_w = int(hud_bar_h * aspect)
                self.hud_bar_h = hud_bar_h
                self.strike_hud_base = pygame.transform.smoothscale(tight_bar, (self.hud_bar_w, self.hud_bar_h))
                _SURFACE_CACHE[hud_key] = (self.hud_bar_w, self.hud_bar_h, self.strike_hud_base)
            else:
                self.hud_bar_w = 400
                self.hud_bar_h = hud_bar_h
                self.strike_hud_base = pygame.Surface((self.hud_bar_w, self.hud_bar_h), pygame.SRCALPHA)
                self.strike_hud_base.fill((160, 40, 40, 200))

        self.circle_rel_positions = [
            (0.510, 0.500),
            (0.676, 0.500),
            (0.849, 0.500)
        ]

        # 6. Geometría y Zona de Bateo Estricta ("Sweet Spot" Encajado en la Caja)
        self.lane_center_x = self.screen_w // 2
        self.char_base_y = self.screen_h - 35
        self.char_idle_pos = (
            self.lane_center_x - (self.sprite_idle.get_width() // 2),
            self.char_base_y - self.sprite_idle.get_height()
        )
        self.char_punch_pos = (
            self.lane_center_x - (self.sprite_punch.get_width() // 2),
            self.char_base_y - self.sprite_punch.get_height()
        )

        # El Sweet Spot exige que el centro de la tarjeta esté verdaderamente encajado en la caja (220px de alto)
        self.sweet_spot_center_y = self.screen_h - 430  # Y = 650
        self.hit_zone_y_min = self.sweet_spot_center_y - 95   # Y = 555 (debe haber entrado bien a la caja)
        self.hit_zone_y_max = self.sweet_spot_center_y + 95   # Y = 745 (antes de salirse por debajo)

        # 7. Estado del jugador, Anti-Spam (Castigo al Whiff) y Combo
        self.is_punching: bool = False
        self.punch_timer: float = 0.0
        self.punch_duration: float = 0.22
        self.punch_cooldown: float = 0.28
        self.whiff_penalty_cooldown: float = 0.65  # Castigo de bloqueo si spameas ESPACIO al aire
        self.is_whiff_penalized: bool = False
        self.whiff_streak: int = 0
        self.cooldown_timer: float = 0.0
        self.pulse_clock: float = 0.0
        self.combo_streak: int = 0

        # 8. Reglas de Victoria / Derrota (Oleada Extendida de 11 Notificaciones en 15s)
        self.strikes: int = 0
        self.max_strikes: int = 3
        self.total_wave_count: int = 11
        self.processed_count: int = 0

        # 9. Diseño de Curva de Pacing de la Oleada
        self.wave_queue: List[dict] = []
        wave_blueprint = [
            # Fase 1: Calentamiento
            ("trash", 0.45, 580.0),
            ("trash", 1.70, 600.0),
            ("safe",  2.95, 600.0),
            # Fase 2: Ritmo de Crucero
            ("trash", 4.20, 640.0),
            ("trash", 5.35, 650.0),
            ("safe",  6.50, 650.0),
            ("trash", 7.65, 670.0),
            # Fase 3: Ráfaga Final
            ("trash", 8.75, 700.0),
            ("safe",  9.85, 700.0),
            ("trash", 10.95, 720.0),
            ("trash", 12.00, 740.0),
        ]

        middle_types = ["trash", "trash", "safe", "trash"]
        random.shuffle(middle_types)
        for idx, m_type in enumerate(middle_types):
            _, sp_time, sp_speed = wave_blueprint[3 + idx]
            wave_blueprint[3 + idx] = (m_type, sp_time, sp_speed)

        for t_name, sp_time, sp_speed in wave_blueprint:
            is_safe = (t_name == "safe")
            sprite = random.choice(self.safe_sprites) if is_safe else random.choice(self.trash_sprites)
            self.wave_queue.append({
                "spawn_time": sp_time,
                "spawned": False,
                "is_safe": is_safe,
                "sprite": sprite,
                "x": float(self.lane_center_x - (target_card_w // 2)),
                "y": -float(target_card_h) - 40.0,
                "w": target_card_w,
                "h": target_card_h,
                "speed": sp_speed,
                "state": "falling",
                "in_sweet_spot": False,
                "fly_vx": 0.0,
                "fly_vy": 0.0,
                "fly_rot": 0.0,
                "fly_rot_speed": 0.0,
                "alpha": 255.0
            })

        # 10. Game Feel Polish (Trauma System, Hit-stop, Partículas, Anillos de Onda)
        self.trauma: float = 0.0
        self.max_shake_offset: float = 28.0
        self.hit_stop_timer: float = 0.0
        self.spark_particles: List[dict] = []
        self.shockwaves: List[dict] = []
        self.popups: List[dict] = []
        self.strike_flash_alpha: float = 0.0

        # Tipografías
        self.font_juice = pygame.font.SysFont("Impact, Arial Black, sans-serif", 58)
        self.font_prompt = pygame.font.SysFont("Impact, Arial Black, sans-serif", 34)
        self.font_strike_x = pygame.font.SysFont("Impact, Arial Black, sans-serif", 46)
        self.font_timer = pygame.font.SysFont("Arial Black, Impact, sans-serif", 32)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        """Maneja el disparo del golpe ascendente con ESPACIO."""
        if self.phase != self.PHASE_PLAY or self.is_finished:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.trigger_punch()

    def exit(self) -> None:
        # La cámara pertenece al motor y se comparte con el resto de escenas.
        pass

    def add_trauma(self, amount: float) -> None:
        """Agrega trauma con clamp en 1.0."""
        self.trauma = min(1.0, self.trauma + amount)

    def spawn_impact_sparks(self, x: float, y: float, count: int = 18, color_base: Tuple[int, int, int] = (255, 220, 50)) -> None:
        """Emisor de chispas lineales limpias con desvanecimiento alfa y onda expansiva."""
        self.shockwaves.append({
            "x": x,
            "y": y,
            "radius": 24.0,
            "max_radius": 190.0,
            "life": 0.22,
            "max_life": 0.22,
            "color": color_base
        })
        for _ in range(count):
            angle = random.uniform(0.0, math.pi * 2)
            speed = random.uniform(260.0, 780.0)
            length = random.uniform(14.0, 34.0)
            life = random.uniform(0.2, 0.45)
            self.spark_particles.append({
                "x": x,
                "y": y,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "length": length,
                "life": life,
                "max_life": life,
                "color": color_base
            })

    def trigger_punch(self) -> None:
        """
        Ejecuta el golpe si no está en cooldown y evalúa el impacto estricto en el Sweet Spot.
        Penaliza el spam de tecla (whiff): si golpeas al aire cuando la notificación aún no ha
        encajado en la caja, aplica bloqueo extendido (0.65s) y si spameas 2 veces al aire -> +1 Strike.
        """
        if self.cooldown_timer > 0.0 or self.is_punching:
            return

        self.is_punching = True
        self.punch_timer = self.punch_duration
        self.cooldown_timer = self.punch_cooldown

        hit_connected = False
        for notif in self.wave_queue:
            if not notif["spawned"] or notif["state"] != "falling":
                continue

            notif_center_y = notif["y"] + (notif["h"] * 0.5)

            # Requisito de encaje: el centro de la tarjeta debe estar dentro de la caja (hit_zone_y_min..hit_zone_y_max)
            if self.hit_zone_y_min <= notif_center_y <= self.hit_zone_y_max:
                hit_connected = True
                self.is_whiff_penalized = False
                # Reproducir la voz del personaje al pegarle a la notificación
                self._play_character_punch_voice()

                if notif["is_safe"]:
                    self.combo_streak = 0
                    self.on_strike("¡ERA IMPORTANTE!")
                    notif["state"] = "hit_fly"
                    notif["fly_vx"] = random.choice([-550.0, 550.0])
                    notif["fly_vy"] = -850.0
                    notif["fly_rot_speed"] = random.uniform(-400.0, 400.0)
                    self.spawn_impact_sparks(self.lane_center_x, notif_center_y, 14, (255, 60, 60))
                else:
                    self.on_successful_hit(notif)
                break

        if not hit_connected:
            # Penalización Anti-Spam acumulativa (NO se perdona al acertar: se guarda hasta el 2do fallo)
            self._play_sfx(self.snd_whiff)
            self.combo_streak = 0
            self.whiff_streak += 1
            self.is_whiff_penalized = True
            self.cooldown_timer = self.whiff_penalty_cooldown
            self.add_trauma(0.28)

            if self.whiff_streak >= 2:
                # 2do golpe al aire acumulado = +1 Strike directo y reinicia la cuenta de 2
                self.whiff_streak = 0
                self.on_strike("¡2 FALLOS AL AIRE!")
            else:
                self.popups.append({
                    "text": "¡FALLO AL AIRE (1/2)! ¡CUIDADO!",
                    "x": float(self.lane_center_x),
                    "y": float(self.hit_zone_y_min - 28),
                    "timer": 0.60,
                    "max_timer": 0.60,
                    "color": (255, 140, 60)
                })

    def on_successful_hit(self, notif: dict) -> None:
        """Impacto kinético sobre notificación basura con Game Feel refinado."""
        self._play_sfx(self.snd_hit)
        self.combo_streak += 1

        notif["state"] = "hit_fly"
        direction = -1.0 if random.random() < 0.5 else 1.0
        notif["fly_vx"] = direction * random.uniform(760.0, 1120.0)
        notif["fly_vy"] = -random.uniform(980.0, 1360.0)
        notif["fly_rot_speed"] = direction * random.uniform(440.0, 840.0)

        # Hit-stop de 4 frames (~0.066s)
        self.hit_stop_timer = 0.066
        self.add_trauma(0.55)

        impact_y = notif["y"] + (notif["h"] // 2)
        self.spawn_impact_sparks(self.lane_center_x, impact_y, count=24, color_base=(255, 235, 70))

        words = ["¡DESPACHADA!", "¡EN MUTE!", "¡HOME RUN!", "¡A LA BASURA!"]
        text = random.choice(words)
        if self.combo_streak >= 3:
            text = f"{text} x{self.combo_streak}"

        self.popups.append({
            "text": text,
            "x": float(self.lane_center_x + random.uniform(-45, 45)),
            "y": float(notif["y"] - 20),
            "timer": 0.65,
            "max_timer": 0.65,
            "color": (255, 235, 45)
        })

        self.processed_count += 1
        self.check_wave_progress()

    def on_strike(self, reason: str) -> None:
        """Aplica +1 Strike, sonido de vibración, sacudida y flash de pantalla."""
        self._play_sfx(self.snd_strike)
        self.strikes += 1
        self.strike_flash_alpha = 190.0
        self.add_trauma(0.85)

        self.popups.append({
            "text": f"¡STRIKE! {reason}",
            "x": float(self.lane_center_x),
            "y": float(self.hit_zone_y_min - 30),
            "timer": 0.85,
            "max_timer": 0.85,
            "color": (255, 60, 60)
        })

        if self.strikes >= self.max_strikes:
            self.finish_game(won=False)

    def check_wave_progress(self) -> None:
        """Verifica victoria si se procesaron todas las notificaciones."""
        if self.strikes >= self.max_strikes:
            return

        if self.processed_count >= self.total_wave_count:
            self.finish_game(won=True)

    def update_game(self, dt: float) -> None:
        """Actualiza física, estado de Sweet Spot, ondas expansivas, trauma y partículas."""
        if getattr(self, "camera_input", None) and self.camera_input.consume_punch():
            self.trigger_punch()
        self.pulse_clock += dt * 10.0

        if self.hit_stop_timer > 0.0:
            self.hit_stop_timer -= dt
            return

        if self.trauma > 0.0:
            self.trauma = max(0.0, self.trauma - (dt * 1.6))

        if self.strike_flash_alpha > 0.0:
            self.strike_flash_alpha = max(0.0, self.strike_flash_alpha - (dt * 320.0))

        if self.cooldown_timer > 0.0:
            self.cooldown_timer = max(0.0, self.cooldown_timer - dt)
            if self.cooldown_timer <= 0.0:
                self.is_whiff_penalized = False

        if self.is_punching:
            self.punch_timer -= dt
            if self.punch_timer <= 0.0:
                self.is_punching = False

        elapsed = self.time_limit - self.time_left
        for notif in self.wave_queue:
            if not notif["spawned"] and elapsed >= notif["spawn_time"]:
                notif["spawned"] = True

            if not notif["spawned"]:
                continue

            if notif["state"] == "falling":
                notif["y"] += notif["speed"] * dt
                notif_center_y = notif["y"] + (notif["h"] * 0.5)

                # Solo se enciende el Sweet Spot cuando el centro de la tarjeta encaja dentro de la caja
                notif["in_sweet_spot"] = (self.hit_zone_y_min <= notif_center_y <= self.hit_zone_y_max)

                if notif_center_y > self.hit_zone_y_max + 20:
                    notif["state"] = "passed"
                    notif["in_sweet_spot"] = False
                    if not notif["is_safe"]:
                        self.combo_streak = 0
                        self.on_strike("¡SE PASÓ EL SPAM!")
                    else:
                        self._play_sfx(self.snd_safe)
                        self.combo_streak += 1
                        self.popups.append({
                            "text": "¡RECIBIDA A SALVO!",
                            "x": float(self.lane_center_x),
                            "y": float(self.hit_zone_y_max - 20),
                            "timer": 0.55,
                            "max_timer": 0.55,
                            "color": (80, 255, 130)
                        })
                    self.processed_count += 1
                    self.check_wave_progress()

            elif notif["state"] == "hit_fly":
                notif["x"] += notif["fly_vx"] * dt
                notif["y"] += notif["fly_vy"] * dt
                notif["fly_vy"] += 2300.0 * dt
                notif["fly_rot"] += notif["fly_rot_speed"] * dt
                notif["alpha"] = max(0.0, notif["alpha"] - (dt * 240.0))
                if notif["alpha"] <= 0.0 or notif["y"] > self.screen_h + 300:
                    notif["state"] = "done"

        # Ondas de choque
        for sw in list(self.shockwaves):
            sw["life"] -= dt
            if sw["life"] <= 0.0:
                self.shockwaves.remove(sw)
            else:
                progress = 1.0 - (sw["life"] / sw["max_life"])
                sw["radius"] = 24.0 + (sw["max_radius"] - 24.0) * progress

        # Partículas
        for p in list(self.spark_particles):
            p["life"] -= dt
            if p["life"] <= 0.0:
                self.spark_particles.remove(p)
            else:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vy"] += 800.0 * dt

        # Popups
        for pop in list(self.popups):
            pop["timer"] -= dt
            pop["y"] -= 65.0 * dt
            if pop["timer"] <= 0.0:
                self.popups.remove(pop)

        if self.time_left <= 0.0 and not self.is_finished:
            if self.strikes < self.max_strikes:
                self.finish_game(won=True)
            else:
                self.finish_game(won=False)

    def _render_sweet_spot_guide(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        """Dibuja la guía visual de la Zona de Bateo ("Sweet Spot") con feedback de color y texto."""
        active_notif = None
        for notif in self.wave_queue:
            if notif["spawned"] and notif["state"] == "falling" and notif["in_sweet_spot"]:
                active_notif = notif
                break

        zone_w = 470
        zone_h = 220
        zone_x = self.lane_center_x - (zone_w // 2) + ox
        zone_y = self.sweet_spot_center_y - (zone_h // 2) + oy

        guide_surf = pygame.Surface((zone_w, zone_h), pygame.SRCALPHA)
        pulse = (math.sin(self.pulse_clock) + 1.0) * 0.5

        if self.is_whiff_penalized and self.cooldown_timer > 0.0:
            # Estado de bloqueo por spamear antes de tiempo (Castigo visual en rojo/naranja)
            border_color = (255, 75, 65, 210)
            glow_color = (255, 50, 50, 45)
            pygame.draw.rect(guide_surf, glow_color, (0, 0, zone_w, zone_h), border_radius=28)
            pygame.draw.rect(guide_surf, border_color, (0, 0, zone_w, zone_h), width=5, border_radius=28)

            prompt_surf = self.font_prompt.render("¡RECARGANDO GUANTE!", True, (255, 95, 85))
            prompt_bg = self.font_prompt.render("¡RECARGANDO GUANTE!", True, (25, 10, 10))
            px = zone_x + zone_w + 18
            py = zone_y + (zone_h // 2) - (prompt_surf.get_height() // 2)
            surface.blit(prompt_bg, (px + 2, py + 2))
            surface.blit(prompt_surf, (px, py))
        elif active_notif is not None:
            if not active_notif["is_safe"]:
                border_color = (90, 255, 110, int(195 + 55 * pulse))
                glow_color = (90, 255, 110, int(45 + 35 * pulse))
                pygame.draw.rect(guide_surf, glow_color, (0, 0, zone_w, zone_h), border_radius=28)
                pygame.draw.rect(guide_surf, border_color, (0, 0, zone_w, zone_h), width=5, border_radius=28)

                prompt_surf = self.font_prompt.render("¡BATEA! [ESPACIO]", True, (110, 255, 120))
                prompt_bg = self.font_prompt.render("¡BATEA! [ESPACIO]", True, (15, 25, 15))
                px = zone_x + zone_w + 18
                py = zone_y + (zone_h // 2) - (prompt_surf.get_height() // 2)
                surface.blit(prompt_bg, (px + 2, py + 2))
                surface.blit(prompt_surf, (px, py))
            else:
                border_color = (255, 215, 70, int(165 + 50 * pulse))
                glow_color = (255, 215, 70, 32)
                pygame.draw.rect(guide_surf, glow_color, (0, 0, zone_w, zone_h), border_radius=28)
                pygame.draw.rect(guide_surf, border_color, (0, 0, zone_w, zone_h), width=4, border_radius=28)

                prompt_surf = self.font_prompt.render("¡NO PEGUES! (SEGURA)", True, (255, 225, 90))
                prompt_bg = self.font_prompt.render("¡NO PEGUES! (SEGURA)", True, (25, 20, 10))
                px = zone_x + zone_w + 18
                py = zone_y + (zone_h // 2) - (prompt_surf.get_height() // 2)
                surface.blit(prompt_bg, (px + 2, py + 2))
                surface.blit(prompt_surf, (px, py))
        else:
            bracket_color = (255, 255, 255, 115)
            b_len = 36
            b_thick = 4
            pygame.draw.line(guide_surf, bracket_color, (0, 0), (b_len, 0), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (0, 0), (0, b_len), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (zone_w - b_len, 0), (zone_w, 0), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (zone_w - 1, 0), (zone_w - 1, b_len), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (0, zone_h - 1), (b_len, zone_h - 1), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (0, zone_h - b_len), (0, zone_h), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (zone_w - b_len, zone_h - 1), (zone_w, zone_h - 1), b_thick)
            pygame.draw.line(guide_surf, bracket_color, (zone_w - 1, zone_h - b_len), (zone_w - 1, zone_h), b_thick)

        surface.blit(guide_surf, (zone_x, zone_y))

    def _render_player_character(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        """
        Renderiza al personaje con sombra elíptica en el piso, respiración natural (idle bobbing)
        e impulso vertical elástico al ejecutar el Uppercut.
        """
        shadow_w = 220 if not self.is_punching else 185
        shadow_h = 34
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (25, 20, 15, 85), (0, 0, shadow_w, shadow_h))
        shadow_rect = shadow_surf.get_rect(center=(self.lane_center_x + ox, self.char_base_y - 8 + oy))
        surface.blit(shadow_surf, shadow_rect)

        if self.is_punching:
            punch_ratio = max(0.0, self.punch_timer / self.punch_duration)
            lunge_y = int(math.sin(punch_ratio * math.pi) * -28)
            surface.blit(
                self.sprite_punch,
                (self.char_punch_pos[0] + ox, self.char_punch_pos[1] + lunge_y + oy)
            )
        else:
            bob_y = int(math.sin(self.pulse_clock * 0.65) * 4.5)
            surface.blit(
                self.sprite_idle,
                (self.char_idle_pos[0] + ox, self.char_idle_pos[1] + bob_y + oy)
            )

    def _render_hud_overlay(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        """
        Renderiza el HUD limpio con el mismo estándar visual de UninorteSprint:
        - Izquierda: Únicamente la barra de Strikes con sus 'X' en los circulitos (sin contador extra).
        - Derecha: Reloj Contador Oficial (`contador_microjuegos.png`) con dígitos dinámicos.
        """
        # 1. Barra de Strikes (Esquina superior izquierda)
        hud_x = 55 + ox
        hud_y = 35 + oy
        surface.blit(self.strike_hud_base, (hud_x, hud_y))

        for s in range(min(self.strikes, len(self.circle_rel_positions))):
            rel_cx, rel_cy = self.circle_rel_positions[s]
            cx = hud_x + int(self.hud_bar_w * rel_cx)
            cy = hud_y + int(self.hud_bar_h * rel_cy)

            x_shadow = self.font_strike_x.render("X", True, (35, 10, 15))
            x_surf = self.font_strike_x.render("X", True, (235, 45, 45))

            rx = cx - (x_surf.get_width() // 2)
            ry = cy - (x_surf.get_height() // 2)

            surface.blit(x_shadow, (rx + 2, ry + 2))
            surface.blit(x_surf, (rx, ry))

        # 2. Reloj Contador Gráfico Oficial suprimido (se utiliza la barra de tiempo inferior)

    def render_game(self, surface: pygame.Surface) -> None:
        """Renderizado completo con jerarquía de capas, ondas expansivas y HUD limpio."""
        shake_magnitude = (self.trauma ** 2) * self.max_shake_offset
        if shake_magnitude > 0.01:
            angle = random.uniform(0.0, math.pi * 2)
            ox = int(math.cos(angle) * shake_magnitude)
            oy = int(math.sin(angle) * shake_magnitude)
        else:
            ox, oy = 0, 0

        # 1. Fondo oficial
        surface.blit(self.bg_surface, (ox, oy))

        # 2. Personaje con sombra elíptica, respiración y lunge de uppercut
        self._render_player_character(surface, ox, oy)

        # 3. Retícula del "Sweet Spot" (Zona de Bateo) frente al personaje
        self._render_sweet_spot_guide(surface, ox, oy)

        # 4. Ondas de choque de impacto (Shockwave Rings)
        for sw in self.shockwaves:
            ratio = max(0.0, sw["life"] / sw["max_life"])
            alpha = int(210 * ratio)
            r = int(sw["radius"])
            if r > 4:
                sw_surf = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(sw_surf, (*sw["color"], alpha), (r + 4, r + 4), r, width=max(2, int(6 * ratio)))
                surface.blit(sw_surf, (int(sw["x"] - r - 4) + ox, int(sw["y"] - r - 4) + oy))

        # 5. Notificaciones en primer plano (con pop de escala 1.07x en el Sweet Spot)
        for notif in self.wave_queue:
            if not notif["spawned"] or notif["state"] in ("passed", "done"):
                continue

            spr = notif["sprite"]
            if notif["state"] == "hit_fly":
                rotated = pygame.transform.rotate(spr, notif["fly_rot"])
                if notif["alpha"] < 255:
                    rotated.set_alpha(int(notif["alpha"]))
                rw, rh = rotated.get_size()
                draw_x = int(notif["x"] + (notif["w"] // 2) - (rw // 2)) + ox
                draw_y = int(notif["y"] + (notif["h"] // 2) - (rh // 2)) + oy
                surface.blit(rotated, (draw_x, draw_y))
            else:
                if notif["in_sweet_spot"] and not notif["is_safe"]:
                    pop_w = int(notif["w"] * 1.07)
                    pop_h = int(notif["h"] * 1.07)
                    scaled_pop = pygame.transform.smoothscale(spr, (pop_w, pop_h))
                    draw_x = int(notif["x"] - ((pop_w - notif["w"]) // 2)) + ox
                    draw_y = int(notif["y"] - ((pop_h - notif["h"]) // 2)) + oy
                    surface.blit(scaled_pop, (draw_x, draw_y))
                else:
                    surface.blit(spr, (int(notif["x"]) + ox, int(notif["y"]) + oy))

        # 6. Partículas de impacto
        for p in self.spark_particles:
            ratio = max(0.0, p["life"] / p["max_life"])
            alpha = int(255 * ratio)
            color = (*p["color"], alpha)
            p_surf = pygame.Surface((int(p["length"] * 2), int(p["length"] * 2)), pygame.SRCALPHA)
            speed = math.hypot(p["vx"], p["vy"])
            if speed > 0:
                dx = (p["vx"] / speed) * p["length"]
                dy = (p["vy"] / speed) * p["length"]
                cx = p["length"]
                cy = p["length"]
                pygame.draw.line(p_surf, color, (cx - dx * 0.4, cy - dy * 0.4), (cx + dx * 0.6, cy + dy * 0.6), 3)
                surface.blit(p_surf, (int(p["x"] - cx) + ox, int(p["y"] - cy) + oy))

        # 7. Popups de impacto
        for pop in self.popups:
            rendered_text = self.font_juice.render(pop["text"], True, pop["color"])
            shadow = self.font_juice.render(pop["text"], True, (15, 15, 15))
            rx = int(pop["x"] - (rendered_text.get_width() // 2)) + ox
            ry = int(pop["y"]) + oy
            surface.blit(shadow, (rx + 3, ry + 3))
            surface.blit(rendered_text, (rx, ry))

        # 8. HUD Overlay Unificado (Solo Barra de Strikes + Reloj Contador Oficial)
        self._render_hud_overlay(surface, ox, oy)

        # 9. Flash perimetral en Strike
        if self.strike_flash_alpha > 0.0:
            flash_overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            flash_overlay.fill((230, 20, 20, int(self.strike_flash_alpha)))
            surface.blit(flash_overlay, (0, 0))
