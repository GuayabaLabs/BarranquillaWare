import math
from typing import Optional, Callable, Dict, Any, List, Tuple
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.settings import SettingsManager, CHARACTER_DISPLAY_NAMES
from ui.button import UIButton
from scenes.load_game import make_watercolor_button_surface, render_outlined_text

# Microjuegos Clásicos + Nuevos (Modo Historia) + Jefe
from microgames.mallorquin_photo import MallorquinPhotoMicrogame
from microgames.uninorte_sprint import UninorteSprintMicrogame
from microgames.ventana_colores import VentanaColoresMicrogame
from microgames.malecon_rueda import MaleconRuedaMicrogame
from microgames.metropolitano_penalty import MetropolitanoPenaltyMicrogame
from microgames.aeropuerto_aterrizaje import AeropuertoAterrizajeMicrogame
from microgames.fritanga_84 import Fritanga84Microgame
from microgames.troja_baile import TrojaBaileMicrogame
from microgames.uninorte_concentrate import UninorteConcentrateMicrogame
from microgames.buenavista_trend import BuenavistaTrendMicrogame
from microgames.metropolitano_moderacion import MetropolitanoModeracionMicrogame
from microgames.punch_alert import PunchAlertMicrogame
from microgames.buenavista_cine import BuenavistaCineMicrogame
from microgames.batalla_flores_boss import BatallaFloresBossMicrogame


INK_DARK = (78, 51, 35)       # #4E3323 Tinta café principal
INK_MUTED = (118, 84, 62)     # Tinta café suave para descripciones
CREAM_TEXT = (255, 250, 238)  # Crema cálido para botones acuarela


def _wrap_text(font: pygame.font.Font, text: str, max_width: int, max_lines: int = 2) -> List[str]:
    """Envuelve texto en líneas sin exceder max_width."""
    words = text.split()
    lines: List[str] = []
    current = ""
    for w in words:
        candidate = f"{current} {w}".strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = w
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    elif current and lines:
        last = lines[-1]
        while font.size(last + "...")[0] > max_width and len(last) > 3:
            last = last[:-1].rstrip()
        lines[-1] = last + "..."
    return lines


