"""Puente entre los juegos de `juegos_extra/` y la arquitectura de BarranquillaWare.

Los juegos extra se escribieron como ejecutables aislados (`from comun import ...`).
Este módulo los importa sin duplicar su lógica y ofrece utilidades para que corran
como `BaseMicrogame`: audio vía AudioManager, teclas combinadas (teclado + mando)
y un temporizador sincronizado con la barra acuarela común.
"""
import importlib
import sys
from pathlib import Path
from typing import Callable, Dict, Optional

import pygame

from core import input_state
from core.audio_manager import AudioManager

EXTRA_DIR = Path(__file__).resolve().parent.parent / "juegos_extra"


def load_extra_module(name: str):
    """Importa `juegos_extra/<name>.py` respetando sus imports planos (`comun`, `animacion`)."""
    extra = str(EXTRA_DIR)
    if extra not in sys.path:
        sys.path.insert(0, extra)
    return importlib.import_module(name)


class ManagedSound:
    """Envuelve un pygame.mixer.Sound para que respete el volumen y el mute de AudioManager."""

    def __init__(self, sound: Optional[pygame.mixer.Sound], volume_scale: float = 1.0) -> None:
        self.sound = sound
        self.volume_scale = volume_scale

    def play(self):
        return AudioManager.get_instance().play_sfx(self.sound, self.volume_scale)

    def set_volume(self, _value: float) -> None:
        """El volumen lo decide AudioManager; se ignora el valor fijo del juego extra."""


def load_managed_sound(filename: str, volume_scale: float = 1.0) -> Optional[ManagedSound]:
    try:
        if not pygame.mixer.get_init():
            return None
        path = Path(AudioManager.get_instance().base_assets_dir) / filename
        if not path.is_absolute():
            path = EXTRA_DIR.parent / path
        return ManagedSound(pygame.mixer.Sound(str(path)), volume_scale)
    except (pygame.error, OSError):
        return None


class HeldKeys:
    """Vector de teclas sostenidas con alias (p. ej. flechas -> A/D) y teclado + mando."""

    def __init__(self, aliases: Optional[Dict[int, tuple]] = None,
                 extra: Optional[Callable[[int], bool]] = None) -> None:
        self.aliases = aliases or {}
        self.extra = extra
        self._pressed = input_state.get_pressed()

    def refresh(self) -> "HeldKeys":
        self._pressed = input_state.get_pressed()
        return self

    def __getitem__(self, key: int) -> bool:
        if self._pressed[key]:
            return True
        for alias in self.aliases.get(key, ()):
            if self._pressed[alias]:
                return True
        return bool(self.extra and self.extra(key))
