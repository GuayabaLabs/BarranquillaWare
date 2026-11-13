import math
from typing import List, Optional, Dict, Any
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.settings import SettingsManager
from core.map_settings import MapSettingsState
from ui.button import UIButton
from effects.gl_particles import GLParticleSystem
from effects.juice_particles import JuiceParticleManager
from scenes.mode_select import ModeSelectScene
from scenes.slide_transition import SlideTransitionState

MODAL_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "jugar": {
        "title": "¡A JUGAR EN CURRAMBA!",
        "color": (235, 75, 35),
        "lines": [
            "¡Bienvenido a BarranquillaWare!",
            "Prepárate para una ráfaga de microjuegos a 60 FPS:",
            "• ¡Esquiva el arroyo en la 84!",
            "• ¡Pela el guineo antes del tiempo límite!",
            "• ¡Baila cumbia al compás del llamador!",
            "",
            "(Presiona cualquier tecla o click para continuar)"
        ]
    },
    "opciones": {
        "title": "CONFIGURACIÓN",
        "color": (135, 55, 185),
        "lines": [
            "Música de Fondo: {music_status}",
            "Efectos de Sonido (SFX): {sfx_status}",
            "Resolución Nativa: 1920 x 1080 (Full HD)",
            "Pantalla Completa: Presiona F11 para alternar",
            "Aceleración Gráfica: Shaders ModernGL Activo",
            "",
            "(Haz click o pulsa ESC para volver)"
        ]
    },
    "estadisticas": {
        "title": "ESTADÍSTICAS Y RÉCORDS",
        "color": (25, 135, 215),
        "lines": [
            "Récord Modo Arcade: {arcade_best} microjuegos consecutivos",
            "Puntaje Modo Historia: {story_score} pts",
            "Minijuegos Despejados: {completed_count} / 6",
            "Explorador Activo: {active_char}",
            "Tasa de Completitud: {completion_pct}%",
            "",
            "(Haz click o pulsa ESC para volver)"
        ]
    }
}

