"""
BarranquillaWare - Entidades del Microjuego '¡Concéntrate, llave!' (Uninorte)
Clases auxiliares: Student, Distraction, VirtualCursor, ProgressBar, ScoreManager.
"""
import math
import random
from typing import Optional, List, Tuple, Dict
import pygame
from core import input_state


class Student:
    """
    Controla los estados de estudio y distracción del estudiante en la biblioteca de Uninorte:
    - STUDYING: Alterna entre los dos sprites de escritura y suma progreso a la tarea.
    - DISTRACTED: Muestra el sprite mirando el celular morado mientras tenga nubes adheridas.
    - Gestiona sacudida reactiva al distraerse y transición suave al recuperar el foco.
    """
    STATE_STUDYING = "STUDYING"
    STATE_DISTRACTED = "DISTRACTED"

    def __init__(
        self,
        center_pos: Tuple[float, float],
        study_frames: List[pygame.Surface],
        distracted_frame: pygame.Surface
    ) -> None:
        self.base_x, self.base_y = center_pos
        self.study_frames = study_frames
        self.distracted_frame = distracted_frame

        self.state: str = self.STATE_STUDYING
        self.anim_timer: float = 0.0
        self.write_cadence: float = 0.24  # Alternancia rítmica de escritura
        self.current_frame_idx: int = 0

        # Efectos reactivos (Game Feel)
        self.shake_timer: float = 0.0
        self.shake_amplitude: float = 0.0
        self.recovery_scale_pulse: float = 0.0
        self.celebration_timer: float = 0.0

        # Lista de referencias a nubes adheridas que bloquean su concentración
        self.attached_clouds: List['Distraction'] = []

        # Perímetro de distracción ampliado (Zona de Ruido)
        self.catch_radius: float = 290.0

    @property
    def is_studying(self) -> bool:
        return self.state == self.STATE_STUDYING and len(self.attached_clouds) == 0

    def attach_cloud(self, cloud: 'Distraction') -> None:
        if cloud not in self.attached_clouds:
            was_studying = self.is_studying
            self.attached_clouds.append(cloud)
            self.state = self.STATE_DISTRACTED
            if was_studying:
                self.shake_timer = 0.35
                self.shake_amplitude = 14.0

    def detach_cloud(self, cloud: 'Distraction') -> None:
        if cloud in self.attached_clouds:
            self.attached_clouds.remove(cloud)
        if len(self.attached_clouds) == 0 and self.state == self.STATE_DISTRACTED:
            self.state = self.STATE_STUDYING
            self.recovery_scale_pulse = 1.0

    def trigger_celebration(self) -> None:
        self.celebration_timer = 1.2

    def update(self, dt: float) -> None:
        self.attached_clouds = [c for c in self.attached_clouds if c.state == Distraction.STATE_ATTACHED]
        if len(self.attached_clouds) == 0:
            if self.state == self.STATE_DISTRACTED:
                self.recovery_scale_pulse = 1.0
            self.state = self.STATE_STUDYING
        else:
            self.state = self.STATE_DISTRACTED

        if self.state == self.STATE_STUDYING:
            self.anim_timer += dt
            self.current_frame_idx = int(self.anim_timer / self.write_cadence) % len(self.study_frames)

        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)

        if self.recovery_scale_pulse > 0.0:
            self.recovery_scale_pulse = max(0.0, self.recovery_scale_pulse - dt * 3.2)

        if self.celebration_timer > 0.0:
            self.celebration_timer = max(0.0, self.celebration_timer - dt)

    def render(self, surface: pygame.Surface, global_offset: Tuple[int, int] = (0, 0)) -> None:
        if self.state == self.STATE_STUDYING:
            sprite = self.study_frames[self.current_frame_idx]
        else:
            sprite = self.distracted_frame

        ox, oy = global_offset
        if self.shake_timer > 0.0:
            decay = self.shake_timer / 0.35
            ox += int(math.sin(self.shake_timer * 55.0) * self.shake_amplitude * decay)
            oy += int(math.cos(self.shake_timer * 42.0) * (self.shake_amplitude * 0.5) * decay)

        if self.celebration_timer > 0.0:
            oy -= int(abs(math.sin(self.celebration_timer * 14.0)) * 18.0)

        if self.recovery_scale_pulse > 0.01:
            s_factor = 1.0 + math.sin(self.recovery_scale_pulse * math.pi) * 0.06
            tw = int(sprite.get_width() * s_factor)
            th = int(sprite.get_height() * s_factor)
            render_surf = pygame.transform.smoothscale(sprite, (tw, th))
        else:
            render_surf = sprite

        rect = render_surf.get_rect(center=(int(self.base_x) + ox, int(self.base_y) + oy))
        surface.blit(render_surf, rect)


