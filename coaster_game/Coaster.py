import argparse
import bisect
import math
import os
import random
import sys
import threading
import time

import pygame

# Compatibilidad con Pygame moderno: algunas versiones antiguas de la rama
# original usaban draw.aacircle, que no forma parte de la API actual.
if not hasattr(pygame.draw, "aacircle"):
    pygame.draw.aacircle = pygame.draw.circle

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

ancho, alto = 1100, 700
margenSup, margenInf = 58, 600
ySuelo = 548
fps = 60
carpeta = os.path.dirname(os.path.abspath(__file__))

# física (píxeles y segundos)
gravedad = 700.0
fAire = 0.10
fRodadura = 22.0
vInicial = 110.0
vMax = 950.0
aMax = 9.5 * gravedad
paso = 6.0
separacion = 74
rMoneda = 38
rMeta = 90
rAncla = 46
tTrazo = 0.30
tBoton = 0.90
tAuto = 0.6
rLlegada = 56

cOscuro = (72, 52, 46)
cCrema = (250, 240, 216)
cCieloAlto = (120, 186, 220)
cCieloBajo = (250, 226, 184)
cRiel = (232, 74, 56)
cMadera = (178, 130, 88)
cMaderaOsc = (126, 90, 62)
cOro = (234, 186, 78)
cOroOsc = (190, 138, 48)
cTurquesa = (92, 164, 156)
cVerde = (128, 176, 120)
cAmarillo = (238, 194, 100)
cCoral = (224, 128, 108)
cMorado = (152, 130, 190)
cVerdeVivo = (86, 182, 104)    
cAzul = (146, 182, 214)        
cAzulOsc = (92, 132, 176)
cCoralVivo = (240, 96, 70)     

# tono de la hora: se multiplica sobre la vía, los carros, la bandera y la estación
tonos = {"tarde": (226, 198, 216), "noche": (186, 196, 236)}

# botones de información sobre el cielo
cajaNivel = pygame.Rect(16, 10, 150, 42)
cajaMonedas = pygame.Rect(182, 10, 220, 42)
cajaTinta = pygame.Rect(ancho - 16 - 270, 10, 270, 42)

niveles = [
    dict(salida=(120, 210), meta=(980, 330), necesarias=2, tinta=1500, rueda=(557, 318),
         monedas=[(400, 400), (620, 430), (820, 390)],
         fantasma=[(220, 260), (320, 330), (420, 300), (470, 230), (420, 170), (340, 190), (330, 260),
                   (420, 320), (540, 300), (600, 220), (560, 150), (480, 150), (470, 220), (560, 260)]),
    dict(salida=(110, 170), meta=(990, 300), necesarias=3, tinta=1500, rueda=(557, 318),
         monedas=[(330, 430), (560, 500), (790, 390), (900, 340)],
         fantasma=[(220, 230), (300, 330), (240, 420), (160, 380), (200, 300), (320, 280), (430, 340),
                   (470, 450), (380, 500), (330, 430), (420, 380), (560, 360), (640, 280), (600, 190),
                   (520, 200), (540, 280)]),
    dict(salida=(110, 160), meta=(1000, 420), necesarias=3, tinta=1900, hora="tarde", rueda=(557, 318),
         monedas=[(570, 312), (660, 400), (570, 488), (480, 400)],
         fantasma=[(230, 200), (330, 280), (420, 380), (560, 470), (700, 400), (690, 280), (570, 230),
                   (460, 300), (500, 400), (600, 420), (640, 340), (580, 300), (540, 360)]),
    dict(salida=(110, 150), meta=(1000, 250), necesarias=3, tinta=1700, hora="noche", rueda=(557, 318),
         monedas=[(380, 430), (570, 262), (780, 435), (900, 300)],
         fantasma=[(220, 220), (330, 340), (260, 450), (350, 520), (470, 440), (420, 330), (520, 250),
                   (640, 330), (600, 450), (700, 520), (800, 440), (740, 330), (820, 230), (880, 320),
                   (830, 420), (760, 380)]),
    dict(salida=(110, 190), meta=(1010, 470), necesarias=5, tinta=1900,
         monedas=[(300, 410), (450, 500), (620, 400), (770, 390), (900, 480), (990, 450)],
         fantasma=[(240, 250), (340, 350), (300, 460), (420, 520), (520, 430), (470, 330), (580, 260),
                   (700, 320), (680, 440), (580, 470), (560, 380), (650, 340), (740, 400), (720, 480)]),
]

mensajeAlgoritmo = ("Tu camino no se mide en likes.", "Ve por tus monedas, no por los corazones.",
                    "En redes, el algoritmo escoge la vía por ti.", "Aquí la vía la dibujas tú.")
reflexionesFantasma = [
    ("Cada corazón se sintió como un premio.", "Pero nadie te preguntó pa' dónde ibas tú."),
    ("Esa vía no se hizo pa' que llegaras.", "Se hizo pa' que no te bajaras del carro."),
    ("Se fue la tarde dando vueltas detrás de likes.", "Y tu meta ahí, quietecita, esperándote."),
    ("De noche el scroll no tiene fondo, ¿oíste?", "El algoritmo no duerme, pero tú sí deberías."),
    ("El mundo entero cabe en tu pantalla.", "Pero si otro traza tu ruta, no vas a conocerlo."),
]
reflexionesPropias = [
    "Tú pusiste el rumbo. Las redes sirven cuando tú las usas, no cuando te usan a ti.",
    "No todo lo que brilla en el feed lleva a algún lado. Escoger también es dejar pasar.",
    "Cayó la tarde y no te dejaste llevar. Eso es tener la cabeza en su sitio, mi llave.",
    "El scroll de la noche no tiene fondo, pero tú supiste cuándo bajarte del carro.",
    "Llegaste a la Ventana al Mundo por tu propia vía, y desde aquí lo ves todo.",
]
reflexionFinal = (
    "Las redes no son el problema.",
    "El problema es cuando dejas que el algoritmo te trace la vía.",
    "Él no quiere que llegues: quiere que te quedes, dando vueltas detrás de corazones.",
    "Y la próxima vez que abras el celular, pregúntate: ¿esta vía la dibujé yo?",
)
duracionIntro = 10.0
duracionDesvanecer = 1.0
cFantasma = (126, 96, 176)


def interpolar(a, b, t):
    return a + (b - a) * t


def limitar(x, a, b):
    return max(a, min(b, x))


def mezclar(c1, c2, t):
    return tuple(int(interpolar(a, b, t)) for a, b in zip(c1, c2))


def partirTexto(texto, fuente, anchoMax):
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = (actual + " " + palabra).strip()
        if fuente.size(prueba)[0] <= anchoMax:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


# vía y física

def remuestrear(pts, salto=paso):
    if len(pts) < 2:
        return list(pts)
    sal = [pts[0]]
    px, py = pts[0]
    falta = salto
    for x, y in pts[1:]:
        d = math.hypot(x - px, y - py)
        while d >= falta and d > 1e-9:
            t = falta / d
            px, py = px + (x - px) * t, py + (y - py) * t
            sal.append((px, py))
            d = math.hypot(x - px, y - py)
            falta = salto
        falta -= d
        px, py = x, y
    if math.dist(sal[-1], pts[-1]) > 1:
        sal.append(pts[-1])
    return sal


def suavizar(pts, pasadas=3):
    # promedio de 5 puntos, los extremos (salida y meta) no se mueven
    for _ in range(pasadas):
        if len(pts) < 5:
            break
        nuevo = [pts[0]]
        for i in range(1, len(pts) - 1):
            a, b = max(0, i - 2), min(len(pts), i + 3)
            n = b - a
            nuevo.append((sum(p[0] for p in pts[a:b]) / n, sum(p[1] for p in pts[a:b]) / n))
        nuevo.append(pts[-1])
        pts = nuevo
    return pts


def armarCamino(crudo):
    if len(crudo) < 2:
        return list(crudo)
    return suavizar(remuestrear(crudo))


class Via:
    def __init__(self, pts):
        self.pts = pts
        n = len(pts)
        self.acum = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.acum.append(self.acum[-1] + math.dist(a, b))
        self.largo = self.acum[-1]
        self.tang = []
        for i in range(n):
            a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
            d = math.dist(a, b) or 1.0
            self.tang.append(((b[0] - a[0]) / d, (b[1] - a[1]) / d))
        # curvatura = ángulo que gira / longitud de arco
        self.curv = [0.0] * n
        w = 4
        for i in range(w, n - w):
            a, b, c = pts[i - w], pts[i], pts[i + w]
            v1 = (b[0] - a[0], b[1] - a[1])
            v2 = (c[0] - b[0], c[1] - b[1])
            ang = abs(math.atan2(v1[0] * v2[1] - v1[1] * v2[0], v1[0] * v2[0] + v1[1] * v2[1]))
            arco = (self.acum[i + w] - self.acum[i - w]) / 2
            self.curv[i] = ang / max(arco, 1e-6)

    def puntoEn(self, s):
        s = limitar(s, 0.0, self.largo)
        i = min(bisect.bisect_right(self.acum, s) - 1, len(self.pts) - 2)
        tramo = (self.acum[i + 1] - self.acum[i]) or 1.0
        f = (s - self.acum[i]) / tramo
        (x0, y0), (x1, y1) = self.pts[i], self.pts[i + 1]
        tx = interpolar(self.tang[i][0], self.tang[i + 1][0], f)
        ty = interpolar(self.tang[i][1], self.tang[i + 1][1], f)
        m = math.hypot(tx, ty) or 1.0
        k = interpolar(self.curv[i], self.curv[i + 1], f)
        return (interpolar(x0, x1, f), interpolar(y0, y1, f)), (tx / m, ty / m), k


class Recorrido:
    # tenemos dos carros enganchados que ruedan por la vía. s es la posición del de atrás
    def __init__(self, via, nivel):
        self.via = via
        self.nivel = nivel
        self.s = 0.0
        self.v = vInicial
        self.tomadas = set()
        self.nuevas = []
        self.estado = "corriendo"   # corriendo, listo, descarrilo, devuelto, atascado, corta
        self.quieto = 0.0
        self.tiempo = 0.0
        self.fuerzaG = 0.0
        self.masLejos = 0.0
        self.sinAvanzar = 0.0
        self.ubicar()

    def ubicar(self):
        self.posAtras, self.tangAtras, _ = self.via.puntoEn(self.s)
        self.posFrente, self.tangFrente, _ = self.via.puntoEn(self.s + separacion)

    def avanzar(self, delta):
        if self.estado != "corriendo":
            return
        self.nuevas = []
        self.tiempo += delta
        divs = 4
        h = delta / divs
        for _ in range(divs):
            _, tgA, kA = self.via.puntoEn(self.s)
            _, tgF, kF = self.via.puntoEn(self.s + separacion)
            a = gravedad * (tgA[1] + tgF[1]) / 2 - fAire * self.v
            if abs(self.v) > 2:
                a -= fRodadura * (1 if self.v > 0 else -1)
            self.v = limitar(self.v + a * h, -vMax, vMax)
            self.s += self.v * h
            k = max(kA, kF)
            self.fuerzaG = self.v * self.v * k / gravedad
            if self.v * self.v * k > aMax:
                self.estado = "descarrilo"
                self.ubicar()
                return
            if self.s <= 0:
                self.s = 0
                self.estado = "devuelto"
                self.ubicar()
                return
            if self.s + separacion >= self.via.largo:
                self.s = self.via.largo - separacion
                self.ubicar()
                llego = math.dist(self.posFrente, self.nivel["meta"]) < 20
                self.estado = "listo" if llego else "corta"
                break
            self.quieto = self.quieto + h if abs(self.v) < 8 else 0.0
            if self.s > self.masLejos + 2.0:
                self.masLejos = self.s
                self.sinAvanzar = 0.0
            else:
                self.sinAvanzar += h
            if self.quieto > 0.5 or self.sinAvanzar > 2.0:
                self.estado = "atascado"
                self.ubicar()
                return
        self.ubicar()
        for i, m in enumerate(self.nivel["monedas"]):
            if i in self.tomadas:
                continue
            if math.dist(self.posAtras, m) < rMoneda or math.dist(self.posFrente, m) < rMoneda:
                self.tomadas.add(i)
                self.nuevas.append(m)
        if self.tiempo > 30 and self.estado == "corriendo":
            self.estado = "atascado"


# cámara

areaMin = 90                  # píxeles mínimos del objeto (cuadro de 640x480)
areaMinBorde = 25             # mínimo si el objeto toca el borde del cuadro
relleno = 24                  # borde replicado alrededor del cuadro
perdidoMax = 6                # cuadros sin ver el objeto antes de "levantar el lápiz"
margenCam = 0.08              # margen de la cámara que se ignora
tamVista = (400, 300)         # tamaño de la imagen de la cámara que se muestra en pantalla


def rangosDesdeMuestra(h, s, v):
    # rango HSV alrededor del color muestreado, permisivo para que los bordes oscuros cuenten
    dh = 12
    sMin = int(max(40, s * 0.4))
    vMin = int(max(35, v * 0.3))
    hBajo, hAlto = h - dh, h + dh
    if hBajo < 0:
        return [((0, sMin, vMin), (hAlto, 255, 255)), ((180 + hBajo, sMin, vMin), (179, 255, 255))]
    if hAlto > 179:
        return [((hBajo, sMin, vMin), (179, 255, 255)), ((0, sMin, vMin), (hAlto - 180, 255, 255))]
    return [((hBajo, sMin, vMin), (hAlto, 255, 255))]


def buscarMarcador(cuadro, rangos):
    # devuelve ((x, y, area) normalizados, máscara) o (None, máscara)
    h0, w0 = cuadro.shape[:2]
    grande = cv2.copyMakeBorder(cuadro, relleno, relleno, relleno, relleno, cv2.BORDER_REPLICATE)
    suave = cv2.GaussianBlur(grande, (7, 7), 0)
    hsv = cv2.cvtColor(suave, cv2.COLOR_BGR2HSV)
    mascara = None
    for bajo, tope in rangos:
        m = cv2.inRange(hsv, np.array(bajo, np.uint8), np.array(tope, np.uint8))
        mascara = m if mascara is None else cv2.bitwise_or(mascara, m)
    nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, nucleo)
    mascara = cv2.dilate(mascara, nucleo, iterations=2)
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mejor, mejorArea = None, 0
    for c in contornos:
        area = cv2.contourArea(c)
        x, y, bw, bh = cv2.boundingRect(c)
        borde = x <= relleno + 2 or y <= relleno + 2 or x + bw >= w0 + relleno - 2 or y + bh >= h0 + relleno - 2
        if area >= (areaMinBorde if borde else areaMin) and area > mejorArea:
            mejor, mejorArea = c, area
    mascara = mascara[relleno:relleno + h0, relleno:relleno + w0]
    if mejor is None or mejorArea > 0.25 * w0 * h0:
        return None, mascara
    m = cv2.moments(mejor)
    if m["m00"] == 0:
        return None, mascara
    cx = min(1.0, max(0.0, (m["m10"] / m["m00"] - relleno) / w0))
    cy = min(1.0, max(0.0, (m["m01"] / m["m00"] - relleno) / h0))
    return (cx, cy, mejorArea), mascara


class Camara:
    def __init__(self, indice=0):
        self.indice = indice
        self.captura = None
        self.activa = True
        self.rangos = None
        self.ruta_calibracion = os.path.join(carpeta, "..", "..", "config", "coaster_calibration.json")
        self.cargarCalibracion()
        self.pedido = None           # (nx, ny) donde tomar el color
        self.pos = None              # posición suavizada en coordenadas de la ventana
        self.perdido = 99
        self.candado = threading.Lock()
        self.vista = None
        self.numCuadro = 0
        self.hilo = threading.Thread(target=self.ciclo, daemon=True)

    def abrir(self):
        if cv2 is None:
            return False
        sistemas = [cv2.CAP_DSHOW, 0] if sys.platform.startswith("win") else [0]
        for sis in sistemas:
            self.captura = cv2.VideoCapture(self.indice, sis) if sis else cv2.VideoCapture(self.indice)
            if self.captura.isOpened():
                self.captura.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.captura.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.captura.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return True
            self.captura.release()
        self.captura = None
        return False

    def iniciar(self):
        self.hilo.start()

    def calibrar(self, cuadro, nx, ny):
        h, w = cuadro.shape[:2]
        x, y = int(nx * w), int(ny * h)
        parche = cuadro[max(0, y - 6):y + 7, max(0, x - 6):x + 7]
        if parche.size == 0:
            return
        hsv = cv2.cvtColor(parche, cv2.COLOR_BGR2HSV).reshape(-1, 3)
        hh, ss, vv = (int(np.median(hsv[:, i])) for i in range(3))
        self.rangos = rangosDesdeMuestra(hh, ss, vv)
        self.guardarCalibracion()

    def cargarCalibracion(self):
        """Recupera los rangos HSV guardados por el menú de pausa."""
        try:
            import json
            ruta = os.path.abspath(self.ruta_calibracion)
            if os.path.exists(ruta):
                with open(ruta, "r", encoding="utf-8") as archivo:
                    datos = json.load(archivo)
                self.rangos = [
                    (tuple(par[0]), tuple(par[1])) for par in datos.get("rangos", [])
                ] or None
        except Exception:
            self.rangos = None

    def guardarCalibracion(self):
        try:
            import json
            if not self.rangos:
                return
            ruta = os.path.abspath(self.ruta_calibracion)
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "w", encoding="utf-8") as archivo:
                json.dump({"rangos": [[list(bajo), list(tope)] for bajo, tope in self.rangos]}, archivo, indent=2)
        except Exception:
            pass

    def ciclo(self):
        while self.activa:
            leyo, cuadro = self.captura.read()
            if not leyo:
                time.sleep(0.01)
                continue
            cuadro = cv2.flip(cuadro, 1)               # espejo
            if self.pedido is not None:
                self.calibrar(cuadro, *self.pedido)
                self.pedido = None
            hallado, mascara = None, None
            if self.rangos:
                hallado, mascara = buscarMarcador(cuadro, self.rangos)
            if hallado:
                nx, ny, _ = hallado
                u = limitar((nx - margenCam) / (1 - 2 * margenCam), 0, 1)
                v = limitar((ny - margenCam) / (1 - 2 * margenCam), 0, 1)
                tx, ty = u * ancho, v * alto
                if self.pos is None:
                    self.pos = (tx, ty)
                else:
                    # lento filtra mucho (sin temblor), rápido filtra poco (sin retraso)
                    rapidez = math.dist(self.pos, (tx, ty))
                    k = min(0.9, 0.2 + rapidez / 90)
                    self.pos = (interpolar(self.pos[0], tx, k), interpolar(self.pos[1], ty, k))
                self.perdido = 0
            else:
                self.perdido += 1
                if self.perdido > perdidoMax:
                    self.pos = None
            chico = cv2.resize(cuadro, tamVista, interpolation=cv2.INTER_AREA)
            if mascara is not None:
                m = cv2.resize(mascara, tamVista, interpolation=cv2.INTER_NEAREST)
                capa = np.zeros_like(chico)
                capa[:] = (120, 176, 128)              # verde de la paleta (en orden azul, verde, rojo)
                tinte = cv2.addWeighted(chico, 0.35, capa, 0.65, 0)
                chico = np.where(m[..., None] > 0, tinte, chico).astype(np.uint8)
            if hallado:
                p = (int(hallado[0] * tamVista[0]), int(hallado[1] * tamVista[1]))
                cv2.circle(chico, p, 20, (216, 240, 250), 3, cv2.LINE_AA)     # crema
                cv2.circle(chico, p, 5, (108, 128, 224), -1, cv2.LINE_AA)     # coral
            rgb = cv2.cvtColor(chico, cv2.COLOR_BGR2RGB)
            with self.candado:
                self.vista = rgb.tobytes()
                self.numCuadro += 1

    def obtenerVista(self):
        with self.candado:
            return self.numCuadro, self.vista

    def detener(self):
        self.activa = False
        time.sleep(0.05)
        if self.captura is not None:
            self.captura.release()


# dibujo

