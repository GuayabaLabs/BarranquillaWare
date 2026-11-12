"""
BarranquillaWare - Componente de Interfaz y Diálogos del Mapa
Renderizado de globos de diálogo (Paloma de Curramba), diálogos de bienvenida,
tarjetas de misión (Quest Card) y modal de victoria final.
"""
import math
from typing import Optional, List
import pygame
from ui.button import UIButton


class StoryMapUI:
    """Gestiona el renderizado de modales, diálogos y tarjetas interactivas del mapa."""

    def __init__(self, screen_w: int = 1920, screen_h: int = 1080) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h

    def render_paloma_dialog(
        self,
        surface: pygame.Surface,
        anim_t: float,
        pages: List[List[str]],
        page_idx: int,
        speaker: str,
        badge: str,
        timer: float,
        portrait_surf: pygame.Surface,
        dialog_box_surf: pygame.Surface,
        font_speaker: pygame.font.Font,
        font_badge: pygame.font.Font,
        font_body: pygame.font.Font,
        font_hint: pygame.font.Font,
    ) -> None:
        """Renderiza el cuadro de diálogo acuarela oficial (text_dialog.png) con paloma_dialog.png."""
        anim = max(0.0, min(1.0, anim_t))

        # 1. Oscurecimiento cálido y suave de fondo
        dim_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        dim_surf.fill((22, 16, 36, int(145 * anim)))
        surface.blit(dim_surf, (0, 0))

        if not pages:
            return

        p_idx = max(0, min(page_idx, len(pages) - 1))
        lines = pages[p_idx]

        bob_y = int(math.sin(timer * 3.0) * 6.0)
        pal_surf = portrait_surf
        pal_w, pal_h = pal_surf.get_size()

        box_surf = dialog_box_surf.copy()
        bw, bh = box_surf.get_size()

        total_x = (self.screen_w - bw) // 2 + 85
        total_y = self.screen_h - bh - 18 + int((1.0 - anim) * 45)

        pal_x = total_x - int(pal_w * 0.72)
        pal_y = total_y + bh - pal_h - 36 + bob_y

        speaker_txt = font_speaker.render(speaker, True, (92, 46, 118))
        box_surf.blit(speaker_txt, speaker_txt.get_rect(center=(int(bw * 0.295), int(bh * 0.228))))

        if badge:
            badge_txt = font_badge.render(badge, True, (135, 80, 155))
            box_surf.blit(badge_txt, (int(bw * 0.47), int(bh * 0.21)))

        start_y = int(bh * 0.38)
        line_spacing = 46
        text_center_x = int(bw * 0.49)
        first_line_min_x = int(bw * 0.145)
        first_line_max_x = int(bw * 0.818) - 10
        other_line_min_x = int(bw * 0.115)
        other_line_max_x = int(bw * 0.895)

        for i, line in enumerate(lines):
            txt_surf = font_body.render(line, True, (68, 42, 82))
            min_x = first_line_min_x if i == 0 else other_line_min_x
            max_x = first_line_max_x if i == 0 else other_line_max_x
            avail_w = max(120, max_x - min_x)

            if txt_surf.get_width() > avail_w:
                scale_f = avail_w / float(txt_surf.get_width())
                new_h = max(14, int(txt_surf.get_height() * scale_f))
                txt_surf = pygame.transform.smoothscale(txt_surf, (avail_w, new_h))

            rect = txt_surf.get_rect(center=(text_center_x, start_y + i * line_spacing))
            if rect.right > max_x:
                rect.right = max_x
            if rect.left < min_x:
                rect.left = min_x
            box_surf.blit(txt_surf, rect)

        total_pages = len(pages)
        if p_idx + 1 < total_pages:
            hint_str = f"Página {p_idx + 1}/{total_pages} • ESPACIO o CLICK para continuar"
        else:
            hint_str = "ESPACIO o CLICK para continuar"
        hint_surf = font_hint.render(hint_str, True, (145, 92, 160))
        box_surf.blit(hint_surf, hint_surf.get_rect(midright=(int(bw * 0.82), int(bh * 0.73))))

        if anim < 0.99:
            box_surf.set_alpha(int(255 * anim))
            pal_copy = pal_surf.copy()
            pal_copy.set_alpha(int(255 * anim))
            surface.blit(box_surf, (total_x, total_y))
            surface.blit(pal_copy, (pal_x, pal_y))
        else:
            surface.blit(box_surf, (total_x, total_y))
            surface.blit(pal_surf, (pal_x, pal_y))

    def render_victory_modal(
        self,
        surface: pygame.Surface,
        confetti: list,
        btn_explore: UIButton,
        btn_menu: UIButton,
    ) -> None:
        """Renderiza el modal de victoria final con confeti y opciones."""
        dim_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        dim_surf.fill((10, 12, 25, 190))
        surface.blit(dim_surf, (0, 0))

        for cf in confetti:
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

        txt_vt = font_v_title.render("★ ¡ORGULLO DE CURRAMBA! ★", True, (255, 225, 80))
        vic_surf.blit(txt_vt, txt_vt.get_rect(center=(vw // 2, 70)))

        txt_vs = font_v_sub.render("¡COMPLETASTE LOS 4 NIVELES DE LA HISTORIA!", True, (255, 255, 255))
        vic_surf.blit(txt_vs, txt_vs.get_rect(center=(vw // 2, 135)))

        badge_w, badge_h = 460, 48
        badge_s = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
        pygame.draw.rect(badge_s, (35, 130, 70), (0, 0, badge_w, badge_h), border_radius=14)
        pygame.draw.rect(badge_s, (110, 250, 160), (0, 0, badge_w, badge_h), width=2, border_radius=14)
        font_badge = pygame.font.SysFont("Arial Black, Impact", 20)
        txt_b = font_badge.render("BIENESTAR DIGITAL: 100% EN ARMONÍA", True, (230, 255, 240))
        badge_s.blit(txt_b, txt_b.get_rect(center=(badge_w // 2, 24)))
        vic_surf.blit(badge_s, badge_s.get_rect(center=(vw // 2, 205)))

        desc = [
            "Recorriste Barranquilla junto a la Paloma aprendiendo a desconectar con calma:",
            "Campus Uninorte, C.C. Buenavista, Estadio Metropolitano y Aeropuerto Cortissoz.",
            "¡La ciudad brilla más bonito cuando disfrutas el presente al ritmo de la brisa!"
        ]
        dy = 265
        for d in desc:
            txt_d = font_v_body.render(d, True, (200, 215, 240))
            vic_surf.blit(txt_d, txt_d.get_rect(center=(vw // 2, dy)))
            dy += 28

        surface.blit(vic_surf, (vx, vy))
        btn_explore.render(surface)
        btn_menu.render(surface)

    def render_intro_dialog(
        self,
        surface: pygame.Surface,
        character_bust: pygame.Surface,
        paloma_guide: pygame.Surface,
    ) -> None:
        """Renderiza el cuadro de diálogo de bienvenida al mapa."""
        dw, dh = 960, 200
        dx = (self.screen_w - dw) // 2
        dy = self.screen_h - dh - 40

        d_surf = pygame.Surface((dw, dh), pygame.SRCALPHA)
        pygame.draw.rect(d_surf, (20, 24, 38, 245), (0, 0, dw, dh), border_radius=24)
        pygame.draw.rect(d_surf, (245, 195, 75), (0, 0, dw, dh), width=3, border_radius=24)

        d_surf.blit(character_bust, (30, 20))
        d_surf.blit(paloma_guide, (dw - paloma_guide.get_width() - 32, 24))

        char_name = "LA PALOMA GUÍA"
        font_d_title = pygame.font.SysFont("Arial Black, Impact", 24)
        font_d_body = pygame.font.SysFont("Arial, sans-serif", 16)
        font_d_sub = pygame.font.SysFont("Arial Black, Impact", 13)

        txt_d_title = font_d_title.render(f"¡{char_name.upper()} TE DA LA BIENVENIDA! 🕊️", True, (255, 220, 80))
        d_surf.blit(txt_d_title, (210, 25))

        lines = [
            "Soy la paloma mensajera de Curramba: conozco cada atajo y cada reto.",
            "Sígueme por los 8 distritos; algunos desafíos solo aparecen en su barrio.",
            "Supera los retos, ilumina las rutas y ayuda a despertar el Carnaval."
        ]
        ly = 68
        for line in lines:
            txt_l = font_d_body.render(line, True, (240, 245, 255))
            d_surf.blit(txt_l, (210, ly))
            ly += 26

        txt_prompt = font_d_sub.render("▶ PULSA ESPACIO O HAZ CLICK PARA EMPEZAR A EXPLORAR", True, (120, 235, 160))
        d_surf.blit(txt_prompt, (210, 160))
        surface.blit(d_surf, (dx, dy))
