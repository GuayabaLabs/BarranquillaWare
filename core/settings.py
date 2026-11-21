import copy
import json
import os
from datetime import datetime
from typing import Dict, Any

SETTINGS_FILE = "settings.json"
SAVE_VERSION = 1

CHARACTER_DISPLAY_NAMES: Dict[str, str] = {
    "westcol": "Westcol",
    "char": "Alex Char",
    "katherine": "Katherine",
    "valdiri": "Valdiri",
}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "music_enabled": True,
    "sound_enabled": True,
    "voice_enabled": True,
    "camera_enabled": True,
    "music_volume": 0.65,
    "sfx_volume": 0.8,
    "voice_volume": 1.0,
    "brightness": 1.0,
    "colorblind_mode": "off",
    "colorblind_intensity": 0.0,
    "fullscreen": False,
    "window_width": 1920,
    "window_height": 1080,
    "arcade_high_score": 0,
    "trofeosObtenidos": [],
    "story_progress": {
        "save_version": SAVE_VERSION,
        "has_active_save": False,
        "character_id": "westcol",
        "current_node_id": 0,
        "unlocked_locations": ["uninorte"],
        "completed_microgames": [],
        "unlocked_achievements": [],
        "high_score": 0,
        "followers": 6700000,
        "likes": 0,
        "achievements": 0,
        "last_camera_x": 835.0,
        "last_camera_y": 470.0,
        "weather": "day",
        "saved_at": "",
        "save_source": "",
    }
}

