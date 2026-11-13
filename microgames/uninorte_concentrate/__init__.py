"""
BarranquillaWare - Subpaquete de Microjuego '¡Concéntrate, llave!'
Re-exporta UninorteConcentrateMicrogame y sus entidades para 100% retrocompatibilidad.
"""
from microgames.uninorte_concentrate.game import UninorteConcentrateMicrogame
from microgames.uninorte_concentrate.entities import (
    Student,
    Distraction,
    VirtualCursor,
    ProgressBar,
    ScoreManager,
)

__all__ = [
    "UninorteConcentrateMicrogame",
    "Student",
    "Distraction",
    "VirtualCursor",
    "ProgressBar",
    "ScoreManager",
]