class MainMenuScene(BaseState):
    """
    Escena del Menú Principal de BarranquillaWare a Resolución Nativa Full HD (1920x1080):
    - Composición visual modular y desacoplada de alto rendimiento.
    - Renderizado de Iguana viva HD libre de aliasing anclada en el muro.
    - Botones en Full HD con destello interno puro (Shimmer) sin artefactos de spray.
    - Modales estilizados en 1080p.
    """
    def __init__(self, screen_w: int = 1920, screen_h: int = 1080) -> None:
        super().__init__()
        self.screen_w = screen_w
        self.screen_h = screen_h

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        # 1. Fondo Full HD
        raw_bg = self.assets.load_surface("fondo_main_menu.png", has_alpha=False)
        self.background = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))

        # 2. Título en 1080p
        self.title_base = self.assets.get_scaled("titulo_main_menu.png", target_width=990)
        self.title_center_x = self.screen_w // 2
        self.title_center_y = 228
        self.timer: float = 0.0

        # 3. Partículas GL y Juice
        self.particles = GLParticleSystem(count=36, screen_w=self.screen_w, screen_h=self.screen_h)
        self.juice_particles = JuiceParticleManager()

        # 4. Iguana HD en 1080p
        self._init_iguana()

        # 5. Botones en 1080p
        self._init_buttons()

        # 6. Modales y Tipografía 1080p
        self.active_modal: Optional[str] = None
        self.modal_alpha: float = 0.0
        self.font_title = pygame.font.SysFont("Arial Black, Impact, sans-serif", 44)
        self.font_body = pygame.font.SysFont("Arial, sans-serif", 28, bold=True)

        # 7. Precarga Cálida de Selección de Modo (Warm Scene Pre-instancing)
        self.mode_select_scene = ModeSelectScene(
            on_back_callback=self._return_from_mode_select,
            on_main_menu_callback=self._return_from_mode_select,
        )

    def _init_iguana(self) -> None:
        self.iguana_hd = self.assets.load_cropped_surface("iguana_main_menu.png")
        self.target_iguana_w = 282
        hd_w = self.iguana_hd.get_width()
        hd_h = self.iguana_hd.get_height()
        self.target_iguana_h = int(self.target_iguana_w * hd_h / hd_w)

        self.iguana_base_x = 28
        self.iguana_base_y = 963  # Muro inferior izquierdo en 1080p
        self.iguana_rect = pygame.Rect(
            self.iguana_base_x,
            self.iguana_base_y - self.target_iguana_h,
            self.target_iguana_w,
            self.target_iguana_h
        )
        self.iguana_hovered: bool = False
        self.iguana_jump_y: float = 0.0
        self.iguana_jump_vel: float = 0.0
        self.iguana_bounce_count: int = 0
        self.iguana_squash_offset: float = 0.0
        self.iguana_squash_vel: float = 0.0
        self.iguana_curiosity: float = 0.0

    def _init_buttons(self) -> None:
        audio_frames = self.assets.get_audio_button_frames(target_size=86)
        music_on, music_off, sound_on, sound_off = audio_frames[0], audio_frames[1], audio_frames[2], audio_frames[3]

        btn_jugar_surf = self.assets.get_scaled("boton_jugar_main_menu.png", target_width=638)
        btn_opciones_surf = self.assets.get_scaled("boton_opciones_main_menu.png", target_width=495)
        btn_estadisticas_surf = self.assets.get_scaled("boton_estad", target_width=495)
        btn_salir_surf = self.assets.get_scaled("boton_salir_main_menu.png", target_width=495)

        centers_y = [518, 652, 788, 922]
        self.btn_jugar = UIButton((self.screen_w // 2, centers_y[0]), btn_jugar_surf, on_click=self._on_play_clicked)
        self.btn_opciones = UIButton((self.screen_w // 2, centers_y[1]), btn_opciones_surf, on_click=self._on_open_settings)
        self.btn_estadisticas = UIButton((self.screen_w // 2, centers_y[2]), btn_estadisticas_surf, on_click=lambda: self._open_modal("estadisticas"))
        self.btn_salir = UIButton((self.screen_w // 2, centers_y[3]), btn_salir_surf, on_click=self._on_exit_clicked)

        self.btn_music = UIButton(
            center_pos=(1710, 78),
            normal_sprite=music_on,
            alt_sprite=music_off,
            is_toggle=True,
            initial_toggle_state=self.audio.music_enabled,
            on_click=self.audio.toggle_music
        )

        self.btn_sound = UIButton(
            center_pos=(1822, 78),
            normal_sprite=sound_on,
            alt_sprite=sound_off,
            is_toggle=True,
            initial_toggle_state=self.audio.sound_enabled,
            on_click=self.audio.toggle_sound
        )

        self.buttons: List[UIButton] = [
            self.btn_jugar,
            self.btn_opciones,
            self.btn_estadisticas,
            self.btn_salir,
            self.btn_music,
            self.btn_sound
        ]

    def sync_audio_buttons(self) -> None:
        """Sincroniza el estado visual de los toggles con el AudioManager (SSOT)."""
        self.btn_music.toggle_state = self.audio.music_enabled
        self.btn_sound.toggle_state = self.audio.sound_enabled

    def enter(self, params: Optional[dict] = None) -> None:
        self.sync_audio_buttons()

    def _open_modal(self, modal_name: str) -> None:
        self.active_modal = modal_name

    def _on_open_settings(self) -> None:
        """Abre el mismo panel provisional usado desde el mapa."""
        if self.state_machine:
            self.state_machine.push_state(
                MapSettingsState(on_calibrate=self._on_calibrate_from_settings)
            )

    def _on_calibrate_from_settings(self) -> None:
        if not self.state_machine:
            return
        self.state_machine.pop_state()
        from microgames.coaster_launcher import CoasterCalibrationState
        self.state_machine.change_state(
            CoasterCalibrationState(
                on_complete_callback=lambda _ok: self.state_machine.change_state(self)
            )
        )

    def _return_from_mode_select(self, from_scene: Optional[BaseState] = None) -> None:
        if not self.state_machine:
            return

        self.audio.play_bgm("7am_ancpg_ost_main_menu.ogg")
        self.sync_audio_buttons()
        trans = SlideTransitionState(
            from_scene=from_scene or self.mode_select_scene,
            to_scene=self,
            direction="right",
            duration=0.65
        )
        self.state_machine.change_state(trans)

    def _on_play_clicked(self) -> None:
        if not self.state_machine:
            return

        self.audio.play_bgm("dodo_airlines_acnh_ost_seleccion_modo.ogg")
        self.mode_select_scene.sync_audio_buttons()
        trans_to_mode = SlideTransitionState(
            from_scene=self,
            to_scene=self.mode_select_scene,
            direction="left",
            duration=0.65
        )
        self.state_machine.change_state(trans_to_mode)

    def _on_exit_clicked(self) -> None:
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _trigger_iguana_reaction(self) -> None:
        self.iguana_jump_vel = -330.0
        self.iguana_bounce_count = 0
        self.audio.play_iguana()
        head_pos = (self.iguana_base_x + 195, self.iguana_base_y - 110 + self.iguana_jump_y)
        self.juice_particles.emit_sparks(head_pos, count=7)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.active_modal:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self.active_modal = None
                self.audio.play_click()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.active_modal = None
                self.audio.play_click()
            return

        if event.type == pygame.MOUSEMOTION:
            was_hov = self.iguana_hovered
            self.iguana_hovered = self.iguana_rect.collidepoint(event.pos)
            if not was_hov and self.iguana_hovered:
                self.audio.play_hover()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.iguana_rect.collidepoint(event.pos):
                self._trigger_iguana_reaction()
                return

        for btn in self.buttons:
            consumed = btn.handle_event(event)
            if consumed and event.type != pygame.MOUSEMOTION:
                break

    def update(self, dt: float) -> None:
        self.timer += dt

        self.particles.update(dt)
        self.juice_particles.update(dt)

        if not self.active_modal:
            for btn in self.buttons:
                btn.update(dt)

        self._update_iguana_physics(dt)
        self._update_modal_transition(dt)

    def _update_iguana_physics(self, dt: float) -> None:
        target_curiosity = 1.0 if self.iguana_hovered else 0.0
        self.iguana_curiosity += (target_curiosity - self.iguana_curiosity) * (1.0 - math.exp(-12.0 * dt))

        if self.iguana_jump_y < 0.0 or self.iguana_jump_vel != 0.0:
            self.iguana_jump_y += self.iguana_jump_vel * dt
            self.iguana_jump_vel += 1380.0 * dt  # Gravedad escalada a 1080p
            if self.iguana_jump_y >= 0.0:
                impact_velocity = self.iguana_jump_vel
                self.iguana_jump_y = 0.0
                if impact_velocity > 55.0 and self.iguana_bounce_count < 2:
                    # Pequeños rebotes con pérdida de energía para suavizar el aterrizaje.
                    self.iguana_jump_vel = -impact_velocity * 0.42
                    self.iguana_bounce_count += 1
                    self.iguana_squash_offset = -min(0.22, impact_velocity / 1900.0)
                else:
                    self.iguana_jump_vel = 0.0
                    self.iguana_bounce_count = 0
                    self.iguana_squash_offset = -0.15
                self.iguana_squash_vel = 0.0

        spring_k = 340.0
        damping_c = 16.0
        acc = -spring_k * self.iguana_squash_offset - damping_c * self.iguana_squash_vel
        self.iguana_squash_vel += acc * dt
        self.iguana_squash_offset += self.iguana_squash_vel * dt

        self.iguana_rect.y = int(self.iguana_base_y - self.target_iguana_h + self.iguana_jump_y)

    def _update_modal_transition(self, dt: float) -> None:
        target_alpha = 255.0 if self.active_modal else 0.0
        blend = 1.0 - math.exp(-16.0 * dt)
        self.modal_alpha += (target_alpha - self.modal_alpha) * blend

    def render(self, surface: pygame.Surface) -> None:
        self.sync_audio_buttons()
        surface.blit(self.background, (0, 0))

        self._render_iguana(surface)
        self.juice_particles.render(surface)
        self._render_title(surface)

        for btn in self.buttons:
            btn.render(surface)

        if self.modal_alpha > 5.0 and self.active_modal:
            self._render_modal(surface)

    def _render_iguana(self, surface: pygame.Surface) -> None:
        breath_cycle = math.sin(self.timer * 2.2)
        base_scale_y = 1.0 + breath_cycle * 0.075 + self.iguana_curiosity * 0.05
        base_scale_x = 1.0 - breath_cycle * 0.035 - self.iguana_curiosity * 0.02
        breath_bob = (math.sin(self.timer * 2.2) * 0.5 + 0.5) * 5.2

        air_stretch = abs(self.iguana_jump_vel) / 2100.0 if self.iguana_jump_y < -1.0 else 0.0
        scale_y = max(0.5, base_scale_y + air_stretch + self.iguana_squash_offset)
        scale_x = max(0.5, base_scale_x - air_stretch * 0.5 - self.iguana_squash_offset * 0.5)

        ig_w = max(10, int(self.target_iguana_w * scale_x))
        ig_h = max(10, int(self.target_iguana_h * scale_y))

        scaled_ig = pygame.transform.smoothscale(self.iguana_hd, (ig_w, ig_h))
        dest_rect = scaled_ig.get_rect(bottomleft=(self.iguana_base_x, int(self.iguana_base_y + self.iguana_jump_y - breath_bob)))
        surface.blit(scaled_ig, dest_rect)

    def _render_title(self, surface: pygame.Surface) -> None:
        bob_y = math.sin(self.timer * 2.1) * 6.5
        rot_angle = math.sin(self.timer * 1.3) * 0.35
        rotated_title = pygame.transform.rotozoom(self.title_base, rot_angle, 1.0)
        title_rect = rotated_title.get_rect(center=(self.title_center_x, int(self.title_center_y + bob_y)))
        surface.blit(rotated_title, title_rect)

    def _render_modal(self, surface: pygame.Surface) -> None:
        modal_info = MODAL_DEFINITIONS.get(self.active_modal or "")
        if not modal_info:
            return

        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        alpha = int(min(180, self.modal_alpha * 0.7))
        overlay.fill((8, 16, 30, alpha))
        surface.blit(overlay, (0, 0))

        card_w, card_h = 870, 540
        card_rect = pygame.Rect((self.screen_w - card_w) // 2, (self.screen_h - card_h) // 2, card_w, card_h)

        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        pygame.draw.rect(card_surf, (0, 0, 0, 75), (0, 12, card_w, card_h - 12), border_radius=36)
        pygame.draw.rect(card_surf, (255, 253, 246, 248), (0, 0, card_w, card_h - 12), border_radius=36)
        pygame.draw.rect(card_surf, (245, 160, 40, 255), (0, 0, card_w, card_h - 12), width=6, border_radius=36)
        surface.blit(card_surf, card_rect.topleft)

        t_render = self.font_title.render(modal_info["title"], True, modal_info["color"])
        t_pos = t_render.get_rect(center=(self.screen_w // 2, card_rect.top + 65))
        surface.blit(t_render, t_pos)

        music_status = "ACTIVADA" if self.audio.music_enabled else "MUTED"
        sfx_status = "ACTIVADO" if self.audio.sound_enabled else "MUTED"

        settings = SettingsManager.get_instance()
        story = settings.get_story_progress()
        completed_count = len(story.get("completed_microgames", []))
        arcade_best = settings.get_arcade_high_score()
        story_score = story.get("high_score", 0)
        active_char = story.get("character_id", "westcol").capitalize()
        completion_pct = int((completed_count / 6.0) * 100)

        cur_y = card_rect.top + 155
        for line in modal_info["lines"]:
            if not line:
                cur_y += 15
                continue

            formatted_line = line.format(music_status=music_status, sfx_status=sfx_status, arcade_best=arcade_best, story_score=story_score, completed_count=completed_count, active_char=active_char, completion_pct=completion_pct)
            color = (75, 75, 75) if not formatted_line.startswith("(") else (145, 145, 145)
            line_surf = self.font_body.render(formatted_line, True, color)
            surface.blit(line_surf, line_surf.get_rect(center=(self.screen_w // 2, cur_y)))
            cur_y += 42
