import math
import os
import random
from typing import List, Optional, Callable, Dict, Any, Tuple
import pygame

from core.settings import CHARACTER_BASE_FOLLOWERS, CHARACTER_DISPLAY_NAMES
from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from ui.button import UIButton
from effects.gl_particles import GLParticleSystem
from effects.juice_particles import JuiceParticleManager
from scenes.load_game import build_centered_pill_button, render_outlined_text

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
        "id": "valdiri",
        "name": "VALDIRI",
        "asset_filename": "valdiri_seleccion_personaje.png",
        "theme_color": (250, 145, 190),  # Rosa coral pop
    }
]

carpetaSeleccion = "seleccion_pj"

presentaciones: Dict[str, Dict[str, Any]] = {
    "westcol": {
        "pose": "poseWestcol.jpg",
        "tarjeta": "tarjetaWestcol.jpg",
        "gesto": [(2, 0.35), (3, 0.35), (2, 0.35), (3, 0.35), (4, 1.2)],
        "frase": "¡Qué más, mi gente!",
    },
    "char": {
        "pose": "poseChar.jpg",
        "tarjeta": "tarjetaChar.jpg",
        "gesto": [(2, 0.9), (3, 1.0), (4, 1.3)],
        "frase": "¡Quiubo, Barranquilla!",
    },
    "katherine": {
        "pose": "poseKatherine.jpg",
        "tarjeta": "tarjetaKatherine.jpg",
        "gesto": [(2, 0.9), (3, 1.1), (4, 1.5)],
        "frase": "println(\"¡Hola, estimados!\")",
        "frases": ["println(\"¡Hola, estimados!\")", "¡No me estreses, estimado!", "Eso no compila, estimada.",
                   "¡No me estreses!", "¿Y el punto y coma, estimado?"],
        "pausa": 1.5,
    },
    "valdiri": {
        "pose": "poseValdiri.jpg",
        "tarjeta": "tarjetaValdiri.jpg",
        "gesto": [(2, 0.8), (3, 0.3), (2, 0.35), (4, 1.5)],
        "frase": "¡Ajá, machi!",
    },
}
reacciones: Dict[Tuple[str, str], str] = {
    ("westcol", "char"): "¡Alcalde, salúdeme en el stream!",
    ("westcol", "katherine"): "Profe, ¿eso viene en el parcial?",
    ("westcol", "valdiri"): "¡Valdiri, hagamos un live!",
    ("char", "westcol"): "¡Westcol, Barranquilla te espera!",
    ("char", "katherine"): "¡Profe, enséñele a la gente!",
    ("char", "valdiri"): "¡Ajá, Valdiri, a bailar!",
    ("katherine", "westcol"): "¡No me estreses, estimado!",
    ("katherine", "char"): "Estimado alcalde, ¿y el wifi del colegio?",
    ("katherine", "valdiri"): "Estimada, guarde ese celular.",
    ("valdiri", "westcol"): "¡Westcol, ponme en tu live!",
    ("valdiri", "char"): "¡Ajá, alcalde, qué más pues!",
    ("valdiri", "katherine"): "Profe, ¿me sacas una foto?",
}
llamadosTarjeta = ["¡Elígeme!", "¡Yo, yo!", "¡Aquí estoy!", "¡Mírame!", "¡Conmigo sí!"]
entradaPresentacion = 0.5
salidaPresentacion = 0.4
altoPresentacion = 1000


def cargarVerde(assets, archivo: str) -> Optional[pygame.Surface]:
    import numpy as np
    ruta = os.path.join(assets.base_dir, carpetaSeleccion, archivo)
    if not os.path.exists(ruta):
        return None
    try:
        imagen = pygame.image.load(ruta).convert_alpha()
    except pygame.error as e:
        print(f"[CharacterSelect] Aviso al cargar {archivo}: {e}")
        return None
    rgb = pygame.surfarray.array3d(imagen).astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    resto = np.maximum(r, b)
    alfa = np.clip(255 - ((g - resto) - 40) * 255 / 60, 0, 255)
    pixeles = pygame.surfarray.pixels3d(imagen)
    pixeles[..., 1] = np.minimum(g, resto + 12).astype(np.uint8)
    del pixeles
    canal = pygame.surfarray.pixels_alpha(imagen)
    canal[...] = alfa.astype(np.uint8)
    del canal
    return imagen


def formatoSeguidores(valor: float) -> str:
    valor = int(valor)
    if valor >= 1_000_000:
        return f"{valor / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if valor >= 1_000:
        return f"{valor // 1000}K"
    return str(valor)


def salidaRebote(x: float) -> float:
    x = max(0.0, min(1.0, x))
    c1 = 1.70158
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2

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

        orig_w = sprite.get_width()
        orig_h = sprite.get_height()
        self.base_width = int(orig_w * target_height / orig_h)
        self.base_height = target_height
        self.base_sprite = pygame.transform.smoothscale(sprite, (self.base_width, self.base_height))

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
            if getattr(self, "_cached_sel_glow_size", None) != (gw, gh):
                self._cached_sel_glow_size = (gw, gh)
                self._cached_sel_glow = pygame.transform.smoothscale(self.glow_texture, (gw, gh))
            surface.blit(self._cached_sel_glow, self._cached_sel_glow.get_rect(center=(self.center_x, int(draw_y))))
        elif self.is_hovered:
            # Hover suave con el color temático del personaje (sin amarillos genéricos)
            gw = int(self.glow_texture.get_width() * 0.98)
            gh = int(self.glow_texture.get_height() * 0.98)
            if getattr(self, "_cached_hov_glow_size", None) != (gw, gh):
                self._cached_hov_glow_size = (gw, gh)
                hover_glow = pygame.transform.smoothscale(self.glow_texture, (gw, gh))
                hover_glow.set_alpha(115)
                self._cached_hov_glow = hover_glow
            surface.blit(self._cached_hov_glow, self._cached_hov_glow.get_rect(center=(self.center_x, int(draw_y))))

        # Renderizar la tarjeta limpia (la ilustración en sí como caja oficial)
        if getattr(self, "_cached_sprite_size", None) != (draw_w, draw_h):
            self._cached_sprite_size = (draw_w, draw_h)
            self._cached_sprite = pygame.transform.smoothscale(self.base_sprite, (draw_w, draw_h))
        dest_rect = self._cached_sprite.get_rect(center=(self.center_x, int(draw_y)))
        surface.blit(self._cached_sprite, dest_rect)


