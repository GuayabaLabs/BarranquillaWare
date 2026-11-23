import math
import os
from typing import Callable, Dict, List, Optional, Tuple
import pygame
from core.audio_manager import AudioManager

class SideNavDrawer:
    """
    Barra desplegable de navegación lateral izquierda (BarranquillaWare).
    
    Características:
    - Arte 100% oficial extraído y renderizado directamente de la referencia (mapa_ui_referencia.png):
      - Fondo completo integrado con los 5 botones originales en proporción exacta:
        * Mapa (destacado amarillo, icono de mapa, rayos y flores)
        * Mensajes (lavanda con chat y badge '1')
        * Seguidores (lavanda con icono de personas)
        * Logros (lavanda con estrella dorada oficial)
        * Perfil (lavanda con marco de foto)
    - Cuando está colapsada (no desplegada), el cuerpo del panel se sitúa en x = -338 px,
      dejando únicamente la pestaña/botón circular del sprite con la flecha ▶ visible
      en el borde izquierdo de la pantalla (x = 0..42 px).
    - Al hacer clic en el botón del sprite, se despliega suavemente mediante interpolación
      con delta time (dt) hacia x = 15 px.
    - Cada uno de los 5 botones cuenta con su propia hitbox interactiva, efectos de hover,
      pulsación táctil con respuesta de audio y despacho de eventos.
    - Clic fuera del panel abierto lo repliega automáticamente.
    """
    def __init__(
        self,
        screen_w: int = 1920,
        screen_h: int = 1080,
        on_nav_selected: Optional[Callable[[str], None]] = None,
        show_notification_badge: bool = False
    ) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.on_nav_selected = on_nav_selected
        self.show_notification_badge: bool = show_notification_badge

        self.is_open: bool = False
        self.anim_t: float = 0.0  # 0.0 = Colapsado, 1.0 = Desplegado

        # Dimensiones calibradas del panel (panel expandido amplio)
        self.panel_w: int = 450
        self.panel_h: int = 780
        self.panel_top_y: int = 220

        # Cinemática de posición X
        self.collapsed_x: int = -400
        self.expanded_x: int = 15

        self.audio = AudioManager.get_instance()
        self.active_tab: str = "mapa"

        # Cargar paneles oficiales: fondo de madera pergamino y pestaña colapsada
        self.panel_expanded = self._load_scaled("recuadro_ui_desplegable_desplegado_mapa.png", (self.panel_w, self.panel_h))
        self.panel_collapsed = self._load_scaled("recuadro_ui_desplegable_mapa.png", (self.panel_w, self.panel_h))
        self.badge_sprite = self._load_scaled("badge_notificacion_mensajes.png", (52, 52))

        # Definición de los 5 botones oficiales compactos centrados dentro del pergamino
        # w = 310, h = 88, x = 55 (margen simétrico de 30px con respecto al marco interior)
        self.nav_items: List[Dict[str, any]] = [
            {"id": "mapa", "label": "Mapa", "rect": pygame.Rect(55, 95, 310, 88), "file": "boton_mapa_mapa.png", "hover_file": "boton_mapa_hover_mapa.png"},
            {"id": "mensajes", "label": "Mensajes", "rect": pygame.Rect(55, 219, 310, 88), "file": "boton_mensajes_mapa.png", "hover_file": "boton_mensajes_hover_mapa.png"},
            {"id": "misiones", "label": "Misiones", "rect": pygame.Rect(55, 343, 310, 88), "file": "boton_misiones_mapa.png", "hover_file": "boton_misiones_hover_mapa.png"},
            {"id": "logros", "label": "Logros", "rect": pygame.Rect(55, 467, 310, 88), "file": "boton_logros_mapa.png", "hover_file": "boton_logros_hover_mapa.png"},
            {"id": "perfil", "label": "Perfil", "rect": pygame.Rect(55, 591, 310, 88), "file": "boton_perfil_mapa.png", "hover_file": "boton_perfil_hover_mapa.png"},
        ]

        # Cargar sprites en escala exacta y precomputar estados normales y hover
        self.button_sprites: Dict[str, pygame.Surface] = {}
        self.button_hover_sprites: Dict[str, pygame.Surface] = {}
        self._init_buttons()

        # Shimmer shader: seguimiento de progreso de barrido luminoso por cada botón
        self.button_shimmer: Dict[str, float] = {item["id"]: 2.0 for item in self.nav_items}
        self.button_press_offset: Dict[str, float] = {item["id"]: 0.0 for item in self.nav_items}

        # Estados de interacción
        self.hovered_item_id: Optional[str] = None
        self.pressed_item_id: Optional[str] = None
        self.tab_hovered: bool = False
        self.tab_pressed: bool = False
        self.focus_index: Optional[int] = None

        # Sección de trofeos que se muestra al tocar Logros
        from core.asset_manager import AssetManager
        assets = AssetManager.get_instance()
        self.seccionActual: str = "botones"
        self.trofeos: List[dict] = []
        self.trofeosObtenidos: List[str] = []
        self.mensajes: List[dict] = []
        self.misiones: List[dict] = []
        self.perfil_data: dict = {}
        self.hoverBotonCerrar: bool = False

        # Botón de cerrar acuarela oficial
        try:
            raw_close = assets.load_cropped_surface("boton_cerrar_x.png")
            self.botonCerrar = pygame.transform.smoothscale(raw_close, (52, 52))
        except Exception:
            self.botonCerrar = assets.cargarSinFondo(os.path.join("Interfaz", "botonX.jpg"), 52)

        # Sellos de estado para misiones
        try:
            raw_desp = assets.load_cropped_surface("sello_estado_despejado.png")
            self.sello_despejado = pygame.transform.smoothscale(raw_desp, (28, 28))
            raw_pend = assets.load_cropped_surface("sello_estado_pendiente.png")
            self.sello_pendiente = pygame.transform.smoothscale(raw_pend, (28, 28))
        except Exception:
            self.sello_despejado = None
            self.sello_pendiente = None

        self.trofeoColor = assets.cargarTrofeo(120)
        self.trofeoGris = assets.cargarTrofeo(120, enGris=True)
        self.trofeoColorCompacto = assets.cargarTrofeo(74)
        self.trofeoGrisCompacto = assets.cargarTrofeo(74, enGris=True)
        self.fuenteTitulo = assets.cargarFuenteTitulo(62)
        self.fuenteTituloMensajes = assets.cargarFuenteCuento(54)
        tam = 62
        self.fuenteTituloSeccion = assets.cargarFuenteTitulo(tam)
        anchoTitulo = 2 * (self.rectBotonCerrar(0).left - self.centroPanel(0) - 14)
        while tam > 30 and max(self.fuenteTituloSeccion.size(n)[0] for n in ("Logros", "Mensajes", "Misiones", "Perfil")) > anchoTitulo:
            tam -= 2
            self.fuenteTituloSeccion = assets.cargarFuenteTitulo(tam)
        self.fuenteNombre = assets.cargarFuenteCuento(34)
        self.fuenteDetalle = assets.cargarFuenteCuento(25)
        self.fuenteNombreCompacto = assets.cargarFuenteCuento(21)
        self.fuenteDetalleCompacto = assets.cargarFuenteCuento(16)
        self.fuenteNombreMsg = assets.cargarFuenteCuento(18)
        self.fuenteAsuntoMsg = assets.cargarFuenteCuento(15)
        self.fuenteDetalleMsg = assets.cargarFuenteCuento(14)

        try:
            self.ficha_card_base = assets.load_cropped_surface("ficha_resumen_partida.png")
        except Exception:
            self.ficha_card_base = None
        self._ficha_cache: Dict[Tuple[int, int], pygame.Surface] = {}
        self.unread_badge_small = (
            pygame.transform.smoothscale(self.badge_sprite, (18, 18))
            if self.badge_sprite is not None
            else None
        )
        # Reloj del destello que pasa por los trofeos ganados
        self.tiempoBrillo: float = 0.0

    def _get_ficha_card(self, w: int, h: int) -> pygame.Surface:
        key = (w, h)
        cached = self._ficha_cache.get(key)
        if cached is not None:
            return cached
        if self.ficha_card_base is not None:
            card = pygame.transform.smoothscale(self.ficha_card_base, (w, h)).convert_alpha()
        else:
            card = pygame.Surface((w, h), pygame.SRCALPHA)
        self._ficha_cache[key] = card
        return card

    def _init_buttons(self) -> None:
        """Carga y optimiza los sprites oficiales de cada botón y sus variantes hover."""
        if self.armarBotonesConBase():
            return
        for item in self.nav_items:
            item_id = item["id"]
            rect = item["rect"]
            sz = (rect.width, rect.height)

            norm = self._load_scaled(item["file"], sz)
            if norm:
                self.button_sprites[item_id] = norm

            hov = self._load_scaled(item["hover_file"], sz)
            if hov:
                self.button_hover_sprites[item_id] = hov
            elif norm:
                self.button_hover_sprites[item_id] = norm

    def armarBotonesConBase(self) -> bool:
        from core.asset_manager import AssetManager
        assets = AssetManager.get_instance()
        try:
            ancho, alto = self.nav_items[0]["rect"].size
            bases = []
            naranja = assets.load_cropped_surface("boton_acuarela_naranja.png")
            rojo = assets.cargarSinFondo(os.path.join("Interfaz", "botonRojo.jpg"), ancho)
            for base in (naranja, rojo):
                altoBase = int(base.get_height() * ancho / float(base.get_width()))
                base = pygame.transform.smoothscale(base, (ancho, min(alto, altoBase)))
                lienzo = pygame.Surface((ancho, alto), pygame.SRCALPHA)
                lienzo.blit(base, base.get_rect(center=(ancho // 2, alto // 2)))
                bases.append(lienzo)
        except Exception as e:
            print(f"[SideNavDrawer] Aviso al armar los botones: {e}")
            return False

        tam = 40
        fuente = assets.cargarFuenteTitulo(tam)
        while tam > 20 and max(fuente.size(item["label"])[0] for item in self.nav_items) > ancho * 0.62:
            tam -= 2
            fuente = assets.cargarFuenteTitulo(tam)

        for item in self.nav_items:
            versiones = []
            for base, contorno in ((bases[0], (150, 70, 20)), (bases[1], (120, 26, 34))):
                imagen = base.copy()
                letras = self.textoConContorno(fuente, item["label"], (255, 248, 236), contorno)
                imagen.blit(letras, letras.get_rect(center=(ancho // 2, alto // 2 - 3)))
                versiones.append(imagen)
            self.button_sprites[item["id"]] = versiones[0]
            self.button_hover_sprites[item["id"]] = versiones[1]
        return True

    def textoConContorno(self, fuente, texto: str, color, colorContorno) -> pygame.Surface:
        cuerpo = fuente.render(texto, True, color)
        borde = fuente.render(texto, True, colorContorno)
        lienzo = pygame.Surface((cuerpo.get_width() + 6, cuerpo.get_height() + 6), pygame.SRCALPHA)
        for dx in (-3, -2, 0, 2, 3):
            for dy in (-3, -2, 0, 2, 3):
                if abs(dx) + abs(dy) >= 3:
                    lienzo.blit(borde, (3 + dx, 3 + dy))
        lienzo.blit(cuerpo, (3, 3))
        return lienzo

    def _load_scaled(self, filename: str, size: Tuple[int, int]) -> Optional[pygame.Surface]:
        from core.asset_manager import AssetManager
        assets = AssetManager.get_instance()
        try:
            return assets.get_scaled(filename, size[0], size[1])
        except Exception as e:
            print(f"[SideNavDrawer] Aviso al cargar {filename}: {e}")
            return None

    def _get_panel_x(self) -> int:
        return int(self.collapsed_x + (self.expanded_x - self.collapsed_x) * self.anim_t)

    def _get_tab_rect(self) -> pygame.Rect:
        """Devuelve el Rect de la pestaña exterior circular en coordenadas de pantalla."""
        panel_x = self._get_panel_x()
        return pygame.Rect(panel_x + 400, self.panel_top_y + 330, 48, 68)

    def _get_item_screen_rect(self, item: Dict[str, any]) -> pygame.Rect:
        panel_x = self._get_panel_x()
        r = item["rect"]
        return pygame.Rect(panel_x + r.x, self.panel_top_y + r.y, r.width, r.height)

    def toggle(self) -> None:
        self.is_open = not self.is_open
        self.audio.play_click()

    def is_blocking(self) -> bool:
        return self.is_open or self.anim_t > 0.05

    def camera_dwell_target(self, pos):
        """Solo activa controles visibles, nunca el fondo del panel."""
        if self._get_tab_rect().collidepoint(pos):
            return ("drawer", "toggle")
        if not self.is_open or self.anim_t < 0.95:
            return None
        if self.seccionActual != "botones":
            if self.rectBotonCerrar(self._get_panel_x()).collidepoint(pos):
                return ("drawer", self.seccionActual, "close")
            return None
        for item in self.nav_items:
            if self._get_item_screen_rect(item).collidepoint(pos):
                return ("drawer", item["id"])
        return None

    def _focus_item(self, index: int) -> None:
        self.focus_index = index % len(self.nav_items)
        item_id = self.nav_items[self.focus_index]["id"]
        if self.hovered_item_id != item_id:
            self.audio.play_hover()
            self.button_shimmer[item_id] = 0.0
        self.hovered_item_id = item_id

    def _activate_item(self, item_id: str) -> None:
        self.active_tab = item_id
        self.audio.play_click()
        if self.on_nav_selected:
            self.on_nav_selected(item_id)

    def _handle_keyboard(self, key: int) -> bool:
        if key == pygame.K_TAB:
            self.toggle()
            if self.is_open and self.seccionActual == "botones":
                self._focus_item(0)
            return True
        if not self.is_open:
            return False
        if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_LEFT, pygame.K_a):
            if self.seccionActual != "botones":
                self.seccionActual = "botones"
                self.hoverBotonCerrar = False
                self._focus_item(self.focus_index or 0)
            else:
                self.toggle()
            return True
        if key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
            if self.seccionActual == "botones":
                step = -1 if key in (pygame.K_UP, pygame.K_w) else 1
                self._focus_item(0 if self.focus_index is None else self.focus_index + step)
            return True
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_RIGHT, pygame.K_d):
            if self.seccionActual == "botones":
                self._focus_item(self.focus_index or 0)
                self._activate_item(self.nav_items[self.focus_index]["id"])
            return True
        return False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN and self._handle_keyboard(event.key):
            return True
        if event.type == pygame.MOUSEMOTION:
            self.focus_index = None
        tab_rect = self._get_tab_rect()
        panel_x = self._get_panel_x()
        panel_rect = pygame.Rect(panel_x, self.panel_top_y, self.panel_w, self.panel_h)

        # En las secciones internas los botones base no responden; el botón X vuelve a ellos
        if self.seccionActual != "botones" and self.is_open:
            if self.manejarSeccionInterna(event, panel_rect, tab_rect):
                return True

        if event.type == pygame.MOUSEMOTION:
            was_tab_hover = self.tab_hovered
            self.tab_hovered = tab_rect.collidepoint(event.pos)
            if not was_tab_hover and self.tab_hovered:
                self.audio.play_hover()

            # Hover sobre los botones del panel si está abierto
            if self.anim_t > 0.1 and panel_rect.collidepoint(event.pos):
                hovered = None
                for item in self.nav_items:
                    if self._get_item_screen_rect(item).collidepoint(event.pos):
                        hovered = item["id"]
                        break
                if hovered != self.hovered_item_id:
                    if hovered is not None:
                        self.audio.play_hover()
                        # Disparar barrido shader de brillo al iniciar hover
                        self.button_shimmer[hovered] = 0.0
                    self.hovered_item_id = hovered
                return True
            else:
                self.hovered_item_id = None

            return self.tab_hovered or (self.is_open and panel_rect.collidepoint(event.pos))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 1. Clic en la pestaña / botoncito del sprite
            if tab_rect.collidepoint(event.pos):
                self.tab_pressed = True
                return True

            # 2. Clic dentro del panel expandido sobre un botón
            if self.is_open and panel_rect.collidepoint(event.pos):
                for item in self.nav_items:
                    if self._get_item_screen_rect(item).collidepoint(event.pos):
                        self.pressed_item_id = item["id"]
                        return True
                return True

            # 3. Clic fuera del panel estando abierto -> colapsar
            if self.is_open and event.pos[0] > (panel_x + self.panel_w):
                self.is_open = False
                self.audio.play_click()
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.tab_pressed:
                self.tab_pressed = False
                if tab_rect.collidepoint(event.pos):
                    self.toggle()
                    return True

            if self.pressed_item_id is not None:
                clicked_id = self.pressed_item_id
                self.pressed_item_id = None
                for item in self.nav_items:
                    if item["id"] == clicked_id and self._get_item_screen_rect(item).collidepoint(event.pos):
                        self._activate_item(clicked_id)
                        return True

            if self.is_open and panel_rect.collidepoint(event.pos):
                return True

        return False

    def update(self, dt: float) -> None:
        target_t = 1.0 if self.is_open else 0.0
        blend = min(1.0, dt * 14.0)
        self.anim_t += (target_t - self.anim_t) * blend

        if abs(self.anim_t - target_t) < 0.001:
            self.anim_t = target_t

        # Al esconder el panel vuelve a mostrar los botones
        if self.anim_t == 0.0:
            self.seccionActual = "botones"
        self.tiempoBrillo += dt

        # Actualizar animaciones de shader y retroalimentación táctil de botones
        for item in self.nav_items:
            item_id = item["id"]
            # 1. Animación suave de presionado táctil (offset Y)
            target_offset = 3.0 if item_id == self.pressed_item_id else 0.0
            cur_offset = self.button_press_offset[item_id]
            self.button_press_offset[item_id] += (target_offset - cur_offset) * min(1.0, dt * 25.0)

            # 2. Shader de barrido de brillo luminoso (shimmer)
            if self.button_shimmer[item_id] < 1.3:
                self.button_shimmer[item_id] += dt * 1.45

    def render(self, surface: pygame.Surface) -> None:
        panel_x = self._get_panel_x()

        # En estado colapsado puro (anim_t == 0.0), dibujamos el recuadro colapsado con la pestaña ▶
        if self.anim_t < 0.05:
            if self.panel_collapsed:
                surface.blit(self.panel_collapsed, (panel_x, self.panel_top_y))
            return

        # 1. Renderizar fondo oficial del recuadro desplegado (recuadro_ui_desplegable_desplegado_mapa.png)
        if self.panel_expanded:
            surface.blit(self.panel_expanded, (panel_x, self.panel_top_y))

        # Secciones internas en lugar de los botones base
        if self.seccionActual == "trofeos":
            self.dibujarSeccionTrofeos(surface, panel_x)
            return
        elif self.seccionActual == "mensajes":
            self.dibujarSeccionMensajes(surface, panel_x)
            return
        elif self.seccionActual == "misiones":
            self.dibujarSeccionMisiones(surface, panel_x)
            return
        elif self.seccionActual == "perfil":
            self.dibujarSeccionPerfil(surface, panel_x)
            return

        # 2. Renderizar los 5 botones oficiales con shaders interactivos
        for item in self.nav_items:
            item_id = item["id"]
            screen_r = self._get_item_screen_rect(item)
            is_hovered = (item_id == self.hovered_item_id)
            draw_y = screen_r.y + int(self.button_press_offset[item_id])

            # Seleccionar sprite base o sprite hover oficial
            if is_hovered and item_id in self.button_hover_sprites:
                btn_surf = self.button_hover_sprites[item_id]
            else:
                btn_surf = self.button_sprites.get(item_id)

            if not btn_surf:
                continue

            # Shader de brillo dinámico (Shimmer Sweep) confinado a la silueta del botón
            shimmer_t = self.button_shimmer[item_id]
            if shimmer_t < 1.15:
                w, h = screen_r.width, screen_r.height
                btn_draw = btn_surf.copy()
                shimmer_overlay = pygame.Surface((w, h), pygame.SRCALPHA)

                # Coordenadas diagonales del barrido
                sweep_x = int(-0.4 * w + shimmer_t * 1.8 * w)
                strip_w = max(16, int(w * 0.18))
                slant = int(h * 0.45)
                points = [
                    (sweep_x, 0),
                    (sweep_x + strip_w, 0),
                    (sweep_x + strip_w - slant, h),
                    (sweep_x - slant, h)
                ]

                # Opacidad en campana senoidal suave
                norm_progress = min(1.0, max(0.0, shimmer_t / 1.15))
                alpha = int(120 * math.sin(norm_progress * math.pi))
                pygame.draw.polygon(shimmer_overlay, (255, 255, 255, alpha), points)

                # Multiplicar por la máscara alfa del botón (cero fugas de luz fuera de la píldora)
                shimmer_overlay.blit(btn_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                # Sumar iluminación aditiva pura
                btn_draw.blit(shimmer_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

                surface.blit(btn_draw, (screen_r.x, draw_y))
            else:
                surface.blit(btn_surf, (screen_r.x, draw_y))

        # 3. Renderizar insignia (badge) de notificación '1' de Mensajes solo si show_notification_badge es True
        if self.show_notification_badge and self.badge_sprite:
            badge_x = panel_x + 328
            badge_y = self.panel_top_y + 206
            surface.blit(self.badge_sprite, (badge_x, badge_y))

    def ponerTrofeos(self, trofeos: List[dict], obtenidos: List[str]) -> None:
        """Guarda la lista de trofeos y cuáles ya se ganaron."""
        self.trofeos = trofeos
        self.trofeosObtenidos = list(obtenidos)

    def mostrarTrofeos(self) -> None:
        self.seccionActual = "trofeos"

    def ponerMensajes(self, mensajes: List[dict]) -> None:
        """Guarda la lista de mensajes y notificaciones."""
        self.mensajes = list(mensajes)

    def mostrarMensajes(self) -> None:
        self.seccionActual = "mensajes"
        self.show_notification_badge = False

    def ponerMisiones(self, misiones: List[dict]) -> None:
        """Guarda la lista de misiones de campaña."""
        self.misiones = list(misiones)

    def mostrarMisiones(self) -> None:
        self.seccionActual = "misiones"

    def ponerPerfil(self, perfil: dict) -> None:
        """Guarda los datos de perfil del jugador."""
        self.perfil_data = dict(perfil)

    def mostrarPerfil(self) -> None:
        self.seccionActual = "perfil"

    def centroPestana(self) -> Tuple[int, int]:
        """Centro de la pestañita del panel, a donde vuela el trofeo ganado."""
        return self._get_tab_rect().center

    def rectBotonCerrar(self, panelX: int) -> pygame.Rect:
        rect = self.botonCerrar.get_rect()
        rect.center = (panelX + 345, self.panel_top_y + 78)
        return rect

    def manejarSeccionInterna(self, event: pygame.event.Event, cajaPanel: pygame.Rect, cajaPestana: pygame.Rect) -> bool:
        # La pestaña sigue funcionando para esconder el panel
        if hasattr(event, "pos") and cajaPestana.collidepoint(event.pos):
            return False

        rectCerrar = self.rectBotonCerrar(self._get_panel_x())
        if event.type == pygame.MOUSEMOTION:
            estaba = self.hoverBotonCerrar
            self.hoverBotonCerrar = rectCerrar.collidepoint(event.pos)
            if self.hoverBotonCerrar and not estaba:
                self.audio.play_hover()
            return cajaPanel.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if rectCerrar.collidepoint(event.pos):
                self.seccionActual = "botones"
                self.hoverBotonCerrar = False
                self.audio.play_click()
                return True
            return cajaPanel.collidepoint(event.pos)

        return False

    def manejarSeccionTrofeos(self, event: pygame.event.Event, cajaPanel: pygame.Rect, cajaPestana: pygame.Rect) -> bool:
        return self.manejarSeccionInterna(event, cajaPanel, cajaPestana)

    def partirTexto(self, texto: str, fuente: pygame.font.Font, anchoMax: int) -> List[str]:
        # Reparte las palabras en renglones que quepan en el ancho
        renglones = []
        actual = ""
        for palabra in texto.split():
            prueba = palabra if not actual else actual + " " + palabra
            if fuente.size(prueba)[0] <= anchoMax or not actual:
                actual = prueba
            else:
                renglones.append(actual)
                actual = palabra
        if actual:
            renglones.append(actual)
        return renglones

    def conDestello(self, imagen: pygame.Surface, progreso: float) -> pygame.Surface:
        """Franja de luz que cruza la imagen en diagonal, como en los botones del menú principal."""
        if progreso >= 1.15:
            return imagen
        w, h = imagen.get_size()
        conLuz = imagen.copy()
        luz = pygame.Surface((w, h), pygame.SRCALPHA)
        barrido = int(-0.4 * w + progreso * 1.8 * w)
        franja = max(16, int(w * 0.22))
        inclinacion = int(h * 0.45)
        puntos = [
            (barrido, 0),
            (barrido + franja, 0),
            (barrido + franja - inclinacion, h),
            (barrido - inclinacion, h)
        ]
        alfa = int(130 * math.sin(min(1.0, progreso / 1.15) * math.pi))
        pygame.draw.polygon(luz, (255, 255, 255, alfa), puntos)
        # La luz solo cae sobre los píxeles del trofeo
        luz.blit(imagen, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        conLuz.blit(luz, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return conLuz

    def centroPanel(self, panelX: int) -> int:
        return panelX + 214

    def dibujarSeccionTrofeos(self, surface: pygame.Surface, panelX: int) -> None:
        """Dibuja los trofeos sobre fichas acuarela: en gris los que faltan y a color los ganados."""
        cafeOscuro = (82, 48, 28)
        cafe = (112, 68, 38)
        cafeApagado = (134, 108, 86)
        top = self.panel_top_y

        centro = self.centroPanel(panelX)
        titulo = self.fuenteTituloSeccion.render("Logros", True, cafeOscuro)
        surface.blit(titulo, titulo.get_rect(center=(centro, top + 72)))

        cerrar = self.botonCerrar
        if self.hoverBotonCerrar:
            cerrar = pygame.transform.smoothscale_by(cerrar, 1.1)
        surface.blit(cerrar, cerrar.get_rect(center=self.rectBotonCerrar(panelX).center))

        n_trofeos = len(self.trofeos)
        compacto = n_trofeos > 2
        trofeo_color = self.trofeoColorCompacto if compacto else self.trofeoColor
        trofeo_gris = self.trofeoGrisCompacto if compacto else self.trofeoGris
        f_nombre = self.fuenteNombreCompacto if compacto else self.fuenteNombre
        f_detalle = self.fuenteDetalleCompacto if compacto else self.fuenteDetalle
        card_w = 320
        card_h = 116 if compacto else 184
        paso_fila = 128 if compacto else 200
        offset_inicio = 132 if compacto else 156
        card_x = centro - card_w // 2
        text_x = (card_x + 92) if compacto else (card_x + 136)
        text_w = card_w - (104 if compacto else 148)
        trofeo_x = card_x + 10

        for i, trofeo in enumerate(self.trofeos):
            fila = top + offset_inicio + i * paso_fila
            obtenido = trofeo["id"] in self.trofeosObtenidos
            card_surf = self._get_ficha_card(card_w, card_h).copy()
            imagen = trofeo_color if obtenido else trofeo_gris
            if obtenido:
                progreso = ((self.tiempoBrillo + i * 0.9) % 3.0) * 1.35
                imagen = self.conDestello(imagen, progreso)
            surface.blit(card_surf, (card_x, fila))
            surface.blit(imagen, (trofeo_x, fila + (card_h - imagen.get_height()) // 2))

            nombre = trofeo["nombre"] if obtenido else "Trofeo escondido"
            detalle = trofeo["descripcion"] if obtenido else "Sigue explorando el mapa"
            y = fila + (8 if compacto else 18)
            salto_nombre = 22 if compacto else 36
            salto_detalle = 16 if compacto else 26
            for renglon in self.partirTexto(nombre, f_nombre, text_w):
                texto = f_nombre.render(renglon, True, cafeOscuro if obtenido else cafe)
                surface.blit(texto, (text_x, y))
                y += salto_nombre
            y += (2 if compacto else 8)
            for renglon in self.partirTexto(detalle, f_detalle, text_w)[:3]:
                texto = f_detalle.render(renglon, True, cafe if obtenido else cafeApagado)
                surface.blit(texto, (text_x, y))
                y += salto_detalle

        cuantos = len([t for t in self.trofeos if t["id"] in self.trofeosObtenidos])
        cuenta = f_nombre.render(f"{cuantos} de {len(self.trofeos)} trofeos", True, cafeOscuro)
        surface.blit(cuenta, cuenta.get_rect(center=(centro, top + (698 if compacto else 705))))

    def dibujarSeccionMensajes(self, surface: pygame.Surface, panelX: int) -> None:
        """Dibuja la bandeja de mensajes narrativos sobre tarjetas acuarela con alta legibilidad."""
        cafeOscuro = (72, 44, 28)
        cafe = (112, 66, 36)
        cafeTexto = (86, 56, 38)
        top = self.panel_top_y

        centro = self.centroPanel(panelX)
        titulo = self.fuenteTituloSeccion.render("Mensajes", True, cafeOscuro)
        titulo_rect = titulo.get_rect(center=(centro, top + 66))
        surface.blit(titulo, titulo_rect)

        cerrar = self.botonCerrar
        if self.hoverBotonCerrar:
            cerrar = pygame.transform.smoothscale_by(cerrar, 1.1)
        surface.blit(cerrar, cerrar.get_rect(center=self.rectBotonCerrar(panelX).center))

        sub = self.fuenteDetalleCompacto.render("Avisos de Curramba", True, cafe)
        sub_rect = sub.get_rect(center=(centro, top + 114))
        surface.blit(sub, sub_rect)

        mensajes_a_mostrar = self.mensajes if self.mensajes else [
            {"remitente": "Paloma de Curramba", "asunto": "¡Bienvenido a BarranquillaWare!", "cuerpo": "Usa las redes con cabeza fría. ¡No todo en el feed es real!", "leido": True},
            {"remitente": "Alerta Digital Uninorte", "asunto": "Zona Libre de Distracciones", "cuerpo": "Enfoca tu mente y silencia avisos innecesarios al estudiar.", "leido": False},
            {"remitente": "Radar Buenavista", "asunto": "Baila a tu propio compás", "cuerpo": "No dejes que los likes dicten tu felicidad ni tu valor.", "leido": False},
            {"remitente": "Tribuna Metropolitano", "asunto": "Convivencia y Respeto", "cuerpo": "Apoya a tu equipo sin lanzar odio en comentarios ni chats.", "leido": False},
            {"remitente": "Seguridad Cortissoz", "asunto": "Alerta de Phishing y Estafas", "cuerpo": "Nunca abras enlaces de premios milagrosos ni compartas claves.", "leido": False},
            {"remitente": "Aleta del Tiburón", "asunto": "El Sabor del Troll", "cuerpo": "No muerdas el anzuelo del trol. Respira hondo y atiende en calma.", "leido": False},
        ]

        visibles = mensajes_a_mostrar[:6]
        n_msg = len(visibles)
        if n_msg <= 4:
            card_h, card_gap, card_y = 122, 14, top + 134
        elif n_msg == 5:
            card_h, card_gap, card_y = 106, 10, top + 132
        else:
            card_h, card_gap, card_y = 94, 4, top + 131

        card_w = 316
        card_x = centro - card_w // 2
        cards_metrics = []
        for msg in visibles:
            card_surf = self._get_ficha_card(card_w, card_h).copy()
            compact_msg = card_h < 98

            if not msg.get("leido", False) and self.unread_badge_small is not None:
                card_surf.blit(self.unread_badge_small, (11, 8 if compact_msg else 10))
            elif self.sello_despejado is not None and msg.get("leido", False):
                s_small = pygame.transform.smoothscale(self.sello_despejado, (18, 18))
                card_surf.blit(s_small, (11, 8 if compact_msg else 10))

            f_rem = self.fuenteNombreMsg if compact_msg else self.fuenteNombreCompacto
            f_as = self.fuenteAsuntoMsg if compact_msg else self.fuenteDetalleCompacto
            f_cuerpo = self.fuenteDetalleMsg if compact_msg else self.fuenteDetalleCompacto

            max_header_w = card_w - 44

            y_rem = 4
            txt_rem = f_rem.render(msg.get("remitente", "Aviso"), True, cafeOscuro)
            if txt_rem.get_width() > max_header_w:
                orig_rh = txt_rem.get_height()
                txt_rem = pygame.transform.smoothscale_by(txt_rem, max_header_w / float(txt_rem.get_width()))
                y_rem += max(0, (orig_rh - txt_rem.get_height()) // 2)
            card_surf.blit(txt_rem, (33, y_rem))
            rem_bb = txt_rem.get_bounding_rect().move(33, y_rem)

            y_as = 29 if compact_msg else 35
            txt_as = f_as.render(msg.get("asunto", ""), True, cafe)
            if txt_as.get_width() > max_header_w:
                orig_ah = txt_as.get_height()
                txt_as = pygame.transform.smoothscale_by(txt_as, max_header_w / float(txt_as.get_width()))
                y_as += max(0, (orig_ah - txt_as.get_height()) // 2)
            card_surf.blit(txt_as, (33, y_as))
            as_bb = txt_as.get_bounding_rect().move(33, y_as)

            cuerpo = msg.get("cuerpo", "")
            renglones = self.partirTexto(cuerpo, f_cuerpo, card_w - 34)
            y_cuerpo = 52 if compact_msg else 57
            salto_cuerpo = 19 if compact_msg else 22
            body_bbs = []
            for r in renglones[:2]:
                txt_c = f_cuerpo.render(r, True, cafeTexto)
                card_surf.blit(txt_c, (17, y_cuerpo))
                body_bbs.append(txt_c.get_bounding_rect().move(17, y_cuerpo))
                y_cuerpo += salto_cuerpo

            cards_metrics.append({
                "card_rect": pygame.Rect(card_x, card_y, card_w, card_h),
                "rem_ink": rem_bb,
                "as_ink": as_bb,
                "body_inks": body_bbs,
            })
            surface.blit(card_surf, (card_x, card_y))
            card_y += card_h + card_gap

        pie = self.fuenteDetalleCompacto.render(f"{len(visibles)} avisos", True, cafeOscuro)
        pie_rect = pie.get_rect(center=(centro, top + 736))
        surface.blit(pie, pie_rect)

        self.last_mensajes_layout_metrics = {
            "titulo_ink": titulo.get_bounding_rect().move(titulo_rect.topleft),
            "sub_ink": sub.get_bounding_rect().move(sub_rect.topleft),
            "pie_ink": pie.get_bounding_rect().move(pie_rect.topleft),
            "panel_rect": pygame.Rect(panelX, top, self.panel_w, self.panel_h),
            "cards": cards_metrics,
        }

    def dibujarSeccionMisiones(self, surface: pygame.Surface, panelX: int) -> None:
        """Dibuja los objetivos de campaña sobre tarjetas acuarela oficiales."""
        cafeOscuro = (72, 44, 28)
        cafe = (112, 68, 38)
        cafeTexto = (96, 66, 46)
        top = self.panel_top_y

        centro = self.centroPanel(panelX)
        titulo = self.fuenteTituloSeccion.render("Misiones", True, cafeOscuro)
        surface.blit(titulo, titulo.get_rect(center=(centro, top + 72)))

        cerrar = self.botonCerrar
        if self.hoverBotonCerrar:
            cerrar = pygame.transform.smoothscale_by(cerrar, 1.1)
        surface.blit(cerrar, cerrar.get_rect(center=self.rectBotonCerrar(panelX).center))

        misiones_a_mostrar = self.misiones if self.misiones else [
            {"id": "uninorte", "titulo": "Biblioteca Uninorte", "desc": "Espanta distracciones y vence el doomscrolling.", "completada": False},
            {"id": "buenavista", "titulo": "C.C. Buenavista", "desc": "Sigue el compás del trend sin volverte viral adicto.", "completada": False},
            {"id": "metropolitano", "titulo": "Estadio Metropolitano", "desc": "Modera el chat en vivo y frena la toxicidad.", "completada": False},
            {"id": "aeropuerto", "titulo": "Aeropuerto Cortissoz", "desc": "Batea el phishing y bloquea mensajes sospechosos.", "completada": False},
            {"id": "aleta", "titulo": "Aleta del Tiburón", "desc": "Atiende los fritos sin engancharte con el trol.", "completada": False},
            {"id": "malecon", "titulo": "Gran Malecón del Río", "desc": "Suelta el celular y reconéctate con el Magdalena.", "completada": False},
        ]

        visibles = misiones_a_mostrar[:6]
        n_mis = len(visibles)
        if n_mis <= 5:
            card_h, card_gap, card_y = 96, 14, top + 128
        else:
            card_h, card_gap, card_y = 84, 8, top + 124
        compact_mis = card_h < 90

        card_w = 316
        card_x = centro - card_w // 2
        completadas = 0

        for mis in visibles:
            comp = bool(mis.get("completada", False))
            if comp:
                completadas += 1

            card_surf = self._get_ficha_card(card_w, card_h).copy()

            sello = self.sello_despejado if comp else self.sello_pendiente
            if sello:
                card_surf.blit(sello, (12, (card_h - sello.get_height()) // 2))

            t_col = (30, 118, 62) if comp else cafeOscuro
            txt_t = self.fuenteNombreCompacto.render(mis.get("titulo", "Misión"), True, t_col)
            max_title_w = card_w - 58
            y_title = 9 if compact_mis else 14
            if txt_t.get_width() > max_title_w:
                orig_th = txt_t.get_height()
                txt_t = pygame.transform.smoothscale_by(txt_t, max_title_w / float(txt_t.get_width()))
                y_title += max(0, (orig_th - txt_t.get_height()) // 2)
            card_surf.blit(txt_t, (48, y_title))

            d_col = (56, 108, 72) if comp else cafeTexto
            renglones = self.partirTexto(mis.get("desc", ""), self.fuenteDetalleCompacto, card_w - 60)
            y_desc = 33 if compact_mis else 39
            for r in renglones[:2]:
                txt_d = self.fuenteDetalleCompacto.render(r, True, d_col)
                card_surf.blit(txt_d, (48, y_desc))
                y_desc += 17

            surface.blit(card_surf, (card_x, card_y))
            card_y += card_h + card_gap

        pie = self.fuenteNombreCompacto.render(f"{completadas} de {len(visibles)} misiones superadas", True, cafeOscuro)
        surface.blit(pie, pie.get_rect(center=(centro, top + 712)))

    def dibujarSeccionPerfil(self, surface: pygame.Surface, panelX: int) -> None:
        """Dibuja la ficha esencial del jugador sin repetir métricas que ya muestra el HUD superior."""
        from core.asset_manager import AssetManager
        assets = AssetManager.get_instance()
        cafeOscuro = (72, 44, 28)
        cafe = (112, 68, 38)
        top = self.panel_top_y

        centro = self.centroPanel(panelX)
        titulo = self.fuenteTituloSeccion.render("Perfil", True, cafeOscuro)
        surface.blit(titulo, titulo.get_rect(center=(centro, top + 72)))

        cerrar = self.botonCerrar
        if self.hoverBotonCerrar:
            cerrar = pygame.transform.smoothscale_by(cerrar, 1.1)
        surface.blit(cerrar, cerrar.get_rect(center=self.rectBotonCerrar(panelX).center))

        pdata = self.perfil_data if self.perfil_data else {}
        cid = pdata.get("character_id", "westcol")
        nombre = pdata.get("nombre", "Protagonista")
        rol = pdata.get("rol", "Creador Consciente")
        niveles = pdata.get("niveles", "0/5")

        card_w = 316
        card_x = centro - card_w // 2
        avatar_card = self._get_ficha_card(card_w, 250).copy()

        portrait_surf = None
        for fn in (f"{cid}_chibi.png", f"{cid}_seleccion_personaje.png"):
            try:
                raw_p = assets.load_cropped_surface(fn)
                pw = max(60, int(round(raw_p.get_width() * (132.0 / max(1, raw_p.get_height())))))
                portrait_surf = pygame.transform.smoothscale(raw_p, (min(140, pw), 132))
                break
            except Exception:
                continue

        if portrait_surf:
            avatar_card.blit(portrait_surf, ((card_w - portrait_surf.get_width()) // 2, 18))

        txt_nom = self.fuenteNombre.render(nombre, True, cafeOscuro)
        avatar_card.blit(txt_nom, txt_nom.get_rect(center=(card_w // 2, 178)))

        txt_rol = self.fuenteDetalleCompacto.render(rol, True, cafe)
        avatar_card.blit(txt_rol, txt_rol.get_rect(center=(card_w // 2, 214)))

        surface.blit(avatar_card, (card_x, top + 148))

        # Ficha única de progreso de campaña (sin repetir Seguidores / Likes / Trofeos del HUD superior)
        prog_card = self._get_ficha_card(card_w, 196).copy()
        t_prog_lbl = self.fuenteNombreCompacto.render("Avance en Barranquilla", True, cafe)
        prog_card.blit(t_prog_lbl, t_prog_lbl.get_rect(center=(card_w // 2, 36)))

        t_prog_val = self.fuenteNombre.render(f"{niveles} distritos", True, (30, 118, 62))
        prog_card.blit(t_prog_val, t_prog_val.get_rect(center=(card_w // 2, 82)))

        consejo = "Vive la ciudad y disfruta el presente."
        rengs = self.partirTexto(consejo, self.fuenteDetalleCompacto, card_w - 42)
        y_c = 132
        for r in rengs[:2]:
            t_r = self.fuenteDetalleCompacto.render(r, True, cafeOscuro)
            prog_card.blit(t_r, t_r.get_rect(center=(card_w // 2, y_c)))
            y_c += 22

        surface.blit(prog_card, (card_x, top + 424))

        pie = self.fuenteDetalleCompacto.render("BarranquillaWare", True, cafe)
        surface.blit(pie, pie.get_rect(center=(centro, top + 705)))
