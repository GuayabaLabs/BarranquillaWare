"""CurramGram Go! — minijuego del Aeropuerto Cortissoz (única versión del juego).

Relación con redes sociales: Cami es creadora de contenido en el Aeropuerto Cortissoz y cada
persona es un caso real de redes (desinformación, sobreexposición de datos, exposición sin
consentimiento, noticia falsa viral, contenido viral y escrache digital). Antes de publicar
debe confirmar, proteger la privacidad y pedir ayuda a la autoridad en vez de exponer a alguien.

Archivos:
- Este archivo: el minijuego dentro de BarranquillaWare (pausa, barra de tiempo, audio, mando, cámara).
- microgames/curramgram/juego.py: la lógica y el dibujo del recorrido.
- assets/curramgram/: sprites y animaciones.

Probarlo solo (desde la raíz del proyecto):  python microgames/curramgram_go.py

Controles:
- Teclado: A/D o flechas caminar · ESPACIO saltar · S/↓ esconderse · E avisar · clic o F foto · P publicar.
- Mando: stick/D-pad caminar · A saltar · ↓ esconderse · X avisar · B foto · Y publicar.
- Cámara: el lapicero apunta la foto; mantener quieto o pellizcar dispara.
"""
if __name__ == "__main__":  # Permite ejecutarlo solo: agrega la raíz del proyecto a sys.path
    import os
    import sys
    _RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _RAIZ)
    os.chdir(_RAIZ)

from typing import Callable, Optional

import pygame

from core import input_state
from core.microgame import BaseMicrogame
from microgames.curramgram import juego as _curram
from microgames.redes_comun import HeldKeys, load_managed_sound

# AUDIO PROPIO (assets/). El sello está en SFX_SELLO de microgames/curramgram/juego.py.
MUSIC_TRACK = "curramgram_musica.mp3"
# Efectos por momento: (archivo, volumen relativo, duración máxima en s). Se recortan al cargar.
SFX = {
    "salto": ("curramgram_salto.mp3", 0.8, 0.9),
    "tropiezo": ("curramgram_tropiezo.mp3", 0.9, 1.2),
    "foto": ("curramgram_foto.mp3", 0.9, 0.8),
    "caso_bien": ("curramgram_caso_bien.mp3", 1.0, 1.8),
    "caso_mal": ("curramgram_caso_mal.mp3", 0.9, 1.6),
}

PHOTO_KEY = pygame.K_f


