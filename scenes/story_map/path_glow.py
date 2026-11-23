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


def _fillet_sharp_corners(
    pts: List[Tuple[float, float]],
    fillet_px: float = 18.0,
    min_angle_deg: float = 18.0,
) -> List[Tuple[float, float]]:
    """Suaviza vértices angulosos (p. ej. intersecciones en L/V) con arcos Bézier tangentes."""
    if len(pts) < 3 or fillet_px <= 1.0:
        return pts

    raw_s: List[float] = [0.0]
    for i in range(1, len(pts)):
        raw_s.append(raw_s[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    total_raw = raw_s[-1]
    if total_raw <= 4.0:
        return pts

    candidates: List[Tuple[float, int]] = []
    for j in range(1, len(pts) - 1):
        v1x, v1y = pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1]
        v2x, v2y = pts[j + 1][0] - pts[j][0], pts[j + 1][1] - pts[j][1]
        l1 = math.hypot(v1x, v1y)
        l2 = math.hypot(v2x, v2y)
        if l1 <= 1e-4 or l2 <= 1e-4:
            continue
        cos_a = max(-1.0, min(1.0, (v1x * v2x + v1y * v2y) / (l1 * l2)))
        ang = math.degrees(math.acos(cos_a))
        if ang >= min_angle_deg and raw_s[j] > 2.0 and (total_raw - raw_s[j]) > 2.0:
            candidates.append((ang, j))

    if not candidates:
        return pts

    # Supresión no-máxima sobre longitud de arco para evitar solapar filetes vecinos
    candidates.sort(key=lambda item: item[0], reverse=True)
    chosen: List[int] = []
    min_sep = fillet_px * 2.1
    for _ang, j in candidates:
        sj = raw_s[j]
        if all(abs(sj - raw_s[cj]) > min_sep for cj in chosen):
            chosen.append(j)
    chosen.sort()

    def _sample_at_s(target_s: float) -> Tuple[float, float]:
        if target_s <= 0.0:
            return pts[0]
        if target_s >= total_raw:
            return pts[-1]
        lo, hi = 0, len(raw_s) - 2
        while lo < hi:
            mid = (lo + hi) // 2
            if raw_s[mid + 1] < target_s:
                lo = mid + 1
            else:
                hi = mid
        seg = max(1e-4, raw_s[lo + 1] - raw_s[lo])
        t = max(0.0, min(1.0, (target_s - raw_s[lo]) / seg))
        return (
            pts[lo][0] + (pts[lo + 1][0] - pts[lo][0]) * t,
            pts[lo][1] + (pts[lo + 1][1] - pts[lo][1]) * t,
        )

    def _append_dedup(dst: List[Tuple[float, float]], pt: Tuple[float, float]) -> None:
        if not dst or math.hypot(pt[0] - dst[-1][0], pt[1] - dst[-1][1]) >= 1e-4:
            dst.append(pt)

    out: List[Tuple[float, float]] = [pts[0]]
    cursor_s = 0.0
    orig_idx = 1

    for j in chosen:
        sj = raw_s[j]
        d = min(fillet_px, sj - cursor_s, total_raw - sj)
        if d < 2.0:
            continue
        s_in = sj - d
        s_out = sj + d
        while orig_idx < len(pts) and raw_s[orig_idx] < s_in:
            if raw_s[orig_idx] > cursor_s:
                _append_dedup(out, pts[orig_idx])
            orig_idx += 1

        q_in = _sample_at_s(s_in)
        vc = pts[j]
        q_out = _sample_at_s(s_out)
        n_sub = max(6, int(math.ceil((2.0 * d) / 4.0)))
        for k in range(n_sub + 1):
            t = k / float(n_sub)
            omt = 1.0 - t
            fx = omt * omt * q_in[0] + 2.0 * omt * t * vc[0] + t * t * q_out[0]
            fy = omt * omt * q_in[1] + 2.0 * omt * t * vc[1] + t * t * q_out[1]
            _append_dedup(out, (fx, fy))

        cursor_s = s_out
        while orig_idx < len(pts) and raw_s[orig_idx] <= cursor_s:
            orig_idx += 1

    while orig_idx < len(pts):
        _append_dedup(out, pts[orig_idx])
        orig_idx += 1

    _append_dedup(out, pts[-1])
    return out


def build_route_polyline(
    node_map: Dict[int, Dict[str, Any]],
    edge_map: Dict[Tuple[int, int], Dict[str, Any]],
    node_path: List[int],
    step_px: int = 6,
    fillet_px: float = 18.0,
) -> Tuple[List[Tuple[float, float]], List[float], float]:
    """Muestrea puntos densos en flotante sobre curvas Bézier, suaviza quiebres y calcula distancias."""
    if not node_path:
        return [], [], 0.0

    raw_pts: List[Tuple[float, float]] = []
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

        chord = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        ctrl_dist = math.hypot(pc[0] - p0[0], pc[1] - p0[1]) + math.hypot(p1[0] - pc[0], p1[1] - pc[1])
        num_steps = max(6, int(max(10.0, (chord + ctrl_dist) * 0.5) // max(4, step_px)))
        seg_pts: List[Tuple[float, float]] = []
        for s_i in range(num_steps + 1):
            t = s_i / float(num_steps)
            omt = 1.0 - t
            bx = omt * omt * p0[0] + 2.0 * omt * t * pc[0] + t * t * p1[0]
            by = omt * omt * p0[1] + 2.0 * omt * t * pc[1] + t * t * p1[1]
            seg_pts.append((bx, by))

        for pt in seg_pts:
            if not raw_pts or math.hypot(pt[0] - raw_pts[-1][0], pt[1] - raw_pts[-1][1]) >= 1e-3:
                raw_pts.append(pt)

    if not raw_pts:
        n0 = node_map.get(node_path[0])
        if n0 is not None:
            return [(float(n0["x"]), float(n0["y"]))], [0.0], 0.0
        return [], [], 0.0

    pts_filleted = _fillet_sharp_corners(raw_pts, fillet_px=fillet_px, min_angle_deg=18.0)
    pts: List[Tuple[float, float]] = []
    for pt in pts_filleted:
        if not pts or math.hypot(pt[0] - pts[-1][0], pt[1] - pts[-1][1]) >= 1e-4:
            pts.append(pt)

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

    def __init__(self, world_w: int, world_h: int, brush_h: int = 32) -> None:
        self.world_w = world_w
        self.world_h = world_h
        self.brush_h = max(16, int(brush_h))
        self.half_w = self.brush_h * 0.5
        self.assets = AssetManager.get_instance()

        self._brush_rgba: Optional[np.ndarray] = None
        self._tile_w: int = 1
        self._sparkle_surf: Optional[pygame.Surface] = None
        self._flow_sparkle_surf: Optional[pygame.Surface] = None
        self._flow_orb_buckets: List[pygame.Surface] = []
        self._flow_orb_surf: Optional[pygame.Surface] = None
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
            self._flow_sparkle_surf = pygame.transform.smoothscale(raw_sp, (26, 26))
        except Exception as exc:
            print(f"[PathGlow] Aviso cargando mapa_destello_ruta.png: {exc}")
            self._sparkle_surf = None
            self._flow_sparkle_surf = None

        # Pre-hornear 10 cubetas cuantizadas (0.1..1.0) para el orbe aditivo (SDL2 BLEND_RGB_ADD ignora set_alpha)
        orb_size = 44
        hc = orb_size * 0.5
        yy, xx = np.mgrid[0:orb_size, 0:orb_size].astype(np.float32)
        dist = np.sqrt((xx + 0.5 - hc) ** 2 + (yy + 0.5 - hc) ** 2) / hc
        falloff = np.clip(1.0 - dist, 0.0, 1.0) ** 2.0
        base_col = np.array([255.0, 215.0, 110.0], dtype=np.float32)
        self._flow_orb_buckets = []
        for q in range(1, 11):
            level = q / 10.0
            orb = pygame.Surface((orb_size, orb_size))
            orb.fill((0, 0, 0))
            orb_rgb = np.clip(falloff[:, :, None] * (0.34 * level) * base_col[None, None, :], 0.0, 255.0).astype(np.uint8)
            arr = pygame.surfarray.pixels3d(orb)
            arr[:] = orb_rgb.transpose(1, 0, 2)
            del arr
            self._flow_orb_buckets.append(orb)
        self._flow_orb_surf = self._flow_orb_buckets[-1]

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

        pts, cum_dists, total_dist = build_route_polyline(node_map, edge_map, node_path, step_px=6, fillet_px=18.0)
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

        # Segmentos de proyección a resolución completa (~4-6 px) para curvas/filetes continuos sin quiebres
        best_d2 = np.full((bb_w, bb_h), 1e9, dtype=np.float32)
        best_s = np.zeros((bb_w, bb_h), dtype=np.float32)
        r_lim = self.half_w
        r2_lim = r_lim * r_lim

        for k in range(len(pts) - 1):
            i0, i1 = k, k + 1
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

            # Desvanecimiento compacto dentro del radio del nodo de parada (9 px) para uniones continuas
            end_fade = np.minimum(
                np.clip((best_s + 2.0) / 8.0, 0.0, 1.0),
                np.clip((total_dist - best_s + 2.0) / 8.0, 0.0, 1.0),
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
        alpha_scale: float = 1.0,
    ) -> None:
        """Dibuja una ruta ya desbloqueada con brillo cálido sutil persistente."""
        alpha_scale = max(0.0, min(1.0, float(alpha_scale)))
        if alpha_scale <= 0.01:
            return
        bbox: pygame.Rect = route_data["bbox"]
        sx = bbox.x - cam_x
        sy = bbox.y - cam_y
        if sx + bbox.width < 0 or sy + bbox.height < 0 or sx > surface.get_width() or sy > surface.get_height():
            return
        full_surf: pygame.Surface = route_data["full_surf"]
        pulse = int(round((122 + 22 * math.sin(timer * 2.1)) * alpha_scale))
        if pulse <= 2:
            return
        full_surf.set_alpha(pulse)
        surface.blit(full_surf, (sx, sy))
        full_surf.set_alpha(255)

    def _get_night_glow_surfaces(
        self,
        route_data: Dict[str, Any],
        tier: str = "active",
    ) -> Tuple[pygame.Surface, Optional[np.ndarray], Dict[int, pygame.Surface]]:
        """Construye y cachea superficies nocturnas por jerarquía ('active'|'completed'|'locked') respetando POI_SPECS."""
        tiers_cache: Dict[str, Any] = route_data.setdefault("_night_glow_tiers", {})
        cached = tiers_cache.get(tier)
        if cached is not None:
            return cached

        full_surf: pygame.Surface = route_data["full_surf"]
        full_alpha: np.ndarray = route_data["full_alpha"]
        w, h = full_surf.get_size()

        night_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        rgb = pygame.surfarray.array3d(full_surf).astype(np.float32)
        a_norm = (full_alpha.astype(np.float32) / 255.0)[:, :, None]

        if tier == "active":
            warm_tint = np.array([255.0, 224.0, 128.0], dtype=np.float32)[None, None, :]
            glow_rgb = np.clip(0.82 * rgb + 0.18 * warm_tint, 0.0, 255.0)
            add_scale = 0.28
        elif tier == "completed":
            ember_tint = np.array([255.0, 198.0, 105.0], dtype=np.float32)[None, None, :]
            glow_rgb = np.clip(0.76 * rgb + 0.24 * ember_tint, 0.0, 255.0)
            add_scale = 0.16
        else:
            moon_tint = np.array([185.0, 218.0, 238.0], dtype=np.float32)[None, None, :]
            glow_rgb = np.clip(0.55 * rgb + 0.45 * moon_tint, 0.0, 255.0)
            add_scale = 0.08

        # En píxeles transparentes (edificios/bordes) RGB debe ser estrictamente 0
        glow_rgb = np.where(full_alpha[:, :, None] > 0, glow_rgb, 0.0)

        n_rgb = pygame.surfarray.pixels3d(night_surf)
        n_a = pygame.surfarray.pixels_alpha(night_surf)
        n_rgb[:] = glow_rgb.astype(np.uint8)
        n_a[:] = full_alpha
        del n_rgb, n_a

        add_base_f32: Optional[np.ndarray] = None
        add_buckets: Dict[int, pygame.Surface] = {}
        if add_scale > 0.0:
            add_base_f32 = np.clip(glow_rgb * a_norm * add_scale, 0.0, 255.0)
            add_full = pygame.Surface((w, h))
            a_rgb = pygame.surfarray.pixels3d(add_full)
            a_rgb[:] = add_base_f32.astype(np.uint8)
            del a_rgb
            add_buckets[10] = add_full

        entry = (night_surf, add_base_f32, add_buckets)
        tiers_cache[tier] = entry
        return entry

    def _get_quantized_add_surf(
        self,
        add_base_f32: Optional[np.ndarray],
        add_buckets: Dict[int, pygame.Surface],
        intensity: float,
    ) -> Optional[pygame.Surface]:
        """Retorna una cubeta cuantizada (1..10) para BLEND_RGB_ADD ya que SDL2 ignora set_alpha()."""
        if add_base_f32 is None:
            return None
        q = max(0, min(10, int(round(intensity * 10.0))))
        if q <= 0:
            return None
        cached = add_buckets.get(q)
        if cached is not None:
            return cached
        w, h, _ = add_base_f32.shape
        surf = pygame.Surface((w, h))
        arr = pygame.surfarray.pixels3d(surf)
        arr[:] = np.clip(add_base_f32 * (q / 10.0), 0.0, 255.0).astype(np.uint8)
        del arr
        add_buckets[q] = surf
        return surf

    def render_night_glow_route(
        self,
        surface: pygame.Surface,
        route_data: Dict[str, Any],
        cam_x: int,
        cam_y: int,
        timer: float = 0.0,
        unlocked: bool = False,
        tier: Optional[str] = None,
        intensity: float = 1.0,
    ) -> None:
        """Dibuja el brillo nocturno del camino por encima del overlay de noche, respetando POI_SPECS."""
        intensity = max(0.0, min(1.0, float(intensity)))
        if intensity <= 0.01:
            return

        bbox: pygame.Rect = route_data["bbox"]
        sx = bbox.x - cam_x
        sy = bbox.y - cam_y
        if sx + bbox.width < 0 or sy + bbox.height < 0 or sx > surface.get_width() or sy > surface.get_height():
            return

        resolved_tier = tier if tier in ("active", "completed", "locked") else ("active" if unlocked else "locked")
        night_surf, add_base_f32, add_buckets = self._get_night_glow_surfaces(route_data, tier=resolved_tier)

        if resolved_tier == "active":
            pulse = 0.88 + 0.12 * math.sin(timer * 2.4)
            alpha = int(round(136 * pulse * intensity))
            if alpha > 2:
                night_surf.set_alpha(alpha)
                surface.blit(night_surf, (sx, sy))
                night_surf.set_alpha(255)
            add_surf = self._get_quantized_add_surf(add_base_f32, add_buckets, intensity)
            if add_surf is not None:
                surface.blit(add_surf, (sx, sy), special_flags=pygame.BLEND_RGB_ADD)

            # Flujo direccional con dt hacia el siguiente nivel (norm_s 0 -> 1)
            full_alpha: np.ndarray = route_data["full_alpha"]
            total_dist = max(1.0, float(route_data["total_dist"]))
            spacing_px = 175.0
            speed_px = 210.0
            n_beads = max(2, int(round(total_dist / spacing_px)))
            phase = (timer * speed_px / total_dist) % 1.0
            sw_screen, sh_screen = surface.get_size()

            for b in range(n_beads):
                p = (b / float(n_beads) + phase) % 1.0
                edge_w = min(1.0, p / 0.06, (1.0 - p) / 0.06)
                if edge_w <= 0.05:
                    continue
                wx, wy = self.sample_point_at_progress(route_data, p)
                lx = int(round(wx)) - bbox.x
                ly = int(round(wy)) - bbox.y
                if lx < 0 or ly < 0 or lx >= bbox.width or ly >= bbox.height:
                    continue
                if int(full_alpha[lx, ly]) < 12:
                    continue
                bx = int(round(wx - cam_x))
                by = int(round(wy - cam_y))
                if not (-60 <= bx <= sw_screen + 60 and -60 <= by <= sh_screen + 60):
                    continue

                bead_strength = edge_w * intensity
                if self._flow_orb_buckets:
                    orb_idx = min(9, int(round(bead_strength * 10.0)) - 1)
                    if orb_idx >= 0:
                        orb = self._flow_orb_buckets[orb_idx]
                        surface.blit(orb, orb.get_rect(center=(bx, by)), special_flags=pygame.BLEND_RGB_ADD)

                if self._flow_sparkle_surf is not None:
                    twinkle = 0.78 + 0.22 * math.sin(timer * 5.0 + b * 1.3)
                    sp_alpha = int(round(255 * bead_strength * twinkle))
                    if sp_alpha > 4:
                        self._flow_sparkle_surf.set_alpha(sp_alpha)
                        surface.blit(self._flow_sparkle_surf, self._flow_sparkle_surf.get_rect(center=(bx, by)))
                        self._flow_sparkle_surf.set_alpha(255)
        elif resolved_tier == "completed":
            pulse = 0.94 + 0.06 * math.sin(timer * 1.4)
            alpha = int(round(120 * pulse * intensity))
            if alpha > 2:
                night_surf.set_alpha(alpha)
                surface.blit(night_surf, (sx, sy))
                night_surf.set_alpha(255)
            add_surf = self._get_quantized_add_surf(add_base_f32, add_buckets, intensity)
            if add_surf is not None:
                surface.blit(add_surf, (sx, sy), special_flags=pygame.BLEND_RGB_ADD)
        else:
            pulse = 0.90 + 0.10 * math.sin(timer * 1.6)
            alpha = int(round(100 * pulse * intensity))
            if alpha > 2:
                night_surf.set_alpha(alpha)
                surface.blit(night_surf, (sx, sy))
                night_surf.set_alpha(255)
            add_surf = self._get_quantized_add_surf(add_base_f32, add_buckets, intensity)
            if add_surf is not None:
                surface.blit(add_surf, (sx, sy), special_flags=pygame.BLEND_RGB_ADD)

    def render_animated_route(
        self,
        surface: pygame.Surface,
        route_data: Dict[str, Any],
        progress: float,
        cam_x: int,
        cam_y: int,
        timer: float = 0.0,
        night_mix: float = 0.0,
    ) -> None:
        """Dibuja la revelación progresiva del camino iluminado y el destello IA en la punta."""
        bbox: pygame.Rect = route_data["bbox"]
        sx = bbox.x - cam_x
        sy = bbox.y - cam_y
        rev_surf = self.get_revealed_surface(route_data, progress)
        if not (sx + bbox.width < 0 or sy + bbox.height < 0 or sx > surface.get_width() or sy > surface.get_height()):
            surface.blit(rev_surf, (sx, sy))
            if night_mix > 0.5 and progress >= 0.999:
                _ns, add_base_f32, add_buckets = self._get_night_glow_surfaces(route_data, tier="active")
                add_surf = self._get_quantized_add_surf(add_base_f32, add_buckets, night_mix)
                if add_surf is not None:
                    surface.blit(add_surf, (sx, sy), special_flags=pygame.BLEND_RGB_ADD)

        if 0.01 < progress < 0.995 and self._sparkle_surf is not None:
            wx, wy = self.sample_point_at_progress(route_data, progress)
            sp_x = int(round(wx - cam_x))
            sp_y = int(round(wy - cam_y))
            if -120 < sp_x < surface.get_width() + 120 and -120 < sp_y < surface.get_height() + 120:
                if night_mix > 0.1 and self._flow_orb_buckets:
                    orb_idx = min(9, max(0, int(round(night_mix * 10.0)) - 1))
                    orb = self._flow_orb_buckets[orb_idx]
                    surface.blit(orb, orb.get_rect(center=(sp_x, sp_y)), special_flags=pygame.BLEND_RGB_ADD)
                pulse_scale = 0.85 + 0.22 * math.sin(timer * 10.0)
                rot = (timer * 95.0) % 360.0
                sp = pygame.transform.rotozoom(self._sparkle_surf, rot, pulse_scale)
                surface.blit(sp, sp.get_rect(center=(sp_x, sp_y)))
