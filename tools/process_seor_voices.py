import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

VOICE_CHAIN = (
    "highpass=f=85:poles=2,"
    "afftdn=nr=10:nf=-40:tn=1,"
    "equalizer=f=240:t=q:w=1.2:g=-2.0,"
    "equalizer=f=3200:t=q:w=1.4:g=2.5,"
    "equalizer=f=7500:t=q:w=1.2:g=1.2,"
    "lowpass=f=12500,"
    "acompressor=threshold=-22dB:ratio=3.2:attack=8:release=110:makeup=4.0,"
    "alimiter=limit=0.70:attack=4:release=60,"
    "silenceremove=start_periods=1:start_duration=0.02:start_threshold=-46dB:detection=rms,"
    "areverse,silenceremove=start_periods=1:start_duration=0.03:start_threshold=-43dB:detection=rms,"
    "afade=t=in:ss=0:d=0.025,areverse,"
    "afade=t=in:ss=0:d=0.012"
)

SHORT_CLIPS: Dict[str, Tuple[Optional[float], Optional[float]]] = {
    "coronaste.ogg": (0.04, 3.38),
    "ombe_casi.ogg": (0.04, 3.25),
    "paloma_saludo.ogg": (0.04, 3.15),
    "paloma_animo.ogg": (0.04, None),
    "paloma_victoria.ogg": (0.04, 3.00),
    "paloma_derrota.ogg": (0.04, 4.15),
}

REFL_SEGMENTS: Dict[str, Tuple[float, float]] = {
    "refl_uninorte_sprint_win.ogg": (4.27, 12.52),
    "refl_uninorte_sprint_lose.ogg": (16.83, 23.79),
    "refl_uninorte_concentrate_win.ogg": (61.04, 68.68),
    "refl_uninorte_concentrate_lose.ogg": (72.80, 78.44),
    "refl_fritanga_84_win.ogg": (85.86, 92.90),
    "refl_fritanga_84_lose.ogg": (97.51, 105.16),
    "refl_fritanga_rabia.ogg": (121.23, 130.31),
    "refl_fritanga_distraido.ogg": (133.93, 141.42),
    "refl_curramgram_go_win.ogg": (196.01, 203.99),
    "refl_curramgram_go_lose.ogg": (215.37, 222.91),
    "refl_emoji_catch_win.ogg": (230.26, 236.82),
    "refl_emoji_catch_lose.ogg": (246.27, 252.85),
}

PALOMA_POI_SEGMENTS: Dict[str, Tuple[float, float]] = {
    "paloma_uninorte_0.ogg": (53.23, 67.96),
    "paloma_uninorte_1.ogg": (136.02, 147.22),
    "paloma_uninorte_win_0.ogg": (154.51, 168.82),
    "paloma_uninorte_lose_0.ogg": (175.97, 186.54),
    "paloma_buenavista_0.ogg": (194.41, 211.13),
    "paloma_buenavista_1.ogg": (232.23, 241.48),
    "paloma_buenavista_win_0.ogg": (247.66, 262.70),
    "paloma_buenavista_lose_0.ogg": (279.24, 289.02),
    "paloma_metropolitano_0.ogg": (338.99, 354.27),
    "paloma_metropolitano_1.ogg": (357.77, 368.12),
    "paloma_metropolitano_win_0.ogg": (394.58, 409.56),
    "paloma_metropolitano_lose_0.ogg": (430.80, 440.24),
    "paloma_aeropuerto_0.ogg": (447.49, 460.23),
    "paloma_aeropuerto_1.ogg": (495.47, 504.23),
    "paloma_aeropuerto_win_0.ogg": (507.12, 520.76),
    "paloma_aeropuerto_lose_0.ogg": (543.74, 554.04),
    "paloma_aleta_0.ogg": (609.61, 623.16),
    "paloma_aleta_1.ogg": (626.43, 640.87),
    "paloma_aleta_win_0.ogg": (654.84, 674.15),
    "paloma_aleta_lose_0.ogg": (675.68, 685.67),
    "paloma_malecon_0.ogg": (720.40, 729.50),
    "paloma_malecon_1.ogg": (739.55, 748.64),
    "paloma_malecon_win_0.ogg": (768.93, 778.71),
    "paloma_malecon_lose_0.ogg": (803.42, 815.28),
}


