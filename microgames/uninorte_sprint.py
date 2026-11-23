import math
import random
from typing import Optional, Callable, List, Tuple, Dict, Any
import pygame
import numpy as np
from PIL import Image

from core.microgame import BaseMicrogame
from core.camera_gestures import CameraGestureInput

# Caché compartida a nivel de módulo para reutilizar spritesheets recortados, fondos y audios .ogg
_SURFACE_CACHE: Dict[Tuple[Any, ...], Any] = {}
_SOUND_CACHE: Dict[Tuple[Any, ...], List[pygame.mixer.Sound]] = {}

class CharacterModel:
    """
    Modelo de personaje con sus 2 frames de animación de caminata:
    - frame 0: Piernas cerradas (fila superior del sheet)
    - frame 1: Piernas abiertas (fila inferior del sheet)
    - native_direction: 1 para Sheet 1 (caminan a la derecha), -1 para Sheet 2 (caminan a la izquierda).
      Sin flip artificial.
    """
    def __init__(
        self,
        frames: List[pygame.Surface],
        native_direction: int
    ) -> None:
        self.frames = frames
        self.native_direction = native_direction


class ZombieNPC:
    """
    Estudiante distraído mirando el celular (Obstáculo FOMO).
    - Usa su spritesheet nativo según la dirección de su carril (cero flip).
    - Desincronización profunda en fase inicial y cadencia de pasos.
    """
    def __init__(
        self,
        x: float,
        world_y: float,
        speed: float,
        direction: int,  # 1 = hacia la derecha (Sheet 1), -1 = hacia la izquierda (Sheet 2)
        model: CharacterModel,
        icon_sprite: Optional[pygame.Surface],
        lane_idx: int,
        phase_offset: float = 0.0
    ) -> None:
        self.x = x
        self.world_y = world_y
        self.speed = speed
        self.direction = direction
        self.lane_idx = lane_idx
        self.icon_sprite = icon_sprite

        # Desincronización explícita de fase y velocidad de caminata
        self.anim_timer = phase_offset + random.uniform(0.0, 2.0)
        self.anim_speed = random.uniform(3.2, 5.8)  # Rango amplio para que nunca vayan al unísono
        self.current_frame_idx = int(self.anim_timer) % len(model.frames)
        self.walk_bob = phase_offset * math.pi + random.uniform(0.0, math.pi * 2)

        # Usar los frames puros tal cual vienen en su spritesheet (sin flip)
        self.frames: List[pygame.Surface] = list(model.frames)
        self.width = self.frames[0].get_width()
        self.height = self.frames[0].get_height()

    def update(self, dt: float, screen_w: int) -> None:
        # Movimiento continuo sin pausas que rompan la cadencia
        self.x += self.speed * self.direction * dt
        self.walk_bob += dt * 8.0

        # Animación de pasos alternados
        self.anim_timer += dt * self.anim_speed
        self.current_frame_idx = int(self.anim_timer) % len(self.frames)

        # Recirculación infinita y homogénea por los márgenes
        margin = 220
        span = screen_w + margin * 2
        if self.direction > 0 and self.x > screen_w + margin:
            self.x -= span
        elif self.direction < 0 and self.x < -margin:
            self.x += span

    def get_current_sprite(self) -> pygame.Surface:
        return self.frames[self.current_frame_idx]

    def get_hitbox(self) -> pygame.Rect:
        # Hitbox centrada en los pies/cadera para evitar castigos injustos en la cabeza
        hw = int(self.width * 0.44)
        hh = int(self.height * 0.46)
        return pygame.Rect(
            int(self.x + (self.width - hw) / 2),
            int(self.world_y + (self.height - hh) - 6),
            hw,
            hh
        )


