import math
import random
from typing import Optional, Callable, List
import pygame

from core.microgame import BaseMicrogame

class BatallaFloresBossMicrogame(BaseMicrogame):
    """
    Etapa Jefe (Boss Stage): '¡LA GRAN GUACHERNA Y BATALLA DE FLORES!'
    - Tiempo límite extendido: 15.0 segundos.
    - Fase 1 (15.0s - 10.0s): ¡ESQUIVA LA MAICENA Y ESPUMA!
      El jugador desfila por la Vía 40 y debe esquivar proyectiles festivos moviéndose con A/D,
      flechas o stick analógico.
    - Fase 2 (10.0s - 5.0s): ¡REPIQUE DE TAMBORA!
      Golpea ESPACIO / Botón A al compás de la percusión cumbiera cuando el aro concéntrico
      alcance el tambor central.
    - Fase 3 (5.0s - 0.0s): ¡ATRAPA LA CORONA REAL!
      La carroza lanza la Corona Dorada del Carnaval al aire. Posiciónate debajo y salta
      para atraparla y consagrarte como Rey Momo de BarranquillaWare.
    """
    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡BATALLA DE FLORES!",
            time_limit=15.0,
            on_complete_callback=on_complete_callback
        )

    def enter(self, params: Optional[dict] = None) -> None:
        # Canción de fondo de la batalla de flores
        self.audio.play_bgm("BatallaDeFloresMusic.mp3")

    def setup_game(self) -> None:
        # 1. Jugador
        self.player_x = 960.0
        self.player_y = 820.0
        self.player_vx = 0.0
        self.player_speed = 680.0
        self.player_is_jumping = False
        self.player_jump_y = 0.0
        self.player_jump_vy = 0.0
        self.player_hit_stun = 0.0
        self.player_health = 3

        # Cargar sprite de personaje activo
        self.player_sprite = None
        try:
            sprite_name = f"{self.character_id}_seleccion_personaje.png"
            raw_s = self.assets.load_surface(sprite_name, has_alpha=True)
            mask = pygame.mask.from_surface(raw_s)
            rects = mask.get_bounding_rects()
            cropped = raw_s.subsurface(rects[0]) if rects else raw_s
            th = 230
            tw = int(cropped.get_width() * (th / float(cropped.get_height())))
            self.player_sprite = pygame.transform.smoothscale(cropped, (tw, th))
        except Exception:
            pass

        # 2. Fase 1: Proyectiles festivos (Maicena y Espuma)
        self.projectiles: List[dict] = []
        self.proj_spawn_timer = 0.0

        # 3. Fase 2: Repique de tambora
        self.rhythm_notes: List[dict] = []
        self.rhythm_score = 0
        self.rhythm_target_score = 4
        self.rhythm_spawn_timer = 0.0
        self.rhythm_drum_pulse = 0.0
        self.rhythm_feedback_text = ""
        self.rhythm_feedback_color = (255, 255, 255)
        self.rhythm_feedback_timer = 0.0

        # 4. Fase 3: Corona real
        self.crown_x = 960.0
        self.crown_y = -100.0
        self.crown_vx = 45.0
        self.crown_vy = 0.0
        self.crown_gravity = 340.0
        self.crown_caught = False
        self.crown_sparkles: List[dict] = []

        # 5. Efectos de Game Feel
        self.screen_shake = 0.0
        self.hit_stop = 0.0
        self.confetti: List[dict] = []
        for _ in range(80):
            self.confetti.append({
                "x": random.uniform(0, 1920),
                "y": random.uniform(-1080, 0),
                "vx": random.uniform(-30, 30),
                "vy": random.uniform(120, 320),
                "rot": random.uniform(0, 360),
                "vrot": random.uniform(-180, 180),
                "color": random.choice([
                    (255, 220, 40),   # Amarillo Carnaval
                    (30, 100, 240),   # Azul Mar
                    (235, 45, 55),    # Rojo Torito
                    (45, 215, 95)     # Verde Cumbia
                ]),
                "size": random.uniform(8, 16)
            })

        # Tipografías
        self.font_phase = pygame.font.SysFont("Arial Black, Impact, sans-serif", 52)
        self.font_sub = pygame.font.SysFont("Arial, sans-serif", 28, bold=True)
        self.font_hud = pygame.font.SysFont("Arial Black, Impact, sans-serif", 32)

    def _get_current_boss_subphase(self) -> int:
        """Determina la fase actual del combate (1, 2 o 3) según el tiempo restante."""
        if self.time_left > 10.0:
            return 1  # Esquiva maicena
        elif self.time_left > 5.0:
            return 2  # Ritmo tambora
        else:
            return 3  # Atrapa corona

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if self.phase != self.PHASE_PLAY or self.is_finished:
            return

        subphase = self._get_current_boss_subphase()

        # Teclas de movimiento continuo
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                if subphase == 3 and not self.player_is_jumping:
                    self.player_is_jumping = True
                    self.player_jump_vy = -680.0
                elif subphase == 2:
                    self._check_rhythm_hit()

            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.player_vx = -self.player_speed
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.player_vx = self.player_speed

        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_LEFT, pygame.K_a) and self.player_vx < 0:
                self.player_vx = 0.0
            elif event.key in (pygame.K_RIGHT, pygame.K_d) and self.player_vx > 0:
                self.player_vx = 0.0

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if subphase == 3 and not self.player_is_jumping:
                self.player_is_jumping = True
                self.player_jump_vy = -680.0
            elif subphase == 2:
                self._check_rhythm_hit()

    def _check_rhythm_hit(self) -> None:
        """Verifica la precisión rítmica al golpear la tambora."""
        hit_found = False
        for note in self.rhythm_notes:
            if not note["hit"]:
                # Radio objetivo del tambor es 110 px
                dist = abs(note["radius"] - 110.0)
                if dist < 42.0:
                    note["hit"] = True
                    hit_found = True
                    self.rhythm_score += 1
                    self.rhythm_drum_pulse = 1.0
                    self.screen_shake = 5.0
                    if hasattr(self.audio, "play_drum"):
                        self.audio.play_drum()

                    if dist < 18.0:
                        self.rhythm_feedback_text = "¡SABOR PERFECTO!"
                        self.rhythm_feedback_color = (255, 235, 60)
                    else:
                        self.rhythm_feedback_text = "¡BIEN TOCADO!"
                        self.rhythm_feedback_color = (100, 255, 140)
                    self.rhythm_feedback_timer = 0.7
                    break

        if not hit_found:
            self.rhythm_feedback_text = "¡A DESTIEMPO!"
            self.rhythm_feedback_color = (255, 100, 100)
            self.rhythm_feedback_timer = 0.5

    def update_game(self, dt: float) -> None:
        if self.hit_stop > 0.0:
            self.hit_stop = max(0.0, self.hit_stop - dt)
            return

        if self.screen_shake > 0.0:
            self.screen_shake = max(0.0, self.screen_shake - dt * 25.0)

        # Actualizar lluvia de confeti continua
        for p in self.confetti:
            p["y"] += p["vy"] * dt
            p["x"] += p["vx"] * dt + math.sin(self.time_left * 4.0 + p["y"] * 0.02) * 20.0 * dt
            p["rot"] += p["vrot"] * dt
            if p["y"] > 1100:
                p["y"] = -40
                p["x"] = random.uniform(0, 1920)

        subphase = self._get_current_boss_subphase()

        # 1. Movimiento del Jugador
        keys = pygame.key.get_pressed()
        move_dir = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move_dir -= 1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move_dir += 1.0

        if move_dir != 0.0:
            self.player_x += move_dir * self.player_speed * dt
        else:
            self.player_x += self.player_vx * dt

        # Límites de la pista del desfile (Vía 40)
        self.player_x = max(260.0, min(1660.0, self.player_x))

        # Física de Salto
        if self.player_is_jumping:
            self.player_jump_y += self.player_jump_vy * dt
            self.player_jump_vy += 1500.0 * dt  # Gravedad
            if self.player_jump_y >= 0.0:
                self.player_jump_y = 0.0
                self.player_is_jumping = False

        if self.player_hit_stun > 0.0:
            self.player_hit_stun = max(0.0, self.player_hit_stun - dt)

        # -------------------------------------------------------------
        # FASE 1: ESQUIVAR PROYECTILES (MAICENA Y ESPUMA)
        # -------------------------------------------------------------
        if subphase == 1:
            self.proj_spawn_timer += dt
            if self.proj_spawn_timer >= 0.42:
                self.proj_spawn_timer = 0.0
                p_type = random.choice(["maicena", "espuma", "harina"])
                self.projectiles.append({
                    "x": random.uniform(320, 1600),
                    "y": -50.0,
                    "vy": random.uniform(520, 750),
                    "vx": random.uniform(-60, 60),
                    "type": p_type,
                    "radius": random.uniform(22, 34)
                })

            # Actualizar proyectiles
            for p in self.projectiles[:]:
                p["y"] += p["vy"] * dt
                p["x"] += p["vx"] * dt

                # Colisión con el jugador
                p_rect = pygame.Rect(self.player_x - 50, self.player_y - 120 + self.player_jump_y, 100, 140)
                if p_rect.collidepoint(p["x"], p["y"]) and self.player_hit_stun <= 0.0:
                    self.player_hit_stun = 0.6
                    self.player_health = max(0, self.player_health - 1)
                    self.screen_shake = 12.0
                    self.hit_stop = 0.06
                    self.projectiles.remove(p)
                    if self.player_health <= 0:
                        self.finish_game(False)
                        return
                    continue

                if p["y"] > 1150:
                    self.projectiles.remove(p)

        # -------------------------------------------------------------
        # FASE 2: RITMO Y REPIQUE DE TAMBORA
        # -------------------------------------------------------------
        elif subphase == 2:
            self.rhythm_spawn_timer += dt
            if self.rhythm_spawn_timer >= 1.05 and len(self.rhythm_notes) < 5:
                self.rhythm_spawn_timer = 0.0
                self.rhythm_notes.append({
                    "radius": 340.0,
                    "speed": 230.0,
                    "hit": False,
                    "missed": False
                })

            for note in self.rhythm_notes:
                if not note["hit"] and not note["missed"]:
                    note["radius"] -= note["speed"] * dt
                    if note["radius"] < 65.0:
                        note["missed"] = True

            if self.rhythm_drum_pulse > 0.0:
                self.rhythm_drum_pulse = max(0.0, self.rhythm_drum_pulse - dt * 3.5)

            if self.rhythm_feedback_timer > 0.0:
                self.rhythm_feedback_timer = max(0.0, self.rhythm_feedback_timer - dt)

        # -------------------------------------------------------------
        # FASE 3: ATRAPAR LA CORONA DEL CARNAVAL
        # -------------------------------------------------------------
        elif subphase == 3:
            if self.crown_y < -50.0:
                self.crown_y = 120.0
                self.crown_x = random.uniform(600, 1320)
                self.crown_vy = -80.0
                self.crown_vx = random.uniform(-40, 40)

            if not self.crown_caught:
                self.crown_y += self.crown_vy * dt
                self.crown_vy += self.crown_gravity * dt
                self.crown_x += self.crown_vx * dt

                # Destellos de la corona dorada
                if random.random() < 0.4:
                    self.crown_sparkles.append({
                        "x": self.crown_x + random.uniform(-30, 30),
                        "y": self.crown_y + random.uniform(-20, 20),
                        "life": 0.5,
                        "size": random.uniform(4, 9)
                    })

                # Colisión / Captura con la cabeza del jugador
                p_head_rect = pygame.Rect(self.player_x - 60, self.player_y - 140 + self.player_jump_y, 120, 90)
                if p_head_rect.collidepoint(self.crown_x, self.crown_y):
                    self.crown_caught = True
                    self.screen_shake = 22.0
                    self.hit_stop = 0.18
                    if hasattr(self.audio, "play_whistle"):
                        self.audio.play_whistle()
                    self.finish_game(True)
                    return

                # Si la corona toca el suelo sin ser atrapada: Fallo
                if self.crown_y > 900.0:
                    self.finish_game(False)
                    return

        # Actualizar destellos
        for sp in self.crown_sparkles[:]:
            sp["life"] -= dt
            if sp["life"] <= 0.0:
                self.crown_sparkles.remove(sp)

    def render_game(self, surface: pygame.Surface) -> None:
        # Offset por Screen Shake
        ox = random.uniform(-self.screen_shake, self.screen_shake) if self.screen_shake > 0 else 0
        oy = random.uniform(-self.screen_shake, self.screen_shake) if self.screen_shake > 0 else 0

        render_surf = pygame.Surface((self.screen_w, self.screen_h))

        # 1. Fondo: Desfile de la Vía 40 con tribunas coloridas
        render_surf.fill((110, 160, 230))  # Cielo soleado barranquillero

        # Río Magdalena y horizonte al fondo
        pygame.draw.rect(render_surf, (80, 130, 185), (0, 340, self.screen_w, 120))

        # Tribunas y palcos festivos
        pygame.draw.rect(render_surf, (245, 195, 45), (0, 420, self.screen_w, 140))
        # Público animado en los palcos
        for i in range(0, self.screen_w, 28):
            bob = math.sin(self.time_left * 8.0 + i) * 6
            shirt_col = [(235, 40, 40), (255, 220, 30), (30, 110, 220), (40, 180, 70)][(i // 28) % 4]
            pygame.draw.circle(render_surf, (240, 190, 160), (i + 14, int(470 + bob)), 10)
            pygame.draw.rect(render_surf, shirt_col, (i + 4, int(480 + bob), 20, 25))

        # Pavimento de la Vía 40 (Cumbia Arena)
        pygame.draw.polygon(render_surf, (65, 70, 80), [
            (0, 560), (self.screen_w, 560),
            (self.screen_w, self.screen_h), (0, self.screen_h)
        ])
        # Líneas de desfile amarillas y rojas
        pygame.draw.line(render_surf, (250, 215, 30), (0, 700), (self.screen_w, 700), 6)
        pygame.draw.line(render_surf, (235, 50, 50), (0, 715), (self.screen_w, 715), 4)

        # 2. Renderizado de Confeti Ambiental
        for p in self.confetti:
            surf_c = pygame.Surface((int(p["size"]), int(p["size"])), pygame.SRCALPHA)
            surf_c.fill(p["color"])
            rot_c = pygame.transform.rotate(surf_c, p["rot"])
            render_surf.blit(rot_c, (p["x"], p["y"]))

        subphase = self._get_current_boss_subphase()

        # 3. Renderizado de Elementos de Fase
        if subphase == 1:
            # Proyectiles (Maicena, Espuma)
            for p in self.projectiles:
                if p["type"] == "espuma":
                    pygame.draw.circle(render_surf, (210, 240, 255), (int(p["x"]), int(p["y"])), int(p["radius"]))
                    pygame.draw.circle(render_surf, (255, 255, 255), (int(p["x"] - 4), int(p["y"] - 4)), int(p["radius"] * 0.6))
                else:
                    # Nube de maicena/harina blanca
                    for ox_m, oy_m in [(-8, -4), (8, -2), (0, 6)]:
                        pygame.draw.circle(render_surf, (245, 245, 240), (int(p["x"] + ox_m), int(p["y"] + oy_m)), int(p["radius"] * 0.75))

        elif subphase == 2:
            # Tambor Gigante en el centro
            center_x, center_y = 960, 480
            drum_scale = 1.0 + self.rhythm_drum_pulse * 0.22
            r_outer = int(120 * drum_scale)
            r_target = 110

            # Aro objetivo dorado
            pygame.draw.circle(render_surf, (255, 220, 50), (center_x, center_y), r_target + 6, 4)
            # Tambor cuerpo
            pygame.draw.circle(render_surf, (150, 75, 35), (center_x, center_y), r_outer)
            pygame.draw.circle(render_surf, (245, 220, 180), (center_x, center_y), int(r_outer * 0.85))
            pygame.draw.circle(render_surf, (120, 60, 25), (center_x, center_y), int(r_outer * 0.85), 3)

            # Círculos rítmicos que se acercan
            for note in self.rhythm_notes:
                if not note["hit"] and not note["missed"]:
                    r_curr = max(10, int(note["radius"]))
                    col = (255, 240, 80) if abs(r_curr - r_target) < 25 else (255, 255, 255)
                    pygame.draw.circle(render_surf, col, (center_x, center_y), r_curr, 5)

            # Feedback de golpe de tambor
            if self.rhythm_feedback_timer > 0.0:
                txt_f = self.font_phase.render(self.rhythm_feedback_text, True, self.rhythm_feedback_color)
                rect_f = txt_f.get_rect(center=(center_x, center_y - 180))
                render_surf.blit(txt_f, rect_f)

        elif subphase == 3:
            # Destellos dorados
            for sp in self.crown_sparkles:
                pygame.draw.circle(render_surf, (255, 255, 180), (int(sp["x"]), int(sp["y"])), int(sp["size"]))

            # Corona Dorada Real del Carnaval
            cx, cy = int(self.crown_x), int(self.crown_y)
            # Resplandor áureo
            glow_surf = pygame.Surface((140, 100), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surf, (255, 220, 50, 80), (0, 0, 140, 100))
            render_surf.blit(glow_surf, (cx - 70, cy - 50))

            # Base de la corona y puntas
            crown_pts = [
                (cx - 45, cy + 20),
                (cx - 50, cy - 25),
                (cx - 22, cy - 5),
                (cx, cy - 38),       # Punta más alta
                (cx + 22, cy - 5),
                (cx + 50, cy - 25),
                (cx + 45, cy + 20)
            ]
            pygame.draw.polygon(render_surf, (25, 20, 10), crown_pts) # Borde
            pygame.draw.polygon(render_surf, (255, 215, 30), [
                (p[0] * 0.96 + cx * 0.04, p[1] * 0.96 + cy * 0.04) for p in crown_pts
            ])
            # Gemas reales (Rubíes y Esmeraldas)
            pygame.draw.circle(render_surf, (220, 30, 40), (cx, cy - 22), 7)
            pygame.draw.circle(render_surf, (30, 180, 80), (cx - 30, cy - 10), 6)
            pygame.draw.circle(render_surf, (30, 180, 80), (cx + 30, cy - 10), 6)

        # 4. Renderizado del Jugador
        py = int(self.player_y + self.player_jump_y)
        px = int(self.player_x)

        # Sombra de contacto
        shadow_w = max(40, int(110 * (1.0 - abs(self.player_jump_y) / 500.0)))
        shadow_surf = pygame.Surface((shadow_w, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (20, 25, 35, 100), (0, 0, shadow_w, 24))
        render_surf.blit(shadow_surf, (px - shadow_w // 2, int(self.player_y + 80)))

        # Sprite del personaje
        if self.player_sprite:
            sw = self.player_sprite.get_width()
            sh = self.player_sprite.get_height()
            draw_x = px - sw // 2
            draw_y = py - sh // 2

            # Efecto de hit stun (parpadeo rojo)
            if self.player_hit_stun > 0.0 and int(self.time_left * 18.0) % 2 == 0:
                tinted = self.player_sprite.copy()
                tinted.fill((255, 80, 80, 160), special_flags=pygame.BLEND_RGBA_MULT)
                render_surf.blit(tinted, (draw_x, draw_y))
            else:
                render_surf.blit(self.player_sprite, (draw_x, draw_y))
        else:
            # Fallback geométrico cartoon
            pygame.draw.rect(render_surf, (40, 120, 220), (px - 35, py - 90, 70, 110), border_radius=12)
            pygame.draw.circle(render_surf, (240, 190, 160), (px, py - 125), 32)

        # 5. Interfaz HUD Superior del Boss Stage
        # Barra de progreso de fases (1, 2, 3)
        hud_bg = pygame.Rect(460, 24, 1000, 76)
        pygame.draw.rect(render_surf, (20, 25, 35, 220), hud_bg, border_radius=16)
        pygame.draw.rect(render_surf, (255, 215, 30), hud_bg, width=3, border_radius=16)

        phase_titles = [
            "FASE 1: ¡ESQUIVA LA HARINA!",
            "FASE 2: ¡TOCA LA TAMBORA!",
            "FASE 3: ¡ATRAPA LA CORONA!"
        ]
        curr_title = phase_titles[subphase - 1]
        txt_phase = self.font_hud.render(curr_title, True, (255, 230, 80))
        render_surf.blit(txt_phase, (hud_bg.centerx - txt_phase.get_width() // 2, hud_bg.y + 10))

        # Indicador de Vidas / Energía (Sombreros Vueltiaos)
        for h in range(3):
            hx = hud_bg.x + 30 + h * 45
            hy = hud_bg.centery
            col = (255, 215, 30) if h < self.player_health else (80, 85, 95)
            pygame.draw.ellipse(render_surf, col, (hx - 16, hy - 10, 32, 20))
            pygame.draw.ellipse(render_surf, (25, 25, 30), (hx - 10, hy - 7, 20, 14))

        # Indicador de Tiempo Restante del Boss (15s)
        time_bar_w = int(220 * (self.time_left / self.time_limit))
        pygame.draw.rect(render_surf, (40, 45, 55), (hud_bg.right - 250, hud_bg.centery - 10, 220, 20), border_radius=8)
        pygame.draw.rect(render_surf, (255, 80, 80), (hud_bg.right - 250, hud_bg.centery - 10, time_bar_w, 20), border_radius=8)

        # Blit final con Screenshake
        surface.blit(render_surf, (int(ox), int(oy)))
