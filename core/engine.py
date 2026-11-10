import os
import sys
import pygame

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
        self.is_fullscreen = not self.is_fullscreen
        self.settings.set("fullscreen", self.is_fullscreen)

        flags = (pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE) if self.enable_gl else (pygame.DOUBLEBUF | pygame.RESIZABLE)
        if self.is_fullscreen:
            flags |= pygame.FULLSCREEN

        self.screen = pygame.display.set_mode((self.width, self.height), flags)

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
        translated = []
        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0:
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE, "unicode": " "}))
            elif event.button in (1, 6, 7):
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "unicode": ""}))
            elif event.button in (2, 3):
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "unicode": "\r"}))
        elif event.type == pygame.JOYHATMOTION:
            hx, hy = event.value
            if hx < 0:
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT, "unicode": ""}))
            elif hx > 0:
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT, "unicode": ""}))
            if hy > 0:
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_UP, "unicode": ""}))
            elif hy < 0:
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN, "unicode": ""}))
        elif event.type == pygame.JOYAXISMOTION:
            deadzone = 0.45
            if event.axis == 0:
                if event.value < -deadzone:
                    translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT, "unicode": ""}))
                elif event.value > deadzone:
                    translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT, "unicode": ""}))
            elif event.axis == 1:
                if event.value < -deadzone:
                    translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_UP, "unicode": ""}))
                elif event.value > deadzone:
                    translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN, "unicode": ""}))
        return translated

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
                    self.width, self.height = event.w, event.h
                    self.settings.set("window_width", self.width)
                    self.settings.set("window_height", self.height)
                    flags = (pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE) if self.enable_gl else (pygame.DOUBLEBUF | pygame.RESIZABLE)
                    if self.is_fullscreen:
                        flags |= pygame.FULLSCREEN
                    self.screen = pygame.display.set_mode((self.width, self.height), flags)
                    continue

                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                    continue

                if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    self._refresh_joysticks()
                    continue

                if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    event = self._map_mouse_event(event)

                self.state_machine.handle_event(event)

                if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
                    for virt_evt in self._translate_joystick_event(event):
                        self.state_machine.handle_event(virt_evt)

            # 2. Lógica
            self.state_machine.update(dt)

            # 3. Renderizado
            self._render_current_frame()
            pygame.display.flip()

        self.shutdown()

    def _render_current_frame(self) -> None:
        current_state = self.state_machine.current_state
        win_w, win_h = pygame.display.get_window_size()
        particles = getattr(current_state, "particles", None)

        if self.enable_gl and self.gl_renderer is not None:
            self.state_machine.render(self.virtual_surface)

            part_bytes = b""
            part_count = 0
            if particles is not None:
                part_bytes = particles.get_instance_bytes()
                part_count = particles.count

            self.gl_renderer.render_frame(
                pygame_surface=self.virtual_surface,
                particle_instance_data=part_bytes,
                particle_count=part_count,
                time_seconds=self.total_time,
                win_w=win_w,
                win_h=win_h
            )
        else:
            self.state_machine.render(self.virtual_surface)
            if particles is not None:
                particles.render_software(self.virtual_surface)

            scaled = pygame.transform.smoothscale(self.virtual_surface, (win_w, win_h))
            self.screen.blit(scaled, (0, 0))

    def shutdown(self) -> None:
        self.settings.save()
        pygame.quit()
        sys.exit()
