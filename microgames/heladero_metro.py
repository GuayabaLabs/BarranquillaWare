import math
import os
import random
import sys
from typing import Callable, List, Optional
import pygame

if __name__ == "__main__":
    raizProyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, raizProyecto)
    os.chdir(raizProyecto)

from core.microgame import BaseMicrogame
from core.asset_manager import quitarBlanco, achicar, borrarFondo

carpetaHelado = "Estadio"
ALTURA_CLIENTE = 561
sabores = [
    {"nombre": "coco", "color": (246, 240, 226), "sombra": (196, 178, 150), "brillo": (255, 255, 250)},
    {"nombre": "corozo", "color": (156, 34, 64), "sombra": (96, 14, 38), "brillo": (214, 96, 120)},
]
companero = {"nombre": "Andrés Felipe Mendoza", "cargo": "CEO & Founder | Speaker | Mentor de líderes"}
postsExito = [
    ("Hoy cerré mi tercera ronda de inversión en Miami. Nunca dejen de soñar en grande. #Bendecido",
     "2.348 recomendaciones · 312 comentarios", ["¿Y yo? Veinte años en el mismo carrito...",
                                                 "Él en Miami y yo aquí sudando la gota gorda."]),
    ("Desayunando en mi oficina con vista al mar. Me levanto a las 4 a.m. mientras ustedes duermen. #Disciplina",
     "5.120 recomendaciones · 840 comentarios", ["Mi oficina es este carrito y esta acera...",
                                                 "Será que yo no tengo disciplina."]),
    ("Orgulloso de anunciar que ahora soy Director Regional. Hoy di mi charla ante 2.000 personas. #NuevoReto",
     "8.902 recomendaciones · 1.204 comentarios", ["Estudiamos en el mismo salón...",
                                                   "Y él ahora le habla a miles de personas."]),
    ("Acuerdo firmado. Ahora a Panamá en jet privado. El éxito es una decisión, no una casualidad.",
     "3.775 recomendaciones · 498 comentarios", ["Él en un avión privado y yo empujando este carrito...",
                                                 "¿En qué momento me quedé atrás?"]),
]
dialogosHinchas = [
    {
        "una": ["¡Señor, una de {a}, porfa!", "Señor, ¿me da una bolita de {a}?"],
        "dos": ["¡Una de {a} y otra de {b}, señor!", "Señor, quiero de {a} y de {b}"],
        "iguales": ["¡Dos de {a}, señor! Mi mamá me dio plata"],
        "perfecto": ["¡Gracias, señor! ¡Está riquísimo!",
                     "¡Uy, qué rico! ¡Gracias, señor heladero!",
                     "¡Cuando sea grande quiero hacer helados como usted!"],
        "bien": ["¡Gracias, señor!", "¡Qué rico, gracias!"],
        "mal": ["Señor... ¿por qué me dio tan poquito?"],
        "sabor": "Señor, yo le pedí de {a}...",
        "espera": "¡Mi papá me está llamando, ya me voy!",
    },
    {
        "una": ["Mijo, una de {a}, que este sol está bravo", "Ay, mijo, ¿me vende una de {a}?"],
        "dos": ["Mijo, una de {a} y otra de {b}", "Ay, mijo, véndame una de {a} y una de {b}"],
        "iguales": ["Mijo, dos de {a}, que este calor no perdona"],
        "perfecto": ["¡Ay, mijo, gracias por siempre vender los helados de la mejor forma!",
                     "Dios le pague, mijo. ¡Qué helado tan sabroso!",
                     "Usted sí atiende con cariño, mijo. ¡Bendiciones!"],
        "bien": ["Gracias, mijo", "Ay, qué sabroso, gracias"],
        "mal": ["Ay, mijo, me sirvió muy poquito"],
        "sabor": "Mijo, yo le pedí de {a}, pero bueno...",
        "espera": "Ay, mijo, me voy que ya empieza el partido",
    },
    {
        "una": ["Ajá, mi llave, ¿me vendes una de {a}?", "Una de {a}, mi llave, pa' aguantar el partido"],
        "dos": ["Una de {a} y otra de {b}, mi llave", "Ajá, viejo, una de {a} y una de {b}"],
        "iguales": ["Doble de {a}, mi llave, que hace un calor..."],
        "perfecto": ["¡Ajá, ese helado está buenísimo, mi llave!",
                     "¡Qué nota, viejo! Usted es el mejor heladero del Metro",
                     "Mi papá me traía donde usted cuando yo era pelao. ¡Sigue igualito!"],
        "bien": ["Bacano, gracias, mi llave", "Eso, gracias, viejo"],
        "mal": ["Ombe, ¿y tan poquito helado?"],
        "sabor": "Ombe, yo te pedí de {a}, pero bueno...",
        "espera": "¡Ombe, ya va a empezar el partido!",
    },
    {
        "una": ["Compadre, una de {a} como en los viejos tiempos", "Compadre, regáleme una de {a}"],
        "dos": ["Compadre, una de {a} y una de {b}", "Una de {a} y otra de {b}, compadre"],
        "iguales": ["Compadre, dos de {a}, que el Junior hoy nos hace sufrir"],
        "perfecto": ["Así se hacen los helados, como antes. ¡Gracias, compadre!",
                     "Usted sí es serio, compadre. ¡Bendiciones pa' ese carrito!",
                     "¡Con este helado hasta el Junior gana hoy, compadre!"],
        "bien": ["Gracias, compadre", "Muy bien, compadre"],
        "mal": ["Compadre, me quedó corto el helado"],
        "sabor": "Compadre, yo le pedí de {a}...",
        "espera": "Compadre, me voy, que no alcanzo a entrar",
    },
    {
        "una": ["¡Veci, una de {a}, porfa!", "¡Ay, veci, me regala una bolita de {a} bien fría?"],
        "dos": ["¡Veci, una de {a} y otra de {b}!", "Una de {a} y una de {b}, veci, pa' compartir"],
        "iguales": ["¡Veci, dos de {a}, que tengo tremenda sed!"],
        "perfecto": ["¡Ay, qué delicia, veci! ¡Le quedó espectacular!",
                     "¡El mejor raspao helado de Barranquilla, veci!",
                     "¡Con esto revivo del calor, gracias veci!"],
        "bien": ["¡Gracias, veci!", "¡Qué rico, veci!"],
        "mal": ["Ay, veci... pero me echó fue muy poquito..."],
        "sabor": "Veci, yo le pedí de {a}...",
        "espera": "¡Veci, me voy que me coge la tarde pa' la clase!",
    },
    {
        "una": ["¡Erda, cuadro, tírame una de {a}!", "¡Tírate una bola de {a}, cuadro, pa' cantar los goles!"],
        "dos": ["¡Una de {a} y una de {b}, cuadro!", "¡Póngale {a} y {b}, que hoy gana papá Junior!"],
        "iguales": ["¡Doble de {a}, cuadro, que hoy juega el Tiburón!"],
        "perfecto": ["¡Erda, cuadro, qué golazo de helado!",
                     "¡Pa' que lo celebre toda la hinchada rojiblanca!",
                     "¡Tú eres el goleador del estadio, cuadro!"],
        "bien": ["¡Vale, cuadro, todo bien!", "¡Firme ahí, cuadro!"],
        "mal": ["No joda, cuadro, me escatimaste el helado"],
        "sabor": "Cuadro, yo te pedí de {a}, pilas ahí...",
        "espera": "¡No joda, ya salió el Junior a la cancha, me fui!",
    },
    {
        "una": ["Maestro, una de {a} bien puesta", "Ajá, maestro, regáleme una bolita de {a}"],
        "dos": ["Maestro, una de {a} y otra de {b}", "Póngame una de {a} y una de {b}, maestro"],
        "iguales": ["Dos de {a}, maestro, que el sol de La Arenosa está picante"],
        "perfecto": ["¡Carajo, maestro, qué elegancia de raspao!",
                     "¡Esto sí es tradición caribeña de la buena!",
                     "¡Con este frescor aguanto hasta el alargue, maestro!"],
        "bien": ["Muchas gracias, maestro", "Firme y elegante, maestro"],
        "mal": ["Carajo, maestro, ¿y esa bolita tan flaca?"],
        "sabor": "Maestro, la bola era de {a}...",
        "espera": "¡Me voy, maestro, que me están guardando puesto en sombra!",
    },
]
finalCompanero = [
    "¿Tú eres el del colegio? ¡Ajá, mano, cuánto tiempo!",
    "Yo vivo de reunión en reunión, ni duermo...",
    "Hace años que no venía al Metro a ver al Junior.",
    "Lo que publico es pura vitrina, viejo. Tú sí estás viviendo.",
]
escenaIntro = [("", "Hoy se cumplen diez años vendiendo helado aquí, afuera del Metro."),
               ("", "Diez años de sol, de partidos del Junior... y de gente que se va contenta."),
               ("", "¡Heladooo! ¡Helado de coco y de corozo, pa'l calor del Metro!")]
# Voz doblada de algunas líneas de las escenas: texto exacto → archivo en assets/voces/ (o assets/).
# Suena cuando la línea aparece en pantalla; si falta el archivo, la línea se muestra igual sin voz.
vocesEscena = {
    "¡Heladooo! ¡Helado de coco y de corozo, pa'l calor del Metro!": ("heladero_pregon.mp3", "heladero_pregon.ogg"),
}
ordenCombos = [[0], [1], [0, 0], [1, 1], [0, 1]]
archivosClientes = [
    "clienteNino.jpg",
    "clienteSenora.jpg",
    "clienteJoven.jpg",
    "clienteAbuelo.jpg",
    "clienteMuchacha.jpg",
    "clienteHincha.jpg",
    "clienteCosteno.jpg",
]
escenaReconoce = [("Tú, el heladero", "Espérate... ¿ese no es Andrés Felipe, el del colegio?"),
                  ("Tú, el heladero", "¡El mismo de las fotos en Miami que me sale en el celular!")]
escenaConfesion = [("Andrés Felipe", "¿Tú eres el del colegio? ¡Ajá, mano, cuánto tiempo!"),
                   ("Andrés Felipe", "Yo vivo de reunión en reunión... ni duermo, viejo."),
                   ("Andrés Felipe", "Hace años que no venía al Metro a ver al Junior."),
                   ("Andrés Felipe", "Lo que publico es pura vitrina. Tú sí estás viviendo."),
                   ("Tú, el heladero", "Y yo comparándome con tus fotos todo el día...")]
precioBola = 2000
propinaPerfecta = 1000
metaPlata = 24000


