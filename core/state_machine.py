from abc import ABC, abstractmethod
from typing import Optional, List
import pygame

class BaseState(ABC):
    """Clase base abstracta para todos los estados y escenas del juego."""
    def __init__(self) -> None:
        self.state_machine: Optional['StateMachine'] = None

    def enter(self, params: Optional[dict] = None) -> None:
        pass

    def exit(self) -> None:
        pass

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        pass

    @abstractmethod
    def render(self, surface: pygame.Surface) -> None:
        pass

class StateMachine:
    """Máquina de estados finita con pila de estados (push/pop para menús y modales)."""
    def __init__(self) -> None:
        self._states: List[BaseState] = []

    @property
    def current_state(self) -> Optional[BaseState]:
        return self._states[-1] if self._states else None

    def change_state(self, new_state: BaseState, params: Optional[dict] = None) -> None:
        if self._states:
            self._states[-1].exit()
            self._states.pop()
        new_state.state_machine = self
        self._states.append(new_state)
        new_state.enter(params)

    def push_state(self, new_state: BaseState, params: Optional[dict] = None) -> None:
        new_state.state_machine = self
        self._states.append(new_state)
        new_state.enter(params)

    def pop_state(self) -> Optional[BaseState]:
        if not self._states:
            return None
        popped = self._states.pop()
        popped.exit()
        return popped

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.current_state:
            self.current_state.handle_event(event)

    def update(self, dt: float) -> None:
        if self.current_state:
            self.current_state.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        # Si hay más de un estado en la pila (ej. modal sobre menú), renderizamos todos en orden
        for state in self._states:
            state.render(surface)
