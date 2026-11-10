import os
import numpy as np
import pygame
from typing import Optional
from core.settings import SettingsManager

class AudioManager:
    """
    Gestor de audio y efectos sonoros interactivos con persistencia en settings.json.
    Soporta múltiples pistas BGM (Menú Principal y Selección de Modo)
    y genera efectos sonoros procedurales de alta respuesta (Game Feel).
    """
    _instance: Optional['AudioManager'] = None

    def __init__(self, base_assets_dir: str = "assets") -> None:
        self.base_assets_dir = base_assets_dir
        self.settings = SettingsManager.get_instance()

        self.music_enabled: bool = bool(self.settings.get("music_enabled", True))
        self.sound_enabled: bool = bool(self.settings.get("sound_enabled", True))
        self.music_volume: float = float(self.settings.get("music_volume", 0.65))
        self.sfx_volume: float = float(self.settings.get("sfx_volume", 0.8))

        self.current_track: Optional[str] = None
        self._hover_sound: Optional[pygame.mixer.Sound] = None
        self._click_sound: Optional[pygame.mixer.Sound] = None
        self._iguana_sound: Optional[pygame.mixer.Sound] = None
        self._pigeon_sound: Optional[pygame.mixer.Sound] = None
        self._win_sound: Optional[pygame.mixer.Sound] = None
        self._lose_sound: Optional[pygame.mixer.Sound] = None
        self._drum_sound: Optional[pygame.mixer.Sound] = None
        self._whistle_sound: Optional[pygame.mixer.Sound] = None

        self._init_audio()
        self.play_bgm("7am_ancpg_ost_main_menu.ogg")

    @classmethod
    def get_instance(cls, base_assets_dir: str = "assets") -> 'AudioManager':
        if cls._instance is None:
            cls._instance = AudioManager(base_assets_dir)
        return cls._instance

    def _init_audio(self) -> None:
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            except Exception:
                return

        self._generate_procedural_sounds()

    def play_bgm(self, filename: str, force_restart: bool = False) -> None:
        """Carga y reproduce una pista BGM en loop si no es la pista que ya suena."""
        if self.current_track == filename and not force_restart:
            return

        self.current_track = filename
        track_path = os.path.join(self.base_assets_dir, filename)
        if os.path.exists(track_path):
            try:
                pygame.mixer.music.load(track_path)
                pygame.mixer.music.set_volume(self.music_volume)
                if self.music_enabled:
                    pygame.mixer.music.play(loops=-1, fade_ms=300)
            except Exception as e:
                print(f"Aviso: no se pudo cargar la música {filename}: {e}")

    def _generate_procedural_sounds(self) -> None:
        """Genera efectos de sonido procedurales tipo pop / arcade nítidos."""
        try:
            sr = 44100
            # 1. Hover Sound: chirping suave de 0.04s
            duration_hover = 0.04
            t_hover = np.linspace(0, duration_hover, int(sr * duration_hover), False)
            freq_hover = np.linspace(540, 840, len(t_hover))
            env_hover = np.sin(np.pi * t_hover / duration_hover) ** 1.5
            wave_hover = np.sin(2 * np.pi * freq_hover * t_hover) * env_hover * 0.25
            arr_hover = (wave_hover * 32767).astype(np.int16)
            self._hover_sound = pygame.sndarray.make_sound(np.column_stack((arr_hover, arr_hover)))

            # 2. Click Sound: pop elástico de 0.08s
            duration_click = 0.08
            t_click = np.linspace(0, duration_click, int(sr * duration_click), False)
            freq_click = np.geomspace(440, 160, len(t_click))
            env_click = np.exp(-t_click * 35.0)
            wave_click = np.sin(2 * np.pi * freq_click * t_click) * env_click * 0.4
            arr_click = (wave_click * 32767).astype(np.int16)
            self._click_sound = pygame.sndarray.make_sound(np.column_stack((arr_click, arr_click)))

            # 3. Iguana Chirp
            duration_ig = 0.09
            t_ig = np.linspace(0, duration_ig, int(sr * duration_ig), False)
            freq_ig = 380 + 120 * np.sin(2 * np.pi * 22 * t_ig)
            env_ig = np.sin(np.pi * t_ig / duration_ig)
            wave_ig = np.sin(2 * np.pi * freq_ig * t_ig) * env_ig * 0.3
            arr_ig = (wave_ig * 32767).astype(np.int16)
            self._iguana_sound = pygame.sndarray.make_sound(np.column_stack((arr_ig, arr_ig)))

            # 4. Pigeon Coo (Arrullo cómico de paloma currambera)
            duration_pg = 0.14
            t_pg = np.linspace(0, duration_pg, int(sr * duration_pg), False)
            freq_pg = 260 + 40 * np.sin(2 * np.pi * 14 * t_pg)
            env_pg = np.sin(np.pi * t_pg / duration_pg) ** 2
            wave_pg = np.sin(2 * np.pi * freq_pg * t_pg) * env_pg * 0.35
            arr_pg = (wave_pg * 32767).astype(np.int16)
            self._pigeon_sound = pygame.sndarray.make_sound(np.column_stack((arr_pg, arr_pg)))
            # 5. Win Sound (Campaneo ascendente triunfal C5 -> E5 -> G5 -> C6)
            duration_win = 0.28
            t_win = np.linspace(0, duration_win, int(sr * duration_win), False)
            freq_win = np.zeros_like(t_win)
            n_pts = len(t_win)
            freq_win[:n_pts // 4] = 523.25
            freq_win[n_pts // 4:n_pts // 2] = 659.25
            freq_win[n_pts // 2:3 * n_pts // 4] = 783.99
            freq_win[3 * n_pts // 4:] = 1046.50
            env_win = np.sin(np.pi * t_win / duration_win) ** 0.8
            wave_win = (np.sin(2 * np.pi * freq_win * t_win) + 0.3 * np.sin(4 * np.pi * freq_win * t_win)) * env_win * 0.32
            arr_win = (wave_win * 32767).astype(np.int16)
            self._win_sound = pygame.sndarray.make_sound(np.column_stack((arr_win, arr_win)))

            # 6. Lose Sound (Buzzer descendente cómico 420Hz -> 160Hz)
            duration_lose = 0.32
            t_lose = np.linspace(0, duration_lose, int(sr * duration_lose), False)
            freq_lose = np.geomspace(420, 160, len(t_lose))
            env_lose = np.exp(-t_lose * 6.5)
            wave_lose = np.sign(np.sin(2 * np.pi * freq_lose * t_lose)) * env_lose * 0.22
            arr_lose = (wave_lose * 32767).astype(np.int16)
            self._lose_sound = pygame.sndarray.make_sound(np.column_stack((arr_lose, arr_lose)))

            # 7. Tambor Alegre (Golpe seco resonante de percusión cumbiera)
            duration_drum = 0.16
            t_drum = np.linspace(0, duration_drum, int(sr * duration_drum), False)
            freq_drum = np.geomspace(220, 60, len(t_drum))
            env_drum = np.exp(-t_drum * 26.0)
            wave_drum = np.sin(2 * np.pi * freq_drum * t_drum) * env_drum * 0.45
            slap_noise = np.random.uniform(-0.25, 0.25, len(t_drum)) * np.exp(-t_drum * 120.0)
            wave_drum += slap_noise
            arr_drum = (np.clip(wave_drum, -1.0, 1.0) * 32767).astype(np.int16)
            self._drum_sound = pygame.sndarray.make_sound(np.column_stack((arr_drum, arr_drum)))

            # 8. Silbato de Carnaval (Pito de Guacherna caribeño)
            duration_whistle = 0.12
            t_wh = np.linspace(0, duration_whistle, int(sr * duration_whistle), False)
            freq_wh = 1950.0 + 350.0 * np.sin(2 * np.pi * 35.0 * t_wh)
            env_wh = np.sin(np.pi * t_wh / duration_whistle) ** 0.6
            wave_wh = np.sin(2 * np.pi * freq_wh * t_wh) * env_wh * 0.28
            arr_wh = (wave_wh * 32767).astype(np.int16)
            self._whistle_sound = pygame.sndarray.make_sound(np.column_stack((arr_wh, arr_wh)))
        except Exception:
            pass

    def toggle_music(self) -> bool:
        self.music_enabled = not self.music_enabled
        self.settings.set("music_enabled", self.music_enabled)
        if not self.music_enabled:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()
            if not pygame.mixer.music.get_busy() and self.current_track:
                self.play_bgm(self.current_track, force_restart=True)
        return self.music_enabled

    def toggle_sound(self) -> bool:
        self.sound_enabled = not self.sound_enabled
        self.settings.set("sound_enabled", self.sound_enabled)
        if self.sound_enabled:
            self.play_click()
        return self.sound_enabled

    def play_hover(self) -> None:
        if self.sound_enabled and self._hover_sound:
            self._hover_sound.set_volume(self.sfx_volume * 0.35)
            self._hover_sound.play()

    def play_click(self) -> None:
        if self.sound_enabled and self._click_sound:
            self._click_sound.set_volume(self.sfx_volume)
            self._click_sound.play()

    def play_iguana(self) -> None:
        if self.sound_enabled and self._iguana_sound:
            self._iguana_sound.set_volume(self.sfx_volume * 0.75)
            self._iguana_sound.play()

    def play_pigeon(self) -> None:
        if self.sound_enabled and self._pigeon_sound:
            self._pigeon_sound.set_volume(self.sfx_volume * 0.75)
            self._pigeon_sound.play()
    def play_win(self) -> None:
        if self.sound_enabled and self._win_sound:
            self._win_sound.set_volume(self.sfx_volume * 0.85)
            self._win_sound.play()

    def play_lose(self) -> None:
        if self.sound_enabled and self._lose_sound:
            self._lose_sound.set_volume(self.sfx_volume * 0.85)
            self._lose_sound.play()

    def play_drum(self) -> None:
        if self.sound_enabled and self._drum_sound:
            self._drum_sound.set_volume(self.sfx_volume * 0.9)
            self._drum_sound.play()

    def play_whistle(self) -> None:
        if self.sound_enabled and self._whistle_sound:
            self._whistle_sound.set_volume(self.sfx_volume * 0.7)
            self._whistle_sound.play()

