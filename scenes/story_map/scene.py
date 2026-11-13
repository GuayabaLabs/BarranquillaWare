import os
import math
import random
from collections import deque
from typing import Optional, Callable, Tuple, Dict, Type, Any, List
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.settings import SettingsManager
from core.map_settings import MapSettingsState
from core.microgame import BaseMicrogame
from core.camera import Camera2D
from ui.button import UIButton
from ui.social_hud import SocialHUD
from ui.side_drawer import SideNavDrawer
from tools.map_dev_tool import MapDevTool, get_bezier_points
from scenes.story_map_data import (
    STORY_CAMPAIGN_ORDER,
    STORY_SECRET_POIS,
    STORY_PLAYABLE_POIS,
    STORY_LEVEL_STAGES,
    PALOMA_STORY_DIALOGS,
)
from scenes.story_map.ui_dialogs import StoryMapUI
from scenes.story_map.ui_dialogs import AvisoTrofeo
from scenes.story_map_data import trofeosMapa, radioGlorieta

from microgames.mallorquin_photo import MallorquinPhotoMicrogame
from microgames.uninorte_sprint import UninorteSprintMicrogame
from microgames.uninorte_concentrate import UninorteConcentrateMicrogame
from microgames.ventana_colores import VentanaColoresMicrogame
from microgames.malecon_rueda import MaleconRuedaMicrogame
from microgames.coaster_launcher import CoasterLauncherState, CoasterCalibrationState
from microgames.metropolitano_penalty import MetropolitanoPenaltyMicrogame
from microgames.metropolitano_moderacion import MetropolitanoModeracionMicrogame
from microgames.aeropuerto_aterrizaje import AeropuertoAterrizajeMicrogame
from microgames.fritanga_84 import Fritanga84Microgame
from microgames.troja_baile import TrojaBaileMicrogame
from microgames.buenavista_cine import BuenavistaCineMicrogame
from microgames.buenavista_trend import BuenavistaTrendMicrogame
from microgames.punch_alert import PunchAlertMicrogame
from microgames.batalla_flores_boss import BatallaFloresBossMicrogame

MICROGAME_MAP: Dict[str, Type[BaseMicrogame]] = {
    "mallorquin": MallorquinPhotoMicrogame,
    "uninorte": UninorteSprintMicrogame,
    "uninorte_sprint": UninorteSprintMicrogame,
    "uninorte_concentrate": UninorteConcentrateMicrogame,
    "ventana": VentanaColoresMicrogame,
    "malecon": CoasterLauncherState,
    "coaster": CoasterLauncherState,
    "metropolitano": MetropolitanoModeracionMicrogame,
    "metropolitano_moderacion": MetropolitanoModeracionMicrogame,
    "metropolitano_penalty": MetropolitanoPenaltyMicrogame,
    "aeropuerto": PunchAlertMicrogame,
    "punch_alert": PunchAlertMicrogame,
    "aeropuerto_aterrizaje": AeropuertoAterrizajeMicrogame,
    "fritanga_84": Fritanga84Microgame,
    "troja_baile": TrojaBaileMicrogame,
    "buenavista": BuenavistaTrendMicrogame,
    "buenavista_cine": BuenavistaCineMicrogame,
    "buenavista_trend": BuenavistaTrendMicrogame,
    "aleta": PunchAlertMicrogame,
    "batalla_flores": BatallaFloresBossMicrogame,
}

# (Constantes STORY_* y PALOMA_STORY_DIALOGS importadas de scenes.story_map_data)
# (Camera2D importada de core.camera)


