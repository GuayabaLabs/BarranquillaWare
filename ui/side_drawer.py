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

        # Sección de trofeos que se muestra al tocar Logros
        from core.asset_manager import AssetManager
        assets = AssetManager.get_instance()
        self.seccionActual: str = "botones"
        self.trofeos: List[dict] = []
        self.trofeosObtenidos: List[str] = []
        self.hoverBotonCerrar: bool = False
        self.botonCerrar = assets.cargarSinFondo(os.path.join("Interfaz", "botonX.jpg"), 74)
        self.trofeoColor = assets.cargarTrofeo(120)
        self.trofeoGris = assets.cargarTrofeo(120, enGris=True)
        self.trofeoColorCompacto = assets.cargarTrofeo(78)
        self.trofeoGrisCompacto = assets.cargarTrofeo(78, enGris=True)
        self.fuenteTitulo = assets.cargarFuenteCuento(62)
        self.fuenteNombre = assets.cargarFuenteCuento(34)
        self.fuenteDetalle = assets.cargarFuenteCuento(25)
        self.fuenteNombreCompacto = assets.cargarFuenteCuento(21)
        self.fuenteDetalleCompacto = assets.cargarFuenteCuento(15)
        # Reloj del destello que pasa por los trofeos ganados
        self.tiempoBrillo: float = 0.0

    def _init_buttons(self) -> None:
        """Carga y optimiza los sprites oficiales de cada botón y sus variantes hover."""
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
        return self.anim_t > 0.05

    def handle_event(self, event: pygame.event.Event) -> bool:
        tab_rect = self._get_tab_rect()
        panel_x = self._get_panel_x()
        panel_rect = pygame.Rect(panel_x, self.panel_top_y, self.panel_w, self.panel_h)

        # En la sección de trofeos los botones no responden; el botón X vuelve a ellos
        if self.seccionActual == "trofeos" and self.is_open:
            if self.manejarSeccionTrofeos(event, panel_rect, tab_rect):
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
                        self.active_tab = clicked_id
                        self.audio.play_click()
                        if self.on_nav_selected:
                            self.on_nav_selected(clicked_id)
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

        # Sección de trofeos en lugar de los botones
        if self.seccionActual == "trofeos":
            self.dibujarSeccionTrofeos(surface, panel_x)
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

    def centroPestana(self) -> Tuple[int, int]:
        """Centro de la pestañita del panel, a donde vuela el trofeo ganado."""
        return self._get_tab_rect().center

    def rectBotonCerrar(self, panelX: int) -> pygame.Rect:
        rect = self.botonCerrar.get_rect()
        rect.center = (panelX + 345, self.panel_top_y + 78)
        return rect

    def manejarSeccionTrofeos(self, event: pygame.event.Event, cajaPanel: pygame.Rect, cajaPestana: pygame.Rect) -> bool:
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

    def dibujarSeccionTrofeos(self, surface: pygame.Surface, panelX: int) -> None:
        """Dibuja los trofeos: en gris los que faltan y a color los ganados."""
        cafeOscuro = (92, 56, 34)
        cafe = (118, 76, 44)
        cafeApagado = (160, 138, 118)
        top = self.panel_top_y

        titulo = self.fuenteTitulo.render("Logros", True, cafeOscuro)
        surface.blit(titulo, titulo.get_rect(center=(panelX + 200, top + 75)))

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
        paso_fila = 130 if compacto else 205
        offset_inicio = 135 if compacto else 160
        text_x = (panelX + 130) if compacto else (panelX + 178)
        text_w = 215 if compacto else 205
        trofeo_x = (panelX + 40) if compacto else (panelX + 42)

        for i, trofeo in enumerate(self.trofeos):
            fila = top + offset_inicio + i * paso_fila
            obtenido = trofeo["id"] in self.trofeosObtenidos
            imagen = trofeo_color if obtenido else trofeo_gris
            if obtenido:
                # Cada trofeo ganado se ilumina cada tres segundos, uno después del otro
                progreso = ((self.tiempoBrillo + i * 0.9) % 3.0) * 1.35
                imagen = self.conDestello(imagen, progreso)
            surface.blit(imagen, (trofeo_x, fila + (4 if compacto else 0)))

            nombre = trofeo["nombre"] if obtenido else "Trofeo escondido"
            detalle = trofeo["descripcion"] if obtenido else "Sigue explorando el mapa"
            y = fila + 4
            salto_nombre = 24 if compacto else 38
            salto_detalle = 18 if compacto else 28
            for renglon in self.partirTexto(nombre, f_nombre, text_w):
                texto = f_nombre.render(renglon, True, cafe if obtenido else cafeApagado)
                surface.blit(texto, (text_x, y))
                y += salto_nombre
            y += (4 if compacto else 10)
            for renglon in self.partirTexto(detalle, f_detalle, text_w):
                texto = f_detalle.render(renglon, True, cafeApagado)
                surface.blit(texto, (text_x, y))
                y += salto_detalle

        cuantos = len([t for t in self.trofeos if t["id"] in self.trofeosObtenidos])
        cuenta = f_nombre.render(f"{cuantos} de {len(self.trofeos)} trofeos", True, cafe)
        surface.blit(cuenta, cuenta.get_rect(center=(panelX + 200, top + (695 if compacto else 705))))
