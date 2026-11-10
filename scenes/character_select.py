import math
from typing import List, Optional, Callable, Dict, Any, Tuple
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from ui.button import UIButton
from effects.gl_particles import GLParticleSystem
from effects.juice_particles import JuiceParticleManager

CHARACTER_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "westcol",
        "name": "WESTCOL",
        "asset_filename": "westcol_seleccion_personaje.png",
        "theme_color": (195, 150, 235),  # Lila / Violeta brillante
    },
    {
        "id": "char",
        "name": "ALEX CHAR",
        "asset_filename": "char_seleccion_personaje.png",
        "theme_color": (105, 180, 245),  # Azul cielo caribeño
    },
    {
        "id": "katherine",
        "name": "KATHERINE",
        "asset_filename": "katherine_seleccion_personaje.png",
        "theme_color": (135, 215, 150),  # Verde menta pastel
    },
    {
        "id": "shakira",
        "name": "SHAKIRA",
        "asset_filename": "shakira_seleccion_personaje.png",
        "theme_color": (250, 145, 190),  # Rosa coral pop
    }
]

class CharacterCard:
    """
    Tarjeta de personaje donde la imagen en sí es la caja (sin cajas ni textos superpuestos a mano).
    Incorpora físicas de elevación, resorte de Squash & Stretch, y aura orgánica en el color del personaje.
    """
    def __init__(
        self,
        config: Dict[str, Any],
        center_pos: Tuple[int, int],
        sprite: pygame.Surface,
        target_height: int = 490
    ) -> None:
        self.config = config
        self.char_id: str = config["id"]
        self.name: str = config["name"]
        self.theme_color: Tuple[int, int, int] = config.get("theme_color", (255, 218, 55))
        self.target_height = target_height

        # Recortar ruido alfa de compresión para obtener el perímetro exacto de la tarjeta
        clean_sprite = self._crop_true_content(sprite)
        orig_w = clean_sprite.get_width()
        orig_h = clean_sprite.get_height()
        self.base_width = int(orig_w * target_height / orig_h)
        self.base_height = target_height
        self.base_sprite = pygame.transform.smoothscale(clean_sprite, (self.base_width, self.base_height))

        self.center_x, self.center_y = center_pos
        self.rect = pygame.Rect(0, 0, self.base_width, self.base_height)
        self.rect.center = (self.center_x, self.center_y)

        # Estados de interacción
        self.is_hovered: bool = False
        self.is_selected: bool = False

        # Físicas elásticas (Game Feel)
        self.scale: float = 1.0
        self.offset_y: float = 0.0
        self.squash_y: float = 0.0
        self.squash_vel: float = 0.0
        self.pulse_timer: float = 0.0

        # Pre-computar textura de resplandor suave en el color temático del personaje
        self.glow_texture = self._create_soft_glow(self.base_width, self.base_height, color=self.theme_color)

    @staticmethod
    def _crop_true_content(surface: pygame.Surface, alpha_threshold: int = 20) -> pygame.Surface:
        mask = pygame.mask.from_surface(surface, alpha_threshold)
        rects = mask.get_bounding_rects()
        if not rects:
            return surface
        bbox = rects[0]
        sub = surface.subsurface(bbox)
        clean = pygame.Surface((bbox.width, bbox.height), pygame.SRCALPHA)
        clean.blit(sub, (0, 0))
        return clean

    def _create_soft_glow(self, width: int, height: int, color: Tuple[int, int, int] = (255, 218, 55)) -> pygame.Surface:
        pad = 60
        gw = width + pad * 2
        gh = height + pad * 2
        surf = pygame.Surface((gw, gh), pygame.SRCALPHA)
        steps = 22
        for i in range(steps, 0, -1):
            ratio = i / steps
            alpha = int(75 * (1.0 - ratio**1.7))
            r_pad = int(pad * ratio)
            rw = width + r_pad * 2
            rh = height + r_pad * 2
            rect = pygame.Rect((gw - rw) // 2, (gh - rh) // 2, rw, rh)
            pygame.draw.rect(surf, (*color, alpha), rect, border_radius=int(38 + r_pad * 0.4))
        return surf

    def trigger_bounce(self) -> None:
        self.squash_vel = -0.24

    def update(self, dt: float) -> None:
        self.pulse_timer += dt * 3.8

        # Físicas de resorte (Hooke + Amortiguamiento)
        spring_k = 360.0
        damping_c = 18.0
        acc = -spring_k * self.squash_y - damping_c * self.squash_vel
        self.squash_vel += acc * dt
        self.squash_y += self.squash_vel * dt

        # Interpolación suave de escala y elevación
        target_scale = 1.05 if self.is_selected else (1.03 if self.is_hovered else 1.0)
        target_offset = -14.0 if self.is_selected else (-8.0 if self.is_hovered else 0.0)

        blend = 1.0 - math.exp(-24.0 * dt)
        self.scale += (target_scale - self.scale) * blend
        self.offset_y += (target_offset - self.offset_y) * blend
        self.rect.centery = int(self.center_y + self.offset_y)

    def render(self, surface: pygame.Surface) -> None:
        eff_scale_x = max(0.5, self.scale - self.squash_y * 0.5)
        eff_scale_y = max(0.5, self.scale + self.squash_y)

        draw_w = max(10, int(self.base_width * eff_scale_x))
        draw_h = max(10, int(self.base_height * eff_scale_y))

        # Flotación viva para la tarjeta seleccionada (Breathing Bob)
        bob_sel = math.sin(self.pulse_timer * 2.8) * 4.5 if self.is_selected else 0.0
        draw_y = self.center_y + self.offset_y + bob_sel

        # Backlight volumétrico en el color identitario del personaje
        if self.is_selected:
            pulse = math.sin(self.pulse_timer) * 0.5 + 0.5
            glow_scale = 1.0 + pulse * 0.05
            gw = int(self.glow_texture.get_width() * glow_scale)
            gh = int(self.glow_texture.get_height() * glow_scale)
            scaled_glow = pygame.transform.smoothscale(self.glow_texture, (gw, gh))
            surface.blit(scaled_glow, scaled_glow.get_rect(center=(self.center_x, int(draw_y))))
        elif self.is_hovered:
            # Hover suave con el color temático del personaje (sin amarillos genéricos)
            gw = int(self.glow_texture.get_width() * 0.98)
            gh = int(self.glow_texture.get_height() * 0.98)
            hover_glow = pygame.transform.smoothscale(self.glow_texture, (gw, gh))
            hover_glow.set_alpha(115)
            surface.blit(hover_glow, hover_glow.get_rect(center=(self.center_x, int(draw_y))))

        # Renderizar la tarjeta limpia (la ilustración en sí como caja oficial)
        scaled_sprite = pygame.transform.smoothscale(self.base_sprite, (draw_w, draw_h))
        dest_rect = scaled_sprite.get_rect(center=(self.center_x, int(draw_y)))
        surface.blit(scaled_sprite, dest_rect)


class CharacterSelectScene(BaseState):
    """
    Escena de Selección de Personajes de BarranquillaWare a 1920x1080 Full HD:
    - 4 Tarjetas oficiales donde la imagen en sí es la caja (Westcol, Alex Char, Katherine, Shakira).
    - Cabecera nativa con título e iconos ensamblados proporcionalmente sin deformación.
    - Soporte completo de shaders GLSL de partículas (ModernGL).
    - Botón 'SELECCIONAR' con aura dorada palpitante y destello Shimmer integrado.
    - Sincronización integral de audio (SSOT).
    """
    def __init__(
        self,
        on_character_chosen: Optional[Callable[[str], None]] = None,
        on_back_callback: Optional[Callable[[], None]] = None
    ) -> None:
        super().__init__()
        self.screen_w = 1920
        self.screen_h = 1080
        self.on_character_chosen = on_character_chosen
        self.on_back_callback = on_back_callback

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        # 1. Fondo Full HD
        raw_bg = self.assets.load_surface("fondo_seleccion_personaje.png", has_alpha=False)
        self.background = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))

        # 2. Pipeline de Partículas (Destellos dorados y Likes flotantes para gala de influencers)
        self.particles = GLParticleSystem(count=45, screen_w=self.screen_w, screen_h=self.screen_h, particle_type="sparkles")
        self.juice_particles = JuiceParticleManager()
        self.timer: float = 0.0

        # 3. Cabecera (Título e Iconos ensamblados en sus proporciones exactas)
        self._init_header_assets()

        # 4. Inicializar Tarjetas de Personajes (Westcol seleccionado por defecto como en el diseño de referencia)
        self.selected_index: int = 0
        self._init_cards()

        # 5. Botones UI
        self._init_buttons()

    def _init_header_assets(self) -> None:
        # 1. Título completo sin recortes arbitrarios (proporción nativa completa)
        raw_t = self.assets.load_surface("titulo_seleccion_personaje.png")
        mask_t = pygame.mask.from_surface(raw_t, 20)
        rects_t = mask_t.get_bounding_rects()
        bbox_t = rects_t[0] if rects_t else pygame.Rect(0, 0, raw_t.get_width(), raw_t.get_height())
        title_sub = raw_t.subsurface(bbox_t)
        title_clean = pygame.Surface((bbox_t.width, bbox_t.height), pygame.SRCALPHA)
        title_clean.blit(title_sub, (0, 0))

        target_tw = 860
        target_th = int(target_tw * bbox_t.height / bbox_t.width)
        self.title_surf = pygame.transform.smoothscale(title_clean, (target_tw, target_th))

        # 2. Icono izquierdo (móvil con corazón + rayos) con presencia e impacto visual
        raw_i = self.assets.load_surface("iconos_seleccion_personaje.png")
        phone_rect = pygame.Rect(40, 112, 634, 528)
        phone_sub = raw_i.subsurface(phone_rect)
        target_pw = 210
        target_ph = int(target_pw * phone_rect.height / phone_rect.width)
        self.icon_left_surf = pygame.transform.smoothscale(phone_sub, (target_pw, target_ph))

        # 3. Icono derecho (pulgar con bocadillo de corazón) en tamaño proporcional
        like_rect = pygame.Rect(1456, 115, 684, 491)
        like_sub = raw_i.subsurface(like_rect)
        target_lw = 230
        target_lh = int(target_lw * like_rect.height / like_rect.width)
        self.icon_right_surf = pygame.transform.smoothscale(like_sub, (target_lw, target_lh))

        self.title_center_x = 960
        self.title_center_y = 135
        self.icon_left_pos = (390, 135)
        self.icon_right_pos = (1530, 135)

    def _init_cards(self) -> None:
        centers_x = [330, 750, 1170, 1590]
        card_y = 530
        target_h = 490

        self.cards: List[CharacterCard] = []
        for i, config in enumerate(CHARACTER_CATALOG):
            sprite = self.assets.load_surface(config["asset_filename"])
            card = CharacterCard(
                config=config,
                center_pos=(centers_x[i], card_y),
                sprite=sprite,
                target_height=target_h
            )
            if i == self.selected_index:
                card.is_selected = True
            self.cards.append(card)

    def _init_buttons(self) -> None:
        # Botón Regresar (ampliado proporcionalmente para mejor ergonomía y presencia visual)
        btn_back_surf = self.assets.get_scaled("regresar_seleccion_personaje.png", target_width=165)
        self.btn_back = UIButton(
            center_pos=(150, 88),
            normal_sprite=btn_back_surf,
            on_click=self._on_back_clicked
        )

        # Botón Seleccionar
        btn_select_surf = self.assets.get_scaled("boton_seleccionar_seleccion_personaje.png", target_width=440)
        self.btn_select = UIButton(
            center_pos=(960, 955),
            normal_sprite=btn_select_surf,
            on_click=self._on_confirm_selection
        )

        # Botones de audio
        audio_frames = self.assets.get_audio_button_frames(target_size=86)
        self.btn_music = UIButton(
            center_pos=(1710, 78),
            normal_sprite=audio_frames[0],
            alt_sprite=audio_frames[1],
            is_toggle=True,
            initial_toggle_state=self.audio.music_enabled,
            on_click=self.audio.toggle_music
        )
        self.btn_sound = UIButton(
            center_pos=(1822, 78),
            normal_sprite=audio_frames[2],
            alt_sprite=audio_frames[3],
            is_toggle=True,
            initial_toggle_state=self.audio.sound_enabled,
            on_click=self.audio.toggle_sound
        )

        self.buttons: List[UIButton] = [
            self.btn_back,
            self.btn_select,
            self.btn_music,
            self.btn_sound
        ]

    def _select_character(self, index: int) -> None:
        if 0 <= index < len(self.cards):
            self.selected_index = index
            for i, card in enumerate(self.cards):
                card.is_selected = (i == index)
            selected_card = self.cards[index]
            selected_card.trigger_bounce()
            self.audio.play_click()
            self.juice_particles.emit_sparks((selected_card.center_x, selected_card.center_y), count=8)

    def _on_confirm_selection(self) -> None:
        selected_id = self.cards[self.selected_index].char_id
        self.audio.play_click()
        self.juice_particles.emit_sparks((960, 955), count=14)
        if self.on_character_chosen:
            self.on_character_chosen(selected_id)

    def _on_back_clicked(self) -> None:
        if self.on_back_callback:
            self.on_back_callback()

    def sync_audio_buttons(self) -> None:
        self.btn_music.toggle_state = self.audio.music_enabled
        self.btn_sound.toggle_state = self.audio.sound_enabled

    def enter(self, params: Optional[dict] = None) -> None:
        self.sync_audio_buttons()
        # Mantiene la música de la pantalla de selección de modo sin reiniciarla
        self.audio.play_bgm("dodo_airlines_acnh_ost_seleccion_modo.ogg")

    def handle_event(self, event: pygame.event.Event) -> None:
        for btn in self.buttons:
            btn.handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            for card in self.cards:
                card.is_hovered = card.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, card in enumerate(self.cards):
                if card.rect.collidepoint(event.pos):
                    self._select_character(i)
                    break
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                new_idx = (self.selected_index - 1) % len(self.cards)
                self._select_character(new_idx)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                new_idx = (self.selected_index + 1) % len(self.cards)
                self._select_character(new_idx)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._on_confirm_selection()
            elif event.key == pygame.K_ESCAPE:
                self._on_back_clicked()

    def update(self, dt: float) -> None:
        self.timer += dt
        self.particles.update(dt)
        self.juice_particles.update(dt)

        for btn in self.buttons:
            btn.update(dt)

        for card in self.cards:
            card.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        self.sync_audio_buttons()
        surface.blit(self.background, (0, 0))

        # 1. Chispas de Juice
        self.juice_particles.render(surface)

        # 2. Cabecera con animación flotante
        self._render_header(surface)

        # 3. Tarjetas de Personajes (las imágenes en sí como cajas)
        for card in self.cards:
            card.render(surface)

        # 4. Halo dorado animado bajo el botón SELECCIONAR
        self._render_button_glow(surface)

        # 5. Botones UI
        for btn in self.buttons:
            btn.render(surface)

    def _render_button_glow(self, surface: pygame.Surface) -> None:
        pulse = math.sin(self.timer * 3.6) * 0.5 + 0.5
        halo_w = int(460 + pulse * 18)
        halo_h = int(140 + pulse * 10)
        alpha = int(70 + pulse * 50)

        glow_surf = pygame.Surface((halo_w, halo_h), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_surf, (255, 210, 50, alpha), (0, 0, halo_w, halo_h))
        surface.blit(glow_surf, glow_surf.get_rect(center=(960, 955)))

    def _render_header(self, surface: pygame.Surface) -> None:
        bob_y = math.sin(self.timer * 2.1) * 4.0
        rot_title = math.sin(self.timer * 1.3) * 0.2

        bob_left = math.sin(self.timer * 2.6 + 0.6) * 5.0
        rot_left = math.sin(self.timer * 1.8) * 2.2

        bob_right = math.sin(self.timer * 2.4 + 1.2) * 5.0
        rot_right = math.sin(self.timer * 1.6 + 0.4) * 2.0

        # Texto del título en el centro (completo sin recortes)
        t_rot = pygame.transform.rotozoom(self.title_surf, rot_title, 1.0)
        surface.blit(t_rot, t_rot.get_rect(center=(self.title_center_x, int(self.title_center_y + bob_y))))

        # Iconos izquierdo y derecho con proporciones nativas completas
        il_rot = pygame.transform.rotozoom(self.icon_left_surf, rot_left, 1.0)
        surface.blit(il_rot, il_rot.get_rect(center=(self.icon_left_pos[0], int(self.icon_left_pos[1] + bob_left))))

        ir_rot = pygame.transform.rotozoom(self.icon_right_surf, rot_right, 1.0)
        surface.blit(ir_rot, ir_rot.get_rect(center=(self.icon_right_pos[0], int(self.icon_right_pos[1] + bob_right))))
