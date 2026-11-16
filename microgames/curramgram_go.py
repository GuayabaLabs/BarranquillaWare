"""CurramGram Go! integrado: el juego del aeropuerto de `juegos_extra/curramgram_go.py` como BaseMicrogame.

Relación con redes sociales: Cami es creadora de contenido en el Aeropuerto Cortissoz y cada
persona es un caso real de redes (desinformación, sobreexposición de datos, exposición sin
consentimiento, noticia falsa viral, contenido viral y escrache digital). Antes de publicar
debe confirmar, proteger la privacidad y pedir ayuda a la autoridad en vez de exponer a alguien.

Obtiene de la arquitectura común: menú de pausa (ESC / Start), barra de tiempo acuarela,
música y efectos vía AudioManager, mando y puntero de cámara para apuntar la foto.

Controles:
- Teclado: A/D o flechas caminar · ESPACIO saltar · S/↓ esconderse · E avisar · clic o F foto · P publicar.
- Mando: stick/D-pad caminar · A saltar · ↓ esconderse · X avisar · B foto · Y publicar.
- Cámara: el lapicero apunta la foto; mantener quieto o pellizcar dispara.
"""
from typing import Callable, Optional

import pygame

from core.microgame import BaseMicrogame
from microgames.extra_bridge import HeldKeys, load_extra_module, load_managed_sound

_curram = load_extra_module("curramgram_go")

# AUDIO RECICLADO (provisional) — cuando haya pistas propias, cambiar aquí:
#   MUSIC_TRACK: música de fondo mientras se recorre la terminal.
#   SFX_SELLO:   al recoger cada sello de pasaporte.
#   Además (ver _play_event_sounds): salto, tropiezo, foto, caso resuelto bien/mal.
MUSIC_TRACK = "contraRelojMusic.mp3"
SFX_SELLO = "char_audio_1_microjuego_puño.ogg"

PHOTO_KEY = pygame.K_f


class _IntegratedCurramGram(_curram.CurramGramGo):
    MOSTRAR_RELOJ = False  # La barra acuarela común ocupa el lugar del reloj
    TEXTO_REINICIO = ""

    def _iniciar_audio(self):
        self.sonido_tambor = load_managed_sound(SFX_SELLO, 0.5)


class CurramGramGoMicrogame(BaseMicrogame):
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
            command_text="¡LLEGA A LA PUERTA 7!",
            time_limit=_curram.DURACION,
            on_complete_callback=on_complete_callback,
        )
        self.outro_duration = 7.0  # Deja leer el perfil con los fenómenos de redes

    def setup_game(self) -> None:
        self.game = _IntegratedCurramGram()
        self.keys = HeldKeys()
        self.mouse = (960, 540)
        self._snap = self._snapshot()

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
            audio.play_jump()
        if now["invulnerable"] > before["invulnerable"] + 0.5:
            audio.play_miss()  # Tropiezo con maleta o carrito
        if now["foto"] != before["foto"] and now["foto"][0] is not None:
            audio.play_click()  # Obturador
        for old, new in zip(before["casos"], now["casos"]):
            if old is None and new is not None:
                if str(new).startswith("ERROR:"):
                    audio.play_lose()
                else:
                    audio.play_drum()
        self._snap = now

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm(MUSIC_TRACK, volume_scale=0.5)

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
        self.game.draw(surface, self.mouse)
