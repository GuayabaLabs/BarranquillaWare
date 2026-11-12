"""
BarranquillaWare - Subpaquete de la Escena del Mapa Mundial (Modo Historia)
Re-exporta todos los símbolos para 100% retrocompatibilidad con tests y menús.
"""
from scenes.story_map.scene import StoryMapScene, Camera2D, MICROGAME_MAP
from scenes.story_map_data import (
    STORY_CAMPAIGN_ORDER,
    STORY_SECRET_POIS,
    STORY_PLAYABLE_POIS,
    STORY_LEVEL_STAGES,
    PALOMA_STORY_DIALOGS,
)
from scenes.story_map.ui_dialogs import StoryMapUI

__all__ = [
    "StoryMapScene",
    "Camera2D",
    "MICROGAME_MAP",
    "STORY_CAMPAIGN_ORDER",
    "STORY_SECRET_POIS",
    "STORY_PLAYABLE_POIS",
    "STORY_LEVEL_STAGES",
    "PALOMA_STORY_DIALOGS",
    "StoryMapUI",
]
