"""
BarranquillaWare - Sistema de Cámara 2D Universal
Cámara suave con soporte de arrastre (Pan & Drag), seguimiento lerp con delta time
y clamping perimetral estricto.
"""
from typing import Tuple


class Camera2D:
    """
    Cámara 2D suave con soporte de arrastre táctil (Mouse Drag),
    seguimiento suave de avatar (Smooth Target Follow con dt),
    y clamping perimetral estricto.
    """
    def __init__(self, world_w: int, world_h: int, view_w: int = 1920, view_h: int = 1080) -> None:
        self.world_w = world_w
        self.world_h = world_h
        self.view_w = view_w
        self.view_h = view_h

        self.max_x = max(0, world_w - view_w)
        self.max_y = max(0, world_h - view_h)

        # Posición inicial centrada en la ciudad
        self.x: float = self.max_x / 2.0
        self.y: float = self.max_y / 2.0
        self.target_x: float = self.x
        self.target_y: float = self.y

        # Velocidad cinética para inercia opcional
        self.vel_x: float = 0.0
        self.vel_y: float = 0.0

        # Estados de arrastre (Pan & Return)
        self.is_dragging: bool = False
        self.drag_start_mouse: Tuple[int, int] = (0, 0)
        self.drag_start_cam: Tuple[float, float] = (0.0, 0.0)

    def set_pos(self, x: float, y: float) -> None:
        self.x = max(0.0, min(float(self.max_x), x))
        self.y = max(0.0, min(float(self.max_y), y))
        self.target_x = self.x
        self.target_y = self.y
        self.vel_x = 0.0
        self.vel_y = 0.0

    def start_drag(self, mouse_pos: Tuple[int, int]) -> None:
        self.is_dragging = True
        self.drag_start_mouse = mouse_pos
        self.drag_start_cam = (self.x, self.y)
        self.vel_x = 0.0
        self.vel_y = 0.0

    def update_drag(self, mouse_pos: Tuple[int, int]) -> None:
        if not self.is_dragging:
            return
        dx = mouse_pos[0] - self.drag_start_mouse[0]
        dy = mouse_pos[1] - self.drag_start_mouse[1]
        new_x = self.drag_start_cam[0] - dx
        new_y = self.drag_start_cam[1] - dy

        self.x = max(0.0, min(float(self.max_x), new_x))
        self.y = max(0.0, min(float(self.max_y), new_y))
        self.target_x = self.x
        self.target_y = self.y

    def stop_drag(self) -> None:
        self.is_dragging = False

    def update(self, dt: float) -> None:
        """
        Interpolación suave hacia (target_x, target_y) con delta time y clamping.
        """
        if self.is_dragging:
            return

        self.target_x = max(0.0, min(float(self.max_x), self.target_x))
        self.target_y = max(0.0, min(float(self.max_y), self.target_y))

        lerp_factor = min(1.0, dt * 8.0)
        self.x += (self.target_x - self.x) * lerp_factor
        self.y += (self.target_y - self.y) * lerp_factor

        # Clamping perimetral estricto
        if self.x < 0.0:
            self.x = 0.0
        elif self.x > self.max_x:
            self.x = float(self.max_x)

        if self.y < 0.0:
            self.y = 0.0
        elif self.y > self.max_y:
            self.y = float(self.max_y)
