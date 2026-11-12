import json
import math
import os
from typing import Dict, List, Tuple, Optional, Any, Callable
import pygame

CONFIG_PATH = os.path.join("config", "map_poi_layout.json")

def get_bezier_points(
    p0: Tuple[int, int],
    pc: Tuple[int, int],
    p1: Tuple[int, int],
    step_px: int = 10
) -> List[Tuple[int, int]]:
    """Calcula puntos equiespaciados a lo largo de una curva Bézier cuadrática."""
    chord = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    control_dist = math.hypot(pc[0] - p0[0], pc[1] - p0[1]) + math.hypot(p1[0] - pc[0], p1[1] - pc[1])
    approx_len = max(10.0, (chord + control_dist) * 0.5)
    num_steps = max(6, int(approx_len // max(4, step_px)))

    points: List[Tuple[int, int]] = []
    for s in range(num_steps + 1):
        t = s / float(num_steps)
        one_minus_t = 1.0 - t
        x = (one_minus_t ** 2) * p0[0] + 2.0 * one_minus_t * t * pc[0] + (t ** 2) * p1[0]
        y = (one_minus_t ** 2) * p0[1] + 2.0 * one_minus_t * t * pc[1] + (t ** 2) * p1[1]
        points.append((int(round(x)), int(round(y))))
    return points


class MapDevTool:
    """
    Herramienta de desarrollo visual en tiempo real para el Mapa Mundial de BarranquillaWare.
    Modos:
    1. Modo POIs: Posición, Escala y Rotación angular con guardado en JSON.
    2. Modo Caminos, Red Vial y Shader de Calles (P):
       - Grafo completo de Red Vial: ramas que nacen de cualquier nodo existente.
       - Conexión de nodos con Shift+Click para cerrar circuitos o conectar avenidas.
       - Inserción de Nodos Medios (I) subdividiendo curvas Bézier con algoritmo exacto.
       - Trazado de vías con Curvas Bézier manuales (arrastre de manijas de control ◆).
       - Marcado de tramos 'hidden' (Túneles) para desaparecer al protagonista y evitar colisiones de Y-sort.
       - Marcado de paradas/hitos de nivel ('is_stop' ★) donde el personaje se detiene.
       - Shader de tinte de calle: ancho, opacidad y paleta cromática en tiempo real.
       - Guardado persistente instantáneo en config/map_poi_layout.json (F5).
    """
    def __init__(
        self,
        screen_w: int = 1920,
        screen_h: int = 1080,
        on_layout_changed_callback: Optional[Callable[[], None]] = None
    ) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.on_layout_changed = on_layout_changed_callback

        self.enabled: bool = False
        self.mode: str = "pois"  # "pois" o "paths"
        self.active_poi_key: str = "mallorquin"
        self.is_dragging_poi: bool = False
        self.drag_offset: Tuple[int, int] = (0, 0)
        self.last_poi_rects: Dict[str, pygame.Rect] = {}

        # ----------------------------------------------------
        # Red Vial (Grafo de Nodos y Aristas con Curvas Bézier)
        # ----------------------------------------------------
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, Any]] = []
        self.selected_node_id: int = -1
        self.selected_edge_idx: int = -1
        self.is_dragging_node: bool = False
        self.is_dragging_edge_ctrl: bool = False

        # Configuración del Shader de Calles (Tinte sobre asfalto acuarela)
        self.street_shader: Dict[str, Any] = {
            "color": [245, 185, 55],
            "alpha": 120,
            "width": 26
        }

        # Paletas rápidas de color para el shader de calle
        self.color_palettes = [
            ("Dorado", (245, 185, 55)),
            ("Turquesa", (45, 195, 205)),
            ("Coral", (235, 95, 85)),
            ("Blanco", (240, 240, 240))
        ]

        # Feedback visual de guardado
        self.toast_msg: str = ""
        self.toast_timer: float = 0.0

        # Fuentes tipográficas
        self.font_title = pygame.font.SysFont("Arial Black, Impact, sans-serif", 15)
        self.font_body = pygame.font.SysFont("Arial, sans-serif", 13, bold=True)
        self.font_small = pygame.font.SysFont("Arial, sans-serif", 11)
        self.font_btn = pygame.font.SysFont("Arial, sans-serif", 11, bold=True)

        # Botón toggle en esquina superior izquierda
        self.toggle_rect = pygame.Rect(18, 18, 120, 32)

        # Panel flotante
        self.panel_x = 18
        self.panel_y = 58
        self.panel_w = 400
        self.panel_h = 450
        self.panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)

        # Botón de guardado
        self.save_btn_rect = pygame.Rect(self.panel_x + 16, self.panel_y + self.panel_h - 38, 160, 28)

        # Controles Modo POIs
        self.scale_dec_btn_rect = pygame.Rect(self.panel_x + 235, self.panel_y + 152, 32, 22)
        self.scale_inc_btn_rect = pygame.Rect(self.panel_x + 273, self.panel_y + 152, 32, 22)
        self.rot_dec_btn_rect = pygame.Rect(self.panel_x + 215, self.panel_y + 178, 44, 22)
        self.rot_inc_btn_rect = pygame.Rect(self.panel_x + 265, self.panel_y + 178, 44, 22)
        self.rot_reset_btn_rect = pygame.Rect(self.panel_x + 315, self.panel_y + 178, 48, 22)

        # Controles Modo Caminos, Red y Shader
        self.path_mid_btn_rect = pygame.Rect(self.panel_x + 16, self.panel_y + 138, 120, 24)
        self.path_stop_btn_rect = pygame.Rect(self.panel_x + 142, self.panel_y + 138, 115, 24)
        self.path_hidden_btn_rect = pygame.Rect(self.panel_x + 263, self.panel_y + 138, 120, 24)

        self.path_straight_btn_rect = pygame.Rect(self.panel_x + 16, self.panel_y + 168, 85, 22)
        self.shader_w_dec_rect = pygame.Rect(self.panel_x + 215, self.panel_y + 168, 30, 22)
        self.shader_w_inc_rect = pygame.Rect(self.panel_x + 250, self.panel_y + 168, 30, 22)
        self.shader_a_dec_rect = pygame.Rect(self.panel_x + 215, self.panel_y + 196, 30, 22)
        self.shader_a_inc_rect = pygame.Rect(self.panel_x + 250, self.panel_y + 196, 30, 22)
        self.delete_pt_btn_rect = pygame.Rect(self.panel_x + 184, self.panel_y + self.panel_h - 38, 140, 28)

        self.palette_btn_rects: List[Tuple[pygame.Rect, str, Tuple[int, int, int]]] = []
        for i, (name, col) in enumerate(self.color_palettes):
            r = pygame.Rect(self.panel_x + 16 + i * 92, self.panel_y + 228, 86, 22)
            self.palette_btn_rects.append((r, name, col))

        # Chips de selección rápida de POIs
        self.poi_chip_rects: Dict[str, pygame.Rect] = {}

        # Cargar configuración existente
        self.layout_data = self.load_layout()
        self._init_poi_chips()

    def _init_poi_chips(self) -> None:
        """Crea los rectángulos interactivos de los chips de selección de POIs."""
        self.poi_chip_rects.clear()
        poi_keys = list(self.layout_data["pois"].keys())
        cols = 4
        chip_w = 86
        chip_h = 20
        start_x = self.panel_x + 16
        start_y = self.panel_y + 64
        for i, key in enumerate(poi_keys):
            row = i // cols
            col = i % cols
            r = pygame.Rect(start_x + col * (chip_w + 5), start_y + row * (chip_h + 4), chip_w, chip_h)
            self.poi_chip_rects[key] = r

    def get_node(self, node_id: int) -> Optional[Dict[str, Any]]:
        for n in self.nodes:
            if n["id"] == node_id:
                return n
        return None

    def load_layout(self) -> Dict[str, Any]:
        """Carga el layout desde config/map_poi_layout.json o retorna defaults."""
        default_layout: Dict[str, Any] = {
            "pois": {
                "mallorquin": {"name": "Parque Mallorquín", "x": 203, "y": 155, "width": 127, "angle": 0.0, "level_id": "mallorquin", "microgame_id": "mallorquin_photo", "kind": "extra", "control_mode": "keyboard_gamepad"},
                "uninorte": {"name": "Campus Uninorte", "x": 145, "y": 505, "width": 390, "angle": 0.0, "level_id": "uninorte", "microgame_id": "uninorte_sprint", "kind": "level", "control_mode": "keyboard_gamepad"},
                "buenavista": {"name": "C.C. Buenavista", "x": 856, "y": 501, "width": 585, "angle": 0.0, "level_id": "buenavista", "microgame_id": "buenavista_trend", "kind": "level", "control_mode": "hybrid"},
                "ventana": {"name": "Ventana al Mundo", "x": 1830, "y": 236, "width": 125, "angle": 0.0, "level_id": "ventana", "microgame_id": "ventana_colores", "kind": "extra", "control_mode": "keyboard_gamepad"},
                "malecon": {"name": "Gran Malecón", "x": 2689, "y": 503, "width": 270, "angle": 0.0, "level_id": "malecon", "microgame_id": "coaster", "kind": "secret", "control_mode": "camera_marker"},
                "aleta": {"name": "Aleta del Tiburón", "x": 2740, "y": 806, "width": 135, "angle": 0.0, "level_id": "aleta", "microgame_id": "punch_alert", "kind": "extra", "control_mode": "keyboard_gamepad"},
                "metropolitano": {"name": "Estadio Metropolitano", "x": 1778, "y": 1242, "width": 365, "angle": 0.0, "level_id": "metropolitano", "microgame_id": "metropolitano_moderacion", "kind": "level", "control_mode": "keyboard_gamepad"},
                "aeropuerto": {"name": "Aeropuerto Ernesto Cortissoz", "x": 2625, "y": 1221, "width": 540, "angle": 0.0, "level_id": "aeropuerto", "microgame_id": "punch_alert", "kind": "level", "control_mode": "keyboard_gamepad"}
            },
            "street_shader": {
                "color": [245, 185, 55],
                "alpha": 120,
                "width": 26
            },
            "street_network": {
                "nodes": [],
                "edges": []
            },
            "custom_paths": []
        }

        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        if "pois" in loaded and isinstance(loaded["pois"], dict):
                            for k, v in loaded["pois"].items():
                                if isinstance(v, dict):
                                    v.setdefault("angle", 0.0)
                                    v.setdefault("level_id", k)
                                    v.setdefault("microgame_id", "")
                                    v.setdefault("kind", "extra")
                                    v.setdefault("control_mode", "keyboard_gamepad")
                                    default_layout["pois"][k] = v
                        if "street_shader" in loaded and isinstance(loaded["street_shader"], dict):
                            default_layout["street_shader"].update(loaded["street_shader"])
                        if "street_network" in loaded and isinstance(loaded["street_network"], dict):
                            default_layout["street_network"] = loaded["street_network"]
                        elif "custom_paths" in loaded and isinstance(loaded["custom_paths"], list):
                            default_layout["custom_paths"] = loaded["custom_paths"]
            except Exception as e:
                print(f"Aviso DevTool: no se pudo cargar {CONFIG_PATH}: {e}")

        # Migración transparente: si existe street_network, usarlo; si hay custom_paths lineal, convertirlo
        net = default_layout.get("street_network", {})
        self.nodes = net.get("nodes", [])
        self.edges = net.get("edges", [])

        if not self.nodes and default_layout.get("custom_paths"):
            legacy = default_layout["custom_paths"]
            self.nodes = []
            self.edges = []
            for idx, pt in enumerate(legacy):
                self.nodes.append({
                    "id": idx,
                    "x": pt.get("x", 0),
                    "y": pt.get("y", 0),
                    "is_stop": pt.get("is_stop", False),
                    "name": pt.get("name", f"Punto {idx + 1}")
                })
                if idx > 0:
                    self.edges.append({
                        "from": idx - 1,
                        "to": idx,
                        "ctrl_x": pt.get("ctrl_x", (legacy[idx - 1]["x"] + pt["x"]) // 2),
                        "ctrl_y": pt.get("ctrl_y", (legacy[idx - 1]["y"] + pt["y"]) // 2),
                        "hidden": pt.get("hidden", False)
                    })

        self.street_shader = default_layout.get("street_shader", self.street_shader)
        return default_layout

    def save_layout(self) -> bool:
        """Guarda la red vial completa (nodos, aristas, Béziers, túneles) en config/map_poi_layout.json."""
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            self.layout_data["street_network"] = {
                "nodes": self.nodes,
                "edges": self.edges
            }
            # Guardar también custom_paths sincronizado para compatibilidad
            self.layout_data["custom_paths"] = [
                {"x": n["x"], "y": n["y"], "is_stop": n.get("is_stop", False), "name": n.get("name", "")}
                for n in self.nodes
            ]
            self.layout_data["street_shader"] = self.street_shader

            for p_cfg in self.layout_data["pois"].values():
                p_cfg["x"] = int(p_cfg["x"])
                p_cfg["y"] = int(p_cfg["y"])
                p_cfg["width"] = int(p_cfg["width"])
                p_cfg["angle"] = round(float(p_cfg.get("angle", 0.0)), 1)

            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.layout_data, f, indent=2, ensure_ascii=False)
            self.toast_msg = "✓ GUARDADO EN config/map_poi_layout.json"
            self.toast_timer = 2.8
            return True
        except Exception as e:
            self.toast_msg = f"ERROR AL GUARDAR: {e}"
            self.toast_timer = 3.5
            return False

    def get_poi_config(self, poi_key: str) -> Dict[str, Any]:
        return self.layout_data["pois"].get(poi_key, {})

    def update(self, dt: float) -> None:
        if self.toast_timer > 0.0:
            self.toast_timer -= dt

    def _notify_change(self) -> None:
        if self.on_layout_changed:
            self.on_layout_changed()

    def split_selected_edge(self) -> bool:
        """
        Inserta un nuevo nodo exactamente a la mitad de la arista seleccionada,
        subdividiendo la curva Bézier con el algoritmo exacto de de Casteljau.
        """
        if not (0 <= self.selected_edge_idx < len(self.edges)):
            # Si no hay arista seleccionada directamente, buscar arista conectada al nodo seleccionado
            if self.selected_node_id != -1:
                for idx, ed in enumerate(self.edges):
                    if ed["to"] == self.selected_node_id or ed["from"] == self.selected_node_id:
                        self.selected_edge_idx = idx
                        break

        if not (0 <= self.selected_edge_idx < len(self.edges)):
            self.toast_msg = "Selecciona una curva (◆) o nodo para insertar punto medio"
            self.toast_timer = 2.0
            return False

        edge = self.edges[self.selected_edge_idx]
        p0 = self.get_node(edge["from"])
        p1 = self.get_node(edge["to"])
        if not p0 or not p1:
            return False

        pc_x = edge.get("ctrl_x", (p0["x"] + p1["x"]) // 2)
        pc_y = edge.get("ctrl_y", (p0["y"] + p1["y"]) // 2)

        # Algoritmo exacto de subdivisión Bézier cuadrática de de Casteljau (t = 0.5)
        mid_x = int(round(0.25 * p0["x"] + 0.5 * pc_x + 0.25 * p1["x"]))
        mid_y = int(round(0.25 * p0["y"] + 0.5 * pc_y + 0.25 * p1["y"]))

        ctrl1_x = int(round((p0["x"] + pc_x) / 2.0))
        ctrl1_y = int(round((p0["y"] + pc_y) / 2.0))

        ctrl2_x = int(round((pc_x + p1["x"]) / 2.0))
        ctrl2_y = int(round((pc_y + p1["y"]) / 2.0))

        # Crear nuevo nodo intermedio
        new_id = max([n["id"] for n in self.nodes], default=-1) + 1
        new_node = {
            "id": new_id,
            "x": mid_x,
            "y": mid_y,
            "is_stop": False,
            "name": f"Nodo {new_id + 1}"
        }
        self.nodes.append(new_node)

        # Reemplazar la arista por las dos nuevas mitades
        was_hidden = edge.get("hidden", False)
        target_to = edge["to"]

        # Arista 1 (P0 -> NewNode)
        edge["to"] = new_id
        edge["ctrl_x"] = ctrl1_x
        edge["ctrl_y"] = ctrl1_y

        # Arista 2 (NewNode -> P1)
        self.edges.append({
            "from": new_id,
            "to": target_to,
            "ctrl_x": ctrl2_x,
            "ctrl_y": ctrl2_y,
            "hidden": was_hidden
        })

        self.selected_node_id = new_id
        self.selected_edge_idx = len(self.edges) - 1
        self.toast_msg = f"✓ Nodo intermedio #{new_id + 1} insertado en la curva"
        self.toast_timer = 2.0
        self._notify_change()
        return True

    def connect_nodes(self, from_id: int, to_id: int) -> bool:
        """Crea una conexión vial directa entre dos nodos existentes."""
        if from_id == to_id:
            return False
        # Evitar duplicar arista
        for ed in self.edges:
            if (ed["from"] == from_id and ed["to"] == to_id) or (ed["from"] == to_id and ed["to"] == from_id):
                self.toast_msg = "Esos nodos ya están conectados"
                self.toast_timer = 1.5
                return False

        n0 = self.get_node(from_id)
        n1 = self.get_node(to_id)
        if not n0 or not n1:
            return False

        ctrl_x = (n0["x"] + n1["x"]) // 2
        ctrl_y = (n0["y"] + n1["y"]) // 2
        self.edges.append({
            "from": from_id,
            "to": to_id,
            "ctrl_x": ctrl_x,
            "ctrl_y": ctrl_y,
            "hidden": False
        })
        self.selected_edge_idx = len(self.edges) - 1
        self.selected_node_id = to_id
        self.toast_msg = f"✓ Conectado: Nodo #{from_id + 1} ↔ Nodo #{to_id + 1}"
        self.toast_timer = 2.0
        self._notify_change()
        return True

    def delete_selected(self) -> bool:
        """Elimina el nodo o arista seleccionada."""
        if self.selected_node_id != -1:
            nid = self.selected_node_id
            # Eliminar aristas asociadas
            self.edges = [e for e in self.edges if e["from"] != nid and e["to"] != nid]
            self.nodes = [n for n in self.nodes if n["id"] != nid]
            self.selected_node_id = self.nodes[-1]["id"] if self.nodes else -1
            self.selected_edge_idx = -1
            self.toast_msg = "Nodo eliminado"
            self.toast_timer = 1.2
            self._notify_change()
            return True

        elif 0 <= self.selected_edge_idx < len(self.edges):
            self.edges.pop(self.selected_edge_idx)
            self.selected_edge_idx = -1
            self.toast_msg = "Tramo de calle eliminado"
            self.toast_timer = 1.2
            self._notify_change()
            return True
        return False

    def handle_event(
        self,
        event: pygame.event.Event,
        camera_pos: Tuple[float, float],
        poi_rects: Optional[Dict[str, pygame.Rect]] = None
    ) -> bool:
        """Procesa eventos para el DevTool. Retorna True si el evento fue consumido."""
        if poi_rects:
            self.last_poi_rects.update(poi_rects)

        # Toggle F1
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.enabled = not self.enabled
            self.toast_msg = f"DevTool {'ACTIVADO' if self.enabled else 'DESACTIVADO'}"
            self.toast_timer = 1.5
            return True

        # Click botón toggle superior
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.toggle_rect.collidepoint(event.pos):
                self.enabled = not self.enabled
                self.toast_msg = f"DevTool {'ACTIVADO' if self.enabled else 'DESACTIVADO'}"
                self.toast_timer = 1.5
                return True

        if not self.enabled:
            return False

        cam_x, cam_y = camera_pos
        world_mouse_x = int(event.pos[0] + cam_x) if hasattr(event, "pos") else 0
        world_mouse_y = int(event.pos[1] + cam_y) if hasattr(event, "pos") else 0

        # ----------------------------------------------------
        # 1. Rueda del ratón (MOUSEWHEEL)
        # ----------------------------------------------------
        if event.type == pygame.MOUSEWHEEL:
            mods = pygame.key.get_mods()
            if self.mode == "pois":
                poi_cfg = self.layout_data["pois"].get(self.active_poi_key)
                if poi_cfg:
                    if mods & pygame.KMOD_CTRL:
                        rot_step = 15.0 if (mods & pygame.KMOD_SHIFT) else 5.0
                        direction = 1.0 if event.y > 0 else -1.0
                        poi_cfg["angle"] = round((poi_cfg.get("angle", 0.0) + direction * rot_step) % 360, 1)
                    else:
                        scale_step = 25 if (mods & pygame.KMOD_SHIFT) else 5
                        delta = scale_step if event.y > 0 else -scale_step
                        poi_cfg["width"] = max(80, min(1600, int(poi_cfg["width"] + delta)))
                    self._notify_change()
                    return True

            elif self.mode == "paths":
                if mods & pygame.KMOD_CTRL:
                    delta_a = 15 if event.y > 0 else -15
                    self.street_shader["alpha"] = max(20, min(255, self.street_shader["alpha"] + delta_a))
                else:
                    delta_w = 2 if event.y > 0 else -2
                    self.street_shader["width"] = max(6, min(80, self.street_shader["width"] + delta_w))
                self._notify_change()
                return True

        # ----------------------------------------------------
        # 2. Teclado
        # ----------------------------------------------------
        if event.type == pygame.KEYDOWN:
            # Guardar F5 o Ctrl+S
            if event.key == pygame.K_F5 or (event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL)):
                self.save_layout()
                return True

            # Tecla P: Alternar Modo POIs / Modo Caminos
            if event.key == pygame.K_p:
                self.mode = "paths" if self.mode == "pois" else "pois"
                self.toast_msg = f"Modo activo: {self.mode.upper()}"
                self.toast_timer = 1.5
                return True

            # Atajos Modo Caminos (I, H, L, C, Supr)
            if self.mode == "paths":
                # I: Insertar nodo medio en la curva
                if event.key == pygame.K_i:
                    return self.split_selected_edge()

                # H: Alternar tramo oculto / túnel
                if event.key == pygame.K_h:
                    if 0 <= self.selected_edge_idx < len(self.edges):
                        ed = self.edges[self.selected_edge_idx]
                        ed["hidden"] = not ed.get("hidden", False)
                        st = "OCULTO (Túnel)" if ed["hidden"] else "VISIBLE"
                        self.toast_msg = f"Tramo: {st}"
                        self.toast_timer = 1.5
                        self._notify_change()
                        return True
                    elif self.selected_node_id != -1:
                        # Buscar arista asociada
                        for ed in self.edges:
                            if ed["to"] == self.selected_node_id or ed["from"] == self.selected_node_id:
                                ed["hidden"] = not ed.get("hidden", False)
                                st = "OCULTO (Túnel)" if ed["hidden"] else "VISIBLE"
                                self.toast_msg = f"Tramo: {st}"
                                self.toast_timer = 1.5
                                self._notify_change()
                                return True

                # L: Alternar punto de nivel / parada
                if event.key == pygame.K_l:
                    cur_node = self.get_node(self.selected_node_id)
                    if cur_node:
                        cur_node["is_stop"] = not cur_node.get("is_stop", False)
                        st = "PARADA / NIVEL (★)" if cur_node["is_stop"] else "VÍA REGULAR"
                        self.toast_msg = f"Nodo #{cur_node['id'] + 1}: {st}"
                        self.toast_timer = 1.8
                        self._notify_change()
                        return True

                # C: Limpiar todos los caminos
                if event.key == pygame.K_c:
                    self.nodes.clear()
                    self.edges.clear()
                    self.selected_node_id = -1
                    self.selected_edge_idx = -1
                    self.toast_msg = "Red de caminos eliminada"
                    self.toast_timer = 1.5
                    self._notify_change()
                    return True

                # Supr o Retroceso: Eliminar seleccionado
                if event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                    return self.delete_selected()

            # Teclas 1 a 8 en modo POIs
            if self.mode == "pois":
                poi_keys = list(self.layout_data["pois"].keys())
                if pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    if idx < len(poi_keys):
                        self.active_poi_key = poi_keys[idx]
                        self.toast_msg = f"Seleccionado: {self.layout_data['pois'][self.active_poi_key].get('name', self.active_poi_key)}"
                        self.toast_timer = 1.2
                        return True

                # M: elegir la fuente de control del contenido del POI.
                if event.key == pygame.K_m:
                    poi_cfg = self.layout_data["pois"].get(self.active_poi_key)
                    if poi_cfg is not None:
                        modes = ["keyboard_gamepad", "hybrid", "camera_marker"]
                        current = poi_cfg.get("control_mode", modes[0])
                        next_mode = modes[(modes.index(current) + 1) % len(modes)] if current in modes else modes[0]
                        poi_cfg["control_mode"] = next_mode
                        self.toast_msg = f"Control: {next_mode}"
                        self.toast_timer = 1.5
                        self._notify_change()
                        return True

                poi_cfg = self.layout_data["pois"].get(self.active_poi_key)
                if poi_cfg:
                    mods = pygame.key.get_mods()
                    is_shift = bool(mods & pygame.KMOD_SHIFT)

                    pos_step = 10 if is_shift else 1
                    if event.key == pygame.K_LEFT:
                        poi_cfg["x"] -= pos_step
                        self._notify_change()
                        return True
                    elif event.key == pygame.K_RIGHT:
                        poi_cfg["x"] += pos_step
                        self._notify_change()
                        return True
                    elif event.key == pygame.K_UP:
                        poi_cfg["y"] -= pos_step
                        self._notify_change()
                        return True
                    elif event.key == pygame.K_DOWN:
                        poi_cfg["y"] += pos_step
                        self._notify_change()
                        return True

                    scale_step = 25 if is_shift else 5
                    if event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS, pygame.K_e, pygame.K_RIGHTBRACKET):
                        poi_cfg["width"] = min(1600, poi_cfg["width"] + scale_step)
                        self._notify_change()
                        return True
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_q, pygame.K_LEFTBRACKET):
                        poi_cfg["width"] = max(80, poi_cfg["width"] - scale_step)
                        self._notify_change()
                        return True

                    rot_step = 15.0 if is_shift else 5.0
                    if event.key == pygame.K_r:
                        direction = -1.0 if is_shift else 1.0
                        poi_cfg["angle"] = round((poi_cfg.get("angle", 0.0) + direction * rot_step) % 360, 1)
                        self._notify_change()
                        return True
                    elif event.key == pygame.K_t:
                        poi_cfg["angle"] = round((poi_cfg.get("angle", 0.0) - rot_step) % 360, 1)
                        self._notify_change()
                        return True
                    elif event.key in (pygame.K_0, pygame.K_KP0):
                        poi_cfg["angle"] = 0.0
                        self._notify_change()
                        return True

        # ----------------------------------------------------
        # 3. Clicks del Ratón (MOUSEBUTTONDOWN)
        # ----------------------------------------------------
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # 3.1. Clicks sobre el Panel UI
                if self.panel_rect.collidepoint(event.pos):
                    if self.save_btn_rect.collidepoint(event.pos):
                        self.save_layout()
                        return True

                    if self.mode == "pois":
                        for p_key, chip_rect in self.poi_chip_rects.items():
                            if chip_rect.collidepoint(event.pos):
                                self.active_poi_key = p_key
                                self.toast_msg = f"Seleccionado: {self.layout_data['pois'][p_key].get('name', p_key)}"
                                self.toast_timer = 1.2
                                return True

                        poi_cfg = self.layout_data["pois"].get(self.active_poi_key)
                        if poi_cfg:
                            if self.scale_dec_btn_rect.collidepoint(event.pos):
                                poi_cfg["width"] = max(80, poi_cfg["width"] - 10)
                                self._notify_change()
                                return True
                            elif self.scale_inc_btn_rect.collidepoint(event.pos):
                                poi_cfg["width"] = min(1600, poi_cfg["width"] + 10)
                                self._notify_change()
                                return True
                            elif self.rot_dec_btn_rect.collidepoint(event.pos):
                                poi_cfg["angle"] = round((poi_cfg.get("angle", 0.0) - 5.0) % 360, 1)
                                self._notify_change()
                                return True
                            elif self.rot_inc_btn_rect.collidepoint(event.pos):
                                poi_cfg["angle"] = round((poi_cfg.get("angle", 0.0) + 5.0) % 360, 1)
                                self._notify_change()
                                return True
                            elif self.rot_reset_btn_rect.collidepoint(event.pos):
                                poi_cfg["angle"] = 0.0
                                self._notify_change()
                                return True

                    elif self.mode == "paths":
                        # Insertar Nodo Medio
                        if self.path_mid_btn_rect.collidepoint(event.pos):
                            return self.split_selected_edge()

                        # Marcar Parada / Nivel
                        elif self.path_stop_btn_rect.collidepoint(event.pos):
                            cur_node = self.get_node(self.selected_node_id)
                            if cur_node:
                                cur_node["is_stop"] = not cur_node.get("is_stop", False)
                                self.toast_msg = f"Nodo #{cur_node['id'] + 1}: {'PARADA (★)' if cur_node['is_stop'] else 'VÍA'}"
                                self.toast_timer = 1.5
                                self._notify_change()
                                return True

                        # Ocultar Tramo (Túnel)
                        elif self.path_hidden_btn_rect.collidepoint(event.pos):
                            if 0 <= self.selected_edge_idx < len(self.edges):
                                ed = self.edges[self.selected_edge_idx]
                                ed["hidden"] = not ed.get("hidden", False)
                                self.toast_msg = f"Tramo: {'OCULTO (Túnel)' if ed['hidden'] else 'VISIBLE'}"
                                self.toast_timer = 1.5
                                self._notify_change()
                                return True
                            elif self.selected_node_id != -1:
                                for ed in self.edges:
                                    if ed["to"] == self.selected_node_id or ed["from"] == self.selected_node_id:
                                        ed["hidden"] = not ed.get("hidden", False)
                                        self.toast_msg = f"Tramo: {'OCULTO (Túnel)' if ed['hidden'] else 'VISIBLE'}"
                                        self.toast_timer = 1.5
                                        self._notify_change()
                                        return True

                        # Enderezar Curva
                        elif self.path_straight_btn_rect.collidepoint(event.pos):
                            if 0 <= self.selected_edge_idx < len(self.edges):
                                ed = self.edges[self.selected_edge_idx]
                                p0 = self.get_node(ed["from"])
                                p1 = self.get_node(ed["to"])
                                if p0 and p1:
                                    ed["ctrl_x"] = (p0["x"] + p1["x"]) // 2
                                    ed["ctrl_y"] = (p0["y"] + p1["y"]) // 2
                                    self.toast_msg = "Curva enderezada a recta"
                                    self.toast_timer = 1.2
                                    self._notify_change()
                                    return True

                        # Ancho y Opacidad
                        elif self.shader_w_dec_rect.collidepoint(event.pos):
                            self.street_shader["width"] = max(6, self.street_shader["width"] - 2)
                            self._notify_change()
                            return True
                        elif self.shader_w_inc_rect.collidepoint(event.pos):
                            self.street_shader["width"] = min(80, self.street_shader["width"] + 2)
                            self._notify_change()
                            return True
                        elif self.shader_a_dec_rect.collidepoint(event.pos):
                            self.street_shader["alpha"] = max(20, self.street_shader["alpha"] - 15)
                            self._notify_change()
                            return True
                        elif self.shader_a_inc_rect.collidepoint(event.pos):
                            self.street_shader["alpha"] = min(255, self.street_shader["alpha"] + 15)
                            self._notify_change()
                            return True

                        # Paleta
                        for r, name, col in self.palette_btn_rects:
                            if r.collidepoint(event.pos):
                                self.street_shader["color"] = list(col)
                                self.toast_msg = f"Color calle: {name}"
                                self.toast_timer = 1.2
                                self._notify_change()
                                return True

                        # Borrar
                        if self.delete_pt_btn_rect.collidepoint(event.pos):
                            return self.delete_selected()

                    return True

            # ------------------------------------------------
            # 3.2. Clicks en el Mundo
            # ------------------------------------------------
            if self.mode == "pois" and event.button == 1:
                for p_key in reversed(list(self.layout_data["pois"].keys())):
                    p_cfg = self.layout_data["pois"][p_key]
                    rect = self.last_poi_rects.get(p_key)
                    if rect is None:
                        rect = pygame.Rect(p_cfg["x"], p_cfg["y"], p_cfg["width"], int(p_cfg["width"] * 0.65))
                    if rect.collidepoint(world_mouse_x, world_mouse_y):
                        self.active_poi_key = p_key
                        self.is_dragging_poi = True
                        self.drag_offset = (world_mouse_x - p_cfg["x"], world_mouse_y - p_cfg["y"])
                        return True

            elif self.mode == "paths":
                if event.button == 1:
                    mods = pygame.key.get_mods()

                    # 1. Comprobar si tocó una Manija Bézier (ctrl_x, ctrl_y)
                    for idx, ed in enumerate(self.edges):
                        dist = math.hypot(ed["ctrl_x"] - world_mouse_x, ed["ctrl_y"] - world_mouse_y)
                        if dist < 14:
                            self.selected_edge_idx = idx
                            self.selected_node_id = ed["to"]
                            self.is_dragging_edge_ctrl = True
                            return True

                    # 2. Comprobar si tocó un Nodo existente
                    for n in self.nodes:
                        dist = math.hypot(n["x"] - world_mouse_x, n["y"] - world_mouse_y)
                        if dist < 16:
                            # Si tenía un nodo seleccionado y pulsó Shift: Conectar ambos nodos
                            if (mods & pygame.KMOD_SHIFT) and self.selected_node_id != -1 and self.selected_node_id != n["id"]:
                                self.connect_nodes(self.selected_node_id, n["id"])
                                return True
                            # Si no es Shift: simplemente seleccionar este nodo como origen de futuras ramas
                            self.selected_node_id = n["id"]
                            self.is_dragging_node = True
                            self.toast_msg = f"Nodo #{n['id'] + 1} seleccionado (Origen de rama)"
                            self.toast_timer = 1.5
                            return True

                    # 3. Click en espacio vacío: Crear nuevo nodo conectado al nodo seleccionado (o al último)
                    new_id = max([n["id"] for n in self.nodes], default=-1) + 1
                    new_node = {
                        "id": new_id,
                        "x": world_mouse_x,
                        "y": world_mouse_y,
                        "is_stop": False,
                        "name": f"Nodo {new_id + 1}"
                    }
                    self.nodes.append(new_node)

                    # Si hay un nodo de origen seleccionado (o si ya había nodos), conectar la nueva rama
                    origin_id = self.selected_node_id if self.selected_node_id != -1 else (self.nodes[-2]["id"] if len(self.nodes) > 1 else -1)
                    if origin_id != -1 and origin_id != new_id:
                        orig_node = self.get_node(origin_id)
                        if orig_node:
                            ctrl_x = (orig_node["x"] + world_mouse_x) // 2
                            ctrl_y = (orig_node["y"] + world_mouse_y) // 2
                            self.edges.append({
                                "from": origin_id,
                                "to": new_id,
                                "ctrl_x": ctrl_x,
                                "ctrl_y": ctrl_y,
                                "hidden": False
                            })
                            self.selected_edge_idx = len(self.edges) - 1

                    self.selected_node_id = new_id
                    self.is_dragging_node = True
                    self._notify_change()
                    return True

                elif event.button == 3:
                    # Click derecho en manija Bézier: enderezar
                    for idx, ed in enumerate(self.edges):
                        dist = math.hypot(ed["ctrl_x"] - world_mouse_x, ed["ctrl_y"] - world_mouse_y)
                        if dist < 14:
                            p0 = self.get_node(ed["from"])
                            p1 = self.get_node(ed["to"])
                            if p0 and p1:
                                ed["ctrl_x"] = (p0["x"] + p1["x"]) // 2
                                ed["ctrl_y"] = (p0["y"] + p1["y"]) // 2
                                self.toast_msg = "Curva enderezada a recta"
                                self.toast_timer = 1.2
                                self._notify_change()
                                return True

                    # Click derecho en nodo: eliminar
                    for n in self.nodes:
                        dist = math.hypot(n["x"] - world_mouse_x, n["y"] - world_mouse_y)
                        if dist < 16:
                            self.selected_node_id = n["id"]
                            self.delete_selected()
                            return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.is_dragging_poi:
                    self.is_dragging_poi = False
                    return True
                if self.is_dragging_node:
                    self.is_dragging_node = False
                    return True
                if self.is_dragging_edge_ctrl:
                    self.is_dragging_edge_ctrl = False
                    return True

        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging_poi and self.mode == "pois":
                poi_cfg = self.layout_data["pois"].get(self.active_poi_key)
                if poi_cfg:
                    poi_cfg["x"] = world_mouse_x - self.drag_offset[0]
                    poi_cfg["y"] = world_mouse_y - self.drag_offset[1]
                    self._notify_change()
                return True

            elif self.is_dragging_node and self.mode == "paths":
                cur_node = self.get_node(self.selected_node_id)
                if cur_node:
                    dx = world_mouse_x - cur_node["x"]
                    dy = world_mouse_y - cur_node["y"]
                    cur_node["x"] = world_mouse_x
                    cur_node["y"] = world_mouse_y
                    # Acompañar las manijas Bézier de aristas conectadas
                    for ed in self.edges:
                        if ed["from"] == cur_node["id"] or ed["to"] == cur_node["id"]:
                            ed["ctrl_x"] = ed.get("ctrl_x", cur_node["x"]) + dx // 2
                            ed["ctrl_y"] = ed.get("ctrl_y", cur_node["y"]) + dy // 2
                    self._notify_change()
                return True

            elif self.is_dragging_edge_ctrl and self.mode == "paths":
                if 0 <= self.selected_edge_idx < len(self.edges):
                    self.edges[self.selected_edge_idx]["ctrl_x"] = world_mouse_x
                    self.edges[self.selected_edge_idx]["ctrl_y"] = world_mouse_y
                    self._notify_change()
                return True

        return False

    def render(self, surface: pygame.Surface, camera_pos: Tuple[float, float], poi_rects: Dict[str, pygame.Rect]) -> None:
        """Renderiza la interfaz DevTool, bounding boxes, shader de calles, red vial, curvas Bézier y manijas."""
        self.last_poi_rects = poi_rects
        cam_x, cam_y = camera_pos

        btn_col = (45, 160, 90) if self.enabled else (40, 50, 70)
        pygame.draw.rect(surface, btn_col, self.toggle_rect, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), self.toggle_rect, width=1, border_radius=8)
        label_btn = "🛠️ DEV ON" if self.enabled else "🛠️ DEV TOOLS"
        txt_btn = self.font_body.render(label_btn, True, (255, 255, 255))
        surface.blit(txt_btn, txt_btn.get_rect(center=self.toggle_rect.center))

        if not self.enabled:
            return

        # ----------------------------------------------------
        # 1. Renderizar Red Vial, Shader de Calle y Curvas Bézier
        # ----------------------------------------------------
        sh_color = tuple(self.street_shader.get("color", [245, 185, 55]))
        sh_alpha = int(self.street_shader.get("alpha", 120))
        sh_width = int(self.street_shader.get("width", 26))

        node_map = {n["id"]: n for n in self.nodes}

        for idx, ed in enumerate(self.edges):
            p0 = node_map.get(ed["from"])
            p1 = node_map.get(ed["to"])
            if not p0 or not p1:
                continue

            pc = (ed.get("ctrl_x", (p0["x"] + p1["x"]) // 2), ed.get("ctrl_y", (p0["y"] + p1["y"]) // 2))
            bezier_pts = get_bezier_points((p0["x"], p0["y"]), pc, (p1["x"], p1["y"]), step_px=8)
            screen_curve = [(int(pt[0] - cam_x), int(pt[1] - cam_y)) for pt in bezier_pts]

            is_hidden = ed.get("hidden", False)
            is_edge_sel = (idx == self.selected_edge_idx)

            # 1.1. Tinte Shader de Calle sobre la curva
            if len(screen_curve) > 1:
                tint_col = (145, 80, 205, max(40, sh_alpha - 20)) if is_hidden else (sh_color[0], sh_color[1], sh_color[2], sh_alpha)
                pygame.draw.lines(surface, (20, 25, 40), False, screen_curve, sh_width + 4)
                pygame.draw.lines(surface, tint_col[:3], False, screen_curve, sh_width)
                for pt in screen_curve:
                    pygame.draw.circle(surface, tint_col[:3], pt, sh_width // 2)

                core_col = (255, 230, 140) if is_edge_sel else (255, 255, 255)
                pygame.draw.lines(surface, core_col, False, screen_curve, 2)

            # 1.2. Manija Bézier y líneas tangentes (en modo paths)
            if self.mode == "paths":
                sx0, sy0 = int(p0["x"] - cam_x), int(p0["y"] - cam_y)
                sxc, syc = int(pc[0] - cam_x), int(pc[1] - cam_y)
                sx1, sy1 = int(p1["x"] - cam_x), int(p1["y"] - cam_y)

                pygame.draw.line(surface, (100, 220, 255), (sx0, sy0), (sxc, syc), 1)
                pygame.draw.line(surface, (100, 220, 255), (sx1, sy1), (sxc, syc), 1)

                handle_rect = pygame.Rect(sxc - 6, syc - 6, 12, 12)
                h_bg = (255, 120, 50) if is_edge_sel else (20, 35, 55)
                pygame.draw.rect(surface, h_bg, handle_rect)
                pygame.draw.rect(surface, (80, 235, 255), handle_rect, width=2)
                pygame.draw.circle(surface, (255, 255, 255), (sxc, syc), 2)

            if is_hidden and len(screen_curve) > 1:
                mid_pt = screen_curve[len(screen_curve) // 2]
                tag_t = self.font_small.render("🚇 TÚNEL (OCULTO)", True, (245, 210, 255))
                t_r = pygame.Rect(mid_pt[0] - tag_t.get_width() // 2 - 4, mid_pt[1] - 18, tag_t.get_width() + 8, 16)
                pygame.draw.rect(surface, (45, 20, 70, 220), t_r, border_radius=4)
                surface.blit(tag_t, (t_r.x + 4, t_r.y + 1))

        # 1.3. Nodos de la Red Vial
        for n in self.nodes:
            sx = int(n["x"] - cam_x)
            sy = int(n["y"] - cam_y)
            is_sel = (n["id"] == self.selected_node_id)
            is_stop = n.get("is_stop", False)

            radius = 12 if is_stop else 8
            border_c = (255, 240, 90) if is_sel else (20, 30, 45)
            pygame.draw.circle(surface, border_c, (sx, sy), radius + 3)

            if is_stop:
                fill_c = (255, 75, 75) if is_sel else (245, 195, 45)
            else:
                fill_c = (255, 100, 100) if is_sel else (60, 220, 130)
            pygame.draw.circle(surface, fill_c, (sx, sy), radius)
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 3)

            lbl_pt = f"★{n['id'] + 1}" if is_stop else str(n["id"] + 1)
            t_num = self.font_small.render(lbl_pt, True, (255, 255, 255))
            surface.blit(t_num, (sx - t_num.get_width() // 2, sy - radius - 15))

        # ----------------------------------------------------
        # 2. Renderizar Bounding Boxes de los POIs
        # ----------------------------------------------------
        for p_key, rect in poi_rects.items():
            screen_r = pygame.Rect(rect.x - int(cam_x), rect.y - int(cam_y), rect.width, rect.height)
            is_active = (p_key == self.active_poi_key and self.mode == "pois")
            color = (255, 220, 60) if is_active else (80, 180, 255)
            width = 3 if is_active else 1

            pygame.draw.rect(surface, color, screen_r, width=width, border_radius=6)

            p_cfg = self.layout_data["pois"].get(p_key, {})
            tag_name = p_cfg.get("name", p_key)
            cur_angle = p_cfg.get("angle", 0)

            if is_active:
                rad = math.radians(float(cur_angle) - 90.0)
                cx, cy = screen_r.center
                needle_len = min(40, max(18, screen_r.width // 4))
                ex = int(cx + math.cos(rad) * needle_len)
                ey = int(cy + math.sin(rad) * needle_len)
                pygame.draw.circle(surface, (255, 220, 60), (cx, cy), 5)
                pygame.draw.line(surface, (255, 80, 80), (cx, cy), (ex, ey), 3)
                pygame.draw.circle(surface, (255, 80, 80), (ex, ey), 4)

            tag_str = f"{tag_name} [{p_cfg.get('level_id', p_key)} · {p_cfg.get('microgame_id', 'sin juego')}]"
            tag_txt = self.font_small.render(tag_str, True, (255, 255, 255))
            tag_bg = pygame.Rect(screen_r.x, screen_r.y - 20, tag_txt.get_width() + 10, 18)
            pygame.draw.rect(surface, (20, 25, 40, 220), tag_bg, border_radius=4)
            surface.blit(tag_txt, (tag_bg.x + 5, tag_bg.y + 2))

        # ----------------------------------------------------
        # 3. Panel de Control DevTool
        # ----------------------------------------------------
        panel_surf = pygame.Surface((self.panel_w, self.panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (15, 20, 32, 240), (0, 0, self.panel_w, self.panel_h), border_radius=14)
        pygame.draw.rect(panel_surf, (240, 190, 70), (0, 0, self.panel_w, self.panel_h), width=2, border_radius=14)

        txt_title = self.font_title.render("🛠️ EDITOR DE MAPA Y RED VIAL", True, (255, 220, 80))
        panel_surf.blit(txt_title, (16, 12))

        mode_label = "📍 POIS (X, Y, ANCHO, ÁNGULO)" if self.mode == "pois" else "🛣️ RED VIAL, RAMAS Y BÉZIER"
        txt_mode = self.font_body.render(f"Modo: {mode_label} [P]", True, (100, 220, 255))
        panel_surf.blit(txt_mode, (16, 36))

        surface.blit(panel_surf, (self.panel_x, self.panel_y))

        # 3.1. RENDER MODO POIS
        if self.mode == "pois":
            poi_keys = list(self.layout_data["pois"].keys())
            for i, key in enumerate(poi_keys):
                chip_r = self.poi_chip_rects.get(key)
                if chip_r:
                    is_sel = (key == self.active_poi_key)
                    bg_col = (235, 175, 45) if is_sel else (35, 45, 65)
                    tx_col = (20, 20, 20) if is_sel else (220, 230, 245)
                    pygame.draw.rect(surface, bg_col, chip_r, border_radius=5)
                    pygame.draw.rect(surface, (180, 200, 230), chip_r, width=1, border_radius=5)
                    short_name = f"{i+1}.{key[:4].capitalize()}"
                    txt_chip = self.font_btn.render(short_name, True, tx_col)
                    surface.blit(txt_chip, txt_chip.get_rect(center=chip_r.center))

            poi_info = self.layout_data["pois"].get(self.active_poi_key, {})
            txt_poi = self.font_body.render(f"Activo: {poi_info.get('name', self.active_poi_key)}", True, (255, 255, 255))
            surface.blit(txt_poi, (self.panel_x + 16, self.panel_y + 116))

            txt_meta = self.font_small.render(
                f"Nivel: {poi_info.get('level_id', self.active_poi_key)} | Juego: {poi_info.get('microgame_id', 'sin asignar')} | {poi_info.get('kind', 'extra').upper()}",
                True, (255, 220, 120)
            )
            surface.blit(txt_meta, (self.panel_x + 16, self.panel_y + 202))
            txt_ctrl = self.font_small.render(
                f"Control: {poi_info.get('control_mode', 'keyboard_gamepad')} (M cambia modo)",
                True, (150, 230, 255)
            )
            surface.blit(txt_ctrl, (self.panel_x + 16, self.panel_y + 218))

            txt_coords = self.font_small.render(f"Posición: X = {poi_info.get('x', 0)}, Y = {poi_info.get('y', 0)}", True, (210, 220, 235))
            surface.blit(txt_coords, (self.panel_x + 16, self.panel_y + 136))

            txt_dim = self.font_small.render(f"Ancho: {poi_info.get('width', 0)} px (Q / E o Rueda)", True, (210, 220, 235))
            surface.blit(txt_dim, (self.panel_x + 16, self.panel_y + 156))
            for btn_r, lbl in [(self.scale_dec_btn_rect, "-"), (self.scale_inc_btn_rect, "+")]:
                pygame.draw.rect(surface, (45, 58, 85), btn_r, border_radius=4)
                pygame.draw.rect(surface, (130, 160, 210), btn_r, width=1, border_radius=4)
                t = self.font_btn.render(lbl, True, (255, 255, 255))
                surface.blit(t, t.get_rect(center=btn_r.center))

            txt_rot = self.font_small.render(f"Ángulo: {poi_info.get('angle', 0)}° (R / T o Ctrl+Rueda)", True, (255, 225, 120))
            surface.blit(txt_rot, (self.panel_x + 16, self.panel_y + 182))
            for btn_r, lbl in [
                (self.rot_dec_btn_rect, "↺ -5°"),
                (self.rot_inc_btn_rect, "↻ +5°"),
                (self.rot_reset_btn_rect, "0°")
            ]:
                pygame.draw.rect(surface, (55, 45, 75), btn_r, border_radius=4)
                pygame.draw.rect(surface, (210, 160, 230), btn_r, width=1, border_radius=4)
                t = self.font_btn.render(lbl, True, (255, 255, 255))
                surface.blit(t, t.get_rect(center=btn_r.center))

            instructions = [
                "• Mover: Arrastrar o Flechas (Shift: 10px)",
                "• Ancho: Teclas +, -, Q, E o Rueda Ratón",
                "• Giro: Teclas R, T o Ctrl + Rueda Ratón",
                "• POIs 1 a 8: Cambiar selección",
                "• Tecla P: Alternar a Modo Red Vial y Curvas",
                "• Guardar: F5, Ctrl+S o botón Guardar"
            ]
            curr_y = self.panel_y + 214
            for line in instructions:
                t = self.font_small.render(line, True, (170, 185, 205))
                surface.blit(t, (self.panel_x + 16, curr_y))
                curr_y += 18

        # 3.2. RENDER MODO RED VIAL, RAMAS Y SHADER
        elif self.mode == "paths":
            cur_node = self.get_node(self.selected_node_id)
            sel_edge = self.edges[self.selected_edge_idx] if (0 <= self.selected_edge_idx < len(self.edges)) else None

            # Info del nodo / rama seleccionada
            if cur_node:
                sel_str = f"Rama activa: Nodo #{cur_node['id'] + 1} (Origen)"
                coords_str = f"Pos: ({cur_node['x']}, {cur_node['y']}) | Tipo: {'[★ PARADA]' if cur_node.get('is_stop') else '[VÍA]'}"
            else:
                sel_str = f"Red Vial: {len(self.nodes)} nodos, {len(self.edges)} calles"
                coords_str = "Click en cualquier nodo para sacar una rama de él"

            txt_p_info = self.font_body.render(sel_str, True, (255, 225, 90) if cur_node else (255, 255, 255))
            surface.blit(txt_p_info, (self.panel_x + 16, self.panel_y + 68))

            t_c = self.font_small.render(coords_str, True, (190, 215, 240))
            surface.blit(t_c, (self.panel_x + 16, self.panel_y + 90))

            if sel_edge:
                hid = sel_edge.get("hidden", False)
                edge_info = f"Calle: #{sel_edge['from'] + 1} ↔ #{sel_edge['to'] + 1} | {'[🚇 TÚNEL]' if hid else '[VISIBLE]'}"
                t_ei = self.font_small.render(edge_info, True, (245, 170, 255) if hid else (160, 240, 180))
                surface.blit(t_ei, (self.panel_x + 16, self.panel_y + 112))

            # Fila 1 de Botones: [+ Nodo Medio], [★ Parada], [👁️ Ocultar]
            pygame.draw.rect(surface, (45, 75, 110), self.path_mid_btn_rect, border_radius=5)
            pygame.draw.rect(surface, (140, 205, 255), self.path_mid_btn_rect, width=1, border_radius=5)
            t_mid = self.font_btn.render("+ N.MEDIO (I)", True, (255, 255, 255))
            surface.blit(t_mid, t_mid.get_rect(center=self.path_mid_btn_rect.center))

            btn_s_col = (180, 130, 30) if (cur_node and cur_node.get("is_stop", False)) else (40, 50, 75)
            pygame.draw.rect(surface, btn_s_col, self.path_stop_btn_rect, border_radius=5)
            pygame.draw.rect(surface, (240, 200, 100), self.path_stop_btn_rect, width=1, border_radius=5)
            t_bs = self.font_btn.render("★ PARADA (L)", True, (255, 255, 255))
            surface.blit(t_bs, t_bs.get_rect(center=self.path_stop_btn_rect.center))

            is_hid_btn = (sel_edge and sel_edge.get("hidden", False))
            btn_h_col = (110, 45, 140) if is_hid_btn else (40, 50, 75)
            pygame.draw.rect(surface, btn_h_col, self.path_hidden_btn_rect, border_radius=5)
            pygame.draw.rect(surface, (200, 150, 240), self.path_hidden_btn_rect, width=1, border_radius=5)
            t_bh = self.font_btn.render("👁️ OCULTAR (H)", True, (255, 255, 255))
            surface.blit(t_bh, t_bh.get_rect(center=self.path_hidden_btn_rect.center))

            # Fila 2 de Botones: [↺ Recta] y Ajustes de Shader
            pygame.draw.rect(surface, (45, 55, 80), self.path_straight_btn_rect, border_radius=5)
            pygame.draw.rect(surface, (140, 175, 220), self.path_straight_btn_rect, width=1, border_radius=5)
            t_str = self.font_btn.render("↺ Recta", True, (255, 255, 255))
            surface.blit(t_str, t_str.get_rect(center=self.path_straight_btn_rect.center))

            txt_sh_w = self.font_small.render(f"Ancho: {self.street_shader['width']}px", True, (220, 230, 245))
            surface.blit(txt_sh_w, (self.panel_x + 112, self.panel_y + 172))
            for b_r, l in [(self.shader_w_dec_rect, "-"), (self.shader_w_inc_rect, "+")]:
                pygame.draw.rect(surface, (45, 58, 85), b_r, border_radius=4)
                pygame.draw.rect(surface, (130, 160, 210), b_r, width=1, border_radius=4)
                t = self.font_btn.render(l, True, (255, 255, 255))
                surface.blit(t, t.get_rect(center=b_r.center))

            txt_sh_a = self.font_small.render(f"Opacidad: {self.street_shader['alpha']}", True, (220, 230, 245))
            surface.blit(txt_sh_a, (self.panel_x + 112, self.panel_y + 200))
            for b_r, l in [(self.shader_a_dec_rect, "-"), (self.shader_a_inc_rect, "+")]:
                pygame.draw.rect(surface, (45, 58, 85), b_r, border_radius=4)
                pygame.draw.rect(surface, (130, 160, 210), b_r, width=1, border_radius=4)
                t = self.font_btn.render(l, True, (255, 255, 255))
                surface.blit(t, t.get_rect(center=b_r.center))

            # Paleta de Tinte de Calle
            for r, name, col in self.palette_btn_rects:
                is_active_pal = (self.street_shader["color"] == list(col))
                pygame.draw.rect(surface, col, r, border_radius=4)
                border_pal = (255, 255, 255) if is_active_pal else (20, 25, 35)
                w_pal = 2 if is_active_pal else 1
                pygame.draw.rect(surface, border_pal, r, width=w_pal, border_radius=4)
                tx_c = (20, 20, 20) if (col[0] + col[1] + col[2]) > 400 else (255, 255, 255)
                t_pal = self.font_btn.render(name, True, tx_c)
                surface.blit(t_pal, t_pal.get_rect(center=r.center))

            # Instrucciones del Modo Red Vial
            instructions_paths = [
                "• Click en un nodo: Elige origen (la rama nace de él)",
                "• Click en mapa: Crea nodo conectado al origen",
                "• Shift + Click en otro nodo: Une los 2 nodos con calle",
                "• Tecla I o [+ N.MEDIO]: Inserta nodo en mitad de curva",
                "• Arrastrar ◆: Curva Bézier | Click Der: Enderezar",
                "• H: Marcar túnel oculto | L: Marcar parada nivel (★)"
            ]
            curr_y = self.panel_y + 258
            for line in instructions_paths:
                t = self.font_small.render(line, True, (170, 185, 205))
                surface.blit(t, (self.panel_x + 16, curr_y))
                curr_y += 18

            # Botón Borrar
            pygame.draw.rect(surface, (140, 45, 45), self.delete_pt_btn_rect, border_radius=6)
            pygame.draw.rect(surface, (240, 110, 110), self.delete_pt_btn_rect, width=1, border_radius=6)
            txt_del = self.font_body.render("🗑️ BORRAR (Supr)", True, (255, 255, 255))
            surface.blit(txt_del, txt_del.get_rect(center=self.delete_pt_btn_rect.center))

        # Botón Guardar general
        pygame.draw.rect(surface, (40, 140, 75), self.save_btn_rect, border_radius=6)
        pygame.draw.rect(surface, (110, 245, 145), self.save_btn_rect, width=1, border_radius=6)
        txt_s = self.font_body.render("💾 GUARDAR (F5)", True, (255, 255, 255))
        surface.blit(txt_s, txt_s.get_rect(center=self.save_btn_rect.center))

        # 4. Toast de notificación
        if self.toast_timer > 0.0:
            toast_w, toast_h = 440, 38
            toast_surf = pygame.Surface((toast_w, toast_h), pygame.SRCALPHA)
            pygame.draw.rect(toast_surf, (20, 30, 45, 235), (0, 0, toast_w, toast_h), border_radius=10)
            pygame.draw.rect(toast_surf, (100, 235, 150), (0, 0, toast_w, toast_h), width=2, border_radius=10)
            t_txt = self.font_body.render(self.toast_msg, True, (240, 255, 245))
            toast_surf.blit(t_txt, t_txt.get_rect(center=(toast_w // 2, toast_h // 2)))
            surface.blit(toast_surf, (self.screen_w // 2 - toast_w // 2, 25))
