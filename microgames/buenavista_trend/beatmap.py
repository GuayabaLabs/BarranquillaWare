"""
BarranquillaWare - Eventos y Mapa Rítmico de 'El Trend en Buenavista'
Contiene la estructura de datos MusicalNoteEvent y la secuencia EN_BARRANQUILLA_BEATMAP_DATA
calibrada al compás 4/4 de salsa costeña (BPM = 114.0) de 'En Barranquilla Me Quedo'.
"""
from dataclasses import dataclass
from typing import List, Tuple

BPM: float = 114.0
BEAT_SEC: float = 60.0 / BPM


def beat(b: float) -> float:
    """Convierte una posición en negras (compás 4/4 a `BPM`) a segundos."""
    return round(b * BEAT_SEC, 3)


@dataclass
class MusicalNoteEvent:
    """
    Evento musical independiente de la lógica de renderizado.
    Representa una nota/tecla sincronizada con 'En Barranquilla Me Quedo'.
    """
    impact_time: float          # Momento exacto de impacto (en segundos desde el inicio de la canción)
    lane: int                   # Carril correspondiente (0: D, 1: F, 2: J, 3: K)
    sprite_type: int            # Tipo de sprite costeño (0: Raspado, 1: Sombrero vueltiao, 2: Marimonda, 3: Tambor alegre)
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