class StoryMapScene(BaseState):
    """
    Escena interactiva del Mapa de Barranquilla (Modo Historia):
    - Ensambla los 4 cuadrantes oficiales en un mundo continuo (3342x1882).
    - Integra locaciones icónicas (Uninorte) según la referencia visual.
    - Sistema de Nubes Algodonosas Caribeñas (Cozy Clouds) con brisa continua, sombras y parallax.
    - Cámara 2D cinética con paneo suave, arrastre táctil e inercia en toda la pantalla.
    - Paneo cinemático de bienvenida desde la costa hacia el centro urbano.
    - Guardado transparente de progreso en settings.json (personaje y posición de cámara).
    """
    _CACHED_WORLD_MAP: Optional[pygame.Surface] = None
    _CACHED_BASE_WORLD_MAP: Optional[pygame.Surface] = None
    def __init__(
        self,
        character_id: str = "westcol",
        on_back_callback: Optional[Callable[[], None]] = None,
        on_main_menu_callback: Optional[Callable[[BaseState], None]] = None,
    ) -> None:
        super().__init__()
        self.screen_w = 1920
        self.screen_h = 1080
        self.character_id = character_id
        self.on_back_callback = on_back_callback
        self.on_main_menu_callback = on_main_menu_callback

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()
        self.settings = SettingsManager.get_instance()

        # Dimensiones de los cuadrantes
        self.quad_w = 1671
        self.quad_h = 941
        self.world_w = self.quad_w * 2
        self.world_h = self.quad_h * 2

        # Herramienta de desarrollo visual y layout persistente (F1 / config/map_poi_layout.json)
        self.dev_tool = MapDevTool(self.screen_w, self.screen_h, on_layout_changed_callback=self._on_devtool_layout_changed)

        # 1. Ensamblar mapa mundial base y estampar POIs
        self._build_world_map()

        # 2. Inicializar sistema de Clima y Atmósfera (Día, Atardecer, Noche, Lluvia)
        self.weather_modes = ["day", "sunset", "night", "rain"]
        self.current_weather = "day"
        self._init_weather_shaders()

        # 3. Inicializar sistema de Nubes Algodonosas Caribeñas Chiquitas (Cozy Clouds)
        self._init_cozy_clouds()

        # 4. Inicializar Cámara 2D cinética
        self.camera = Camera2D(self.world_w, self.world_h, self.screen_w, self.screen_h)
        self.story_ui = StoryMapUI(self.screen_w, self.screen_h)

        # 5. Paneo cinemático inicial (de Norte costero a Centro urbano)
        self.cinematic_timer: float = 0.0
        self.cinematic_duration: float = 1.2
        self.intro_start_pos = (self.camera.max_x * 0.45, 40.0)
        self.intro_target_pos = (self.camera.max_x * 0.50, self.camera.max_y * 0.50)
        self.camera.set_pos(self.intro_start_pos[0], self.intro_start_pos[1])

        # 6. Timer general y sistema de lluvia
        self.timer: float = 0.0
        self.toast_msg: Optional[str] = None
        self.toast_timer: float = 0.0
        self.font_toast = pygame.font.SysFont("Arial Black, Impact, sans-serif", 24)
        self._init_rain_particles()

        # 7. Sistema de Punto de Interés Clave (Uninorte Key Location Effects)
        self._init_poi_effects()

        # 8. Menú Desplegable / In-Game Pause & Save Drawer
        self._init_drawer_menu()

        # 9. Tarjeta de Misión / Quest Card de Locación
        self._init_quest_card()

        # 10. Sistema de Viñeta Narrativa de Bienvenida y Final del Carnaval
        self._init_narrative_and_carnaval()

        # 11. Sistema de Navegación del Jugador en el Overworld (Opción 1.C y 2.A)
        self._init_player_navigation()
        self.intro_target_pos = (
            max(0.0, min(float(self.camera.max_x), self.player_pos[0] - self.screen_w / 2.0)),
            max(0.0, min(float(self.camera.max_y), self.player_pos[1] - self.screen_h / 2.0))
        )
        self._has_done_intro_pan: bool = False
        self.camera.set_pos(self.intro_target_pos[0], self.intro_target_pos[1])

        # 12. Barra de Navegación Lateral Izquierda y HUD Social Superior
        self.social_hud = SocialHUD(self.screen_w, self.screen_h)
        self.side_drawer = SideNavDrawer(self.screen_w, self.screen_h, on_nav_selected=self._on_side_nav_selected)
        self._sync_social_hud()

        # 13. Trofeos escondidos en las glorietas de la Ventana al Mundo y la Aleta del Tiburón
        self.iniciarTrofeos()

    def _count_completed_campaign_levels(self, completed_microgames: Optional[list] = None) -> int:
        """Cuenta cuántos de los 4 niveles principales de la Historia han sido completados."""
        if completed_microgames is None:
            completed_microgames = self.settings.get_story_progress().get("completed_microgames", [])
        done_set = set(completed_microgames)
        count = 0
        for poi_key in STORY_CAMPAIGN_ORDER:
            stages = STORY_LEVEL_STAGES.get(poi_key, [])
            if stages and all(st["id"] in done_set for st in stages):
                count += 1
        return count

    def _sync_social_hud(self) -> Dict[str, Any]:
        """Sincroniza el SocialHUD con el personaje activo, el puntaje y los niveles superados."""
        progress = self.settings.get_story_progress()
        completed_list = progress.get("completed_microgames", [])
        high_score = int(progress.get("high_score", 0))
        levels_done = self._count_completed_campaign_levels(completed_list)
        if hasattr(self, "social_hud"):
            metricas = self.social_hud.sync_from_story_progress(self.character_id, high_score, levels_done)
            # El contador de logros muestra los trofeos escondidos del mapa
            self.social_hud.set_metric("logros", f"{len(self.leerTrofeosObtenidos())}/{len(trofeosMapa)}")
            return metricas
        return {}

    def _on_side_nav_selected(self, nav_id: str) -> None:
        """Callback ejecutado al seleccionar una opción del SideNavDrawer izquierdo."""
        if nav_id == "mapa":
            # Si se selecciona mapa, enfocar la cámara suavemente en el jugador
            self.camera.target_x = max(0.0, min(float(self.camera.max_x), self.player_pos[0] - self.screen_w / 2.0))
            self.camera.target_y = max(0.0, min(float(self.camera.max_y), self.player_pos[1] - self.screen_h / 2.0))
        elif nav_id == "logros":
            # Muestra la sección de trofeos dentro del panel lateral
            self.side_drawer.mostrarTrofeos()
        else:
            print(f"[StoryMap] Pestaña de navegación seleccionada: {nav_id}")

    def iniciarTrofeos(self) -> None:
        """Prepara los trofeos escondidos del mapa y la ventana que avisa al ganarlos."""
        self.avisoTrofeo = AvisoTrofeo(self.screen_w, self.screen_h)
        # Nodos seguidos que el personaje ha pisado junto a cada monumento
        self.rachaGlorieta = {trofeo["id"]: [] for trofeo in trofeosMapa}
        self.side_drawer.ponerTrofeos(trofeosMapa, self.leerTrofeosObtenidos())
        # El nodo donde arranca también cuenta como inicio de la vuelta
        self.revisarVueltaGlorieta(self.player_node_id)

    def leerTrofeosObtenidos(self) -> list:
        return list(self.settings.get("trofeosObtenidos", []))

    def revisarVueltaGlorieta(self, idNodo: int) -> None:
        """Cuenta los nodos seguidos junto a cada monumento y entrega el trofeo al cerrar la vuelta."""
        nodos, aristas, mapaNodos, vecinos, mapaAristas = self._get_street_graph()
        nodo = mapaNodos.get(idNodo)
        if nodo is None:
            return

        obtenidos = self.leerTrofeosObtenidos()
        for trofeo in trofeosMapa:
            monumento = self.poi_registry.get(trofeo["monumento"])
            if not monumento:
                continue
            centro = monumento["rect"].center
            racha = self.rachaGlorieta[trofeo["id"]]

            # Si se aleja del monumento, la cuenta vuelve a empezar
            if math.hypot(nodo["x"] - centro[0], nodo["y"] - centro[1]) > radioGlorieta:
                racha.clear()
                continue

            racha.append(idNodo)
            if len(racha) > 12:
                racha.pop(0)
            if trofeo["id"] in obtenidos:
                continue

            # La vuelta se cierra al volver a un nodo ya pisado después de pasar por otros tres
            for i in range(len(racha) - 2, -1, -1):
                if racha[i] == idNodo:
                    vuelta = racha[i:-1]
                    if len(set(vuelta)) >= 4:
                        self.ganarTrofeo(trofeo)
                    break

    def ganarTrofeo(self, trofeo: dict) -> None:
        """Guarda el trofeo ganado y abre la ventana de ¡Qué nota!"""
        obtenidos = self.leerTrofeosObtenidos()
        if trofeo["id"] in obtenidos:
            return
        obtenidos.append(trofeo["id"])
        self.settings.set("trofeosObtenidos", obtenidos)
        self.side_drawer.ponerTrofeos(trofeosMapa, obtenidos)
        self._sync_social_hud()
        self.avisoTrofeo.abrir(trofeo["nombre"], self.side_drawer.centroPestana())

    def _build_world_map(self) -> None:
        """Carga y une los 4 cuadrantes, reutilizando la superficie cacheada si ya fue ensamblada."""
        if StoryMapScene._CACHED_WORLD_MAP is not None and StoryMapScene._CACHED_BASE_WORLD_MAP is not None:
            self.base_world_map = StoryMapScene._CACHED_BASE_WORLD_MAP.copy()
            self.world_map = StoryMapScene._CACHED_WORLD_MAP.copy()
            # Calcular y asignar rectángulos de los POIs
            self._calc_all_poi_rects()
            return

        self.world_map = pygame.Surface((self.world_w, self.world_h))

        quad_names = [
            ("primer", 0, 0),
            ("segundo", self.quad_w, 0),
            ("tercer", 0, self.quad_h),
            ("cuarto", self.quad_w, self.quad_h)
        ]

        for name, gx, gy in quad_names:
            surf = self.assets.load_surface(f"{name}_cuadrante_mapa.png", has_alpha=False)
            if surf.get_size() != (self.quad_w, self.quad_h):
                surf = pygame.transform.smoothscale(surf, (self.quad_w, self.quad_h))
            self.world_map.blit(surf, (gx, gy))

        # Maquillaje y reparación cosmética de costuras en los cuadrantes
        if hasattr(self, "_repair_quadrant_seams"):
            self._repair_quadrant_seams()

        # Guardar copia base inmaculada antes de estampar POIs
        self.base_world_map = self.world_map.copy()

        # Renderizar tinte shader de calles antes de estampar POIs
        self._render_street_shader()

        # Integrar ubicaciones mejoradas desde assets oficiales y layout configurable
        self._stamp_all_pois()

        # Guardar en caché estática de clase para reingresos instantáneos
        StoryMapScene._CACHED_BASE_WORLD_MAP = self.base_world_map.copy()
        StoryMapScene._CACHED_WORLD_MAP = self.world_map.copy()

    def _calc_all_poi_rects(self) -> None:
        """Calcula rápidamente los bounding rects de cada POI sin re-estampar texturas."""
        for key, asset, dx, dy, dw, dh, _scol, _soff in self.POI_SPECS:
            cfg = self.dev_tool.get_poi_config(key) if hasattr(self, "dev_tool") else {}
            tw = max(40, cfg.get("width", dw))
            # Proporción estimada por default o config
            th = int(dh * (tw / float(dw))) if dw > 0 else dh
            bx = cfg.get("x", dx)
            by = cfg.get("y", dy)
            cx = bx + tw // 2
            cy = by + th // 2
            rect = pygame.Rect(0, 0, tw, th)
            rect.center = (cx, cy)
            setattr(self, f"{key}_rect", rect)

    def _on_devtool_layout_changed(self) -> None:
        """Re-estampa dinámicamente el mapa mundial cuando se mueve o escala un POI en DevTool."""
        if not hasattr(self, "base_world_map") or self.base_world_map is None:
            return
        self.world_map = self.base_world_map.copy()
        self._render_street_shader()
        self._stamp_all_pois()
        StoryMapScene._CACHED_WORLD_MAP = self.world_map.copy()
        # Actualizar rectángulos en el registro central
        if hasattr(self, "poi_registry"):
            for p_key in self.poi_registry:
                attr = f"{p_key}_rect"
                if hasattr(self, attr):
                    self.poi_registry[p_key]["rect"] = getattr(self, attr)
        # Sincronizar posición del jugador con el nodo en DevTool si no está en movimiento
        if hasattr(self, "player_node_id") and not getattr(self, "player_is_moving", False):
            nodes, _, node_map, _, _ = self._get_street_graph()
            if self.player_node_id in node_map:
                curr_n = node_map[self.player_node_id]
                self.player_pos = (float(curr_n["x"]), float(curr_n["y"]))

    def _render_street_shader(self) -> None:
        """
        Renderiza el tinte translúcido de la red vial a lo largo de las curvas Bézier
        trazadas en DevTool (con soporte para bifurcaciones, ramas, nodos medios y túneles).
        """
        if hasattr(self, "dev_tool"):
            nodes = self.dev_tool.nodes
            edges = self.dev_tool.edges
            shader_cfg = self.dev_tool.street_shader
        else:
            net = self.layout_data.get("street_network", {})
            nodes = net.get("nodes", [])
            edges = net.get("edges", [])
            shader_cfg = self.layout_data.get("street_shader", {"color": [245, 185, 55], "alpha": 120, "width": 26})

        if not nodes or not edges:
            return

        node_map = {n["id"]: n for n in nodes}
        color = tuple(shader_cfg.get("color", [245, 185, 55]))
        alpha = int(shader_cfg.get("alpha", 120))
        width = int(shader_cfg.get("width", 26))

        from tools.map_dev_tool import get_bezier_points

        street_surf = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)

        for edge in edges:
            p0 = node_map.get(edge["from"])
            p1 = node_map.get(edge["to"])
            if not p0 or not p1:
                continue

            pc = (edge.get("ctrl_x", (p0["x"] + p1["x"]) // 2), edge.get("ctrl_y", (p0["y"] + p1["y"]) // 2))
            pts = get_bezier_points((p0["x"], p0["y"]), pc, (p1["x"], p1["y"]), step_px=6)
            if len(pts) > 1:
                is_hid = edge.get("hidden", False)
                seg_col = (130, 75, 190, max(30, alpha - 30)) if is_hid else (color[0], color[1], color[2], alpha)

                pygame.draw.lines(street_surf, (20, 25, 40, int(alpha * 0.35)), False, pts, width + 4)
                pygame.draw.lines(street_surf, seg_col, False, pts, width)
                for pt in pts:
                    pygame.draw.circle(street_surf, seg_col, pt, width // 2)

        self.world_map.blit(street_surf, (0, 0))

    def is_segment_hidden(self, edge_idx: int) -> bool:
        """Retorna si el tramo entre nodos está marcado como túnel oculto (para evitar colisión de Y-sort)."""
        edges = self.dev_tool.edges if hasattr(self, "dev_tool") else []
        if 0 <= edge_idx < len(edges):
            return bool(edges[edge_idx].get("hidden", False))
        return False

    def _stamp_poi(
        self,
        asset_filename: str,
        poi_key: str,
        default_x: int,
        default_y: int,
        default_w: int,
        shadow_color: Tuple[int, int, int, int] = (20, 35, 55, 45),
        shadow_offset: Tuple[int, int] = (8, 12)
    ) -> pygame.Rect:
        """
        Escala, rota y estampa un POI sobre el mapa mundial preservando su centro geométrico,
        generando silueta de sombra proyectada rápida con pygame.mask.
        """
        surf = self.assets.load_surface(asset_filename, has_alpha=True)
        mask = pygame.mask.from_surface(surf)
        rects = mask.get_bounding_rects()
        tight_surf = surf.subsurface(rects[0]) if rects else surf

        cfg = self.dev_tool.get_poi_config(poi_key) if hasattr(self, "dev_tool") else {}
        target_w = max(40, cfg.get("width", default_w))
        target_h = max(20, int(tight_surf.get_height() * (target_w / float(tight_surf.get_width()))))
        scaled_surf = pygame.transform.smoothscale(tight_surf, (target_w, target_h))

        # Rotación (ángulo en grados: positivo = sentido horario)
        angle = float(cfg.get("angle", 0.0))
        if abs(angle) > 0.01:
            rotated_surf = pygame.transform.rotate(scaled_surf, -angle)
        else:
            rotated_surf = scaled_surf

        # Anclaje y preservación del centro
        base_x = cfg.get("x", default_x)
        base_y = cfg.get("y", default_y)
        cx = base_x + target_w // 2
        cy = base_y + target_h // 2
        final_rect = rotated_surf.get_rect(center=(cx, cy))

        # Sombra proyectada con silueta rápida basada en máscara nativa SDL
        try:
            m = pygame.mask.from_surface(rotated_surf, 40)
            shadow_shape = m.to_surface(setcolor=shadow_color, unsetcolor=(0, 0, 0, 0))
            self.world_map.blit(shadow_shape, (final_rect.x + shadow_offset[0], final_rect.y + shadow_offset[1]))
        except Exception:
            pass

        # Estampar POI
        self.world_map.blit(rotated_surf, final_rect.topleft)
        return final_rect

    POI_SPECS = [
        ("mallorquin", "parque_mallorquin_mapa.png", 266, 81, 672, 445, (20, 35, 55, 42), (8, 12)),
        ("uninorte", "uninorte_mapa.png", 145, 505, 390, 270, (25, 40, 60, 48), (10, 14)),
        ("buenavista", "buenavista_mallplaza_mapa.png", 860, 380, 460, 307, (25, 35, 55, 45), (10, 14)),
        ("ventana", "ventana_al_mundo_mapa.png", 1772, 275, 245, 290, (20, 30, 50, 48), (8, 12)),
        ("malecon", "luna_del_rio_mapa.png", 2780, 460, 350, 385, (15, 35, 65, 55), (10, 14)),
        ("aleta", "aleta_del_tiburon_mapa.png", 2680, 720, 260, 365, (20, 30, 50, 48), (8, 12)),
        ("metropolitano", "metropolitano_mapa.png", 1725, 1154, 440, 288, (20, 30, 50, 48), (10, 14)),
        ("aeropuerto", "aeropuerto_ernesto_cortissoz_mapa.png", 2611, 1311, 540, 353, (20, 30, 50, 48), (10, 14)),
    ]

    def _stamp_all_pois(self) -> None:
        """Estampa todos los POIs configurables sobre el mapa mundial actual."""
        for key, asset, dx, dy, dw, dh, scol, soff in self.POI_SPECS:
            try:
                rect = self._stamp_poi(asset, key, dx, dy, dw, shadow_color=scol, shadow_offset=soff)
            except Exception as e:
                print(f"Aviso: no se pudo cargar {asset}: {e}")
                rect = pygame.Rect(dx, dy, dw, dh)
            setattr(self, f"{key}_rect", rect)

    def _repair_quadrant_seams(self) -> None:
        """
        Maquilla y repara a nivel de pixel las discontinuidades en las costuras de los cuadrantes:
        - Spot 1 (Calle diagonal Y=941): realinea los faroles cortados y suaviza el asfalto.
        - Spot 2 (Cruce de los 4 cuadrantes X=1671, Y=941): florece la copa del guayacan rosado unificando las 4 esquinas.
        - Spot 3 (Glorieta este Y=941, X=2567): conecta y endereza el farol de la glorieta.
        """
        qh = self.quad_h
        qw = self.quad_w

        def _draw_cozy_street_lamp(surf: pygame.Surface, cx: int, cy: int) -> None:
            # 1. Sombra eliptica en el suelo
            shadow = pygame.Surface((24, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (20, 25, 35, 90), (0, 0, 24, 10))
            surf.blit(shadow, (cx - 12, cy - 5))

            # 2. Base redonda del poste
            pygame.draw.ellipse(surf, (15, 18, 24), (cx - 7, cy - 6, 14, 8))
            pygame.draw.ellipse(surf, (35, 42, 54), (cx - 5, cy - 5, 10, 5))

            # 3. Poste de hierro forjado vertical
            pole_h = 36
            pole_top_y = cy - pole_h
            pygame.draw.rect(surf, (15, 18, 24), (cx - 3, pole_top_y, 6, pole_h))
            pygame.draw.line(surf, (45, 55, 70), (cx - 1, pole_top_y), (cx - 1, cy - 2), 2)
            pygame.draw.rect(surf, (15, 18, 24), (cx - 4, cy - 18, 8, 3))
            pygame.draw.rect(surf, (45, 55, 70), (cx - 3, cy - 17, 6, 1))

            # 4. Soporte / Mensula de la linterna
            pygame.draw.polygon(surf, (15, 18, 24), [
                (cx - 6, pole_top_y),
                (cx + 6, pole_top_y),
                (cx + 4, pole_top_y + 3),
                (cx - 4, pole_top_y + 3)
            ])

            # 5. Linterna de cristal amarillo luminoso
            lantern_h = 20
            lantern_top_y = pole_top_y - lantern_h
            glow = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 230, 100, 55), (16, 16), 15)
            surf.blit(glow, (cx - 16, lantern_top_y - 4))

            # Carcasa de cristal amarillo
            pygame.draw.polygon(surf, (15, 18, 24), [
                (cx - 9, lantern_top_y),
                (cx + 9, lantern_top_y),
                (cx + 6, pole_top_y),
                (cx - 6, pole_top_y)
            ])
            pygame.draw.polygon(surf, (255, 225, 40), [
                (cx - 7, lantern_top_y + 2),
                (cx + 7, lantern_top_y + 2),
                (cx + 4, pole_top_y - 1),
                (cx - 4, pole_top_y - 1)
            ])
            pygame.draw.polygon(surf, (255, 250, 150), [
                (cx - 3, lantern_top_y + 4),
                (cx + 3, lantern_top_y + 4),
                (cx + 1, pole_top_y - 3),
                (cx - 1, pole_top_y - 3)
            ])

            # 6. Techo conico azul/cian
            roof_top_y = lantern_top_y - 10
            pygame.draw.polygon(surf, (15, 18, 24), [
                (cx - 10, lantern_top_y + 1),
                (cx + 10, lantern_top_y + 1),
                (cx, roof_top_y - 2)
            ])
            pygame.draw.polygon(surf, (30, 95, 140), [
                (cx - 8, lantern_top_y),
                (cx + 8, lantern_top_y),
                (cx, roof_top_y)
            ])
            pygame.draw.polygon(surf, (60, 160, 210), [
                (cx - 3, lantern_top_y),
                (cx + 1, lantern_top_y),
                (cx, roof_top_y + 2)
            ])
            pygame.draw.line(surf, (15, 18, 24), (cx, roof_top_y - 2), (cx, roof_top_y - 7), 2)
            pygame.draw.circle(surf, (15, 18, 24), (cx, roof_top_y - 7), 2)

        # 1. Spot 1: Faroles y asfalto en la avenida diagonal (Y = qh = 941)
        # Suavizado del escalon de asfalto y lineas de carril
        for y in range(qh - 2, qh + 3):
            for x in range(1142, 1230):
                c_top = self.world_map.get_at((x, qh - 3))
                c_bot = self.world_map.get_at((x, qh + 3))
                blend = ((c_top[0] + c_bot[0]) // 2, (c_top[1] + c_bot[1]) // 2, (c_top[2] + c_bot[2]) // 2)
                self.world_map.set_at((x, y), blend)

        # Linea divisoria central amarilla continua
        pygame.draw.line(self.world_map, (250, 220, 30), (1178, qh - 6), (1188, qh + 6), 3)

        # Farol izquierdo Spot 1 (alineado con linterna en 1071 y base en 1078)
        _draw_cozy_street_lamp(self.world_map, 1076, 966)
        # Farol derecho Spot 1 (alineado con linterna en 1269 y base en 1279)
        _draw_cozy_street_lamp(self.world_map, 1278, 969)

        # 2. Spot 2: Arbol Guayacan Rosa y Follaje verde en el cruce de los 4 cuadrantes (qw, qh)
        green_foliage = [
            (qw - 18, qh - 38, 22, (55, 150, 40)),
            (qw + 18, qh - 40, 20, (65, 165, 45)),
            (qw, qh - 48, 24, (50, 140, 35)),
            (qw - 2, qh - 28, 26, (70, 175, 50)),
        ]
        for gx, gy, gr, _ in green_foliage:
            pygame.draw.circle(self.world_map, (25, 45, 20), (gx, gy), gr + 3)
        for gx, gy, gr, gcol in green_foliage:
            pygame.draw.circle(self.world_map, gcol, (gx, gy), gr)
            pygame.draw.circle(self.world_map, (min(255, gcol[0] + 30), min(255, gcol[1] + 30), min(255, gcol[2] + 20)), (gx - 3, gy - 3), int(gr * 0.55))

        petals = [
            (qw - 16, qh - 6, 20, (245, 115, 185)),
            (qw + 18, qh - 8, 22, (255, 135, 200)),
            (qw - 4, qh + 8, 24, (235, 100, 175)),
            (qw + 12, qh + 12, 19, (248, 125, 190)),
            (qw - 22, qh + 2, 18, (225, 85, 165)),
            (qw + 4, qh - 2, 16, (255, 175, 220)),
            (qw - 6, qh - 14, 18, (255, 145, 205)),
            (qw + 22, qh + 2, 16, (240, 110, 180)),
            (qw, qh + 2, 18, (255, 190, 230))
        ]
        for px, py, r, _ in petals:
            pygame.draw.circle(self.world_map, (35, 25, 45), (px, py), r + 2)
        for px, py, r, col in petals:
            pygame.draw.circle(self.world_map, col, (px, py), r)
            pygame.draw.circle(self.world_map, (min(255, col[0] + 35), min(255, col[1] + 35), min(255, col[2] + 35)), (px - 3, py - 3), int(r * 0.55))

        # Tronco central y raices
        pygame.draw.line(self.world_map, (25, 15, 10), (qw - 1, qh + 18), (qw + 1, qh + 46), 7)
        pygame.draw.line(self.world_map, (95, 45, 25), (qw - 1, qh + 18), (qw + 1, qh + 46), 4)
        pygame.draw.line(self.world_map, (25, 15, 10), (qw, qh + 44), (qw - 8, qh + 50), 4)
        pygame.draw.line(self.world_map, (25, 15, 10), (qw, qh + 44), (qw + 9, qh + 50), 4)

        # 3. Spot 3: Farol en la glorieta este (X=2567, Y=941)
        _draw_cozy_street_lamp(self.world_map, 2567, 967)

    def _init_poi_effects(self) -> None:
        """Inicializa el registro y efectos interactivos de todos los puntos de interés clave."""
        # Registro centralizado de Puntos de Interés (POIs) y sus microjuegos
        self.poi_registry = {
            "mallorquin": {
                "title": "ECORRESERVA MALLORQUÍN",
                "district": "DISTRITO ECOLÓGICO",
                "microgame_id": "mallorquin_photo",
                "microgame_title": "ECORRESERVA MALLORQUÍN",
                "desc": [
                    "Paseo contemplativo junto a la ciénaga y el mar Caribe.",
                    "Observa las aves sin prisa y disfruta la brisa costera."
                ],
                "rect": self.mallorquin_rect
            },
            "uninorte": {
                "title": "CAMPUS UNINORTE",
                "district": "NIVEL 1 • DISTRITO ACADÉMICO",
                "microgame_id": "uninorte_sprint",
                "microgame_title": "RONDAS: PASILLO + BIBLIOTECA",
                "desc": [
                    "Ronda 1: Cruza el pasillo hacia el salón sin distraerte con el celular.",
                    "Ronda 2: Despeja las notificaciones en la biblioteca para estudiar en paz."
                ],
                "rect": self.uninorte_rect
            },
            "ventana": {
                "title": "VENTANA AL MUNDO",
                "district": "DISTRITO MONUMENTAL",
                "microgame_id": "ventana_colores",
                "microgame_title": "VENTANA AL MUNDO",
                "desc": [
                    "Monumento icónico de colores frente a la brisa del norte.",
                    "Un rincón colorido para admirar el horizonte currambero."
                ],
                "rect": self.ventana_rect
            },
            "malecon": {
                "title": "GRAN MALECÓN DEL RÍO",
                "district": "DISTRITO TURÍSTICO",
                "microgame_id": "coaster",
                "microgame_title": "COASTER · CALIBRA EL LÁPIZ",
                "desc": [
                    "Atardecer dorado frente al río Magdalena.",
                    "Camina tranquilo sintiendo la brisa del río."
                ],
                "rect": self.malecon_rect
            },
            "metropolitano": {
                "title": "ESTADIO METROPOLITANO",
                "district": "NIVEL 3 • DISTRITO DEPORTIVO",
                "microgame_id": "metropolitano_moderacion",
                "microgame_title": "¡MODERA LA BARRA BRAVA!",
                "desc": [
                    "Cuida el ambiente de la tribuna en la pantalla gigante del estadio.",
                    "Usa FLECHAS y ESPACIO para moderar a los hinchas tóxicos con empatía."
                ],
                "rect": self.metropolitano_rect
            },
            "buenavista": {
                "title": "C.C. BUENAVISTA & MALLPLAZA",
                "district": "NIVEL 2 • DISTRITO COMERCIAL",
                "microgame_id": "buenavista_trend",
                "microgame_title": "EL TREND EN BUENAVISTA",
                "desc": [
                    "Sigue el ritmo de la bachata viral con las teclas D, F, J y K.",
                    "Baila con alegría y conserva tus 3 corazones sin presión por los likes."
                ],
                "rect": self.buenavista_rect
            },
            "aleta": {
                "title": "ALETA DEL TIBURÓN",
                "district": "VENTANA DE CAMPEONES",
                "microgame_id": "aleta_campeones",
                "microgame_title": "ALETA DEL TIBURÓN",
                "desc": [
                    "Homenaje brillante a la pasión rojiblanca junto al río.",
                    "Un mirador sereno para descansar en el recorrido."
                ],
                "rect": self.aleta_rect
            },
            "aeropuerto": {
                "title": "AEROPUERTO CORTISSOZ",
                "district": "NIVEL 4 • DISTRITO AÉREO",
                "microgame_id": "punch_alert",
                "microgame_title": "¡DESPACHA EL SPAM!",
                "desc": [
                    "Antes de despegar, limpia tu pantalla de ventanas emergentes y spam.",
                    "Viaja ligero de equipaje digital para cerrar tu aventura en calma."
                ],
                "rect": self.aeropuerto_rect
            },
            "batalla_flores": {
                "title": "¡BATALLA DE FLORES!",
                "district": "VÍA 40",
                "microgame_id": "batalla_flores_boss",
                "microgame_title": "¡BATALLA DE FLORES!",
                "desc": [
                    "Gran desfile folclórico de celebración en la Vía 40."
                ],
                "rect": pygame.Rect(self.quad_w - 120, self.quad_h - 120, 240, 240)
            }
        }

        # Banderas de hover para cada POI
        for p_key in self.poi_registry.keys():
            setattr(self, f"{p_key}_hover", False)

        self.active_poi: str = "uninorte"

        # 1. Halo / Resplandor elíptico en el suelo
        w, h = 480, 280
        self.poi_ground_glow = pygame.Surface((w, h), pygame.SRCALPHA)
        cw, ch = w // 2, h // 2 + 18
        for r in range(110, 0, -6):
            f = 1.0 - (r / 110.0)
            alpha = int(72 * f * f)
            pygame.draw.ellipse(self.poi_ground_glow, (255, 205, 80, alpha), (cw - r * 1.5, ch - r * 0.65, r * 3.0, r * 1.3))

        # 2. Pin / Diamante dorado estilizado de ubicación clave
        pin_w, pin_h = 36, 44
        self.poi_pin_surf = pygame.Surface((pin_w, pin_h), pygame.SRCALPHA)
        pts = [(pin_w // 2, 4), (pin_w - 6, pin_h // 2 - 2), (pin_w // 2, pin_h - 6), (6, pin_h // 2 - 2)]
        pygame.draw.polygon(self.poi_pin_surf, (255, 215, 75), pts)
        pygame.draw.polygon(self.poi_pin_surf, (255, 248, 175), [(pin_w // 2, 8), (pin_w - 10, pin_h // 2 - 2), (pin_w // 2, pin_h // 2 - 2), (pin_w // 2, 8)])
        pygame.draw.polygon(self.poi_pin_surf, (175, 120, 25), pts, width=2)
        pygame.draw.circle(self.poi_pin_surf, (255, 255, 255, 230), (pin_w // 2 - 3, pin_h // 2 - 6), 3)

        # 2B. Estrella Dorada de Nivel Despejado / Completado
        star_w, star_h = 44, 44
        self.poi_star_surf = pygame.Surface((star_w, star_h), pygame.SRCALPHA)
        cx, cy = star_w // 2, star_h // 2
        pts_star = []
        for i in range(10):
            r = 20 if i % 2 == 0 else 9
            angle = -math.pi / 2 + i * (math.pi / 5)
            pts_star.append((cx + int(math.cos(angle) * r), cy + int(math.sin(angle) * r)))
        pygame.draw.polygon(self.poi_star_surf, (255, 215, 60), pts_star)
        pygame.draw.polygon(self.poi_star_surf, (255, 250, 180), pts_star, width=2)
        pygame.draw.polygon(self.poi_star_surf, (180, 120, 20), pts_star, width=1)
        pygame.draw.circle(self.poi_star_surf, (255, 255, 255), (cx, cy), 4)

        # 3. Chispitas doradas flotantes para cada locación
        self._sp_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        self.poi_sparkles = {}
        for p_key, p_info in self.poi_registry.items():
            r = p_info["rect"]
            self.poi_sparkles[p_key] = []
            for _ in range(7):
                self.poi_sparkles[p_key].append({
                    "rel_x": random.uniform(30, max(40, r.width - 30)),
                    "rel_y": random.uniform(40, max(50, r.height)),
                    "vy": random.uniform(22, 38),
                    "phase": random.uniform(0, math.pi * 2),
                    "size": random.uniform(3.5, 6.0),
                    "life": random.uniform(0.0, 1.0)
                })

    def _init_weather_shaders(self) -> None:
        """Pre-genera los overlays de atmósfera para el ciclo Día / Atardecer / Noche / Lluvia."""
        # Overlays optimizados a tamaño de pantalla (1920x1080)
        self.weather_overlays = {
            "day": None,
            "sunset": pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA),
            "night": pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA),
            "rain": pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA),
        }
        # Atardecer cálido ambarino (Golden Hour del Malecón)
        self.weather_overlays["sunset"].fill((255, 138, 48, 52))

        # Noche caribeña azul medianoche
        self.weather_overlays["night"].fill((18, 28, 68, 118))

        # Lluvia tropical fresca
        self.weather_overlays["rain"].fill((55, 82, 115, 65))

    def _init_rain_particles(self) -> None:
        """Inicializa partículas livianas de lluvia tropical caribeña en pantalla."""
        import random
        self.rain_drops = []
        for _ in range(120):
            self.rain_drops.append({
                "x": random.uniform(0, self.screen_w),
                "y": random.uniform(0, self.screen_h),
                "speed": random.uniform(850, 1150),
                "length": random.uniform(14, 24),
                "alpha": random.randint(110, 180)
            })

    def _init_cozy_clouds(self) -> None:
        """Genera nubes algodonosas chiquitas y variadas repartidas armónicamente por todo el mapa."""
        def make_cloud(scale: float, alpha: int = 210) -> pygame.Surface:
            w, h = int(360 * scale), int(180 * scale)
            surf = pygame.Surface((w + 30, h + 30), pygame.SRCALPHA)
            circles = [
                (int(90 * scale), int(105 * scale), int(58 * scale)),
                (int(175 * scale), int(78 * scale), int(82 * scale)),
                (int(260 * scale), int(100 * scale), int(64 * scale)),
                (int(135 * scale), int(115 * scale), int(52 * scale)),
                (int(215 * scale), int(115 * scale), int(52 * scale)),
            ]
            # Sombra proyectada suave
            for cx, cy, r in circles:
                pygame.draw.circle(surf, (30, 45, 75, int(alpha * 0.22)), (cx + 12, cy + 18), r)
            # Cuerpo blanco esponjoso
            for cx, cy, r in circles:
                pygame.draw.circle(surf, (255, 255, 255, alpha), (cx, cy), r)
                # Resalte cálido superior
                pygame.draw.circle(surf, (255, 245, 250, int(alpha * 0.7)), (cx, cy - 3), int(r * 0.82))
            return surf

        qw, qh = self.quad_w, self.quad_h
        # 14 nubes más chiquitas distribuidas en cuadrantes y uniones
        self.clouds = [
            # Litoral Norte y Mar Caribe
            {"surf": make_cloud(0.58), "x": 260.0, "y": 80.0, "vx": 12.0, "parallax": 1.15, "bob": 0.0},
            {"surf": make_cloud(0.44), "x": 880.0, "y": 120.0, "vx": 9.5, "parallax": 1.10, "bob": 1.2},
            {"surf": make_cloud(0.64), "x": 1580.0, "y": 70.0, "vx": 14.0, "parallax": 1.18, "bob": 2.1},
            {"surf": make_cloud(0.48), "x": 2320.0, "y": 95.0, "vx": 11.0, "parallax": 1.12, "bob": 3.4},
            # Centro urbano y costuras de unión (Camuflaje de Spots con cortes de faroles y árbol)
            {"surf": make_cloud(0.68), "x": 1040.0, "y": float(qh - 45), "vx": 4.5, "parallax": 1.12, "bob": 0.5},   # Spot 1: Faroles calle diagonal
            {"surf": make_cloud(0.72), "x": float(qw - 30), "y": float(qh - 30), "vx": 3.0, "parallax": 1.14, "bob": 1.8}, # Spot 2: Árbol rosa central
            {"surf": make_cloud(0.65), "x": 2585.0, "y": float(qh - 40), "vx": 4.0, "parallax": 1.11, "bob": 2.6},   # Spot 3: Farola glorieta este
            {"surf": make_cloud(0.48), "x": float(qw + 230), "y": float(qh + 140), "vx": 10.5, "parallax": 1.11, "bob": 1.9},
            {"surf": make_cloud(0.55), "x": float(qw - 280), "y": float(qh + 160), "vx": 11.5, "parallax": 1.14, "bob": 2.7},
            # Este (Río Magdalena y Malecón)
            {"surf": make_cloud(0.60), "x": 2620.0, "y": 490.0, "vx": 12.5, "parallax": 1.15, "bob": 1.5},
            {"surf": make_cloud(0.50), "x": 2980.0, "y": 740.0, "vx": 13.5, "parallax": 1.12, "bob": 3.0},
            # Sur (Estadio Metropolitano y Aeropuerto)
            {"surf": make_cloud(0.62), "x": 1860.0, "y": 1340.0, "vx": 11.5, "parallax": 1.16, "bob": 0.5},
            {"surf": make_cloud(0.46), "x": 1220.0, "y": 1470.0, "vx": 9.0, "parallax": 1.10, "bob": 2.3},
            {"surf": make_cloud(0.52), "x": 2560.0, "y": 1510.0, "vx": 12.0, "parallax": 1.13, "bob": 3.8},
            {"surf": make_cloud(0.40), "x": 480.0, "y": 1370.0, "vx": 8.0, "parallax": 1.08, "bob": 1.1},
        ]

    def _init_drawer_menu(self) -> None:
        """Inicializa el menú desplegable (Drawer lateral) de pausa, ajustes y guardado."""
        self.menu_open: bool = False
        self.menu_anim_t: float = 0.0
        self.drawer_w: int = 440
        self.save_feedback_timer: float = 0.0

        # Tipografías del Drawer
        self.font_drawer_title = pygame.font.SysFont("Arial Black, Impact, sans-serif", 22)
        self.font_drawer_btn = pygame.font.SysFont("Arial, sans-serif", 17, bold=True)
        self.font_drawer_sub = pygame.font.SysFont("Arial, sans-serif", 14)
        self.font_drawer_save = pygame.font.SysFont("Arial Black, Impact, sans-serif", 15)

        # 1. Botón circular flotante para abrir/cerrar el menú (esquina superior derecha)
        btn_toggle_surf = pygame.Surface((56, 56), pygame.SRCALPHA)
        pygame.draw.circle(btn_toggle_surf, (16, 24, 40, 220), (28, 28), 27)
        pygame.draw.circle(btn_toggle_surf, (240, 195, 95, 230), (28, 28), 27, 2)
        # Tres barras de menú hamburguesa
        for bar_y in [18, 28, 38]:
            pygame.draw.line(btn_toggle_surf, (255, 250, 240), (16, bar_y), (40, bar_y), 3)

        self.btn_menu_toggle = UIButton(
            center_pos=(1855, 55),
            normal_sprite=btn_toggle_surf,
            on_click=self._toggle_menu
        )

        # 2. Generador de superficies para botones del menú
        def make_drawer_btn(text: str, bg_color: Tuple[int, int, int], border_color: Tuple[int, int, int]) -> pygame.Surface:
            bw, bh = 340, 52
            surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(surf, (*bg_color, 245), (0, 0, bw, bh), border_radius=14)
            pygame.draw.rect(surf, (*border_color, 255), (0, 0, bw, bh), width=2, border_radius=14)
            txt = self.font_drawer_btn.render(text, True, (255, 255, 255))
            surf.blit(txt, txt.get_rect(center=(bw // 2, bh // 2)))
            return surf

        self.btn_resume = UIButton(
            center_pos=(220, 290),
            normal_sprite=make_drawer_btn("REANUDAR", (30, 55, 90), (80, 160, 230)),
            on_click=self._toggle_menu
        )

        self.btn_save_game = UIButton(
            center_pos=(220, 365),
            normal_sprite=make_drawer_btn("GUARDAR PARTIDA", (40, 75, 45), (100, 215, 120)),
            on_click=self._on_save_clicked
        )

        self.btn_exit_map = UIButton(
            center_pos=(220, 680),
            normal_sprite=make_drawer_btn("SALIR AL MENÚ", (75, 30, 30), (230, 95, 90)),
            on_click=self._on_exit_clicked
        )

        self.btn_calibrate_pointer = UIButton(
            center_pos=(220, 520),
            normal_sprite=make_drawer_btn("CALIBRAR LÁPIZ", (65, 55, 105), (160, 140, 235)),
            on_click=self._on_calibrate_pointer
        )

        self.btn_settings = UIButton(
            center_pos=(220, 600),
            normal_sprite=make_drawer_btn("AJUSTES", (55, 75, 105), (120, 180, 230)),
            on_click=self._on_open_settings
        )

        # Botones de audio tipo toggle dentro del Drawer
        audio_frames = self.assets.get_audio_button_frames(target_size=64)
        self.btn_drawer_music = UIButton(
            center_pos=(160, 440),
            normal_sprite=audio_frames[0],
            alt_sprite=audio_frames[1],
            is_toggle=True,
            initial_toggle_state=self.audio.music_enabled,
            on_click=self.audio.toggle_music
        )
        self.btn_drawer_sound = UIButton(
            center_pos=(280, 440),
            normal_sprite=audio_frames[2],
            alt_sprite=audio_frames[3],
            is_toggle=True,
            initial_toggle_state=self.audio.sound_enabled,
            on_click=self.audio.toggle_sound
        )

        self.drawer_buttons = [
            self.btn_resume,
            self.btn_save_game,
            self.btn_drawer_music,
            self.btn_drawer_sound,
            self.btn_calibrate_pointer,
            self.btn_settings,
            self.btn_exit_map
        ]

        # Aspecto nuevo del menú: ventana de flores, botones morados y letra del juego de la montaña rusa
        self.prepararMenuMapa()


    def _init_narrative_and_carnaval(self) -> None:
        """Inicializa las viñetas de introducción, diálogos cozy de la Paloma y celebración del Carnaval."""
        self.show_intro_dialog: bool = False
        self.intro_dialog_shown: bool = False
        self.show_victory_modal: bool = False
        self.victory_modal_shown: bool = False

        # Estado del Sistema de Diálogos de la Paloma (Cozy Watercolor Dialogs)
        self.paloma_dialog_open: bool = False
        self.paloma_dialog_anim_t: float = 0.0
        self.paloma_dialog_speaker: str = "PALOMA DE CURRAMBA"
        self.paloma_dialog_badge: str = ""
        self.paloma_dialog_pages: list = []
        self.paloma_dialog_page_idx: int = 0
        self.paloma_dialog_on_finish: Optional[Callable[[], None]] = None

        # Estado de encadenamiento de rondas por nivel (Uninorte y Buenavista tienen 2 rondas)
        self.current_level_stage_idx: int = 0

        self.carnaval_confetti = []
        self.carnaval_fireworks = []

        # Cargar busto del personaje y sprites de diálogo de la Paloma
        self._load_character_bust()
        self._load_paloma_guide()
        self._load_paloma_dialog_assets()

        # Tipografías cálidas para el cuadro de diálogo
        self.font_paloma_speaker = pygame.font.SysFont("Trebuchet MS, Arial, sans-serif", 22, bold=True)
        self.font_paloma_badge = pygame.font.SysFont("Trebuchet MS, Arial, sans-serif", 16, bold=True)
        self.font_paloma_body = pygame.font.SysFont("Trebuchet MS, Arial, sans-serif", 23, bold=True)
        self.font_paloma_hint = pygame.font.SysFont("Trebuchet MS, Arial, sans-serif", 16, bold=True)

        # Botones de la pantalla de Victoria
        def make_vic_btn(text: str, bg_col, b_col) -> pygame.Surface:
            bw, bh = 290, 52
            surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(surf, bg_col, (0, 0, bw, bh), border_radius=14)
            pygame.draw.rect(surf, b_col, (0, 0, bw, bh), width=2, border_radius=14)
            font_b = pygame.font.SysFont("Arial Black, Impact", 18)
            txt = font_b.render(text, True, (255, 255, 255))
            surf.blit(txt, txt.get_rect(center=(bw // 2, bh // 2)))
            return surf

        self.btn_vic_explore = UIButton(
            center_pos=(self.screen_w // 2 - 170, self.screen_h // 2 + 180),
            normal_sprite=make_vic_btn("SEGUIR EXPLORANDO", (35, 120, 60), (100, 245, 140)),
            on_click=self._close_victory_modal
        )
        self.btn_vic_menu = UIButton(
            center_pos=(self.screen_w // 2 + 170, self.screen_h // 2 + 180),
            normal_sprite=make_vic_btn("SALIR AL MENÚ", (160, 45, 45), (245, 110, 110)),
            on_click=self.request_exit
        )

    def _load_paloma_dialog_assets(self) -> None:
        """Carga y escala proporcionalmente text_dialog.png y paloma_dialog.png para las conversaciones."""
        try:
            raw_box = self.assets.load_surface("text_dialog.png", has_alpha=True)
            bw, bh = raw_box.get_size()
            target_w = 1060
            target_h = max(240, int(bh * (target_w / float(max(1, bw)))))
            self.dialog_box_surf = pygame.transform.smoothscale(raw_box, (target_w, target_h))
        except Exception:
            self.dialog_box_surf = pygame.Surface((1060, 530), pygame.SRCALPHA)
            pygame.draw.rect(self.dialog_box_surf, (255, 244, 218, 248), (20, 60, 1020, 420), border_radius=36)
            pygame.draw.rect(self.dialog_box_surf, (150, 95, 175), (20, 60, 1020, 420), width=6, border_radius=36)

        try:
            raw_pal = self.assets.load_surface("paloma_dialog.png", has_alpha=True)
            mask = pygame.mask.from_surface(raw_pal)
            rects = mask.get_bounding_rects()
            cropped = raw_pal.subsurface(rects[0]) if rects else raw_pal
            target_h = 330
            target_w = max(180, int(cropped.get_width() * (target_h / float(max(1, cropped.get_height())))))
            self.paloma_dialog_portrait = pygame.transform.smoothscale(cropped, (target_w, target_h))
        except Exception:
            self.paloma_dialog_portrait = self.paloma_guide

    def open_paloma_dialog(
        self,
        pages: list,
        speaker: str = "PALOMA DE CURRAMBA",
        badge: str = "",
        on_finish: Optional[Callable[[], None]] = None,
        voice_prefix: str = ""
    ) -> None:
        """Abre el cuadro de diálogo acuarela de la Paloma con soporte multipágina y callback al terminar."""
        if not pages:
            if on_finish:
                on_finish()
            return
        self.paloma_dialog_pages = pages
        self.paloma_dialog_page_idx = 0
        self.paloma_dialog_speaker = speaker
        self.paloma_dialog_badge = badge
        self.paloma_dialog_on_finish = on_finish
        self.paloma_dialog_voice_prefix = voice_prefix
        self.paloma_dialog_open = True
        self.camera.stop_drag()
        self._trigger_dialog_voice(0)
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def _trigger_dialog_voice(self, page_idx: int) -> None:
        """Reproduce clip de voz opcional si existe en assets (soporte para doblaje Tarea 005)."""
        prefix = getattr(self, "paloma_dialog_voice_prefix", "")
        if prefix:
            voice_name = f"{prefix}_{page_idx}.ogg"
            try:
                import os
                full_p = os.path.join(self.assets.assets_dir, voice_name)
                if os.path.exists(full_p):
                    self.audio.play_sound(voice_name)
                    return
            except Exception:
                pass
        if hasattr(self.audio, "play_pigeon") and page_idx == 0:
            self.audio.play_pigeon()

    def advance_paloma_dialog(self) -> None:
        """Avanza a la siguiente página del diálogo de la Paloma o ejecuta la acción final al terminar."""
        if not self.paloma_dialog_open:
            return
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()
        if self.paloma_dialog_page_idx + 1 < len(self.paloma_dialog_pages):
            self.paloma_dialog_page_idx += 1
            self._trigger_dialog_voice(self.paloma_dialog_page_idx)
        else:
            self.paloma_dialog_open = False
            cb = self.paloma_dialog_on_finish
            self.paloma_dialog_on_finish = None
            if cb:
                cb()

    def get_current_campaign_poi(self) -> str:
        """Retorna el siguiente POI objetivo dentro de la ruta de 4 niveles del Modo Historia."""
        progress = self.settings.get_story_progress()
        unlocked = set(progress.get("unlocked_locations", []))
        completed = set(progress.get("completed_microgames", []))
        for poi_key in STORY_CAMPAIGN_ORDER:
            stages = STORY_LEVEL_STAGES.get(poi_key, [])
            all_stages_done = all(st["id"] in completed for st in stages) if stages else (poi_key in unlocked)
            if not all_stages_done:
                return poi_key
        return STORY_CAMPAIGN_ORDER[-1]

    def _load_character_bust(self) -> None:
        sprite_filename = f"{self.character_id}_seleccion_personaje.png"
        try:
            raw = self.assets.load_surface(sprite_filename, has_alpha=True)
            mask = pygame.mask.from_surface(raw)
            rects = mask.get_bounding_rects()
            cropped = raw.subsurface(rects[0]) if rects else raw
            target_h = 160
            target_w = int(cropped.get_width() * (target_h / float(cropped.get_height())))
            self.character_bust = pygame.transform.smoothscale(cropped, (target_w, target_h))
        except Exception:
            self.character_bust = pygame.Surface((100, 160), pygame.SRCALPHA)
            pygame.draw.rect(self.character_bust, (220, 160, 60), (0, 0, 100, 160), border_radius=14)

    def _load_paloma_guide(self) -> None:
        """Carga a la paloma como guía diegética del recorrido por Curramba."""
        try:
            raw = self.assets.load_surface("paloma_dialog.png", has_alpha=True)
            mask = pygame.mask.from_surface(raw)
            rects = mask.get_bounding_rects()
            cropped = raw.subsurface(rects[0]) if rects else raw
            target_h = 135
            target_w = max(90, int(cropped.get_width() * (target_h / float(cropped.get_height()))))
            self.paloma_guide = pygame.transform.smoothscale(cropped, (target_w, target_h))
        except Exception:
            self.paloma_guide = pygame.Surface((110, 135), pygame.SRCALPHA)
            pygame.draw.ellipse(self.paloma_guide, (220, 225, 232), (10, 25, 90, 80))
            pygame.draw.circle(self.paloma_guide, (235, 240, 245), (78, 35), 30)
            pygame.draw.polygon(self.paloma_guide, (245, 170, 55), [(105, 35), (88, 43), (105, 50)])

    def _close_victory_modal(self) -> None:
        self.show_victory_modal = False
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def _spawn_carnaval_celebration(self) -> None:
        import random
        for _ in range(50):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(120, 420)
            self.carnaval_confetti.append({
                "x": float(random.randint(100, self.screen_w - 100)),
                "y": float(random.randint(50, 400)),
                "vx": math.cos(angle) * spd * 0.4,
                "vy": random.uniform(60, 180),
                "color": random.choice([(255, 215, 60), (255, 60, 110), (50, 210, 255), (100, 255, 130), (245, 140, 40)]),
                "size": random.uniform(6.0, 12.0),
                "life": 1.0
            })
    def _init_quest_card(self) -> None:
        """Inicializa la tarjeta modal de misión / microjuego con assets 100% ilustrados (cero formas de código)."""
        self.quest_card_open: bool = False
        self.quest_card_anim_t: float = 0.0
        self.quest_card_w: int = 620
        self.quest_card_h: int = 830
        self.tex_quest_card = self.assets.load_surface("recuadro_mision_nivel.png")

        # Tipografía redondeada caribeña de alta legibilidad (cero fuentes toscas o cursivas ilegibles)
        self.font_quest_title = self.assets.get_font("arial rounded", 26, bold=True)
        self.font_quest_sub = self.assets.get_font("arial rounded", 15, bold=True)
        self.font_quest_body = self.assets.get_font("trebuchet ms", 16, bold=False)
        self.font_quest_btn = self.assets.get_font("arial rounded", 19, bold=True)

        # Texturas ilustradas de apoyo (cartucho de pergamino con flores, separador y sellos de cera)
        self.tex_quest_cartridge = self.assets.load_surface("cinta_distrito_modal.png")
        self.tex_quest_status_ribbon = self.assets.load_surface("cinta_estado_modal.png")
        self.tex_quest_sep = self.assets.load_surface("separador_floral_modal.png")
        self.tex_sello_despejado = self.assets.load_surface("sello_estado_despejado.png")
        self.tex_sello_pendiente = self.assets.load_surface("sello_estado_pendiente.png")
        self.tex_emblema_estrella = self.assets.load_surface("emblema_estrella_modal.png")

        # Botón '¡A JUGAR!' ilustrado en acuarela caribeña pura (cero rectángulos de código)
        raw_play_surf = self.assets.load_surface("boton_jugar_modal.png")
        btn_play_w = 280
        if raw_play_surf:
            aspect = raw_play_surf.get_height() / max(1, raw_play_surf.get_width())
            btn_play_h = int(btn_play_w * aspect)
            play_surf = pygame.transform.smoothscale(raw_play_surf, (btn_play_w, btn_play_h))
        else:
            play_surf = pygame.Surface((btn_play_w, 75), pygame.SRCALPHA)

        play_cy = self.screen_h // 2 - self.quest_card_h // 2 + int(self.quest_card_h * 0.80)
        self.btn_quest_play = UIButton(
            center_pos=(self.screen_w // 2, play_cy),
            normal_sprite=play_surf,
            on_click=self._launch_microgame
        )

        # Botón de cierre 'X' ilustrado: medallón circular de cera con trinitarias
        # Posicionado arriba a la izquierda por indicación directa del usuario
        raw_close_surf = self.assets.load_surface("boton_cerrar_modal.png")
        close_size = 62
        if raw_close_surf:
            close_surf = pygame.transform.smoothscale(raw_close_surf, (close_size, close_size))
        else:
            close_surf = pygame.Surface((close_size, close_size), pygame.SRCALPHA)

        close_cx = self.screen_w // 2 - self.quest_card_w // 2 + int(self.quest_card_w * 0.13)
        close_cy = self.screen_h // 2 - self.quest_card_h // 2 + int(self.quest_card_h * 0.105)

        self.btn_quest_close = UIButton(
            center_pos=(close_cx, close_cy),
            normal_sprite=close_surf,
            on_click=self._close_quest_card
        )

    def _notify_poi_arrival(self, poi_name: str) -> None:
        """Activa el saludo cozy de la Paloma y abre el flujo del nivel al llegar a uno de los 4 POIs jugables."""
        poi_info = self.poi_registry.get(poi_name, {})
        title = poi_info.get("title", poi_name.upper())

        # Los niveles principales y secretos configurados en el mapa son jugables.
        if poi_name not in STORY_PLAYABLE_POIS:
            self.toast_msg = f"📍 {title} — PUNTO PANORÁMICO DE CURRAMBA"
            self.toast_timer = 2.5
            if hasattr(self.audio, "play_hover"):
                self.audio.play_hover()
            return

        self.toast_msg = f"📍 {title} — LA PALOMA TE ESPERA"
        self.toast_timer = 2.5
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

        if poi_name in self.poi_registry:
            self.active_poi = poi_name

        # Iniciar diálogo con la Paloma para el nivel
        if poi_name in PALOMA_STORY_DIALOGS:
            dlg_cfg = PALOMA_STORY_DIALOGS[poi_name]
            self.current_level_stage_idx = 0
            self.open_paloma_dialog(
                pages=dlg_cfg["pre_pages"],
                speaker=dlg_cfg.get("speaker", "PALOMA DE CURRAMBA"),
                badge=dlg_cfg.get("level_badge", title),
                on_finish=lambda: self._open_quest_card(poi_name),
                voice_prefix=dlg_cfg.get("voice_clip_prefix", "")
            )
        else:
            self._open_quest_card(poi_name)

    def _open_quest_card(self, poi_name: str = "uninorte") -> None:
        """Abre la tarjeta de misión del nodo y centra la cámara suavemente."""
        if poi_name in self.poi_registry:
            self.active_poi = poi_name
        self.quest_card_open = True
        self.camera.stop_drag()
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def _close_quest_card(self) -> None:
        self.quest_card_open = False
        if hasattr(self.audio, "play_hover"):
            self.audio.play_hover()

    def _exit_microgame_to_main_menu(self) -> None:
        if not self.state_machine:
            return
        self.state_machine.pop_state()  # pausa
        self.state_machine.pop_state()  # minijuego
        self.state_machine.push_state(self)
        self.request_exit()

    def _launch_microgame(self) -> None:
        """Lanza el desafío exclusivo del distrito activo (soportando niveles de múltiples rondas encadenadas)."""
        self._close_quest_card()
        self.paloma_dialog_open = False
        poi_info = self.poi_registry.get(self.active_poi, {})

        stages = STORY_LEVEL_STAGES.get(self.active_poi, [])
        if stages:
            idx = max(0, min(self.current_level_stage_idx, len(stages) - 1))
            stage_info = stages[idx]
            microgame_cls = stage_info.get("cls")
        else:
            microgame_cls = MICROGAME_MAP.get(self.active_poi)
            if microgame_cls is None:
                microgame_cls = MICROGAME_MAP.get(poi_info.get("microgame_id", ""))

        if microgame_cls is None:
            self.toast_msg = "MINIJUEGO NO DISPONIBLE"
            self.toast_timer = 2.5
            return

        import inspect
        sig = inspect.signature(microgame_cls.__init__)
        kwargs: Dict[str, Any] = {"on_complete_callback": self._on_microgame_complete}
        if "character_id" in sig.parameters:
            kwargs["character_id"] = self.character_id

        microgame = microgame_cls(**kwargs)
        if stages and idx + 1 < len(stages):
            # Ronda intermedia del nivel: cartel breve de ronda superada
            microgame.outro_message = f"¡RONDA {idx + 1} SUPERADA!"
        elif stages and idx + 1 == len(stages):
            # Última ronda que completa el nivel
            microgame.outro_message = f"¡{poi_info.get('title', 'NIVEL')} DESPEJADO!"

        microgame.pause_return_callback = self._return_from_microgame_pause
        microgame.open_pause_menu = lambda: self.state_machine.push_state(
            __import__("core.microgame_pause", fromlist=["MicrogamePauseState"]).MicrogamePauseState(
                previous=microgame,
                return_callback=getattr(microgame, "pause_return_callback", None),
                restart_callback=self._launch_microgame
            )
        ) if self.state_machine else None
        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(microgame)

    def _return_from_microgame_pause(self) -> None:
        if not self.state_machine:
            return
        self.state_machine.pop_state()  # pausa
        self.state_machine.pop_state()  # minijuego
        self.state_machine.push_state(self)

    def _on_microgame_complete(self, won: bool) -> None:
        """Retorna al mapa o encadena la Ronda 2 del nivel actual y muestra la reflexión de la Paloma."""
        poi_info = self.poi_registry.get(self.active_poi, {})
        stages = STORY_LEVEL_STAGES.get(self.active_poi, [])
        dlg_cfg = PALOMA_STORY_DIALOGS.get(self.active_poi, {})

        if won:
            progress = self.settings.get_story_progress()
            completed = list(progress.get("completed_microgames", []))
            unlocked = list(progress.get("unlocked_locations", []))

            if stages:
                idx = max(0, min(self.current_level_stage_idx, len(stages) - 1))
                stage_id = stages[idx]["id"]
                if stage_id not in completed:
                    completed.append(stage_id)

                # ¿Hay una segunda ronda encadenada en este mismo nivel (Uninorte / Buenavista)?
                if self.current_level_stage_idx + 1 < len(stages):
                    self.current_level_stage_idx += 1
                    new_score = int(progress.get("high_score", 0)) + 100
                    self.settings.update_story_progress(
                        has_active_save=True,
                        character_id=self.character_id,
                        completed_microgames=completed,
                        high_score=new_score
                    )
                    self._sync_social_hud()
                    # Encadenar directamente la Ronda 2 sin cortar el ritmo con diálogos intermedios
                    self._launch_microgame()
                    return

            # Nivel completado en su totalidad
            m_id = poi_info.get("microgame_id", "uninorte_sprint")
            if m_id not in completed:
                completed.append(m_id)
            if self.active_poi not in unlocked:
                unlocked.append(self.active_poi)

            self.current_level_stage_idx = 0
            new_score = int(progress.get("high_score", 0)) + 100
            self.settings.update_story_progress(
                has_active_save=True,
                character_id=self.character_id,
                completed_microgames=completed,
                unlocked_locations=unlocked,
                high_score=new_score
            )
            metrics = self._sync_social_hud()
            if metrics:
                self.settings.update_story_progress(
                    followers=metrics["followers"],
                    likes=metrics["likes"],
                    achievements=metrics["achievements"]
                )

            if hasattr(self, "state_machine") and self.state_machine:
                self.state_machine.change_state(self)

            # Toast celebratorio oficial de nivel completado
            self.toast_msg = f"🎉 ¡{poi_info.get('title', 'NIVEL')} DESPEJADO CON ÉXITO!"
            self.toast_timer = 4.0

            # Verificar si se completaron los 4 niveles principales de la Historia
            all_4_levels_cleared = all(p in unlocked for p in STORY_CAMPAIGN_ORDER)

            def _after_post_win_dialog() -> None:
                if (all_4_levels_cleared or m_id == "batalla_flores_boss" or len(completed) >= 8) and not self.victory_modal_shown:
                    self.show_victory_modal = True
                    self.victory_modal_shown = True
                    self._spawn_carnaval_celebration()

            post_win_pages = dlg_cfg.get("post_win_pages", [])
            if post_win_pages:
                self.open_paloma_dialog(
                    pages=post_win_pages,
                    speaker=dlg_cfg.get("speaker", "PALOMA DE CURRAMBA"),
                    badge=f"★ {dlg_cfg.get('level_badge', poi_info.get('title', ''))} COMPLETADO ★",
                    on_finish=_after_post_win_dialog,
                    voice_prefix=f"{dlg_cfg.get('voice_clip_prefix', '')}_win"
                )
            else:
                _after_post_win_dialog()
        else:
            # Derrota: regresar al mapa y mostrar mensaje cálido de ánimo de la Paloma
            if hasattr(self, "state_machine") and self.state_machine:
                self.state_machine.change_state(self)

            post_lose_pages = dlg_cfg.get("post_lose_pages", [])
            if post_lose_pages:
                self.open_paloma_dialog(
                    pages=post_lose_pages,
                    speaker=dlg_cfg.get("speaker", "PALOMA DE CURRAMBA"),
                    badge=dlg_cfg.get("level_badge", poi_info.get("title", "")),
                    voice_prefix=f"{dlg_cfg.get('voice_clip_prefix', '')}_lose"
                )

    def _open_pause_menu(self) -> None:
        """Abre el menú de pausa floral oficial (recuadro_menu_pausa.png) en el mapa."""
        if hasattr(self, "state_machine") and self.state_machine:
            from core.microgame_pause import MicrogamePauseState
            self.camera.stop_drag()
            self.state_machine.push_state(
                MicrogamePauseState(
                    previous=self,
                    return_callback=self._on_exit_clicked,
                    save_callback=self._on_save_clicked,
                    on_calibrate=self._on_calibrate_pointer
                )
            )
        else:
            self._toggle_menu()

    def _toggle_menu(self) -> None:
        self.menu_open = not self.menu_open
        if self.menu_open:
            self.camera.stop_drag()
            self.btn_drawer_music.toggle_state = self.audio.music_enabled
            self.btn_drawer_sound.toggle_state = self.audio.sound_enabled

    def _on_save_clicked(self) -> None:
        self.save_current_state()
        self.save_feedback_timer = 2.5
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def _on_exit_clicked(self) -> None:
        self.save_current_state()
        self.request_exit()

    def _on_calibrate_pointer(self) -> None:
        """Abre la calibración del lapicero y vuelve al mapa al completarla."""
        self.menu_open = False
        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(
                CoasterCalibrationState(
                    on_complete_callback=lambda _ok: self.state_machine.change_state(self)
                )
            )

    def _on_open_settings(self) -> None:
        self.menu_open = False
        if self.state_machine:
            self.state_machine.push_state(MapSettingsState(on_calibrate=self._on_calibrate_from_settings))

    def _on_calibrate_from_settings(self) -> None:
        if self.state_machine:
            self.state_machine.pop_state()
        self._on_calibrate_pointer()

    def set_weather(self, weather_name: str) -> None:
        """Cambia el clima actual del mapa ('day', 'sunset', 'night', 'rain')."""
        if weather_name in self.weather_modes:
            self.current_weather = weather_name

    def cycle_weather(self) -> str:
        """Rota de forma cíclica entre los climas disponibles."""
        idx = (self.weather_modes.index(self.current_weather) + 1) % len(self.weather_modes)
        self.current_weather = self.weather_modes[idx]
        return self.current_weather

    def save_current_state(self) -> None:
        """Auto-guarda transparentemente el estado actual del Modo Historia en settings.json."""
        metrics = self._sync_social_hud()
        update_payload: Dict[str, Any] = {
            "has_active_save": True,
            "character_id": self.character_id,
            "current_node_id": self.player_node_id if hasattr(self, "player_node_id") else 0,
            "last_camera_x": float(self.camera.x),
            "last_camera_y": float(self.camera.y)
        }
        if metrics:
            update_payload["followers"] = metrics["followers"]
            update_payload["likes"] = metrics["likes"]
            update_payload["achievements"] = metrics["achievements"]
        self.settings.update_story_progress(**update_payload)

    def request_exit(self) -> None:
        """Guarda el progreso y sale directamente al menú principal cuando está disponible."""
        self.save_current_state()
        if self.on_main_menu_callback:
            self.on_main_menu_callback(self)
        elif self.on_back_callback:
            self.on_back_callback()

    def _init_player_navigation(self) -> None:
        """Inicializa el sistema de navegación del avatar del jugador sobre la red vial."""
        progress = self.settings.get_story_progress()
        saved_node_id = progress.get("current_node_id", 0)

        nodes, edges, node_map, adj, edge_map = self._get_street_graph()

        if saved_node_id in node_map:
            self.player_node_id: int = saved_node_id
        elif nodes:
            self.player_node_id = nodes[0]["id"]
        else:
            self.player_node_id = 0

        if self.player_node_id in node_map:
            st = node_map[self.player_node_id]
            self.player_pos: Tuple[float, float] = (float(st["x"]), float(st["y"]))
        else:
            self.player_pos = (808.0, 464.0)

        self.player_is_moving: bool = False
        self.player_path_edges: list = []
        self.player_edge_idx: int = 0
        self.player_edge_dist: float = 0.0
        self.player_speed: float = 430.0  # px/s velocidad de viaje constante
        self.player_anim_timer: float = 0.0
        self.player_alpha: float = 1.0
        self.player_target_poi: Optional[str] = None
        self.player_facing_right: bool = True
        self.player_chibi_surf: Optional[pygame.Surface] = None

        # Construir badge circular con recorte de rostro y cargar chibi
        self._build_player_token()
        self._load_player_chibi()

    def _load_player_chibi(self) -> None:
        """Carga y procesa el sprite chibi del personaje para renderizado en mapa."""
        chibi_filename = f"{self.character_id}_chibi.png"
        try:
            raw = self.assets.load_surface(chibi_filename, has_alpha=True)
            mask = pygame.mask.from_surface(raw)
            rects = mask.get_bounding_rects()
            if rects:
                crop = raw.subsurface(rects[0])
            else:
                crop = raw
            target_h = 70
            aspect = crop.get_width() / max(1, crop.get_height())
            target_w = max(24, int(target_h * aspect))
            self.player_chibi_surf = pygame.transform.smoothscale(crop, (target_w, target_h))
        except Exception:
            try:
                raw_fallback = self.assets.load_surface(f"{self.character_id}_seleccion_personaje.png", has_alpha=True)
                mask = pygame.mask.from_surface(raw_fallback)
                rects = mask.get_bounding_rects()
                crop = raw_fallback.subsurface(rects[0]) if rects else raw_fallback
                target_h = 70
                aspect = crop.get_width() / max(1, crop.get_height())
                target_w = max(24, int(target_h * aspect))
                self.player_chibi_surf = pygame.transform.smoothscale(crop, (target_w, target_h))
            except Exception:
                self.player_chibi_surf = pygame.Surface((46, 70), pygame.SRCALPHA)
                pygame.draw.ellipse(self.player_chibi_surf, (245, 195, 65), (4, 4, 38, 62))

    def _build_player_token(self) -> None:
        """
        Construye el token/insignia circular estilizada del avatar del jugador
        con crop de busto del personaje seleccionado, borde dorado y punta indicadora.
        """
        token_d = 52
        token_h = 62
        surf = pygame.Surface((token_d, token_h), pygame.SRCALPHA)

        cx = token_d // 2
        cy = token_d // 2
        r = token_d // 2 - 2

        # 1. Base circular dorada
        pygame.draw.circle(surf, (245, 195, 65), (cx, cy), r + 2)
        pygame.draw.circle(surf, (30, 25, 45), (cx, cy), r)

        # 2. Punta indicadora inferior
        pointer_pts = [(cx - 7, cy + r - 3), (cx + 7, cy + r - 3), (cx, token_h - 2)]
        pygame.draw.polygon(surf, (245, 195, 65), pointer_pts)
        pygame.draw.polygon(surf, (160, 110, 25), pointer_pts, 1)

        # 3. Recorte circular del rostro del personaje
        sprite_filename = f"{self.character_id}_seleccion_personaje.png"
        try:
            raw = self.assets.load_surface(sprite_filename, has_alpha=True)
            mask = pygame.mask.from_surface(raw)
            rects = mask.get_bounding_rects()
            if rects:
                br = rects[0]
                head_size = int(min(br.width, br.height * 0.46))
                hx = br.x + (br.width - head_size) // 2
                hy = br.y + int(br.height * 0.02)
                face_crop = raw.subsurface((hx, hy, head_size, head_size))
            else:
                face_crop = raw

            inner_d = (r - 2) * 2
            face_scaled = pygame.transform.smoothscale(face_crop, (inner_d, inner_d))

            face_mask_surf = pygame.Surface((inner_d, inner_d), pygame.SRCALPHA)
            pygame.draw.circle(face_mask_surf, (255, 255, 255, 255), (inner_d // 2, inner_d // 2), inner_d // 2)
            face_mask_surf.blit(face_scaled, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

            surf.blit(face_mask_surf, (cx - inner_d // 2, cy - inner_d // 2))
        except Exception:
            inner_d = (r - 2) * 2
            pygame.draw.circle(surf, (220, 160, 60), (cx, cy), inner_d // 2)

        # 4. Aro dorado frontal con brillo superior
        pygame.draw.circle(surf, (255, 220, 95), (cx, cy), r, width=3)
        pygame.draw.arc(surf, (255, 255, 255, 180), (cx - r + 3, cy - r + 3, (r - 3) * 2, (r - 3) * 2), 0.7, 2.4, 2)

        self.player_token_surf = surf

        # Sombra de contacto suave para el suelo
        sw, sh = 46, 16
        shadow = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (15, 22, 35, 120), (0, 0, sw, sh))
        self.player_shadow_surf = shadow

    def _get_street_graph(self):
        """Retorna la topología completa (nodos, aristas, adyacencias, mapa) de la red vial actual."""
        if hasattr(self, "dev_tool"):
            nodes = self.dev_tool.nodes
            edges = self.dev_tool.edges
        else:
            net = getattr(self, "layout_data", {}).get("street_network", {})
            nodes = net.get("nodes", [])
            edges = net.get("edges", [])

        node_map = {n["id"]: n for n in nodes}
        adj = {n["id"]: [] for n in nodes}
        edge_map = {}
        for e in edges:
            u, v = e["from"], e["to"]
            if u in node_map and v in node_map:
                if v not in adj[u]:
                    adj[u].append(v)
                if u not in adj[v]:
                    adj[v].append(u)
                edge_map[(u, v)] = e
                edge_map[(v, u)] = e
        return nodes, edges, node_map, adj, edge_map

    def _find_shortest_path(self, start_id: int, goal_id: int) -> Optional[list]:
        """Calcula la ruta más corta entre dos nodos en la red vial mediante BFS."""
        if start_id == goal_id:
            return [start_id]
        nodes, edges, node_map, adj, edge_map = self._get_street_graph()
        if start_id not in node_map or goal_id not in node_map:
            return None

        queue = deque([[start_id]])
        visited = {start_id}
        while queue:
            path = queue.popleft()
            curr = path[-1]
            if curr == goal_id:
                return path
            for nbr in adj.get(curr, []):
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append(path + [nbr])
        return None

    def _start_path_travel(self, path: list, target_poi: Optional[str] = None) -> None:
        """Configura y arranca el desplazamiento sobre la cola de aristas Bézier a velocidad física constante."""
        if len(path) < 2:
            if target_poi:
                self._open_quest_card(target_poi)
            return

        nodes, edges, node_map, adj, edge_map = self._get_street_graph()

        edge_queue = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            e = edge_map.get((u, v))
            if not e:
                continue
            nu, nv = node_map[u], node_map[v]
            p0 = (nu["x"], nu["y"])
            p1 = (nv["x"], nv["y"])
            cx = e.get("ctrl_x", (p0[0] + p1[0]) // 2)
            cy = e.get("ctrl_y", (p0[1] + p1[1]) // 2)
            pts = get_bezier_points(p0, (cx, cy), p1, step_px=5)
            if len(pts) < 2:
                pts = [p0, p1]

            cum = [0.0]
            for k in range(1, len(pts)):
                d_seg = math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1])
                cum.append(cum[-1] + d_seg)

            edge_queue.append({
                "from": u,
                "to": v,
                "points": pts,
                "cum_dists": cum,
                "total_dist": max(1.0, cum[-1]),
                "hidden": bool(e.get("hidden", False))
            })

        if edge_queue:
            self.player_path_edges = edge_queue
            self.player_edge_idx = 0
            self.player_edge_dist = 0.0
            self.player_is_moving = True
            self.player_target_poi = target_poi
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()

    def _handle_dpad_move(self, dir_vec: Tuple[float, float]) -> bool:
        """
        Navegación tipo D-Pad / WASD / Flechas en intersecciones (Opción 1.C):
        Selecciona la arista cuya tangente de salida tenga mayor coincidencia direccional (dot product),
        y viaja únicamente hasta el siguiente nodo de la red. Así cada nodo
        vuelve a ser una parada navegable, como en la versión anterior.
        """
        if self.player_is_moving:
            return False

        nodes, edges, node_map, adj, edge_map = self._get_street_graph()
        curr_id = self.player_node_id
        if curr_id not in node_map or not adj.get(curr_id):
            return False

        curr_n = node_map[curr_id]
        best_nbr = None
        best_dot = 0.20

        for nbr_id in adj[curr_id]:
            e = edge_map.get((curr_id, nbr_id))
            if not e:
                continue
            nbr_n = node_map[nbr_id]
            cx = e.get("ctrl_x", (curr_n["x"] + nbr_n["x"]) // 2)
            cy = e.get("ctrl_y", (curr_n["y"] + nbr_n["y"]) // 2)
            dx = float(cx - curr_n["x"])
            dy = float(cy - curr_n["y"])
            mag = math.hypot(dx, dy)
            if mag < 1.0:
                dx = float(nbr_n["x"] - curr_n["x"])
                dy = float(nbr_n["y"] - curr_n["y"])
                mag = math.hypot(dx, dy)
            if mag > 0.001:
                dot = (dx / mag) * dir_vec[0] + (dy / mag) * dir_vec[1]
                if dot > best_dot:
                    best_dot = dot
                    best_nbr = nbr_id

        if best_nbr is None:
            return False

        # Cada nodo es una parada: no saltar nodos intermedios ni limitarse a
        # los POI que tienen minijuego.
        path = [curr_id, best_nbr]
        self._start_path_travel(path)
        return True

    def _find_node_near_world_pos(self, world_pos: Tuple[float, float], max_dist: float = 28.0) -> Optional[dict]:
        """Encuentra el nodo más cercano a una posición del mundo dentro del radio de tolerancia."""
        nodes, _, _, _, _ = self._get_street_graph()
        best_node = None
        best_d = max_dist
        for n in nodes:
            d = math.hypot(n["x"] - world_pos[0], n["y"] - world_pos[1])
            if d < best_d:
                best_d = d
                best_node = n
        return best_node

    def _get_poi_target_node(self, poi_key: str) -> Optional[int]:
        """Determina el nodo objetivo en la red vial correspondiente a un POI (priorizando nodos de parada)."""
        nodes, _, node_map, _, _ = self._get_street_graph()
        poi_info = self.poi_registry.get(poi_key)
        if not poi_info or not nodes:
            return None
        poi_rect = poi_info["rect"]
        center = (poi_rect.centerx, poi_rect.centery)

        # Candidatos con is_stop dentro de 450px
        stop_cands = [
            n for n in nodes
            if n.get("is_stop") and math.hypot(n["x"] - center[0], n["y"] - center[1]) < 450.0
        ]
        if stop_cands:
            best_stop = min(stop_cands, key=lambda n: math.hypot(n["x"] - center[0], n["y"] - center[1]))
            return best_stop["id"]

        # Si no hay parada cercana, nodo más cercano general
        best_n = min(nodes, key=lambda n: math.hypot(n["x"] - center[0], n["y"] - center[1]))
        return best_n["id"]

    def _get_nearest_poi_to_pos(self, pos: Tuple[float, float], max_dist: float = 340.0) -> Optional[str]:
        """Retorna el POI jugable más cercano a una posición dentro de la distancia máxima."""
        best_key = None
        best_d = max_dist
        for p_key in STORY_PLAYABLE_POIS:
            p_info = self.poi_registry.get(p_key)
            if not p_info:
                continue
            r = p_info["rect"]
            d = math.hypot(r.centerx - pos[0], r.centery - pos[1])
            if d < best_d:
                best_d = d
                best_key = p_key
        return best_key

    def _render_level_stops(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Renderiza todos los nodos, destacando en amarillo solo los POI."""
        nodes, _, node_map, _, _ = self._get_street_graph()
        playable_stop_ids = {
            tid for tid in (self._get_poi_target_node(pk) for pk in STORY_PLAYABLE_POIS) if tid is not None
        }

        pulse = math.sin(self.timer * 3.5) * 0.5 + 0.5
        for n in nodes:
            sx = n["x"] - cam_x
            sy = n["y"] - cam_y
            if -40 < sx < self.screen_w + 40 and -40 < sy < self.screen_h + 40:
                if n["id"] in playable_stop_ids:
                    glow_r = int(14 + 4 * pulse)
                    glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, (245, 195, 60, int(70 + 50 * pulse)), (glow_r, glow_r), glow_r)
                    surface.blit(glow_surf, (sx - glow_r, sy - glow_r))
                    pygame.draw.circle(surface, (255, 215, 70), (sx, sy), 9)
                    pygame.draw.circle(surface, (40, 30, 20), (sx, sy), 7)
                    pygame.draw.circle(surface, (255, 240, 180), (sx, sy), 4)
                else:
                    # Nodo de navegación: visible pero sin competir con un nivel.
                    pygame.draw.circle(surface, (115, 137, 153), (sx, sy), 4)
                    pygame.draw.circle(surface, (225, 235, 225), (sx, sy), 2)

    def _render_player_avatar(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Renderiza el avatar del jugador: sombra de contacto, cuerpo chibi con bamboleo/waddle al caminar y desvanecimiento en túneles."""
        if not hasattr(self, "player_pos") or self.player_alpha <= 0.01:
            return

        px = int(self.player_pos[0]) - cam_x
        py = int(self.player_pos[1]) - cam_y

        if not (-100 < px < self.screen_w + 100 and -120 < py < self.screen_h + 100):
            return

        # Animación de marcha / waddle:
        # Si se mueve: bamboleo angular de lado a lado (walk cycle oscilante) y rebote de pasos.
        # En reposo: respiración sutil (idle breathing).
        if self.player_is_moving:
            walk_freq = 14.0
            tilt_angle = math.sin(self.player_anim_timer * walk_freq) * 7.5  # Inclinación ±7.5°
            bob_y = -abs(math.sin(self.player_anim_timer * walk_freq)) * 5.0  # Pequeño salto en cada paso
        else:
            tilt_angle = 0.0
            bob_y = math.sin(self.player_anim_timer * 3.2) * 2.2

        # 1. Sombra de contacto suave en el suelo
        if hasattr(self, "player_shadow_surf"):
            sw, sh = self.player_shadow_surf.get_size()
            if self.player_alpha < 0.99:
                sh_copy = self.player_shadow_surf.copy()
                sh_copy.set_alpha(int(120 * self.player_alpha))
                surface.blit(sh_copy, (px - sw // 2, py - sh // 2 + 2))
            else:
                surface.blit(self.player_shadow_surf, (px - sw // 2, py - sh // 2 + 2))

        # 2. Renderizado del sprite Chibi del personaje seleccionado
        if getattr(self, "player_chibi_surf", None) is not None:
            chibi_to_draw = self.player_chibi_surf
            # Voltear horizontalmente según la dirección en que mira
            if not getattr(self, "player_facing_right", True):
                chibi_to_draw = pygame.transform.flip(chibi_to_draw, True, False)

            # Aplicar rotación de paso (waddle)
            if abs(tilt_angle) > 0.05:
                # Invertir tilt si mira a la izquierda para mantener la sincronía del paso
                actual_tilt = tilt_angle if getattr(self, "player_facing_right", True) else -tilt_angle
                rotated_surf = pygame.transform.rotozoom(chibi_to_draw, actual_tilt, 1.0)
            else:
                rotated_surf = chibi_to_draw

            rw, rh = rotated_surf.get_size()
            cw = chibi_to_draw.get_width()
            ch = chibi_to_draw.get_height()

            # Posicionar los pies del chibi en (px, py)
            draw_x = px - rw // 2
            draw_y = int(py - ch + 2 + bob_y - (rh - ch) // 2)

            if self.player_alpha < 0.99:
                c_copy = rotated_surf.copy()
                c_copy.set_alpha(int(255 * self.player_alpha))
                surface.blit(c_copy, (draw_x, draw_y))
            else:
                surface.blit(rotated_surf, (draw_x, draw_y))

        elif hasattr(self, "player_token_surf"):
            # Fallback a token badge circular si no hubiera sprite chibi
            tw, th = self.player_token_surf.get_size()
            token_x = px - tw // 2
            token_y = int(py - th + 8 + bob_y)

            if self.player_alpha < 0.99:
                tk_copy = self.player_token_surf.copy()
                tk_copy.set_alpha(int(255 * self.player_alpha))
                surface.blit(tk_copy, (token_x, token_y))
            else:
                surface.blit(self.player_token_surf, (token_x, token_y))

    def focus_camera_on_player(self, instant: bool = True) -> None:
        """Centra la cámara exactamente sobre la posición actual del personaje en el mapa."""
        target_x = max(0.0, min(float(self.camera.max_x), self.player_pos[0] - self.screen_w / 2.0))
        target_y = max(0.0, min(float(self.camera.max_y), self.player_pos[1] - self.screen_h / 2.0))
        self.intro_target_pos = (target_x, target_y)
        if instant:
            self.camera.set_pos(target_x, target_y)
        else:
            self.camera.target_x = target_x
            self.camera.target_y = target_y

    def enter(self, params: Optional[dict] = None) -> None:
        if params and "character_id" in params:
            self.character_id = params["character_id"]
            self._load_character_bust()
            self._build_player_token()
            self._load_player_chibi()

        # Enfocar la cámara en el personaje para no perderlo al entrar o al volver de un nivel
        self.focus_camera_on_player(instant=True)
        self.cinematic_timer = self.cinematic_duration
        self._has_done_intro_pan = True

        # Persistir personaje seleccionado y posición de cámara enfocada
        self.save_current_state()

        # Asegurar estado limpio de diálogos y popups
        self.show_intro_dialog = False
        self.show_victory_modal = False

        # Mostrar diálogo de bienvenida de la Paloma la primera vez que se entra a una partida limpia
        progress = self.settings.get_story_progress()
        is_fresh_story = (
            not progress.get("completed_microgames")
            and int(progress.get("high_score", 0)) == 0
            and int(progress.get("current_node_id", 0)) == 0
        )
        if not self.intro_dialog_shown and is_fresh_story:
            self.intro_dialog_shown = True
            welcome_cfg = PALOMA_STORY_DIALOGS.get("welcome", {})
            if welcome_cfg:
                self.open_paloma_dialog(
                    pages=welcome_cfg.get("pages", []),
                    speaker=welcome_cfg.get("speaker", "PALOMA DE CURRAMBA"),
                    badge="BIENVENIDO A BARRANQUILLA WARE",
                    voice_prefix=welcome_cfg.get("voice_clip_prefix", "")
                )

        # Música continua de exploración sin cortes
        cafe_track = "cafe_bistro_mapa.ogg" if os.path.exists(os.path.join("assets", "cafe_bistro_mapa.ogg")) else "cafe_bistro_mapa.mp3"
        self.audio.play_bgm(cafe_track)

    def handle_event(self, event: pygame.event.Event) -> None:
        # 1. DevTool intercepta eventos si está activo
        if hasattr(self, "dev_tool"):
            p_rects = {k: v["rect"] for k, v in self.poi_registry.items()} if hasattr(self, "poi_registry") else None
            if self.dev_tool.handle_event(event, (self.camera.x, self.camera.y), poi_rects=p_rects):
                return

        # Mientras se muestra el aviso de trofeo, el mapa no recibe eventos
        if hasattr(self, "avisoTrofeo") and self.avisoTrofeo.estaOcupado():
            self.avisoTrofeo.handle_event(event)
            return

        # Interacción con el diálogo acuarela de la Paloma
        if getattr(self, "paloma_dialog_open", False):
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e):
                self.advance_paloma_dialog()
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.paloma_dialog_open = False
                self.paloma_dialog_on_finish = None
                if hasattr(self.audio, "play_hover"):
                    self.audio.play_hover()
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.advance_paloma_dialog()
                return
            return

        # Interacción con la viñeta introductoria legacy
        if self.show_intro_dialog:
            if (event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE)) or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                self.show_intro_dialog = False
                if hasattr(self.audio, "play_click"):
                    self.audio.play_click()
                return

        # Interacción con el modal de Victoria del Carnaval
        if self.show_victory_modal:
            if self.btn_vic_explore.handle_event(event):
                return
            if self.btn_vic_menu.handle_event(event):
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._close_victory_modal()
                return
            return

        # Interacción con la barra de navegación lateral izquierda (SideNavDrawer)
        if hasattr(self, "side_drawer") and self.side_drawer.handle_event(event):
            return

        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_m):
            if self.quest_card_open:
                self._close_quest_card()
                return
            self._open_pause_menu()
            return

        # Si la tarjeta de misión está abierta, interacción con la tarjeta
        if self.quest_card_open:
            consumed_play = self.btn_quest_play.handle_event(event)
            consumed_close = self.btn_quest_close.handle_event(event)
            if consumed_play or consumed_close:
                return

            # Click fuera de la tarjeta para cerrar, o clic en sello superior derecho como respaldo
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                card_rect = pygame.Rect(
                    self.screen_w // 2 - self.quest_card_w // 2,
                    self.screen_h // 2 - self.quest_card_h // 2,
                    self.quest_card_w,
                    self.quest_card_h
                )
                if not card_rect.collidepoint(event.pos):
                    self._close_quest_card()
                else:
                    tr_x = card_rect.left + int(self.quest_card_w * 0.86)
                    tr_y = card_rect.top + int(self.quest_card_h * 0.11)
                    if (event.pos[0] - tr_x) ** 2 + (event.pos[1] - tr_y) ** 2 < 34 ** 2:
                        self._close_quest_card()
            return

        # Si el menú está abierto, interacción exclusiva con el Drawer
        if self.menu_open:
            drawer_x = int(self.screen_w - self.drawer_w * self.menu_anim_t)

            # Click fuera del Drawer para cerrar
            if event.type == pygame.MOUSEBUTTONDOWN and event.pos[0] < drawer_x:
                self._toggle_menu()
                return

            # Delegar eventos a los botones del Drawer con offset de coordenadas
            if hasattr(event, "pos"):
                rel_pos = (event.pos[0] - drawer_x, event.pos[1])
                drawer_event = pygame.event.Event(event.type, {**event.dict, "pos": rel_pos})
                for btn in self.drawer_buttons:
                    btn.handle_event(drawer_event)
            return

        # Botón hamburguesa flotante para abrir menú con mouse
        # Con el aspecto nuevo abre apenas se hace clic, con un área un poco más grande que su dibujo
        if getattr(self, "menuMapaListo", False) and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_menu_toggle.rect.inflate(20, 20).collidepoint(event.pos):
                self._toggle_menu()
                return
        consumed = self.btn_menu_toggle.handle_event(event)
        if consumed and event.type != pygame.MOUSEMOTION:
            return

        # Conmutadores interactivos de Clima, Acción de Misión y Navegación D-Pad
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.set_weather("day")
            elif event.key == pygame.K_2:
                self.set_weather("sunset")
            elif event.key == pygame.K_3:
                self.set_weather("night")
            elif event.key == pygame.K_4:
                self.set_weather("rain")
            elif event.key == pygame.K_c:
                self.cycle_weather()
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                nearest_poi = self._get_nearest_poi_to_pos(self.player_pos, max_dist=280.0)
                if nearest_poi:
                    self._notify_poi_arrival(nearest_poi)
                    return

            # Controles D-Pad / Flechas / WASD en intersecciones (Opción 1.C)
            dpad_dirs = {
                pygame.K_UP: (0.0, -1.0),
                pygame.K_w: (0.0, -1.0),
                pygame.K_DOWN: (0.0, 1.0),
                pygame.K_s: (0.0, 1.0),
                pygame.K_LEFT: (-1.0, 0.0),
                pygame.K_a: (-1.0, 0.0),
                pygame.K_RIGHT: (1.0, 0.0),
                pygame.K_d: (1.0, 0.0),
            }
            if event.key in dpad_dirs:
                if self.camera.is_dragging:
                    self.camera.stop_drag()
                if self._handle_dpad_move(dpad_dirs[event.key]):
                    return

        # Arrastre de cámara con mouse en toda la superficie y click en POIs
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            self.cinematic_timer = self.cinematic_duration  # Interrumpir cinemática si el usuario interactúa
            self.mouse_down_pos = event.pos
            self.camera.start_drag(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button in (1, 3):
            self.camera.stop_drag()
            # Point & Click sobre nodos y POIs (Opción 1.C)
            if hasattr(self, "mouse_down_pos") and not self.menu_open and not (hasattr(self, "side_drawer") and self.side_drawer.is_blocking()):
                dist = math.hypot(event.pos[0] - self.mouse_down_pos[0], event.pos[1] - self.mouse_down_pos[1])
                if dist < 10.0:
                    world_click = (event.pos[0] + self.camera.x, event.pos[1] + self.camera.y)

                    # 1. ¿Click directo sobre un nodo de la red vial?
                    clicked_node = self._find_node_near_world_pos(world_click, max_dist=28.0)
                    if clicked_node is not None and clicked_node["id"] != self.player_node_id:
                        path = self._find_shortest_path(self.player_node_id, clicked_node["id"])
                        if path:
                            self._start_path_travel(path)
                            return

                    # 2. ¿Click sobre un nivel principal o secreto jugable?
                    for p_key in STORY_PLAYABLE_POIS:
                        p_info = self.poi_registry.get(p_key)
                        if not p_info:
                            continue
                        if p_info["rect"].collidepoint(world_click) or getattr(self, f"{p_key}_hover", False):
                            target_node = self._get_poi_target_node(p_key)
                            if target_node is not None:
                                if self.player_node_id == target_node and not self.player_is_moving:
                                    self._notify_poi_arrival(p_key)
                                else:
                                    path = self._find_shortest_path(self.player_node_id, target_node)
                                    if path:
                                        self._start_path_travel(path, target_poi=p_key)
                            return
        elif event.type == pygame.MOUSEMOTION:
            self.camera.update_drag(event.pos)

    def update(self, dt: float) -> None:
        self.timer += dt
        if self.toast_timer > 0.0:
            self.toast_timer = max(0.0, self.toast_timer - dt)
            if self.toast_timer == 0.0:
                self.toast_msg = None
        if hasattr(self, "dev_tool"):
            self.dev_tool.update(dt)

        # Animación suave del menú lateral (Drawer)
        drawer_target = 1.0 if self.menu_open else 0.0
        self.menu_anim_t += (drawer_target - self.menu_anim_t) * min(1.0, dt * 14.0)

        # Animación suave de la tarjeta de misión (Quest Card)
        quest_target = 1.0 if self.quest_card_open else 0.0
        self.quest_card_anim_t += (quest_target - self.quest_card_anim_t) * min(1.0, dt * 16.0)

        # Animación suave del cuadro de diálogo de la Paloma
        paloma_target = 1.0 if getattr(self, "paloma_dialog_open", False) else 0.0
        self.paloma_dialog_anim_t += (paloma_target - self.paloma_dialog_anim_t) * min(1.0, dt * 16.0)

        if self.save_feedback_timer > 0.0:
            self.save_feedback_timer -= dt

        # Si el menú está desplegándose, actualizar botones del drawer
        if self.menu_anim_t > 0.01:
            for btn in self.drawer_buttons:
                btn.update(dt)

        self.btn_menu_toggle.update(dt)

        # Actualizar SocialHUD y SideNavDrawer izquierdo
        if hasattr(self, "social_hud"):
            self.social_hud.update(dt)
        if hasattr(self, "side_drawer"):
            self.side_drawer.update(dt)
        if hasattr(self, "avisoTrofeo"):
            self.avisoTrofeo.update(dt)

        # Actualizar confeti del Carnaval
        for cf in self.carnaval_confetti:
            cf["y"] += cf["vy"] * dt
            cf["x"] += cf["vx"] * dt
            if cf["y"] > self.screen_h:
                cf["y"] = -10
                cf["x"] = float(random.randint(0, self.screen_w))

        if self.show_victory_modal:
            self.btn_vic_explore.update(dt)
            self.btn_vic_menu.update(dt)
            return

        if getattr(self, "paloma_dialog_open", False):
            return

        if self.show_intro_dialog:
            return

        # El personaje espera quieto mientras se muestra el aviso de trofeo
        if hasattr(self, "avisoTrofeo") and self.avisoTrofeo.estaOcupado():
            return

        # Si el menú, la tarjeta de misión o el drawer lateral están activos, pausar arrastre del mapa
        if self.menu_open or self.quest_card_open or (hasattr(self, "side_drawer") and self.side_drawer.is_blocking()):
            return

        # ----------------- NAVEGACIÓN Y MOVIMIENTO DEL JUGADOR -----------------
        if self.player_is_moving and self.player_path_edges:
            self.player_anim_timer += dt
            curr_edge = self.player_path_edges[self.player_edge_idx]

            # Manejo de túneles ocultos (fade out del avatar)
            is_hid = curr_edge.get("hidden", False)
            if is_hid:
                self.player_alpha = max(0.0, self.player_alpha - dt * 9.0)
            else:
                self.player_alpha = min(1.0, self.player_alpha + dt * 9.0)

            # Avance a velocidad constante física
            self.player_edge_dist += self.player_speed * dt
            if self.player_edge_dist >= curr_edge["total_dist"]:
                # Llegada al nodo final de esta arista
                pts = curr_edge["points"]
                self.player_pos = (float(pts[-1][0]), float(pts[-1][1]))
                self.player_node_id = curr_edge["to"]
                self.settings.update_story_progress(current_node_id=self.player_node_id)
                self.revisarVueltaGlorieta(self.player_node_id)

                self.player_edge_idx += 1
                if self.player_edge_idx >= len(self.player_path_edges):
                    # Fin de la ruta completa
                    self.player_is_moving = False
                    self.player_path_edges = []
                    self.player_edge_dist = 0.0
                    self.player_alpha = 1.0
                    if self.player_target_poi:
                        self._notify_poi_arrival(self.player_target_poi)
                        self.player_target_poi = None
                else:
                    self.player_edge_dist = 0.0
            else:
                # Interpolación exacta sobre los puntos de la curva Bézier
                cum = curr_edge["cum_dists"]
                pts = curr_edge["points"]
                d = self.player_edge_dist
                idx = 0
                while idx < len(cum) - 2 and cum[idx + 1] < d:
                    idx += 1
                p_a = pts[idx]
                p_b = pts[idx + 1]
                seg_len = cum[idx + 1] - cum[idx]
                t = (d - cum[idx]) / max(1e-4, seg_len)
                new_px = p_a[0] + (p_b[0] - p_a[0]) * t
                new_py = p_a[1] + (p_b[1] - p_a[1]) * t

                # Determinar orientación hacia la que camina
                diff_x = new_px - self.player_pos[0]
                if abs(diff_x) > 0.3:
                    self.player_facing_right = (diff_x > 0)

                self.player_pos = (new_px, new_py)
        else:
            self.player_anim_timer += dt
            self.player_alpha = min(1.0, self.player_alpha + dt * 8.0)

        # Detección de Hover sobre niveles principales y secretos jugables.
        mouse_pos = pygame.mouse.get_pos()
        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)
        world_mouse = (mouse_pos[0] + cam_x, mouse_pos[1] + cam_y)
        for p_key, p_info in self.poi_registry.items():
            if p_key not in STORY_PLAYABLE_POIS:
                setattr(self, f"{p_key}_hover", False)
                continue
            setattr(self, f"{p_key}_hover", p_info["rect"].collidepoint(world_mouse))

        # Actualizar chispitas doradas flotantes de todos los POIs
        for p_key, sparkle_list in self.poi_sparkles.items():
            r = self.poi_registry[p_key]["rect"]
            for sp in sparkle_list:
                sp["rel_y"] -= sp["vy"] * dt
                sp["life"] += dt * 0.9
                if sp["rel_y"] < -20 or sp["life"] > 1.0:
                    sp["rel_y"] = float(r.height - 15)
                    sp["life"] = 0.0

        # Brisa caribeña continua sobre las nubes algodonosas
        for cloud in self.clouds:
            cloud["x"] += cloud["vx"] * dt
            if cloud["x"] > self.world_w + 250:
                cloud["x"] = -350.0

        # Lluvia tropical caribeña
        if self.current_weather == "rain":
            for drop in self.rain_drops:
                drop["y"] += drop["speed"] * dt
                drop["x"] -= 160.0 * dt
                if drop["y"] > self.screen_h + 30:
                    drop["y"] = -30
                    drop["x"] = (drop["x"] + self.screen_w) % self.screen_w

        # Animación cinemática suave al ingresar
        if self.cinematic_timer < self.cinematic_duration:
            self.cinematic_timer += dt
            t = min(1.0, self.cinematic_timer / self.cinematic_duration)
            t_smooth = t * t * (3.0 - 2.0 * t)
            cur_x = self.intro_start_pos[0] + (self.intro_target_pos[0] - self.intro_start_pos[0]) * t_smooth
            cur_y = self.intro_start_pos[1] + (self.intro_target_pos[1] - self.intro_start_pos[1]) * t_smooth
            self.camera.x = cur_x
            self.camera.y = cur_y
            self.camera.target_x = cur_x
            self.camera.target_y = cur_y
        else:
            # Mantener la cámara siempre enfocada en el personaje (salvo cuando el usuario arrastra con el mouse)
            if not self.camera.is_dragging:
                self.camera.target_x = self.player_pos[0] - self.screen_w / 2.0
                self.camera.target_y = self.player_pos[1] - self.screen_h / 2.0
            self.camera.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        # 1. Renderizar el mapa mundial continuo con offset de cámara cinética
        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)
        surface.blit(self.world_map, (-cam_x, -cam_y))

        # 2. Hitos de parada en las calles (is_stop)
        self._render_level_stops(surface, cam_x, cam_y)

        # 3. Avatar del jugador (sombra, token con rostro, rebote y túnel)
        self._render_player_avatar(surface, cam_x, cam_y)

        # 4. Renderizar efectos dinámicos de niveles principales y secretos.
        progress = self.settings.get_story_progress()
        completed_games = progress.get("completed_microgames", [])

        for p_key in STORY_PLAYABLE_POIS:
            p_info = self.poi_registry.get(p_key)
            if not p_info:
                continue
            p_rect = p_info["rect"]
            p_screen_x = p_rect.x - cam_x
            p_screen_y = p_rect.y - cam_y

            if -500 < p_screen_x < self.screen_w + 500 and -500 < p_screen_y < self.screen_h + 500:
                is_hovered = getattr(self, f"{p_key}_hover", False)
                pulse = math.sin(self.timer * 2.5 + (0.8 if p_key == 'metropolitano' else 0.0)) * 0.5 + 0.5
                glow_alpha = int(140 + 75 * pulse) if not is_hovered else 240
                glow_copy = self.poi_ground_glow.copy()
                glow_copy.set_alpha(glow_alpha)
                surface.blit(glow_copy, glow_copy.get_rect(center=(p_screen_x + p_rect.width // 2, p_screen_y + p_rect.height - 10)))

                sparkle_list = self.poi_sparkles.get(p_key, [])
                for sp in sparkle_list:
                    sp_x = p_screen_x + sp["rel_x"] + math.sin(self.timer * 2.0 + sp["phase"]) * 6.0
                    sp_y = p_screen_y + sp["rel_y"]
                    fade = math.sin(sp["life"] * math.pi)
                    sp_alpha = int(220 * max(0.0, fade))
                    self._sp_surf.fill((0, 0, 0, 0))
                    pygame.draw.circle(self._sp_surf, (255, 235, 110, sp_alpha), (8, 8), max(1, int(sp["size"] * fade)))
                    surface.blit(self._sp_surf, (sp_x - 8, sp_y - 8))

                bob_y = math.sin(self.timer * 2.8) * 5.0 - (6.0 if is_hovered else 0.0)
                pin_center_x = p_screen_x + p_rect.width // 2
                pin_center_y = p_screen_y - 18 + int(bob_y)

                # Si el microjuego de la locación fue completado, mostrar Estrella Dorada
                is_cleared = p_info["microgame_id"] in completed_games
                pin_to_draw = self.poi_star_surf if is_cleared else self.poi_pin_surf
                surface.blit(pin_to_draw, pin_to_draw.get_rect(center=(pin_center_x, pin_center_y)))

        # 3. Renderizar nubes algodonosas caribeñas con profundidad parallax
        for cloud in self.clouds:
            cloud_screen_x = int(cloud["x"] - cam_x * cloud["parallax"])
            cloud_screen_y = int(cloud["y"] - cam_y * cloud["parallax"] + math.sin(self.timer * 1.5 + cloud["bob"]) * 2.5)

            cw, ch = cloud["surf"].get_size()
            if -cw < cloud_screen_x < self.screen_w + cw and -ch < cloud_screen_y < self.screen_h + ch:
                surface.blit(cloud["surf"], (cloud_screen_x, cloud_screen_y))

        # 4. Shader de atmósfera para Clima y Ciclo Día / Atardecer / Noche / Lluvia
        overlay = self.weather_overlays.get(self.current_weather)
        if overlay is not None:
            surface.blit(overlay, (0, 0))

        # 5. Trazas de lluvia tropical caribeña en pantalla si el clima es 'rain'
        if self.current_weather == "rain":
            for drop in self.rain_drops:
                dx1, dy1 = int(drop["x"]), int(drop["y"])
                dx2 = dx1 - int(drop["length"] * 0.45)
                dy2 = dy1 + int(drop["length"])
                color = (205, 230, 255, drop["alpha"])
                pygame.draw.line(surface, color, (dx1, dy1), (dx2, dy2), 1)

        # 6. HUD de Redes Sociales (Seguidores, Likes, Logros)
        if hasattr(self, "social_hud"):
            self.social_hud.render(surface)

        # 7. Barra de Navegación Lateral Izquierda (SideNavDrawer)
        if hasattr(self, "side_drawer"):
            self.side_drawer.render(surface)

        # 8. Botón circular flotante de menú hamburguesa (Pausa actual)
        if self.menu_anim_t < 0.95:
            self.btn_menu_toggle.render(surface)

        # 9. Renderizar Drawer Desplegable de Pausa y Guardado
        if self.menu_anim_t > 0.01:
            self._render_drawer_menu(surface)

        # 10. Renderizar Tarjeta Modal de Misión / Microjuego
        if self.quest_card_anim_t > 0.01:
            self._render_quest_card(surface)

        # 10B. Renderizar Diálogo Acuarela de la Paloma Guía
        if getattr(self, "paloma_dialog_anim_t", 0.0) > 0.01:
            self._render_paloma_dialog(surface)

        # 9. Renderizar Viñeta Narrativa de Bienvenida
        if self.show_intro_dialog:
            self._render_intro_dialog(surface)

        # 10. Renderizar Celebración de Victoria del Carnaval
        if self.show_victory_modal:
            self._render_victory_modal(surface)

        # 10C. Aviso de trofeo ganado con sus fuegos artificiales y el vuelo al panel
        if hasattr(self, "avisoTrofeo"):
            self.avisoTrofeo.render(surface)

        # 11. Renderizar Herramienta de Desarrollo Visual (DevTool F1)
        if hasattr(self, "dev_tool"):
            poi_rects = {k: v["rect"] for k, v in self.poi_registry.items()}
            self.dev_tool.render(surface, (self.camera.x, self.camera.y), poi_rects)

        # 12. Renderizar Toast Informativo flotante
        if self.toast_msg and self.toast_timer > 0.0:
            self._render_toast(surface)

    def _render_toast(self, surface: pygame.Surface) -> None:
        """Dibuja un banner / toast animado centrado en la parte superior."""
        alpha = min(255, int(255 * (self.toast_timer / 0.5))) if self.toast_timer < 0.5 else 255
        txt_surf = self.font_toast.render(self.toast_msg, True, (255, 255, 255))
        padding_x, padding_y = 36, 16
        bw = txt_surf.get_width() + padding_x * 2
        bh = txt_surf.get_height() + padding_y * 2
        toast_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(toast_surf, (20, 24, 38, int(230 * (alpha / 255.0))), (0, 0, bw, bh), border_radius=18)
        pygame.draw.rect(toast_surf, (245, 195, 60, int(240 * (alpha / 255.0))), (0, 0, bw, bh), width=3, border_radius=18)
        txt_surf.set_alpha(alpha)
        toast_surf.blit(txt_surf, (padding_x, padding_y))
        rect = toast_surf.get_rect(center=(self.screen_w // 2, 85))
        surface.blit(toast_surf, rect)

    def _render_drawer_menu(self, surface: pygame.Surface) -> None:
        """Renderiza el panel lateral desplegable de opciones y guardado."""
        # Menú nuevo con la ventana de flores
        if self.dibujarMenuMapa(surface):
            return

        # A) Oscurecimiento de fondo
        dim_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        dim_surf.fill((10, 16, 28, int(150 * self.menu_anim_t)))
        surface.blit(dim_surf, (0, 0))

        # B) Superficie del Drawer
        drawer_surf = pygame.Surface((self.drawer_w, self.screen_h), pygame.SRCALPHA)
        pygame.draw.rect(drawer_surf, (15, 22, 36, 240), (0, 0, self.drawer_w, self.screen_h))
        pygame.draw.line(drawer_surf, (240, 195, 95, 210), (0, 0), (0, self.screen_h), 3)

        # Título
        txt_title = self.font_drawer_title.render("MODO HISTORIA", True, (255, 245, 230))
        drawer_surf.blit(txt_title, txt_title.get_rect(center=(self.drawer_w // 2, 75)))

        # Subtítulo y estado del personaje
        char_label = self.character_id.capitalize()
        txt_sub = self.font_drawer_sub.render(f"Explorando con: {char_label}", True, (245, 205, 115))
        drawer_surf.blit(txt_sub, txt_sub.get_rect(center=(self.drawer_w // 2, 112)))

        # Separador decorativo
        pygame.draw.line(drawer_surf, (65, 90, 125, 160), (40, 140), (self.drawer_w - 40, 140), 1)

        # Información de partida guardada
        txt_auto = self.font_drawer_sub.render("Auto-guardado activo en config", True, (155, 185, 215))
        drawer_surf.blit(txt_auto, txt_auto.get_rect(center=(self.drawer_w // 2, 175)))

        # Cartel de confirmación de guardado manual
        if self.save_feedback_timer > 0.0:
            badge_w, badge_h = 320, 38
            badge_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
            pygame.draw.rect(badge_surf, (35, 115, 65, 225), (0, 0, badge_w, badge_h), border_radius=10)
            pygame.draw.rect(badge_surf, (110, 245, 150), (0, 0, badge_w, badge_h), width=2, border_radius=10)
            txt_ok = self.font_drawer_save.render("PARTIDA GUARDADA", True, (220, 255, 230))
            badge_surf.blit(txt_ok, txt_ok.get_rect(center=(badge_w // 2, badge_h // 2)))
            drawer_surf.blit(badge_surf, badge_surf.get_rect(center=(self.drawer_w // 2, 225)))

        # Renderizar botones del Drawer
        for btn in self.drawer_buttons:
            btn.render(drawer_surf)

        # Posición horizontal animada (slide-in desde la derecha)
        drawer_x = int(self.screen_w - self.drawer_w * self.menu_anim_t)
        surface.blit(drawer_surf, (drawer_x, 0))

    def textoConContorno(self, fuente, texto: str, color, colorContorno) -> pygame.Surface:
        # Texto con un contorno parejo alrededor para que se lea sobre los botones
        cuerpo = fuente.render(texto, True, color)
        borde = fuente.render(texto, True, colorContorno)
        lienzo = pygame.Surface((cuerpo.get_width() + 6, cuerpo.get_height() + 6), pygame.SRCALPHA)
        for dx in (-3, -2, 0, 2, 3):
            for dy in (-3, -2, 0, 2, 3):
                if abs(dx) + abs(dy) >= 3:
                    lienzo.blit(borde, (3 + dx, 3 + dy))
        lienzo.blit(cuerpo, (3, 3))
        return lienzo

    def cambiarImagenBoton(self, boton: UIButton, imagen: pygame.Surface, centro: Tuple[int, int]) -> None:
        # Cambia la imagen y el lugar de un botón sin cambiar lo que hace al pulsarlo
        boton.normal_sprite = imagen
        boton.width, boton.height = imagen.get_size()
        boton.center_x, boton.center_y = centro
        boton.rect = pygame.Rect(0, 0, boton.width, boton.height)
        boton.rect.center = centro

    def ponerContorno(self, imagen: pygame.Surface, color, grosor: int) -> pygame.Surface:
        # Pega la silueta de la imagen en el color pedido, corrida en círculo, por debajo de la imagen
        conContorno = pygame.Surface((imagen.get_width() + grosor * 2, imagen.get_height() + grosor * 2), pygame.SRCALPHA)
        silueta = pygame.mask.from_surface(imagen, 100).to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
        for grados in range(0, 360, 15):
            dx = round(math.cos(math.radians(grados)) * grosor)
            dy = round(math.sin(math.radians(grados)) * grosor)
            conContorno.blit(silueta, (grosor + dx, grosor + dy))
        conContorno.blit(imagen, (grosor, grosor))
        return conContorno

    def prepararMenuMapa(self) -> None:
        """Carga la ventana y los botones nuevos del menú del mapa y el botón para abrirlo."""
        self.menuMapaListo = False
        try:
            # El panel se ensancha y llega de arriba a abajo para que los botones quepan con aire a los lados
            self.drawer_w = 560
            alto = self.screen_h
            # El papel de la ventana va del 18% al 83% del ancho; su centro queda un poco a la derecha
            self.centroPapelMenu = int(self.drawer_w * 0.508)
            ventana = self.assets.cargarSinFondo(os.path.join("Interfaz", "ventanaMenuPausa.jpg"), self.drawer_w)
            self.ventanaMenuMapa = pygame.transform.smoothscale(ventana, (self.drawer_w, alto))
            morado = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonMorado.jpg"), 300)
            rojo = pygame.transform.smoothscale(
                self.assets.cargarSinFondo(os.path.join("Interfaz", "botonRojo.jpg"), 300), morado.get_size())
            self.fuenteTituloMenu = self.assets.cargarFuenteCuento(44)
            self.fuenteTextoMenu = self.assets.cargarFuenteCuento(22)
            fuenteBoton = self.assets.cargarFuenteCuento(36)

            # Cada botón guarda su versión morada y la roja que se ve al pasar el mouse
            botones = [
                (self.btn_resume, "Reanudar", 360),
                (self.btn_save_game, "Guardar partida", 448),
                (self.btn_calibrate_pointer, "Calibrar lápiz", 624),
                (self.btn_settings, "Ajustes", 712),
                (self.btn_exit_map, "Salir al menú", 800),
            ]
            self.botonesMenuMapa = []
            for boton, texto, y in botones:
                versiones = []
                for fondo, contorno in ((morado, (70, 30, 110)), (rojo, (120, 26, 34))):
                    imagen = fondo.copy()
                    letras = self.textoConContorno(fuenteBoton, texto, (255, 248, 236), contorno)
                    imagen.blit(letras, letras.get_rect(center=(imagen.get_width() // 2, imagen.get_height() // 2 - 3)))
                    versiones.append(imagen)
                self.cambiarImagenBoton(boton, versiones[0], (self.centroPapelMenu, y))
                self.botonesMenuMapa.append((boton, versiones[0], versiones[1]))

            # Los botones de música y sonido quedan entre guardar y calibrar
            self.btn_drawer_music.center_x, self.btn_drawer_music.center_y = (self.centroPapelMenu - 60, 536)
            self.btn_drawer_music.rect.center = (self.centroPapelMenu - 60, 536)
            self.btn_drawer_sound.center_x, self.btn_drawer_sound.center_y = (self.centroPapelMenu + 60, 536)
            self.btn_drawer_sound.rect.center = (self.centroPapelMenu + 60, 536)

            # Botón nuevo para abrir el menú
            botonMenu = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonMenu.jpg"), 76)
            # Contorno rojo más oscuro de la misma familia para que resalte sobre el mapa
            botonMenu = self.ponerContorno(botonMenu, (128, 52, 48), 4)
            self.cambiarImagenBoton(self.btn_menu_toggle, botonMenu, (1855, 58))
            self.menuMapaListo = True
        except Exception as e:
            print(f"Aviso: no se pudo cargar el menú nuevo del mapa: {e}")

    def dibujarMenuMapa(self, surface: pygame.Surface) -> bool:
        if not getattr(self, "menuMapaListo", False):
            return False

        # Oscurece el mapa multiplicando sus colores, según qué tan abierto esté el menú
        tono = [int(255 - (255 - c) * self.menu_anim_t) for c in (120, 112, 136)]
        surface.fill(tono, special_flags=pygame.BLEND_RGB_MULT)

        panel = pygame.Surface((self.drawer_w, self.screen_h), pygame.SRCALPHA)
        panel.blit(self.ventanaMenuMapa, (0, 0))

        cafe = (110, 68, 38)
        titulo = self.textoConContorno(self.fuenteTituloMenu, "Modo historia", (110, 62, 150), (255, 250, 238))
        panel.blit(titulo, titulo.get_rect(center=(int(self.drawer_w * 0.56), 200)))
        explorando = self.fuenteTextoMenu.render(f"Explorando con {self.character_id.capitalize()}", True, cafe)
        panel.blit(explorando, explorando.get_rect(center=(int(self.drawer_w * 0.56), 248)))

        if self.save_feedback_timer > 0.0:
            aviso = self.fuenteTextoMenu.render("Partida guardada", True, (56, 146, 76))
        else:
            aviso = self.fuenteTextoMenu.render("Guardado automático", True, (150, 118, 90))
        panel.blit(aviso, aviso.get_rect(center=(int(self.drawer_w * 0.56), 284)))

        # Morado normal y rojo cuando el mouse está encima
        for boton, morado, rojo in self.botonesMenuMapa:
            boton.normal_sprite = rojo if boton.is_hovered else morado
        for boton in self.drawer_buttons:
            boton.render(panel)

        drawerX = int(self.screen_w - self.drawer_w * self.menu_anim_t)
        surface.blit(panel, (drawerX, 0))
        return True

    def _render_quest_card(self, surface: pygame.Surface) -> None:
        """Renderiza la tarjeta modal de misión del nodo activo con marco de acuarela ilustrado."""
        poi_info = self.poi_registry.get(self.active_poi, self.poi_registry["uninorte"])

        # A) Oscurecimiento de fondo
        dim_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        dim_surf.fill((10, 16, 28, int(160 * self.quest_card_anim_t)))
        surface.blit(dim_surf, (0, 0))

        # B) Tarjeta emergente
        cw = int(self.quest_card_w * (0.85 + 0.15 * self.quest_card_anim_t))
        ch = int(self.quest_card_h * (0.85 + 0.15 * self.quest_card_anim_t))
        card_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)

        # Fondo ilustrado de acuarela caribeña con flores y textura pergamino (sin halo blanco)
        if hasattr(self, "tex_quest_card") and self.tex_quest_card:
            card_scaled = pygame.transform.smoothscale(self.tex_quest_card, (cw, ch))
            card_surf.blit(card_scaled, (0, 0))
        else:
            pygame.draw.rect(card_surf, (255, 252, 244, 250), (0, 0, cw, ch), border_radius=28)
            pygame.draw.rect(card_surf, (245, 195, 80), (0, 0, cw, ch), width=4, border_radius=28)
            pygame.draw.rect(card_surf, (45, 30, 20), (0, 0, cw, ch), width=1, border_radius=28)

        # Emblema ornamental en el medallón superior derecho de la tarjeta (Estrella Currambera)
        if hasattr(self, "tex_emblema_estrella") and self.tex_emblema_estrella:
            star_size = int(cw * 0.08)
            star_scaled = pygame.transform.smoothscale(self.tex_emblema_estrella, (star_size, star_size))
            star_rect = star_scaled.get_rect(center=(int(cw * 0.855), int(ch * 0.105)))
            card_surf.blit(star_scaled, star_rect)

        # Encabezado: Título de la Locación con tamaño auto-adaptable y posición desahogada
        title_text = poi_info["title"]
        title_size = 26
        f_title = self.assets.get_font("arial rounded", title_size, bold=True)
        txt_title = f_title.render(title_text, True, (42, 26, 16))
        max_title_w = int(cw * 0.68)
        while txt_title.get_width() > max_title_w and title_size > 18:
            title_size -= 2
            f_title = self.assets.get_font("arial rounded", title_size, bold=True)
            txt_title = f_title.render(title_text, True, (42, 26, 16))
        card_surf.blit(txt_title, txt_title.get_rect(center=(cw // 2, int(ch * 0.20))))

        # Subtítulo de Distrito sobre cartucho de pergamino con flores ilustrado
        cart_w = int(cw * 0.56)
        if hasattr(self, "tex_quest_cartridge") and self.tex_quest_cartridge:
            cart_h = int(cart_w * (self.tex_quest_cartridge.get_height() / max(1, self.tex_quest_cartridge.get_width())))
            cart_scaled = pygame.transform.smoothscale(self.tex_quest_cartridge, (cart_w, cart_h))
            cart_rect = cart_scaled.get_rect(center=(cw // 2, int(ch * 0.282)))
            card_surf.blit(cart_scaled, cart_rect)
            txt_dist = self.font_quest_sub.render(poi_info["district"], True, (75, 45, 85))
            card_surf.blit(txt_dist, txt_dist.get_rect(center=cart_rect.center))
        else:
            txt_dist = self.font_quest_sub.render(poi_info["district"], True, (80, 55, 35))
            card_surf.blit(txt_dist, txt_dist.get_rect(center=(cw // 2, int(ch * 0.282))))

        # Separador decorativo ilustrado de pincelada y flor de trinitaria
        if hasattr(self, "tex_quest_sep") and self.tex_quest_sep:
            sep_w = int(cw * 0.58)
            sep_h = int(sep_w * (self.tex_quest_sep.get_height() / max(1, self.tex_quest_sep.get_width())))
            sep_scaled = pygame.transform.smoothscale(self.tex_quest_sep, (sep_w, max(12, sep_h)))
            card_surf.blit(sep_scaled, sep_scaled.get_rect(center=(cw // 2, int(ch * 0.352))))

        # Título del Microjuego / Rondas en terracota caribeño cálido
        txt_m_title = self.font_quest_btn.render(poi_info["microgame_title"], True, (215, 80, 45))
        card_surf.blit(txt_m_title, txt_m_title.get_rect(center=(cw // 2, int(ch * 0.405))))

        # Descripción de la misión en tinta café oscuro con espaciado cómodo
        desc_lines = poi_info["desc"]
        curr_y = int(ch * 0.455)
        for line in desc_lines:
            txt_line = self.font_quest_body.render(line, True, (55, 42, 30))
            card_surf.blit(txt_line, txt_line.get_rect(center=(cw // 2, curr_y)))
            curr_y += 32

        # Tarjeta de estado con sello de cera ilustrado sin colisión de texto
        progress = self.settings.get_story_progress()
        is_done = poi_info["microgame_id"] in progress.get("completed_microgames", [])
        status_text = "ESTADO: DESPEJADO (+100 PTS)" if is_done else "ESTADO: PENDIENTE POR DESPEJAR"
        status_col = (30, 125, 55) if is_done else (190, 95, 25)
        sello_tex = self.tex_sello_despejado if is_done else self.tex_sello_pendiente

        # Cápsula ilustrada de estado utilizando cinta de pergamino elegante
        stat_w = int(cw * 0.68)
        ribbon_tex = getattr(self, "tex_quest_status_ribbon", None) or getattr(self, "tex_quest_cartridge", None)
        if ribbon_tex:
            stat_h = int(stat_w * (ribbon_tex.get_height() / max(1, ribbon_tex.get_width())))
            stat_scaled = pygame.transform.smoothscale(ribbon_tex, (stat_w, max(38, stat_h)))
            stat_rect = stat_scaled.get_rect(center=(cw // 2, int(ch * 0.605)))
            card_surf.blit(stat_scaled, stat_rect)

            # Sello de cera en el lado izquierdo del cartucho
            sello_size = int(stat_h * 0.82)
            if sello_tex:
                sello_scaled = pygame.transform.smoothscale(sello_tex, (sello_size, sello_size))
                sello_x = stat_rect.left + 14
                card_surf.blit(sello_scaled, (sello_x, stat_rect.centery - sello_size // 2))

            txt_st = self.font_quest_sub.render(status_text, True, status_col)
            # Centrar el texto en el área disponible a la derecha del sello con amplio margen
            text_area_left = stat_rect.left + 14 + sello_size + 8
            text_area_right = stat_rect.right - 18
            card_surf.blit(txt_st, txt_st.get_rect(center=((text_area_left + text_area_right) // 2, stat_rect.centery)))
        else:
            txt_st = self.font_quest_sub.render(status_text, True, status_col)
            card_surf.blit(txt_st, txt_st.get_rect(center=(cw // 2, int(ch * 0.605))))

        # Renderizar en la pantalla centrado
        card_rect = card_surf.get_rect(center=(self.screen_w // 2, self.screen_h // 2))
        surface.blit(card_surf, card_rect)

        # Sincronizar posición de botones con la tarjeta animada
        # Botón Play centrado en la parte inferior
        self.btn_quest_play.set_center((self.screen_w // 2, card_rect.top + int(ch * 0.80)))
        # Botón Cerrar 'X' ilustrado arriba a la izquierda
        self.btn_quest_close.set_center((card_rect.left + int(cw * 0.13), card_rect.top + int(ch * 0.105)))

        # Botones de la tarjeta
        self.btn_quest_play.render(surface)
        self.btn_quest_close.render(surface)

    def _render_paloma_dialog(self, surface: pygame.Surface) -> None:
        """Renderiza el cuadro de diálogo acuarela oficial (text_dialog.png) acompañado por paloma_dialog.png."""
        self.story_ui.render_paloma_dialog(
            surface=surface,
            anim_t=self.paloma_dialog_anim_t,
            pages=self.paloma_dialog_pages,
            page_idx=self.paloma_dialog_page_idx,
            speaker=self.paloma_dialog_speaker,
            badge=self.paloma_dialog_badge,
            timer=self.timer,
            portrait_surf=self.paloma_dialog_portrait,
            dialog_box_surf=self.dialog_box_surf,
            font_speaker=self.font_paloma_speaker,
            font_badge=self.font_paloma_badge,
            font_body=self.font_paloma_body,
            font_hint=self.font_paloma_hint,
        )

    def _render_intro_dialog(self, surface: pygame.Surface) -> None:
        self.story_ui.render_intro_dialog(surface, self.character_bust, self.paloma_guide)

    def _render_victory_modal(self, surface: pygame.Surface) -> None:
        self.story_ui.render_victory_modal(
            surface=surface,
            confetti=self.carnaval_confetti,
            btn_explore=self.btn_vic_explore,
            btn_menu=self.btn_vic_menu,
        )
