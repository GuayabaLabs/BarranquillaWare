"""
Herramienta offline de reparacion visual definitiva de las costuras del Mapa Mundial
(BarranquillaWare - StoryMapScene).

Pipeline v5 (2D geometric alignment + polar roundabouts + material-safe exemplar):
1. Armonizacion cromatica material-aware (incluye paso residual para Q3/Q4) + suavizado
   oceanico ancho y puente de espuma en X=1671.
2. Alineacion geometrica 2D (d_along + d_across) para alinear simultaneamente lineas '/'
   y '\\' de cuadriculas y vias diagonales tanto en zonas con traslape (ov > 0) como en
   zonas con brecha real faltante (hg > 0).
3. Puente direccional guiado por tensor de estructura (pendientes hasta +-4.0) en
   cuadriculas/vias con brecha real.
4. Reconstruccion polar eliptica exacta con centros medidos para Aleta del Tiburon
   (Y=941) y Glorieta Sur (X=1671), mas reparacion limpia de la union T superior.
5. Inpainting 2D por ejemplares (stride=1, 9x9) protegido contra sangrado de blanco/acera
   en copas de arboles, palmas costeras, parque central y arbustos, mas reparacion
   quirurgica de los 5 faroles sobre Y=941.
"""

from __future__ import annotations

import argparse
import os
from typing import List, Tuple

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image

QUAD_W = 1671
QUAD_H = 941
WORLD_W = QUAD_W * 2
WORLD_H = QUAD_H * 2


def _box_smooth_1d(arr: np.ndarray, radius: int, axis: int = 0) -> np.ndarray:
    if radius <= 0 or arr.shape[axis] <= 1:
        return arr
    pad_width = [(0, 0)] * arr.ndim
    pad_width[axis] = (radius, radius)
    padded = np.pad(arr, pad_width, mode="edge")
    csum = np.cumsum(padded, axis=axis, dtype=np.float64)
    zero_pad = [(0, 0)] * arr.ndim
    zero_pad[axis] = (1, 0)
    csum = np.pad(csum, zero_pad, mode="constant")
    n = arr.shape[axis]
    win = float(2 * radius + 1)
    sl_hi = [slice(None)] * arr.ndim
    sl_lo = [slice(None)] * arr.ndim
    sl_hi[axis] = slice(2 * radius + 1, 2 * radius + 1 + n)
    sl_lo[axis] = slice(0, n)
    return ((csum[tuple(sl_hi)] - csum[tuple(sl_lo)]) / win).astype(np.float32)


def _smooth_1d(arr: np.ndarray, radius: int, passes: int = 2) -> np.ndarray:
    out = arr.astype(np.float32).copy()
    for _ in range(passes):
        out = _box_smooth_1d(out, radius, axis=0)
    return out


