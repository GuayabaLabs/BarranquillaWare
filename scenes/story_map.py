import os
import math
import random
from typing import Optional, Callable, Tuple
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.settings import SettingsManager
from ui.button import UIButton
from tools.map_dev_tool import MapDevTool
from scenes.slide_transition import SlideTransitionState

class Camera2D:
    """
    Cámara 2D suave con soporte de arrastre táctil (Mouse Drag),
    inercia cinética, navegación por teclado y clamping perimetral.
    """
    def __init__(self, world_w: int, world_h: int, view_w: int = 1920, view_h: int = 1080) -> None:
        self.world_w = world_w
        self.world_h = world_h
        self.view_w = view_w
        self.view_h = view_h

        self.max_x = max(0, world_w - view_w)
        self.max_y = max(0, world_h - view_h)

        # Posición inicial centrada en la ciudad
        self.x: float = self.max_x / 2.0
        self.y: float = self.max_y / 2.0
        self.target_x: float = self.x
        self.target_y: float = self.y

        # Velocidad cinética para inercia
        self.vel_x: float = 0.0
        self.vel_y: float = 0.0

        # Estados de arrastre
        self.is_dragging: bool = False
        self.drag_start_mouse: Tuple[int, int] = (0, 0)
        self.drag_start_cam: Tuple[float, float] = (0.0, 0.0)

    def set_pos(self, x: float, y: float) -> None:
        self.x = max(0.0, min(float(self.max_x), x))
        self.y = max(0.0, min(float(self.max_y), y))
        self.target_x = self.x
        self.target_y = self.y
        self.vel_x = 0.0
        self.vel_y = 0.0

    def start_drag(self, mouse_pos: Tuple[int, int]) -> None:
        self.is_dragging = True
        self.drag_start_mouse = mouse_pos
        self.drag_start_cam = (self.x, self.y)
        self.vel_x = 0.0
        self.vel_y = 0.0

    def update_drag(self, mouse_pos: Tuple[int, int]) -> None:
        if not self.is_dragging:
            return
        dx = mouse_pos[0] - self.drag_start_mouse[0]
        dy = mouse_pos[1] - self.drag_start_mouse[1]
        new_x = self.drag_start_cam[0] - dx
        new_y = self.drag_start_cam[1] - dy

        # Calcular velocidad para inercia
        self.vel_x = (new_x - self.x) * 18.0
        self.vel_y = (new_y - self.y) * 18.0

        self.x = max(0.0, min(float(self.max_x), new_x))
        self.y = max(0.0, min(float(self.max_y), new_y))
        self.target_x = self.x
        self.target_y = self.y

    def stop_drag(self) -> None:
        self.is_dragging = False

    def update(self, dt: float, move_dir: Tuple[float, float]) -> None:
        if not self.is_dragging:
            # Control por teclado (WASD / Flechas)
            speed = 950.0
            if move_dir[0] != 0.0 or move_dir[1] != 0.0:
                self.vel_x = move_dir[0] * speed
                self.vel_y = move_dir[1] * speed

            # Aplicar inercia y fricción
            friction = math.exp(-7.5 * dt)
            self.x += self.vel_x * dt
            self.y += self.vel_y * dt
            self.vel_x *= friction
            self.vel_y *= friction

            # Clamping a bordes del mapa mundial
            if self.x < 0.0:
                self.x = 0.0
                self.vel_x = 0.0
            elif self.x > self.max_x:
                self.x = self.max_x
                self.vel_x = 0.0

            if self.y < 0.0:
                self.y = 0.0
                self.vel_y = 0.0
            elif self.y > self.max_y:
                self.y = self.max_y
                self.vel_y = 0.0


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

        # 5. Paneo cinemático inicial (de Norte costero a Centro urbano)
        self.cinematic_timer: float = 0.0
        self.cinematic_duration: float = 1.2
        self.intro_start_pos = (self.camera.max_x * 0.45, 40.0)
        self.intro_target_pos = (self.camera.max_x * 0.50, self.camera.max_y * 0.50)
        self.camera.set_pos(self.intro_start_pos[0], self.intro_start_pos[1])

        # 6. Timer general y sistema de lluvia
        self.timer: float = 0.0
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

    def _build_world_map(self) -> None:
        """Carga y une los 4 cuadrantes, agregando Uninorte según el mapa de referencia."""
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
        self._integrate_mallorquin_poi()
        self._integrate_uninorte_poi()
        self._integrate_buenavista_poi()
        self._integrate_ventana_poi()
        self._integrate_malecon_poi()
        self._integrate_aleta_poi()
        self._integrate_metropolitano_poi()
        self._integrate_aeropuerto_poi()
        # Rutas automáticas eliminadas por solicitud del usuario (trazado manual vía DevTool)


    def _on_devtool_layout_changed(self) -> None:
        """Re-estampa dinámicamente el mapa mundial cuando se mueve o escala un POI en DevTool."""
        if not hasattr(self, "base_world_map") or self.base_world_map is None:
            return
        self.world_map = self.base_world_map.copy()
        self._render_street_shader()
        self._integrate_mallorquin_poi()
        self._integrate_uninorte_poi()
        self._integrate_buenavista_poi()
        self._integrate_ventana_poi()
        self._integrate_malecon_poi()
        self._integrate_aleta_poi()
        self._integrate_metropolitano_poi()
        self._integrate_aeropuerto_poi()
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

    def _integrate_mallorquin_poi(self) -> None:
        """Estampa la mejora del Parque Mallorquín (muelles, torre y manglares) en el noroeste."""
        try:
            self.mallorquin_rect = self._stamp_poi(
                "parque_mallorquin_mapa.png", "mallorquin", 266, 81, 672,
                shadow_color=(20, 35, 55, 42), shadow_offset=(8, 12)
            )
        except Exception as e:
            print(f"Aviso: no se pudo cargar parque_mallorquin_mapa.png: {e}")
            self.mallorquin_rect = pygame.Rect(266, 81, 672, 445)

    def _integrate_uninorte_poi(self) -> None:
        """Estampa el campus de Uninorte en su coordenada exacta."""
        try:
            self.uninorte_rect = self._stamp_poi(
                "uninorte_mapa.png", "uninorte", 145, 505, 390,
                shadow_color=(25, 40, 60, 48), shadow_offset=(10, 14)
            )
        except Exception as e:
            print(f"Aviso: no se pudo cargar uninorte_mapa.png: {e}")
            self.uninorte_rect = pygame.Rect(145, 505, 390, 270)

    def _integrate_metropolitano_poi(self) -> None:
        """Estampa el Estadio Metropolitano centrado armoniosamente en la gran glorieta ovalada sur."""
        try:
            self.metropolitano_rect = self._stamp_poi(
                "metropolitano_mapa.png", "metropolitano", 1725, 1154, 440,
                shadow_color=(20, 30, 50, 48), shadow_offset=(10, 14)
            )
        except Exception as e:
            print(f"Aviso: no se pudo cargar metropolitano_mapa.png: {e}")
            self.metropolitano_rect = pygame.Rect(1725, 1154, 440, 288)

    def _integrate_ventana_poi(self) -> None:
        """Estampa el monumento de la Ventana al Mundo centrado exactamente en la rotonda costera norte."""
        try:
            self.ventana_rect = self._stamp_poi(
                "ventana_al_mundo_mapa.png", "ventana", 1772, 275, 245,
                shadow_color=(20, 30, 50, 48), shadow_offset=(8, 12)
            )
        except Exception as e:
            print(f"Aviso: no se pudo cargar ventana_al_mundo_mapa.png: {e}")
            self.ventana_rect = pygame.Rect(1772, 275, 245, 290)

    def _integrate_malecon_poi(self) -> None:
        """Estampa la rueda panorámica Luna del Río a orillas del Río Magdalena."""
        try:
            self.malecon_rect = self._stamp_poi(
                "luna_del_rio_mapa.png", "malecon", 2780, 460, 350,
                shadow_color=(15, 35, 65, 55), shadow_offset=(10, 14)
            )
        except Exception as e:
            print(f"Aviso: no se pudo cargar luna_del_rio_mapa.png: {e}")
            self.malecon_rect = pygame.Rect(2780, 460, 350, 385)

    def _integrate_buenavista_poi(self) -> None:
        """Estampa el complejo comercial Buenavista & Mallplaza en el norte."""
        try:
            self.buenavista_rect = self._stamp_poi(
                "buenavista_mallplaza_mapa.png", "buenavista", 860, 380, 460,
                shadow_color=(25, 35, 55, 45), shadow_offset=(10, 14)
            )
        except Exception as e:
            print(f"Aviso: no se pudo cargar buenavista_mallplaza_mapa.png: {e}")
            self.buenavista_rect = pygame.Rect(860, 380, 460, 307)

    def _integrate_aleta_poi(self) -> None:
        """Estampa el monumento de la Aleta del Tiburón (Ventana de Campeones)."""
        try:
            self.aleta_rect = self._stamp_poi(
                "aleta_del_tiburon_mapa.png", "aleta", 2680, 720, 260,
                shadow_color=(20, 30, 50, 48), shadow_offset=(8, 12)
            )
        except Exception as e:
            print(f"Aviso: no se pudo cargar aleta_del_tiburon_mapa.png: {e}")
            self.aleta_rect = pygame.Rect(2680, 720, 260, 365)

    def _integrate_aeropuerto_poi(self) -> None:
        """Estampa la terminal aérea y pista del Aeropuerto Ernesto Cortissoz alineado en el sector sureste."""
        try:
            self.aeropuerto_rect = self._stamp_poi(
                "aeropuerto_ernesto_cortissoz_mapa.png", "aeropuerto", 2611, 1311, 540,
                shadow_color=(20, 30, 50, 48), shadow_offset=(10, 14)
            )
        except Exception as e:
            print(f"Aviso: no se pudo cargar aeropuerto_ernesto_cortissoz_mapa.png: {e}")
            self.aeropuerto_rect = pygame.Rect(2611, 1311, 540, 353)

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

    def _draw_overworld_routes(self) -> None:
        """Dibuja los senderos punteados luminosos que interconectan las 6 locaciones de la historia."""
        nodes = [
            (self.mallorquin_rect.centerx, self.mallorquin_rect.centery),
            (self.uninorte_rect.centerx, self.uninorte_rect.centery),
            (self.ventana_rect.centerx, self.ventana_rect.centery),
            (self.malecon_rect.centerx, self.malecon_rect.centery),
            (self.quad_w, self.quad_h),  # Centro de la ciudad (Guayacán Rosa)
            (self.metropolitano_rect.centerx, self.metropolitano_rect.centery),
            (self.aeropuerto_rect.centerx, self.aeropuerto_rect.centery)
        ]

        progress = self.settings.get_story_progress()
        completed = progress.get("completed_microgames", [])

        # Segmentos de la historia
        reqs = ["mallorquin_photo", "uninorte_sprint", "ventana_colores", "malecon_rueda", "metropolitano_penalty", "aeropuerto_aterrizaje"]

        for i in range(len(nodes) - 1):
            p1 = nodes[i]
            p2 = nodes[i + 1]
            dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            steps = int(dist // 22)

            is_active = (i < len(reqs) and reqs[i] in completed)
            dot_color = (255, 220, 80) if is_active else (255, 255, 255)
            dot_r = 5 if is_active else 3

            for s in range(steps):
                t = s / float(max(1, steps))
                arc = math.sin(t * math.pi) * 22.0
                nx = -(p2[1] - p1[1]) / max(1.0, dist)
                ny = (p2[0] - p1[0]) / max(1.0, dist)

                dx = int(p1[0] + (p2[0] - p1[0]) * t + nx * arc)
                dy = int(p1[1] + (p2[1] - p1[1]) * t + ny * arc)

                pygame.draw.circle(self.world_map, (20, 30, 45), (dx + 1, dy + 2), dot_r + 1)
                pygame.draw.circle(self.world_map, dot_color, (dx, dy), dot_r)

    def _init_poi_effects(self) -> None:
        """Inicializa el registro y efectos interactivos de todos los puntos de interés clave."""
        import random

        # Registro centralizado de Puntos de Interés (POIs) y sus microjuegos
        self.poi_registry = {
            "mallorquin": {
                "title": "ECORRESERVA MALLORQUÍN",
                "district": "DISTRITO ECOLÓGICO · NIVEL 01",
                "microgame_id": "mallorquin_photo",
                "microgame_title": "¡FOTOGRAFÍA AL FLAMENCO!",
                "desc": [
                    "¡Un flamenco rosado vuela entre los manglares!",
                    "Mueve el visor de la cámara y presiona ESPACIO",
                    "o haz click cuando esté centrado para la foto perfecta."
                ],
                "rect": self.mallorquin_rect
            },
            "uninorte": {
                "title": "CAMPUS UNINORTE",
                "district": "DISTRITO ACADÉMICO · NIVEL 02",
                "microgame_id": "uninorte_sprint",
                "microgame_title": "CARRERA AL AULA DE 6:30",
                "desc": [
                    "¡El profesor ya casi cierra la puerta del aula!",
                    "Pulsa repetidamente ESPACIO o haz click velozmente",
                    "para correr por el pasillo y llegar a tiempo."
                ],
                "rect": self.uninorte_rect
            },
            "ventana": {
                "title": "VENTANA AL MUNDO",
                "district": "DISTRITO MONUMENTAL · NIVEL 03",
                "microgame_id": "ventana_colores",
                "microgame_title": "¡ARMONIZA LOS CRISTALES!",
                "desc": [
                    "¡El monumento pide su panel de color armónico!",
                    "Pulsa el número del color (1-4) o haz click",
                    "en el botón correspondiente antes de 4 segundos."
                ],
                "rect": self.ventana_rect
            },
            "malecon": {
                "title": "GRAN MALECÓN DEL RÍO",
                "district": "DISTRITO TURÍSTICO · NIVEL 04",
                "microgame_id": "malecon_rueda",
                "microgame_title": "¡FRENA EN LA CIMA!",
                "desc": [
                    "¡La rueda panorámica Luna del Río gira a toda velocidad!",
                    "Presiona ESPACIO cuando la cabina dorada",
                    "pase por el arco verde superior para admirar el río."
                ],
                "rect": self.malecon_rect
            },
            "metropolitano": {
                "title": "ESTADIO METROPOLITANO",
                "district": "DISTRITO DEPORTIVO · NIVEL 05",
                "microgame_id": "metropolitano_penalty",
                "microgame_title": "EL PENAL DEL TIBURÓN",
                "desc": [
                    "¡Minuto 94 de la final en el Metropolitano!",
                    "Espera a que la mira apunte al ángulo y presiona",
                    "ESPACIO para cobrar el penal y cantar el gol."
                ],
                "rect": self.metropolitano_rect
            },
            "buenavista": {
                "title": "C.C. BUENAVISTA & MALLPLAZA",
                "district": "DISTRITO COMERCIAL · NORTE",
                "microgame_id": "buenavista_shopping",
                "microgame_title": "¡TARDE EN EL CENTRO COMERCIAL!",
                "desc": [
                    "¡El puente que une los mundos de compras caribeñas!",
                    "Muévete entre las tiendas y encuentra la mejor",
                    "oferta antes de que termine la tarde fresca."
                ],
                "rect": self.buenavista_rect
            },
            "aleta": {
                "title": "ALETA DEL TIBURÓN",
                "district": "VENTANA DE CAMPEONES",
                "microgame_id": "aleta_campeones",
                "microgame_title": "¡PASIÓN ROJIBLANCA!",
                "desc": [
                    "¡El gran monumento brilla junto al Río Magdalena!",
                    "Armoniza las aletas de colores y celebra el gol",
                    "con toda la hinchada tiburona."
                ],
                "rect": self.aleta_rect
            },
            "aeropuerto": {
                "title": "AEROPUERTO CORTISSOZ",
                "district": "DISTRITO AÉREO · NIVEL 06",
                "microgame_id": "aeropuerto_aterrizaje",
                "microgame_title": "¡ATERRIZA EN LA PISTA!",
                "desc": [
                    "¡Aproximación con viento cruzado en Soledad!",
                    "Mueve el avión con izquierda/derecha o mouse",
                    "para alinearlo con la pista al momento del toque."
                ],
                "rect": self.aeropuerto_rect
            },
            "batalla_flores": {
                "title": "¡BATALLA DE FLORES!",
                "district": "VÍA 40 · ETAPA JEFE FINAL",
                "microgame_id": "batalla_flores_boss",
                "microgame_title": "¡LA GRAN GUACHERNA!",
                "desc": [
                    "¡El clímax del Carnaval ha llegado a la Vía 40!",
                    "Esquiva la maicena, repica al ritmo de la tambora",
                    "y salta para atrapar la Corona del Rey Momo."
                ],
                "rect": pygame.Rect(self.quad_w - 120, self.quad_h - 120, 240, 240)
            }
        }

        # Banderas de hover para cada POI
        for p_key in self.poi_registry.keys():
            setattr(self, f"{p_key}_hover", False)

        self.active_poi: str = "uninorte"
        self.uninorte_hover: bool = False
        self.metropolitano_hover: bool = False
        self.mallorquin_hover: bool = False

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

    def _init_uninorte_effects(self) -> None:
        """Alias de compatibilidad retroactiva para inicializar efectos de POIs."""
        self._init_poi_effects()

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
            center_pos=(220, 520),
            normal_sprite=make_drawer_btn("SALIR AL MENÚ", (75, 30, 30), (230, 95, 90)),
            on_click=self._on_exit_clicked
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
            self.btn_exit_map
        ]


    def _init_narrative_and_carnaval(self) -> None:
        """Inicializa las viñetas de introducción y la celebración de victoria del Carnaval."""
        self.show_intro_dialog: bool = False
        self.intro_dialog_shown: bool = False
        self.show_victory_modal: bool = False
        self.victory_modal_shown: bool = False

        self.carnaval_confetti = []
        self.carnaval_fireworks = []

        # Cargar busto del personaje para el diálogo
        self._load_character_bust()

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
        """Inicializa la tarjeta modal de misión / microjuego que aparece al pulsar un nodo."""
        self.quest_card_open: bool = False
        self.quest_card_anim_t: float = 0.0
        self.quest_card_w: int = 580
        self.quest_card_h: int = 510

        self.font_quest_title = pygame.font.SysFont("Arial Black, Impact, sans-serif", 28)
        self.font_quest_sub = pygame.font.SysFont("Arial, sans-serif", 17, bold=True)
        self.font_quest_body = pygame.font.SysFont("Arial, sans-serif", 16)
        self.font_quest_btn = pygame.font.SysFont("Arial Black, Impact, sans-serif", 20)

        # Botón '¡A JUGAR!'
        btn_play_w, btn_play_h = 320, 56
        play_surf = pygame.Surface((btn_play_w, btn_play_h), pygame.SRCALPHA)
        pygame.draw.rect(play_surf, (245, 180, 50), (0, 0, btn_play_w, btn_play_h), border_radius=16)
        pygame.draw.rect(play_surf, (255, 235, 140), (0, 0, btn_play_w, btn_play_h), width=3, border_radius=16)
        txt_play = self.font_quest_btn.render("¡A JUGAR!", True, (35, 25, 15))
        play_surf.blit(txt_play, txt_play.get_rect(center=(btn_play_w // 2, btn_play_h // 2)))

        self.btn_quest_play = UIButton(
            center_pos=(self.screen_w // 2, self.screen_h // 2 + 155),
            normal_sprite=play_surf,
            on_click=self._launch_microgame
        )

        # Botón de cierre 'X'
        btn_close_surf = pygame.Surface((44, 44), pygame.SRCALPHA)
        pygame.draw.circle(btn_close_surf, (40, 50, 70, 220), (22, 22), 20)
        pygame.draw.circle(btn_close_surf, (220, 100, 95), (22, 22), 20, 2)
        txt_x = self.font_quest_sub.render("✕", True, (255, 255, 255))
        btn_close_surf.blit(txt_x, txt_x.get_rect(center=(22, 21)))

        self.btn_quest_close = UIButton(
            center_pos=(self.screen_w // 2 + self.quest_card_w // 2 - 32, self.screen_h // 2 - self.quest_card_h // 2 + 32),
            normal_sprite=btn_close_surf,
            on_click=self._close_quest_card
        )

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

    def _launch_microgame(self) -> None:
        """Inicia el microjuego correspondiente al nodo pulsado."""
        self._close_quest_card()
        if self.active_poi == "mallorquin":
            from microgames.mallorquin_photo import MallorquinPhotoMicrogame
            microgame = MallorquinPhotoMicrogame(
                character_id=self.character_id,
                on_complete_callback=self._on_microgame_complete
            )
        elif self.active_poi == "uninorte":
            from microgames.uninorte_sprint import UninorteSprintMicrogame
            microgame = UninorteSprintMicrogame(
                character_id=self.character_id,
                on_complete_callback=self._on_microgame_complete
            )
        elif self.active_poi == "ventana":
            from microgames.ventana_colores import VentanaColoresMicrogame
            microgame = VentanaColoresMicrogame(
                character_id=self.character_id,
                on_complete_callback=self._on_microgame_complete
            )
        elif self.active_poi == "malecon":
            from microgames.malecon_rueda import MaleconRuedaMicrogame
            microgame = MaleconRuedaMicrogame(
                character_id=self.character_id,
                on_complete_callback=self._on_microgame_complete
            )
        elif self.active_poi == "metropolitano":
            from microgames.metropolitano_penalty import MetropolitanoPenaltyMicrogame
            microgame = MetropolitanoPenaltyMicrogame(
                character_id=self.character_id,
                on_complete_callback=self._on_microgame_complete
            )
        elif self.active_poi == "aeropuerto":
            from microgames.aeropuerto_aterrizaje import AeropuertoAterrizajeMicrogame
            microgame = AeropuertoAterrizajeMicrogame(
                character_id=self.character_id,
                on_complete_callback=self._on_microgame_complete
            )
        elif self.active_poi == "batalla_flores":
            from microgames.batalla_flores_boss import BatallaFloresBossMicrogame
            microgame = BatallaFloresBossMicrogame(
                character_id=self.character_id,
                on_complete_callback=self._on_microgame_complete
            )
        else:
            from microgames.uninorte_sprint import UninorteSprintMicrogame
            microgame = UninorteSprintMicrogame(
                character_id=self.character_id,
                on_complete_callback=self._on_microgame_complete
            )

        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(microgame)

    def _on_microgame_complete(self, won: bool) -> None:
        """Retorna al mapa tras terminar el microjuego y actualiza el progreso."""
        if won:
            poi_info = self.poi_registry.get(self.active_poi, {})
            m_id = poi_info.get("microgame_id", "uninorte_sprint")
            progress = self.settings.get_story_progress()
            completed = list(progress.get("completed_microgames", []))
            if m_id not in completed:
                completed.append(m_id)
            unlocked = list(progress.get("unlocked_locations", []))
            if self.active_poi not in unlocked:
                unlocked.append(self.active_poi)

            self.settings.update_story_progress(
                completed_microgames=completed,
                unlocked_locations=unlocked,
                high_score=progress.get("high_score", 0) + 100
            )

            # Si se derrota la Etapa Jefe o se completan los 7 microjuegos, coronar Rey Momo
            if (m_id == "batalla_flores_boss" or len(completed) >= 7) and not self.victory_modal_shown:
                self.show_victory_modal = True
                self.victory_modal_shown = True
                self._spawn_carnaval_celebration()
        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.change_state(self)

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
        self.settings.update_story_progress(
            character_id=self.character_id,
            current_node_id=self.player_node_id if hasattr(self, "player_node_id") else 0,
            last_camera_x=float(self.camera.x),
            last_camera_y=float(self.camera.y)
        )

    def request_exit(self) -> None:
        """Persiste el progreso y ejecuta el retorno hacia el flujo previo."""
        self.save_current_state()
        if self.on_back_callback:
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

        # Construir badge circular con recorte de rostro
        self._build_player_token()

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

        from collections import deque
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
        from tools.map_dev_tool import get_bezier_points

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
        y viaja a lo largo del camino hasta el siguiente nodo de parada (is_stop) o bifurcación (grado != 2).
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

        path = [curr_id, best_nbr]
        prev_id = curr_id
        curr_walk = best_nbr
        while True:
            walk_node = node_map[curr_walk]
            if walk_node.get("is_stop", False) or len(adj[curr_walk]) != 2:
                break
            next_candidates = [x for x in adj[curr_walk] if x != prev_id]
            if not next_candidates:
                break
            next_step = next_candidates[0]
            path.append(next_step)
            prev_id = curr_walk
            curr_walk = next_step

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
        """Retorna el POI más cercano a una posición dentro de la distancia máxima."""
        best_key = None
        best_d = max_dist
        for p_key, p_info in self.poi_registry.items():
            r = p_info["rect"]
            d = math.hypot(r.centerx - pos[0], r.centery - pos[1])
            if d < best_d:
                best_d = d
                best_key = p_key
        return best_key

    def _render_level_stops(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Renderiza los hitos visuales de parada (is_stop) en las calles sobre el mapa."""
        nodes, _, _, _, _ = self._get_street_graph()
        pulse = math.sin(self.timer * 3.5) * 0.5 + 0.5
        for n in nodes:
            if not n.get("is_stop", False):
                continue
            sx = n["x"] - cam_x
            sy = n["y"] - cam_y
            if -40 < sx < self.screen_w + 40 and -40 < sy < self.screen_h + 40:
                glow_r = int(14 + 4 * pulse)
                glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (245, 195, 60, int(70 + 50 * pulse)), (glow_r, glow_r), glow_r)
                surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

                pygame.draw.circle(surface, (255, 215, 70), (sx, sy), 9)
                pygame.draw.circle(surface, (40, 30, 20), (sx, sy), 7)
                pygame.draw.circle(surface, (255, 240, 180), (sx, sy), 4)

    def _render_player_avatar(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Renderiza el avatar del jugador: sombra de contacto, bobbing rítmico y desvanecimiento en túneles."""
        if not hasattr(self, "player_pos") or self.player_alpha <= 0.01:
            return

        px = int(self.player_pos[0]) - cam_x
        py = int(self.player_pos[1]) - cam_y

        if not (-80 < px < self.screen_w + 80 and -100 < py < self.screen_h + 80):
            return

        bob_spd = 14.0 if self.player_is_moving else 3.8
        bob_amp = 5.0 if self.player_is_moving else 2.5
        bob_y = math.sin(self.player_anim_timer * bob_spd) * bob_amp

        # 1. Sombra de contacto sobre el piso
        if hasattr(self, "player_shadow_surf"):
            sw, sh = self.player_shadow_surf.get_size()
            if self.player_alpha < 0.99:
                sh_copy = self.player_shadow_surf.copy()
                sh_copy.set_alpha(int(120 * self.player_alpha))
                surface.blit(sh_copy, (px - sw // 2, py - sh // 2 + 3))
            else:
                surface.blit(self.player_shadow_surf, (px - sw // 2, py - sh // 2 + 3))

        # 2. Token / Insignia circular
        if hasattr(self, "player_token_surf"):
            tw, th = self.player_token_surf.get_size()
            token_x = px - tw // 2
            token_y = int(py - th + 8 + bob_y)

            if self.player_alpha < 0.99:
                tk_copy = self.player_token_surf.copy()
                tk_copy.set_alpha(int(255 * self.player_alpha))
                surface.blit(tk_copy, (token_x, token_y))
            else:
                surface.blit(self.player_token_surf, (token_x, token_y))

    def enter(self, params: Optional[dict] = None) -> None:
        if params and "character_id" in params:
            self.character_id = params["character_id"]
            self._load_character_bust()
            self._build_player_token()

        # Persistir personaje seleccionado de inmediato
        self.save_current_state()

        # Reiniciar animación de paneo cinemático al entrar
        self.cinematic_timer = 0.0
        self.camera.set_pos(self.intro_start_pos[0], self.intro_start_pos[1])

        # Asegurar estado limpio de diálogos y popups
        self.show_intro_dialog = False
        self.show_victory_modal = False

        # Música continua de exploración sin cortes
        cafe_track = "cafe_bistro_mapa.ogg" if os.path.exists(os.path.join("assets", "cafe_bistro_mapa.ogg")) else "cafe_bistro_mapa.mp3"
        self.audio.play_bgm(cafe_track)

    def handle_event(self, event: pygame.event.Event) -> None:
        # 1. DevTool intercepta eventos si está activo
        if hasattr(self, "dev_tool"):
            p_rects = {k: v["rect"] for k, v in self.poi_registry.items()} if hasattr(self, "poi_registry") else None
            if self.dev_tool.handle_event(event, (self.camera.x, self.camera.y), poi_rects=p_rects):
                return
        # Tecla ESC o M para abrir/cerrar menú desplegable de pausa
        # Interacción con la viñeta introductoria
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

        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_m):
            if self.quest_card_open:
                self._close_quest_card()
                return
            self._toggle_menu()
            return

        # Si la tarjeta de misión está abierta, interacción con la tarjeta
        if self.quest_card_open:
            consumed_play = self.btn_quest_play.handle_event(event)
            consumed_close = self.btn_quest_close.handle_event(event)
            if consumed_play or consumed_close:
                return

            # Click fuera de la tarjeta para cerrar
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                card_rect = pygame.Rect(
                    self.screen_w // 2 - self.quest_card_w // 2,
                    self.screen_h // 2 - self.quest_card_h // 2,
                    self.quest_card_w,
                    self.quest_card_h
                )
                if not card_rect.collidepoint(event.pos):
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
                    self._open_quest_card(nearest_poi)
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
            if hasattr(self, "mouse_down_pos") and not self.menu_open:
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

                    # 2. ¿Click sobre un POI?
                    for p_key, p_info in self.poi_registry.items():
                        if p_info["rect"].collidepoint(world_click) or getattr(self, f"{p_key}_hover", False):
                            target_node = self._get_poi_target_node(p_key)
                            if target_node is not None:
                                if self.player_node_id == target_node and not self.player_is_moving:
                                    self._open_quest_card(p_key)
                                else:
                                    path = self._find_shortest_path(self.player_node_id, target_node)
                                    if path:
                                        self._start_path_travel(path, target_poi=p_key)
                            return
        elif event.type == pygame.MOUSEMOTION:
            self.camera.update_drag(event.pos)

    def update(self, dt: float) -> None:
        self.timer += dt
        self.camera.update(dt, (0.0, 0.0))
        if hasattr(self, "dev_tool"):
            self.dev_tool.update(dt)

        # Animación suave del menú lateral (Drawer)
        drawer_target = 1.0 if self.menu_open else 0.0
        self.menu_anim_t += (drawer_target - self.menu_anim_t) * min(1.0, dt * 14.0)

        # Animación suave de la tarjeta de misión (Quest Card)
        quest_target = 1.0 if self.quest_card_open else 0.0
        self.quest_card_anim_t += (quest_target - self.quest_card_anim_t) * min(1.0, dt * 16.0)

        if self.save_feedback_timer > 0.0:
            self.save_feedback_timer -= dt

        # Si el menú está desplegándose, actualizar botones del drawer
        if self.menu_anim_t > 0.01:
            for btn in self.drawer_buttons:
                btn.update(dt)

        self.btn_menu_toggle.update(dt)

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

        if self.show_intro_dialog:
            return

        # Si el menú o la tarjeta de misión están abiertos, pausar arrastre del mapa
        if self.menu_open or self.quest_card_open:
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

                self.player_edge_idx += 1
                if self.player_edge_idx >= len(self.player_path_edges):
                    # Fin de la ruta completa
                    self.player_is_moving = False
                    self.player_path_edges = []
                    self.player_edge_dist = 0.0
                    self.player_alpha = 1.0
                    if self.player_target_poi:
                        self._open_quest_card(self.player_target_poi)
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
                self.player_pos = (
                    p_a[0] + (p_b[0] - p_a[0]) * t,
                    p_a[1] + (p_b[1] - p_a[1]) * t
                )

            # Opción 2.A: Seguimiento suave automático de la cámara mientras se mueve
            cam_target_x = max(0.0, min(float(self.camera.max_x), self.player_pos[0] - self.screen_w / 2.0))
            cam_target_y = max(0.0, min(float(self.camera.max_y), self.player_pos[1] - self.screen_h / 2.0))
            lerp = 1.0 - math.exp(-7.5 * dt)
            self.camera.x += (cam_target_x - self.camera.x) * lerp
            self.camera.y += (cam_target_y - self.camera.y) * lerp
            self.camera.vel_x = 0.0
            self.camera.vel_y = 0.0
        else:
            self.player_anim_timer += dt
            self.player_alpha = min(1.0, self.player_alpha + dt * 8.0)

        # Detección de Hover del mouse sobre los POIs
        mouse_pos = pygame.mouse.get_pos()
        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)
        world_mouse = (mouse_pos[0] + cam_x, mouse_pos[1] + cam_y)
        prog = self.settings.get_story_progress()
        completed_count = len(prog.get('completed_microgames', []))
        for p_key, p_info in self.poi_registry.items():
            if p_key == "batalla_flores" and completed_count < 6:
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
        else:
            # Control por teclado si no hay arrastre
            keys = pygame.key.get_pressed()
            move_x = 0.0
            move_y = 0.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                move_x -= 1.0
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                move_x += 1.0
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                move_y -= 1.0
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                move_y += 1.0

            if move_x != 0.0 and move_y != 0.0:
                move_x *= 0.7071
                move_y *= 0.7071

            self.camera.update(dt, (move_x, move_y))

    def render(self, surface: pygame.Surface) -> None:
        # 1. Renderizar el mapa mundial continuo con offset de cámara cinética
        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)
        surface.blit(self.world_map, (-cam_x, -cam_y))

        # 2. Hitos de parada en las calles (is_stop)
        self._render_level_stops(surface, cam_x, cam_y)

        # 3. Avatar del jugador (sombra, token con rostro, rebote y túnel)
        self._render_player_avatar(surface, cam_x, cam_y)

        # 4. Renderizar efectos dinámicos de Puntos Clave (Mallorquín, Uninorte, Metropolitano)
        progress = self.settings.get_story_progress()
        completed_games = progress.get("completed_microgames", [])

        for p_key, p_info in self.poi_registry.items():
            if p_key == "batalla_flores" and len(completed_games) < 6:
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
                    sp_surf = pygame.Surface((12, 12), pygame.SRCALPHA)
                    pygame.draw.circle(sp_surf, (255, 235, 110, sp_alpha), (6, 6), max(1, int(sp["size"] * fade)))
                    surface.blit(sp_surf, (sp_x - 6, sp_y - 6))

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

        # 6. Botón circular flotante de menú hamburguesa
        if self.menu_anim_t < 0.95:
            self.btn_menu_toggle.render(surface)

        # 7. Renderizar Drawer Desplegable de Pausa y Guardado
        if self.menu_anim_t > 0.01:
            self._render_drawer_menu(surface)

        # 8. Renderizar Tarjeta Modal de Misión / Microjuego
        if self.quest_card_anim_t > 0.01:
            self._render_quest_card(surface)

        # 9. Renderizar Viñeta Narrativa de Bienvenida
        if self.show_intro_dialog:
            self._render_intro_dialog(surface)

        # 10. Renderizar Celebración de Victoria del Carnaval
        if self.show_victory_modal:
            self._render_victory_modal(surface)

        # 11. Renderizar Herramienta de Desarrollo Visual (DevTool F1)
        if hasattr(self, "dev_tool"):
            poi_rects = {k: v["rect"] for k, v in self.poi_registry.items()}
            self.dev_tool.render(surface, (self.camera.x, self.camera.y), poi_rects)

    def _render_drawer_menu(self, surface: pygame.Surface) -> None:
        """Renderiza el panel lateral desplegable de opciones y guardado."""
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

    def _render_quest_card(self, surface: pygame.Surface) -> None:
        """Renderiza la tarjeta modal de misión del nodo activo."""
        poi_info = self.poi_registry.get(self.active_poi, self.poi_registry["uninorte"])

        # A) Oscurecimiento de fondo
        dim_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        dim_surf.fill((10, 16, 28, int(160 * self.quest_card_anim_t)))
        surface.blit(dim_surf, (0, 0))

        # B) Tarjeta emergente
        cw = int(self.quest_card_w * (0.85 + 0.15 * self.quest_card_anim_t))
        ch = int(self.quest_card_h * (0.85 + 0.15 * self.quest_card_anim_t))
        card_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)

        # Fondo cálido marfil estilo sticker
        pygame.draw.rect(card_surf, (255, 252, 244, 250), (0, 0, cw, ch), border_radius=28)
        pygame.draw.rect(card_surf, (245, 195, 80), (0, 0, cw, ch), width=4, border_radius=28)
        pygame.draw.rect(card_surf, (45, 30, 20), (0, 0, cw, ch), width=1, border_radius=28)

        # Encabezado: Título de la Locación
        txt_title = self.font_quest_title.render(poi_info["title"], True, (45, 30, 18))
        card_surf.blit(txt_title, txt_title.get_rect(center=(cw // 2, 55)))

        # Subtítulo de Distrito
        badge_dist = pygame.Surface((340, 32), pygame.SRCALPHA)
        pygame.draw.rect(badge_dist, (240, 235, 220), (0, 0, 340, 32), border_radius=16)
        pygame.draw.rect(badge_dist, (180, 150, 100), (0, 0, 340, 32), width=1, border_radius=16)
        txt_dist = self.font_quest_sub.render(poi_info["district"], True, (90, 65, 40))
        badge_dist.blit(txt_dist, txt_dist.get_rect(center=(170, 16)))
        card_surf.blit(badge_dist, badge_dist.get_rect(center=(cw // 2, 100)))

        # Separador decorativo
        pygame.draw.line(card_surf, (220, 200, 175), (40, 130), (cw - 40, 130), 2)

        # Título del Microjuego
        txt_m_title = self.font_quest_btn.render(poi_info["microgame_title"], True, (215, 75, 45))
        card_surf.blit(txt_m_title, txt_m_title.get_rect(center=(cw // 2, 165)))

        # Descripción de la misión
        desc_lines = poi_info["desc"]
        curr_y = 215
        for line in desc_lines:
            txt_line = self.font_quest_body.render(line, True, (65, 55, 45))
            card_surf.blit(txt_line, txt_line.get_rect(center=(cw // 2, curr_y)))
            curr_y += 30

        # Tarjeta de recompensa / récord
        progress = self.settings.get_story_progress()
        is_done = poi_info["microgame_id"] in progress.get("completed_microgames", [])
        status_text = "ESTADO: COMPLETADO (+100 PTS)" if is_done else "ESTADO: PENDIENTE POR DESPEJAR"
        status_col = (45, 140, 70) if is_done else (180, 110, 30)

        badge_status = pygame.Surface((380, 36), pygame.SRCALPHA)
        pygame.draw.rect(badge_status, (*status_col, 35), (0, 0, 380, 36), border_radius=12)
        pygame.draw.rect(badge_status, status_col, (0, 0, 380, 36), width=2, border_radius=12)
        txt_st = self.font_quest_sub.render(status_text, True, status_col)
        badge_status.blit(txt_st, txt_st.get_rect(center=(190, 18)))
        card_surf.blit(badge_status, badge_status.get_rect(center=(cw // 2, 330)))

        # Renderizar en la pantalla centrado
        card_rect = card_surf.get_rect(center=(self.screen_w // 2, self.screen_h // 2))
        surface.blit(card_surf, card_rect)

        # Botones de la tarjeta
        self.btn_quest_play.render(surface)
        self.btn_quest_close.render(surface)

    def _render_intro_dialog(self, surface: pygame.Surface) -> None:
        dw, dh = 960, 200
        dx = (self.screen_w - dw) // 2
        dy = self.screen_h - dh - 40

        d_surf = pygame.Surface((dw, dh), pygame.SRCALPHA)
        pygame.draw.rect(d_surf, (20, 24, 38, 245), (0, 0, dw, dh), border_radius=24)
        pygame.draw.rect(d_surf, (245, 195, 75), (0, 0, dw, dh), width=3, border_radius=24)

        # Busto del personaje
        d_surf.blit(self.character_bust, (30, 20))

        # Texto de diálogo
        char_name = self.character_id.upper()
        font_d_title = pygame.font.SysFont("Arial Black, Impact", 24)
        font_d_body = pygame.font.SysFont("Arial, sans-serif", 16)
        font_d_sub = pygame.font.SysFont("Arial Black, Impact", 13)

        txt_d_title = font_d_title.render(f"¡BIENVENIDO A BARRANQUILLA, {char_name}! 🌴", True, (255, 220, 80))
        d_surf.blit(txt_d_title, (210, 25))

        lines = [
            "¡El Carnaval está en marcha y Curramba te espera con 6 distritos emblemáticos!",
            "Explora el mapa con el mouse o teclado y haz click en las locaciones para jugar.",
            "Supera los 6 desafíos para iluminar las rutas y coronarte Rey Momo."
        ]
        ly = 68
        for line in lines:
            txt_l = font_d_body.render(line, True, (240, 245, 255))
            d_surf.blit(txt_l, (210, ly))
            ly += 26

        txt_prompt = font_d_sub.render("▶ PULSA ESPACIO O HAZ CLICK PARA EMPEZAR A EXPLORAR", True, (120, 235, 160))
        d_surf.blit(txt_prompt, (210, 160))

        surface.blit(d_surf, (dx, dy))

    def _render_victory_modal(self, surface: pygame.Surface) -> None:
        # Fondo oscurecido
        dim_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        dim_surf.fill((10, 12, 25, 190))
        surface.blit(dim_surf, (0, 0))

        # Confeti
        for cf in self.carnaval_confetti:
            c_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(c_surf, (*cf["color"], 235), (8, 8), int(cf["size"]))
            surface.blit(c_surf, (int(cf["x"]), int(cf["y"])))

        vw, vh = 860, 520
        vx = (self.screen_w - vw) // 2
        vy = (self.screen_h - vh) // 2

        vic_surf = pygame.Surface((vw, vh), pygame.SRCALPHA)
        pygame.draw.rect(vic_surf, (20, 25, 42, 250), (0, 0, vw, vh), border_radius=28)
        pygame.draw.rect(vic_surf, (255, 215, 60), (0, 0, vw, vh), width=4, border_radius=28)

        font_v_title = pygame.font.SysFont("Arial Black, Impact", 38)
        font_v_sub = pygame.font.SysFont("Arial Black, Impact", 22)
        font_v_body = pygame.font.SysFont("Arial, sans-serif", 17)

        # Título
        txt_vt = font_v_title.render("★ ¡REY MOMO DEL CARNAVAL! ★", True, (255, 225, 80))
        vic_surf.blit(txt_vt, txt_vt.get_rect(center=(vw // 2, 70)))

        txt_vs = font_v_sub.render("¡CONQUISTASTE LOS 6 DISTRITOS DE CURRAMBA!", True, (255, 255, 255))
        vic_surf.blit(txt_vs, txt_vs.get_rect(center=(vw // 2, 135)))

        # Badge de Puntuación
        badge_w, badge_h = 420, 48
        badge_s = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
        pygame.draw.rect(badge_s, (35, 130, 70), (0, 0, badge_w, badge_h), border_radius=14)
        pygame.draw.rect(badge_s, (110, 250, 160), (0, 0, badge_w, badge_h), width=2, border_radius=14)
        font_badge = pygame.font.SysFont("Arial Black, Impact", 20)
        txt_b = font_badge.render("PUNTAJE FINAL: 600 PTS (100%)", True, (230, 255, 240))
        badge_s.blit(txt_b, txt_b.get_rect(center=(badge_w // 2, 24)))
        vic_surf.blit(badge_s, badge_s.get_rect(center=(vw // 2, 205)))

        # Mensaje de felicitación
        desc = [
            "Has recorrido de punta a punta Barranquilla superando cada desafío:",
            "Mallorquín, Uninorte, Ventana al Mundo, Gran Malecón, Metropolitano y Cortissoz.",
            "¡Toda la ciudad celebra tu victoria al ritmo de cumbia, tambora y guache!"
        ]
        dy = 265
        for d in desc:
            txt_d = font_v_body.render(d, True, (200, 215, 240))
            vic_surf.blit(txt_d, txt_d.get_rect(center=(vw // 2, dy)))
            dy += 28

        surface.blit(vic_surf, (vx, vy))

        # Renderizar botones
        self.btn_vic_explore.render(surface)
        self.btn_vic_menu.render(surface)
