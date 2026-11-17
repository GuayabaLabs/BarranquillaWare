"""Estado de teclas sostenidas combinando teclado real y mando.

El motor traduce el mando a KEYDOWN/KEYUP virtuales, pero `pygame.key.get_pressed()`
solo conoce el teclado físico. Los microjuegos que leen teclas sostenidas deben
usar `get_pressed()` de este módulo para que el D-pad/stick también funcione.
"""
from typing import Set

import pygame

# Teclas mantenidas por el mando (las actualiza core.engine.Engine).
VIRTUAL_KEYS: Set[int] = set()


class _CombinedPressed:
    def __init__(self, real) -> None:
        self._real = real

    def __getitem__(self, key: int) -> bool:
        try:
            if self._real[key]:
                return True
        except IndexError:
            pass
        return key in VIRTUAL_KEYS

    def __len__(self) -> int:
        return len(self._real)


def get_pressed() -> _CombinedPressed:
    """Igual que pygame.key.get_pressed(), pero incluye las teclas virtuales del mando."""
    return _CombinedPressed(pygame.key.get_pressed())


def clear() -> None:
    VIRTUAL_KEYS.clear()
