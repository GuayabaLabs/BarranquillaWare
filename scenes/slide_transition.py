import math
import pygame

from core.state_machine import BaseState

class SlideTransitionState(BaseState):
    """
    Transición de cámara panorámica tipo viaje urbano:
    Desplaza la escena de origen y la de destino horizontalmente con curva de desaceleración cúbica.
    - direction == "left": Viaje hacia la derecha (la escena actual sale a la izquierda, la nueva entra por la derecha).
    - direction == "right": Regreso hacia la izquierda (la escena actual sale a la derecha, la anterior entra por la izquierda).
    """
    def __init__(
        self,
        from_scene: BaseState,
        to_scene: BaseState,
        direction: str = "left",
        duration: float = 0.65
    ) -> None:
        super().__init__()
        self.from_scene = from_scene
        self.to_scene = to_scene
        self.direction = direction
        self.duration = duration
        self.timer: float = 0.0

        # Captura estática congelada (Snapshot Optimization) de origen y destino al arrancar
        self.surf_from = pygame.Surface((1920, 1080))
        self.surf_to = pygame.Surface((1920, 1080))
        self.from_scene.render(self.surf_from)
        self.to_scene.render(self.surf_to)

    @property
    def particles(self):
        # Durante la transición panorámica los snapshots están congelados en la superficie 2D
        return None

    def handle_event(self, event: pygame.event.Event) -> None:
        # Bloquear inputs interactivos durante la transición de cámara
        pass

    def update(self, dt: float) -> None:
        self.timer += dt

        if self.timer >= self.duration:
            # Transición completa: cambiar definitivamente a la escena destino
            if self.state_machine:
                self.state_machine.change_state(self.to_scene)

    def render(self, surface: pygame.Surface) -> None:
        # Calcular progreso no lineal (Cubic Ease-Out)
        progress = min(1.0, self.timer / self.duration)
        ease = 1.0 - math.pow(1.0 - progress, 3.0)

        w = 1920
        if self.direction == "left":
            # Viaje a la derecha: mundo se mueve a la izquierda
            offset = int(ease * w)
            surface.blit(self.surf_from, (-offset, 0))
            surface.blit(self.surf_to, (w - offset, 0))
        else:
            # Regreso a la izquierda: mundo se mueve a la derecha
            offset = int(ease * w)
            surface.blit(self.surf_from, (offset, 0))
            surface.blit(self.surf_to, (-w + offset, 0))
