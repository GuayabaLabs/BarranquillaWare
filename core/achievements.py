"""
Sistema Central de Logros (Achievements) para BarranquillaWare (Tarea 002).
Gestiona los 4 logros oficiales ocultos en el mapa y los minijuegos,
con persistencia en disco, recompensas de seguidores/likes y notificaciones.
"""

from typing import Any, Dict, List, Optional
from core.settings import SettingsManager

# Identificadores canónicos de los 4 logros
ACHIEVEMENT_PALOMA = "logro_paloma"
ACHIEVEMENT_UNINORTE = "logro_uninorte"
ACHIEVEMENT_METRO = "logro_metro"
ACHIEVEMENT_BUENAVISTA = "logro_buenavista"

ACHIEVEMENTS_CATALOG: Dict[str, Dict[str, Any]] = {
    ACHIEVEMENT_PALOMA: {
        "id": ACHIEVEMENT_PALOMA,
        "title": "¡Aja, Curramba!",
        "category": "HISTORIA",
        "desc": "Conociste a la sabia Paloma de Curramba y aceptaste salvar la ciudad de las pantallas.",
        "hint": "Habla con la Paloma en cualquier distrito del mapa.",
        "reward_followers": 200,
        "reward_likes": 100,
        "order": 1
    },
    ACHIEVEMENT_UNINORTE: {
        "id": ACHIEVEMENT_UNINORTE,
        "title": "Cerebro Desconectado",
        "category": "ACADÉMICO",
        "desc": "Estudiaste en la biblioteca de Uninorte despejando todas las notificaciones virales.",
        "hint": "Supera la ronda de concentración en el Campus Uninorte.",
        "reward_followers": 350,
        "reward_likes": 200,
        "order": 2
    },
    ACHIEVEMENT_METRO: {
        "id": ACHIEVEMENT_METRO,
        "title": "La Muralla del Metro",
        "category": "DEPORTE",
        "desc": "Atajaste los penales o moderaste el chat protegiendo al Junior de Barranquilla.",
        "hint": "Supera el desafío del Estadio Metropolitano.",
        "reward_followers": 500,
        "reward_likes": 400,
        "order": 3
    },
    ACHIEVEMENT_BUENAVISTA: {
        "id": ACHIEVEMENT_BUENAVISTA,
        "title": "Trendsetter de Curramba",
        "category": "VIRAL",
        "desc": "Demostraste tu sabor caribeño bailando la coreografía oficial en el CC Buenavista.",
        "hint": "Clava el ritmo en el minijuego musical de Buenavista.",
        "reward_followers": 400,
        "reward_likes": 500,
        "order": 4
    }
}

TOTAL_ACHIEVEMENTS = len(ACHIEVEMENTS_CATALOG)


class AchievementManager:
    """Administrador centralizado de logros de BarranquillaWare."""
    _instance: Optional['AchievementManager'] = None

    def __init__(self) -> None:
        self.settings = SettingsManager.get_instance()

    @classmethod
    def get_instance(cls) -> 'AchievementManager':
        if cls._instance is None:
            cls._instance = AchievementManager()
        return cls._instance

    def get_unlocked_ids(self) -> List[str]:
        """Retorna la lista de identificadores de logros desbloqueados."""
        progress = self.settings.get_story_progress()
        unlocked = progress.get("unlocked_achievements")
        if not isinstance(unlocked, list):
            unlocked = []
        return list(unlocked)

    def is_unlocked(self, achievement_id: str) -> bool:
        """Verifica si un logro ya ha sido conseguido."""
        return achievement_id in self.get_unlocked_ids()

    def get_unlocked_count(self) -> int:
        """Retorna la cantidad de logros desbloqueados (0 a 4)."""
        return len(self.get_unlocked_ids())

    def unlock(self, achievement_id: str) -> Optional[Dict[str, Any]]:
        """
        Intenta desbloquear un logro.
        Retorna la información del logro si fue recién desbloqueado, o None si ya lo estaba.
        """
        if achievement_id not in ACHIEVEMENTS_CATALOG:
            return None

        unlocked = self.get_unlocked_ids()
        if achievement_id in unlocked:
            return None  # Ya estaba desbloqueado

        unlocked.append(achievement_id)
        info = ACHIEVEMENTS_CATALOG[achievement_id]

        # Actualizar progreso y métricas sociales
        progress = self.settings.get_story_progress()
        current_followers = progress.get("followers", 0) + info.get("reward_followers", 0)
        current_likes = progress.get("likes", 0) + info.get("reward_likes", 0)

        self.settings.update_story_progress(
            unlocked_achievements=unlocked,
            achievements=len(unlocked),
            followers=current_followers,
            likes=current_likes
        )

        return info

    def get_all_achievements(self) -> List[Dict[str, Any]]:
        """Retorna la lista de todos los logros ordenados con su estado activo."""
        unlocked = set(self.get_unlocked_ids())
        result = []
        for ach in sorted(ACHIEVEMENTS_CATALOG.values(), key=lambda a: a["order"]):
            item = dict(ach)
            item["unlocked"] = ach["id"] in unlocked
            result.append(item)
        return result
