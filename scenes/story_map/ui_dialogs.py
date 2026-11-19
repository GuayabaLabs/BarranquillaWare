"""
BarranquillaWare - Componente de Interfaz y Diálogos del Mapa
Renderizado de globos de diálogo (Paloma de Curramba), diálogos de bienvenida,
tarjetas de misión (Quest Card) y modal de victoria final.
"""
import math
from typing import Optional, List
import pygame
from ui.button import UIButton
import os
from typing import Tuple
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from effects.juice_particles import JuiceParticleManager, FuegosArtificiales, pegarBrillo, brillo


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
        talk_frames: Optional[List[pygame.Surface]] = None,
        is_talking: Optional[bool] = None,
    ) -> None:
        """Renderiza el cuadro de diálogo acuarela oficial con paloma animada modulando pico y pestañeo."""
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

        # Selección de frame animado de la Paloma (pico sincronizado con voz activa + pestañeo natural)
        talking = is_talking if is_talking is not None else AudioManager.get_instance().is_voice_playing()
        if talk_frames and len(talk_frames) >= 4 and anim > 0.05:
            blink_c = timer % 3.8
            if blink_c < 0.16:
                pal_surf = talk_frames[3]
            elif talking:
                step = int((timer * 6.2) % 4)
                pal_surf = talk_frames[[0, 1, 2, 1][step]]
            else:
                pal_surf = talk_frames[0]
        else:
            pal_surf = portrait_surf
        pal_w, pal_h = pal_surf.get_size()

        box_surf = dialog_box_surf.copy()
        bw, bh = box_surf.get_size()

        total_x = (self.screen_w - bw) // 2 + 85
        total_y = self.screen_h - bh - 18 + int((1.0 - anim) * 45)

        pal_x = total_x - int(pal_w * 0.72)
        pal_y = total_y + bh - pal_h - 36 + bob_y

        speaker_txt = font_speaker.render(speaker, True, (92, 46, 118))
        anchoFranja = int(bw * 0.23)
        if speaker_txt.get_width() > anchoFranja:
            speaker_txt = pygame.transform.smoothscale_by(speaker_txt, anchoFranja / float(speaker_txt.get_width()))
        box_surf.blit(speaker_txt, speaker_txt.get_rect(center=(int(bw * 0.306), int(bh * 0.228))))

        start_y = int(bh * 0.43)
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

        txt_vs = font_v_sub.render("¡COMPLETASTE LOS 5 NIVELES DE LA HISTORIA!", True, (255, 255, 255))
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
            "Campus Uninorte, C.C. Buenavista, Estadio Metropolitano,",
            "Aeropuerto Cortissoz y la Aleta del Tiburón.",
            "¡La ciudad brilla más bonito cuando disfrutas el presente al ritmo de la brisa!"
        ]
        dy = 258
        for d in desc:
            txt_d = font_v_body.render(d, True, (200, 215, 240))
            vic_surf.blit(txt_d, txt_d.get_rect(center=(vw // 2, dy)))
            dy += 26

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


class AvisoTrofeo:
    """Ventana de ¡Qué nota! que sale al ganar un trofeo escondido del mapa."""

    def __init__(self, screen_w: int = 1920, screen_h: int = 1080) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        self.ventana = assets.cargarSinFondo(os.path.join("Interfaz", "VentanaAviso.jpg"), 1000)
        self.trofeo = assets.cargarTrofeo(210)
        self.botonCerrar = self.ponerBorde(assets.cargarSinFondo(os.path.join("Interfaz", "botonX.jpg"), 92))
        self.fuenteFelicidades = assets.cargarFuenteCuento(42)
        self.fuenteNombre = assets.cargarFuenteCuento(58)

        self.cajaVentana = self.ventana.get_rect(center=(screen_w // 2, screen_h // 2))
        # La X va por fuera de la ventana, sobre la esquina de arriba a la derecha
        self.cajaCerrar = self.botonCerrar.get_rect(center=(self.cajaVentana.right - 4, self.cajaVentana.top + 36))
        # El trofeo flota más abajo para no tocar el letrero de ¡Qué nota!
        self.centroTrofeo = (self.cajaVentana.centerx, self.cajaVentana.top + 262)

        self.fuegos = FuegosArtificiales()
        self.chispas = JuiceParticleManager()

        # Se preparan de una vez los resplandores para que la ventana no se trabe al aparecer
        brillo((255, 220, 130), 150)
        brillo((255, 214, 110), 70)
        self.fuegos.prepararBrillos()

        self.abierto: bool = False
        self.entrada: float = 0.0          # 0 escondida, 1 del todo visible
        self.tiempo: float = 0.0
        self.tarjeta: Optional[pygame.Surface] = None
        self.hoverCerrar: bool = False
        self.vuelo: float = -1.0           # segundos que lleva volando el trofeo; -1 si no vuela
        self.duracionVuelo: float = 1.1
        self.destinoVuelo: Tuple[int, int] = (24, 584)
        self.brilloLlegada: float = 0.0

    def abrir(self, nombreTrofeo: str, destino: Tuple[int, int]) -> None:
        """Muestra la ventana con el nombre del trofeo y prende los fuegos."""
        self.destinoVuelo = destino
        self.abierto = True
        self.entrada = 0.0
        self.tiempo = 0.0
        self.vuelo = -1.0
        self.hoverCerrar = False

        # Se escribe el texto una sola vez sobre una copia de la ventana
        cafe = (110, 68, 38)
        cafeOscuro = (86, 50, 28)
        self.tarjeta = self.ventana.copy()
        # Un poco a la izquierda del centro para no tocar las flores de abajo
        centroTexto = self.tarjeta.get_width() // 2
        for texto, fuente, color, alto in (("¡Felicidades! Obtuviste el trofeo:", self.fuenteFelicidades, cafe, 396),
                                           (nombreTrofeo, self.fuenteNombre, cafeOscuro, 450)):
            letras = fuente.render(texto, True, color)
            caja = letras.get_rect(center=(centroTexto, alto))
            libre = self.mitadLibre(centroTexto, caja.top + 6, caja.bottom - 4)
            if letras.get_width() / 2.0 > libre:
                letras = pygame.transform.smoothscale_by(letras, libre * 2.0 / letras.get_width())
            self.tarjeta.blit(letras, letras.get_rect(center=(centroTexto, alto)))

        self.fuegos.lanzarAlrededor(self.cajaVentana)
        self.audio.play_win()

    def mitadLibre(self, centro: int, arriba: int, abajo: int) -> float:
        import numpy
        if getattr(self, "colorVentana", None) is None:
            rgb = pygame.surfarray.array3d(self.ventana).astype(numpy.int16)
            self.colorVentana = (rgb.max(axis=2) - rgb.min(axis=2)) > 90
        manchas = self.colorVentana
        ancho = manchas.shape[0]
        libre = ancho / 2.0
        for y in range(max(0, arriba), min(manchas.shape[1], abajo), 3):
            fila = manchas[:, y]
            derecha = next((x for x in range(centro, ancho) if fila[x]), ancho)
            izquierda = next((x for x in range(centro, -1, -1) if fila[x]), 0)
            libre = min(libre, derecha - centro, centro - izquierda)
        return max(40.0, libre - 14)

    def ponerBorde(self, imagen: pygame.Surface) -> pygame.Surface:
        """Le pone a la imagen un borde blanco de calcomanía con una línea fina de tinta café por fuera."""
        grosorBlanco = 6
        grosorTinta = 3
        margen = grosorBlanco + grosorTinta
        ancho, alto = imagen.get_size()
        conBorde = pygame.Surface((ancho + margen * 2, alto + margen * 2), pygame.SRCALPHA)

        silueta = pygame.mask.from_surface(imagen, 100)
        tinta = silueta.to_surface(setcolor=(86, 50, 28, 255), unsetcolor=(0, 0, 0, 0))
        blanco = silueta.to_surface(setcolor=(255, 252, 244, 255), unsetcolor=(0, 0, 0, 0))

        # Se pega la silueta corrida en círculo para que el borde salga parejo
        for capa, radio in ((tinta, margen), (blanco, grosorBlanco)):
            for grados in range(0, 360, 15):
                dx = round(math.cos(math.radians(grados)) * radio)
                dy = round(math.sin(math.radians(grados)) * radio)
                conBorde.blit(capa, (margen + dx, margen + dy))
        conBorde.blit(imagen, (margen, margen))
        return conBorde

    def cerrar(self) -> None:
        """Cierra la ventana y manda el trofeo volando hasta el panel de logros."""
        if not self.abierto:
            return
        self.abierto = False
        self.hoverCerrar = False
        self.fuegos.apagar()
        self.vuelo = 0.0
        self.audio.play_click()

    def estaOcupado(self) -> bool:
        return self.abierto or self.vuelo >= 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.abierto:
            return
        if event.type == pygame.MOUSEMOTION:
            estaba = self.hoverCerrar
            self.hoverCerrar = self.cajaCerrar.collidepoint(event.pos)
            if self.hoverCerrar and not estaba:
                self.audio.play_hover()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.cajaCerrar.collidepoint(event.pos):
                self.cerrar()
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_x):
            self.cerrar()
        elif event.type == pygame.JOYBUTTONDOWN and event.button in (0, 1, 2, 3, 6, 7):
            self.cerrar()

    def posicionVuelo(self) -> Tuple[float, float, float]:
        """Dónde va el trofeo en su viaje: hace una curva hacia arriba y baja hasta la pestaña."""
        t = max(0.0, min(1.0, self.vuelo / self.duracionVuelo))
        suave = t * t * (3.0 - 2.0 * t)
        x0, y0 = self.centroTrofeo
        x1, y1 = x0 - 160, y0 - 360
        x2, y2 = self.destinoVuelo
        x = (1 - suave) ** 2 * x0 + 2 * (1 - suave) * suave * x1 + suave ** 2 * x2
        y = (1 - suave) ** 2 * y0 + 2 * (1 - suave) * suave * y1 + suave ** 2 * y2
        escala = 1.0 - 0.86 * suave
        return x, y, escala

    def update(self, dt: float) -> None:
        self.tiempo += dt
        self.fuegos.update(dt)
        self.chispas.update(dt)

        if self.abierto:
            self.entrada = min(1.0, self.entrada + dt / 0.35)
            if self.tiempo >= 6.0:
                self.cerrar()
        else:
            self.entrada = max(0.0, self.entrada - dt / 0.25)

        if self.vuelo >= 0.0:
            self.vuelo += dt
            x, y, _ = self.posicionVuelo()
            self.chispas.emit_sparks((x, y), count=1)
            if self.vuelo >= self.duracionVuelo:
                # Llegó al panel: destello y chispas en la pestaña
                self.vuelo = -1.0
                self.brilloLlegada = 1.0
                self.chispas.emit_sparks(self.destinoVuelo, count=14)
                self.audio.play_hover()

        self.brilloLlegada = max(0.0, self.brilloLlegada - dt * 1.3)

    def render(self, surface: pygame.Surface) -> None:
        if self.entrada > 0.0:
            # Oscurece el mapa con un tono morado multiplicando sus colores (más rápido que una capa transparente)
            tono = [int(255 - (255 - c) * self.entrada) for c in (128, 120, 142)]
            surface.fill(tono, special_flags=pygame.BLEND_RGB_MULT)

        # Los fuegos van detrás de la ventana para que la rodeen
        self.fuegos.render(surface)

        if self.entrada > 0.0 and self.tarjeta is not None:
            self.dibujarVentana(surface)

        if self.vuelo >= 0.0:
            x, y, escala = self.posicionVuelo()
            giro = math.sin(min(1.0, self.vuelo / self.duracionVuelo) * math.pi) * 18.0
            volando = pygame.transform.rotozoom(self.trofeo, giro, escala)
            surface.blit(volando, volando.get_rect(center=(int(x), int(y))))

        self.chispas.render(surface)

        if self.brilloLlegada > 0.0:
            pegarBrillo(surface, self.destinoVuelo, (255, 214, 110), 70, self.brilloLlegada)

    def dibujarVentana(self, surface: pygame.Surface) -> None:
        # Entra creciendo con un rebotico y sale encogiéndose
        t = self.entrada
        escala = 0.8 + 0.2 * (1 - (1 - t) ** 3) + 0.04 * math.sin(t * math.pi)
        centro = self.cajaVentana.center

        if abs(escala - 1.0) > 0.005 or t < 1.0:
            tarjeta = pygame.transform.smoothscale_by(self.tarjeta, escala)
            tarjeta.set_alpha(int(255 * t))
        else:
            tarjeta = self.tarjeta
        surface.blit(tarjeta, tarjeta.get_rect(center=centro))

        # El trofeo flota sobre la ventana con un resplandor dorado detrás
        if self.vuelo < 0.0:
            dx = (self.centroTrofeo[0] - centro[0]) * escala
            dy = (self.centroTrofeo[1] - centro[1]) * escala + math.sin(self.tiempo * 2.4) * 6.0
            posTrofeo = (int(centro[0] + dx), int(centro[1] + dy))
            pegarBrillo(surface, posTrofeo, (255, 220, 130), 150, (0.45 + 0.15 * math.sin(self.tiempo * 3.0)) * t)
            trofeo = self.trofeo
            if abs(escala - 1.0) > 0.005 or t < 1.0:
                trofeo = pygame.transform.smoothscale_by(self.trofeo, escala)
                trofeo.set_alpha(int(255 * t))
            surface.blit(trofeo, trofeo.get_rect(center=posTrofeo))

        # Botón X en la esquina de arriba a la derecha
        if self.abierto:
            dx = (self.cajaCerrar.centerx - centro[0]) * escala
            dy = (self.cajaCerrar.centery - centro[1]) * escala
            boton = self.botonCerrar
            crecer = escala * (1.1 if self.hoverCerrar else 1.0)
            if abs(crecer - 1.0) > 0.005:
                boton = pygame.transform.smoothscale_by(self.botonCerrar, crecer)
            surface.blit(boton, boton.get_rect(center=(int(centro[0] + dx), int(centro[1] + dy))))
