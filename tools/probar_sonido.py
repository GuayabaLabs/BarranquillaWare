import os
import sys
import time

os.environ.pop("SDL_AUDIODRIVER", None)
os.environ.pop("SDL_VIDEODRIVER", None)

import pygame

print("========================================================")
print("     DIAGNÓSTICO Y PRUEBA DE AUDIO - BARRANQUILLAWARE")
print("========================================================")

try:
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()
    init_info = pygame.mixer.get_init()
    print(f"[OK] Tarjeta de sonido inicializada: Frecuencia={init_info[0]}Hz, Formato={init_info[1]}, Canales={init_info[2]}")
except Exception as e:
    print(f"[ERROR] No se pudo inicializar la tarjeta de sonido: {e}")
    sys.exit(1)

track = os.path.join("assets", "7am_ancpg_ost_main_menu.ogg")
if not os.path.exists(track):
    print(f"[ERROR] No se encontro el archivo de audio: {track}")
    sys.exit(1)

print("\nReproduciendo 4 segundos de musica del Menu Principal a volumen maximo...")
print("-> Si no escuchas nada, revisa el icono del parlante en la barra de tareas de Windows")
print("   y el 'Mezclador de volumen' para asegurarte que Python no este silenciado o en 0%.")

try:
    pygame.mixer.music.load(track)
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.play()
    for s in range(4, 0, -1):
        print(f"   Sonando... ({s}s restantes)")
        time.sleep(1)
    pygame.mixer.music.stop()
    print("\n[OK] Prueba de musica completada con exito.")
except Exception as e:
    print(f"[ERROR] Error durante la reproduccion: {e}")

from core.audio_manager import AudioManager
audio = AudioManager.get_instance()
print("\nProbando efectos de sonido procedurales (Pop Click & Hover)...")
audio.sound_enabled = True
audio.set_sfx_volume(1.0)
audio.play_click()
time.sleep(0.5)
audio.play_hover()
time.sleep(0.5)
audio.play_win()
time.sleep(0.8)
print("[OK] Efectos probados.")
print("\nSi escuchaste la musica y los efectos, el audio funciona perfectamente.")
