import math
import random
import threading
from typing import Any, Callable, Dict, List, Optional

import pygame

from core.state_machine import BaseState
from effects.juice_particles import dibujarFuego, puntosFigura, paletasFuego, subidaFuego, estallidoFuego, pegarChispa, pegarBrillo
from effects.fuegos_sonido import avisar_estallido, SonidoFuegos

esperaCohete = 0.7
subidaCohete = 1.8
alturaCohete = 95
xCohete = 1150
inicioAclarado = 0.4
duracionAclarado = 2.3
colorNoche = (12, 9, 30)
paletaPersonaje = {"westcol": "morado", "char": "azul", "katherine": "verde", "valdiri": "rosa"}
fuegosFinales = [(-560, 160, "corazon", 180, "rosa", 0.25), (500, 140, "circulo", 190, "dorado", 0.45),
                 (-330, 420, "circulo", 160, "turquesa", 0.7), (300, 400, "corazon", 170, "rojo", 0.9),
                 (-120, 260, "circulo", 210, "morado", 1.15)]


def suave(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class FuegosTransitionState(BaseState):
    CAMERA_POINTER = False
    _draws_voice_badge = True

    def __init__(self, from_scene: BaseState, loader_fn: Callable[[], BaseState]) -> None:
        super().__init__()
        self.from_scene = from_scene
        self.loader_fn = loader_fn
        self.w, self.h = 1920, 1080
        self.t = 0.0

        cid = None
        try:
            cid = from_scene.cards[from_scene.selected_index].char_id
        except Exception:
            pass
        self.paleta = paletaPersonaje.get(cid, "dorado")

        self.velo = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.estrellas = [(random.uniform(0, self.w), random.uniform(0, self.h), random.uniform(0, 6.28),
                           random.choice((1, 1, 2))) for _ in range(110)]

        self.cohete = [float(xCohete), self.h + 60.0]
        self.estela: List[List[float]] = []
        self.estallido: Optional[float] = None
        self.estallidoCentro = (xCohete, alturaCohete)
        self.secundarios: List[Dict[str, Any]] = []
        self.brasas: List[Dict[str, Any]] = []
        self.flash = 0.0
        self.fin = inicioAclarado + duracionAclarado

        self.destino: Optional[BaseState] = None
        self.fotoMapa: Optional[pygame.Surface] = None
        self._resultado: Optional[BaseState] = None
        self._fotoMapa: Optional[pygame.Surface] = None
        self._error: Optional[BaseException] = None
        self._hilo = threading.Thread(target=self._cargar, name="bw-fuegos-loader", daemon=True)
        self._hilo.start()

    @property
    def particles(self):
        return None

    def _cargar(self) -> None:
        try:
            from effects.juice_particles import brillo
            disenos = [("circulo", 400, self.paleta)] + [(f, e, p) for _, _, f, e, p, _ in fuegosFinales]
            for forma, escala, paleta in disenos:
                alcance = max(math.hypot(p[0], p[1]) for p in puntosFigura(forma)) * escala
                brillo(paletasFuego[paleta][1], int(alcance * 1.3))
        except Exception:
            pass
        try:
            escena = self.loader_fn()
            enfocar = getattr(escena, "focus_camera_on_player", None)
            if callable(enfocar):
                try:
                    enfocar(instant=True)
                except Exception:
                    pass
            foto = pygame.Surface((self.w, self.h))
            escena.render(foto)
            self._fotoMapa = foto
            self._resultado = escena
        except BaseException as exc:
            self._error = exc

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def tiempoCohete(self) -> float:
        return self.t - esperaCohete

    def oscuridad(self) -> float:
        if self.estallido is None:
            return suave(self.tiempoCohete() / subidaCohete) ** 0.8
        return 1.0 - suave((self.t - self.estallido - inicioAclarado) / duracionAclarado)

    def update(self, dt: float) -> None:
        self.t += dt
        self.flash = max(0.0, self.flash - dt * 2.2)
        tc = self.tiempoCohete()

        if self.estallido is None and self.oscuridad() < 1.0:
            self.from_scene.update(dt)

        for fuego in self.secundarios:
            fuego["t"] += dt
            avisar_estallido(fuego["clave"], fuego["t"], subidaFuego)

        if self.destino is None and not self._hilo.is_alive():
            if self._error is not None:
                raise self._error
            self.destino = self._resultado
            self.fotoMapa = self._fotoMapa

        if self.estallido is None and tc > 0:
            avance = min(1.0, tc / subidaCohete)
            y = self.h + 60 - (self.h + 60 - alturaCohete) * (1 - (1 - avance) ** 2.2)
            if tc > subidaCohete:
                y = alturaCohete - min(45.0, (tc - subidaCohete) * 20)
            self.cohete = [xCohete + math.sin(self.t * 5.5) * 6, y]
            self.estela.append([self.cohete[0] + random.uniform(-3, 3), self.cohete[1], 0.0])
            if tc >= subidaCohete and self.destino is not None:
                self.estallar()
        for punto in self.estela:
            punto[2] += dt
        self.estela = [p for p in self.estela if p[2] < 0.8]

        for brasa in self.brasas:
            brasa["vy"] += 480 * dt
            brasa["x"] += brasa["vx"] * dt
            brasa["y"] += brasa["vy"] * dt
            brasa["vx"] *= 0.985
            brasa["vida"] -= dt
        self.brasas = [b for b in self.brasas if b["vida"] > 0]

        if self.estallido is not None and self.t - self.estallido >= self.fin:
            if self.state_machine and self.destino:
                self.state_machine.change_state(self.destino)

    def estallar(self) -> None:
        self.estallido = self.t
        self.estallidoCentro = (int(self.cohete[0]), int(self.cohete[1]))
        self.flash = 1.0
        SonidoFuegos.get().estallar()
        try:
            __import__("core.audio_manager", fromlist=["AudioManager"]).AudioManager.get_instance().fadeout_music(1800)
        except pygame.error:
            pass
        cx, cy = self.estallidoCentro
        marca = random.random()
        ultimo = 0.0
        for i, (dx, dy, forma, escala, paleta, retraso) in enumerate(fuegosFinales):
            self.secundarios.append({"centro": (cx + dx, cy + dy), "forma": forma, "escala": escala, "paleta": paleta,
                                     "t": -retraso, "desdeY": self.h + 80, "clave": ("transicion", marca, i)})
            ultimo = max(ultimo, retraso)
        self.fin = max(inicioAclarado + duracionAclarado, ultimo + subidaFuego + estallidoFuego + 0.05)
        colores = paletasFuego[self.paleta]
        for _ in range(90):
            angulo = random.uniform(0, math.tau)
            rapidez = random.uniform(180, 700)
            self.brasas.append({"x": cx, "y": cy, "vx": math.cos(angulo) * rapidez, "vy": math.sin(angulo) * rapidez - 80,
                                "vida": random.uniform(1.3, 1.9), "color": random.choice(colores[1:]),
                                "r": random.choice((2, 3, 3, 4))})

    def render(self, surface: pygame.Surface) -> None:
        oscuro = self.oscuridad()
        if self.estallido is None:
            if oscuro >= 1.0:
                surface.fill(colorNoche)
            else:
                self.from_scene.render(surface)
                if oscuro > 0.0:
                    self.velo.fill((*colorNoche, int(255 * oscuro)))
                    surface.blit(self.velo, (0, 0))
        else:
            if self.fotoMapa is not None and oscuro < 1.0:
                surface.blit(self.fotoMapa, (0, 0))
                self.velo.fill((*colorNoche, int(255 * oscuro)))
                surface.blit(self.velo, (0, 0))
            else:
                surface.fill(colorNoche)

        if oscuro > 0.4:
            fuerza = (oscuro - 0.4) / 0.6
            for x, y, fase, r in self.estrellas:
                luz = (140 + 90 * math.sin(self.t * 3 + fase)) * fuerza
                if luz > 20:
                    pygame.draw.circle(surface, (int(luz), int(luz), min(255, int(luz) + 30)), (int(x), int(y)), r)

        claro = paletasFuego[self.paleta][2]
        for punto in self.estela:
            vida = 1.0 - punto[2] / 0.8
            pegarChispa(surface, (punto[0], punto[1] + 30 * punto[2] ** 2), claro, 3, 220 * vida)
        if self.estallido is None:
            if self.tiempoCohete() > 0:
                pegarBrillo(surface, self.cohete, paletasFuego[self.paleta][1], 60, 0.9)
                pegarChispa(surface, self.cohete, (255, 250, 230), 7)
        else:
            tiempo = self.t - self.estallido
            dibujarFuego(surface, self.estallidoCentro, puntosFigura("circulo"), 400, subidaFuego + tiempo,
                         paletasFuego[self.paleta], self.estallidoCentro[1], duracion=2.1, tamChispa=7,
                         detalle=True, chispitas=True)
            for fuego in self.secundarios:
                if fuego["t"] >= 0:
                    dibujarFuego(surface, fuego["centro"], puntosFigura(fuego["forma"]), fuego["escala"], fuego["t"],
                                 paletasFuego[fuego["paleta"]], fuego["desdeY"], tamChispa=5)
            for brasa in self.brasas:
                alfa = 255 * min(1.0, brasa["vida"] / 0.5)
                pegarChispa(surface, (brasa["x"], brasa["y"]), brasa["color"], brasa["r"], alfa)

        if self.flash > 0:
            self.velo.fill((255, 245, 225, int(130 * self.flash)))
            surface.blit(self.velo, (0, 0))
