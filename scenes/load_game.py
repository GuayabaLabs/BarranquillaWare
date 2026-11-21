import math
from typing import Callable, Dict, List, Optional, Tuple
import os
import pygame

from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.settings import SettingsManager
from core.state_machine import BaseState
from effects.gl_particles import GLParticleSystem
from effects.juice_particles import JuiceParticleManager
from ui.button import UIButton
from ui.focus_nav import FocusNavigator


def render_outlined_text(
    font: pygame.font.Font,
    text: str,
    fill_color: Tuple[int, int, int],
    outline_color: Tuple[int, int, int],
    thickness: int = 2,
) -> pygame.Surface:
    """Renderiza texto con contorno nítido y limpio para botones de acuarela."""
    base = font.render(text, True, fill_color)
    edge = font.render(text, True, outline_color)
    out = pygame.Surface(
        (base.get_width() + thickness * 2, base.get_height() + thickness * 2),
        pygame.SRCALPHA,
    )
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if dx == 0 and dy == 0:
                continue
            if dx * dx + dy * dy <= thickness * thickness + 1:
                out.blit(edge, (thickness + dx, thickness + dy))
    out.blit(base, (thickness, thickness))
    return out


def _poner_borde_calcomania(imagen: pygame.Surface, grosor_blanco: int = 5, grosor_tinta: int = 2) -> pygame.Surface:
    """Añade borde blanco tipo calcomanía con línea fina de tinta café para que el sello X resalte limpio."""
    margen = grosor_blanco + grosor_tinta
    ancho, alto = imagen.get_size()
    con_borde = pygame.Surface((ancho + margen * 2, alto + margen * 2), pygame.SRCALPHA)
    silueta = pygame.mask.from_surface(imagen, 100)
    tinta = silueta.to_surface(setcolor=(86, 50, 28, 255), unsetcolor=(0, 0, 0, 0))
    blanco = silueta.to_surface(setcolor=(255, 252, 244, 255), unsetcolor=(0, 0, 0, 0))
    for capa, radio in ((tinta, margen), (blanco, grosor_blanco)):
        for grados in range(0, 360, 15):
            dx = round(math.cos(math.radians(grados)) * radio)
            dy = round(math.sin(math.radians(grados)) * radio)
            con_borde.blit(capa, (margen + dx, margen + dy))
    con_borde.blit(imagen, (margen, margen))
    return con_borde