class FreePlayScene(BaseState):
    """
    Modo Libre / Catálogo Completo de Minijuegos de BarranquillaWare (Estilo Acuarela Cozy 1920x1080):
    - Fondo acuarela pre-escalado cacheado (cero degradados por línea en cada frame).
    - Catálogo paginado (4x2 por página) con TODOS los microjuegos jugables (clásicos + nuevos)
      y acceso permanente a la Etapa Jefe (Batalla de Flores).
    - Instanciación perezosa (solo al hacer click) para no activar cámara/micrófono en menús ni pruebas.
    """

    def __init__(
        self,
        character_id: str = "westcol",
        on_back_callback: Optional[Callable[[], None]] = None,
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
        self._active_microgame = None

        # 1. Fondo acuarela pre-escalado cacheado
        raw_bg = self.assets.load_surface("fondo_modo_libre.png", has_alpha=False)
        self.background = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))

        # Título ilustrado oficial de Modo Libre
        self.title_surf = self.assets.get_scaled("titulo_modo_libre.png", target_width=440)

        # Tipografías acuarela del proyecto (IndieFlower-Regular)
        self.font_sub = self.assets.cargarFuenteCuento(24)
        self.font_card_title = self.assets.cargarFuenteCuento(24)
        self.font_card_district = self.assets.cargarFuenteCuento(17)
        self.font_card_desc = self.assets.cargarFuenteCuento(17)
        self.font_badge = self.assets.cargarFuenteCuento(18)
        self.font_boss_title = self.assets.cargarFuenteCuento(28)
        self.font_boss_desc = self.assets.cargarFuenteCuento(20)
        self.font_page = self.assets.cargarFuenteCuento(22)

        # 2. Catálogo completo de microjuegos jugables (8 clásicos + 5 nuevos)
        self.games_data: List[Dict[str, Any]] = [
            {
                "id": "mallorquin_photo",
                "title": "FOTOGRAFÍA AL FLAMENCO",
                "district": "ECORRESERVA MALLORQUÍN",
                "desc": "Vive el momento real sin filtros y encuadra al flamenco caribeño.",
                "difficulty": 2,
                "theme_color": (224, 108, 146),
                "cls": MallorquinPhotoMicrogame,
            },
            {
                "id": "uninorte_sprint",
                "title": "CARRERA AL AULA A-203",
                "district": "CAMPUS UNINORTE",
                "desc": "Cruza el campus sin distraerte con el celular antes de la clase.",
                "difficulty": 2,
                "theme_color": (218, 148, 42),
                "cls": UninorteSprintMicrogame,
            },
            {
                "id": "uninorte_concentrate",
                "title": "¡CONCÉNTRATE, LLAVE!",
                "district": "BIBLIOTECA UNINORTE",
                "desc": "Espanta nubes de redes sociales para mantener la mente enfocada.",
                "difficulty": 2,
                "theme_color": (72, 168, 128),
                "cls": UninorteConcentrateMicrogame,
            },
            {
                "id": "ventana_colores",
                "title": "ARMONIZA LOS CRISTALES",
                "district": "VENTANA AL MUNDO",
                "desc": "Verifica el color real antes de compartir información.",
                "difficulty": 2,
                "theme_color": (58, 148, 212),
                "cls": VentanaColoresMicrogame,
            },
            {
                "id": "buenavista_trend",
                "title": "EL TREND EN BUENAVISTA",
                "district": "C.C. BUENAVISTA",
                "desc": "Sigue el compás con D/F/J/K sin dejarte dominar por el algoritmo.",
                "difficulty": 3,
                "theme_color": (162, 102, 206),
                "cls": BuenavistaTrendMicrogame,
            },
            {
                "id": "buenavista_cine",
                "title": "¡SILENCIO, HAY FUNCIÓN!",
                "district": "CINE BUENAVISTA",
                "desc": "Chista (SHHH o Espacio) a quienes usan el celular en la sala.",
                "difficulty": 3,
                "theme_color": (182, 92, 134),
                "cls": BuenavistaCineMicrogame,
            },
            {
                "id": "malecon_rueda",
                "title": "FRENA EN LA CIMA",
                "district": "GRAN MALECÓN DEL RÍO",
                "desc": "Suelta el scroll y detén la cabina VIP en lo más alto del río.",
                "difficulty": 3,
                "theme_color": (214, 118, 52),
                "cls": MaleconRuedaMicrogame,
            },
            {
                "id": "metropolitano_moderacion",
                "title": "¡MODERA LA BARRA!",
                "district": "ESTADIO METROPOLITANO",
                "desc": "Frena el ciberacoso en el chat en vivo sin silenciar al hincha sano.",
                "difficulty": 3,
                "theme_color": (205, 68, 76),
                "cls": MetropolitanoModeracionMicrogame,
            },
            {
                "id": "metropolitano_penalty",
                "title": "EL PENAL DEL TIBURÓN",
                "district": "ESTADIO METROPOLITANO",
                "desc": "Ignora la presión en vivo de las redes y clávala al ángulo.",
                "difficulty": 3,
                "theme_color": (212, 62, 68),
                "cls": MetropolitanoPenaltyMicrogame,
            },
            {
                "id": "punch_alert",
                "title": "¡DESPACHA EL SPAM!",
                "district": "AEROPUERTO CORTISSOZ",
                "desc": "Batea las alertas invasivas y deja pasar las noticias reales.",
                "difficulty": 4,
                "theme_color": (68, 148, 198),
                "cls": PunchAlertMicrogame,
            },
            {
                "id": "aeropuerto_aterrizaje",
                "title": "ATERRIZA EN MODO AVIÓN",
                "district": "AEROPUERTO CORTISSOZ",
                "desc": "Ignora notificaciones distractoras y alinea el avión en pista.",
                "difficulty": 3,
                "theme_color": (56, 165, 108),
                "cls": AeropuertoAterrizajeMicrogame,
            },
            {
                "id": "fritanga_84",
                "title": "LA FRITANGA DE LA 84",
                "district": "CALLE 84 · FRITOS",
                "desc": "Cocina a tu ritmo sin afán viral: voltea las arepas en su punto.",
                "difficulty": 3,
                "theme_color": (222, 148, 38),
                "cls": Fritanga84Microgame,
            },
            {
                "id": "troja_baile",
                "title": "EQUILIBRIO EN LA TROJA",
                "district": "LA TROJA · CALLE 74",
                "desc": "Desconéctate y baila el momento real equilibrando el vaso.",
                "difficulty": 4,
                "theme_color": (212, 66, 98),
                "cls": TrojaBaileMicrogame,
            },
        ]

        # 3. Cargar assets acuarela de tarjetas, cintas, estrellas y sellos
        self.cw, self.ch = 412, 260
        self.gap_x, self.gap_y = 28, 22
        self.grid_w = 4 * self.cw + 3 * self.gap_x
        self.grid_start_x = (self.screen_w - self.grid_w) // 2
        self.grid_start_y = 200

        raw_card = self.assets.load_cropped_surface("tarjeta_slot_partida.png")
        self.card_bg_surf = pygame.transform.smoothscale(raw_card, (self.cw, self.ch))

        raw_ribbon = self.assets.load_cropped_surface("cinta_distrito_modal.png")
        self.header_ribbon_surf = pygame.transform.smoothscale(raw_ribbon, (700, 44))
        self.card_ribbon_surf = pygame.transform.smoothscale(raw_ribbon, (self.cw - 44, 34))
        self.page_ribbon_surf = pygame.transform.smoothscale(raw_ribbon, (230, 46))
        self.char_badge_surf = pygame.transform.smoothscale(raw_ribbon, (310, 48))

        raw_star = self.assets.load_cropped_surface("estrella_dificultad.png")
        self.star_on_surf = pygame.transform.smoothscale(raw_star, (20, 20))
        self.star_off_surf = pygame.transform.grayscale(self.star_on_surf)
        self.star_off_surf.set_alpha(95)

        raw_emblem = self.assets.load_cropped_surface("emblema_estrella_modal.png")
        self.emblem_surf = pygame.transform.smoothscale(raw_emblem, (64, 60))

        raw_done = self.assets.load_cropped_surface("sello_estado_despejado.png")
        self.seal_done_surf = pygame.transform.smoothscale(raw_done, (30, 31))
        raw_pend = self.assets.load_cropped_surface("sello_estado_pendiente.png")
        self.seal_pend_surf = pygame.transform.smoothscale(raw_pend, (30, 31))

        self.btn_play_normal = make_watercolor_button_surface(
            self.assets, "green", "¡JUGAR!", (140, 42), font_size=20
        )
        self.btn_play_hover = make_watercolor_button_surface(
            self.assets, "orange", "¡JUGAR!", (140, 42), font_size=20
        )

        # 4. Paginación fluida (8 por página)
        self.cards_per_page = 8
        self.current_page = 0
        self.total_pages = max(1, math.ceil(len(self.games_data) / self.cards_per_page))
        self.card_rects: List[pygame.Rect] = []
        self._visible_indices: List[int] = []
        self._hover_lifts: Dict[int, float] = {}
        self.selected_card_pos: int = -1
        self._rebuild_page_layout()

        # Botones de navegación de página
        prev_surf = make_watercolor_button_surface(self.assets, "orange", "< ANTERIOR", (185, 48), font_size=20)
        next_surf = make_watercolor_button_surface(self.assets, "green", "SIGUIENTE >", (185, 48), font_size=20)
        nav_y = self.grid_start_y + 2 * self.ch + self.gap_y + 34
        self.btn_prev_page = UIButton((self.screen_w // 2 - 235, nav_y), prev_surf, on_click=self.prev_page)
        self.btn_next_page = UIButton((self.screen_w // 2 + 235, nav_y), next_surf, on_click=self.next_page)

        # Botón Volver
        btn_back_surf = self.assets.get_scaled("boton_volver_seleccion_modo.png", target_width=175)
        self.btn_back = UIButton(
            center_pos=(130, 75),
            normal_sprite=btn_back_surf,
            on_click=self._on_back_clicked,
        )

        # 5. Tarjeta Dorada Acuarela de la Etapa Jefe (siempre visible en la parte inferior)
        boss_y = nav_y + 44
        self.boss_card_rect = pygame.Rect(self.grid_start_x, boss_y, self.grid_w, 114)
        self.boss_card_bg = pygame.transform.smoothscale(raw_card, (self.grid_w, 114))
        self.boss_btn_surf = make_watercolor_button_surface(
            self.assets, "orange", "DESAFIAR JEFE", (240, 56), font_size=22
        )
        self._boss_hover_lift = 0.0

    def _rebuild_page_layout(self) -> None:
        start = self.current_page * self.cards_per_page
        end = min(len(self.games_data), start + self.cards_per_page)
        self._visible_indices = list(range(start, end))
        self.card_rects = []
        for slot_idx in range(len(self._visible_indices)):
            col = slot_idx % 4
            row = slot_idx // 4
            rx = self.grid_start_x + col * (self.cw + self.gap_x)
            ry = self.grid_start_y + row * (self.ch + self.gap_y)
            self.card_rects.append(pygame.Rect(rx, ry, self.cw, self.ch))

    def prev_page(self) -> None:
        if self.total_pages <= 1:
            return
        self.current_page = (self.current_page - 1) % self.total_pages
        self.selected_card_pos = -1
        self._rebuild_page_layout()

    def next_page(self) -> None:
        if self.total_pages <= 1:
            return
        self.current_page = (self.current_page + 1) % self.total_pages
        self.selected_card_pos = -1
        self._rebuild_page_layout()

    def _on_back_clicked(self) -> None:
        self.audio.play_click()
        if self.on_back_callback:
            self.on_back_callback()

    def enter(self, params: Optional[dict] = None) -> None:
        if params and "character_id" in params:
            self.character_id = params["character_id"]
        self.audio.play_bgm("dodo_airlines_acnh_ost_seleccion_modo.ogg")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._on_back_clicked()
                return
            if event.key in (pygame.K_PAGEUP, pygame.K_LEFT, pygame.K_a):
                self.audio.play_click()
                self.prev_page()
                return
            if event.key in (pygame.K_PAGEDOWN, pygame.K_RIGHT, pygame.K_d):
                self.audio.play_click()
                self.next_page()
                return

        if event.type == pygame.MOUSEWHEEL:
            if event.y < 0:
                self.next_page()
            elif event.y > 0:
                self.prev_page()
            return

        if self.btn_back.handle_event(event):
            return
        if self.total_pages > 1:
            if self.btn_prev_page.handle_event(event):
                return
            if self.btn_next_page.handle_event(event):
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.boss_card_rect.collidepoint(event.pos):
                self._launch_boss_stage()
                return

            for slot_idx, rect in enumerate(self.card_rects):
                if rect.collidepoint(event.pos):
                    self._launch_game(self._visible_indices[slot_idx])
                    return

    def _launch_boss_stage(self) -> None:
        self.audio.play_click()
        boss_game = BatallaFloresBossMicrogame(
            character_id=self.character_id,
            on_complete_callback=self._on_game_complete,
        )
        boss_game.pause_return_callback = lambda: self._on_game_complete(False)
        self._active_microgame = boss_game
        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(boss_game)

    def _launch_game(self, game_idx: int) -> None:
        self.audio.play_click()
        g_data = self.games_data[game_idx]
        microgame = g_data["cls"](
            character_id=self.character_id,
            on_complete_callback=self._on_game_complete,
        )
        microgame.pause_return_callback = lambda: self._on_game_complete(False)
        self._active_microgame = microgame

        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(microgame)

    def _on_game_complete(self, won: bool) -> None:
        if self._active_microgame is not None and hasattr(self._active_microgame, "cleanup"):
            try:
                self._active_microgame.cleanup()
            except Exception:
                pass
        self._active_microgame = None
        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(self)

    def update(self, dt: float) -> None:
        self.timer += dt
        self.btn_back.update(dt)
        if self.total_pages > 1:
            self.btn_prev_page.update(dt)
            self.btn_next_page.update(dt)

        mouse_pos = pygame.mouse.get_pos()
        blend = 1.0 - math.exp(-16.0 * dt)
        for slot_idx, rect in enumerate(self.card_rects):
            game_idx = self._visible_indices[slot_idx]
            target = -6.0 if rect.collidepoint(mouse_pos) else 0.0
            cur = self._hover_lifts.get(game_idx, 0.0)
            self._hover_lifts[game_idx] = cur + (target - cur) * blend

        boss_target = -5.0 if self.boss_card_rect.collidepoint(mouse_pos) else 0.0
        self._boss_hover_lift += (boss_target - self._boss_hover_lift) * blend

    def render(self, surface: pygame.Surface) -> None:
        # 1. Fondo acuarela pre-escalado
        surface.blit(self.background, (0, 0))

        # 2. Encabezado ilustrado y cinta de subtítulo
        bob_y = math.sin(self.timer * 2.0) * 3.0
        surface.blit(self.title_surf, self.title_surf.get_rect(center=(self.screen_w // 2, int(74 + bob_y))))

        ribbon_rect = self.header_ribbon_surf.get_rect(center=(self.screen_w // 2, 152))
        surface.blit(self.header_ribbon_surf, ribbon_rect)
        sub_txt = self.font_sub.render(
            "CATÁLOGO DE MINIJUEGOS · ELIGE CUALQUIERA PARA PRACTICAR", True, INK_DARK
        )
        surface.blit(sub_txt, sub_txt.get_rect(center=(ribbon_rect.centerx, ribbon_rect.centery - 1)))

        # Indicador de personaje y progreso en esquina superior derecha
        progress = self.settings.get_story_progress()
        completed_games = set(progress.get("completed_microgames", []))
        char_label = CHARACTER_DISPLAY_NAMES.get((self.character_id or "westcol").lower(), "Westcol")
        cleared_count = sum(1 for g in self.games_data if g["id"] in completed_games)
        badge_rect = self.char_badge_surf.get_rect(center=(1720, 75))
        surface.blit(self.char_badge_surf, badge_rect)
        badge_txt = self.font_badge.render(
            f"{char_label} · {cleared_count}/{len(self.games_data)} LISTOS", True, INK_DARK
        )
        surface.blit(badge_txt, badge_txt.get_rect(center=badge_rect.center))

        # 3. Tarjetas acuarela de la página actual
        mouse_pos = pygame.mouse.get_pos()
        for slot_idx, rect in enumerate(self.card_rects):
            game_idx = self._visible_indices[slot_idx]
            g_data = self.games_data[game_idx]
            is_hover = rect.collidepoint(mouse_pos)
            is_cleared = g_data["id"] in completed_games
            lift_y = int(round(self._hover_lifts.get(game_idx, 0.0)))
            draw_rect = rect.move(0, lift_y)

            self._render_game_card(surface, draw_rect, g_data, is_hover, is_cleared)

        # 4. Controles de paginación acuarela
        if self.total_pages > 1:
            self.btn_prev_page.render(surface)
            self.btn_next_page.render(surface)
            nav_y = self.btn_prev_page.center_y
            page_rect = self.page_ribbon_surf.get_rect(center=(self.screen_w // 2, nav_y))
            surface.blit(self.page_ribbon_surf, page_rect)
            page_lbl = self.font_page.render(
                f"PÁGINA {self.current_page + 1} / {self.total_pages}", True, INK_DARK
            )
            surface.blit(page_lbl, page_lbl.get_rect(center=(page_rect.centerx, page_rect.centery - 1)))

        # 5. Tarjeta de la Etapa Jefe (siempre accesible abajo)
        self._render_boss_card(surface, mouse_pos)

        # 6. Botón Volver
        self.btn_back.render(surface)

    def _render_game_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        g_data: Dict[str, Any],
        is_hover: bool,
        is_cleared: bool,
    ) -> None:
        # Sombra acuarela suave bajo la tarjeta
        shadow = pygame.Surface((rect.width + 12, rect.height + 12), pygame.SRCALPHA)
        pygame.draw.rect(
            shadow,
            (92, 62, 42, 55 if not is_hover else 85),
            (6, 8, rect.width, rect.height),
            border_radius=24,
        )
        surface.blit(shadow, (rect.x - 6, rect.y - 4))

        # Marco de pergamino acuarela oficial
        card_surf = self.card_bg_surf.copy()

        # Realce de borde al hacer hover
        if is_hover:
            pygame.draw.rect(
                card_surf,
                g_data["theme_color"],
                (6, 6, rect.width - 12, rect.height - 12),
                width=4,
                border_radius=20,
            )

        # Cinta de distrito superior
        card_surf.blit(self.card_ribbon_surf, (22, 16))
        txt_dist = self.font_card_district.render(g_data["district"], True, INK_DARK)
        card_surf.blit(txt_dist, txt_dist.get_rect(center=(rect.width // 2, 32)))

        # Título (máx 2 líneas)
        title_lines = _wrap_text(self.font_card_title, g_data["title"], rect.width - 48, max_lines=2)
        ty = 60
        for line in title_lines:
            t_surf = self.font_card_title.render(line, True, INK_DARK)
            card_surf.blit(t_surf, (26, ty))
            ty += 26

        # Descripción (máx 2 líneas)
        desc_lines = _wrap_text(self.font_card_desc, g_data["desc"], rect.width - 52, max_lines=2)
        dy = max(112, ty + 4)
        for line in desc_lines:
            d_surf = self.font_card_desc.render(line, True, INK_MUTED)
            card_surf.blit(d_surf, (26, dy))
            dy += 21

        # Estrellas de dificultad reales (estrella_dificultad.png)
        diff = int(g_data.get("difficulty", 2))
        star_y = 166
        for s_i in range(5):
            star_img = self.star_on_surf if s_i < diff else self.star_off_surf
            card_surf.blit(star_img, (26 + s_i * 24, star_y))

        # Sello de estado a la izquierda (sin glifos rotos)
        if is_cleared:
            card_surf.blit(self.seal_done_surf, (26, 202))
            lbl_badge = self.font_badge.render("COMPLETADO", True, (24, 114, 62))
        else:
            card_surf.blit(self.seal_pend_surf, (26, 202))
            lbl_badge = self.font_badge.render("DISPONIBLE", True, INK_MUTED)
        card_surf.blit(lbl_badge, (64, 205))

        # Botón JUGAR acuarela a la derecha
        play_btn = self.btn_play_hover if is_hover else self.btn_play_normal
        card_surf.blit(play_btn, (rect.width - play_btn.get_width() - 24, 196))

        surface.blit(card_surf, rect)

    def _render_boss_card(self, surface: pygame.Surface, mouse_pos: Tuple[int, int]) -> None:
        b_hover = self.boss_card_rect.collidepoint(mouse_pos)
        lift = int(round(self._boss_hover_lift))
        draw_rect = self.boss_card_rect.move(0, lift)

        shadow = pygame.Surface((draw_rect.width + 14, draw_rect.height + 14), pygame.SRCALPHA)
        pygame.draw.rect(
            shadow,
            (98, 62, 32, 75 if not b_hover else 110),
            (7, 8, draw_rect.width, draw_rect.height),
            border_radius=22,
        )
        surface.blit(shadow, (draw_rect.x - 7, draw_rect.y - 4))

        b_surf = self.boss_card_bg.copy()
        # Tinte dorado cálido sutil para destacar el Boss Stage
        tint = pygame.Surface(draw_rect.size, pygame.SRCALPHA)
        tint.fill((255, 224, 130, 52 if b_hover else 34))
        b_surf.blit(tint, (0, 0))
        border_col = (218, 138, 32) if b_hover else (184, 128, 56)
        pygame.draw.rect(b_surf, border_col, (4, 4, draw_rect.width - 8, draw_rect.height - 8), width=3, border_radius=20)

        # Emblema de estrella real (cero emoji roto)
        b_surf.blit(self.emblem_surf, (30, (draw_rect.height - self.emblem_surf.get_height()) // 2))

        txt_boss_t = render_outlined_text(
            self.font_boss_title,
            "ETAPA JEFE: LA GRAN GUACHERNA Y BATALLA DE FLORES",
            (255, 246, 214),
            (116, 56, 18),
            thickness=2,
        )
        b_surf.blit(txt_boss_t, (112, 18))

        txt_boss_d = self.font_boss_desc.render(
            "Desafío multietapa de 15s: Esquiva la maicena, toca la tambora y corona al Rey Momo sin pantallas.",
            True,
            INK_DARK,
        )
        b_surf.blit(txt_boss_d, (114, 62))

        b_surf.blit(
            self.boss_btn_surf,
            (draw_rect.width - self.boss_btn_surf.get_width() - 32, (draw_rect.height - self.boss_btn_surf.get_height()) // 2),
        )

        surface.blit(b_surf, draw_rect)
