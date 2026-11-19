import os
import sys
from typing import Optional
import pygame
import numpy as np

from core.state_machine import StateMachine
from core.audio_manager import AudioManager
from core.settings import SettingsManager

class Engine:
    """
    Motor principal de BarranquillaWare con pipeline híbrido OpenGL + ModernGL:
    - Canvas virtual nativo Full HD 1920x1080 (16:9).
    - Shaders GLSL para partículas instanciadas (volteo 3D y curvatura por viento).
    - Viewport con Letterbox / Pillarbox automático al redimensionar (e.g. 1280x720) o en Fullscreen.
    - Mapeo inverso de coordenadas de mouse a resolución virtual 1080p.
    - Gameloop desacoplado a 60 FPS con Delta Time (dt).
    """
    VIRTUAL_WIDTH: int = 1920
    VIRTUAL_HEIGHT: int = 1080
    FPS: int = 60

    def __init__(self, title: str = "BarranquillaWare", enable_gl: bool = True) -> None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
        except Exception:
            pass
        pygame.init()
        pygame.font.init()

        self.title = title
        self.settings = SettingsManager.get_instance()
        self.enable_gl = enable_gl and (os.environ.get("SDL_VIDEODRIVER") != "dummy")

        # Cargar resolución de ventana preferida o por defecto 1920x1080
        self.width = int(self.settings.get("window_width", self.VIRTUAL_WIDTH))
        self.height = int(self.settings.get("window_height", self.VIRTUAL_HEIGHT))
        self.is_fullscreen = bool(self.settings.get("fullscreen", False))

        self.virtual_surface = pygame.Surface((self.VIRTUAL_WIDTH, self.VIRTUAL_HEIGHT))
        pygame.display.set_caption(self.title)

        self.gl_renderer = None
        if self.enable_gl:
            self._init_opengl()

        if not self.enable_gl:
            self._init_software_display()

        self.clock = pygame.time.Clock()
        self.is_running: bool = False
        self.total_time: float = 0.0

        self.audio = AudioManager.get_instance()
        self.state_machine = StateMachine()

        # Soporte universal de Mandos / Joysticks (Plug & Play)
        pygame.joystick.init()
        self.joysticks = {}
        self._refresh_joysticks()

        # Entrada persistente de Visión / Gestos MediaPipe en segundo plano
        from core.camera_gestures import CameraGestureInput
        self.camera_input = CameraGestureInput.get_instance()
        # Iniciar cámara en segundo plano sin bloquear el arranque ni el gameloop
        if self.camera_input.available and os.environ.get("SDL_VIDEODRIVER") != "dummy":
            self.camera_input.start()

        # Sistema de Puntero Lapicero Cinético por Hover (MediaPipe en Menús y Overworld)
        self.cam_cursor_x: float = float(self.VIRTUAL_WIDTH // 2)
        self.cam_cursor_y: float = float(self.VIRTUAL_HEIGHT // 2)
        self.cam_hover_time: float = 0.0
        self.cam_hover_duration: float = 0.70  # 700 ms de permanencia para confirmar clic automático
        self.cam_hover_anchor_x: float = float(self.VIRTUAL_WIDTH // 2)
        self.cam_hover_anchor_y: float = float(self.VIRTUAL_HEIGHT // 2)
        self.cam_hover_tolerance: float = 38.0  # Margen de temblor permitido en píxeles
        self.cam_click_cooldown: float = 0.0
        self.cam_pencil_surf: Optional[pygame.Surface] = None
        self._init_cam_pencil_sprite()

    def _init_cam_pencil_sprite(self) -> None:
        try:
            from core.asset_manager import AssetManager
            assets = AssetManager.get_instance()
            raw = assets.load_surface("puntero_lapiz.png", has_alpha=True)
            w = 58
            h = int(raw.get_height() * (w / float(raw.get_width())))
            self.cam_pencil_surf = pygame.transform.smoothscale(raw, (w, h))
        except Exception:
            self.cam_pencil_surf = None

    def _refresh_joysticks(self) -> None:
        self.joysticks.clear()
        for i in range(pygame.joystick.get_count()):
            try:
                joy = pygame.joystick.Joystick(i)
                joy.init()
                self.joysticks[joy.get_instance_id()] = joy
            except Exception:
                pass

    def _init_opengl(self) -> None:
        try:
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
            
            flags = pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
            if self.is_fullscreen:
                flags |= pygame.FULLSCREEN

            self.screen = pygame.display.set_mode((self.width, self.height), flags)
            from core.renderer_gl import GLRenderer
            self.gl_renderer = GLRenderer(self.VIRTUAL_WIDTH, self.VIRTUAL_HEIGHT)
        except Exception as e:
            print(f"Aviso: Fallback a software 2D (No se pudo iniciar ModernGL: {e})")
            self.enable_gl = False

    def _init_software_display(self) -> None:
        flags = pygame.DOUBLEBUF | pygame.RESIZABLE
        if self.is_fullscreen:
            flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((self.width, self.height), flags)

    def toggle_fullscreen(self) -> None:
        entering_fullscreen = not self.is_fullscreen

        if entering_fullscreen:
            # Capturar el tamaño real de la ventana antes de cambiar a fullscreen.
            if not (pygame.display.get_surface().get_flags() & pygame.FULLSCREEN):
                current_size = pygame.display.get_window_size()
                if current_size[0] > 0 and current_size[1] > 0:
                    self.width, self.height = current_size
                    self.settings.data["window_width"] = self.width
                    self.settings.data["window_height"] = self.height
            self.is_fullscreen = True
            self.settings.data["fullscreen"] = True
            flags = (pygame.OPENGL | pygame.DOUBLEBUF) if self.enable_gl else 0
            flags |= pygame.FULLSCREEN
            sizes = pygame.display.get_desktop_sizes()
            target_size = sizes[0] if sizes else (self.VIRTUAL_WIDTH, self.VIRTUAL_HEIGHT)
        else:
            self.is_fullscreen = False
            self.settings.data["fullscreen"] = False
            flags = (pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE) if self.enable_gl else (pygame.DOUBLEBUF | pygame.RESIZABLE)
            self.width = max(640, int(self.settings.get("window_width", self.VIRTUAL_WIDTH)))
            self.height = max(360, int(self.settings.get("window_height", self.VIRTUAL_HEIGHT)))
            target_size = (self.width, self.height)

        self.screen = pygame.display.set_mode(target_size, flags)
        actual_size = pygame.display.get_window_size()
        if not self.is_fullscreen and actual_size[0] > 0 and actual_size[1] > 0:
            self.width, self.height = actual_size
        self.settings.save()

    def _map_mouse_event(self, event: pygame.event.Event) -> pygame.event.Event:
        """Traduce las coordenadas del mouse de la ventana a coordenadas virtuales (1920x1080)."""
        if not self.enable_gl or self.gl_renderer is None:
            win_w, win_h = pygame.display.get_window_size()
            scale_x = self.VIRTUAL_WIDTH / max(1, win_w)
            scale_y = self.VIRTUAL_HEIGHT / max(1, win_h)
            virt_x = int(event.pos[0] * scale_x)
            virt_y = int(event.pos[1] * scale_y)
            event_dict = dict(event.__dict__)
            event_dict['pos'] = (virt_x, virt_y)
            if 'rel' in event_dict:
                event_dict['rel'] = (int(event_dict['rel'][0] * scale_x), int(event_dict['rel'][1] * scale_y))
            return pygame.event.Event(event.type, event_dict)

        win_w, win_h = pygame.display.get_window_size()
        self.gl_renderer.compute_viewport(win_w, win_h)
        virt_x, virt_y = self.gl_renderer.screen_to_virtual(event.pos[0], event.pos[1])
        event_dict = dict(event.__dict__)
        event_dict['pos'] = (virt_x, virt_y)

        if 'rel' in event_dict and self.gl_renderer.scale > 0:
            rel_x = int(event_dict['rel'][0] / self.gl_renderer.scale)
            rel_y = int(event_dict['rel'][1] / self.gl_renderer.scale)
            event_dict['rel'] = (rel_x, rel_y)

        return pygame.event.Event(event.type, event_dict)

    def _translate_joystick_event(self, event: pygame.event.Event) -> list:
        """Traduce eventos de gamepad a teclado virtual para compatibilidad universal."""
        from core import input_state
        translated = []
        current = self.state_machine.current_state
        custom_keys = getattr(current, "GAMEPAD_BUTTON_KEYS", None) or {}
        input_state.set_input_device("gamepad")

        def _emit(key_type: int, key: int) -> None:
            if key_type == pygame.KEYDOWN:
                input_state.VIRTUAL_KEYS.add(key)
            else:
                input_state.VIRTUAL_KEYS.discard(key)
            data = {"key": key, "mod": 0, "scancode": 0, "gamepad": True}
            if key_type == pygame.KEYDOWN:
                data["unicode"] = " " if key == pygame.K_SPACE else ""
            translated.append(pygame.event.Event(key_type, data))

        if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
            key_type = pygame.KEYDOWN if event.type == pygame.JOYBUTTONDOWN else pygame.KEYUP
            if event.button in custom_keys:
                _emit(key_type, custom_keys[event.button])
                return translated
            btn_map = {0: pygame.K_SPACE, 1: pygame.K_ESCAPE, 2: pygame.K_RETURN, 3: pygame.K_RETURN, 6: pygame.K_ESCAPE, 7: pygame.K_ESCAPE}
            if event.button in btn_map:
                _emit(key_type, btn_map[event.button])
            return translated

        if not hasattr(self, "_joy_held_dirs"):
            self._joy_held_dirs = {"hat": set(), "axis_x": None, "axis_y": None}

        if event.type == pygame.JOYHATMOTION:
            hx, hy = event.value
            desired = set()
            if hx < 0:
                desired.add(pygame.K_LEFT)
            elif hx > 0:
                desired.add(pygame.K_RIGHT)
            if hy > 0:
                desired.add(pygame.K_UP)
            elif hy < 0:
                desired.add(pygame.K_DOWN)
            prev = self._joy_held_dirs["hat"]
            for k in prev - desired:
                _emit(pygame.KEYUP, k)
            for k in desired - prev:
                _emit(pygame.KEYDOWN, k)
            self._joy_held_dirs["hat"] = desired
        elif event.type == pygame.JOYAXISMOTION:
            enter_dz, exit_dz = 0.50, 0.30
            for axis, name, neg_k, pos_k in (
                (0, "axis_x", pygame.K_LEFT, pygame.K_RIGHT),
                (1, "axis_y", pygame.K_UP, pygame.K_DOWN),
            ):
                if event.axis != axis:
                    continue
                prev_k = self._joy_held_dirs[name]
                if prev_k is None:
                    new_k = neg_k if event.value < -enter_dz else pos_k if event.value > enter_dz else None
                else:
                    if event.value < -enter_dz:
                        new_k = neg_k
                    elif event.value > enter_dz:
                        new_k = pos_k
                    elif abs(event.value) < exit_dz:
                        new_k = None
                    else:
                        new_k = prev_k
                if new_k != prev_k:
                    if prev_k is not None:
                        _emit(pygame.KEYUP, prev_k)
                    if new_k is not None:
                        _emit(pygame.KEYDOWN, new_k)
                    self._joy_held_dirs[name] = new_k
        return translated

    def _dispatch_event(self, event: pygame.event.Event) -> None:
        """Despacha un evento de entrada respetando la pausa global de microjuegos."""
        if (event.type in (pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)
                and not getattr(event, "gamepad", False)):
            from core import input_state
            input_state.set_input_device("keyboard")
        current = self.state_machine.current_state
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and hasattr(current, "open_pause_menu"):
            current.open_pause_menu()
            return
        self.state_machine.handle_event(event)

    def _dispatch_input_event(self, event: pygame.event.Event) -> None:
        current = self.state_machine.current_state
        self._dispatch_event(event)
        if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
            handles_raw = getattr(current, "handles_raw_gamepad", None)
            if callable(handles_raw) and handles_raw(event):
                return
            for virt_evt in self._translate_joystick_event(event):
                self._dispatch_event(virt_evt)

    def run(self) -> None:
        self.is_running = True

        while self.is_running:
            raw_dt = self.clock.tick(self.FPS) / 1000.0
            dt = min(raw_dt, 0.08)
            self.total_time += dt

            # 1. Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False
                    break

                if event.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:
                        # Pygame/SDL ya redimensionó la ventana. No llamar a
                        # set_mode aquí: en Windows eso reinicia el drag del borde.
                        self.width, self.height = event.w, event.h
                        self.settings.data["window_width"] = self.width
                        self.settings.data["window_height"] = self.height
                    continue

                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                    continue

                if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    self._refresh_joysticks()
                    continue

                if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    event = self._map_mouse_event(event)

                self._dispatch_input_event(event)

            # 1.5. Inyección de eventos ópticos del Puntero Lapicero MediaPipe (Hover & Clic)
            if os.environ.get("SDL_VIDEODRIVER") != "dummy":
                self.camera_input.keep_alive()
            self._update_camera_cursor_interaction(dt)

            # 2. Lógica
            self.state_machine.update(dt)
            if hasattr(self, "audio") and hasattr(self.audio, "update"):
                self.audio.update(dt)

            # 3. Renderizado
            self._render_current_frame()
            pygame.display.flip()

        self.shutdown()

    def _render_current_frame(self) -> None:
        current_state = self.state_machine.current_state
        win_w, win_h = pygame.display.get_window_size()
        particles = getattr(current_state, "particles", None)

        # Solo procesar como sistema de partículas del motor si implementa la interfaz requerida
        has_gl_particles = particles is not None and hasattr(particles, "get_instance_bytes")
        has_sw_particles = particles is not None and hasattr(particles, "render_software")

        # Parámetros visuales globales
        brightness = max(0.5, min(1.5, float(self.settings.get("brightness", 1.0))))
        mode = self.settings.get("colorblind_mode", "off")
        intensity = max(0.0, min(1.0, float(self.settings.get("colorblind_intensity", 0.0))))

        matrices = {
            "protanopia": np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]], dtype=np.float32),
            "deuteranopia": np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]], dtype=np.float32),
            "tritanopia": np.array([[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]], dtype=np.float32),
        }
        matrix = matrices.get(mode)

        if self.enable_gl and self.gl_renderer is not None:
            self.state_machine.render(self.virtual_surface)
            # El lapicero va DESPUÉS de la escena para que no quede oculto debajo del fondo.
            self._render_camera_cursor(self.virtual_surface)

            part_bytes = b""
            part_count = 0
            if has_gl_particles:
                part_bytes = particles.get_instance_bytes()
                part_count = particles.count

            # El post-procesado visual se ejecuta en GPU a 60 FPS sin bloquear la CPU
            self.gl_renderer.render_frame(
                pygame_surface=self.virtual_surface,
                particle_instance_data=part_bytes,
                particle_count=part_count,
                time_seconds=self.total_time,
                win_w=win_w,
                win_h=win_h,
                brightness=brightness,
                color_matrix=matrix,
                color_intensity=intensity if matrix is not None else 0.0
            )
        else:
            self.state_machine.render(self.virtual_surface)
            if has_sw_particles:
                particles.render_software(self.virtual_surface)
            self._render_camera_cursor(self.virtual_surface)

            self._apply_visual_settings(self.virtual_surface, brightness, matrix, intensity)

            # Mantener 16:9 también sin OpenGL: escalar el lienzo completo a
            # la ventana deformaba la imagen y las coordenadas de interacción.
            scale = min(win_w / self.VIRTUAL_WIDTH, win_h / self.VIRTUAL_HEIGHT)
            draw_w = max(1, int(self.VIRTUAL_WIDTH * scale))
            draw_h = max(1, int(self.VIRTUAL_HEIGHT * scale))
            offset_x = (win_w - draw_w) // 2
            offset_y = (win_h - draw_h) // 2
            self.screen.fill((10, 10, 14))
            scaled = pygame.transform.smoothscale(self.virtual_surface, (draw_w, draw_h))
            self.screen.blit(scaled, (offset_x, offset_y))

    def _apply_visual_settings(
        self,
        surface: pygame.Surface,
        brightness: float,
        matrix: Optional[np.ndarray],
        intensity: float
    ) -> None:
        """Aplica brillo y filtro de daltonismo acelerado por downscale (fallback CPU)."""
        if brightness != 1.0:
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            if brightness < 1.0:
                overlay.fill((0, 0, 0, int((1.0 - brightness) * 150)))
            else:
                overlay.fill((255, 255, 255, int((brightness - 1.0) * 85)))
            surface.blit(overlay, (0, 0))

        if matrix is not None and intensity > 0.0:
            # Optimización 4x de cálculo matricial: downsample a 960x540, dot product rápido y recomposición
            w, h = surface.get_size()
            sw, sh = w // 2, h // 2
            small = pygame.transform.scale(surface, (sw, sh))
            arr = pygame.surfarray.pixels3d(small)
            flat = arr.reshape(-1, 3).astype(np.float32)
            mix_m = np.eye(3, dtype=np.float32) * (1.0 - intensity) + matrix * intensity
            res_small = np.clip(flat @ mix_m.T, 0, 255).astype(np.uint8).reshape((sw, sh, 3))
            del arr
            pygame.surfarray.blit_array(small, res_small)
            scaled = pygame.transform.scale(small, (w, h))
            surface.blit(scaled, (0, 0))

    def _camera_pointer_allowed(self) -> bool:
        """El lapicero se apaga en menús de navegación, en el mapa y en microjuegos con cámara o gestos propios."""
        current = self.state_machine.current_state
        if getattr(current, "CAMERA_ACTIONS", None):
            return False
        # Desactivar el cursor de cámara totalmente en el mapa y en todos los menús de navegación/configuración
        menu_scene_names = (
            "StoryMapScene",
            "MainMenuScene",
            "ModeSelectScene",
            "CharacterSelectScene",
            "LoadGameScene",
            "FreePlayScene",
            "ArcadeModeScene",
            "MapSettingsState",
            "SlideTransitionState",
        )
        if current.__class__.__name__ in menu_scene_names:
            return False
        return bool(getattr(current, "CAMERA_POINTER", True))

    def _update_camera_cursor_interaction(self, dt: float) -> None:
        """Actualiza el lapicero óptico MediaPipe y simula eventos de MOUSEMOTION y MOUSEBUTTONDOWN por Hover o Gesto."""
        current = self.state_machine.current_state
        if getattr(current, "CAMERA_ACTIONS", None) and hasattr(current, "update_camera_actions"):
            current.update_camera_actions(getattr(self, "camera_input", None))
        if hasattr(current, "update_camera_walk"):
            current.update_camera_walk(getattr(self, "camera_input", None), dt)
        if (
            not getattr(self, "camera_input", None)
            or not self.camera_input.enabled
            or not self.camera_input.is_hand_present()
            or not self._camera_pointer_allowed()
        ):
            self.cam_hover_time = 0.0
            self._cam_dwell_target = None
            self._cam_dwell_fired = False
            return

        hand_x, hand_y = self.camera_input.get_position()
        target_x = max(10.0, min(float(self.VIRTUAL_WIDTH - 10), hand_x * self.VIRTUAL_WIDTH))
        target_y = max(10.0, min(float(self.VIRTUAL_HEIGHT - 10), hand_y * self.VIRTUAL_HEIGHT))

        # LERP suave para amortiguar jitter
        smooth = min(1.0, dt * 22.0)
        self.cam_cursor_x += (target_x - self.cam_cursor_x) * smooth
        self.cam_cursor_y += (target_y - self.cam_cursor_y) * smooth

        virt_pos = (int(self.cam_cursor_x), int(self.cam_cursor_y))

        # Despachar MOUSEMOTION virtual para activar hovers en botones
        motion_evt = pygame.event.Event(pygame.MOUSEMOTION, {"pos": virt_pos, "rel": (0, 0), "buttons": (0, 0, 0)})
        self.state_machine.handle_event(motion_evt)

        resolver = getattr(current, "camera_dwell_target", None)
        target = resolver(virt_pos) if callable(resolver) else None
        if callable(resolver) and target != getattr(self, "_cam_dwell_target", None):
            self.cam_hover_time = 0.0
            self.cam_hover_anchor_x = self.cam_cursor_x
            self.cam_hover_anchor_y = self.cam_cursor_y
            self._cam_dwell_target = target
            self._cam_dwell_fired = False

        # Lógica de Hover por Tiempo (Dwell Time):
        dist_anchor = ((self.cam_cursor_x - self.cam_hover_anchor_x) ** 2 + (self.cam_cursor_y - self.cam_hover_anchor_y) ** 2) ** 0.5
        if dist_anchor < self.cam_hover_tolerance:
            self.cam_hover_time += dt
        else:
            self.cam_hover_anchor_x = self.cam_cursor_x
            self.cam_hover_anchor_y = self.cam_cursor_y
            self.cam_hover_time = 0.0

        if self.cam_click_cooldown > 0.0:
            self.cam_click_cooldown = max(0.0, self.cam_click_cooldown - dt)

        dwell_ok = (target is not None and not getattr(self, "_cam_dwell_fired", False)
                    if callable(resolver) else bool(getattr(current, "CAMERA_DWELL_CLICK", True)))
        if not dwell_ok:
            self.cam_hover_time = 0.0
        hover_triggered = dwell_ok and self.cam_hover_time >= self.cam_hover_duration and self.cam_click_cooldown <= 0.0
        gesture_triggered = self.camera_input.consume_click() and self.cam_click_cooldown <= 0.0

        if hover_triggered or gesture_triggered:
            # Emitir clic virtual en la posición del lapicero
            down_evt = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": virt_pos, "button": 1})
            up_evt = pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": virt_pos, "button": 1})
            self.state_machine.handle_event(down_evt)
            self.state_machine.handle_event(up_evt)

            self.cam_click_cooldown = 0.55  # Evitar doble disparo inmediato
            self.cam_hover_time = 0.0
            if callable(resolver):
                self._cam_dwell_fired = True

    def _render_camera_cursor(self, surface: pygame.Surface) -> None:
        """Dibuja el lapicero y el medidor radial de hover cuando MediaPipe tiene una mano fijada."""
        if (
            not getattr(self, "camera_input", None)
            or not self.camera_input.enabled
            or not self.camera_input.is_hand_present()
            or not self._camera_pointer_allowed()
        ):
            return

        cx, cy = int(self.cam_cursor_x), int(self.cam_cursor_y)

        # Anillo radial de progreso de Hover
        radius = 28
        progress = max(0.0, min(1.0, self.cam_hover_time / max(0.01, self.cam_hover_duration)))
        halo_surf = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
        rc = radius + 5

        # Círculo base translúcido
        pygame.draw.circle(halo_surf, (255, 230, 90, 50), (rc, rc), radius, width=2)

        # Arco de llenado radial
        if progress > 0.04:
            import math
            start_angle = -math.pi / 2.0
            end_angle = start_angle + math.pi * 2.0 * progress
            arc_rect = pygame.Rect(rc - radius, rc - radius, radius * 2, radius * 2)
            pygame.draw.arc(halo_surf, (255, 220, 50, 220), arc_rect, start_angle, end_angle, 4)

        surface.blit(halo_surf, (cx - rc, cy - rc))

        # Dibujar sprite del lapicero (con su punta alineada en cx, cy)
        if self.cam_pencil_surf:
            pw = self.cam_pencil_surf.get_width()
            ph = self.cam_pencil_surf.get_height()
            # La punta de puntero_lapiz.png está en x=55/1312, y=195/1199
            tip_x = int(55 * (pw / 1312.0))
            tip_y = int(195 * (ph / 1199.0))
            surface.blit(self.cam_pencil_surf, (cx - tip_x, cy - tip_y))
        else:
            pygame.draw.circle(surface, (255, 215, 60), (cx, cy), 8)

    def shutdown(self) -> None:
        if hasattr(self, "camera_input") and self.camera_input:
            self.camera_input.stop()
        self.settings.save()
        pygame.quit()
        sys.exit()
