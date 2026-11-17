import os
import subprocess
import pygame

def process_audio_files():
    downloads_dir = r"C:\Users\USUARIO\Downloads"
    dest_voces = "assets/voces"
    dest_assets = "assets"
    os.makedirs(dest_voces, exist_ok=True)

    files = [
        "coronaste.ogg",
        "ombe_casi.ogg",
        "paloma_saludo.ogg",
        "paloma_animo.ogg",
        "paloma_victoria.ogg",
        "paloma_derrota.ogg"
    ]

    print("=== PROCESAMIENTO Y LIMPIEZA ACÚSTICA DE VOCES DE SEOR ===")

    for filename in files:
        src = os.path.join(downloads_dir, filename)
        dst_v = os.path.join(dest_voces, filename)
        dst_a = os.path.join(dest_assets, filename)

        if not os.path.exists(src):
            print(f"[ERROR] No se encontró el archivo: {src}")
            continue

        # Pipeline acústico profesional con ffmpeg:
        # 1. highpass=f=80: elimina golpes de mesa, frecuencias subsónicas y retumbos.
        # 2. lowpass=f=12500: elimina siseos estáticos ultrasónicos.
        # 3. afftdn=nr=18:nf=-35:tn=1: denoiser por FFT adaptativo contra ruido de fondo y ventiladores.
        # 4. silenceremove: recorta los segundos vacíos al inicio y final para 0ms de lag de respuesta.
        # 5. loudnorm=I=-16:TP=-1.5:LRA=11: normalización estándar de volumen para videojuegos.
        # 6. libvorbis a 44100Hz: compatibilidad nativa con pygame.mixer.
        cmd = [
            "ffmpeg", "-y", "-i", src,
            "-af", "highpass=f=80,lowpass=f=12500,afftdn=nr=18:nf=-35:tn=1,silenceremove=start_periods=1:start_duration=0.03:start_threshold=-40dB:detection=peak:stop_periods=1:stop_duration=0.15:stop_threshold=-42dB,loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "44100",
            "-c:a", "libvorbis", "-q:a", "5",
            dst_v
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[FAIL] Falló ffmpeg para {filename}: {res.stderr}")
        else:
            # Copiar también en assets/ para compatibilidad directa
            import shutil
            shutil.copyfile(dst_v, dst_a)
            print(f"[OK] Procesado y limpiado: {filename} -> {dst_v} & {dst_a}")

    # Verificar con pygame
    pygame.mixer.init()
    print("\n--- Verificación de reproducción en Pygame ---")
    for filename in files:
        target = os.path.join(dest_voces, filename)
        if os.path.exists(target):
            snd = pygame.mixer.Sound(target)
            print(f"✓ {filename}: Duración limpia = {snd.get_length():.2f}s (Carga exitosa)")

if __name__ == "__main__":
    process_audio_files()
