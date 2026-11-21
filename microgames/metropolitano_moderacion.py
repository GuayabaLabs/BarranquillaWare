import math
import random
from typing import Optional, Callable, List, Tuple, Dict, Any
import pygame

from core.microgame import BaseMicrogame
from core.asset_manager import AssetManager
from core.camera_gestures import CameraGestureInput
from core.settings import CHARACTER_DISPLAY_NAMES


class MetropolitanoModeracionMicrogame(BaseMicrogame):
    CAMERA_POINTER = True  # El lapicero apunta el martillo; pellizcar golpea.
    CAMERA_DWELL_CLICK = False  # No golpear por mirar un mensaje inocente.
    """
    Nivel 3 — Estadio Metropolitano Roberto Meléndez
    Microjuego: ¡Modera la Barra Brava!

    Temática: Convivencia digital y freno al ciberacoso en chats en vivo.
    Duración: 20 segundos (o ronda rápida configurable para Modo Arcade).
    Interacción: Martillo de moderación ('Ban Hammer') con FLECHAS / WASD + ESPACIO/ENTER, o click.
    Dinámica: Cuadrícula 3x3 siempre llena de espectadores con mensajes en vivo.
              Identifica a los barras bravas tóxicos (filas 3-4 del spritesheet) y modéralos
              sin golpear a los hinchas sanos.
    """

    TARGET_BANS: int = 10
    TOTAL_DURATION: float = 20.0

    TOXIC_CHAT_TAGS: Tuple[str, ...] = (
        "¡FUERA TODOS!",
        "¡QUÉ BASURA!",
        "¡NO SIRVEN!",
        "¡PURO HATE!",
        "¡A SILENCIAR!",
        "¡TROLL EN VIVO!",
    )

    HEALTHY_CHAT_TAGS: Tuple[str, ...] = (
        "¡VAMOS TIBURÓN!",
        "¡BUEN PARTIDO!",
        "¡DALE JUNIOR!",
        "¡RESPETO TOTAL!",
        "¡PURO CARNAVAL!",
        "¡PAZ EN LA RED!",
    )

    def __init__(
        self,
        character_id: Any = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None,
        time_limit: Optional[float] = None,
        target_bans: Optional[int] = None,
        arcade_mode: bool = False,
    ) -> None:
        if callable(character_id) and on_complete_callback is None:
            on_complete_callback = character_id
            character_id = "westcol"

        self.character_id: str = str(character_id or "westcol")
        self.arcade_mode: bool = bool(arcade_mode)
        resolved_duration = (
            float(time_limit)
            if time_limit is not None
            else (6.5 if self.arcade_mode else self.TOTAL_DURATION)
        )
        self.target_bans: int = (
            int(target_bans)
            if target_bans is not None
            else (3 if self.arcade_mode else self.TARGET_BANS)
        )

        super().__init__(
            command_text="¡MODERA LA BARRA!",
            time_limit=resolved_duration,
            on_complete_callback=on_complete_callback,
        )
        self.intro_duration = 0.7 if self.arcade_mode else 1.0
        self.outro_duration = 1.0 if self.arcade_mode else 1.8

    # Música del estadio: versión instrumental de la canción del Junior (sin voz, para no tapar el juego).
    # Si todavía no está en assets/, suena la versión original.
    JUNIOR_INSTRUMENTAL = ("JuniorCancion_instrumental.mp3", "JuniorCancion_instrumental.ogg")
    JUNIOR_ORIGINAL = "JuniorCancion.mp3"

    @classmethod
    def musica_estadio(cls) -> str:
        import os
        for nombre in cls.JUNIOR_INSTRUMENTAL:
            if os.path.exists(os.path.join("assets", nombre)):
                return nombre
        return cls.JUNIOR_ORIGINAL

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm(self.musica_estadio(), volume_scale=0.45)

    def setup_game(self) -> None:
        """Inicializa estructuras del tablero 3x3, slots y assets."""
        self.camera_input = CameraGestureInput.get_instance()
        if not self.camera_input.enabled:
            self.camera_input.start()

        self.bans_count: int = 0
        self.innocent_hits: int = 0

        # Pantalla y proporciones
        self.trauma: float = 0.0
        self.max_shake_offset: float = 24.0
        self.particles: List[Dict[str, Any]] = []
        self.ripples: List[Dict[str, Any]] = []
        self.floating_texts: List[Dict[str, Any]] = []

        # Estado del Martillo con Control por Flechas
        self.grid_row: int = 1
        self.grid_col: int = 1
        self.hammer_pos = [self.screen_w // 2, self.screen_h // 2]
        self.hammer_target_pos = [self.screen_w // 2, self.screen_h // 2]
        self.hammer_angle: float = 25.0
        self.hammer_swing_timer: float = 0.0
        self.hammer_stun_timer: float = 0.0

        # Recorte milimétrico calibrado según los 9 monitores reales del fondo (1920x1080)
        col_ranges = [(392, 746), (783, 1131), (1168, 1524)]
        row_ranges = [(256, 432), (470, 646), (684, 866)]

        self.screen_rect = pygame.Rect(380, 245, 1155, 630)
        self.cell_w = 340
        self.cell_h = 172
        self._load_sprites()
        self._load_moderator_badge()

        # Inicializar 9 slots alineados con precisión a los paneles del fondo
        self.slots: List[Dict[str, Any]] = []
        for r_idx, (y1, y2) in enumerate(row_ranges):
            for c_idx, (x1, x2) in enumerate(col_ranges):
                panel_rect = pygame.Rect(x1, y1, x2 - x1, y2 - y1)
                slot_data = {
                    "rect": panel_rect,
                    "row": r_idx,
                    "col": c_idx,
                    "is_toxic": False,
                    "timer": random.uniform(1.8, 3.5),
                    "max_lifetime": 3.0,
                    "sprite": None,
                    "chat_tag": "",
                    "banned_anim": 0.0,
                    "transition_alpha": 255.0,
                    "just_banned": False,
                }
                self.slots.append(slot_data)

        # Distribuir exactamente 2 o 3 barras bravas al inicio
        initial_toxic_indices = set(random.sample(range(9), k=random.choice([2, 3])))
        for idx, s in enumerate(self.slots):
            is_toxic = idx in initial_toxic_indices
            s["is_toxic"] = is_toxic
            s["sprite"] = (
                random.choice(self.toxic_sprites)
                if (is_toxic and self.toxic_sprites)
                else (random.choice(self.healthy_sprites) if self.healthy_sprites else None)
            )
            s["chat_tag"] = random.choice(self.TOXIC_CHAT_TAGS if is_toxic else self.HEALTHY_CHAT_TAGS)
            s["timer"] = random.uniform(2.0, 3.8)
            s["max_lifetime"] = s["timer"]

        # Centrar el martillo en la celda inicial (1, 1)
        self._update_hammer_target_from_grid()
        self.hammer_pos = list(self.hammer_target_pos)
        self.hit_stop_timer: float = 0.0

        # Fuentes tipográficas refinadas estilo Cozy / Arcade
        self.font_score = self.assets.cargarFuenteCuento(30)
        self.font_badge = pygame.font.SysFont("Segoe UI Black, Arial Black, Impact", 24)
        self.font_status = pygame.font.SysFont("Segoe UI Black, Arial Black, Impact", 22)
        self.font_counter = pygame.font.SysFont("Segoe UI Black, Trebuchet MS, Arial Black", 24, bold=True)
        self.font_chat = pygame.font.SysFont("Arial, sans-serif", 14, bold=True)
        self.font_theme = self.assets.cargarFuenteCuento(22)

        # Shader precomputado de pantalla LED (Scanlines + Vignette)
        self._build_led_shader_surface()

    def _load_moderator_badge(self) -> None:
        self.mod_avatar: Optional[pygame.Surface] = None
        try:
            raw = self.assets.load_cropped_surface(f"{self.character_id}_chibi.png", alpha_threshold=15)
            h = 62
            w = max(20, int(raw.get_width() * (h / float(max(1, raw.get_height())))))
            self.mod_avatar = pygame.transform.smoothscale(raw, (w, h))
        except Exception:
            self.mod_avatar = None

        self.theme_ribbon_surf: Optional[pygame.Surface] = None
        try:
            raw_rib = self.assets.load_cropped_surface("cinta_distrito_modal.png")
            self.theme_ribbon_surf = pygame.transform.smoothscale(raw_rib, (920, 44))
        except Exception:
            self.theme_ribbon_surf = None

    def _update_hammer_target_from_grid(self) -> None:
        """Calcula la posición objetivo del martillo según la casilla seleccionada en la cuadrícula."""
        for s in self.slots:
            if s["row"] == self.grid_row and s["col"] == self.grid_col:
                self.hammer_target_pos = [s["rect"].centerx, s["rect"].centery]
                break

    def _build_led_shader_surface(self) -> None:
        """Crea un overlay de shader para la pantalla LED del estadio (Scanlines + Viñeta)."""
        w, h = self.screen_rect.width, self.screen_rect.height
        self.shader_surf = pygame.Surface((w, h), pygame.SRCALPHA)

        scanline_color = (0, 0, 0, 42)
        for y in range(0, h, 4):
            pygame.draw.line(self.shader_surf, scanline_color, (0, y), (w, y), 2)

        border_thickness = 18
        for i in range(border_thickness):
            alpha = int(85 * (1.0 - (i / border_thickness)))
            c = (5, 8, 20, alpha)
            pygame.draw.rect(self.shader_surf, c, (i, i, w - 2 * i, h - 2 * i), width=1)

    def _populate_slot(self, slot: Dict[str, Any], initial: bool = False, force_healthy: bool = False) -> None:
        """
        Asigna un espectador al slot con rotación progresiva:
        - Control estricto de población: siempre entre 2 y 3 barras bravas en el tablero.
        - Si force_healthy=True, el siguiente espectador es siempre sano.
        """
        current_toxic_count = sum(
            1 for s in self.slots if s.get("is_toxic", False) and s.get("banned_anim", 0.0) <= 0.0
        )

        if force_healthy:
            is_toxic = False
        else:
            if current_toxic_count < 2:
                is_toxic = True
            elif current_toxic_count < 3:
                is_toxic = random.random() < 0.40
            else:
                is_toxic = False

        slot["is_toxic"] = is_toxic
        slot["sprite"] = (
            random.choice(self.toxic_sprites)
            if (is_toxic and self.toxic_sprites)
            else (random.choice(self.healthy_sprites) if self.healthy_sprites else None)
        )
        slot["chat_tag"] = random.choice(self.TOXIC_CHAT_TAGS if is_toxic else self.HEALTHY_CHAT_TAGS)
        slot["timer"] = random.uniform(2.2, 3.8)
        slot["max_lifetime"] = slot["timer"]
        slot["transition_alpha"] = 255.0

    def _apply_screen_shader_to_sprite(self, base_surf: pygame.Surface) -> pygame.Surface:
        return base_surf

    def _load_sprites(self) -> None:
        """
        Carga fondo y spritesheet de espectadores (5 filas x 8 columnas):
        - Filas 0 a 2 (24 sprites): Aficionados sanos del Junior.
        - Filas 3 y 4 (16 sprites): Barras bravas conflictivos y tóxicos.
        """
        self.bg_surf: Optional[pygame.Surface] = None
        try:
            raw_bg = self.assets.load_surface("fondo_chat_estadio_microjuego.png", has_alpha=False)
            self.bg_surf = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))
        except Exception:
            self.bg_surf = None

        self.toxic_sprites: List[pygame.Surface] = []
        self.healthy_sprites: List[pygame.Surface] = []

        try:
            sheet = self.assets.load_surface("espectadores_junior_chat_estadio_microjuego.png", has_alpha=True)
            sw, sh = sheet.get_size()
            cols, rows = 8, 5
            cw = sw // cols
            ch = sh // rows
            sprite_size = 142

            for r in range(rows):
                for c in range(cols):
                    margin_x = 4
                    margin_y = 4
                    sub = sheet.subsurface((c * cw + margin_x, r * ch + margin_y, cw - margin_x * 2, ch - margin_y * 2))
                    scaled = pygame.transform.smoothscale(sub, (sprite_size, sprite_size))
                    shaded_sprite = self._apply_screen_shader_to_sprite(scaled)
                    if r >= 3:
                        self.toxic_sprites.append(shaded_sprite)
                    else:
                        self.healthy_sprites.append(shaded_sprite)
        except Exception:
            pass

        self._build_hammer_surface()

    def _build_hammer_surface(self) -> None:
        target_size = (180, 165)
        try:
            raw_hammer = self.assets.load_surface("martillo_baneador_chat_estadio_microjuego.png", has_alpha=True)
            self.hammer_surf = pygame.transform.smoothscale(raw_hammer, target_size)
        except Exception:
            self.hammer_surf = pygame.Surface(target_size, pygame.SRCALPHA)
            pygame.draw.line(self.hammer_surf, (110, 60, 25), (40, 140), (110, 70), 18)
            head_rect = pygame.Rect(80, 30, 80, 60)
            pygame.draw.rect(self.hammer_surf, (230, 40, 40), head_rect, border_radius=8)
            pygame.draw.rect(self.hammer_surf, (255, 255, 255), head_rect, width=3, border_radius=8)

    def update_game(self, dt: float) -> None:
        """Lógica de microjuego desacoplada con dt."""
        if self.hit_stop_timer > 0.0:
            self.hit_stop_timer -= dt
            return

        if self.trauma > 0.0:
            self.trauma = max(0.0, self.trauma - dt * 2.2)

        lerp_speed = 18.0
        self.hammer_pos[0] += (self.hammer_target_pos[0] - self.hammer_pos[0]) * min(1.0, dt * lerp_speed)
        self.hammer_pos[1] += (self.hammer_target_pos[1] - self.hammer_pos[1]) * min(1.0, dt * lerp_speed)

        if self.hammer_stun_timer > 0.0:
            self.hammer_stun_timer = max(0.0, self.hammer_stun_timer - dt)

        if self.hammer_swing_timer > 0.0:
            self.hammer_swing_timer -= dt * 6.0
            t = max(0.0, self.hammer_swing_timer)
            self.hammer_angle = 25.0 - (1.0 - t) * 70.0
        else:
            self.hammer_angle = 25.0

        # Pacing progresivo proporcional al time_limit real (soporta 20s y modo rápido Arcade)
        duration = max(1.0, float(self.time_limit))
        elapsed = max(0.0, duration - self.time_left)
        progress_ratio = min(1.0, elapsed / duration)
        speed_factor = 1.0 + progress_ratio * 1.35

        for s in self.slots:
            if s["banned_anim"] > 0.0:
                s["banned_anim"] -= dt * 2.5
                if s["banned_anim"] <= 0.0:
                    s["banned_anim"] = 0.0
                    force_healthy = s.get("just_banned", False)
                    self._populate_slot(s, force_healthy=force_healthy)

            s["timer"] -= dt * speed_factor
            if s["timer"] <= 0.0 and s["banned_anim"] <= 0.0:
                self._populate_slot(s)

        # Regulación activa: garantizar entre 2 y 3 barras bravas en el tablero
        toxic_slots = [s for s in self.slots if s["is_toxic"] and s["banned_anim"] <= 0.0]
        if len(toxic_slots) < 2:
            healthy_candidates = [
                s for s in self.slots
                if not s["is_toxic"] and s["banned_anim"] <= 0.0 and not s.get("just_banned", False)
            ]
            if healthy_candidates:
                target_slot = random.choice(healthy_candidates)
                target_slot["is_toxic"] = True
                target_slot["sprite"] = random.choice(self.toxic_sprites) if self.toxic_sprites else None
                target_slot["chat_tag"] = random.choice(self.TOXIC_CHAT_TAGS)
                target_slot["timer"] = random.uniform(2.2, 3.8)
                target_slot["max_lifetime"] = target_slot["timer"]
        elif len(toxic_slots) > 3:
            excess_slot = random.choice(toxic_slots)
            excess_slot["is_toxic"] = False
            excess_slot["sprite"] = random.choice(self.healthy_sprites) if self.healthy_sprites else None
            excess_slot["chat_tag"] = random.choice(self.HEALTHY_CHAT_TAGS)

        for s in self.slots:
            if s["banned_anim"] <= 0.0 and s.get("just_banned", False):
                s["just_banned"] = False

        for p in self.particles[:]:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
            if p["life"] <= 0.0:
                self.particles.remove(p)

        for rp in self.ripples[:]:
            rp["r"] += dt * 320.0
            rp["life"] -= dt * 2.4
            if rp["life"] <= 0.0:
                self.ripples.remove(rp)

        for ft in self.floating_texts[:]:
            ft["y"] -= 60.0 * dt
            ft["life"] -= dt
            if ft["life"] <= 0.0:
                self.floating_texts.remove(ft)

        if self.bans_count >= self.target_bans:
            self.outro_message = "¡CHAT EN PAZ!"
            self.finish_game(won=True)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        """Maneja el martillo con Flechas / WASD y Barra Espaciadora / Enter / Click."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.grid_col = max(0, self.grid_col - 1)
                self._update_hammer_target_from_grid()
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.grid_col = min(2, self.grid_col + 1)
                self._update_hammer_target_from_grid()
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.grid_row = max(0, self.grid_row - 1)
                self._update_hammer_target_from_grid()
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.grid_row = min(2, self.grid_row + 1)
                self._update_hammer_target_from_grid()
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z, pygame.K_x):
                self._on_hammer_strike(tuple(self.hammer_target_pos))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for s in self.slots:
                if s["rect"].collidepoint(event.pos):
                    self.grid_row = s["row"]
                    self.grid_col = s["col"]
                    self._update_hammer_target_from_grid()
                    break
            self._on_hammer_strike(event.pos)

        elif event.type == pygame.MOUSEMOTION:
            # El puntero óptico del motor envía movimiento virtual igual que el mouse.
            # Mantener sincronizados el martillo y la selección del tablero.
            for slot in self.slots:
                if slot["rect"].collidepoint(event.pos):
                    self.grid_row = slot["row"]
                    self.grid_col = slot["col"]
                    self.hammer_target_pos = [slot["rect"].centerx, slot["rect"].centery]
                    break

    def _on_hammer_strike(self, pos: Tuple[int, int]) -> None:
        self.hammer_swing_timer = 1.0
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

        if self.hammer_stun_timer > 0.0:
            self._add_floating_text("¡MARTILLO BLOQUEADO!", pos[0], pos[1] - 30, (255, 130, 60))
            return

        hit_any = False
        for s in self.slots:
            if s["rect"].collidepoint(pos) and s["banned_anim"] <= 0.0:
                hit_any = True
                if s["is_toxic"]:
                    self._handle_successful_ban(s, pos)
                else:
                    self._handle_innocent_hit(s, pos)
                break

        if not hit_any:
            self._add_smoke_particles(pos[0], pos[1], (180, 180, 180), count=6)

    def _handle_successful_ban(self, slot: Dict[str, Any], pos: Tuple[int, int]) -> None:
        self.bans_count += 1
        slot["banned_anim"] = 1.0
        slot["just_banned"] = True
        if hasattr(self.audio, "play_hit"):
            self.audio.play_hit()

        self.trauma = min(1.0, self.trauma + 0.55)
        self.hit_stop_timer = 0.04

        self.ripples.append({"x": pos[0], "y": pos[1], "r": 24.0, "life": 1.0, "color": (255, 195, 70)})
        self._add_smoke_particles(pos[0], pos[1], (255, 50, 70), count=16)
        self._add_smoke_particles(pos[0], pos[1], (255, 215, 80), count=12)
        self._add_floating_text("+1 MODERADO", pos[0], pos[1] - 42, (255, 235, 120))

    def _handle_innocent_hit(self, slot: Dict[str, Any], pos: Tuple[int, int]) -> None:
        self.innocent_hits += 1
        if hasattr(self.audio, "play_miss"):
            self.audio.play_miss()

        if self.bans_count > 0:
            self.bans_count -= 1

        self.hammer_stun_timer = 0.60
        self.trauma = min(1.0, self.trauma + 0.45)

        self.ripples.append({"x": pos[0], "y": pos[1], "r": 20.0, "life": 1.0, "color": (90, 175, 255)})
        self._add_smoke_particles(pos[0], pos[1], (90, 175, 255), count=14)
        self._add_floating_text("-1 (¡HINCHA SANO!)", pos[0], pos[1] - 42, (255, 110, 110))

    def _add_smoke_particles(self, x: float, y: float, color: Tuple[int, int, int], count: int = 10) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(120, 360)
            self.particles.append({
                "x": x,
                "y": y,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "color": color,
                "life": random.uniform(0.25, 0.55),
                "max_life": 0.55,
                "radius": random.uniform(4.0, 9.0),
            })

    def _add_floating_text(self, text: str, x: float, y: float, color: Tuple[int, int, int]) -> None:
        self.floating_texts.append({
            "text": text,
            "x": x,
            "y": y,
            "color": color,
            "life": 0.85,
            "max_life": 0.85,
        })

    def render_game(self, surface: pygame.Surface) -> None:
        shake_mag = (self.trauma ** 2) * self.max_shake_offset
        shake_x = int(random.uniform(-shake_mag, shake_mag)) if shake_mag > 0.1 else 0
        shake_y = int(random.uniform(-shake_mag, shake_mag)) if shake_mag > 0.1 else 0

        render_surf = surface
        if shake_x != 0 or shake_y != 0:
            render_surf = surface.copy()

        # 1. Fondo del Estadio
        if self.bg_surf:
            render_surf.blit(self.bg_surf, (0, 0))
        else:
            render_surf.fill((28, 34, 52))
            pygame.draw.rect(render_surf, (44, 52, 78), (100, 100, self.screen_w - 200, self.screen_h - 150), border_radius=12)

        # 2. Marco LED Superior + Avatar del Moderador
        self._render_led_header(render_surf)

        # 3. Renderizado de las 9 Casillas (3x3)
        for s in self.slots:
            self._render_slot(render_surf, s)

        # 4. Shader de pantalla LED
        if hasattr(self, "shader_surf"):
            render_surf.blit(self.shader_surf, (self.screen_rect.x, self.screen_rect.y))

        # 5. Ondas expansivas de impacto
        for rp in self.ripples:
            alpha = int(200 * max(0.0, rp["life"]))
            rad = max(4, int(rp["r"]))
            r_surf = pygame.Surface((rad * 2 + 8, rad * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(r_surf, (*rp["color"], alpha), (rad + 4, rad + 4), rad, width=4)
            render_surf.blit(r_surf, (int(rp["x"] - rad - 4), int(rp["y"] - rad - 4)))

        # 6. Partículas
        for p in self.particles:
            alpha = int(255 * (p["life"] / p["max_life"]))
            rad = max(1, int(p["radius"] * (p["life"] / p["max_life"])))
            s = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p["color"], alpha), (rad, rad), rad)
            render_surf.blit(s, (p["x"] - rad, p["y"] - rad))

        # 7. Textos flotantes
        for ft in self.floating_texts:
            alpha = int(255 * (ft["life"] / ft["max_life"]))
            txt_surf = self.font_status.render(ft["text"], True, ft["color"])
            txt_surf.set_alpha(alpha)
            render_surf.blit(txt_surf, (ft["x"] - txt_surf.get_width() // 2, ft["y"]))

        # 8. Banner inferior de temática social (Convivencia digital en vivo)
        self._render_theme_banner(render_surf)

        # 9. Martillo
        self._render_hammer(render_surf)

        if shake_x != 0 or shake_y != 0:
            surface.fill((0, 0, 0))
            surface.blit(render_surf, (int(shake_x), int(shake_y)))

    def _render_led_header(self, surf: pygame.Surface) -> None:
        bar_w = 820
        bar_h = 52
        bar_x = (self.screen_w - bar_w) // 2
        bar_y = 42

        # Sombra suave
        shadow_surf = pygame.Surface((bar_w + 24, bar_h + 24), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (30, 18, 12, 95), (8, 8, bar_w + 8, bar_h + 8), border_radius=26)
        surf.blit(shadow_surf, (bar_x - 12, bar_y - 8))

        # Cápsula estilo pergamino acuarela cálido
        capsule_surf = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        pygame.draw.rect(capsule_surf, (250, 241, 224, 242), (0, 0, bar_w, bar_h), border_radius=26)
        pygame.draw.rect(capsule_surf, (132, 86, 54, 220), (0, 0, bar_w, bar_h), width=3, border_radius=26)

        pad_left = 22
        pad_right = 128
        pad_y = 9
        track_w = bar_w - pad_left - pad_right
        track_h = bar_h - (pad_y * 2)
        pygame.draw.rect(capsule_surf, (62, 42, 32, 225), (pad_left, pad_y, track_w, track_h), border_radius=17)

        total_segments = max(1, self.target_bans)
        gap = 5
        seg_w = max(8, (track_w - (total_segments - 1) * gap - 8) // total_segments)
        start_seg_x = pad_left + 4
        seg_y = pad_y + 4
        seg_h = track_h - 8

        for i in range(total_segments):
            sx = start_seg_x + i * (seg_w + gap)
            is_filled = i < self.bans_count
            if is_filled:
                pygame.draw.rect(capsule_surf, (226, 74, 86), (sx, seg_y, seg_w, seg_h), border_radius=6)
                pygame.draw.rect(capsule_surf, (255, 206, 178), (sx + 2, seg_y + 2, max(2, seg_w - 4), max(2, seg_h // 3)), border_radius=3)
                pygame.draw.rect(capsule_surf, (255, 244, 226), (sx, seg_y, seg_w, seg_h), width=1, border_radius=6)
            else:
                pygame.draw.rect(capsule_surf, (92, 68, 56), (sx, seg_y, seg_w, seg_h), border_radius=6)

        num_str = f"{self.bans_count} / {self.target_bans}"
        col_text = (34, 134, 72) if self.bans_count >= self.target_bans else (78, 51, 35)
        txt_num = self.font_counter.render(num_str, True, col_text)
        txt_x = bar_w - pad_right + (pad_right - txt_num.get_width()) // 2
        txt_y = bar_h // 2 - txt_num.get_height() // 2
        capsule_surf.blit(txt_num, (txt_x, txt_y))
        surf.blit(capsule_surf, (bar_x, bar_y))

        # Badge del moderador activo (character_id) a la izquierda del medidor
        char_name = CHARACTER_DISPLAY_NAMES.get(self.character_id.lower(), self.character_id.capitalize())
        mod_w, mod_h = 250, 56
        mod_surf = pygame.Surface((mod_w, mod_h), pygame.SRCALPHA)
        pygame.draw.rect(mod_surf, (252, 244, 228, 238), (0, 0, mod_w, mod_h), border_radius=24)
        pygame.draw.rect(mod_surf, (132, 86, 54, 215), (0, 0, mod_w, mod_h), width=2, border_radius=24)
        if self.mod_avatar:
            mod_surf.blit(self.mod_avatar, (10, (mod_h - self.mod_avatar.get_height()) // 2))
        lbl_mod = self.font_chat.render("MOD EN VIVO", True, (186, 62, 62))
        lbl_name = self.font_theme.render(char_name.upper(), True, (78, 51, 35))
        mod_surf.blit(lbl_mod, (76, 6))
        mod_surf.blit(lbl_name, (76, 22))
        surf.blit(mod_surf, (bar_x - mod_w - 20, bar_y - 2))

    def _render_theme_banner(self, surf: pygame.Surface) -> None:
        msg = "CHAT EN VIVO · MODERA EL CIBERACOSO SIN SILENCIAR AL HINCHA SANO"
        if self.theme_ribbon_surf:
            rect = self.theme_ribbon_surf.get_rect(center=(self.screen_w // 2, 982))
            surf.blit(self.theme_ribbon_surf, rect)
            txt = self.font_theme.render(msg, True, (78, 51, 35))
            surf.blit(txt, txt.get_rect(center=(rect.centerx, rect.centery - 1)))
        else:
            pill = pygame.Rect(self.screen_w // 2 - 440, 960, 880, 42)
            pygame.draw.rect(surf, (250, 241, 224), pill, border_radius=20)
            txt = self.font_theme.render(msg, True, (78, 51, 35))
            surf.blit(txt, txt.get_rect(center=pill.center))

    def _render_slot(self, surf: pygame.Surface, slot: Dict[str, Any]) -> None:
        rect: pygame.Rect = slot["rect"]

        # 1. Fondo papel marfil cálido del monitor
        bg_card = (252, 248, 240)
        pygame.draw.rect(surf, bg_card, rect, border_radius=12)
        pygame.draw.rect(surf, (226, 212, 192), rect, width=3, border_radius=12)
        pygame.draw.rect(surf, (78, 54, 42), rect, width=2, border_radius=12)

        # 2. Resaltador focal en la casilla seleccionada
        is_focused = slot["row"] == self.grid_row and slot["col"] == self.grid_col
        if is_focused:
            focus_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pulse = int(180 + 65 * math.sin(pygame.time.get_ticks() / 110.0))
            pygame.draw.rect(focus_surf, (255, 215, 75, 55), (0, 0, rect.width, rect.height), border_radius=12)
            pygame.draw.rect(focus_surf, (242, 174, 48, pulse), (0, 0, rect.width, rect.height), width=4, border_radius=12)
            surf.blit(focus_surf, (rect.x, rect.y))

        # 3. Espectador centrado en la parte superior del panel
        if slot["sprite"]:
            spr = slot["sprite"]
            sx = rect.centerx - spr.get_width() // 2
            sy = rect.top + 6
            surf.blit(spr, (sx, sy))

        # 4. Chip de chat en vivo en la franja inferior del monitor
        chat_tag = slot.get("chat_tag", "")
        if chat_tag:
            chip_rect = pygame.Rect(rect.x + 14, rect.bottom - 30, rect.width - 28, 24)
            if slot["is_toxic"]:
                chip_bg = (254, 224, 224)
                chip_border = (212, 74, 78)
                chip_txt_col = (146, 32, 38)
            else:
                chip_bg = (228, 246, 236)
                chip_border = (68, 162, 108)
                chip_txt_col = (30, 96, 60)
            pygame.draw.rect(surf, chip_bg, chip_rect, border_radius=8)
            pygame.draw.rect(surf, chip_border, chip_rect, width=1, border_radius=8)
            t_chat = self.font_chat.render(chat_tag, True, chip_txt_col)
            surf.blit(t_chat, t_chat.get_rect(center=chip_rect.center))

        # 5. Estampilla de baneo
        if slot["banned_anim"] > 0.0:
            stamp_w, stamp_h = 228, 56
            stamp_surf = pygame.Surface((stamp_w, stamp_h), pygame.SRCALPHA)
            pygame.draw.rect(stamp_surf, (216, 48, 56, 238), (0, 0, stamp_w, stamp_h), border_radius=10)
            pygame.draw.rect(stamp_surf, (255, 248, 236, 245), (0, 0, stamp_w, stamp_h), width=3, border_radius=10)
            t_ban = self.font_badge.render("[ BANEADO ]", True, (255, 250, 240))
            stamp_surf.blit(t_ban, t_ban.get_rect(center=(stamp_w // 2, stamp_h // 2)))

            rot_stamp = pygame.transform.rotate(stamp_surf, -10.0)
            surf.blit(
                rot_stamp,
                (rect.centerx - rot_stamp.get_width() // 2, rect.centery - rot_stamp.get_height() // 2),
            )

    def _render_hammer(self, surf: pygame.Surface) -> None:
        rot_hammer = pygame.transform.rotate(self.hammer_surf, self.hammer_angle)
        hx = self.hammer_pos[0] - rot_hammer.get_width() // 2 + 15
        hy = self.hammer_pos[1] - rot_hammer.get_height() // 2 - 25

        if self.hammer_stun_timer > 0.0:
            rot_hammer.set_alpha(105 if int(pygame.time.get_ticks() / 80) % 2 == 0 else 210)

        surf.blit(rot_hammer, (hx, hy))
