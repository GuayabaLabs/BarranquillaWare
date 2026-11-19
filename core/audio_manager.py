import os
import time
import numpy as np
import pygame
from typing import Dict, Optional, Tuple
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
        self._bgm_volume_scale: float = 1.0
        self._duck_factor: float = 1.0
        self._duck_target: float = 1.0
        self.duck_level: float = 0.26
        self._voice_cache: Dict[Tuple[str, Optional[tuple]], pygame.mixer.Sound] = {}
        self._voice_channel: Optional[pygame.mixer.Channel] = None
        self._voice_end_time: float = 0.0
        self._hover_sound: Optional[pygame.mixer.Sound] = None
        self._click_sound: Optional[pygame.mixer.Sound] = None
        self._iguana_sound: Optional[pygame.mixer.Sound] = None
        self._pigeon_sound: Optional[pygame.mixer.Sound] = None
        self._win_sound: Optional[pygame.mixer.Sound] = None
        self._lose_sound: Optional[pygame.mixer.Sound] = None
        self._drum_sound: Optional[pygame.mixer.Sound] = None
        self._whistle_sound: Optional[pygame.mixer.Sound] = None
        self._jump_sound: Optional[pygame.mixer.Sound] = None
        self._hit_sound: Optional[pygame.mixer.Sound] = None
        self._miss_sound: Optional[pygame.mixer.Sound] = None

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

        self._ensure_voice_channel()
        self._generate_procedural_sounds()

    def _ensure_voice_channel(self) -> Optional[pygame.mixer.Channel]:
        """Reserva un canal dedicado para voces de Paloma/SEOR y evita solapamientos."""
        mixer_init = pygame.mixer.get_init()
        if not mixer_init:
            self._reserved_voice_channel = None
            self._reserved_voice_mixer_init = None
            return None
        try:
            if pygame.mixer.get_num_channels() < 4:
                pygame.mixer.set_num_channels(8)
            pygame.mixer.set_reserved(1)
            cached_ch = getattr(self, "_reserved_voice_channel", None)
            if cached_ch is None or getattr(self, "_reserved_voice_mixer_init", None) != mixer_init:
                cached_ch = pygame.mixer.Channel(0)
                self._reserved_voice_channel = cached_ch
                self._reserved_voice_mixer_init = mixer_init
            return cached_ch
        except Exception:
            return None

    def _effective_bgm_volume(self) -> float:
        if not self.music_enabled:
            return 0.0
        return max(0.0, min(1.0, self.music_volume * self._bgm_volume_scale * self._duck_factor))

    def sync_music_volume(self) -> None:
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(self._effective_bgm_volume())

    def play_bgm(
        self,
        filename: str,
        force_restart: bool = False,
        volume_scale: float = 1.0,
    ) -> None:
        """Carga y reproduce una pista en loop con un volumen relativo opcional."""
        self._bgm_volume_scale = max(0.0, float(volume_scale))
        if self.current_track != filename or force_restart:
            self.stop_voice(fade_ms=0)
        if not self.is_voice_playing():
            self._duck_factor = 1.0
            self._duck_target = 1.0
        applied_volume = self._effective_bgm_volume()
        if self.current_track == filename and not force_restart:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(applied_volume)
            return

        self.current_track = filename
        track_path = os.path.join(self.base_assets_dir, filename)
        if os.path.exists(track_path):
            try:
                pygame.mixer.music.load(track_path)
                pygame.mixer.music.set_volume(applied_volume)
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
            wave_hover = np.clip(np.sin(2 * np.pi * freq_hover * t_hover) * env_hover * 0.78, -1.0, 1.0)
            arr_hover = (wave_hover * 32767).astype(np.int16)
            self._hover_sound = pygame.sndarray.make_sound(np.column_stack((arr_hover, arr_hover)))

            # 2. Click Sound: pop elástico de 0.08s
            duration_click = 0.08
            t_click = np.linspace(0, duration_click, int(sr * duration_click), False)
            freq_click = np.geomspace(440, 160, len(t_click))
            env_click = np.exp(-t_click * 35.0)
            wave_click = np.clip(np.sin(2 * np.pi * freq_click * t_click) * env_click * 0.85, -1.0, 1.0)
            arr_click = (wave_click * 32767).astype(np.int16)
            self._click_sound = pygame.sndarray.make_sound(np.column_stack((arr_click, arr_click)))

            # 3. Iguana Chirp
            duration_ig = 0.09
            t_ig = np.linspace(0, duration_ig, int(sr * duration_ig), False)
            freq_ig = 380 + 120 * np.sin(2 * np.pi * 22 * t_ig)
            env_ig = np.sin(np.pi * t_ig / duration_ig)
            wave_ig = np.clip(np.sin(2 * np.pi * freq_ig * t_ig) * env_ig * 0.82, -1.0, 1.0)
            arr_ig = (wave_ig * 32767).astype(np.int16)
            self._iguana_sound = pygame.sndarray.make_sound(np.column_stack((arr_ig, arr_ig)))

            # 4. Pigeon Coo (Arrullo cómico de paloma currambera)
            duration_pg = 0.14
            t_pg = np.linspace(0, duration_pg, int(sr * duration_pg), False)
            freq_pg = 260 + 40 * np.sin(2 * np.pi * 14 * t_pg)
            env_pg = np.sin(np.pi * t_pg / duration_pg) ** 2
            wave_pg = np.clip(np.sin(2 * np.pi * freq_pg * t_pg) * env_pg * 0.84, -1.0, 1.0)
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
            wave_win = np.clip(
                (np.sin(2 * np.pi * freq_win * t_win) + 0.3 * np.sin(4 * np.pi * freq_win * t_win)) * env_win * 0.68,
                -1.0,
                1.0,
            )
            arr_win = (wave_win * 32767).astype(np.int16)
            self._win_sound = pygame.sndarray.make_sound(np.column_stack((arr_win, arr_win)))

            # 6. Lose Sound (Buzzer descendente cómico 420Hz -> 160Hz)
            duration_lose = 0.32
            t_lose = np.linspace(0, duration_lose, int(sr * duration_lose), False)
            freq_lose = np.geomspace(420, 160, len(t_lose))
            env_lose = np.exp(-t_lose * 6.5)
            wave_lose = np.clip(np.sign(np.sin(2 * np.pi * freq_lose * t_lose)) * env_lose * 0.78, -1.0, 1.0)
            arr_lose = (wave_lose * 32767).astype(np.int16)
            self._lose_sound = pygame.sndarray.make_sound(np.column_stack((arr_lose, arr_lose)))

            # 7. Tambor Alegre (Golpe seco resonante de percusión cumbiera)
            duration_drum = 0.16
            t_drum = np.linspace(0, duration_drum, int(sr * duration_drum), False)
            freq_drum = np.geomspace(220, 60, len(t_drum))
            env_drum = np.exp(-t_drum * 26.0)
            wave_drum = np.sin(2 * np.pi * freq_drum * t_drum) * env_drum * 0.78
            slap_noise = np.random.uniform(-0.32, 0.32, len(t_drum)) * np.exp(-t_drum * 120.0)
            wave_drum += slap_noise
            arr_drum = (np.clip(wave_drum, -1.0, 1.0) * 32767).astype(np.int16)
            self._drum_sound = pygame.sndarray.make_sound(np.column_stack((arr_drum, arr_drum)))

            # 8. Silbato de Carnaval (Pito de Guacherna caribeño)
            duration_whistle = 0.12
            t_wh = np.linspace(0, duration_whistle, int(sr * duration_whistle), False)
            freq_wh = 1950.0 + 350.0 * np.sin(2 * np.pi * 35.0 * t_wh)
            env_wh = np.sin(np.pi * t_wh / duration_whistle) ** 0.6
            wave_wh = np.clip(np.sin(2 * np.pi * freq_wh * t_wh) * env_wh * 0.82, -1.0, 1.0)
            arr_wh = (wave_wh * 32767).astype(np.int16)
            self._whistle_sound = pygame.sndarray.make_sound(np.column_stack((arr_wh, arr_wh)))

            # 9. Jump Sound (Impulso ascendente elástico)
            duration_jump = 0.10
            t_jump = np.linspace(0, duration_jump, int(sr * duration_jump), False)
            freq_jump = np.geomspace(260, 740, len(t_jump))
            env_jump = np.sin(np.pi * t_jump / duration_jump) ** 0.7
            wave_jump = np.clip(np.sin(2 * np.pi * freq_jump * t_jump) * env_jump * 0.82, -1.0, 1.0)
            arr_jump = (wave_jump * 32767).astype(np.int16)
            self._jump_sound = pygame.sndarray.make_sound(np.column_stack((arr_jump, arr_jump)))

            # 10. Hit Sound (Impacto seco de acierto / baneo / shh)
            duration_hit = 0.11
            t_hit = np.linspace(0, duration_hit, int(sr * duration_hit), False)
            hit_noise = np.random.uniform(-1.0, 1.0, len(t_hit)) * np.exp(-t_hit * 48.0)
            hit_tone = np.sin(2 * np.pi * np.geomspace(300, 110, len(t_hit)) * t_hit) * np.exp(-t_hit * 24.0)
            wave_hit = np.clip((hit_noise * 0.45 + hit_tone * 0.75) * 0.85, -1.0, 1.0)
            arr_hit = (wave_hit * 32767).astype(np.int16)
            self._hit_sound = pygame.sndarray.make_sound(np.column_stack((arr_hit, arr_hit)))

            # 11. Miss Sound (Error / golpe en vacío / advertencia)
            duration_miss = 0.16
            t_miss = np.linspace(0, duration_miss, int(sr * duration_miss), False)
            freq_miss = np.geomspace(280, 120, len(t_miss))
            env_miss = np.exp(-t_miss * 12.0)
            wave_miss = np.clip(
                (0.65 * np.sin(2 * np.pi * freq_miss * t_miss) + 0.35 * np.sign(np.sin(2 * np.pi * freq_miss * t_miss)))
                * env_miss
                * 0.80,
                -1.0,
                1.0,
            )
            arr_miss = (wave_miss * 32767).astype(np.int16)
            self._miss_sound = pygame.sndarray.make_sound(np.column_stack((arr_miss, arr_miss)))
        except Exception:
            pass

    def toggle_music(self) -> bool:
        self.music_enabled = not self.music_enabled
        self.settings.set("music_enabled", self.music_enabled)
        if not self.music_enabled:
            if pygame.mixer.get_init():
                pygame.mixer.music.pause()
        else:
            if pygame.mixer.get_init():
                if not self.is_voice_playing():
                    self._duck_factor = 1.0
                    self._duck_target = 1.0
                pygame.mixer.music.set_volume(self._effective_bgm_volume())
                pygame.mixer.music.unpause()
                if not pygame.mixer.music.get_busy() and self.current_track:
                    self.play_bgm(self.current_track, force_restart=True, volume_scale=self._bgm_volume_scale)
        return self.music_enabled

    def toggle_sound(self) -> bool:
        self.sound_enabled = not self.sound_enabled
        self.settings.set("sound_enabled", self.sound_enabled)
        if self.sound_enabled:
            self.play_click()
        else:
            self.stop_voice(fade_ms=0)
            self.sonarEscritura(False)
        return self.sound_enabled

    def set_sfx_volume(self, volume: float) -> float:
        self.sfx_volume = round(max(0.0, min(1.0, float(volume))), 2)
        self.settings.set("sfx_volume", self.sfx_volume)
        voice_snd = getattr(self, "_voice_sound", None)
        if voice_snd is not None and self.is_voice_playing():
            try:
                v_scale = getattr(self, "_voice_volume_scale", 1.0)
                voice_snd.set_volume(max(0.0, min(1.0, self.sfx_volume * v_scale)) if self.sound_enabled else 0.0)
            except Exception:
                pass
        canal_esc = getattr(self, "canalEscritura", None)
        sonido_esc = getattr(self, "sonidoEscritura", None)
        if canal_esc is not None and sonido_esc is not None:
            try:
                if canal_esc.get_busy():
                    escritura_scale = 0.35 if self.is_voice_playing() else 0.7
                    sonido_esc.set_volume(
                        max(0.0, min(1.0, self.sfx_volume * escritura_scale)) if self.sound_enabled else 0.0
                    )
            except Exception:
                pass
        return self.sfx_volume

    def set_music_volume(self, volume: float) -> float:
        self.music_volume = round(max(0.0, min(1.0, float(volume))), 2)
        self.settings.set("music_volume", self.music_volume)
        if pygame.mixer.get_init():
            if not self.is_voice_playing():
                self._duck_factor = 1.0
                self._duck_target = 1.0
            pygame.mixer.music.set_volume(self._effective_bgm_volume())
        return self.music_volume

    def play_sfx(
        self,
        sound: Optional[pygame.mixer.Sound],
        volume_scale: float = 1.0,
    ) -> Optional[pygame.mixer.Channel]:
        if not self.sound_enabled or sound is None:
            return None
        volume = max(0.0, min(1.0, self.sfx_volume * volume_scale))
        sound.set_volume(volume)
        return sound.play()

    def sonarEscritura(self, escribiendo: bool) -> None:
        canal = getattr(self, "canalEscritura", None)
        if not escribiendo:
            if canal is not None:
                canal.fadeout(180)
                self.canalEscritura = None
            return
        if canal is not None and canal.get_busy():
            return
        if getattr(self, "sonidoEscritura", None) is None:
            ruta = os.path.join(self.base_assets_dir, "escribir.mp3")
            try:
                self.sonidoEscritura = pygame.mixer.Sound(ruta) if pygame.mixer.get_init() and os.path.exists(ruta) else False
            except pygame.error:
                self.sonidoEscritura = False
        if not self.sonidoEscritura or not self.sound_enabled:
            return
        escritura_scale = 0.35 if self.is_voice_playing() else 0.7
        self.sonidoEscritura.set_volume(max(0.0, min(1.0, self.sfx_volume * escritura_scale)))
        self.canalEscritura = self.sonidoEscritura.play(loops=-1)

    def play_hover(self) -> None:
        self.play_sfx(self._hover_sound, 0.55)

    def play_click(self) -> None:
        self.play_sfx(self._click_sound, 1.0)

    def play_iguana(self) -> None:
        self.play_sfx(self._iguana_sound, 0.95)

    def play_pigeon(self) -> None:
        self.play_sfx(self._pigeon_sound, 0.95)

    def play_win(self) -> None:
        self.play_sfx(self._win_sound, 1.0)

    def play_lose(self) -> None:
        self.play_sfx(self._lose_sound, 1.0)

    def play_drum(self) -> None:
        self.play_sfx(self._drum_sound, 1.0)

    def play_whistle(self) -> None:
        self.play_sfx(self._whistle_sound, 0.95)

    def play_jump(self) -> None:
        self.play_sfx(self._jump_sound, 0.95)

    def play_hit(self) -> None:
        self.play_sfx(self._hit_sound, 1.0)

    def play_miss(self) -> None:
        self.play_sfx(self._miss_sound, 0.95)

    def resolve_voice_path(self, clip_name: str) -> Optional[str]:
        """Retorna la ruta del primer archivo de voz existente en assets/voces/ o assets/."""
        for path in (
            os.path.join(self.base_assets_dir, "voces", clip_name),
            os.path.join(self.base_assets_dir, clip_name),
        ):
            if os.path.exists(path):
                return path
        return None

    def _load_voice_sound(self, clip_name: str) -> Optional[pygame.mixer.Sound]:
        """Carga con caché el Sound de una voz según la configuración actual del mixer."""
        if not pygame.mixer.get_init():
            return None
        path = self.resolve_voice_path(clip_name)
        if path is None:
            return None
        key = (path, pygame.mixer.get_init())
        cached = self._voice_cache.get(key)
        if cached is not None:
            return cached
        try:
            snd = pygame.mixer.Sound(path)
            self._voice_cache[key] = snd
            return snd
        except Exception:
            return None

    def get_voice_duration(self, clip_name: str) -> float:
        """Retorna la duración en segundos de una voz localizada (0.0 si no existe)."""
        snd = self._load_voice_sound(clip_name)
        if snd is None:
            return 0.0
        try:
            return max(0.0, float(snd.get_length()))
        except Exception:
            return 0.0

    def is_voice_playing(self) -> bool:
        """Indica si hay una línea de voz activamente en reproducción."""
        if not self.sound_enabled or not pygame.mixer.get_init():
            return False
        ch = getattr(self, "_voice_channel", None)
        now = time.monotonic()
        if ch is not None:
            try:
                busy = bool(ch.get_busy())
            except Exception:
                busy = False
            if not busy:
                self._voice_end_time = 0.0
                return False
            if self._voice_end_time > 0.0 and now >= self._voice_end_time:
                self._voice_end_time = 0.0
                return False
            return True
        return self._voice_end_time > now

    def stop_voice(self, fade_ms: int = 80) -> None:
        """Detiene limpiamente la voz actual (con fade opcional) evitando cortes secos o solapamientos."""
        ch = getattr(self, "_voice_channel", None)
        if ch is not None:
            try:
                if fade_ms > 0 and ch.get_busy():
                    ch.fadeout(int(fade_ms))
                else:
                    ch.stop()
            except Exception:
                pass
        self._voice_channel = None
        self._voice_sound = None
        self._voice_end_time = 0.0
        self._duck_target = 1.0
        if fade_ms <= 0 and self._duck_factor < 1.0:
            self._duck_factor = 1.0
            self.sync_music_volume()

    def update(self, dt: float) -> None:
        """Actualiza el ducking dinámico de música según la reproducción de voz."""
        active = self.is_voice_playing()
        target = self.duck_level if active else 1.0
        self._duck_target = target
        if abs(self._duck_factor - target) > 0.002:
            rate = 14.0 if target < self._duck_factor else 2.8
            step = min(1.0, max(0.0, float(dt)) * rate)
            new_factor = self._duck_factor + (target - self._duck_factor) * step
            if abs(new_factor - target) <= 0.004:
                new_factor = target
            self._duck_factor = new_factor
            self.sync_music_volume()
        elif self._duck_factor != target:
            self._duck_factor = target
            self.sync_music_volume()

        canal_esc = getattr(self, "canalEscritura", None)
        sonido_esc = getattr(self, "sonidoEscritura", None)
        if canal_esc is not None and sonido_esc:
            try:
                if canal_esc.get_busy():
                    escritura_scale = 0.35 if active else 0.7
                    target_esc_vol = (
                        max(0.0, min(1.0, self.sfx_volume * escritura_scale))
                        if self.sound_enabled else 0.0
                    )
                    if abs(float(sonido_esc.get_volume()) - target_esc_vol) > 0.01:
                        sonido_esc.set_volume(target_esc_vol)
            except Exception:
                pass

    def play_voice(
        self,
        clip_name: str,
        volume_scale: float = 1.0,
        fallback_sound: Optional[pygame.mixer.Sound] = None,
    ) -> Optional[pygame.mixer.Channel]:
        """
        Reproduce una línea de voz localizada (ej. 'coronaste.ogg', 'ombe_casi.ogg')
        buscando en 'assets/voces/' y luego en 'assets/', con caché y canal dedicado
        para evitar solapamiento y activar ducking suave sobre la música de fondo.
        """
        if not self.sound_enabled:
            return None

        loaded_sound = self._load_voice_sound(clip_name)
        target_sound = loaded_sound if loaded_sound is not None else fallback_sound
        if target_sound is None:
            return None

        # Detener cualquier voz previa antes de reproducir la nueva
        self.stop_voice(fade_ms=0)

        volume = max(0.0, min(1.0, self.sfx_volume * volume_scale))
        try:
            target_sound.set_volume(volume)
        except Exception:
            pass

        ch = self._ensure_voice_channel()
        if ch is not None:
            try:
                ch.play(target_sound)
            except Exception:
                ch = self.play_sfx(target_sound, volume_scale)
        else:
            ch = self.play_sfx(target_sound, volume_scale)

        if ch is not None or loaded_sound is not None:
            try:
                dur = float(target_sound.get_length())
            except Exception:
                dur = 2.0
            self._voice_channel = ch
            self._voice_sound = target_sound
            self._voice_volume_scale = volume_scale
            self._voice_end_time = time.monotonic() + max(0.1, dur + 0.05)
            self._duck_target = self.duck_level
        return ch

    def get_pitched_sound(self, sound: pygame.mixer.Sound, pitch_factor: float) -> pygame.mixer.Sound:
        """
        Modula dinámicamente el tono (pitch) de un Sound mediante remuestreo de numpy.
        Útil para generar variaciones de voz por personaje cuando no existen audios grabados propios.
        """
        if abs(pitch_factor - 1.0) < 0.02 or not pygame.mixer.get_init():
            return sound
        try:
            arr = pygame.sndarray.array(sound)
            n_samples = len(arr)
            indices = np.round(np.arange(0, n_samples, pitch_factor)).astype(int)
            indices = indices[indices < n_samples]
            pitched_arr = arr[indices]
            return pygame.sndarray.make_sound(pitched_arr)
        except Exception:
            return sound

