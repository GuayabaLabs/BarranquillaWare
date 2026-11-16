"""Emoji Catch: Balance! — minijuego del feed y la salud mental (única versión del juego).

Relación con redes sociales: el feed lanza emojis de odio (haters) y de apoyo. La mano morada
bloquea a los haters y la azul atrapa lo positivo; si se escapan los negativos, baja la salud mental.

Archivos:
- Este archivo: el minijuego dentro de BarranquillaWare (pausa, barra de tiempo, audio, mando, cámara).
- microgames/emojis/juego.py: la lógica y el dibujo.
- assets/emoji_catch/: sprites.

Probarlo solo (desde la raíz del proyecto):  python microgames/emoji_catch.py

Controles:
- Teclado: A/D mano morada (negativos) · J/L mano azul (positivos). Flechas también mueven la morada.
- Mando: stick/D-pad mano morada · X/B mano azul.
- Cámara: la mano en la mitad izquierda guía la mano morada; la de la mitad derecha, la azul.
"""
if __name__ == "__main__":  # Permite ejecutarlo solo: agrega la raíz del proyecto a sys.path
    import os
    import sys
    _RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _RAIZ)
    os.chdir(_RAIZ)

import os
from typing import Callable, Optional

import pygame

from core.camera_gestures import CameraGestureInput
from core.microgame import BaseMicrogame
from microgames.emojis import juego as _emoji
from microgames.redes_comun import HeldKeys

# AUDIO RECICLADO (provisional) — cuando haya pistas propias, cambiar aquí:
#   MUSIC_TRACK: música de fondo de la biblioteca mientras caen emojis.
#   Bloquear un emoji negativo: SFX_BLOQUEO en microgames/emojis/juego.py.
#   Además (ver _play_event_sounds): emoji positivo atrapado, emoji que se escapa,
#   Mega-Hater bloqueado y "ánimo a tope".
MUSIC_TRACK = "concentracionMusic.mp3"

# Límites horizontales de cada mano en el juego.
HAND_LIMITS = ((120.0, 900.0), (1020.0, 1800.0))


class EmojiCatchMicrogame(BaseMicrogame):
    # Contexto narrativo de la Paloma antes de jugar (mismo diálogo del Modo Historia).
    dialogoPaloma = [
        ["¡Eche, mira cómo se llenó tu feed!",
         "Hay haters lanzando odio y amigos",
         "mandando buena vibra, todo al mismo tiempo."],
        ["Con la mano morada bloquea a los haters",
         "y con la azul atrapa lo positivo.",
         "Si dejas pasar el odio, baja tu salud mental."],
        ["No se trata de tener más likes:",
         "se trata de cuidar tu balance.",
         "¡Bloquea, silencia y cuida tu ánimo!"],
    ]
    # Mismo cierre que los minijuegos del mapa: letrero Ganaste/Perdiste + enseñanza.
    ensenanzaFinal = {
        "gana": ["Tu feed no se controla solo:",
                 "bloquear el odio y buscar lo positivo",
                 "también es cuidar tu salud mental."],
        "pierde": ["Dejar pasar todo el odio del feed",
                   "desgasta tu salud mental.",
                   "Bloquea, silencia y busca balance."],
    }
    CAMERA_POINTER = False  # Lee las manos directamente
    # Mando: X/B mueven la mano azul (J/L). El D-pad/stick ya llega como flechas.
    GAMEPAD_BUTTON_KEYS = {2: pygame.K_j, 1: pygame.K_l}
    # La barra de tiempo común va arriba al centro, donde estaba la caja de TIEMPO.
    TIME_BAR_LAYOUT = (1020, 64, 500)

    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡ATRAPA Y BALANCEA!\n[A/D] morada · [J/L] azul",
            time_limit=_emoji.DURACION,
            on_complete_callback=on_complete_callback,
        )

    def _snapshot(self) -> dict:
        g = self.game
        return {"pos": g.positividad, "grietas": len(g.grietas), "animo": g.animo_activo,
                "megas": sum(1 for i in g.items if i.get("mega")), "puntos": g.puntos}

    def _play_event_sounds(self) -> None:
        before, now = self._snap, self._snapshot()
        audio = self.audio
        if now["pos"] > before["pos"]:
            audio.play_hit()  # Emoji positivo atrapado
        if now["grietas"] > before["grietas"]:
            audio.play_miss()  # Se escapó un emoji
        if now["animo"] > before["animo"] + 1.0:
            audio.play_whistle()  # Ánimo a tope
        if now["megas"] < before["megas"] and now["puntos"] >= before["puntos"] + 60:
            audio.play_drum()  # Mega-Hater bloqueado
        self._snap = now

    def setup_game(self) -> None:
        self.game = _emoji.EmojiCatch()
        self._snap = self._snapshot()
        self.keys = HeldKeys(aliases={pygame.K_a: (pygame.K_LEFT,), pygame.K_d: (pygame.K_RIGHT,)})
        self.camera_input = CameraGestureInput.get_instance()
        if os.environ.get("SDL_VIDEODRIVER") != "dummy" and not self.camera_input.enabled:
            self.camera_input.start()

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm(MUSIC_TRACK, volume_scale=0.5)

    def _apply_camera_hands(self, dt: float) -> None:
        cam = self.camera_input
        if not (cam and cam.enabled and cam.is_hand_present()):
            return
        for x_norm, _y in cam.get_hands():
            side = 0 if x_norm < 0.5 else 1
            lo, hi = HAND_LIMITS[side]
            local = (x_norm - 0.5 * side) / 0.5  # 0..1 dentro de su mitad
            target = lo + max(0.0, min(1.0, local)) * (hi - lo)
            current = self.game.manos[side]
            step = target - current
            self.game.direccion[side] = (step > 4) - (step < -4)
            self.game.manos[side] = current + step * min(1.0, dt * 14.0)

    def update(self, dt: float) -> None:
        if self.phase == self.PHASE_PLAY:
            self.game.update(dt, self.keys.refresh())
            self._apply_camera_hands(dt)
            self._play_event_sounds()
            self.time_left = self.game.tiempo
            if self.game.final and not self.is_finished:
                self.finish_game(won=bool(self.game.victoria))
            return
        super().update(dt)

    def render_game(self, surface: pygame.Surface) -> None:
        self.game.draw(surface)


if __name__ == "__main__":
    from core.standalone import ejecutar_minijuego

    ejecutar_minijuego(EmojiCatchMicrogame, "Emoji Catch: Balance!")
