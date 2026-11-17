"""Navegación por foco para menús con teclado y mando.

Un solo helper reutilizable: flechas/WASD (y el D-pad/stick, que el motor traduce
a flechas) mueven el foco al botón más cercano en esa dirección; Enter/Espacio
(botón A del mando) lo activa. El mouse y el puntero de cámara siguen funcionando
igual: al mover el mouse sobre un botón, ese botón pasa a tener el foco.
"""
from typing import Callable, List, Optional, Sequence

import pygame

from ui.button import UIButton

DIRECTION_KEYS = {
    pygame.K_UP: (0, -1),
    pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_d: (1, 0),
}
ACTIVATE_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


class FocusNavigator:
    """Mantiene qué botón tiene el foco y lo mueve espacialmente."""

    def __init__(self, get_buttons: Callable[[], Sequence[UIButton]], default_index: int = 0) -> None:
        self._get_buttons = get_buttons
        self.default_index = default_index
        self.focused: Optional[UIButton] = None

    def _buttons(self) -> List[UIButton]:
        return [b for b in self._get_buttons() if b is not None]

    def reset(self) -> None:
        if self.focused is not None:
            self.focused.set_focus(False)
        self.focused = None

    def focus(self, btn: Optional[UIButton]) -> None:
        if btn is self.focused:
            return
        if self.focused is not None:
            self.focused.set_focus(False)
        self.focused = btn
        if btn is not None:
            btn.set_focus(True)

    def _move(self, direction) -> None:
        buttons = self._buttons()
        if not buttons:
            return
        current = self.focused if self.focused in buttons else None
        if current is None:
            idx = min(max(0, self.default_index), len(buttons) - 1)
            self.focus(buttons[idx])
            return
        cx, cy = current.rect.center
        dx, dy = direction
        best, best_score = None, float("inf")
        for btn in buttons:
            if btn is current:
                continue
            bx, by = btn.rect.center
            along = (bx - cx) * dx + (by - cy) * dy
            if along <= 4:
                continue
            across = abs((bx - cx) * dy) + abs((by - cy) * dx)
            score = along + across * 2.0
            if score < best_score:
                best, best_score = btn, score
        if best is None:
            # Envolver: ir al botón más lejano en la dirección opuesta.
            opposite = [b for b in buttons if b is not current]
            if not opposite:
                return
            best = min(opposite, key=lambda b: (b.rect.centerx - cx) * dx + (b.rect.centery - cy) * dy)
        self.focus(best)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Retorna True si el evento fue consumido por la navegación."""
        if event.type == pygame.MOUSEMOTION:
            # El ratón usa el hover original del botón, sin dejar foco persistente.
            self.reset()
            return False
        if event.type != pygame.KEYDOWN:
            return False
        if event.key in DIRECTION_KEYS:
            self._move(DIRECTION_KEYS[event.key])
            return True
        if event.key in ACTIVATE_KEYS:
            buttons = self._buttons()
            if self.focused in buttons:
                self.focused.activate()
                return True
            if buttons:
                # Primer Enter sin foco: enfocar el botón por defecto.
                self.focus(buttons[min(max(0, self.default_index), len(buttons) - 1)])
                return True
        return False