class Distraction:
    """
    Representa una nube de distracción de red social:
    1. Instagram, 2. TikTok, 3. YouTube, 4. X, 5. Facebook, 6. WhatsApp.
    """
    STATE_APPROACHING = "APPROACHING"
    STATE_ATTACHED = "ATTACHED"
    STATE_POPPING = "POPPING"
    STATE_DEAD = "DEAD"

    NETWORK_NAMES = ["Instagram", "TikTok", "YouTube", "X", "Facebook", "WhatsApp"]
    NETWORK_COLORS = [
        (235, 95, 165),   # Instagram (Rosa/Naranja)
        (95, 225, 235),   # TikTok (Cyan/Neón)
        (245, 85, 85),    # YouTube (Rojo coral)
        (155, 110, 175),  # X (Púrpura pizarra)
        (85, 155, 245),   # Facebook (Azul cielo)
        (105, 215, 115),  # WhatsApp (Verde menta)
    ]

    def __init__(
        self,
        network_idx: int,
        sprite: pygame.Surface,
        start_pos: Tuple[float, float],
        target_pos: Tuple[float, float],
        speed: float
    ) -> None:
        self.network_idx = network_idx
        self.network_name = self.NETWORK_NAMES[network_idx % len(self.NETWORK_NAMES)]
        self.theme_color = self.NETWORK_COLORS[network_idx % len(self.NETWORK_COLORS)]
        self.sprite = sprite

        self.x, self.y = start_pos
        self.target_x, self.target_y = target_pos
        self.speed = speed

        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = max(1.0, math.hypot(dx, dy))
        self.dir_x = dx / dist
        self.dir_y = dy / dist
        self.perp_x = -self.dir_y
        self.perp_y = self.dir_x

        self.float_phase: float = random.uniform(0.0, math.pi * 2.0)
        self.float_freq: float = random.uniform(3.2, 5.2)
        self.float_amp: float = random.uniform(16.0, 30.0)

        self.attached_offset_x: float = random.uniform(-220.0, 220.0)
        self.attached_offset_y: float = random.uniform(-180.0, -40.0)

        self.state: str = self.STATE_APPROACHING
        self.pop_timer: float = 0.0
        self.pop_duration: float = 0.18
        self.hit_radius: float = max(sprite.get_width(), sprite.get_height()) * 0.48

    def pop(self) -> None:
        if self.state in (self.STATE_APPROACHING, self.STATE_ATTACHED):
            self.state = self.STATE_POPPING
            self.pop_timer = 0.0

    def update(self, dt: float, student: Student) -> None:
        self.float_phase += dt * self.float_freq

        if self.state == self.STATE_APPROACHING:
            wave_vel = math.cos(self.float_phase) * self.float_amp * self.float_freq * 0.25
            self.x += (self.dir_x * self.speed + self.perp_x * wave_vel) * dt
            self.y += (self.dir_y * self.speed + self.perp_y * wave_vel) * dt

            dist_to_student = math.hypot(self.x - student.base_x, self.y - (student.base_y - 30.0))
            if dist_to_student <= student.catch_radius:
                self.state = self.STATE_ATTACHED
                self.attached_offset_x = (self.x - student.base_x) * 0.75
                self.attached_offset_y = (self.y - student.base_y) * 0.75
                student.attach_cloud(self)

        elif self.state == self.STATE_ATTACHED:
            bob_x = math.cos(self.float_phase * 1.4) * 10.0
            bob_y = math.sin(self.float_phase * 1.8) * 12.0
            self.x = student.base_x + self.attached_offset_x + bob_x
            self.y = student.base_y + self.attached_offset_y + bob_y

        elif self.state == self.STATE_POPPING:
            self.pop_timer += dt
            if self.pop_timer >= self.pop_duration:
                self.state = self.STATE_DEAD

    def render(self, surface: pygame.Surface, global_offset: Tuple[int, int] = (0, 0)) -> None:
        if self.state == self.STATE_DEAD:
            return

        ox, oy = global_offset
        cx = int(self.x) + ox
        cy = int(self.y) + oy

        if self.state == self.STATE_POPPING:
            p = min(1.0, self.pop_timer / self.pop_duration)
            scale = 1.0 + math.sin(p * math.pi) * 0.38
            alpha = int(255 * (1.0 - p))
            tw = max(4, int(self.sprite.get_width() * scale))
            th = max(4, int(self.sprite.get_height() * scale))
            pop_surf = pygame.transform.smoothscale(self.sprite, (tw, th))
            pop_surf.set_alpha(alpha)
            rect = pop_surf.get_rect(center=(cx, cy))
            surface.blit(pop_surf, rect)
            return

        pulse = 1.0 + math.sin(self.float_phase) * 0.04
        if self.state == self.STATE_ATTACHED:
            pulse = 1.06 + math.sin(self.float_phase * 2.5) * 0.06

        tw = int(self.sprite.get_width() * pulse)
        th = int(self.sprite.get_height() * pulse)
        scaled = pygame.transform.smoothscale(self.sprite, (tw, th))
        rect = scaled.get_rect(center=(cx, cy))
        surface.blit(scaled, rect)