class HeladeroMetroMicrogame(BaseMicrogame):
    ensenanzaFinal = {
        "gana": ["En LinkedIn todos muestran su mejor foto,",
                 "pero nadie publica el cansancio ni la soledad.",
                 "Tu valor está en la fila, no en el feed, mi llave."],
        "pierde": ["Te comparaste con una foto y se te derritió el día.",
                   "Lo que ves en redes es la vitrina, no la vida.",
                   "Tu trabajo bien hecho también es éxito."],
    }
    GAMEPAD_BUTTON_KEYS = {2: pygame.K_1, 1: pygame.K_2, 0: pygame.K_SPACE, 3: pygame.K_RETURN}
    CAMERA_ACTIONS = {"accion": pygame.K_RETURN, "dedos": (pygame.K_1, pygame.K_2)}
    TIME_BAR_LAYOUT = (1585, 48, 470)
    fraseRedes = "Usa las redes pa' inspirarte, no pa' compararte."

    def __init__(self, character_id: str = "westcol",
                 on_complete_callback: Optional[Callable[[bool], None]] = None) -> None:
        self.character_id = character_id
        super().__init__(command_text="¡Sirve el helado con cariño!\nNo te compares con lo que ves en el celular",
                         time_limit=130.0, on_complete_callback=on_complete_callback)

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.fadeout_music(600)

    def ponerMusica(self) -> None:
        self.audio.play_bgm("JuniorCancion.mp3", volume_scale=0.45)

    def setup_game(self) -> None:
        self.maxAnimo = 5
        self.cargarImagenes()
        titulo = self.assets.cargarFuenteTitulo
        self.fuenteGlobo = self.assets.cargarFuenteCuento(32)
        self.fuenteEscena = self.assets.cargarFuenteCuento(58)
        self.fuenteHablante = titulo(34)
        self.fuenteChica = titulo(20)
        self.fuenteAppNombre = titulo(22)
        self.fuenteAviso = titulo(40)
        self.fuenteGuia = titulo(34)
        self.fuenteHud = titulo(30)
        self.fuentePensamiento = self.assets.cargarFuenteCuento(40)

        self.tinas = [pygame.Rect(0, 0, 230, 104), pygame.Rect(0, 0, 230, 104)]
        self.tinas[0].center = (800, 808)
        self.tinas[1].center = (1064, 808)
        self.puntoCono = (1330, 760)
        if self.carrito is not None and self.escalaCarrito:
            e = self.escalaCarrito
            w, h = self.carrito.get_size()
            self.cajaCarrito = self.carrito.get_rect(midbottom=(960, self.screen_h + 4))
            c = self.cajaCarrito
            for tina, (x0, y0, x1, y1) in zip(self.tinas, ((268, 232, 668, 556), (676, 232, 1066, 556))):
                tina.update(c.x + int(x0 * e), c.y + int(y0 * e), int((x1 - x0) * e), int((y1 - y0) * e))
            self.puntoCono = (c.x + int(1176 * e), c.y + int(262 * e))
            self.prepararPotes()
        elif self.carrito is not None:
            w, h = self.carrito.get_size()
            self.cajaCarrito = self.carrito.get_rect(topleft=(960 - w // 2, 830 - int(h * 0.53)))
            c = self.cajaCarrito
            for tina, (fx, fy) in zip(self.tinas, ((0.345, 0.525), (0.65, 0.534))):
                tina.size = (int(w * 0.25), int(h * 0.2))
                tina.center = (c.x + int(w * fx), c.y + int(h * fy))
            self.puntoCono = (c.x + int(w * 0.864), c.y + int(h * 0.245))
        self.surcos = [pygame.Surface(t.size, pygame.SRCALPHA) for t in self.tinas]
        self.anillosTina = []
        if self.anillos:
            import numpy as np
            base = self.anillos[0]
            fila = pygame.surfarray.array_alpha(base)[:, base.get_height() // 2]
            llenos = np.nonzero(fila > 100)[0]
            huecos = [x for x in range(llenos.min(), llenos.max()) if fila[x] <= 100]
            proporcion = (len(huecos) / float(base.get_width())) if huecos else 0.6
            for tina in self.tinas:
                ancho = int(tina.w * 1.16)
                alto = int(ancho * base.get_height() / base.get_width() * (tina.h / float(tina.w)) / (base.get_height() / float(base.get_width())) )
                hueco = pygame.Surface((ancho, alto), pygame.SRCALPHA)
                interior = pygame.Rect(0, 0, int(tina.w * 1.0), int(tina.h * 1.0))
                interior.center = (ancho // 2, alto // 2)
                hueco.fill((255, 255, 255, 255))
                pygame.draw.ellipse(hueco, (255, 255, 255, 0), interior)
                aros = []
                for a in self.anillos:
                    aro = pygame.transform.smoothscale(a, (ancho, alto))
                    aro.blit(hueco, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                    aros.append(aro)
                self.anillosTina.append(aros)
        self.mascarasTina = []
        for t in self.tinas:
            mascara = pygame.Surface(t.size, pygame.SRCALPHA)
            pygame.draw.ellipse(mascara, (255, 255, 255, 255), mascara.get_rect())
            self.mascarasTina.append(mascara)
        self.relojSurcos = 0.0
        self.puntoPote = (548, 968)
        if self.carrito is not None and self.escalaCarrito:
            self.puntoPote = (self.cajaCarrito.x + int(165 * self.escalaCarrito),
                              self.cajaCarrito.y + int(560 * self.escalaCarrito))

        self.cajaCelular = self.marcoCelular.get_rect(topleft=(28, 150)) if self.marcoCelular else pygame.Rect(28, 150, 400, 800)
        m = self.cajaCelular
        self.pantalla = pygame.Rect(m.x + int(m.w * 0.075), m.y + int(m.h * 0.035), int(m.w * 0.85), int(m.h * 0.93))

        self.tiempo = 0.0
        self.animo = 3
        self.servidos = 0
        self.perfectos = 0
        self.plata = 0
        self.plataMostrada = 0.0

        self.sabor = 0
        self.raspando = False
        self.teclaRaspar = False
        self.vueltas = 0.0
        self.ultimoPunto = None
        self.cono: List[dict] = []
        self.volando: List[dict] = []
        self.monedas: List[dict] = []
        self.posMano = [1250.0, 900.0]
        self.ratonPos = (960, 540)
        self.temblor = 0.0
        self.arrastrandoCono = False
        self.posCono = list(self.puntoCono)
        self.conoViaje = None

        self.cliente = None
        self.esperaCliente = 1.2
        self.ordenClientes = list(range(len(archivosClientes)))
        random.shuffle(self.ordenClientes)
        self.cuantosClientes = 0
        self.llegaCompanero = 105.0

        self.momentosPost = [0.0, 35.0, 58.0, 82.0]
        self.seguidas = 0
        self.lagrimas = None
        self.destaqueAnimo = None
        self.gotas: List[dict] = []
        self.cualPost = 0
        self.aviso = None
        self.postAbierto = None
        self.celularCentro = 0.0
        self.pensamiento = None

        self.celularFuera = 0.0
        self.tiempoJuego = 0.0
        self.desdeUltimoPost = 0.0
        self.volumenMusica = 1.0
        self.mensajes: List[dict] = []
        self.corazonesVolando: List[dict] = []
        self.finalPendiente = None
        self.escena = None
        self.introHecha = False
        self.decision = None
        self.campanitas = None
        ruta = os.path.join(self.assets.base_dir, carpetaHelado, "campanitas.mp3")
        try:
            if pygame.mixer.get_init() and os.path.exists(ruta):
                self.campanitas = pygame.mixer.Sound(ruta)
        except pygame.error:
            self.campanitas = None

    def cargarOpcional(self, archivo: str, ancho: int = 1200):
        ruta = os.path.join(carpetaHelado, archivo)
        if not os.path.exists(os.path.join(self.assets.base_dir, ruta)):
            return None
        try:
            imagen = self.assets.cargarSinFondo(ruta, ancho)
            return imagen.subsurface(imagen.get_bounding_rect(min_alpha=60)).copy()
        except Exception as e:
            print(f"[Heladero] Aviso al cargar {archivo}: {e}")
            return None

    def cargarFondoOpcional(self, archivo: str):
        ruta = os.path.join(carpetaHelado, archivo)
        if not os.path.exists(os.path.join(self.assets.base_dir, ruta)):
            return None
        try:
            return pygame.transform.smoothscale(self.assets.load_surface(ruta, has_alpha=False), (self.screen_w, self.screen_h))
        except Exception as e:
            print(f"[Heladero] Aviso al cargar {archivo}: {e}")
            return None

    def aAncho(self, imagen: pygame.Surface, ancho: int) -> pygame.Surface:
        alto = max(1, int(imagen.get_height() * ancho / float(imagen.get_width())))
        return pygame.transform.smoothscale(imagen, (ancho, alto))

    def aAlto(self, imagen: pygame.Surface, alto: int) -> pygame.Surface:
        caja = imagen.get_bounding_rect(min_alpha=60)
        recortada = imagen.subsurface(caja).copy() if (caja.w > 0 and caja.h > 0) else imagen
        h = recortada.get_height()
        if h <= 0:
            return recortada
        if h == alto:
            return recortada if recortada is not imagen else imagen.copy()
        ancho = max(1, int(round(recortada.get_width() * alto / float(h))))
        return pygame.transform.smoothscale(recortada, (ancho, alto))

    def separar(self, hoja: pygame.Surface, columnas: int, filas: int = 1, margen: float = 0.0) -> list:
        piezas = []
        w, h = hoja.get_width() // columnas, hoja.get_height() // filas
        mx, my = int(w * margen), int(h * margen)
        for f in range(filas):
            for c in range(columnas):
                trozo = hoja.subsurface((c * w + mx, f * h + my, w - 2 * mx, h - 2 * my))
                caja = trozo.get_bounding_rect(min_alpha=60)
                piezas.append(trozo.subsurface(caja).copy() if caja.w > 0 else trozo.copy())
        return piezas

    def cargarVerde(self, archivo: str):
        from collections import deque
        import numpy as np
        ruta = os.path.join(self.assets.base_dir, carpetaHelado, archivo)
        if not os.path.exists(ruta):
            return None
        try:
            imagen = pygame.image.load(ruta).convert_alpha()
        except pygame.error as e:
            print(f"[Heladero] Aviso al cargar {archivo}: {e}")
            return None
        rgb = pygame.surfarray.array3d(imagen).transpose(1, 0, 2).astype(np.float32)
        h, w, _ = rgb.shape
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        resto = np.maximum(r, b)
        dom = g - resto
        is_green = dom > 32
        pure_chroma = (g > 170) & (dom > 85)

        visited = pure_chroma.copy()
        frontier = np.zeros_like(visited)
        frontier[1:, :] |= pure_chroma[:-1, :]
        frontier[:-1, :] |= pure_chroma[1:, :]
        frontier[:, 1:] |= pure_chroma[:, :-1]
        frontier[:, :-1] |= pure_chroma[:, 1:]
        frontier &= is_green & ~visited
        frontier[0, :] |= is_green[0, :] & ~visited[0, :]
        frontier[-1, :] |= is_green[-1, :] & ~visited[-1, :]
        frontier[:, 0] |= is_green[:, 0] & ~visited[:, 0]
        frontier[:, -1] |= is_green[:, -1] & ~visited[:, -1]

        visited |= frontier
        ys_s, xs_s = np.nonzero(frontier)
        q = deque(zip(ys_s.tolist(), xs_s.tolist()))
        while q:
            cy, cx = q.popleft()
            if cy > 0 and not visited[cy - 1, cx] and is_green[cy - 1, cx]:
                visited[cy - 1, cx] = True
                q.append((cy - 1, cx))
            if cy + 1 < h and not visited[cy + 1, cx] and is_green[cy + 1, cx]:
                visited[cy + 1, cx] = True
                q.append((cy + 1, cx))
            if cx > 0 and not visited[cy, cx - 1] and is_green[cy, cx - 1]:
                visited[cy, cx - 1] = True
                q.append((cy, cx - 1))
            if cx + 1 < w and not visited[cy, cx + 1] and is_green[cy, cx + 1]:
                visited[cy, cx + 1] = True
                q.append((cy, cx + 1))

        band1 = np.zeros_like(visited)
        band1[1:, :] |= visited[:-1, :]
        band1[:-1, :] |= visited[1:, :]
        band1[:, 1:] |= visited[:, :-1]
        band1[:, :-1] |= visited[:, 1:]
        band1 &= ~visited

        band2 = np.zeros_like(visited)
        band2[1:, :] |= band1[:-1, :]
        band2[:-1, :] |= band1[1:, :]
        band2[:, 1:] |= band1[:, :-1]
        band2[:, :-1] |= band1[:, 1:]
        band2 &= ~(visited | band1)

        alfa = np.where(visited, np.clip(255 - (dom - 35) * 255 / 60, 0, 255), 255.0)
        aa_edge = np.clip(255 - (dom - 10) * 10, 0, 255)
        alfa = np.where(band1 & (dom > 10), aa_edge, alfa)

        despill = (visited & (dom > 12)) | ((band1 | band2) & (dom > 2))
        rgb_out = rgb.copy()
        rgb_out[..., 1] = np.where(despill, np.clip(resto + 2, 0, 255), g)

        pixeles = pygame.surfarray.pixels3d(imagen)
        pixeles[...] = np.clip(rgb_out, 0, 255).transpose(1, 0, 2).astype(np.uint8)
        del pixeles
        canal = pygame.surfarray.pixels_alpha(imagen)
        canal[...] = np.clip(alfa, 0, 255).T.astype(np.uint8)
        del canal
        return imagen

    def pintarCorozo(self, tira: pygame.Surface) -> pygame.Surface:
        import numpy as np
        pintada = tira.copy()
        rgb = pygame.surfarray.array3d(tira).astype(np.float32)
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        alto = tira.get_height()
        ancho = tira.get_width() // 6
        xs = (np.arange(tira.get_width()) % ancho).astype(np.float32)[:, None]
        ys = np.arange(alto, dtype=np.float32)[None, :]
        cx, cy, rx, ry = 207.5 * ancho / 416.0, 197.0 * alto / 416.0, 166.0 * ancho / 416.0, 128.0 * alto / 416.0
        dentro = ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2 <= 1.0
        luz = (r + g + b) / 3.0
        crema = dentro & (r >= g - 4) & (g >= b - 4) & (r - b > 6) & (luz > 120) & (r - g < 40)
        tono = np.clip((luz - 120.0) / 135.0, 0.0, 1.0)[..., None]
        oscuro = np.array([92.0, 16.0, 40.0])
        claro = np.array([196.0, 70.0, 104.0])
        nuevo = oscuro + (claro - oscuro) * tono
        mezcla = np.where(crema[..., None], nuevo, rgb)
        pygame.surfarray.pixels3d(pintada)[...] = np.clip(mezcla, 0, 255).astype(np.uint8)
        return pintada

    def prepararPotes(self) -> None:
        import numpy as np
        self.raspados = None
        if not self.tirasVerdes:
            return
        self.raspados = []
        self.lugarPotes = []
        for i, tira in enumerate(self.tirasVerdes):
            tina = self.tinas[i]
            ancho = tira.get_width() // 6
            cuadros = [tira.subsurface((k * ancho, 0, ancho, tira.get_height())).copy() for k in range(6)]
            bocaOriginal = self.medirBoca(cuadros[0]) if self.tirasNuevas[i] else pygame.Rect(38, 67, 339, 260)
            escala = tina.w / float(bocaOriginal.w)
            cuadros = [pygame.transform.smoothscale_by(c, escala) for c in cuadros]
            w, h = cuadros[0].get_size()
            boca = pygame.Rect(int(bocaOriginal.x * escala), int(bocaOriginal.y * escala),
                               int(bocaOriginal.w * escala), int(bocaOriginal.h * escala))
            dentro = np.zeros((w, h), dtype=bool)
            xs = (np.arange(w)[:, None] - boca.centerx) / (boca.w / 2.0)
            ys = (np.arange(h)[None, :] - boca.centery) / (boca.h / 2.0)
            dentro = (xs * xs + ys * ys) <= 1.0
            base = pygame.surfarray.array3d(cuadros[0]).astype(np.int16)
            baseAlfa = pygame.surfarray.array_alpha(cuadros[0])
            listos = []
            for k, cuadro in enumerate(cuadros):
                rgb = pygame.surfarray.array3d(cuadro).astype(np.int16)
                distinto = np.abs(rgb - base).sum(axis=2) > 70
                if self.tirasNuevas[i] and k > 0:
                    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
                    piel = (r - b > 45) & (r >= g)
                    manga = (np.minimum(np.minimum(r, g), b) > 205) & (b <= r + 4)
                    zona = distinto | (baseAlfa < 60)
                    cerca = self.ensanchar(self.soloBrazo(self.ensanchar(zona & (piel | manga), 2)), 6)
                    conservar = dentro | (ys < 0) | (zona & cerca)
                else:
                    conservar = dentro | (ys < 0) | (baseAlfa < 60) | (distinto & (k > 0))
                canal = pygame.surfarray.pixels_alpha(cuadro)
                canal[...] = np.where(conservar, canal, 0).astype(np.uint8)
                del canal
                if k == 0:
                    listos.append(cuadro)
                elif self.tirasNuevas[i]:
                    listos.append(self.extenderAbajo(cuadro, 700))
                else:
                    listos.append(self.extenderManga(cuadro, 500, 0.7))
            self.raspados.append(listos)
            self.lugarPotes.append((tina.x - boca.x, tina.y - boca.y))

    def medirBoca(self, cuadro: pygame.Surface) -> pygame.Rect:
        import numpy as np
        alfa = pygame.surfarray.array_alpha(cuadro)
        caja = cuadro.get_bounding_rect(min_alpha=100)
        mayor, filaMayor = 0, caja.top
        for y in range(caja.top, caja.top + int(caja.h * 0.6)):
            xs = np.nonzero(alfa[:, y] > 100)[0]
            if len(xs) and xs.max() - xs.min() > mayor + 1:
                mayor, filaMayor = xs.max() - xs.min(), y
        xs = np.nonzero(alfa[:, filaMayor] > 100)[0]
        alto = max(4, 2 * (filaMayor - caja.top))
        return pygame.Rect(int(xs.min()), caja.top, int(mayor), alto)

    def ensanchar(self, mascara, radio: int):
        import numpy as np
        try:
            import cv2
            nucleo = np.ones((radio * 2 + 1, radio * 2 + 1), np.uint8)
            return cv2.dilate(mascara.astype(np.uint8), nucleo) > 0
        except Exception:
            return mascara

    def soloBrazo(self, mascara):
        import numpy as np
        w, h = mascara.shape
        brazo = np.zeros_like(mascara)
        semillas = [(x, h - 2) for x in np.nonzero(mascara[:, h - 2])[0]]
        if not semillas:
            return brazo
        try:
            import cv2
            img = (mascara.T.astype(np.uint8)) * 255
            n, etiquetas = cv2.connectedComponents(img, connectivity=8)
            ids = {etiquetas[y, x] for x, y in semillas}
            ids.discard(0)
            return np.isin(etiquetas.T, list(ids))
        except Exception:
            return mascara

    def extenderAbajo(self, cuadro: pygame.Surface, largo: int) -> pygame.Surface:
        import numpy as np
        w, h = cuadro.get_size()
        alfa = pygame.surfarray.array_alpha(cuadro)

        def centro(y):
            xs = np.nonzero(alfa[:, y] > 100)[0]
            return xs.mean() if len(xs) else None
        abajo, arriba = centro(h - 3), centro(max(0, h - 45))
        pendiente = 0.0 if abajo is None or arriba is None else (abajo - arriba) / 42.0
        lienzo = pygame.Surface((w + largo, h + largo), pygame.SRCALPHA)
        fila = cuadro.subsurface((0, h - 3, w, 2)).copy()
        for dy in range(0, largo, 2):
            lienzo.blit(fila, (int(pendiente * dy), h - 3 + dy))
        lienzo.blit(cuadro, (0, 0))
        return lienzo

    def anchoTorso(self, imagen: pygame.Surface) -> int:
        import numpy as np
        alfa = pygame.surfarray.array_alpha(imagen)
        anchos = []
        for f in (0.8, 0.86, 0.92):
            xs = np.nonzero(alfa[:, int(imagen.get_height() * f)] > 100)[0]
            if len(xs):
                anchos.append(xs.max() - xs.min())
        return int(sorted(anchos)[len(anchos) // 2]) if anchos else imagen.get_width()

    def anchoCabeza(self, imagen: pygame.Surface) -> int:
        import numpy as np
        alfa = pygame.surfarray.array_alpha(imagen)
        mayor = 1
        for y in range(0, int(imagen.get_height() * 0.28), 2):
            fila = alfa[:, y] > 100
            if not fila.any():
                continue
            padded = np.concatenate(([False], fila, [False]))
            inicios = np.nonzero(padded[1:] & ~padded[:-1])[0]
            fines = np.nonzero(~padded[1:] & padded[:-1])[0]
            tramo = int((fines - inicios).max()) if len(inicios) else 0
            if tramo > mayor:
                mayor = tramo
        return mayor

    def igualarA(self, imagen: pygame.Surface, modelo: pygame.Surface) -> pygame.Surface:
        escala = self.anchoCabeza(modelo) / float(max(1, self.anchoCabeza(imagen)))
        return pygame.transform.smoothscale_by(imagen, escala)

    def _normalizarFraming(self, imagen: pygame.Surface, modelo: pygame.Surface, alto: int) -> pygame.Surface:
        img = self.aAlto(imagen, alto)
        head_m = self.anchoCabeza(modelo)
        head_f = self.anchoCabeza(img)
        if head_m > 10 and head_f > 10:
            ratio = head_m / float(head_f)
            if 1.015 < ratio <= 1.25:
                nuevo_w = max(1, int(round(img.get_width() * ratio)))
                nuevo_h = max(alto, int(round(img.get_height() * ratio)))
                escalada = pygame.transform.smoothscale(img, (nuevo_w, nuevo_h))
                return escalada.subsurface((0, 0, nuevo_w, alto)).copy()
        return img

    def igualarTamanos(self) -> None:
        if self.hinchas is not None:
            self.hinchas["espera"] = [self.aAlto(f, ALTURA_CLIENTE) for f in self.hinchas["espera"]]
            self.hinchas["feliz"] = [self.aAlto(f, ALTURA_CLIENTE) for f in self.hinchas["feliz"]]
            if self.pedidosClientes is not None:
                for tipo, figuras in enumerate(self.pedidosClientes):
                    self.pedidosClientes[tipo] = [self.aAlto(f, ALTURA_CLIENTE) for f in figuras]
            num_h = len(self.hinchas["espera"])
            for i in range(num_h):
                variantes = [self.hinchas["espera"][i]]
                if i < len(self.hinchas["feliz"]):
                    variantes.append(self.hinchas["feliz"][i])
                if self.pedidosClientes is not None and i < len(self.pedidosClientes):
                    variantes.extend(self.pedidosClientes[i])
                modelo = max(variantes, key=self.anchoCabeza)
                self.hinchas["espera"][i] = self._normalizarFraming(self.hinchas["espera"][i], modelo, ALTURA_CLIENTE)
                if i < len(self.hinchas["feliz"]):
                    self.hinchas["feliz"][i] = self._normalizarFraming(self.hinchas["feliz"][i], modelo, ALTURA_CLIENTE)
                if self.pedidosClientes is not None and i < len(self.pedidosClientes):
                    self.pedidosClientes[i] = [
                        self._normalizarFraming(f, modelo, ALTURA_CLIENTE) for f in self.pedidosClientes[i]
                    ]
        elif self.pedidosClientes is not None:
            for tipo, figuras in enumerate(self.pedidosClientes):
                self.pedidosClientes[tipo] = [self.aAlto(f, ALTURA_CLIENTE) for f in figuras]

        if self.companeroImg is not None and self.companeroImg.get("cliente") is not None:
            self.companeroImg["cliente"] = self.aAlto(self.companeroImg["cliente"], ALTURA_CLIENTE)
        if self.companeroHelado is not None:
            self.companeroHelado = self.aAlto(self.companeroHelado, ALTURA_CLIENTE)
        if self.companeroImg is not None and self.companeroImg.get("cliente") is not None and self.companeroHelado is not None:
            comp_esp = self.companeroImg["cliente"]
            modelo_comp = max((comp_esp, self.companeroHelado), key=self.anchoCabeza)
            self.companeroImg["cliente"] = self._normalizarFraming(comp_esp, modelo_comp, ALTURA_CLIENTE)
            self.companeroHelado = self._normalizarFraming(self.companeroHelado, modelo_comp, ALTURA_CLIENTE)

    def cargarCruda(self, archivo: str, ancho: int):
        ruta = os.path.join(carpetaHelado, archivo)
        if not os.path.exists(os.path.join(self.assets.base_dir, ruta)):
            return None
        try:
            return achicar(self.assets.load_surface(ruta), ancho)
        except Exception as e:
            print(f"[Heladero] Aviso al cargar {archivo}: {e}")
            return None

    def separarCrudo(self, hoja: pygame.Surface, columnas: int, filas: int, margen: float) -> list:
        w, h = hoja.get_width() // columnas, hoja.get_height() // filas
        mx, my = int(w * margen), int(h * margen)
        return [hoja.subsurface((c * w + mx, f * h + my, w - 2 * mx, h - 2 * my)).copy()
                for f in range(filas) for c in range(columnas)]

    def recortarFigura(self, celda: pygame.Surface, corte: float = 0.08) -> pygame.Surface:
        import numpy as np
        celda = celda.convert_alpha()
        rgb = pygame.surfarray.array3d(celda).astype(np.int16)
        blanco = ((rgb.max(axis=2) - rgb.min(axis=2)) <= 24) & (rgb.min(axis=2) >= 222)
        ocupado = ~blanco
        filas = np.nonzero(ocupado.any(axis=0))[0]
        if len(filas) == 0:
            return celda
        arriba, abajo = filas[0], filas[-1]
        abajo = int(abajo - (abajo - arriba) * corte)
        celda = celda.subsurface((0, 0, celda.get_width(), abajo)).copy()
        blanco = blanco[:, :abajo]
        w, h = celda.get_size()
        semillas = [(x, 0) for x in range(w)] + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
        limpia = borrarFondo(celda, blanco, 3, semillas)
        caja = limpia.get_bounding_rect(min_alpha=60)
        return limpia.subsurface(caja).copy()

    def quitarFondoCuadro(self, cuadro: pygame.Surface) -> pygame.Surface:
        import numpy as np
        cuadro = cuadro.convert_alpha()
        rgb = pygame.surfarray.array3d(cuadro).astype(np.int16)
        blanco = ((rgb.max(axis=2) - rgb.min(axis=2)) <= 24) & (rgb.min(axis=2) >= 222)
        w, h = cuadro.get_size()
        semillas = [(x, 0) for x in range(w)] + [(0, y) for y in range(h)]
        return borrarFondo(cuadro, blanco, 3, semillas)

    def extenderManga(self, mano: pygame.Surface, largo: int = 900, pendiente: float = 0.62) -> pygame.Surface:
        w, h = mano.get_size()
        lienzo = pygame.Surface((w + largo, h + int(largo * pendiente) + 2), pygame.SRCALPHA)
        derecha = mano.subsurface((w - 6, int(h * 0.55), 6, h - int(h * 0.55)))
        abajo = mano.subsurface((int(w * 0.6), h - 6, w - int(w * 0.6), 6))
        for k in range(largo, 0, -2):
            dy = int(k * pendiente)
            lienzo.blit(derecha, (w - 6 + k, int(h * 0.55) + dy))
            lienzo.blit(abajo, (int(w * 0.6) + k, h - 6 + dy))
        lienzo.blit(mano, (0, 0))
        return lienzo

    def cargarImagenes(self) -> None:
        self.fondo = self.cargarFondoOpcional("fondoHelado.png")
        if self.fondo is None:
            try:
                fondo = self.assets.load_surface("fondo_chat_estadio_microjuego.png", has_alpha=False)
                self.fondo = pygame.transform.smoothscale(fondo, (self.screen_w, self.screen_h))
            except Exception:
                self.fondo = pygame.Surface((self.screen_w, self.screen_h))
                self.fondo.fill((120, 170, 220))

        self.escalaCarrito = None
        carrito = self.cargarVerde("carrito.jpg")
        if carrito is not None:
            self.escalaCarrito = 0.8
            self.carrito = pygame.transform.smoothscale_by(carrito, self.escalaCarrito)
        else:
            carrito = self.cargarOpcional("carrito.png", 1600)
            self.carrito = self.aAncho(carrito, 1000) if carrito else None

        self.utensilios = None
        hoja = self.cargarOpcional("utensilios.png", 1600)
        if hoja is not None:
            piezas = self.separar(hoja, 4)
            self.utensilios = {"cuchara": piezas[0], "cono": self.aAncho(piezas[1], 92),
                               "bolas": [piezas[2], piezas[3]]}

        self.mano = None
        mano = self.cargarOpcional("manoHeladero.png", 1200)
        if mano is not None:
            mano = self.aAncho(mano, 360)
            self.anchoMano = mano.get_size()
            self.mano = self.extenderManga(mano)

        self.hinchas = None
        hoja = self.cargarVerde("hinchas.jpg")
        if hoja is not None:
            piezas = []
            for celda in self.separarCrudo(hoja, 4, 2, 0.03):
                caja = celda.get_bounding_rect(min_alpha=100)
                figura = celda.subsurface(caja).copy()
                figura = figura.subsurface((0, 0, figura.get_width(), int(figura.get_height() * 0.95))).copy()
                piezas.append(self.aAlto(figura, ALTURA_CLIENTE))
            self.hinchas = {"espera": piezas[:4], "feliz": piezas[4:]}
        hoja = None if self.hinchas is not None else self.cargarCruda("hinchas.png", 1800)
        if hoja is not None:
            piezas = [self.aAlto(self.recortarFigura(p), ALTURA_CLIENTE) for p in self.separarCrudo(hoja, 4, 2, 0.03)]
            self.hinchas = {"espera": piezas[:4], "feliz": piezas[4:]}

        extras = [
            ("clienteMuchacha_espera.png", "clienteMuchacha_feliz.png"),
            ("clienteHincha_espera.png", "clienteHincha_feliz.png"),
            ("clienteCosteno_espera.png", "clienteCosteno_feliz.png"),
        ]
        if self.hinchas is not None:
            for f_esp, f_fel in extras:
                for clave, archivo in (("espera", f_esp), ("feliz", f_fel)):
                    ruta_extra = os.path.join(carpetaHelado, archivo)
                    if os.path.exists(os.path.join(self.assets.base_dir, ruta_extra)):
                        try:
                            img = self.assets.load_surface(ruta_extra, has_alpha=True)
                            self.hinchas[clave].append(self.aAlto(img, ALTURA_CLIENTE))
                        except Exception as e:
                            print(f"[Heladero] Aviso al cargar {archivo}: {e}")

        self.companeroImg = None
        verde = self.cargarVerde("companero.jpg")
        if verde is not None:
            mitades = self.separarCrudo(verde, 2, 1, 0.0)
            busto = mitades[0].subsurface(mitades[0].get_bounding_rect(min_alpha=100)).copy()
            figura = mitades[1].subsurface(mitades[1].get_bounding_rect(min_alpha=100)).copy()
            figura = figura.subsurface((0, 0, figura.get_width(), int(figura.get_height() * 0.96))).copy()
            lado = int(busto.get_width() * 0.62)
            cara = pygame.Rect(0, 0, lado, lado)
            cara.midtop = (busto.get_width() // 2, int(busto.get_height() * 0.04))
            cara = cara.clip(busto.get_rect())
            avatar = pygame.Surface(cara.size, pygame.SRCALPHA)
            avatar.fill((178, 208, 236, 255))
            avatar.blit(busto.subsurface(cara), (0, 0))
            self.companeroImg = {"avatar": avatar, "cliente": self.aAlto(figura, ALTURA_CLIENTE)}
        hoja = None if self.companeroImg is not None else self.cargarOpcional("companero.png", 1400)
        cruda = self.cargarCruda("companero.png", 1400)
        if hoja is not None and cruda is not None:
            piezas = self.separar(hoja, 2)
            piezas[1] = self.recortarFigura(self.separarCrudo(cruda, 2, 1, 0.01)[1])
            busto = piezas[0]
            lado = int(busto.get_width() * 0.62)
            cara = pygame.Rect(0, 0, lado, lado)
            cara.midtop = (busto.get_width() // 2, int(busto.get_height() * 0.04))
            cara = cara.clip(busto.get_rect())
            self.companeroImg = {"avatar": busto.subsurface(cara).copy(), "cliente": self.aAlto(piezas[1], ALTURA_CLIENTE)}

        self.appBase = self.cargarOpcional("appLinked.png", 900)
        self.fotosPosts = None
        hoja = self.cargarOpcional("postExito.png", 1600) or self.cargarOpcional("postsExito.png", 1600)
        if hoja is not None:
            self.fotosPosts = self.separar(hoja, 4)

        cronometro = self.cargarOpcional("cronometro.png", 600)
        self.cronometro = self.aAncho(cronometro, 76) if cronometro is not None else None

        self.raspados = None
        self.mangaCompleta = False
        self.tirasNuevas = [False, False]
        coco = self.cargarVerde("raspadoCoco.jpg")
        corozo = self.cargarVerde("raspadoCorozo.jpg")
        if corozo is None and coco is not None:
            corozo = self.pintarCorozo(coco)
        self.tirasVerdes = [coco, corozo]
        if any(tira is None for tira in self.tirasVerdes):
            self.tirasVerdes = None
        hojas = [None] if self.tirasVerdes else [self.cargarCruda(nombre, 3000) for nombre in ("raspadoCoco.png", "raspadoCorozo.png")]
        if all(hoja is not None for hoja in hojas):
            self.raspados = []
            for hoja in hojas:
                cuadros = [self.aAncho(self.quitarFondoCuadro(c), 322) for c in self.separarCrudo(hoja, 6, 1, 0.015)]
                self.tamCuadro = cuadros[0].get_size()
                self.raspados.append([cuadros[0]] + [self.extenderManga(c, 500, 0.7) for c in cuadros[1:]])

        self.pedidosClientes = None
        hojas = [self.cargarVerde(n) for n in archivosClientes]
        if all(h is not None for h in hojas):
            self.pedidosClientes = []
            for idx, hoja in enumerate(hojas):
                figuras = []
                for celda in self.separarCrudo(hoja, 5, 1, 0.03):
                    figura = celda.subsurface(celda.get_bounding_rect(min_alpha=100)).copy()
                    if idx < 4:
                        figura = figura.subsurface((0, 0, figura.get_width(), int(figura.get_height() * 0.95))).copy()
                    figuras.append(self.aAlto(figura, ALTURA_CLIENTE))
                self.pedidosClientes.append(figuras)
        self.companeroHelado = None
        imagen = self.cargarVerde("companeroHelado.jpg")
        if imagen is not None:
            figura = imagen.subsurface(imagen.get_bounding_rect(min_alpha=100)).copy()
            figura = figura.subsurface((0, 0, figura.get_width(), int(figura.get_height() * 0.96))).copy()
            self.companeroHelado = self.aAlto(figura, ALTURA_CLIENTE)
        self.igualarTamanos()
        self.imagenesLagrimas = None
        hoja = self.cargarVerde("lagrimas.jpg")
        if hoja is not None:
            self.imagenesLagrimas = [c.subsurface(c.get_bounding_rect(min_alpha=60)).copy()
                                     for c in self.separarCrudo(hoja, 3, 1, 0.01)]

        self.anillos = None
        hoja = self.cargarVerde("anilloRaspado.jpg")
        if hoja is not None:
            self.anillos = []
            for celda in self.separarCrudo(hoja, 6, 1, 0.03):
                caja = celda.get_bounding_rect(min_alpha=100)
                self.anillos.append(celda.subsurface(caja).copy() if caja.w > 0 else celda)
        self.marLagrimas = None
        hoja = self.cargarVerde("marLagrimas.jpg")
        if hoja is not None:
            self.marLagrimas = []
            for celda in self.separarCrudo(hoja, 1, 4, 0.03):
                caja = celda.get_bounding_rect(min_alpha=100)
                agua = celda.subsurface(caja).copy() if caja.w > 0 else celda
                self.marLagrimas.append(pygame.transform.smoothscale(agua, (self.screen_w + 80, int(agua.get_height() * (self.screen_w + 80) / agua.get_width()))))

        self.potes = None
        hoja = self.cargarOpcional("potePropinas.png", 1800)
        if hoja is not None:
            self.potes = [self.aAncho(p, 128) for p in self.separar(hoja, 5)]

        self.dinero = None
        hoja = self.cargarOpcional("dinero.png", 1600)
        if hoja is not None:
            piezas = self.separar(hoja, 4)
            self.dinero = [self.aAncho(piezas[0], 38), self.aAncho(piezas[1], 42),
                           self.aAncho(piezas[2], 74), self.aAncho(piezas[3], 74)]

        self.poteVacio = self.poteLleno = None
        try:
            hoja = self.assets.cargarSinFondo(os.path.join("Fritanga", "potePropinas.jpg"), 1400)
            alfa = pygame.surfarray.array_alpha(hoja)
            ocupadas = (alfa > 60).any(axis=1)
            mitad = hoja.get_width() // 2
            huecos = [x for x in range(int(hoja.get_width() * 0.3), int(hoja.get_width() * 0.7)) if not ocupadas[x]]
            corte = huecos[len(huecos) // 2] if huecos else mitad
            vacio = hoja.subsurface((0, 0, corte, hoja.get_height()))
            lleno = hoja.subsurface((corte, 0, hoja.get_width() - corte, hoja.get_height()))
            vacio = vacio.subsurface(vacio.get_bounding_rect(min_alpha=60)).copy()
            lleno = lleno.subsurface(lleno.get_bounding_rect(min_alpha=60)).copy()
            self.poteVacio = self.aAncho(vacio, 128)
            self.poteLleno = pygame.transform.smoothscale(self.aAncho(lleno, 128), self.poteVacio.get_size())
        except Exception as e:
            print(f"[Heladero] Aviso: sin pote de propinas: {e}")

        self.flecha = None
        try:
            flecha = self.assets.cargarSinFondo(os.path.join("Fritanga", "flechaAbajo.jpg"), 600)
            self.flecha = self.aAncho(flecha.subsurface(flecha.get_bounding_rect(min_alpha=60)).copy(), 46)
        except Exception:
            pass

        self.marcoCelular = None
        try:
            crudo = achicar(self.assets.load_surface(os.path.join("Piano", "marcoCelular.jpg")), 1200)
            marco = quitarBlanco(crudo.copy(), ((0.5, 0.5),))
            marco = marco.subsurface(marco.get_bounding_rect(min_alpha=60)).copy()
            self.marcoCelular = self.aAncho(marco, 400)
        except Exception as e:
            print(f"[Heladero] Aviso: sin marco de celular: {e}")

        try:
            lleno = self.assets.cargarSinFondo(os.path.join("Piano", "corazonLleno.jpg"), 300)
            vacio = self.assets.cargarSinFondo(os.path.join("Piano", "corazonVacio.jpg"), 300)
            self.corazonLleno = self.aAncho(lleno, 56)
            self.corazonVacio = self.aAncho(vacio, 56)
            panel = self.assets.cargarSinFondo(os.path.join("Piano", "panelCorazones.jpg"), 900)
            self.panelCorazones = pygame.transform.smoothscale(panel, (self.maxAnimo * 64 + 50, 84))
        except Exception:
            self.corazonLleno = self.corazonVacio = self.panelCorazones = None

        try:
            globo = self.assets.cargarSinFondo(os.path.join("Fritanga", "globoTexto.jpg"), 1200)
            self.globo = globo.subsurface(globo.get_bounding_rect(min_alpha=60)).copy()
            nuevo = self.cargarVerde("globoCliente.jpg")
            if nuevo is not None:
                self.globo = nuevo.subsurface(nuevo.get_bounding_rect(min_alpha=60)).copy()
            else:
                self.globo = pygame.transform.flip(self.globo, True, False)
        except Exception:
            self.globo = None

        self.botonNaranja = None
        try:
            naranja = self.assets.load_cropped_surface("boton_acuarela_naranja.png")
            self.botonNaranja = naranja
        except Exception:
            pass
        self.botonAzul = self.botonGris = None
        try:
            boton = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonMorado.jpg"), 400)
            self.botonAzul = boton
            self.botonGris = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonRojo.jpg"), 400)
        except Exception:
            pass

    def textoBorde(self, fuente, texto: str, color=(255, 248, 236), borde=(96, 56, 30), grosor: int = 3) -> pygame.Surface:
        return self.textoConBorde(fuente, texto, color, borde, grosor)

    def partirEnLineas(self, fuente, texto: str, anchoMax: int) -> list:
        lineas, actual = [], ""
        for palabra in texto.split():
            prueba = (actual + " " + palabra).strip()
            if fuente.size(prueba)[0] <= anchoMax or not actual:
                actual = prueba
            else:
                lineas.append(actual)
                actual = palabra
        if actual:
            lineas.append(actual)
        return lineas

    def plataTexto(self, valor: float) -> str:
        return "$" + f"{int(valor):,}".replace(",", ".")

    def decir(self, texto: str, x: float, y: float, color=(255, 248, 236), borde=(92, 46, 118)) -> None:
        self.mensajes.append({"texto": texto, "x": x, "y": y, "vida": 1.6, "color": color, "borde": borde})

    def nuevoCliente(self) -> None:
        esCompanero = self.tiempoJuego >= self.llegaCompanero or self.cuantosClientes >= len(self.ordenClientes)
        if esCompanero:
            pedido = [0, 1]
            frase = "Una de coco y una de corozo, como en el recreo del colegio"
            tipo = -1
        else:
            tipo = self.ordenClientes[self.cuantosClientes % len(self.ordenClientes)]
            dialogos = dialogosHinchas[tipo % len(dialogosHinchas)]
            cuantas = 1 if self.cuantosClientes == 0 or random.random() < 0.4 else 2
            pedido = [random.randint(0, 1) for _ in range(cuantas)]
            nombres = [sabores[s]["nombre"] for s in pedido]
            if cuantas == 1:
                frase = random.choice(dialogos["una"]).format(a=nombres[0])
            elif pedido[0] == pedido[1]:
                frase = random.choice(dialogos["iguales"]).format(a=nombres[0])
            else:
                frase = random.choice(dialogos["dos"]).format(a=nombres[0], b=nombres[1])
        self.cuantosClientes += 1
        self.cliente = {"tipo": tipo, "pedido": pedido, "frase": frase, "estado": "llegando", "t": 0.0,
                        "paciencia": 18.0, "esCompanero": esCompanero, "respuesta": "", "dialogo": 0}

    def faltantes(self) -> list:
        c = self.cliente
        if c is None or c["estado"] != "esperando":
            return []
        pendientes = list(c["pedido"])
        for bola in self.cono + [v["bola"] for v in self.volando]:
            if bola["sabor"] in pendientes:
                pendientes.remove(bola["sabor"])
        return pendientes

    def calidadActual(self) -> float:
        return max(0.0, min(1.0, (self.vueltas - 0.3) / 2.0))

    def pasarCuchara(self, cantidad: float) -> None:
        if len(self.cono) + len(self.volando) >= 2:
            return
        if self.animo <= 1:
            cantidad *= 0.55
        elif self.animo == 2:
            cantidad *= 0.8
        antes = self.calidadActual()
        self.vueltas = min(3.0, self.vueltas + cantidad)
        if antes < 1.0 <= self.calidadActual() and hasattr(self.audio, "play_hit"):
            self.audio.play_hit()

    def marcarSurco(self, punto) -> None:
        if self.raspados is not None:
            return
        tina = self.tinas[self.sabor]
        x, y = punto[0] - tina.x, punto[1] - tina.y
        capa = self.surcos[self.sabor]
        datos = sabores[self.sabor]
        hueco = pygame.Rect(0, 0, 34, 18)
        hueco.center = (int(x), int(y))
        pygame.draw.ellipse(capa, (*datos["sombra"], 120), hueco)
        pygame.draw.arc(capa, (*datos["brillo"], 170), hueco.move(-2, -3), 0.3, 2.8, 3)

    def soltarCuchara(self) -> None:
        if self.vueltas >= 0.3 and len(self.cono) + len(self.volando) < 2:
            bola = {"sabor": self.sabor, "calidad": self.calidadActual()}
            self.volando.append({"bola": bola, "desde": tuple(self.posMano), "t": 0.0})
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()
        elif 0.0 < self.vueltas < 0.3:
            tina = self.tinas[self.sabor]
            self.decir("¡Raspa más!", tina.centerx, tina.top - 50, (255, 236, 150), (150, 70, 20))
        self.vueltas = 0.0
        self.raspando = False
        self.teclaRaspar = False
        self.ultimoPunto = None

    def entregar(self) -> None:
        c = self.cliente
        if not self.cono or c is None or c["estado"] != "esperando" or self.volando:
            return
        pedido = sorted(c["pedido"])
        servido = sorted(b["sabor"] for b in self.cono)
        calidad = sum(max(0.0, b["calidad"] - b.get("derretido", 0.0)) for b in self.cono) / max(1, len(c["pedido"]))
        if len(self.cono) < len(c["pedido"]):
            calidad *= 0.6
        bolas = len(self.cono)
        c["servido"] = servido
        self.cono = []
        self.servidos += 1
        c["estado"] = "feliz"
        c["t"] = 0.0
        pago = precioBola * bolas
        if c["esCompanero"]:
            c["respuesta"] = ""
            c["estado"] = "confiesa"
            self.pagar(pago + propinaPerfecta * 2)

            def terminar():
                self.companeroAtendido = True
                self.finalPendiente = (self.animo > 2, 0.6)
            self.iniciarEscena(escenaConfesion, terminar, enLinea=True)
            return
        dialogos = dialogosHinchas[c["tipo"] % len(dialogosHinchas)]
        if servido != pedido and len(servido) == len(pedido):
            falta = [s for s in pedido if s not in servido] or pedido
            c["respuesta"] = dialogos["sabor"].format(a=sabores[falta[0]]["nombre"])
        elif calidad >= 0.85:
            c["respuesta"] = random.choice(dialogos["perfecto"])
            self.perfectos += 1
            pago += propinaPerfecta
        elif calidad >= 0.45:
            c["respuesta"] = random.choice(dialogos["bien"])
        else:
            c["respuesta"] = random.choice(dialogos["mal"])
            c["estado"] = "triste"
        self.pagar(pago)
        if self.servidos % 2 == 0:
            self.cambiarAnimo(1)

    def pagar(self, valor: int) -> None:
        self.plata += valor
        piezas = max(2, valor // 1000)
        for i in range(piezas):
            self.monedas.append({"t": -i * 0.12, "tipo": i % 4 if self.dinero else i % 2,
                                 "desde": (1560 + random.uniform(-40, 40), 760 + random.uniform(-30, 30)),
                                 "giro": random.uniform(-40, 40)})
        self.decir("+" + self.plataTexto(valor), 1500, 700, (255, 236, 150), (40, 110, 60))

    def ajustarMusica(self) -> None:
        objetivo = 0.3 + 0.7 * (self.animo / float(self.maxAnimo))
        if abs(objetivo - self.volumenMusica) < 0.01:
            return
        self.volumenMusica += (objetivo - self.volumenMusica) * 0.08
        if getattr(self.audio, "current_track", None) == "JuniorCancion.mp3" and hasattr(self.audio, "_effective_bgm_volume"):
            self.audio._bgm_volume_scale = 0.45 * self.volumenMusica
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.set_volume(self.audio._effective_bgm_volume())
            except pygame.error:
                pass

    def cambiarAnimo(self, cuanto: int) -> None:
        anterior = self.animo
        self.animo = max(0, min(self.maxAnimo, self.animo + cuanto))
        if self.animo > anterior:
            self.corazonesVolando.append({"x": 1520.0, "y": 620.0, "t": 0.0})
            if hasattr(self.audio, "play_win"):
                self.audio.play_win()
        elif self.animo < anterior:
            self.trigger_screenshake(8.0, 0.25)
            if hasattr(self.audio, "play_miss"):
                self.audio.play_miss()
        if self.animo <= 0 and not self.is_finished and self.finalPendiente is None:
            self.finalPendiente = (False, 2.2)
            self.pensamiento = {"lineas": ["Ya no me provoca vender nada...", "Mejor recojo el carrito."], "t": 0.0, "dur": 2.2}

    def avisarPost(self) -> None:
        if self.cualPost >= len(postsExito):
            return
        self.soltarCuchara()
        self.arrastrandoCono = False
        self.decision = {"post": self.cualPost, "t": 0.0, "opcion": 1}
        self.desdeUltimoPost = 0.0
        self.pensamiento = None
        self.cualPost += 1
        if hasattr(self.audio, "play_hover"):
            self.audio.play_hover()

    def abrirPost(self) -> None:
        if self.decision is None:
            return
        self.postAbierto = {"post": self.decision["post"], "t": 0.0}
        self.decision = None
        self.cambiarAnimo(-1)
        self.destaqueAnimo = {"t": 0.0, "sube": False, "indice": self.animo}
        self.seguidas += 1
        if self.seguidas >= 2:
            self.empezarLagrimas()

    def silenciar(self) -> None:
        if self.decision is None:
            return
        self.decision = None
        self.seguidas = 0
        self.cambiarAnimo(1)
        self.destaqueAnimo = {"t": 0.0, "sube": True, "indice": self.animo - 1}
        self.pensamiento = {"lineas": ["¡Eso! A lo mío.", "Mi trabajo también vale."], "t": 0.0, "dur": 2.2}
        self.detenerLagrimas()
        self.restaurarMusicaAlegre()

    def empezarLagrimas(self) -> None:
        self.lagrimas = {"t": 0.0, "dur": 7.5}
        self.gotas = []
        for _ in range(9):
            self.gotas.append(self.nuevaGota(random.uniform(-0.6, 0.0)))
        if hasattr(self.audio, "play_bgm"):
            self.audio.play_bgm("cancion_triste_heladero.ogg", volume_scale=0.55)

    def detenerLagrimas(self) -> None:
        self.lagrimas = None
        self.gotas = []

    def restaurarMusicaAlegre(self) -> None:
        if getattr(self.audio, "current_track", None) == "cancion_triste_heladero.ogg":
            self.ponerMusica()

    def nuevaGota(self, retraso: float = 0.0) -> dict:
        lado = random.random()
        if lado < 0.4:
            x = random.uniform(40, 520)
        elif lado < 0.8:
            x = random.uniform(1400, 1880)
        else:
            x = random.uniform(560, 1360)
        return {"x": x, "y": random.uniform(-120, 300), "v": random.uniform(60, 160), "tam": random.uniform(0.7, 1.4),
                "t": retraso, "tipo": random.randint(0, 2)}

    def actualizarLagrimas(self, dt: float) -> None:
        if self.destaqueAnimo is not None:
            self.destaqueAnimo["t"] += dt
            if self.destaqueAnimo["t"] >= 2.6:
                self.destaqueAnimo = None
        if self.lagrimas is None:
            return
        self.lagrimas["t"] += dt
        for g in self.gotas:
            g["t"] += dt
            if g["t"] > 0:
                g["v"] += dt * 40
                g["y"] += g["v"] * dt
        if self.lagrimas["t"] < self.lagrimas["dur"] - 2.0:
            self.gotas = [g if g["y"] < self.screen_h + 80 else self.nuevaGota() for g in self.gotas]
        if self.lagrimas["t"] >= self.lagrimas["dur"]:
            self.lagrimas = None
            self.gotas = []
            self.restaurarMusicaAlegre()

    def dibujarLagrimas(self, surface: pygame.Surface) -> None:
        if self.lagrimas is None:
            return
        tl = self.lagrimas["t"]
        k = min(1.0, tl / 0.6, max(0.0, (self.lagrimas["dur"] - tl) / 2.0))
        if k <= 0.0:
            return
        borroso = pygame.transform.smoothscale(pygame.transform.smoothscale(surface, (192, 108)), (self.screen_w, self.screen_h))
        borroso.fill((214, 226, 245), special_flags=pygame.BLEND_RGB_MULT)
        borroso.set_alpha(int(170 * k))
        surface.blit(borroso, (0, 0))
        if self.marLagrimas:
            subida = min(1.0, tl / 1.2)
            cuadro = self.marLagrimas[int(tl * 5) % len(self.marLagrimas)]
            cuadro.set_alpha(int(235 * k))
            y = self.screen_h - int(cuadro.get_height() * (0.55 + 0.45 * subida))
            surface.blit(cuadro, (-40 + int(math.sin(tl * 1.5) * 30), y))
            oleaje = None
        else:
            oleaje = pygame.Surface((self.screen_w, 260), pygame.SRCALPHA)
        puntos = [(0, 260)]
        for x in range(0, self.screen_w + 40, 40):
            puntos.append((x, 120 + math.sin(x * 0.01 + tl * 2.2) * 26 + math.sin(x * 0.023 - tl * 1.3) * 14))
        puntos.append((self.screen_w, 260))
        if oleaje is not None:
            pygame.draw.polygon(oleaje, (180, 206, 240, int(120 * k)), puntos)
            pygame.draw.lines(oleaje, (255, 255, 255, int(150 * k)), False, puntos[1:-1], 4)
            surface.blit(oleaje, (0, self.screen_h - 260))
        for g in self.gotas:
            if g["t"] <= 0:
                continue
            w, h = int(46 * g["tam"]), int(66 * g["tam"])
            if self.imagenesLagrimas:
                imagen = pygame.transform.smoothscale(self.imagenesLagrimas[g["tipo"] % len(self.imagenesLagrimas)], (w, h))
                imagen.set_alpha(int(230 * k))
                surface.blit(imagen, imagen.get_rect(center=(int(g["x"]), int(g["y"]))))
                continue
            gota = pygame.Surface((w, h + 140), pygame.SRCALPHA)
            pygame.draw.rect(gota, (200, 222, 250, int(55 * k)), (w // 2 - w // 6, 0, w // 3, 140), border_radius=w // 6)
            cuerpo = pygame.Rect(0, 140 - h // 3, w, h)
            pygame.draw.ellipse(gota, (196, 220, 250, int(120 * k)), cuerpo)
            pygame.draw.ellipse(gota, (110, 140, 190, int(150 * k)), cuerpo, 3)
            brillo = pygame.Rect(cuerpo.x + w // 5, cuerpo.y + h // 6, w // 4, h // 3)
            pygame.draw.ellipse(gota, (255, 255, 255, int(210 * k)), brillo)
            surface.blit(gota, (int(g["x"] - w // 2), int(g["y"] - 140)))

    def dibujarDestaqueAnimo(self, surface: pygame.Surface) -> None:
        d = self.destaqueAnimo
        if d is None or self.panelCorazones is None:
            return
        entrada = min(1.0, d["t"] / 0.3, max(0.0, (2.6 - d["t"]) / 0.4))
        panel = pygame.Surface(self.panelCorazones.get_size(), pygame.SRCALPHA)
        panel.blit(self.panelCorazones, (0, 0))
        for i in range(self.maxAnimo):
            lleno = i < self.animo
            imagen = self.corazonLleno if lleno else self.corazonVacio
            if imagen is None:
                continue
            centro = (50 + i * 64, 42)
            if i == d["indice"]:
                if d["sube"]:
                    imagen = pygame.transform.smoothscale_by(self.corazonLleno, 1.0 + 0.35 * abs(math.sin(d["t"] * 8.0)))
                elif d["t"] < 0.9:
                    imagen = self.corazonLleno
                    centro = (centro[0] + int(math.sin(d["t"] * 60.0) * 6), centro[1])
            panel.blit(imagen, imagen.get_rect(center=centro))
        panel = pygame.transform.smoothscale_by(panel, 1.8 * (0.6 + 0.4 * entrada))
        panel.set_alpha(int(255 * entrada))
        centro = (self.screen_w // 2, 120) if self.postAbierto is None else (430, 200)
        caja = panel.get_rect(center=centro)
        surface.blit(panel, caja)
        if d["sube"]:
            frase, color, borde = "¡Ganas ánimo!", (220, 255, 210), (30, 110, 60)
        else:
            frase, color, borde = "¡Pierdes ánimo!", (255, 220, 220), (150, 25, 35)
        letrero = self.textoBorde(self.fuenteAviso, frase, color, borde, 4)
        letrero.set_alpha(int(255 * entrada))
        surface.blit(letrero, letrero.get_rect(midtop=(caja.centerx, caja.bottom + 6)))

    def botonesDecision(self):
        ver = pygame.Rect(0, 0, 400, 100)
        seguir = pygame.Rect(0, 0, 400, 100)
        ver.center = (470, 760)
        seguir.center = (1450, 760)
        return ver, seguir

    def sonarVozLinea(self, texto: str) -> float:
        """Reproduce la voz doblada de una línea (si existe). Devuelve su duración en segundos (0 si no hay)."""
        for archivo in vocesEscena.get(texto, ()):
            if hasattr(self.audio, "resolve_voice_path") and self.audio.resolve_voice_path(archivo):
                canal = self.audio.play_voice(archivo, volume_scale=1.0)
                if canal is None:
                    return 0.0  # Voces desactivadas en Opciones
                return float(self.audio.get_voice_duration(archivo))
        return 0.0

    def iniciarEscena(self, lineas: list, alFinal=None, negra: bool = False, enLinea: bool = False) -> None:
        self.soltarCuchara()
        self.arrastrandoCono = False
        self.pensamiento = None
        self.escena = {"lineas": lineas, "i": 0, "t": 0.0, "alFinal": alFinal, "negra": negra, "enLinea": enLinea}

    def avanzarEscena(self) -> None:
        e = self.escena
        if e is None:
            return
        texto = e["lineas"][e["i"]][1]
        if e["t"] < len(texto) / 30.0:
            e["t"] = len(texto) / 30.0
            return
        e["i"] += 1
        e["t"] = 0.0
        if e["i"] >= len(e["lineas"]):
            alFinal = e["alFinal"]
            self.escena = None
            if hasattr(self.audio, "sonarEscritura"):
                self.audio.sonarEscritura(False)
            if alFinal is not None:
                alFinal()

    def cerrarPost(self) -> None:
        if self.postAbierto is None or self.postAbierto["t"] < 0.8:
            return
        lineas = postsExito[self.postAbierto["post"]][2]
        self.pensamiento = {"lineas": lineas, "t": 0.0, "dur": 2.6}
        self.postAbierto = None

    def tinaEn(self, pos) -> Optional[int]:
        for i, tina in enumerate(self.tinas):
            if tina.inflate(30, 40).collidepoint(pos):
                return i
        return None

    def cajaBotar(self) -> pygame.Rect:
        caja = pygame.Rect(0, 0, 210, 64)
        caja.midtop = (self.puntoCono[0] + 10, self.puntoCono[1] + 120)
        return caja

    def botarCono(self) -> None:
        if not self.cono or self.volando or self.conoViaje is not None:
            return
        self.cono = []
        self.arrastrandoCono = False
        self.decir("¡A rehacerlo!", self.puntoCono[0], self.puntoCono[1] - 80, (255, 236, 200), (130, 40, 30))
        if hasattr(self.audio, "play_miss"):
            self.audio.play_miss()

    def conoEquivocado(self) -> bool:
        c = self.cliente
        if not self.cono or c is None or c["estado"] != "esperando":
            return False
        pendientes = list(c["pedido"])
        for bola in self.cono:
            if bola["sabor"] not in pendientes:
                return True
            pendientes.remove(bola["sabor"])
        return False

    def dibujarBotar(self, surface: pygame.Surface) -> None:
        if not self.cono or self.arrastrandoCono or self.conoViaje is not None or self.escena is not None:
            return
        caja = self.cajaBotar()
        if self.conoEquivocado():
            latido = 1.0 + 0.07 * abs(math.sin(self.tiempo * 6.0))
            centro = caja.center
            caja = caja.inflate(int(caja.w * (latido - 1.0)), int(caja.h * (latido - 1.0)))
            caja.center = centro
        if self.botonGris is not None:
            surface.blit(pygame.transform.smoothscale(self.botonGris, caja.size), caja)
        else:
            pygame.draw.rect(surface, (220, 90, 90), caja, border_radius=30)
        letras = self.textoBorde(self.fuenteHud, "Botar (B)", (255, 248, 236), (120, 26, 34), 3)
        if letras.get_width() > caja.w - 30:
            letras = pygame.transform.smoothscale_by(letras, (caja.w - 30) / letras.get_width())
        surface.blit(letras, letras.get_rect(center=(caja.centerx, caja.centery - 2)))

    def cajaCono(self) -> pygame.Rect:
        caja = pygame.Rect(0, 0, 130, 220)
        caja.midtop = (self.puntoCono[0], self.puntoCono[1] - 110)
        return caja

    def cajaCliente(self) -> pygame.Rect:
        return pygame.Rect(1380, 520, 460, 560)

    def avisoCaja(self) -> pygame.Rect:
        return pygame.Rect(self.cajaCelular.x + 20, self.cajaCelular.y + 120, self.cajaCelular.w - 40, 200)

    def botonesAviso(self):
        caja = self.avisoCaja()
        ver = pygame.Rect(caja.x + 14, caja.bottom - 70, (caja.w - 42) // 2, 54)
        callar = pygame.Rect(ver.right + 14, ver.y, ver.w, 54)
        return ver, callar

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and hasattr(event, "pos"):
            self.ratonPos = event.pos
        if self.finalPendiente is not None:
            return
        if self.escena is not None:
            if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.KEYDOWN and event.key != pygame.K_ESCAPE):
                self.avanzarEscena()
            return
        if self.decision is not None:
            ver, seguir = self.botonesDecision()
            if self.decision["t"] < 0.6 and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_t:
                    self.abrirPost()
                elif event.key == pygame.K_x:
                    self.silenciar()
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.decision["opcion"] = 0
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.decision["opcion"] = 1
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    if self.decision["opcion"] == 0:
                        self.abrirPost()
                    else:
                        self.silenciar()
            elif event.type == pygame.MOUSEMOTION:
                if ver.collidepoint(event.pos):
                    self.decision["opcion"] = 0
                elif seguir.collidepoint(event.pos):
                    self.decision["opcion"] = 1
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if ver.collidepoint(event.pos):
                    self.abrirPost()
                elif seguir.collidepoint(event.pos):
                    self.silenciar()
            return
        if self.postAbierto is not None:
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                self.cerrarPost()
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_KP1):
                self.elegirSabor(0)
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.elegirSabor(1)
            elif event.key == pygame.K_SPACE:
                if len(self.cono) + len(self.volando) < 2:
                    self.teclaRaspar = True
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.mandarCono()
            elif event.key in (pygame.K_BACKSPACE, pygame.K_b):
                self.botarCono()
        elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
            if self.teclaRaspar:
                self.soltarCuchara()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.cono and self.cajaBotar().collidepoint(event.pos) and not self.volando:
                self.botarCono()
                return
            if self.cono and self.cajaCono().collidepoint(event.pos) and not self.volando:
                self.arrastrandoCono = True
                return
            tina = self.tinaEn(event.pos)
            if tina is not None and len(self.cono) + len(self.volando) < 2:
                self.elegirSabor(tina)
                self.raspando = True
                self.ultimoPunto = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.arrastrandoCono:
                self.arrastrandoCono = False
                if self.cajaCliente().collidepoint(event.pos) or event.pos[0] > 1380:
                    self.entregar()
                else:
                    self.conoViaje = {"desde": tuple(self.posCono), "hasta": self.puntoCono, "t": 0.0, "entrega": False}
            elif self.raspando:
                self.soltarCuchara()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.botarCono()

    def mandarCono(self) -> None:
        if not self.cono or self.volando or self.cliente is None or self.cliente["estado"] != "esperando":
            return
        self.conoViaje = {"desde": self.puntoCono, "hasta": (1560, 760), "t": 0.0, "entrega": True}

    def elegirSabor(self, cual: int) -> None:
        if cual != self.sabor:
            self.vueltas = 0.0
        self.sabor = cual

    def update_game(self, dt: float) -> None:
        self.tiempo += dt
        if self.introHecha and self.escena is None and self.decision is None and self.postAbierto is None \
                and self.finalPendiente is None:
            self.tiempoJuego += dt
            self.desdeUltimoPost += dt
        self.ajustarMusica()
        if not self.is_finished and self.finalPendiente is None and self.time_left - dt <= 0.0 \
                and self.escena is None and self.decision is None and self.postAbierto is None:
            self.time_left = 0.0
            self.finish_game(self.animo > 2)
            return
        if self.finalPendiente is not None:
            ganado, espera = self.finalPendiente
            espera -= dt
            self.finalPendiente = (ganado, espera)
            self.actualizarAnimaciones(dt)
            if espera <= 0.0:
                self.finalPendiente = None
                self.finish_game(ganado)
            return
        if not self.introHecha:
            self.introHecha = True
            if self.campanitas is not None and hasattr(self.audio, "play_sfx"):
                self.audio.play_sfx(self.campanitas, 1.0)
            self.iniciarEscena(escenaIntro, self.ponerMusica, negra=True)
        if self.escena is not None or self.decision is not None or self.postAbierto is not None:
            self.time_left += dt
            if self.escena is not None:
                e = self.escena
                texto = e["lineas"][e["i"]][1]
                if e.get("vozDe") != e["i"]:
                    # Línea nueva: si tiene voz doblada, suena al aparecer en pantalla
                    e["vozDe"] = e["i"]
                    e["durVoz"] = self.sonarVozLinea(texto)
                e["t"] += dt
                conVoz = e.get("durVoz", 0.0) > 0.0
                if hasattr(self.audio, "sonarEscritura"):
                    # Mientras habla la voz no suena el tecleo de la máquina de escribir
                    self.audio.sonarEscritura(e["t"] < len(texto) / 30.0 and not e.get("enLinea") and not conVoz)
                if e["t"] >= max(len(texto) / 30.0 + 3.0, e.get("durVoz", 0.0) + 0.8):
                    self.avanzarEscena()
            if self.decision is not None:
                self.decision["t"] += dt
            self.actualizarLagrimas(dt)
            self.actualizarCelular(dt)
            self.actualizarAnimaciones(dt)
            return
        if self.cliente is not None and self.cliente["esCompanero"]:
            self.time_left = max(self.time_left, 12.0)
        self.actualizarLagrimas(dt)
        self.actualizarMano(dt)
        self.actualizarCliente(dt)
        self.actualizarCelular(dt)
        self.actualizarAnimaciones(dt)
        for bola in self.cono:
            bola["derretido"] = min(0.6, bola.get("derretido", 0.0) + dt * 0.012)

    def actualizarMano(self, dt: float) -> None:
        tina = self.tinas[self.sabor]
        if self.raspando:
            mx, my = self.ratonPos
            mx = max(tina.left + 10, min(tina.right - 10, mx))
            my = max(tina.top + 8, min(tina.bottom - 8, my))
            if self.ultimoPunto is not None:
                recorrido = math.hypot(mx - self.ultimoPunto[0], my - self.ultimoPunto[1])
                if recorrido > 1.0:
                    self.pasarCuchara(recorrido / 520.0)
                    self.marcarSurco((mx, my))
            self.ultimoPunto = (mx, my)
            objetivo = (mx, my)
        elif self.teclaRaspar:
            self.pasarCuchara(dt * 0.95)
            giro = self.tiempo * 5.0
            objetivo = (tina.centerx + math.cos(giro) * tina.w * 0.28, tina.centery + math.sin(giro) * tina.h * 0.28)
            self.marcarSurco(objetivo)
        elif self.postAbierto is not None:
            objetivo = (1260, 1010)
        else:
            objetivo = (1250, 900)
        rapidez = min(1.0, dt * (24.0 if (self.raspando or self.teclaRaspar) else 8.0))
        self.posMano[0] += (objetivo[0] - self.posMano[0]) * rapidez
        self.posMano[1] += (objetivo[1] - self.posMano[1]) * rapidez
        self.temblor = 0.0
        self.relojSurcos += dt
        if self.relojSurcos >= 0.12:
            self.relojSurcos = 0.0
            for capa in self.surcos:
                capa.fill((255, 255, 255, 246), special_flags=pygame.BLEND_RGBA_MULT)
        if self.arrastrandoCono:
            mx, my = self.ratonPos
            self.posCono = [float(mx), float(my) + 40]

    def actualizarCliente(self, dt: float) -> None:
        if self.cliente is None:
            if getattr(self, "companeroAtendido", False):
                return
            self.esperaCliente -= dt
            if self.esperaCliente <= 0.0:
                self.nuevoCliente()
            return
        c = self.cliente
        c["t"] += dt
        if c["estado"] == "llegando" and c["t"] >= 0.6:
            c["estado"] = "esperando"
            c["t"] = 0.0
            if c["esCompanero"]:
                self.iniciarEscena(escenaReconoce, enLinea=True)
        elif c["estado"] == "esperando" and not c["esCompanero"]:
            c["paciencia"] -= dt
            if c["paciencia"] <= 0.0:
                c["estado"] = "bravo"
                c["t"] = 0.0
                c["respuesta"] = dialogosHinchas[c["tipo"] % len(dialogosHinchas)]["espera"]
                self.cambiarAnimo(-1)
        elif c["estado"] in ("feliz", "triste", "bravo") and c["t"] >= 2.8:
            if c["esCompanero"]:
                self.companeroAtendido = True
            self.cliente = None
            self.esperaCliente = 1.0

    def actualizarCelular(self, dt: float) -> None:
        libre = not (self.raspando or self.teclaRaspar or self.vueltas > 0.0 or self.cono or self.volando
                     or self.arrastrandoCono or self.conoViaje is not None)
        primero = self.cualPost == 0
        if self.cualPost < len(self.momentosPost) and self.tiempoJuego >= self.momentosPost[self.cualPost] \
                and self.tiempoJuego < self.llegaCompanero - 3.0 and self.decision is None and self.postAbierto is None \
                and self.escena is None and (primero or (libre and self.desdeUltimoPost >= 18.0)):
            self.avisarPost()
        if self.postAbierto is not None:
            self.postAbierto["t"] += dt
            if self.postAbierto["t"] >= 6.0:
                self.cerrarPost()
        objetivo = 1.0 if (self.postAbierto is not None or self.decision is not None) else 0.0
        fuera = 1.0 if (objetivo == 0.0 and self.cualPost >= 1 and self.celularCentro < 0.05) else 0.0
        self.celularFuera += (fuera - self.celularFuera) * min(1.0, dt * 5.0)
        self.celularCentro += (objetivo - self.celularCentro) * min(1.0, dt * 7.0)
        if self.pensamiento is not None:
            self.pensamiento["t"] += dt
            if self.pensamiento["t"] >= self.pensamiento["dur"]:
                self.pensamiento = None

    def actualizarAnimaciones(self, dt: float) -> None:
        for v in list(self.volando):
            v["t"] += dt / 0.32
            if v["t"] >= 1.0:
                self.volando.remove(v)
                if len(self.cono) < 2:
                    self.cono.append(dict(v["bola"]))
        if self.conoViaje is not None:
            self.conoViaje["t"] += dt / 0.35
            if self.conoViaje["t"] >= 1.0:
                if self.conoViaje["entrega"]:
                    self.entregar()
                self.conoViaje = None
                self.posCono = list(self.puntoCono)
        for m in list(self.monedas):
            m["t"] += dt / 0.6
            if m["t"] >= 1.0:
                self.monedas.remove(m)
                if hasattr(self.audio, "play_hover"):
                    self.audio.play_hover()
        self.plataMostrada += (self.plata - self.plataMostrada) * min(1.0, dt * 3.0)
        if abs(self.plata - self.plataMostrada) < 20:
            self.plataMostrada = float(self.plata)
        for m in list(self.mensajes):
            m["vida"] -= dt
            if m["vida"] <= 0:
                self.mensajes.remove(m)
        for h in list(self.corazonesVolando):
            h["t"] += dt / 0.9
            if h["t"] >= 1.0:
                self.corazonesVolando.remove(h)

    def finish_game(self, won: bool) -> None:
        yaTerminado = self.is_finished
        if not yaTerminado and hasattr(self.audio, "sonarEscritura"):
            self.audio.sonarEscritura(False)
        super().finish_game(won)
        if yaTerminado:
            return
        if getattr(self, "finLetrero", None):
            self.outro_duration = max(self.outro_duration, self.finLetrero + self.horarioFinal()[-1] + 3.0)
        try:
            self.audio.fadeout_music(1500)
        except pygame.error:
            pass

    def lineasFinales(self) -> list:
        return list(self.ensenanzaFinal["gana" if self.is_won else "pierde"]) + [self.fraseRedes]

    def horarioFinal(self) -> list:
        horario = []
        momento = 0.5
        lineas = self.lineasFinales()
        for i, linea in enumerate(lineas):
            if i == len(lineas) - 1:
                momento += 0.5
            horario.append(momento)
            momento += len(linea) / 24.0 + 0.45
        horario.append(momento)
        return horario

    def dibujarEnsenanzaFinal(self, surface: pygame.Surface) -> None:
        inicio = getattr(self, "finLetrero", None)
        if not inicio or self.outro_timer < inicio:
            return
        t = self.outro_timer - inicio
        if not getattr(self, "sonoApagon", False):
            self.sonoApagon = True
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()
            if hasattr(self, "_trigger_ensenanza_voice"):
                self._trigger_ensenanza_voice()
        if t < 0.3 and int(t * 20) % 2 == 0:
            return
        surface.fill((8, 6, 12))
        if getattr(self, "fuenteFinal", None) is None:
            self.fuenteFinal = self.assets.cargarFuenteCuento(60)
        lineas = self.lineasFinales()
        horario = self.horarioFinal()
        if hasattr(self.audio, "sonarEscritura"):
            self.audio.sonarEscritura(any(horario[i] <= t < horario[i] + len(linea) / 24.0 for i, linea in enumerate(lineas)))
        alto = self.fuenteFinal.get_linesize() + 20
        separacion = 50
        y = 540 - (alto * len(lineas) + separacion) // 2
        for i, linea in enumerate(lineas):
            ultima = i == len(lineas) - 1
            if ultima:
                y += separacion
            letras = min(len(linea), int(max(0.0, t - horario[i]) * 24))
            if letras > 0:
                color = (255, 214, 120) if ultima else (255, 247, 230)
                texto = self.textoBorde(self.fuenteFinal, linea[:letras], color, (60, 50, 70), 3)
                izquierda = 960 - self.fuenteFinal.size(linea)[0] // 2
                surface.blit(texto, texto.get_rect(midleft=(izquierda, y + alto // 2)))
            y += alto
        fin = self.outro_duration - self.outro_timer
        if fin < 0.35:
            surface.fill([int(255 * max(0.0, fin) / 0.35)] * 3, special_flags=pygame.BLEND_RGB_MULT)

    def _render_fuse_timer(self, surface: pygame.Surface) -> None:
        e = self.escena
        if e is not None and e.get("negra"):
            return
        super()._render_fuse_timer(surface)

    def render_game(self, surface: pygame.Surface) -> None:
        surface.blit(self.fondo, (0, 0))
        self.dibujarCliente(surface)
        self.dibujarCarrito(surface)
        self.dibujarPote(surface)
        self.dibujarConoEnCarrito(surface)
        self.dibujarMano(surface)
        for v in self.volando:
            t = v["t"]
            x0, y0 = v["desde"]
            x1, y1 = self.puntoBolaEnCono(len(self.cono))
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t - math.sin(t * math.pi) * 110
            self.dibujarBola(surface, v["bola"], (x, y), 46)
        self.dibujarConoMovil(surface)
        self.dibujarBotar(surface)
        self.dibujarMonedas(surface)
        self.dibujarCelularPequeno(surface)
        self.dibujarHud(surface)
        self.dibujarGuia(surface)
        self.dibujarMensajes(surface)
        if self.celularCentro > 0.01:
            self.dibujarPostAbierto(surface)
        self.dibujarPensamiento(surface)
        self.dibujarDestaqueAnimo(surface)
        self.dibujarLagrimas(surface)
        if self.escena is not None:
            self.dibujarEscena(surface)

    def textoEscenaActual(self):
        e = self.escena
        quien, texto = e["lineas"][e["i"]]
        letras = min(len(texto), int(e["t"] * 30))
        return quien, texto, texto[:letras], letras >= len(texto)

    def dibujarAyudaEscena(self, surface: pygame.Surface, punto) -> None:
        e = self.escena
        ayuda = self.textoBorde(self.fuenteChica, "Clic o cualquier tecla para seguir", (255, 248, 236), (40, 30, 50), 2)
        ayuda.set_alpha(int(160 + 95 * abs(math.sin(e["t"] * 3.0))))
        surface.blit(ayuda, ayuda.get_rect(midtop=punto))

    def dibujarEscena(self, surface: pygame.Surface) -> None:
        e = self.escena
        quien, texto = e["lineas"][e["i"]]
        if e.get("enLinea"):
            if not quien.startswith("Andrés"):
                _, _, visible, completo = self.textoEscenaActual()
                caja = self.dibujarNube(surface, self.partirEnLineas(self.fuentePensamiento, texto, 1100), visible, 1.0)
                if completo:
                    self.dibujarAyudaEscena(surface, (caja.centerx, caja.bottom + 12))
            return
        negra = e.get("negra", False) and e["i"] < len(e["lineas"]) - 1
        if negra:
            surface.fill((6, 5, 10))
        else:
            velo = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            entrada = 1.0
            if e.get("negra", False):
                entrada = max(0.0, 1.0 - e["t"] / 0.8)
            velo.fill((6, 5, 10, int(190 + 65 * entrada)))
            surface.blit(velo, (0, 0))
        letras = min(len(texto), int(e["t"] * 30))
        lineas = self.partirEnLineas(self.fuenteEscena, texto, 1200)
        alto = self.fuenteEscena.get_linesize()
        esAndres = quien.startswith("Andrés")
        foto = None
        if esAndres and self.companeroImg is not None:
            foto = pygame.transform.smoothscale(self.companeroImg["avatar"], (170, 170))
            mascara = pygame.Surface(foto.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(mascara, (255, 255, 255, 255), (85, 85), 85)
            foto.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        bloque = alto * len(lineas) + 70
        y = 540 - bloque // 2 + (60 if foto is not None else 0)
        if foto is not None:
            centroFoto = (960, y - 110)
            surface.blit(foto, foto.get_rect(center=centroFoto))
            pygame.draw.circle(surface, (255, 248, 236), centroFoto, 86, 4)
        if quien:
            color = (150, 200, 255) if esAndres else (255, 214, 120)
            nombre = self.textoBorde(self.fuenteHablante, quien, color, (40, 30, 50), 3)
            surface.blit(nombre, nombre.get_rect(midtop=(960, y)))
            y += 70
        restantes = letras
        for linea in lineas:
            parte = linea[:max(0, restantes)]
            restantes -= len(linea) + 1
            if parte:
                render = self.textoBorde(self.fuenteEscena, parte, (255, 248, 236), (40, 30, 50), 3)
                surface.blit(render, (960 - self.fuenteEscena.size(linea)[0] // 2, y))
            y += alto
        if letras >= len(texto):
            ayuda = self.textoBorde(self.fuenteChica, "Clic o cualquier tecla para seguir", (255, 248, 236), (40, 30, 50), 2)
            ayuda.set_alpha(int(160 + 95 * abs(math.sin(e["t"] * 3.0))))
            surface.blit(ayuda, ayuda.get_rect(midtop=(960, y + 30)))

    def dibujarCarrito(self, surface: pygame.Surface) -> None:
        if self.carrito is not None:
            surface.blit(self.carrito, self.cajaCarrito)
        else:
            cuerpo = pygame.Rect(560, 720, 820, 400)
            pygame.draw.rect(surface, (238, 238, 236), cuerpo, border_radius=36)
            pygame.draw.rect(surface, (60, 44, 70), cuerpo, width=5, border_radius=36)
            for i, tina in enumerate(self.tinas):
                pygame.draw.ellipse(surface, (190, 196, 204), tina.inflate(26, 22))
                pygame.draw.ellipse(surface, sabores[i]["color"], tina)
        orden = sorted(range(len(self.tinas)), key=lambda k: k == self.sabor)
        for i in orden:
            tina = self.tinas[i]
            if self.raspados is not None:
                cuadro = 0
                if i == self.sabor and self.raspandoAhora():
                    avance = min(1.0, self.vueltas / 2.3)
                    cuadro = 1 + min(4, int(avance * 5))
                imagen = self.raspados[i][cuadro]
                temblor = int(math.sin(self.tiempo * 40.0) * self.temblor) if cuadro else 0
                if getattr(self, "lugarPotes", None):
                    x, y = self.lugarPotes[i]
                    surface.blit(imagen, (x + temblor, y))
                else:
                    w, h = self.tamCuadro
                    surface.blit(imagen, (tina.centerx + temblor - w // 2, tina.centery + int(h * 0.11) - h // 2))
            else:
                capa = self.surcos[i].copy()
                capa.blit(self.mascarasTina[i], (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                surface.blit(capa, tina)
        for i, tina in enumerate(self.tinas):
            etiqueta = self.textoBorde(self.fuenteHud, f"{i + 1} · {sabores[i]['nombre'].capitalize()}", (255, 248, 236), (96, 56, 30), 3)
            surface.blit(etiqueta, etiqueta.get_rect(midtop=(tina.centerx, min(tina.bottom + 30, self.screen_h - 60))))
        if (self.raspando or self.teclaRaspar or self.vueltas > 0.0) and self.anillos:
            tina = self.tinas[self.sabor]
            progreso = self.calidadActual()
            if progreso >= 1.0:
                cuadro = 5 if int(self.tiempo * 6) % 2 == 0 else 4
            elif progreso <= 0.0:
                cuadro = 0
            else:
                cuadro = 1 + min(2, int(progreso * 3))
            anillo = self.anillosTina[self.sabor][cuadro]
            anillo.set_alpha(225)
            surface.blit(anillo, anillo.get_rect(center=tina.center))
        elif self.raspando or self.teclaRaspar or self.vueltas > 0.0:
            tina = self.tinas[self.sabor]
            progreso = self.calidadActual()
            caja = tina.inflate(60, 60)
            pygame.draw.arc(surface, (255, 248, 236), caja, 0, 2 * math.pi, 8)
            color = (230, 90, 70) if progreso < 0.45 else (240, 190, 60) if progreso < 0.85 else (80, 190, 110)
            if progreso > 0:
                pygame.draw.arc(surface, color, caja, math.pi / 2, math.pi / 2 + 2 * math.pi * progreso, 8)

    def puntoBolaEnCono(self, indice: int):
        return (self.puntoCono[0], self.puntoCono[1] - 8 - indice * 46)

    def dibujarConoEnCarrito(self, surface: pygame.Surface) -> None:
        if self.arrastrandoCono or self.conoViaje is not None:
            return
        x, y = self.puntoCono
        if self.utensilios is not None:
            cono = self.utensilios["cono"]
            surface.blit(cono, cono.get_rect(midtop=(x, y - 6)))
        else:
            puntos = [(x - 46, y), (x + 46, y), (x, y + 150)]
            pygame.draw.polygon(surface, (222, 168, 96), puntos)
            pygame.draw.polygon(surface, (96, 56, 30), puntos, 4)
        for i, bola in enumerate(self.cono):
            self.dibujarBola(surface, bola, self.puntoBolaEnCono(i), 48)

    def dibujarConoMovil(self, surface: pygame.Surface) -> None:
        if not (self.arrastrandoCono or self.conoViaje is not None):
            return
        if self.conoViaje is not None:
            t = self.conoViaje["t"]
            t = t * t * (3 - 2 * t)
            x0, y0 = self.conoViaje["desde"]
            x1, y1 = self.conoViaje["hasta"]
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t - math.sin(t * math.pi) * 80
        else:
            x, y = self.posCono
        if self.utensilios is not None:
            cono = self.utensilios["cono"]
            surface.blit(cono, cono.get_rect(midtop=(int(x), int(y) - 6)))
        else:
            puntos = [(x - 44, y), (x + 44, y), (x, y + 140)]
            pygame.draw.polygon(surface, (222, 168, 96), puntos)
            pygame.draw.polygon(surface, (96, 56, 30), puntos, 4)
        for i, bola in enumerate(self.cono):
            self.dibujarBola(surface, bola, (x, y - 8 - i * 46), 48)

    def dibujarBola(self, surface: pygame.Surface, bola: dict, centro, radio: int) -> None:
        calidad = max(0.0, bola["calidad"] - bola.get("derretido", 0.0))
        datos = sabores[bola["sabor"]]
        radio = int(radio * (0.72 + 0.28 * calidad))
        if self.utensilios is not None:
            imagen = self.utensilios["bolas"][bola["sabor"]]
            imagen = pygame.transform.smoothscale(imagen, (radio * 2, int(radio * 2 * (0.78 + 0.22 * calidad))))
            surface.blit(imagen, imagen.get_rect(center=(int(centro[0]), int(centro[1]))))
            return
        pygame.draw.circle(surface, datos["color"], (int(centro[0]), int(centro[1])), radio)
        pygame.draw.circle(surface, (90, 50, 60), (int(centro[0]), int(centro[1])), radio, 3)

    def raspandoAhora(self) -> bool:
        return self.raspando or self.teclaRaspar or self.vueltas > 0.0

    def dibujarBolaEnCuchara(self, surface: pygame.Surface, punta) -> None:
        if self.vueltas <= 0.0:
            return
        avance = min(1.0, self.vueltas / 2.3)
        self.dibujarBola(surface, {"sabor": self.sabor, "calidad": self.calidadActual()}, punta, int(14 + 32 * avance))

    def dibujarMano(self, surface: pygame.Surface) -> None:
        if self.raspados is not None and self.raspandoAhora():
            return
        temblor = math.sin(self.tiempo * 40.0) * self.temblor
        x, y = self.posMano[0] + temblor, self.posMano[1]
        if self.mano is not None:
            w, h = self.anchoMano
            surface.blit(self.mano, (int(x - w * 0.142), int(y - h * 0.133)))
        else:
            pygame.draw.line(surface, (190, 190, 200), (x + 150, y + 180), (x, y), 12)
            pygame.draw.circle(surface, (200, 204, 212), (int(x), int(y)), 32)
        self.dibujarBolaEnCuchara(surface, (x, y))

    def dibujarPote(self, surface: pygame.Surface) -> None:
        nivel = min(1.0, self.plataMostrada / float(metaPlata))
        if self.potes is not None:
            imagen = self.potes[min(len(self.potes) - 1, int(math.ceil(nivel * (len(self.potes) - 1))))]
        elif self.poteVacio is not None:
            imagen = self.poteLleno if nivel >= 0.5 else self.poteVacio
        else:
            return
        caja = imagen.get_rect(midbottom=self.puntoPote)
        surface.blit(imagen, caja)
        texto = self.textoBorde(self.fuenteHud, self.plataTexto(self.plataMostrada), (255, 248, 236), (40, 110, 60), 3)
        surface.blit(texto, texto.get_rect(midtop=(caja.centerx, caja.bottom + 4)))

    def dibujarMonedas(self, surface: pygame.Surface) -> None:
        if self.poteVacio is not None:
            destino = self.poteVacio.get_rect(midbottom=self.puntoPote).midtop
        else:
            destino = self.puntoPote
        for m in self.monedas:
            t = m["t"]
            if t < 0.0:
                continue
            x0, y0 = m["desde"]
            x = x0 + (destino[0] - x0) * t
            y = y0 + (destino[1] + 20 - y0) * t - math.sin(t * math.pi) * 220
            if self.dinero is not None:
                imagen = pygame.transform.rotate(self.dinero[m["tipo"]], m["giro"] * t)
                surface.blit(imagen, imagen.get_rect(center=(int(x), int(y))))
            else:
                pygame.draw.circle(surface, (236, 190, 70), (int(x), int(y)), 16)
                pygame.draw.circle(surface, (130, 90, 30), (int(x), int(y)), 16, 3)

    def dibujarCliente(self, surface: pygame.Surface) -> None:
        c = self.cliente
        if c is None:
            return
        entrada = min(1.0, c["t"] / 0.6) if c["estado"] == "llegando" else 1.0
        salida = 0.0
        if c["estado"] in ("feliz", "triste", "bravo") and c["t"] > 2.2:
            salida = min(1.0, (c["t"] - 2.2) / 0.6)
        x = 1610 + (1 - entrada) * 420 + salida * 420
        feliz = c["estado"] in ("feliz", "confiesa")
        imagen = None
        servido = c.get("servido")
        if c["esCompanero"] and self.companeroImg is not None:
            imagen = self.companeroImg["cliente"]
            if feliz and servido and self.companeroHelado is not None:
                imagen = self.companeroHelado
        elif self.hinchas is not None and c["tipo"] >= 0:
            num_h = len(self.hinchas["espera"])
            idx = c["tipo"] if c["tipo"] < num_h else (c["tipo"] % num_h)
            imagen = self.hinchas["feliz" if feliz else "espera"][idx]
            if feliz and servido and self.pedidosClientes is not None and c["tipo"] < len(self.pedidosClientes) and servido in ordenCombos:
                imagen = self.pedidosClientes[c["tipo"]][ordenCombos.index(servido)]
        if imagen is not None:
            caja = imagen.get_rect(midbottom=(int(x), self.screen_h + 2))
            surface.blit(imagen, caja)
            arriba = caja.top
        else:
            cuerpo = pygame.Rect(0, 0, 230, 300)
            cuerpo.midbottom = (int(x), self.screen_h + 40)
            pygame.draw.rect(surface, (250, 250, 250), cuerpo, border_radius=60)
            cabeza = (cuerpo.centerx, cuerpo.y - 60)
            pygame.draw.circle(surface, (196, 140, 100), cabeza, 70)
            arriba = cabeza[1] - 70
        punta = (int(x) - 40, arriba - 6)
        e = self.escena
        if e is not None and e.get("enLinea") and c["esCompanero"]:
            quien, texto = e["lineas"][e["i"]]
            if quien.startswith("Andrés"):
                _, _, visible, completo = self.textoEscenaActual()
                rect = self.dibujarGlobo(surface, texto, punta, 480, 0, visible)
                if completo:
                    self.dibujarAyudaEscena(surface, (rect.centerx, rect.bottom + 6))
            return
        if self.celularCentro > 0.05 or self.escena is not None:
            return
        if c["estado"] == "esperando":
            self.dibujarPedido(surface, c, punta)
        elif c["respuesta"]:
            self.dibujarGlobo(surface, c["respuesta"], punta, 480)

    def dibujarGlobo(self, surface: pygame.Surface, texto: str, centro, anchoMax: int, extra: int = 0,
                     visible: Optional[str] = None) -> pygame.Rect:
        lineas = self.partirEnLineas(self.fuenteGlobo, texto, anchoMax)
        textos = [self.fuenteGlobo.render(l, True, (110, 62, 36)) for l in lineas]
        if visible is not None:
            restantes = len(visible)
            parciales = []
            for linea in lineas:
                parte = linea[:max(0, restantes)]
                restantes -= len(linea) + 1
                parciales.append(self.fuenteGlobo.render(parte, True, (110, 62, 36)))
            anchos = textos
            textos = parciales
        else:
            anchos = textos
        ancho = max(max(t.get_width() for t in anchos) + 80, 300 if extra else 0)
        cuerpo = sum(t.get_height() for t in anchos) + 44 + extra
        alto = int(cuerpo / 0.79)
        if self.globo is not None:
            caja = pygame.transform.smoothscale(self.globo, (ancho, alto))
        else:
            caja = pygame.Surface((ancho, alto), pygame.SRCALPHA)
            pygame.draw.rect(caja, (255, 250, 238), caja.get_rect(), border_radius=28)
        rect = caja.get_rect(midbottom=centro)
        rect.right = min(rect.right, self.screen_w - 20)
        surface.blit(caja, rect)
        y = rect.y + 22
        for t, molde in zip(textos, anchos):
            surface.blit(t, (rect.centerx - molde.get_width() // 2, y))
            y += molde.get_height()
        self.finTextoGlobo = y
        return rect

    def dibujarPedido(self, surface: pygame.Surface, c: dict, punta) -> None:
        rect = self.dibujarGlobo(surface, c["frase"], punta, 420, 64)
        fila = self.finTextoGlobo + 32
        x0 = rect.centerx - 34 * (len(c["pedido"]) - 1)
        for i, s in enumerate(c["pedido"]):
            centro = (x0 + i * 68, fila)
            self.dibujarBola(surface, {"sabor": s, "calidad": 1.0}, centro, 26)
        if not c["esCompanero"]:
            centro = (rect.x - 52, rect.y + int(rect.h * 0.79) // 2 + 6)
            segundos = int(math.ceil(max(0.0, c["paciencia"])))
            urgente = segundos <= 5
            temblor = int(math.sin(self.tiempo * 30.0) * 4) if urgente else 0
            if self.cronometro is not None:
                reloj = self.cronometro.get_rect(center=(centro[0] + temblor, centro[1] - int(self.cronometro.get_height() * 0.09)))
                surface.blit(self.cronometro, reloj)
            else:
                pygame.draw.circle(surface, (255, 250, 238), (centro[0] + temblor, centro[1]), 32)
                pygame.draw.circle(surface, (110, 70, 50), (centro[0] + temblor, centro[1]), 32, 4)
            color = (200, 40, 40) if urgente else (60, 40, 30)
            numero = self.fuenteHud.render(str(segundos), True, color)
            surface.blit(numero, numero.get_rect(center=(centro[0] + temblor, centro[1] + 2)))

    def pasoActual(self):
        c = self.cliente
        if self.postAbierto is not None or self.finalPendiente is not None or self.decision is not None \
                or self.escena is not None:
            return None
        if c is None or c["estado"] != "esperando":
            return None
        if self.raspando or self.teclaRaspar:
            tina = self.tinas[self.sabor]
            if self.calidadActual() >= 1.0:
                return ("¡Perfecta! Suelta", (tina.centerx, tina.top - 20))
            return ("¡Sigue raspando!", (tina.centerx, tina.top - 20))
        if self.volando:
            return None
        if self.conoEquivocado():
            return ("¡Ese no es! Bótalo y hazlo otra vez", self.cajaBotar().midtop)
        faltan = self.faltantes()
        if faltan and len(self.cono) < 2:
            tina = self.tinas[faltan[0]]
            texto = f"Mantén presionado y raspa el {sabores[faltan[0]]['nombre']}"
            return (texto, (tina.centerx, tina.top - 20))
        if self.conoEquivocado():
            return ("¡Ese no es! Bótalo y hazlo otra vez", self.cajaBotar().midtop)
        if self.cono:
            return ("¡Arrastra el cono al cliente!", self.cajaCono().midtop)
        return None

    def dibujarGuia(self, surface: pygame.Surface) -> None:
        paso = self.pasoActual()
        if paso is None:
            return
        texto, punto = paso
        if punto is None:
            letrero = self.textoBorde(self.fuenteGuia, texto, (255, 248, 236), (96, 56, 30), 4)
            caja = self.avisoCaja()
            surface.blit(letrero, letrero.get_rect(midleft=(self.cajaCelular.right + 20, caja.bottom - 40)))
            return
        salto = int(abs(math.sin(self.tiempo * 5.0)) * 14)
        x, y = punto
        if self.flecha is not None:
            surface.blit(self.flecha, self.flecha.get_rect(midbottom=(x, y - salto)))
            arriba = y - salto - self.flecha.get_height()
        else:
            pygame.draw.polygon(surface, (255, 220, 90), [(x - 18, y - 30 - salto), (x + 18, y - 30 - salto), (x, y - salto)])
            arriba = y - 30 - salto
        letrero = self.textoBorde(self.fuenteGuia, texto, (255, 248, 236), (96, 56, 30), 4)
        caja = letrero.get_rect(midbottom=(x, arriba - 4))
        caja.clamp_ip(pygame.Rect(440, 120, self.screen_w - 460, self.screen_h))
        surface.blit(letrero, caja)

    def corrimientoCelular(self) -> int:
        return -int((self.cajaCelular.right + 40) * self.celularFuera)

    def dibujarCelularPequeno(self, surface: pygame.Surface) -> None:
        if self.celularCentro > 0.01 or self.celularFuera > 0.99:
            return
        dx = self.corrimientoCelular()
        self.dibujarPantallaApp(surface, self.pantalla.move(dx, 0), None)
        if self.marcoCelular is not None:
            surface.blit(self.marcoCelular, self.cajaCelular.move(dx, 0))
        if self.aviso is not None:
            self.dibujarAviso(surface)

    def dibujarAviso(self, surface: pygame.Surface) -> None:
        a = self.aviso
        caja = self.avisoCaja()
        temblor = int(math.sin(a["t"] * 50.0) * 5) if (a["t"] % 1.0) < 0.3 else 0
        tarjeta = caja.move(temblor, 0)
        pygame.draw.rect(surface, (255, 255, 255), tarjeta, border_radius=18)
        pygame.draw.rect(surface, (40, 80, 140), tarjeta, width=4, border_radius=18)
        partes = companero["nombre"].split()
        titulo = self.fuenteAppNombre.render(partes[0] + " " + partes[1], True, (20, 40, 70))
        surface.blit(titulo, (tarjeta.x + 18, tarjeta.y + 12))
        sub = self.fuenteChica.render("tu compañero del colegio publicó:", True, (90, 100, 120))
        surface.blit(sub, (tarjeta.x + 18, tarjeta.y + 44))
        vista = postsExito[a["post"]][0]
        corto = self.partirEnLineas(self.fuenteChica, vista, tarjeta.w - 36)[0] + "..."
        surface.blit(self.fuenteChica.render(corto, True, (30, 30, 40)), (tarjeta.x + 18, tarjeta.y + 72))
        ver, callar = self.botonesAviso()
        latido = 1.0 + 0.08 * abs(math.sin(a["t"] * 6.0))
        for boton, texto, imagen, contorno in ((ver, "Ver (T)", self.botonAzul, (70, 30, 110)),
                                               (callar, "Silenciar (X)", self.botonGris, (120, 26, 34))):
            caja = boton.move(temblor, 0)
            if boton is callar:
                centro = caja.center
                caja = caja.inflate(int(caja.w * (latido - 1.0)), int(caja.h * (latido - 1.0)))
                caja.center = centro
            if imagen is not None:
                fondo = pygame.transform.smoothscale(imagen, caja.size)
                surface.blit(fondo, caja)
            else:
                pygame.draw.rect(surface, (60, 90, 150), caja, border_radius=24)
            letras = self.textoBorde(self.fuenteChica, texto, (255, 248, 236), contorno, 2)
            surface.blit(letras, letras.get_rect(center=(caja.centerx, caja.centery - 2)))
        resto = 1.0 - a["t"] / a["dur"]
        pygame.draw.rect(surface, (230, 120, 60), (tarjeta.x + 18, tarjeta.bottom - 10, int((tarjeta.w - 36) * resto), 5), border_radius=3)

    def dibujarPantallaApp(self, surface: pygame.Surface, pantalla: pygame.Rect, post: Optional[int]) -> None:
        if self.appBase is not None:
            surface.blit(pygame.transform.smoothscale(self.appBase, pantalla.size), pantalla)
            if post is not None:
                self.llenarPostApp(surface, pantalla, post)
            return
        pygame.draw.rect(surface, (243, 242, 238), pantalla, border_radius=26)
        if post is None:
            return
        fuente = self.assets.cargarFuenteTitulo(22)
        y = pantalla.y + 40
        for linea in self.partirEnLineas(fuente, postsExito[post][0], pantalla.w - 40):
            surface.blit(fuente.render(linea, True, (30, 30, 40)), (pantalla.x + 20, y))
            y += fuente.get_linesize()

    def llenarPostApp(self, surface: pygame.Surface, pantalla: pygame.Rect, post: int) -> None:
        texto, reacciones, _ = postsExito[post]
        w, h = pantalla.size

        def caja(x0, y0, x1, y1):
            return pygame.Rect(pantalla.x + int(w * x0), pantalla.y + int(h * y0), int(w * (x1 - x0)), int(h * (y1 - y0)))

        blanco = (253, 253, 252)
        radio = int(w * 0.075)
        centro = (pantalla.x + int(w * 0.168), pantalla.y + int(h * 0.285))
        if self.companeroImg is not None:
            foto = pygame.transform.smoothscale(self.companeroImg["avatar"], (radio * 2, radio * 2))
            mascara = pygame.Surface(foto.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(mascara, (255, 255, 255, 255), (radio, radio), radio)
            foto.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surface.blit(foto, foto.get_rect(center=centro))
            pygame.draw.circle(surface, (70, 50, 90), centro, radio, 2)

        zonaNombre = caja(0.262, 0.255, 0.93, 0.31)
        pygame.draw.rect(surface, blanco, zonaNombre)
        fuenteNombre = self.assets.cargarFuenteTitulo(max(12, int(h * 0.019)))
        fuenteCargo = self.assets.cargarFuenteTitulo(max(10, int(h * 0.014)))
        nombre = fuenteNombre.render(companero["nombre"], True, (20, 30, 50))
        if nombre.get_width() > zonaNombre.w:
            nombre = pygame.transform.smoothscale_by(nombre, zonaNombre.w / nombre.get_width())
        surface.blit(nombre, (zonaNombre.x, zonaNombre.y))
        cargo = fuenteCargo.render(companero["cargo"], True, (100, 105, 120))
        if cargo.get_width() > zonaNombre.w:
            cargo = pygame.transform.smoothscale_by(cargo, zonaNombre.w / cargo.get_width())
        surface.blit(cargo, (zonaNombre.x, zonaNombre.y + nombre.get_height() + 2))

        zonaTexto = caja(0.09, 0.325, 0.91, 0.398)
        pygame.draw.rect(surface, blanco, zonaTexto)
        tam = max(11, int(h * 0.019))
        while True:
            fuente = self.assets.cargarFuenteTitulo(tam)
            lineas = self.partirEnLineas(fuente, texto, zonaTexto.w)
            if len(lineas) * fuente.get_linesize() <= zonaTexto.h or tam <= 10:
                break
            tam -= 1
        y = zonaTexto.y
        for linea in lineas:
            surface.blit(fuente.render(linea, True, (30, 30, 40)), (zonaTexto.x, y))
            y += fuente.get_linesize()

        zonaFoto = caja(0.1, 0.41, 0.9, 0.666)
        if self.fotosPosts is not None:
            imagen = self.fotosPosts[post % len(self.fotosPosts)]
            escala = max(zonaFoto.w / imagen.get_width(), zonaFoto.h / imagen.get_height())
            imagen = pygame.transform.smoothscale_by(imagen, escala)
            area = pygame.Rect(0, 0, zonaFoto.w, zonaFoto.h)
            area.center = imagen.get_rect().center
            surface.blit(imagen, zonaFoto.topleft, area)
            pygame.draw.rect(surface, (70, 50, 90), zonaFoto, 2, border_radius=6)

        zonaReacciones = caja(0.1, 0.668, 0.9, 0.688)
        fuente = self.assets.cargarFuenteTitulo(max(10, int(h * 0.014)))
        letras = fuente.render(reacciones, True, (100, 105, 120))
        if letras.get_width() > zonaReacciones.w:
            letras = pygame.transform.smoothscale_by(letras, zonaReacciones.w / letras.get_width())
        surface.blit(letras, letras.get_rect(midleft=zonaReacciones.midleft))

    def dibujarPostAbierto(self, surface: pygame.Surface) -> None:
        c = self.celularCentro
        suave = c * c * (3 - 2 * c)
        velo = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        velo.fill((20, 26, 40, int(150 * suave)))
        surface.blit(velo, (0, 0))
        escala = 1.0 + 0.32 * suave
        caja = self.cajaCelular.move(self.corrimientoCelular(), 0)
        ancho, alto = int(caja.w * escala), int(caja.h * escala)
        cx = caja.centerx + (960 - caja.centerx) * suave
        cy = caja.centery + (540 - caja.centery) * suave
        grande = pygame.Rect(0, 0, ancho, alto)
        grande.center = (int(cx), int(cy))
        pantalla = pygame.Rect(grande.x + int(grande.w * 0.075), grande.y + int(grande.h * 0.035),
                               int(grande.w * 0.85), int(grande.h * 0.93))
        mostrarPost = self.postAbierto is not None
        post = self.postAbierto["post"] if mostrarPost else max(0, self.cualPost - 1)
        self.dibujarPantallaApp(surface, pantalla, post if mostrarPost else None)
        if not mostrarPost:
            self.dibujarNotificacion(surface, pantalla, post)
        if self.marcoCelular is not None:
            surface.blit(pygame.transform.smoothscale(self.marcoCelular, grande.size), grande)
        if self.postAbierto is not None:
            self.dibujarAyudaCelular(surface, grande, suave)
        elif self.decision is not None:
            self.dibujarDecision(surface, grande)

    def dibujarNotificacion(self, surface: pygame.Surface, pantalla: pygame.Rect, post: int) -> None:
        tarjeta = pygame.Rect(pantalla.x + 18, pantalla.y + int(pantalla.h * 0.17), pantalla.w - 36, int(pantalla.h * 0.3))
        pygame.draw.rect(surface, (255, 255, 255), tarjeta, border_radius=18)
        pygame.draw.rect(surface, (40, 80, 140), tarjeta, width=4, border_radius=18)
        if self.companeroImg is not None:
            foto = pygame.transform.smoothscale(self.companeroImg["avatar"], (70, 70))
            mascara = pygame.Surface(foto.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(mascara, (255, 255, 255, 255), (35, 35), 35)
            foto.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surface.blit(foto, (tarjeta.x + 16, tarjeta.y + 16))
        nombre = self.fuenteAppNombre.render(companero["nombre"], True, (20, 40, 70))
        if nombre.get_width() > tarjeta.w - 110:
            nombre = pygame.transform.smoothscale_by(nombre, (tarjeta.w - 110) / nombre.get_width())
        surface.blit(nombre, (tarjeta.x + 98, tarjeta.y + 22))
        sub = self.fuenteChica.render("tu compañero del colegio publicó:", True, (90, 100, 120))
        if sub.get_width() > tarjeta.w - 110:
            sub = pygame.transform.smoothscale_by(sub, (tarjeta.w - 110) / sub.get_width())
        surface.blit(sub, (tarjeta.x + 98, tarjeta.y + 56))
        fuente = self.assets.cargarFuenteTitulo(20)
        y = tarjeta.y + 98
        for linea in self.partirEnLineas(fuente, postsExito[post][0], tarjeta.w - 32):
            if y + fuente.get_linesize() > tarjeta.bottom - 8:
                break
            surface.blit(fuente.render(linea, True, (30, 30, 40)), (tarjeta.x + 16, y))
            y += fuente.get_linesize()

    def dibujarDecision(self, surface: pygame.Surface, grande: pygame.Rect) -> None:
        d = self.decision
        entrada = min(1.0, d["t"] / 0.35)
        pregunta = self.textoBorde(self.fuenteAviso, "¿Ves la publicación?", (255, 236, 120), (140, 25, 35), 5)
        latido = 1.0 + 0.05 * math.sin(d["t"] * 7.0)
        pregunta = pygame.transform.smoothscale_by(pregunta, (0.6 + 0.4 * entrada) * latido)
        pregunta.set_alpha(int(255 * entrada))
        surface.blit(pregunta, pregunta.get_rect(center=(grande.centerx, grande.top + int(grande.h * 0.6))))
        ver, seguir = self.botonesDecision()
        for i, (caja, texto, imagen, contorno, pie) in enumerate((
                (ver, "Ver publicación (T)", self.botonAzul, (70, 30, 110), "Te va a doler..."),
                (seguir, "Seguir vendiendo (X)", self.botonNaranja, (150, 70, 20), "Tus clientes te esperan"))):
            elegido = d["opcion"] == i
            escala = (1.08 if elegido else 1.0) * (0.6 + 0.4 * entrada)
            dibujo = caja.inflate(int(caja.w * (escala - 1.0)), int(caja.h * (escala - 1.0)))
            dibujo.center = caja.center
            fondo = self.botonGris if elegido else imagen
            if fondo is not None:
                surface.blit(pygame.transform.smoothscale(fondo, dibujo.size), dibujo)
            else:
                pygame.draw.rect(surface, (90, 120, 180), dibujo, border_radius=40)
            letras = self.textoBorde(self.fuenteGuia, texto, (255, 248, 236), (120, 26, 34) if elegido else contorno, 3)
            if letras.get_width() > dibujo.w - 40:
                letras = pygame.transform.smoothscale_by(letras, (dibujo.w - 40) / letras.get_width())
            surface.blit(letras, letras.get_rect(center=(dibujo.centerx, dibujo.centery - 3)))
            nota = self.textoBorde(self.fuenteChica, pie, (255, 248, 236), (40, 40, 70), 2)
            surface.blit(nota, nota.get_rect(midtop=(dibujo.centerx, dibujo.bottom + 10)))

    def botonGuardarCelular(self, grande: pygame.Rect) -> pygame.Rect:
        caja = pygame.Rect(0, 0, 400, 96)
        caja.midleft = (grande.right + 70, grande.centery + 150)
        return caja

    def dibujarAyudaCelular(self, surface: pygame.Surface, grande: pygame.Rect, suave: float) -> None:
        lineas = ["Te quedaste mirando el celular...", "y los clientes siguen esperando."]
        y = grande.centery - 150
        for linea in lineas:
            texto = self.textoBorde(self.fuenteGuia, linea, (255, 248, 236), (40, 40, 70), 4)
            texto.set_alpha(int(255 * suave))
            surface.blit(texto, texto.get_rect(midleft=(grande.right + 60, y)))
            y += texto.get_height() + 6
        if self.postAbierto["t"] < 0.8:
            return
        caja = self.botonGuardarCelular(grande)
        latido = 1.0 + 0.06 * abs(math.sin(self.postAbierto["t"] * 5.0))
        centro = caja.center
        caja = caja.inflate(int(caja.w * (latido - 1.0)), int(caja.h * (latido - 1.0)))
        caja.center = centro
        if self.botonNaranja is not None:
            surface.blit(pygame.transform.smoothscale(self.botonNaranja, caja.size), caja)
        else:
            pygame.draw.rect(surface, (240, 150, 60), caja, border_radius=40)
        letras = self.textoBorde(self.fuenteGuia, "Guardar el celular", (255, 248, 236), (150, 70, 20), 3)
        surface.blit(letras, letras.get_rect(center=(caja.centerx, caja.centery - 3)))
        tecla = self.textoBorde(self.fuenteChica, "o pulsa cualquier tecla", (255, 248, 236), (40, 40, 70), 2)
        surface.blit(tecla, tecla.get_rect(midtop=(caja.centerx, caja.bottom + 10)))

    def dibujarPensamiento(self, surface: pygame.Surface) -> None:
        p = self.pensamiento
        if p is None:
            return
        visible = min(1.0, p["t"] / 0.3, (p["dur"] - p["t"]) / 0.3)
        self.dibujarNube(surface, p["lineas"], None, max(0.0, visible))

    def dibujarNube(self, surface: pygame.Surface, lineas: list, visible: Optional[str], alfa: float) -> pygame.Rect:
        moldes = [self.textoBorde(self.fuentePensamiento, l, (255, 248, 236), (60, 50, 80), 3) for l in lineas]
        textos = moldes
        if visible is not None:
            restantes = len(visible)
            textos = []
            for linea in lineas:
                parte = linea[:max(0, restantes)]
                restantes -= len(linea) + 1
                textos.append(self.textoBorde(self.fuentePensamiento, parte, (255, 248, 236), (60, 50, 80), 3))
        alto = sum(t.get_height() for t in moldes) + 40
        ancho = max(t.get_width() for t in moldes) + 90
        nube = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        pygame.draw.rect(nube, (60, 70, 110, 210), nube.get_rect(), border_radius=min(alto // 2, 60))
        y = 20
        for texto, molde in zip(textos, moldes):
            nube.blit(texto, (ancho // 2 - molde.get_width() // 2, y))
            y += molde.get_height()
        nube.set_alpha(int(255 * alfa))
        caja = nube.get_rect(center=(960, 380))
        surface.blit(nube, caja)
        return caja

    def dibujarHud(self, surface: pygame.Surface) -> None:
        x, y = 690, 28
        if self.panelCorazones is not None:
            surface.blit(self.panelCorazones, (x, y))
        for i in range(self.maxAnimo):
            imagen = self.corazonLleno if i < self.animo else self.corazonVacio
            centro = (x + 50 + i * 64, y + 42)
            if imagen is not None:
                if i < self.animo:
                    latido = 1.0 + 0.05 * math.sin(self.tiempo * 6.0 + i)
                    imagen = pygame.transform.smoothscale_by(imagen, latido)
                surface.blit(imagen, imagen.get_rect(center=centro))
            else:
                pygame.draw.circle(surface, (230, 70, 100) if i < self.animo else (200, 200, 210), centro, 24)
        animo = self.textoBorde(self.fuenteHud, "Ánimo", (255, 248, 236), (96, 56, 30), 3)
        surface.blit(animo, animo.get_rect(midtop=(x + (self.maxAnimo * 64 + 50) // 2, y + 86)))
        for h in self.corazonesVolando:
            t = h["t"]
            destino = (x + 50 + (self.animo - 1) * 64, y + 42)
            hx = h["x"] + (destino[0] - h["x"]) * t
            hy = h["y"] + (destino[1] - h["y"]) * t - math.sin(t * math.pi) * 120
            if self.corazonLleno is not None:
                surface.blit(self.corazonLleno, self.corazonLleno.get_rect(center=(int(hx), int(hy))))

    def dibujarMensajes(self, surface: pygame.Surface) -> None:
        for m in self.mensajes:
            subida = (1.6 - m["vida"]) * 40
            texto = self.textoBorde(self.fuenteAviso, m["texto"], m["color"], m["borde"])
            texto.set_alpha(int(255 * min(1.0, m["vida"] / 0.4)))
            surface.blit(texto, texto.get_rect(center=(int(m["x"]), int(m["y"] - subida))))


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    for driver in ("SDL_AUDIODRIVER", "SDL_VIDEODRIVER"):
        if os.environ.get(driver) == "dummy":
            del os.environ[driver]
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080))
    pygame.display.set_caption("BarranquillaWare · El Heladero del Metro")
    clock = pygame.time.Clock()
    game = HeladeroMetroMicrogame()
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            game.handle_event(event)
        game.update(dt)
        game.render(screen)
        pygame.display.flip()
    pygame.quit()