class UninorteSprintMicrogame(BaseMicrogame):
    """
    Microjuego 1: 'Carrera al Salón A-203' (Campus Uninorte).
    - Duración: 10 Segundos exactos.
    - Mecánica: Solo salto HACIA ADELANTE (Timing puro) con scroll vertical de cámara hacia el salón.
    - Controles: ESPACIO, FLECHA ARRIBA, W o Click izquierdo.
    - Game Feel: Screenshake no lineal cuadrático, hit-stop, partículas elásticas de pisada y animación natural.
    """
    ensenanzaFinal = {
        "gana": ["Llegaste a tiempo porque tus ojos",
                 "iban en el camino y no en la pantalla.",
                 "Ningún mensaje es más importante que tus responsabilidades."],
        "pierde": ["Caminar mirando el celular es como",
                   "caminar con los ojos cerrados:",
                   "chocas, te pierdes y llegas tarde."],
    }

    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡ESQUIVA LOS CELULARES!",
            time_limit=20.0,
            on_complete_callback=on_complete_callback
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("contraRelojMusic.mp3")

    def setup_game(self) -> None:
        self._last_walk_finger: Optional[int] = None
        self._walk_finger_idle: float = 0.0
        self._walk_step_buffer: float = 0.0
        self._walk_step_flash: float = 0.0
        self._walk_feedback_font = self.assets.cargarFuenteCuento(24)
        self.camera_input = CameraGestureInput.get_instance()
        if not self.camera_input.enabled:
            self.camera_input.start()
        # 1. Configuración de Carriles y Mundo Vertical (2 Tramos de 1920x1080 = 2160 px totales)
        # Carril 0: Inicio en la parte baja del Tramo 1 (Entrada Campus Uninorte)
        # Carriles 1 a 12: 12 carriles de tráfico peatonal rítmico
        # Carril 13: Meta frente al Salón A-203 en la parte superior del Tramo 2
        self.lane_height = 135
        self.total_lanes = 13
        self.player_lane = 0
        self.max_lane = self.total_lanes

        # Altura exacta equivalente a 2 pantallas apiladas verticalmente
        self.world_height = self.screen_h * 2
        self.player_x = self.screen_w // 2

        self.player_world_y = self._lane_to_world_y(self.player_lane)
        self.player_target_world_y = self.player_world_y
        self.player_visual_world_y = self.player_world_y

        # Dinámica de salto del jugador (Con bloqueo en el aire y recuperación de aterrizaje)
        self.is_jumping = False
        self.jump_progress = 0.0
        self.jump_duration = 0.24   # Duración real del salto en el aire (impide teletransportarse)
        self.jump_cooldown = 0.0    # Pausa de asentamiento al tocar el suelo antes del siguiente salto
        self.jump_recovery = 0.14   # 0.24s salto + 0.14s apoyo = mínimo 0.38s por paso (~5.0s mínimo sin parar)
        self.jump_height = 34.0
        self.jump_start_world_y = self.player_world_y

        # Cámara vertical suave (Lerp)
        self.camera_y = float(self.world_height - self.screen_h)
        self.camera_target_y = self.camera_y

        # Sistema de Game Feel (Juice)
        self.trauma = 0.0          # Decrece cuadráticamente para screenshake orgánico
        self.freeze_frames = 0     # Hit-stop frames al colisionar
        self.stun_timer = 0.0      # Aturdimiento del jugador
        self.step_particles: List[dict] = []

        # 2. Cargar Fondos Modulares si existen (o usar Placeholder estructural)
        self.bg_full, self.bg_tramo_1, self.bg_tramo_2 = self._load_background_chunks()

        # 3. Cargar Spritesheets de NPCs con Modelos de 2 Frames
        self.character_models = self._extract_character_models()
        self.icon_sprites = self._extract_icon_sprites()
        self.player_sprite = self._load_player_chibi()

        # 4. Población Equilibrada de Zombies en los 12 Carriles
        self.zombies: List[ZombieNPC] = []
        self._spawn_equilibrated_zombies()

        # 5. Elementos de UI y Fuentes
        self.spr_counter = self._load_optional_ui("contador_microjuegos.png", target_h=96)
        self.spr_paloma = self._load_optional_ui("paloma_dialog.png", target_h=190)
        self.spr_bubble = self._load_optional_ui("text_dialog.png", target_h=110)

        # 6. Voces y Efectos de Choque en el Pasillo (Game Feel / Identidad Caribeña)
        self.hit_sounds: List[pygame.mixer.Sound] = []
        self._load_pasillo_sounds()

        self.font_door = pygame.font.SysFont("Arial Black, Impact, sans-serif", 22)
        self.font_timer = pygame.font.SysFont("Arial Black, Impact, sans-serif", 32)
        self.font_dialog = pygame.font.SysFont("Arial, sans-serif", 17, bold=True)
        self.font_badge = pygame.font.SysFont("Consolas, monospace", 15, bold=True)
        self.font_prompt = pygame.font.SysFont("Arial Black, Impact, sans-serif", 26)

        # Puerta del Salón
        self.door_progress = 0.0

        self.iniciarNotificaciones()

    def _load_pasillo_sounds(self) -> None:
        """Carga (o reutiliza desde caché) el pool de audios reactivos de choque en el pasillo."""
        filenames = (
            "aja_estas_ciego_audio_pasillo_microjuego.ogg",
            "erda_audio_pasillo_microjuego.ogg",
            "que_pasa_valemia_audio_pasillo_microjuego.ogg",
        )
        sfx_vol = getattr(self.audio, "sfx_volume", 0.85)
        mixer_cfg = pygame.mixer.get_init()
        if mixer_cfg is None:
            return
        cache_key = ("pasillo", mixer_cfg, filenames)
        cached = _SOUND_CACHE.get(cache_key)
        if cached is not None:
            for snd in cached:
                snd.set_volume(sfx_vol)
            self.hit_sounds.extend(cached)
            return

        loaded: List[pygame.mixer.Sound] = []
        for fname in filenames:
            path = f"assets/{fname}"
            try:
                snd = pygame.mixer.Sound(path)
                snd.set_volume(sfx_vol)
                loaded.append(snd)
                self.hit_sounds.append(snd)
            except Exception as e:
                print(f"[UninorteSprint] Aviso al cargar sonido {fname}: {e}")
        if loaded:
            _SOUND_CACHE[cache_key] = loaded

    def _play_random_pasillo_voice(self) -> None:
        """Reproduce aleatoriamente una de las frases caribeñas al chocar."""
        if not self.hit_sounds:
            return
        snd = random.choice(self.hit_sounds)
        if hasattr(self.audio, "play_sfx"):
            self.audio.play_sfx(snd)
        else:
            if hasattr(self.audio, "sound_enabled") and not self.audio.sound_enabled:
                return
            snd.set_volume(getattr(self.audio, "sfx_volume", 0.85))
            snd.play()

    def _lane_to_world_y(self, lane: int) -> float:
        # Carril 0 en Y=1980 (abajo del tramo 1), Carril 13 en Y=225 (frente al salón en tramo 2)
        return 1980.0 - (lane * self.lane_height)

    def _load_background_chunks(self) -> Tuple[Optional[pygame.Surface], Optional[pygame.Surface], Optional[pygame.Surface]]:
        """
        Carga el fondo real si existe en assets/:
        1. 'fondo_minijuego_crossy.png' (fondo principal ilustrado por el usuario).
        2. 'fondo_uninorte_completo.png'
        3. 'fondo_uninorte_tramo_1.png' y 'fondo_uninorte_tramo_2.png'
        """
        cache_key = ("bg_chunks", self.screen_w, self.screen_h, self.world_height)
        cached = _SURFACE_CACHE.get(cache_key)
        if cached is not None:
            return cached

        bg_full = None
        bg_t1 = None
        bg_t2 = None

        # Prioridad 1: fondo_minijuego_crossy.png
        try:
            raw_crossy = self.assets.load_surface("fondo_minijuego_crossy.png", has_alpha=False)
            bg_full = pygame.transform.smoothscale(raw_crossy, (self.screen_w, self.world_height))
            res = (bg_full, None, None)
            _SURFACE_CACHE[cache_key] = res
            return res
        except Exception:
            pass

        try:
            raw_full = self.assets.load_surface("fondo_uninorte_completo.png", has_alpha=False)
            bg_full = pygame.transform.smoothscale(raw_full, (self.screen_w, self.world_height))
        except Exception:
            pass

        try:
            raw_t1 = self.assets.load_surface("fondo_uninorte_tramo_1.png", has_alpha=False)
            bg_t1 = pygame.transform.smoothscale(raw_t1, (self.screen_w, self.screen_h))
        except Exception:
            pass

        try:
            raw_t2 = self.assets.load_surface("fondo_uninorte_tramo_2.png", has_alpha=False)
            bg_t2 = pygame.transform.smoothscale(raw_t2, (self.screen_w, self.screen_h))
        except Exception:
            pass

        res = (bg_full, bg_t1, bg_t2)
        if bg_full is not None or bg_t1 is not None or bg_t2 is not None:
            _SURFACE_CACHE[cache_key] = res
        return res

    def _load_optional_ui(self, filename: str, target_h: int) -> Optional[pygame.Surface]:
        cache_key = ("optional_ui", filename, target_h)
        if cache_key in _SURFACE_CACHE:
            return _SURFACE_CACHE[cache_key]
        try:
            surf = self.assets.load_surface(filename, has_alpha=True)
            scale = target_h / float(surf.get_height())
            tw = int(surf.get_width() * scale)
            res = pygame.transform.smoothscale(surf, (tw, target_h))
            _SURFACE_CACHE[cache_key] = res
            return res
        except Exception:
            return None

    def _load_player_chibi(self) -> Optional[pygame.Surface]:
        cache_key = ("player_chibi", self.character_id)
        if cache_key in _SURFACE_CACHE:
            return _SURFACE_CACHE[cache_key]
        chibi_file = f"{self.character_id}_chibi.png"
        try:
            raw = self.assets.load_surface(chibi_file, has_alpha=True)
            mask = pygame.mask.from_surface(raw)
            rects = mask.get_bounding_rects()
            cropped = raw.subsurface(rects[0]) if rects else raw
            target_h = 135
            target_w = int(cropped.get_width() * (target_h / float(cropped.get_height())))
            res = pygame.transform.smoothscale(cropped, (target_w, target_h))
            _SURFACE_CACHE[cache_key] = res
            return res
        except Exception:
            try:
                raw = self.assets.load_surface("westcol_chibi.png", has_alpha=True)
                target_h = 135
                target_w = int(raw.get_width() * (target_h / float(raw.get_height())))
                res = pygame.transform.smoothscale(raw, (target_w, target_h))
                _SURFACE_CACHE[cache_key] = res
                return res
            except Exception:
                return None

    def _extract_character_models(self) -> List[CharacterModel]:
        """
        Extrae los 6 personajes únicos con sus 2 frames de caminata sin voltearlos:
        - Sheet 1 (spritesheet_npc_microjuego_crossy.png): Miran hacia la DERECHA (native_direction = 1).
        - Sheet 2 (spritesheet_npc_2_microjuego_crossy.png): Miran hacia la IZQUIERDA (native_direction = -1).
        Fila superior = Piernas cerradas (frame 0)
        Fila inferior = Piernas abiertas (frame 1)
        """
        target_h = 140
        cache_key = ("char_models", target_h)
        cached = _SURFACE_CACHE.get(cache_key)
        if cached is not None:
            return [CharacterModel(frames=list(frames), native_direction=nd) for frames, nd in cached]

        models: List[CharacterModel] = []

        sheet_specs = [
            {
                "file": "spritesheet_npc_microjuego_crossy.png",
                "native_direction": 1,  # Miran a la derecha -> Caminan exclusivamente a la derecha
                "chars": [
                    {"top": (158, 26, 250, 461), "bot": (134, 531, 284, 465)},
                    {"top": (599, 46, 278, 443), "bot": (595, 548, 306, 450)},
                    {"top": (1057, 63, 291, 431), "bot": (1059, 577, 341, 428)}
                ]
            },
            {
                "file": "spritesheet_npc_2_microjuego_crossy.png",
                "native_direction": -1,  # Miran a la izquierda -> Caminan exclusivamente a la izquierda
                "chars": [
                    {"top": (130, 21, 267, 457), "bot": (132, 520, 299, 454)},
                    {"top": (611, 38, 285, 440), "bot": (611, 521, 292, 453)},
                    {"top": (1093, 21, 278, 457), "bot": (1086, 512, 287, 468)}
                ]
            }
        ]

        for s_info in sheet_specs:
            filename = s_info["file"]
            native_dir = s_info["native_direction"]
            try:
                pil_img = Image.open(f"assets/{filename}").convert("RGBA")
                arr = np.array(pil_img)
                bg_mask = (arr[:, :, 0] > 238) & (arr[:, :, 1] > 238) & (arr[:, :, 2] > 238)
                arr[bg_mask, 3] = 0

                for ch in s_info["chars"]:
                    frames = []
                    for box in [ch["top"], ch["bot"]]:
                        bx, by, bw, bh = box
                        crop = np.ascontiguousarray(arr[by:by+bh, bx:bx+bw])
                        surf = pygame.image.frombuffer(crop.tobytes(), (bw, bh), "RGBA").convert_alpha()
                        tw = int(bw * (target_h / float(bh)))
                        scaled = pygame.transform.smoothscale(surf, (tw, target_h))
                        frames.append(scaled)

                    models.append(CharacterModel(frames=frames, native_direction=native_dir))
            except Exception as e:
                print(f"[UninorteSprint] Error al extraer modelos de {filename}: {e}")

        if models:
            _SURFACE_CACHE[cache_key] = [(tuple(m.frames), m.native_direction) for m in models]
        return models

    def _extract_icon_sprites(self) -> List[pygame.Surface]:
        target_size = 50
        cache_key = ("icon_sprites", target_size)
        cached = _SURFACE_CACHE.get(cache_key)
        if cached is not None:
            return list(cached)

        icons = []
        icon_boxes = [
            (551, 27, 155, 155), (885, 27, 152, 160), (1208, 28, 150, 159),
            (1369, 29, 149, 157), (718, 32, 154, 150), (23, 34, 169, 149),
            (1051, 36, 145, 148), (376, 37, 160, 146)
        ]
        try:
            full_surf = self.assets.load_surface("spritesheet_iconos_redes_sociales.png", has_alpha=True)
            for (ix, iy, iw, ih) in icon_boxes:
                sub = full_surf.subsurface(pygame.Rect(ix, iy, iw, ih))
                scaled = pygame.transform.smoothscale(sub, (target_size, target_size))
                icons.append(scaled)
            if icons:
                _SURFACE_CACHE[cache_key] = tuple(icons)
        except Exception as e:
            print(f"[UninorteSprint] Error cargando iconos: {e}")

        return icons

    def _spawn_equilibrated_zombies(self) -> None:
        """
        Puebla homogéneamente desde el primer segundo todos los carriles (1 a 7).
        - Carriles hacia la DERECHA (dir = 1) usan exclusivamente Sheet 1 (native_direction = 1).
        - Carriles hacia la IZQUIERDA (dir = -1) usan exclusivamente Sheet 2 (native_direction = -1).
        """
        if not self.character_models:
            return

        right_models = [m for m in self.character_models if m.native_direction == 1]
        left_models = [m for m in self.character_models if m.native_direction == -1]

        lane_configs = [
            {"lane": 1,  "dir": 1,  "speed": 280.0, "count": 3},
            {"lane": 2,  "dir": -1, "speed": 310.0, "count": 4},
            {"lane": 3,  "dir": 1,  "speed": 290.0, "count": 3},
            {"lane": 4,  "dir": -1, "speed": 330.0, "count": 4},
            {"lane": 5,  "dir": 1,  "speed": 300.0, "count": 3},
            {"lane": 6,  "dir": -1, "speed": 340.0, "count": 4},
            {"lane": 7,  "dir": 1,  "speed": 310.0, "count": 3},
            {"lane": 8,  "dir": -1, "speed": 350.0, "count": 4},
            {"lane": 9,  "dir": 1,  "speed": 320.0, "count": 3},
            {"lane": 10, "dir": -1, "speed": 360.0, "count": 4},
            {"lane": 11, "dir": 1,  "speed": 330.0, "count": 3},
            {"lane": 12, "dir": -1, "speed": 370.0, "count": 4},
        ]

        right_idx = 0
        left_idx = 0
        icon_idx = 0
        margin = 200
        total_span = self.screen_w + margin * 2

        for config in lane_configs:
            lane = config["lane"]
            world_y = self._lane_to_world_y(lane) - 60
            direction = config["dir"]
            speed = config["speed"]
            count = config["count"]
            spacing = total_span / float(count)

            for i in range(count):
                offset_jitter = random.uniform(-45, 45)
                x = -margin + (i * spacing) + offset_jitter

                if direction > 0 and right_models:
                    mod = right_models[right_idx % len(right_models)]
                    right_idx += 1
                elif left_models:
                    mod = left_models[left_idx % len(left_models)]
                    left_idx += 1
                else:
                    mod = self.character_models[0]

                icon = self.icon_sprites[icon_idx % len(self.icon_sprites)] if self.icon_sprites else None
                icon_idx += 1

                # Desfase explícito de fase por individuo (0.0, 0.35, 0.70, 1.05...)
                phase_offset = (i * 0.43) + (lane * 0.27)

                zombie = ZombieNPC(
                    x=x,
                    world_y=world_y,
                    speed=speed + random.uniform(-15.0, 15.0),
                    direction=direction,
                    model=mod,
                    icon_sprite=icon,
                    lane_idx=lane,
                    phase_offset=phase_offset
                )
                self.zombies.append(zombie)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        # Bloquear spam: no se puede volver a saltar mientras está en el aire o asentando el paso
        if self.is_finished or self.stun_timer > 0.0 or self.freeze_frames > 0:
            return
        if self.is_jumping or self.jump_cooldown > 0.0:
            return

        is_forward_jump = False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                is_forward_jump = True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            is_forward_jump = True

        if is_forward_jump:
            self._jump_forward()

    def exit(self) -> None:
        # La cámara pertenece al motor y se comparte con el resto de escenas.
        self.callarTictac()
        super().exit()

    def _jump_forward(self) -> None:
        if self.player_lane < self.max_lane:
            self.jump_start_world_y = self.player_visual_world_y
            self.player_lane += 1
            self.player_target_world_y = self._lane_to_world_y(self.player_lane)
            self.is_jumping = True
            self.jump_progress = 0.0

            self._spawn_dust(self.player_x, self.player_visual_world_y)

            if hasattr(self.audio, "play_jump"):
                self.audio.play_jump()

    def _spawn_dust(self, x: float, world_y: float) -> None:
        for _ in range(7):
            self.step_particles.append({
                "x": x + random.uniform(-25, 25),
                "world_y": world_y + 35 + random.uniform(-5, 5),
                "vx": random.uniform(-65, 65),
                "vy": random.uniform(-40, -10),
                "life": 0.35,
                "max_life": 0.35,
                "radius": random.uniform(5, 11)
            })

    def update_game(self, dt: float) -> None:
        self._walk_step_flash = max(0.0, self._walk_step_flash - dt)
        self._walk_step_buffer = max(0.0, self._walk_step_buffer - dt)
        self._walk_finger_idle += dt
        if self._walk_finger_idle >= 0.65:
            self._last_walk_finger = None
        if getattr(self, "camera_input", None) and self.camera_input.enabled and self.camera_input.is_hand_present():
            f0 = self.camera_input.consume_finger(0)
            f1 = self.camera_input.consume_finger(1)
            tapped = 0 if (f0 and self._last_walk_finger != 0) else 1 if (f1 and self._last_walk_finger != 1) else None
            if tapped is not None:
                self._last_walk_finger = tapped
                self._walk_finger_idle = 0.0
                self._walk_step_buffer = 0.35
        if self._walk_step_buffer > 0.0 and not self.is_jumping and self.jump_cooldown <= 0.0:
            self._jump_forward()
            if self.is_jumping:
                self._walk_step_flash = 0.25
            self._walk_step_buffer = 0.0
        # Hit-Stop / Freeze frame al impactar
        if self.freeze_frames > 0:
            self.freeze_frames -= 1
            return

        # Decaimiento del trauma del screenshake (cuadrático natural)
        if self.trauma > 0.0:
            self.trauma = max(0.0, self.trauma - dt * 2.2)

        # 1. Actualizar zombies
        for z in self.zombies:
            z.update(dt, self.screen_w)

        # 2. Interpolación del salto del jugador (Compromiso real en el aire + pausa al aterrizar)
        if self.jump_cooldown > 0.0:
            self.jump_cooldown = max(0.0, self.jump_cooldown - dt)

        if self.is_jumping:
            self.jump_progress += dt / self.jump_duration
            if self.jump_progress >= 1.0:
                self.jump_progress = 1.0
                self.is_jumping = False
                self.player_visual_world_y = self.player_target_world_y
                self.jump_cooldown = self.jump_recovery
                self._spawn_dust(self.player_x, self.player_visual_world_y)

                # Condición de Victoria se evalúa únicamente al aterrizar en el aula
                if self.player_lane >= self.max_lane and not self.is_finished:
                    self.finish_game(won=True)
            else:
                # Interpolación suave con curva ease-out entre origen y destino del salto
                ease_t = 1.0 - ((1.0 - self.jump_progress) ** 2)
                self.player_visual_world_y = (
                    self.jump_start_world_y
                    + (self.player_target_world_y - self.jump_start_world_y) * ease_t
                )

        # 3. Cámara vertical suave (Lerp)
        self.camera_target_y = self.player_visual_world_y - 720.0
        min_cam = 0.0
        max_cam = self.world_height - self.screen_h
        self.camera_target_y = max(min_cam, min(max_cam, self.camera_target_y))
        self.camera_y += (self.camera_target_y - self.camera_y) * min(1.0, dt * 10.0)

        # 4. Timer de aturdimiento
        if self.stun_timer > 0.0:
            self.stun_timer = max(0.0, self.stun_timer - dt)

        # 5. Detección de colisiones
        player_hitbox = self._get_player_hitbox()
        for z in self.zombies:
            if abs(self.player_visual_world_y - (z.world_y + z.height * 0.5)) < 65:
                if player_hitbox.colliderect(z.get_hitbox()):
                    self._on_player_hit()
                    break

        # 6. Cierre de puerta en el último segundo
        if self.time_left < 1.8 and not self.is_won:
            self.door_progress = min(1.0, self.door_progress + dt * 1.5)

        # 7. Partículas
        for p in self.step_particles[:]:
            p["x"] += p["vx"] * dt
            p["world_y"] += p["vy"] * dt
            p["life"] -= dt
            if p["life"] <= 0:
                self.step_particles.remove(p)

    def _get_player_hitbox() -> pygame.Rect:
        return pygame.Rect(0, 0, 10, 10)

    def _get_player_hitbox(self) -> pygame.Rect:
        hw, hh = 56, 56
        return pygame.Rect(
            int(self.player_x - hw / 2),
            int(self.player_visual_world_y - hh / 2 + 10),
            hw,
            hh
        )

    def _on_player_hit(self) -> None:
        """Penalización con Juice: hit-stop de 4 frames, trauma de screenshake, voz de pasillo y rebote."""
        if self.stun_timer > 0.0:
            return

        self.stun_timer = 0.40
        self.freeze_frames = 4       # Hit-stop táctil
        if self.tiempoDistraido > 0.0:
            # Chocar por ir mirando el celular cierra todavía más la visión
            self.choquesDistraido += 1
        self.trauma = 0.65           # Screen shake perceptible

        # Impacto sonoro físico + Voz reactiva del estudiante ("¡Ajá estás ciego!", "¡Erda!", "¡Qué pasa valemía!")
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()
        self._play_random_pasillo_voice()

        self.jump_start_world_y = self.player_visual_world_y
        self.player_lane = max(0, self.player_lane - 1)
        self.player_target_world_y = self._lane_to_world_y(self.player_lane)
        self.is_jumping = True
        self.jump_progress = 0.0
        self.jump_cooldown = 0.20
        self._spawn_dust(self.player_x, self.player_visual_world_y)

    def render_game(self, surface: pygame.Surface) -> None:
        # Calcular Screenshake no lineal
        shake_offset_x = 0
        shake_offset_y = 0
        if self.trauma > 0.0:
            shake_mag = (self.trauma ** 2) * 16.0
            shake_offset_x = int(random.uniform(-shake_mag, shake_mag))
            shake_offset_y = int(random.uniform(-shake_mag, shake_mag))

        cam_offset = int(self.camera_y) + shake_offset_y

        # 1. Renderizar Fondo (Real si existe en assets/, sino Placeholder estructural)
        using_placeholder = True
        if self.bg_full is not None:
            surface.blit(self.bg_full, (shake_offset_x, -cam_offset))
            using_placeholder = False
        elif self.bg_tramo_1 is not None or self.bg_tramo_2 is not None:
            surface.fill((238, 222, 198))
            if self.bg_tramo_2 is not None:
                # Tramo 2 va en la mitad superior del mundo
                surface.blit(self.bg_tramo_2, (shake_offset_x, 0 - cam_offset))
            if self.bg_tramo_1 is not None:
                # Tramo 1 va en la mitad inferior del mundo
                surface.blit(self.bg_tramo_1, (shake_offset_x, self.screen_h - cam_offset))
            using_placeholder = not (self.bg_tramo_1 is not None and self.bg_tramo_2 is not None)
        else:
            # Fondo de Adoquines (Placeholder)
            surface.fill((238, 222, 198))
            for lane in range(self.total_lanes + 2):
                lane_wy = self._lane_to_world_y(lane) + int(self.lane_height * 0.48)
                screen_ly = lane_wy - cam_offset
                if -50 <= screen_ly <= self.screen_h + 50:
                    pygame.draw.line(surface, (216, 196, 170), (0, screen_ly), (self.screen_w, screen_ly), 3)

            self._render_world_scenery(surface, cam_offset, shake_offset_x)
            self._render_classroom_door(surface, cam_offset, shake_offset_x)

        # 3. Y-Sorting para Zombies y Jugador
        render_list = []
        for z in self.zombies:
            sy = z.world_y + z.height - cam_offset
            if -200 <= sy <= self.screen_h + 200:
                render_list.append(("zombie", z.world_y + z.height, z))

        render_list.append(("player", self.player_visual_world_y + 40, None))
        render_list.sort(key=lambda item: item[1])

        for item_type, _, obj in render_list:
            if item_type == "zombie":
                self._draw_zombie(surface, obj, cam_offset, shake_offset_x)
            else:
                self._draw_player(surface, cam_offset, shake_offset_x)

        # Partículas de polvo
        for p in self.step_particles:
            px = p["x"] + shake_offset_x
            py = p["world_y"] - cam_offset
            alpha_ratio = p["life"] / p["max_life"]
            dust_col = (195, 175, 150)
            pygame.draw.circle(surface, dust_col, (int(px), int(py)), int(p["radius"] * alpha_ratio))

        self.dibujarExtrasNoti(surface, cam_offset, shake_offset_x)

        # 4. Overlay de UI Fijo
        self._render_hud_overlay(surface)

        # Badge indicador de Placeholder para el fondo (desaparece cuando cargas el fondo final)
        if using_placeholder:
            badge_bg = pygame.Rect(30, self.screen_h - 45, 420, 30)
            pygame.draw.rect(surface, (20, 20, 25, 210), badge_bg, border_radius=6)
            lbl_ph = self.font_badge.render("[PLACEHOLDER - FONDO CAMPUS UNINORTE]", True, (245, 215, 90))
            surface.blit(lbl_ph, lbl_ph.get_rect(center=badge_bg.center))

    def _render_world_scenery(self, surface: pygame.Surface, cam_offset: int, shake_x: int) -> None:
        bench_lanes = [1, 3, 5, 7, 9, 11]
        for l in bench_lanes:
            wy = self._lane_to_world_y(l) - 30
            sy = wy - cam_offset
            if -80 <= sy <= self.screen_h + 80:
                bench_rect = pygame.Rect(40 + shake_x, sy, 180, 48)
                pygame.draw.rect(surface, (190, 185, 175), bench_rect, border_radius=6)
                pygame.draw.rect(surface, (135, 130, 120), bench_rect, width=3, border_radius=6)

                pot_rect = pygame.Rect(self.screen_w - 220 + shake_x, sy, 170, 60)
                pygame.draw.rect(surface, (200, 195, 185), pot_rect, border_radius=8)
                pygame.draw.rect(surface, (140, 135, 125), pot_rect, width=3, border_radius=8)
                pygame.draw.circle(surface, (60, 160, 85), (pot_rect.centerx - 28, sy - 8), 32)
                pygame.draw.circle(surface, (45, 135, 70), (pot_rect.centerx + 28, sy - 10), 34)
                pygame.draw.circle(surface, (80, 180, 95), (pot_rect.centerx, sy - 18), 36)

    def _render_classroom_door(self, surface: pygame.Surface, cam_offset: int, shake_x: int) -> None:
        door_center_x = self.screen_w // 2 + shake_x
        door_world_y = self._lane_to_world_y(self.max_lane) - 60
        door_sy = door_world_y - cam_offset
        door_w, door_h = 260, 170

        wall_sy = door_sy - 90
        pygame.draw.rect(surface, (230, 222, 212), (0, wall_sy, self.screen_w, 260))
        pygame.draw.line(surface, (175, 165, 150), (0, wall_sy + 260), (self.screen_w, wall_sy + 260), 5)

        pygame.draw.rect(surface, (60, 48, 40), (door_center_x - door_w // 2 - 8, door_sy - 8, door_w + 16, door_h + 8), border_radius=6)
        pygame.draw.rect(surface, (255, 245, 185), (door_center_x - door_w // 2, door_sy, door_w, door_h))

        close_amount = self.door_progress if not self.is_won else 0.0
        leaf_w = int((door_w // 2) * close_amount)
        if leaf_w > 0:
            pygame.draw.rect(surface, (170, 120, 75), (door_center_x - door_w // 2, door_sy, leaf_w, door_h))
            pygame.draw.rect(surface, (170, 120, 75), (door_center_x + door_w // 2 - leaf_w, door_sy, leaf_w, door_h))

        badge_w, badge_h = 280, 46
        badge_rect = pygame.Rect(door_center_x - badge_w // 2, door_sy - 52, badge_w, badge_h)
        pygame.draw.rect(surface, (255, 255, 255), badge_rect, border_radius=8)
        pygame.draw.rect(surface, (45, 45, 45), badge_rect, width=3, border_radius=8)
        lbl_door = self.font_door.render("SALÓN A-203", True, (30, 30, 30))
        surface.blit(lbl_door, lbl_door.get_rect(center=badge_rect.center))

    def _draw_zombie(self, surface: pygame.Surface, z: ZombieNPC, cam_offset: int, shake_x: int) -> None:
        sx = z.x + shake_x
        sy = z.world_y - cam_offset

        # Cálculo de fade-out / esfumado en los bordes del pasillo
        # Pasillo transitable central: aprox x=360 a x=1560
        # Fuera de ese rango (al pasar detrás de las bancas / jardineras / paredes), se desvanecen suavemente
        center_x = sx + z.width / 2.0
        fade_margin_left = 420.0
        fade_margin_right = self.screen_w - 420.0
        fade_distance = 180.0

        if center_x < fade_margin_left:
            # Esfumándose hacia la izquierda
            alpha_factor = max(0.0, min(1.0, (center_x - (fade_margin_left - fade_distance)) / fade_distance))
        elif center_x > fade_margin_right:
            # Esfumándose hacia la derecha
            alpha_factor = max(0.0, min(1.0, ((fade_margin_right + fade_distance) - center_x) / fade_distance))
        else:
            alpha_factor = 1.0

        # Si ya se esfumó por completo, no renderizar
        if alpha_factor <= 0.01:
            return

        alpha_int = int(255 * alpha_factor)

        # 1. Sombra con desvanecimiento
        sw = int(z.width * 0.70)
        sh = 20
        shadow_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        shadow_alpha = int(75 * alpha_factor)
        pygame.draw.ellipse(shadow_surf, (20, 15, 10, shadow_alpha), (0, 0, sw, sh))
        surface.blit(shadow_surf, shadow_surf.get_rect(center=(int(center_x), int(sy + z.height - 4))))

        # 2. Sprite de personaje con alfa
        bob_y = math.sin(z.walk_bob) * 3.5
        current_spr = z.get_current_sprite()
        draw_y = int(sy + bob_y)

        if alpha_int < 250:
            spr_faded = current_spr.copy()
            spr_faded.fill((255, 255, 255, alpha_int), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(spr_faded, (int(sx), draw_y))
        else:
            surface.blit(current_spr, (int(sx), draw_y))

        # 3. Icono FOMO con alfa
        if z.icon_sprite:
            icon_bob = math.cos(z.walk_bob * 1.2) * 5.0
            ix = int(sx + (z.width - z.icon_sprite.get_width()) / 2)
            iy = int(sy - z.icon_sprite.get_height() + 8 + icon_bob)
            if alpha_int < 250:
                icon_faded = z.icon_sprite.copy()
                icon_faded.fill((255, 255, 255, alpha_int), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(icon_faded, (ix, iy))
            else:
                surface.blit(z.icon_sprite, (ix, iy))

    def _draw_player(self, surface: pygame.Surface, cam_offset: int, shake_x: int) -> None:
        jump_arc = 0.0
        if self.is_jumping:
            jump_arc = math.sin(self.jump_progress * math.pi) * self.jump_height

        px = int(self.player_x + shake_x)
        py = int(self.player_visual_world_y - cam_offset - jump_arc)

        shadow_scale = 1.0 - (jump_arc / self.jump_height) * 0.45
        sw = int(72 * shadow_scale)
        sh = int(22 * shadow_scale)
        if sw > 0 and sh > 0:
            shadow_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (25, 20, 15, 85), (0, 0, sw, sh))
            surface.blit(shadow_surf, shadow_surf.get_rect(center=(px, int(self.player_visual_world_y - cam_offset + 35))))

        if self.player_sprite:
            pw = self.player_sprite.get_width()
            ph = self.player_sprite.get_height()
            draw_pos = (px - pw // 2, py - ph + 38)
            if self.stun_timer > 0.0 and int(self.stun_timer * 20) % 2 == 0:
                tinted = self.player_sprite.copy()
                tinted.fill((255, 100, 100, 160), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(tinted, draw_pos)
            else:
                surface.blit(self.player_sprite, draw_pos)
        else:
            ph_rect = pygame.Rect(px - 30, py - 70, 60, 90)
            pygame.draw.rect(surface, (50, 120, 210), ph_rect, border_radius=12)
            pygame.draw.rect(surface, (255, 255, 255), ph_rect, width=3, border_radius=12)

    def _render_hud_overlay(self, surface: pygame.Surface) -> None:
        return
        # ==============================================================
        # 1. CONTADOR GRÁFICO (RELOJ + DÍGITOS DENTRO DEL RECUADRO)
        # ==============================================================
        counter_x = self.screen_w - 310
        counter_y = 20
        if self.spr_counter:
            surface.blit(self.spr_counter, (counter_x, counter_y))
            # Ajuste: 10px a la izquierda (x + 77) y 3px abajo (y + 18)
            display_rect = pygame.Rect(counter_x + 77, counter_y + 18, 138, 70)
            time_display = f"0:{int(math.ceil(self.time_left)):02d}"
            col = (45, 45, 45) if self.time_left > 4.0 else (225, 40, 40)
            txt_t = self.font_timer.render(time_display, True, col)
            surface.blit(txt_t, txt_t.get_rect(center=display_rect.center))
        else:
            txt_t = self.font_timer.render(f"TIEMPO: {self.time_left:.1f}s", True, (40, 40, 40))
            surface.blit(txt_t, (self.screen_w - 240, 40))

    def iniciarNotificaciones(self) -> None:
        self.momentosNoti = [3.5, 10.0]
        self.tiempoJugado = 0.0
        self.avisoAbierto = False
        self.tiempoAviso = 0.0
        self.opcionAviso = 1
        self.notiActual = ("", "")
        self.iconoNoti = None
        self.tiempoDistraido = 0.0
        self.duracionDistraccion = 4.0
        # Choques mientras se mira el celular: cada uno cierra más el túnel de visión (se reinicia al terminar)
        self.choquesDistraido = 0
        self.escalaTunel = 1.0
        self.saltoNormal = (self.jump_duration, self.jump_recovery)
        self.mensajeFlotante = ""
        self.tiempoMensaje = 0.0
        self.sonidoTictac = self.cargarTictac()
        self.canalTictac = None
        self.ultimoUpdate = 0

        self.notificaciones = [
            ("Grupo del salón", "Tienes 27 mensajes sin leer"),
            ("Valentina", "Subió una historia nueva"),
            ("Te etiquetaron", "Mira el video donde sales"),
            ("Tendencias", "Todo el mundo está viendo esto"),
        ]
        random.shuffle(self.notificaciones)

        self.frasesGlobo = [
            "Solo reviso una cosa...",
            "¿Y si me escribió?",
            "Un video más y ya",
            "¿Cuántos likes llevo?",
            "¿Ya me contestaron?",
            "Ahorita lo guardo",
        ]
        iconoPuntos = self.icon_sprites[7] if len(self.icon_sprites) > 7 else None
        cuantos = 0
        for z in self.zombies:
            if iconoPuntos is not None and z.icon_sprite is iconoPuntos:
                z.frase = self.frasesGlobo[cuantos % len(self.frasesGlobo)]
                z.cicloGlobo = random.uniform(0.0, 5.0)
                z.icon_sprite = None
                cuantos += 1
            else:
                z.frase = None
        self.globosHechos = {}

        self.imagenesNoti = self.cargarImagenesNoti()

    def cargarImagenesNoti(self) -> bool:
        try:
            import os
            celular = self.assets.cargarSinFondo(os.path.join("Uninorte", "celularNotificacion.jpg"), 500)
            self.celular = pygame.transform.smoothscale_by(celular, 640 / float(celular.get_height()))
            self.celularMini = pygame.transform.smoothscale_by(celular, 125 / float(celular.get_height()))
            self.globo = self.assets.cargarSinFondo(os.path.join("Uninorte", "globoPensamiento.jpg"), 210)
            self.botonMorado = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonMorado.jpg"), 300)
            rojo = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonRojo.jpg"), 300)
            self.botonRojo = pygame.transform.smoothscale_by(rojo, 1.05)
        except Exception as e:
            print(f"[UninorteSprint] Aviso: faltan imágenes de la notificación: {e}")
            return False
        self.fuenteAvisoTitulo = self.assets.cargarFuenteTitulo(46)
        self.fuenteNotiApp = self.assets.cargarFuenteCuento(32)
        self.fuenteNotiTexto = self.assets.cargarFuenteCuento(36)
        self.fuenteBotonAviso = self.assets.cargarFuenteTitulo(30)
        self.fuenteAyudaAviso = self.assets.cargarFuenteCuento(24)
        self.fuenteGlobo = self.assets.cargarFuenteCuento(22)
        self.fuenteMensaje = self.assets.cargarFuenteCuento(38)
        self.fuenteEnsenanza = self.assets.cargarFuenteCuento(46)
        self.tunel = self.crearTunel()
        self.ensenanzas = [
            ["Cuando miras la pantalla,", "te pierdes lo que pasa a tu alrededor."],
            ["Un ratico en el celular", "se vuelve un buen rato sin ver el camino."],
            ["La notificación puede esperar.", "El camino y la gente que va contigo, no."],
        ]
        self.ensenanza = self.ensenanzas[0]
        return True

    def cargarTictac(self):
        guardado = UninorteSprintMicrogame.__dict__.get("tictacGuardado")
        if guardado is not None:
            return guardado
        try:
            import os
            import numpy
            if not pygame.mixer.get_init():
                return None
            original = pygame.mixer.Sound(os.path.join("assets", "Uninorte", "tictac.mp3"))
            onda = pygame.sndarray.array(original).astype(numpy.float32)
            pico = max(1.0, float(numpy.abs(onda).max()))
            onda = numpy.clip(onda * (26000.0 / pico), -32767, 32767).astype(numpy.int16)
            sonido = pygame.sndarray.make_sound(numpy.ascontiguousarray(onda))
            UninorteSprintMicrogame.tictacGuardado = sonido
            return sonido
        except Exception as e:
            print(f"[UninorteSprint] Aviso: no se pudo cargar el tictac: {e}")
            return None

    def sonarTictac(self) -> None:
        if self.sonidoTictac is None or not getattr(self.audio, "sound_enabled", True):
            return
        self.callarTictac()
        self.canalTictac = self.sonidoTictac.play(loops=-1)
        if self.canalTictac is not None:
            self.canalTictac.set_volume(max(0.0, min(1.0, getattr(self.audio, "sfx_volume", 0.8))))

    def callarTictac(self) -> None:
        if getattr(self, "canalTictac", None) is not None:
            self.canalTictac.stop()
            self.canalTictac = None

    # Tamaño del túnel (1 = el de siempre) tras 0, 1, 2 y 3+ choques mirando el celular
    ESCALAS_TUNEL = (1.0, 0.68, 0.48, 0.34)

    def crearTunel(self, escala: float = 1.0) -> pygame.Surface:
        tunel = pygame.Surface((self.screen_w, 2000), pygame.SRCALPHA)
        oscuro = (20, 20, 22)
        tunel.fill((*oscuro, 252))
        centro = (self.screen_w // 2, 1000)
        borde, hueco = int(230 * escala), max(30, int(95 * escala))
        paso = max(2, int(5 * escala))
        for radio in range(borde, hueco, -paso):
            claridad = (radio - hueco) / float(max(1, borde - hueco))
            pygame.draw.circle(tunel, (*oscuro, int(252 * claridad)), centro, radio)
        pygame.draw.circle(tunel, (*oscuro, 0), centro, hueco)
        return tunel

    def tunelActual(self) -> pygame.Surface:
        """Túnel de visión según los choques (solo 4 tamaños en caché; el cambio coincide con el golpe)."""
        if not hasattr(self, "_tuneles"):
            self._tuneles = {1.0: self.tunel}
        escala = self.ESCALAS_TUNEL[min(self.choquesDistraido, len(self.ESCALAS_TUNEL) - 1)]
        self.escalaTunel = escala
        if escala not in self._tuneles:
            self._tuneles[escala] = self.crearTunel(escala)
        return self._tuneles[escala]

    def update(self, dt: float) -> None:
        if self.phase == self.PHASE_PLAY and not self.is_finished and getattr(self, "imagenesNoti", False):
            if self.avisoAbierto:
                if hasattr(self.audio, "update"):
                    self.audio.update(dt)
                self.tiempoAviso += dt
                self.ultimoUpdate = pygame.time.get_ticks()
                if self.canalTictac is not None:
                    if getattr(self.audio, "sound_enabled", True):
                        self.canalTictac.set_volume(max(0.0, min(1.0, getattr(self.audio, "sfx_volume", 0.8))))
                        self.canalTictac.unpause()
                    else:
                        self.callarTictac()
                self.revisarGestosAviso(dt)
                return
            self.tiempoJugado += dt
            self.revisarLlegadaNoti()
            self.actualizarDistraccion(dt)
        if getattr(self, "tiempoMensaje", 0.0) > 0.0:
            self.tiempoMensaje = max(0.0, self.tiempoMensaje - dt)
        super().update(dt)

    def revisarLlegadaNoti(self) -> None:
        if not self.momentosNoti or self.tiempoJugado < self.momentosNoti[0]:
            return
        if self.is_jumping or self.stun_timer > 0.0 or self.freeze_frames > 0 or self.tiempoDistraido > 0.0:
            return
        self.momentosNoti.pop(0)
        if self.player_lane >= self.max_lane - 1:
            return
        self.notiActual = self.notificaciones[len(self.momentosNoti) % len(self.notificaciones)]
        self.iconoNoti = random.choice(self.icon_sprites) if self.icon_sprites else None
        self.avisoAbierto = True
        self._walk_step_buffer = 0.0
        self._last_walk_finger = None
        self.reset_binary_camera_choice()
        self.tiempoAviso = 0.0
        self.opcionAviso = 1
        self.ultimoUpdate = pygame.time.get_ticks()
        self.sonarTictac()
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def revisarGestosAviso(self, dt: float = 1 / 60) -> None:
        camara = getattr(self, "camera_input", None)
        if not camara or not camara.enabled or self.tiempoAviso < 0.6:
            self.reset_binary_camera_choice()
            return
        choice = self.poll_binary_camera_choice(camara, dt)
        if choice is not None:
            self.elegirOpcionAviso(choice)

    def elegirOpcionAviso(self, opcion: int) -> None:
        self.avisoAbierto = False
        self.reset_binary_camera_choice()
        self.callarTictac()
        if opcion == 0:
            self.tiempoDistraido = self.duracionDistraccion
            self.jump_duration = 0.42
            self.jump_recovery = 0.30
            self.mensajeFlotante = "Solo un ratico..."
            self.ensenanza = random.choice(self.ensenanzas)
        else:
            self.mensajeFlotante = "¡Ojos al frente!"
        self.tiempoMensaje = 1.6
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def actualizarDistraccion(self, dt: float) -> None:
        if self.tiempoDistraido <= 0.0:
            return
        self.tiempoDistraido = max(0.0, self.tiempoDistraido - dt)
        if self.tiempoDistraido == 0.0:
            self.jump_duration, self.jump_recovery = self.saltoNormal
            self.choquesDistraido = 0
            self.escalaTunel = 1.0

    def botonesAviso(self) -> list:
        return [
            self.botonMorado.get_rect(center=(960 - 175, 880)),
            self.botonMorado.get_rect(center=(960 + 175, 880)),
        ]

    def handle_event(self, event: pygame.event.Event) -> None:
        if not getattr(self, "avisoAbierto", False) or self.phase != self.PHASE_PLAY:
            super().handle_event(event)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            super().handle_event(event)
            return
        if self.tiempoAviso < 0.6:
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            for i, caja in enumerate(self.botonesAviso()):
                if caja.collidepoint(event.pos):
                    if event.type == pygame.MOUSEMOTION and self.opcionAviso != i:
                        self.opcionAviso = i
                        if hasattr(self.audio, "play_hover"):
                            self.audio.play_hover()
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.elegirOpcionAviso(i)
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.opcionAviso = 0
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.opcionAviso = 1
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.elegirOpcionAviso(self.opcionAviso)

    def render(self, surface: pygame.Surface) -> None:
        super().render(surface)
        if getattr(self, "avisoAbierto", False) and self.phase == self.PHASE_PLAY:
            self.dibujarAviso(surface)
        elif self.phase == self.PHASE_PLAY and getattr(self, "camera_input", None) and self.camera_input.enabled:
            self._draw_walking_feedback(surface)
        if getattr(self, "canalTictac", None) is not None and pygame.time.get_ticks() - self.ultimoUpdate > 150:
            self.canalTictac.pause()

    def _draw_walking_feedback(self, surface: pygame.Surface) -> None:
        if not hasattr(self, "_walk_feedback_paper"):
            paper = self.assets.load_cropped_surface("tarjeta_slot_partida.png")
            self._walk_feedback_paper = pygame.transform.smoothscale(paper, (540, 86))
        surface.blit(self._walk_feedback_paper, (690, 108))
        for idx, (x, lbl) in enumerate(((760, "ÍNDICE"), (845, "MEDIO"))):
            active = self._last_walk_finger == idx
            col = (113, 182, 155) if (active and self._walk_step_flash > 0) else (190, 161, 211) if active else (215, 204, 192)
            pygame.draw.circle(surface, col, (x, 148), 22)
            pygame.draw.circle(surface, (104, 74, 65), (x, 148), 22, 2)
            t = self._walk_feedback_font.render(lbl, True, (78, 51, 35))
            surface.blit(t, t.get_rect(center=(x, 180)))
        msg = "¡Paso!" if self._walk_step_flash > 0 else "Alterna índice y medio para caminar"
        label = self._walk_feedback_font.render(msg, True, (78, 51, 35))
        surface.blit(label, label.get_rect(center=(1050, 150)))

    def partirEnLineas(self, fuente, texto: str, anchoMax: int) -> list:
        lineas = []
        actual = ""
        for palabra in texto.split():
            prueba = (actual + " " + palabra).strip()
            if fuente.size(prueba)[0] <= anchoMax or not actual:
                actual = prueba
            else:
                lineas.append(actual)
                actual = palabra
        if actual:
            lineas.append(actual)
        return lineas

    def dibujarAviso(self, surface: pygame.Surface) -> None:
        surface.fill((104, 98, 122), special_flags=pygame.BLEND_RGB_MULT)

        titulo = self.textoConBorde(self.fuenteAvisoTitulo, "¡Bzz, bzz! Te llegó una notificación", (255, 248, 236), (92, 46, 118))
        surface.blit(titulo, titulo.get_rect(center=(960, 120)))

        entrada = min(1.0, self.tiempoAviso / 0.25)
        escala = 0.75 + 0.25 * (1.0 - (1.0 - entrada) ** 2)
        temblor = 0
        if self.tiempoAviso < 0.7:
            temblor = int(math.sin(self.tiempoAviso * 70.0) * 8)
        celular = self.celular if escala >= 0.999 else pygame.transform.smoothscale_by(self.celular, escala)
        caja = celular.get_rect(center=(960 + temblor, 480))
        surface.blit(celular, caja)

        if escala >= 0.999:
            tarjeta = pygame.Rect(caja.left + int(caja.width * 0.21), caja.top + int(caja.height * 0.17),
                                  int(caja.width * 0.6), int(caja.height * 0.15))
            app = self.fuenteNotiApp.render(self.notiActual[0], True, (92, 46, 118))
            if app.get_width() > tarjeta.width - 70:
                app = pygame.transform.smoothscale_by(app, (tarjeta.width - 70) / float(app.get_width()))
            anchoFila = app.get_width()
            if self.iconoNoti is not None:
                anchoFila += self.iconoNoti.get_width() + 10
            x = tarjeta.centerx - anchoFila // 2
            if self.iconoNoti is not None:
                surface.blit(self.iconoNoti, self.iconoNoti.get_rect(midleft=(x, tarjeta.centery)))
                x += self.iconoNoti.get_width() + 10
            surface.blit(app, app.get_rect(midleft=(x, tarjeta.centery)))

            y = tarjeta.bottom + 34
            for linea in self.partirEnLineas(self.fuenteNotiTexto, self.notiActual[1], int(caja.width * 0.66)):
                texto = self.fuenteNotiTexto.render(linea, True, (90, 64, 52))
                surface.blit(texto, texto.get_rect(midtop=(caja.centerx, y)))
                y += texto.get_height() + 2

        etiquetas = ["Revisar", "Seguir el rumbo"]
        for i, boton in enumerate(self.botonesAviso()):
            elegido = i == self.opcionAviso
            imagen = self.botonRojo if elegido else self.botonMorado
            surface.blit(imagen, imagen.get_rect(center=boton.center))
            contorno = (120, 26, 34) if elegido else (70, 30, 110)
            texto = self.textoConBorde(self.fuenteBotonAviso, etiquetas[i], (255, 248, 236), contorno)
            surface.blit(texto, texto.get_rect(center=(boton.centerx, boton.centery - 3)))

        ayuda = "Cruceta o flechas para elegir · A o Enter para aceptar"
        camara = getattr(self, "camera_input", None)
        if camara and camara.enabled:
            ayuda = "Pellizco/puño (mantén): revisar · Palma abierta (mantén): seguir"
            progress_pair = getattr(self, "_choice_hold_progress", (0.0, 0.0))
            for index, progress in enumerate(progress_pair):
                rect = self.botonesAviso()[index]
                bar = pygame.Rect(rect.left + 30, rect.bottom + 10, rect.width - 60, 10)
                pygame.draw.rect(surface, (225, 210, 192), bar, border_radius=5)
                fill = bar.copy()
                fill.width = int(bar.width * min(1.0, progress))
                if fill.width:
                    pygame.draw.rect(surface, (132, 91, 160) if index == 0 else (78, 151, 121), fill, border_radius=5)
        texto = self.textoConBorde(self.fuenteAyudaAviso, ayuda, (255, 248, 236), (70, 50, 40))
        surface.blit(texto, texto.get_rect(center=(960, 975)))

    def globoConFrase(self, frase: str, volteado: bool) -> pygame.Surface:
        clave = (frase, volteado)
        if clave not in self.globosHechos:
            globo = pygame.transform.flip(self.globo, True, False) if volteado else self.globo.copy()
            w, h = globo.get_size()
            lineas = self.partirEnLineas(self.fuenteGlobo, frase, int(w * 0.66))
            alto = self.fuenteGlobo.get_linesize()
            y = int(h * 0.38) - (len(lineas) * alto) // 2
            for linea in lineas:
                texto = self.fuenteGlobo.render(linea, True, (80, 46, 92))
                globo.blit(texto, texto.get_rect(midtop=(w // 2, y)))
                y += alto
            self.globosHechos[clave] = globo
        return self.globosHechos[clave]

    def dibujarExtrasNoti(self, surface: pygame.Surface, cam_offset: int, shake_x: int) -> None:
        if not getattr(self, "imagenesNoti", False):
            return

        for z in self.zombies:
            frase = getattr(z, "frase", None)
            if not frase:
                continue
            centroX = z.x + shake_x + z.width / 2.0
            if centroX < 420 or centroX > self.screen_w - 420:
                continue
            sy = z.world_y - cam_offset
            if sy < 120 or sy > self.screen_h:
                continue
            fase = (self.tiempoJugado + z.cicloGlobo) % 5.0
            if fase > 3.0:
                continue
            globo = self.globoConFrase(frase, z.direction < 0)
            crecer = min(1.0, fase / 0.2)
            if crecer < 1.0:
                globo = pygame.transform.smoothscale_by(globo, 0.6 + 0.4 * crecer)
            if fase > 2.7:
                globo = globo.copy()
                globo.set_alpha(int(255 * (3.0 - fase) / 0.3))
            colita = 0.8 if z.direction < 0 else 0.2
            surface.blit(globo, globo.get_rect(bottomleft=(int(centroX - globo.get_width() * colita), int(sy + 6))))

        if self.tiempoDistraido > 0.0:
            fuerza = min(1.0, (self.duracionDistraccion - self.tiempoDistraido) / 0.3, self.tiempoDistraido / 0.5)
            yJugador = int(self.player_visual_world_y - cam_offset - 30)
            tunel = self.tunelActual()
            tunel.set_alpha(int(255 * fuerza))
            surface.blit(tunel, (shake_x, yJugador - 1000))

            vaiven = math.sin(self.tiempoJugado * 6.0) * 4
            celular = self.celularMini.get_rect(midleft=(int(self.player_x + shake_x + 40), int(yJugador - 60 + vaiven)))
            surface.blit(self.celularMini, celular)

            arriba = max(150, yJugador - 420)
            for i, linea in enumerate(self.ensenanza):
                texto = self.textoConBorde(self.fuenteEnsenanza, linea, (255, 244, 220), (48, 48, 50))
                texto.set_alpha(int(255 * fuerza))
                surface.blit(texto, texto.get_rect(center=(self.screen_w // 2 + shake_x, arriba + i * 62)))

        if self.tiempoMensaje > 0.0 and self.mensajeFlotante:
            subida = (1.6 - self.tiempoMensaje) * 40
            texto = self.textoConBorde(self.fuenteMensaje, self.mensajeFlotante, (255, 248, 236), (92, 46, 118))
            texto.set_alpha(int(255 * min(1.0, self.tiempoMensaje / 0.4)))
            yJugador = self.player_visual_world_y - cam_offset
            surface.blit(texto, texto.get_rect(center=(int(self.player_x + shake_x), int(yJugador - 160 - subida))))
