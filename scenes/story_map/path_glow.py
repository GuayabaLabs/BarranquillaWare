"""
BarranquillaWare - Sistema de Camino Iluminado en Acuarela (Modo Historia)
Calcula la ruta real más corta (Dijkstra por distancia en píxeles sobre aristas visibles),
rasteriza la pincelada IA (mapa_camino_pincelada.png) sin costuras ni halos, recorta contra
la máscara alfa de edificios/monumentos (POI_SPECS) y anima la revelación con destello.
"""
from __future__ import annotations

import heapq
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pygame

from core.asset_manager import AssetManager
from tools.map_dev_tool import get_bezier_points


def compute_campaign_dijkstra_path(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    start_id: int,
    goal_id: int,
) -> Optional[List[int]]:
    """
    Calcula el trazado más corto por distancia real en píxeles (curva Bézier)
    usando únicamente aristas visibles (hidden=False) de la red vial.
    """
    if start_id == goal_id:
        return [start_id]

    node_map = {n["id"]: n for n in nodes}
    if start_id not in node_map or goal_id not in node_map:
        return None

    adj: Dict[int, List[Tuple[int, float]]] = {nid: [] for nid in node_map}
    for edge in edges:
        if edge.get("hidden", False):
            continue
        u = edge.get("from")
        v = edge.get("to")
        if u not in node_map or v not in node_map:
            continue
        nu, nv = node_map[u], node_map[v]
        p0 = (nu["x"], nu["y"])
        p1 = (nv["x"], nv["y"])
        pc = (edge.get("ctrl_x", (p0[0] + p1[0]) // 2), edge.get("ctrl_y", (p0[1] + p1[1]) // 2))
        pts = get_bezier_points(p0, pc, p1, step_px=6)
        if len(pts) >= 2:
            dist = sum(
                math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
                for i in range(1, len(pts))
            )
        else:
            dist = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        dist = max(1.0, dist)
        adj[u].append((v, dist))
        adj[v].append((u, dist))

    pq: List[Tuple[float, int, List[int]]] = [(0.0, start_id, [start_id])]
    best_dist: Dict[int, float] = {start_id: 0.0}

    while pq:
        d, curr, path = heapq.heappop(pq)
        if curr == goal_id:
            return path
        if d > best_dist.get(curr, float("inf")):
            continue
        for nbr, w in adj.get(curr, []):
            nd = d + w
            if nd < best_dist.get(nbr, float("inf")):
                best_dist[nbr] = nd
                heapq.heappush(pq, (nd, nbr, path + [nbr]))

    return None


def build_route_polyline(
    node_map: Dict[int, Dict[str, Any]],
    edge_map: Dict[Tuple[int, int], Dict[str, Any]],
    node_path: List[int],
    step_px: int = 6,
) -> Tuple[List[Tuple[float, float]], List[float], float]:
    """Muestrea puntos densos sobre las curvas Bézier de una ruta y calcula distancias acumuladas."""
    if not node_path:
        return [], [], 0.0

    pts: List[Tuple[float, float]] = []
    for i in range(len(node_path) - 1):
        u, v = node_path[i], node_path[i + 1]
        nu, nv = node_map.get(u), node_map.get(v)
        if nu is None or nv is None:
            continue
        p0 = (float(nu["x"]), float(nu["y"]))
        p1 = (float(nv["x"]), float(nv["y"]))
        edge = edge_map.get((u, v))
        if edge is not None:
            pc = (
                float(edge.get("ctrl_x", (p0[0] + p1[0]) * 0.5)),
                float(edge.get("ctrl_y", (p0[1] + p1[1]) * 0.5)),
            )
        else:
            pc = ((p0[0] + p1[0]) * 0.5, (p0[1] + p1[1]) * 0.5)
        seg_pts = get_bezier_points((int(p0[0]), int(p0[1])), (int(pc[0]), int(pc[1])), (int(p1[0]), int(p1[1])), step_px=step_px)
        if len(seg_pts) < 2:
            seg_pts = [(p0[0], p0[1]), (p1[0], p1[1])]
        for idx, pt in enumerate(seg_pts):
            if i > 0 and idx == 0 and pts:
                continue
            pts.append((float(pt[0]), float(pt[1])))

    if not pts:
        n0 = node_map.get(node_path[0])
        if n0 is not None:
            return [(float(n0["x"]), float(n0["y"]))], [0.0], 0.0
        return [], [], 0.0

    cum_dists: List[float] = [0.0]
    for i in range(1, len(pts)):
        cum_dists.append(cum_dists[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    return pts, cum_dists, cum_dists[-1]


class WatercolorRouteRenderer:
    """
    Pre-renderiza trazados viales usando exclusivamente la textura acuarela IA
    `mapa_camino_pincelada.png`, recorta contra POI_SPECS y soporta revelación progresiva
    con `mapa_destello_ruta.png`.
    """

    def __init__(self, world_w: int, world_h: int, brush_h: int = 44) -> None:
        self.world_w = world_w
        self.world_h = world_h
        self.brush_h = max(16, int(brush_h))
        self.half_w = self.brush_h * 0.5
        self.assets = AssetManager.get_instance()

        self._brush_rgba: Optional[np.ndarray] = None
        self._tile_w: int = 1
        self._sparkle_surf: Optional[pygame.Surface] = None
        self._route_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._load_assets()

    def _load_assets(self) -> None:
        try:
            raw_brush = self.assets.load_surface("mapa_camino_pincelada.png", has_alpha=True)
            bw, bh = raw_brush.get_size()
            # Recortar banda central sin bordes extremos y crear cinta palíndroma 100% continua
            crop_x0 = int(bw * 0.08)
            crop_w = max(32, int(bw * 0.84))
            sub = raw_brush.subsurface(pygame.Rect(crop_x0, 0, crop_w, bh))
            scaled_w = max(64, int(round(crop_w * (self.brush_h / float(max(1, bh))))))
            scaled = pygame.transform.smoothscale(sub, (scaled_w, self.brush_h))
            rgb = pygame.surfarray.array3d(scaled)
            alpha = pygame.surfarray.array_alpha(scaled)
            rgba = np.dstack([rgb, alpha[:, :, None]]).astype(np.uint8)
            # Palíndromo horizontal [A, reverse(A)] para cero costuras en rutas largas
            self._brush_rgba = np.concatenate([rgba, rgba[::-1, :, :]], axis=0)
            self._tile_w = self._brush_rgba.shape[0]
        except Exception as exc:
            print(f"[PathGlow] Aviso cargando mapa_camino_pincelada.png: {exc}")
            self._brush_rgba = None
            self._tile_w = 1

        try:
            raw_sp = self.assets.load_cropped_surface("mapa_destello_ruta.png", alpha_threshold=6)
            self._sparkle_surf = pygame.transform.smoothscale(raw_sp, (92, 92))
        except Exception as exc:
            print(f"[PathGlow] Aviso cargando mapa_destello_ruta.png: {exc}")
            self._sparkle_surf = None

    def invalidate_cache(self) -> None:
        self._route_cache.clear()

    def get_or_build_route(
        self,
        from_poi: str,
        to_poi: str,
        node_path: List[int],
        node_map: Dict[int, Dict[str, Any]],
        edge_map: Dict[Tuple[int, int], Dict[str, Any]],
        poi_occluders: Optional[List[Tuple[pygame.Surface, pygame.Rect]]] = None,
    ) -> Optional[Dict[str, Any]]:
        key = (from_poi, to_poi)
        if key in self._route_cache:
            return self._route_cache[key]

        pts, cum_dists, total_dist = build_route_polyline(node_map, edge_map, node_path, step_px=6)
        if len(pts) < 2 or total_dist <= 1.0:
            return None

        pad = int(math.ceil(self.half_w)) + 4
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        min_x = max(0, int(math.floor(min(xs))) - pad)
        min_y = max(0, int(math.floor(min(ys))) - pad)
        max_x = min(self.world_w, int(math.ceil(max(xs))) + pad)
        max_y = min(self.world_h, int(math.ceil(max(ys))) + pad)
        bb_w = max(1, max_x - min_x)
        bb_h = max(1, max_y - min_y)
        bbox = pygame.Rect(min_x, min_y, bb_w, bb_h)

        # Segmentos de proyección (~14 px) para rasterizado exacto sin costuras ni solapamientos
        seg_indices = list(range(0, len(pts), 2))
        if seg_indices[-1] != len(pts) - 1:
            seg_indices.append(len(pts) - 1)

        best_d2 = np.full((bb_w, bb_h), 1e9, dtype=np.float32)
        best_s = np.zeros((bb_w, bb_h), dtype=np.float32)
        r_lim = self.half_w
        r2_lim = r_lim * r_lim

        for k in range(len(seg_indices) - 1):
            i0, i1 = seg_indices[k], seg_indices[k + 1]
            ax, ay = pts[i0][0] - min_x, pts[i0][1] - min_y
            bx, by = pts[i1][0] - min_x, pts[i1][1] - min_y
            sa, sb = cum_dists[i0], cum_dists[i1]
            dx, dy = bx - ax, by - ay
            len2 = dx * dx + dy * dy
            if len2 < 1e-4:
                continue

            lx0 = max(0, int(math.floor(min(ax, bx) - r_lim - 1)))
            lx1 = min(bb_w, int(math.ceil(max(ax, bx) + r_lim + 1)))
            ly0 = max(0, int(math.floor(min(ay, by) - r_lim - 1)))
            ly1 = min(bb_h, int(math.ceil(max(ay, by) + r_lim + 1)))
            if lx1 <= lx0 or ly1 <= ly0:
                continue

            gx = np.arange(lx0, lx1, dtype=np.float32)[:, None]
            gy = np.arange(ly0, ly1, dtype=np.float32)[None, :]
            t = np.clip(((gx - ax) * dx + (gy - ay) * dy) / len2, 0.0, 1.0)
            px = ax + t * dx
            py = ay + t * dy
            d2 = (gx - px) ** 2 + (gy - py) ** 2

            sub_d2 = best_d2[lx0:lx1, ly0:ly1]
            sub_s = best_s[lx0:lx1, ly0:ly1]
            better = (d2 < sub_d2) & (d2 <= r2_lim)
            if np.any(better):
                sub_d2[better] = d2[better]
                sub_s[better] = (sa + t * (sb - sa))[better]

        full_surf = pygame.Surface((bb_w, bb_h), pygame.SRCALPHA)
        inside = best_d2 <= r2_lim
        if self._brush_rgba is not None and np.any(inside):
            dist = np.sqrt(np.minimum(best_d2, r2_lim))
            u_idx = np.mod(np.round(best_s).astype(np.int32), self._tile_w)
            v_idx = np.clip(
                np.round((0.5 + 0.5 * (dist / max(1e-4, r_lim))) * (self.brush_h - 1)).astype(np.int32),
                0,
                self.brush_h - 1,
            )
            sampled = self._brush_rgba[u_idx, v_idx]
            rgb_out = sampled[:, :, :3]
            a_out = sampled[:, :, 3].astype(np.float32)

            # Desvanecimiento limpio en extremos para entrar/salir suave de los nodos
            end_fade = np.minimum(
                np.clip(best_s / 18.0, 0.0, 1.0),
                np.clip((total_dist - best_s) / 18.0, 0.0, 1.0),
            )
            a_out = np.where(inside, a_out * end_fade, 0.0)
            a_u8 = np.clip(a_out, 0, 255).astype(np.uint8)

            arr_rgb = pygame.surfarray.pixels3d(full_surf)
            arr_a = pygame.surfarray.pixels_alpha(full_surf)
            arr_rgb[:] = rgb_out
            arr_a[:] = a_u8
            del arr_rgb, arr_a

        # Recortar contra máscara alfa de edificios/monumentos (POI_SPECS) para jamás taparlos
        if poi_occluders:
            for poi_surf, poi_rect in poi_occluders:
                inter = poi_rect.clip(bbox)
                if inter.width <= 0 or inter.height <= 0:
                    continue
                px_off = inter.x - poi_rect.x
                py_off = inter.y - poi_rect.y
                rx_off = inter.x - bbox.x
                ry_off = inter.y - bbox.y
                poi_a = pygame.surfarray.pixels_alpha(poi_surf)[
                    px_off : px_off + inter.width, py_off : py_off + inter.height
                ]
                rt_a = pygame.surfarray.pixels_alpha(full_surf)[
                    rx_off : rx_off + inter.width, ry_off : ry_off + inter.height
                ]
                rt_a[poi_a >= 6] = 0
                del poi_a, rt_a

        norm_s = np.clip(best_s / max(1.0, total_dist), 0.0, 1.0).astype(np.float32)
        full_alpha = pygame.surfarray.array_alpha(full_surf).copy()
        reveal_surf = pygame.Surface((bb_w, bb_h), pygame.SRCALPHA)

        route_data = {
            "from_poi": from_poi,
            "to_poi": to_poi,
            "bbox": bbox,
            "pts": pts,
            "cum_dists": cum_dists,
            "total_dist": total_dist,
            "full_surf": full_surf,
            "full_alpha": full_alpha,
            "norm_s": norm_s,
            "reveal_surf": reveal_surf,
            "last_progress": -1.0,
        }
        self._route_cache[key] = route_data
        return route_data

    def sample_point_at_progress(self, route_data: Dict[str, Any], progress: float) -> Tuple[float, float]:
        """Retorna la posición (world_x, world_y) sobre la curva Bézier para progress in [0, 1]."""
        pts = route_data["pts"]
        cum = route_data["cum_dists"]
        total = route_data["total_dist"]
        if not pts:
            return (0.0, 0.0)
        if progress <= 0.0:
            return pts[0]
        if progress >= 1.0:
            return pts[-1]

        target_d = progress * total
        lo, hi = 0, len(cum) - 2
        while lo < hi:
            mid = (lo + hi) // 2
            if cum[mid + 1] < target_d:
                lo = mid + 1
            else:
                hi = mid
        seg_len = max(1e-4, cum[lo + 1] - cum[lo])
        t = max(0.0, min(1.0, (target_d - cum[lo]) / seg_len))
        p0, p1 = pts[lo], pts[lo + 1]
        return (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)

    def get_revealed_surface(self, route_data: Dict[str, Any], progress: float) -> pygame.Surface:
        """
        Actualiza y retorna la superficie revelada hasta `progress` (0..1)
        tocando únicamente la región sucia alrededor del frente de onda para mantener 60 FPS.
        """
        progress = max(0.0, min(1.0, float(progress)))
        if progress >= 0.999:
            return route_data["full_surf"]

        last_p = route_data["last_progress"]
        reveal_surf: pygame.Surface = route_data["reveal_surf"]
        full_surf: pygame.Surface = route_data["full_surf"]
        full_alpha: np.ndarray = route_data["full_alpha"]
        norm_s: np.ndarray = route_data["norm_s"]
        bbox: pygame.Rect = route_data["bbox"]
        pts: List[Tuple[float, float]] = route_data["pts"]
        cum: List[float] = route_data["cum_dists"]
        total: float = max(1.0, route_data["total_dist"])

        feather = 0.035
        if last_p < 0.0 or progress < last_p:
            reveal_surf.blit(full_surf, (0, 0))
            dirty_min_p = 0.0
            dirty_max_p = 1.0
            rx0, ry0, rx1, ry1 = 0, 0, bbox.width, bbox.height
        else:
            dirty_min_p = max(0.0, last_p - feather - 0.02)
            dirty_max_p = min(1.0, progress + 0.02)
            pad = int(math.ceil(self.half_w)) + 8
            sel = [
                pts[i]
                for i in range(len(pts))
                if (dirty_min_p - 0.03) <= (cum[i] / total) <= (dirty_max_p + 0.03)
            ]
            if not sel:
                route_data["last_progress"] = progress
                return reveal_surf
            rx0 = max(0, int(math.floor(min(p[0] for p in sel))) - bbox.x - pad)
            ry0 = max(0, int(math.floor(min(p[1] for p in sel))) - bbox.y - pad)
            rx1 = min(bbox.width, int(math.ceil(max(p[0] for p in sel))) - bbox.x + pad)
            ry1 = min(bbox.height, int(math.ceil(max(p[1] for p in sel))) - bbox.y + pad)

        if rx1 > rx0 and ry1 > ry0:
            sub_s = norm_s[rx0:rx1, ry0:ry1]
            sub_full_a = full_alpha[rx0:rx1, ry0:ry1]
            ramp = np.clip((progress - sub_s) / feather, 0.0, 1.0)
            new_a = (sub_full_a.astype(np.float32) * ramp).astype(np.uint8)
            rev_a = pygame.surfarray.pixels_alpha(reveal_surf)[rx0:rx1, ry0:ry1]
            rev_a[:] = new_a
            del rev_a

        route_data["last_progress"] = progress
        return reveal_surf

    def render_persistent_route(
        self,
        surface: pygame.Surface,
        route_data: Dict[str, Any],
        cam_x: int,
        cam_y: int,
        timer: float = 0.0,
    ) -> None:
        """Dibuja una ruta ya desbloqueada con brillo cálido sutil persistente."""
        bbox: pygame.Rect = route_data["bbox"]
        sx = bbox.x - cam_x
        sy = bbox.y - cam_y
        if sx + bbox.width < 0 or sy + bbox.height < 0 or sx > surface.get_width() or sy > surface.get_height():
            return
        full_surf: pygame.Surface = route_data["full_surf"]
        pulse = int(122 + 22 * math.sin(timer * 2.1))
        full_surf.set_alpha(pulse)
        surface.blit(full_surf, (sx, sy))
        full_surf.set_alpha(255)

    def render_animated_route(
        self,
        surface: pygame.Surface,
        route_data: Dict[str, Any],
        progress: float,
        cam_x: int,
        cam_y: int,
        timer: float = 0.0,
    ) -> None:
        """Dibuja la revelación progresiva del camino iluminado y el destello IA en la punta."""
        bbox: pygame.Rect = route_data["bbox"]
        sx = bbox.x - cam_x
        sy = bbox.y - cam_y
        rev_surf = self.get_revealed_surface(route_data, progress)
        if not (sx + bbox.width < 0 or sy + bbox.height < 0 or sx > surface.get_width() or sy > surface.get_height()):
            surface.blit(rev_surf, (sx, sy))

        if 0.01 < progress < 0.995 and self._sparkle_surf is not None:
            wx, wy = self.sample_point_at_progress(route_data, progress)
            sp_x = int(round(wx - cam_x))
            sp_y = int(round(wy - cam_y))
            if -120 < sp_x < surface.get_width() + 120 and -120 < sp_y < surface.get_height() + 120:
                pulse_scale = 0.85 + 0.22 * math.sin(timer * 10.0)
                rot = (timer * 95.0) % 360.0
                sp = pygame.transform.rotozoom(self._sparkle_surf, rot, pulse_scale)
                surface.blit(sp, sp.get_rect(center=(sp_x, sp_y)))