class CharacterSelectScene(BaseState):
    """
    Escena de Selección de Personajes de BarranquillaWare a 1920x1080 Full HD:
    - 4 Tarjetas oficiales donde la imagen en sí es la caja (Westcol, Alex Char, Katherine, Valdiri).
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

        self.cargarPresentaciones()

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
        target_lw = 175
        target_lh = int(target_lw * like_rect.height / like_rect.width)
        self.icon_right_surf = pygame.transform.smoothscale(like_sub, (target_lw, target_lh))

        self.title_center_x = 960
        self.title_center_y = 135
        self.icon_left_pos = (390, 135)
        self.icon_right_pos = (1485, 146)

    def _init_cards(self) -> None:
        centers_x = [330, 750, 1170, 1590]
        card_y = 530
        target_h = 490

        self.cards: List[CharacterCard] = []
        for i, config in enumerate(CHARACTER_CATALOG):
            try:
                sprite = self.assets.load_cropped_surface(config["asset_filename"], alpha_threshold=20)
            except Exception as e:
                print(f"[CharacterSelect] Fallback para {config['asset_filename']}: {e}")
                # Fallback seguro con placeholder si falta el asset
                sprite = pygame.Surface((300, 490), pygame.SRCALPHA)
                pygame.draw.rect(sprite, config.get("theme_color", (100, 100, 100)), (0, 0, 300, 490), border_radius=16)
            datos = presentaciones.get(config["id"])
            if datos:
                try:
                    nueva = cargarVerde(self.assets, datos["tarjeta"])
                except Exception as e:
                    print(f"[CharacterSelect] Aviso con {datos['tarjeta']}: {e}")
                    nueva = None
                if nueva is not None:
                    sprite = nueva.subsurface(nueva.get_bounding_rect(min_alpha=20)).copy()

            card = CharacterCard(
                config=config,
                center_pos=(centers_x[i], card_y),
                sprite=sprite,
                target_height=target_h
            )
            if i == self.selected_index:
                card.is_selected = True
            self.cards.append(card)

    def _build_centered_pill_button(
        self,
        base_surface: pygame.Surface,
        label: str,
        target_size: Tuple[int, int],
        font_size: int,
        fill_color: Tuple[int, int, int],
        outline_color: Tuple[int, int, int],
    ) -> pygame.Surface:
        """Delega en el constructor compartido de botones píldora centrados."""
        return build_centered_pill_button(
            self.assets, base_surface, label, target_size, font_size, fill_color, outline_color
        )

    def _init_buttons(self) -> None:
        # Botón Regresar (base limpia de acuarela morada + 'Volver' centrado por tinta)
        back_base = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonMorado.jpg"), 220)
        btn_back_surf = self._build_centered_pill_button(
            back_base,
            label="Volver",
            target_size=(192, 66),
            font_size=30,
            fill_color=(255, 251, 242),
            outline_color=(66, 28, 108),
        )
        self.btn_back = UIButton(
            center_pos=(150, 88),
            normal_sprite=btn_back_surf,
            on_click=self._on_back_clicked
        )

        # Botón Seleccionar (base limpia dorada + 'Seleccionar' centrado por tinta)
        select_base = self.assets.load_cropped_surface("boton_jugar_modal.png", alpha_threshold=20)
        btn_select_surf = self._build_centered_pill_button(
            select_base,
            label="Seleccionar",
            target_size=(360, 124),
            font_size=44,
            fill_color=(64, 24, 92),
            outline_color=(255, 248, 232),
        )
        self.btn_select = UIButton(
            center_pos=(960, 955),
            normal_sprite=btn_select_surf,
            on_click=self.celebrar
        )

        # Botones de audio
        audio_frames = self.assets.get_audio_button_frames(target_size=82)
        self.btn_music = UIButton(
            center_pos=(1730, 76),
            normal_sprite=audio_frames[0],
            alt_sprite=audio_frames[1],
            is_toggle=True,
            initial_toggle_state=self.audio.music_enabled,
            on_click=self.audio.toggle_music
        )
        self.btn_sound = UIButton(
            center_pos=(1832, 76),
            normal_sprite=audio_frames[2],
            alt_sprite=audio_frames[3],
            is_toggle=True,
            initial_toggle_state=self.audio.sound_enabled,
            on_click=self.audio.toggle_sound
        )
        voice_frames = self.assets.get_voice_button_frames(target_size=82)
        self.btn_voice = UIButton(
            center_pos=(1628, 76),
            normal_sprite=voice_frames[0],
            alt_sprite=voice_frames[1],
            is_toggle=True,
            initial_toggle_state=self.audio.voice_enabled,
            on_click=self.audio.toggle_voice
        )
        self._draws_voice_badge = True

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
            self.presentar(index)

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
        if hasattr(self, "btn_voice"):
            self.btn_voice.toggle_state = self.audio.voice_enabled

    def enter(self, params: Optional[dict] = None) -> None:
        self.presentacion = None
        self.saliendo = []
        self.ladoSiguiente = -1
        self.lluvia = []
        self.celebracion = None
        self.quieto = 0.0
        self.vitrina = 0.0
        self.reaccion = None
        self.llamado = None
        self.presentar(self.selected_index)
        self.sync_audio_buttons()
        # Mantiene la música de la pantalla de selección de modo sin reiniciarla
        self.audio.play_bgm("dodo_airlines_acnh_ost_seleccion_modo.ogg")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            self.quieto = 0.0
        if self.celebracion is not None:
            return
        all_buttons = list(self.buttons)
        if hasattr(self, "btn_voice"):
            all_buttons.append(self.btn_voice)
        for btn in all_buttons:
            if btn.handle_event(event) and event.type != pygame.MOUSEMOTION:
                return

        if event.type == pygame.MOUSEMOTION:
            for card in self.cards:
                card.is_hovered = card.rect.collidepoint(event.pos)
            for i, card in enumerate(self.cards):
                if card.is_hovered and i != self.selected_index:
                    self.seleccionarPorEncima(i)
                    break
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
                self.celebrar()
            elif event.key == pygame.K_ESCAPE:
                self._on_back_clicked()

    def update(self, dt: float) -> None:
        self.timer += dt
        self.particles.update(dt)
        self.juice_particles.update(dt)

        for btn in self.buttons:
            btn.update(dt)
        if hasattr(self, "btn_voice"):
            self.btn_voice.update(dt)

        for card in self.cards:
            card.update(dt)

        self.actualizarPresentacion(dt)

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

        self.dibujarPresentacion(surface)

        # 5. Botones UI
        for btn in self.buttons:
            btn.render(surface)
        if hasattr(self, "btn_voice"):
            self.btn_voice.render(surface)
        if (not self.state_machine or self.state_machine.current_state is self) and hasattr(self.audio, "render_voice_muted_badge"):
            self.audio.render_voice_muted_badge(surface, right_top=(1873, 130))

        self.dibujarCelebracion(surface)

    def exit(self) -> None:
        self.audio.sonarEscritura(False)
        self.escribiendo = False

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

    def cargarPresentaciones(self) -> None:
        self.presentacion = None
        self.saliendo = []
        self.ladoSiguiente = -1
        self.flashPantalla = 0.0
        self.poses: Dict[str, List[pygame.Surface]] = {}
        self.desfasesPose: Dict[str, List[int]] = {}
        self.globoFrase = None
        self.nombresGrandes: Dict[str, pygame.Surface] = {}
        try:
            for config in CHARACTER_CATALOG:
                cid = config["id"]
                hoja = cargarVerde(self.assets, presentaciones[cid]["pose"])
                if hoja is None:
                    continue
                escala = altoPresentacion / float(hoja.get_height())
                cuadros, desfases = self.cortarPoses(hoja, 6)
                self.poses[cid] = [pygame.transform.smoothscale_by(c, escala) for c in cuadros]
                self.desfasesPose[cid] = [int(d * escala) for d in desfases]
            globo = self.assets.cargarSinFondo(os.path.join("Fritanga", "globoTexto.jpg"), 1200)
            self.globoFrase = globo.subsurface(globo.get_bounding_rect(min_alpha=60)).copy()
        except Exception as e:
            print(f"[CharacterSelect] Presentación sin assets: {e}")
        self.fuenteNombreGrande = self.assets.cargarFuenteTitulo(150)
        self.fuenteFrase = self.assets.cargarFuenteCuento(54)
        self.fuenteSeguidores = self.assets.cargarFuenteCuento(50)
        self.veloPresentacion = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        self.lluvia: List[Dict[str, Any]] = []
        self.proximaGota = 0.0
        self.celebracion: Optional[Dict[str, Any]] = None
        self.quieto = 0.0
        self.vitrina = 0.0
        self.escribiendo = False
        self.prepararLluvia()
        self.prepararSonidos()
        self.fuenteListo = self.assets.cargarFuenteTitulo(170)
        self.selloListo = None
        try:
            from effects.juice_particles import brillo, puntosFigura, paletasFuego
            for forma, escala, paleta in (("circulo", 175, "dorado"), ("circulo", 190, "rosa"), ("corazon", 165, "turquesa"),
                                          ("circulo", 160, "morado"), ("corazon", 160, "rojo")):
                alcance = max(math.hypot(p[0], p[1]) for p in puntosFigura(forma)) * escala
                brillo(paletasFuego[paleta][1], int(alcance * 1.3))
        except Exception as e:
            print(f"[CharacterSelect] Sin brillos previos: {e}")
        self.reaccion: Optional[Dict[str, Any]] = None
        self.llamado: Optional[Dict[str, Any]] = None
        self.proximoLlamado = 2.5
        self.tinte = [18.0, 14.0, 26.0]
        self.fuenteReaccion = self.assets.cargarFuenteCuento(34)
        self.fuenteLlamado = self.assets.cargarFuenteTitulo(30)
        self.caras: Dict[str, pygame.Surface] = {}
        self.halos: Dict[str, pygame.Surface] = {}
        for config in CHARACTER_CATALOG:
            cid = config["id"]
            self.halos[cid] = self.crearHalo(480, self.colorClaro(config["theme_color"]))
            if cid in self.poses:
                try:
                    self.caras[cid] = self.caraCircular(self.poses[cid][0], 46)
                except Exception as e:
                    print(f"[CharacterSelect] Sin cara para {cid}: {e}")

    def prepararLluvia(self) -> None:
        self.piezasLluvia: Dict[str, List[pygame.Surface]] = {cid: [] for cid in presentaciones}
        fuenteChat = self.assets.cargarFuenteCuento(32)
        usuarios = [("costeño23", (205, 95, 30)), ("lamejor_bq", (200, 60, 125)), ("juniorFC", (190, 135, 0)),
                    ("cumbia_99", (40, 115, 190)), ("ElPelao", (45, 140, 65)), ("curramba.tv", (130, 75, 200))]
        mensajes = ["W", "WWWW", "GG", "¡Crack!", "jajajaja", "¡Vamos!", "Westcol <3", "¡Qué nivel!"]
        globoChat = None
        try:
            crudo = self.assets.cargarSinFondo(os.path.join("Piano", "globoComentario.jpg"), 900)
            crudo = crudo.subsurface(crudo.get_bounding_rect(min_alpha=40)).copy()
            globoChat = pygame.transform.smoothscale_by(crudo, 60 / float(crudo.get_height()))
        except Exception as e:
            print(f"[CharacterSelect] Sin globo de comentario: {e}")
        self.globoChat = globoChat
        for k, mensaje in enumerate(mensajes):
            usuario, colorUsuario = usuarios[k % len(usuarios)]
            nombre = fuenteChat.render(usuario + ":", True, colorUsuario)
            texto = fuenteChat.render(" " + mensaje, True, (80, 46, 92))
            ancho = nombre.get_width() + texto.get_width() + 44
            if globoChat is not None:
                chip = self.estirarPastilla(globoChat, max(ancho, globoChat.get_height() * 2))
            else:
                chip = pygame.Surface((ancho, 60), pygame.SRCALPHA)
                pygame.draw.rect(chip, (250, 240, 228), chip.get_rect(), border_radius=30)
            x = (chip.get_width() - nombre.get_width() - texto.get_width()) // 2
            chip.blit(nombre, nombre.get_rect(midleft=(x, chip.get_height() // 2 - 1)))
            chip.blit(texto, texto.get_rect(midleft=(x + nombre.get_width(), chip.get_height() // 2 - 1)))
            self.piezasLluvia["westcol"].append(chip)

        banderas = self.piezasDeHoja("banderitas.jpg", (96, 116, 136))
        if banderas:
            self.piezasLluvia["char"].extend(banderas)
        else:
            for ancho in (54, 70, 86):
                self.piezasLluvia["char"].append(self.banderaBarranquilla(ancho))

        fuenteCodigo = self.assets.cargarFuenteTitulo(52)
        coloresCodigo = [(120, 220, 255), (255, 205, 95), (205, 155, 255), (140, 235, 155), (255, 140, 170)]
        for k, token in enumerate(["{ }", "</>", ";", "if", "( )", "=>", "#", "def", "[ ]", "True", "print( )", "0101"]):
            color = coloresCodigo[k % len(coloresCodigo)]
            self.piezasLluvia["katherine"].append(self.textoContorno(fuenteCodigo, token, color, self.colorOscuro(color, 0.35), 4))

        corazones = self.piezasDeHoja("corazonesValdiri.jpg", (50, 62, 76, 40, 54))
        if corazones:
            self.piezasLluvia["valdiri"].extend(self.contornear(pieza, 3) for pieza in corazones)
        else:
            for tam, color in ((56, (255, 95, 140)), (74, (255, 150, 190)), (44, (240, 60, 110))):
                self.piezasLluvia["valdiri"].append(self.contornear(self.dibujoCorazon(tam, color), 3))
            for tam in (34, 48):
                self.piezasLluvia["valdiri"].append(self.contornear(self.dibujoDestello(tam, (255, 245, 200)), 3))
        estrella = self.piezasLluvia["valdiri"][-1]
        self.estrellaSeleccion = pygame.transform.smoothscale_by(estrella, 80 / float(estrella.get_height()))

    def contornear(self, pieza: pygame.Surface, grosor: int) -> pygame.Surface:
        import numpy as np
        alfa = pygame.surfarray.array_alpha(pieza)
        opacos = alfa > 160
        if not opacos.any():
            return pieza
        rgb = pygame.surfarray.array3d(pieza)[opacos]
        promedio = rgb.mean(axis=0)
        tono = pygame.Color(int(promedio[0]), int(promedio[1]), int(promedio[2]))
        h, s, v, _ = tono.hsva
        tono.hsva = (h, min(100.0, s * 1.6 + 20), v * 0.72, 100)
        borde = (tono.r, tono.g, tono.b)
        silueta = pygame.mask.from_surface(pieza, 100).to_surface(setcolor=(*borde, 255), unsetcolor=(0, 0, 0, 0))
        lienzo = pygame.Surface((pieza.get_width() + grosor * 2, pieza.get_height() + grosor * 2), pygame.SRCALPHA)
        for grados in range(0, 360, 30):
            lienzo.blit(silueta, (grosor + round(math.cos(math.radians(grados)) * grosor),
                                  grosor + round(math.sin(math.radians(grados)) * grosor)))
        lienzo.blit(pieza, (grosor, grosor))
        return lienzo

    def estirarPastilla(self, base: pygame.Surface, ancho: int) -> pygame.Surface:
        alto = base.get_height()
        tapa = min(base.get_width() // 2 - 1, alto)
        pastilla = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        pastilla.blit(base.subsurface((0, 0, tapa, alto)), (0, 0))
        centro = base.subsurface((tapa, 0, base.get_width() - tapa * 2, alto))
        pastilla.blit(pygame.transform.smoothscale(centro, (ancho - tapa * 2, alto)), (tapa, 0))
        pastilla.blit(base.subsurface((base.get_width() - tapa, 0, tapa, alto)), (ancho - tapa, 0))
        return pastilla

    def piezasDeHoja(self, archivo: str, altos: Tuple[int, ...]) -> List[pygame.Surface]:
        try:
            hoja = cargarVerde(self.assets, archivo)
        except Exception as e:
            print(f"[CharacterSelect] Aviso con {archivo}: {e}")
            return []
        if hoja is None:
            return []
        mascara = pygame.mask.from_surface(hoja, 100)
        cajas = [c for c in mascara.get_bounding_rects() if c.w > hoja.get_width() * 0.04 and c.h > hoja.get_height() * 0.08]
        cajas.sort(key=lambda c: (c.x, c.y))
        piezas = []
        for k, caja in enumerate(cajas):
            pieza = hoja.subsurface(caja.inflate(8, 8).clip(hoja.get_rect())).copy()
            alto = altos[k % len(altos)]
            piezas.append(pygame.transform.smoothscale_by(pieza, alto / float(pieza.get_height())))
        return piezas

    def banderaBarranquilla(self, ancho: int) -> pygame.Surface:
        alto = int(ancho * 0.66)
        pieza = pygame.Surface((ancho + 8, alto + 46), pygame.SRCALPHA)
        pygame.draw.line(pieza, (125, 85, 55), (4, 0), (4, alto + 44), 5)
        tela = pygame.Rect(7, 2, ancho, alto)
        pygame.draw.rect(pieza, (215, 40, 50), tela)
        pygame.draw.rect(pieza, (250, 205, 45), tela.inflate(-int(ancho * 0.24), -int(alto * 0.24)))
        pygame.draw.rect(pieza, (40, 150, 70), tela.inflate(-int(ancho * 0.5), -int(alto * 0.5)))
        radio = alto * 0.16
        puntas = []
        for k in range(16):
            r = radio if k % 2 == 0 else radio * 0.45
            angulo = math.pi * k / 8
            puntas.append((tela.centerx + math.cos(angulo) * r, tela.centery + math.sin(angulo) * r))
        pygame.draw.polygon(pieza, (255, 250, 235), puntas)
        pygame.draw.rect(pieza, (90, 30, 35), tela, 2)
        return pieza

    def dibujoCorazon(self, tam: int, color) -> pygame.Surface:
        pieza = pygame.Surface((tam, tam), pygame.SRCALPHA)
        r = tam * 0.27
        pygame.draw.circle(pieza, color, (int(tam * 0.3), int(tam * 0.33)), int(r))
        pygame.draw.circle(pieza, color, (int(tam * 0.7), int(tam * 0.33)), int(r))
        pygame.draw.polygon(pieza, color, [(tam * 0.05, tam * 0.42), (tam * 0.95, tam * 0.42), (tam * 0.5, tam * 0.95)])
        pygame.draw.circle(pieza, (255, 255, 255, 170), (int(tam * 0.27), int(tam * 0.27)), max(2, int(tam * 0.07)))
        return pieza

    def dibujoDestello(self, tam: int, color) -> pygame.Surface:
        pieza = pygame.Surface((tam, tam), pygame.SRCALPHA)
        c = tam / 2
        puntas = []
        for k in range(8):
            r = c if k % 2 == 0 else c * 0.22
            angulo = math.pi * k / 4 - math.pi / 2
            puntas.append((c + math.cos(angulo) * r, c + math.sin(angulo) * r))
        pygame.draw.polygon(pieza, color, puntas)
        return pieza

    def prepararSonidos(self) -> None:
        self.sonidoEntrada = self.sonidoGlobo = self.sonidoFoto = self.sonidoSello = None
        if not pygame.mixer.get_init():
            return
        try:
            import numpy as np
            sr = pygame.mixer.get_init()[0]
            canales = pygame.mixer.get_init()[2]

            def armar(onda):
                datos = (np.clip(onda, -1.0, 1.0) * 32767).astype(np.int16)
                if canales > 1:
                    datos = np.column_stack([datos] * canales)
                return pygame.sndarray.make_sound(np.ascontiguousarray(datos))

            duracion = 0.42
            n = int(sr * duracion)
            t = np.linspace(0, duracion, n, False)
            ruido = np.random.default_rng(7).uniform(-1, 1, n)
            corte = 0.02 + 0.22 * np.sin(np.pi * t / duracion) ** 2
            filtrado = np.empty(n)
            previo = 0.0
            for i in range(n):
                previo += corte[i] * (ruido[i] - previo)
                filtrado[i] = previo
            filtrado /= max(1e-6, np.abs(filtrado).max())
            self.sonidoEntrada = armar(filtrado * np.sin(np.pi * t / duracion) ** 2 * 0.75)

            duracion = 0.1
            t = np.linspace(0, duracion, int(sr * duracion), False)
            frecuencia = np.geomspace(950, 360, len(t))
            fase = 2 * np.pi * np.cumsum(frecuencia) / sr
            self.sonidoGlobo = armar(np.sin(fase) * np.exp(-t * 38) * (1 - np.exp(-t * 900)) * 0.8)
        except Exception as e:
            print(f"[CharacterSelect] Sonidos procedurales no disponibles: {e}")
        for atributo, ruta in (("sonidoFoto", os.path.join("Punch", "foto.mp3")), ("sonidoSello", "curramgram_sello.mp3")):
            try:
                completo = os.path.join(self.assets.base_dir, ruta)
                if os.path.exists(completo):
                    setattr(self, atributo, pygame.mixer.Sound(completo))
            except pygame.error as e:
                print(f"[CharacterSelect] Aviso con {ruta}: {e}")

    def cortarPoses(self, hoja: pygame.Surface, cantidad: int):
        ancho = hoja.get_width() // cantidad
        alto = hoja.get_height()
        mascara = pygame.mask.from_surface(hoja, 40)
        grupos: List[List[pygame.mask.Mask]] = [[] for _ in range(cantidad)]
        for parte in mascara.connected_components(minimum=12):
            caja = parte.get_bounding_rects()[0] if parte.get_bounding_rects() else None
            if caja is None:
                continue
            if caja.w > ancho * 1.6:
                grupos = None
                break
            grupos[min(cantidad - 1, max(0, int(parte.centroid()[0] // ancho)))].append(parte)
        cuadros, desfases = [], []
        for k in range(cantidad):
            if grupos is None or not grupos[k]:
                cuadros.append(hoja.subsurface((k * ancho, 0, ancho, alto)).copy())
                desfases.append(0)
                continue
            union = pygame.mask.Mask(hoja.get_size())
            for parte in grupos[k]:
                union.draw(parte, (0, 0))
            engrosada = pygame.mask.Mask(hoja.get_size())
            for dx, dy in ((0, 0), (2, 0), (-2, 0), (0, 2), (0, -2), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                engrosada.draw(union, (dx, dy))
            cajas = engrosada.get_bounding_rects()
            izquierda = min(c.left for c in cajas)
            derecha = max(c.right for c in cajas)
            region = pygame.Rect(izquierda, 0, derecha - izquierda, alto).clip(hoja.get_rect())
            cuadro = hoja.subsurface(region).copy()
            recorte = engrosada.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(255, 255, 255, 0))
            cuadro.blit(recorte, (0, 0), area=region, special_flags=pygame.BLEND_RGBA_MIN)
            cuadros.append(cuadro)
            desfases.append(region.centerx - (k * ancho + ancho // 2))
        return cuadros, desfases

    def presentar(self, indice: int) -> None:
        cid = self.cards[indice].char_id
        if cid not in self.poses:
            return
        if self.presentacion is not None:
            viejo = self.presentacion
            if (viejo["salida"] is None and viejo["t"] >= 0.8 and viejo["cid"] != cid
                    and self.celebracion is None and (viejo["cid"], cid) in reacciones):
                self.reaccion = {"de": viejo["cid"], "texto": reacciones[(viejo["cid"], cid)], "lado": viejo["lado"], "t": 0.0}
            if viejo["salida"] is None:
                viejo["salida"] = 0.0
            self.saliendo.append(viejo)
        for gota in self.lluvia:
            if gota["muere"] is None:
                gota["muere"] = 0.0
        self.presentacion = {"cid": cid, "lado": self.ladoSiguiente, "t": 0.0, "salida": None, "flasheo": False,
                             "gestoInicio": entradaPresentacion, "globo": False,
                             "fraseIndice": 0, "fraseInicio": entradaPresentacion + 0.15}
        self.ladoSiguiente *= -1
        self.proximaGota = 0.25
        self.vitrina = 0.0
        self.ponerEscritura(False)
        self.audio.play_sfx(self.sonidoEntrada, 0.8)

    def ponerEscritura(self, activa: bool) -> None:
        if activa != self.escribiendo:
            self.escribiendo = activa
            self.audio.sonarEscritura(activa)

    def seleccionarPorEncima(self, indice: int, sonido: bool = True) -> None:
        self.selected_index = indice
        for i, card in enumerate(self.cards):
            card.is_selected = (i == indice)
        tarjeta = self.cards[indice]
        tarjeta.trigger_bounce()
        if sonido:
            self.audio.play_hover()
        self.juice_particles.emit_sparks((tarjeta.center_x, tarjeta.center_y), count=8)
        self.presentar(indice)

    def cuadroGesto(self, p: Dict[str, Any]) -> Optional[int]:
        t = p["t"] - p.get("gestoInicio", entradaPresentacion)
        if t < 0:
            return None
        for cuadro, duracion in presentaciones[p["cid"]]["gesto"]:
            if t < duracion:
                return cuadro
            t -= duracion
        return None

    def cuadroPose(self, p: Dict[str, Any]) -> int:
        if self.celebracion is not None and p is self.presentacion:
            return 5
        gesto = self.cuadroGesto(p)
        if gesto is not None:
            return gesto
        return 1 if (p["t"] + 0.7) % 2.9 < 0.13 else 0

    def actualizarPresentacion(self, dt: float) -> None:
        self.flashPantalla = max(0.0, self.flashPantalla - dt * 3.0)
        self.actualizarLluvia(dt)
        self.actualizarCelebracion(dt)
        self.actualizarVitrina(dt)
        self.actualizarFrase()
        self.actualizarAmbiente(dt)
        for p in self.saliendo:
            p["t"] += dt
            p["salida"] += dt
        self.saliendo = [p for p in self.saliendo if p["salida"] < salidaPresentacion]
        p = self.presentacion
        if p is None:
            return
        p["t"] += dt
        if p["salida"] is not None:
            p["salida"] += dt
            if p["salida"] >= salidaPresentacion:
                self.presentacion = None
            return
        if p["cid"] == "valdiri" and self.cuadroGesto(p) == 3 and not p["flasheo"] and self.celebracion is None:
            p["flasheo"] = True
            self.flashPantalla = 1.0
            self.audio.play_sfx(self.sonidoFoto, 0.8)
        duracion = sum(d for _, d in presentaciones[p["cid"]]["gesto"]) + presentaciones[p["cid"]].get("pausa", 5.0)
        if p["t"] - p["gestoInicio"] >= duracion:
            p["gestoInicio"] = p["t"]
            p["flasheo"] = False
            if len(presentaciones[p["cid"]].get("frases", [])) > 1:
                p["fraseIndice"] += 1
                p["fraseInicio"] = p["t"] + 0.15
                p["globo"] = False

    def dibujarPresentacion(self, surface: pygame.Surface) -> None:
        activos = list(self.saliendo)
        if self.presentacion is not None:
            activos.append(self.presentacion)
        if not activos:
            return
        nivel = 0.0
        for p in activos:
            if p["salida"] is None:
                nivel = max(nivel, min(1.0, p["t"] / 0.3))
            else:
                nivel = max(nivel, 1.0 - p["salida"] / salidaPresentacion)
        self.veloPresentacion.fill((int(self.tinte[0]), int(self.tinte[1]), int(self.tinte[2]), int(180 * nivel)))
        if self.presentacion is not None:
            self.dibujarRayos(self.veloPresentacion, self.presentacion, nivel)
        surface.blit(self.veloPresentacion, (0, 0))
        self.dibujarLlamado(surface)
        self.dibujarLluvia(surface)
        for p in activos:
            self.dibujarPersonajeGrande(surface, p)
        self.dibujarReaccion(surface)
        if self.flashPantalla > 0:
            self.veloPresentacion.fill((255, 255, 255, int(200 * self.flashPantalla)))
            surface.blit(self.veloPresentacion, (0, 0))

    def dibujarPersonajeGrande(self, surface: pygame.Surface, p: Dict[str, Any]) -> None:
        cid = p["cid"]
        config = next(c for c in CHARACTER_CATALOG if c["id"] == cid)
        color = config["theme_color"]
        izquierda = p["lado"] < 0
        haciaDentro = 1 if izquierda else -1
        opacidad = 1.0 if p["salida"] is None else max(0.0, 1.0 - p["salida"] / salidaPresentacion)

        numeroCuadro = self.cuadroPose(p)
        cuadro = self.poses[cid][numeroCuadro]
        desfase = self.desfasesPose.get(cid, [0] * 6)[numeroCuadro]
        bajada = max(-18.0, (1.0 - salidaRebote(p["t"] / entradaPresentacion)) * 1100)
        if p["salida"] is not None:
            bajada = max(bajada, (p["salida"] / salidaPresentacion) ** 2 * 1100)
        centroX = (380 if izquierda else 1540) + math.sin(p["t"] * 1.7) * 12
        respira = math.sin(p["t"] * 2.6) * 5
        if self.celebracion is not None and p is self.presentacion:
            tc = self.celebracion["t"]
            respira -= abs(math.sin(tc * 9.0)) * 36 * math.exp(-tc * 1.2)
        caja = cuadro.get_rect(midbottom=(int(centroX + desfase), int(self.screen_h + 70 + respira + bajada)))
        surface.blit(cuadro, caja)
        caja = caja.move(-desfase, 0)
        if self.celebracion is not None and p is self.presentacion:
            self.dibujarEstrellas(surface, (int(centroX), 560), self.celebracion["t"])

        if p["t"] > 0.3:
            aparicion = salidaRebote((p["t"] - 0.3) / 0.45)
            if cid not in self.nombresGrandes:
                self.nombresGrandes[cid] = self.nombreConPlaca(CHARACTER_DISPLAY_NAMES.get(cid, config["name"]), color)
            if aparicion >= 1.0:
                clave = ("inclinado", cid, haciaDentro)
                if clave not in self.nombresGrandes:
                    self.nombresGrandes[clave] = pygame.transform.rotozoom(self.nombresGrandes[cid], 3 * haciaDentro, 1.0)
                latido = 1.0 + 0.09 * math.sin((p["t"] - 0.75) * 3.4)
                base = self.conDestello(self.nombresGrandes[clave], (p["t"] - 0.75) % 3.0 / 0.9)
                nombre = pygame.transform.smoothscale_by(base, latido)
            else:
                nombre = pygame.transform.rotozoom(self.nombresGrandes[cid], 3 * haciaDentro, max(0.05, aparicion))
            nombre.set_alpha(int(255 * opacidad))
            centroNombre = (1190 if izquierda else 730, 595)
            surface.blit(nombre, nombre.get_rect(center=centroNombre))

            avance = min(1.0, max(0.0, (p["t"] - 0.5) / 1.2))
            avance = 1 - (1 - avance) ** 3
            cifra = formatoSeguidores(CHARACTER_BASE_FOLLOWERS.get(cid, 0) * avance)
            clave = ("seguidores", cid, cifra)
            if clave not in self.nombresGrandes:
                self.nombresGrandes[clave] = self.textoContorno(self.fuenteSeguidores, f"{cifra} seguidores", (255, 255, 255), self.colorOscuro(color, 0.4), 3)
            seguidores = self.nombresGrandes[clave]
            seguidores.set_alpha(int(255 * opacidad * min(1.0, aparicion)))
            surface.blit(seguidores, seguidores.get_rect(center=(centroNombre[0], 765)))

        tiempoFrase = p["t"] - p.get("fraseInicio", entradaPresentacion + 0.15)
        celebrando = self.celebracion is not None and p is self.presentacion
        if tiempoFrase > 0 and self.globoFrase is not None and not celebrando:
            punta = (int(centroX + haciaDentro * 175), caja.top + int(altoPresentacion * 0.3))
            self.dibujarGlobo(surface, self.fraseActual(p), tiempoFrase, punta, not izquierda, opacidad)

    def dibujarEstrellas(self, surface: pygame.Surface, centro: Tuple[int, int], tiempo: float) -> None:
        estrella = getattr(self, "estrellaSeleccion", None)
        if estrella is None:
            return
        for k in range(11):
            angulo = -math.pi - 0.45 + k * (math.pi + 0.9) / 10 + math.sin(tiempo * 0.8 + k) * 0.04
            radioX = 320 * (1 + 0.1 * (k % 2))
            radioY = 450 * (1 + 0.06 * (k % 3))
            punto = (centro[0] + math.cos(angulo) * radioX, centro[1] + 40 + math.sin(angulo) * radioY)
            inicio = k * 0.06
            if tiempo < inicio:
                continue
            aparece = salidaRebote((tiempo - inicio) / 0.3)
            titila = 0.55 + 0.45 * abs(math.sin(tiempo * 5.0 + k * 1.7))
            escala = max(0.05, aparece * titila * (0.55 + 0.45 * ((k * 7) % 5) / 4))
            giro = math.sin(tiempo * 3 + k) * 18
            pieza = pygame.transform.rotozoom(estrella, giro, escala)
            surface.blit(pieza, pieza.get_rect(center=(int(punto[0]), int(punto[1]))))

    def conDestello(self, base: pygame.Surface, avance: float) -> pygame.Surface:
        if not 0.0 <= avance < 1.0:
            return base
        w, h = base.get_size()
        capa = pygame.Surface((w, h), pygame.SRCALPHA)
        centro = (1.0 - avance) * (w * 1.5) - w * 0.25
        inclinacion = h * 0.45
        fuerza = math.sin(avance * math.pi)
        pasos = 9
        for k in range(pasos):
            ancho = 110 * (1 - k / pasos) + 14
            gris = int(120 * fuerza * ((k + 1) / pasos) ** 1.4)
            puntas = [(centro - ancho / 2 + inclinacion / 2, 0), (centro + ancho / 2 + inclinacion / 2, 0),
                      (centro + ancho / 2 - inclinacion / 2, h), (centro - ancho / 2 - inclinacion / 2, h)]
            pygame.draw.polygon(capa, (gris, gris, gris, 255), puntas)
        brillante = base.copy()
        brillante.blit(capa, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return brillante

    def fraseActual(self, p: Dict[str, Any]) -> str:
        datos = presentaciones[p["cid"]]
        frases = datos.get("frases") or [datos["frase"]]
        return frases[p.get("fraseIndice", 0) % len(frases)]

    def dibujarGlobo(self, surface: pygame.Surface, frase: str, tiempo: float, punta: Tuple[int, int],
                     voltear: bool, opacidad: float) -> None:
        anchoTexto = self.fuenteFrase.size(frase)[0]
        if not hasattr(self, "cacheGlobos"):
            self.cacheGlobos = {}
        base = self.cacheGlobos.get("base")
        if base is None:
            base = pygame.transform.smoothscale_by(self.globoFrase, 190 / float(self.globoFrase.get_height()))
            self.cacheGlobos["base"] = base
        ancho = max(base.get_width(), anchoTexto + 150)
        vacio = self.cacheGlobos.get((frase, voltear))
        if vacio is None:
            izquierdo = int(base.get_width() * 0.32)
            derecho = int(base.get_width() * 0.3)
            vacio = pygame.Surface((ancho, base.get_height()), pygame.SRCALPHA)
            vacio.blit(base.subsurface((0, 0, izquierdo, base.get_height())), (0, 0))
            centro = base.subsurface((izquierdo, 0, base.get_width() - izquierdo - derecho, base.get_height()))
            vacio.blit(pygame.transform.smoothscale(centro, (ancho - izquierdo - derecho, base.get_height())), (izquierdo, 0))
            vacio.blit(base.subsurface((base.get_width() - derecho, 0, derecho, base.get_height())), (ancho - derecho, 0))
            if voltear:
                vacio = pygame.transform.flip(vacio, True, False)
            self.cacheGlobos[(frase, voltear)] = vacio
        globo = vacio.copy()
        visibles = frase[:int(tiempo * 30)]
        if visibles:
            letras = self.fuenteFrase.render(visibles, True, (90, 50, 36))
            caja = pygame.Rect(0, 0, anchoTexto, letras.get_height())
            caja.center = (ancho // 2, int(globo.get_height() * 0.38))
            globo.blit(letras, letras.get_rect(midleft=caja.midleft))
        escala = max(0.05, salidaRebote(tiempo / 0.3))
        if escala != 1.0:
            globo = pygame.transform.smoothscale_by(globo, escala)
        globo.set_alpha(int(255 * opacidad))
        desdeBorde = int(base.get_width() * 0.11 * escala)
        caja = globo.get_rect(bottom=punta[1])
        if voltear:
            caja.right = punta[0] + desdeBorde
        else:
            caja.left = punta[0] - desdeBorde
        surface.blit(globo, caja)

    def textoContorno(self, fuente, texto: str, color, borde, grosor: int) -> pygame.Surface:
        cuerpo = fuente.render(texto, True, color)
        contorno = fuente.render(texto, True, borde)
        lienzo = pygame.Surface((cuerpo.get_width() + grosor * 2, cuerpo.get_height() + grosor * 2), pygame.SRCALPHA)
        for grados in range(0, 360, 30):
            lienzo.blit(contorno, (grosor + round(math.cos(math.radians(grados)) * grosor),
                                   grosor + round(math.sin(math.radians(grados)) * grosor)))
        lienzo.blit(cuerpo, (grosor, grosor))
        return lienzo

    def colorOscuro(self, color, factor: float) -> Tuple[int, int, int]:
        return tuple(int(c * factor) for c in color)

    def textoGrande(self, texto: str, color, fuente=None) -> pygame.Surface:
        fuente = fuente or self.fuenteNombreGrande
        frente = self.textoContorno(fuente, texto, color, self.colorOscuro(color, 0.5), 7)
        sombra = self.textoContorno(fuente, texto, self.colorOscuro(color, 0.25), self.colorOscuro(color, 0.25), 7)
        sombra.set_alpha(150)
        lienzo = pygame.Surface((frente.get_width(), frente.get_height() + 10), pygame.SRCALPHA)
        lienzo.blit(sombra, (0, 10))
        lienzo.blit(frente, (0, 0))
        return lienzo

    def nombreConPlaca(self, texto: str, color) -> pygame.Surface:
        letras = self.textoGrande(texto, color)
        ancho, alto = letras.get_width() + 90, int(letras.get_height() * 0.86)
        factor = 4
        grande = pygame.Surface(((ancho + 12) * factor, (alto + 14) * factor), pygame.SRCALPHA)
        caja = pygame.Rect(0, 0, ancho * factor, alto * factor)
        radio = alto * factor // 3
        pygame.draw.rect(grande, (*self.colorOscuro(color, 0.18), 120), caja.move(8 * factor, 12 * factor), border_radius=radio)
        pygame.draw.rect(grande, (*self.colorOscuro(color, 0.4), 240), caja, border_radius=radio)
        placa = pygame.transform.smoothscale(grande, (ancho + 12, alto + 14))
        placa.blit(letras, letras.get_rect(center=(ancho // 2, alto // 2 + 2)))
        return placa

    def actualizarFrase(self) -> None:
        p = self.presentacion
        activa = False
        if p is not None and p["salida"] is None and self.celebracion is None:
            tiempo = p["t"] - p["fraseInicio"]
            if tiempo > 0 and not p["globo"]:
                p["globo"] = True
                self.audio.play_sfx(self.sonidoGlobo, 0.7)
            activa = 0 < tiempo and int(tiempo * 30) < len(self.fraseActual(p))
        self.ponerEscritura(activa)

    def actualizarLluvia(self, dt: float) -> None:
        p = self.presentacion
        if p is not None and p["salida"] is None and self.piezasLluvia.get(p["cid"]):
            self.proximaGota -= dt
            if self.proximaGota <= 0:
                self.proximaGota = random.uniform(0.16, 0.3)
                self.soltarGota(p)
        vivas = []
        for gota in self.lluvia:
            gota["t"] += dt
            gota["y"] -= gota["vy"] * dt
            if gota["giro"]:
                gota["angulo"] = gota["anguloBase"] + math.sin(gota["t"] * 1.9 + gota["fase"]) * gota["giro"]
            if gota["muere"] is not None:
                gota["muere"] += dt
            if gota["y"] > -120 and (gota["muere"] is None or gota["muere"] < 0.45):
                vivas.append(gota)
        self.lluvia = vivas

    def soltarGota(self, p: Dict[str, Any]) -> None:
        giro = 0.0 if p["cid"] == "westcol" else random.choice((-1, 1)) * random.uniform(8, 18)
        pieza = random.choice(self.piezasLluvia[p["cid"]])
        mitad = pieza.get_width() / 2 + 20
        x = None
        for _ in range(8):
            prueba = random.uniform(mitad, self.screen_w - mitad)
            libre = all(abs(prueba - g["x"]) > mitad + g["pieza"].get_width() / 2
                        or g["y"] < self.screen_h - g["pieza"].get_height() - pieza.get_height() - 10
                        for g in self.lluvia)
            if libre:
                x = prueba
                break
        if x is None:
            return
        self.lluvia.append({
            "pieza": pieza,
            "x": x,
            "y": self.screen_h + 60,
            "vy": random.uniform(110, 190),
            "fase": random.uniform(0, 6.28),
            "amplitud": random.uniform(10, 26),
            "giro": giro,
            "anguloBase": random.uniform(-10, 10) if giro else 0.0,
            "angulo": 0.0,
            "t": 0.0,
            "muere": None,
        })

    def dibujarLluvia(self, surface: pygame.Surface) -> None:
        for gota in self.lluvia:
            alfa = min(1.0, gota["t"] / 0.4)
            if gota["y"] < 260:
                alfa *= max(0.0, (gota["y"] + 120) / 380.0)
            if gota["muere"] is not None:
                alfa *= max(0.0, 1.0 - gota["muere"] / 0.45)
            if alfa <= 0.01:
                continue
            pieza = gota["pieza"]
            if gota["angulo"]:
                pieza = pygame.transform.rotate(pieza, gota["angulo"])
            pieza.set_alpha(int(235 * alfa))
            x = gota["x"] + math.sin(gota["t"] * 1.6 + gota["fase"]) * gota["amplitud"]
            surface.blit(pieza, pieza.get_rect(center=(int(x), int(gota["y"]))))

    def celebrar(self) -> None:
        if self.celebracion is not None:
            return
        if not self.poses:
            self._on_confirm_selection()
            return
        cid = self.cards[self.selected_index].char_id
        if self.presentacion is None or self.presentacion["cid"] != cid or self.presentacion["salida"] is not None:
            self.presentar(self.selected_index)
        disenos = [((330, 260), "circulo", 175, "dorado"), ((1600, 240), "circulo", 190, "rosa"),
                   ((960, 150), "corazon", 165, "turquesa"), ((620, 430), "circulo", 160, "morado"),
                   ((1320, 410), "corazon", 160, "rojo")]
        marca = random.random()
        fuegos = [{
            "centro": centro,
            "forma": forma,
            "escala": escala,
            "paleta": paleta,
            "t": -i * 0.22,
            "desdeY": self.screen_h + 70,
            "clave": ("seleccion", marca, i),
        } for i, (centro, forma, escala, paleta) in enumerate(disenos)]
        self.celebracion = {"t": 0.0, "fuegos": fuegos, "golpe": False, "listo": False}
        self.ponerEscritura(False)
        self.flashPantalla = 0.6
        self.audio.play_win()

    def posicionSello(self) -> Tuple[int, int]:
        p = self.presentacion
        izquierda = p is None or p["lado"] < 0
        return (1190, 395) if izquierda else (730, 395)

    def actualizarCelebracion(self, dt: float) -> None:
        c = self.celebracion
        if c is None:
            return
        from effects.juice_particles import subidaFuego
        from effects.fuegos_sonido import avisar_estallido
        c["t"] += dt
        for fuego in c["fuegos"]:
            fuego["t"] += dt
            avisar_estallido(fuego["clave"], fuego["t"], subidaFuego)
        if c["t"] >= 0.35 and not c["golpe"]:
            c["golpe"] = True
            self.audio.play_sfx(self.sonidoSello, 1.0)
            self.juice_particles.emit_sparks(self.posicionSello(), count=30)
        umbral = 0.25 if getattr(self, "chosen_mode", "historia") == "historia" else 1.5
        if c["t"] >= umbral and not c["listo"]:
            c["listo"] = True
            self._on_confirm_selection()
        if c["t"] >= 9.0:
            self.celebracion = None

    def dibujarCelebracion(self, surface: pygame.Surface) -> None:
        c = self.celebracion
        if c is None:
            return
        self.dibujarFuegosCelebracion(surface, c["fuegos"], 0)
        if c["t"] > 0.1:
            if self.selloListo is None:
                self.selloListo = self.textoGrande("¡LISTO!", (255, 214, 70), self.fuenteListo)
            avance = min(1.0, (c["t"] - 0.1) / 0.25)
            if avance < 1.0:
                escala = 1.0 + 1.8 * (1.0 - avance) ** 2
            else:
                escala = 1.0 + 0.06 * math.sin((c["t"] - 0.35) * 14) * math.exp(-(c["t"] - 0.35) * 4)
            if c["t"] > 1.2:
                if getattr(self, "selloQuieto", None) is None:
                    self.selloQuieto = pygame.transform.rotozoom(self.selloListo, -8, 1.0)
                sello = self.selloQuieto
            else:
                sello = pygame.transform.rotozoom(self.selloListo, -8, escala)
            sello.set_alpha(int(255 * min(1.0, avance * 1.5)))
            surface.blit(sello, sello.get_rect(center=self.posicionSello()))

    def dibujarFuegosCelebracion(self, surface: pygame.Surface, fuegos: List[Dict[str, Any]], desplazamiento: int) -> None:
        from effects.juice_particles import dibujarFuego, puntosFigura, paletasFuego
        for fuego in fuegos:
            if fuego["t"] < 0.0:
                continue
            centro = (fuego["centro"][0], fuego["centro"][1] + desplazamiento)
            dibujarFuego(surface, centro, puntosFigura(fuego["forma"]), fuego["escala"], fuego["t"],
                         paletasFuego[fuego["paleta"]], fuego["desdeY"] + desplazamiento, tamChispa=5)

    def actualizarVitrina(self, dt: float) -> None:
        if self.celebracion is not None or not self.poses:
            return
        self.quieto += dt
        self.vitrina += dt
        if self.quieto < 10.0:
            return
        if self.presentacion is None or self.vitrina >= 6.5:
            self.seleccionarPorEncima((self.selected_index + 1) % len(self.cards), sonido=False)

    def colorClaro(self, color) -> Tuple[int, int, int]:
        return tuple(int(c + (255 - c) * 0.55) for c in color)

    def colorDe(self, cid: str) -> Tuple[int, int, int]:
        for config in CHARACTER_CATALOG:
            if config["id"] == cid:
                return config["theme_color"]
        return (200, 200, 200)

    def crearHalo(self, radio: int, color) -> pygame.Surface:
        halo = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
        pasos = 30
        for i in range(pasos, 0, -1):
            alfa = int(95 * (1.0 - i / pasos) ** 1.6)
            pygame.draw.circle(halo, (*color, alfa), (radio, radio), int(radio * i / pasos))
        return halo

    def caraCircular(self, cuadro: pygame.Surface, radio: int) -> pygame.Surface:
        import numpy as np
        alfa = pygame.surfarray.array_alpha(cuadro)
        filas = np.nonzero((alfa > 100).any(axis=0))[0]
        arriba = int(filas.min()) if len(filas) else 0
        franja = alfa[:, arriba:arriba + int(cuadro.get_height() * 0.25)]
        columnas = np.nonzero((franja > 100).any(axis=1))[0]
        centroX = int(columnas.mean()) if len(columnas) else cuadro.get_width() // 2
        lado = min(cuadro.get_width(), int(cuadro.get_height() * 0.41))
        caja = pygame.Rect(0, 0, lado, lado)
        caja.midtop = (centroX, max(0, arriba - int(lado * 0.04)))
        caja = caja.clip(cuadro.get_rect())
        cara = pygame.Surface(caja.size, pygame.SRCALPHA)
        cara.fill((255, 246, 236, 255))
        cara.blit(cuadro.subsurface(caja), (0, 0))
        cara = pygame.transform.smoothscale(cara, (radio * 2, radio * 2))
        mascara = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
        pygame.draw.circle(mascara, (255, 255, 255, 255), (radio, radio), radio)
        cara.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.circle(cara, (255, 255, 255), (radio, radio), radio, 4)
        return cara

    def actualizarAmbiente(self, dt: float) -> None:
        p = self.presentacion
        activa = p is not None and p["salida"] is None
        objetivo = [c * 0.25 for c in self.colorDe(p["cid"])] if activa else [18.0, 14.0, 26.0]
        paso = min(1.0, dt * 4.0)
        self.tinte = [a + (b - a) * paso for a, b in zip(self.tinte, objetivo)]
        if self.reaccion is not None:
            self.reaccion["t"] += dt
            if self.reaccion["t"] > 2.8:
                self.reaccion = None
        if self.llamado is not None:
            self.llamado["t"] += dt
            if self.llamado["t"] > 1.4:
                self.llamado = None
        if activa and self.celebracion is None:
            self.proximoLlamado -= dt
            if self.proximoLlamado <= 0:
                self.proximoLlamado = random.uniform(2.4, 3.6)
                opciones = [i for i, card in enumerate(self.cards) if card.char_id != p["cid"]]
                if opciones:
                    indice = random.choice(opciones)
                    self.llamado = {"i": indice, "t": 0.0, "texto": random.choice(llamadosTarjeta)}
                    self.cards[indice].trigger_bounce()

    def dibujarRayos(self, surface: pygame.Surface, p: Dict[str, Any], nivel: float) -> None:
        if p["salida"] is not None:
            nivel *= max(0.0, 1.0 - p["salida"] / salidaPresentacion)
        if nivel <= 0.01:
            return
        claro = self.colorClaro(self.colorDe(p["cid"]))
        oscuro = [int((a * 0.72 + b * 0.28)) for a, b in zip(self.tinte, claro)]
        centro = (380 if p["lado"] < 0 else 1540, 430)
        radio = 680
        giro = self.timer * 10.0
        ancho = math.radians(7)
        for k in range(12):
            a = math.radians(giro + k * 30)
            puntas = [centro, (centro[0] + math.cos(a - ancho) * radio, centro[1] + math.sin(a - ancho) * radio),
                      (centro[0] + math.cos(a + ancho) * radio, centro[1] + math.sin(a + ancho) * radio)]
            pygame.draw.polygon(surface, (*oscuro, int(160 * nivel)), puntas)
        halo = self.halos.get(p["cid"])
        if halo is not None:
            halo.set_alpha(int(255 * nivel))
            surface.blit(halo, halo.get_rect(center=centro))

    def pastillaTexto(self, letras: pygame.Surface) -> pygame.Surface:
        base = getattr(self, "globoChat", None)
        ancho = letras.get_width() + 50
        if base is not None:
            pastilla = self.estirarPastilla(base, max(ancho, base.get_height() * 2))
        else:
            pastilla = pygame.Surface((ancho, 60), pygame.SRCALPHA)
            pygame.draw.rect(pastilla, (250, 240, 228), pastilla.get_rect(), border_radius=30)
        pastilla.blit(letras, letras.get_rect(center=(pastilla.get_width() // 2, pastilla.get_height() // 2 - 1)))
        return pastilla

    def dibujarLlamado(self, surface: pygame.Surface) -> None:
        l = self.llamado
        if l is None or self.celebracion is not None or not (0 <= l["i"] < len(self.cards)):
            return
        card = self.cards[l["i"]]
        t = l["t"]
        envolvente = min(1.0, t / 0.15) * min(1.0, max(0.0, (1.4 - t) / 0.3))
        if envolvente <= 0.01:
            return
        margen = 70
        capa = pygame.Surface((card.base_width + margen * 2, card.base_height + margen * 2), pygame.SRCALPHA)
        cx, cy = card.center_x, card.center_y
        card.center_x, card.center_y = capa.get_width() // 2, capa.get_height() // 2
        try:
            card.render(capa)
        finally:
            card.center_x, card.center_y = cx, cy
        capa.set_alpha(int(235 * envolvente))
        surface.blit(capa, capa.get_rect(center=(cx, cy)))

        clave = ("llamado", l["texto"])
        if clave not in self.nombresGrandes:
            self.nombresGrandes[clave] = self.pastillaTexto(self.fuenteLlamado.render(l["texto"], True, (80, 46, 92)))
        pastilla = pygame.transform.rotozoom(self.nombresGrandes[clave], math.sin(t * 12) * 6 * math.exp(-t * 2.5),
                                             max(0.05, salidaRebote(t / 0.25)))
        pastilla.set_alpha(int(255 * envolvente))
        surface.blit(pastilla, pastilla.get_rect(midbottom=(cx, cy - card.base_height // 2 + 4)))

    def dibujarReaccion(self, surface: pygame.Surface) -> None:
        r = self.reaccion
        if r is None:
            return
        t = r["t"]
        clave = ("reaccion", r["de"], r["texto"])
        if clave not in self.nombresGrandes:
            pastilla = self.pastillaTexto(self.fuenteReaccion.render(r["texto"], True, (80, 46, 92)))
            cara = self.caras.get(r["de"])
            anchoCara = cara.get_width() + 10 if cara is not None else 0
            alto = max(pastilla.get_height(), cara.get_height() if cara is not None else 0)
            pieza = pygame.Surface((anchoCara + pastilla.get_width(), alto), pygame.SRCALPHA)
            if cara is not None:
                pieza.blit(cara, cara.get_rect(midleft=(0, alto // 2)))
            pieza.blit(pastilla, pastilla.get_rect(midleft=(anchoCara, alto // 2)))
            self.nombresGrandes[clave] = pieza
        pieza = self.nombresGrandes[clave]
        escala = max(0.05, salidaRebote(t / 0.3))
        if escala != 1.0:
            pieza = pygame.transform.smoothscale_by(pieza, escala)
        pieza.set_alpha(int(255 * min(1.0, max(0.0, (2.8 - t) / 0.4))))
        y = int(880 - min(t, 2.8) * 12)
        if r["lado"] < 0:
            surface.blit(pieza, pieza.get_rect(midleft=(40, y)))
        else:
            surface.blit(pieza, pieza.get_rect(midright=(self.screen_w - 40, y)))
