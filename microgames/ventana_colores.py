import math
import random
from typing import Optional, Callable
import pygame

from core.microgame import BaseMicrogame

class VentanaColoresMicrogame(BaseMicrogame):
    # Control por movimiento: gestos de cámara -> teclas del juego (ver BaseMicrogame).
    CAMERA_ACTIONS = {"dedos": (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4)}
    # Colores del mando Xbox: B rojo, Y amarillo, X azul, A verde.
    GAMEPAD_BUTTON_KEYS = {1: pygame.K_1, 3: pygame.K_2, 2: pygame.K_3, 0: pygame.K_4}
    """
    Microjuego 4: '¡Armoniza los Cristales!' (Monumento Ventana al Mundo).
    - Consigna: ¡TOCA EL COLOR QUE FALTA!
    - Mecánica: La torre de la Ventana al Mundo tiene 4 grandes paneles de cristal:
      Rojo, Amarillo, Azul y Verde. Uno de los cristales parpadea en blanco y pide su color.
      Presiona la tecla numérica (1: ROJO, 2: AMARILLO, 3: AZUL, 4: VERDE) o haz click
      sobre el botón de color correspondiente antes de que termine el tiempo (4s).
    - Game Feel: Resonancia de cristal, chispitas de luz prismáticas, screenshake e impacto.
    """
    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡TOCA EL COLOR CORRECTO!",
            time_limit=4.0,
            on_complete_callback=on_complete_callback
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("tranquilaMusic.mp3")

    def setup_game(self) -> None:
        self.colors_palette = [
            {"id": 1, "name": "ROJO", "key": pygame.K_1, "color": (235, 45, 55), "glow": (255, 120, 130)},
            {"id": 2, "name": "AMARILLO", "key": pygame.K_2, "color": (250, 210, 40), "glow": (255, 240, 140)},
            {"id": 3, "name": "AZUL", "key": pygame.K_3, "color": (40, 120, 240), "glow": (120, 190, 255)},
            {"id": 4, "name": "VERDE", "key": pygame.K_4, "color": (45, 190, 75), "glow": (140, 245, 160)}
        ]

        # Seleccionar color objetivo al azar
        self.target_color_idx = random.randint(0, 3)
        self.target_color = self.colors_palette[self.target_color_idx]

        self.answered: bool = False
        self.is_correct: bool = False
        self.prism_sparkles = []

        # Botones táctiles inferiores
        self.buttons = []
        btn_w, btn_h = 240, 75
        spacing = 40
        total_w = 4 * btn_w + 3 * spacing
        start_x = (self.screen_w - total_w) // 2
        btn_y = self.screen_h - 130

        for i, col in enumerate(self.colors_palette):
            bx = start_x + i * (btn_w + spacing)
            self.buttons.append({
                "idx": i,
                "rect": pygame.Rect(bx, btn_y, btn_w, btn_h),
                "data": col
            })

        # Cargar sprite del personaje espectador
        self._load_character()

    def _load_character(self) -> None:
        sprite_filename = f"{self.character_id}_seleccion_personaje.png"
        try:
            raw = self.assets.load_surface(sprite_filename, has_alpha=True)
            mask = pygame.mask.from_surface(raw)
            rects = mask.get_bounding_rects()
            cropped = raw.subsurface(rects[0]) if rects else raw
            target_h = 240
            target_w = int(cropped.get_width() * (target_h / float(cropped.get_height())))
            self.character_sprite = pygame.transform.smoothscale(cropped, (target_w, target_h))
        except Exception:
            self.character_sprite = pygame.Surface((120, 240), pygame.SRCALPHA)
            pygame.draw.rect(self.character_sprite, (220, 160, 60), (0, 0, 120, 240), border_radius=18)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if self.answered:
            return

        # Selección por teclado numérico (1, 2, 3, 4)
        if event.type == pygame.KEYDOWN:
            for i, col in enumerate(self.colors_palette):
                if event.key in (col["key"], getattr(pygame, f"K_KP{col['id']}", None)):
                    self._check_choice(i)
                    return

        # Selección por click del mouse
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.buttons:
                if btn["rect"].collidepoint(event.pos):
                    self._check_choice(btn["idx"])
                    return

    def _check_choice(self, chosen_idx: int) -> None:
        self.answered = True
        if chosen_idx == self.target_color_idx:
            self.is_correct = True
            self.trigger_screenshake(12.0, 0.2)
            self._spawn_prism_sparkles()
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()
            self.evaluate(True, delay=1.0, message="¡ARMONÍA PERFECTA!")
        else:
            self.is_correct = False
            self.trigger_screenshake(8.0, 0.15)
            if hasattr(self.audio, "play_miss"):
                self.audio.play_miss()
            self.evaluate(False, delay=1.0, message="¡COLOR INCORRECTO!")

    def _spawn_prism_sparkles(self) -> None:
        cx, cy = self.screen_w // 2, 420
        for _ in range(25):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(120, 360)
            self.prism_sparkles.append({
                "x": float(cx),
                "y": float(cy),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "color": random.choice([c["color"] for c in self.colors_palette]),
                "size": random.uniform(5.0, 9.0),
                "life": 1.0
            })

    def update_game(self, dt: float) -> None:
        for sp in self.prism_sparkles:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt * 1.5

    def draw_game(self, screen: pygame.Surface) -> None:
        # 1. Cielo crepuscular con gradiente
        for y in range(self.screen_h):
            t = y / float(self.screen_h)
            r = int(25 * (1 - t) + 15 * t)
            g = int(35 * (1 - t) + 25 * t)
            b = int(75 * (1 - t) + 45 * t)
            screen.fill((r, g, b), (0, y, self.screen_w, 1))

        # 2. Glorieta y suelo
        pygame.draw.ellipse(screen, (30, 45, 60), (self.screen_w // 2 - 450, 740, 900, 180))
        pygame.draw.ellipse(screen, (40, 60, 80), (self.screen_w // 2 - 450, 740, 900, 180), width=4)

        # 3. Dibujar las dos torres de la Ventana al Mundo
        self._draw_monument(screen)

        # 4. Renderizar chispitas de prisma
        for sp in self.prism_sparkles:
            if sp["life"] > 0.0:
                alpha = int(255 * max(0.0, sp["life"]))
                surf_sp = pygame.Surface((18, 18), pygame.SRCALPHA)
                pygame.draw.circle(surf_sp, (*sp["color"], alpha), (9, 9), int(sp["size"]))
                screen.blit(surf_sp, (int(sp["x"]) - 9, int(sp["y"]) - 9))

        # 5. Renderizar personaje
        screen.blit(self.character_sprite, (120, self.screen_h - 290))

        # 6. Renderizar botones de colores en la parte inferior
        self._draw_buttons(screen)

    def _draw_monument(self, screen: pygame.Surface) -> None:
        cx = self.screen_w // 2
        top_y = 170
        bot_y = 750

        # Torre Izquierda y Derecha
        t_w = 110
        gap = 40
        left_x = cx - gap // 2 - t_w
        right_x = cx + gap // 2

        # Paneles de la torre izquierda (4 pisos)
        floor_h = (bot_y - top_y) // 4
        pulse = math.sin(self.timer * 8.0) * 0.5 + 0.5

        for i in range(4):
            py = top_y + i * floor_h
            col_data = self.colors_palette[i]
            is_target = (i == self.target_color_idx)

            # Panel izquierdo
            fill_col = col_data["color"]
            if is_target and not self.answered:
                # Parpadeo de color blanco / brillante pidiendo respuesta
                fill_col = (
                    int(col_data["color"][0] * (1 - pulse) + 255 * pulse),
                    int(col_data["color"][1] * (1 - pulse) + 255 * pulse),
                    int(col_data["color"][2] * (1 - pulse) + 255 * pulse)
                )

            # Marco de cristal
            pygame.draw.rect(screen, fill_col, (left_x, py + 4, t_w, floor_h - 8), border_radius=6)
            pygame.draw.rect(screen, (255, 255, 255), (left_x, py + 4, t_w, floor_h - 8), width=3, border_radius=6)

            # Panel derecho (reflejo invertido)
            inv_col = self.colors_palette[3 - i]["color"]
            pygame.draw.rect(screen, inv_col, (right_x, py + 4, t_w, floor_h - 8), border_radius=6)
            pygame.draw.rect(screen, (255, 255, 255), (right_x, py + 4, t_w, floor_h - 8), width=3, border_radius=6)

        # Indicador central de color objetivo
        if not self.answered:
            font_q = pygame.font.SysFont("Arial Black, Impact", 26)
            lbl = font_q.render(f"¡ELIGE: {self.target_color['name']}!", True, self.target_color["color"])
            badge_w = lbl.get_width() + 40
            badge_surf = pygame.Surface((badge_w, 48), pygame.SRCALPHA)
            pygame.draw.rect(badge_surf, (20, 25, 40, 230), (0, 0, badge_w, 48), border_radius=14)
            pygame.draw.rect(badge_surf, self.target_color["color"], (0, 0, badge_w, 48), width=2, border_radius=14)
            badge_surf.blit(lbl, lbl.get_rect(center=(badge_w // 2, 24)))
            screen.blit(badge_surf, badge_surf.get_rect(center=(cx, top_y - 45)))

    def _draw_buttons(self, screen: pygame.Surface) -> None:
        mouse_pos = pygame.mouse.get_pos()
        font_btn = pygame.font.SysFont("Arial Black, Impact", 22)
        font_num = pygame.font.SysFont("Arial Black, Impact", 16)

        for btn in self.buttons:
            rect = btn["rect"]
            col_data = btn["data"]
            is_hover = rect.collidepoint(mouse_pos)

            surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg_col = col_data["glow"] if is_hover else col_data["color"]
            pygame.draw.rect(surf, (*bg_col, 240), (0, 0, rect.width, rect.height), border_radius=16)
            pygame.draw.rect(surf, (255, 255, 255), (0, 0, rect.width, rect.height), width=3, border_radius=16)

            # Texto del botón
            txt_name = font_btn.render(col_data["name"], True, (25, 20, 15))
            txt_num = font_num.render(f"[{col_data['id']}]", True, (255, 255, 255))
            surf.blit(txt_name, txt_name.get_rect(center=(rect.width // 2, rect.height // 2 - 8)))
            surf.blit(txt_num, txt_num.get_rect(center=(rect.width // 2, rect.height // 2 + 18)))

            screen.blit(surf, rect)
