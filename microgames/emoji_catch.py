"""Emoji Catch integrado: el juego de `juegos_extra/emoji_catch.py` como BaseMicrogame.

Obtiene de la arquitectura común: menú de pausa (ESC / Start), barra de tiempo acuarela,
música y efectos vía AudioManager, mando y control por movimiento con dos manos.

Controles:
- Teclado: A/D mano morada (negativos) · J/L mano azul (positivos). Flechas también mueven la morada.
- Mando: stick/D-pad mano morada · X/B mano azul.
- Cámara: la mano en la mitad izquierda guía la mano morada; la de la mitad derecha, la azul.
"""
import os
from typing import Callable, Optional

import pygame

from core.camera_gestures import CameraGestureInput
from core.microgame import BaseMicrogame
from microgames.extra_bridge import HeldKeys, load_extra_module, load_managed_sound

_emoji = load_extra_module("emoji_catch")

# AUDIO RECICLADO (provisional) — cuando haya pistas propias, cambiar aquí:
#   MUSIC_TRACK: música de fondo de la biblioteca mientras caen emojis.
#   SFX_BLOCK:   al bloquear (atrapar) un emoji negativo con la mano morada.
#   Además (ver _play_event_sounds): emoji positivo atrapado, emoji que se escapa,
#   Mega-Hater bloqueado y "ánimo a tope".
MUSIC_TRACK = "concentracionMusic.mp3"
SFX_BLOCK = "char_audio_0_microjuego_puño.ogg"

# Límites horizontales de cada mano en el juego original.
HAND_LIMITS = ((120.0, 900.0), (1020.0, 1800.0))


class _IntegratedEmojiCatch(_emoji.EmojiCatch):
    MOSTRAR_BARRA_TIEMPO_PROPIA = False  # La barra acuarela común la reemplaza
    TEXTO_REINICIO = ""

    def _iniciar_audio(self):
        # La música la pone el microjuego con AudioManager; aquí solo el efecto de bloqueo.
        self.sonido_bloqueo = load_managed_sound(SFX_BLOCK, 0.6)


class EmojiCatchMicrogame(BaseMicrogame):
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
    # La barra común reemplaza la barra fina propia, sobre el medidor de salud.
    TIME_BAR_LAYOUT = (970, 840, 600)

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
        self.game = _IntegratedEmojiCatch()
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
        # Al terminar se usan el letrero y la enseñanza comunes en vez del panel propio.
        final, self.game.final = self.game.final, "" if self.is_finished else self.game.final
        try:
            self.game.draw(surface)
        finally:
            self.game.final = final
