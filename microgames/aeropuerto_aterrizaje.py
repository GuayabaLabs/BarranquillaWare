import math
import random
from typing import Optional, Callable, List, Dict, Any
import pygame

from core.microgame import BaseMicrogame

INK_DARK = (78, 51, 35)


class AeropuertoAterrizajeMicrogame(BaseMicrogame):
    """
    Microjuego 6: '¡Aterriza en Modo Avión!' (Aeropuerto Internacional Ernesto Cortissoz).
    - Temática social: Modo Avión al aterrizar — no te distraigas con notificaciones en momentos críticos.
    - Mecánica: Alinea el avión comercial con viento cruzado (Flechas, A/D o Mouse) dentro de la pista.
    """

    NOTIF_TEXTS = (
        "99+ mensajes sin leer",
        "¡Nuevo trend viral ahora!",
        "@chisme_bq te etiquetó",
        "¡Mira este video ya!",
    )

    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡ATERRIZA EN MODO AVIÓN!",
            time_limit=4.0,
            on_complete_callback=on_complete_callback,
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("contraRelojMusic.mp3")

    def setup_game(self) -> None:
        self.plane_x = float(self.screen_w // 2 + random.randint(-220, 220))
        self.plane_y = 220.0
        self.plane_target_y = 780.0
        self.wind_force = random.choice([-1.0, 1.0]) * random.uniform(160.0, 240.0)

        self.runway_cx = self.screen_w // 2
        self.runway_top_w = 120
        self.runway_bot_w = 480
        self.runway_top_y = 420
        self.runway_bot_y = 920

        self.landed: bool = False
        self.touchdown_success: bool = False
        self.tire_smoke: List[Dict[str, Any]] = []
        self.elapsed_anim: float = 0.0

        # Notificaciones distractoras flotando a los lados (fenómeno redes sociales)
        self.distraction_cards = [
            {
                "x": 150.0 if i % 2 == 0 else float(self.screen_w - 490),
                "y": 240.0 + (i // 2) * 165.0,
                "phase": random.uniform(0, math.tau),
                "text": txt,
            }
            for i, txt in enumerate(self.NOTIF_TEXTS)
        ]

        self.font_ui = self.assets.cargarFuenteCuento(22)
        self.font_small = self.assets.cargarFuenteCuento(18)

        self._load_character()
        self.backdrop_surf = self._build_backdrop_surface()

    def _build_backdrop_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.screen_w, self.screen_h))
        # Cielo acuarela cálido de atardecer en Soledad / Barranquilla
        band_h = 8
        for y in range(0, self.screen_h, band_h):
            t = y / float(self.screen_h)
            r = int(246 * (1 - t) + 128 * t)
            g = int(198 * (1 - t) + 168 * t)
            b = int(162 * (1 - t) + 210 * t)
            surf.fill((r, g, b), (0, y, self.screen_w, band_h))

        # Sol cálido acuarela en el horizonte
        sun = pygame.Surface((320, 320), pygame.SRCALPHA)
        pygame.draw.circle(sun, (255, 226, 138, 120), (160, 160), 140)
        pygame.draw.circle(sun, (255, 240, 185, 190), (160, 160), 86)
        surf.blit(sun, (self.screen_w // 2 - 160, 210))

        # Nubes suaves acuarela
        for cx, cy, rw, rh in [(290, 190, 240, 72), (1560, 210, 270, 78), (640, 145, 200, 60)]:
            cloud = pygame.Surface((rw, rh), pygame.SRCALPHA)
            pygame.draw.ellipse(cloud, (255, 249, 238, 195), (0, 10, rw, rh - 12))
            pygame.draw.ellipse(cloud, (255, 252, 246, 210), (35, 0, rw - 70, rh - 18))
            surf.blit(cloud, (cx - rw // 2, cy - rh // 2))

        # Terreno verde acuarela de aproximación
        pygame.draw.rect(surf, (108, 152, 98), (0, self.runway_top_y - 20, self.screen_w, self.screen_h))
        pygame.draw.rect(surf, (92, 136, 86), (0, self.runway_top_y + 120, self.screen_w, self.screen_h))

        # Silueta de Torre de Control del Aeropuerto Cortissoz
        tx = self.screen_w // 2 + 370
        pygame.draw.rect(surf, (238, 226, 204), (tx, 270, 38, 140), border_radius=4)
        pygame.draw.rect(surf, INK_DARK, (tx, 270, 38, 140), width=2, border_radius=4)
        pygame.draw.polygon(surf, (218, 92, 78), [(tx - 24, 270), (tx + 62, 270), (tx + 50, 232), (tx - 12, 232)])
        pygame.draw.rect(surf, (132, 204, 232), (tx - 10, 240, 58, 20), border_radius=3)

        # Pista en perspectiva
        pts_runway = [
            (self.runway_cx - self.runway_top_w // 2, self.runway_top_y),
            (self.runway_cx + self.runway_top_w // 2, self.runway_top_y),
            (self.runway_cx + self.runway_bot_w // 2, self.runway_bot_y),
            (self.runway_cx - self.runway_bot_w // 2, self.runway_bot_y),
        ]
        pygame.draw.polygon(surf, (68, 66, 72), pts_runway)
        pygame.draw.polygon(surf, (248, 240, 224), pts_runway, width=5)

        for i in range(12):
            t = i / 11.0
            lx1 = int((self.runway_cx - self.runway_top_w // 2) * (1 - t) + (self.runway_cx - self.runway_bot_w // 2) * t)
            rx1 = int((self.runway_cx + self.runway_top_w // 2) * (1 - t) + (self.runway_cx + self.runway_bot_w // 2) * t)
            ly1 = int(self.runway_top_y * (1 - t) + self.runway_bot_y * t)
            pygame.draw.circle(surf, (118, 238, 152), (lx1, ly1), 6)
            pygame.draw.circle(surf, (118, 238, 152), (rx1, ly1), 6)

        for i in range(7):
            t1 = i / 7.0
            t2 = (i + 0.5) / 7.0
            y1 = int(self.runway_top_y * (1 - t1) + self.runway_bot_y * t1)
            y2 = int(self.runway_top_y * (1 - t2) + self.runway_bot_y * t2)
            lw = int(4 * (1 - t1) + 12 * t1)
            pygame.draw.line(surf, (252, 220, 102), (self.runway_cx, y1), (self.runway_cx, y2), lw)

        return surf

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
            self.plane_x = float(event.pos[0])

    def update_game(self, dt: float) -> None:
        self.elapsed_anim += dt
        if not self.landed:
            keys = pygame.key.get_pressed()
            speed = 880.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.plane_x -= speed * dt
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.plane_x += speed * dt

            self.plane_x += self.wind_force * dt
            descent_speed = (self.plane_target_y - 220.0) / (self.time_limit * 0.85)
            self.plane_y += descent_speed * dt

            if self.plane_y >= self.plane_target_y:
                self._evaluate_landing()

        for sm in self.tire_smoke:
            sm["x"] += sm["vx"] * dt
            sm["y"] += sm["vy"] * dt
            sm["size"] += dt * 35.0
            sm["life"] -= dt * 1.8

    def _evaluate_landing(self) -> None:
        self.landed = True
        self.plane_y = self.plane_target_y
        dist_from_center = abs(self.plane_x - self.runway_cx)

        if dist_from_center <= 150:
            self.touchdown_success = True
            self.outro_message = "¡MODO AVIÓN PERFECTO!"
            self.trigger_screenshake(16.0, 0.25)
            self._spawn_tire_smoke()
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()
            self.evaluate(True, delay=1.1, message="¡MODO AVIÓN PERFECTO!")
        else:
            self.touchdown_success = False
            self.outro_message = "¡TE DISTRAJISTE!"
            self.trigger_screenshake(10.0, 0.2)
            if hasattr(self.audio, "play_miss"):
                self.audio.play_miss()
            self.evaluate(False, delay=1.0, message="¡TE DISTRAJISTE!")

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
                    "life": 1.0,
                })

    def draw_game(self, screen: pygame.Surface) -> None:
        screen.blit(self.backdrop_surf, (0, 0))

        # Notificaciones distractoras flotantes (el jugador debe ignorarlas y aterrizar)
        for card in self.distraction_cards:
            bob = math.sin(self.elapsed_anim * 4.2 + card["phase"]) * 8.0
            c_rect = pygame.Rect(int(card["x"]), int(card["y"] + bob), 330, 62)
            card_surf = pygame.Surface(c_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(card_surf, (253, 245, 232, 226), (0, 0, c_rect.width, c_rect.height), border_radius=16)
            pygame.draw.rect(card_surf, (224, 92, 86, 220), (0, 0, c_rect.width, c_rect.height), width=3, border_radius=16)
            pygame.draw.circle(card_surf, (226, 68, 72), (26, 31), 11)
            excl = self.font_small.render("!", True, (255, 250, 240))
            card_surf.blit(excl, excl.get_rect(center=(26, 30)))
            txt = self.font_small.render(card["text"], True, INK_DARK)
            card_surf.blit(txt, (48, 19))
            screen.blit(card_surf, c_rect)

        for sm in self.tire_smoke:
            if sm["life"] > 0.0:
                alpha = int(180 * max(0.0, sm["life"]))
                surf_sm = pygame.Surface((int(sm["size"] * 2), int(sm["size"] * 2)), pygame.SRCALPHA)
                pygame.draw.circle(surf_sm, (238, 236, 230, alpha), (int(sm["size"]), int(sm["size"])), int(sm["size"]))
                screen.blit(surf_sm, (int(sm["x"] - sm["size"]), int(sm["y"] - sm["size"])))

        self._draw_airplane(screen)
        screen.blit(self.character_sprite, (60, self.screen_h - 265))

        # Banner superior acuarela: Modo Avión + Viento
        banner = pygame.Rect(self.screen_w // 2 - 360, 28, 720, 74)
        pygame.draw.rect(screen, (252, 244, 228), banner, border_radius=20)
        pygame.draw.rect(screen, INK_DARK, banner, width=3, border_radius=20)
        txt_mode = self.font_ui.render("MODO AVIÓN ACTIVO · IGNORA LAS NOTIFICACIONES", True, INK_DARK)
        screen.blit(txt_mode, txt_mode.get_rect(center=(banner.centerx, banner.y + 23)))

        wind_dir_str = "VIENTO >>" if self.wind_force > 0 else "<< VIENTO"
        txt_w = self.font_small.render(f"TURBULENCIA EN CORTISSOZ: {wind_dir_str}", True, (192, 74, 48))
        screen.blit(txt_w, txt_w.get_rect(center=(banner.centerx, banner.y + 52)))

    def _draw_airplane(self, screen: pygame.Surface) -> None:
        px, py = int(self.plane_x), int(self.plane_y)
        scale = 0.65 + 0.35 * (py / self.plane_target_y)

        shadow_y = self.runway_bot_y - 20
        shadow_w = int(180 * scale)
        shadow_h = int(24 * scale)
        s_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(s_surf, (42, 34, 28, int(115 * scale)), (0, 0, shadow_w, shadow_h))
        screen.blit(s_surf, (px - shadow_w // 2, shadow_y))

        fuse_w = int(48 * scale)
        fuse_h = int(130 * scale)
        fuse_rect = pygame.Rect(px - fuse_w // 2, py - fuse_h // 2, fuse_w, fuse_h)
        pygame.draw.ellipse(screen, (252, 248, 240), fuse_rect)
        pygame.draw.ellipse(screen, INK_DARK, fuse_rect, width=3)

        wing_span = int(220 * scale)
        wing_y = py + int(10 * scale)
        pts_wings = [
            (px - wing_span // 2, wing_y),
            (px, py - int(15 * scale)),
            (px + wing_span // 2, wing_y),
            (px + wing_span // 2 - int(25 * scale), wing_y + int(24 * scale)),
            (px, py + int(25 * scale)),
            (px - wing_span // 2 + int(25 * scale), wing_y + int(24 * scale)),
        ]
        pygame.draw.polygon(screen, (236, 234, 228), pts_wings)
        pygame.draw.polygon(screen, INK_DARK, pts_wings, width=3)

        for tx in [px - int(60 * scale), px + int(60 * scale)]:
            turb_w = int(22 * scale)
            turb_h = int(32 * scale)
            pygame.draw.rect(screen, (92, 98, 108), (tx - turb_w // 2, wing_y - 4, turb_w, turb_h), border_radius=5)
            pygame.draw.ellipse(screen, (248, 186, 64), (tx - turb_w // 4, wing_y + turb_h - 6, turb_w // 2, int(16 * scale)))

        pts_tail = [
            (px - int(8 * scale), py + int(20 * scale)),
            (px, py - int(45 * scale)),
            (px + int(8 * scale), py + int(20 * scale)),
        ]
        pygame.draw.polygon(screen, (224, 62, 68), pts_tail)
        pygame.draw.polygon(screen, INK_DARK, pts_tail, width=2)