def crearFondo():
    sup = pygame.Surface((ancho, alto))
    for y in range(alto):
        sup.fill(mezclar(cCieloAlto, cCieloBajo, limitar(y / ySuelo, 0, 1) ** 1.4), (0, y, ancho, 1))
    pygame.draw.circle(sup, (255, 240, 200), (930, 150), 78)
    pygame.draw.circle(sup, (255, 222, 130), (930, 150), 56)

    def colinas(color, base, amp, frec, fase):
        pts = [(0, alto)]
        for x in range(0, ancho + 20, 20):
            pts.append((x, base + math.sin(x * frec + fase) * amp + math.sin(x * frec * 2.3 + fase * 2) * amp * 0.4))
        pts.append((ancho, alto))
        pygame.draw.polygon(sup, color, pts)

    colinas((160, 212, 178), 440, 30, 0.006, 0.5)
    colinas((116, 192, 134), 495, 24, 0.009, 2.0)
    # carpa
    cx, base, anc, alt = 850, ySuelo, 170, 100
    for i in range(6):
        x0 = cx - anc // 2 + i * anc // 6
        x1 = x0 + anc // 6
        color = (236, 84, 84) if i % 2 == 0 else cCrema
        pygame.draw.polygon(sup, color, [(cx, base - alt), (x0, base - 40), (x1, base - 40)])
        pygame.draw.rect(sup, color, (x0, base - 40, anc // 6 + 1, 40))
    pygame.draw.line(sup, cOscuro, (cx, base - alt), (cx, base - alt - 22), 3)
    pygame.draw.polygon(sup, cAmarillo, [(cx, base - alt - 22), (cx + 18, base - alt - 16), (cx, base - alt - 10)])
    pygame.draw.rect(sup, (88, 168, 110), (0, ySuelo, ancho, alto - ySuelo))
    pygame.draw.rect(sup, (66, 140, 92), (0, ySuelo, ancho, 8))
    return sup


def cargarFondoNivel(i):
    # busca fondos/nivel1.jpg, nivel2.jpg... y devuelve None si no existe.
    # Si el nivel tiene rueda que gira (y su imagen existe) se usa el fondo sin la rueda
    nombres = [f"nivel{i + 1}"]
    if niveles[i].get("rueda") and imagenRueda(niveles[i]) is not None:
        nombres.insert(0, f"nivel{i + 1}SinRueda")
    rutas = [os.path.join(carpeta, "fondos", f"{n}.{ext}") for n in nombres for ext in ("jpg", "jpeg", "png")]
    for ruta in rutas:
        if not os.path.exists(ruta):
            continue
        try:
            foto = pygame.image.load(ruta).convert()
        except pygame.error:
            continue
        # se agranda hasta cubrir toda la ventana y se recorta lo que sobre
        esc = max(ancho / foto.get_width(), alto / foto.get_height())
        medida = (int(foto.get_width() * esc) + 1, int(foto.get_height() * esc) + 1)
        foto = pygame.transform.smoothscale(foto, medida)
        sup = pygame.Surface((ancho, alto))
        sup.blit(foto, ((ancho - medida[0]) // 2, (alto - medida[1]) // 2))
        return sup
    return None


def dibujarNoria(sup, t, cx=190, cy=395, r=110):
    color = (222, 150, 160)
    pygame.draw.polygon(sup, color, [(cx, cy), (cx - 55, ySuelo), (cx - 38, ySuelo)])
    pygame.draw.polygon(sup, color, [(cx, cy), (cx + 55, ySuelo), (cx + 38, ySuelo)])
    pygame.draw.circle(sup, color, (cx, cy), r, 5)
    pygame.draw.circle(sup, color, (cx, cy), r // 2, 3)
    for i in range(8):
        a = t * 0.25 + i * math.pi / 4
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        pygame.draw.line(sup, color, (cx, cy), (x, y), 3)
        pygame.draw.circle(sup, (250, 200, 130), (int(x), int(y + 10)), 11)
        pygame.draw.circle(sup, color, (int(x), int(y + 10)), 11, 3)
    pygame.draw.circle(sup, color, (cx, cy), 9)


radioRueda = 198               # radio del aro de la rueda en pantalla
cabinasRueda = 16              # cuántas cabinas cuelgan del aro
altoCabina = 38                # alto en pantalla de cada cabina
velocidadRueda = 0.08          # qué tan rápido gira (radianes por segundo)


def imagenRueda(nivel):
    # rueda de día en los niveles de día y la de luces de neón en la tarde y la noche
    nombre = "ruedaNoche" if nivel.get("hora") in ("tarde", "noche") else "ruedaDia"
    clave = ("ruedaLista", nombre)
    if clave not in almacen:
        img = cargarElemento(nombre, True)
        if img is not None:
            esc = 2 * radioRueda / max(img.get_size())
            img = pygame.transform.smoothscale(img, (round(img.get_width() * esc), round(img.get_height() * esc)))
        almacen[clave] = img
    return almacen[clave]


coloresCabina = (cVerdeVivo, cMorado, (236, 110, 170), (110, 160, 230))   # luces de noche
vaivenCabina = 2.5             # cuántos grados se mecen las cabinas


def imagenCabina(hora, luz=None):
    # la cabina no lleva contorno porque es parte del fondo; se oscurece en la tarde y la noche.
    # Con luz, la cabina se ilumina de ese color, como si tuviera un foco adentro
    clave = ("cabinaLista", hora, luz)
    if clave not in almacen:
        img = cargarElemento("cabina")
        if img is not None:
            img = pygame.transform.smoothscale(img, (round(altoCabina * img.get_width() / img.get_height()), altoCabina))
            entonar(img, hora)
            if luz is not None:
                img.fill(tuple(c // 3 for c in luz), special_flags=pygame.BLEND_RGB_ADD)
        almacen[clave] = img
    return almacen[clave]


def dibujarRueda(sup, nivel, t):
    # el aro gira sobre el eje del fondo; las cabinas giran con él pero siempre cuelgan derechas
    img = imagenRueda(nivel)
    if img is None:
        return
    cx, cy = nivel["rueda"]
    ang = t * velocidadRueda
    if nivel.get("hora") in ("tarde", "noche"):
        # resplandor de las luces de neón
        pegarBrillo(sup, (cx, cy), mezclar(cVerdeVivo, cMorado, 0.5), radioRueda + 40, 0.35)
    # el aro se vuelve a girar solo cuando avanzó 0.2 grados (el borde se mueve menos de 1 píxel)
    grados = round(math.degrees(ang) * 5) / 5
    guardada = almacen.get("ruedaGirada")
    if guardada is None or guardada[0] != (id(img), grados):
        guardada = almacen["ruedaGirada"] = ((id(img), grados), pygame.transform.rotozoom(img, -grados, 1))
    girada = guardada[1]
    sup.blit(girada, girada.get_rect(center=(cx, cy)))
    # las cabinas usan el mismo ángulo que el aro para moverse juntos, sin temblar
    ang = math.radians(grados)
    hora = nivel.get("hora", "dia")
    noche = hora in ("tarde", "noche")
    for k in range(cabinasRueda):
        a = ang + k * math.tau / cabinasRueda
        punto = (cx + math.cos(a) * radioRueda * 0.97, cy + math.sin(a) * radioRueda * 0.97)
        luz = coloresCabina[k % len(coloresCabina)] if noche else None
        cabina = imagenCabina(hora, luz)
        if cabina is None:
            return
        if noche:
            # halo de color que titila despacio, a juego con el neón de la rueda
            pegarBrillo(sup, (punto[0], punto[1] + altoCabina * 0.6), luz, 30,
                        0.5 + 0.2 * math.sin(t * 2 + k * 1.7))
        # cuelga del aro y se mece un poquito, cada una a su ritmo
        vaiven = math.radians(vaivenCabina * math.sin(t * 1.3 + k * 0.9))
        pegarGirado(sup, cabina, punto, (cabina.get_width() / 2, 3), vaiven)


def dibujarNubes(sup, t):
    for i, (y, esc) in enumerate([(120, 1.0), (205, 0.7), (150, 1.2)]):
        x = (t * (9 + i * 4) + i * 420) % (ancho + 300) - 150
        for dx, dy, r in [(0, 0, 26), (28, -10, 32), (62, 0, 24), (30, 10, 26)]:
            pygame.draw.circle(sup, (255, 255, 255), (int(x + dx * esc), int(y + dy * esc)), int(r * esc))


# estilo pintado a mano

almacen = {}


def temblorFijo(i, semilla=0.0):
    # número entre -1 y 1 que siempre es el mismo para el mismo i, así el trazo no vibra
    v = math.sin(i * 12.9898 + semilla * 78.233) * 43758.5453
    return (v - math.floor(v)) * 2 - 1


def subdividir(pts, salto, cerrado=False):
    # agrega puntos en los lados largos para que el temblor se note a lo largo de la línea
    sal = []
    n = len(pts)
    for i in range(n if cerrado else n - 1):
        a, b = pts[i], pts[(i + 1) % n]
        tramos = max(1, int(math.dist(a, b) // salto))
        for k in range(tramos):
            sal.append((interpolar(a[0], b[0], k / tramos), interpolar(a[1], b[1], k / tramos)))
    if not cerrado:
        sal.append(pts[-1])
    return sal


def pintarSuave(sup, pts, margen, fondo, dibujar):
    # dibuja en una capa más grande y la achica con suavizado, así los bordes no se ven pixelados
    x0 = int(min(p[0] for p in pts) - margen)
    y0 = int(min(p[1] for p in pts) - margen)
    w = int(max(p[0] for p in pts) + margen) - x0 + 1
    h = int(max(p[1] for p in pts) + margen) - y0 + 1
    k = 3 if w * h < 90000 else 2
    capa = pygame.Surface((w * k, h * k), pygame.SRCALPHA)
    capa.fill((*fondo, 0))
    dibujar(capa, lambda q: [((x - x0) * k, (y - y0) * k) for x, y in q], k)
    pegar(sup, pygame.transform.smoothscale(capa, (w, h)), (x0, y0))


class CapaGuardada(pygame.Surface):
    # capa transparente que se pinta una vez y se reutiliza; guarda el color ya multiplicado por
    # la transparencia para que los bordes suaves no se oscurezcan al pegarla
    def __init__(self, medida=(ancho, alto)):
        super().__init__(medida, pygame.SRCALPHA)


def pegar(sup, capa, pos):
    if isinstance(sup, CapaGuardada):
        sup.blit(capa.premul_alpha(), pos, special_flags=pygame.BLEND_PREMULTIPLIED)
    else:
        sup.blit(capa, pos)


def dibujarGuardado(sup, nombre, clave, dibujo):
    # solo se vuelve a pintar cuando cambia la clave (por ejemplo, cuando cambia la vía)
    guardado = almacen.get(nombre)
    if guardado is None or guardado[0] != clave:
        capa = CapaGuardada()
        dibujo(capa)
        guardado = almacen[nombre] = (clave, capa)
    sup.blit(guardado[1], (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)


def entonar(sup, hora, caja=None):
    # multiplica lo dibujado por el color de la hora, así se ve de tarde o de noche
    if hora in tonos:
        sup.fill(tonos[hora], caja, special_flags=pygame.BLEND_RGB_MULT)


def dibujarEntonado(sup, caja, hora, dibujo):
    # lo que se mueve (bandera, carros) se pinta en una capa aparte, se entona y se pega
    if hora not in tonos:
        dibujo(sup)
        return
    if "capaTono" not in almacen:
        almacen["capaTono"] = CapaGuardada()
    capa = almacen["capaTono"]
    caja = caja.clip(capa.get_rect())
    capa.set_clip(caja)
    capa.fill((0, 0, 0, 0), caja)
    dibujo(capa)
    capa.set_clip(None)
    entonar(capa, hora, caja)
    sup.blit(capa, caja.topleft, area=caja, special_flags=pygame.BLEND_PREMULTIPLIED)


def brillo(color, r):
    # halo de luz suave, como pigmento claro que se corre en el papel mojado
    clave = ("brillo", color, r)
    if clave not in almacen:
        k = 3
        g = pygame.Surface((2 * r * k, 2 * r * k), pygame.SRCALPHA)
        g.fill((*color, 0))
        for i in range(r * k, 0, -2):
            pygame.draw.circle(g, (*color, int(200 * (1 - i / (r * k)) ** 1.6)), (r * k, r * k), i)
        almacen[clave] = pygame.transform.smoothscale(g, (2 * r, 2 * r))
    return almacen[clave]


def pegarBrillo(sup, centro, color, r, fuerza=1.0):
    luz = brillo(color, r)
    luz.set_alpha(int(255 * limitar(fuerza, 0, 1)))
    sup.blit(luz, (centro[0] - r, centro[1] - r))


def puntosEstrella(centro, r, adentro=0.45, puntas=5, giro=0.0):
    pts = []
    for k in range(puntas * 2):
        a = -math.pi / 2 + giro + k * math.pi / puntas
        rr = r if k % 2 == 0 else r * adentro
        pts.append((centro[0] + math.cos(a) * rr, centro[1] + math.sin(a) * rr))
    return pts


def puntoNitido(color, r):
    # circulito de color con anillo de tinta, pintado 4 veces más grande y achicado (se guarda)
    clave = ("puntoNitido", color, r)
    if clave not in almacen:
        k = 4
        lado = (2 * r + 6) * k
        c = lado / 2
        sup = pygame.Surface((lado, lado), pygame.SRCALPHA)
        sup.fill((*cOscuro, 0))
        pygame.draw.circle(sup, cOscuro, (c, c), (r + 1) * k)
        pygame.draw.circle(sup, color, (c, c), (r - 1) * k)
        almacen[clave] = pygame.transform.smoothscale(sup, (lado // k, lado // k))
    return almacen[clave]


def pastillaNitida(w, h, color):
    # pastilla de acuarela nítida: se pinta 4 veces más grande y se achica. Contorno de tinta,
    # la orilla con más pigmento y un brillo suave arriba. Se guarda para no repintarla
    clave = ("pastilla", w, h, color)
    if clave not in almacen:
        k = 4
        m = 2 * k
        capa = pygame.Surface((w * k + 2 * m, h * k + 2 * m), pygame.SRCALPHA)
        capa.fill((*cOscuro, 0))
        caja = pygame.Rect(m, m, w * k, h * k)
        pygame.draw.rect(capa, cOscuro, caja, border_radius=caja.h // 2)
        adentro = caja.inflate(-4 * k, -4 * k)
        pygame.draw.rect(capa, mezclar(color, cOscuro, 0.2), adentro, border_radius=adentro.h // 2)
        centro = adentro.inflate(-2 * k, -2 * k)
        pygame.draw.rect(capa, color, centro, border_radius=centro.h // 2)
        brillo = pygame.Surface(capa.get_size(), pygame.SRCALPHA)
        franja = pygame.Rect(centro.x + 4 * k, centro.y + k, centro.w - 8 * k, centro.h // 4)
        pygame.draw.rect(brillo, (*cCrema, 110), franja, border_radius=franja.h // 2)
        capa.blit(brillo, (0, 0))
        almacen[clave] = pygame.transform.smoothscale(capa, (w + 4, h + 4))
    return almacen[clave]


def redondear(img, r):
    # recorta la imagen con esquinas redondas y suaves (la máscara se guarda por tamaño)
    clave = ("esquinas", img.get_size(), r)
    if clave not in almacen:
        k = 3
        w, h = img.get_size()
        mascara = pygame.Surface((w * k, h * k), pygame.SRCALPHA)
        mascara.fill((255, 255, 255, 0))
        pygame.draw.rect(mascara, (255, 255, 255, 255), (0, 0, w * k, h * k), border_radius=r * k)
        almacen[clave] = pygame.transform.smoothscale(mascara, (w, h))
    sal = img.convert_alpha()
    sal.blit(almacen[clave], (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return sal


def iconoNitido(nombre, tam=28):
    # pastilla redonda de tinta con el símbolo en crema; todos con el mismo tamaño y grosor de trazo.
    # Se dibuja 4 veces más grande y se achica para que quede nítido
    clave = ("icono", nombre, tam)
    if clave in almacen:
        return almacen[clave]
    # si hay imagen en la carpeta elementos se usa esa
    archivos = {"flecha": "botonPlay", "atras": "botonRehacer", "equis": "botonEliminar"}
    img = cargarElemento(archivos.get(nombre, ""))
    if img is not None:
        # los íconos son redondos: se recortan con un círculo limpio un poco hacia adentro (así se va
        # el filito blanco de la orilla) y se les pone un contorno fino de tinta. Todo 4 veces más grande
        k = 4
        lado = tam * k
        grande = pygame.transform.smoothscale(img, (lado, lado))
        mascara = pygame.Surface((lado, lado), pygame.SRCALPHA)
        mascara.fill((255, 255, 255, 0))
        pygame.draw.circle(mascara, (255, 255, 255, 255), (lado / 2, lado / 2), lado * 0.46)
        grande.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.circle(grande, cOscuro, (lado / 2, lado / 2), lado * 0.46, k)
        almacen[clave] = pygame.transform.smoothscale(grande, (tam, tam))
        return almacen[clave]
    k = 4
    lado = tam * k
    sup = pygame.Surface((lado, lado), pygame.SRCALPHA)
    sup.fill((*cOscuro, 0))
    pygame.draw.circle(sup, cOscuro, (lado / 2, lado / 2), lado / 2 - k)
    g = lado * 0.11

    def p(x, y):
        return (x * lado, y * lado)

    if nombre == "flecha":
        tri = [p(0.41, 0.32), p(0.41, 0.68), p(0.70, 0.5)]
        pygame.draw.polygon(sup, cCrema, tri)
        lineaRedonda(sup, cCrema, tri, g * 0.8, True)
    elif nombre == "atras":
        # flecha curva de deshacer: arco por arriba y punta a la izquierda
        arco = [p(0.52 + 0.17 * math.cos(math.radians(a)), 0.54 + 0.17 * math.sin(math.radians(a)))
                for a in range(215, 451, 6)]
        lineaRedonda(sup, cCrema, arco, g)
        (x0, y0), (x1, y1) = arco[0], arco[1]
        d = math.dist(arco[0], arco[1]) or 1
        ux, uy = (x0 - x1) / d, (y0 - y1) / d
        punta = [(x0 + ux * g * 1.2, y0 + uy * g * 1.2),
                 (x0 - uy * g * 1.1, y0 + ux * g * 1.1), (x0 + uy * g * 1.1, y0 - ux * g * 1.1)]
        pygame.draw.polygon(sup, cCrema, punta)
        lineaRedonda(sup, cCrema, punta, g * 0.5, True)
    elif nombre == "equis":
        lineaRedonda(sup, cCrema, [p(0.36, 0.36), p(0.64, 0.64)], g)
        lineaRedonda(sup, cCrema, [p(0.36, 0.64), p(0.64, 0.36)], g)
    almacen[clave] = pygame.transform.smoothscale(sup, (tam, tam))
    return almacen[clave]


def cargarEstrellas():
    # usa elementos/estrellaLlena y elementos/estrellaVacia; si no hay, se dibujan las estrellas a mano
    if "estrellas" in almacen:
        return almacen["estrellas"]
    llena = cargarElemento("estrellaLlena")
    vacia = cargarElemento("estrellaVacia")
    if llena is not None and vacia is None:
        # sin estrella vacía se hace una gris clarita a partir de la llena
        vacia = pygame.transform.grayscale(llena)
        vacia.fill((222, 212, 190), special_flags=pygame.BLEND_RGB_MULT)
    almacen["estrellas"] = (llena, vacia) if llena is not None else None
    return almacen["estrellas"]


def imagenEstrella(img, r, k=1):
    # acomoda la imagen en un cuadrado del tamaño de la estrella dibujada, sin deformarla
    lado = int(r * 2 + 12) * k
    clave = ("imagenEstrella", id(img), lado)
    if clave not in almacen:
        esc = lado / max(img.get_size())
        chica = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * esc)), max(1, int(img.get_height() * esc))))
        cuadro = pygame.Surface((lado, lado), pygame.SRCALPHA)
        cuadro.blit(chica, chica.get_rect(center=(lado / 2, lado / 2)), special_flags=pygame.BLEND_RGBA_MAX)
        almacen[clave] = cuadro
    return almacen[clave]


def estrellaLlena(sup, centro, r, frac, t, imagen=None):
    # estrella que se va llenando de pintura desde abajo, con la orilla mojada ondulada.
    # Sirve con la estrella dibujada o con una imagen de estrella traída de afuera
    k = 3
    lado = int(r * 2 + 12)
    tam = lado * k
    if imagen is None:
        c = tam / 2
        estrella = [(c + (x - centro[0]) * k, c + (y - centro[1]) * k) for x, y in puntosEstrella(centro, r)]
        capa = pygame.Surface((tam, tam), pygame.SRCALPHA)
        capa.fill((*cOro, 0))
        pygame.draw.polygon(capa, (*cOro, 245), estrella)
    else:
        capa = imagenEstrella(imagen, r, k).copy()
    if frac < 1:
        # la máscara guarda la forma de la estrella antes de borrar lo que está arriba de la pintura
        mascara = capa.copy()
        mascara.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_MAX)
        forma = capa.get_bounding_rect(min_alpha=40)
        nivel = forma.bottom - frac * forma.h
        onda = [(x, nivel + math.sin(x / tam * 9 + t * 7) * 2.2 * k) for x in range(0, tam + 3 * k, 3 * k)]
        pygame.draw.polygon(capa, (0, 0, 0, 0), [(0, 0)] + onda + [(tam, 0)])
        orilla = pygame.Surface((tam, tam), pygame.SRCALPHA)
        orilla.fill((*cOroOsc, 0))
        pygame.draw.lines(orilla, (*cOroOsc, 255), False, onda, 2 * k)
        orilla.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        capa.blit(orilla, (0, 0))
    pegar(sup, pygame.transform.smoothscale(capa, (lado, lado)), (centro[0] - lado / 2, centro[1] - lado / 2))


subidaFuego = 0.45             # segundos que tarda el cohete en subir
estallidoFuego = 1.5           # segundos que dura el estallido
cicloFuego = 3.0               # cada cuánto vuelve a salir un cohete
# cada fuego usa una sola familia de colores: oscuro, medio y claro
paletasFuego = {
    "rojo": ((200, 56, 52), (240, 96, 80), (255, 184, 168)),
    "dorado": ((214, 140, 36), (246, 192, 80), (255, 236, 170)),
    "azul": ((56, 104, 186), (104, 162, 232), (200, 226, 252)),
    "morado": ((132, 80, 180), (196, 122, 214), (240, 206, 246)),
    "turquesa": ((36, 140, 140), (80, 196, 186), (192, 242, 232)),
    "verde": ((56, 146, 76), (108, 200, 118), (204, 242, 200)),
    "rosa": ((196, 66, 128), (238, 128, 180), (255, 212, 232)),
}


def paletaVuelta(nombre, vuelta):
    # en cada vuelta el fuego cambia de color, pasando por todas las paletas
    nombres = list(paletasFuego)
    return paletasFuego[nombres[(nombres.index(nombre) + vuelta * 3) % len(nombres)]]


def puntosFigura(forma):
    # dónde queda cada chispa al abrirse el fuego (entre -1 y 1) y de qué tipo es: 0 las grandes de afuera,
    # 1 las claras de adentro y 2 las bolitas pequeñas. Se calcula una vez por figura
    clave = ("figura", forma)
    if clave in almacen:
        return almacen[clave]
    pts = []
    if forma == "circulo":
        for anillo, n, r in ((0, 36, 1.0), (2, 28, 0.82), (1, 22, 0.64), (2, 16, 0.46), (1, 10, 0.28)):
            for k in range(n):
                a = (k + anillo * 0.5) * math.tau / n
                pts.append((math.cos(a) * r, math.sin(a) * r, anillo))
    elif forma == "corazon":
        for anillo, n, r in ((0, 48, 1.0), (2, 36, 0.8), (1, 26, 0.6), (2, 16, 0.4), (1, 8, 0.2)):
            for k in range(n):
                a = k * math.tau / n
                x = 16 * math.sin(a) ** 3
                y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
                pts.append((x / 17 * r, (y - 3) / 17 * r, anillo))
    elif forma == "k":
        # palo de la K y sus dos brazos, con una chispa cada poquito
        for a, b in (((-0.5, -1), (-0.5, 1)), ((-0.4, 0.1), (0.55, -1)), ((-0.15, -0.15), (0.6, 1))):
            n = int(math.dist(a, b) / 0.12)
            for k in range(n + 1):
                pts.append((interpolar(a[0], b[0], k / n), interpolar(a[1], b[1], k / n), 0))
    almacen[clave] = pts
    return pts


def puntosTexto(texto, fuente, salto=5, escala=1.4):
    # chispas que forman una palabra: se escribe la palabra en grande y se toma un punto cada pocos píxeles
    clave = ("figuraTexto", texto, salto, escala)
    if clave not in almacen:
        letras = pygame.transform.smoothscale_by(fuente.render(texto, True, (255, 255, 255)), escala)
        mascara = pygame.mask.from_surface(letras)
        w, h = letras.get_size()
        almacen[clave] = [(x - w / 2, y - h / 2, 0) for x in range(0, w, salto) for y in range(0, h, salto)
                          if mascara.get_at((x, y))]
    return almacen[clave]


def chispaLuz(color, r):
    # chispa encendida: halo de luz, gota de color y centro casi blanco (se guarda por color y tamaño)
    clave = ("chispa", color, r)
    if clave not in almacen:
        sup = pygame.Surface((6 * r, 6 * r), pygame.SRCALPHA)
        sup.blit(brillo(color, 3 * r), (0, 0))
        k = 4
        gota = pygame.Surface((2 * r * k, 2 * r * k), pygame.SRCALPHA)
        gota.fill((*color, 0))
        pygame.draw.circle(gota, color, (r * k, r * k), r * k)
        pygame.draw.circle(gota, mezclar(color, (255, 255, 255), 0.75), (r * k, r * k), r * k * 0.55)
        sup.blit(pygame.transform.smoothscale(gota, (2 * r, 2 * r)), (2 * r, 2 * r))
        almacen[clave] = sup
    return almacen[clave]


def pegarChispa(sup, punto, color, r, alfa=255):
    chispa = chispaLuz(color, r)
    chispa.set_alpha(int(limitar(alfa, 0, 255)))
    sup.blit(chispa, chispa.get_rect(center=(round(punto[0]), round(punto[1]))))


def sonarFuego(clave, t):
    # Sonido del estallido (módulo común de BarranquillaWare); si el Coaster corre solo, sin sonido
    try:
        from effects.fuegos_sonido import avisar_estallido
    except ImportError:
        return
    avisar_estallido(clave, t, subidaFuego)


def dibujarFuego(sup, centro, figura, escala, t, paleta, duracion=estallidoFuego, tamChispa=4, detalle=False,
                 chispitas=False):
    # fuego artificial: un cohete sube desde abajo y estalla en chispas de luz que forman la figura.
    # t son los segundos desde que salió el cohete. Con detalle, las chispas de afuera dejan una estela
    # de bolitas y adentro titilan brillitos sueltos. Con chispitas, las de afuera vuelven a estallar
    cx, cy = centro
    oscuro, medio, claro = paleta
    if t < subidaFuego:
        f = t / subidaFuego
        y = interpolar(margenInf, cy, 1 - (1 - f) ** 2)
        trazoMano(sup, [(cx, y + 40), (cx, y)], medio, 2, 0.6, cx, False, False)
        pegarChispa(sup, (cx, y), claro, 5)
        return
    f = (t - subidaFuego) / duracion
    if f >= 1:
        return
    alcance = max(math.hypot(p[0], p[1]) for p in figura) * escala
    # resplandor grande al estallar que queda suave mientras duran las chispas
    pegarBrillo(sup, centro, medio, int(alcance * 1.3), 0.3 * (1 - f) + 0.7 * max(0.0, 1 - f / 0.25))
    abre = 1 - (1 - min(1.0, f / 0.35)) ** 3          # se abre rápido y se queda quieto para que se lea
    caida = 30 * max(0.0, (f - 0.55) / 0.45) ** 2     # al final las chispas bajan un poco
    alfa = 255 if f < 0.6 else 255 * (1 - (f - 0.6) / 0.4)
    if detalle and f > 0.25:
        # brillitos sueltos que se prenden y se apagan entre las chispas
        for k in range(26):
            a = (temblorFijo(k, cx) + 1) * math.pi
            d = (temblorFijo(k, cx + 1) + 1) / 2 * alcance * 0.85
            luz = alfa * max(0.0, math.sin(t * 18 + k * 2.3))
            if luz > 10:
                pegarChispa(sup, (cx + math.cos(a) * d, cy + math.sin(a) * d + caida), claro, 2, luz)
    for k, (dx, dy, anillo) in enumerate(figura):
        x, y = cx + dx * escala * abre, cy + dy * escala * abre + caida
        color = claro if anillo == 1 else medio
        if f < 0.35:
            cola = (cx + dx * escala * abre * 0.6, cy + dy * escala * abre * 0.6)
            pygame.draw.aaline(sup, oscuro, cola, (x, y))
        # al final las chispas titilan
        luz = alfa if f < 0.45 else alfa * (0.65 + 0.35 * math.sin(t * 28 + k * 1.9))
        r = max(2, tamChispa - anillo)
        if f > 0.6:
            r = max(2, round(r * (1 - 0.4 * (f - 0.6) / 0.4)))
        if detalle and anillo == 0 and f > 0.1:
            # estela de bolitas que quedan atrás de cada chispa de afuera y caen un poquito más
            for n, fuerza in ((1, 0.6), (2, 0.4), (3, 0.22)):
                atras = escala * abre * (1 - 0.08 * n)
                pegarChispa(sup, (cx + dx * atras, cy + dy * atras + caida * (1 + 0.3 * n)), medio, 2, luz * fuerza)
        pegarChispa(sup, (x, y), color, r, luz)
        if chispitas and anillo == 0 and k % 2 == 0 and f > 0.4:
            # una de cada dos chispas de afuera estalla otra vez en un circulito de bolitas mini
            g = (f - 0.4) / 0.6
            rr = 16 * (1 - (1 - g) ** 2)
            for n in range(6):
                b = n * math.tau / 6 + k
                pegarChispa(sup, (x + math.cos(b) * rr, y + math.sin(b) * rr + 6 * g * g), claro, 2, 240 * (1 - g))


def lineaRedonda(sup, color, pts, grosor, cerrado=False):
    # línea gruesa con las uniones redondeadas para que no queden huecos entre tramos
    pygame.draw.lines(sup, color, cerrado, pts, int(grosor))
    if grosor > 2:
        for p in pts:
            pygame.draw.circle(sup, color, p, grosor / 2)


def trazoMano(sup, pts, color, grosor=2, tremor=1.0, semilla=0.0, cerrado=False, doble=True):
    # línea hecha a mano: cada punto se corre un poco y se repasa con una segunda línea fina
    if len(pts) < 2:
        return
    suc = [(x + temblorFijo(i, semilla) * tremor, y + temblorFijo(i, semilla + 1.7) * tremor)
           for i, (x, y) in enumerate(pts)]
    lineas = [(suc, color, grosor)]
    if doble and grosor >= 2:
        repaso = [(x + temblorFijo(i, semilla + 4.1) * tremor + 1, y + temblorFijo(i, semilla + 5.3) * tremor + 1)
                  for i, (x, y) in enumerate(pts)]
        lineas.append((repaso, mezclar(color, cCrema, 0.45), 1))
    if grosor <= 2:
        # las líneas finas se dibujan directo con suavizado, que es más rápido
        for q, c, g in lineas:
            tramos = list(zip(q, q[1:])) + ([(q[-1], q[0])] if cerrado else [])
            for a, b in tramos:
                pygame.draw.aaline(sup, c, a, b, g)
        return

    def dibujar(capa, escalar, k):
        for q, c, g in lineas:
            lineaRedonda(capa, c, escalar(q), g * k, cerrado)

    pintarSuave(sup, suc, grosor + tremor + 3, color, dibujar)


def perfil(sup, pts, color=cOscuro, grosor=2, tremor=0.8, semilla=0.0):
    # contorno cerrado de un polígono, dibujado a mano
    trazoMano(sup, subdividir(pts, 20, True), color, grosor, tremor, semilla, True)


def contornoCaja(caja, r):
    # puntos alrededor de un rectángulo con esquinas redondeadas
    r = min(r, caja.w // 2, caja.h // 2)
    esquinas = ((caja.right - r, caja.top + r, -90), (caja.right - r, caja.bottom - r, 0),
                (caja.left + r, caja.bottom - r, 90), (caja.left + r, caja.top + r, 180))
    pts = []
    n = max(4, int(r / 6))          # esquinas grandes llevan más puntos para que no se vean facetadas
    for cx, cy, ang in esquinas:
        for k in range(n + 1):
            a = math.radians(ang + k * 90 / n)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return subdividir(pts, 16, True)


def lavado(sup, pts, color, alfa=225, borde=0.35):
    # mancha de acuarela: relleno un poco transparente y el borde más cargado de pigmento
    oscuro = mezclar(color, cOscuro, borde)

    def dibujar(capa, escalar, k):
        q = escalar(pts)
        pygame.draw.polygon(capa, (*color, alfa), q)
        lineaRedonda(capa, (*oscuro, alfa), q, 2 * k, True)

    pintarSuave(sup, pts, 4, oscuro, dibujar)


def granoPapel():
    # textura de papel: manchitas suaves de pigmento (sin puntos blancos), se crea una sola vez
    if "grano" not in almacen:
        rnd = random.Random(7)
        chico = pygame.Surface((40, 40), pygame.SRCALPHA)
        for x in range(40):
            for y in range(40):
                chico.set_at((x, y), (120, 90, 60, rnd.randrange(0, 20)))
        almacen["grano"] = pygame.transform.smoothscale(chico, (160, 160))
    return almacen["grano"]


def baseCartulina(w, h, relleno, r):
    # papel pintado con sombra suave, manchas de agua y granito; se guarda para no rehacerlo
    clave = (w, h, relleno, r)
    if clave in almacen:
        return almacen[clave]
    m = 8
    capa = pygame.Surface((w + 2 * m, h + 2 * m), pygame.SRCALPHA)
    for k in range(5, 0, -1):
        pygame.draw.rect(capa, (70, 50, 40, 10 * (6 - k)), (m - k, m - k + 5, w + 2 * k, h + 2 * k),
                         border_radius=r + k)
    # el papel se pinta 3 veces más grande y se achica, así las esquinas quedan suaves
    k = 3
    carta = pygame.Surface((w * k, h * k), pygame.SRCALPHA)
    carta.fill((*relleno, 255))
    rnd = random.Random(w * 31 + h)
    tinte = pygame.Surface((w * k, h * k), pygame.SRCALPHA)
    for _ in range(3):
        ew, eh = rnd.randrange(w // 3, w // 2 + 1), rnd.randrange(h // 2, h + 1)
        caja = (rnd.randrange(-ew // 3, w - ew // 2) * k, rnd.randrange(-eh // 3, h - eh // 2) * k, ew * k, eh * k)
        pygame.draw.ellipse(tinte, (*mezclar(relleno, cMadera, 0.22), 46), caja)
    carta.blit(tinte, (0, 0))
    pygame.draw.rect(carta, (*mezclar(relleno, cMaderaOsc, 0.2), 255), (0, 0, w * k, h * k), 4 * k,
                     border_radius=r * k)
    carta = pygame.transform.smoothscale(carta, (w, h))
    grano = granoPapel()
    for gx in range(0, w, 160):
        for gy in range(0, h, 160):
            carta.blit(grano, (gx, gy))
    mascara = pygame.Surface((w * k, h * k), pygame.SRCALPHA)
    mascara.fill((255, 255, 255, 0))
    pygame.draw.rect(mascara, (255, 255, 255, 255), (0, 0, w * k, h * k), border_radius=r * k)
    carta.blit(pygame.transform.smoothscale(mascara, (w, h)), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    capa.blit(carta, (m, m))
    almacen[clave] = capa
    return capa


def panel(sup, caja, relleno=cCrema, borde=cOscuro, r=12, grosor=3):
    # el panel completo (papel y contorno) se guarda para no repintarlo en cada cuadro
    clave = ("panel", caja.x, caja.y, caja.w, caja.h, tuple(relleno), tuple(borde), r, grosor)
    if clave not in almacen:
        capa = baseCartulina(caja.w, caja.h, tuple(relleno), r).copy()
        trazoMano(capa, contornoCaja(pygame.Rect(8, 8, caja.w, caja.h), r), borde, grosor, 0.8,
                  caja.x * 0.013 + caja.y * 0.007, True)
        almacen[clave] = capa
    sup.blit(almacen[clave], (caja.x - 8, caja.y - 8))


def puntosCirculo(centro, r, n=32, irregular=0.0, semilla=0.0):
    # puntos alrededor de un círculo; irregular deforma el borde como una mancha de agua
    pts = []
    for k in range(n):
        a = k * math.tau / n
        rr = r * (1 + irregular * temblorFijo(k, semilla))
        pts.append((centro[0] + math.cos(a) * rr, centro[1] + math.sin(a) * rr))
    return pts


def circuloMano(sup, centro, r, color=cOscuro, grosor=2, tremor=0.8, semilla=0.0):
    trazoMano(sup, puntosCirculo(centro, r), color, grosor, tremor, semilla, True)


def arcoMano(sup, centro, r, frac, color, grosor=4, semilla=0.0):
    # arco que empieza arriba y avanza como las agujas del reloj
    n = max(2, int(r * math.tau * frac / 6))
    pts = []
    for k in range(n + 1):
        a = -math.pi / 2 + math.tau * frac * k / n
        pts.append((centro[0] + math.cos(a) * r, centro[1] + math.sin(a) * r))
    trazoMano(sup, pts, color, grosor, 0.6, semilla, False, False)


def anilloPintado(sup, centro, r, color, semilla=0.0):
    # anillo que resalta sobre cualquier fondo: halo de luz, centro clarito, borde crema por fuera,
    # banda de color vivo y contorno de tinta por fuera y por dentro
    pegarBrillo(sup, centro, color, round(r) + 26, 0.6)
    # el anillo se pinta una vez por cada tamaño (de medio en medio píxel) y se guarda
    r = round(r * 2) / 2
    clave = ("anillo", r, color, semilla)
    if clave not in almacen:
        lado = int(2 * r + 30)
        c = (lado / 2, lado / 2)
        capa = CapaGuardada((lado, lado))
        lavado(capa, puntosCirculo(c, r - 5, 24, 0.05, semilla), cCrema, 110, 0.05)
        circuloMano(capa, c, r + 3, cCrema, 10, 0.6, semilla)
        circuloMano(capa, c, r, color, 7, 0.6, semilla)
        circuloMano(capa, c, r + 8, cOscuro, 2, 0.6, semilla + 1)
        circuloMano(capa, c, r - 4.5, cOscuro, 2, 0.6, semilla + 2)
        almacen[clave] = capa
    capa = almacen[clave]
    sup.blit(capa, capa.get_rect(center=(round(centro[0]), round(centro[1]))), special_flags=pygame.BLEND_PREMULTIPLIED)

def cargarTarjeta():
    for ext in ("jpg", "jpeg", "png"):
        ruta = os.path.join(carpeta, "fondos", f"tarjeta.{ext}")
        if not os.path.exists(ruta):
            continue
        try:
            foto = pygame.image.load(ruta).convert_alpha()
        except pygame.error:
            continue
        foto = achicar(foto, 1200)
        if cv2 is not None:
            return quitarCuadritos(foto)
        # sin opencv: recorte aproximado con esquinas redondeadas
        mancha = pygame.mask.from_threshold(foto, (255, 255, 255, 255), (120, 120, 120, 255))
        mancha.invert()
        trozos = [r for r in mancha.get_bounding_rects() if r.w * r.h > 4000]
        if trozos:
            img = foto.subsurface(trozos[0].unionall(trozos[1:]).inflate(-16, -16)).copy()
            mascara = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            mascara.fill((255, 255, 255, 0))
            pygame.draw.rect(mascara, (255, 255, 255, 255), mascara.get_rect(), border_radius=img.get_height() // 8)
            img.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            return img
    return None


def borrarFondo(foto, fondo, borde, semillas=((0, 0),)):
    # borra el fondo que está conectado con la orilla de la imagen (o con otro punto de semillas)
    # y recorta lo que sobra. fondo es una tabla de verdadero/falso que dice qué píxeles parecen fondo
    marca = fondo.astype(np.uint8).T.copy()
    h, w = marca.shape
    for punto in semillas:
        cv2.floodFill(marca, np.zeros((h + 2, w + 2), np.uint8), punto, 2)
    dibujo = (marca != 2).astype(np.uint8) * 255
    dibujo = cv2.erode(dibujo, np.ones((borde, borde), np.uint8))   # quita el filito claro de la orilla
    dibujo = cv2.GaussianBlur(dibujo, (borde, borde), 0)
    alfa = pygame.surfarray.pixels_alpha(foto)
    alfa[:] = dibujo.T
    del alfa
    ys, xs = np.nonzero(dibujo)
    caja = pygame.Rect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min()) + 1, int(ys.max() - ys.min()) + 1)
    return foto.subsurface(caja).copy()


def quitarCuadritos(foto):
    # la tarjeta trae un fondo de cuadritos grises: gris puro (los cuadritos y su sombra)
    # o casi gris pero claro (la orilla difuminada)
    rgb = pygame.surfarray.array3d(foto).astype(np.int16)
    tinte = rgb.max(axis=2) - rgb.min(axis=2)
    return borrarFondo(foto, (tinte <= 8) | ((tinte <= 16) & (rgb.min(axis=2) >= 165)), 7)


def quitarBlanco(foto):
    # borra el fondo blanco de una imagen; si ya trae transparencia, solo se recorta
    if foto.get_at((0, 0)).a < 250:
        return foto.subsurface(foto.get_bounding_rect(min_alpha=10)).copy()
    if cv2 is None:
        mancha = pygame.mask.from_threshold(foto, (255, 255, 255, 255), (26, 26, 26, 255))
        mancha.invert()
        foto = mancha.to_surface(setsurface=foto, unsetcolor=(0, 0, 0, 0))
        return foto.subsurface(foto.get_bounding_rect(min_alpha=10)).copy()
    rgb = pygame.surfarray.array3d(foto).astype(np.int16)
    return borrarFondo(foto, ((rgb.max(axis=2) - rgb.min(axis=2)) <= 20) & (rgb.min(axis=2) >= 225), 3)


def achicar(img, lado):
    # en el juego las imágenes se ven pequeñas; trabajar con ellas en tamaño completo es lento
    mayor = max(img.get_size())
    if mayor <= lado:
        return img
    esc = lado / mayor
    return pygame.transform.smoothscale(img, (round(img.get_width() * esc), round(img.get_height() * esc)))


def quitarTodoBlanco(foto):
    # para la rueda: también se borra el blanco que queda encerrado entre los rayos.
    # Lo casi blanco queda semitransparente y a su color se le quita el blanco del papel
    if cv2 is None:
        return quitarBlanco(foto)
    rgb = pygame.surfarray.array3d(foto).astype(np.float32)
    alfa = np.clip((250 - rgb.min(axis=2)) / 30, 0, 1)
    color = 255 - (255 - rgb) / np.maximum(alfa, 0.05)[..., None]
    pygame.surfarray.blit_array(foto, np.clip(color, 0, 255).astype(np.uint8))
    pixeles = pygame.surfarray.pixels_alpha(foto)
    pixeles[:] = (alfa * 255).astype(np.uint8)
    del pixeles
    return foto.subsurface(foto.get_bounding_rect(min_alpha=10)).copy()


def cargarElemento(nombre, todoBlanco=False):
    # busca la imagen en la carpeta elementos (o en fondos), en png o jpg, sin fondo blanco.
    # Devuelve None si no existe, y así el juego usa el dibujo hecho por código
    clave = ("elemento", nombre, todoBlanco)
    if clave in almacen:
        return almacen[clave]
    img = None
    for subcarpeta in ("elementos", "fondos"):
        for ext in ("png", "jpg", "jpeg"):
            ruta = os.path.join(carpeta, subcarpeta, f"{nombre}.{ext}")
            if img is None and os.path.exists(ruta):
                try:
                    foto = achicar(pygame.image.load(ruta).convert_alpha(), 800)
                    img = quitarTodoBlanco(foto) if todoBlanco else quitarBlanco(foto)
                except pygame.error:
                    img = None
    almacen[clave] = img
    return img


def estirarSinDeformar(img, w, h, prop=0.2):
    # las esquinas se escalan parejo y solo los lados y el centro se estiran, así el borde no se deforma
    iw, ih = img.get_size()
    c = int(min(iw, ih) * prop)
    t = max(1, min(int(min(w, h) * prop), w // 2, h // 2))
    xs, ys = (0, c, iw - c, iw), (0, c, ih - c, ih)
    xd, yd = (0, t, w - t, w), (0, t, h - t, h)
    sal = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(3):
        for j in range(3):
            medida = (xd[i + 1] - xd[i], yd[j + 1] - yd[j])
            if medida[0] <= 0 or medida[1] <= 0:
                continue
            trozo = img.subsurface((xs[i], ys[j], xs[i + 1] - xs[i], ys[j + 1] - ys[j]))
            sal.blit(pygame.transform.smoothscale(trozo, medida), (xd[i], yd[j]), special_flags=pygame.BLEND_RGBA_MAX)
    return sal


def cajaPintada(sup, caja):
    # cajita de arriba (nivel, monedas y tinta) hecha con elementos/botonGeneral.
    # Las puntas redondas no se deforman; si no hay imagen se usa el panel pintado
    img = cargarElemento("botonGeneral")
    if img is None:
        panel(sup, caja, cCrema, cOscuro, 14, 3)
        return
    clave = ("cajaPintada", caja.w, caja.h)
    m = 4
    if clave not in almacen:
        capa = pygame.Surface((caja.w + 2 * m, caja.h + 2 * m), pygame.SRCALPHA)
        capa.blit(estirarSinDeformar(img, caja.w, caja.h, 0.5), (m, m))
        # contorno café encima para que resalte sobre cualquier fondo
        trazoMano(capa, contornoCaja(pygame.Rect(m, m, caja.w, caja.h), caja.h // 2), cOscuro, 3, 0.8,
                  caja.x * 0.013, True)
        almacen[clave] = capa
    sup.blit(almacen[clave], (caja.x - m, caja.y - m))


def huecoCentro(img):
    # mide el hueco transparente del centro caminando desde el medio hacia cada lado
    w, h = img.get_size()
    cx, cy = w // 2, h // 2
    izq, der, arr, aba = cx, cx, cy, cy
    while izq > 0 and img.get_at((izq - 1, cy)).a < 128:
        izq -= 1
    while der < w - 1 and img.get_at((der + 1, cy)).a < 128:
        der += 1
    while arr > 0 and img.get_at((cx, arr - 1)).a < 128:
        arr -= 1
    while aba < h - 1 and img.get_at((cx, aba + 1)).a < 128:
        aba += 1
    return pygame.Rect(izq, arr, der - izq + 1, aba - arr + 1)


def cargarMarco():
    # elementos/marcoCamara trae cuadritos grises por fuera y en el hueco del centro: se borran los dos.
    # Devuelve la imagen y el hueco donde va la cámara, o None si no hay imagen
    if "marco" in almacen:
        return almacen["marco"]
    almacen["marco"] = None
    for ext in ("png", "jpg", "jpeg"):
        ruta = os.path.join(carpeta, "elementos", f"marcoCamara.{ext}")
        if cv2 is None or not os.path.exists(ruta):
            continue
        try:
            foto = achicar(pygame.image.load(ruta).convert_alpha(), 800)
        except pygame.error:
            continue
        rgb = pygame.surfarray.array3d(foto).astype(np.int16)
        tinte = rgb.max(axis=2) - rgb.min(axis=2)
        fondo = (tinte <= 8) | ((tinte <= 16) & (rgb.min(axis=2) >= 165))
        w, h = foto.get_size()
        img = borrarFondo(foto, fondo, 5, ((0, 0), (w // 2, h // 2)))
        almacen["marco"] = (img, huecoCentro(img))
        break
    return almacen["marco"]


def dibujarMarcoCamara(sup, caja, grosor):
    # pega el marco de modo que su hueco quede justo sobre caja, donde ya está la cámara.
    # Se corta en las orillas del hueco: las esquinas se achican parejo hasta el grosor pedido
    # y los lados se estiran hasta que el hueco mida lo mismo que caja
    img, hueco = cargarMarco()
    esc = grosor / hueco.x
    arriba = round(hueco.top * esc)
    clave = ("marcoListo", caja.size, grosor)
    m = 4
    if clave not in almacen:
        # todo se arma 3 veces más grande y se achica al final, así el contorno queda nítido
        k = 3
        iw, ih = img.get_size()
        xs, ys = (0, hueco.left, hueco.right, iw), (0, hueco.top, hueco.bottom, ih)
        bx, by = round((iw - hueco.right) * esc), round((ih - hueco.bottom) * esc)
        xd = [(v + m) * k for v in (0, grosor, grosor + caja.w, grosor + caja.w + bx)]
        yd = [(v + m) * k for v in (0, arriba, arriba + caja.h, arriba + caja.h + by)]
        marco = pygame.Surface((xd[3] + m * k, yd[3] + m * k), pygame.SRCALPHA)
        for i in range(3):
            for j in range(3):
                if i == 1 and j == 1:
                    continue           # el hueco del centro queda vacío
                trozo = img.subsurface((xs[i], ys[j], xs[i + 1] - xs[i], ys[j + 1] - ys[j]))
                medida = (xd[i + 1] - xd[i], yd[j + 1] - yd[j])
                marco.blit(pygame.transform.smoothscale(trozo, medida), (xd[i], yd[j]))
        # contorno café que sigue la orilla de afuera: la silueta del marco en tinta se pega corrida
        # en todas las direcciones por debajo del marco (como el contorno de los carritos)
        silueta = marco.copy()
        silueta.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        silueta.fill((*cOscuro, 0), special_flags=pygame.BLEND_RGBA_ADD)
        sal = pygame.Surface(marco.get_size(), pygame.SRCALPHA)
        r = (2 if grosor >= 15 else 1.5) * k
        for paso in range(24):
            a = paso * math.tau / 24
            sal.blit(silueta, (math.cos(a) * r, math.sin(a) * r), special_flags=pygame.BLEND_RGBA_MAX)
        sal.fill((0, 0, 0, 0), (xd[1], yd[1], xd[2] - xd[1], yd[2] - yd[1]))     # nada de tinta sobre la cámara
        sal.blit(marco, (0, 0))
        almacen[clave] = pygame.transform.smoothscale(sal, (sal.get_width() // k, sal.get_height() // k))
    sup.blit(almacen[clave], (caja.x - grosor - m, caja.y - arriba - m))


def tarjetaPintada(sup, caja):
    if "tarjeta" not in almacen:
        almacen["tarjeta"] = cargarTarjeta()
    base = almacen["tarjeta"]
    if base is None:
        panel(sup, caja, cCrema, cOscuro, 22, 5)
        return
    clave = ("tarjeta", caja.w, caja.h)
    if clave not in almacen:
        almacen[clave] = armarTarjeta(base, caja.w, caja.h)
    sup.blit(almacen[clave], (caja.x - 12, caja.y - 12))


def bordeTarjeta(w, h):
    # grosor aproximado del borde azul de la imagen ya estirada
    return int(min(w, h) * 0.2) // 2


def armarTarjeta(base, w, h):
    # sombra suave debajo, imagen recortada con esquinas redondas y contorno de tinta encima,
    # así la orilla de la imagen nunca se ve y la tarjeta resalta sobre el fondo
    m = 12
    r = int(bordeTarjeta(w, h) * 1.3)
    sal = pygame.Surface((w + 2 * m, h + 2 * m), pygame.SRCALPHA)
    for k in range(7, 0, -1):
        pygame.draw.rect(sal, (50, 36, 30, 9 * (8 - k)), (m - k, m - k + 6, w + 2 * k, h + 2 * k),
                         border_radius=r + k)
    img = estirarSinDeformar(base, w, h)
    forma = pygame.Rect(5, 5, w - 10, h - 10)
    k = 3
    mascara = pygame.Surface((w * k, h * k), pygame.SRCALPHA)
    mascara.fill((255, 255, 255, 0))
    pygame.draw.rect(mascara, (255, 255, 255, 255), (forma.x * k, forma.y * k, forma.w * k, forma.h * k),
                     border_radius=r * k)
    img.blit(pygame.transform.smoothscale(mascara, (w, h)), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    sal.blit(img, (m, m))
    grosor = 4 if min(w, h) >= 300 else 3
    trazoMano(sal, contornoCaja(forma.move(m, m), r), cOscuro, grosor, 0.8, w * 0.01 + h * 0.02, True)
    return sal

def cargarFuente(tam):
    carpetaFuenteLetra = os.path.join(carpeta, "fuenteLetra")
    if os.path.isdir(carpetaFuenteLetra):
        for nombre in sorted(os.listdir(carpetaFuenteLetra)):
            if nombre.lower().endswith((".ttf", ".otf")):
                return pygame.font.Font(os.path.join(carpetaFuenteLetra, nombre), int(tam * 1.3))
    return pygame.font.SysFont("trebuchetms,verdana,arial", tam, bold=True)


def cargarFuenteTitulo(tam):
    ruta = os.path.join(os.path.dirname(carpeta), "assets", "Titulos.ttf")
    if os.path.exists(ruta):
        try:
            from core.asset_manager import FuenteTitulo
            return FuenteTitulo(ruta, int(tam * 1.15))
        except ImportError:
            return pygame.font.Font(ruta, int(tam * 1.15))
    return cargarFuente(tam)


def crearBarra():
    # franja de madera de abajo: tablas con vetas pintadas
    h = alto - margenInf
    sup = pygame.Surface((ancho, h))
    sup.fill(cMadera)
    rnd = random.Random(3)
    for _ in range(70):
        x, y = rnd.randrange(-20, ancho), rnd.randrange(6, h)
        color = mezclar(cMadera, cMaderaOsc, rnd.uniform(0.15, 0.5))
        pygame.draw.line(sup, color, (x, y), (x + rnd.randrange(40, 160), y + rnd.randrange(-3, 4)),
                         rnd.choice((1, 2, 3)))
    for y in range(25, h, 25):
        trazoMano(sup, subdividir([(0, y), (ancho, y)], 40), cMaderaOsc, 2, 1.0, y * 0.3)
    trazoMano(sup, subdividir([(0, 3), (ancho, 3)], 30), cOscuro, 4, 1.0, 9.0)
    return sup


def dibujarVia(sup, camino):
    # vía nítida: todo se pinta al doble de tamaño y se achica. Cada pieza lleva primero una línea
    # de tinta gruesa y encima su color, así todas quedan con un contorno parejo
    if len(camino) < 2:
        return
    n = len(camino)
    normales = []
    for i, (x, y) in enumerate(camino):
        a, b = camino[max(0, i - 1)], camino[min(n - 1, i + 1)]
        d = math.dist(a, b) or 1.0
        normales.append((-(b[1] - a[1]) / d, (b[0] - a[0]) / d))
    viga = [(x + nx * 11, y + ny * 11) for (x, y), (nx, ny) in zip(camino, normales)]
    brillo = [(x - nx * 2, y - ny * 2) for (x, y), (nx, ny) in zip(camino, normales)]
    # soportes cada 10 puntos, desde la viga hasta la madera de abajo
    soportes = []
    for i in range(0, n, 10):
        x, y = camino[i]
        if y < margenInf - 16:
            soportes.append([(x, y + 8), (x + temblorFijo(i, 2.0) * 3, margenInf + 4)])
    bordes = list(camino) + [p for soporte in soportes for p in soporte]

    def dibujar(capa, escalar, k):
        riel, vigaG, brilloG = escalar(camino), escalar(viga), escalar(brillo)
        lineaRedonda(capa, (*cCrema, 60), riel, 22 * k)          # halo claro para leerla sobre la foto
        for soporte in soportes:
            columna = escalar(soporte)
            lineaRedonda(capa, cOscuro, columna, 8 * k)
            lineaRedonda(capa, cMadera, columna, 5 * k)
        for i in range(0, n, 3):
            lineaRedonda(capa, cOscuro, [riel[i], vigaG[i]], 4.5 * k)
        lineaRedonda(capa, cOscuro, vigaG, 6 * k)
        lineaRedonda(capa, cMaderaOsc, vigaG, 3.5 * k)
        for i in range(0, n, 3):
            lineaRedonda(capa, cMadera, [riel[i], vigaG[i]], 2.5 * k)
        lineaRedonda(capa, cOscuro, riel, 12 * k)
        lineaRedonda(capa, cRiel, riel, 8.5 * k)
        lineaRedonda(capa, mezclar(cRiel, cCrema, 0.55), brilloG, 2 * k)

    pintarSuave(sup, bordes, 14, cOscuro, dibujar)


anchoCarro = 70                          # ancho en pantalla del carrito de imagen
asientoCarro = (0.13, 0.42)              # dónde va la cadera del pasajero (fracción del carrito)
altoPasajero = 34                        # alto en pantalla del pasajero con los brazos abajo
coloresPasajero = {1: (cTurquesa, cAmarillo), 2: (cMorado, cVerde)}   # camiseta y gorra


grosorContorno = 2                       # contorno de tinta de carritos y pasajeros
margenContorno = 2 * grosorContorno      # espacio extra que ocupan la tinta y el halo


def conContorno(img, medida):
    # achica la imagen a medida y le pone alrededor un contorno de tinta y por fuera un halo crema
    # suave, así resalta sobre cualquier fondo. Se trabaja 3 veces más grande para que quede nítido
    k = 3
    w, h = medida
    m = margenContorno * k
    grande = pygame.transform.smoothscale(img, (w * k, h * k))
    silueta = grande.copy()
    silueta.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    tela = pygame.Surface((w * k + 2 * m, h * k + 2 * m), pygame.SRCALPHA)

    def estampar(destino, color, radio):
        # pega la silueta corrida en todas las direcciones: queda una silueta más gorda
        mancha = silueta.copy()
        mancha.fill((*color, 0), special_flags=pygame.BLEND_RGBA_ADD)
        for r in (radio, radio / 2):
            for paso in range(24):
                a = paso * math.tau / 24
                destino.blit(mancha, (m + math.cos(a) * r, m + math.sin(a) * r), special_flags=pygame.BLEND_RGBA_MAX)

    estampar(tela, cCrema, m)
    tela.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_MULT)     # el halo queda suave
    tinta = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    estampar(tinta, cOscuro, grosorContorno * k)
    tela.blit(tinta, (0, 0))
    tela.blit(grande, (m, m))
    return pygame.transform.smoothscale(tela, (w + 2 * margenContorno, h + 2 * margenContorno))


def imagenCarro(numero):
    # el carrito se voltea para que mire hacia la derecha y se achica al tamaño del juego
    clave = ("carroListo", numero)
    if clave not in almacen:
        img = cargarElemento(f"carrito{numero}")
        if img is not None:
            img = pygame.transform.flip(img, True, False)
            alto = round(anchoCarro * img.get_height() / img.get_width())
            img = conContorno(img, (anchoCarro, alto))
        almacen[clave] = img
    return almacen[clave]


def imagenPasajero(numero, manos):
    # persona1.png (brazos abajo) y persona1Manos.png (brazos arriba); las dos con la misma escala
    clave = ("pasajeroListo", numero, manos)
    if clave not in almacen:
        normal = cargarElemento(f"persona{numero}")
        img = cargarElemento(f"persona{numero}Manos") if manos else normal
        if normal is None or img is None:
            almacen[clave] = None
        else:
            esc = altoPasajero / normal.get_height()
            medida = (max(1, round(img.get_width() * esc)), max(1, round(img.get_height() * esc)))
            img = conContorno(img, medida)
            # la cadera es el centro de lo que hay pintado en la franja de abajo de la persona
            alto = max(1, medida[1] // 8)
            franja = img.subsurface((0, img.get_height() - margenContorno - alto, img.get_width(), alto))
            cadera = pygame.mask.from_surface(franja).centroid()[0]
            almacen[clave] = (img, cadera)
    return almacen[clave]


def pegarGirado(sup, img, ancla, puntoImg, ang):
    # gira la imagen y la pega de modo que su punto puntoImg quede justo sobre ancla
    c, s = math.cos(ang), math.sin(ang)
    vx, vy = puntoImg[0] - img.get_width() / 2, puntoImg[1] - img.get_height() / 2
    centro = (ancla[0] - (c * vx - s * vy), ancla[1] - (s * vx + c * vy))
    girada = imagenGirada(img, ang)
    pegar(sup, girada, girada.get_rect(center=centro).topleft)


def precargarImagenes():
    # prepara todas las imágenes al abrir el juego; si se cargan la primera vez que aparecen,
    # el juego se traba un momento en plena partida
    cargarEstrellas()
    for numero in (1, 2):
        imagenCarro(numero)
        imagenPasajero(numero, False)
        imagenPasajero(numero, True)
    for icono in ("flecha", "atras", "equis"):
        iconoNitido(icono)
    cargarElemento("moneda")
    cargarElemento("botonGeneral")
    cargarElemento("techo")
    for nombre in imagenesBoton.values():
        cargarElemento(nombre)
    cargarMarco()
    for hora in ("dia", "tarde", "noche"):
        imagenCabina(hora)
        for luz in coloresCabina:
            imagenCabina(hora, luz)


def imagenGirada(img, ang):
    # girar es lento, así que se guardan las imágenes ya giradas (de medio grado en medio grado)
    grados = round(math.degrees(ang) * 2) / 2
    clave = (id(img), grados)
    giradas = almacen.setdefault("giradas", {})
    if clave not in giradas:
        if len(giradas) > 600:
            giradas.clear()
        giradas[clave] = pygame.transform.rotozoom(img, -grados, 1)
    return giradas[clave]


def dibujarPasajero(sup, cadera, ang, numero, manos):
    lista = imagenPasajero(numero, manos)
    if lista is not None:
        img, cx = lista
        pegarGirado(sup, img, cadera, (cx, img.get_height() - margenContorno), ang)
        return
    # sin imágenes: persona sencilla de perfil mirando hacia la derecha
    c, s = math.cos(ang), math.sin(ang)

    def loc(a, b):
        return (cadera[0] + c * a - s * b, cadera[1] + s * a + c * b)

    camiseta, gorra = coloresPasajero[numero]
    if manos:
        for dx in (-2, 4):
            trazoMano(sup, [loc(dx, -14), loc(dx + 3, -24), loc(dx + 6, -36)], cOscuro, 3, 0.3, dx, False, False)
    torso = [loc(-6, 2), loc(6, 2), loc(5, -15), loc(-5, -15)]
    lavado(sup, torso, camiseta, 245)
    perfil(sup, torso, cOscuro, 2, 0.4, numero)
    if not manos:
        trazoMano(sup, [loc(1, -12), loc(8, -6), loc(13, -7)], cOscuro, 3, 0.3, 2.0, False, False)
    cabeza = loc(1, -22)
    lavado(sup, puntosCirculo(cabeza, 7, 16), (240, 200, 164), 250, 0.2)
    circuloMano(sup, cabeza, 7, cOscuro, 2, 0.4, numero)
    pygame.draw.circle(sup, cOscuro, loc(4, -23), 1.3)
    trazoMano(sup, [loc(3, -19), loc(5, -19.5)], cOscuro, 1, 0.2, 1.0, False, False)
    visera = [loc(-7, -24), loc(6, -24), loc(11, -23), loc(5, -30), loc(-6, -30)]
    lavado(sup, visera, gorra, 245)
    perfil(sup, visera, cOscuro, 2, 0.4, numero + 1)


def dibujarCarro(sup, punto, ang, emocion, numero, manos=False):
    # carrito de imagen con su pasajero; si falta la imagen se usa el carrito pintado por código
    img = imagenCarro(numero)
    if img is None:
        dibujarCarroPintado(sup, punto, ang, emocion, *estilosPintados[numero - 1])
        return
    temblor = (random.uniform(-1, 1) * emocion * 1.5, random.uniform(-1, 1) * emocion * 1.5)
    c, s = math.cos(ang), math.sin(ang)
    w, h = img.get_size()
    wc, hc = w - 2 * margenContorno, h - 2 * margenContorno      # tamaño del carrito sin el contorno
    # la base de las ruedas queda sobre el riel; el pasajero se pinta antes para que el carro lo tape
    ax = asientoCarro[0] * wc
    ay = 1 - hc + asientoCarro[1] * hc
    cadera = (punto[0] + c * ax - s * ay + temblor[0], punto[1] + s * ax + c * ay + temblor[1])
    dibujarPasajero(sup, cadera, ang, numero, manos)
    ancla = (punto[0] - s * 1 + temblor[0], punto[1] + c * 1 + temblor[1])
    pegarGirado(sup, img, ancla, (w / 2, h - margenContorno), ang)


estilosPintados = ((cMorado, (cVerde, cAmarillo)), (cTurquesa, (cCoral, cAmarillo)))   # atrás, adelante


def dibujarCarroPintado(sup, punto, ang, emocion, colorCuerpo, gorras):
    # emocion (0 a 1) sube los brazos de los pasajeros y hace "vibrar" (según, yo, ok?) el carro
    c, s = math.cos(ang), math.sin(ang)
    temblor = (random.uniform(-1, 1) * emocion * 1.5, random.uniform(-1, 1) * emocion * 1.5)

    def loc(a, b):
        return (punto[0] + c * a - s * b + temblor[0], punto[1] + s * a + c * b + temblor[1])

    cuerpo = [loc(-25, -5), loc(25, -5), loc(31, -21), loc(-31, -21)]
    lavado(sup, cuerpo, colorCuerpo, 238)
    lavado(sup, [loc(-27, -15), loc(28, -15), loc(29, -11), loc(-28, -11)], cCrema, 215, 0.1)
    perfil(sup, cuerpo, cOscuro, 2, 0.7, 3.0)
    for hx, gorra in zip((-9, 12), gorras):
        cabeza = loc(hx, -30)
        if emocion > 0.35:
            pygame.draw.line(sup, cOscuro, loc(hx, -23), loc(hx - 4, -43), 2)
            pygame.draw.line(sup, cOscuro, loc(hx, -23), loc(hx + 6, -43), 2)
        pygame.draw.circle(sup, (240, 200, 164), cabeza, 8)
        pygame.draw.circle(sup, cOscuro, cabeza, 8, 2)
        pygame.draw.circle(sup, cOscuro, loc(hx - 3, -31), 1)
        pygame.draw.circle(sup, cOscuro, loc(hx + 3, -31), 1)
        if emocion > 0.35:
            pygame.draw.circle(sup, cOscuro, loc(hx, -27), 2)
        else:
            pygame.draw.line(sup, cOscuro, loc(hx - 2, -27), loc(hx + 2, -27), 1)
        gor = [loc(hx - 8, -33), loc(hx + 8, -33), loc(hx + 6, -41), loc(hx - 6, -41)]
        lavado(sup, gor, gorra, 240)
        perfil(sup, gor, cOscuro, 2, 0.4, hx)
    for wx in (-16, 16):
        rueda = loc(wx, -3)
        pygame.draw.circle(sup, cMaderaOsc, rueda, 6)
        pygame.draw.circle(sup, cOscuro, rueda, 6, 2)
        pygame.draw.circle(sup, (214, 204, 186), rueda, 2)


def dibujarEnganche(sup, pa, pf):
    d = (pf[0] - pa[0], pf[1] - pa[1])
    m = math.hypot(*d) or 1.0
    d = (d[0] / m, d[1] / m)
    arriba = (d[1], -d[0])
    p1 = (pa[0] + d[0] * 30 + arriba[0] * 10, pa[1] + d[1] * 30 + arriba[1] * 10)
    p2 = (pf[0] - d[0] * 30 + arriba[0] * 10, pf[1] - d[1] * 30 + arriba[1] * 10)
    pygame.draw.line(sup, cOscuro, p1, p2, 5)
    pygame.draw.line(sup, cMaderaOsc, p1, p2, 3)


altoMoneda = 30                          # alto en pantalla de la moneda de imagen


def dibujarMoneda(sup, punto, t, semilla, alto=altoMoneda):
    giro = abs(math.cos(t * 3 + semilla))
    img = cargarElemento("moneda")
    if img is not None:
        # moneda de imagen: se aplana a lo ancho para que parezca que gira
        clave = ("monedaLista", alto)
        if clave not in almacen:
            almacen[clave] = conContorno(img, (round(alto * img.get_width() / img.get_height()), alto))
        base = almacen[clave]
        ancho = max(3, round(base.get_width() * (0.15 + 0.85 * giro)))
        girada = pygame.transform.smoothscale(base, (ancho, base.get_height()))
        sup.blit(girada, girada.get_rect(center=(round(punto[0]), round(punto[1]))))
        return
    anc = giro * 12 + 3
    x, y = punto

    def ovalo(ax, ay, dx=0, dy=0, n=18):
        return [(x + dx + math.cos(k * math.tau / n) * ax, y + dy + math.sin(k * math.tau / n) * ay)
                for k in range(n)]

    lavado(sup, ovalo(anc, 13), cOro, 240, 0.35)
    if anc > 8:
        lavado(sup, ovalo(anc - 5, 8, 1, 1), mezclar(cOro, cOroOsc, 0.4), 140, 0.2)
        lavado(sup, ovalo(anc * 0.3, 3.5, -anc * 0.35, -6, 10), cCrema, 210, 0.05)
        trazoMano(sup, [(x, y - 4), (x, y + 7)], cOroOsc, 2, 0.4, semilla, False, False)
    trazoMano(sup, ovalo(anc, 13), cOscuro, 2, 0.5, semilla, True, False)


def dibujarBandera(sup, punto, t):
    x, y = int(punto[0]), int(punto[1])
    cima = y - 80
    poste = [(x - 3, cima), (x + 3, cima), (x + 3, margenInf + 4), (x - 3, margenInf + 4)]
    lavado(sup, poste, cMadera, 240)
    trazoMano(sup, subdividir([(x - 3, cima), (x - 3, margenInf + 4)], 28), cOscuro, 2, 0.6, x, False, False)
    trazoMano(sup, subdividir([(x + 3, cima), (x + 3, margenInf + 4)], 28), cOscuro, 2, 0.6, x + 3, False, False)
    tabla = [(x - 36, y + 6), (x + 40, y + 6), (x + 40, y + 15), (x - 36, y + 15)]
    lavado(sup, tabla, cMadera, 240)
    perfil(sup, tabla, cOscuro, 2, 0.6, 5.0)
    ola = [math.sin(t * 5 + k * 0.7) * 3 for k in range(11)]
    tela = [(x + 3 + k * 6, cima + 2 + ola[k]) for k in range(11)]
    tela += [(x + 3 + k * 6, cima + 36 + ola[k]) for k in range(10, -1, -1)]
    lavado(sup, tela, cCoralVivo, 245)
    franja = [(x + 3 + k * 6, cima + 13 + ola[k]) for k in range(11)]
    franja += [(x + 3 + k * 6, cima + 24 + ola[k]) for k in range(10, -1, -1)]
    lavado(sup, franja, cCrema, 225, 0.1)
    perfil(sup, tela, cOscuro, 2, 0.5, 6.0)
    pygame.draw.circle(sup, cOro, (x, cima - 3), 5)
    pygame.draw.circle(sup, cOscuro, (x, cima - 3), 5, 2)


def dibujarEstacion(sup, punto):
    # plataforma larga: aquí esperan los dos carros antes de salir
    x, y = int(punto[0]), int(punto[1])
    izq = x - separacion - 66
    for px in (izq + 26, x):
        poste = [(px - 6, y + 14), (px + 6, y + 14), (px + 6, margenInf + 4), (px - 6, margenInf + 4)]
        lavado(sup, poste, cMadera, 240)
        for dx in (-6, 6):
            trazoMano(sup, subdividir([(px + dx, y + 14), (px + dx, margenInf + 4)], 28),
                      cOscuro, 2, 0.6, px + dx, False, False)
    tabla = [(izq, y + 8), (x + 18, y + 8), (x + 18, y + 19), (izq, y + 19)]
    lavado(sup, tabla, cMadera, 240)
    perfil(sup, tabla, cOscuro, 2, 0.6, 1.0)
    # el techo va alto para que las cabezas de los pasajeros no lo toquen
    imgTecho = cargarElemento("techo")
    if imgTecho is not None:
        # techo de imagen, más ancho que el pintado y centrado en el mismo lugar. Se apoya donde termina
        # el poste y crece hacia arriba; lleva contorno de tinta como los carritos
        w = round((x + 22 - izq) * 1.35)
        h = round(w * imgTecho.get_height() / imgTecho.get_width())
        clave = ("techoListo", w)
        if clave not in almacen:
            almacen[clave] = conContorno(imgTecho, (w, h))
        centro = (izq + x + 22) / 2
        pegar(sup, almacen[clave], (centro - w / 2 - margenContorno, y - 68 - h - margenContorno))
    else:
        techo = [(izq, y - 70), (x + 22, y - 70), (x + 10, y - 84), (izq + 12, y - 84)]
        lavado(sup, techo, cCoralVivo, 245)
        perfil(sup, techo, cOscuro, 2, 0.6, 2.0)
    trazoMano(sup, subdividir([(izq + 6, y - 70), (izq + 6, y + 8)], 28), cMaderaOsc, 4, 0.6, 3.0, False, False)


def dibujarLapiz(sup, punto, color):
    u, p = (0.707, -0.707), (0.707, 0.707)

    def pt(a, b):
        return (punto[0] + u[0] * a + p[0] * b, punto[1] + u[1] * a + p[1] * b)

    # punta de madera, cuerpo, anillo de metal y borrador, cada uno como una mancha con su contorno
    partes = (([pt(0, 0), pt(14, -6), pt(14, 6)], mezclar(cCrema, cMadera, 0.35), 1.0),
              ([pt(14, -6), pt(46, -6), pt(46, 6), pt(14, 6)], color, 2.0),
              ([pt(46, -6), pt(51, -6), pt(51, 6), pt(46, 6)], mezclar(cCrema, cMaderaOsc, 0.3), 3.0),
              ([pt(51, -6), pt(58, -5), pt(58, 5), pt(51, 6)], mezclar(cCoral, cCrema, 0.3), 4.0))
    for poli, c, sem in partes:
        lavado(sup, poli, c, 245, 0.3)
        perfil(sup, poli, cOscuro, 2, 0.4, sem)
    lavado(sup, [pt(16, -1), pt(44, -1), pt(44, 2), pt(16, 2)], mezclar(color, cCrema, 0.5), 200, 0.05)
    lavado(sup, [pt(0, 0), pt(5, -2.5), pt(5, 2.5)], cOscuro, 240, 0)


def dibujarBarraTinta(sup, caja, resto, color):
    # barra nítida: se pinta 4 veces más grande y se achica. Contorno de tinta, fondo de papel
    # y la tinta con la orilla más cargada de pigmento y un brillo arriba.
    # Solo se vuelve a pintar cuando cambia lo que queda de tinta
    clave = (caja.size, int(caja.w * resto), color)
    guardada = almacen.get("barraTinta")
    if guardada is not None and guardada[0] == clave:
        sup.blit(guardada[1], (caja.x - 2, caja.y - 2))
        return
    k = 4
    m = 2 * k
    w, h = caja.w * k, caja.h * k
    capa = pygame.Surface((w + 2 * m, h + 2 * m), pygame.SRCALPHA)
    capa.fill((*cOscuro, 0))
    pygame.draw.rect(capa, cOscuro, (m, m, w, h), border_radius=h // 2)
    g = 2 * k
    adentro = pygame.Rect(m + g, m + g, w - 2 * g, h - 2 * g)
    pygame.draw.rect(capa, (250, 242, 222), adentro, border_radius=adentro.h // 2)
    largo = int(adentro.w * resto)
    if largo >= 2 * k:
        tinta = pygame.Rect(adentro.x, adentro.y, largo, adentro.h)
        radio = min(tinta.h, tinta.w) // 2
        pygame.draw.rect(capa, mezclar(color, cOscuro, 0.25), tinta, border_radius=radio)
        pygame.draw.rect(capa, color, tinta.inflate(-2 * k, -2 * k), border_radius=max(1, radio - k))
        brillo = pygame.Surface(capa.get_size(), pygame.SRCALPHA)
        franja = pygame.Rect(tinta.x + 3 * k, tinta.y + int(1.5 * k), max(1, tinta.w - 6 * k), int(1.6 * k))
        pygame.draw.rect(brillo, (*cCrema, 150), franja, border_radius=franja.h // 2)
        capa.blit(brillo, (0, 0))
    chica = pygame.transform.smoothscale(capa, (caja.w + 4, caja.h + 4))
    almacen["barraTinta"] = (clave, chica)
    sup.blit(chica, (caja.x - 2, caja.y - 2))


imagenesBoton = {cVerde: "botonVerde", cAmarillo: "botonAmarillo", cCoral: "botonRojo"}
margenBoton = 4                # espacio alrededor del botón de imagen para su contorno


def botonPintado(caja, color, activo):
    # fondo del botón hecho con la imagen de su color (las esquinas no se deforman); apagado se ve gris.
    # Devuelve None si no hay imagen y así se usa el panel pintado
    img = cargarElemento(imagenesBoton.get(color, ""))
    if img is None:
        return None
    clave = ("botonListo", caja.size, color, activo)
    if clave not in almacen:
        listo = estirarSinDeformar(img, caja.w, caja.h, 0.3)
        if not activo:
            listo = pygame.transform.grayscale(listo)
            listo.fill((236, 228, 214), special_flags=pygame.BLEND_RGB_MULT)
        # contorno café encima para que resalte; queda con un margen alrededor para que no se corte
        m = margenBoton
        capa = pygame.Surface((caja.w + 2 * m, caja.h + 2 * m), pygame.SRCALPHA)
        capa.blit(listo, (m, m))
        # va un poquito hacia adentro para quedar encima del borde que ya trae la imagen
        borde = pygame.Rect(m, m, caja.w, caja.h).inflate(-4, -4)
        trazoMano(capa, contornoCaja(borde, round(caja.h * 0.2)), cOscuro, 3, 0.8, caja.w * 0.011, True)
        almacen[clave] = capa
    return almacen[clave]


def gestorAudio():
    modulo = sys.modules.get("core.audio_manager")
    if modulo is None or not hasattr(modulo, "AudioManager"):
        return None
    return modulo.AudioManager.get_instance()


def cargarSonido(nombre):
    clave = ("sonido", nombre)
    if clave not in almacen:
        sonido = None
        if pygame.mixer.get_init():
            for ruta in (os.path.join(carpeta, "elementos", nombre), os.path.join(os.path.dirname(carpeta), "assets", nombre)):
                if sonido is None and os.path.exists(ruta):
                    try:
                        sonido = pygame.mixer.Sound(ruta)
                    except pygame.error:
                        sonido = None
        almacen[clave] = sonido
    return almacen[clave]


def sonar(nombre):
    sonido = cargarSonido(nombre)
    if sonido is None:
        return
    gestor = gestorAudio()
    if gestor is not None:
        gestor.play_sfx(sonido)
    else:
        sonido.set_volume(0.8)
        sonido.play()


def sonarEscritura(escribiendo):
    gestor = gestorAudio()
    if gestor is not None and hasattr(gestor, "sonarEscritura"):
        gestor.sonarEscritura(escribiendo)
        return
    canal = almacen.get("canalEscritura")
    if not escribiendo:
        if canal is not None:
            canal.fadeout(180)
            almacen["canalEscritura"] = None
        return
    if canal is not None and canal.get_busy():
        return
    sonido = cargarSonido("escribir.mp3")
    if sonido is not None:
        sonido.set_volume(0.55)
        almacen["canalEscritura"] = sonido.play(loops=-1)


def ponerMusica():
    gestor = gestorAudio()
    if gestor is not None and hasattr(gestor, "play_bgm"):
        gestor.play_bgm("tranquilaMusic.mp3")
        return
    ruta = os.path.join(os.path.dirname(carpeta), "assets", "tranquilaMusic.mp3")
    if not os.path.exists(ruta):
        return
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(ruta)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(loops=-1, fade_ms=600)
    except pygame.error:
        pass


def callarMusica():
    almacen["musicaCallada"] = bool(pygame.mixer.get_init() and pygame.mixer.music.get_busy())
    if almacen["musicaCallada"]:
        pygame.mixer.music.pause()


def volverMusica():
    gestor = gestorAudio()
    if almacen.pop("musicaCallada", False):
        if gestor is None or getattr(gestor, "music_enabled", True):
            pygame.mixer.music.unpause()
            if gestor is not None and hasattr(gestor, "sync_music_volume"):
                gestor.sync_music_volume()
    elif gestor is None:
        ponerMusica()


def buscarElemento(*nombres):
    for nombre in nombres:
        for ext in ("png", "jpg", "jpeg"):
            ruta = os.path.join(carpeta, "elementos", f"{nombre}.{ext}")
            if os.path.exists(ruta):
                return ruta
    return None


def cargarTrazosFantasma():
    if "trazosFantasma" in almacen:
        return almacen["trazosFantasma"]
    trazos = []
    hoja = cargarElemento("trazoFantasma")
    if hoja is not None and np is not None:
        ocupadas = (pygame.surfarray.array_alpha(hoja) > 60).any(axis=1)
        inicio = None
        for x, hay in enumerate(list(ocupadas) + [False]):
            if hay and inicio is None:
                inicio = x
            elif not hay and inicio is not None:
                if x - inicio > 20:
                    pieza = hoja.subsurface((inicio, 0, x - inicio, hoja.get_height()))
                    pieza = pieza.subsurface(pieza.get_bounding_rect(min_alpha=10)).copy()
                    trazos.append(pygame.transform.smoothscale_by(pieza, 26 / pieza.get_width()))
                inicio = None
    almacen["trazosFantasma"] = trazos
    return trazos


def cargarLuzAlgoritmo():
    if "luzAlgoritmo" in almacen:
        return almacen["luzAlgoritmo"]
    luz = None
    ruta = buscarElemento("luzAlgoritmo", "luzAlgortimo")
    if ruta is not None and np is not None:
        try:
            foto = achicar(pygame.image.load(ruta).convert_alpha(), 500)
            rgb = pygame.surfarray.array3d(foto).astype(np.float32)
            minimo = rgb.min(axis=2)
            w, h = foto.get_size()
            peso = np.clip(250 - minimo, 0, None)
            xs, ys = np.indices((w, h))
            cx = float((xs * peso).sum() / max(peso.sum(), 1.0))
            cy = float((ys * peso).sum() / max(peso.sum(), 1.0))
            fila = minimo[int(cx):, int(cy)]
            radio = next((i for i, v in enumerate(fila) if v < 160), 20)
            dentro = (xs - cx) ** 2 + (ys - cy) ** 2 < radio ** 2
            alfa = np.clip((250 - minimo) / 30, 0, 1)
            alfa[dentro] = 1.0
            color = 255 - (255 - rgb) / np.maximum(alfa, 0.05)[..., None]
            color[dentro] = rgb[dentro]
            pygame.surfarray.blit_array(foto, np.clip(color, 0, 255).astype(np.uint8))
            pixeles = pygame.surfarray.pixels_alpha(foto)
            pixeles[:] = (alfa * 255).astype(np.uint8)
            del pixeles
            caja = foto.get_bounding_rect(min_alpha=10)
            foto = foto.subsurface(caja).copy()
            escala = 13 / max(radio, 1)
            luz = (pygame.transform.smoothscale_by(foto, escala), ((cx - caja.x) * escala, (cy - caja.y) * escala))
        except pygame.error:
            luz = None
    almacen["luzAlgoritmo"] = luz
    return luz


def caminoFantasma(nivel):
    clave = ("caminoFantasma", id(nivel))
    if clave not in almacen:
        puntos = nivel.get("fantasma")
        almacen[clave] = armarCamino([nivel["salida"]] + list(puntos)) if puntos else []
    return almacen[clave]


def corazonesFantasma(nivel):
    clave = ("corazonesFantasma", id(nivel))
    if clave not in almacen:
        camino = caminoFantasma(nivel)
        if len(camino) < 5:
            almacen[clave] = []
        else:
            via = Via(camino)
            corazones = []
            for f in (0.3, 0.6, 0.9):
                opciones = [via.puntoEn(via.largo * min(0.97, max(0.05, f + d)))[0] for d in (0, -0.03, 0.03, -0.06, 0.06, -0.09, 0.09)]
                corazones.append(next((p for p in opciones if all(math.dist(p, m) >= 64 for m in nivel["monedas"])), opciones[0]))
            almacen[clave] = corazones
    return almacen[clave]


def imagenCorazon(alto=30):
    clave = ("corazon", alto)
    if clave not in almacen:
        ruta = os.path.join(os.path.dirname(carpeta), "assets", "Piano", "corazonLleno.jpg")
        img = None
        if os.path.exists(ruta):
            try:
                foto = achicar(pygame.image.load(ruta).convert_alpha(), 300)
                img = quitarBlanco(foto)
                medida = (max(1, round(img.get_width() * alto / img.get_height())), alto)
                img = conContorno(img, medida)
            except pygame.error:
                img = None
        almacen[clave] = img
    return almacen[clave]


def dibujarCorazon(sup, centro, alto, t, semilla):
    img = imagenCorazon(alto)
    salto = math.sin(t * 2.6 + semilla * 1.7) * 3
    punto = (centro[0], centro[1] + salto)
    pegarBrillo(sup, punto, cCoral, int(alto * 0.9), 0.45 + 0.2 * math.sin(t * 3 + semilla))
    if img is not None:
        sup.blit(img, img.get_rect(center=(int(punto[0]), int(punto[1]))))
        return
    forma = [(punto[0] + x * alto * 0.55, punto[1] + y * alto * 0.55) for x, y, anillo in puntosFigura("corazon") if anillo == 0]
    lavado(sup, forma, cCoralVivo, 235, 0.4)


def dibujarViaFantasma(sup, camino, hora):
    if len(camino) < 2:
        return

    def pintar(capa):
        pintados = cargarTrazosFantasma()
        if pintados:
            via = Via(camino)
            s, n = 13.0, 0
            while s < via.largo - 13:
                punto, tangente, _ = via.puntoEn(s)
                giro = -math.degrees(math.atan2(tangente[1], tangente[0]))
                trazo = pygame.transform.rotozoom(pintados[n % len(pintados)], giro, 1.0)
                pegar(capa, trazo, trazo.get_rect(center=(round(punto[0]), round(punto[1]))).topleft)
                s += 40
                n += 1
        else:
            def trazos(lienzo, escalar, k):
                for i in range(0, len(camino) - 4, 7):
                    tramo = escalar(camino[i:i + 4])
                    lineaRedonda(lienzo, (*cFantasma, 200), tramo, 6 * k)
                    lineaRedonda(lienzo, (*mezclar(cFantasma, cCrema, 0.7), 230), tramo, 2 * k)

            pintarSuave(capa, camino, 8, cFantasma, trazos)
        entonar(capa, hora)

    dibujarGuardado(sup, "viaFantasma", (id(camino), len(camino), hora), pintar)


def dibujarPulsoFantasma(sup, camino, t):
    if len(camino) < 5:
        return
    clave = ("viaFantasmaObjeto", id(camino))
    if clave not in almacen:
        almacen[clave] = Via(camino)
    via = almacen[clave]
    avance = (t * 170) % (via.largo + 220)
    if avance <= via.largo:
        punto = via.puntoEn(avance)[0]
        pintada = cargarLuzAlgoritmo()
        if pintada is not None:
            luz, centro = pintada
            latido = 1.0 + 0.08 * math.sin(t * 9)
            if abs(latido - 1.0) > 0.01:
                luz = pygame.transform.smoothscale_by(luz, latido)
                centro = (centro[0] * latido, centro[1] * latido)
            sup.blit(luz, (round(punto[0] - centro[0]), round(punto[1] - centro[1])))
            return
        pegarBrillo(sup, punto, cFantasma, 26, 0.85)
        bolita = puntoNitido(mezclar(cFantasma, cCrema, 0.55), 5)
        sup.blit(bolita, bolita.get_rect(center=(int(punto[0]), int(punto[1]))))


class Boton:
    def __init__(self, caja, etiqueta, color, accion, icono=None):
        self.caja = pygame.Rect(caja)
        self.etiqueta, self.color, self.accion, self.icono = etiqueta, color, accion, icono
        self.sobre = 0.0
        self.habilitado = lambda: True

    def dibujar(self, sup, fuente):
        activo = self.habilitado()
        relleno = self.color if activo else (204, 196, 182)
        fondo = botonPintado(self.caja, self.color, activo)
        if fondo is None:
            panel(sup, self.caja, relleno, cOscuro, 14, 3)
        else:
            sup.blit(fondo, (self.caja.x - margenBoton, self.caja.y - margenBoton))
        if self.sobre > 0 and activo:
            frac = limitar(self.sobre / tBoton, 0, 1)
            barra = pygame.Rect(self.caja.x + 8, self.caja.bottom - 13, int((self.caja.w - 16) * frac), 7)
            if barra.w >= 8:
                lavado(sup, contornoCaja(barra, 3), cCrema, 230, 0.25)
        txt = fuente.render(self.etiqueta, True, cOscuro)
        grupo = txt.get_width() + (38 if self.icono else 0)
        x0 = self.caja.centerx - grupo // 2
        if self.icono:
            icono = iconoNitido(self.icono)
            sup.blit(icono, icono.get_rect(midleft=(x0, self.caja.centery - 1)))
            x0 += 38
        sup.blit(txt, (x0, self.caja.centery - txt.get_height() // 2 + 1))


# Jueguito

class Juego:
    def __init__(self, usarCamara=True, indiceCamara=0, pantalla=None, auto_flip=True):
        pygame.init()
        self.pantalla = pantalla if pantalla is not None else pygame.display.set_mode((ancho, alto))
        self.auto_flip = auto_flip
        pygame.display.set_caption("Lápiz coaster")
        self.reloj = pygame.time.Clock()
        self.fuentes = {n: cargarFuente(n) for n in (14, 16, 20, 26, 36, 54)}
        self.fuentesTitulo = {n: cargarFuenteTitulo(n) for n in (13, 16, 18, 20, 24, 36)}
        self.fondoBase = crearFondo()
        self.fondos = {}                 # cada fondo se carga la primera vez que se juega su nivel
        self.barra = crearBarra()
        almacen["tarjeta"] = cargarTarjeta()     # se recorta al inicio para que no se trabe después
        precargarImagenes()
        self.tiempo = 0.0
        self.camara = None
        self.modo = "raton"
        self.aviso, self.avisoHasta = "", 0.0
        if usarCamara:
            if cv2 is None:
                print("Falta OpenCV: python -m pip install opencv-python numpy (se usa el mouse)")
            else:
                cam = Camara(indiceCamara)
                if cam.abrir():
                    cam.iniciar()
                    self.camara, self.modo = cam, "camara"
                else:
                    print("No se pudo abrir la cámara (permisos o está en uso). Se usa el mouse.")
        self.cursor, self.abajo = None, False
        self.vistaSup, self.vistaNum = None, -1
        self.rectVista = pygame.Rect(140, 175, 400, 300)
        self.cuenta = None
        self.bloqueo = False
        self.numNivel = 0
        self.estrellas = [0] * len(niveles)
        self.particulas = []
        self.caidos = []
        self.tutorialVisto = False
        self.introVista = False
        self.tIntro = 0.0
        self.tDesvanecer = -10.0
        self.capaIntro = None
        self.finalVisto = False
        self.esFinal = False
        self.terminado = False
        self.pasosTut, self.paso = [], 0
        self.tarjeta = pygame.Rect(0, 0, 640, 250)
        self.estado = "calibrar" if self.modo == "camara" else "dibujar"
        self.cargarNivel(0)
        self.crearBotones()
        if self.estado == "dibujar":
            self.mostrarIntro()

    # niveles y estados
    def cargarNivel(self, i):
        self.numNivel = i
        if i not in self.fondos:
            self.fondos[i] = cargarFondoNivel(i)
        self.fondo = self.fondos[i] or self.fondoBase
        self.hayFoto = self.fondos[i] is not None
        self.nivel = niveles[i]
        self.pts, self.trazos, self.camino = [], [], []
        self.viaPrev = None
        self.tintaUsada = 0.0
        self.trazoActivo = False
        self.espera = 0.0
        self.llegando = False
        self.autoT = 0.0
        self.viaje = None
        self.caminoViaje = []
        self.resultado = None
        self.caidos = []
        self.particulas = []
        self.letreros = []          # "+1" que suben al tomar una moneda
        self.manosHasta = 0.0       # hasta cuándo los pasajeros tienen las manos arriba
        self.pulsoMonedas = 0.0     # brillo del contador de monedas
        self.tResultado = 0.0
        self.siguioFantasma = False
        self.coberturaFantasma = 0.0
        self.estrellasSonadas = 0
        self.corazonesTomados = set()
        self.tRevelacion = 0.0
        self.lineasRevelacion = []
        self.doradasRevelacion = 1

    def crearBotones(self):
        self.botProbar = Boton((30, 618, 200, 62), "Probar", cVerde, self.probar, "flecha")
        self.botDeshacer = Boton((250, 618, 200, 62), "Deshacer", cAmarillo, self.deshacer, "atras")
        self.botBorrar = Boton((470, 618, 200, 62), "Borrar", cCoral, self.borrar, "equis")
        self.botJugar = Boton((ancho // 2 - 110, 520, 220, 70), "Jugar", cVerde, self.empezar, "flecha")
        self.botJugar.habilitado = lambda: self.camara is not None and self.camara.rangos is not None
        self.botRepetir = Boton((0, 0, 210, 54), "Ajustar vía", cAmarillo, self.volverADibujar)
        self.botSiguiente = Boton((0, 0, 210, 54), "Siguiente", cVerde, self.siguienteNivel, "flecha")
        self.botAdelante = Boton((0, 0, 180, 46), "Siguiente", cVerde, self.siguientePaso)
        self.botSaltar = Boton((0, 0, 140, 46), "Saltar", cAmarillo, self.terminarTutorial)

    def botonesAhora(self):
        if self.estado == "calibrar":
            return [self.botJugar]
        if self.estado == "tutorial":
            return [self.botAdelante, self.botSaltar]
        if self.estado == "dibujar":
            return [self.botProbar, self.botDeshacer, self.botBorrar]
        if self.estado == "resultado" and not self.esFinal:
            return [self.botRepetir] +([self.botSiguiente] if self.resultado["gano"] else [])
        return []

    def avisar(self, texto, segs=2.4):
        self.aviso, self.avisoHasta = texto, self.tiempo + segs

    def empezar(self):
        if not self.introVista:
            self.mostrarIntro()
        elif not self.tutorialVisto:
            self.iniciarTutorial()
        else:
            self.estado = "dibujar"

    def mostrarIntro(self):
        self.estado = "intro"
        self.tIntro = self.tiempo
        callarMusica()

    def terminarIntro(self):
        if self.estado == "intro":
            self.tDesvanecer = self.tiempo
            volverMusica()
        self.introVista = True
        if not self.tutorialVisto:
            self.iniciarTutorial()
        else:
            self.estado = "dibujar"

    def volverADibujar(self):
        if self.resultado and self.resultado["gano"]:
            self.cargarNivel(self.numNivel)
        self.estado = "dibujar"
        self.viaje = None
        self.caidos = []
        self.particulas = []
        self.llegando = False
        self.autoT = 0.0

    def siguienteNivel(self):
        self.cargarNivel((self.numNivel + 1) % len(niveles))
        self.estado = "dibujar"

    # tutorial
    def iniciarTutorial(self):
        n = self.nivel
        cam = self.modo == "camara"
        self.pasosTut = [
            ("circulo", n["salida"], 64, "Aquí sale el carro. Tu vía empieza en este punto."),
            ("circulo", n["meta"], 64, "Esta es la meta. Cuando tu línea llegue hasta aquí, los carros salen solos."),
            ("circulo", n["monedas"][0], 40, "Estas son las monedas: son tus metas, no los likes. Pasa la vía por ellas para recogerlas."),
        ]
        corazones = corazonesFantasma(n)
        if corazones:
            self.pasosTut.append(("circulo", corazones[1], 48,
                                  "Esta vía punteada es la del algoritmo: te tienta con corazones, pero los likes "
                                  "no te llevan a la meta. Si la sigues, pierdes."))
        self.pasosTut += [
            ("caja", cajaMonedas, 0, "Aquí ves cuántas monedas llevas y cuántas necesitas para pasar el nivel."),
            ("caja", cajaTinta, 0, "Esta es la tinta. Se va gastando mientras dibujas."),
            ("caja", (20, 608, 664, 80), 0,
             "Aquí abajo están los botones: Probar, Deshacer y Borrar. "
             + ("Para pulsar uno, deja el lápiz encima un momento." if cam else "Para pulsar uno, haz clic.")),
            ("circulo", n["salida"], 46,
             "Para dibujar, lleva el lápiz a este anillo y muévelo hasta la meta." if cam
             else "Para dibujar, mantén el clic desde este anillo hasta la meta."),
        ]
        self.paso = 0
        self.estado = "tutorial"
        self.colocarTutorial()

    def colocarTutorial(self):
        forma, dato, _, _ = self.pasosTut[self.paso]
        cy = dato[1] if forma == "circulo" else dato[1] + dato[3] / 2
        y = 330 if cy < 300 else 100
        self.tarjeta.midtop = (ancho // 2, y)
        # márgenes para no pisar el borde azul de la imagen
        mx, my = self.margenesTarjeta()
        self.botAdelante.caja.bottomright = (self.tarjeta.right - mx, self.tarjeta.bottom - my)
        self.botSaltar.caja.bottomleft = (self.tarjeta.left + mx, self.tarjeta.bottom - my)
        self.botAdelante.etiqueta = "Empezar" if self.paso == len(self.pasosTut) - 1 else "Siguiente"

    def margenesTarjeta(self, w=None, h=None):
        # el borde azul mide más o menos media esquina de la imagen; se suma un respiro adentro
        w, h = w or self.tarjeta.w, h or self.tarjeta.h
        borde = bordeTarjeta(w, h)
        return borde + 22, borde + 16

    def siguientePaso(self):
        self.paso += 1
        if self.paso >= len(self.pasosTut):
            self.terminarTutorial()
        else:
            self.colocarTutorial()

    def terminarTutorial(self):
        self.tutorialVisto = True
        self.estado = "dibujar"

    # edición de la vía
    def puntoAncla(self):
        return self.pts[-1] if self.pts else self.nivel["salida"]

    def refrescar(self):
        self.camino = armarCamino(self.pts)
        self.viaPrev = Via(self.camino) if len(self.camino) >= 5 else None

    def deshacer(self):
        if self.trazos:
            ind = self.trazos.pop()
            del self.pts[ind:]
            if not self.trazos:
                self.pts = []
            self.tintaUsada = sum(math.dist(a, b) for a, b in zip(self.pts, self.pts[1:]))
            self.refrescar()
        self.llegando = False

    def borrar(self):
        self.pts, self.trazos, self.camino, self.tintaUsada = [], [], [], 0.0
        self.viaPrev = None
        self.llegando = False

    def probar(self):
        if len(self.pts) < 2:
            self.avisar("Dibuja la vía primero.")
            return
        crudo = list(self.pts)
        if crudo[-1] != self.nivel["meta"] and math.dist(crudo[-1], self.nivel["meta"]) <= rMeta:
            crudo.append(self.nivel["meta"])         # se pega a la meta sola
        camino = armarCamino(crudo)
        via = Via(camino) if len(camino) >= 5 else None
        if via is None or via.largo < separacion + 30:
            self.avisar("La vía es muy corta.")
            return
        self.caminoViaje = camino
        self.viaje = Recorrido(via, self.nivel)
        self.coberturaFantasma = self.coberturaAlgoritmo(camino)
        self.siguioFantasma = False
        self.corazonesTomados = set()
        self.estado = "viajando"
        self.trazoActivo = False
        self.llegando = False
        self.autoT = 0.0

    def coberturaAlgoritmo(self, camino):
        fantasma = caminoFantasma(self.nivel)
        if len(fantasma) < 5 or len(camino) < 5:
            return 0.0
        muestraFantasma = fantasma[::2]
        muestra = camino[::2]
        cubiertos = 0
        for fx, fy in muestraFantasma:
            for x, y in muestra:
                if (x - fx) ** 2 + (y - fy) ** 2 < 28 * 28:
                    cubiertos += 1
                    break
        return cubiertos / len(muestraFantasma)

    def tocaCorazon(self, corazon):
        r = self.viaje
        for punto, tangente in ((r.posAtras, r.tangAtras), (r.posFrente, r.tangFrente)):
            dx, dy = corazon[0] - punto[0], corazon[1] - punto[1]
            largo = dx * tangente[0] + dy * tangente[1]
            alto = -dx * tangente[1] + dy * tangente[0]
            if abs(largo) < 34 and -48 < alto < 8:
                return True
        return False

    # entrada
    def actualizarEntrada(self, delta):
        if self.modo == "camara":
            meta = self.camara.pos
            if meta is None:
                self.cursor = None
            elif self.cursor is None:
                self.cursor = meta
            else:
                self.cursor = (interpolar(self.cursor[0], meta[0], 0.45), interpolar(self.cursor[1], meta[1], 0.45))
            self.abajo = self.cursor is not None
        else:
            self.cursor = pygame.mouse.get_pos()
            self.abajo = pygame.mouse.get_pressed()[0]

    def actualizarBotones(self, delta):
        if self.modo != "camara":
            return
        lista = self.botonesAhora()
        encima = None
        for b in lista:
            if (self.cursor is not None and b.caja.collidepoint(self.cursor)
                    and b.habilitado() and not self.trazoActivo):
                encima = b
        if encima is None:
            self.bloqueo = False
        for b in lista:
            if b is encima and not self.bloqueo:
                b.sobre += delta
            else:
                b.sobre = max(0.0, b.sobre - delta * 3)
        if encima is not None and encima.sobre >= tBoton:
            for b in lista:
                b.sobre = 0.0
            self.bloqueo = True           # hay que salir del botón para volver a pulsar
            encima.accion()

    def actualizarDibujo(self, delta):
        if self.llegando:
            # ya llegó a la meta: cuenta corta y salen los carros
            self.autoT += delta
            if self.autoT >= tAuto:
                self.llegando = False
                self.probar()
            return
        if not self.abajo or self.cursor is None:
            self.trazoActivo = False
            self.espera = 0.0
            return
        x = limitar(self.cursor[0], 12, ancho - 12)
        y = limitar(self.cursor[1], margenSup + 6, margenInf - 6)
        if not self.trazoActivo:
            if self.tintaUsada >= self.nivel["tinta"]:
                return
            if math.dist((x, y), self.puntoAncla()) < rAncla:
                self.espera += delta
                necesario = tTrazo if self.modo == "camara" else 0.0
                if self.espera >= necesario:
                    if not self.pts:
                        self.pts.append(self.nivel["salida"])
                    self.trazos.append(len(self.pts))
                    self.trazoActivo = True
            else:
                self.espera = 0.0
            return
        if math.dist((x, y), self.nivel["meta"]) < rLlegada:
            self.tintaUsada += math.dist(self.pts[-1], self.nivel["meta"])
            self.pts.append(self.nivel["meta"])
            self.refrescar()
            self.trazoActivo = False
            self.llegando = True
            self.autoT = 0.0
            return
        if math.dist((x, y), self.pts[-1]) >= 4:
            self.tintaUsada += math.dist((x, y), self.pts[-1])
            self.pts.append((x, y))
            self.refrescar()
            if random.random() < 0.3:
                # gotitas que salpica el lápiz al pintar
                self.chispas(x, y, 1, [cAmarillo, cRiel, cCrema], 70, 0.45, 260)
            if self.tintaUsada >= self.nivel["tinta"]:
                self.trazoActivo = False
                self.avisar("Se acabó la tinta.")

    # actualización
    def chispas(self, x, y, n, colores, rapidez=240, vida=0.8, grav=500):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            vel = random.uniform(0.3, 1) * rapidez
            self.particulas.append([x, y, math.cos(a) * vel, math.sin(a) * vel - rapidez * 0.3,
                                    vida * random.uniform(0.6, 1), vida, random.choice(colores),
                                    random.randint(3, 6), grav, random.uniform(0, 50)])

    def colocarResultado(self, gano, conTexto, conReflexion=False):
        alt = 400 if gano else (280 if conTexto else 230)
        if conReflexion:
            alt += 56
        fondo = 330 + alt // 2
        self.altTarjeta = alt
        _, my = self.margenesTarjeta(640, alt)
        for b in (self.botRepetir, self.botSiguiente):
            b.caja.bottom = fondo - my
        if gano:
            self.botRepetir.caja.right = ancho // 2 - 15
            self.botSiguiente.caja.left = ancho // 2 + 15
        else:
            self.botRepetir.caja.centerx = ancho // 2

    def actualizarViaje(self, delta):
        r = self.viaje
        r.avanzar(delta)
        for m in r.nuevas:
            self.chispas(m[0], m[1], 14, [cOro, cOroOsc, cCrema], 180, 0.6, 300)
            self.pulsoMonedas = 1.0
            sonar("obtener.mp3")
            self.letreros.append((m[0], m[1] - 34, self.tiempo, "+1"))
        for i, corazon in enumerate(corazonesFantasma(self.nivel)):
            if i not in self.corazonesTomados and self.tocaCorazon(corazon):
                self.corazonesTomados.add(i)
                if self.coberturaFantasma >= 0.75:
                    sonar("fail.mp3")
                self.chispas(corazon[0], corazon[1], 10, [cCoral, cCoralVivo, cCrema], 160, 0.6, 280)
                self.letreros.append((corazon[0], corazon[1] - 34, self.tiempo, "+1", cCoral))
        if r.estado == "corriendo":
            # en una bajada empinada levantan las manos (y las dejan arriba un momento)
            if max(r.tangAtras[1], r.tangFrente[1]) > 0.35 and r.v > 150:
                self.manosHasta = self.tiempo + 0.5
            # estela de gotitas cuando va rápido
            if abs(r.v) > 380 and random.random() < 0.6:
                x = r.posAtras[0] - r.tangAtras[0] * 30
                y = r.posAtras[1] - r.tangAtras[1] * 30 - 12
                self.chispas(x, y, 1, [cCrema, mezclar(cCrema, cTurquesa, 0.4)], 40, 0.5, -30)
            return
        tomadas = len(r.tomadas)
        total = len(self.nivel["monedas"])
        gano, titulo, texto, estrellas = False, "", "", 0
        llego = r.estado == "listo" and tomadas >= self.nivel["necesarias"]
        self.siguioFantasma = self.coberturaFantasma >= (0.85 if llego else 0.75)
        if r.estado == "listo":
            if tomadas >= self.nivel["necesarias"] and not self.siguioFantasma:
                gano = True
                estrellas = 1 + (tomadas == total) + (self.tintaUsada <= 0.7 * self.nivel["tinta"])
                titulo = "¡Nivel superado!"
                texto = f"Monedas {tomadas}/{total}   ·   Tinta usada {int(100 * self.tintaUsada / self.nivel['tinta'])}%"
                self.estrellas[self.numNivel] = max(self.estrellas[self.numNivel], estrellas)
                mx, my = self.nivel["meta"]
                self.chispas(mx, my - 40, 70, [cOro, cCoral, cTurquesa, cAmarillo, cCrema], 420, 1.4, 600)
            else:
                titulo = "Faltaron monedas"
                texto = f"Monedas {tomadas}/{total}. Necesitas {self.nivel['necesarias']}."
        else:
            titulo = {"descarrilo": "¡Descarriló!", "devuelto": "Se devolvió",
                      "atascado": "Se quedó sin impulso", "corta": "No llegó a la meta"}[r.estado]
            if r.estado in ("descarrilo", "corta"):
                self.caidos = []
                for punto, tg in ((r.posAtras, r.tangAtras), (r.posFrente, r.tangFrente)):
                    self.caidos.append(dict(x=punto[0], y=punto[1], vx=r.v * tg[0], vy=r.v * tg[1] - 80,
                                            ang=math.atan2(tg[1], tg[0]), giro=random.choice((-1, 1)) * 5))
                self.chispas(r.posFrente[0], r.posFrente[1], 30, [cCrema, mezclar(cCrema, cMadera, 0.4), cCoral, cAmarillo], 260, 0.9, 400)
        reflexion = ""
        if self.siguioFantasma:
            gano, estrellas = False, 0
            titulo = "Te llevó el algoritmo"
            cuantos = len(self.corazonesTomados)
            if r.estado == "listo":
                texto = "Llegaste, pero por la vía que él escogió por ti."
            elif cuantos:
                texto = f"Te dio {cuantos} {'corazón' if cuantos == 1 else 'corazones'}, pero no llegaste a tu meta."
            else:
                texto = "Seguiste su vía y no llegaste a tu meta."
            reflexion = reflexionesFantasma[self.numNivel % len(reflexionesFantasma)]
        elif gano:
            reflexion = reflexionesPropias[self.numNivel % len(reflexionesPropias)]
        self.resultado = dict(gano=gano, titulo=titulo, texto=texto, estrellas=estrellas, reflexion=reflexion)
        self.colocarResultado(gano, bool(texto), bool(reflexion) and not self.siguioFantasma)
        self.estado = "resultado"
        self.tResultado = self.tiempo
        self.estrellasSonadas = 0
        if self.siguioFantasma:
            self.estado = "revelacion"
            self.tRevelacion = self.tiempo
            self.lineasRevelacion = self.lineasEscritas(reflexion)
            self.doradasRevelacion = self.lineasDoradas(reflexion)
        elif gano and self.numNivel == len(niveles) - 1 and not self.finalVisto:
            self.finalVisto = True
            self.esFinal = True
            self.altTarjeta -= 70
        self.botRepetir.etiqueta = "Repetir" if gano else "Ajustar vía"
        self.botRepetir.icono = "atras" if gano else None      # mismo símbolo que deshacer
        self.botSiguiente.etiqueta = "Siguiente" if self.numNivel < len(niveles) - 1 else "Volver al mapa"

    def actualizar(self, delta):
        self.tiempo += delta
        self.actualizarEntrada(delta)
        if self.cuenta is not None:
            self.cuenta -= delta
            if self.cuenta <= 0:
                self.cuenta = None
                self.camara.pedido = (0.5, 0.5)
        if self.estado == "dibujar":
            self.actualizarDibujo(delta)
        elif self.estado == "viajando":
            self.actualizarViaje(delta)
        elif self.estado == "revelacion":
            if self.tiempo - self.tRevelacion >= self.horarioEscritura(self.lineasRevelacion)[-1] + 3.0:
                self.pasarAlResultado()
        elif self.estado == "intro" and self.tiempo - self.tIntro >= duracionIntro:
            self.terminarIntro()
        elif self.estado == "resultado" and self.resultado and self.resultado["gano"]:
            llenas = sum(1 for i in range(self.resultado["estrellas"]) if self.tiempo - self.tResultado >= 0.9 + i * 0.6)
            while self.estrellasSonadas < llenas:
                self.estrellasSonadas += 1
                sonar("obtener.mp3")
            if self.esFinal and self.tiempo - self.tResultado >= 4.5:
                self.estado = "revelacion"
                self.tRevelacion = self.tiempo
                self.lineasRevelacion = self.lineasEscritas(reflexionFinal)
                self.doradasRevelacion = self.lineasDoradas(reflexionFinal)
        if self.estado == "intro":
            sonarEscritura(self.escribiendo(self.lineasEscritas(mensajeAlgoritmo), self.tiempo - self.tIntro))
        elif self.estado == "revelacion":
            sonarEscritura(self.escribiendo(self.lineasRevelacion, self.tiempo - self.tRevelacion))
        else:
            sonarEscritura(False)
        self.actualizarBotones(delta)
        for cd in self.caidos:
            cd["vy"] += gravedad * delta
            cd["x"] += cd["vx"] * delta
            cd["y"] += cd["vy"] * delta
            cd["ang"] += cd["giro"] * delta
            if cd["y"] > ySuelo - 6:
                cd["y"], cd["vy"], cd["vx"], cd["giro"] = ySuelo - 6, 0, cd["vx"] * 0.6, cd["giro"] * 0.5
        for p in self.particulas:
            p[0] += p[2] * delta
            p[1] += p[3] * delta
            p[3] += p[8] * delta
            p[4] -= delta
        self.particulas = [p for p in self.particulas if p[4] > 0]
        self.pulsoMonedas = max(0.0, self.pulsoMonedas - delta * 1.6)
        self.letreros = [letrero for letrero in self.letreros if self.tiempo - letrero[2] < 1.0]

    # dibujo
    def texto(self, s, tam, color, punto, alinear="topleft", sombra=False):
        sup = self.fuentes[tam].render(s, True, color)
        r = sup.get_rect()
        setattr(r, alinear, punto)
        if sombra:
            self.pantalla.blit(self.fuentes[tam].render(s, True, cOscuro), r.move(2, 2))
        self.pantalla.blit(sup, r)

    def titulo(self, s, tam, color, punto, alinear="topleft"):
        sup = self.fuentesTitulo[tam].render(s, True, color)
        r = sup.get_rect()
        setattr(r, alinear, punto)
        self.pantalla.blit(sup, r)

    def tituloEscalado(self, s, tam, color, centro, escala=1.0):
        sup = self.fuentesTitulo[tam].render(s, True, color)
        if abs(escala - 1) > 0.01:
            sup = pygame.transform.smoothscale_by(sup, escala)
        self.pantalla.blit(sup, sup.get_rect(center=centro))

    def textoEscalado(self, s, tam, color, centro, escala=1.0, alfa=255):
        sup = self.fuentes[tam].render(s, True, color)
        if abs(escala - 1) > 0.01:
            sup = pygame.transform.smoothscale_by(sup, escala)
        if alfa < 255:
            sup.set_alpha(int(alfa))
        self.pantalla.blit(sup, sup.get_rect(center=centro))

    def superficieCamara(self):
        num, datos = self.camara.obtenerVista()
        if datos and num != self.vistaNum:
            self.vistaNum = num
            self.vistaSup = pygame.image.frombuffer(datos, tamVista, "RGB").convert()
        return self.vistaSup

    def posReposo(self):
        sx, sy = self.nivel["salida"]
        if self.viaPrev is not None and self.viaPrev.largo > separacion:
            pa, ta, _ = self.viaPrev.puntoEn(0)
            pf, tf, _ = self.viaPrev.puntoEn(separacion)
            return pa, pf, math.atan2(ta[1], ta[0]), math.atan2(tf[1], tf[0])
        return (sx - separacion, sy), (sx, sy), 0.0, 0.0

    def dibujarMundo(self):
        s = self.pantalla
        s.blit(self.fondo, (0, 0))
        if self.hayFoto and self.nivel.get("rueda"):
            dibujarRueda(s, self.nivel, self.tiempo)
        if not self.hayFoto:
            dibujarNubes(s, self.tiempo)
            dibujarNoria(s, self.tiempo)
        hora = self.nivel.get("hora", "dia")
        salida, meta = self.nivel["salida"], self.nivel["meta"]

        def pintarEstacion(capa):
            dibujarEstacion(capa, salida)
            entonar(capa, hora)

        dibujarGuardado(s, "estacion", (salida, hora), pintarEstacion)
        cajaBandera = pygame.Rect(meta[0] - 45, meta[1] - 100, 110, margenInf + 110 - meta[1])
        dibujarEntonado(s, cajaBandera, hora, lambda capa: dibujarBandera(capa, meta, self.tiempo))
        enMarcha = self.viaje is not None and self.estado in ("viajando", "resultado")
        camino = self.caminoViaje if enMarcha else self.camino
        fantasma = caminoFantasma(self.nivel)
        dibujarViaFantasma(s, fantasma, hora)

        def pintarVia(capa):
            dibujarVia(capa, camino)
            entonar(capa, hora)
            if hora == "noche" and len(camino) > 1:
                # reflejo claro de la luz sobre el riel para que no se pierda en la oscuridad
                reflejo = [(x, y - 2.5) for x, y in camino]
                pygame.draw.aalines(capa, mezclar(cCrema, cAmarillo, 0.35), False, reflejo)
                pygame.draw.aalines(capa, mezclar(cCrema, cAmarillo, 0.35), False, [(x, y + 0.6) for x, y in reflejo])

        dibujarGuardado(s, "via", (id(camino), len(camino), hora), pintarVia)
        if hora in tonos:
            self.dibujarLuces(camino, hora)
        for i, corazon in enumerate(corazonesFantasma(self.nivel)):
            if not (enMarcha and i in self.corazonesTomados):
                dibujarCorazon(s, corazon, 30, self.tiempo, i)
        if self.estado in ("dibujar", "tutorial"):
            dibujarPulsoFantasma(s, fantasma, self.tiempo)
        if self.estado == "dibujar":
            self.dibujarSugerido(fantasma)
        tomadas = self.viaje.tomadas if self.viaje else set()
        for i, m in enumerate(self.nivel["monedas"]):
            if i in tomadas:
                continue
            # la moneda flota un poco y de vez en cuando le sale un destello
            pos = (m[0], m[1] + math.sin(self.tiempo * 2.2 + i * 1.3) * 3)
            if hora in tonos:
                pegarBrillo(s, pos, cOro, 30, 0.55)
            dibujarMoneda(s, pos, self.tiempo, i)
            destello = math.sin(self.tiempo * 3 + i * 2.1)
            if destello > 0.4:
                tam = (destello - 0.4) / 0.6 * 8
                lavado(s, puntosEstrella((pos[0] + 13, pos[1] - 12), tam, 0.28, 4), cCrema, 235, 0.15)
        self.dibujarCarros(enMarcha, hora)
        for p in self.particulas:
            # gotas de pintura que se van aclarando al desaparecer
            vida = limitar(p[4] / p[5], 0, 1)
            gota = puntosCirculo((p[0], p[1]), p[7] // 2 + 2, 7, 0.3, p[9])
            lavado(s, gota, p[6], int(70 + 170 * vida), 0.35)
        for letrero in self.letreros:
            x, y, t0, txt = letrero[:4]
            colorLetrero = letrero[4] if len(letrero) > 4 else cOro
            # "+1" que salta, sube y se desvanece
            e = self.tiempo - t0
            y -= 46 * (1 - (1 - min(e / 0.8, 1)) ** 3)
            alfa = 255 if e < 0.6 else max(0, 255 * (1 - (e - 0.6) / 0.4))
            escala = 1 + 0.5 * max(0.0, 1 - e / 0.18)
            lavado(s, puntosCirculo((x, y), 19 * escala, 12, 0.2, x), colorLetrero, int(alfa * 0.85), 0.3)
            self.textoEscalado(txt, 20, cOscuro, (x, y - 2), escala, alfa)

    def dibujarSugerido(self, fantasma):
        corazones = corazonesFantasma(self.nivel)
        if not corazones:
            return
        letrero = "Sugerido para ti"
        w = self.fuentes[14].size(letrero)[0] + 26
        caja = self.cajaSugerido(corazones, w)
        panel(self.pantalla, caja, mezclar(cFantasma, cCrema, 0.15), mezclar(cFantasma, cOscuro, 0.45), 10, 2)
        self.texto(letrero, 14, cCrema, caja.center, "center")

    def cajaSugerido(self, corazones, w):
        sx, sy = self.nivel["salida"]
        inicio = (sx + 116, sy - 1)
        estorbos = [pygame.Rect(0, 0, 64, 64).move(m[0] - 32, m[1] - 32) for m in self.nivel["monedas"]]
        estorbos += [pygame.Rect(0, 0, 40, 40).move(c[0] - 20, c[1] - 20) for c in corazones]
        opciones = []
        for x, y in corazones:
            for dy in (-62, 32):
                caja = pygame.Rect(int(x - w / 2), int(y + dy), w, 30)
                lejos = math.dist(caja.center, inicio) >= 220
                libre = caja.collidelist(estorbos) < 0 and caja.top > margenSup + 10 and caja.bottom < margenInf - 10
                opciones.append((not (lejos and libre), not lejos, caja))
        return min(opciones, key=lambda o: o[:2])[2]

    def dibujarCarros(self, enMarcha, hora):
        s = self.pantalla
        if self.caidos:
            puntos = [(cd["x"], cd["y"]) for cd in self.caidos]

            def pintar(capa):
                for numero, cd in enumerate(self.caidos, 1):
                    dibujarCarro(capa, (cd["x"], cd["y"]), cd["ang"], 0, numero)
        else:
            if enMarcha:
                r = self.viaje
                pa, pf = r.posAtras, r.posFrente
                aa = math.atan2(r.tangAtras[1], r.tangAtras[0])
                af = math.atan2(r.tangFrente[1], r.tangFrente[0])
                emo = limitar(r.fuerzaG / (aMax / gravedad), 0, 1) if self.estado == "viajando" else 0
            else:
                pa, pf, aa, af = self.posReposo()
                emo = 0
            puntos = [pa, pf]

            def pintar(capa):
                dibujarEnganche(capa, pa, pf)
                manos = self.estado == "viajando" and self.tiempo < self.manosHasta
                dibujarCarro(capa, pa, aa, emo, 1, manos)
                dibujarCarro(capa, pf, af, emo, 2, manos)
        xs, ys = [p[0] for p in puntos], [p[1] for p in puntos]
        caja = pygame.Rect(min(xs) - 70, min(ys) - 80, max(xs) - min(xs) + 140, max(ys) - min(ys) + 130)
        if hora == "noche":
            # luz suave detrás de los carros para que resalten sobre el cielo oscuro
            for p in puntos:
                pegarBrillo(s, (p[0], p[1] - 16), cCrema, 56, 0.45)
        dibujarEntonado(s, caja, hora, pintar)
        if hora in tonos and not self.caidos:
            # farol del carro de adelante
            luz = (pf[0] + math.cos(af) * 38, pf[1] + math.sin(af) * 38 - 10)
            pegarBrillo(s, luz, cAmarillo, 26, 0.75)

    def dibujarLuces(self, camino, hora):
        # faroles de la estación, luz en la bandera y focos de colores a lo largo de la vía
        s = self.pantalla
        fuerza = 0.8 if hora == "tarde" else 1.0
        x, y = self.nivel["salida"]
        for px in (x - separacion - 52, x + 8):
            pegarBrillo(s, (px, y - 62), cAmarillo, 30, fuerza * (0.8 + 0.2 * math.sin(self.tiempo * 5 + px)))
            pygame.draw.aacircle(s, mezclar(cAmarillo, cCrema, 0.5), (px, y - 62), 4)
        mx, my = self.nivel["meta"]
        pegarBrillo(s, (mx, my - 83), cOro, 26, fuerza)
        # los focos se prenden más fuerte cuando pasa el carro
        sCarro = self.viaje.s + separacion / 2 if self.viaje and self.estado == "viajando" else None
        colores = (cAmarillo, cCoral, cTurquesa, cOro)
        for n, i in enumerate(range(6, len(camino) - 3, 12)):
            (x0, y0), (x1, y1) = camino[i - 1], camino[i + 1]
            d = math.dist((x0, y0), (x1, y1)) or 1.0
            px = camino[i][0] - (y1 - y0) / d * 11
            py = camino[i][1] + (x1 - x0) / d * 11
            luz = 0.55 + 0.25 * math.sin(self.tiempo * 4 + n * 1.7)
            if sCarro is not None:
                luz += 0.8 * math.exp(-((i * paso - sCarro) / 110) ** 2)
            color = colores[n % 4]
            pegarBrillo(s, (px, py), color, 24, fuerza * luz)
            pygame.draw.aacircle(s, mezclar(color, cCrema, 0.55), (px, py), 4)
            pygame.draw.aacircle(s, cOscuro, (px, py), 4.5, 1)

    def dibujarAncla(self):
        if self.estado != "dibujar":
            return
        mx, my = int(self.nivel["meta"][0]), int(self.nivel["meta"][1])
        s = self.pantalla
        if self.llegando:
            # arco que se va pintando de verde alrededor de la meta
            lavado(s, puntosCirculo((mx, my), 46, 24, 0.05, 7.0), cCrema, 150, 0.15)
            circuloMano(s, (mx, my), 40, cCrema, 6, 0.8, 7.0)
            arcoMano(s, (mx, my), 40, limitar(self.autoT / tAuto, 0, 1), cVerde, 8, 7.0)
            circuloMano(s, (mx, my), 45, cOscuro, 2, 0.8, 8.0)
            circuloMano(s, (mx, my), 35, cOscuro, 1, 0.8, 9.0)
            return
        pulso = 4 * math.sin(self.tiempo * 6)
        anilloPintado(s, (mx, my), rLlegada * 0.7 + pulso, cCoralVivo, 3.0)
        if self.trazoActivo or self.tintaUsada >= self.nivel["tinta"]:
            return
        ax, ay = self.puntoAncla()
        anilloPintado(s, (ax, ay), rAncla * 0.55 + pulso, cVerdeVivo, 5.0)
        if self.espera > 0 and self.modo == "camara":
            frac = limitar(self.espera / tTrazo, 0, 1)
            arcoMano(s, (ax, ay), 35, frac, cAmarillo, 7, 6.0)
            arcoMano(s, (ax, ay), 39, frac, cOscuro, 2, 6.5)
        if not self.pts:
            # letrero en un papelito para que se lea sobre cualquier foto
            w = self.fuentes[16].size("Empieza aquí")[0] + 24
            panel(s, pygame.Rect(ax + 50, ay - 18, w, 34), cCrema, cOscuro, 10, 2)
            self.texto("Empieza aquí", 16, cOscuro, (ax + 50 + w // 2, ay - 2), "center")

    def dibujarHud(self):
        s = self.pantalla
        brilloM = self.pulsoMonedas
        if brilloM > 0:
            # el contador se ilumina de dorado al tomar una moneda
            luz = pygame.transform.smoothscale(brillo(cOro, 40), (cajaMonedas.w + 70, cajaMonedas.h + 70))
            luz.set_alpha(int(255 * brilloM))
            s.blit(luz, (cajaMonedas.x - 35, cajaMonedas.y - 35))
        for caja in (cajaNivel, cajaMonedas, cajaTinta):
            cajaPintada(s, caja)
        self.titulo(f"Nivel {self.numNivel + 1}/{len(niveles)}", 18, cOscuro, cajaNivel.center, "center")
        tomadas = len(self.viaje.tomadas) if self.viaje else 0
        cy = cajaMonedas.centery
        dibujarMoneda(s, (cajaMonedas.x + 28, cy), brilloM * 4, 0, 22)
        self.tituloEscalado(f"{tomadas}/{len(self.nivel['monedas'])}", 24, cOscuro,
                            (cajaMonedas.x + 80, cy), 1 + 0.3 * brilloM)
        self.titulo(f"necesitas {self.nivel['necesarias']}", 13, cMaderaOsc, (cajaMonedas.x + 118, cy), "midleft")
        resto = limitar(1 - self.tintaUsada / self.nivel["tinta"], 0, 1)
        self.titulo("Tinta", 16, cMaderaOsc, (cajaTinta.x + 14, cajaTinta.centery), "midleft")
        barra = pygame.Rect(cajaTinta.x + 72, cajaTinta.centery - 8, 184, 16)
        # barra de tinta pintada: fondo de papel y una mancha que se acorta al gastar
        # turquesa cuando está llena, amarillo a la mitad y coral cuando se acaba
        if resto > 0.5:
            color = mezclar(cAmarillo, cTurquesa, (resto - 0.5) * 2)
        else:
            color = mezclar(cCoral, cAmarillo, resto * 2)
        dibujarBarraTinta(s, barra, resto, color)

    def dibujarBase(self):
        s = self.pantalla
        hora = self.nivel.get("hora", "dia")
        if ("barra", hora) not in almacen:
            # la madera de abajo también cambia con la hora
            barra = self.barra.copy()
            entonar(barra, hora)
            almacen[("barra", hora)] = barra
        s.blit(almacen[("barra", hora)], (0, margenInf))
        if self.estado in ("dibujar", "tutorial"):
            for b in (self.botProbar, self.botDeshacer, self.botBorrar):
                b.dibujar(s, self.fuentesTitulo[20])
        if self.camara is not None and self.estado in ("dibujar", "viajando", "resultado", "tutorial"):
            vista = self.superficieCamara()
            if vista:
                # foto pegada sobre un papelito, con un velo crema para que no desentone
                caja = pygame.Rect(ancho - 146, 612, 120, 78)
                hayMarco = cargarMarco() is not None
                if not hayMarco:
                    panel(s, caja.inflate(12, 12), cCrema, cOscuro, 6, 2)
                s.blit(pygame.transform.smoothscale(vista, caja.size), caja)
                velo = pygame.Surface(caja.size, pygame.SRCALPHA)
                velo.fill((*cCrema, 45))
                s.blit(velo, caja)
                if hayMarco:
                    dibujarMarcoCamara(s, caja, 9)
                else:
                    trazoMano(s, contornoCaja(caja, 3), cOscuro, 2, 0.6, 2.0, True)

    def dibujarCursor(self):
        if self.cursor is None or self.estado == "viajando":
            return
        p = (int(self.cursor[0]), int(self.cursor[1]))
        if self.modo == "raton" and not self.abajo:
            punto = puntoNitido(cCrema, 6)
            self.pantalla.blit(punto, punto.get_rect(center=p))
            return
        punto = puntoNitido(cAmarillo if self.trazoActivo else cCrema, 9)
        self.pantalla.blit(punto, punto.get_rect(center=p))
        dibujarLapiz(self.pantalla, p, cAmarillo)

    def dibujarFuegos(self, tarjeta):
        # una estrella: fuegos a la izquierda; dos: también a la derecha; tres: también el felicidades arriba.
        # En cada lado el primero estalla cuando se llena su estrella y los otros dos van después
        s = self.pantalla
        izq, der = tarjeta.left - 115, tarjeta.right + 115
        lados = (
            ((izq, tarjeta.centery - 20, "circulo", 90, "dorado"),
             (izq + 10, tarjeta.top + 30, "corazon", 72, "rojo"),
             (izq - 10, tarjeta.bottom - 40, "k", 62, "azul")),
            ((der, tarjeta.centery - 20, "circulo", 90, "turquesa"),
             (der - 10, tarjeta.top + 30, "k", 62, "morado"),
             (der + 10, tarjeta.bottom - 40, "corazon", 72, "rojo")),
        )
        for i in range(min(2, self.resultado["estrellas"])):
            for j, (x, y, forma, escala, paleta) in enumerate(lados[i]):
                ciclo = cicloFuego + j * 0.4          # cada uno a su ritmo para que no salgan siempre juntos
                ef = self.tiempo - self.tResultado - (0.45 + i * 0.6) - j * 0.75
                if ef > 0:
                    # en cada vuelta sale un poco corrido y de otro tamaño
                    vuelta = int(ef // ciclo)
                    semilla = i * 10 + j
                    lugar = (x + temblorFijo(vuelta, semilla) * 25, y + temblorFijo(vuelta, semilla + 0.5) * 35)
                    tam = escala * (0.97 + 0.18 * temblorFijo(vuelta, semilla + 0.9))
                    dibujarFuego(s, lugar, puntosFigura(forma), tam, ef % ciclo, paletaVuelta(paleta, vuelta),
                                 detalle=forma != "k", chispitas=forma == "circulo")
                    sonarFuego(("coaster", i, j), ef % ciclo)
        if self.resultado["estrellas"] < 3:
            return
        # arriba se turnan: primero el felicidades solo (siempre amarillo) y en la siguiente vuelta un fuego redondo
        ef = self.tiempo - self.tResultado - 1.65
        if ef > 0:
            arriba = (tarjeta.centerx, tarjeta.top - 62)
            vuelta = int(ef // cicloFuego)
            sonarFuego(("coaster", "arriba"), ef % cicloFuego)
            if vuelta % 2 == 0:
                dibujarFuego(s, arriba, puntosTexto("¡Felicidades!", self.fuentes[54]), 1, ef % cicloFuego,
                             paletasFuego["dorado"], 2.4, 3)
            else:
                # el redondo de arriba tiene espacio a los lados, así que se corre más
                lugar = (arriba[0] + temblorFijo(vuelta, 30) * 150, arriba[1] + temblorFijo(vuelta, 30.5) * 10)
                tam = 62 * (0.97 + 0.13 * temblorFijo(vuelta, 30.9))
                dibujarFuego(s, lugar, puntosFigura("circulo"), tam, ef % cicloFuego, paletaVuelta("rojo", vuelta // 2),
                             detalle=True, chispitas=True)

    def dibujarResultado(self):
        s = self.pantalla
        velo = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        velo.fill((50, 36, 30, 115))
        s.blit(velo, (0, 0))
        tarjeta = pygame.Rect(0, 0, 640, self.altTarjeta)
        tarjeta.center = (ancho // 2, 330)
        if self.resultado["gano"]:
            self.dibujarFuegos(tarjeta)
        tarjetaPintada(s, tarjeta)
        res = self.resultado
        e = self.tiempo - self.tResultado
        # título, texto y estrellas quedan centrados entre el borde de arriba y los botones
        arriba = tarjeta.top + bordeTarjeta(tarjeta.w, tarjeta.h)
        abajo = self.botRepetir.caja.top - 6
        if self.esFinal:
            abajo = tarjeta.bottom - bordeTarjeta(tarjeta.w, tarjeta.h)
        lineasReflexion = []
        if res.get("reflexion") and not self.siguioFantasma:
            lineasReflexion = partirTexto(res["reflexion"], self.fuentes[20], tarjeta.w - 150)
        altoBloque = 50 + (40 if res["texto"] else 0) + (78 if res["gano"] else 0) + 28 * len(lineasReflexion)
        y = (arriba + abajo - altoBloque) / 2
        self.titulo(res["titulo"], 36, cOscuro, (tarjeta.centerx, y + 25), "center")
        y += 58
        if res["texto"]:
            self.texto(res["texto"], 16, cOscuro, (tarjeta.centerx, y), "midtop")
            y += 40
        for linea in lineasReflexion:
            self.texto(linea, 20, mezclar(cFantasma, cOscuro, 0.35) if self.siguioFantasma else cMaderaOsc,
                       (tarjeta.centerx, y), "midtop")
            y += 28
        if res["gano"]:
            cy = y + 34
            for i in range(3):
                cx = tarjeta.centerx + (i - 1) * 76
                hueco = puntosEstrella((cx, cy), 26)
                ti = e - (0.35 + i * 0.6)          # cada estrella empieza a llenarse después de la anterior
                gano = i < res["estrellas"] and ti > 0
                lleno = 1 - (1 - min(1.0, ti / 0.55)) ** 2 if gano else 0
                if lleno >= 1:
                    # brilla fuerte al llenarse y queda con un brillo suave que respira
                    pegarBrillo(s, (cx, cy), cOro, 50, 0.45 + 0.5 * max(0.0, 1 - (ti - 0.55) / 0.6)
                                + 0.08 * math.sin(self.tiempo * 3 + i))
                imagenes = cargarEstrellas()
                if imagenes:
                    # estrellas traídas de afuera: primero la vacía y encima la llena que se va revelando
                    vacia = imagenEstrella(imagenes[1], 26)
                    s.blit(vacia, vacia.get_rect(center=(cx, cy)))
                    if lleno > 0:
                        estrellaLlena(s, (cx, cy), 26, lleno, self.tiempo, imagenes[0])
                else:
                    lavado(s, hueco, (214, 204, 184), 240)
                    if lleno > 0:
                        estrellaLlena(s, (cx, cy), 26, lleno, self.tiempo)
                    perfil(s, hueco, cOscuro, 3 if lleno >= 1 else 2, 0.6, i)
                if lleno >= 1 and ti - 0.55 < 0.7:
                    # destello crema en la punta cuando termina de llenarse
                    f = (ti - 0.55) / 0.7
                    tam = 11 * math.sin(f * math.pi)
                    if tam > 0.5:
                        lavado(s, puntosEstrella((cx + 10, cy - 14), tam, 0.25, 4), cCrema, 240, 0.1)
        for b in self.botonesAhora():
            b.dibujar(s, self.fuentesTitulo[20])

    def lineasEscritas(self, frases):
        lineas = []
        for frase in frases:
            lineas += partirTexto(frase, self.fuentes[36], ancho - 200)
        return lineas

    def lineasDoradas(self, frases):
        return len(partirTexto(frases[-1], self.fuentes[36], ancho - 200))

    def horarioEscritura(self, lineas):
        horario = []
        momento = 0.5
        for linea in lineas:
            horario.append(momento)
            momento += len(linea) / 24.0 + 0.45
        horario.append(momento)
        return horario

    def textoBordeado(self, texto, color):
        fuente = self.fuentes[36]
        cuerpo = fuente.render(texto, True, color)
        borde = fuente.render(texto, True, (60, 50, 70))
        lienzo = pygame.Surface((cuerpo.get_width() + 6, cuerpo.get_height() + 6), pygame.SRCALPHA)
        for grados in range(0, 360, 30):
            lienzo.blit(borde, (3 + round(math.cos(math.radians(grados)) * 3), 3 + round(math.sin(math.radians(grados)) * 3)))
        lienzo.blit(cuerpo, (3, 3))
        return lienzo

    def escribiendo(self, lineas, t):
        horario = self.horarioEscritura(lineas)
        return any(horario[i] <= t < horario[i] + len(linea) / 24.0 for i, linea in enumerate(lineas))

    def dibujarEscritura(self, lineas, t, centroY=330, sup=None, doradas=1):
        s = sup or self.pantalla
        # La pantalla queda negra desde el primer cuadro; el parpadeo inicial solo oculta las letras
        # (antes se saltaba el relleno y se alcanzaba a ver el juego detrás).
        s.fill((8, 6, 12))
        if t < 0.3 and int(t * 20) % 2 == 0:
            return
        horario = self.horarioEscritura(lineas)
        altoLinea = self.fuentes[36].get_linesize() + 16
        y = centroY - altoLinea * len(lineas) // 2
        for i, linea in enumerate(lineas):
            letras = min(len(linea), int(max(0.0, t - horario[i]) * 24))
            if letras > 0:
                color = cOro if i >= len(lineas) - doradas else (255, 247, 230)
                texto = self.textoBordeado(linea[:letras], color)
                izquierda = ancho // 2 - self.fuentes[36].size(linea)[0] // 2
                s.blit(texto, texto.get_rect(midleft=(izquierda, y + altoLinea // 2)))
            y += altoLinea

    def introLista(self):
        lineas = self.lineasEscritas(mensajeAlgoritmo)
        return self.tiempo - self.tIntro >= self.horarioEscritura(lineas)[-1]

    def dibujarIntro(self):
        lineas = self.lineasEscritas(mensajeAlgoritmo)
        self.dibujarEscritura(lineas, self.tiempo - self.tIntro, 330, doradas=self.lineasDoradas(mensajeAlgoritmo))

    def dibujarDesvanecer(self):
        e = self.tiempo - self.tDesvanecer
        if e >= duracionDesvanecer or e < 0:
            self.capaIntro = None
            return
        if self.capaIntro is None:
            self.capaIntro = pygame.Surface((ancho, alto))
            self.dibujarEscritura(self.lineasEscritas(mensajeAlgoritmo), duracionIntro, 330, self.capaIntro,
                                  self.lineasDoradas(mensajeAlgoritmo))
        avance = e / duracionDesvanecer
        self.capaIntro.set_alpha(int(255 * (1 - avance * avance * (3 - 2 * avance))))
        self.pantalla.blit(self.capaIntro, (0, 0))

    def revelacionLista(self):
        return self.tiempo - self.tRevelacion >= self.horarioEscritura(self.lineasRevelacion)[-1]

    def pasarAlResultado(self):
        if self.estado != "revelacion":
            return
        if self.esFinal:
            self.terminado = True
            return
        self.estado = "resultado"
        self.tResultado = self.tiempo
        self.estrellasSonadas = 0

    def dibujarRevelacion(self):
        t = self.tiempo - self.tRevelacion
        altoLinea = self.fuentes[36].get_linesize() + 16
        centroY = max(265, 24 + altoLinea * len(self.lineasRevelacion) // 2)
        self.dibujarEscritura(self.lineasRevelacion, t, centroY, doradas=self.doradasRevelacion)
        if self.revelacionLista():
            aparece = min(1.0, (t - self.horarioEscritura(self.lineasRevelacion)[-1]) / 0.5)
            abajo = centroY + altoLinea * len(self.lineasRevelacion) // 2
            self.textoEscalado("Clic o espacio para seguir", 16, mezclar(cCrema, cMadera, 0.4),
                               (ancho // 2, min(alto - 24, max(500, abajo + 26))), 1.0, 255 * aparece)

    def dibujarTutorial(self):
        s = self.pantalla
        forma, dato, tam, texto = self.pasosTut[self.paso]
        capa = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        capa.fill((50, 36, 30, 150))
        if forma == "circulo":
            pygame.draw.circle(capa, (0, 0, 0, 0), (int(dato[0]), int(dato[1])), tam)
        else:
            pygame.draw.rect(capa, (0, 0, 0, 0), dato, border_radius=14)
        s.blit(capa, (0, 0))
        pulso = 3 * math.sin(self.tiempo * 6)
        # resaltado a mano: trazo crema grueso y una línea de tinta por fuera
        if forma == "circulo":
            circuloMano(s, dato, tam + pulso, cCrema, 4, 1.0, self.paso)
            circuloMano(s, dato, tam + pulso + 5, cOscuro, 2, 1.0, self.paso + 0.5)
        else:
            marco = pygame.Rect(dato).inflate(int(pulso * 2) + 6, int(pulso * 2) + 6)
            trazoMano(s, contornoCaja(marco, 16), cCrema, 4, 1.0, self.paso, True)
            trazoMano(s, contornoCaja(marco.inflate(10, 10), 20), cOscuro, 2, 1.0, self.paso + 0.5, True)
        tarjetaPintada(s, self.tarjeta)
        mx, my = self.margenesTarjeta()
        anchoTexto = self.tarjeta.w - 2 * mx - 90
        for i, linea in enumerate(partirTexto(texto, self.fuentes[20], anchoTexto)[:3]):
            self.texto(linea, 20, cOscuro, (self.tarjeta.x + mx, self.tarjeta.y + my + 6 + i * 30))
        # número del paso en una pastilla azul
        insignia = pygame.Rect(0, 0, 76, 40)
        insignia.topright = (self.tarjeta.right - mx + 8, self.tarjeta.y + my - 4)
        s.blit(pastillaNitida(insignia.w, insignia.h, cAzul), (insignia.x - 2, insignia.y - 2))
        self.texto(f"{self.paso + 1}/{len(self.pasosTut)}", 20, cOscuro, (insignia.centerx, insignia.centery + 1), "center")
        # puntitos de progreso entre los dos botones: azul el actual, café los ya vistos
        total = len(self.pasosTut)
        cy = self.botSaltar.caja.centery
        x0 = (self.botSaltar.caja.right + self.botAdelante.caja.left) / 2 - (total - 1) * 9
        for i in range(total):
            if i == self.paso:
                punto = puntoNitido(cAzulOsc, 7)
            else:
                punto = puntoNitido(cMaderaOsc if i < self.paso else cCrema, 4)
            s.blit(punto, punto.get_rect(center=(round(x0 + i * 18), cy)))
        for b in self.botonesAhora():
            b.dibujar(s, self.fuentesTitulo[20])

    def dibujarCalibracion(self):
        s = self.pantalla
        s.blit(self.fondoBase, (0, 0))
        dibujarNubes(s, self.tiempo)
        tarjetaPintada(s, pygame.Rect(10, 20, 1080, 660))
        self.titulo("Calibra tu lápiz", 36, cOscuro, (self.rectVista.x, 100))
        # la cámara va dentro de elementos/marcoCamara; si no hay imagen, sobre un papelito con contorno de tinta
        hayMarco = cargarMarco() is not None
        if not hayMarco:
            panel(s, self.rectVista.inflate(24, 24), cCrema, cOscuro, 22, 3)
        vista = self.superficieCamara()
        if vista:
            if vista.get_size() != self.rectVista.size:
                vista = pygame.transform.smoothscale(vista, self.rectVista.size)
            # con el marco va recta, así sus esquinas tapan las de la cámara sin dejar huecos
            s.blit(vista if hayMarco else redondear(vista, 14), self.rectVista)
        else:
            lavado(s, contornoCaja(self.rectVista, 14), mezclar(cCrema, cMadera, 0.3), 255, 0.1)
        if hayMarco:
            dibujarMarcoCamara(s, self.rectVista, 20)
        else:
            trazoMano(s, contornoCaja(self.rectVista, 14), cOscuro, 3, 0.6, 1.0, True)
        c = self.rectVista.center
        circuloMano(s, c, 26, cCrema, 4, 0.8, 1.0)
        circuloMano(s, c, 30, cOscuro, 2, 0.8, 2.0)
        frase = "Ubica el objeto en el círculo y pulsa espacio en el teclado para calibrar."
        for i, linea in enumerate(partirTexto(frase, self.fuentes[26], 400)):
            self.texto(linea, 26, cOscuro, (590, 165 + i * 38))
        if self.cuenta is not None:
            self.texto(str(int(self.cuenta) + 1), 54, cCoral, (self.rectVista.centerx, self.rectVista.top + 20), "midtop", True)
        if self.camara.rangos is None:
            estado, color = "Sin calibrar", cCoral
        elif self.camara.pos is not None:
            estado, color = "Lápiz detectado", cVerde
        else:
            estado, color = "Calibrado, no veo el objeto", cAmarillo
        self.texto(estado, 26, color, (590, 350))
        frase = "Para jugar, deja el lápiz sobre el botón jugar o pulsa enter en el teclado."
        for i, linea in enumerate(partirTexto(frase, self.fuentes[20], 400)):
            self.texto(linea, 20, cMaderaOsc, (590, 410 + i * 30))
        self.botJugar.dibujar(s, self.fuentesTitulo[20])

    def dibujar(self):
        if self.estado == "calibrar":
            self.dibujarCalibracion()
        else:
            self.dibujarMundo()
            self.dibujarAncla()
            self.dibujarHud()
            self.dibujarBase()
            if self.estado == "resultado":
                self.dibujarResultado()
            if self.estado == "tutorial":
                self.dibujarTutorial()
            if self.estado == "intro":
                self.dibujarIntro()
            if self.estado == "revelacion":
                self.dibujarRevelacion()
            self.dibujarDesvanecer()
            if self.tiempo < self.avisoHasta:
                w = self.fuentes[16].size(self.aviso)[0] + 40
                panel(self.pantalla, pygame.Rect(ancho // 2 - w // 2, 76, w, 40), cCrema, cOscuro, 14, 3)
                self.texto(self.aviso, 16, cOscuro, (ancho // 2, 96), "center")
        self.dibujarCursor()
        if self.auto_flip:
            pygame.display.flip()

    # eventos
    def manejar(self, ev):
        if ev.type == pygame.QUIT:
            return False
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.estado == "revelacion":
            if self.revelacionLista():
                self.pasarAlResultado()
            return True
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.estado == "calibrar" and self.camara and self.rectVista.collidepoint(ev.pos):
                nx = (ev.pos[0] - self.rectVista.x) / self.rectVista.w
                ny = (ev.pos[1] - self.rectVista.y) / self.rectVista.h
                self.camara.pedido = (nx, ny)
            elif self.modo == "raton" or self.estado in ("calibrar", "resultado", "tutorial", "intro"):
                for b in self.botonesAhora():
                    if b.caja.collidepoint(ev.pos) and b.habilitado():
                        b.accion()
                        break
        if ev.type == pygame.KEYDOWN:
            k = ev.key
            if k == pygame.K_q:
                return False
            if k == pygame.K_m and self.camara is not None:
                self.modo = "raton" if self.modo == "camara" else "camara"
                if self.estado == "calibrar":
                    self.empezar()
            if k == pygame.K_k and self.camara is not None:
                self.estado = "calibrar"
            if self.estado == "calibrar":
                if k == pygame.K_SPACE and self.camara:
                    self.cuenta = 3.0
                elif k == pygame.K_RETURN and self.botJugar.habilitado():
                    self.empezar()
            elif self.estado == "intro":
                if k in (pygame.K_SPACE, pygame.K_RETURN):
                    if self.introLista():
                        self.terminarIntro()
                    else:
                        self.tIntro = self.tiempo - self.horarioEscritura(self.lineasEscritas(mensajeAlgoritmo))[-1]
            elif self.estado == "revelacion":
                if k in (pygame.K_SPACE, pygame.K_RETURN):
                    if self.revelacionLista():
                        self.pasarAlResultado()
                    else:
                        self.tRevelacion = self.tiempo - self.horarioEscritura(self.lineasRevelacion)[-1]
            elif self.estado == "tutorial":
                if k in (pygame.K_SPACE, pygame.K_RETURN):
                    self.siguientePaso()
                elif k == pygame.K_ESCAPE:
                    self.terminarTutorial()
            elif self.estado == "dibujar":
                if k in (pygame.K_SPACE, pygame.K_RETURN):
                    self.probar()
                elif k in (pygame.K_u, pygame.K_BACKSPACE):
                    self.deshacer()
                elif k == pygame.K_c:
                    self.borrar()
            elif self.estado == "viajando" and k == pygame.K_ESCAPE:
                self.estado, self.viaje = "dibujar", None
            elif self.estado == "resultado" and not self.esFinal:
                if k in (pygame.K_RETURN, pygame.K_r):
                    self.volverADibujar()
                elif k == pygame.K_n and self.resultado["gano"]:
                    self.siguienteNivel()
        return True

    def ejecutar(self):
        corriendo = True
        while corriendo:
            delta = min(self.reloj.tick(fps) / 1000, 0.05)
            for ev in pygame.event.get():
                corriendo = self.manejar(ev) and corriendo
            self.actualizar(delta)
            corriendo = corriendo and not self.terminado
            self.dibujar()
        if self.camara:
            self.camara.detener()
        pygame.quit()


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raton", action="store_true", help="jugar con el mouse (sin cámara)")
    ap.add_argument("--camara", type=int, default=0, help="índice de la cámara")
    opc = ap.parse_args()
    pygame.init()
    Juego(usarCamara=not opc.raton, indiceCamara=opc.camara).ejecutar()


if __name__ == "__main__":
    principal()
