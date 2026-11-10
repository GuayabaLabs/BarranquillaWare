import math
from typing import Optional, Callable, Dict, Any, List
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.settings import SettingsManager
from ui.button import UIButton
from scenes.slide_transition import SlideTransitionState

# Microjuegos
from microgames.mallorquin_photo import MallorquinPhotoMicrogame
from microgames.uninorte_sprint import UninorteSprintMicrogame
from microgames.ventana_colores import VentanaColoresMicrogame
from microgames.malecon_rueda import MaleconRuedaMicrogame
from microgames.metropolitano_penalty import MetropolitanoPenaltyMicrogame
from microgames.aeropuerto_aterrizaje import AeropuertoAterrizajeMicrogame
from microgames.batalla_flores_boss import BatallaFloresBossMicrogame
from microgames.fritanga_84 import Fritanga84Microgame
from microgames.troja_baile import TrojaBaileMicrogame

class FreePlayScene(BaseState):
    """
    Modo Libre / Catálogo de Minijuegos de BarranquillaWare:
    - Cuadrícula interactiva de 3x2 con tarjetas ilustradas de los 6 microjuegos.
    - Muestra estado de despeje (Estrella Dorada) y permite jugar cualquier minijuego individualmente.
    - Soporte de retorno suave a Selección de Modo.
    """
    def __init__(
        self,
        character_id: str = "westcol",
        on_back_callback: Optional[Callable[[], None]] = None
    ) -> None:
        super().__init__()
        self.screen_w = 1920
        self.screen_h = 1080
        self.character_id = character_id
        self.on_back_callback = on_back_callback

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()
        self.settings = SettingsManager.get_instance()

        self.timer = 0.0

        # Tipografías
        self.font_title = pygame.font.SysFont("Arial Black, Impact, sans-serif", 40)
        self.font_sub = pygame.font.SysFont("Arial, sans-serif", 18, bold=True)
        self.font_card_title = pygame.font.SysFont("Arial Black, Impact, sans-serif", 20)
        self.font_card_district = pygame.font.SysFont("Arial, sans-serif", 14, bold=True)
        self.font_card_desc = pygame.font.SysFont("Arial, sans-serif", 13)

        # Definición de las 6 tarjetas de minijuegos
        self.games_data: List[Dict[str, Any]] = [
            {
                "id": "mallorquin_photo",
                "title": "¡FOTOGRAFÍA AL FLAMENCO!",
                "district": "ECORRESERVA MALLORQUÍN",
                "desc": "Enfoca y dispara la cámara al flamenco caribeño.",
                "theme_color": (245, 115, 160),
                "cls": MallorquinPhotoMicrogame
            },
            {
                "id": "uninorte_sprint",
                "title": "CARRERA AL AULA DE 6:30",
                "district": "CAMPUS UNINORTE",
                "desc": "Corre mofando el pasillo antes de que cierre la puerta.",
                "theme_color": (250, 185, 45),
                "cls": UninorteSprintMicrogame
            },
            {
                "id": "ventana_colores",
                "title": "¡ARMONIZA LOS CRISTALES!",
                "district": "VENTANA AL MUNDO",
                "desc": "Armoniza los cristales de colores primarios en la torre.",
                "theme_color": (45, 165, 235),
                "cls": VentanaColoresMicrogame
            },
            {
                "id": "malecon_rueda",
                "title": "¡FRENA EN LA CIMA!",
                "district": "GRAN MALECÓN DEL RÍO",
                "desc": "Frena la cabina VIP en la cima de la rueda panorámica.",
                "theme_color": (240, 125, 55),
                "cls": MaleconRuedaMicrogame
            },
            {
                "id": "metropolitano_penalty",
                "title": "EL PENAL DEL TIBURÓN",
                "district": "ESTADIO METROPOLITANO",
                "desc": "Patea el penal decisivo al ángulo y canta el gol.",
                "theme_color": (230, 50, 60),
                "cls": MetropolitanoPenaltyMicrogame
            },
            {
                "id": "aeropuerto_aterrizaje",
                "title": "¡ATERRIZA EN LA PISTA!",
                "district": "AEROPUERTO CORTISSOZ",
                "desc": "Alinea el avión comercial con viento cruzado al tocar pista.",
                "theme_color": (45, 195, 110),
                "cls": AeropuertoAterrizajeMicrogame
            },
            {
                "id": "fritanga_84",
                "title": "¡LA FRITANGA DE LA 84!",
                "district": "CALLE 84 · PUESTO DE FRITOS",
                "desc": "Voltea las arepas de huevo en el caldero en su punto dorado.",
                "theme_color": (255, 175, 45),
                "cls": Fritanga84Microgame
            },
            {
                "id": "troja_baile",
                "title": "¡EQUILIBRIO EN LA TROJA!",
                "district": "LA TROJA · CALLE 74",
                "desc": "Baila salsa brava equilibrando el vaso helado en la cabeza.",
                "theme_color": (235, 60, 95),
                "cls": TrojaBaileMicrogame
            }
        ]

        # Botón Volver
        btn_back_surf = self.assets.get_scaled("boton_volver_seleccion_modo.png", target_width=170)
        self.btn_back = UIButton(
            center_pos=(130, 65),
            normal_sprite=btn_back_surf,
            on_click=self._on_back_clicked
        )

        # Generar rectángulos de las tarjetas (Cuadrícula 4x2)
        self.card_rects = []
        cw, ch = 390, 250
        gap_x, gap_y = 28, 24
        grid_w = 4 * cw + 3 * gap_x
        start_x = (self.screen_w - grid_w) // 2
        start_y = 190

        for idx, g in enumerate(self.games_data):
            col = idx % 4
            row = idx // 4
            rx = start_x + col * (cw + gap_x)
            ry = start_y + row * (ch + gap_y)
            self.card_rects.append(pygame.Rect(rx, ry, cw, ch))

        # Tarjeta dorada de la Etapa Jefe (Boss Stage)
        self.boss_card_rect = pygame.Rect(start_x, start_y + 2 * (ch + gap_y) + 12, grid_w, 88)

    def _on_back_clicked(self) -> None:
        self.audio.play_click()
        if self.on_back_callback:
            self.on_back_callback()

    def enter(self, params: Optional[dict] = None) -> None:
        if params and "character_id" in params:
            self.character_id = params["character_id"]
        self.audio.play_bgm("dodo_airlines_acnh_ost_seleccion_modo.ogg")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._on_back_clicked()
            return

        if self.btn_back.handle_event(event):
            return

        # Click sobre alguna tarjeta para jugar ese minijuego
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if hasattr(self, "boss_card_rect") and self.boss_card_rect.collidepoint(event.pos):
                self._launch_boss_stage()
                return

            for idx, rect in enumerate(self.card_rects):
                if rect.collidepoint(event.pos):
                    self._launch_game(idx)
                    return

    def _launch_boss_stage(self) -> None:
        self.audio.play_click()
        boss_game = BatallaFloresBossMicrogame(
            character_id=self.character_id,
            on_complete_callback=self._on_game_complete
        )
        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(boss_game)

    def _launch_game(self, game_idx: int) -> None:
        self.audio.play_click()
        g_data = self.games_data[game_idx]
        microgame = g_data["cls"](
            character_id=self.character_id,
            on_complete_callback=self._on_game_complete
        )

        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(microgame)

    def _on_game_complete(self, won: bool) -> None:
        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(self)

    def update(self, dt: float) -> None:
        self.timer += dt
        self.btn_back.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        # 1. Fondo suave con degradado cálido
        for y in range(self.screen_h):
            t = y / float(self.screen_h)
            r = int(24 * (1 - t) + 12 * t)
            g = int(32 * (1 - t) + 18 * t)
            b = int(52 * (1 - t) + 30 * t)
            surface.fill((r, g, b), (0, y, self.screen_w, 1))

        # Ondas sutiles de fondo
        for i in range(8):
            wy = 80 + i * 130
            wave_off = math.sin(self.timer * 1.5 + i) * 30.0
            pygame.draw.line(surface, (35, 48, 75, 40), (0, wy + wave_off), (self.screen_w, wy - wave_off), 2)

        # 2. Encabezado principal
        txt_title = self.font_title.render("MODO LIBRE · CATÁLOGO DE MINIJUEGOS", True, (255, 245, 230))
        surface.blit(txt_title, txt_title.get_rect(center=(self.screen_w // 2, 75)))

        txt_sub = self.font_sub.render("Selecciona cualquier minijuego para practicar libremente", True, (245, 195, 90))
        surface.blit(txt_sub, txt_sub.get_rect(center=(self.screen_w // 2, 125)))

        # 3. Renderizar las 6 tarjetas
        mouse_pos = pygame.mouse.get_pos()
        progress = self.settings.get_story_progress()
        completed_games = progress.get("completed_microgames", [])

        for idx, (rect, g_data) in enumerate(zip(self.card_rects, self.games_data)):
            is_hover = rect.collidepoint(mouse_pos)
            is_cleared = g_data["id"] in completed_games

            # Tarjeta interactiva con hover pop
            card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg_col = (30, 38, 56, 240) if not is_hover else (45, 56, 82, 255)
            border_col = g_data["theme_color"] if is_hover else (65, 80, 110)

            pygame.draw.rect(card_surf, bg_col, (0, 0, rect.width, rect.height), border_radius=22)
            pygame.draw.rect(card_surf, border_col, (0, 0, rect.width, rect.height), width=3, border_radius=22)

            # Franja de acento superior
            pygame.draw.rect(card_surf, g_data["theme_color"], (0, 0, rect.width, 10), border_top_left_radius=22, border_top_right_radius=22)

            # Tag de Distrito
            txt_dist = self.font_card_district.render(g_data["district"], True, g_data["theme_color"])
            card_surf.blit(txt_dist, (24, 25))

            # Título del minijuego
            txt_t = self.font_card_title.render(g_data["title"], True, (255, 255, 255))
            card_surf.blit(txt_t, (24, 55))

            # Descripción
            txt_d = self.font_card_desc.render(g_data["desc"], True, (190, 205, 225))
            card_surf.blit(txt_d, (24, 98))

            # Badge de Estado / Despejado con Estrella
            badge_surf = pygame.Surface((220, 38), pygame.SRCALPHA)
            if is_cleared:
                pygame.draw.rect(badge_surf, (35, 125, 60, 220), (0, 0, 220, 38), border_radius=12)
                pygame.draw.rect(badge_surf, (110, 245, 150), (0, 0, 220, 38), width=2, border_radius=12)
                lbl_badge = self.font_card_district.render("★ COMPLETADO", True, (220, 255, 230))
            else:
                pygame.draw.rect(badge_surf, (50, 60, 80, 180), (0, 0, 220, 38), border_radius=12)
                lbl_badge = self.font_card_district.render("DISPONIBLE", True, (180, 195, 215))

            badge_surf.blit(lbl_badge, lbl_badge.get_rect(center=(110, 19)))
            card_surf.blit(badge_surf, (24, 190))

            # Botón JUGAR a la derecha
            btn_play_w = 140
            play_surf = pygame.Surface((btn_play_w, 42), pygame.SRCALPHA)
            p_col = (255, 215, 60) if is_hover else (70, 90, 130)
            p_txt_col = (25, 20, 15) if is_hover else (240, 245, 255)
            pygame.draw.rect(play_surf, p_col, (0, 0, btn_play_w, 42), border_radius=14)
            lbl_play = self.font_card_district.render("¡JUGAR! ▶", True, p_txt_col)
            play_surf.blit(lbl_play, lbl_play.get_rect(center=(btn_play_w // 2, 21)))
            card_surf.blit(play_surf, (rect.width - btn_play_w - 24, 188))

            surface.blit(card_surf, rect)

        # 4. Renderizar Tarjeta Dorada de la Etapa Jefe (Boss Stage)
        if hasattr(self, "boss_card_rect"):
            b_hover = self.boss_card_rect.collidepoint(mouse_pos)
            b_surf = pygame.Surface((self.boss_card_rect.width, self.boss_card_rect.height), pygame.SRCALPHA)
            b_bg = (55, 42, 22, 245) if not b_hover else (75, 58, 28, 255)
            b_border = (255, 215, 45) if b_hover else (205, 160, 30)

            pygame.draw.rect(b_surf, b_bg, (0, 0, self.boss_card_rect.width, self.boss_card_rect.height), border_radius=18)
            pygame.draw.rect(b_surf, b_border, (0, 0, self.boss_card_rect.width, self.boss_card_rect.height), width=3, border_radius=18)

            # Icono Corona
            txt_crown = self.font_title.render("👑", True, (255, 225, 80))
            b_surf.blit(txt_crown, (28, 16))

            # Título y Subtítulo
            txt_boss_t = self.font_card_title.render("¡ETAPA JEFE: LA GRAN GUACHERNA Y BATALLA DE FLORES!", True, (255, 230, 90))
            b_surf.blit(txt_boss_t, (90, 18))
            txt_boss_d = self.font_card_district.render("Desafío multietapa de 15 segundos: Esquiva la maicena, toca la tambora y corona al Rey Momo.", True, (240, 220, 180))
            b_surf.blit(txt_boss_d, (90, 50))

            # Botón JUGAR JEFE
            btn_jw = 190
            j_surf = pygame.Surface((btn_jw, 44), pygame.SRCALPHA)
            j_col = (255, 220, 50) if b_hover else (210, 170, 35)
            pygame.draw.rect(j_surf, j_col, (0, 0, btn_jw, 44), border_radius=14)
            lbl_j = self.font_card_district.render("DESAFIAR JEFE ▶", True, (30, 20, 10))
            j_surf.blit(lbl_j, lbl_j.get_rect(center=(btn_jw // 2, 22)))
            b_surf.blit(j_surf, (self.boss_card_rect.width - btn_jw - 24, 23))

            surface.blit(b_surf, self.boss_card_rect)

        # 5. Botón Volver
        self.btn_back.render(surface)