def _trim_args(start_s: Optional[float], end_s: Optional[float]) -> List[str]:
    args: List[str] = []
    if start_s is not None:
        args.extend(["-ss", f"{start_s:.3f}"])
    if end_s is not None:
        args.extend(["-to", f"{end_s:.3f}"])
    return args


def master_voice_clip(
    src_path: Path,
    dest_voces_path: Path,
    dest_assets_path: Path,
    start_s: Optional[float] = None,
    end_s: Optional[float] = None,
    target_lufs: float = -14.0,
    target_tp: float = -1.0,
    target_lra: float = 6.0,
) -> bool:
    """Ejecuta masterizacion vocal de 2 pasadas con ffmpeg loudnorm y replica en assets/."""
    trim = _trim_args(start_s, end_s)

    # Pasada 1: medicion EBU R128 exacta en mono unificado tras limpieza/EQ/compresion/recorte
    pass1_af = f"{VOICE_CHAIN},loudnorm=I={target_lufs}:TP={target_tp}:LRA={target_lra}:print_format=json"
    cmd1 = ["ffmpeg", "-hide_banner", "-y", *trim, "-i", str(src_path), "-ac", "1", "-af", pass1_af, "-f", "null", "-"]
    res1 = subprocess.run(cmd1, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res1.returncode != 0:
        print(f"[FAIL] Pass 1 {dest_voces_path.name}: {res1.stderr}")
        return False

    json_match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res1.stderr, re.DOTALL)
    if not json_match:
        print(f"[FAIL] Sin JSON loudnorm en {dest_voces_path.name}")
        return False
    stats = json.loads(json_match.group(0))

    # Pasada 2: normalizacion lineal mono + limite True Peak en -1.0 dBTP
    pass2_af = (
        f"{VOICE_CHAIN},"
        f"loudnorm=I={target_lufs}:TP={target_tp}:LRA={target_lra}:"
        f"measured_I={stats['input_i']}:"
        f"measured_TP={stats['input_tp']}:"
        f"measured_LRA={stats['input_lra']}:"
        f"measured_thresh={stats['input_thresh']}:"
        f"offset={stats['target_offset']}:"
        f"linear=true:print_format=summary"
    )
    cmd2 = [
        "ffmpeg", "-hide_banner", "-y", *trim, "-i", str(src_path),
        "-ac", "1",
        "-af", pass2_af,
        "-ar", "44100",
        "-c:a", "libvorbis", "-q:a", "6",
        str(dest_voces_path),
    ]
    res2 = subprocess.run(cmd2, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res2.returncode != 0:
        print(f"[FAIL] Pass 2 {dest_voces_path.name}: {res2.stderr}")
        return False

    shutil.copyfile(dest_voces_path, dest_assets_path)
    return True


def verify_voice_outputs(dest_voces: Path) -> None:
    """Verifica con ffmpeg ebur128 y volumedetect todas las voces .ogg en assets/voces/."""
    files = sorted(dest_voces.glob("*.ogg"))
    print(f"\n=== AUDITORIA ACUSTICA ({len(files)} voces) ===")
    for p in files:
        res = subprocess.run(
            ["ffmpeg", "-hide_banner", "-i", str(p), "-af", "ebur128=peak=true,volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stderr
        dur_m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", res)
        dur = int(dur_m[1]) * 3600 + int(dur_m[2]) * 60 + float(dur_m[3]) if dur_m else 0.0
        i_m = re.findall(r"I:\s*(-?[\d.]+)\s*LUFS", res)
        tp_m = re.findall(r"True peak:\s*\n\s*Peak:\s*(-?[\d.]+)\s*dBFS", res)
        max_m = re.findall(r"max_volume:\s*(-?[\d.]+)\s*dB", res)
        mean_m = re.findall(r"mean_volume:\s*(-?[\d.]+)\s*dB", res)
        lufs = float(i_m[-1]) if i_m else -99.0
        tp = float(tp_m[-1]) if tp_m else -99.0
        mx = float(max_m[-1]) if max_m else -99.0
        mn = float(mean_m[-1]) if mean_m else -99.0
        print(f"  {p.name:36s} dur={dur:5.2f}s | I={lufs:6.1f} LUFS | mean={mn:5.1f} dB | TP={tp:5.1f} dBTP | max={mx:5.1f} dB")


def main() -> None:
    parser = argparse.ArgumentParser(description="Masterizacion unificada de voces de SEOR a -14 LUFS.")
    parser.add_argument("--short-dir", type=Path, default=None, help="Directorio con los 6 audios cortos (.ogg)")
    parser.add_argument("--refl-wav", type=Path, default=None, help="WAV maestro con las 12 reflexiones")
    parser.add_argument("--poi-wav", type=Path, default=None, help="WAV maestro con los 24 dialogos de Paloma POI")
    parser.add_argument("--welcome-0", type=Path, default=None, help="Audio raw para paloma_welcome_0.ogg")
    parser.add_argument("--welcome-1", type=Path, default=None, help="Audio raw para paloma_welcome_1.ogg")
    parser.add_argument("--target-lufs", type=float, default=-14.0)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    dest_voces = Path("assets/voces")
    dest_assets = Path("assets")
    dest_voces.mkdir(parents=True, exist_ok=True)

    if args.verify_only:
        verify_voice_outputs(dest_voces)
        return

    processed = 0

    if args.short_dir and args.short_dir.exists():
        for name, (ss, se) in SHORT_CLIPS.items():
            src = args.short_dir / name
            if src.exists():
                ok = master_voice_clip(src, dest_voces / name, dest_assets / name, ss, se, target_lufs=args.target_lufs)
                if ok:
                    processed += 1
                    print(f"[OK] short -> {name}")
            else:
                print(f"[WARN] Falta {src}")

    if args.refl_wav and args.refl_wav.exists():
        for name, (ss, se) in REFL_SEGMENTS.items():
            ok = master_voice_clip(args.refl_wav, dest_voces / name, dest_assets / name, ss, se, target_lufs=args.target_lufs)
            if ok:
                processed += 1
                print(f"[OK] refl  -> {name}")

    if args.poi_wav and args.poi_wav.exists():
        for name, (ss, se) in PALOMA_POI_SEGMENTS.items():
            ok = master_voice_clip(args.poi_wav, dest_voces / name, dest_assets / name, ss, se, target_lufs=args.target_lufs)
            if ok:
                processed += 1
                print(f"[OK] poi   -> {name}")

    if args.welcome_0 and args.welcome_0.exists():
        if master_voice_clip(args.welcome_0, dest_voces / "paloma_welcome_0.ogg", dest_assets / "paloma_welcome_0.ogg", 0.85, 19.35, target_lufs=args.target_lufs):
            processed += 1
            print("[OK] welcome -> paloma_welcome_0.ogg")

    if args.welcome_1 and args.welcome_1.exists():
        if master_voice_clip(args.welcome_1, dest_voces / "paloma_welcome_1.ogg", dest_assets / "paloma_welcome_1.ogg", 0.90, 18.55, target_lufs=args.target_lufs):
            processed += 1
            print("[OK] welcome -> paloma_welcome_1.ogg")

    print(f"\nTotal procesados: {processed}")
    verify_voice_outputs(dest_voces)


if __name__ == "__main__":
    main()
