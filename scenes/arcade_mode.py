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
from scenes.load_game import make_watercolor_button_surface, render_outlined_text

# Microjuegos disponibles en el Modo Arcade (Clásicos + Nuevos + Jefe)
from microgames.mallorquin_photo import MallorquinPhotoMicrogame
from microgames.uninorte_sprint import UninorteSprintMicrogame
from microgames.ventana_colores import VentanaColoresMicrogame
from microgames.malecon_rueda import MaleconRuedaMicrogame
from microgames.metropolitano_penalty import MetropolitanoPenaltyMicrogame
from microgames.aeropuerto_aterrizaje import AeropuertoAterrizajeMicrogame
from microgames.fritanga_84 import Fritanga84Microgame
from microgames.troja_baile import TrojaBaileMicrogame
from microgames.uninorte_concentrate import UninorteConcentrateMicrogame
from microgames.buenavista_trend import BuenavistaTrendMicrogame
from microgames.metropolitano_moderacion import MetropolitanoModeracionMicrogame
from microgames.punch_alert import PunchAlertMicrogame
from microgames.buenavista_cine import BuenavistaCineMicrogame
from microgames.curramgram_go import CurramGramGoMicrogame
from microgames.emoji_catch import EmojiCatchMicrogame


INK_DARK = (78, 51, 35)       # #4E3323
INK_MUTED = (118, 84, 62)
CREAM_TEXT = (255, 250, 238)