def make_watercolor_button_surface(
    assets: AssetManager,
    plate_type: str,
    text: str,
    size: Tuple[int, int],
    font_size: int = 26,
) -> pygame.Surface:
    """Construye un botón píldora usando exclusivamente texturas de acuarela del proyecto."""
    w, h = size
    plate_map = {
        "green": ("boton_acuarela_verde.png", (255, 251, 242), (14, 76, 42)),
        "orange": ("boton_acuarela_naranja.png", (255, 251, 242), (118, 44, 10)),
        "purple": (os.path.join("Interfaz", "botonMorado.jpg"), (255, 251, 242), (66, 28, 108)),
        "red": (os.path.join("Interfaz", "botonRojo.jpg"), (255, 251, 242), (118, 22, 32)),
    }
    asset_name, fill_col, outline_col = plate_map.get(plate_type, plate_map["purple"])

    if asset_name.endswith(".jpg"):
        base_plate = assets.cargarSinFondo(asset_name, w)
        plate = pygame.transform.smoothscale(base_plate, (w, h))
    else:
        raw_plate = assets.load_cropped_surface(asset_name)
        plate = pygame.transform.smoothscale(raw_plate, (w, h))

    cur_size = font_size
    font = assets.cargarFuenteTitulo(cur_size)
    max_text_w = int(w * 0.86)
    while font.size(text)[0] > max_text_w and cur_size > 15:
        cur_size -= 1
        font = assets.cargarFuenteTitulo(cur_size)

    label_surf = render_outlined_text(font, text, fill_col, outline_col, thickness=2)
    plate.blit(label_surf, label_surf.get_rect(center=(w // 2, h // 2 - 2)))
    return plate


class StorySaveModalPanel:
    """
    Panel modal ilustrado en acuarela para 'Partida Guardada Encontrada' y 'Cargar Partida'.
    Cero rectángulos ni botones generados por código: utiliza exclusivamente assets PNG/JPG
    correlacionados con el arte oficial de BarranquillaWare.
    """

    def __init__(
        self,
        screen_w: int = 1920,
        screen_h: int = 1080,
        mode: str = "confirm",
        on_continue: Optional[Callable[[], None]] = None,
        on_new_game: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
    ) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.mode = mode  # "confirm" (ModeSelect) | "load_screen" (MainMenu -> Cargar Partida)
        self.on_continue = on_continue
        self.on_new_game = on_new_game
        self.on_cancel = on_cancel
        self.on_delete = on_delete

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()
        self.settings = SettingsManager.get_instance()

        # Marco horizontal de pergamino acuarela (1320x820 centrado, proporción nativa ~1.609:1)
        self.frame_w = 1320
        self.frame_h = 820
        self.frame_rect = pygame.Rect(
            (self.screen_w - self.frame_w) // 2,
            (self.screen_h - self.frame_h) // 2,
            self.frame_w,
            self.frame_h,
        )
        raw_frame = self.assets.load_cropped_surface("recuadro_partida_guardada.png")
        self.frame_surf = pygame.transform.smoothscale(raw_frame, (self.frame_w, self.frame_h))

        # Tarjeta interior amplia con marco dorado/morado acuarela (sin choque floral)
        raw_slot = self.assets.load_cropped_surface("tarjeta_slot_partida.png")
        self.slot_w = 896
        self.slot_h = 318
        self.slot_surf = pygame.transform.smoothscale(raw_slot, (self.slot_w, self.slot_h))
        self.slot_rect = pygame.Rect(0, 0, self.slot_w, self.slot_h)
        self.slot_rect.center = (self.frame_rect.left + 642, self.frame_rect.top + 383)

        # Separador floral y retratos
        raw_sep = self.assets.load_cropped_surface("separador_floral_modal.png")
        sep_w = 540
        sep_h = max(18, int(sep_w * raw_sep.get_height() / max(1, raw_sep.get_width())))
        self.sep_surf = pygame.transform.smoothscale(raw_sep, (sep_w, sep_h))

        self._portrait_cache: Dict[str, pygame.Surface] = {}

        # Tipografías unificadas de Coaster (IndieFlower-Regular.ttf)
        self.font_title = self.assets.cargarFuenteCuento(42)
        self.font_sub = self.assets.cargarFuenteCuento(25)
        self.font_char = self.assets.cargarFuenteCuento(33)
        self.font_stat = self.assets.cargarFuenteCuento(24)
        self.font_meta = self.assets.cargarFuenteCuento(20)

        # Botón de cierre X en alta resolución con borde tipo calcomanía nítido en la esquina superior derecha
        close_base = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonX.jpg"), 92)
        close_surf = _poner_borde_calcomania(close_base, grosor_blanco=5, grosor_tinta=2)
        self.btn_close = UIButton(
            (self.frame_rect.left + 1204, self.frame_rect.top + 106),
            close_surf,
            on_click=self._handle_cancel,
        )

        self.delete_confirm_timer: float = 0.0
        self._load_btn_size: Tuple[int, int] = (286, 60)
        self._load_btn_font_size: int = 26
        self.buttons: List[UIButton] = []
        self.btn_continue: Optional[UIButton] = None
        self.btn_new: Optional[UIButton] = None
        self.btn_cancel: Optional[UIButton] = None
        self.btn_delete: Optional[UIButton] = None

        self.refresh()

    def _fit_uniform_button_font_size(
        self,
        labels: List[str],
        btn_w: int,
        start_size: int = 25,
        min_size: int = 16,
    ) -> int:
        max_text_w = int(btn_w * 0.86)
        size = start_size
        while size > min_size:
            font = self.assets.cargarFuenteTitulo(size)
            if all(font.size(lbl)[0] <= max_text_w for lbl in labels):
                return size
            size -= 1
        return size

    def _get_portrait(self, char_id: str, has_save: bool) -> pygame.Surface:
        clean_id = (char_id or "westcol").strip().lower()
        key = clean_id if has_save else "_empty_paloma"
        if key in self._portrait_cache:
            return self._portrait_cache[key]

        if has_save:
            candidates = [
                f"{clean_id}_seleccion_personaje.png",
                "katherine_seleccion_personaje.png" if clean_id == "mujer" else "westcol_seleccion_personaje.png",
                "westcol_seleccion_personaje.png",
                "paloma_parada_seleccion_modo.png",
            ]
            max_w, max_h = 218, 266
        else:
            candidates = ["paloma_parada_seleccion_modo.png"]
            max_w, max_h = 228, 240

        surf: Optional[pygame.Surface] = None
        for fname in candidates:
            try:
                raw = self.assets.load_cropped_surface(fname, alpha_threshold=20)
                scale = min(max_w / max(1, raw.get_width()), max_h / max(1, raw.get_height()))
                nw = max(24, int(raw.get_width() * scale))
                nh = max(24, int(raw.get_height() * scale))
                surf = pygame.transform.smoothscale(raw, (nw, nh))
                break
            except Exception:
                continue

        if surf is None:
            surf = pygame.Surface((120, 160), pygame.SRCALPHA)

        self._portrait_cache[key] = surf
        return surf

    def refresh(self) -> None:
        """Reconstruye los botones según si existe o no una partida guardada activa."""
        summary = self.settings.get_story_save_summary()
        has_save = summary["has_save"]
        self.delete_confirm_timer = 0.0

        fl, ft = self.frame_rect.left, self.frame_rect.top

        if has_save:
            if self.mode == "load_screen":
                btn_size = self._load_btn_size
                btn_fs = self._fit_uniform_button_font_size(
                    ["Continuar Partida", "Nueva Partida", "Borrar Partida", "Volver", "¿Confirmar?"],
                    btn_size[0],
                    start_size=26,
                )
                self._load_btn_font_size = btn_fs
                cont_surf = make_watercolor_button_surface(
                    self.assets, "green", "Continuar Partida", btn_size, font_size=btn_fs
                )
                new_surf = make_watercolor_button_surface(
                    self.assets, "orange", "Nueva Partida", btn_size, font_size=btn_fs
                )
                del_surf = make_watercolor_button_surface(
                    self.assets, "red", "Borrar Partida", btn_size, font_size=btn_fs
                )
                back_surf = make_watercolor_button_surface(
                    self.assets, "purple", "Volver", btn_size, font_size=btn_fs
                )
                col_l, col_r = fl + 460, fl + 774
                row_1, row_2 = ft + 578, ft + 648
                self.btn_continue = UIButton((col_l, row_1), cont_surf, on_click=self._handle_continue)
                self.btn_new = UIButton((col_r, row_1), new_surf, on_click=self._handle_new)
                self.btn_delete = UIButton((col_l, row_2), del_surf, on_click=self._handle_delete)
                self.btn_cancel = UIButton((col_r, row_2), back_surf, on_click=self._handle_cancel)
                self.buttons = [self.btn_continue, self.btn_new, self.btn_delete, self.btn_cancel, self.btn_close]
            else:
                btn_size = (268, 68)
                btn_fs = self._fit_uniform_button_font_size(
                    ["Continuar Partida", "Nueva Partida", "Cancelar"],
                    btn_size[0],
                    start_size=26,
                )
                cont_surf = make_watercolor_button_surface(
                    self.assets, "green", "Continuar Partida", btn_size, font_size=btn_fs
                )
                new_surf = make_watercolor_button_surface(
                    self.assets, "orange", "Nueva Partida", btn_size, font_size=btn_fs
                )
                cancel_surf = make_watercolor_button_surface(
                    self.assets, "purple", "Cancelar", btn_size, font_size=btn_fs
                )
                row_y = ft + 584
                self.btn_continue = UIButton((fl + 276, row_y), cont_surf, on_click=self._handle_continue)
                self.btn_new = UIButton((fl + 560, row_y), new_surf, on_click=self._handle_new)
                self.btn_delete = None
                self.btn_cancel = UIButton((fl + 844, row_y), cancel_surf, on_click=self._handle_cancel)
                self.buttons = [self.btn_continue, self.btn_new, self.btn_cancel, self.btn_close]
        else:
            btn_size = (284, 68)
            btn_fs = self._fit_uniform_button_font_size(
                ["Iniciar Historia", "Volver"],
                btn_size[0],
                start_size=27,
            )
            start_surf = make_watercolor_button_surface(
                self.assets, "green", "Iniciar Historia", btn_size, font_size=btn_fs
            )
            back_surf = make_watercolor_button_surface(
                self.assets, "purple", "Volver", btn_size, font_size=btn_fs
            )
            row_y = ft + 596
            self.btn_continue = UIButton((fl + 486, row_y), start_surf, on_click=self._handle_new)
            self.btn_new = None
            self.btn_delete = None
            self.btn_cancel = UIButton((fl + 798, row_y), back_surf, on_click=self._handle_cancel)
            self.buttons = [self.btn_continue, self.btn_cancel, self.btn_close]

    def _handle_continue(self) -> None:
        if self.on_continue:
            self.on_continue()

    def _handle_new(self) -> None:
        if self.on_new_game:
            self.on_new_game()

    def _handle_cancel(self) -> None:
        if self.on_cancel:
            self.on_cancel()

    def _handle_delete(self) -> None:
        if self.delete_confirm_timer <= 0.0:
            self.delete_confirm_timer = 3.2
            if self.btn_delete is not None:
                confirm_surf = make_watercolor_button_surface(
                    self.assets, "red", "¿Confirmar?", self._load_btn_size, font_size=self._load_btn_font_size
                )
                self.btn_delete.normal_sprite = confirm_surf
            return
        self.delete_confirm_timer = 0.0
        if self.on_delete:
            self.on_delete()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._handle_cancel()
            return True

        if not hasattr(self, "focus_nav"):
            self.focus_nav = FocusNavigator(lambda: self.buttons, default_index=0)
        if self.focus_nav.handle_event(event):
            return True

        for btn in self.buttons:
            consumed = btn.handle_event(event)
            if consumed and event.type != pygame.MOUSEMOTION:
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.frame_rect.collidepoint(event.pos):
                self._handle_cancel()
                return True
        return False

    def update(self, dt: float) -> None:
        if self.delete_confirm_timer > 0.0:
            self.delete_confirm_timer = max(0.0, self.delete_confirm_timer - dt)
            if self.delete_confirm_timer == 0.0 and self.btn_delete is not None:
                self.btn_delete.normal_sprite = make_watercolor_button_surface(
                    self.assets, "red", "Borrar Partida", self._load_btn_size, font_size=self._load_btn_font_size
                )
        for btn in self.buttons:
            btn.update(dt)

    def _render_fitted_text(
        self,
        surface: pygame.Surface,
        text: str,
        start_size: int,
        color: Tuple[int, int, int],
        max_w: int,
        min_size: int = 14,
        titulo: bool = False,
    ) -> pygame.Surface:
        cargar = self.assets.cargarFuenteTitulo if titulo else self.assets.cargarFuenteCuento
        size = start_size
        font = cargar(size)
        while font.size(text)[0] > max_w and size > min_size:
            size -= 1
            font = cargar(size)
        return font.render(text, True, color)

    def render(self, surface: pygame.Surface, draw_backdrop: bool = True) -> None:
        if draw_backdrop:
            overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            overlay.fill((22, 16, 36, 175))
            surface.blit(overlay, (0, 0))

        surface.blit(self.frame_surf, self.frame_rect.topleft)

        summary = self.settings.get_story_save_summary()
        has_save = summary["has_save"]

        fl, ft = self.frame_rect.left, self.frame_rect.top
        # Centro compartido de cabecera libre de cayenas superiores y del sello X
        header_cx = fl + 690

        if self.mode == "load_screen":
            title_txt = "CARGAR PARTIDA" if has_save else "HISTORIAL DE PARTIDA"
            sub_txt = (
                "Retoma tu recorrido por Barranquilla o gestiona tu progreso guardado."
                if has_save
                else "Consulta aquí tu avance guardado en el Modo Historia."
            )
        else:
            title_txt = "PARTIDA GUARDADA ENCONTRADA"
            sub_txt = "¿Deseas continuar tu recorrido por Barranquilla o empezar desde cero?"

        t_surf = self._render_fitted_text(surface, title_txt, 42, (84, 52, 112), max_w=700, titulo=True)
        t_sh = self._render_fitted_text(surface, title_txt, 42, (255, 255, 255), max_w=700, titulo=True)
        surface.blit(t_sh, t_sh.get_rect(center=(header_cx + 1, ft + 162)))
        surface.blit(t_surf, t_surf.get_rect(center=(header_cx, ft + 160)))

        s_surf = self._render_fitted_text(surface, sub_txt, 25, (112, 82, 134), max_w=840)
        surface.blit(s_surf, s_surf.get_rect(center=(header_cx, ft + 202)))

        # Tarjeta interior de ficha de partida en acuarela
        surface.blit(self.slot_surf, self.slot_rect.topleft)

        portrait = self._get_portrait(summary["character_id"], has_save)
        surface.blit(portrait, portrait.get_rect(center=(self.slot_rect.left + 132, self.slot_rect.centery)))

        info_left = self.slot_rect.left + 252
        info_right = self.slot_rect.right - 34
        info_w = info_right - info_left
        info_cx = (info_left + info_right) // 2

        if has_save:
            name_surf = self._render_fitted_text(
                surface, f"Explorador: {summary['character_name']}", 33, (76, 48, 102), max_w=365
            )
            prog_surf = self._render_fitted_text(
                surface,
                f"Retos: {summary['levels_cleared']}/{summary['total_levels']} distritos",
                24,
                (30, 128, 68),
                max_w=230,
            )
            surface.blit(name_surf, name_surf.get_rect(midleft=(info_left, self.slot_rect.top + 48)))
            surface.blit(prog_surf, prog_surf.get_rect(midright=(info_right, self.slot_rect.top + 48)))

            dest_surf = self._render_fitted_text(
                surface,
                f"Próximo destino: {summary['next_district']}",
                24,
                (118, 72, 42),
                max_w=info_w,
            )
            surface.blit(dest_surf, dest_surf.get_rect(midleft=(info_left, self.slot_rect.top + 92)))

            surface.blit(self.sep_surf, self.sep_surf.get_rect(center=(info_cx, self.slot_rect.top + 128)))

            row_metrics = (
                f"Seguidores: {summary['followers_text']}   •   "
                f"Likes: {summary['likes_text']}   •   "
                f"Puntos: {summary['high_score']}"
            )
            m_surf = self._render_fitted_text(surface, row_metrics, 24, (168, 86, 36), max_w=info_w)
            surface.blit(m_surf, m_surf.get_rect(midleft=(info_left, self.slot_rect.top + 168)))

            row_extra = (
                f"Logros: {summary['trophies_count']}/{summary['trophies_total']}   •   "
                f"Clima: {summary['weather_label']}"
            )
            e_surf = self._render_fitted_text(surface, row_extra, 23, (88, 56, 120), max_w=info_w)
            surface.blit(e_surf, e_surf.get_rect(midleft=(info_left, self.slot_rect.top + 212)))

            row_saved = (
                f"Último guardado: {summary['saved_at']} ({summary['save_source_label']})  |  "
                f"Auto-guardado activo"
            )
            sv_surf = self._render_fitted_text(surface, row_saved, 20, (124, 96, 74), max_w=info_w)
            surface.blit(sv_surf, sv_surf.get_rect(midleft=(info_left, self.slot_rect.top + 258)))
        else:
            empty_title = self._render_fitted_text(
                surface, "AÚN NO HAY PARTIDA GUARDADA", 32, (84, 52, 112), max_w=info_w, titulo=True
            )
            surface.blit(empty_title, empty_title.get_rect(center=(info_cx, self.slot_rect.top + 58)))
            surface.blit(self.sep_surf, self.sep_surf.get_rect(center=(info_cx, self.slot_rect.top + 102)))

            line1 = self._render_fitted_text(
                surface, "Inicia el Modo Historia y elige tu personaje para comenzar.", 24, (92, 58, 36), max_w=info_w
            )
            line2 = self._render_fitted_text(
                surface, "Tu avance se guarda automáticamente al superar misiones", 22, (124, 88, 62), max_w=info_w
            )
            line3 = self._render_fitted_text(
                surface, "y también de forma manual en Pausa > Guardar partida.", 22, (124, 88, 62), max_w=info_w
            )
            surface.blit(line1, line1.get_rect(center=(info_cx, self.slot_rect.top + 150)))
            surface.blit(line2, line2.get_rect(center=(info_cx, self.slot_rect.top + 196)))
            surface.blit(line3, line3.get_rect(center=(info_cx, self.slot_rect.top + 238)))

        for btn in self.buttons:
            btn.render(surface)


class LoadGameScene(BaseState):
    """
    Pantalla dedicada de Cargar Partida accesible desde el Menú Principal.
    Comparte la estética acuarela oficial del proyecto y permite continuar, iniciar nueva
    partida o limpiar el guardado sin borrar preferencias del jugador.
    """

    def __init__(
        self,
        on_continue_story: Optional[Callable[[str], None]] = None,
        on_new_story: Optional[Callable[[], None]] = None,
        on_back: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.screen_w = 1920
        self.screen_h = 1080
        self.on_continue_story = on_continue_story
        self.on_new_story = on_new_story
        self.on_back = on_back

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()
        self.settings = SettingsManager.get_instance()

        raw_bg = self.assets.load_surface("fondo_main_menu.png", has_alpha=False)
        self.background = pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))
        self.particles = GLParticleSystem(count=28, screen_w=self.screen_w, screen_h=self.screen_h)
        self.juice_particles = JuiceParticleManager()

        self.toast_msg: Optional[str] = None
        self.toast_timer: float = 0.0
        self.font_toast = self.assets.cargarFuenteCuento(24)

        self.panel = StorySaveModalPanel(
            screen_w=self.screen_w,
            screen_h=self.screen_h,
            mode="load_screen",
            on_continue=self._handle_continue,
            on_new_game=self._handle_new_game,
            on_cancel=self._handle_back,
            on_delete=self._handle_delete_save,
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.panel.refresh()

    def _handle_continue(self) -> None:
        self.audio.play_click()
        progress = self.settings.get_story_progress()
        char_id = str(progress.get("character_id", "westcol"))
        if self.on_continue_story:
            self.on_continue_story(char_id)

    def _handle_new_game(self) -> None:
        self.audio.play_click()
        self.settings.reset_story_progress()
        if self.on_new_story:
            self.on_new_story()

    def _handle_delete_save(self) -> None:
        self.audio.play_click()
        self.settings.delete_story_save()
        self.panel.refresh()
        self.toast_msg = "Partida guardada eliminada"
        self.toast_timer = 2.6

    def _handle_back(self) -> None:
        self.audio.play_click()
        if self.on_back:
            self.on_back()

    def handle_event(self, event: pygame.event.Event) -> None:
        self.panel.handle_event(event)

    def update(self, dt: float) -> None:
        self.particles.update(dt)
        self.juice_particles.update(dt)
        self.panel.update(dt)
        if self.toast_timer > 0.0:
            self.toast_timer = max(0.0, self.toast_timer - dt)
            if self.toast_timer == 0.0:
                self.toast_msg = None

    def render(self, surface: pygame.Surface) -> None:
        surface.blit(self.background, (0, 0))
        self.panel.render(surface, draw_backdrop=True)
        self.juice_particles.render(surface)

        if self.toast_msg and self.toast_timer > 0.0:
            ribbon = self.assets.load_cropped_surface("cinta_estado_modal.png")
            txt = self.font_toast.render(self.toast_msg, True, (76, 48, 102))
            rw = max(420, txt.get_width() + 90)
            rh = 58
            r_surf = pygame.transform.smoothscale(ribbon, (rw, rh))
            r_surf.blit(txt, txt.get_rect(center=(rw // 2, rh // 2)))
            surface.blit(r_surf, r_surf.get_rect(center=(self.screen_w // 2, 102)))