class VirtualCursor:
    """Cursor en forma de lapicero de BarranquillaWare."""

    def __init__(self, screen_w: int, screen_h: int, pencil_surface: pygame.Surface) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.x: float = screen_w * 0.5
        self.y: float = screen_h * 0.45
        self.vx: float = 0.0
        self.vy: float = 0.0

        self.max_speed: float = 1250.0
        self.accel: float = 9000.0
        self.friction: float = 14.0
        self.aoe_radius: float = 72.0

        self.slap_timer: float = 0.0
        self.slap_duration: float = 0.12
        self.ripples: List[Dict[str, float]] = []

        self.pencil_surf = pencil_surface
        pw = self.pencil_surf.get_width()
        ph = self.pencil_surf.get_height()
        self.tip_offset_x = int(55 * (pw / 1312.0) - pw * 0.5)
        self.tip_offset_y = int(195 * (ph / 1199.0) - ph * 0.5)

    @property
    def tip_x(self) -> float:
        return self.x + self.tip_offset_x

    @property
    def tip_y(self) -> float:
        return self.y + self.tip_offset_y

    def trigger_pop_Wave(self) -> None:
        self.slap_timer = self.slap_duration
        self.ripples.append({
            "x": self.tip_x,
            "y": self.tip_y,
            "r": 16.0,
            "max_r": self.aoe_radius,
            "alpha": 240.0
        })

    def update(self, dt: float, clouds: Optional[List[Distraction]] = None) -> None:
        keys = input_state.get_pressed()
        ix = 0.0
        iy = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            ix -= 1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            ix += 1.0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            iy -= 1.0
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            iy += 1.0

        if ix != 0.0 or iy != 0.0:
            length = math.hypot(ix, iy)
            ix /= length
            iy /= length
            self.vx += ix * self.accel * dt
            self.vy += iy * self.accel * dt
        else:
            decay = max(0.0, 1.0 - self.friction * dt)
            self.vx *= decay
            self.vy *= decay

        speed = math.hypot(self.vx, self.vy)
        if speed > self.max_speed:
            self.vx = (self.vx / speed) * self.max_speed
            self.vy = (self.vy / speed) * self.max_speed

        self.x += self.vx * dt
        self.y += self.vy * dt

        if clouds and (ix != 0.0 or iy != 0.0):
            nearest_c = None
            nearest_d = 110.0
            for c in clouds:
                if c.state in (Distraction.STATE_APPROACHING, Distraction.STATE_ATTACHED):
                    d = math.hypot(c.x - self.tip_x, c.y - self.tip_y)
                    if d < nearest_d:
                        nearest_d = d
                        nearest_c = c
            if nearest_c is not None and nearest_d > 6.0:
                pull = 120.0 * dt
                self.x += ((nearest_c.x - self.tip_x) / nearest_d) * pull
                self.y += ((nearest_c.y - self.tip_y) / nearest_d) * pull

        margin = 32.0
        self.x = max(margin, min(float(self.screen_w) - margin, self.x))
        self.y = max(margin, min(float(self.screen_h) - margin, self.y))

        if self.slap_timer > 0.0:
            self.slap_timer = max(0.0, self.slap_timer - dt)

        for r in self.ripples:
            r["r"] += (r["max_r"] - r["r"]) * min(1.0, dt * 18.0)
            r["alpha"] -= 1200.0 * dt
        self.ripples = [r for r in self.ripples if r["alpha"] > 5.0]

    def get_pop_targets(self, clouds: List[Distraction], extra_radius: float = 0.0) -> List[Distraction]:
        hit_list: List[Distraction] = []
        effective_radius = self.aoe_radius + extra_radius
        for c in clouds:
            if c.state in (Distraction.STATE_APPROACHING, Distraction.STATE_ATTACHED):
                dist = math.hypot(c.x - self.tip_x, c.y - self.tip_y)
                if dist <= (effective_radius + c.hit_radius * 0.45):
                    hit_list.append(c)
        return hit_list

    def render(self, surface: pygame.Surface, has_target_in_range: bool = False, is_cam_controlled: bool = False) -> None:
        cx, cy = int(self.x), int(self.y)
        tx, ty = int(self.tip_x), int(self.tip_y)

        if has_target_in_range:
            ring_col = (110, 235, 140, 160)
        elif is_cam_controlled:
            ring_col = (90, 215, 255, 130)
        else:
            ring_col = (255, 235, 130, 60)

        ring_surf = pygame.Surface((int(self.aoe_radius * 2 + 8), int(self.aoe_radius * 2 + 8)), pygame.SRCALPHA)
        rc = int(self.aoe_radius + 4)
        pygame.draw.circle(ring_surf, ring_col, (rc, rc), int(self.aoe_radius), width=2)
        surface.blit(ring_surf, (tx - rc, ty - rc))

        for r in self.ripples:
            rad = int(r["r"])
            alpha = int(max(0.0, min(255.0, r["alpha"])))
            rip_s = pygame.Surface((rad * 2 + 8, rad * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(rip_s, (255, 240, 110, alpha), (rad + 4, rad + 4), rad, width=3)
            surface.blit(rip_s, (int(r["x"]) - rad - 4, int(r["y"]) - rad - 4))

        is_slapping = self.slap_timer > 0.0
        sprite = self.pencil_surf
        scale = 0.88 if is_slapping else 1.0
        angle = -12.0 if is_slapping else 0.0

        if scale != 1.0 or angle != 0.0:
            tw = max(10, int(sprite.get_width() * scale))
            th = max(10, int(sprite.get_height() * scale))
            sprite = pygame.transform.smoothscale(sprite, (tw, th))
            if angle != 0.0:
                sprite = pygame.transform.rotate(sprite, angle)

        rect = sprite.get_rect(center=(cx, cy))
        surface.blit(sprite, rect)


class ProgressBar:
    """Gestiona el progreso de la tarea del estudiante (0.0 a 100.0 %)."""

    def __init__(self, frame_surface: pygame.Surface, center_top_pos: Tuple[int, int]) -> None:
        self.frame_surface = frame_surface
        self.rect = self.frame_surface.get_rect(midtop=center_top_pos)

        self.progress: float = 0.0
        self.fill_rate_per_sec: float = 100.0 / 16.0
        self.completed: bool = False
        self.sparkle_phase: float = 0.0

        fw, fh = self.frame_surface.get_size()
        self.track_x = self.rect.left + int(fw * 0.235)
        self.track_y = self.rect.top + int(fh * 0.412)
        self.track_w = int(fw * 0.669)
        self.track_h = int(fh * 0.368)

    def update(self, dt: float, is_studying: bool, rate_multiplier: float = 1.0) -> bool:
        self.sparkle_phase += dt * 6.0
        just_completed = False
        if is_studying and not self.completed:
            effective_rate = self.fill_rate_per_sec * max(0.1, rate_multiplier)
            self.progress = min(100.0, self.progress + effective_rate * dt)
            if self.progress >= 100.0:
                self.progress = 100.0
                self.completed = True
                just_completed = True
        return just_completed

    def render(self, surface: pygame.Surface, is_studying: bool) -> None:
        surface.blit(self.frame_surface, self.rect)
        ratio = max(0.0, min(1.0, self.progress / 100.0))
        fill_w = int(self.track_w * ratio)

        if self.dibujarRellenoPintado(surface, fill_w, is_studying):
            return

        if fill_w > 0:
            if self.completed:
                col_main = (60, 225, 115)
                col_hi = (150, 255, 180)
            elif is_studying:
                col_main = (75, 210, 110)
                col_hi = (170, 255, 190)
            else:
                col_main = (120, 160, 135)
                col_hi = (165, 195, 175)

            fill_rect = pygame.Rect(self.track_x, self.track_y, fill_w, self.track_h)
            radius = min(self.track_h // 2, max(6, fill_w // 2))
            pygame.draw.rect(surface, col_main, fill_rect, border_radius=radius)

            hi_rect = pygame.Rect(self.track_x + 4, self.track_y + 3, max(0, fill_w - 8), max(4, self.track_h // 3))
            pygame.draw.rect(surface, col_hi, hi_rect, border_radius=max(3, radius // 2))
            pygame.draw.rect(surface, (45, 130, 70), fill_rect, width=2, border_radius=radius)

    def dibujarRellenoPintado(self, surface: pygame.Surface, ancho: int, estudiando: bool) -> bool:
        if getattr(self, "rellenoPintado", None) is None:
            try:
                import os
                from core.asset_manager import AssetManager
                relleno = AssetManager.get_instance().cargarSinFondo(os.path.join("Interfaz", "barraTiempoRelleno.jpg"), 300)
                alto = self.track_h
                self.rellenoPintado = pygame.transform.smoothscale(
                    relleno, (int(relleno.get_width() * alto / relleno.get_height()), alto))
                self.rellenoApagado = pygame.transform.grayscale(self.rellenoPintado)
            except Exception as e:
                print(f"Aviso: no se pudo cargar el relleno de la barra de enfoque: {e}")
                self.rellenoPintado = False
        if not self.rellenoPintado:
            return False
        if ancho < 8:
            return True
        if getattr(self, "barraCompleta", None) is None:
            self.barraCompleta = self.armarBarra(self.rellenoPintado, self.track_w)
            self.barraCompletaApagada = self.armarBarra(self.rellenoApagado, self.track_w)
        barra = self.barraCompleta if estudiando or self.completed else self.barraCompletaApagada
        alto = barra.get_height()
        punta = min(alto // 2, ancho // 2)
        surface.blit(barra, (self.track_x, self.track_y), (0, 0, ancho - punta, alto))
        surface.blit(barra, (self.track_x + ancho - punta, self.track_y), (self.track_w - punta, 0, punta, alto))
        return True

    def armarBarra(self, relleno: pygame.Surface, ancho: int) -> pygame.Surface:
        alto = relleno.get_height()
        punta = min(alto, relleno.get_width() // 2, ancho // 2)
        barra = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        barra.blit(relleno, (0, 0), (0, 0, punta, alto))
        centro = relleno.subsurface((punta, 0, relleno.get_width() - punta * 2, alto))
        if ancho - punta * 2 > 0:
            barra.blit(pygame.transform.smoothscale(centro, (ancho - punta * 2, alto)), (punta, 0))
        barra.blit(relleno, (ancho - punta, 0), (relleno.get_width() - punta, 0, punta, alto))
        return barra


class ScoreManager:
    """Gestiona la puntuación y las rachas internamente para el resultado final."""

    def __init__(self) -> None:
        self.score: int = 0
        self.streak: int = 0
        self.max_streak: int = 0
        self.popped_count: int = 0
        self.task_bonus_awarded: bool = False

    def register_pop(self, num_popped: int, pos: Tuple[float, float]) -> int:
        if num_popped <= 0:
            self.streak = 0
            return 0

        gained_total = 0
        for _ in range(num_popped):
            self.streak += 1
            self.popped_count += 1
            self.max_streak = max(self.max_streak, self.streak)
            mult = 1 + (self.streak // 4)
            pts = 60 * mult
            self.score += pts
            gained_total += pts
        return gained_total

    def award_task_completion_bonus(self, pos: Tuple[float, float]) -> None:
        if not self.task_bonus_awarded:
            self.task_bonus_awarded = True
            self.score += 400

    def update(self, dt: float) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        pass
