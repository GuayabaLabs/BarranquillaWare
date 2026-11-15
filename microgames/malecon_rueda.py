import math
import random
from typing import Optional, Callable
import pygame

from core.microgame import BaseMicrogame

class MaleconRuedaMicrogame(BaseMicrogame):
    """
    Microjuego 5: '¡Frena en la Cima!' (Gran Malecón del Río - Rueda Luna del Río).
    - Consigna: ¡FRENA EN LA CIMA!
    - Mecánica: La gran rueda panorámica 'Luna del Río' gira a orillas del Magdalena.
      En la cúspide (las 12 en punto) hay un arco de parada panorámica verde.
      Presiona ESPACIO o haz CLICK cuando la cabina VIP dorada pase por el arco superior.
    - Game Feel: Clac mecánico de freno, chispas de frenado, fuegos artificiales sobre el río.
    """
    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡FRENA EN LA CIMA!",
            time_limit=4.0,
            on_complete_callback=on_complete_callback
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("contraRelojMusic.mp3")

    def setup_game(self) -> None:
        self.wheel_cx = self.screen_w // 2
        self.wheel_cy = 470
        self.wheel_radius = 230

        # Ángulo de la rueda (radianes)
        self.wheel_angle = random.uniform(math.pi * 0.4, math.pi * 0.9)
        self.rot_speed = random.uniform(3.4, 4.4)

        # Cabinas
        self.num_cabins = 8
        self.target_cabin_idx = 0  # Cabina dorada especial

        # Estado del juego
        self.stopped: bool = False
        self.won_game: bool = False
        self.fireworks = []

        # Fondo del Río Magdalena
        self.river_wave_timer = 0.0
        self._load_character()

    def _load_character(self) -> None:
        sprite_filename = f"{self.character_id}_seleccion_personaje.png"
        try:
            raw = self.assets.load_surface(sprite_filename, has_alpha=True)
            mask = pygame.mask.from_surface(raw)
            rects = mask.get_bounding_rects()
            cropped = raw.subsurface(rects[0]) if rects else raw
            target_h = 230
            target_w = int(cropped.get_width() * (target_h / float(cropped.get_height())))
            self.character_sprite = pygame.transform.smoothscale(cropped, (target_w, target_h))
        except Exception:
            self.character_sprite = pygame.Surface((120, 230), pygame.SRCALPHA)
            pygame.draw.rect(self.character_sprite, (220, 160, 60), (0, 0, 120, 230), border_radius=18)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if self.stopped:
            return

        if (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE) or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self._brake_wheel()

    def _brake_wheel(self) -> None:
        self.stopped = True
        # La cúspide de la rueda (12 en punto) corresponde a un ángulo de -pi/2 (270 grados o 3*pi/2)
        # Calculamos el ángulo actual de la cabina dorada
        vip_angle = (self.wheel_angle + self.target_cabin_idx * (2 * math.pi / self.num_cabins)) % (2 * math.pi)
        target_angle = (3 * math.pi / 2) % (2 * math.pi)

        # Diferencia angular absoluta
        diff = abs(vip_angle - target_angle)
        diff = min(diff, 2 * math.pi - diff)

        # Margen de éxito: +/- 0.36 radianes (~20 grados)
        if diff <= 0.38:
            self.won_game = True
            self.trigger_screenshake(14.0, 0.22)
            self._spawn_fireworks()
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()
            self.evaluate(True, delay=1.1, message="¡VISTA ESPECTACULAR!")
        else:
            self.won_game = False
            self.trigger_screenshake(7.0, 0.15)
            if hasattr(self.audio, "play_miss"):
                self.audio.play_miss()
            self.evaluate(False, delay=1.0, message="¡A DESTIEMPO!")

    def _spawn_fireworks(self) -> None:
        for fx in [self.wheel_cx - 320, self.wheel_cx + 320]:
            for _ in range(20):
                angle = random.uniform(0, math.pi * 2)
                spd = random.uniform(90, 280)
                self.fireworks.append({
                    "x": float(fx),
                    "y": 280.0,
                    "vx": math.cos(angle) * spd,
                    "vy": math.sin(angle) * spd,
                    "color": random.choice([(255, 220, 80), (255, 90, 120), (90, 215, 255), (140, 255, 120)]),
                    "size": random.uniform(4.0, 7.5),
                    "life": 1.0
                })

    def update_game(self, dt: float) -> None:
        if not self.stopped:
            self.wheel_angle += self.rot_speed * dt

        self.river_wave_timer += dt

        for fw in self.fireworks:
            fw["x"] += fw["vx"] * dt
            fw["y"] += fw["vy"] * dt
            fw["life"] -= dt * 1.4

    def draw_game(self, screen: pygame.Surface) -> None:
        # 1. Cielo crepuscular del Río Magdalena
        for y in range(self.screen_h):
            t = y / float(self.screen_h)
            r = int(245 * (1 - t) + 35 * t)
            g = int(140 * (1 - t) + 55 * t)
            b = int(75 * (1 - t) + 115 * t)
            screen.fill((r, g, b), (0, y, self.screen_w, 1))

        # 2. Río Magdalena con reflejo dorado
        river_y = 660
        pygame.draw.rect(screen, (35, 75, 125), (0, river_y, self.screen_w, self.screen_h - river_y))
        for wave_i in range(12):
            wy = river_y + wave_i * 32
            wx_off = math.sin(self.river_wave_timer * 2.0 + wave_i) * 25.0
            pygame.draw.line(screen, (55, 120, 185), (0, wy), (self.screen_w, wy), 2)
            # Brillo dorado del atardecer
            pygame.draw.line(screen, (245, 195, 90), (self.wheel_cx - 180 + wx_off, wy), (self.wheel_cx + 180 + wx_off, wy), 3)

        # 3. Muelle y malecón de concreto en primer plano
        pygame.draw.rect(screen, (70, 75, 85), (0, 840, self.screen_w, 240))
        pygame.draw.line(screen, (240, 195, 60), (0, 842), (self.screen_w, 842), 4)

        # Barandas del Gran Malecón
        for rx in range(0, self.screen_w, 48):
            pygame.draw.line(screen, (215, 220, 230), (rx, 785), (rx, 840), 3)
        pygame.draw.line(screen, (230, 235, 245), (0, 785), (self.screen_w, 785), 5)

        # 4. Dibujar la Rueda Panorámica
        self._draw_ferris_wheel(screen)

        # 5. Fuegos artificiales
        for fw in self.fireworks:
            if fw["life"] > 0.0:
                alpha = int(255 * max(0.0, fw["life"]))
                s_fw = pygame.Surface((16, 16), pygame.SRCALPHA)
                pygame.draw.circle(s_fw, (*fw["color"], alpha), (8, 8), int(fw["size"]))
                screen.blit(s_fw, (int(fw["x"]) - 8, int(fw["y"]) - 8))

        # 6. Personaje en la baranda
        screen.blit(self.character_sprite, (140, self.screen_h - 275))

    def _draw_ferris_wheel(self, screen: pygame.Surface) -> None:
        cx, cy, r = self.wheel_cx, self.wheel_cy, self.wheel_radius

        # Torre / Soportes en A de la rueda
        pygame.draw.line(screen, (40, 45, 60), (cx - 120, 840), (cx, cy), 12)
        pygame.draw.line(screen, (40, 45, 60), (cx + 120, 840), (cx, cy), 12)
        pygame.draw.line(screen, (255, 215, 60), (cx - 120, 840), (cx, cy), 4)
        pygame.draw.line(screen, (255, 215, 60), (cx + 120, 840), (cx, cy), 4)

        # Arco superior de parada panorámica (Zona objetivo verde)
        target_arc_surf = pygame.Surface((180, 70), pygame.SRCALPHA)
        pygame.draw.arc(target_arc_surf, (50, 240, 110, 230), (10, 10, 160, 50), 0.3, math.pi - 0.3, 10)
        font_top = pygame.font.SysFont("Arial Black, Impact", 16)
        txt_top = font_top.render("¡CIMA!", True, (50, 240, 110))
        target_arc_surf.blit(txt_top, txt_top.get_rect(center=(90, 45)))
        screen.blit(target_arc_surf, target_arc_surf.get_rect(center=(cx, cy - r - 15)))

        # Aros circulares de la rueda
        pygame.draw.circle(screen, (245, 235, 210), (cx, cy), r, width=6)
        pygame.draw.circle(screen, (255, 210, 70), (cx, cy), r - 35, width=3)
        pygame.draw.circle(screen, (40, 50, 70), (cx, cy), 28)
        pygame.draw.circle(screen, (255, 225, 100), (cx, cy), 12)

        # Rayos y Cabinas
        for i in range(self.num_cabins):
            ang = self.wheel_angle + i * (2 * math.pi / self.num_cabins)
            kx = cx + math.cos(ang) * r
            ky = cy + math.sin(ang) * r

            # Rayo metálico
            pygame.draw.line(screen, (220, 215, 195), (cx, cy), (int(kx), int(ky)), 2)

            # Cabina
            is_vip = (i == self.target_cabin_idx)
            cab_w, cab_h = (44, 38) if is_vip else (34, 30)
            cab_col = (255, 215, 60) if is_vip else (240, 80, 80)
            if is_vip and not self.stopped:
                # Destello de cabina VIP
                pulse = math.sin(self.timer * 10.0) * 0.5 + 0.5
                cab_col = (255, int(190 + 65 * pulse), int(40 + 80 * pulse))

            # Dibujar cabina siempre nivelada verticalmente
            cab_rect = pygame.Rect(int(kx) - cab_w // 2, int(ky) - 6, cab_w, cab_h)
            pygame.draw.rect(screen, cab_col, cab_rect, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255), cab_rect, width=2, border_radius=8)
            # Ventanilla de cristal
            win_rect = pygame.Rect(cab_rect.x + 4, cab_rect.y + 4, cab_w - 8, cab_h // 2)
            pygame.draw.rect(screen, (160, 230, 255), win_rect, border_radius=4)