class CurramGramGoMicrogame(BaseMicrogame):
    CAMERA_ACTIONS = {"eje_x": (pygame.K_LEFT, pygame.K_RIGHT),
                      "eje_y": (pygame.K_SPACE, pygame.K_s),
                      "accion": PHOTO_KEY, "dedos": (pygame.K_e, pygame.K_p)}
    # Contexto narrativo de la Paloma antes de jugar (mismo diálogo del Modo Historia).
    dialogoPaloma = [
        ["¡Ajá, llegamos al Aeropuerto Cortissoz!",
         "Cami es creadora de contenido y tiene",
         "que llegar a la puerta 7 antes de su vuelo."],
        ["En el camino verá cosas que parecen virales:",
         "un chisme, un accidente, una foto privada...",
         "¡Ojo! No todo lo que se ve merece un post."],
        ["Antes de publicar: confirma lo que ves,",
         "protege los datos y la imagen de los demás,",
         "y si alguien hace algo malo, avísale a la Policía."],
        ["Junta los sellos, resuelve los 6 casos",
         "y llega a tiempo a la puerta 7.",
         "¡Dale, que el avión no espera!"],
    ]
    # Mismo cierre que los minijuegos del mapa: letrero Ganaste/Perdiste + enseñanza.
    ensenanzaFinal = {
        "gana": ["Antes de publicar: confirma lo que ves,",
                 "protege los datos y la imagen de otros",
                 "y deja que la autoridad haga justicia, no tus redes."],
        "pierde": ["Un chisme, una foto privada o un escrache",
                   "se vuelven virales en segundos.",
                   "Verifica y respeta antes de publicar."],
    }
    # Mando: X avisar (E), Y publicar (P), B foto (F). A=Espacio (saltar / empezar).
    GAMEPAD_BUTTON_KEYS = {2: pygame.K_e, 3: pygame.K_p, 1: PHOTO_KEY}
    TIME_BAR_LAYOUT = (1690, 56, 400)

    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡LLEGA A LA PUERTA 7!\n[A/D] caminar · [E] avisar · [P] publicar",
            time_limit=_curram.DURACION,
            on_complete_callback=on_complete_callback,
        )

    def setup_game(self) -> None:
        self.game = _curram.CurramGramGo()
        self.game.inicio = False  # La Paloma y la portada común reemplazan el panel de inicio propio
        self.keys = HeldKeys()
        self.mouse = (960, 540)
        self._snap = self._snapshot()
        self.sfx = {k: load_managed_sound(f, v, m) for k, (f, v, m) in SFX.items()}

    def _sonar(self, clave: str, respaldo) -> None:
        """Efecto propio del juego; si no cargó, el efecto general equivalente de AudioManager."""
        sonido = self.sfx.get(clave)
        if sonido is not None:
            sonido.play()
        else:
            respaldo()

    def _snapshot(self) -> dict:
        g = self.game
        return {
            "salto": g.salto,
            "invulnerable": g.invulnerable,
            "foto": (g.last_camera, g.flash_timer),
            "casos": list(g.casos),
        }

    def _play_event_sounds(self) -> None:
        """Efectos reciclados de AudioManager según lo que acaba de pasar en el juego."""
        before, now = self._snap, self._snapshot()
        audio = self.audio
        if now["salto"] > 0 and before["salto"] <= 0:
            self._sonar("salto", audio.play_jump)
        if now["invulnerable"] > before["invulnerable"] + 0.5:
            self._sonar("tropiezo", audio.play_miss)  # Tropiezo con maleta o carrito
        if now["foto"] != before["foto"] and now["foto"][0] is not None:
            self._sonar("foto", audio.play_click)  # Obturador
        for old, new in zip(before["casos"], now["casos"]):
            if old is None and new is not None:
                if str(new).startswith("ERROR:"):
                    self._sonar("caso_mal", audio.play_lose)
                else:
                    self._sonar("caso_bien", audio.play_drum)
        self._snap = now

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm(MUSIC_TRACK, volume_scale=0.5)
        super().enter(params)

    def _photo_target(self):
        """Apunta al caso más cercano a Cami (para teclado/mando sin mouse)."""
        cam = self.game._camara()
        idx = min(range(len(_curram.PUNTOS)), key=lambda i: abs(_curram.PUNTOS[i] - self.game.x))
        return (int(_curram.PUNTOS[idx] - cam), _curram.PISO - 90)

    def handle_game_event(self, event: pygame.event.Event) -> None:
        game = self.game
        if event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.mouse = event.pos
            if not game.inicio and not game.final:
                game._capturar_foto(event.pos)
        elif event.type == pygame.KEYDOWN:
            if game.final:
                return
            if event.key == PHOTO_KEY and not game.inicio:
                target = self._photo_target()
                self.mouse = target
                game._capturar_foto(target)
            else:
                game.keydown(event.key)
        elif event.type == pygame.KEYUP:
            game.keyup(event.key)
        self._play_event_sounds()

    def update(self, dt: float) -> None:
        if self.phase == self.PHASE_PLAY:
            self.game.update(dt, self.keys.refresh(), self.mouse)
            self._play_event_sounds()
            self.time_left = self.game.tiempo
            if self.game.final and not self.is_finished:
                self.finish_game(won=bool(self.game.victoria))
            return
        super().update(dt)

    def render_game(self, surface: pygame.Surface) -> None:
        gamepad = input_state.is_gamepad_active()
        if gamepad != getattr(self, "_hint_gamepad", None):
            self._hint_gamepad = gamepad
            self.command_text = ("¡LLEGA A LA PUERTA 7!\n[LS] caminar · [X] avisar · [Y] publicar" if gamepad else
                                 "¡LLEGA A LA PUERTA 7!\n[A/D] caminar · [E] avisar · [P] publicar")
            if hasattr(self, "portadaIntro"):
                del self.portadaIntro
        self.game.gamepad_hints = gamepad
        # Durante la portada común no se dibuja el panel propio de inicio.
        inicio, self.game.inicio = self.game.inicio, self.game.inicio and self.phase == self.PHASE_PLAY
        try:
            self.game.draw(surface, self.mouse)
        finally:
            self.game.inicio = inicio


if __name__ == "__main__":
    from core.standalone import ejecutar_minijuego

    ejecutar_minijuego(CurramGramGoMicrogame, "CurramGram Go!")
