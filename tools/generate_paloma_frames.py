import os
import numpy as np
from PIL import Image, ImageDraw

def create_paloma_frames():
    base_path = "assets/paloma_dialog.png"
    if not os.path.exists(base_path):
        raise FileNotFoundError(f"No se encontró el asset base: {base_path}")

    base = Image.open(base_path).convert("RGBA")
    arr_base = np.array(base)
    h_img, w_img, _ = arr_base.shape
    print(f"Generando frames de animación para Paloma ({w_img}x{h_img})...")

    def get_seam_y(x):
        # Parabola de la comisura del pico: (830, 470) vértice
        return 470.0 + ((x - 830.0) / 100.0) ** 2 * 28.0

    def make_mouth_frame(max_gap=0):
        if max_gap == 0:
            return base.copy()

        out = arr_base.copy()

        for x in range(742, 960):
            seam = get_seam_y(x)
            rel = (x - 742.0) / (955.0 - 742.0)
            if 0 <= rel <= 1:
                gap = max_gap * np.sin(rel * np.pi)
            else:
                gap = 0

            shift = int(round(gap))
            if shift <= 0:
                continue

            # 1. Cavidad bucal profunda
            for y in range(int(seam), int(seam + shift)):
                norm_y = (y - seam) / float(shift)
                tongue_x_rel = (rel - 0.52) / 0.22
                is_tongue = False
                if abs(tongue_x_rel) <= 1.0:
                    tongue_top = 0.35 + 0.35 * (tongue_x_rel ** 2)
                    if norm_y >= tongue_top:
                        is_tongue = True

                if is_tongue:
                    # Lengua coral cálida
                    out[y, x] = [238, 102, 82, 255]
                else:
                    # Cavidad interior ciruela/rubí profundo
                    out[y, x] = [72, 20, 48, 255]

            # 2. Desplazamiento de mandíbula inferior y borde
            for y in range(540, int(seam), -1):
                if y + shift < h_img:
                    r, g, b, a = arr_base[y, x]
                    if a > 0:
                        out[y + shift, x] = arr_base[y, x]

        return Image.fromarray(out)

    def make_blink_frame():
        # Centro exacto del iris en (595, 435), radio 60
        img = base.copy()
        draw = ImageDraw.Draw(img)
        cx, cy = 595, 435
        r_iris = 60

        # Párpado con color lavanda de la cabeza
        draw.ellipse([cx - r_iris, cy - r_iris, cx + r_iris, cy + r_iris], fill=(216, 192, 238, 255))
        # Sombra sutil de acuarela en el borde superior del párpado
        draw.arc([cx - r_iris + 2, cy - r_iris + 2, cx + r_iris - 2, cy + r_iris - 2], start=180, end=360, fill=(182, 152, 212, 255), width=5)
        # Arco de pestañas alegre (sonrisa de ojos cerrada ⌒)
        col = (65, 28, 90, 255)
        w_line = 9
        draw.arc([cx - 46, cy - 32, cx + 46, cy + 28], start=190, end=350, fill=col, width=w_line)
        draw.line([(cx - 40, cy - 8), (cx - 52, cy - 14)], fill=col, width=w_line - 3)
        return img

    f0 = make_mouth_frame(0)
    f1 = make_mouth_frame(14)
    f2 = make_mouth_frame(26)
    fb = make_blink_frame()

    f0.save("assets/paloma_dialog_habla_0.png")
    f1.save("assets/paloma_dialog_habla_1.png")
    f2.save("assets/paloma_dialog_habla_2.png")
    fb.save("assets/paloma_dialog_pestaneo.png")
    print("[OK] Frames guardados en assets/: habla_0, habla_1, habla_2, pestaneo.")

if __name__ == "__main__":
    create_paloma_frames()
