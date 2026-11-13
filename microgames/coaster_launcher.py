"""Puente seguro hacia la versión original del juego Coaster con lapicero.

El Coaster antiguo conserva su lógica y calibración, pero se ejecuta sobre una
superficie embebida en el estado del motor principal.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from typing import Callable, Optional
import pygame

from core.state_machine import BaseState
from core.audio_manager import AudioManager


class CoasterLauncherState(BaseState):
    def __init__(self, on_complete_callback: Optional[Callable[[bool], None]] = None, calibration_only: bool = False) -> None:
        super().__init__()
        self.on_complete_callback = on_complete_callback
        self.calibration_only = calibration_only
        self.game = None
        self.legacy_surface: Optional[pygame.Surface] = None
        self.legacy_level_count = 0
        self.error = ""
        self.font = pygame.font.SysFont("Arial Black, Impact, sans-serif", 34)
        self.font_sub = pygame.font.SysFont("Arial, sans-serif", 20)

    def enter(self, params: Optional[dict] = None) -> None:
        AudioManager.get_instance().play_bgm("tranquilaMusic.mp3")
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Buscar prioritariamente en la carpeta oficial del juego (coaster_game)
        coaster_dir = os.path.join(root, "coaster_game")
        if not os.path.exists(coaster_dir):
            coaster_dir = os.path.join(root, "Project-TBD", "JuegoMontañaRusa")
        coaster_file = os.path.join(coaster_dir, "Coaster.py")
        if not os.path.exists(coaster_file):
            self.error = "No se encontró el juego de Coaster"
            return
        try:
            if coaster_dir not in sys.path:
                sys.path.insert(0, coaster_dir)
            spec = importlib.util.spec_from_file_location("legacy_coaster", coaster_file)
            module = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(module)
            self.legacy_level_count = len(module.niveles)
            self.legacy_surface = pygame.Surface((module.ancho, module.alto))
            self.game = module.Juego(usarCamara=True, pantalla=self.legacy_surface, auto_flip=False)
        except Exception as exc:
            self.error = f"No se pudo abrir Coaster: {exc}"

    def exit(self) -> None:
        if self.game and getattr(self.game, "camara", None):
            self.game.camara.detener()
        self.game = None
        self.legacy_surface = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.game:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._finish(False)
            return
        forwarded = event
        if hasattr(event, "pos"):
            sx = 1100 / 1920
            sy = 700 / 1080
            data = dict(event.__dict__)
            data["pos"] = (int(event.pos[0] * sx), int(event.pos[1] * sy))
            forwarded = pygame.event.Event(event.type, data)
        previous_state = self.game.estado
        previous_level = self.game.numNivel
        previous_won = bool((self.game.resultado or {}).get("gano", False))
        previous_next_label = getattr(getattr(self.game, "botSiguiente", None), "etiqueta", "")
        handled = self.game.manejar(forwarded)
        # El juego legacy usa False para salir solo en QUIT o Q. No convertir
        # una transición de nivel en una salida accidental del estado embebido.
        if not handled and (event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_q)):
            self._finish(False)
            return

        # En la versión original, el botón final reciclaba el nivel 1. En la
        # campaña embebida, completar el último nivel devuelve al mapa.
        if (
            previous_state == "resultado"
            and previous_won
            and self.legacy_level_count > 0
            and previous_level == self.legacy_level_count - 1
            and self.game.estado == "dibujar"
            and self.game.numNivel == 0
            and "volver al mapa" in previous_next_label.casefold()
        ):
            self._finish(True)

    def update(self, dt: float) -> None:
        if self.error:
            return
        if self.game:
            previous_state = self.game.estado
            self.game.actualizar(min(dt, 0.05))
            if self.calibration_only and previous_state == "calibrar" and self.game.estado != "calibrar":
                self._finish(True)

    def _finish(self, won: bool) -> None:
        if self.game and getattr(self.game, "camara", None):
            self.game.camara.detener()
        self.game = None
        if self.on_complete_callback:
            self.on_complete_callback(won)

    def render(self, surface: pygame.Surface) -> None:
        if self.game and self.legacy_surface:
            self.game.dibujar()
            scaled = pygame.transform.smoothscale(self.legacy_surface, surface.get_size())
            surface.blit(scaled, (0, 0))
            return
        surface.fill((18, 24, 40))
        title = "COASTER · LUNA DEL RÍO"
        subtitle = self.error or "La versión original se está ejecutando en su propia ventana."
        hint = "Calibra el lápiz en Coaster · ESC para volver"
        surface.blit(self.font.render(title, True, (255, 220, 80)), (surface.get_width() // 2 - 330, 420))
        surface.blit(self.font_sub.render(subtitle, True, (235, 240, 250)), (surface.get_width() // 2 - 410, 490))
        surface.blit(self.font_sub.render(hint, True, (130, 220, 180)), (surface.get_width() // 2 - 300, 540))


class CoasterCalibrationState(BaseState):
    """Calibrador independiente: no muestra el menú ni el botón Jugar."""
    def __init__(self, on_complete_callback: Optional[Callable[[bool], None]] = None) -> None:
        super().__init__()
        self.on_complete_callback = on_complete_callback
        self.camera = None
        self.module = None
        self.requested = False
        self.saved = False
        self.error = ""
        self.font = pygame.font.SysFont("Arial Black, Impact, sans-serif", 38)
        self.small = pygame.font.SysFont("Arial, sans-serif", 20, bold=True)

    def enter(self, params: Optional[dict] = None) -> None:
        try:
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            folder = os.path.join(root, "coaster_game")
            if not os.path.exists(folder):
                folder = os.path.join(root, "Project-TBD", "JuegoMontañaRusa")
            path = os.path.join(folder, "Coaster.py")
            if folder not in sys.path:
                sys.path.insert(0, folder)
            spec = importlib.util.spec_from_file_location("legacy_coaster_calibration", path)
            self.module = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(self.module)
            self.camera = self.module.Camara(0)
            if not self.camera.abrir():
                self.error = "No se pudo abrir la cámara"
            else:
                self.camera.iniciar()
        except Exception as exc:
            self.error = str(exc)

    def exit(self) -> None:
        if self.camera:
            self.camera.detener()
        self.camera = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._finish(False)
            elif event.key == pygame.K_SPACE and self.camera:
                self.camera.pedido = (0.5, 0.5)
                self.requested = True
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.saved:
                self._finish(True)

    def update(self, dt: float) -> None:
        if self.camera and self.requested and self.camera.rangos:
            self.saved = True

    def _finish(self, ok: bool) -> None:
        if self.on_complete_callback:
            self.on_complete_callback(ok)

    def render(self, surface: pygame.Surface) -> None:
        # Se dibuja igual a la calibración del juego de la montaña rusa
        if self.dibujarComoCoaster(surface):
            return
        surface.fill((18, 24, 40))
        title = self.font.render("CALIBRAR LÁPIZ", True, (255, 220, 80))
        surface.blit(title, title.get_rect(center=(surface.get_width() // 2, 120)))
        preview = None
        if self.camera:
            _, data = self.camera.obtenerVista()
            if data and self.module:
                try:
                    preview = pygame.image.frombuffer(data, self.module.tamVista, "RGB").copy()
                except Exception:
                    preview = None
        # Layout adaptable: la mira debe quedar exactamente sobre el centro
        # de la imagen de cámara, no sobre el centro del panel completo.
        sw, sh = surface.get_size()
        panel_w = min(1500, sw - 120)
        panel_h = min(720, sh - 250)
        box = pygame.Rect(0, 0, panel_w, panel_h)
        box.center = (sw // 2, sh // 2 + 35)
        pygame.draw.rect(surface, (35, 45, 62), box, border_radius=18)
        preview_rect = pygame.Rect(box.x + 55, box.y + 68, int(box.w * 0.62), box.h - 135)
        if preview:
            # Mantener proporción 4:3 y centrarla dentro de su columna.
            target_w = preview_rect.w
            target_h = int(target_w * 3 / 4)
            if target_h > preview_rect.h:
                target_h = preview_rect.h
                target_w = int(target_h * 4 / 3)
            preview = pygame.transform.smoothscale(preview, (target_w, target_h))
            preview_rect = preview.get_rect(center=preview_rect.center)
            surface.blit(preview, preview_rect)
        pygame.draw.rect(surface, (95, 120, 145), preview_rect, 2, border_radius=8)
        pygame.draw.circle(surface, (255, 235, 120), preview_rect.center, min(52, preview_rect.h // 8), 4)
        pygame.draw.circle(surface, (255, 245, 170), preview_rect.center, 5)
        msg = "Coloca el lápiz en el círculo y pulsa ESPACIO" if not self.saved else "Calibración guardada · pulsa ENTER para volver"
        if self.error:
            msg = self.error
        surface.blit(self.small.render(msg, True, (235, 240, 250)), (box.x + 55, box.bottom - 48))
        surface.blit(self.small.render("ESC: cancelar", True, (150, 190, 220)), (box.right - 210, box.bottom - 48))

    def dibujarComoCoaster(self, surface: pygame.Surface) -> bool:
        """Pantalla de calibrar lápiz hecha con los mismos dibujos del juego de la montaña rusa."""
        m = self.module
        if m is None or not hasattr(m, "tarjetaPintada"):
            return False
        if getattr(self, "lienzoCoaster", None) is None:
            self.lienzoCoaster = pygame.Surface((m.ancho, m.alto))
            self.fondoCoaster = m.crearFondo()
            self.fuentesCoaster = {n: m.cargarFuente(n) for n in (20, 26, 36)}
            self.rectVista = pygame.Rect(140, 175, 400, 300)
            self.vistaCamara = None

        s = self.lienzoCoaster
        tiempo = pygame.time.get_ticks() / 1000.0

        def texto(frase, tam, color, punto):
            sup = self.fuentesCoaster[tam].render(frase, True, color)
            s.blit(sup, sup.get_rect(topleft=punto))

        s.blit(self.fondoCoaster, (0, 0))
        m.dibujarNubes(s, tiempo)
        m.tarjetaPintada(s, pygame.Rect(10, 20, 1080, 660))
        texto("Calibra tu lápiz", 36, m.cOscuro, (self.rectVista.x, 100))

        # La cámara va dentro del marco de elementos/marcoCamara; si no hay imagen, sobre un papelito
        hayMarco = m.cargarMarco() is not None
        if not hayMarco:
            m.panel(s, self.rectVista.inflate(24, 24), m.cCrema, m.cOscuro, 22, 3)
        if self.camera:
            _, datos = self.camera.obtenerVista()
            if datos:
                try:
                    self.vistaCamara = pygame.image.frombuffer(datos, m.tamVista, "RGB").copy()
                except Exception:
                    self.vistaCamara = None
        if self.vistaCamara is not None:
            vista = pygame.transform.smoothscale(self.vistaCamara, self.rectVista.size)
            s.blit(vista if hayMarco else m.redondear(vista, 14), self.rectVista)
        else:
            m.lavado(s, m.contornoCaja(self.rectVista, 14), m.mezclar(m.cCrema, m.cMadera, 0.3), 255, 0.1)
        if hayMarco:
            m.dibujarMarcoCamara(s, self.rectVista, 20)
        else:
            m.trazoMano(s, m.contornoCaja(self.rectVista, 14), m.cOscuro, 3, 0.6, 1.0, True)

        centro = self.rectVista.center
        m.circuloMano(s, centro, 26, m.cCrema, 4, 0.8, 1.0)
        m.circuloMano(s, centro, 30, m.cOscuro, 2, 0.8, 2.0)

        frase = "Ubica el objeto en el círculo y pulsa espacio en el teclado para calibrar."
        for i, linea in enumerate(m.partirTexto(frase, self.fuentesCoaster[26], 400)):
            texto(linea, 26, m.cOscuro, (590, 165 + i * 38))

        if self.error:
            estado, color = self.error, m.cCoral
        elif self.camera is None or self.camera.rangos is None:
            estado, color = "Sin calibrar", m.cCoral
        elif self.camera.pos is not None:
            estado, color = "Lápiz detectado", m.cVerde
        else:
            estado, color = "Calibrado, no veo el objeto", m.cAmarillo
        for i, linea in enumerate(m.partirTexto(estado, self.fuentesCoaster[26], 400)):
            texto(linea, 26, color, (590, 350 + i * 38))

        if self.saved:
            frase = "Calibración guardada. Pulsa enter para volver."
        else:
            frase = "Después de calibrar, pulsa enter para volver. Con esc cancelas."
        for i, linea in enumerate(m.partirTexto(frase, self.fuentesCoaster[20], 400)):
            texto(linea, 20, m.cMaderaOsc, (590, 440 + i * 30))

        surface.blit(pygame.transform.smoothscale(s, surface.get_size()), (0, 0))
        return True
