"""
BarranquillaWare - Previsualización de Niveles Estilo Mario Wonder y Miniaturas
Carga/recorta miniaturas reales de los 5 niveles jugables y renderiza el callout
flotante en estilo cozy acuarela con posicionamiento anti-colisión en 1920x1080.
"""
import math
import os
from typing import Any, Dict, List, Optional, Tuple
import pygame

from core.asset_manager import AssetManager
from scenes.story_map_data import STORY_LEVEL_PREVIEW_META, STORY_LEVEL_STAGES


def _load_preview_source(asset_ref: str) -> Optional[pygame.Surface]:
    """Carga la imagen real del microjuego desde assets/ o una ruta relativa del proyecto."""
    assets = AssetManager.get_instance()
    if not asset_ref:
        return None
    if os.path.exists(asset_ref):
        try:
            return pygame.image.load(asset_ref).convert_alpha()
        except Exception:
            return None
    try:
        return assets.load_surface(asset_ref, has_alpha=False).convert_alpha()
    except Exception:
        return None


def crop_cover_rounded(
    src: pygame.Surface,
    target_w: int,
    target_h: int,
    crop_anchor: str = "center",
    border_radius: int = 12,
) -> pygame.Surface:
    """Recorta proporcionalmente (cover) sin deformar y aplica esquinas redondeadas limpias."""
    sw, sh = src.get_size()
    if sw <= 0 or sh <= 0:
        return pygame.Surface((target_w, target_h), pygame.SRCALPHA)

    target_ratio = target_w / float(max(1, target_h))
    src_ratio = sw / float(max(1, sh))

    if src_ratio > target_ratio:
        crop_h = sh
        crop_w = max(1, int(round(sh * target_ratio)))
        cx = max(0, (sw - crop_w) // 2)
        cy = 0
    else:
        crop_w = sw
        crop_h = max(1, int(round(sw / target_ratio)))
        cx = 0
        overflow_y = max(0, sh - crop_h)
        if crop_anchor == "top":
            cy = int(overflow_y * 0.05)
        elif crop_anchor == "bottom":
            cy = int(overflow_y * 0.90)
        else:
            cy = overflow_y // 2

    cropped = src.subsurface(pygame.Rect(cx, cy, crop_w, crop_h))
    scaled = pygame.transform.smoothscale(cropped, (target_w, target_h)).convert_alpha()

    if border_radius > 0:
        mask = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, target_w, target_h), border_radius=border_radius)
        scaled.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    return scaled


