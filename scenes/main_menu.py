import math
from typing import List, Optional, Dict, Any
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from scenes.story_map_data import STORY_CAMPAIGN_ORDER, trofeosMapa
from core.settings import SettingsManager
from core.achievements import AchievementManager
from core.map_settings import MapSettingsState
from ui.button import UIButton
from ui.focus_nav import FocusNavigator
from effects.gl_particles import GLParticleSystem
from effects.juice_particles import JuiceParticleManager
from scenes.mode_select import ModeSelectScene
from scenes.load_game import LoadGameScene, render_outlined_text
from scenes.slide_transition import SlideTransitionState

# Marcadores internos de color para las líneas de logros (no se dibujan).
LOGRO_ON = ""
LOGRO_OFF = ""

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
    "logros": {
        "title": "LOGROS DEL ÚLTIMO GUARDADO",
        "color": (135, 55, 185),
        # Las líneas se generan en vivo desde AchievementManager (ver _build_logros_lines).
        "lines": [],
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
        # Prepara en segundo plano la interfaz común de los minijuegos (sin congelar el menú)
        self.assets.precargarInterfaz(en_segundo_plano=True)

        # 1. Fondo Full HD
        raw_bg = self.assets.load_surface("fondo_main_menu.png", has_alpha=False)
        self.background = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))

        # 2. Título en 1080p
        self.title_base = self.assets.get_scaled("titulo_main_menu.png", target_width=880)
        self.title_center_x = self.screen_w // 2
        self.title_center_y = 182
        self.timer: float = 0.0

        # 3. Partículas GL y Juice
        self.particles = GLParticleSystem(count=36, screen_w=self.screen_w, screen_h=self.screen_h)
        self.juice_particles = JuiceParticleManager()

        # 4. Iguana HD en 1080p
        self._init_iguana()

        # 5. Botones en 1080p
        self._init_buttons()

        # 6. Modales acuarela y Tipografía 1080p
        self.active_modal: Optional[str] = None
        self.modal_alpha: float = 0.0
        self.font_title = self.assets.cargarFuenteTitulo(36)
        self.font_body = self.assets.cargarFuenteCuento(27)
        self.font_sub = self.assets.cargarFuenteCuento(22)
        self._modal_frame = self.assets.get_scaled("recuadro_partida_guardada.png", target_width=1060)
        import os
        close_base = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonX.jpg"), 78)
        from scenes.load_game import _poner_borde_calcomania
        self._modal_close_surf = _poner_borde_calcomania(close_base, grosor_blanco=4, grosor_tinta=2)
        self._modal_close_hovered: bool = False
        self._modal_close_rect = self._modal_close_surf.get_rect(
            center=(self.screen_w // 2 + self._modal_frame.get_width() // 2 - 96, self.screen_h // 2 - self._modal_frame.get_height() // 2 + 88)
        )
        self._modal_trofeo_on = self.assets.cargarTrofeo(48)
        self._modal_trofeo_off = self.assets.cargarTrofeo(48, enGris=True)

        # 7. Carga diferida (lazy) de Selección de Modo y Cargar Partida para arranque instantáneo
        self._mode_select_scene: Optional[ModeSelectScene] = None
        self._load_game_scene: Optional[LoadGameScene] = None

    @property
    def mode_select_scene(self) -> ModeSelectScene:
        if self._mode_select_scene is None:
            self._mode_select_scene = ModeSelectScene(
                on_back_callback=self._return_from_mode_select,
                on_main_menu_callback=self._return_from_mode_select,
            )
        return self._mode_select_scene

    @property
    def load_game_scene(self) -> LoadGameScene:
        if self._load_game_scene is None:
            self._load_game_scene = LoadGameScene(
                on_continue_story=self._continue_story_from_load,
                on_new_story=self._new_story_from_load,
                on_back=self._return_from_load_game,
            )
        return self._load_game_scene

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

    def _scale_button_tight(self, filename: str, target_width: int) -> pygame.Surface:
        """Recorta halos transparentes residuales (alpha<=20) y escala preservando proporción."""
        cropped = self.assets.load_cropped_surface(filename, alpha_threshold=20)
        orig_w, orig_h = cropped.get_size()
        target_height = max(1, int(round(orig_h * (target_width / max(1, orig_w)))))
        return pygame.transform.smoothscale(cropped, (target_width, target_height))

    def girarTono(self, imagen: pygame.Surface, grados: float) -> pygame.Surface:
        import numpy as np
        rgb = pygame.surfarray.array3d(imagen).astype(np.float32)
        y = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        i = rgb @ np.array([0.596, -0.274, -0.322], dtype=np.float32)
        q = rgb @ np.array([0.211, -0.523, 0.312], dtype=np.float32)
        angulo = math.radians(grados)
        i2 = i * math.cos(angulo) - q * math.sin(angulo)
        q2 = i * math.sin(angulo) + q * math.cos(angulo)
        r = y + 0.956 * i2 + 0.621 * q2
        g = y - 0.272 * i2 - 0.647 * q2
        b = y - 1.106 * i2 + 1.703 * q2
        girada = imagen.copy()
        pygame.surfarray.pixels3d(girada)[...] = np.clip(np.stack([r, g, b], axis=2), 0, 255).astype(np.uint8)
        return girada

    def textoConContornoMenu(self, fuente, texto: str, color, colorContorno) -> pygame.Surface:
        cuerpo = fuente.render(texto, True, color)
        borde = fuente.render(texto, True, colorContorno)
        lienzo = pygame.Surface((cuerpo.get_width() + 8, cuerpo.get_height() + 8), pygame.SRCALPHA)
        for grados in range(0, 360, 30):
            dx = round(math.cos(math.radians(grados)) * 4)
            dy = round(math.sin(math.radians(grados)) * 4)
            lienzo.blit(borde, (4 + dx, 4 + dy))
        lienzo.blit(cuerpo, (4, 4))
        return lienzo

    def armarBotonesMenu(self):
        import os
        try:
            naranja = self.assets.load_cropped_surface("boton_acuarela_naranja.png")
            verde = self.assets.load_cropped_surface("boton_acuarela_verde.png")
            morado = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonMorado.jpg"), 440)
            rojo = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonRojo.jpg"), 440)
        except Exception as e:
            print(f"Aviso: no se pudieron armar los botones del menú: {e}")
            return None
        tam = (440, 104)
        amarillo = self.girarTono(naranja, -25)
        azul = self.girarTono(morado, 80)
        rosado = self.girarTono(rojo, 30)
        bases = [
            ("Jugar", amarillo, (150, 96, 10)),
            ("Cargar partida", verde, (20, 100, 60)),
            ("Opciones", azul, (28, 58, 120)),
            ("Logros", morado, (70, 30, 110)),
            ("Salir", rosado, (140, 20, 80)),
        ]
        tamLetra = 46
        fuente = self.assets.cargarFuenteTitulo(tamLetra)
        while tamLetra > 24 and max(fuente.size(n)[0] for n, _, _ in bases) > tam[0] * 0.78:
            tamLetra -= 2
            fuente = self.assets.cargarFuenteTitulo(tamLetra)
        listos = []
        for nombre, base, contorno in bases:
            boton = pygame.transform.smoothscale(base, tam)
            letras = self.textoConContornoMenu(fuente, nombre, (255, 248, 236), contorno)
            boton.blit(letras, letras.get_rect(center=(tam[0] // 2, tam[1] // 2 - 3)))
            listos.append(boton)
        return listos

    def _init_buttons(self) -> None:
        audio_frames = self.assets.get_audio_button_frames(target_size=86)
        music_on, music_off, sound_on, sound_off = audio_frames[0], audio_frames[1], audio_frames[2], audio_frames[3]

        botones = self.armarBotonesMenu()
        if botones is not None:
            btn_jugar_surf, btn_cargar_surf, btn_opciones_surf, btn_logros_surf, btn_salir_surf = botones
            paso = btn_jugar_surf.get_height() + 22
            centers_y = [410 + i * paso for i in range(5)]
        else:
            btn_jugar_surf = self._scale_button_tight("boton_jugar_main_menu.png", target_width=496)
            btn_cargar_surf = self._scale_button_tight("boton_cargar_partida_main_menu.png", target_width=364)
            btn_opciones_surf = self._scale_button_tight("boton_opciones_main_menu.png", target_width=366)
            btn_logros_surf = self._scale_button_tight("boton_logros_mapa.png", target_width=364)
            btn_logros_surf = pygame.transform.smoothscale(
                btn_logros_surf, (btn_logros_surf.get_width(), btn_logros_surf.get_height() - 4)
            )
            btn_salir_surf = self._scale_button_tight("boton_salir_main_menu.png", target_width=366)
            centers_y = [414, 544, 666, 784, 902]
        self.btn_jugar = UIButton((self.screen_w // 2, centers_y[0]), btn_jugar_surf, on_click=self._on_play_clicked)
        self.btn_cargar = UIButton((self.screen_w // 2, centers_y[1]), btn_cargar_surf, on_click=self._on_load_game_clicked)
        self.btn_opciones = UIButton((self.screen_w // 2, centers_y[2]), btn_opciones_surf, on_click=self._on_open_settings)
        self.btn_logros = UIButton((self.screen_w // 2, centers_y[3]), btn_logros_surf, on_click=lambda: self._open_modal("logros"))
        self.btn_salir = UIButton((self.screen_w // 2, centers_y[4]), btn_salir_surf, on_click=self._on_exit_clicked)

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

        self.btn_voice = UIButton(
            center_pos=(1598, 78),
            normal_sprite=self.assets.get_voice_button_frames(target_size=86)[0],
            alt_sprite=self.assets.get_voice_button_frames(target_size=86)[1],
            is_toggle=True,
            initial_toggle_state=self.audio.voice_enabled,
            on_click=self.audio.toggle_voice
        )

        self.buttons: List[UIButton] = [
            self.btn_jugar,
            self.btn_cargar,
            self.btn_opciones,
            self.btn_logros,
            self.btn_salir,
            self.btn_music,
            self.btn_sound
        ]
        self._draws_voice_badge = True
        # Teclado / mando: foco inicial en "Jugar"
        self.focus_nav = FocusNavigator(
            lambda: [*self.buttons, self.btn_voice] if hasattr(self, "btn_voice") else self.buttons,
            default_index=0,
        )

    def sync_audio_buttons(self) -> None:
        """Sincroniza el estado visual de los toggles con el AudioManager (SSOT)."""
        self.btn_music.toggle_state = self.audio.music_enabled
        self.btn_sound.toggle_state = self.audio.sound_enabled
        self.btn_voice.toggle_state = self.audio.voice_enabled

    def enter(self, params: Optional[dict] = None) -> None:
        self.sync_audio_buttons()
        self.audio.play_bgm("7am_ancpg_ost_main_menu.ogg")

    def _build_logros_lines(self) -> List[str]:
        """Resumen de la última partida guardada y estado de cada trofeo oficial del mapa."""
        settings = SettingsManager.get_instance()
        summary = settings.get_story_save_summary()
        if not summary["has_save"]:
            header = "Aún no hay partida guardada en Modo Historia."
        else:
            header = f"{summary['character_name']} · Niveles {summary['levels_cleared']}/{len(STORY_CAMPAIGN_ORDER)}"
        obtenidos = set(settings.get("trofeosObtenidos", []) or [])
        unlocked = len([t for t in trofeosMapa if t["id"] in obtenidos])
        lines = [f"{header} · Trofeos: {unlocked} / {len(trofeosMapa)}"]
        for trofeo in trofeosMapa:
            if trofeo["id"] in obtenidos:
                lines.append(f"{LOGRO_ON}{trofeo['nombre']} — ¡Desbloqueado!")
            else:
                lines.append(f"{LOGRO_OFF}Trofeo escondido — Sigue explorando")
        return lines

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
        if self._mode_select_scene is None:
            from scenes.loading_scene import LoadingScene

            def _build_mode():
                sc = self.mode_select_scene
                sc.sync_audio_buttons()
                return sc

            self.state_machine.change_state(
                LoadingScene(_build_mode, message="Cargando selección de modo...")
            )
            return

        self.mode_select_scene.sync_audio_buttons()
        trans_to_mode = SlideTransitionState(
            from_scene=self,
            to_scene=self.mode_select_scene,
            direction="left",
            duration=0.65
        )
        self.state_machine.change_state(trans_to_mode)

    def _on_load_game_clicked(self) -> None:
        if not self.state_machine:
            return

        self.audio.play_click()
        if self._load_game_scene is None:
            from scenes.loading_scene import LoadingScene

            def _build_load():
                sc = self.load_game_scene
                sc.enter()
                return sc

            self.state_machine.change_state(
                LoadingScene(_build_load, message="Cargando partidas guardadas...")
            )
            return

        self.load_game_scene.enter()
        trans_to_load = SlideTransitionState(
            from_scene=self,
            to_scene=self.load_game_scene,
            direction="left",
            duration=0.55
        )
        self.state_machine.change_state(trans_to_load)

    def _return_from_load_game(self, from_scene: Optional[BaseState] = None) -> None:
        if not self.state_machine:
            return

        self.audio.play_bgm("7am_ancpg_ost_main_menu.ogg")
        self.sync_audio_buttons()
        trans = SlideTransitionState(
            from_scene=from_scene or self.load_game_scene,
            to_scene=self,
            direction="right",
            duration=0.55
        )
        self.state_machine.change_state(trans)

    def _continue_story_from_load(self, character_id: str) -> None:
        if not self.state_machine:
            return

        from scenes.story_map import StoryMapScene
        story_map = StoryMapScene(
            character_id=character_id,
            on_back_callback=lambda: self._return_from_mode_select(self.state_machine.current_state if self.state_machine else None),
            on_main_menu_callback=self._return_from_mode_select,
        )
        trans = SlideTransitionState(
            from_scene=self.load_game_scene,
            to_scene=story_map,
            direction="left",
            duration=0.65
        )
        self.state_machine.change_state(trans)

    def _new_story_from_load(self) -> None:
        if not self.state_machine:
            return

        if self.mode_select_scene.state_machine is None:
            self.mode_select_scene.state_machine = self.state_machine
        setattr(self.mode_select_scene.character_select_scene, "chosen_mode", "historia")
        self.audio.play_bgm("dodo_airlines_acnh_ost_seleccion_modo.ogg")
        trans = SlideTransitionState(
            from_scene=self.load_game_scene,
            to_scene=self.mode_select_scene.character_select_scene,
            direction="left",
            duration=0.65
        )
        self.state_machine.change_state(trans)

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
            if event.type == pygame.MOUSEMOTION:
                was_hov = self._modal_close_hovered
                self._modal_close_hovered = self._modal_close_rect.collidepoint(event.pos)
                if self._modal_close_hovered and not was_hov:
                    self.audio.play_hover()
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self.active_modal = None
                self._modal_close_hovered = False
                self.audio.play_click()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                frame_rect = self._modal_frame.get_rect(center=(self.screen_w // 2, self.screen_h // 2))
                if self._modal_close_rect.collidepoint(event.pos) or not frame_rect.collidepoint(event.pos):
                    self.active_modal = None
                    self._modal_close_hovered = False
                    self.audio.play_click()
            return

        if self.focus_nav.handle_event(event):
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

        all_buttons = list(self.buttons)
        if hasattr(self, "btn_voice"):
            all_buttons.append(self.btn_voice)
        for btn in all_buttons:
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
            if hasattr(self, "btn_voice"):
                self.btn_voice.update(dt)

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
        if hasattr(self, "btn_voice"):
            self.btn_voice.render(surface)
        if (not self.state_machine or self.state_machine.current_state is self) and hasattr(self.audio, "render_voice_muted_badge"):
            self.audio.render_voice_muted_badge(surface, right_top=(1865, 134))

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
        overlay.fill((18, 12, 32, alpha))
        surface.blit(overlay, (0, 0))

        frame_rect = self._modal_frame.get_rect(center=(self.screen_w // 2, self.screen_h // 2))
        surface.blit(self._modal_frame, frame_rect.topleft)

        self._modal_close_rect = self._modal_close_surf.get_rect(
            center=(frame_rect.right - 92, frame_rect.top + 90)
        )
        close_draw = (
            pygame.transform.smoothscale_by(self._modal_close_surf, 1.08)
            if self._modal_close_hovered
            else self._modal_close_surf
        )
        surface.blit(close_draw, close_draw.get_rect(center=self._modal_close_rect.center))

        t_render = render_outlined_text(
            self.font_title,
            modal_info["title"],
            (92, 50, 126),
            (255, 250, 240),
            thickness=2,
        )
        t_pos = t_render.get_rect(center=(frame_rect.centerx + 16, frame_rect.top + 148))
        surface.blit(t_render, t_pos)

        settings = SettingsManager.get_instance()
        if self.active_modal == "logros":
            summary = settings.get_story_save_summary()
            obtenidos = set(settings.get("trofeosObtenidos", []) or [])
            unlocked = len([t for t in trofeosMapa if t["id"] in obtenidos])
            if summary["has_save"]:
                sub_text = f"{summary['character_name']} · {summary['levels_cleared']}/{len(STORY_CAMPAIGN_ORDER)} distritos · {unlocked}/{len(trofeosMapa)} trofeos"
            else:
                sub_text = f"Sin partida guardada · {unlocked}/{len(trofeosMapa)} trofeos"
            sub_surf = self.font_sub.render(sub_text, True, (112, 82, 134))
            surface.blit(sub_surf, sub_surf.get_rect(center=(frame_rect.centerx + 16, frame_rect.top + 194)))

            row_y = frame_rect.top + 252
            row_step = 74
            icon_x = frame_rect.left + 178
            text_x = icon_x + 68
            max_desc_w = 510
            for trofeo in trofeosMapa:
                got = trofeo["id"] in obtenidos
                icon = self._modal_trofeo_on if got else self._modal_trofeo_off
                surface.blit(icon, icon.get_rect(center=(icon_x, row_y)))
                if got:
                    title_str = trofeo["nombre"]
                    desc_str = trofeo["descripcion"]
                    col_t = (38, 126, 62)
                    col_d = (92, 58, 38)
                else:
                    title_str = "Trofeo escondido"
                    desc_str = "Sigue explorando el mapa"
                    col_t = (116, 92, 74)
                    col_d = (148, 124, 106)
                t_row = self.font_body.render(title_str, True, col_t)
                d_row = self.font_sub.render(desc_str, True, col_d)
                if d_row.get_width() > max_desc_w:
                    sc = max_desc_w / float(d_row.get_width())
                    d_row = pygame.transform.smoothscale(
                        d_row, (max_desc_w, max(12, int(round(d_row.get_height() * sc))))
                    )
                surface.blit(t_row, (text_x, row_y - 24))
                surface.blit(d_row, (text_x, row_y + 4))
                row_y += row_step
            return

        music_status = "ACTIVADA" if self.audio.music_enabled else "MUTED"
        sfx_status = "ACTIVADO" if self.audio.sound_enabled else "MUTED"
        summary = settings.get_story_save_summary()
        arcade_best = settings.get_arcade_high_score()
        story_score = summary["high_score"]
        completed_count = summary["levels_cleared"]
        active_char = summary["character_name"] if summary["has_save"] else "Ninguno"
        completion_pct = int((completed_count / float(len(STORY_CAMPAIGN_ORDER))) * 100)

        cur_y = frame_rect.top + 216
        for line in modal_info["lines"]:
            if not line:
                cur_y += 12
                continue
            formatted_line = line.format(
                music_status=music_status,
                sfx_status=sfx_status,
                arcade_best=arcade_best,
                story_score=story_score,
                completed_count=completed_count,
                active_char=active_char,
                completion_pct=completion_pct,
            )
            color = (74, 48, 34) if not formatted_line.startswith("(") else (130, 96, 72)
            line_surf = self.font_body.render(formatted_line, True, color)
            surface.blit(line_surf, line_surf.get_rect(center=(frame_rect.centerx, cur_y)))
            cur_y += 42

    def camera_dwell_target(self, pos: tuple[int, int]) -> Optional[Any]:
        """Solo permite dwell-click cuando el puntero está físicamente sobre un botón interactivo o modal."""
        if getattr(self, "active_modal", None):
            return ("modal", self.active_modal)
        all_buttons = list(self.buttons)
        if hasattr(self, "btn_voice"):
            all_buttons.append(self.btn_voice)
        for i, btn in enumerate(all_buttons):
            if hasattr(btn, "rect") and btn.rect.collidepoint(pos):
                return ("btn", i)
        return None