CHARACTER_BASE_FOLLOWERS: Dict[str, int] = {
    "westcol": 6700000,      # 6.7M (tarjeta oficial)
    "char": 810000,          # 810K (tarjeta oficial)
    "katherine": 250,        # 250 (tarjeta oficial)
    "valdiri": 10000000,     # 10M (tarjeta oficial)
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
        follower_Step = 200_000      # +0.2M por ronda (10M -> 10.2M -> 10.4M...)
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

    def __init__(self, filepath: str | None = None) -> None:
        default_file = (
            SETTINGS_FILE
            if SETTINGS_FILE != "settings.json"
            else (os.environ.get("BARRANQUILLAWARE_SETTINGS_FILE") or SETTINGS_FILE)
        )
        self.filepath = filepath or default_file
        self.data: Dict[str, Any] = copy.deepcopy(DEFAULT_SETTINGS)
        self.load()

    @classmethod
    def get_instance(cls) -> 'SettingsManager':
        if cls._instance is None:
            cls._instance = SettingsManager()
        return cls._instance

    def _normalize_story_progress(self, raw: Any) -> Dict[str, Any]:
        merged = copy.deepcopy(DEFAULT_SETTINGS["story_progress"])
        if isinstance(raw, dict):
            merged.update(copy.deepcopy(raw))
        if not isinstance(merged.get("unlocked_locations"), list):
            merged["unlocked_locations"] = ["uninorte"]
        if not isinstance(merged.get("completed_microgames"), list):
            merged["completed_microgames"] = []
        if not isinstance(merged.get("unlocked_achievements"), list):
            merged["unlocked_achievements"] = []
        # Las partidas anteriores conservan su progreso con el personaje sustituto.
        if str(merged.get("character_id", "")).lower() == "shakira":
            merged["character_id"] = "valdiri"
            metrics = compute_social_metrics("valdiri", int(merged.get("high_score", 0)), 0)
            merged["followers"] = metrics["followers"]
            merged["likes"] = metrics["likes"]
        return merged

    def load(self) -> None:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data.update(loaded)
                        self.data["story_progress"] = self._normalize_story_progress(
                            self.data.get("story_progress")
                        )
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
            progress = copy.deepcopy(DEFAULT_SETTINGS["story_progress"])
            self.data["story_progress"] = progress
            self.save()
        return self._normalize_story_progress(progress)

    def update_story_progress(self, **kwargs: Any) -> None:
        """Actualiza campos específicos del progreso de Modo Historia y persiste a disco."""
        if not isinstance(self.data.get("story_progress"), dict):
            self.data["story_progress"] = copy.deepcopy(DEFAULT_SETTINGS["story_progress"])
        else:
            self.data["story_progress"] = self._normalize_story_progress(self.data["story_progress"])

        self.data["story_progress"].update(copy.deepcopy(kwargs))
        self.data["story_progress"]["save_version"] = SAVE_VERSION

        is_active = bool(self.data["story_progress"].get("has_active_save"))
        if is_active:
            if "saved_at" not in kwargs or not kwargs.get("saved_at"):
                self.data["story_progress"]["saved_at"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            if "save_source" not in kwargs and not self.data["story_progress"].get("save_source"):
                self.data["story_progress"]["save_source"] = "auto"

        self.save()

    def reset_story_progress(self, character_id: str = "westcol") -> None:
        """Reinicia el progreso del Modo Historia y logros de campaña sin tocar ajustes del jugador."""
        char_key = (character_id or "westcol").lower()
        fresh = copy.deepcopy(DEFAULT_SETTINGS["story_progress"])
        fresh["character_id"] = char_key
        fresh["unlocked_locations"] = ["uninorte"]
        fresh["completed_microgames"] = []
        fresh["unlocked_achievements"] = []
        fresh["trofeos_obtenidos"] = []
        fresh["has_active_save"] = False
        fresh["weather"] = "day"
        fresh["saved_at"] = ""
        fresh["save_source"] = ""
        metrics = compute_social_metrics(char_key, 0, 0)
        fresh["followers"] = metrics["followers"]
        fresh["likes"] = metrics["likes"]
        fresh["achievements"] = metrics["achievements"]
        self.data["story_progress"] = fresh
        self.data["trofeosObtenidos"] = []
        self.data.pop("achievements_progress", None)
        self.save()

    def delete_story_save(self) -> None:
        """Elimina limpiamente la partida guardada de Modo Historia conservando preferencias."""
        self.reset_story_progress(character_id="westcol")

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

    def get_story_save_summary(self) -> Dict[str, Any]:
        """Retorna un resumen canónico y consistente de la partida guardada para UI y menús."""
        has_save = self.has_saved_story()
        progress = self.get_story_progress()
        char_id = str(progress.get("character_id", "westcol")).lower()
        char_label = CHARACTER_DISPLAY_NAMES.get(char_id, char_id.capitalize())
        high_score = int(progress.get("high_score", 0))
        completed_list = list(progress.get("completed_microgames", []))
        done_set = set(completed_list)

        campaign_stages = [
            ("uninorte", "Campus Uninorte", ("uninorte_sprint", "uninorte_concentrate")),
            ("ventana", "Ventana al Mundo", ("punch_alert",)),
            ("buenavista", "C.C. Buenavista", ("buenavista_trend",)),
            ("metropolitano", "Estadio Metropolitano", ("metropolitano_moderacion",)),
            ("aleta", "Aleta del Tiburón", ("fritanga_84",)),
        ]
        levels_cleared = 0
        next_district = "¡Aventura Completada!"
        found_next = False
        for _key, title, req_ids in campaign_stages:
            if all(req in done_set for req in req_ids):
                levels_cleared += 1
            elif not found_next:
                next_district = title
                found_next = True

        metrics = compute_social_metrics(char_id, high_score, levels_cleared)
        trofeos = self.get("trofeosObtenidos", [])
        trophies_count = len(trofeos) if isinstance(trofeos, list) else 0
        trophies_total = 4

        saved_at = str(progress.get("saved_at", "") or "").strip()
        if has_save and not saved_at:
            saved_at = "Sesión anterior"
        save_source = str(progress.get("save_source", "") or "").strip().lower()
        save_source_label = "Guardado manual" if save_source == "manual" else "Auto-guardado"

        weather = str(progress.get("weather", "day") or "day").lower()
        weather_labels = {
            "day": "Sol Caribe",
            "sunset": "Atardecer",
            "night": "Noche",
            "rain": "Lluvia",
        }

        return {
            "has_save": has_save,
            "character_id": char_id,
            "character_name": char_label,
            "high_score": high_score,
            "completed_microgames": completed_list,
            "levels_cleared": levels_cleared,
            "total_levels": len(campaign_stages),
            "next_district": next_district,
            "followers": metrics["followers"],
            "likes": metrics["likes"],
            "followers_text": metrics["followers_text"],
            "likes_text": metrics["likes_text"],
            "trophies_count": trophies_count,
            "trophies_total": trophies_total,
            "current_node_id": int(progress.get("current_node_id", 0)),
            "weather": weather,
            "weather_label": weather_labels.get(weather, "Sol Caribe"),
            "saved_at": saved_at,
            "save_source": save_source,
            "save_source_label": save_source_label,
        }

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