class ArcadeModeScene(BaseState):
    """
    Modo Arcade WarioWare ('Frenesí Caribeño' — Estilo Acuarela Cálido):
    - Cadena ininterrumpida de microjuegos aleatorios (clásicos de 4s y nuevos con ventana justa).
    - 4 vidas (Máscaras de Marimonda).
    - Velocidad creciente (+15% cada 4 rondas superadas).
    - Intersticio acuarela cálido con barra de mecha, confeti y transición fluida.
    - Pantalla de Game Over en pergamino acuarela con emblemas de estrella reales.
    """

    STATE_INTERSTITIAL = "interstitial"
    STATE_RESULT = "result"
    STATE_GAME_OVER = "game_over"

    def __init__(
        self,
        character_id: str = "westcol",
        on_exit_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.screen_w = 1920
        self.screen_h = 1080
        self.character_id = character_id
        self.on_exit_callback = on_exit_callback

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()
        self.settings = SettingsManager.get_instance()

        # Pool completo compatible de microjuegos
        self.microgame_pool: List[Type[BaseMicrogame]] = [
            MallorquinPhotoMicrogame,
            UninorteSprintMicrogame,
            VentanaColoresMicrogame,
            MaleconRuedaMicrogame,
            MetropolitanoPenaltyMicrogame,
            AeropuertoAterrizajeMicrogame,
            Fritanga84Microgame,
            TrojaBaileMicrogame,
            UninorteConcentrateMicrogame,
            BuenavistaTrendMicrogame,
            MetropolitanoModeracionMicrogame,
            PunchAlertMicrogame,
            BuenavistaCineMicrogame,
            CurramGramGoMicrogame,
            EmojiCatchMicrogame,
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
        self._active_microgame: Optional[BaseMicrogame] = None

        # Efectos visuales de Game Feel
        self.screenshake_amp = 0.0
        self.screenshake_time = 0.0
        self.confetti_particles = []

        # Tipografías acuarela del proyecto (IndieFlower-Regular)
        self.font_huge = self.assets.cargarFuenteCuento(64)
        self.font_title = self.assets.cargarFuenteCuento(44)
        self.font_sub = self.assets.cargarFuenteCuento(28)
        self.font_btn = self.assets.cargarFuenteCuento(24)
        self.font_rec = self.assets.cargarFuenteCuento(23)

        # Caché de fondos acuarela y overlays (cero loops de 1080 líneas)
        self._build_watercolor_assets()
        self._frame_surf = pygame.Surface((self.screen_w, self.screen_h))
        self._ray_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        self._confetti_cache: dict = {}

        # Superficie de vida (Máscara de Marimonda)
        self.mask_life_surf = self._create_marimonda_mask_surf(is_broken=False)
        self.mask_dead_surf = self._create_marimonda_mask_surf(is_broken=True)

        # Cargar sprite del personaje
        self._load_character_sprite()

        # Botones de Game Over
        self._init_game_over_buttons()

    def _build_watercolor_assets(self) -> None:
        raw_bg = self.assets.load_surface("fondo_modo_libre.png", has_alpha=False)
        self._bg_normal = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))
        # Velo pergamino cálido suave para que los banners acuarela resalten nítidos
        warm_wash = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        warm_wash.fill((252, 240, 218, 55))
        self._bg_normal.blit(warm_wash, (0, 0))

        self._bg_danger = self._bg_normal.copy()
        danger_wash = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        danger_wash.fill((215, 72, 68, 70))
        self._bg_danger.blit(danger_wash, (0, 0))

        raw_frame = self.assets.load_cropped_surface("recuadro_partida_guardada.png")
        self.gameover_frame_surf = pygame.transform.smoothscale(raw_frame, (1080, 670))

        raw_card = self.assets.load_cropped_surface("tarjeta_slot_partida.png")
        self.hud_lives_pill = pygame.transform.smoothscale(raw_card, (356, 98))
        self.result_card_surf = pygame.transform.smoothscale(raw_card, (760, 270))

        raw_dist = self.assets.load_cropped_surface("cinta_distrito_modal.png")
        self.hud_record_ribbon = pygame.transform.smoothscale(raw_dist, (450, 66))
        self.speed_ribbon_surf = pygame.transform.smoothscale(raw_dist, (380, 52))

        raw_state = self.assets.load_cropped_surface("cinta_estado_modal.png")
        self.round_ribbon_surf = pygame.transform.smoothscale(raw_state, (680, 108))
        self.record_banner_surf = pygame.transform.smoothscale(raw_state, (540, 66))

        raw_emblem = self.assets.load_cropped_surface("emblema_estrella_modal.png")
        self.star_emblem_surf = pygame.transform.smoothscale(raw_emblem, (48, 45))

        raw_sep = self.assets.load_cropped_surface("separador_floral_modal.png")
        sep_w = 500
        sep_h = max(18, int(sep_w * raw_sep.get_height() / max(1, raw_sep.get_width())))
        self.sep_surf = pygame.transform.smoothscale(raw_sep, (sep_w, sep_h))

    def _create_marimonda_mask_surf(self, is_broken: bool = False) -> pygame.Surface:
        mw, mh = 64, 76
        surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        col_face = (242, 146, 58) if not is_broken else (164, 152, 144)
        col_nose = (232, 72, 86) if not is_broken else (130, 120, 116)
        col_ear = (66, 178, 218) if not is_broken else (142, 140, 138)

        pygame.draw.circle(surf, col_ear, (12, 30), 12)
        pygame.draw.circle(surf, col_ear, (mw - 12, 30), 12)
        pygame.draw.ellipse(surf, col_face, (10, 12, mw - 20, mh - 24))
        pygame.draw.ellipse(surf, INK_DARK, (10, 12, mw - 20, mh - 24), width=3)
        pygame.draw.circle(surf, (255, 252, 245), (22, 28), 9)
        pygame.draw.circle(surf, (255, 252, 245), (mw - 22, 28), 9)
        pygame.draw.circle(surf, INK_DARK, (22, 28), 4)
        pygame.draw.circle(surf, INK_DARK, (mw - 22, 28), 4)
        pts_nose = [(mw // 2 - 6, 36), (mw // 2 + 6, 36), (mw // 2 + 10, mh - 6), (mw // 2 - 10, mh - 6)]
        pygame.draw.polygon(surf, col_nose, pts_nose)
        pygame.draw.polygon(surf, INK_DARK, pts_nose, width=2)

        if is_broken:
            pygame.draw.line(surf, (186, 48, 52), (14, 18), (mw - 14, mh - 18), 3)
            pygame.draw.line(surf, (186, 48, 52), (mw - 14, 18), (14, mh - 18), 3)

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
        retry_surf = make_watercolor_button_surface(
            self.assets, "green", "REINTENTAR", (320, 74), font_size=28
        )
        exit_surf = make_watercolor_button_surface(
            self.assets, "red", "SALIR AL MENÚ", (320, 74), font_size=28
        )
        self.btn_retry = UIButton(
            center_pos=(self.screen_w // 2 - 185, 768),
            normal_sprite=retry_surf,
            on_click=self._restart_arcade,
        )
        self.btn_exit = UIButton(
            center_pos=(self.screen_w // 2 + 185, 768),
            normal_sprite=exit_surf,
            on_click=self._exit_arcade,
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
        if self._active_microgame is not None and hasattr(self._active_microgame, "cleanup"):
            try:
                self._active_microgame.cleanup()
            except Exception:
                pass
        self._active_microgame = None
        if self.on_exit_callback:
            self.on_exit_callback()

    def enter(self, params: Optional[dict] = None) -> None:
        if params and "character_id" in params:
            self.character_id = params["character_id"]
            self._load_character_sprite()
        if not (params and params.get("resume_round")):
            self._restart_arcade()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.phase == self.STATE_GAME_OVER:
            self.btn_retry.handle_event(event)
            self.btn_exit.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._exit_arcade()

    def update(self, dt: float) -> None:
        self.phase_timer += dt

        if self.screenshake_time > 0.0:
            self.screenshake_time -= dt
            if self.screenshake_time <= 0.0:
                self.screenshake_amp = 0.0

        for cf in self.confetti_particles[:]:
            cf["x"] += cf["vx"] * dt
            cf["y"] += cf["vy"] * dt
            cf["life"] -= dt * 1.15
            if cf["life"] <= 0.0:
                self.confetti_particles.remove(cf)

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

    def _compute_arcade_time_limit(self, chosen_cls: Type[BaseMicrogame]) -> float:
        """Calcula una ventana justa según la categoría del microjuego y el multiplicador actual."""
        if chosen_cls is CurramGramGoMicrogame:
            # La ruta completa y sus seis casos requieren su ventana original.
            return 120.0
        if chosen_cls is EmojiCatchMicrogame:
            return max(18.0, 30.0 / self.speed_multiplier)
        if chosen_cls is MetropolitanoModeracionMicrogame:
            return max(4.5, 6.5 / self.speed_multiplier)
        if chosen_cls in (BuenavistaTrendMicrogame, BuenavistaCineMicrogame, PunchAlertMicrogame):
            return max(5.5, 8.5 / self.speed_multiplier)
        if chosen_cls is UninorteSprintMicrogame:
            return max(11.0, 15.0 / min(1.4, self.speed_multiplier))
        if chosen_cls is UninorteConcentrateMicrogame:
            return max(15.0, 20.0 / min(1.35, self.speed_multiplier))
        return max(1.8, 4.0 / self.speed_multiplier)

    def _launch_next_microgame(self) -> None:
        """Elige un microjuego al azar del catálogo arcade y lo ejecuta."""
        chosen_cls = random.choice(self.microgame_pool)
        fair_time = self._compute_arcade_time_limit(chosen_cls)

        if chosen_cls is MetropolitanoModeracionMicrogame:
            microgame = MetropolitanoModeracionMicrogame(
                character_id=self.character_id,
                on_complete_callback=self._on_microgame_result,
                time_limit=fair_time,
                target_bans=3,
                arcade_mode=True,
            )
        elif chosen_cls is PunchAlertMicrogame:
            microgame = PunchAlertMicrogame(
                character_id=self.character_id,
                on_complete_callback=self._on_microgame_result,
                time_limit=fair_time,
            )
        else:
            microgame = chosen_cls(
                character_id=self.character_id,
                on_complete_callback=self._on_microgame_result,
            )
            microgame.time_limit = fair_time
            microgame.time_left = fair_time
            if chosen_cls in (CurramGramGoMicrogame, EmojiCatchMicrogame):
                # Estos juegos llevan su propio reloj, sincronizado con la barra común.
                microgame.game.tiempo = fair_time

        microgame.pause_return_callback = self._exit_arcade
        microgame.pause_menu_callback = self._exit_arcade
        self._active_microgame = microgame

        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(microgame)

    def _on_microgame_result(self, won: bool) -> None:
        """Callback al terminar el microjuego."""
        if self._active_microgame is not None and hasattr(self._active_microgame, "cleanup"):
            try:
                self._active_microgame.cleanup()
            except Exception:
                pass
        self._active_microgame = None

        self.last_won = won
        self.phase = self.STATE_RESULT
        self.phase_timer = 0.0
        self.speed_just_increased = False

        if won:
            self.score += 1
            self.round_num += 1
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()

            if self.score > 0 and self.score % 4 == 0:
                self.speed_multiplier = min(2.1, self.speed_multiplier + 0.15)
                self.speed_just_increased = True
                self._spawn_celebration_confetti()
        else:
            self.lives -= 1
            self.round_num += 1
            self.screenshake_amp = 16.0
            self.screenshake_time = 0.25

        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(self, {"resume_round": True})

    def _enter_game_over(self) -> None:
        self.phase = self.STATE_GAME_OVER
        self.is_new_record = self.settings.update_arcade_high_score(self.score)
        self.screenshake_amp = 18.0
        self.screenshake_time = 0.30

    def _spawn_celebration_confetti(self) -> None:
        for _ in range(36):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(140, 380)
            self.confetti_particles.append({
                "x": float(self.screen_w // 2),
                "y": float(self.screen_h // 2),
                "vx": math.cos(angle) * spd,
                "vy": math.sin(angle) * spd,
                "color": random.choice([(245, 190, 58), (232, 86, 106), (68, 178, 212), (76, 188, 114)]),
                "size": random.uniform(6.0, 11.0),
                "life": 1.0,
            })

    def render(self, surface: pygame.Surface) -> None:
        ox, oy = 0, 0
        if self.screenshake_amp > 0.0:
            ox = int(random.uniform(-self.screenshake_amp, self.screenshake_amp))
            oy = int(random.uniform(-self.screenshake_amp, self.screenshake_amp))

        bg_surf = self._frame_surf
        bg_surf.blit(self._bg_normal if self.lives > 1 else self._bg_danger, (0, 0))

        # Rayos suaves dorados estilo caribeño
        rot_ang = self.phase_timer * 0.9
        cx, cy = self.screen_w // 2, self.screen_h // 2
        self._ray_surf.fill((0, 0, 0, 0))
        for i in range(12):
            ang = rot_ang + i * (math.pi / 6)
            p1 = (cx, cy)
            p2 = (cx + int(math.cos(ang - 0.11) * 1400), cy + int(math.sin(ang - 0.11) * 1400))
            p3 = (cx + int(math.cos(ang + 0.11) * 1400), cy + int(math.sin(ang + 0.11) * 1400))
            pygame.draw.polygon(self._ray_surf, (255, 224, 130, 26), [p1, p2, p3])
        bg_surf.blit(self._ray_surf, (0, 0))

        if self.phase == self.STATE_INTERSTITIAL:
            self._render_interstitial(bg_surf)
        elif self.phase == self.STATE_RESULT:
            self._render_result(bg_surf)
        elif self.phase == self.STATE_GAME_OVER:
            self._render_game_over(bg_surf)

        self._render_hud(bg_surf)

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

    def _render_hud(self, surface: pygame.Surface) -> None:
        # A) Panel acuarela de Récord y Racha arriba a la izquierda
        rec_rect = self.hud_record_ribbon.get_rect(topleft=(40, 28))
        surface.blit(self.hud_record_ribbon, rec_rect)
        best = self.settings.get_arcade_high_score()
        txt_best = self.font_sub.render(f"RÉCORD: {best}   |   RACHA: {self.score}", True, INK_DARK)
        surface.blit(txt_best, txt_best.get_rect(center=(rec_rect.centerx, rec_rect.centery - 2)))

        # B) Vidas en píldora acuarela arriba a la derecha
        pill_rect = self.hud_lives_pill.get_rect(topright=(self.screen_w - 40, 22))
        surface.blit(self.hud_lives_pill, pill_rect)
        start_x = pill_rect.x + 28
        for i in range(self.max_lives):
            lx = start_x + i * 76
            ly = pill_rect.y + 11
            surf_to_draw = self.mask_life_surf if i < self.lives else self.mask_dead_surf
            surface.blit(surf_to_draw, (lx, ly))

    def _render_interstitial(self, surface: pygame.Surface) -> None:
        cx, cy = self.screen_w // 2, self.screen_h // 2

        # Halo cálido acuarela detrás del personaje
        halo = pygame.Surface((420, 420), pygame.SRCALPHA)
        pygame.draw.circle(halo, (255, 244, 214, 155), (210, 210), 185)
        pygame.draw.circle(halo, (245, 198, 118, 95), (210, 210), 205, width=6)
        surface.blit(halo, halo.get_rect(center=(cx, cy + 50)))

        # Personaje centrado con rebote alegre
        bob_y = math.sin(self.phase_timer * 11.0) * 12.0
        surface.blit(self.character_sprite, (cx - self.character_sprite.get_width() // 2, int(cy - 95 + bob_y)))

        # Cinta de Ronda
        rib_rect = self.round_ribbon_surf.get_rect(center=(cx, cy - 235))
        surface.blit(self.round_ribbon_surf, rib_rect)
        txt_round = render_outlined_text(
            self.font_huge,
            f"¡RONDA {self.round_num}!",
            CREAM_TEXT,
            INK_DARK,
            thickness=3,
        )
        surface.blit(txt_round, txt_round.get_rect(center=rib_rect.center))

        # Cinta de velocidad
        spd_rect = self.speed_ribbon_surf.get_rect(center=(cx, cy + 258))
        surface.blit(self.speed_ribbon_surf, spd_rect)
        col_spd = (28, 118, 66) if self.speed_multiplier <= 1.15 else (186, 54, 48)
        txt_spd = self.font_sub.render(f"VELOCIDAD: {self.speed_multiplier:.2f}x", True, col_spd)
        surface.blit(txt_spd, txt_spd.get_rect(center=(spd_rect.centerx, spd_rect.centery - 1)))

        # Barra de mecha estilo acuarela
        bar_w, bar_h = 480, 22
        bx = cx - bar_w // 2
        by = cy + 308
        progress = min(1.0, self.phase_timer / self.interstitial_duration)
        pygame.draw.rect(surface, (246, 232, 206), (bx - 4, by - 4, bar_w + 8, bar_h + 8), border_radius=12)
        pygame.draw.rect(surface, INK_DARK, (bx - 4, by - 4, bar_w + 8, bar_h + 8), width=2, border_radius=12)
        pygame.draw.rect(surface, (118, 86, 66), (bx, by, bar_w, bar_h), border_radius=10)
        fill_w = max(0, int(bar_w * (1.0 - progress)))
        if fill_w > 0:
            bar_col = (74, 178, 128) if progress < 0.5 else ((238, 168, 56) if progress < 0.8 else (222, 74, 72))
            pygame.draw.rect(surface, bar_col, (bx, by, fill_w, bar_h), border_radius=10)
        spark_x = int(bx + fill_w)
        pygame.draw.circle(surface, (255, 245, 160), (spark_x, by + bar_h // 2), 11)
        pygame.draw.circle(surface, (232, 126, 48), (spark_x, by + bar_h // 2), 13, width=2)

    def _render_result(self, surface: pygame.Surface) -> None:
        cx, cy = self.screen_w // 2, self.screen_h // 2
        card_rect = self.result_card_surf.get_rect(center=(cx, cy - 10))
        surface.blit(self.result_card_surf, card_rect)

        if self.last_won:
            banner_text = "¡BIEN HECHO!"
            banner_col = (28, 134, 72)
            sub_text = f"RACHA ACTUAL: {self.score} VICTORIAS"
        else:
            banner_text = "¡FALLASTE!"
            banner_col = (196, 52, 54)
            sub_text = f"VIDAS RESTANTES: {self.lives}"

        txt_b = render_outlined_text(self.font_huge, banner_text, banner_col, (255, 250, 240), thickness=2)
        surface.blit(txt_b, txt_b.get_rect(center=(cx, cy - 52)))

        txt_s = self.font_title.render(sub_text, True, INK_DARK)
        surface.blit(txt_s, txt_s.get_rect(center=(cx, cy + 36)))

        if self.speed_just_increased:
            rib = self.record_banner_surf.get_rect(center=(cx, cy + 168))
            surface.blit(self.record_banner_surf, rib)
            txt_speedup = render_outlined_text(
                self.font_sub, "¡VELOCIDAD AUMENTADA!", CREAM_TEXT, (148, 72, 20), thickness=2
            )
            surface.blit(txt_speedup, txt_speedup.get_rect(center=rib.center))

    def _render_game_over(self, surface: pygame.Surface) -> None:
        cx, cy = self.screen_w // 2, self.screen_h // 2

        # Velo cálido suave detrás del modal
        backdrop = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        backdrop.fill((48, 30, 22, 125))
        surface.blit(backdrop, (0, 0))

        # Pergamino acuarela oficial
        frame_rect = self.gameover_frame_surf.get_rect(center=(cx, cy))
        surface.blit(self.gameover_frame_surf, frame_rect)

        # Título Game Over en tinta café / coral
        txt_go = render_outlined_text(
            self.font_huge, "FIN DEL JUEGO", (196, 56, 54), (255, 248, 232), thickness=3
        )
        surface.blit(txt_go, txt_go.get_rect(center=(cx, frame_rect.top + 118)))

        surface.blit(self.sep_surf, self.sep_surf.get_rect(center=(cx, frame_rect.top + 186)))

        # Puntaje Final
        txt_sc = self.font_title.render(f"PUNTAJE FINAL: {self.score}", True, INK_DARK)
        surface.blit(txt_sc, txt_sc.get_rect(center=(cx, frame_rect.top + 260)))

        # Récord
        best = self.settings.get_arcade_high_score()
        txt_rc = self.font_sub.render(f"MEJOR RÉCORD: {best}", True, INK_MUTED)
        surface.blit(txt_rc, txt_rc.get_rect(center=(cx, frame_rect.top + 324)))

        # Cinta acuarela + emblemas reales si superó el récord (cero glifo roto)
        if self.is_new_record:
            rec_rect = self.record_banner_surf.get_rect(center=(cx, frame_rect.top + 408))
            surface.blit(self.record_banner_surf, rec_rect)
            surface.blit(self.star_emblem_surf, (rec_rect.left + 16, rec_rect.centery - 22))
            surface.blit(self.star_emblem_surf, (rec_rect.right - 64, rec_rect.centery - 22))
            txt_rec = render_outlined_text(
                self.font_rec, "¡NUEVO RÉCORD HISTÓRICO!", CREAM_TEXT, (132, 62, 18), thickness=2
            )
            surface.blit(txt_rec, txt_rec.get_rect(center=rec_rect.center))

        # Botones acuarela
        self.btn_retry.render(surface)
        self.btn_exit.render(surface)
