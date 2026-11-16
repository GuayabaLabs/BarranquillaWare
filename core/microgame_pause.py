from __future__ import annotations

from typing import Callable, Optional, List, Dict, Any
import pygame

from core.state_machine import BaseState
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.map_settings import MapSettingsState


class MicrogamePauseState(BaseState):
    """
    Menú de pausa unificado para minijuegos y mapa general.
    Utiliza los assets oficiales de recuadro y botones:
    - Continuar / Reanudar
    - Opciones / Ajustes (despliega MapSettingsState sin perder el estado pausado)
    - Reiniciar minijuego (si está disponible en el contexto)
    - Volver al mapa / Salir
    """
    def __init__(
        self,
        previous: BaseState,
        return_callback: Optional[Callable[[], None]] = None,
        restart_callback: Optional[Callable[[], None]] = None,
        menu_callback: Optional[Callable[[], None]] = None,
        save_callback: Optional[Callable[[], None]] = None,
        on_calibrate: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.previous = previous
        self.return_callback = return_callback
        self.restart_callback = restart_callback
        self.menu_callback = menu_callback
        self.save_callback = save_callback
        self.calibrate_callback = on_calibrate

        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        self.selected = 0
        self.items: List[Dict[str, Any]] = [
            {"id": "resume", "label": "CONTINUAR", "asset": "boton_continuar_menu_pausa.png"},
            {"id": "options", "label": "OPCIONES", "asset": "boton_opciones_menu_pausa.png"},
        ]
        if self.restart_callback:
            self.items.append({"id": "restart", "label": "REINICIAR", "asset": "boton_reiniciar_menu_pausa.png"})
        if self.save_callback:
            self.items.append({"id": "save", "label": "GUARDAR PARTIDA", "asset": None})
        if self.calibrate_callback:
            self.items.append({"id": "calibrate", "label": "CALIBRAR CÁMARA", "asset": None})
        if self.return_callback:
            self.items.append({"id": "map", "label": "VOLVER AL MAPA", "asset": None})
        if self.menu_callback:
            self.items.append({"id": "menu", "label": "SALIR AL MENÚ", "asset": "boton_salir_menu_pausa.png"})

        # Tipografías y geometría de la ventana
        self.font_item = pygame.font.SysFont("Arial Black, Impact, sans-serif", 24)
        self.font_hint = pygame.font.SysFont("Arial, sans-serif", 16, bold=True)

        self.box_w = 640
        self.box_h = 620
        self.btn_w = 400
        self.btn_h = 72

        # Cargar y pre-escalar texturas oficiales
        self.save_feedback_timer: float = 0.0
        self.bg_box: Optional[pygame.Surface] = None
        self.button_surfs: Dict[str, pygame.Surface] = {}
        self._load_assets()

    def _load_assets(self) -> None:
        try:
            raw_box = self.assets.load_surface("recuadro_menu_pausa.png", has_alpha=True)
            self.bg_box = pygame.transform.smoothscale(raw_box, (self.box_w, self.box_h))
        except Exception:
            self.bg_box = None

        for it in self.items:
            if not it["asset"]:
                self.button_surfs[it["id"]] = None
                continue
            try:
                raw_btn = self.assets.load_surface(it["asset"], has_alpha=True)
                self.button_surfs[it["id"]] = pygame.transform.smoothscale(raw_btn, (self.btn_w, self.btn_h))
            except Exception:
                self.button_surfs[it["id"]] = None

    def handle_event(self, event: pygame.event.Event) -> None:
        # Con la ventana nueva, el mouse busca los botones en su nuevo lugar
        cajas = self.cajasBotones()
        if cajas and event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            for i, caja in enumerate(cajas):
                if caja.collidepoint(event.pos):
                    if event.type == pygame.MOUSEMOTION:
                        if self.selected != i:
                            self.selected = i
                            self.audio.play_click()
                    elif event.button == 1:
                        self.selected = i
                        self._choose()
                    break
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.items)
                self.audio.play_click()
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.items)
                self.audio.play_click()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._choose()
            elif event.key == pygame.K_ESCAPE:
                self._resume()

        elif event.type == pygame.MOUSEMOTION:
            # Detección de hover por cursor
            box_x = (1920 - self.box_w) // 2
            box_y = (1080 - self.box_h) // 2
            start_y = box_y + 90
            spacing = min(92, (self.box_h - 140) // max(1, len(self.items)))
            for i in range(len(self.items)):
                btn_rect = pygame.Rect((1920 - self.btn_w) // 2, start_y + i * spacing, self.btn_w, self.btn_h)
                if btn_rect.collidepoint(event.pos):
                    if self.selected != i:
                        self.selected = i
                        self.audio.play_click()
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            box_x = (1920 - self.box_w) // 2
            box_y = (1080 - self.box_h) // 2
            start_y = box_y + 90
            spacing = min(92, (self.box_h - 140) // max(1, len(self.items)))
            for i in range(len(self.items)):
                btn_rect = pygame.Rect((1920 - self.btn_w) // 2, start_y + i * spacing, self.btn_w, self.btn_h)
                if btn_rect.collidepoint(event.pos):
                    self.selected = i
                    self._choose()
                    break

        elif event.type == pygame.JOYHATMOTION and event.value[1] != 0:
            if event.value[1] > 0:
                self.selected = (self.selected - 1) % len(self.items)
            else:
                self.selected = (self.selected + 1) % len(self.items)
            self.audio.play_click()

        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0:  # Botón A
                self._choose()
            elif event.button in (1, 6, 7):  # Botón B o Start
                self._resume()

    def _resume(self) -> None:
        self.audio.play_click()
        if self.state_machine:
            self.state_machine.pop_state()

    def _open_options(self) -> None:
        self.audio.play_click()
        if self.state_machine:
            on_cal = self._on_calibrate_from_options if self.calibrate_callback else None
            self.state_machine.push_state(MapSettingsState(on_calibrate=on_cal))

    def _on_calibrate_from_options(self) -> None:
        if self.state_machine:
            self.state_machine.pop_state()
        if self.calibrate_callback:
            self.calibrate_callback()

    def _choose(self) -> None:
        current_id = self.items[self.selected]["id"]
        if current_id == "resume":
            self._resume()
        elif current_id == "options":
            self._open_options()
        elif current_id == "restart":
            self.audio.play_click()
            if self.restart_callback:
                self.restart_callback()
        elif current_id == "map":
            self.audio.play_click()
            if self.return_callback:
                self.return_callback()
        elif current_id == "menu":
            self.audio.play_click()
            if self.menu_callback:
                self.menu_callback()
        elif current_id == "save":
            self.audio.play_click()
            self.save_feedback_timer = 3.0
            if self.save_callback:
                self.save_callback()
        elif current_id == "calibrate":
            self.audio.play_click()
            if self.calibrate_callback:
                self.calibrate_callback()

    def update(self, dt: float) -> None:
        if self.save_feedback_timer > 0.0:
            self.save_feedback_timer = max(0.0, self.save_feedback_timer - dt)

    def render(self, surface: pygame.Surface) -> None:
        # Ventana de pausa nueva con botones morados que se ponen rojos al pasar por encima
        if self.dibujarPausa(surface):
            return

        # Renderiza el estado de fondo congelado
        self.previous.render(surface)

        # Cortina oscura translúcida
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((8, 12, 25, 185))
        surface.blit(veil, (0, 0))

        box_x = (surface.get_width() - self.box_w) // 2
        box_y = (surface.get_height() - self.box_h) // 2
        box_rect = pygame.Rect(box_x, box_y, self.box_w, self.box_h)

        if self.bg_box:
            surface.blit(self.bg_box, (box_x, box_y))
        else:
            pygame.draw.rect(surface, (20, 26, 44), box_rect, border_radius=24)
            pygame.draw.rect(surface, (245, 195, 75), box_rect, width=4, border_radius=24)

        start_y = box_y + 90
        spacing = min(92, (self.box_h - 140) // max(1, len(self.items)))

        for i, it in enumerate(self.items):
            item_id = it["id"]
            btn_x = (surface.get_width() - self.btn_w) // 2
            btn_y = start_y + i * spacing
            btn_rect = pygame.Rect(btn_x, btn_y, self.btn_w, self.btn_h)

            surf = self.button_surfs.get(item_id)
            if surf:
                if i == self.selected:
                    # Resaltado brillante para botón seleccionado
                    glow_rect = btn_rect.inflate(12, 12)
                    glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(glow_surf, (255, 230, 110, 140), (0, 0, glow_rect.width, glow_rect.height), border_radius=18)
                    surface.blit(glow_surf, glow_rect.topleft)

                surface.blit(surf, (btn_x, btn_y))
            else:
                # Fallback procedimental con buen contraste
                fill = (245, 195, 75) if i == self.selected else (45, 58, 85)
                color = (30, 30, 35) if i == self.selected else (240, 245, 255)
                pygame.draw.rect(surface, fill, btn_rect, border_radius=14)
                txt = self.font_item.render(it["label"], True, color)
                surface.blit(txt, txt.get_rect(center=btn_rect.center))

        hint = self.font_hint.render("↑ ↓ / CLICK ELEGIR  ·  ENTER/A ACEPTAR  ·  ESC REANUDAR", True, (240, 245, 255))
        surface.blit(hint, hint.get_rect(center=(surface.get_width() // 2, box_y + self.box_h - 38)))

    def prepararPausa(self) -> bool:
        """Carga una sola vez la ventana y los botones nuevos. Devuelve False si falta alguna imagen."""
        if getattr(self, "pausaLista", None) is not None:
            return self.pausaLista
        try:
            import os
            ventana = self.assets.cargarSinFondo(os.path.join("Interfaz", "ventanaMenuPausa.jpg"), 660)
            self.ventanaPausa = pygame.transform.smoothscale_by(ventana, 1080 / float(ventana.get_height()))
            # El papel de la ventana va del 18% al 83% del ancho; su centro queda un poco a la derecha
            anchoVentana = self.ventanaPausa.get_width()
            self.centroPapel = 960 - anchoVentana // 2 + int(anchoVentana * 0.508)
            self.botonMorado = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonMorado.jpg"), 300)
            rojo = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonRojo.jpg"), 300)
            # El rojo crece un poquito para que se note cuál está elegido
            self.botonRojo = pygame.transform.smoothscale_by(rojo, 1.05)
            self.fuenteTituloPausa = self.assets.cargarFuenteCuento(84)
            self.fuenteBotonPausa = self.assets.cargarFuenteCuento(44)
            self.fuenteEstadoPausa = self.assets.cargarFuenteCuento(22)
            self.fuenteAyudaPausa = self.assets.cargarFuenteCuento(28)
            self.pausaLista = True
        except Exception as e:
            print(f"Aviso: no se pudo cargar la ventana de pausa: {e}")
            self.pausaLista = False
        return self.pausaLista

    def cajasBotones(self) -> list:
        """Lugar de cada botón dentro de la ventana nueva (lista vacía si no hay ventana nueva)."""
        if not self.prepararPausa():
            return []
        alto = self.botonMorado.get_height()
        separacion = 10
        total = len(self.items) * alto + (len(self.items) - 1) * separacion
        centro_y = 600 if self.save_callback else 590
        arriba = centro_y - total // 2
        cajas = []
        for i in range(len(self.items)):
            caja = self.botonMorado.get_rect(midtop=(self.centroPapel, arriba + i * (alto + separacion)))
            cajas.append(caja)
        return cajas

    def textoConContorno(self, fuente, texto: str, color, colorContorno) -> pygame.Surface:
        # Texto con un contorno parejo alrededor para que se lea sobre el botón
        cuerpo = fuente.render(texto, True, color)
        borde = fuente.render(texto, True, colorContorno)
        lienzo = pygame.Surface((cuerpo.get_width() + 6, cuerpo.get_height() + 6), pygame.SRCALPHA)
        for dx in (-3, -2, 0, 2, 3):
            for dy in (-3, -2, 0, 2, 3):
                if abs(dx) + abs(dy) >= 3:
                    lienzo.blit(borde, (3 + dx, 3 + dy))
        lienzo.blit(cuerpo, (3, 3))
        return lienzo

    def dibujarPausa(self, surface: pygame.Surface) -> bool:
        if not self.prepararPausa():
            return False

        self.previous.render(surface)
        # Oscurece el juego congelado multiplicando sus colores
        surface.fill((104, 98, 122), special_flags=pygame.BLEND_RGB_MULT)

        if self.state_machine and self.state_machine.current_state is not self:
            return True

        ventana = self.ventanaPausa.get_rect(center=(960, 540))
        surface.blit(self.ventanaPausa, ventana)

        cajas = self.cajasBotones()
        primerBoton = cajas[0].top if cajas else ventana.top + 400
        ultimoBoton = cajas[-1].bottom if cajas else ventana.top + 760
        espacioEstado = 40 if self.save_callback else 0
        titulo = self.textoConContorno(self.fuenteTituloPausa, "Pausa", (110, 62, 150), (255, 250, 238))
        surface.blit(titulo, titulo.get_rect(midbottom=(self.centroPapel, primerBoton - 44 - espacioEstado)))

        if self.save_callback:
            if self.save_feedback_timer > 0.0:
                estado_txt = "Partida guardada — Retoma en Cargar Partida"
                estado_col = (38, 134, 68)
            else:
                estado_txt = "Auto-guardado activo tras cada misión"
                estado_col = (116, 76, 48)
            estado_surf = self.fuenteEstadoPausa.render(estado_txt, True, estado_col)
            surface.blit(estado_surf, estado_surf.get_rect(center=(self.centroPapel, primerBoton - 26)))

        for i, caja in enumerate(cajas):
            elegido = i == self.selected
            boton = self.botonRojo if elegido else self.botonMorado
            surface.blit(boton, boton.get_rect(center=caja.center))
            contorno = (120, 26, 34) if elegido else (70, 30, 110)
            # Solo la primera letra en mayúscula
            etiqueta = self.items[i]["label"].capitalize()
            texto = self.textoConContorno(self.fuenteBotonPausa, etiqueta, (255, 248, 236), contorno)
            surface.blit(texto, texto.get_rect(center=(caja.centerx, caja.centery - 3)))

        # Ayuda corta debajo de los botones, centrada en el papel
        for i, linea in enumerate(("Enter para aceptar", "Esc para seguir")):
            ayuda = self.fuenteAyudaPausa.render(linea, True, (126, 90, 62))
            surface.blit(ayuda, ayuda.get_rect(midtop=(self.centroPapel, max(ventana.top + 790, ultimoBoton + 16) + i * 30)))
        return True
