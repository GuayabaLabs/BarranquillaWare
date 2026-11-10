import math
from typing import List, Optional, Callable
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from ui.button import UIButton
from effects.gl_particles import GLParticleSystem
from effects.juice_particles import JuiceParticleManager
from scenes.character_select import CharacterSelectScene
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
    def __init__(self, on_back_callback: Optional[Callable[[], None]] = None) -> None:
        super().__init__()
        self.screen_w = 1920
        self.screen_h = 1080
        self.on_back_callback = on_back_callback

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        # 1. Fondo de Selección de Modo
        raw_bg = self.assets.load_surface("fondo_seleccion_modo.png", has_alpha=False)
        self.background = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))

        # 2. Partículas y Juice
        self.particles = GLParticleSystem(count=36, screen_w=self.screen_w, screen_h=self.screen_h)
        self.juice_particles = JuiceParticleManager()
        self.timer: float = 0.0

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

        # 6. Botones
        self._init_buttons()

    def _init_paloma(self) -> None:
        self.paloma_hd = self.assets.load_cropped_surface("paloma_seleccion_modo.png")
        self.target_paloma_w = 260
        hd_w = self.paloma_hd.get_width()
        hd_h = self.paloma_hd.get_height()
        self.target_paloma_h = int(self.target_paloma_w * hd_h / hd_w)

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

    def sync_audio_buttons(self) -> None:
        """Sincroniza el estado visual de los toggles con el AudioManager (SSOT)."""
        self.btn_music.toggle_state = self.audio.music_enabled
        self.btn_sound.toggle_state = self.audio.sound_enabled

    def enter(self, params: Optional[dict] = None) -> None:
        self.sync_audio_buttons()
        # Mantiene la reproducción continua de la música de selección de modo
        self.audio.play_bgm("dodo_airlines_acnh_ost_seleccion_modo.ogg")

    def _select_mode(self, mode_id: str) -> None:
        """Entra directamente a la selección de personaje tras pulsar cualquier modo de juego."""
        self.audio.play_click()
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
            self._enter_story_map(character_id)
        else:
            print(f"Modo '{mode}' seleccionado con personaje '{character_id}' (pendiente de implementación).")

    def _enter_story_map(self, character_id: str) -> None:
        if self.state_machine is None:
            return

        from scenes.story_map import StoryMapScene
        story_map = StoryMapScene(
            character_id=character_id,
            on_back_callback=self._return_from_story_map
        )

        trans = SlideTransitionState(
            from_scene=self.character_select_scene,
            to_scene=story_map,
            direction="left",
            duration=0.65
        )
        self.state_machine.change_state(trans)

    def _return_from_story_map(self) -> None:
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
        self.paloma_jump_vel = -280.0
        self.audio.play_pigeon()
        head_pos = (self.paloma_base_x + 130, self.paloma_base_y - 120 + self.paloma_jump_y)
        self.juice_particles.emit_sparks(head_pos, count=7)

    def handle_event(self, event: pygame.event.Event) -> None:
        # Tecla ESCAPE o BACKSPACE para volver al menú principal
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._on_back_clicked()
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

        for btn in self.buttons:
            consumed = btn.handle_event(event)
            if consumed and event.type != pygame.MOUSEMOTION:
                break

    def update(self, dt: float) -> None:
        self.timer += dt

        self.particles.update(dt)
        self.juice_particles.update(dt)

        for btn in self.buttons:
            btn.update(dt)

        self._update_paloma(dt)

    def _update_paloma(self, dt: float) -> None:
        # Físicas de salto
        if self.paloma_jump_y < 0.0 or self.paloma_jump_vel != 0.0:
            self.paloma_jump_y += self.paloma_jump_vel * dt
            self.paloma_jump_vel += 1250.0 * dt
            if self.paloma_jump_y >= 0.0:
                self.paloma_jump_y = 0.0
                self.paloma_jump_vel = 0.0
                self.paloma_squash = -0.16
                self.paloma_squash_vel = 0.0

        # Rebote de resorte
        spring_k = 360.0
        damping_c = 16.0
        acc = -spring_k * self.paloma_squash - damping_c * self.paloma_squash_vel
        self.paloma_squash_vel += acc * dt
        self.paloma_squash += self.paloma_squash_vel * dt

        self.paloma_rect.y = int(self.paloma_base_y - self.target_paloma_h + self.paloma_jump_y)

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

    def _render_title(self, surface: pygame.Surface) -> None:
        bob_y = math.sin(self.timer * 2.1) * 5.0
        rot_angle = math.sin(self.timer * 1.3) * 0.25
        rotated_title = pygame.transform.rotozoom(self.title_base, rot_angle, 1.0)
        title_rect = rotated_title.get_rect(center=(self.title_center_x, int(self.title_center_y + bob_y)))
        surface.blit(rotated_title, title_rect)

    def _render_paloma(self, surface: pygame.Surface) -> None:
        # Movimiento orgánico de paloma: picoteo/cabeceo rítmico y respiración
        peck = math.sin(self.timer * 4.2)
        peck_offset_x = peck * 4.0 if peck > 0 else 0.0  # Cabeza hacia adelante
        breath = math.sin(self.timer * 2.5)

        scale_y = max(0.5, 1.0 + breath * 0.05 + self.paloma_squash)
        scale_x = max(0.5, 1.0 - breath * 0.025 - self.paloma_squash * 0.5)

        pw = max(10, int(self.target_paloma_w * scale_x))
        ph = max(10, int(self.target_paloma_h * scale_y))

        scaled_pg = pygame.transform.smoothscale(self.paloma_hd, (pw, ph))
        draw_x = int(self.paloma_base_x + peck_offset_x)
        draw_y = int(self.paloma_base_y + self.paloma_jump_y)
        dest = scaled_pg.get_rect(bottomleft=(draw_x, draw_y))
        surface.blit(scaled_pg, dest)