# Mapa de eventos musicales para 'En Barranquilla Me Quedo' (4/4 salsa a 114 BPM, ~29s).
# Alineación 1:1 carril == icono: 0=Raspado (D), 1=Sombrero (F), 2=Marimonda (J), 3=Tambor (K).
# Cada compás de 4 tiempos [4k, 4k+4) resuelve limpiamente en el tiempo 1 del siguiente compás.
# Formato: (impact_time_sec, lane_0_to_3, sprite_type_0_to_3, fall_speed_px_s)
EN_BARRANQUILLA_BEATMAP_DATA: List[Tuple[float, int, int, float]] = [
    # FASE 1 (0–10s, beats 3–18.5): Entrada y tumbao base (1, 2, 3&), espacios >= 0.526s
    (beat(3.0), 0, 0, 410.0),    # 1.579s — Pickup compás 1 (idx 0: carril 0)
    (beat(4.0), 2, 2, 410.0),    # 2.105s — Compás 2: 1
    (beat(5.0), 1, 1, 415.0),    # 2.632s — Compás 2: 2
    (beat(6.5), 3, 3, 415.0),    # 3.421s — Compás 2: 3& (> 2.30s para test carril erróneo)
    (beat(8.0), 0, 0, 420.0),    # 4.211s — Compás 3: 1 (idx 4: carril 0)
    (beat(9.0), 2, 2, 420.0),    # 4.737s — Compás 3: 2
    (beat(10.5), 1, 1, 425.0),   # 5.526s — Compás 3: 3&
    (beat(12.0), 3, 3, 425.0),   # 6.316s — Compás 4: 1
    (beat(13.0), 1, 1, 430.0),   # 6.842s — Compás 4: 2
    (beat(14.5), 0, 0, 430.0),   # 7.632s — Compás 4: 3&
    (beat(16.0), 2, 2, 435.0),   # 8.421s — Compás 5: 1
    (beat(17.0), 3, 3, 435.0),   # 8.947s — Compás 5: 2
    (beat(18.5), 1, 1, 440.0),   # 9.737s — Compás 5: 3&

    # FASE 2 (10–20s, beats 20–37.5): Clave salsera 3-2 / 2-3 + cáscara (espacios >= 0.263s)
    (beat(20.0), 0, 0, 475.0),   # 10.526s — Compás 6: 1
    (beat(21.5), 2, 2, 480.0),   # 11.316s — Compás 6: 2&
    (beat(22.5), 3, 3, 485.0),   # 11.842s — Compás 6: 3&
    (beat(23.0), 1, 1, 490.0),   # 12.105s — Compás 6: 4
    (beat(24.0), 0, 0, 495.0),   # 12.632s — Compás 7: 1
    (beat(25.0), 1, 1, 495.0),   # 13.158s — Compás 7: 2
    (beat(25.5), 2, 2, 500.0),   # 13.421s — Compás 7: 2&
    (beat(26.5), 3, 3, 505.0),   # 13.947s — Compás 7: 3&
    (beat(27.5), 1, 1, 510.0),   # 14.474s — Compás 7: 4&
    (beat(28.0), 2, 2, 515.0),   # 14.737s — Compás 8: 1
    (beat(29.5), 0, 0, 515.0),   # 15.526s — Compás 8: 2&
    (beat(30.5), 3, 3, 520.0),   # 16.053s — Compás 8: 3&
    (beat(31.0), 1, 1, 525.0),   # 16.316s — Compás 8: 4
    (beat(32.0), 0, 0, 530.0),   # 16.842s — Compás 9: 1
    (beat(33.0), 2, 2, 530.0),   # 17.368s — Compás 9: 2
    (beat(33.5), 3, 3, 535.0),   # 17.632s — Compás 9: 2&
    (beat(34.5), 1, 1, 540.0),   # 18.158s — Compás 9: 3&
    (beat(35.5), 2, 2, 540.0),   # 18.684s — Compás 9: 4&
    (beat(36.0), 0, 0, 545.0),   # 18.947s — Compás 10: 1
    (beat(37.5), 3, 3, 545.0),   # 19.737s — Compás 10: 2&

    # FASE 3 (20–30s, beats 38.5–55): Coro y montuno barranquillero en 4/4 (cierra compás 10 y 11–14)
    (beat(38.5), 1, 1, 570.0),   # 20.263s — Compás 10: 3&
    (beat(39.0), 2, 2, 575.0),   # 20.526s — Compás 10: 4
    (beat(40.0), 0, 0, 580.0),   # 21.053s — Compás 11: 1
    (beat(40.5), 1, 1, 580.0),   # 21.316s — Compás 11: 1&
    (beat(41.5), 3, 3, 585.0),   # 21.842s — Compás 11: 2&
    (beat(42.0), 2, 2, 590.0),   # 22.105s — Compás 11: 3
    (beat(42.5), 0, 0, 590.0),   # 22.368s — Compás 11: 3&
    (beat(43.5), 1, 1, 595.0),   # 22.895s — Compás 11: 4&
    (beat(44.0), 3, 3, 600.0),   # 23.158s — Compás 12: 1
    (beat(45.0), 2, 2, 600.0),   # 23.684s — Compás 12: 2
    (beat(45.5), 0, 0, 605.0),   # 23.947s — Compás 12: 2&
    (beat(46.5), 1, 1, 610.0),   # 24.474s — Compás 12: 3&
    (beat(47.0), 3, 3, 610.0),   # 24.737s — Compás 12: 4
    (beat(47.5), 2, 2, 615.0),   # 25.000s — Compás 12: 4&
    (beat(48.0), 0, 0, 615.0),   # 25.263s — Compás 13: 1
    (beat(48.5), 1, 1, 620.0),   # 25.526s — Compás 13: 1&
    (beat(49.5), 3, 3, 620.0),   # 26.053s — Compás 13: 2&
    (beat(50.0), 2, 2, 625.0),   # 26.316s — Compás 13: 3
    (beat(50.5), 0, 0, 625.0),   # 26.579s — Compás 13: 3&
    (beat(51.5), 1, 1, 630.0),   # 27.105s — Compás 13: 4&
    (beat(52.0), 3, 3, 630.0),   # 27.368s — Compás 14: 1
    (beat(53.0), 2, 2, 635.0),   # 27.895s — Compás 14: 2
    (beat(53.5), 0, 0, 635.0),   # 28.158s — Compás 14: 2&
    (beat(54.5), 1, 1, 640.0),   # 28.684s — Compás 14: 3&
    (beat(55.0), 3, 3, 640.0),   # 28.947s — Compás 14: 4 (cierre final)
]

# Alias de retrocompatibilidad para pruebas externas que importen IMITADORA_BEATMAP_DATA
IMITADORA_BEATMAP_DATA = EN_BARRANQUILLA_BEATMAP_DATA
