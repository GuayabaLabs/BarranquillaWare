import math
import random
from typing import Optional, Callable, List, Type, Tuple
import pygame

from core.state_machine import BaseState
from core.microgame import BaseMicrogame
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.settings import SettingsManager
from ui.button import UIButton

# Microjuegos disponibles en el Modo Arcade
from microgames.mallorquin_photo import MallorquinPhotoMicrogame
from microgames.uninorte_sprint import UninorteSprintMicrogame
from microgames.ventana_colores import VentanaColoresMicrogame
from microgames.malecon_rueda import MaleconRuedaMicrogame
from microgames.metropolitano_penalty import MetropolitanoPenaltyMicrogame
from microgames.aeropuerto_aterrizaje import AeropuertoAterrizajeMicrogame
from microgames.batalla_flores_boss import BatallaFloresBossMicrogame
from microgames.fritanga_84 import Fritanga84Microgame
from microgames.troja_baile import TrojaBaileMicrogame

class ArcadeModeScene(BaseState):
    """
    Modo Arcade WarioWare ('Frenesí Caribeño'):
    - Cadena ininterrumpida de microjuegos aleatorios.
    - 4 vidas (Máscaras de Marimonda).
    - Velocidad creciente (+15% cada 4 rondas superadas).
    - Intersticio de 1.4s con conteo de ronda, velocidad y reacción del personaje.
    - Pantalla de Game Over con persistencia de récord en settings.json.
    """
    STATE_INTERSTITIAL = "interstitial"
    STATE_RESULT = "result"
    STATE_GAME_OVER = "game_over"

    def __init__(
        self,
        character_id: str = "westcol",
        on_exit_callback: Optional[Callable[[], None]] = None
    ) -> None:
        super().__init__()
        self.screen_w = 1920
        self.screen_h = 1080
        self.character_id = character_id
        self.on_exit_callback = on_exit_callback

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()
        self.settings = SettingsManager.get_instance()

        # Pool de microjuegos disponibles
        self.microgame_pool: List[Type[BaseMicrogame]] = [
            MallorquinPhotoMicrogame,
            UninorteSprintMicrogame,
            VentanaColoresMicrogame,
            MaleconRuedaMicrogame,
            MetropolitanoPenaltyMicrogame,
            AeropuertoAterrizajeMicrogame,
            Fritanga84Microgame,
            TrojaBaileMicrogame
        ]

        # Estado del juego Arcade
        self.max_lives = 4
        self.lives = self.max_lives
        self.score = 0
        self.round_num = 1
        self.speed_multiplier = 1.0

        # Sub-estados y temporizadores
        self.phase = self.STATE_INTERSTITIAL
        self.phase_timer = 0.0
        self.interstitial_duration = 1.4
        self.result_duration = 0.9

        # Historial de ronda previa
        self.last_won: bool = True
        self.speed_just_increased: bool = False
        self.is_new_record: bool = False

        # Efectos visuales de Game Feel
        self.screenshake_amp = 0.0
        self.screenshake_time = 0.0
        self.confetti_particles = []

        # Tipografías
        self.font_huge = pygame.font.SysFont("Arial Black, Impact, sans-serif", 68)
        self.font_title = pygame.font.SysFont("Arial Black, Impact, sans-serif", 46)
        self.font_sub = pygame.font.SysFont("Arial Black, Impact, sans-serif", 28)
        self.font_btn = pygame.font.SysFont("Arial Black, Impact, sans-serif", 24)
        self.font_rec = pygame.font.SysFont("Arial Black, Impact", 20)

        # Caché de superficies de fondo y efectos (evita asignaciones 1920x1080 por frame)
        self._bg_normal = self._build_gradient_bg((30, 20, 45), (15, 10, 25))
        self._bg_danger = self._build_gradient_bg((55, 15, 20), (30, 8, 12))
        self._frame_surf = pygame.Surface((self.screen_w, self.screen_h))
        self._ray_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        self._confetti_cache: dict = {}

        # Superficie de vida (Máscara de Marimonda estilizada)
        self.mask_life_surf = self._create_marimonda_mask_surf(is_broken=False)
        self.mask_dead_surf = self._create_marimonda_mask_surf(is_broken=True)

        # Cargar sprite del personaje
        self._load_character_sprite()

        # Botones de Game Over
        self._init_game_over_buttons()

    def _create_marimonda_mask_surf(self, is_broken: bool = False) -> pygame.Surface:
        mw, mh = 64, 76
        surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        col_face = (245, 140, 45) if not is_broken else (110, 115, 125)
        col_nose = (255, 60, 95) if not is_broken else (75, 80, 90)
        col_ear = (50, 190, 240) if not is_broken else (90, 95, 105)

        # Orejas grandes de Marimonda
        pygame.draw.circle(surf, col_ear, (12, 30), 12)
        pygame.draw.circle(surf, col_ear, (mw - 12, 30), 12)
        # Cabeza
        pygame.draw.ellipse(surf, col_face, (10, 12, mw - 20, mh - 24))
        pygame.draw.ellipse(surf, (20, 25, 35), (10, 12, mw - 20, mh - 24), width=3)
        # Ojos grandes cósmicos
        pygame.draw.circle(surf, (255, 255, 255), (22, 28), 9)
        pygame.draw.circle(surf, (255, 255, 255), (mw - 22, 28), 9)
        pygame.draw.circle(surf, (20, 20, 20), (22, 28), 4)
        pygame.draw.circle(surf, (20, 20, 20), (mw - 22, 28), 4)
        # Nariz larga de trompeta hacia abajo
        pts_nose = [(mw // 2 - 6, 36), (mw // 2 + 6, 36), (mw // 2 + 10, mh - 6), (mw // 2 - 10, mh - 6)]
        pygame.draw.polygon(surf, col_nose, pts_nose)
        pygame.draw.polygon(surf, (20, 25, 35), pts_nose, width=2)

        if is_broken:
            # Grietas de vida perdida
            pygame.draw.line(surf, (230, 60, 60), (14, 18), (mw - 14, mh - 18), 3)
            pygame.draw.line(surf, (230, 60, 60), (mw - 14, 18), (14, mh - 18), 3)

        return surf

    def _load_character_sprite(self) -> None:
        sprite_filename = f"{self.character_id}_seleccion_personaje.png"
        try:
            raw = self.assets.load_surface(sprite_filename, has_alpha=True)
            mask = pygame.mask.from_surface(raw)
            rects = mask.get_bounding_rects()
            cropped = raw.subsurface(rects[0]) if rects else raw
            target_h = 320
            target_w = int(cropped.get_width() * (target_h / float(cropped.get_height())))
            self.character_sprite = pygame.transform.smoothscale(cropped, (target_w, target_h))
        except Exception:
            self.character_sprite = pygame.Surface((150, 320), pygame.SRCALPHA)
            pygame.draw.rect(self.character_sprite, (220, 160, 60), (0, 0, 150, 320), border_radius=20)

    def _init_game_over_buttons(self) -> None:
        def make_btn(text: str, bg_col: Tuple[int, int, int], b_col: Tuple[int, int, int]) -> pygame.Surface:
            bw, bh = 320, 58
            surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(surf, bg_col, (0, 0, bw, bh), border_radius=16)
            pygame.draw.rect(surf, b_col, (0, 0, bw, bh), width=3, border_radius=16)
            txt = self.font_btn.render(text, True, (255, 255, 255))
            surf.blit(txt, txt.get_rect(center=(bw // 2, bh // 2)))
            return surf

        self.btn_retry = UIButton(
            center_pos=(self.screen_w // 2 - 180, 780),
            normal_sprite=make_btn("REINTENTAR", (35, 140, 70), (110, 245, 150)),
            on_click=self._restart_arcade
        )
        self.btn_exit = UIButton(
            center_pos=(self.screen_w // 2 + 180, 780),
            normal_sprite=make_btn("SALIR AL MENÚ", (160, 45, 45), (245, 110, 110)),
            on_click=self._exit_arcade
        )

    def _restart_arcade(self) -> None:
        self.lives = self.max_lives
        self.score = 0
        self.round_num = 1
        self.speed_multiplier = 1.0
        self.phase = self.STATE_INTERSTITIAL
        self.phase_timer = 0.0
        self.is_new_record = False
        self.speed_just_increased = False

    def _exit_arcade(self) -> None:
        if self.on_exit_callback:
            self.on_exit_callback()

    def enter(self, params: Optional[dict] = None) -> None:
        if params and "character_id" in params:
            self.character_id = params["character_id"]
            self._load_character_sprite()
        self._restart_arcade()
        # La música entre rondas la deja puesta el último minijuego
        # self.audio.play_bgm("dodo_airlines_acnh_ost_seleccion_modo.ogg")

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.phase == self.STATE_GAME_OVER:
            self.btn_retry.handle_event(event)
            self.btn_exit.handle_event(event)

    def update(self, dt: float) -> None:
        self.phase_timer += dt

        # Screenshake update
        if self.screenshake_time > 0.0:
            self.screenshake_time -= dt
            if self.screenshake_time <= 0.0:
                self.screenshake_amp = 0.0

        # Partículas de confeti
        for cf in self.confetti_particles:
            cf["x"] += cf["vx"] * dt
            cf["y"] += cf["vy"] * dt
            cf["life"] -= dt * 1.2

        if self.phase == self.STATE_INTERSTITIAL:
            if self.phase_timer >= self.interstitial_duration:
                self._launch_next_microgame()

        elif self.phase == self.STATE_RESULT:
            if self.phase_timer >= self.result_duration:
                if self.lives <= 0:
                    self._enter_game_over()
                else:
                    self.phase = self.STATE_INTERSTITIAL
                    self.phase_timer = 0.0

        elif self.phase == self.STATE_GAME_OVER:
            self.btn_retry.update(dt)
            self.btn_exit.update(dt)

    def _launch_next_microgame(self) -> None:
        """Elige un microjuego al azar o etapa jefe cada 10 rondas y lo ejecuta en la máquina de estados."""
        is_boss_stage = (self.round_num > 1 and self.round_num % 10 == 0)

        if is_boss_stage:
            chosen_cls = BatallaFloresBossMicrogame
        else:
            chosen_cls = random.choice(self.microgame_pool)

        microgame = chosen_cls(
            character_id=self.character_id,
            on_complete_callback=self._on_microgame_result
        )

        # Ajustar límite de tiempo según velocidad actual (los jefes mantienen su duración de 15s)
        if not is_boss_stage:
            microgame.time_limit = max(1.8, 4.0 / self.speed_multiplier)
        else:
            microgame.time_limit = 15.0

        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(microgame)

    def _on_microgame_result(self, won: bool) -> None:
        """Callback al terminar el microjuego."""
        self.last_won = won
        self.phase = self.STATE_RESULT
        self.phase_timer = 0.0
        self.speed_just_increased = False

        is_boss_round = (self.round_num > 1 and self.round_num % 10 == 0)

        if won:
            self.score += 1
            self.round_num += 1
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()

            # Victoria en Boss Stage recompensa restaurando 1 vida
            if is_boss_round and self.lives < self.max_lives:
                self.lives += 1
                self._spawn_celebration_confetti()

            # Cada 4 microjuegos ganados, aumentar la velocidad
            if self.score > 0 and self.score % 4 == 0:
                self.speed_multiplier = min(2.1, self.speed_multiplier + 0.15)
                self.speed_just_increased = True
                self._spawn_celebration_confetti()
        else:
            self.lives -= 1
            self.round_num += 1
            self.screenshake_amp = 18.0
            self.screenshake_time = 0.25

        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(self)

    def _enter_game_over(self) -> None:
        self.phase = self.STATE_GAME_OVER
        self.is_new_record = self.settings.update_arcade_high_score(self.score)
        self.screenshake_amp = 22.0
        self.screenshake_time = 0.35

    def _spawn_celebration_confetti(self) -> None:
        for _ in range(35):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(140, 380)
            self.confetti_particles.append({
                "x": float(self.screen_w // 2),
                "y": float(self.screen_h // 2),
                "vx": math.cos(angle) * spd,
                "vy": math.sin(angle) * spd,
                "color": random.choice([(255, 215, 60), (255, 65, 110), (60, 220, 255), (100, 255, 140)]),
                "size": random.uniform(6.0, 11.0),
                "life": 1.0
            })

    def render(self, surface: pygame.Surface) -> None:
        # Calcular screenshake offset
        ox, oy = 0, 0
        if self.screenshake_amp > 0.0:
            ox = int(random.uniform(-self.screenshake_amp, self.screenshake_amp))
            oy = int(random.uniform(-self.screenshake_amp, self.screenshake_amp))

        # 1. Fondo dinámico de fiesta caribeña (pre-renderizado)
        bg_surf = self._frame_surf
        bg_surf.blit(self._bg_normal if self.lives > 1 else self._bg_danger, (0, 0))

        # Rayos de luz radiales rotatorios en una única superficie reutilizable
        rot_ang = self.phase_timer * 1.2
        cx, cy = self.screen_w // 2, self.screen_h // 2
        self._ray_surf.fill((0, 0, 0, 0))
        for i in range(12):
            ang = rot_ang + i * (math.pi / 6)
            p1 = (cx, cy)
            p2 = (cx + int(math.cos(ang - 0.12) * 1400), cy + int(math.sin(ang - 0.12) * 1400))
            p3 = (cx + int(math.cos(ang + 0.12) * 1400), cy + int(math.sin(ang + 0.12) * 1400))
            pygame.draw.polygon(self._ray_surf, (255, 215, 80, 15), [p1, p2, p3])
        bg_surf.blit(self._ray_surf, (0, 0))

        # 2. Renderizar contenido de fase
        if self.phase == self.STATE_INTERSTITIAL:
            self._render_interstitial(bg_surf)
        elif self.phase == self.STATE_RESULT:
            self._render_result(bg_surf)
        elif self.phase == self.STATE_GAME_OVER:
            self._render_game_over(bg_surf)

        # 3. HUD Superior permanente (Vidas y Récord)
        self._render_hud(bg_surf)

        # 4. Confeti (con caché de sprites por color y tamaño)
        for cf in self.confetti_particles:
            if cf["life"] > 0.0:
                alpha = int(255 * max(0.0, cf["life"]))
                key = (tuple(cf["color"]), int(cf["size"]))
                c_surf = self._confetti_cache.get(key)
                if c_surf is None:
                    c_surf = pygame.Surface((18, 18), pygame.SRCALPHA)
                    pygame.draw.circle(c_surf, (*key[0], 255), (9, 9), key[1])
                    self._confetti_cache[key] = c_surf
                c_surf.set_alpha(alpha)
                bg_surf.blit(c_surf, (int(cf["x"]), int(cf["y"])))

        surface.blit(bg_surf, (ox, oy))

    def _build_gradient_bg(self, top_col: tuple, bot_col: tuple) -> pygame.Surface:
        surf = pygame.Surface((self.screen_w, self.screen_h))
        for y in range(self.screen_h):
            t = y / float(self.screen_h)
            r = int(top_col[0] * (1 - t) + bot_col[0] * t)
            g = int(top_col[1] * (1 - t) + bot_col[1] * t)
            b = int(top_col[2] * (1 - t) + bot_col[2] * t)
            surf.fill((r, g, b), (0, y, self.screen_w, 1))
        return surf

    def _render_hud(self, surface: pygame.Surface) -> None:
        # A) Vidas en la esquina superior derecha
        start_x = self.screen_w - 70 - (self.max_lives * 75)
        for i in range(self.max_lives):
            lx = start_x + i * 75
            ly = 35
            surf_to_draw = self.mask_life_surf if i < self.lives else self.mask_dead_surf
            surface.blit(surf_to_draw, (lx, ly))

        # B) Récord personal en la esquina superior izquierda
        best = self.settings.get_arcade_high_score()
        txt_best = self.font_sub.render(f"RÉCORD: {best}", True, (255, 215, 75))
        surface.blit(txt_best, (50, 45))

    def _render_interstitial(self, surface: pygame.Surface) -> None:
        cx, cy = self.screen_w // 2, self.screen_h // 2

        # Personaje centrado con rebote alegre
        bob_y = math.sin(self.phase_timer * 12.0) * 14.0
        surface.blit(self.character_sprite, (cx - self.character_sprite.get_width() // 2, int(cy - 60 + bob_y)))

        # Cartel de Ronda
        txt_round = self.font_huge.render(f"¡RONDA {self.round_num}!", True, (255, 235, 90))
        surface.blit(txt_round, txt_round.get_rect(center=(cx, cy - 230)))

        # Indicador de velocidad
        spd_text = f"VELOCIDAD: {self.speed_multiplier:.2f}x"
        col_spd = (80, 245, 120) if self.speed_multiplier <= 1.15 else (255, 90, 80)
        txt_spd = self.font_sub.render(spd_text, True, col_spd)
        surface.blit(txt_spd, txt_spd.get_rect(center=(cx, cy + 240)))

        # Barra de mecha que se consume hacia el juego
        bar_w = 460
        bar_h = 16
        bx = cx - bar_w // 2
        by = cy + 290
        progress = min(1.0, self.phase_timer / self.interstitial_duration)
        pygame.draw.rect(surface, (40, 45, 60), (bx, by, bar_w, bar_h), border_radius=8)
        pygame.draw.rect(surface, (255, 80, 80), (bx, by, int(bar_w * (1.0 - progress)), bar_h), border_radius=8)
        # Chispa ardiente
        spark_x = int(bx + bar_w * (1.0 - progress))
        pygame.draw.circle(surface, (255, 240, 120), (spark_x, by + bar_h // 2), 10)

    def _render_result(self, surface: pygame.Surface) -> None:
        cx, cy = self.screen_w // 2, self.screen_h // 2

        if self.last_won:
            banner_text = "¡BIEN HECHO!"
            banner_col = (60, 245, 120)
            sub_text = f"RACHA: {self.score} VICTORIAS"
        else:
            banner_text = "¡FALLASTE!"
            banner_col = (255, 75, 75)
            sub_text = f"VIDAS RESTANTES: {self.lives}"

        txt_b = self.font_huge.render(banner_text, True, banner_col)
        surface.blit(txt_b, txt_b.get_rect(center=(cx, cy - 60)))

        txt_s = self.font_title.render(sub_text, True, (255, 255, 255))
        surface.blit(txt_s, txt_s.get_rect(center=(cx, cy + 30)))

        if self.speed_just_increased:
            txt_speedup = self.font_sub.render("¡VELOCIDAD AUMENTADA!", True, (255, 220, 60))
            surface.blit(txt_speedup, txt_speedup.get_rect(center=(cx, cy + 110)))

    def _render_game_over(self, surface: pygame.Surface) -> None:
        cx, cy = self.screen_w // 2, self.screen_h // 2

        # Panel oscuro modal
        pw, ph = 760, 560
        p_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, (20, 22, 35, 245), (0, 0, pw, ph), border_radius=28)
        pygame.draw.rect(p_surf, (255, 75, 75), (0, 0, pw, ph), width=4, border_radius=28)

        # Título Game Over
        txt_go = self.font_huge.render("GAME OVER", True, (255, 80, 80))
        p_surf.blit(txt_go, txt_go.get_rect(center=(pw // 2, 75)))

        # Puntaje Final
        txt_sc = self.font_title.render(f"PUNTAJE FINAL: {self.score}", True, (255, 245, 220))
        p_surf.blit(txt_sc, txt_sc.get_rect(center=(pw // 2, 175)))

        # Récord
        best = self.settings.get_arcade_high_score()
        txt_rc = self.font_sub.render(f"MEJOR RÉCORD: {best}", True, (255, 215, 75))
        p_surf.blit(txt_rc, txt_rc.get_rect(center=(pw // 2, 235)))

        # Badge si superó el récord
        if self.is_new_record:
            badge_surf = pygame.Surface((360, 46), pygame.SRCALPHA)
            pygame.draw.rect(badge_surf, (255, 215, 60), (0, 0, 360, 46), border_radius=14)
            txt_rec = self.font_rec.render("★ ¡NUEVO RÉCORD HISTÓRICO! ★", True, (35, 25, 15))
            badge_surf.blit(txt_rec, txt_rec.get_rect(center=(180, 23)))
            p_surf.blit(badge_surf, badge_surf.get_rect(center=(pw // 2, 305)))

        surface.blit(p_surf, p_surf.get_rect(center=(cx, cy - 40)))

        # Renderizar botones
        self.btn_retry.render(surface)
        self.btn_exit.render(surface)