class LevelPreviewBuilder:
    """Construye y cachea miniaturas enmarcadas en acuarela y el callout estilo Mario Wonder."""

    # Dimensiones del marco marco_callout_nivel.png (nativo 960x644) escalado a 386x259
    CALLOUT_W: int = 386
    CALLOUT_H: int = 259
    # Caja del cuerpo principal dentro de 386x259 (excluyendo los rayos decorativos)
    BODY_X: int = 18
    BODY_Y: int = 29
    BODY_W: int = 367
    BODY_H: int = 229
    INTERIOR_CX: int = 204

    def __init__(self, screen_w: int = 1920, screen_h: int = 1080) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.assets = AssetManager.get_instance()

        self._thumb_cache: Dict[Tuple[str, int, int], pygame.Surface] = {}
        self._callout_card_cache: Dict[Tuple[str, bool], pygame.Surface] = {}

        # Cargar assets ilustrados del callout
        self.tex_frame = self._load_opt("marco_callout_nivel.png", (self.CALLOUT_W, self.CALLOUT_H))
        self.tex_tail_base = self._load_opt("colita_callout_nivel.png", (38, 32))
        self.tex_bezel = self._load_opt("tarjeta_slot_partida.png")
        self.tex_ribbon = self._load_opt("cinta_estado_modal.png")
        self.tex_sello_done = self._load_opt("sello_estado_despejado.png", (40, 40))
        self.tex_sello_pending = self._load_opt("sello_estado_pendiente.png", (40, 40))

        star_filled = self._load_opt("estrella_dificultad.png", (19, 19))
        self.star_filled = star_filled
        if star_filled is not None:
            star_empty = pygame.transform.grayscale(star_filled.copy())
            star_empty.fill((255, 255, 255, 85), special_flags=pygame.BLEND_RGBA_MULT)
            self.star_empty = star_empty
        else:
            self.star_empty = None

        # Estado para inspección / tests
        self.last_callout_rect: Optional[pygame.Rect] = None
        self.last_tail_rect: Optional[pygame.Rect] = None
        self.last_tail_dir: Optional[str] = None
        self.last_poi_key: Optional[str] = None

    def clear_last_callout(self) -> None:
        """Limpia el estado de rectángulo visible cuando el callout no se renderiza."""
        self.last_callout_rect = None
        self.last_tail_rect = None
        self.last_tail_dir = None
        self.last_poi_key = None

    def contains_screen_pos(self, pos: Tuple[int, int]) -> bool:
        """Indica si una posición en pantalla cae sobre la tarjeta visible del callout."""
        return self.last_callout_rect is not None and self.last_callout_rect.collidepoint(pos)

    def _load_opt(self, filename: str, size: Optional[Tuple[int, int]] = None) -> Optional[pygame.Surface]:
        try:
            surf = self.assets.load_surface(filename, has_alpha=True)
            if size is not None:
                return pygame.transform.smoothscale(surf, size)
            return surf
        except Exception:
            return None

    def get_framed_thumbnail(
        self,
        poi_key: str,
        outer_w: int,
        outer_h: int,
        inset: int = 6,
    ) -> pygame.Surface:
        """Retorna una miniatura proporcional enmarcada en borde acuarela dorado/lila."""
        key = (poi_key, outer_w, outer_h)
        if key in self._thumb_cache:
            return self._thumb_cache[key]

        canvas = pygame.Surface((outer_w, outer_h), pygame.SRCALPHA)
        if self.tex_bezel is not None:
            bezel = pygame.transform.smoothscale(self.tex_bezel, (outer_w, outer_h))
            canvas.blit(bezel, (0, 0))

        meta = STORY_LEVEL_PREVIEW_META.get(poi_key, {})
        src = _load_preview_source(meta.get("preview_asset", ""))
        inner_w = max(20, outer_w - inset * 2)
        inner_h = max(20, outer_h - inset * 2)
        if src is not None:
            thumb = crop_cover_rounded(
                src,
                inner_w,
                inner_h,
                crop_anchor=meta.get("crop_anchor", "center"),
                border_radius=max(6, inset + 4),
            )
            canvas.blit(thumb, (inset, inset))

        self._thumb_cache[key] = canvas
        return canvas

    def _get_callout_card_surface(self, poi_key: str, is_cleared: bool, poi_info: Dict[str, Any]) -> pygame.Surface:
        """Compone y cachea la tarjeta del callout flotante (sin colita ni animación)."""
        cache_key = (poi_key, bool(is_cleared))
        if cache_key in self._callout_card_cache:
            return self._callout_card_cache[cache_key]

        card = pygame.Surface((self.CALLOUT_W, self.CALLOUT_H), pygame.SRCALPHA)
        if self.tex_frame is not None:
            card.blit(self.tex_frame, (0, 0))

        meta = STORY_LEVEL_PREVIEW_META.get(poi_key, {})
        title_str = meta.get("callout_title", poi_info.get("title", poi_key.upper()))
        difficulty = int(meta.get("difficulty", 2))
        max_diff = int(meta.get("max_difficulty", 5))
        stages = STORY_LEVEL_STAGES.get(poi_key, [])
        rounds = max(1, len(stages)) if poi_key in STORY_LEVEL_STAGES else 1

        # 1. Título destacado en cabecera con fuente de Coaster (evitando el pétalo rosa en x~352)
        title_size = 24
        f_title = self.assets.cargarFuenteTitulo(title_size)
        txt_title = f_title.render(title_str, True, (42, 26, 16))
        while txt_title.get_width() > 296 and title_size > 17:
            title_size -= 1
            f_title = self.assets.cargarFuenteTitulo(title_size)
            txt_title = f_title.render(title_str, True, (42, 26, 16))
        title_rect = txt_title.get_rect(center=(self.INTERIOR_CX - 6, 55))
        card.blit(txt_title, title_rect)

        # 2. Miniatura real del microjuego centrada dentro del pergamino
        thumb_w, thumb_h = 312, 134
        thumb_x = self.INTERIOR_CX - thumb_w // 2
        thumb_y = 72
        framed_thumb = self.get_framed_thumbnail(poi_key, thumb_w, thumb_h, inset=6)
        card.blit(framed_thumb, (thumb_x, thumb_y))

        # 3. Etiqueta de rondas en esquina inferior izquierda de la miniatura
        rounds_label = "2 RONDAS" if rounds >= 2 else "1 RONDA"
        if self.tex_ribbon is not None:
            rib_w, rib_h = 104, 24
            rib_scaled = pygame.transform.smoothscale(self.tex_ribbon, (rib_w, rib_h))
            rib_rect = pygame.Rect(thumb_x + 10, thumb_y + thumb_h - rib_h - 8, rib_w, rib_h)
            card.blit(rib_scaled, rib_rect)
            f_round = self.assets.cargarFuenteCuento(15)
            txt_round = f_round.render(rounds_label, True, (82, 42, 102))
            card.blit(txt_round, txt_round.get_rect(center=(rib_rect.centerx, rib_rect.centery - 1)))

        # 4. Sello de estado (Despejado / Pendiente) en esquina superior derecha de la miniatura
        sello = self.tex_sello_done if is_cleared else self.tex_sello_pending
        if sello is not None:
            sello_rect = sello.get_rect(center=(thumb_x + thumb_w - 18, thumb_y + 22))
            card.blit(sello, sello_rect)

        # 5. Franja inferior: Estado + Dificultad con estrellas acuarela
        bottom_cy = 226
        f_meta = self.assets.cargarFuenteCuento(16)
        status_str = "DESPEJADO" if is_cleared else "PENDIENTE"
        status_col = (28, 122, 54) if is_cleared else (184, 86, 22)
        txt_status = f_meta.render(status_str, True, status_col)
        card.blit(txt_status, txt_status.get_rect(midleft=(thumb_x + 2, bottom_cy - 1)))

        # Estrellas de dificultad alineadas a la derecha
        if self.star_filled is not None:
            star_w = self.star_filled.get_width()
            star_gap = 2
            stars_total_w = max_diff * star_w + (max_diff - 1) * star_gap
            stars_x0 = (thumb_x + thumb_w) - stars_total_w - 2
            txt_diff = f_meta.render("Dificultad", True, (86, 54, 34))
            card.blit(txt_diff, txt_diff.get_rect(midright=(stars_x0 - 8, bottom_cy - 1)))
            for idx in range(max_diff):
                s_surf = self.star_filled if idx < difficulty else self.star_empty
                if s_surf is not None:
                    card.blit(s_surf, (stars_x0 + idx * (star_w + star_gap), bottom_cy - star_w // 2))

        self._callout_card_cache[cache_key] = card
        return card

    def compute_placement(
        self,
        anchor_screen: Tuple[int, int],
        blocked_rects: List[pygame.Rect],
        active_poi_rect: Optional[pygame.Rect] = None,
        player_rect: Optional[pygame.Rect] = None,
        obstacle_rects: Optional[List[pygame.Rect]] = None,
    ) -> Tuple[pygame.Rect, str]:
        """
        Calcula una posición libre de colisiones con HUD, bordes, edificio activo,
        personaje chibi y monumentos cercanos, manteniendo la colita hacia anchor_screen.
        Retorna (card_rect, tail_dir) donde card_rect es el rect completo de la textura 386x259.
        """
        safe_vp = pygame.Rect(68, 17, self.screen_w - 84, self.screen_h - 38)
        ax, ay = int(anchor_screen[0]), int(anchor_screen[1])

        def body_rect_of(r: pygame.Rect) -> pygame.Rect:
            return pygame.Rect(r.x + self.BODY_X, r.y + self.BODY_Y, self.BODY_W, self.BODY_H)

        def card_from_body(bx: int, by: int) -> pygame.Rect:
            return pygame.Rect(bx - self.BODY_X, by - self.BODY_Y, self.CALLOUT_W, self.CALLOUT_H)

        def clamp_to_safe(r: pygame.Rect) -> pygame.Rect:
            res = r.copy()
            if res.left + self.BODY_X < safe_vp.left:
                res.x = safe_vp.left - self.BODY_X
            if res.right > safe_vp.right:
                res.x = safe_vp.right - res.width
            if res.top + self.BODY_Y < safe_vp.top:
                res.y = safe_vp.top - self.BODY_Y
            if res.bottom > safe_vp.bottom:
                res.y = safe_vp.bottom - res.height
            return res

        def choose_tail_dir(br: pygame.Rect) -> str:
            deltas = [
                ("down", ay - br.bottom),
                ("up", br.top - ay),
                ("left", br.left - ax),
                ("right", ax - br.right),
            ]
            best_side = max(deltas, key=lambda kv: kv[1])
            if best_side[1] > -10:
                return best_side[0]
            return min(
                [
                    ("down", abs(br.bottom - ay)),
                    ("up", abs(ay - br.top)),
                    ("left", abs(ax - br.left)),
                    ("right", abs(br.right - ax)),
                ],
                key=lambda kv: kv[1],
            )[0]

        def predict_tail_rect(br: pygame.Rect, t_dir: str) -> pygame.Rect:
            overlap = 10
            if t_dir == "down":
                tx = max(br.left + 44, min(br.right - 44, ax))
                return pygame.Rect(tx - 19, br.bottom - overlap, 38, 32)
            if t_dir == "up":
                tx = max(br.left + 44, min(br.right - 44, ax))
                return pygame.Rect(tx - 19, br.top + overlap - 32, 38, 32)
            if t_dir == "left":
                ty = max(br.top + 44, min(br.bottom - 44, ay))
                return pygame.Rect(br.left + overlap - 32, ty - 19, 32, 38)
            ty = max(br.top + 44, min(br.bottom - 44, ay))
            return pygame.Rect(br.right - overlap, ty - 19, 32, 38)

        def clip_area_sum(rect: pygame.Rect, obstacles: List[pygame.Rect]) -> int:
            total = 0
            for blk in obstacles:
                inter = rect.clip(blk)
                if inter.width > 0 and inter.height > 0:
                    total += inter.width * inter.height
            return total

        hud_rects = list(blocked_rects)
        primary_obstacles = [r for r in (active_poi_rect, player_rect) if r is not None]
        secondary_obstacles = list(obstacle_rects) if obstacle_rects else []

        # Generar candidatos: alrededor del ancla + alrededor del perímetro exterior del edificio/personaje
        raw_candidates: List[Tuple[int, pygame.Rect]] = []
        gap_anchor = 34
        cx_offset = self.BODY_X + self.BODY_W // 2
        cy_offset = self.BODY_Y + self.BODY_H // 2
        raw_candidates.extend([
            (0, pygame.Rect(ax - cx_offset, ay - gap_anchor - self.CALLOUT_H, self.CALLOUT_W, self.CALLOUT_H)),
            (1, pygame.Rect(ax - cx_offset, ay + gap_anchor - self.BODY_Y, self.CALLOUT_W, self.CALLOUT_H)),
            (2, pygame.Rect(ax + gap_anchor - self.BODY_X, ay - cy_offset, self.CALLOUT_W, self.CALLOUT_H)),
            (3, pygame.Rect(ax - gap_anchor - self.CALLOUT_W, ay - cy_offset, self.CALLOUT_W, self.CALLOUT_H)),
        ])

        refs: List[pygame.Rect] = []
        if active_poi_rect is not None and player_rect is not None:
            refs.append(active_poi_rect.union(player_rect))
            refs.append(active_poi_rect)
            refs.append(player_rect)
        elif active_poi_rect is not None:
            refs.append(active_poi_rect)
        elif player_rect is not None:
            refs.append(player_rect)

        for ref in refs:
            for b_gap in (44, 36, 26, 16):
                # Arriba del edificio/personaje
                top_y = ref.top - b_gap - self.BODY_H
                # Abajo del edificio/personaje
                bot_y = ref.bottom + b_gap
                xs_horiz = [
                    ax - self.BODY_W // 2,
                    ref.centerx - self.BODY_W // 2,
                    ref.left,
                    ref.right - self.BODY_W,
                    safe_vp.left,
                    safe_vp.right - self.BODY_W,
                ]
                for blk in hud_rects:
                    if blk.left > safe_vp.left and blk.left - self.BODY_W - 8 >= safe_vp.left:
                        xs_horiz.append(blk.left - self.BODY_W - 8)
                    if blk.right + 8 + self.BODY_W <= safe_vp.right:
                        xs_horiz.append(blk.right + 8)
                for bx in xs_horiz:
                    raw_candidates.append((0, card_from_body(bx, top_y)))
                    raw_candidates.append((2, card_from_body(bx, bot_y)))

                # Derecha del edificio/personaje
                right_x = ref.right + b_gap
                # Izquierda del edificio/personaje
                left_x = ref.left - b_gap - self.BODY_W
                ys_vert = [
                    ay - self.BODY_H // 2,
                    ref.centery - self.BODY_H // 2,
                    ref.top,
                    ref.bottom - self.BODY_H,
                    max(140, ref.top - 40),
                ]
                for blk in hud_rects:
                    if blk.bottom < 320:
                        ys_vert.append(blk.bottom + 8)
                        ys_vert.append(blk.bottom + 24)
                for by in ys_vert:
                    raw_candidates.append((1, card_from_body(right_x, by)))
                    raw_candidates.append((1, card_from_body(left_x, by)))

        best_choice: Optional[Tuple[int, int, str, pygame.Rect]] = None
        seen_pos = set()
        for idx, (dir_bias, raw_r) in enumerate(raw_candidates):
            clamped = clamp_to_safe(raw_r)
            key = (clamped.x, clamped.y)
            if key in seen_pos:
                continue
            seen_pos.add(key)

            br = body_rect_of(clamped)
            t_dir = choose_tail_dir(br)
            tr = predict_tail_rect(br, t_dir)
            # Evaluar contra el envolvente ±3 px de la animación flotante vertical
            br_env = pygame.Rect(br.x, br.y - 3, br.width, br.height + 6)
            tr_env = pygame.Rect(tr.x, tr.y - 3, tr.width, tr.height + 6)

            hud_ov = clip_area_sum(br_env, hud_rects) + clip_area_sum(tr_env, hud_rects)
            out_vp_pen = (
                200000
                if (tr_env.top < 0 or tr_env.bottom > self.screen_h or tr_env.left < 0 or tr_env.right > self.screen_w)
                else 0
            )
            prim_ov = clip_area_sum(br_env, primary_obstacles) + clip_area_sum(tr_env, primary_obstacles)
            sec_ov = clip_area_sum(br_env, secondary_obstacles) + clip_area_sum(tr_env, secondary_obstacles)

            # Evitar tapar el punto ancla cuando no hay obstáculo primario o incluso con él
            anchor_pen = 500000 if br_env.inflate(10, 10).collidepoint(ax, ay) else 0

            # Distancia desde el punto de anclaje de la colita al anchor_screen
            if t_dir == "down":
                att_x, att_y = tr.centerx, br.bottom
            elif t_dir == "up":
                att_x, att_y = tr.centerx, br.top
            elif t_dir == "left":
                att_x, att_y = br.left, tr.centery
            else:
                att_x, att_y = br.right, tr.centery
            dist_pen = int(math.hypot(att_x - ax, att_y - ay))

            score = (
                hud_ov * 20000
                + out_vp_pen
                + prim_ov * 10000
                + sec_ov * 2000
                + anchor_pen
                + dist_pen * 3
                + dir_bias * 25
                + idx
            )
            if best_choice is None or score < best_choice[0]:
                best_choice = (score, idx, t_dir, clamped)

        chosen_rect = best_choice[3] if best_choice else clamp_to_safe(raw_candidates[0][1])
        chosen_dir = best_choice[2] if best_choice else "down"

        # Ajuste defensivo final si tras el clamp todavía rozara algún HUD superior
        br = body_rect_of(chosen_rect)
        tr = predict_tail_rect(br, chosen_dir)
        br_env = pygame.Rect(br.x, br.y - 3, br.width, br.height + 6)
        tr_env = pygame.Rect(tr.x, tr.y - 3, tr.width, tr.height + 6)
        cur_penalty = (
            clip_area_sum(br_env, hud_rects)
            + clip_area_sum(tr_env, hud_rects)
            + clip_area_sum(br_env, primary_obstacles)
            + clip_area_sum(tr_env, primary_obstacles)
            + clip_area_sum(br_env, secondary_obstacles)
            + clip_area_sum(tr_env, secondary_obstacles)
        )
        for blk in hud_rects:
            if br_env.colliderect(blk) or tr_env.colliderect(blk):
                if blk.bottom < 220 and min(br_env.top, tr_env.top) < blk.bottom:
                    pad_top = 32 if (ay < br.top or chosen_dir == "up") else 10
                    cand_rect = chosen_rect.copy()
                    cand_rect.y += (blk.bottom + pad_top) - br.top
                    if cand_rect.bottom > safe_vp.bottom:
                        cand_rect.y = safe_vp.bottom - cand_rect.height
                    cbr = body_rect_of(cand_rect)
                    cdir = choose_tail_dir(cbr)
                    ctr = predict_tail_rect(cbr, cdir)
                    cbr_env = pygame.Rect(cbr.x, cbr.y - 3, cbr.width, cbr.height + 6)
                    ctr_env = pygame.Rect(ctr.x, ctr.y - 3, ctr.width, ctr.height + 6)
                    cand_penalty = (
                        clip_area_sum(cbr_env, hud_rects)
                        + clip_area_sum(ctr_env, hud_rects)
                        + clip_area_sum(cbr_env, primary_obstacles)
                        + clip_area_sum(ctr_env, primary_obstacles)
                        + clip_area_sum(cbr_env, secondary_obstacles)
                        + clip_area_sum(ctr_env, secondary_obstacles)
                    )
                    if cand_penalty < cur_penalty:
                        chosen_rect = cand_rect
                        chosen_dir = cdir
                        br, tr = cbr, ctr
                        br_env, tr_env = cbr_env, ctr_env
                        cur_penalty = cand_penalty

        return chosen_rect, chosen_dir

    def render_callout(
        self,
        surface: pygame.Surface,
        poi_key: str,
        poi_info: Dict[str, Any],
        is_cleared: bool,
        anchor_screen: Tuple[int, int],
        blocked_rects: List[pygame.Rect],
        anim_t: float,
        timer: float,
        active_poi_rect: Optional[pygame.Rect] = None,
        player_rect: Optional[pygame.Rect] = None,
        obstacle_rects: Optional[List[pygame.Rect]] = None,
    ) -> Optional[pygame.Rect]:
        """Renderiza el callout flotante estilo Mario Wonder apuntando hacia anchor_screen."""
        if anim_t <= 0.02:
            self.clear_last_callout()
            return None

        card_base = self._get_callout_card_surface(poi_key, is_cleared, poi_info)
        card_rect, tail_dir = self.compute_placement(
            anchor_screen,
            blocked_rects,
            active_poi_rect=active_poi_rect,
            player_rect=player_rect,
            obstacle_rects=obstacle_rects,
        )

        # Animación elástica de entrada + leve flotación sinusoidal
        ease = 1.0 - (1.0 - min(1.0, anim_t)) ** 3
        scale = 0.86 + 0.14 * ease
        float_y = int(round(math.sin(timer * 2.8) * 3.0 * ease))

        draw_w = max(20, int(round(self.CALLOUT_W * scale)))
        draw_h = max(20, int(round(self.CALLOUT_H * scale)))
        scaled_card = pygame.transform.smoothscale(card_base, (draw_w, draw_h))
        if ease < 0.99:
            scaled_card.set_alpha(int(255 * ease))

        draw_rect = scaled_card.get_rect(center=(card_rect.centerx, card_rect.centery + float_y))
        body_left = draw_rect.x + int(self.BODY_X * scale)
        body_top = draw_rect.y + int(self.BODY_Y * scale)
        body_w = int(self.BODY_W * scale)
        body_h = int(self.BODY_H * scale)
        body_rect = pygame.Rect(body_left, body_top, body_w, body_h)

        # Renderizar tarjeta principal
        surface.blit(scaled_card, draw_rect.topleft)

        # Renderizar colita acuarela apuntando al ancla real del nivel
        tail_rect: Optional[pygame.Rect] = None
        if self.tex_tail_base is not None:
            rot_map = {"down": 0, "up": 180, "left": -90, "right": 90}
            tail_surf = pygame.transform.rotate(self.tex_tail_base, rot_map.get(tail_dir, 0))
            if abs(scale - 1.0) > 0.01:
                tw = max(8, int(tail_surf.get_width() * scale))
                th = max(8, int(tail_surf.get_height() * scale))
                tail_surf = pygame.transform.smoothscale(tail_surf, (tw, th))
            if ease < 0.99:
                tail_surf.set_alpha(int(255 * ease))

            ax, ay = int(anchor_screen[0]), int(anchor_screen[1])
            overlap = max(4, int(10 * scale))
            if tail_dir == "down":
                tx = max(body_rect.left + 44, min(body_rect.right - 44, ax))
                tail_rect = tail_surf.get_rect(midtop=(tx, body_rect.bottom - overlap))
            elif tail_dir == "up":
                tx = max(body_rect.left + 44, min(body_rect.right - 44, ax))
                tail_rect = tail_surf.get_rect(midbottom=(tx, body_rect.top + overlap))
            elif tail_dir == "left":
                ty = max(body_rect.top + 44, min(body_rect.bottom - 44, ay))
                tail_rect = tail_surf.get_rect(midright=(body_rect.left + overlap, ty))
            else:  # right
                ty = max(body_rect.top + 44, min(body_rect.bottom - 44, ay))
                tail_rect = tail_surf.get_rect(midleft=(body_rect.right - overlap, ty))

            surface.blit(tail_surf, tail_rect.topleft)

        self.last_callout_rect = body_rect
        self.last_tail_rect = tail_rect
        self.last_tail_dir = tail_dir
        self.last_poi_key = poi_key
        return body_rect
