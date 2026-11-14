import os
import math
import random
from typing import Optional, Callable, List, Tuple, Dict, Any
import pygame

from core.microgame import BaseMicrogame
from core.asset_manager import AssetManager
from core.camera_gestures import CameraGestureInput


class MetropolitanoModeracionMicrogame(BaseMicrogame):
    """
    Nivel 3 — Estadio Metropolitano Roberto Meléndez
    Microjuego: ¡Modera la Barra Brava!
    
    Temática: Convivencia digital y ciberacoso en redes sociales.
    Duración: 20 segundos.
    Interacción: Martillo de moderación ('Ban Hammer') controlado con FLECHAS del teclado y ESPACIO/ENTER.
    Dinámica: Cuadrícula 3x3 SIEMPRE llena de aficionados. Van cambiando progresivamente.
              El jugador debe identificar a los barras bravas (filas 3-4 del spritesheet)
              y martillarlos.
    Visual: Shader procedimental de pantalla LED gigante del estadio (scanlines + viñeta + flicker)
            con recorte limpio ajustado exactamente al monitor del Roberto Meléndez.
    """

    TARGET_BANS: int = 10
    TOTAL_DURATION: float = 20.0

    def __init__(self, on_complete_callback: Optional[Callable[[bool], None]] = None) -> None:
        super().__init__(
            command_text="¡MODERA LA BARRA!",
            time_limit=self.TOTAL_DURATION,
            on_complete_callback=on_complete_callback
        )
        self.intro_duration = 1.0
        self.outro_duration = 1.8

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("JuniorCancion.mp3")

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
        self.floating_texts: List[Dict[str, Any]] = []

        # Estado del Martillo con Control por Flechas
        self.grid_row: int = 1
        self.grid_col: int = 1
        self.hammer_pos = [self.screen_w // 2, self.screen_h // 2]
        self.hammer_target_pos = [self.screen_w // 2, self.screen_h // 2]
        self.hammer_angle: float = 25.0
        self.hammer_swing_timer: float = 0.0
        self.hammer_stun_timer: float = 0.0

        # Recorte milimétrico calibrado según los 9 monitores reales del fondo (1920x1080):
        # Columnas reales en textura:
        # Col 0 (izquierda): x=[392, 746] (ancho: 354, centro: 569) - Desplazado a la derecha
        # Col 1 (centro):    x=[783, 1131] (ancho: 348, centro: 957)
        # Col 2 (derecha):   x=[1168, 1524] (ancho: 356, centro: 1346) - Desplazado a la izquierda
        # Filas reales en textura:
        # Fila 0: y=[256, 432] (alto: 176, centro: 344)
        # Fila 1: y=[470, 646] (alto: 176, centro: 558)
        # Fila 2: y=[684, 866] (alto: 182, centro: 775)
        col_ranges = [(392, 746), (783, 1131), (1168, 1524)]
        row_ranges = [(256, 432), (470, 646), (684, 866)]

        self.screen_rect = pygame.Rect(380, 245, 1155, 630)

        # Cargar Assets con dimensiones ajustadas a los monitores individuales
        self.cell_w = 340
        self.cell_h = 172
        self._load_sprites()

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
                    "banned_anim": 0.0,
                    "transition_alpha": 255.0,
                    "just_banned": False,
                }
                self.slots.append(slot_data)

        # Distribuir exactamente 2 o 3 barras bravas al inicio
        initial_toxic_indices = set(random.sample(range(9), k=random.choice([2, 3])))
        for idx, s in enumerate(self.slots):
            is_toxic = (idx in initial_toxic_indices)
            s["is_toxic"] = is_toxic
            s["sprite"] = random.choice(self.toxic_sprites) if (is_toxic and self.toxic_sprites) else (random.choice(self.healthy_sprites) if self.healthy_sprites else None)
            s["timer"] = random.uniform(2.0, 3.8)
            s["max_lifetime"] = s["timer"]

        # Centrar el martillo en la celda inicial (1, 1)
        self._update_hammer_target_from_grid()
        self.hammer_pos = list(self.hammer_target_pos)

        self.hit_stop_timer: float = 0.0

        # Fuentes tipográficas refinadas estilo Cozy / Arcade
        self.font_score = pygame.font.SysFont("Segoe UI Black, Arial Black, Impact", 32)
        self.font_badge = pygame.font.SysFont("Segoe UI Black, Arial Black, Impact", 26)
        self.font_status = pygame.font.SysFont("Segoe UI Black, Arial Black, Impact", 22)
        self.font_counter = pygame.font.SysFont("Segoe UI Black, Trebuchet MS, Arial Black", 24, bold=True)

        # Shader precomputado de pantalla LED (Scanlines + Grid sutil + Vignette)
        self._build_led_shader_surface()

    def _update_hammer_target_from_grid(self) -> None:
        """Calcula la posición objetivo del martillo según la casilla seleccionada en la cuadrícula."""
        for s in self.slots:
            if s["row"] == self.grid_row and s["col"] == self.grid_col:
                self.hammer_target_pos = [s["rect"].centerx, s["rect"].centery]
                break

    def _build_led_shader_surface(self) -> None:
        """
        Crea un overlay de shader para la pantalla LED del estadio:
        - Scanlines horizontales estilo fósforo CRT/LED.
        - Viñeta de oscurecimiento radial en los bordes.
        - Ruido de brillo/flicker leve.
        """
        w, h = self.screen_rect.width, self.screen_rect.height
        self.shader_surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # 1. Scanlines
        scanline_color = (0, 0, 0, 50)
        for y in range(0, h, 4):
            pygame.draw.line(self.shader_surf, scanline_color, (0, y), (w, y), 2)

        # 2. Viñeta en los bordes de la pantalla
        vignette_color = (10, 15, 30, 80)
        border_thickness = 18
        for i in range(border_thickness):
            alpha = int(90 * (1.0 - (i / border_thickness)))
            c = (5, 8, 20, alpha)
            pygame.draw.rect(self.shader_surf, c, (i, i, w - 2 * i, h - 2 * i), width=1)

    def _populate_slot(self, slot: Dict[str, Any], initial: bool = False, force_healthy: bool = False) -> None:
        """
        Asigna un espectador al slot con rotación progresiva:
        - Control estricto de población: siempre se mantienen entre 2 y 3 barras bravas en todo el tablero.
        - Si un barra brava es moderado en esta casilla (force_healthy=True), se garantiza que el siguiente
          sea un hincha sano (nunca reaparece un barra brava inmediatamente en el mismo cuadro).
        """
        current_toxic_count = sum(1 for s in self.slots if s.get("is_toxic", False) and s.get("banned_anim", 0.0) <= 0.0)

        if force_healthy:
            is_toxic = False
        else:
            # Si hay menos de 2, permitimos generar tóxico; si ya hay 3 o más, FORZAMOS hincha sano
            if current_toxic_count < 2:
                is_toxic = True
            elif current_toxic_count < 3:
                is_toxic = (random.random() < 0.40)
            else:
                is_toxic = False

        slot["is_toxic"] = is_toxic
        slot["sprite"] = random.choice(self.toxic_sprites) if (is_toxic and self.toxic_sprites) else (random.choice(self.healthy_sprites) if self.healthy_sprites else None)
        slot["timer"] = random.uniform(2.2, 3.8)
        slot["max_lifetime"] = slot["timer"]
        slot["transition_alpha"] = 255.0

    def _apply_screen_shader_to_sprite(self, base_surf: pygame.Surface) -> pygame.Surface:
        """
        Retorna el sprite limpio al 100% de color y nitidez.
        El fondo blanco y el marco se dibujan ahora ocupando todo el recuadro del monitor en _render_slot.
        """
        return base_surf
        """
        Carga y procesa fondos y el spritesheet de espectadores:
        - Dimensiones del spritesheet: 1536x1024
        - Disposición: 5 filas x 8 columnas (40 sprites en total, cada uno de 192x204.8 px).
        - Filas 0 a 2 (primeras 3 filas, 24 sprites): Aficionados sanos/festivos del Junior.
        - Filas 3 y 4 (últimas 2 filas, 16 sprites): Barras bravas conflictivos y tóxicos.
        """
    def _load_sprites(self) -> None:
        """
        Carga y procesa fondos y el spritesheet de espectadores:
        - Dimensiones del spritesheet: 1536x1024
        - Disposición: 5 filas x 8 columnas (40 sprites en total, cada uno de 192x204.8 px).
        - Filas 0 a 2 (primeras 3 filas, 24 sprites): Aficionados sanos/festivos del Junior.
        - Filas 3 y 4 (últimas 2 filas, 16 sprites): Barras bravas conflictivos y tóxicos.
        """
        # 1. Fondo del estadio
        self.bg_surf: Optional[pygame.Surface] = None
        try:
            raw_bg = self.assets.load_surface("fondo_chat_estadio_microjuego.png", has_alpha=False)
            self.bg_surf = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))
        except Exception:
            self.bg_surf = None

        # 2. Spritesheet de 5 filas x 8 columnas
        self.toxic_sprites: List[pygame.Surface] = []
        self.healthy_sprites: List[pygame.Surface] = []

        try:
            sheet = self.assets.load_surface("espectadores_junior_chat_estadio_microjuego.png", has_alpha=True)
            sw, sh = sheet.get_size()
            cols = 8
            rows = 5
            cw = sw // cols  # 192 px
            ch = sh // rows  # 204 px

            # Tamaño cuadradito manteniendo relación de aspecto original (1:1) sin aplastar
            sprite_size = 170

            for r in range(rows):
                for c in range(cols):
                    # Recorte interno sin bordes de corte
                    margin_x = 4
                    margin_y = 4
                    sub = sheet.subsurface((c * cw + margin_x, r * ch + margin_y, cw - margin_x * 2, ch - margin_y * 2))
                    scaled = pygame.transform.smoothscale(sub, (sprite_size, sprite_size))
                    
                    # Aplicar base de monitor cuadrada de alto contraste
                    shaded_sprite = self._apply_screen_shader_to_sprite(scaled)

                    # Últimas dos filas (filas 3 y 4) = Barras bravas conflictivos
                    if r >= 3:
                        self.toxic_sprites.append(shaded_sprite)
                    else:
                        # Filas 0, 1, 2 = Aficionados sanos
                        self.healthy_sprites.append(shaded_sprite)
        except Exception:
            pass

        # 3. Textura del martillo
        self._build_hammer_surface()

    def _build_hammer_surface(self) -> None:
        """Carga y procesa el sprite oficial del Martillo Baneador ('martillo_baneador_chat_estadio_microjuego.png')."""
        target_size = (180, 165)
        try:
            raw_hammer = self.assets.load_surface("martillo_baneador_chat_estadio_microjuego.png", has_alpha=True)
            self.hammer_surf = pygame.transform.smoothscale(raw_hammer, target_size)
        except Exception:
            # Fallback elegante si el archivo no estuviese disponible
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

        # Interpolación suave del martillo hacia la casilla seleccionada por flechas
        lerp_speed = 18.0
        self.hammer_pos[0] += (self.hammer_target_pos[0] - self.hammer_pos[0]) * min(1.0, dt * lerp_speed)
        self.hammer_pos[1] += (self.hammer_target_pos[1] - self.hammer_pos[1]) * min(1.0, dt * lerp_speed)

        # Cooldown de aturdimiento del martillo si golpeó inocente
        if self.hammer_stun_timer > 0.0:
            self.hammer_stun_timer = max(0.0, self.hammer_stun_timer - dt)

        # Animación del swing del martillo
        if self.hammer_swing_timer > 0.0:
            self.hammer_swing_timer -= dt * 6.0
            t = max(0.0, self.hammer_swing_timer)
            # Oscilación rápida: 25 -> -45 -> 25
            self.hammer_angle = 25.0 - (1.0 - t) * 70.0
        else:
            self.hammer_angle = 25.0

        # Pacing progresivo de rotación en 20 segundos
        elapsed = self.TOTAL_DURATION - self.time_left
        progress_ratio = min(1.0, elapsed / self.TOTAL_DURATION)

        # A medida que pasa el tiempo, los espectadores rotan más rápido
        speed_factor = 1.0 + progress_ratio * 1.5

        # Actualizar cada uno de los 9 slots (SIEMPRE LLENOS)
        for s in self.slots:
            if s["banned_anim"] > 0.0:
                s["banned_anim"] -= dt * 2.5
                if s["banned_anim"] <= 0.0:
                    s["banned_anim"] = 0.0
                    # Rellenar garantizando hincha sano en la casilla recién martillada
                    force_healthy = s.get("just_banned", False)
                    self._populate_slot(s, force_healthy=force_healthy)

            # Transición/cambio suave si está expirando su tiempo
            s["timer"] -= dt * speed_factor
            if s["timer"] <= 0.0 and s["banned_anim"] <= 0.0:
                self._populate_slot(s)

        # Regulación activa: garantizar siempre entre 2 y 3 barras bravas en el tablero
        toxic_slots = [s for s in self.slots if s["is_toxic"] and s["banned_anim"] <= 0.0]
        if len(toxic_slots) < 2:
            # Seleccionar un slot sano y transformarlo en barra brava (excluyendo casillas recién martilladas)
            healthy_candidates = [s for s in self.slots if not s["is_toxic"] and s["banned_anim"] <= 0.0 and not s.get("just_banned", False)]
            if healthy_candidates:
                target_slot = random.choice(healthy_candidates)
                target_slot["is_toxic"] = True
                target_slot["sprite"] = random.choice(self.toxic_sprites) if self.toxic_sprites else None
                target_slot["timer"] = random.uniform(2.2, 3.8)
                target_slot["max_lifetime"] = target_slot["timer"]
        elif len(toxic_slots) > 3:
            # Si supera los 3, convertir el excedente en hincha sano
            excess_slot = random.choice(toxic_slots)
            excess_slot["is_toxic"] = False
            excess_slot["sprite"] = random.choice(self.healthy_sprites) if self.healthy_sprites else None

        # Limpiar flag de protección en el frame siguiente
        for s in self.slots:
            if s["banned_anim"] <= 0.0 and s.get("just_banned", False):
                s["just_banned"] = False

        # Actualizar partículas
        for p in self.particles[:]:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
            if p["life"] <= 0.0:
                self.particles.remove(p)

        # Textos flotantes
        for ft in self.floating_texts[:]:
            ft["y"] -= 60.0 * dt
            ft["life"] -= dt
            if ft["life"] <= 0.0:
                self.floating_texts.remove(ft)

        # Verificación de meta alcanzada antes del tiempo
        if self.bans_count >= self.TARGET_BANS:
            self.finish_game(won=True)

    def _spawn_random_spectator(self, lifetime: float) -> None:
        """Activa un slot vacío aleatorio rotando entre hinchas sanos y barras bravas tóxicos."""
        available = [s for s in self.slots if not s["active"] and s["banned_anim"] <= 0.0]
        if not available:
            return

        slot = random.choice(available)
        slot["active"] = True
        slot["timer"] = lifetime + random.uniform(-0.1, 0.2)
        slot["max_lifetime"] = slot["timer"]
        slot["popup_scale"] = 0.2
        slot["hit_innocent"] = False

        # Probabilidad de barra brava tóxico (55% tóxico, 45% hincha sano)
        is_toxic = random.random() < 0.55
        slot["is_toxic"] = is_toxic

        if is_toxic:
            slot["comment"] = random.choice(self.TOXIC_COMMENTS)
            slot["sprite"] = random.choice(self.toxic_sprites) if self.toxic_sprites else None
        else:
            slot["comment"] = random.choice(self.HEALTHY_COMMENTS)
            slot["sprite"] = random.choice(self.healthy_sprites) if self.healthy_sprites else None

    def handle_game_event(self, event: pygame.event.Event) -> None:
        """Maneja el martillo con Flechas del Teclado / WASD y Barra Espaciadora / Enter para golpear."""
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
                # Golpear la casilla actualmente seleccionada por las flechas
                self._on_hammer_strike(tuple(self.hammer_target_pos))

        # Soporte secundario opcional con mouse sin perder la orientación de flechas
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
        """Ejecuta el martillazo de moderación en la coordenada indicada."""
        self.hammer_swing_timer = 1.0

        if self.hammer_stun_timer > 0.0:
            # Martillo temporalmente aturdido por golpear a un inocente
            self._add_floating_text("¡MARTILLO BLOQUEADO!", pos[0], pos[1] - 30, (255, 120, 50))
            return

        # Buscar si impactó algún slot
        hit_any = False
        for s in self.slots:
            if s["rect"].collidepoint(pos) and s["banned_anim"] <= 0.0:
                hit_any = True
                if s["is_toxic"]:
                    # ¡Acierto! Barra brava moderado
                    self._handle_successful_ban(s, pos)
                else:
                    # ¡Falso positivo! Martilló a un hincha sano
                    self._handle_innocent_hit(s, pos)
                break

        if not hit_any:
            # Golpe en vacío
            self._add_smoke_particles(pos[0], pos[1], (180, 180, 180), count=6)

    def _handle_successful_ban(self, slot: Dict[str, Any], pos: Tuple[int, int]) -> None:
        """Modera con éxito a un barra brava."""
        self.bans_count += 1
        slot["banned_anim"] = 1.0  # Muestra sello BANEADO
        slot["just_banned"] = True  # Marca la casilla para que NO vuelva a salir un barra brava aquí al reaparecer

        # Game Feel: Screenshake no lineal + Hitstop
        self.trauma = min(1.0, self.trauma + 0.6)
        self.hit_stop_timer = 0.04  # 40ms de impacto crujiente

        # Partículas de Baneo cibernético (rojas y doradas)
        self._add_smoke_particles(pos[0], pos[1], (255, 30, 30), count=18)
        self._add_smoke_particles(pos[0], pos[1], (255, 215, 0), count=12)

        self._add_floating_text("+1 BANEADO", pos[0], pos[1] - 40, (255, 40, 40))

    def _handle_innocent_hit(self, slot: Dict[str, Any], pos: Tuple[int, int]) -> None:
        """Penalización: golpear a un hincha sano resta progreso (-1 gema de baneo) y aturde el martillo."""
        self.innocent_hits += 1

        # RESTAR BARRA DE PROGRESO (penalización directa por falso positivo)
        if self.bans_count > 0:
            self.bans_count -= 1

        # El martillo queda bloqueado 0.6s por falso positivo
        self.hammer_stun_timer = 0.60
        self.trauma = min(1.0, self.trauma + 0.45)

        # Partículas de error azul
        self._add_smoke_particles(pos[0], pos[1], (80, 160, 255), count=14)
        self._add_floating_text("-1 BARRITA (¡HINCHA SANO!)", pos[0], pos[1] - 40, (255, 90, 90))

    def _add_smoke_particles(self, x: float, y: float, color: Tuple[int, int, int], count: int = 10) -> None:
        """Genera partículas explosivas radiales."""
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(120, 380)
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
        """Inserta texto flotante con fade."""
        self.floating_texts.append({
            "text": text,
            "x": x,
            "y": y,
            "color": color,
            "life": 0.85,
            "max_life": 0.85,
        })

    def render_game(self, surface: pygame.Surface) -> None:
        """Renderizado desacoplado de la pantalla gigante y la cuadrícula 3x3."""
        # Aplicar Screenshake no lineal cuadrático
        shake_mag = (self.trauma ** 2) * self.max_shake_offset
        shake_x = int(random.uniform(-shake_mag, shake_mag)) if shake_mag > 0.1 else 0
        shake_y = int(random.uniform(-shake_mag, shake_mag)) if shake_mag > 0.1 else 0

        # Canvas interno con shake
        render_surf = surface
        if shake_x != 0 or shake_y != 0:
            render_surf = surface.copy()

        # 1. Fondo de la pantalla del Estadio
        if self.bg_surf:
            render_surf.blit(self.bg_surf, (0, 0))
        else:
            # Fallback elegante oscuro con gradiente
            render_surf.fill((18, 22, 35))
            pygame.draw.rect(render_surf, (28, 35, 55), (100, 100, self.screen_w - 200, self.screen_h - 150), border_radius=12)

        # 2. Marco LED Superior del Estadio Metropolitano
        self._render_led_header(render_surf)

        # 3. Renderizado de las 9 Casillas (3x3)
        for s in self.slots:
            self._render_slot(render_surf, s)

        # 4. Shader de pantalla LED (Scanlines + viñeta + flicker)
        if hasattr(self, "shader_surf"):
            render_surf.blit(self.shader_surf, (self.screen_rect.x, self.screen_rect.y))

        # 5. Partículas
        for p in self.particles:
            alpha = int(255 * (p["life"] / p["max_life"]))
            rad = max(1, int(p["radius"] * (p["life"] / p["max_life"])))
            s = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p["color"], alpha), (rad, rad), rad)
            render_surf.blit(s, (p["x"] - rad, p["y"] - rad))

        # 6. Textos flotantes
        for ft in self.floating_texts:
            alpha = int(255 * (ft["life"] / ft["max_life"]))
            txt_surf = self.font_status.render(ft["text"], True, ft["color"])
            txt_surf.set_alpha(alpha)
            render_surf.blit(txt_surf, (ft["x"] - txt_surf.get_width() // 2, ft["y"]))

        # 7. Renderizar Martillo en la posición del Cursor
        self._render_hammer(render_surf)

        # Si hubo shake, volcar al surface principal con el desplazamiento
        if shake_x != 0 or shake_y != 0:
            surface.fill((0, 0, 0))
            surface.blit(render_surf, (int(shake_x), int(shake_y)))

    def _render_led_header(self, surf: pygame.Surface) -> None:
        """
        Dibuja la barra de progreso de moderación con estética Cozy / Arcade pulida:
        - Barra más amplia y cómoda (780 px) para que el número final '10/10' quepa con holgura.
        - Sin iconos extraños o recortes artificiales a la izquierda.
        - Medidor segmentado de 10 ranuras tipo gemas de cristal esmaltado.
        - Tipografía limpia y moderna (Segoe UI Black / Trebuchet MS).
        """
        bar_w = 780
        bar_h = 46
        bar_x = (self.screen_w - bar_w) // 2
        bar_y = 48

        # 1. Sombra suave de caída (drop shadow orgánica)
        shadow_surf = pygame.Surface((bar_w + 24, bar_h + 24), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (10, 8, 25, 110), (8, 8, bar_w + 8, bar_h + 8), border_radius=24)
        surf.blit(shadow_surf, (bar_x - 12, bar_y - 8))

        # 2. Cápsula exterior (acabado esmaltado crema/azul noche suave)
        capsule_surf = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        pygame.draw.rect(capsule_surf, (26, 22, 48, 235), (0, 0, bar_w, bar_h), border_radius=23)
        # Borde exterior pastel suave
        pygame.draw.rect(capsule_surf, (225, 210, 248, 180), (0, 0, bar_w, bar_h), width=2, border_radius=23)

        # 3. Riel interior oscuro acogedor
        pad_left = 22
        pad_right = 110  # Espacio holgado reservado a la derecha para el texto '10/10'
        pad_y = 8
        track_w = bar_w - pad_left - pad_right
        track_h = bar_h - (pad_y * 2)
        pygame.draw.rect(capsule_surf, (15, 13, 30, 240), (pad_left, pad_y, track_w, track_h), border_radius=15)

        # 4. Segmentos tipo gemas (10 ranuras cómodas para los 10 baneos requeridos)
        total_segments = self.TARGET_BANS
        gap = 5
        seg_w = (track_w - (total_segments - 1) * gap - 8) // total_segments
        start_seg_x = pad_left + 4
        seg_y = pad_y + 4
        seg_h = track_h - 8

        for i in range(total_segments):
            sx = start_seg_x + i * (seg_w + gap)
            is_filled = (i < self.bans_count)

            if is_filled:
                # Segmento activo: degradado carmesí/dorado con brillo superior
                pygame.draw.rect(capsule_surf, (245, 75, 95), (sx, seg_y, seg_w, seg_h), border_radius=6)
                # Resalte de brillo cozy
                pygame.draw.rect(capsule_surf, (255, 190, 200), (sx + 2, seg_y + 2, seg_w - 4, seg_h // 3), border_radius=3)
                pygame.draw.rect(capsule_surf, (255, 245, 220), (sx, seg_y, seg_w, seg_h), width=1, border_radius=6)
            else:
                # Segmento vacío: hendidura tenue suave
                pygame.draw.rect(capsule_surf, (26, 23, 45), (sx, seg_y, seg_w, seg_h), border_radius=6)
                pygame.draw.rect(capsule_surf, (44, 39, 70), (sx, seg_y, seg_w, seg_h), width=1, border_radius=6)

        # 5. Indicador numérico estético y holgado a la derecha (ej. '10 / 10')
        num_str = f"{self.bans_count} / {self.TARGET_BANS}"
        col_text = (140, 255, 160) if self.bans_count >= self.TARGET_BANS else (255, 245, 225)
        txt_num = self.font_counter.render(num_str, True, col_text)
        txt_x = bar_w - pad_right + (pad_right - txt_num.get_width()) // 2
        txt_y = bar_h // 2 - txt_num.get_height() // 2
        capsule_surf.blit(txt_num, (txt_x, txt_y))

        # Volcar cápsula terminada a la pantalla
        surf.blit(capsule_surf, (bar_x, bar_y))

    def _render_slot(self, surf: pygame.Surface, slot: Dict[str, Any]) -> None:
        """
        Dibuja el espectador en su panel correspondiente:
        - Fondo blanco/marfil del monitor ocupando el tamaño COMPLETO del recuadro (rect).
        - El sprite original permanece en su tamaño cuadradito (1:1) centrado dentro del recuadro.
        - Foco dinámico y estampilla de baneo integrados.
        """
        rect: pygame.Rect = slot["rect"]

        # 1. Fondito blanco/marfil del monitor que abarca todo el tamaño del recuadro
        # Proporciona alto contraste y soporte estructural con las dimensiones reales del panel
        bg_card = (248, 246, 242)
        pygame.draw.rect(surf, bg_card, rect, border_radius=10)
        # Sombra interior biselada suave
        pygame.draw.rect(surf, (220, 215, 205), rect, width=3, border_radius=10)
        # Borde exterior delimitador
        pygame.draw.rect(surf, (40, 35, 65), rect, width=2, border_radius=10)

        # 2. Resaltador focal en la casilla seleccionada con flechas (pulso sutil)
        is_focused = (slot["row"] == self.grid_row and slot["col"] == self.grid_col)
        if is_focused:
            focus_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pulse = int(170 + 70 * math.sin(pygame.time.get_ticks() / 110.0))
            pygame.draw.rect(focus_surf, (255, 220, 50, 45), (0, 0, rect.width, rect.height), border_radius=10)
            pygame.draw.rect(focus_surf, (255, 200, 40, pulse), (0, 0, rect.width, rect.height), width=4, border_radius=10)
            surf.blit(focus_surf, (rect.x, rect.y))

        # 3. Renderizado del espectador cuadrado (1:1) perfectamente centrado
        if slot["sprite"]:
            spr = slot["sprite"]
            sx = rect.centerx - spr.get_width() // 2
            sy = rect.centery - spr.get_height() // 2
            surf.blit(spr, (sx, sy))

        # 4. Estampilla de baneo si acaba de ser martillado
        if slot["banned_anim"] > 0.0:
            stamp_w = 210
            stamp_h = 56
            stamp_surf = pygame.Surface((stamp_w, stamp_h), pygame.SRCALPHA)
            pygame.draw.rect(stamp_surf, (220, 20, 30, 235), (0, 0, stamp_w, stamp_h), border_radius=8)
            pygame.draw.rect(stamp_surf, (255, 255, 255, 245), (0, 0, stamp_w, stamp_h), width=3, border_radius=8)
            t_ban = self.font_badge.render("[ BANEADO ]", True, (255, 255, 255))
            stamp_surf.blit(t_ban, (stamp_w // 2 - t_ban.get_width() // 2, stamp_h // 2 - t_ban.get_height() // 2))

            rot_stamp = pygame.transform.rotate(stamp_surf, -10.0)
            surf.blit(rot_stamp, (rect.centerx - rot_stamp.get_width() // 2, rect.centery - rot_stamp.get_height() // 2))

    def _render_hammer(self, surf: pygame.Surface) -> None:
        """Renderiza el sprite oficial del Martillo de Baneo en la casilla enfocada."""
        rot_hammer = pygame.transform.rotate(self.hammer_surf, self.hammer_angle)
        # Offset visual para que la cabeza del martillo golpee el centro exacto de la casilla
        hx = self.hammer_pos[0] - rot_hammer.get_width() // 2 + 15
        hy = self.hammer_pos[1] - rot_hammer.get_height() // 2 - 25

        # Si está en cooldown/aturdido tras falso positivo, parpadeo sutil de advertencia
        if self.hammer_stun_timer > 0.0:
            if int(pygame.time.get_ticks() / 80) % 2 == 0:
                rot_hammer.set_alpha(100)
            else:
                rot_hammer.set_alpha(210)

        surf.blit(rot_hammer, (hx, hy))
