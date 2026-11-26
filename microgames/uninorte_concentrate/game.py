import math
import os
import random
from typing import Optional, Callable, List, Tuple, Dict, Any
import pygame
import numpy as np
from PIL import Image

from core.microgame import BaseMicrogame
from core.camera_gestures import CameraGestureInput
from microgames.uninorte_concentrate.entities import (
    Student,
    Distraction,
    VirtualCursor,
    ProgressBar,
    ScoreManager,
)

# Caché compartida a nivel de módulo para evitar recorte/flood-fill/escalado repetido al reabrir
_SURFACE_CACHE: Dict[Tuple[Any, ...], Any] = {}


class UninorteConcentrateMicrogame(BaseMicrogame):
    CAMERA_POINTER = False  # Usa la cámara directamente
    dialogoPaloma = [
        ["¡A estudiar en la biblioteca de Uninorte!",
         "Las notificaciones de redes sociales",
         "quieren robarte la atención a toda costa."],
        ["Mueve el puntero (mouse, flechas o cámara)",
         "y haz CLIC o pulsa ESPACIO sobre las nubes",
         "para reventarlas y llenar la barra de Enfoque."],
    ]
    """
    Microjuego «¡Concéntrate, llave!» — Nivel 1: Uninorte
    - Duración: 25 segundos.
    - Mecánica: Proteger la concentración del estudiante reventando las nubes de redes sociales
      con la manita controlada por teclado (WASD/Flechas + Espacio) antes o después de que lo alcancen.
    - Condición de victoria: Alcanzar el 100% de la barra de enfoque antes de que se agoten los 25s.
      Si termina antes de los 25s, el jugador puede seguir reventando distracciones para sumar puntos extra.
    """
    ensenanzaFinal = {
        "gana": ["Terminaste porque cuidaste tu atención.",
                 "Cada vez que algo te saca de la tarea,",
                 "volver a concentrarte cuesta más de lo que crees."],
        "pierde": ["Cada notificación te sacó de la tarea,",
                   "y volver a concentrarte cuesta",
                   "más de lo que crees."],
    }

    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡CONCÉNTRATE, LLAVE!",
            time_limit=25.0,
            on_complete_callback=on_complete_callback
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("concentracionMusic.mp3", volume_scale=0.65)

    def setup_game(self) -> None:
        self.camera_input = CameraGestureInput.get_instance()
        if (
            os.environ.get("SDL_VIDEODRIVER") != "dummy"
            and self.camera_input.available
            and not self.camera_input.enabled
            and not self.camera_input.suspended
        ):
            self.camera_input.keep_alive(retry_interval=2.0)
        # 1. Fondo ilustrado de biblioteca Uninorte
        self.bg_surface = self._load_background()

        # 2. Cargar y limpiar los 3 sprites del estudiante (removiendo damero RGB si existe)
        study_1 = self._load_clean_student_sprite(
            "estudiante_concentrado_concentracion_minijuego.png", target_h=540
        )
        study_2 = self._load_clean_student_sprite(
            "estudiante_concentrado_mano_alzada_concentracion_minijuego.png", target_h=540
        )
        distracted = self._load_clean_student_sprite(
            "estudiante_desconcentrado_concentracion_minijuego.png", target_h=540
        )

        # Ubicación del estudiante sentado frente al escritorio de la biblioteca
        self.student = Student(
            center_pos=(self.screen_w * 0.50, self.screen_h * 0.63),
            study_frames=[study_1, study_2],
            distracted_frame=distracted
        )

        # 3. Extraer las 6 nubes del spritesheet 3x2
        self.cloud_sprites = self._extract_social_cloud_sprites(target_h=142)
        self.clouds: List[Distraction] = []

        # 4. Barra de progreso ("Enfoque") en la parte superior
        bar_frame = self._load_focus_bar_frame(target_w=760)
        self.progress_bar = ProgressBar(bar_frame, center_top_pos=(self.screen_w // 2, 18))

        # 5. Puntero de Valdiri o lapicero oficial para los demás personajes
        pencil_sprite = (
            self._load_character_cursor_sprite(target_h=118)
            if self.character_id == "valdiri"
            else self._load_pencil_cursor_sprite(target_w=84)
        )
        self.cursor = VirtualCursor(self.screen_w, self.screen_h, pencil_surface=pencil_sprite)
        if self.character_id == "valdiri":
            # La punta del índice ocupa otra posición que la punta del lapicero.
            self.cursor.tip_offset_x = int(pencil_sprite.get_width() * (0.44 - 0.5))
            self.cursor.tip_offset_y = int(pencil_sprite.get_height() * (0.23 - 0.5))

        # 6. Gestor de puntuación y rachas (interno)
        self.score_manager = ScoreManager()

        # 7. Reloj contador visual en la esquina superior derecha
        self.spr_counter = self._load_optional_ui("contador_microjuegos.png", target_h=92)
        self.font_clock = pygame.font.SysFont("Arial Black, Impact, sans-serif", 30)
        self.font_hint = pygame.font.SysFont("Arial, sans-serif", 18, bold=True)

        # 8. Control de oleadas (menos nubes en pantalla, pero mayor velocidad de aproximación)
        self.elapsed_play_time: float = 0.0
        self.spawn_timer: float = 0.55
        self.watercolor_particles: List[Dict[str, Any]] = []
        self.screen_trauma: float = 0.0
        self._attach_sfx_cooldown: float = 0.0
        self._gesture_pos_freeze_timer: float = 0.0
        self._frozen_cam_pos: Optional[Tuple[float, float]] = None
        self._cursor_trail: List[Tuple[float, float]] = []
        self._pinch_ripples: List[Dict[str, float]] = []

    def _load_pencil_cursor_sprite(self, target_w: int = 84) -> pygame.Surface:
        """Carga y procesa el sprite oficial del Lapicero de BarranquillaWare ('puntero_lapiz.png')."""
        cache_key = ("pencil", target_w)
        cached = _SURFACE_CACHE.get(cache_key)
        if cached is not None:
            return cached
        try:
            raw = self.assets.load_surface("puntero_lapiz.png", has_alpha=True)
            scale = target_w / float(max(1, raw.get_width()))
            target_h = int(raw.get_height() * scale)
            res = pygame.transform.smoothscale(raw, (target_w, target_h))
            _SURFACE_CACHE[cache_key] = res
            return res
        except Exception:
            fb = pygame.Surface((target_w, target_w), pygame.SRCALPHA)
            pygame.draw.polygon(fb, (255, 215, 60), [(0, 0), (target_w, target_w // 2), (target_w // 2, target_w)])
            return fb

    def _load_character_cursor_sprite(self, target_h: int = 118) -> pygame.Surface:
        """
        Extrae el puntero temático desde `spritesheet_punteros_concentracion_microjuego.png`:
        1. Westcol (Traje de gala con moño y collar)
        2. Char (Gorra Juniorista / Barranquilla)
        3. Katherine (Carnet Uninorte y libro)
        4. Valdiri (Pulsera dorada y celular)
        """
        char_order = ["westcol", "char", "katherine", "valdiri"]
        idx = 0
        cid = getattr(self, "character_id", "westcol").lower()
        for i, name in enumerate(char_order):
            if name in cid:
                idx = i
                break

        cache_key = ("char_cursor", idx, target_h)
        cached = _SURFACE_CACHE.get(cache_key)
        if cached is not None:
            return cached

        try:
            if cid == "valdiri":
                sub = self.assets.load_surface(
                    "valdiri_puntero_concentracion_microjuego.png", has_alpha=True
                ).copy()
            else:
                sheet = self.assets.load_surface(
                    "spritesheet_punteros_concentracion_microjuego.png", has_alpha=True
                )
                sw, sh = sheet.get_size()
                cw = sw // 4
                cell_rect = pygame.Rect(idx * cw, 0, cw, sh)
                sub = sheet.subsurface(cell_rect).copy()
            bbox = sub.get_bounding_rect(min_alpha=20)
            if bbox.width > 0 and bbox.height > 0:
                sub = sub.subsurface(bbox).copy()
            scale = target_h / float(max(1, sub.get_height()))
            tw = int(sub.get_width() * scale)
            res = pygame.transform.smoothscale(sub, (tw, target_h))
            _SURFACE_CACHE[cache_key] = res
            return res
        except Exception:
            # Fallback limpio
            fb = pygame.Surface((target_h, target_h), pygame.SRCALPHA)
            pygame.draw.circle(fb, (255, 220, 180), (target_h // 2, target_h // 2), target_h // 3)
            return fb

    def _load_background(self) -> pygame.Surface:
        cache_key = ("bg", self.screen_w, self.screen_h)
        cached = _SURFACE_CACHE.get(cache_key)
        if cached is not None:
            return cached
        try:
            raw = self.assets.load_surface("fondo_concentracion_microjuego.png", has_alpha=False)
            res = pygame.transform.smoothscale(raw, (self.screen_w, self.screen_h))
            _SURFACE_CACHE[cache_key] = res
            return res
        except Exception:
            surf = pygame.Surface((self.screen_w, self.screen_h))
            surf.fill((245, 225, 200))
            return surf

    @staticmethod
    def _flood_fill_border_bg_mask(bg: np.ndarray) -> np.ndarray:
        """
        Propagación vectorizada en NumPy por segmentos horizontales y verticales desde los 4 bordes.
        Produce la máscara exacta de flood-fill 4-conectada sin bucles píxel-a-píxel en Python.
        """
        ch, cw = bg.shape
        vis = np.zeros((ch, cw), dtype=bool)
        vis[0, :] = bg[0, :]
        vis[-1, :] = bg[-1, :]
        vis[:, 0] = bg[:, 0]
        vis[:, -1] = bg[:, -1]

        h_starts = bg.copy()
        h_starts[:, 1:] &= ~bg[:, :-1]
        h_ids = np.cumsum(h_starts.ravel(), dtype=np.int32).reshape(ch, cw)
        h_ids[~bg] = 0
        n_h = int(h_ids.max()) + 1

        v_starts = bg.copy()
        v_starts[1:, :] &= ~bg[:-1, :]
        v_ids = np.cumsum(v_starts.T.ravel(), dtype=np.int32).reshape(cw, ch).T
        v_ids[~bg] = 0
        n_v = int(v_ids.max()) + 1

        h_hit = np.zeros(n_h, dtype=bool)
        v_hit = np.zeros(n_v, dtype=bool)
        frontier = vis.copy()
        while frontier.any():
            h_hit[h_ids[frontier]] = True
            h_hit[0] = False
            vis2 = vis | h_hit[h_ids]
            new_h = vis2 & ~vis
            vis = vis2
            frontier2 = frontier | new_h
            if not frontier2.any():
                break
            v_hit[v_ids[frontier2]] = True
            v_hit[0] = False
            vis3 = vis | v_hit[v_ids]
            frontier = vis3 & ~vis
            vis = vis3
        return vis

    def _load_clean_student_sprite(self, filename: str, target_h: int) -> pygame.Surface:
        """
        Carga el sprite del estudiante, recorta primero crop_box, elimina automáticamente cualquier
        fondo damero blanco/gris en archivos RGB mediante flood-fill vectorizado con NumPy desde
        los bordes, escala preservando proporción y cachea el resultado en memoria.
        """
        cache_key = ("student", filename, target_h)
        cached = _SURFACE_CACHE.get(cache_key)
        if cached is not None:
            return cached
        try:
            path = self.assets._resolve_path(filename)
            pil_img = Image.open(path)
            # Recorte consistente basado en los límites de tinta oscura antes de procesar píxeles
            x0 = min(140, pil_img.width)
            y0 = min(5, pil_img.height)
            x1 = min(1270, pil_img.width)
            y1 = min(1112, pil_img.height)
            if x1 > x0 and y1 > y0:
                pil_img = pil_img.crop((x0, y0, x1, y1))
            cropped_arr = np.array(pil_img.convert("RGBA"))
            ch, cw, _ = cropped_arr.shape

            # Si menos del 5% de los píxeles son transparentes, tiene fondo damero cocido
            if (cropped_arr[:, :, 3] < 15).sum() < (ch * cw * 0.05):
                rgb = cropped_arr[:, :, :3]
                sat = rgb.max(axis=2) - rgb.min(axis=2)
                lum = rgb.min(axis=2)

                # El damero exterior tiene saturación casi nula (<= 12) y alta luminosidad (>= 210),
                # mientras que el personaje está rodeado por un borde oscuro continuo.
                is_bg = (sat <= 12) & (lum >= 210)
                visited = self._flood_fill_border_bg_mask(is_bg)
                cropped_arr[visited, 3] = 0

            surf = pygame.image.frombuffer(cropped_arr.tobytes(), (cw, ch), "RGBA").convert_alpha()

            scale = target_h / float(ch)
            target_w = int(cw * scale)
            res = pygame.transform.smoothscale(surf, (target_w, target_h))
            _SURFACE_CACHE[cache_key] = res
            return res
        except Exception:
            fallback = pygame.Surface((int(target_h * 1.05), target_h), pygame.SRCALPHA)
            pygame.draw.rect(fallback, (74, 105, 132), fallback.get_rect(), border_radius=24)
            return fallback

    def _extract_social_cloud_sprites(self, target_h: int = 142) -> List[pygame.Surface]:
        """
        Extrae las 6 nubes de redes sociales organizadas en cuadrícula 3x2:
        1. Instagram, 2. TikTok, 3. YouTube, 4. X, 5. Facebook, 6. WhatsApp.
        """
        cache_key = ("clouds", target_h)
        cached = _SURFACE_CACHE.get(cache_key)
        if cached is not None:
            return list(cached)

        sprites: List[pygame.Surface] = []
        try:
            sheet = self.assets.load_surface(
                "spritesheet_popups_redes_sociales_concentracion_microjuego.png", has_alpha=True
            )
            sw, sh = sheet.get_size()
            # Puntos de corte exactos verificados en los valles del spritesheet 1536x1024
            x_cuts = [0, 522, 1014, sw]
            y_cuts = [0, 505, sh]

            for row in range(2):
                for col in range(3):
                    rx = x_cuts[col]
                    ry = y_cuts[row]
                    rw = x_cuts[col + 1] - rx
                    rh = y_cuts[row + 1] - ry
                    sub = sheet.subsurface(pygame.Rect(rx, ry, rw, rh)).copy()
                    bbox = sub.get_bounding_rect(min_alpha=25)
                    if bbox.width > 0 and bbox.height > 0:
                        sub = sub.subsurface(bbox).copy()
                    scale = target_h / float(max(1, sub.get_height()))
                    tw = int(sub.get_width() * scale)
                    sprites.append(pygame.transform.smoothscale(sub, (tw, target_h)))
            _SURFACE_CACHE[cache_key] = tuple(sprites)
        except Exception:
            for col_rgb in Distraction.NETWORK_COLORS:
                fb = pygame.Surface((160, target_h), pygame.SRCALPHA)
                pygame.draw.ellipse(fb, col_rgb, fb.get_rect())
                sprites.append(fb)
        return sprites

    def _load_focus_bar_frame(self, target_w: int = 760) -> pygame.Surface:
        cache_key = ("focus_bar", target_w)
        cached = _SURFACE_CACHE.get(cache_key)
        if cached is not None:
            return cached
        try:
            cropped = self.assets.load_cropped_surface(
                "barra_enfoque_concentracion_microjuego.png", alpha_threshold=20
            )
            orig_w, orig_h = cropped.get_size()
            scale = target_w / float(max(1, orig_w))
            target_h = int(orig_h * scale)
            res = pygame.transform.smoothscale(cropped, (target_w, target_h))
            _SURFACE_CACHE[cache_key] = res
            return res
        except Exception:
            fb = pygame.Surface((target_w, 160), pygame.SRCALPHA)
            pygame.draw.rect(fb, (90, 50, 75), fb.get_rect(), width=6, border_radius=24)
            return fb

    def _load_optional_ui(self, filename: str, target_h: int) -> Optional[pygame.Surface]:
        cache_key = ("optional_ui", filename, target_h)
        if cache_key in _SURFACE_CACHE:
            return _SURFACE_CACHE[cache_key]
        try:
            surf = self.assets.load_cropped_surface(filename, alpha_threshold=15)
            scale = target_h / float(max(1, surf.get_height()))
            tw = int(surf.get_width() * scale)
            res = pygame.transform.smoothscale(surf, (tw, target_h))
            _SURFACE_CACHE[cache_key] = res
            return res
        except Exception:
            return None

    def _spawn_cloud(self) -> None:
        """Genera una nube de distracción rápida hacia el estudiante."""
        # Capacidad aumentada (+70% de densidad en pantalla: hasta 5 nubes simultáneas)
        active_unattached = [c for c in self.clouds if c.state == Distraction.STATE_APPROACHING]
        if len(active_unattached) >= 5:
            return

        net_idx = random.randrange(len(self.cloud_sprites))
        sprite = self.cloud_sprites[net_idx]

        edge = random.choice(["left", "right", "top_left", "top_right"])
        if edge == "left":
            sx = -80.0
            sy = random.uniform(200.0, self.screen_h - 260.0)
        elif edge == "right":
            sx = float(self.screen_w) + 80.0
            sy = random.uniform(200.0, self.screen_h - 260.0)
        elif edge == "top_left":
            sx = random.uniform(100.0, self.screen_w * 0.35)
            sy = -70.0
        else:
            sx = random.uniform(self.screen_w * 0.65, self.screen_w - 100.0)
            sy = -70.0

        # Velocidad incrementada significativamente (desafío de reflejos rápidos)
        difficulty_ratio = min(1.0, self.elapsed_play_time / 20.0)
        base_speed = random.uniform(340.0, 440.0) + difficulty_ratio * 160.0

        target_x = self.student.base_x + random.uniform(-40.0, 40.0)
        target_y = self.student.base_y - random.uniform(20.0, 80.0)

        cloud = Distraction(
            network_idx=net_idx,
            sprite=sprite,
            start_pos=(sx, sy),
            target_pos=(target_x, target_y),
            speed=base_speed
        )
        self.clouds.append(cloud)

    def _spawn_watercolor_burst(self, pos: Tuple[float, float], base_color: Tuple[int, int, int], count: int = 16) -> None:
        """Crea una explosión de gotas y manchas suaves de acuarela al destruir una nube."""
        r, g, b = base_color
        pastel_variants = [
            (min(255, r + 30), min(255, g + 30), min(255, b + 30)),
            (max(80, r - 20), max(80, g - 20), max(80, b - 20)),
            (255, 245, 220)
        ]
        for _ in range(count):
            angle = random.uniform(0.0, math.pi * 2.0)
            speed = random.uniform(90.0, 340.0)
            self.watercolor_particles.append({
                "x": pos[0] + random.uniform(-12.0, 12.0),
                "y": pos[1] + random.uniform(-12.0, 12.0),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed - 40.0,
                "radius": random.uniform(8.0, 22.0),
                "color": random.choice(pastel_variants),
                "alpha": 225.0,
                "decay": random.uniform(320.0, 520.0)
            })

    def _trigger_pop_action(self, extra_radius: float = 0.0) -> None:
        """Ejecuta el reventón del cursor cuando el jugador presiona Espacio o hace gesto."""
        self.cursor.trigger_pop_Wave()
        hit_clouds = self.cursor.get_pop_targets(self.clouds, extra_radius=extra_radius)

        if hit_clouds:
            for c in hit_clouds:
                if c.state == Distraction.STATE_ATTACHED:
                    self.student.detach_cloud(c)
                c.pop()
                self._spawn_watercolor_burst((c.x, c.y), c.theme_color, count=18)

            self.score_manager.register_pop(len(hit_clouds), (self.cursor.x, self.cursor.y))
            self.screen_trauma = min(0.45, self.screen_trauma + 0.18)
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()
        else:
            # Golpe en vacío
            self.score_manager.register_pop(0, (self.cursor.x, self.cursor.y))
            if hasattr(self.audio, "play_miss"):
                self.audio.play_miss()

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            # Sincroniza la posición del lápiz con el cursor del mouse, alineando la mina exactamente con el puntero
            self.cursor.x = float(event.pos[0] - self.cursor.tip_offset_x)
            self.cursor.y = float(event.pos[1] - self.cursor.tip_offset_y)
            self.cursor.vx = 0.0
            self.cursor.vy = 0.0

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Clic izquierdo para pinchar y reventar distracciones
            self.cursor.x = float(event.pos[0] - self.cursor.tip_offset_x)
            self.cursor.y = float(event.pos[1] - self.cursor.tip_offset_y)
            self._trigger_pop_action()

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._trigger_pop_action()

        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0:  # Botón A en gamepad
                self._trigger_pop_action()

    def update(self, dt: float) -> None:
        """
        Sobreescribe el ciclo de actualización para que el juego dure exactamente los 25 segundos
        completos, evaluando victoria o derrota según si la tarea llegó al 100%.
        """
        if self.paloma_intro is not None and self.paloma_intro.active:
            super().update(dt)
            return
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
                self.finish_game(won=self.progress_bar.completed)

        elif self.phase == self.PHASE_OUTRO:
            self.update_outro(dt)

    def update_game(self, dt: float) -> None:
        if getattr(self, "camera_input", None) and self.camera_input.enabled and self.camera_input.is_hand_present():
            # Acción de clic cinético: pellizco de dedos o puño cerrado (apretar)
            pinch_hit = self.camera_input.consume_click()
            fist_hit = hasattr(self.camera_input, "consume_fist") and self.camera_input.consume_fist()
            gesture_active = (
                getattr(self.camera_input, "is_pinching", lambda: False)()
                or getattr(self.camera_input, "is_fist", lambda: False)()
            )

            # Control óptico de MediaPipe: mueve el lapicero en pantalla independiente del ratón del sistema
            hand_x, hand_y = self.camera_input.get_position()
            target_x = max(48.0, min(self.screen_w - 48.0, hand_x * self.screen_w))
            target_y = max(48.0, min(self.screen_h - 48.0, hand_y * self.screen_h))

            # Si se acaba de disparar el gesto de pellizco o puño, congelar temporalmente la posición
            # para amortiguar el micro-desplazamiento involuntario de la mano/dedo al contraerse.
            if pinch_hit or fist_hit:
                self._gesture_pos_freeze_timer = 0.22
                self._frozen_cam_pos = (self.cursor.x, self.cursor.y)
                self._pinch_ripples.append({"x": self.cursor.x, "y": self.cursor.y, "r": 10.0, "alpha": 220.0})
                # Radio de tolerancia moderado (+26px) para comodidad sin regalar clics lejanos
                self._trigger_pop_action(extra_radius=26.0)

            if self._gesture_pos_freeze_timer > 0.0:
                self._gesture_pos_freeze_timer -= dt
                if self._frozen_cam_pos is not None:
                    target_x, target_y = self._frozen_cam_pos
            elif gesture_active:
                # Si la mano sigue contraída/sostenida, reducir la velocidad de movimiento para estabilizar
                smooth = min(1.0, dt * 6.0)
                self.cursor.x += (target_x - self.cursor.x) * smooth
                self.cursor.y += (target_y - self.cursor.y) * smooth
                self.cursor.vx = 0.0
                self.cursor.vy = 0.0
            else:
                self._frozen_cam_pos = None
                # Zona muerta de 6px para eliminar micro-temblores de la cámara al apuntar
                dx = target_x - self.cursor.x
                dy = target_y - self.cursor.y
                if (dx * dx + dy * dy) >= 36.0:
                    smooth = min(1.0, dt * 24.0)
                    self.cursor.x += dx * smooth
                    self.cursor.y += dy * smooth
                self.cursor.vx = 0.0
                self.cursor.vy = 0.0
        self.elapsed_play_time += dt

        # 1. Spawner de distracciones (+70% de cadencia y densidad)
        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0:
            self._spawn_cloud()
            difficulty = min(1.0, self.elapsed_play_time / 22.0)
            # Intervalos reducidos un 40% (~1.10s al inicio bajando a ~0.55s) para +70% de nubes totales
            self.spawn_timer = max(0.55, 1.10 - difficulty * 0.55) + random.uniform(-0.10, 0.12)

        # 2. Actualizar nubes y comprobar si alguna acaba de distraer al estudiante
        prev_attached = len(self.student.attached_clouds)
        for c in self.clouds:
            c.update(dt, self.student)
        self.clouds = [c for c in self.clouds if c.state != Distraction.STATE_DEAD]

        if self._attach_sfx_cooldown > 0.0:
            self._attach_sfx_cooldown = max(0.0, self._attach_sfx_cooldown - dt)

        if len(self.student.attached_clouds) > prev_attached:
            self.screen_trauma = min(0.65, self.screen_trauma + 0.32)
            self.mostrarEnsenanza()
            if self._attach_sfx_cooldown <= 0.0:
                if hasattr(self.audio, "play_miss"):
                    self.audio.play_miss()
                self._attach_sfx_cooldown = 0.35

        # 3. Actualizar estudiante y barra de progreso (nunca retrocede)
        self.student.update(dt)
        # Si la cámara está activa, llenar la barra un 15% más rápido para compensar la motricidad gestual
        cam_active = bool(
            getattr(self, "camera_input", None)
            and self.camera_input.enabled
            and self.camera_input.is_hand_present()
        )
        fill_multiplier = 1.15 if cam_active else 1.0
        just_finished_task = self.progress_bar.update(dt, self.student.is_studying, rate_multiplier=fill_multiplier)
        if just_finished_task:
            self.student.trigger_celebration()
            self.score_manager.award_task_completion_bonus((self.student.base_x, self.student.base_y - 180.0))
            self._spawn_watercolor_burst(
                (self.student.base_x, self.student.base_y - 120.0), (120, 235, 155), count=32
            )
            # Victoria instantánea al tocar el 100% de la tarea
            self.finish_game(won=True)

        # 4. Actualizar cursor virtual con asistencia magnética sutil
        self.cursor.update(dt, self.clouds)
        self._cursor_trail.append((self.cursor.x, self.cursor.y))
        if len(self._cursor_trail) > 6:
            self._cursor_trail.pop(0)
        for rp in self._pinch_ripples:
            rp["r"] += 165.0 * dt
            rp["alpha"] -= 520.0 * dt
        self._pinch_ripples = [rp for rp in self._pinch_ripples if rp["alpha"] > 8.0]

        # 5. Actualizar partículas de acuarela y puntuación
        for p in self.watercolor_particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= max(0.0, 1.0 - 4.0 * dt)
            p["vy"] += 180.0 * dt  # Gravedad suave de gota
            p["radius"] += 12.0 * dt
            p["alpha"] -= p["decay"] * dt
        self.watercolor_particles = [p for p in self.watercolor_particles if p["alpha"] > 5.0]

        self.score_manager.update(dt)

        if self.screen_trauma > 0.0:
            self.screen_trauma = max(0.0, self.screen_trauma - dt * 1.8)

    def exit(self) -> None:
        # La cámara pertenece al motor y se comparte con el resto de escenas.
        super().exit()

    def render_game(self, surface: pygame.Surface) -> None:
        # Screenshake no lineal (cuadrático)
        shake_amt = (self.screen_trauma ** 2) * 16.0
        ox = int(random.uniform(-shake_amt, shake_amt)) if shake_amt > 0.5 else 0
        oy = int(random.uniform(-shake_amt, shake_amt)) if shake_amt > 0.5 else 0

        # 1. Fondo de biblioteca Uninorte
        surface.blit(self.bg_surface, (ox, oy))

        # 2. Estudiante en el escritorio central
        self.student.render(surface, global_offset=(ox, oy))

        # 3. Nubes de distracción
        for c in self.clouds:
            c.render(surface, global_offset=(ox, oy))

        # 4. Explosiones de partículas de acuarela
        for p in self.watercolor_particles:
            rad = int(p["radius"])
            alpha = int(max(0.0, min(255.0, p["alpha"])))
            p_surf = pygame.Surface((rad * 2 + 4, rad * 2 + 4), pygame.SRCALPHA)
            r, g, b = p["color"]
            pygame.draw.circle(p_surf, (r, g, b, alpha), (rad + 2, rad + 2), rad)
            surface.blit(p_surf, (int(p["x"]) - rad + ox, int(p["y"]) - rad + oy))

        # 5. Barra superior de progreso ("Enfoque")
        self.progress_bar.render(surface, self.student.is_studying)

        # 6. Puntuación y rachas (esquina superior izquierda)
        self.score_manager.render(surface)

        # 7. Temporizador de 25 segundos (esquina superior derecha)
        self._render_top_right_timer(surface)

        # 8. Leyenda discreta de controles en la parte inferior
        cam_active = getattr(self, "camera_input", None) and self.camera_input.enabled and self.camera_input.is_hand_present()
        if cam_active:
            hint_txt = "🖐️ CÁMARA MEDIAPIPE: Mover dedo y Pellizcar/Cerrar puño para Pinchar"
        else:
            hint_txt = "MOUSE / CLICK: Apuntar y Pinchar   |   WASD / FLECHAS + ESPACIO"
        h_surf = self.font_hint.render(hint_txt, True, (255, 248, 235))
        h_bg = self.font_hint.render(hint_txt, True, (45, 30, 25))
        hx = (self.screen_w - h_surf.get_width()) // 2
        hy = self.screen_h - 86
        if getattr(self, "mostrarLeyendaControles", False):
            surface.blit(h_bg, (hx + 2, hy + 2))
            surface.blit(h_surf, (hx, hy))

        self.dibujarEnsenanza(surface)

        # 9. Estela de movimiento, ondas de pellizco y cursor personalizado (siempre al frente)
        for i, (tx, ty) in enumerate(self._cursor_trail[:-1]):
            alpha = int(28 + i * 18)
            rad = 4 + i
            dot = pygame.Surface((rad * 2 + 2, rad * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(dot, (255, 232, 140, alpha), (rad + 1, rad + 1), rad)
            surface.blit(dot, (int(tx) - rad - 1, int(ty) - rad - 1))
        for rp in self._pinch_ripples:
            rr = max(2, int(rp["r"]))
            rs = pygame.Surface((rr * 2 + 4, rr * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(rs, (120, 235, 165, max(0, min(255, int(rp["alpha"])))), (rr + 2, rr + 2), rr, width=3)
            surface.blit(rs, (int(rp["x"]) - rr - 2, int(rp["y"]) - rr - 2))
        has_target = len(self.cursor.get_pop_targets(self.clouds)) > 0
        self.cursor.render(surface, has_target_in_range=has_target, is_cam_controlled=bool(cam_active))

    def _render_top_right_timer(self, surface: pygame.Surface) -> None:
        return
        secs = max(0, int(math.ceil(self.time_left)))
        tx = self.screen_w - 220
        ty = 28

        if self.spr_counter is not None:
            surface.blit(self.spr_counter, (tx, ty))
            num_col = (225, 55, 55) if secs <= 5 else (65, 40, 35)
            t_surf = self.font_clock.render(f"{secs:02d}s", True, num_col)
            rect = t_surf.get_rect(
                center=(tx + int(self.spr_counter.get_width() * 0.60), ty + int(self.spr_counter.get_height() * 0.54))
            )
            surface.blit(t_surf, rect)
        else:
            pill = pygame.Rect(tx, ty, 175, 72)
            pygame.draw.rect(surface, (255, 248, 235), pill, border_radius=18)
            pygame.draw.rect(surface, (95, 65, 55), pill, width=4, border_radius=18)
            num_col = (225, 55, 55) if secs <= 5 else (65, 40, 35)
            t_surf = self.font_clock.render(f"⏱ {secs:02d}s", True, num_col)
            surface.blit(t_surf, t_surf.get_rect(center=pill.center))

    def mostrarEnsenanza(self) -> None:
        if not hasattr(self, "ensenanzas"):
            self.ensenanzas = [
                ["Las notificaciones están hechas para atraparte:", "tu atención es lo que las apps se quieren ganar."],
                ["Hacer mil cosas a la vez no es rendir más:", "es hacerlas todas a medias."],
                ["Silenciar el celular un rato", "es un regalo para tu cabeza."],
                ["Tu atención vale oro:", "no se la regales a cualquier notificación."],
            ]
            self.cualEnsenanza = -1
            self.inicioEnsenanza = -100.0
        if self.elapsed_play_time - self.inicioEnsenanza < 6.0:
            return
        self.cualEnsenanza = (self.cualEnsenanza + 1) % len(self.ensenanzas)
        self.inicioEnsenanza = self.elapsed_play_time

    def dibujarEnsenanza(self, surface: pygame.Surface) -> None:
        if not hasattr(self, "ensenanzas") or self.cualEnsenanza < 0:
            return
        tiempo = self.elapsed_play_time - self.inicioEnsenanza
        if tiempo > 3.5:
            return
        visible = min(1.0, tiempo / 0.3, (3.5 - tiempo) / 0.5)
        if getattr(self, "fuenteEnsenanza", None) is None:
            self.fuenteEnsenanza = self.assets.cargarFuenteCuento(40)
        arriba = self.progress_bar.rect.bottom + 34
        for i, linea in enumerate(self.ensenanzas[self.cualEnsenanza]):
            texto = self.textoConBorde(self.fuenteEnsenanza, linea, (255, 247, 230), (60, 44, 36), 3)
            texto.set_alpha(int(255 * visible))
            surface.blit(texto, texto.get_rect(center=(self.screen_w // 2, arriba + i * 52)))

    def get_result_data(self) -> Dict[str, Any]:
        """Devuelve el contrato de salida para el sistema de niveles de BarranquillaWare."""
        return {
            "won": self.is_won,
            "score": self.score_manager.score,
            "max_streak": self.score_manager.max_streak,
            "popped_distractions": self.score_manager.popped_count,
            "task_progress": self.progress_bar.progress
        }
