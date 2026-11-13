import math
import random
from typing import Optional, Callable
import pygame

from core.microgame import BaseMicrogame

class AeropuertoAterrizajeMicrogame(BaseMicrogame):
    """
    Microjuego 6: '¡Aterriza en la Pista!' (Aeropuerto Internacional Ernesto Cortissoz).
    - Consigna: ¡ATERRIZA EN LA PISTA!
    - Mecánica: Un avión comercial desciende hacia la pista de Barranquilla con viento cruzado.
      Mueve el avión horizontalmente (Flechas, A/D o Mouse) para mantenerlo dentro de la franja
      central de la pista cuando el tren de aterrizaje toque tierra al final de los 4 segundos.
    - Game Feel: Turbulencia caribeña, humo de neumáticos, chirrido de freno, screenshake.
    """
    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡ATERRIZA EN LA PISTA!",
            time_limit=4.0,
            on_complete_callback=on_complete_callback
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("contraRelojMusic.mp3")

    def setup_game(self) -> None:
        # Posición del avión
        self.plane_x = float(self.screen_w // 2 + random.randint(-220, 220))
        self.plane_y = 220.0
        self.plane_target_y = 780.0  # Nivel de la pista donde toca tierra

        # Ráfagas de viento cruzado lateral
        self.wind_force = random.choice([-1.0, 1.0]) * random.uniform(160.0, 240.0)

        # Dimensiones de la pista en perspectiva (suelo)
        self.runway_cx = self.screen_w // 2
        self.runway_top_w = 120
        self.runway_bot_w = 480
        self.runway_top_y = 420
        self.runway_bot_y = 920

        # Estado
        self.landed: bool = False
        self.touchdown_success: bool = False
        self.tire_smoke = []

        self._load_character()

    def _load_character(self) -> None:
        sprite_filename = f"{self.character_id}_seleccion_personaje.png"
        try:
            raw = self.assets.load_surface(sprite_filename, has_alpha=True)
            mask = pygame.mask.from_surface(raw)
            rects = mask.get_bounding_rects()
            cropped = raw.subsurface(rects[0]) if rects else raw
            target_h = 220
            target_w = int(cropped.get_width() * (target_h / float(cropped.get_height())))
            self.character_sprite = pygame.transform.smoothscale(cropped, (target_w, target_h))
        except Exception:
            self.character_sprite = pygame.Surface((110, 220), pygame.SRCALPHA)
            pygame.draw.rect(self.character_sprite, (220, 160, 60), (0, 0, 110, 220), border_radius=18)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if self.landed:
            return

        if event.type == pygame.MOUSEMOTION:
            # Control por mouse directo
            self.plane_x = float(event.pos[0])

    def update_game(self, dt: float) -> None:
        if not self.landed:
            # Control por teclado suave
            keys = pygame.key.get_pressed()
            speed = 880.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.plane_x -= speed * dt
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.plane_x += speed * dt

            # Deriva por viento caribeño
            self.plane_x += self.wind_force * dt

            # Descenso progresivo hacia la pista
            descent_speed = (self.plane_target_y - 220.0) / (self.time_limit * 0.85)
            self.plane_y += descent_speed * dt

            # Verificar aterrizaje cuando llega a la pista
            if self.plane_y >= self.plane_target_y:
                self._evaluate_landing()

        # Actualizar partículas de humo de llantas
        for sm in self.tire_smoke:
            sm["x"] += sm["vx"] * dt
            sm["y"] += sm["vy"] * dt
            sm["size"] += dt * 35.0
            sm["life"] -= dt * 1.8

    def _evaluate_landing(self) -> None:
        self.landed = True
        self.plane_y = self.plane_target_y

        # Ancho permitido en la base de la pista (+/- 140px del centro)
        dist_from_center = abs(self.plane_x - self.runway_cx)

        if dist_from_center <= 150:
            self.touchdown_success = True
            self.trigger_screenshake(16.0, 0.25)
            self._spawn_tire_smoke()
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()
            self.evaluate(True, delay=1.1, message="¡ATERRIZAJE PERFECTO!")
        else:
            self.touchdown_success = False
            self.trigger_screenshake(10.0, 0.2)
            self.evaluate(False, delay=1.0, message="¡FUERA DE PISTA!")

    def _spawn_tire_smoke(self) -> None:
        for offset_x in [-55, 55]:
            for _ in range(16):
                angle = random.uniform(math.pi * 0.8, math.pi * 1.2) if offset_x < 0 else random.uniform(-0.2, 0.2)
                spd = random.uniform(60, 210)
                self.tire_smoke.append({
                    "x": self.plane_x + offset_x,
                    "y": self.plane_y + 40,
                    "vx": math.cos(angle) * spd,
                    "vy": -random.uniform(40, 110),
                    "size": random.uniform(10.0, 18.0),
                    "life": 1.0
                })

    def draw_game(self, screen: pygame.Surface) -> None:
        # 1. Cielo crepuscular
        for y in range(self.screen_h):
            t = y / float(self.screen_h)
            r = int(140 * (1 - t) + 40 * t)
            g = int(185 * (1 - t) + 80 * t)
            b = int(245 * (1 - t) + 120 * t)
            screen.fill((r, g, b), (0, y, self.screen_w, 1))

        # 2. Terreno de aproximación a Soledad / Barranquilla
        pygame.draw.rect(screen, (55, 95, 60), (0, self.runway_top_y - 20, self.screen_w, self.screen_h))

        # 3. Pista de asfalto en perspectiva
        pts_runway = [
            (self.runway_cx - self.runway_top_w // 2, self.runway_top_y),
            (self.runway_cx + self.runway_top_w // 2, self.runway_top_y),
            (self.runway_cx + self.runway_bot_w // 2, self.runway_bot_y),
            (self.runway_cx - self.runway_bot_w // 2, self.runway_bot_y)
        ]
        pygame.draw.polygon(screen, (40, 42, 48), pts_runway)
        pygame.draw.polygon(screen, (240, 240, 240), pts_runway, width=4)

        # Luces de borde de pista (Verdes en cabecera, rojas en final)
        for i in range(12):
            t = i / 11.0
            lx1 = int((self.runway_cx - self.runway_top_w // 2) * (1 - t) + (self.runway_cx - self.runway_bot_w // 2) * t)
            rx1 = int((self.runway_cx + self.runway_top_w // 2) * (1 - t) + (self.runway_cx + self.runway_bot_w // 2) * t)
            ly1 = int(self.runway_top_y * (1 - t) + self.runway_bot_y * t)
            # Bombillas iluminadas
            pygame.draw.circle(screen, (80, 255, 120), (lx1, ly1), 5)
            pygame.draw.circle(screen, (80, 255, 120), (rx1, ly1), 5)

        # Línea central punteada de la pista
        for i in range(7):
            t1 = i / 7.0
            t2 = (i + 0.5) / 7.0
            y1 = int(self.runway_top_y * (1 - t1) + self.runway_bot_y * t1)
            y2 = int(self.runway_top_y * (1 - t2) + self.runway_bot_y * t2)
            lw = int(4 * (1 - t1) + 12 * t1)
            pygame.draw.line(screen, (255, 230, 80), (self.runway_cx, y1), (self.runway_cx, y2), lw)

        # 4. Humo de neumáticos si hubo toque de pista
        for sm in self.tire_smoke:
            if sm["life"] > 0.0:
                alpha = int(180 * max(0.0, sm["life"]))
                surf_sm = pygame.Surface((int(sm["size"] * 2), int(sm["size"] * 2)), pygame.SRCALPHA)
                pygame.draw.circle(surf_sm, (220, 225, 235, alpha), (int(sm["size"]), int(sm["size"])), int(sm["size"]))
                screen.blit(surf_sm, (int(sm["x"] - sm["size"]), int(sm["y"] - sm["size"])))

        # 5. Dibujar avión comercial visto desde atrás en aproximación
        self._draw_airplane(screen)

        # 6. Personaje piloto / torre de control en la esquina inferior izquierda
        screen.blit(self.character_sprite, (60, self.screen_h - 265))

        # Indicador de viento cruzado
        wind_dir_str = "VIENTO >>" if self.wind_force > 0 else "<< VIENTO"
        font_wind = pygame.font.SysFont("Arial Black, Impact", 18)
        txt_w = font_wind.render(f"TURBULENCIA: {wind_dir_str}", True, (255, 220, 60))
        screen.blit(txt_w, (self.screen_w // 2 - txt_w.get_width() // 2, 90))

    def _draw_airplane(self, screen: pygame.Surface) -> None:
        px, py = int(self.plane_x), int(self.plane_y)
        scale = 0.65 + 0.35 * (py / self.plane_target_y)

        # Sombra proyectada en el suelo
        shadow_y = self.runway_bot_y - 20
        shadow_w = int(180 * scale)
        shadow_h = int(24 * scale)
        s_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(s_surf, (20, 25, 30, int(120 * scale)), (0, 0, shadow_w, shadow_h))
        screen.blit(s_surf, (px - shadow_w // 2, shadow_y))

        # Fuselaje del avión
        fuse_w = int(48 * scale)
        fuse_h = int(130 * scale)
        fuse_rect = pygame.Rect(px - fuse_w // 2, py - fuse_h // 2, fuse_w, fuse_h)
        pygame.draw.ellipse(screen, (245, 250, 255), fuse_rect)
        pygame.draw.ellipse(screen, (20, 30, 45), fuse_rect, width=3)

        # Alas anchas
        wing_span = int(220 * scale)
        wing_y = py + int(10 * scale)
        pts_wings = [
            (px - wing_span // 2, wing_y),
            (px, py - int(15 * scale)),
            (px + wing_span // 2, wing_y),
            (px + wing_span // 2 - int(25 * scale), wing_y + int(24 * scale)),
            (px, py + int(25 * scale)),
            (px - wing_span // 2 + int(25 * scale), wing_y + int(24 * scale))
        ]
        pygame.draw.polygon(screen, (220, 230, 245), pts_wings)
        pygame.draw.polygon(screen, (20, 30, 45), pts_wings, width=3)

        # Turbinas con fuego azul/amarillo
        for tx in [px - int(60 * scale), px + int(60 * scale)]:
            turb_w = int(22 * scale)
            turb_h = int(32 * scale)
            pygame.draw.rect(screen, (70, 80, 95), (tx - turb_w // 2, wing_y - 4, turb_w, turb_h), border_radius=5)
            # Fuego de empuje
            pygame.draw.ellipse(screen, (255, 200, 60), (tx - turb_w // 4, wing_y + turb_h - 6, turb_w // 2, int(16 * scale)))

        # Estabilizador vertical (cola roja)
        pts_tail = [
            (px - int(8 * scale), py + int(20 * scale)),
            (px, py - int(45 * scale)),
            (px + int(8 * scale), py + int(20 * scale))
        ]
        pygame.draw.polygon(screen, (235, 45, 55), pts_tail)
        pygame.draw.polygon(screen, (20, 30, 45), pts_tail, width=2)
