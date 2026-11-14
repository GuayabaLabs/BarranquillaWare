import json
import os
from typing import Dict, Any

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "music_enabled": True,
    "sound_enabled": True,
    "music_volume": 0.65,
    "sfx_volume": 0.8,
    "brightness": 1.0,
    "colorblind_mode": "off",
    "colorblind_intensity": 0.0,
    "fullscreen": False,
    "window_width": 1920,
    "window_height": 1080,
    "arcade_high_score": 0,
    "trofeosObtenidos": [],
    "story_progress": {
        "has_active_save": False,
        "character_id": "westcol",
        "current_node_id": 0,
        "unlocked_locations": ["uninorte"],
        "completed_microgames": [],
        "high_score": 0,
        "followers": 6700000,
        "likes": 0,
        "achievements": 0,
        "last_camera_x": 835.0,
        "last_camera_y": 470.0
    }
}

CHARACTER_BASE_FOLLOWERS: Dict[str, int] = {
    "westcol": 6700000,      # 6.7M (tarjeta oficial)
    "char": 810000,          # 810K (tarjeta oficial)
    "katherine": 250,        # 250 (tarjeta oficial)
    "shakira": 103300000,    # 103.3M (tarjeta oficial)
}

def format_social_count(value: int) -> str:
    """Formatea un entero de seguidores o likes en notación compacta (ej: 810K, 6.7M, 103.3M)."""
    val = max(0, int(value))
    if val >= 1_000_000:
        m_val = val / 1_000_000.0
        formatted = f"{m_val:.1f}".rstrip("0").rstrip(".")
        return f"{formatted}M"
    if val >= 1_000:
        k_val = val / 1_000.0
        formatted = f"{k_val:.1f}".rstrip("0").rstrip(".")
        return f"{formatted}K"
    return str(val)

def compute_social_metrics(character_id: str, high_score: int, completed_levels_count: int) -> Dict[str, Any]:
    """
    Calcula las métricas de Seguidores, Likes y Logros según el personaje activo,
    el puntaje acumulado (100 pts por ronda superada) y los niveles de historia despejados.
    """
    char_key = (character_id or "westcol").lower()
    base_followers = CHARACTER_BASE_FOLLOWERS.get(char_key, 6700000)
    rounds_cleared = max(0, int(high_score) // 100)

    # Crecimiento proporcional por ronda superada para que el número en la cápsula cambie visiblemente
    if base_followers >= 10_000_000:
        follower_Step = 200_000      # +0.2M por ronda (103.3M -> 103.5M -> 103.7M...)
        likes_step = 450_000         # +450K likes por ronda
    elif base_followers >= 1_000_000:
        follower_Step = 100_000      # +0.1M por ronda (6.7M -> 6.8M -> 6.9M...)
        likes_step = 125_000         # +125K likes por ronda
    elif base_followers >= 10_000:
        follower_Step = 15_000       # +15K por ronda (810K -> 825K -> 840K...)
        likes_step = 35_000          # +35K likes por ronda
    else:
        follower_Step = 180          # +180 por ronda (250 -> 430 -> 610 -> 1.3K...)
        likes_step = 650             # +650 likes por ronda

    total_followers = base_followers + rounds_cleared * follower_Step
    total_likes = rounds_cleared * likes_step
    total_achievements = max(0, min(4, int(completed_levels_count)))

    return {
        "followers": total_followers,
        "likes": total_likes,
        "achievements": total_achievements,
        "followers_text": format_social_count(total_followers),
        "likes_text": format_social_count(total_likes),
        "achievements_text": f"{total_achievements}/4"
    }

class SettingsManager:
    """
    Gestor de configuración persistente con settings.json.
    Carga y guarda automáticamente sin interrumpir la ejecución si el archivo no existe.
    """
    _instance = None

    def __init__(self, filepath: str = SETTINGS_FILE) -> None:
        self.filepath = filepath
        self.data: Dict[str, Any] = dict(DEFAULT_SETTINGS)
        self.load()

    @classmethod
    def get_instance(cls) -> 'SettingsManager':
        if cls._instance is None:
            cls._instance = SettingsManager()
        return cls._instance

    def load(self) -> None:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data.update(loaded)
            except Exception as e:
                print(f"Aviso: no se pudo leer {self.filepath}, usando valores por defecto: {e}")
        else:
            self.save()

    def save(self) -> None:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Aviso: no se pudo guardar {self.filepath}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def get_story_progress(self) -> Dict[str, Any]:
        """Retorna una copia del diccionario con el progreso de Modo Historia."""
        progress = self.data.get("story_progress")
        if not isinstance(progress, dict):
            progress = dict(DEFAULT_SETTINGS["story_progress"])
            self.data["story_progress"] = progress
            self.save()
        return dict(progress)

    def update_story_progress(self, **kwargs: Any) -> None:
        """Actualiza campos específicos del progreso de Modo Historia y persiste a disco."""
        if not isinstance(self.data.get("story_progress"), dict):
            self.data["story_progress"] = dict(DEFAULT_SETTINGS["story_progress"])
        self.data["story_progress"].update(kwargs)
        self.save()

    def reset_story_progress(self, character_id: str = "westcol") -> None:
        """Reinicia el progreso del Modo Historia a los valores iniciales por defecto."""
        char_key = (character_id or "westcol").lower()
        fresh = dict(DEFAULT_SETTINGS["story_progress"])
        fresh["character_id"] = char_key
        fresh["unlocked_locations"] = ["uninorte"]
        fresh["completed_microgames"] = []
        fresh["trofeos_obtenidos"] = []
        metrics = compute_social_metrics(char_key, 0, 0)
        fresh["followers"] = metrics["followers"]
        fresh["likes"] = metrics["likes"]
        fresh["achievements"] = metrics["achievements"]
        self.data["story_progress"] = fresh
        self.data["trofeosObtenidos"] = []
        self.save()

    def has_saved_story(self) -> bool:
        """Retorna True si existe una partida activa o con avances en el Modo Historia."""
        progress = self.get_story_progress()
        if progress.get("has_active_save"):
            return True
        if len(progress.get("completed_microgames", [])) > 0:
            return True
        if int(progress.get("high_score", 0)) > 0:
            return True
        if int(progress.get("current_node_id", 0)) != 0:
            return True
        return False

    def get_arcade_high_score(self) -> int:
        """Obtiene el récord histórico del Modo Arcade."""
        return int(self.data.get("arcade_high_score", 0))

    def update_arcade_high_score(self, score: int) -> bool:
        """
        Actualiza el récord del Modo Arcade si el puntaje actual supera al récord anterior.
        Retorna True si se batió el récord, False en caso contrario.
        """
        current_best = self.get_arcade_high_score()
        if score > current_best:
            self.data["arcade_high_score"] = score
            self.save()
            return True
        return False
