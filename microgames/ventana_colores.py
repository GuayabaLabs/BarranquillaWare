import math
import random
from typing import Optional, Callable
import pygame

from core.microgame import BaseMicrogame

INK_DARK = (78, 51, 35)


class VentanaColoresMicrogame(BaseMicrogame):
    # Control por movimiento: gestos de cámara -> teclas del juego (ver BaseMicrogame).
    CAMERA_ACTIONS = {"dedos": (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4)}
    # Colores del mando Xbox: B rojo, Y amarillo, X azul, A verde.
    GAMEPAD_BUTTON_KEYS = {1: pygame.K_1, 3: pygame.K_2, 2: pygame.K_3, 0: pygame.K_4}
    """
    Microjuego 4: '¡Armoniza los Cristales!' (Monumento Ventana al Mundo).
    - Temática social: Verifica los hechos reales (color real) antes de compartir información.
    - Mecánica: Toca el color que falta (1..4 o click en el botón correspondiente).
    """

    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡VERIFICA EL COLOR REAL!",
            time_limit=4.0,
            on_complete_callback=on_complete_callback,
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("tranquilaMusic.mp3")

    def setup_game(self) -> None:
        self.colors_palette = [
            {"id": 1, "name": "ROJO", "key": pygame.K_1, "color": (228, 66, 72), "glow": (250, 126, 132)},
            {"id": 2, "name": "AMARILLO", "key": pygame.K_2, "color": (246, 204, 64), "glow": (255, 232, 134)},
            {"id": 3, "name": "AZUL", "key": pygame.K_3, "color": (56, 136, 224), "glow": (122, 186, 250)},
            {"id": 4, "name": "VERDE", "key": pygame.K_4, "color": (62, 184, 92), "glow": (132, 232, 152)},
        ]

        self.target_color_idx = random.randint(0, 3)
        self.target_color = self.colors_palette[self.target_color_idx]

        self.answered: bool = False
        self.is_correct: bool = False
        self.prism_sparkles = []

        self.buttons = []
        btn_w, btn_h = 240, 76
        spacing = 40
        total_w = 4 * btn_w + 3 * spacing
        start_x = (self.screen_w - total_w) // 2
        btn_y = self.screen_h - 134

        for i, col in enumerate(self.colors_palette):
            bx = start_x + i * (btn_w + spacing)
            self.buttons.append({"idx": i, "rect": pygame.Rect(bx, btn_y, btn_w, btn_h), "data": col})

        self.font_banner = self.assets.cargarFuenteCuento(22)
        self.font_q = self.assets.cargarFuenteCuento(26)
        self.font_btn = self.assets.cargarFuenteCuento(24)
        self.font_num = self.assets.cargarFuenteCuento(18)

        self._load_character()
        self.backdrop_surf = self._build_backdrop_surface()

    def _build_backdrop_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.screen_w, self.screen_h))
        for y in range(0, self.screen_h, 8):
            t = y / float(self.screen_h)
            r = int(58 * (1 - t) + 186 * t)
            g = int(88 * (1 - t) + 154 * t)
            b = int(146 * (1 - t) + 178 * t)
            surf.fill((r, g, b), (0, y, self.screen_w, 8))

        # Estrellitas suaves del atardecer
        for sx, sy, sr in [(220, 140, 3), (420, 210, 2), (1490, 150, 3), (1680, 230, 2), (1240, 110, 2)]:
            pygame.draw.circle(surf, (255, 246, 210), (sx, sy), sr)

        # Glorieta y suelo acuarela
        pygame.draw.ellipse(surf, (132, 116, 102), (self.screen_w // 2 - 480, 735, 960, 190))
        pygame.draw.ellipse(surf, INK_DARK, (self.screen_w // 2 - 480, 735, 960, 190), width=4)
        pygame.draw.ellipse(surf, (198, 182, 158), (self.screen_w // 2 - 360, 755, 720, 120))
        return surf

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

        if event.type == pygame.KEYDOWN:
            for i, col in enumerate(self.colors_palette):
                if event.key in (col["key"], getattr(pygame, f"K_KP{col['id']}", None)):
                    self._check_choice(i)
                    return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.buttons:
                if btn["rect"].collidepoint(event.pos):
                    self._check_choice(btn["idx"])
                    return

    def _check_choice(self, chosen_idx: int) -> None:
        self.answered = True
        if chosen_idx == self.target_color_idx:
            self.is_correct = True
            self.outro_message = "¡DATO VERIFICADO!"
            self.trigger_screenshake(12.0, 0.2)
            self._spawn_prism_sparkles()
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()
            self.evaluate(True, delay=1.0, message="¡DATO VERIFICADO!")
        else:
            self.is_correct = False
            self.outro_message = "¡COMPARTISTE SIN VERIFICAR!"
            self.trigger_screenshake(8.0, 0.15)
            if hasattr(self.audio, "play_miss"):
                self.audio.play_miss()
            self.evaluate(False, delay=1.0, message="¡COMPARTISTE SIN VERIFICAR!")

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
                "life": 1.0,
            })

    def update_game(self, dt: float) -> None:
        for sp in self.prism_sparkles:
            sp["x"] += sp["vx"] * dt
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt * 1.5

    def draw_game(self, screen: pygame.Surface) -> None:
        screen.blit(self.backdrop_surf, (0, 0))

        # Banner superior temática social
        top_pill = pygame.Rect(self.screen_w // 2 - 360, 24, 720, 46)
        pygame.draw.rect(screen, (252, 244, 228), top_pill, border_radius=20)
        pygame.draw.rect(screen, INK_DARK, top_pill, width=3, border_radius=20)
        txt_b = self.font_banner.render("VENTANA AL MUNDO · VERIFICA ANTES DE COMPARTIR", True, INK_DARK)
        screen.blit(txt_b, txt_b.get_rect(center=top_pill.center))

        self._draw_monument(screen)

        for sp in self.prism_sparkles:
            if sp["life"] > 0.0:
                alpha = int(255 * max(0.0, sp["life"]))
                surf_sp = pygame.Surface((18, 18), pygame.SRCALPHA)
                pygame.draw.circle(surf_sp, (*sp["color"], alpha), (9, 9), int(sp["size"]))
                screen.blit(surf_sp, (int(sp["x"]) - 9, int(sp["y"]) - 9))

        screen.blit(self.character_sprite, (120, self.screen_h - 290))
        self._draw_buttons(screen)

    def _draw_monument(self, screen: pygame.Surface) -> None:
        cx = self.screen_w // 2
        top_y = 175
        bot_y = 755

        t_w = 114
        gap = 38
        left_x = cx - gap // 2 - t_w
        right_x = cx + gap // 2

        floor_h = (bot_y - top_y) // 4
        pulse = math.sin((self.time_limit - self.time_left) * 8.0) * 0.5 + 0.5

        for i in range(4):
            py = top_y + i * floor_h
            col_data = self.colors_palette[i]
            is_target = i == self.target_color_idx

            fill_col = col_data["color"]
            if is_target and not self.answered:
                fill_col = (
                    int(col_data["color"][0] * (1 - pulse) + 255 * pulse),
                    int(col_data["color"][1] * (1 - pulse) + 255 * pulse),
                    int(col_data["color"][2] * (1 - pulse) + 255 * pulse),
                )

            pygame.draw.rect(screen, fill_col, (left_x, py + 4, t_w, floor_h - 8), border_radius=8)
            pygame.draw.rect(screen, (252, 248, 240), (left_x, py + 4, t_w, floor_h - 8), width=3, border_radius=8)

            inv_col = self.colors_palette[3 - i]["color"]
            pygame.draw.rect(screen, inv_col, (right_x, py + 4, t_w, floor_h - 8), border_radius=8)
            pygame.draw.rect(screen, (252, 248, 240), (right_x, py + 4, t_w, floor_h - 8), width=3, border_radius=8)

        if not self.answered:
            lbl = self.font_q.render(f"¡VERIFICA Y ELIGE: {self.target_color['name']}!", True, INK_DARK)
            badge_w = max(360, lbl.get_width() + 56)
            badge_rect = pygame.Rect(0, 0, badge_w, 48)
            badge_rect.center = (cx, top_y - 44)
            pygame.draw.rect(screen, (252, 244, 228), badge_rect, border_radius=16)
            pygame.draw.rect(screen, self.target_color["color"], badge_rect, width=4, border_radius=16)
            screen.blit(lbl, lbl.get_rect(center=badge_rect.center))

    def _draw_buttons(self, screen: pygame.Surface) -> None:
        mouse_pos = pygame.mouse.get_pos()

        for btn in self.buttons:
            rect = btn["rect"]
            col_data = btn["data"]
            is_hover = rect.collidepoint(mouse_pos)

            surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg_col = col_data["glow"] if is_hover else col_data["color"]
            pygame.draw.rect(surf, (*bg_col, 245), (0, 0, rect.width, rect.height), border_radius=18)
            pygame.draw.rect(surf, (255, 250, 240), (0, 0, rect.width, rect.height), width=4, border_radius=18)
            pygame.draw.rect(surf, INK_DARK, (2, 2, rect.width - 4, rect.height - 4), width=2, border_radius=16)

            txt_name = self.font_btn.render(col_data["name"], True, INK_DARK)
            txt_num = self.font_num.render(f"[{col_data['id']}]", True, (255, 252, 245))
            surf.blit(txt_name, txt_name.get_rect(center=(rect.width // 2, rect.height // 2 - 9)))
            surf.blit(txt_num, txt_num.get_rect(center=(rect.width // 2, rect.height // 2 + 18)))

            screen.blit(surf, rect)