def _material_weights(img: np.ndarray) -> np.ndarray:
    r = img[:, :, 0]
    g = img[:, :, 1]
    b = img[:, :, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = mx - mn

    non_ink = np.clip((lum - 68.0) / 28.0, 0.0, 1.0)
    non_white = np.clip((236.0 - mn) / 12.0, 0.0, 1.0)
    base = non_ink * non_white

    # Incluye durazno (bloques) y arena (playa) en la misma clase calida clara
    w_warm = (
        base
        * np.clip((r - b - 10.0) / 16.0, 0.0, 1.0)
        * np.clip((r - g - 3.0) / 14.0, 0.0, 1.0)
        * np.clip((g - b - 3.0) / 12.0, 0.0, 1.0)
        * np.clip((lum - 175.0) / 22.0, 0.0, 1.0)
    )
    w_grass = base * np.clip((g - r - 4.0) / 16.0, 0.0, 1.0) * np.clip((g - b - 24.0) / 22.0, 0.0, 1.0)
    w_asph = base * np.clip((26.0 - sat) / 14.0, 0.0, 1.0) * np.clip((152.0 - lum) / 25.0, 0.0, 1.0)
    w_ocean = base * np.clip((b - r - 18.0) / 22.0, 0.0, 1.0) * np.clip((b - g + 12.0) / 24.0, 0.0, 1.0)
    w_pink = base * np.clip((r - g - 25.0) / 25.0, 0.0, 1.0) * np.clip((b - g - 15.0) / 20.0, 0.0, 1.0)

    weights = np.stack([w_warm, w_grass, w_asph, w_ocean, w_pink], axis=-1)
    wsum = np.maximum(1.0, weights.sum(axis=-1, keepdims=True))
    return (weights / wsum).astype(np.float32)


def harmonize_colors_along_seam(
    arr: np.ndarray,
    seam_pos: int,
    axis: int = 0,
    radius: int = 240,
    strip_d: int = 38,
    sm_r: int = 20,
) -> np.ndarray:
    work = arr if axis == 0 else np.transpose(arr, (1, 0, 2)).copy()
    h, w, _ = work.shape
    weights = _material_weights(work)

    a_slice = work[seam_pos - strip_d : seam_pos - 2]
    b_slice = work[seam_pos + 2 : seam_pos + strip_d]
    wa_slice = weights[seam_pos - strip_d : seam_pos - 2]
    wb_slice = weights[seam_pos + 2 : seam_pos + strip_d]

    n_mat = weights.shape[-1]
    diff_prof = np.zeros((w, n_mat, 3), dtype=np.float32)

    for m in range(n_mat):
        wa_col = wa_slice[:, :, m].sum(axis=0)
        wb_col = wb_slice[:, :, m].sum(axis=0)
        sa_col = (a_slice * wa_slice[:, :, m : m + 1]).sum(axis=0)
        sb_col = (b_slice * wb_slice[:, :, m : m + 1]).sum(axis=0)

        wa_s = _smooth_1d(wa_col, sm_r, passes=2)
        wb_s = _smooth_1d(wb_col, sm_r, passes=2)
        sa_s = _smooth_1d(sa_col, sm_r, passes=2)
        sb_s = _smooth_1d(sb_col, sm_r, passes=2)

        g_wa = float(wa_col.sum())
        g_wb = float(wb_col.sum())
        if g_wa < 20.0 or g_wb < 20.0:
            continue
        g_mean_a = sa_col.sum(axis=0) / g_wa
        g_mean_b = sb_col.sum(axis=0) / g_wb
        g_diff = g_mean_b - g_mean_a

        valid = (wa_s > 2.5) & (wb_s > 2.5)
        mean_a = np.where(valid[:, None], sa_s / np.maximum(wa_s[:, None], 1e-4), g_mean_a[None, :])
        mean_b = np.where(valid[:, None], sb_s / np.maximum(wb_s[:, None], 1e-4), g_mean_b[None, :])
        local_diff = np.where(valid[:, None], mean_b - mean_a, g_diff[None, :])
        conf = np.clip(np.minimum(wa_s, wb_s) / 12.0, 0.0, 1.0)[:, None]
        blended_diff = conf * local_diff + (1.0 - conf) * g_diff[None, :]
        blended_diff = np.clip(blended_diff, -58.0, 58.0)
        diff_prof[:, m, :] = _smooth_1d(blended_diff, max(8, sm_r // 2), passes=2)

    y0 = max(0, seam_pos - radius)
    y1 = min(h, seam_pos + radius)
    ys_a = np.arange(y0, seam_pos, dtype=np.float32)
    t_a = 0.5 * (1.0 + np.cos(np.pi * (seam_pos - ys_a) / float(radius)))
    ys_b = np.arange(seam_pos, y1, dtype=np.float32)
    t_b = 0.5 * (1.0 + np.cos(np.pi * (ys_b - seam_pos) / float(radius)))

    corr_a = np.einsum("ywm,wmc->ywc", weights[y0:seam_pos], diff_prof) * (0.5 * t_a[:, None, None])
    corr_b = np.einsum("ywm,wmc->ywc", weights[seam_pos:y1], diff_prof) * (0.5 * t_b[:, None, None])

    work[y0:seam_pos] = np.clip(work[y0:seam_pos] + corr_a, 0.0, 255.0)
    work[seam_pos:y1] = np.clip(work[seam_pos:y1] - corr_b, 0.0, 255.0)

    return work if axis == 0 else np.transpose(work, (1, 0, 2)).copy()


def blend_ocean_seam(arr: np.ndarray, x_seam: int = QUAD_W, y_max: int = 258, half_w: int = 72) -> np.ndarray:
    """Igualacion suave de color/luminancia oceanica + puente organico de olas en X=1671."""
    out = arr.copy()
    band = out[:y_max, x_seam - half_w : x_seam + half_w].copy()
    left_edge = out[:y_max, x_seam - half_w : x_seam]
    right_edge = out[:y_max, x_seam : x_seam + half_w]

    lum_l = _smooth_1d(left_edge[:, -24:].mean(axis=1), 18, passes=2)
    lum_r = _smooth_1d(right_edge[:, :24].mean(axis=1), 18, passes=2)
    diff = np.clip(lum_r - lum_l, -28.0, 28.0)

    u_l = np.linspace(0.0, 1.0, half_w, dtype=np.float32)
    u_r = np.linspace(0.0, 1.0, half_w, dtype=np.float32)
    corr_l = diff[:, None, :] * (0.5 * (1.0 - np.cos(np.pi * u_l))[None, :, None]) * 0.5
    corr_r = -diff[:, None, :] * (0.5 * (1.0 + np.cos(np.pi * u_r))[None, :, None]) * 0.5
    band[:, :half_w] = np.clip(left_edge + corr_l, 0.0, 255.0)
    band[:, half_w:] = np.clip(right_edge + corr_r, 0.0, 255.0)

    vy = np.clip((float(y_max) - np.arange(y_max, dtype=np.float32)) / 24.0, 0.0, 1.0)[:, None, None]
    out[:y_max, x_seam - half_w : x_seam + half_w] = (
        out[:y_max, x_seam - half_w : x_seam + half_w] * (1.0 - vy) + band * vy
    )

    # Puente exemplar estrecho (6px) estrictamente en el mar [0..234] sin invadir la arena
    hole_sea = np.zeros(out.shape[:2], dtype=bool)
    hole_sea[0:234, x_seam - 3 : x_seam + 3] = True
    out = exemplar_inpaint_mask(
        out,
        hole_sea,
        patch_r=5,
        search_r=28,
        core_r=0,
        stride=1,
    )
    return out


def _bilinear_sample_2d(src: np.ndarray, sy: np.ndarray, sx: np.ndarray) -> np.ndarray:
    h, w, _ = src.shape
    sy_c = np.clip(sy, 0.0, float(h - 1))
    sx_c = np.clip(sx, 0.0, float(w - 1))
    y0 = np.floor(sy_c).astype(np.int32)
    x0 = np.floor(sx_c).astype(np.int32)
    y1 = np.minimum(y0 + 1, h - 1)
    x1 = np.minimum(x0 + 1, w - 1)
    fy = (sy_c - y0)[:, :, None]
    fx = (sx_c - x0)[:, :, None]
    return (
        src[y0, x0] * (1.0 - fx) * (1.0 - fy)
        + src[y0, x1] * fx * (1.0 - fy)
        + src[y1, x0] * (1.0 - fx) * fy
        + src[y1, x1] * fx * fy
    )


def _interp_anchors_2d(
    length: int,
    anchors: List[Tuple[int, float, float, float, float, float]],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    anchors: list of (pos, d_along_a, d_along_b, ov_a_or_neg, ov_b_or_neg, fill_hg)
    """
    xs = np.arange(length, dtype=np.float32)
    ax = np.array([a[0] for a in anchors], dtype=np.float32)
    sa = np.interp(xs, ax, np.array([a[1] for a in anchors], dtype=np.float32))
    sb = np.interp(xs, ax, np.array([a[2] for a in anchors], dtype=np.float32))
    ova = np.interp(xs, ax, np.array([a[3] for a in anchors], dtype=np.float32))
    ovb = np.interp(xs, ax, np.array([a[4] for a in anchors], dtype=np.float32))
    hg = np.interp(xs, ax, np.array([a[5] for a in anchors], dtype=np.float32))
    sa = _smooth_1d(sa, 16, passes=2)
    sb = _smooth_1d(sb, 16, passes=2)
    ova = _smooth_1d(ova, 16, passes=2)
    ovb = _smooth_1d(ovb, 16, passes=2)
    hg = _smooth_1d(hg, 12, passes=2)
    return sa, sb, ova, ovb, hg


def exemplar_inpaint_mask(
    img: np.ndarray,
    hole_mask: np.ndarray,
    exclude_source_mask: np.ndarray | None = None,
    patch_r: int = 4,
    search_r: int = 32,
    core_r: int = 0,
    stride: int = 1,
) -> np.ndarray:
    out = img.copy()
    h, w, _ = out.shape
    known = (~hole_mask).copy()
    orig_known = known.copy()
    if exclude_source_mask is not None:
        orig_known &= ~exclude_source_mask

    if not hole_mask.any():
        return out

    ys_all, xs_all = np.where(hole_mask)
    y_min, y_max = int(ys_all.min()), int(ys_all.max())
    x_min, x_max = int(xs_all.min()), int(xs_all.max())

    chunk_w = 112 if (x_max - x_min) > 140 else (x_max - x_min + 1)
    chunk_h = 112 if (y_max - y_min) > 140 else (y_max - y_min + 1)
    ksize = 2 * patch_r + 1

    for cy0 in range(y_min, y_max + 1, chunk_h):
        cy1 = min(y_max + 1, cy0 + chunk_h)
        for cx0 in range(x_min, x_max + 1, chunk_w):
            cx1 = min(x_max + 1, cx0 + chunk_w)
            if not hole_mask[cy0:cy1, cx0:cx1].any():
                continue

            wy0 = max(0, cy0 - search_r - patch_r)
            wy1 = min(h, cy1 + search_r + patch_r)
            wx0 = max(0, cx0 - search_r - patch_r)
            wx1 = min(w, cx1 + search_r + patch_r)

            sub_img = out[wy0:wy1, wx0:wx1].copy()
            sub_known = known[wy0:wy1, wx0:wx1].copy()
            sub_orig = orig_known[wy0:wy1, wx0:wx1].copy()
            sh, sw, _ = sub_img.shape

            if sh < ksize or sw < ksize:
                continue

            valid_centers = sliding_window_view(sub_orig, (ksize, ksize)).all(axis=(2, 3))
            vy_idx, vx_idx = np.where(valid_centers)
            if len(vy_idx) == 0:
                # Fallback sin exclude_source_mask si fue muy restrictivo
                sub_orig_fb = (~hole_mask[wy0:wy1, wx0:wx1])
                valid_centers = sliding_window_view(sub_orig_fb, (ksize, ksize)).all(axis=(2, 3))
                vy_idx, vx_idx = np.where(valid_centers)
                if len(vy_idx) == 0:
                    continue
            vy_idx = vy_idx + patch_r
            vx_idx = vx_idx + patch_r
            if stride > 1:
                step_mask = (vy_idx % stride == 0) & (vx_idx % stride == 0)
                if step_mask.sum() >= 80:
                    vy_idx = vy_idx[step_mask]
                    vx_idx = vx_idx[step_mask]

            all_patches = sliding_window_view(sub_img, (ksize, ksize, 3))[:, :, 0]
            cand_patches = all_patches[vy_idx - patch_r, vx_idx - patch_r].reshape(len(vy_idx), -1)

            target_region = np.zeros((sh, sw), dtype=bool)
            target_region[cy0 - wy0 : cy1 - wy0, cx0 - wx0 : cx1 - wx0] = True

            lum = sub_img.mean(axis=2)
            gx = np.abs(np.diff(lum, axis=1, prepend=lum[:, :1]))
            gy = np.abs(np.diff(lum, axis=0, prepend=lum[:1, :]))
            grad = gx + gy

            pad_img = np.pad(sub_img, ((patch_r, patch_r), (patch_r, patch_r), (0, 0)), mode="edge")
            pad_known = np.pad(sub_known, ((patch_r, patch_r), (patch_r, patch_r)), mode="constant", constant_values=False)

            max_iters = int((target_region & (~sub_known)).sum()) + 8
            for _ in range(max_iters):
                todo = target_region & (~sub_known)
                if not todo.any():
                    break
                pad_nbr = np.pad(sub_known, 1, mode="constant", constant_values=False)
                has_nbr = pad_nbr[:-2, 1:-1] | pad_nbr[2:, 1:-1] | pad_nbr[1:-1, :-2] | pad_nbr[1:-1, 2:]
                frontier = todo & has_nbr
                fy, fx = np.where(frontier)
                if len(fy) == 0:
                    fy, fx = np.where(todo)
                    if len(fy) == 0:
                        break

                win_k = sliding_window_view(pad_known, (ksize, ksize))
                confs = win_k[fy, fx].mean(axis=(1, 2))
                pad_g = np.pad(grad * sub_known, 1, mode="constant", constant_values=0.0)
                g_loc = np.maximum.reduce(
                    [
                        pad_g[fy, fx],
                        pad_g[fy, fx + 1],
                        pad_g[fy, fx + 2],
                        pad_g[fy + 1, fx],
                        pad_g[fy + 1, fx + 2],
                        pad_g[fy + 2, fx],
                        pad_g[fy + 2, fx + 1],
                        pad_g[fy + 2, fx + 2],
                    ]
                )
                prios = confs * (1.0 + g_loc * 0.08)
                best_f = int(np.argmax(prios))
                best_y, best_x = int(fy[best_f]), int(fx[best_f])

                t_patch = pad_img[best_y : best_y + ksize, best_x : best_x + ksize]
                t_known = pad_known[best_y : best_y + ksize, best_x : best_x + ksize]
                k_flat = np.repeat(t_known.ravel(), 3)
                if not k_flat.any():
                    sub_known[best_y, best_x] = True
                    pad_known[best_y + patch_r, best_x + patch_r] = True
                    continue
                t_vec = t_patch.reshape(-1)[k_flat]

                dist2 = (vy_idx - best_y) ** 2 + (vx_idx - best_x) ** 2
                local_sel = dist2 <= float((search_r + 2) ** 2)
                if not local_sel.any():
                    local_sel = np.ones(len(vy_idx), dtype=bool)
                c_sub = cand_patches[local_sel][:, k_flat]
                d_sub = dist2[local_sel]

                diff = c_sub - t_vec[None, :]
                ssd = (diff * diff).mean(axis=1) + 0.002 * d_sub
                best_idx = int(np.argmin(ssd))
                best_patch = cand_patches[local_sel][best_idx].reshape(ksize, ksize, 3)

                yy0 = max(0, best_y - core_r)
                yy1 = min(sh, best_y + core_r + 1)
                xx0 = max(0, best_x - core_r)
                xx1 = min(sw, best_x + core_r + 1)
                py_off = patch_r - best_y
                px_off = patch_r - best_x
                patch_sub = best_patch[yy0 + py_off : yy1 + py_off, xx0 + px_off : xx1 + px_off]
                fill_here = target_region[yy0:yy1, xx0:xx1] & (~sub_known[yy0:yy1, xx0:xx1])
                sub_img[yy0:yy1, xx0:xx1][fill_here] = patch_sub[fill_here]
                sub_known[yy0:yy1, xx0:xx1][fill_here] = True
                pad_img[yy0 + patch_r : yy1 + patch_r, xx0 + patch_r : xx1 + patch_r][fill_here] = patch_sub[fill_here]
                pad_known[yy0 + patch_r : yy1 + patch_r, xx0 + patch_r : xx1 + patch_r][fill_here] = True

            out[cy0:cy1, cx0:cx1] = sub_img[cy0 - wy0 : cy1 - wy0, cx0 - wx0 : cx1 - wx0]
            known[cy0:cy1, cx0:cx1] = sub_known[cy0 - wy0 : cy1 - wy0, cx0 - wx0 : cx1 - wx0]

    return out


def _structure_bridge_band(band: np.ndarray, seam_local: int, bridge_mask_x: np.ndarray, hg: np.ndarray) -> np.ndarray:
    r"""
    Puentea suavemente la franja abierta [yt+1 .. yb-1] encontrando para cada columna x
    la pendiente s = dx/dy in [-4.0, +4.0] que mejor empareja el parche vertical de RGB
    arriba [yt-2..yt] con abajo [yb..yb+2] a lo largo de la recta x + s*dy.
    """
    out = band.copy()
    bh, w, _ = out.shape
    g_col = np.where(bridge_mask_x, np.maximum(1, np.ceil(hg).astype(np.int32)), 0)
    xs_b = np.where(bridge_mask_x)[0]
    if len(xs_b) == 0:
        return out

    cand_s = np.linspace(-4.0, 4.0, 81, dtype=np.float32)  # paso 0.1 hasta +-4.0
    reg = (0.35 * (cand_s ** 2))[None, :]

    for gx_i in np.unique(g_col[xs_b]):
        if gx_i <= 0:
            continue
        cols = xs_b[g_col[xs_b] == gx_i]
        yt = max(2, seam_local - 1 - int(gx_i))
        yb = min(bh - 3, seam_local + int(gx_i))
        span = float(yb - yt)
        if span <= 1.0:
            continue

        ymid = 0.5 * (yt + yb)
        k_t = np.array([yt - 2, yt - 1, yt], dtype=np.int32)
        k_b = np.array([yb, yb + 1, yb + 2], dtype=np.int32)

        cost = np.repeat(reg, len(cols), axis=0).astype(np.float32)
        cols_f = cols.astype(np.float32)[:, None]
        for kt, kb in zip(k_t, k_b):
            dyt = float(ymid - kt)
            dyb = float(kb - ymid)
            for ox in (-1.0, 0.0, 1.0):
                xt = np.clip(cols_f + ox - cand_s[None, :] * dyt, 0.0, float(w - 1))
                xb = np.clip(cols_f + ox + cand_s[None, :] * dyb, 0.0, float(w - 1))
                xt0 = np.floor(xt).astype(np.int32)
                xt1 = np.minimum(w - 1, xt0 + 1)
                fxt = (xt - xt0)[:, :, None]
                ct = out[kt, xt0] * (1.0 - fxt) + out[kt, xt1] * fxt

                xb0 = np.floor(xb).astype(np.int32)
                xb1 = np.minimum(w - 1, xb0 + 1)
                fxb = (xb - xb0)[:, :, None]
                cb = out[kb, xb0] * (1.0 - fxb) + out[kb, xb1] * fxb

                diff = ct - cb
                cost += (diff * diff).mean(axis=2)

        best_idx = np.argmin(cost, axis=1)
        slopes_g = cand_s[best_idx]
        s_full = np.zeros(w, dtype=np.float32)
        s_full[cols] = slopes_g
        s_sm = _smooth_1d(s_full, 1, passes=1)
        slopes_g = np.where(
            (cols > 0) & (cols < w - 1) & bridge_mask_x[np.maximum(0, cols - 1)] & bridge_mask_x[np.minimum(w - 1, cols + 1)],
            s_sm[cols],
            slopes_g,
        )

        for idx_c, x in enumerate(cols):
            s = float(slopes_g[idx_c])
            for y in range(yt + 1, yb):
                t = (y - yt) / span
                wt = 0.5 * (1.0 - np.cos(np.pi * t))
                xt = float(np.clip(x - s * (y - yt), 0.0, float(w - 1)))
                xb = float(np.clip(x + s * (yb - y), 0.0, float(w - 1)))
                xt0 = int(np.floor(xt))
                xt1 = min(w - 1, xt0 + 1)
                fxt = xt - xt0
                col_t = out[yt, xt0] * (1.0 - fxt) + out[yt, xt1] * fxt

                xb0 = int(np.floor(xb))
                xb1 = min(w - 1, xb0 + 1)
                fxb = xb - xb0
                col_b = out[yb, xb0] * (1.0 - fxb) + out[yb, xb1] * fxb

                out[y, x] = col_t * (1.0 - wt) + col_b * wt
    return out


def align_and_repair_seam(
    arr: np.ndarray,
    seam_pos: int,
    anchors: List[Tuple[int, float, float, float, float, float]],
    exemplar_ranges: List[Tuple[int, int]],
    axis: int = 0,
    taper_r: int = 110,
    exclude_mask: np.ndarray | None = None,
    bridge_exclude_ranges: List[Tuple[int, int]] | None = None,
    foliage_only_ranges: List[Tuple[int, int]] | None = None,
) -> np.ndarray:
    """
    Alineacion 2D por tramos:
    - (sa, sb): corrimiento tangencial a lo largo de la costura.
    - (ova, ovb): corrimiento normal en zonas con traslape (ova < 0 / ovb > 0 recorta filas
      duplicadas para alinear simultaneamente lineas '/' y '\\').
    - hg >= 0: apertura de brecha real [-hg .. +hg] en zonas con filas faltantes,
      rellenada con puente de tensor de estructura (cuadriculas/vias) o exemplar 2D (arboles/palmas).
    """
    work = arr if axis == 0 else np.transpose(arr, (1, 0, 2)).copy()
    excl_w = None
    if exclude_mask is not None:
        excl_w = exclude_mask if axis == 0 else np.transpose(exclude_mask, (1, 0)).copy()

    h, w, _ = work.shape
    sa, sb, ova, ovb, hg = _interp_anchors_2d(w, anchors)

    y_start = max(0, seam_pos - taper_r)
    y_end = min(h, seam_pos + taper_r)
    band = work[y_start:y_end].copy()
    bh = band.shape[0]
    seam_local = seam_pos - y_start

    gy = np.arange(bh, dtype=np.float32)[:, None]
    gx = np.arange(w, dtype=np.float32)[None, :]

    # Parte A (arriba/izquierda):
    # - Si hg > 0: abre brecha colocando fila (seam_local-1) en (seam_local-1-hg).
    # - Si ova < 0 (ej. -1.5): desplaza muestreo hacia arriba (recorta traslape).
    ya = gy[:seam_local]
    da = np.maximum(0.0, (float(seam_local - 1) - hg[None, :]) - ya)
    fall_a = 0.5 * (1.0 + np.cos(np.pi * np.clip(da / float(taper_r), 0.0, 1.0)))
    sy_a = np.minimum(float(seam_local - 1), ya + (hg[None, :] + ova[None, :]) * fall_a)
    sx_a = gx - sa[None, :] * fall_a
    warped_a = _bilinear_sample_2d(band, sy_a, sx_a)

    # Parte B (abajo/derecha):
    # - Si hg > 0: abre brecha colocando fila seam_local en (seam_local+hg).
    # - Si ovb > 0 (ej. +1.5): desplaza muestreo hacia abajo (recorta traslape).
    yb = gy[seam_local:]
    db = np.maximum(0.0, yb - (float(seam_local) + hg[None, :]))
    fall_b = 0.5 * (1.0 + np.cos(np.pi * np.clip(db / float(taper_r), 0.0, 1.0)))
    sy_b = np.maximum(float(seam_local), yb + (ovb[None, :] - hg[None, :]) * fall_b)
    sx_b = gx - sb[None, :] * fall_b
    warped_b = _bilinear_sample_2d(band, sy_b, sx_b)

    warped = np.concatenate([warped_a, warped_b], axis=0)

    is_ex = np.zeros(w, dtype=bool)
    for r0, r1 in exemplar_ranges:
        is_ex[max(0, r0) : min(w, r1)] = True

    is_excl_bridge = np.zeros(w, dtype=bool)
    if bridge_exclude_ranges:
        for r0, r1 in bridge_exclude_ranges:
            is_excl_bridge[max(0, r0) : min(w, r1)] = True

    bridge_x = (~is_ex) & (~is_excl_bridge) & (hg >= 0.35)
    if bridge_x.any():
        warped = _structure_bridge_band(warped, seam_local, bridge_x, hg)

    # En zonas alineadas (hg < 0.35), solo un micro-feather de 1px sin blur
    micro_x = (~is_ex) & (~is_excl_bridge) & (~bridge_x)
    if micro_x.any():
        y0m, y1m = seam_local - 1, seam_local
        avg_c = 0.5 * (warped[y0m - 1, micro_x] + warped[y1m + 1, micro_x])
        warped[y0m, micro_x] = 0.78 * warped[y0m, micro_x] + 0.22 * avg_c
        warped[y1m, micro_x] = 0.78 * warped[y1m, micro_x] + 0.22 * avg_c

    # Exemplar 2D en rangos organicos: apertura estrecha proporcional a hg
    hole_gen = np.zeros((bh, w), dtype=bool)
    for x in np.where(is_ex)[0]:
        g = max(1, int(np.ceil(hg[x])))
        hole_gen[max(0, seam_local - g) : min(bh, seam_local + g + 1), x] = True
    if hole_gen.any():
        sub_excl = excl_w[y_start:y_end] if excl_w is not None else None
        warped = exemplar_inpaint_mask(
            warped,
            hole_gen,
            exclude_source_mask=sub_excl,
            patch_r=4,
            search_r=30,
            core_r=0,
            stride=1,
        )

    work[y_start:y_end] = np.clip(warped, 0.0, 255.0)
    return work if axis == 0 else np.transpose(work, (1, 0, 2)).copy()


def _polar_bridge_band(
    arr: np.ndarray,
    cx: float,
    cy: float,
    ar: float,
    hole_y0: int,
    hole_y1: int,
    hole_x0: int,
    hole_x1: int,
    axis: int = 0,
) -> None:
    h, w, _ = arr.shape
    src = arr.copy()

    if axis == 0:
        y_t = hole_y0 - 1
        y_b = hole_y1
        for y in range(hole_y0, hole_y1):
            t = (y - y_t) / float(y_b - y_t)
            for x in range(hole_x0, hole_x1):
                dx_n = (x - cx) / ar
                dy = y - cy
                r = float(np.hypot(dx_n, dy))
                val_t = r * r - (y_t - cy) ** 2
                val_b = r * r - (y_b - cy) ** 2
                sgn = -1.0 if x < cx else 1.0
                xt = cx + sgn * ar * np.sqrt(max(0.0, val_t)) if val_t >= 0 else float(x)
                xb = cx + sgn * ar * np.sqrt(max(0.0, val_b)) if val_b >= 0 else float(x)
                xt0 = int(np.clip(np.floor(xt), 0, w - 2))
                ft = xt - xt0
                ct = src[y_t, xt0] * (1.0 - ft) + src[y_t, xt0 + 1] * ft
                xb0 = int(np.clip(np.floor(xb), 0, w - 2))
                fb = xb - xb0
                cb = src[y_b, xb0] * (1.0 - fb) + src[y_b, xb0 + 1] * fb
                wt = 0.5 * (1.0 - np.cos(np.pi * t))
                arr[y, x] = ct * (1.0 - wt) + cb * wt
    else:
        x_l = hole_x0 - 1
        x_r = hole_x1
        for y in range(hole_y0, hole_y1):
            for x in range(hole_x0, hole_x1):
                t = (x - x_l) / float(x_r - x_l)
                dx_n = (x - cx) / ar
                dy = y - cy
                r = float(np.hypot(dx_n, dy))
                val_l = r * r - ((x_l - cx) / ar) ** 2
                val_r = r * r - ((x_r - cx) / ar) ** 2
                sgn = -1.0 if y < cy else 1.0
                yl = cy + sgn * np.sqrt(max(0.0, val_l)) if val_l >= 0 else float(y)
                yr = cy + sgn * np.sqrt(max(0.0, val_r)) if val_r >= 0 else float(y)
                yl0 = int(np.clip(np.floor(yl), 0, h - 2))
                fl = yl - yl0
                cl = src[yl0, x_l] * (1.0 - fl) + src[yl0 + 1, x_l] * fl
                yr0 = int(np.clip(np.floor(yr), 0, h - 2))
                fr = yr - yr0
                cr = src[yr0, x_r] * (1.0 - fr) + src[yr0 + 1, x_r] * fr
                wt = 0.5 * (1.0 - np.cos(np.pi * t))
                arr[y, x] = cl * (1.0 - wt) + cr * wt


def reconstruct_aleta_roundabout(arr: np.ndarray) -> np.ndarray:
    """
    Reconstruye la elipse exacta de Aleta del Tiburon (centro real cx=2805, cy=959, ar=1.60)
    puenteando [937..945] sobre ambos arcos tras limpiar y reclonar los arbustos cortados.
    """
    # Extraer sprite del arbusto limpio en [y=961..991, x=2741..2771]
    b_patch = arr[961:991, 2741:2771].copy()
    lum_b = b_patch.mean(axis=2)
    r_b = b_patch[:, :, 0]
    b_core = (r_b < 98.0) & (lum_b < 135.0)
    yy, xx = np.mgrid[0:30, 0:30]
    b_core &= (((xx - 15.0) / 12.5) ** 2 + ((yy - 15.0) / 11.5) ** 2) <= 1.0
    pad_c = np.pad(b_core, 1, mode="constant")
    b_dil = pad_c[:-2, 1:-1] | pad_c[2:, 1:-1] | pad_c[1:-1, :-2] | pad_c[1:-1, 2:] | b_core
    b_alpha = np.where(b_core, 1.0, np.where(b_dil, 0.25, 0.0)).astype(np.float32)

    # Puente polar eliptico exacto sobre ambos arcos (y=937..945)
    _polar_bridge_band(arr, cx=2805.0, cy=959.0, ar=1.60, hole_y0=937, hole_y1=945, hole_x0=2665, hole_x1=2733, axis=0)
    _polar_bridge_band(arr, cx=2805.0, cy=959.0, ar=1.60, hole_y0=937, hole_y1=945, hole_x0=2882, hole_x1=2946, axis=0)

    lum_all = arr.mean(axis=2)
    is_true_grass = (
        (arr[:, :, 1] - arr[:, :, 0] > 10.0)
        & (arr[:, :, 1] - arr[:, :, 2] > 35.0)
        & (lum_all > 118.0)
        & (lum_all < 225.0)
    )
    non_grass = ~is_true_grass

    yy_all, xx_all = np.mgrid[0 : arr.shape[0], 0 : arr.shape[1]]
    bush_mask = (((xx_all - 2748.0) ** 2 + (yy_all - 940.0) ** 2) <= 10.5 ** 2) | (
        ((xx_all - 2862.0) ** 2 + (yy_all - 942.0) ** 2) <= 10.5 ** 2
    )
    arr = exemplar_inpaint_mask(
        arr,
        bush_mask,
        exclude_source_mask=non_grass,
        patch_r=4,
        search_r=20,
        core_r=0,
        stride=1,
    )

    for cx_b, cy_b in [(2748, 940), (2862, 942)]:
        d2 = (xx_all - float(cx_b)) ** 2 + (yy_all - float(cy_b)) ** 2
        inner = d2 <= 10.5 ** 2
        ring = (d2 > 11.5 ** 2) & (d2 <= 16.0 ** 2) & is_true_grass
        if ring.any() and inner.any():
            delta = arr[ring].mean(axis=0) - arr[inner].mean(axis=0)
            arr[inner] = np.clip(arr[inner] + delta, 0.0, 255.0)

    for cx_b, cy_b in [(2748, 936), (2862, 940)]:
        px0, py0 = cx_b - 15, cy_b - 15
        ba = b_alpha[:, :, None]
        arr[py0 : py0 + 30, px0 : px0 + 30] = arr[py0 : py0 + 30, px0 : px0 + 30] * (1.0 - ba) + b_patch * ba
    return arr


def reconstruct_south_roundabout(arr: np.ndarray) -> np.ndarray:
    """
    Reconstruye limpiamente los arcos elipticos superior e inferior de la Glorieta Sur
    (centro real cx=1946.5, cy=1382.0, ar=1.74) y limpia la union en T superior en X=1671.
    """
    # 1. Arcos superior e inferior de la rotonda sobre X=1671 (franja 1667..1675)
    _polar_bridge_band(
        arr, cx=1946.5, cy=1382.0, ar=1.74, hole_y0=1286, hole_y1=1336, hole_x0=1667, hole_x1=1675, axis=1
    )
    _polar_bridge_band(
        arr, cx=1946.5, cy=1382.0, ar=1.74, hole_y0=1425, hole_y1=1504, hole_x0=1667, hole_x1=1675, axis=1
    )

    # 2. Union en T superior (y=1246..1286, x=1668..1674)
    t_mask = np.zeros(arr.shape[:2], dtype=bool)
    t_mask[1246:1286, 1668:1674] = True
    arr = exemplar_inpaint_mask(
        arr,
        t_mask,
        patch_r=4,
        search_r=26,
        core_r=0,
        stride=1,
    )
    return arr


def extract_intact_lamp_sprite(arr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    x0, y0, x1, y1 = 2024, 971, 2058, 1063
    patch = arr[y0:y1, x0:x1].copy()
    ph, pw, _ = patch.shape

    lum = patch.mean(axis=2)
    r, g, b = patch[:, :, 0], patch[:, :, 1], patch[:, :, 2]
    is_dark = lum < 115.0
    is_yellow = (r > 195.0) & (g > 155.0) & (b < 110.0)
    is_blue_cap = (b > 135.0) & (r < 115.0)
    core = is_dark | is_yellow | is_blue_cap

    yy, xx = np.mgrid[0:ph, 0:pw]
    in_bounds = ((yy <= 33) & (np.abs(xx - 16.5) <= 10.5)) | ((yy > 33) & (np.abs(xx - 16.5) <= 7.5))
    core = core & in_bounds

    dil = core.copy()
    for _ in range(2):
        pad = np.pad(dil, 1, mode="constant")
        dil = (
            pad[:-2, :-2] | pad[:-2, 1:-1] | pad[:-2, 2:]
            | pad[1:-1, :-2] | pad[1:-1, 1:-1] | pad[1:-1, 2:]
            | pad[2:, :-2] | pad[2:, 1:-1] | pad[2:, 2:]
        )
    alpha = np.where(core, 1.0, np.where(dil, 0.72, 0.0)).astype(np.float32)
    pad_a = np.pad(alpha, 1, mode="constant")
    alpha_s = (
        pad_a[:-2, 1:-1] + pad_a[2:, 1:-1] + pad_a[1:-1, :-2] + pad_a[1:-1, 2:] + 4.0 * alpha
    ) / 8.0
    alpha = np.where(core, 1.0, alpha_s).astype(np.float32)
    return patch, alpha


def _lamp_foreground_mask(patch: np.ndarray) -> np.ndarray:
    lum = patch.mean(axis=2)
    r, g, b = patch[:, :, 0], patch[:, :, 1], patch[:, :, 2]
    core = (lum < 140.0) | ((r > 180.0) & (g > 140.0) & (b < 125.0)) | ((b > 120.0) & (r < 135.0))
    dil = core.copy()
    for _ in range(3):
        pad = np.pad(dil, 1, mode="constant")
        dil = (
            pad[:-2, :-2] | pad[:-2, 1:-1] | pad[:-2, 2:]
            | pad[1:-1, :-2] | pad[1:-1, 1:-1] | pad[1:-1, 2:]
            | pad[2:, :-2] | pad[2:, 1:-1] | pad[2:, 2:]
        )
    return dil


def _build_all_lamps_exclusion_mask(shape: Tuple[int, int]) -> np.ndarray:
    m = np.zeros(shape, dtype=bool)
    boxes = [
        (468, 845, 510, 966),
        (1054, 872, 1098, 1006),
        (1248, 880, 1296, 1030),
        (1846, 854, 1884, 964),
        (2550, 896, 2594, 1038),
    ]
    for x0, y0, x1, y1 in boxes:
        m[y0:y1, x0:x1] = True
    return m


def repair_cut_streetlamps(arr: np.ndarray, lamp_rgb: np.ndarray, lamp_alpha: np.ndarray) -> np.ndarray:
    lh, lw, _ = lamp_rgb.shape
    pole_cx_local = 17
    base_y_local = 87

    full_replace = [
        (476, 848, 502, 962, 489, 956),
        (1058, 874, 1094, 1004, 1079, 998),
        (1252, 882, 1292, 1028, 1276, 1023),
        (2552, 898, 2592, 1034, 2572, 1029),
    ]
    mask_all = np.zeros(arr.shape[:2], dtype=bool)
    for hx0, hy0, hx1, hy1, _, _ in full_replace:
        mask_all[hy0:hy1, hx0:hx1] |= _lamp_foreground_mask(arr[hy0:hy1, hx0:hx1])

    excl = _build_all_lamps_exclusion_mask(arr.shape[:2]) | mask_all
    arr = exemplar_inpaint_mask(
        arr,
        mask_all,
        exclude_source_mask=excl,
        patch_r=5,
        search_r=48,
        core_r=0,
        stride=1,
    )

    # Base del farol 1864: borrar solo la silueta oscura desplazada preservando sombra/acera natural
    m1864 = np.zeros(arr.shape[:2], dtype=bool)
    sub_18 = arr[938:958, 1854:1874]
    dark_18 = sub_18.mean(axis=2) < 145.0
    pad_18 = np.pad(dark_18, 1, mode="constant")
    dil_18 = pad_18[:-2, 1:-1] | pad_18[2:, 1:-1] | pad_18[1:-1, :-2] | pad_18[1:-1, 2:] | dark_18
    m1864[938:958, 1854:1874] = dil_18
    arr = exemplar_inpaint_mask(
        arr,
        m1864,
        exclude_source_mask=excl | m1864,
        patch_r=3,
        search_r=18,
        core_r=0,
        stride=1,
    )

    for _, _, _, _, tcx, tby in full_replace:
        px0 = int(tcx - pole_cx_local)
        py0 = int(tby - base_y_local)
        a = lamp_alpha[:, :, None]
        arr[py0 : py0 + lh, px0 : px0 + lw] = (
            arr[py0 : py0 + lh, px0 : px0 + lw] * (1.0 - a) + lamp_rgb * a
        )

    px4 = int(1864 - pole_cx_local)
    py4 = int(956 - base_y_local)
    y_cut = 934 - py4
    a4 = lamp_alpha[y_cut:, :, None]
    arr[py4 + y_cut : py4 + lh, px4 : px4 + lw] = (
        arr[py4 + y_cut : py4 + lh, px4 : px4 + lw] * (1.0 - a4) + lamp_rgb[y_cut:, :] * a4
    )
    return arr


def build_repaired_quadrants(source_dir: str, out_dir: str, save_preview: bool = False) -> np.ndarray:
    q_files = [
        "primer_cuadrante_mapa.png",
        "segundo_cuadrante_mapa.png",
        "tercer_cuadrante_mapa.png",
        "cuarto_cuadrante_mapa.png",
    ]
    quads = [
        np.array(
            Image.open(os.path.join(source_dir, fn)).convert("RGB").resize((QUAD_W, QUAD_H), Image.Resampling.LANCZOS),
            dtype=np.float32,
        )
        for fn in q_files
    ]

    full = np.zeros((WORLD_H, WORLD_W, 3), dtype=np.float32)
    full[:QUAD_H, :QUAD_W] = quads[0]
    full[:QUAD_H, QUAD_W:] = quads[1]
    full[QUAD_H:, :QUAD_W] = quads[2]
    full[QUAD_H:, QUAD_W:] = quads[3]

    lamp_rgb, lamp_alpha = extract_intact_lamp_sprite(full)

    # 1. Armonizacion cromatica material-aware + suavizado oceanico
    full = harmonize_colors_along_seam(full, QUAD_H, axis=0, radius=240)
    full = harmonize_colors_along_seam(full, QUAD_W, axis=1, radius=240)
    full = blend_ocean_seam(full, x_seam=QUAD_W, y_max=258, half_w=72)

    lamp_excl = _build_all_lamps_exclusion_mask(full.shape[:2])

    # 2. Costura horizontal Y = 941:
    # (x, dx_top, dx_bot, ov_top, ov_bot, fill_hg)
    # Nota:
    # - En Q1/Q3 (x=0..1671): las cuadriculas tienen brecha real +2.2..3.3px y dx=+2.5..3.8px.
    # - En Q2/Q4 (x=1850..2650): las cuadriculas tienen traslape ~2.9px (ov_top=-1.45, ov_bot=+1.45)
    #   y dx=-5.3px (sa=-2.65, sb=+2.65) para alinear '/' y '\\' simultaneamente.
    # - En Aleta y palmas costeras (x=2670..3342): brecha real ~6-8px.
    y_anchors = [
        (0, 1.0, -1.0, 0.0, 0.0, 1.0),
        (70, 1.0, -1.0, 0.0, 0.0, 1.1),        # Palma 1
        (250, 1.2, -1.2, 0.0, 0.0, 1.7),       # Grid 1 (G=3.4, dx=+2.4)
        (418, 1.1, -1.1, 0.0, 0.0, 0.6),       # Road 1 (diff=+2.27px)
        (555, 1.5, -1.5, 0.0, 0.0, 1.1),       # Grid 2a
        (700, 1.2, -1.2, 0.0, 0.0, 1.0),       # Palma 2 + arbol verde vecino
        (900, 1.9, -1.9, 0.0, 0.0, 1.1),       # Grid 3 (G=2.2, dx=+3.8)
        (1070, 1.8, -1.8, 0.0, 0.0, 1.1),      # Grid 3b
        (1165, 2.0, -2.0, 0.0, 0.0, 1.1),      # Road 2 (diff=+4.02px, G=2.2)
        (1275, 1.0, -1.0, 0.0, 0.0, 1.0),
        (1380, 0.5, -0.5, 0.0, 0.0, 1.0),      # Arbol parque izq
        (1515, 0.0, 0.0, 0.0, 0.0, 1.0),       # Arbol pequeno parque izq
        (1671, 0.0, 0.0, 0.0, 0.0, 1.2),       # Arbol rosa central
        (1790, -1.5, 1.5, 0.0, 0.0, 1.0),      # Arbol pequeno parque der
        (1890, -2.2, 2.2, -1.1, 1.1, 0.0),     # Transicion hacia Q2/Q4
        (1955, -2.5, 2.5, -1.2, 1.2, 0.0),     # Road 3
        (2160, -2.25, 2.25, -1.1, 1.1, 0.0),   # Grid 4a (dx=-4.5, ov=2.2)
        (2360, -2.25, 2.25, -1.1, 1.1, 0.0),   # Grid 4b
        (2560, -2.0, 2.0, -1.1, 1.1, 0.0),     # Grid 4c
        (2695, -0.4, 0.4, 0.0, 0.0, 0.0),      # Glorieta Aleta izq (puente polar luego)
        (2805, 0.0, 0.0, 0.0, 0.0, 0.0),       # Centro Aleta
        (2920, -2.0, 2.0, 0.0, 0.0, 0.0),      # Glorieta Aleta der (puente polar luego)
        (2960, 0.0, 0.0, 0.0, 0.0, 0.4),       # Playa fuera de Aleta
        (3018, 0.0, 0.0, 0.0, 0.0, 1.3),       # Palma costa 1
        (3075, 0.0, 0.0, 0.0, 0.0, 0.6),       # Orilla arena entre palmas
        (3132, 0.0, 0.0, 0.0, 0.0, 1.3),       # Palma costa 2
        (3206, 0.0, 0.0, 0.0, 0.0, 1.3),       # Palma costa 3
        (3341, 0.0, 0.0, 0.0, 0.0, 0.8),       # Mar derecha
    ]
    y_exemplar = [
        (35, 98),      # Palma 1
        (652, 765),    # Palma 2 + arbol verde vecino
        (922, 992),    # Arbol verde
        (1320, 1432),  # Arbol parque izq
        (1478, 1556),  # Arbol pequeno izq
        (1602, 1732),  # Arbol rosa central
        (1758, 1830),  # Arbol pequeno der
        (2985, 3045),  # Palma costa 1
        (3058, 3098),  # Orilla arena entre palmas
        (3105, 3158),  # Palma costa 2
        (3168, 3245),  # Palma costa 3
        (3260, 3341),  # Mar derecha
    ]
    full = align_and_repair_seam(
        full,
        QUAD_H,
        y_anchors,
        exemplar_ranges=y_exemplar,
        axis=0,
        taper_r=110,
        exclude_mask=lamp_excl,
        bridge_exclude_ranges=[(2665, 2946)],
    )

    # 3. Costura vertical X = 1671:
    # (y, dy_left, dy_right, ov_left, ov_right, fill_hg)
    x_anchors = [
        (0, 0.0, 0.0, 0.0, 0.0, 0.0),          # Mar (ya puenteado)
        (235, 0.0, 0.0, 0.0, 0.0, 0.0),
        (295, 0.8, -0.8, 0.0, 0.0, 1.0),       # Arbol verde playa
        (402, 0.7, -0.7, 0.0, 0.0, 0.0),       # Via curva superior
        (455, 0.5, -0.5, -4.0, 4.0, 0.0),      # Grid bajo curva superior (ov=8)
        (560, 0.8, -0.8, -5.0, 5.0, 0.0),      # Grid + DiagRoad1 (dy=+1.5, ov=10)
        (640, 1.2, -1.2, -5.0, 5.0, 0.0),      # DiagRoad1
        (740, 0.8, -0.8, -5.0, 5.0, 0.0),      # Grid cuadrado verde
        (825, 0.8, -0.8, -4.5, 4.5, 0.0),
        (875, 1.6, -1.6, -2.0, 2.0, 1.0),      # Arbol verde tras arbol rosa
        (955, 0.0, 0.0, 0.0, 0.0, 1.1),        # Arbol rosa central
        (1060, 0.0, 0.0, 0.0, 0.0, 0.0),
        (1155, 0.45, -0.45, 0.0, 0.0, 0.0),    # DiagRoad2 (diff=+0.87px)
        (1265, 0.0, 0.0, 0.0, 0.0, 0.0),       # T-junction Glorieta Sur
        (1310, 0.6, -0.6, 0.0, 0.0, 0.0),      # Glorieta Sur arco superior
        (1382, 1.2, -1.2, 0.0, 0.0, 0.0),      # Centro Glorieta Sur
        (1475, 2.1, -2.1, 0.0, 0.0, 0.0),      # Glorieta Sur arco inferior (diff=+4.26px)
        (1538, 0.0, 0.0, 0.0, 0.0, 1.0),       # Arbusto bajo glorieta
        (1640, -0.5, 0.5, 0.0, 0.0, 0.65),     # Grid inferior (dy=-1.0, Gx=+1.3)
        (1881, -0.5, 0.5, 0.0, 0.0, 0.65),
    ]
    x_exemplar = [
        (266, 330),    # Arbol verde playa
        (838, 1012),   # Arbol verde tras arbol rosa + arbol rosa completo
        (1518, 1562),  # Arbusto sur bajo glorieta
    ]
    full = align_and_repair_seam(
        full,
        QUAD_W,
        x_anchors,
        exemplar_ranges=x_exemplar,
        axis=1,
        taper_r=110,
        bridge_exclude_ranges=[(1246, 1506)],  # Glorieta Sur se reconstruye polarmente
    )

    # 4. Reconstruccion dedicada para Glorieta Sur (X=1671) y Aleta del Tiburon (Y=941)
    full = reconstruct_south_roundabout(full)
    full = reconstruct_aleta_roundabout(full)

    # 5. Reparacion quirurgica de los 5 faroles sobre Y=941
    full = repair_cut_streetlamps(full, lamp_rgb, lamp_alpha)

    out_u8 = np.clip(full, 0, 255).astype(np.uint8)

    if save_preview:
        os.makedirs("artifacts/_v5_inspect", exist_ok=True)
        pil_full = Image.fromarray(out_u8)
        crops = [
            ("x_top", (1521, 0, 1821, 660)),
            ("x_mid", (1521, 620, 1821, 1280)),
            ("x_bot", (1521, 1240, 1821, 1882)),
            ("y_1", (0, 791, 700, 1091)),
            ("y_2", (660, 791, 1360, 1091)),
            ("y_3", (1320, 791, 2020, 1091)),
            ("y_4", (1980, 791, 2680, 1091)),
            ("y_5", (2640, 791, 3342, 1091)),
        ]
        for cname, box in crops:
            pil_full.crop(box).save(os.path.join("artifacts", "_v5_inspect", f"{cname}.png"))

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        Image.fromarray(out_u8[:QUAD_H, :QUAD_W]).save(os.path.join(out_dir, "primer_cuadrante_mapa.png"))
        Image.fromarray(out_u8[:QUAD_H, QUAD_W:]).save(os.path.join(out_dir, "segundo_cuadrante_mapa.png"))
        Image.fromarray(out_u8[QUAD_H:, :QUAD_W]).save(os.path.join(out_dir, "tercer_cuadrante_mapa.png"))
        Image.fromarray(out_u8[QUAD_H:, QUAD_W:]).save(os.path.join(out_dir, "cuarto_cuadrante_mapa.png"))

    return out_u8


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default="artifacts/_orig_head")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    build_repaired_quadrants(args.source_dir, args.out_dir, save_preview=args.preview)
    print("Done repairing quadrants v5.")
