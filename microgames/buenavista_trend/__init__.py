"""
BarranquillaWare - Subpaquete de Microjuego 'El Trend en Buenavista'
Re-exporta BuenavistaTrendMicrogame y beatmap para 100% retrocompatibilidad.
"""
from microgames.buenavista_trend.game import BuenavistaTrendMicrogame
from microgames.buenavista_trend.beatmap import (
    MusicalNoteEvent,
    EN_BARRANQUILLA_BEATMAP_DATA,
    IMITADORA_BEATMAP_DATA,
)

__all__ = [
    "BuenavistaTrendMicrogame",
    "MusicalNoteEvent",
    "EN_BARRANQUILLA_BEATMAP_DATA",
    "IMITADORA_BEATMAP_DATA",
]
