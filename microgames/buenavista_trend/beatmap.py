"""
BarranquillaWare - Eventos y Mapa Rítmico de 'El Trend en Buenavista'
Contiene la estructura de datos MusicalNoteEvent y la secuencia IMITADORA_BEATMAP_DATA.
"""
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class MusicalNoteEvent:
    """
    Evento musical independiente de la lógica de renderizado.
    Representa una nota/tecla sincronizada con el audio de 'Imitadora' (Romeo Santos).
    """
    impact_time: float          # Momento exacto de impacto (en segundos desde el inicio de la canción)
    lane: int                   # Carril correspondiente (0: D, 1: F, 2: J, 3: K)
    sprite_type: int            # Tipo de sprite (0: Nota rosa, 1: Fuego naranja, 2: Tenis morado, 3: Claqueta rosa)
    fall_speed: float           # Velocidad de descenso (en píxeles lógicos por segundo)
    spawn_time: float = 0.0     # Momento de aparición

    # Estado en tiempo de ejecución
    spawned: bool = False
    state: str = "pending"      # "pending", "falling", "hit", "missed", "done"
    y: float = 0.0              # Centro vertical actual de la nota
    hit_anim_timer: float = 0.0 # Temporizador de iluminación/expansión al acertar
    miss_anim_timer: float = 0.0
    judgment: str = ""          # "PERFECTO", "BIEN", "FALLO"
    penalized: bool = False     # Garantiza que una misma nota nunca produzca más de un fallo


# Mapa de eventos musicales ajustado a los transientes e impactos reales de
# 'assets/imitadora_ost_piano_tiles_microjuego.ogg' (0.0s a 30.0s).
# Formato: (impact_time_sec, lane_0_to_3, sprite_type_0_to_3, fall_speed_px_s)
IMITADORA_BEATMAP_DATA: List[Tuple[float, int, int, float]] = [
    # FASE 1 (0–10s): Notas espaciadas, velocidad moderada
    (1.80, 0, 0, 410.0),
    (2.54, 2, 1, 410.0),
    (3.28, 1, 2, 415.0),
    (4.08, 3, 3, 415.0),
    (4.92, 0, 0, 420.0),
    (5.62, 2, 1, 420.0),
    (6.34, 1, 2, 425.0),
    (7.04, 3, 3, 425.0),
    (7.90, 2, 0, 430.0),
    (8.52, 0, 1, 430.0),
    (9.34, 1, 2, 435.0),

    # FASE 2 (10–20s): Aumenta la frecuencia y combinaciones
    (10.46, 3, 3, 470.0),
    (11.14, 1, 0, 475.0),
    (11.68, 2, 1, 480.0),
    (12.14, 0, 2, 485.0),
    (13.28, 3, 3, 490.0),
    (13.80, 2, 0, 495.0),
    (14.30, 1, 1, 500.0),
    (15.04, 0, 2, 505.0),
    (15.70, 2, 3, 510.0),
    (16.20, 3, 0, 515.0),
    (16.60, 1, 1, 515.0),
    (17.12, 0, 2, 520.0),
    (17.70, 2, 3, 525.0),
    (18.16, 1, 0, 525.0),
    (18.72, 3, 1, 530.0),
    (19.14, 0, 2, 535.0),
    (19.70, 2, 3, 540.0),

    # FASE 3 (20–30s): Mayor intensidad musical y secuencias de reflejos
    (20.30, 1, 0, 565.0),
    (20.82, 3, 1, 570.0),
    (21.32, 0, 2, 575.0),
    (21.90, 2, 3, 580.0),
    (22.34, 1, 0, 585.0),
    (22.74, 3, 1, 585.0),
    (23.18, 2, 2, 590.0),
    (23.68, 0, 3, 595.0),
    (24.50, 1, 0, 600.0),
    (24.86, 3, 1, 600.0),
    (25.38, 2, 2, 605.0),
    (25.80, 0, 3, 610.0),
    (26.76, 1, 0, 615.0),
    (27.00, 3, 1, 615.0),
    (27.46, 2, 2, 620.0),
    (27.86, 0, 3, 625.0),
    (28.32, 1, 0, 630.0),
    (28.76, 3, 1, 630.0),
    (29.06, 2, 2, 635.0),
]
