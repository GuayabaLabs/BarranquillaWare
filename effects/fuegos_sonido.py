"""Sonido de los fuegos artificiales, sincronizado con cada estallido.

- Los archivos `assets/fuego1.mp3`…`fuego3.mp3` traen varias explosiones seguidas (~6 s). Al cargar se
  separan en estallidos sueltos: se detecta el golpe de cada explosión y se corta ~0,9 s desde ahí,
  con desvanecido. Así cada fuego que se ve suena con UN estallido, justo al reventar (sin "fiuum").
- Suena cuando el fuego pasa de subir a estallar (`avisar_estallido`), nunca al lanzar el cohete.
- No tapa lo demás: volumen bajo, canales reservados (no le quita canal a una voz) y, si hay otro
  audio sonando (p. ej. las voces de SEOR "¡Coronaste!"), baja todavía más.
"""
import os
import random
from typing import Dict, List, Optional

import numpy as np
import pygame

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVOS = ("fuego1.mp3", "fuego2.mp3", "fuego3.mp3")
SUBIDA_FUEGO = 0.45          # Igual que subidaFuego en effects/juice_particles.py
DURACION_ESTALLIDO = 0.9     # Segundos de cada estallido recortado
VOLUMEN = 0.32               # Relativo al volumen de efectos de Opciones
VOLUMEN_CON_VOZ = 0.12       # Si hay otro audio sonando (voz, efecto), los fuegos bajan aún más
CANALES_RESERVADOS = 2


def separar_estallidos(sonido: pygame.mixer.Sound, frec: int) -> List[pygame.mixer.Sound]:
    """Divide una grabación con varias explosiones en estallidos sueltos que empiezan en el golpe."""
    datos = pygame.sndarray.array(sonido)
    mono = np.abs(datos.astype(np.int32)).reshape(len(datos), -1).max(axis=1)
    ventana = max(1, frec // 100)                      # envolvente cada 10 ms
    env = np.array([mono[i:i + ventana].max() for i in range(0, len(mono), ventana)])
    if env.max() <= 0:
        return []
    env = env / env.max()
    largo = int(DURACION_ESTALLIDO * frec)
    rampa = int(0.2 * frec)
    piezas, k = [], 0
    while k < len(env):
        # Golpe: salto fuerte respecto a los 150 ms anteriores (el inicio de una explosión).
        previo = env[max(0, k - 15):k].max() if k > 0 else 0.0
        if env[k] >= 0.45 and env[k] >= previo * 1.8 + 0.12:
            inicio = max(0, k * ventana - frec // 200)       # 5 ms antes del golpe
            trozo = datos[inicio:inicio + largo].copy()
            if len(trozo) >= frec // 3:
                n = min(rampa, len(trozo))
                curva = np.linspace(1.0, 0.0, n)
                trozo[-n:] = (trozo[-n:] * (curva[:, None] if trozo.ndim > 1 else curva)).astype(trozo.dtype)
                piezas.append(pygame.sndarray.make_sound(np.ascontiguousarray(trozo)))
            k += int(DURACION_ESTALLIDO * 100 * 0.7)        # siguiente golpe, sin pisar este
        else:
            k += 1
    return piezas


class SonidoFuegos:
    _instancia: Optional["SonidoFuegos"] = None

    def __init__(self) -> None:
        self.estallidos: List[pygame.mixer.Sound] = []
        self.ultimo_t: Dict[object, float] = {}
        self.canales: List[pygame.mixer.Channel] = []
        if not pygame.mixer.get_init():
            return
        try:
            pygame.mixer.set_reserved(CANALES_RESERVADOS)
            self.canales = [pygame.mixer.Channel(i) for i in range(CANALES_RESERVADOS)]
        except pygame.error:
            self.canales = []
        frec = pygame.mixer.get_init()[0]
        for nombre in ARCHIVOS:
            ruta = os.path.join(RAIZ, "assets", nombre)
            if os.path.exists(ruta):
                try:
                    self.estallidos += separar_estallidos(pygame.mixer.Sound(ruta), frec)
                except (pygame.error, ValueError):
                    pass

    @classmethod
    def get(cls) -> "SonidoFuegos":
        if cls._instancia is None:
            cls._instancia = cls()
        return cls._instancia

    def _otro_audio_sonando(self) -> bool:
        reservados = set(self.canales)
        try:
            total = pygame.mixer.get_num_channels()
        except pygame.error:
            return False
        for i in range(total):
            canal = pygame.mixer.Channel(i)
            if canal not in reservados and canal.get_busy():
                return True
        return False

    def estallar(self) -> None:
        if not self.estallidos or not pygame.mixer.get_init():
            return
        try:
            from core.audio_manager import AudioManager
            audio = AudioManager.get_instance()
            if not audio.sound_enabled:
                return
            base = audio.sfx_volume
        except Exception:
            base = 0.8
        volumen = base * (VOLUMEN_CON_VOZ if self._otro_audio_sonando() else VOLUMEN)
        sonido = random.choice(self.estallidos)
        canal = next((c for c in self.canales if not c.get_busy()), None)
        if canal is None:
            return  # Ya suenan dos estallidos: no se amontonan
        canal.set_volume(volumen)
        canal.play(sonido)

    def avisar_estallido(self, clave, t: float, subida: float = SUBIDA_FUEGO) -> None:
        """Llamar cada frame con el tiempo del fuego (desde que sale el cohete). Suena al cruzar la subida."""
        previo = self.ultimo_t.get(clave)
        self.ultimo_t[clave] = t
        if previo is None:
            return
        # Cruzó el momento del estallido (también al dar la vuelta del ciclo)
        if (previo < subida <= t) or (t < previo and t >= subida):
            self.estallar()


def avisar_estallido(clave, t: float, subida: float = SUBIDA_FUEGO) -> None:
    SonidoFuegos.get().avisar_estallido(clave, t, subida)
