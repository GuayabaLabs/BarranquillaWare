import json
import os
from typing import Dict, Any

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "music_enabled": True,
    "sound_enabled": True,
    "music_volume": 0.65,
    "sfx_volume": 0.8,
    "fullscreen": False,
    "window_width": 1920,
    "window_height": 1080,
    "arcade_high_score": 0,
    "story_progress": {
        "character_id": "westcol",
        "unlocked_locations": ["uninorte"],
        "completed_microgames": [],
        "high_score": 0,
        "last_camera_x": 835.0,
        "last_camera_y": 470.0
    }
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

    def reset_story_progress(self) -> None:
        """Reinicia el progreso del Modo Historia a los valores iniciales por defecto."""
        self.data["story_progress"] = dict(DEFAULT_SETTINGS["story_progress"])
        self.save()

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
