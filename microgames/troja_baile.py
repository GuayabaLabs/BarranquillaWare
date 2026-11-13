import math
import random
from typing import Optional, Callable
import pygame

from core.microgame import BaseMicrogame

class TrojaBaileMicrogame(BaseMicrogame):
    """
    Microjuego Folclórico 8: 'Salsa y Cumbia en La Troja' (Calle 74 con Cra 44).
    - Consigna: ¡MANTÉN EL EQUILIBRIO!
    - Mecánica: Baila en la esquina salsera más famosa de Barranquilla con un velón / vaso
      helado en la cabeza. Usa las flechas IZQUIERDA / DERECHA, A / D o el stick para
      mantener el balance en la zona verde sin que caiga al suelo durante 4 segundos.
    """
    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡EQUILIBRIO EN LA TROJA!",
            time_limit=4.0,
            on_complete_callback=on_complete_callback
        )

    def enter(self, params: Optional[dict] = None) -> None:
        # Canción de fondo de la batalla de flores
        self.audio.play_bgm("BatallaDeFloresMusic.mp3")

    def setup_game(self) -> None:
        # Físicas del balance
        self.angle: float = 0.0          # Ángulo actual en grados (-55..+55)
        self.angular_vel: float = 0.0    # Velocidad angular
        self.max_safe_angle: float = 38.0
        self.unbalance_force: float = 85.0
        self.push_power: float = 145.0

        # Personaje y baile
        self.dancer_center = (960, 680)
        self.dance_bob = 0.0

        # Sprite del personaje
        self.player_sprite = None
        try:
            sprite_name = f"{self.character_id}_seleccion_personaje.png"
            raw_s = self.assets.load_surface(sprite_name, has_alpha=True)
            mask = pygame.mask.from_surface(raw_s)
            rects = mask.get_bounding_rects()
            cropped = raw_s.subsurface(rects[0]) if rects else raw_s
            th = 280
            tw = int(cropped.get_width() * (th / float(cropped.get_height())))
            self.player_sprite = pygame.transform.smoothscale(cropped, (tw, th))
        except Exception:
            pass

        # Notas musicales flotantes en La Troja
        self.notes: list = []
        for _ in range(8):
            self.notes.append({
                "x": random.uniform(300, 1620),
                "y": random.uniform(250, 750),
                "vy": random.uniform(-60, -25),
                "char": random.choice(["♪", "♫", "♩", "♬"]),
                "size": random.randint(28, 44),
                "color": random.choice([(255, 220, 50), (255, 75, 110), (50, 210, 255), (100, 255, 130)])
            })

        self.font_music = pygame.font.SysFont("Arial, sans-serif", 36, bold=True)
        self.font_troja = pygame.font.SysFont("Arial Black, Impact, sans-serif", 32)
        self.font_angle = pygame.font.SysFont("Arial Black, Impact, sans-serif", 24)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if self.phase != self.PHASE_PLAY or self.is_finished:
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.angular_vel -= self.push_power * 0.4
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.angular_vel += self.push_power * 0.4

    def update_game(self, dt: float) -> None:
        # 1. Entrada continua por teclado o mouse
        keys = pygame.key.get_pressed()
        correction = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            correction -= self.push_power * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            correction += self.push_power * dt

        # Entrada por posición relativa del ratón
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:
            mx, _ = pygame.mouse.get_pos()
            if mx < self.dancer_center[0] - 40:
                correction -= self.push_power * dt
            elif mx > self.dancer_center[0] + 40:
                correction += self.push_power * dt

        # 2. Desestabilización caótica por la música de salsa brava
        rhythm_wobble = math.sin(self.time_left * 8.5) * self.unbalance_force * dt
        # Desequilibrio físico (gravedad amplifica la inclinación)
        gravity_pull = math.sin(math.radians(self.angle)) * 140.0 * dt

        self.angular_vel += rhythm_wobble + gravity_pull + correction
        self.angular_vel *= (1.0 - dt * 2.2) # Fricción
        self.angle += self.angular_vel * dt * 45.0

        # Rebote rítmico del cuerpo bailando
        self.dance_bob = math.sin(self.time_left * 12.0) * 12.0

        # 3. Comprobar caída
        if abs(self.angle) > self.max_safe_angle:
            self.finish_game(False)
            return

        # Si el tiempo expira dentro de los límites: Victoria
        if self.time_left <= 0.05 and not self.is_finished:
            self.finish_game(True)
            return

        # 4. Actualizar notas musicales
        for n in self.notes:
            n["y"] += n["vy"] * dt
            if n["y"] < 120:
                n["y"] = random.uniform(700, 800)
                n["x"] = random.uniform(300, 1620)

    def render_game(self, surface: pygame.Surface) -> None:
        # Fondo: Esquina nocturna de La Troja con luces de neón y ambiente salsero
        surface.fill((20, 16, 30))

        # Degradado de luces de fiesta rojas y amarillas
        glow_bar = pygame.Surface((self.screen_w, 380), pygame.SRCALPHA)
        pygame.draw.rect(glow_bar, (220, 50, 40, 45), (0, 0, self.screen_w, 380))
        surface.blit(glow_bar, (0, 320))

        # Fachada y letrero emblemático de La Troja
        let_rect = pygame.Rect(self.screen_w // 2 - 380, 50, 760, 80)
        pygame.draw.rect(surface, (180, 25, 30), let_rect, border_radius=16)
        pygame.draw.rect(surface, (255, 215, 40), let_rect, width=4, border_radius=16)
        txt_troja = self.font_troja.render("LA TROJA · PATRIMONIO CULTURAL Y SALSERO", True, (255, 240, 160))
        surface.blit(txt_troja, txt_troja.get_rect(center=let_rect.center))

        # Notas musicales flotando en el aire
        for n in self.notes:
            txt_n = self.font_music.render(n["char"], True, n["color"])
            surface.blit(txt_n, (int(n["x"]), int(n["y"])))

        dx, dy = self.dancer_center
        dy_bob = int(dy + self.dance_bob)

        # Sombra en el suelo
        pygame.draw.ellipse(surface, (10, 8, 16, 180), (dx - 120, dy + 115, 240, 45))

        # 1. Dibujar Personaje Bailando
        if self.player_sprite:
            sw, sh = self.player_sprite.get_size()
            surface.blit(self.player_sprite, (dx - sw // 2, dy_bob - sh // 2))
            head_top_y = dy_bob - sh // 2 + 10
        else:
            pygame.draw.rect(surface, (240, 120, 50), (dx - 45, dy_bob - 120, 90, 180), border_radius=14)
            pygame.draw.circle(surface, (245, 190, 150), (dx, dy_bob - 150), 40)
            head_top_y = dy_bob - 190

        # 2. Vaso Helado / Velón de Cumbia en la cabeza con rotación física
        glass_w, glass_h = 44, 75
        glass_surf = pygame.Surface((glass_w + 40, glass_h + 40), pygame.SRCALPHA)
        gx, gy = (glass_w + 40) // 2, (glass_h + 40) // 2

        # Vaso de cerveza helada espumosa
        pygame.draw.polygon(glass_surf, (245, 180, 30), [
            (gx - 16, gy - 26), (gx + 16, gy - 26),
            (gx + 12, gy + 26), (gx - 12, gy + 26)
        ])
        # Espuma blanca en el borde
        pygame.draw.ellipse(glass_surf, (255, 255, 255), (gx - 18, gy - 32, 36, 14))
        # Borde de cristal
        pygame.draw.polygon(glass_surf, (220, 240, 255), [
            (gx - 16, gy - 26), (gx + 16, gy - 26),
            (gx + 12, gy + 26), (gx - 12, gy + 26)
        ], width=2)

        # Rotar el vaso según el ángulo de inclinación
        rot_glass = pygame.transform.rotate(glass_surf, -self.angle)
        rect_g = rot_glass.get_rect(center=(dx, head_top_y - 30))
        surface.blit(rot_glass, rect_g)

        # 3. Medidor de Inclinación Superior (Arco de Equilibrio)
        meter_x, meter_y = self.screen_w // 2, 210
        meter_w, meter_h = 480, 28
        meter_rect = pygame.Rect(meter_x - meter_w // 2, meter_y, meter_w, meter_h)

        # Riel del medidor
        pygame.draw.rect(surface, (30, 25, 40), meter_rect, border_radius=14)
        pygame.draw.rect(surface, (80, 70, 95), meter_rect, width=2, border_radius=14)

        # Zona segura verde central
        safe_ratio = self.max_safe_angle / 55.0
        safe_w = int(meter_w * safe_ratio * 0.7)
        safe_rect = pygame.Rect(meter_x - safe_w // 2, meter_y + 3, safe_w, meter_h - 6)
        pygame.draw.rect(surface, (45, 210, 85), safe_rect, border_radius=10)

        # Aguja indicadora
        t_pos = max(-1.0, min(1.0, self.angle / self.max_safe_angle))
        needle_x = int(meter_x + t_pos * (meter_w // 2 - 20))
        pygame.draw.circle(surface, (255, 235, 60), (needle_x, meter_y + meter_h // 2), 16)
        pygame.draw.circle(surface, (20, 20, 25), (needle_x, meter_y + meter_h // 2), 6)

        # Texto de ayuda
        txt_help = self.font_angle.render("◄ EQUILIBRA CON FLECHAS [← / →] O RATÓN ►", True, (240, 230, 210))
        surface.blit(txt_help, txt_help.get_rect(center=(meter_x, meter_y + 55)))
