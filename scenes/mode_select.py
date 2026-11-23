import math
from typing import List, Optional, Callable
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.settings import SettingsManager, compute_social_metrics
from ui.button import UIButton
from ui.focus_nav import FocusNavigator
from effects.gl_particles import GLParticleSystem
from effects.juice_particles import JuiceParticleManager
from scenes.character_select import CharacterSelectScene
from scenes.load_game import StorySaveModalPanel
from scenes.slide_transition import SlideTransitionState

class ModeSelectScene(BaseState):
    """
    Escena de Selección de Modo de BarranquillaWare a 1920x1080 Full HD:
    - Escenario de Barranquilla con la mascota Paloma viva (picoteo y respiración).
    - Tarjetas interactivas de Modo Historia, Modo Arcade y Modo Libre con Shimmer interno.
    - Acceso instantáneo a Selección de Personajes con Warm Pre-instancing (0 ms I/O).
    - Botón de regreso '← VOLVER' con animación panorámica de cámara inversa.
    - Toggles de audio integrados y música continua de Dodo Airlines.
    """
    def __init__(
        self,
        on_back_callback: Optional[Callable[[], None]] = None,
        on_main_menu_callback: Optional[Callable[[BaseState], None]] = None,
    ) -> None:
        super().__init__()
        self.screen_w = 1920
        self.screen_h = 1080
        self.on_back_callback = on_back_callback
        self.on_main_menu_callback = on_main_menu_callback

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()
        self.settings = SettingsManager.get_instance()

        # 1. Fondo de Selección de Modo
        raw_bg = self.assets.load_surface("fondo_seleccion_modo.png", has_alpha=False)
        self.background = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))

        # 2. Partículas y Juice
        self.particles = GLParticleSystem(count=36, screen_w=self.screen_w, screen_h=self.screen_h)
        self.juice_particles = JuiceParticleManager()
        self.timer: float = 0.0

        # Toast de notificación para modos en desarrollo
        self.toast_msg: Optional[str] = None
        self.toast_timer: float = 0.0
        self.font_toast = self.assets.cargarFuenteCuento(26)

        # 3. Título Ilustrado Full HD
        self.title_base = self.assets.get_scaled("titulo_seleccion_modo.png", target_width=760)
        self.title_center_x = self.screen_w // 2
        self.title_center_y = 140

        # 4. Paloma HD (Mascota del escenario)
        self._init_paloma()

        # 5. Escena de Selección de Personajes (Warm Pre-instancing para 0 ms de latencia I/O)
        self.character_select_scene = CharacterSelectScene(
            on_back_callback=self._return_from_character_select,
            on_character_chosen=self._on_character_chosen
        )

        # 6. Botones y Modal de Partida Guardada (Modo Historia)
        self._init_buttons()
        self._init_story_save_modal()

    def _init_paloma(self) -> None:
        self.paloma_hd_descanso = self.assets.load_cropped_surface("paloma_seleccion_modo.png", alpha_threshold=25)
        self.paloma_hd_parada = self.assets.load_cropped_surface("paloma_parada_seleccion_modo.png", alpha_threshold=25)
        self.paloma_hd_volando = self.assets.load_cropped_surface("paloma_volando_seleccion_modo.png", alpha_threshold=25)

        self.paloma_surfaces = {
            "descanso": self.paloma_hd_descanso,
            "parada": self.paloma_hd_parada,
            "volando": self.paloma_hd_volando,
        }

        self.paloma_state: str = "descanso"
        self.paloma_hd = self.paloma_hd_descanso
        self.target_paloma_w = 260
        orig_w = self.paloma_hd.get_width()
        orig_h = self.paloma_hd.get_height()
        self.target_paloma_h = int(self.target_paloma_w * orig_h / orig_w)

        self.paloma_base_x = 90
        self.paloma_base_y = 995
        self.paloma_rect = pygame.Rect(
            self.paloma_base_x,
            self.paloma_base_y - self.target_paloma_h,
            self.target_paloma_w,
            self.target_paloma_h
        )
        self.paloma_hovered: bool = False
        self.paloma_jump_y: float = 0.0
        self.paloma_jump_vel: float = 0.0
        self.paloma_squash: float = 0.0
        self.paloma_squash_vel: float = 0.0
        self.paloma_curiosity: float = 0.0
        self.paloma_flight_tilt: float = 0.0
        self.paloma_clicks_count: int = 0
        self.paloma_stand_timer: float = 0.0

    def _init_buttons(self) -> None:
        # Botón Volver
        btn_back_surf = self.assets.get_scaled("boton_volver_seleccion_modo.png", target_width=175)
        self.btn_back = UIButton((130, 75), btn_back_surf, on_click=self._on_back_clicked)

        # Botones de audio
        audio_frames = self.assets.get_audio_button_frames(target_size=86)
        self.btn_music = UIButton(
            (1710, 78),
            audio_frames[0],
            alt_sprite=audio_frames[1],
            is_toggle=True,
            initial_toggle_state=self.audio.music_enabled,
            on_click=self.audio.toggle_music
        )
        self.btn_sound = UIButton(
            (1822, 78),
            audio_frames[2],
            alt_sprite=audio_frames[3],
            is_toggle=True,
            initial_toggle_state=self.audio.sound_enabled,
            on_click=self.audio.toggle_sound
        )
        voice_frames = self.assets.get_voice_button_frames(target_size=86)
        self.btn_voice = UIButton(
            (1598, 78),
            voice_frames[0],
            alt_sprite=voice_frames[1],
            is_toggle=True,
            initial_toggle_state=self.audio.voice_enabled,
            on_click=self.audio.toggle_voice
        )
        self._draws_voice_badge = True

        # Tarjetas de Modo de Juego
        card_w = 470
        btn_historia_surf = self.assets.get_scaled("boton_modo_historia_seleccion_modo.png", target_width=card_w)
        btn_arcade_surf = self.assets.get_scaled("boton_modo_arcade_seleccion_modo.png", target_width=card_w)
        btn_libre_surf = self.assets.get_scaled("boton_modo_libre_seleccion_modo.png", target_width=card_w)

        center_y = 550
        self.btn_historia = UIButton((420, center_y), btn_historia_surf, on_click=lambda: self._select_mode("historia"))
        self.btn_arcade = UIButton((960, center_y), btn_arcade_surf, on_click=lambda: self._select_mode("arcade"))
        self.btn_libre = UIButton((1500, center_y), btn_libre_surf, on_click=lambda: self._select_mode("libre"))

        self.buttons: List[UIButton] = [
            self.btn_back,
            self.btn_music,
            self.btn_sound,
            self.btn_historia,
            self.btn_arcade,
            self.btn_libre
        ]
        # Teclado / mando: foco inicial en "Modo Historia"
        self.focus_nav = FocusNavigator(
            lambda: [*self.buttons, self.btn_voice] if hasattr(self, "btn_voice") else self.buttons,
            default_index=3,
        )

    def _init_story_save_modal(self) -> None:
        """Inicializa el modal acuarela de 'Continuar Partida' vs 'Nueva Partida' para el Modo Historia."""
        self.story_save_modal_open: bool = False
        self.story_save_panel = StorySaveModalPanel(
            screen_w=self.screen_w,
            screen_h=self.screen_h,
            mode="confirm",
            on_continue=self._on_continue_story_clicked,
            on_new_game=self._on_new_story_clicked,
            on_cancel=self._close_story_save_modal,
        )
        self.modal_rect = self.story_save_panel.frame_rect
        self.btn_continue_story = self.story_save_panel.btn_continue
        self.btn_new_story = self.story_save_panel.btn_new
        self.btn_cancel_modal = self.story_save_panel.btn_cancel
        self.modal_buttons: List[UIButton] = self.story_save_panel.buttons

    def _sync_story_save_modal_refs(self) -> None:
        self.modal_rect = self.story_save_panel.frame_rect
        self.btn_continue_story = self.story_save_panel.btn_continue
        self.btn_new_story = self.story_save_panel.btn_new
        self.btn_cancel_modal = self.story_save_panel.btn_cancel
        self.modal_buttons = self.story_save_panel.buttons

    def _close_story_save_modal(self) -> None:
        self.audio.play_click()
        self.story_save_modal_open = False

    def _on_continue_story_clicked(self) -> None:
        """Carga directamente la partida guardada en StoryMapScene sin pasar por selección de personaje."""
        self.audio.play_click()
        self.story_save_modal_open = False
        progress = self.settings.get_story_progress()
        saved_char = str(progress.get("character_id", "westcol"))
        self._continue_saved_story_map(saved_char)

    def _on_new_story_clicked(self) -> None:
        """Reinicia el progreso guardado de la historia y avanza a elegir un nuevo personaje."""
        self.audio.play_click()
        self.story_save_modal_open = False
        self.settings.reset_story_progress()
        self._advance_to_character_select("historia")

    def sync_audio_buttons(self) -> None:
        """Sincroniza el estado visual de los toggles con el AudioManager (SSOT)."""
        self.btn_music.toggle_state = self.audio.music_enabled
        self.btn_sound.toggle_state = self.audio.sound_enabled
        if hasattr(self, "btn_voice"):
            self.btn_voice.toggle_state = self.audio.voice_enabled

    def enter(self, params: Optional[dict] = None) -> None:
        self.sync_audio_buttons()
        # Mantiene la reproducción continua de la música de selección de modo
        self.audio.play_bgm("dodo_airlines_acnh_ost_seleccion_modo.ogg")

    def _select_mode(self, mode_id: str) -> None:
        """Gestiona la selección de modo: abre modal si hay partida guardada de historia o avanza a personajes."""
        self.audio.play_click()
        if mode_id == "arcade":
            self.juice_particles.emit_sparks((960, 550), count=10)
        elif mode_id == "libre":
            self.juice_particles.emit_sparks((1500, 550), count=10)

        if mode_id == "historia" and self.settings.has_saved_story():
            self.story_save_panel.refresh()
            self._sync_story_save_modal_refs()
            self.story_save_modal_open = True
            return

        self._advance_to_character_select(mode_id)

    def _advance_to_character_select(self, mode_id: str) -> None:
        if self.state_machine is None:
            return

        setattr(self.character_select_scene, "chosen_mode", mode_id)

        trans = SlideTransitionState(
            from_scene=self,
            to_scene=self.character_select_scene,
            direction="left",
            duration=0.65
        )
        self.state_machine.change_state(trans)

    def _return_from_character_select(self) -> None:
        if self.state_machine is None:
            return

        trans = SlideTransitionState(
            from_scene=self.character_select_scene,
            to_scene=self,
            direction="right",
            duration=0.65
        )
        self.state_machine.change_state(trans)

    def _on_character_chosen(self, character_id: str) -> None:
        mode = getattr(self.character_select_scene, "chosen_mode", "historia")
        if mode == "historia":
            # Al elegir personaje desde CharacterSelectScene se inicia una Nueva Partida limpia con ese personaje
            self.settings.reset_story_progress(character_id=character_id)
            self._enter_story_map(character_id)
        elif mode == "arcade":
            self._enter_arcade_mode(character_id)
        elif mode == "libre":
            self._enter_free_play(character_id)

    def _enter_story_map(self, character_id: str) -> None:
        if self.state_machine is None:
            return

        from scenes.loading_scene import LoadingScene
        from scenes.story_map import StoryMapScene

        def _build():
            return StoryMapScene(
                character_id=character_id,
                on_back_callback=self._return_from_subscene,
                on_main_menu_callback=self.on_main_menu_callback,
            )

        self.state_machine.change_state(LoadingScene(_build, message="Cargando mapa de Barranquilla..."))

    def _continue_saved_story_map(self, character_id: str) -> None:
        """Entra directamente a StoryMapScene desde ModeSelectScene al continuar partida guardada."""
        if self.state_machine is None:
            return

        from scenes.loading_scene import LoadingScene
        from scenes.story_map import StoryMapScene

        def _build():
            return StoryMapScene(
                character_id=character_id,
                on_back_callback=self._return_to_mode_select_from_story,
                on_main_menu_callback=self.on_main_menu_callback,
            )

        self.state_machine.change_state(LoadingScene(_build, message="Cargando partida guardada..."))

    def _return_to_mode_select_from_story(self) -> None:
        if self.state_machine is None:
            return

        current = self.state_machine.current_state
        trans = SlideTransitionState(
            from_scene=current,
            to_scene=self,
            direction="right",
            duration=0.65
        )
        self.state_machine.change_state(trans)

    def _enter_arcade_mode(self, character_id: str) -> None:
        if self.state_machine is None:
            return

        from scenes.loading_scene import LoadingScene
        from scenes.arcade_mode import ArcadeModeScene

        def _build():
            return ArcadeModeScene(
                character_id=character_id,
                on_exit_callback=self._return_from_subscene,
            )

        self.state_machine.change_state(LoadingScene(_build, message="Cargando Modo Arcade..."))

    def _enter_free_play(self, character_id: str) -> None:
        if self.state_machine is None:
            return

        from scenes.loading_scene import LoadingScene
        from scenes.free_play import FreePlayScene

        def _build():
            return FreePlayScene(
                character_id=character_id,
                on_back_callback=self._return_from_subscene,
            )

        self.state_machine.change_state(LoadingScene(_build, message="Cargando Modo Libre..."))

    def _return_from_subscene(self) -> None:
        if self.state_machine is None:
            return

        current = self.state_machine.current_state
        trans = SlideTransitionState(
            from_scene=current,
            to_scene=self.character_select_scene,
            direction="right",
            duration=0.65
        )
        self.state_machine.change_state(trans)

    def _on_back_clicked(self) -> None:
        if self.on_back_callback:
            self.on_back_callback()

    def _trigger_paloma_reaction(self) -> None:
        self.paloma_clicks_count += 1
        self.paloma_stand_timer = 0.0

        if self.paloma_state == "descanso":
            # Primeros clics: cambia a parada e inicia salto con squash de impulso
            self.paloma_state = "parada"
            self.paloma_hd = self.paloma_hd_parada
            self.paloma_jump_vel = -440.0
            self.paloma_squash = -0.20
        elif self.paloma_state == "parada":
            # Si sube demasiado (umbral de altura) o clics repetidos, despliega alas a 'volando'
            if self.paloma_jump_y < -150.0 or self.paloma_clicks_count >= 3:
                self.paloma_state = "volando"
                self.paloma_hd = self.paloma_hd_volando
                self.paloma_jump_vel = -480.0
                self.paloma_squash = 0.22
            else:
                self.paloma_jump_vel = min(-420.0, self.paloma_jump_vel - 180.0)
                self.paloma_squash = -0.16
        elif self.paloma_state == "volando":
            # Aleteo continuo en pleno vuelo (malabarismo aéreo con clics)
            self.paloma_jump_vel = -460.0
            self.paloma_squash = 0.20

        self.audio.play_pigeon()
        spark_pos = (self.paloma_rect.centerx, self.paloma_rect.centery)
        self.juice_particles.emit_sparks(spark_pos, count=8)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.story_save_modal_open:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._close_story_save_modal()
                return
            if self.story_save_panel.handle_event(event):
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self.story_save_panel.frame_rect.collidepoint(event.pos):
                    self._close_story_save_modal()
            return

        # Tecla ESCAPE o BACKSPACE para volver al menú principal
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._on_back_clicked()
            return

        if self.focus_nav.handle_event(event):
            return

        # Interacción Paloma
        if event.type == pygame.MOUSEMOTION:
            was_hov = self.paloma_hovered
            self.paloma_hovered = self.paloma_rect.collidepoint(event.pos)
            if not was_hov and self.paloma_hovered:
                self.audio.play_hover()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.paloma_rect.collidepoint(event.pos):
                self._trigger_paloma_reaction()
                return

        all_buttons = list(self.buttons)
        if hasattr(self, "btn_voice"):
            all_buttons.append(self.btn_voice)
        for btn in all_buttons:
            consumed = btn.handle_event(event)
            if consumed and event.type != pygame.MOUSEMOTION:
                break

    def update(self, dt: float) -> None:
        self.timer += dt

        if self.toast_timer > 0.0:
            self.toast_timer -= dt
            if self.toast_timer <= 0.0:
                self.toast_msg = None

        self.particles.update(dt)
        self.juice_particles.update(dt)

        if self.story_save_modal_open:
            self.story_save_panel.update(dt)
        else:
            for btn in self.buttons:
                btn.update(dt)
            if hasattr(self, "btn_voice"):
                self.btn_voice.update(dt)

        self._update_paloma(dt)

    def _update_paloma(self, dt: float) -> None:
        # 1. Curiosidad interactiva al hacer hover (comportamiento orgánico estilo iguana)
        target_curiosity = 1.0 if self.paloma_hovered else 0.0
        self.paloma_curiosity += (target_curiosity - self.paloma_curiosity) * (1.0 - math.exp(-12.0 * dt))

        # 2. Transición automática a 'volando' si la altura supera el umbral (-150 px)
        if self.paloma_jump_y < -150.0 and self.paloma_state != "volando":
            self.paloma_state = "volando"
            self.paloma_hd = self.paloma_hd_volando

        # 3. Físicas de gravedad según estado (vuelo tiene sustentación aerodinámica)
        gravity = 920.0 if self.paloma_state == "volando" else 1380.0

        if self.paloma_jump_y < 0.0 or self.paloma_jump_vel != 0.0:
            self.paloma_jump_y += self.paloma_jump_vel * dt
            self.paloma_jump_vel += gravity * dt

            # Velocidad terminal suave al planear en vuelo
            if self.paloma_state == "volando" and self.paloma_jump_vel > 390.0:
                self.paloma_jump_vel = 390.0

            # Techo suave para evitar salir de la pantalla de 1080p
            if self.paloma_jump_y < -760.0:
                self.paloma_jump_y = -760.0
                self.paloma_jump_vel = max(0.0, self.paloma_jump_vel)

            # Impacto / aterrizaje en el suelo
            if self.paloma_jump_y >= 0.0:
                self.paloma_jump_y = 0.0
                self.paloma_jump_vel = 0.0
                self.paloma_squash = -0.22
                self.paloma_squash_vel = 0.0
                self.paloma_flight_tilt = 0.0

                # Al aterrizar se queda erguida en 'parada'
                self.paloma_state = "parada"
                self.paloma_hd = self.paloma_hd_parada
                self.paloma_stand_timer = 0.0
                self.juice_particles.emit_sparks((self.paloma_rect.centerx, self.paloma_base_y), count=5)

        # 4. Regreso a 'descanso' tras reposo sin interacción en el suelo
        if self.paloma_jump_y >= 0.0 and self.paloma_state == "parada":
            self.paloma_stand_timer += dt
            if self.paloma_stand_timer > 4.5:
                self.paloma_state = "descanso"
                self.paloma_hd = self.paloma_hd_descanso
                self.paloma_clicks_count = 0
                self.paloma_stand_timer = 0.0

        # 5. Rebote de resorte elástico (Harmonic spring-damper squash & stretch)
        spring_k = 340.0
        damping_c = 16.0
        acc = -spring_k * self.paloma_squash - damping_c * self.paloma_squash_vel
        self.paloma_squash_vel += acc * dt
        self.paloma_squash += self.paloma_squash_vel * dt

        # 6. Sincronización del Rect con la geometría activa del estado actual
        cur_surf = self.paloma_surfaces[self.paloma_state]
        cur_h = int(self.target_paloma_w * cur_surf.get_height() / cur_surf.get_width())
        self.paloma_rect.width = self.target_paloma_w
        self.paloma_rect.height = cur_h
        self.paloma_rect.y = int(self.paloma_base_y - cur_h + self.paloma_jump_y)

    def render(self, surface: pygame.Surface) -> None:
        self.sync_audio_buttons()
        surface.blit(self.background, (0, 0))

        # 1. Paloma
        self._render_paloma(surface)
        self.juice_particles.render(surface)

        # 2. Título ilustrado con balanceo orgánico
        self._render_title(surface)

        # 3. Botones (Volver, Audio y Tarjetas de modo)
        for btn in self.buttons:
            btn.render(surface)
        if hasattr(self, "btn_voice"):
            self.btn_voice.render(surface)
        if (not self.state_machine or self.state_machine.current_state is self) and hasattr(self.audio, "render_voice_muted_badge"):
            self.audio.render_voice_muted_badge(surface, right_top=(1865, 134))

        # 4. Toast de notificación flotante
        self._render_toast(surface)

        # 5. Modal de Partida Guardada (Continuar vs Nueva Partida)
        if self.story_save_modal_open:
            self._render_story_save_modal(surface)

    def _render_story_save_modal(self, surface: pygame.Surface) -> None:
        """Renderiza el modal acuarela de Continuar Partida o Nueva Partida."""
        self.story_save_panel.render(surface, draw_backdrop=True)

    def _render_toast(self, surface: pygame.Surface) -> None:
        if not self.toast_msg or self.toast_timer <= 0.0:
            return

        alpha = 255
        if self.toast_timer < 0.35:
            alpha = max(0, min(255, int(self.toast_timer * 255 / 0.35)))
        elif (2.5 - self.toast_timer) < 0.2:
            alpha = max(0, min(255, int((2.5 - self.toast_timer) * 255 / 0.2)))

        font_toast = self.assets.cargarFuenteCuento(25)
        txt_surf = font_toast.render(self.toast_msg, True, (76, 48, 102))
        bw = max(460, txt_surf.get_width() + 96)
        bh = 62
        ribbon = self.assets.load_cropped_surface("cinta_estado_modal.png")
        toast_surf = pygame.transform.smoothscale(ribbon, (bw, bh))
        toast_surf.blit(txt_surf, txt_surf.get_rect(center=(bw // 2, bh // 2 - 1)))
        if alpha < 255:
            toast_surf.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)

        surface.blit(toast_surf, toast_surf.get_rect(center=(self.screen_w // 2, 850)))

    def _render_title(self, surface: pygame.Surface) -> None:
        bob_y = math.sin(self.timer * 2.1) * 5.0
        rot_angle = math.sin(self.timer * 1.3) * 0.25
        rotated_title = pygame.transform.rotozoom(self.title_base, rot_angle, 1.0)
        title_rect = rotated_title.get_rect(center=(self.title_center_x, int(self.title_center_y + bob_y)))
        surface.blit(rotated_title, title_rect)

    def _render_paloma(self, surface: pygame.Surface) -> None:
        cur_surf = self.paloma_surfaces[self.paloma_state]
        base_h = int(self.target_paloma_w * cur_surf.get_height() / cur_surf.get_width())

        # Estiramiento aéreo dinámico según velocidad (air stretch)
        air_stretch = abs(self.paloma_jump_vel) / 2200.0 if self.paloma_jump_y < -2.0 else 0.0

        rot_angle = 0.0
        peck_offset_x = 0.0

        if self.paloma_state == "descanso":
            # Picoteo rítmico y respiración sutil
            peck = math.sin(self.timer * 4.2)
            peck_offset_x = peck * 4.0 if peck > 0 else 0.0
            breath = math.sin(self.timer * 2.5)

            base_scale_y = 1.0 + breath * 0.05 + self.paloma_curiosity * 0.03
            base_scale_x = 1.0 - breath * 0.025 - self.paloma_curiosity * 0.015
            scale_y = max(0.5, base_scale_y + air_stretch + self.paloma_squash)
            scale_x = max(0.5, base_scale_x - air_stretch * 0.5 - self.paloma_squash * 0.5)

        elif self.paloma_state == "parada":
            # Paloma erguida: cabeceo alerta más dinámico
            peck = math.sin(self.timer * 7.2)
            peck_offset_x = peck * 5.0 if peck > 0 else 0.0
            breath = math.sin(self.timer * 3.6)

            base_scale_y = 1.0 + breath * 0.04 + self.paloma_curiosity * 0.05
            base_scale_x = 1.0 - breath * 0.02 - self.paloma_curiosity * 0.025
            scale_y = max(0.5, base_scale_y + air_stretch + self.paloma_squash)
            scale_x = max(0.5, base_scale_x - air_stretch * 0.5 - self.paloma_squash * 0.5)

        else:  # "volando"
            # Aleteo vibrante de alta frecuencia (Game Feel)
            flap_cycle = math.sin(self.timer * 22.0)
            flap_y = -flap_cycle * 0.12
            flap_x = flap_cycle * 0.09

            # Inclinación aerodinámica de cabeceo según velocidad vertical
            target_tilt = max(-16.0, min(16.0, -self.paloma_jump_vel * 0.035))
            self.paloma_flight_tilt += (target_tilt - self.paloma_flight_tilt) * 0.25
            rot_angle = self.paloma_flight_tilt + math.sin(self.timer * 7.0) * 3.0

            # Bamboleo horizontal en corriente de viento
            peck_offset_x = math.sin(self.timer * 4.5) * 8.0

            scale_y = max(0.4, 1.0 + flap_y + air_stretch * 0.6 + self.paloma_squash)
            scale_x = max(0.4, 1.0 + flap_x - air_stretch * 0.3 - self.paloma_squash * 0.5)

        pw = max(10, int(self.target_paloma_w * scale_x))
        ph = max(10, int(base_h * scale_y))

        scaled_pg = pygame.transform.smoothscale(cur_surf, (pw, ph))
        if abs(rot_angle) > 0.5:
            scaled_pg = pygame.transform.rotozoom(scaled_pg, rot_angle, 1.0)

        cx = self.paloma_base_x + self.target_paloma_w // 2 + peck_offset_x
        if self.paloma_state == "volando":
            cy = self.paloma_base_y - base_h // 2 + self.paloma_jump_y
            dest = scaled_pg.get_rect(center=(int(cx), int(cy)))
        else:
            draw_y = int(self.paloma_base_y + self.paloma_jump_y)
            dest = scaled_pg.get_rect(midbottom=(int(cx), draw_y))

        self.paloma_rect = dest
        surface.blit(scaled_pg, dest)
