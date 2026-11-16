import math
import random
from typing import Optional, Callable, List
import pygame

from core.microgame import BaseMicrogame

class Fritanga84Microgame(BaseMicrogame):
    # Control por movimiento: gestos de cámara -> teclas del juego (ver BaseMicrogame).
    CAMERA_ACTIONS = {"accion": pygame.K_SPACE}
    """
    Microjuego Folclórico 7: 'La Fritanga de la 84' (Calle 84 con Cra 51B).
    - Consigna: ¡VOLTEA LA AREPA!
    - Mecánica: 3 arepas de huevo se están fritando en un caldero con aceite caliente.
      Haz click sobre cada una o presiona ESPACIO/Flechas para voltearlas cuando alcancen
      el punto dorado crujiente antes de que se quemen.
    """
    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡VOLTEA LA AREPA!",
            time_limit=4.0,
            on_complete_callback=on_complete_callback
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("contraRelojMusic.mp3")

    def setup_game(self) -> None:
        # Caldero central
        self.caldero_center = (960, 580)
        self.caldero_radius = 380

        # 3 Arepas en el caldero
        positions = [(760, 540), (960, 480), (1160, 560)]
        self.arepas = []
        for idx, (ax, ay) in enumerate(positions):
            self.arepas.append({
                "id": idx,
                "x": float(ax),
                "y": float(ay),
                "radius": 85.0,
                "flip_progress": 0.0, # 0 = cara 1, 1 = volteada
                "is_flipped": False,
                "doneness": random.uniform(0.15, 0.35), # 0.0 -> 1.0 (óptimo 0.6..0.9, quemado > 1.05)
                "cook_speed": random.uniform(0.38, 0.48),
                "squash": 1.0
            })

        # Burbujas de aceite hirviendo
        self.bubbles: List[dict] = []
        for _ in range(35):
            self._spawn_bubble()

        # Partículas de humo y chispas
        self.smoke_particles: List[dict] = []

        self.font_arepa = pygame.font.SysFont("Arial Black, Impact, sans-serif", 24)
        self.font_status = pygame.font.SysFont("Arial Black, Impact, sans-serif", 32)

    def _spawn_bubble(self) -> None:
        ang = random.uniform(0, math.pi * 2)
        r = random.uniform(20, self.caldero_radius - 50)
        bx = self.caldero_center[0] + math.cos(ang) * r
        by = self.caldero_center[1] + math.sin(ang) * (r * 0.65)
        self.bubbles.append({
            "x": bx,
            "y": by,
            "r": random.uniform(5, 14),
            "max_r": random.uniform(14, 26),
            "grow_spd": random.uniform(18, 38),
            "life": 1.0
        })

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if self.phase != self.PHASE_PLAY or self.is_finished:
            return

        # Voltear con click directo sobre la arepa
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for a in self.arepas:
                dist = math.hypot(event.pos[0] - a["x"], event.pos[1] - a["y"])
                if dist <= a["radius"] + 15 and not a["is_flipped"]:
                    self._flip_arepa(a)
                    return

        # Voltear con barra espaciadora la primera que esté lista
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
            unflipped = [a for a in self.arepas if not a["is_flipped"]]
            if unflipped:
                # Voltear la que esté más cocida
                unflipped.sort(key=lambda x: x["doneness"], reverse=True)
                self._flip_arepa(unflipped[0])

    def _flip_arepa(self, a: dict) -> None:
        a["is_flipped"] = True
        a["squash"] = 0.2
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()
        # Humo y chispas de aceite
        for _ in range(12):
            self.smoke_particles.append({
                "x": a["x"] + random.uniform(-20, 20),
                "y": a["y"] + random.uniform(-20, 20),
                "vx": random.uniform(-40, 40),
                "vy": random.uniform(-140, -60),
                "r": random.uniform(8, 18),
                "life": 0.6,
                "color": (245, 235, 220)
            })

    def update_game(self, dt: float) -> None:
        # 1. Cocinar arepas
        all_flipped = True
        any_burned = False

        for a in self.arepas:
            a["doneness"] += a["cook_speed"] * dt

            # Físicas de squash de la vuelta
            if a["squash"] < 1.0:
                a["squash"] = min(1.0, a["squash"] + dt * 4.5)

            if not a["is_flipped"]:
                all_flipped = False
                if a["doneness"] > 1.25: # Se quemó
                    any_burned = True
            else:
                if a["doneness"] > 1.45:
                    any_burned = True

        if any_burned:
            self.finish_game(False)
            return

        if all_flipped and not self.is_finished:
            self.finish_game(True)
            return

        # 2. Burbujas de aceite
        for b in self.bubbles[:]:
            b["r"] += b["grow_spd"] * dt
            if b["r"] >= b["max_r"]:
                self.bubbles.remove(b)
                self._spawn_bubble()

        # 3. Partículas de humo
        for sp in self.smoke_particles[:]:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["r"] += dt * 14
            sp["life"] -= dt
            if sp["life"] <= 0:
                self.smoke_particles.remove(sp)

    def render_game(self, surface: pygame.Surface) -> None:
        # Fondo: Mostrador de fritos típico de la 84
        surface.fill((45, 30, 25))

        # Textura de baldosas de cocina
        for x in range(0, self.screen_w, 80):
            pygame.draw.line(surface, (55, 38, 32), (x, 0), (x, self.screen_h), 2)
        for y in range(0, self.screen_h, 80):
            pygame.draw.line(surface, (55, 38, 32), (0, y), (self.screen_w, y), 2)

        cx, cy = self.caldero_center
        cr = self.caldero_radius

        # 1. Caldero de hierro fundido negro con asas
        # Asas de hierro
        pygame.draw.circle(surface, (25, 25, 30), (cx - cr - 25, cy), 45, 14)
        pygame.draw.circle(surface, (25, 25, 30), (cx + cr + 25, cy), 45, 14)

        # Borde exterior del caldero
        pygame.draw.ellipse(surface, (22, 24, 28), (cx - cr - 18, cy - int(cr * 0.65) - 18, (cr + 18) * 2, int(cr * 1.3) + 36))
        pygame.draw.ellipse(surface, (45, 48, 55), (cx - cr - 6, cy - int(cr * 0.65) - 6, (cr + 6) * 2, int(cr * 1.3) + 12))

        # Aceite hirviendo dorado
        pygame.draw.ellipse(surface, (220, 145, 25), (cx - cr, cy - int(cr * 0.65), cr * 2, int(cr * 1.3)))
        pygame.draw.ellipse(surface, (245, 175, 35), (cx - int(cr * 0.85), cy - int(cr * 0.55), int(cr * 1.7), int(cr * 1.1)))

        # Burbujas en el aceite
        for b in self.bubbles:
            pygame.draw.circle(surface, (255, 215, 80), (int(b["x"]), int(b["y"])), int(b["r"]))
            pygame.draw.circle(surface, (255, 245, 160), (int(b["x"] - b["r"] * 0.3), int(b["y"] - b["r"] * 0.3)), max(1, int(b["r"] * 0.4)))

        # 2. Arepas de Huevo
        for a in self.arepas:
            ax, ay = int(a["x"]), int(a["y"])
            ar = int(a["radius"])
            sq = a["squash"]

            # Color según grado de cocción (de masa cruda amarilla a dorada y marrón tostado)
            done = a["doneness"]
            if done < 0.5:
                # Masa amarilla maicera cruda
                col = (250, 210, 70)
                edge_col = (220, 175, 40)
            elif done < 1.0:
                # Dorado crujiente perfecto
                t = (done - 0.5) / 0.5
                col = (int(250 - t * 30), int(210 - t * 65), int(70 - t * 35))
                edge_col = (185, 110, 25)
            else:
                # Quemándose
                col = (110, 60, 30)
                edge_col = (45, 25, 15)

            # Sombra en el aceite
            shadow_surf = pygame.Surface((ar * 2 + 20, int(ar * 1.5 * sq) + 20), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (140, 70, 10, 120), (10, 10, ar * 2, int(ar * 1.5 * sq)))
            surface.blit(shadow_surf, (ax - ar - 10, ay - int(ar * 0.75 * sq) - 10))

            # Arepa elipse con efecto squash
            arepa_rect = pygame.Rect(ax - ar, ay - int(ar * 0.75 * sq), ar * 2, int(ar * 1.5 * sq))
            pygame.draw.ellipse(surface, edge_col, arepa_rect)
            inner_rect = pygame.Rect(ax - ar + 6, ay - int(ar * 0.75 * sq) + 4, ar * 2 - 12, max(2, int(ar * 1.5 * sq) - 8))
            pygame.draw.ellipse(surface, col, inner_rect)

            # Pancita abombada del huevo en el centro
            egg_bump = pygame.Rect(ax - 28, ay - int(20 * sq), 56, max(2, int(40 * sq)))
            pygame.draw.ellipse(surface, (min(255, col[0] + 25), min(255, col[1] + 20), col[2]), egg_bump)

            # Etiqueta de estado
            if a["is_flipped"]:
                lbl = self.font_arepa.render("¡LISTA! ✓", True, (110, 255, 130))
            elif done > 0.65:
                lbl = self.font_arepa.render("¡VOLTÉALA!", True, (255, 235, 60))
            else:
                lbl = self.font_arepa.render("DORANDO...", True, (255, 255, 255))
            surface.blit(lbl, lbl.get_rect(center=(ax, ay + 65)))

        # 3. Humo
        for sp in self.smoke_particles:
            s_surf = pygame.Surface((int(sp["r"] * 2), int(sp["r"] * 2)), pygame.SRCALPHA)
            alpha = int(180 * (sp["life"] / 0.6))
            pygame.draw.circle(s_surf, (*sp["color"], alpha), (int(sp["r"]), int(sp["r"])), int(sp["r"]))
            surface.blit(s_surf, (int(sp["x"] - sp["r"]), int(sp["y"] - sp["r"])))

        # 4. Título superior
        txt_title = self.font_status.render("CALLE 84 · PUESTO DE FRITOS TRADICIONAL", True, (255, 220, 80))
        surface.blit(txt_title, txt_title.get_rect(center=(self.screen_w // 2, 80)))
