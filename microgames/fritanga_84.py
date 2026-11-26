import math
import os
import random
import sys
from typing import Optional, Callable, List
import pygame

if __name__ == "__main__":
    raizProyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, raizProyecto)
    os.chdir(raizProyecto)

from core.microgame import BaseMicrogame
from core.camera_gestures import CameraGestureInput
from core.asset_manager import quitarBlanco, achicar

carpetaFritanga = "Fritanga"

frasesTrol = [
    ("La arepa de huevo es mejor sin huevo y con piña", "¡Sin huevo no es arepa de huevo, ignorante!"),
    ("El patillazo sabe mejor caliente", "¡El patillazo es frío, eso lo sabe todo el mundo!"),
    ("¿Suero costeño? Eso es yogur dañado y salado", "¡Respeta el suero, que tú no sabes comer!"),
    ("Esas arepas tienen más aceite que el caldero", "¡Mis arepas salen doraditas, ven y pruébalas!"),
    ("El que le echa suero a la arepa no sabe comer", "¡El que no sabe comer eres tú!"),
]
burlasTrol = [
    ("Jajaja, se picó el cocinero", "¡Yo no me pico, tú eres el que no sabe!"),
    ("Uy, se calentó más que el aceite", "¡Ven y repite eso aquí en el puesto!"),
    ("Sigue escribiendo, que me estás haciendo famoso", "¡Me vas a oír hasta que aprendas!"),
    ("Mientras me peleas, se te quema la arepa", "¡Mis arepas no son problema tuyo!"),
]
comentariosNormales = [
    "¡Qué arepa tan bacana!", "Mándame una pa' acá", "Esa espumadera es arte",
    "¿A cómo el patillazo?", "Ajá, ¿y la mía?", "Esa arepa está en su punto",
    "Ese patillazo se ve heladito", "¿Hay carimañolas?", "Échale suero a esa arepa",
    "Ese caldero suena sabroso", "Una de huevo y un patillazo, porfa",
    "¡Qué hambre me dio!", "Esas arepas se ven crocanticas", "Saludos desde Soledad",
    "¿Hasta qué hora abren?", "Ese huevo quedó en su punto", "Pásame la receta, porfa",
    "Mi abuela las hacía igualitas", "Se me hizo agua la boca", "¿El patillazo lleva hielo?",
    "¿Tienen ají de suero?", "Barranquilla se respeta", "Esa vitrina está full",
    "Saludos desde el Prado", "Ya voy pa' allá", "Guárdame una, no seas malo",
]
mensajesRabia = [
    "¡Con rabia no se cocina!", "¡Calma, que se te va todo!", "¡La rabia te tiene torpe!",
    "¡Así no se cocina, mi llave!", "¡Respira, que se te riega!", "¡Esa rabia te está saliendo cara!",
]
reflexionesResponder = [
    ["Ajá, ¿y pa' qué le respondes, mi llave?", "Él ganó seguidores con tu rabia", "y a ti se te estaba quemando la arepa."],
    ["¿Pa' qué le sigues respondiendo, mi llave?", "Mira el chat: todos gozando con tu pelea.",
     "La rabia en redes da vistas, pero el que se quema eres tú."],
    ["¿Pa' qué le contestas, si eso es justo lo que quiere?", "El que escribe esas cosas no busca conversar:",
     "busca verte caliente, y cada respuesta es leña pa' su candela."],
    ["¿Y pa' qué le respondes? Mientras peleabas,", "las manos se te fueron pal' celular",
     "y lo que de verdad importa se quedó solo."],
]
reflexionesIgnorar = [
    ["¡Eso es tener la cabeza fría, mi llave!", "Al que vive de provocar,", "el silencio le quita el negocio."],
    ["No todo comentario merece respuesta.", "Tu calma también dice algo,", "y dice mucho más que cualquier insulto."],
    ["Mientras él gritaba, tú seguías cocinando.", "Tu tiempo y tu paz valen más", "que ganarle una pelea a un desconocido."],
]
comentariosPelea = ["¡Pelea, pelea!", "Jajajajaja", "Uy, se puso bravo", "Dale, respóndele otra vez", "Ignóralo, mi llave",
                    "Esto se puso bueno", "Traigan las crispetas", "Uy, el cocinero está caliente", "¡Se armó!",
                    "Esto va pa' tendencia", "Ombe, cálmate", "No le contestes más"]
comentariosCalma = ["Bien hecho, no le pares bolas", "Ese siempre dice lo mismo", "Tú sigue cocinando, mi llave",
                    "Esa es la actitud", "Respeto, cocinero", "Así se hace, sin pelear", "Ese trol se quedó solo",
                    "Cabeza fría, mi llave"]
comentariosAnteTrol = [
    "¡Pelea, pelea!", "¡Ponlo en su lugar!", "¡Respóndele, no te dejes!", "¡Dale duro!",
    "¡Contéstale, cocinero!", "¡Eso no se puede quedar así!", "¡Cállalo, mi llave!",
    "¡No te dejes humillar!", "¡Que se respete el puesto!",
    "Ignóralo, llave", "No le pares bolas",
]
apoyoPorTema = {
    "La arepa de huevo es mejor sin huevo y con piña": [
        "¿Con piña? ¡Qué sacrilegio!", "¡Defiende la arepa de huevo!", "¡Sin huevo no es arepa, dile!",
        "¡Ese no ha probado una arepa en su vida!"],
    "El patillazo sabe mejor caliente": [
        "¿Patillazo caliente? ¡Ese está loco!", "¡Defiende el patillazo!", "¡El patillazo es frío y punto!",
        "¡Dile que venga a probar el tuyo!"],
    "¿Suero costeño? Eso es yogur dañado y salado": [
        "¡Con el suero no te metas!", "¡Defiende el suero costeño!", "¡Ese no sabe nada de la costa!",
        "¿Yogur dañado? ¡Respóndele eso!"],
    "Esas arepas tienen más aceite que el caldero": [
        "¡Tus arepas están perfectas!", "¡Dile que venga a probarlas!", "¡Esas arepas están doraditas!",
        "¡No te dejes, que tus fritos son los mejores!"],
    "El que le echa suero a la arepa no sabe comer": [
        "¡Arepa con suero es lo mejor!", "¡Defiende el suero en la arepa!", "¡El que no sabe es él!",
        "¡Dile cómo se come en Barranquilla!"],
}
apoyoContraBurla = [
    "¡No te dejes, cocinero!", "¡Te está buscando, contéstale!", "¡Ese man se está burlando de ti!",
    "¡Dale donde le duele!",
]
pedidosPatillazo = [
    "Un patillazo, porfa", "¿Me regalas un patillazo?", "Un patillazo bien frío", "Uno de patilla, mi llave",
    "¡Patillazo pa' este calor!", "Me da uno grande, porfa", "¿Me vendes un patillazo?", "Uno pa' llevar, ajá",
]
pedidosPorCliente = {
    0: ["Amigo, ¿me regalas un patillazo?", "Un patillazo bien frío, amigo", "¿Me vendes uno, porfa?",
        "Amigo, ¿y mi patillazo?"],
    4: ["¡Un patillazo pa' celebrar el gol!", "Uno de patilla, mi llave", "¡Patillazo pa' este calor!",
        "Ajá, mi llave, ¿y el mío?"],
    5: ["Mijo, ¿me regalas un patillazo?", "Mijo, uno bien frío, porfa", "Ay, mijo, ¿y mi patillazo?",
        "Mijo, con este calor me derrito"],
    6: ["Un patillazo de rapidez, que voy a hacer una carrera", "Rapidito, que me cogen la carrera",
        "Uno de patilla, mi llave, que voy de afán", "¡Ombe, que se me va el cliente!"],
    7: ["Señor, ¿me alcanza pa' un patillazo?", "Señor, uno chiquito, porfa", "¿Ya casi, señor?",
        "Señor, ¿me lo da bien frío?"],
}
graciasPorCliente = {0: "¡Gracias, amigo!", 5: "¡Gracias, mijo!", 7: "¡Gracias, señor!"}


class Fritanga84Microgame(BaseMicrogame):
    ensenanzaFinal = {
        "gana": ["Ese trol escribía barbaridades para que te enojaras.",
                 "No le diste tu rabia, y sin tu rabia",
                 "no tenía de qué vivir."],
        "pierde": ["Se te escaparon unas arepas, pero no peleaste con nadie.",
                   "Con calma todo sale mejor:",
                   "en la cocina y en las redes."],
    }
    ensenanzaRabia = ["Le respondiste y el que ganó fue el trol:",
                      "cada comentario tuyo le dio más vistas y más plata.",
                      "Tu calma vale más que tener la razón en internet."]
    ensenanzaDistraido = ["Mientras le respondías al trol, se te quemaba la comida.",
                          "Pelear en redes te roba la atención",
                          "de lo que de verdad importa."]
    fraseRedes = "Usa las redes pa' compartir lo bueno, no pa' pelear."

    GAMEPAD_POINTER = True
    GAMEPAD_BUTTON_KEYS = {2: pygame.K_p, 3: pygame.K_e}
    CAMERA_POINTER = True
    CAMERA_POINTER_DRAG = True
    CAMERA_DWELL_CLICK = False
    CAMERA_CLICK_COOLDOWN = 0.14
    CAMERA_POINTER_MARGIN = 0.08
    def __init__(
        self,
        character_id: str = "westcol",
        on_complete_callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        self.character_id = character_id
        super().__init__(
            command_text="¡Voltea la arepa!\nSirve el patillazo y no le pares bolas al trol",
            time_limit=75.0,
            on_complete_callback=on_complete_callback
        )

    def enter(self, params: Optional[dict] = None) -> None:
        self.audio.play_bgm("contraRelojMusic.mp3")

    def setup_game(self) -> None:
        self.camara = CameraGestureInput.get_instance()
        self.listo = self.cargarImagenes()

        self.tiempoJugado = 0.0
        self.fallos = 0
        self.maxFallos = 5
        self.puntoQuemado = 1.6
        self.arepasListas = 0
        self.patillazosServidos = 0

        self.ubicarCaldero()
        self.arepas = []
        for lugar, coccion in enumerate((0.3, 0.05, -0.25)):
            self.arepas.append(self.nuevaArepa(lugar, coccion))

        self.llenado = 0.0
        self.estadoVaso = "listo"
        self.tiempoVaso = 0.0
        self.vasoPendiente = False
        self.teclaServir = False
        self.mouseServir = False
        self.gestoServir = False
        self._servir_por_camara = False
        self._arrastre_por_camara = False
        self._control_camara_activo = False
        self.sirviendoAntes = False
        self.vasoNuevo = 0.0
        self.puntoDerrame = 1.08
        self.vasoAplastado = False
        self.posArrastre = [0.0, 0.0]
        self.agarreVaso = (0, 0)
        self.origenEntrega = self.baseVaso
        self.puntoApretado = (0, 0)

        self.ordenClientes = [4, 6, 1, 7, 5, 0]
        self.cliente = None
        self.esperaCliente = 1.5
        self.cuantosClientes = 0

        self.espectadores = 120.0
        self.chat: List[dict] = []
        self.esperaComentario = 0.8
        self.momentosTrol = [10.0, 32.0, 54.0]
        self.trol = {"estado": "nada", "t": 0.0, "frase": "", "respuesta": "", "cuantas": 0}
        self.cuantasFrases = 0
        self.finTrol = -100.0
        self.esperaBurla = -1.0
        self.ultimaDecision = None

        self.reflexion = None
        self.reflexionPendiente = None
        self.esperaReflexion = -1.0
        self.burlaPendiente = None
        self.cuantasReflexiones = {}
        self.respuestas = 0
        self.seguidoresTrol = 1240
        self.ultimaPelea = -10.0
        self.escribiendo = 0.0
        self.duracionEscribir = 2.0
        self.textoEscribiendo = ""
        self.rabia = 0.0
        self.arrebato = 0.0
        self.duracionArrebato = 2.8
        self.esperaMensajeRabia = 3.0
        self.pausaTermo = 0.0
        self.pausaQuemada = 0.0
        self.duracionQuemada = 4.4
        self.rabiaMostrada = 0.0
        self.congelarTermo = False
        self.destaqueTermo = None
        self.tutorialPendiente = True
        self.tutorial = None

        self.tiempoAviso = 0.0
        self.opcionAviso = 1
        self.celularCentro = 0.0
        self.filtro = 0.0
        self.musicaPausada = False

        self.sonidoAceite = self.cargarSonido(os.path.join(carpetaFritanga, "aceite.mp3"))
        self.refuerzoAceite = 1.3
        self.chisporroteo = None
        self.golpeAceite = 0.0
        if self.sonidoAceite is None:
            self.sonidoAceite = self.crearSonidoAceite()
            self.refuerzoAceite = 1.0
        else:
            self.sonidoAceite, self.chisporroteo = self.reforzarAceite(self.sonidoAceite)
        self.canalAceite = None
        self.cancionTrol = self.cargarSonido(os.path.join(carpetaFritanga, "trol.mp3"))
        self.canalTrol = None
        self.sonidoError = self.cargarSonido("Error.mp3")
        self.sonidoAy = self.cargarSonido(os.path.join(carpetaFritanga, "ay.mp3"))
        self.agache = 0.0
        self.vocesRabia = [voz for voz in (self.cargarSonido(os.path.join(carpetaFritanga, "esteVale.mp3")),
                                           self.cargarSonido(os.path.join(carpetaFritanga, "cachaco.mp3")))
                           if voz is not None]
        self.cualVoz = 0
        self.ultimoUpdate = 0
        self.brillos = [{"x": random.uniform(-0.7, 0.7), "y": random.uniform(-0.5, 0.5), "fase": random.uniform(0, 6)}
                        for _ in range(4)]

        self.secuencia = None
        self.tiempoSecuencia = 0.0
        self.manoQuemada = False

        self.burbujas: List[dict] = []
        self.gotas: List[dict] = []
        self.humo: List[dict] = []
        self.mensajes: List[dict] = []
        self.emojisVolando: List[dict] = []
        self.globosHechos = {}
        self.manoObjetivo = None
        self.tiempoMano = 0.0
        self.posMano = list(self.manoReposo) if self.listo else [0.0, 0.0]

    def cargarImagenes(self) -> bool:
        try:
            fondo = self.assets.load_surface(os.path.join(carpetaFritanga, "fondoFritanga.png"), has_alpha=False)
            self.fondo = pygame.transform.smoothscale(fondo, (self.screen_w, self.screen_h))

            caldero = self.recortar(self.assets.cargarSinFondo(os.path.join(carpetaFritanga, "calderoNormal.jpg"), 1200))
            self.caldero = self.aAncho(caldero, 820)

            arepas = self.separarPiezas("arepas.jpg", 4)
            self.arepaCruda = self.aplastar(arepas[0], 150)
            self.arepaDorada = self.aplastar(arepas[1], 150)
            self.arepaQuemada = self.aplastar(arepas[2], 150)
            self.arepaQuemadaEntera = self.aAncho(arepas[2], 140)
            self.arepaVolando = self.aAncho(arepas[3], 120)
            self.iconoArepa = self.aplastar(arepas[1], 62)
            self.iconoQuemada = self.aplastar(arepas[2], 62)

            manos = self.separarPiezas("manos.jpg", 2)
            self.mano = self.aAncho(manos[0], 420)
            self.manoCuritas = self.aAncho(manos[1], 420)

            botellon = self.recortar(self.assets.cargarSinFondo(os.path.join(carpetaFritanga, "bPatillazo.jpg"), 1200))
            sirviendo = self.recortar(self.assets.cargarSinFondo(os.path.join(carpetaFritanga, "bSirviendo.jpg"), 1200))
            escala = 230 / float(botellon.get_width())
            self.botellon = pygame.transform.smoothscale_by(botellon, escala)
            self.botellonSirviendo = pygame.transform.smoothscale_by(sirviendo, escala)

            vasos = self.separarPiezas("vasosPatillazo.jpg", 4)
            cuarto = self.recortar(self.assets.cargarSinFondo(os.path.join(carpetaFritanga, "vaso34.jpg"), 1200))
            self.vasos = [self.aAncho(vasos[0], 110), self.aAncho(cuarto, 110),
                          self.aAncho(vasos[1], 110), self.aAncho(vasos[2], 110)]
            regados = self.separarPiezas("vasosRegados.jpg", 2)
            self.vasoCayendo = self.aAncho(regados[0], 210)
            self.vasoCharco = self.aAncho(regados[1], 230)
            apretado = self.recortar(self.assets.cargarSinFondo(os.path.join(carpetaFritanga, "vasoApretado.jpg"), 1200))
            self.vasoApretado = self.aAncho(apretado, 175)
            flecha = self.recortar(self.assets.cargarSinFondo(os.path.join(carpetaFritanga, "flechaAbajo.jpg"), 1200))
            self.flechaAbajo = self.aAncho(flecha, 34)
            self.prepararMedidor()

            crudo = achicar(self.assets.load_surface(os.path.join(carpetaFritanga, "clientes.jpg")), 1200)
            sinRaya = crudo.subsurface((0, 0, crudo.get_width(), int(crudo.get_height() * 0.783))).copy()
            huecos = [(55, 322), (188, 341), (176, 54), (42, 82), (196, 90), (34, 112), (12, 211), (16, 166),
                      (665, 29), (780, 310), (758, 423)]
            hojaClientes = self.limpiarHalo(self.borrarHuecos(quitarBlanco(sinRaya), huecos))
            self.clientes = [self.aAncho(self.quitarSobras(pieza), 300) for pieza in self.separarPiezas(hojaClientes, 4)]
            self.clientes += self.cargarClientesNuevos()

            self.emojis = [self.aAncho(pieza, 96) for pieza in self.separarPiezas("emojis.jpg", 4)]
            self.avatarTrol = self.aAncho(self.emojis[2], 50)
            potes = self.separarPiezas("potePropinas.jpg", 2)
            self.potePropinas = self.aAncho(potes[1], 150)

            gotas = self.separarPiezas("gotasAceite.jpg", 6)
            self.gotasChicas = [self.aAncho(g, 26) for g in gotas]
            self.gotasGrandes = [self.aAncho(g, 64) for g in gotas]

            globo = self.recortar(self.assets.cargarSinFondo(os.path.join(carpetaFritanga, "globoTexto.jpg"), 1200))
            self.globoTexto = globo
            cuaderno = self.recortar(self.assets.cargarSinFondo(os.path.join(carpetaFritanga, "cuaderno.jpg"), 1200))
            self.cuaderno = self.aAncho(cuaderno, 300)
            self.iconoArepaChica = self.aplastar(arepas[1], 38)
            self.iconoQuemadaChica = self.aplastar(arepas[2], 38)

            comentario = self.assets.cargarSinFondo(os.path.join("Piano", "globoComentario.jpg"), 900)
            self.globoComentario = pygame.transform.smoothscale_by(comentario, 46 / float(comentario.get_height()))
            enVivo = self.assets.cargarSinFondo(os.path.join("Piano", "etiquetaEnVivo.jpg"), 600)
            self.etiquetaEnVivo = pygame.transform.smoothscale_by(enVivo, 44 / float(enVivo.get_height()))
            vistas = self.assets.cargarSinFondo(os.path.join("Piano", "pastillaEspectadores.jpg"), 700)
            self.pastillaVistas = pygame.transform.smoothscale_by(vistas, 44 / float(vistas.get_height()))
            crudoMarco = achicar(self.assets.load_surface(os.path.join("Piano", "marcoCelular.jpg")), 1200)
            marco = self.recortar(quitarBlanco(crudoMarco.copy(), ((0.5, 0.5),)))
            self.marcoCelular = self.aAncho(marco, 400)
            self.avatares = self.cortarAvatares()
            marcoTermo = self.recortar(self.assets.cargarSinFondo(os.path.join(carpetaFritanga, "termometroMarco.jpg"), 1200))
            self.marcoTermometro = self.aAncho(marcoTermo, 540)
            w, h = self.marcoTermometro.get_size()
            self.canalTermometro = pygame.Rect(int(w * 0.108), int(h * 0.35), int(w * 0.78), int(h * 0.49))
            rellenoTermo = self.recortar(self.assets.cargarSinFondo(os.path.join(carpetaFritanga, "termometroRelleno.jpg"), 1200))
            self.rellenoTermometro = pygame.transform.smoothscale(rellenoTermo, self.canalTermometro.size)

            camara = self.recortar(self.assets.cargarSinFondo(os.path.join(carpetaFritanga, "camara.jpg"), 1200))
            huecosCamara = [(203, 409), (483, 739), (446, 1078), (547, 1079)]
            camara = self.limpiarHalo(self.borrarHuecos(camara, huecosCamara), 3)
            self.camaraLive = self.aAncho(camara, 250)
            self.botonRojo = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonRojo.jpg"), 300)
            self.botonMorado = self.assets.cargarSinFondo(os.path.join("Interfaz", "botonMorado.jpg"), 300)
        except Exception as e:
            print(f"[Fritanga] Aviso: faltan imágenes de la fritanga: {e}")
            return False

        self.imagenQuemadura = self.cargarOpcional("FAy.png")

        self.fuenteHud = self.assets.cargarFuenteCuento(40)
        self.fuenteArepa = self.assets.cargarFuenteTitulo(30)
        self.fuenteMensaje = self.assets.cargarFuenteTitulo(34)
        self.fuenteGlobo = self.assets.cargarFuenteCuento(30)
        self.fuenteChat = self.assets.cargarFuenteCuento(22)
        self.fuenteTrol = self.assets.cargarFuenteCuento(24)
        self.fuenteAyuda = self.assets.cargarFuenteCuento(28)
        self.fuenteBoton = self.assets.cargarFuenteTitulo(30)
        self.fuenteCelular = self.assets.cargarFuenteCuento(30)
        self.fuenteVistas = self.assets.cargarFuenteCuento(48)
        self.fuentePregunta = self.assets.cargarFuenteTitulo(58)
        self.fuenteCuaderno = self.assets.cargarFuenteCuento(54)
        self.fuenteTutorial = self.assets.cargarFuenteCuento(36)

        self.capaBurbujas = pygame.Surface((700, 340), pygame.SRCALPHA)
        self.nube = self.crearNube(90)
        self.bordeRojo = self.crearBordeRojo()
        return True

    def prepararMedidor(self) -> None:
        import numpy
        marco, relleno = self.separarPiezas("medidor.jpg", 2)
        escala = 200 / float(marco.get_height())
        self.medidorMarco = pygame.transform.smoothscale_by(marco, escala)
        self.medidorRelleno = pygame.transform.smoothscale_by(relleno, escala)
        w, h = self.medidorMarco.get_size()
        rgb = pygame.surfarray.array3d(self.medidorMarco).astype(numpy.int16)
        alfa = pygame.surfarray.array_alpha(self.medidorMarco)
        oscuro = (rgb.max(axis=2) < 150) & (alfa > 60)
        filas = numpy.arange(h)[None, :]
        dentro = (alfa > 100) & ~oscuro & (filas >= int(145 * escala))
        columnas = numpy.arange(w)[:, None]
        dentro &= (columnas > int(w * 0.13)) & (columnas < int(w * 0.87))
        self.medidorDentro = pygame.Surface((w, h), pygame.SRCALPHA)
        self.medidorDentro.fill((255, 255, 255, 0))
        pixeles = pygame.surfarray.pixels_alpha(self.medidorDentro)
        pixeles[:] = numpy.where(dentro, 255, 0).astype(numpy.uint8)
        del pixeles
        self.medidorTrazos = self.medidorMarco.copy()
        pixeles = pygame.surfarray.pixels_alpha(self.medidorTrazos)
        pixeles[:] = numpy.where(oscuro, alfa, 0).astype(numpy.uint8)
        del pixeles
        self.nivelesMedidor = (int(145 * escala), int(365 * escala), int(885 * escala))

    def cargarClientesNuevos(self) -> list:
        crudo = achicar(self.assets.load_surface(os.path.join(carpetaFritanga, "clientes2.jpg")), 1200)
        sinRaya = crudo.subsurface((0, 0, crudo.get_width(), int(crudo.get_height() * 0.771))).copy()
        abajo = sinRaya.get_height()
        pygame.draw.rect(sinRaya, (60, 40, 30), (0, abajo - 2, int(sinRaya.get_width() * 0.275), 2))
        hoja = quitarBlanco(sinRaya)
        hoja = hoja.subsurface((0, 0, hoja.get_width(), hoja.get_height() - 2)).copy()
        hoja = self.limpiarHalo(self.borrarHuecos(hoja, [(1114, 233)]))
        piezas = [self.quitarSobras(pieza) for pieza in self.separarFiguras(hoja, 4)]
        escala = 500 / float(max(p.get_height() for p in piezas))
        return [pygame.transform.smoothscale_by(pieza, escala) for pieza in piezas]

    def separarFiguras(self, hoja: pygame.Surface, cuantas: int) -> list:
        mascara = pygame.mask.from_surface(hoja, 60)
        figuras = sorted(mascara.connected_components(), key=lambda parte: parte.count(), reverse=True)[:cuantas]
        cajas = sorted((figura.get_bounding_rects()[0] for figura in figuras), key=lambda caja: caja.x)
        cortes = [0]
        for izquierda, derecha in zip(cajas, cajas[1:]):
            cortes.append((izquierda.right + derecha.left) // 2)
        cortes.append(hoja.get_width())
        return [self.recortar(hoja.subsurface((cortes[i], 0, cortes[i + 1] - cortes[i], hoja.get_height())))
                for i in range(cuantas)]

    def cortarAvatares(self) -> list:
        hoja = self.assets.cargarSinFondo(os.path.join("Piano", "avataresPublico.jpg"), 1200)
        w, h = hoja.get_size()
        avatares = []
        for fila in range(2):
            for columna in range(4):
                celda = hoja.subsurface((columna * w // 4, fila * h // 2, w // 4, h // 2))
                avatares.append(self.aAncho(self.recortar(celda), 42))
        return avatares

    def cargarOpcional(self, archivo: str):
        ruta = os.path.join(carpetaFritanga, archivo)
        try:
            if not os.path.exists(os.path.join(self.assets.base_dir, ruta)):
                return None
            return self.recortar(self.assets.cargarSinFondo(ruta, 1200))
        except Exception as e:
            print(f"[Fritanga] Aviso al cargar {archivo}: {e}")
            return None

    def recortar(self, imagen: pygame.Surface) -> pygame.Surface:
        caja = imagen.get_bounding_rect(min_alpha=60)
        return imagen.subsurface(caja).copy()

    def aAncho(self, imagen: pygame.Surface, ancho: int) -> pygame.Surface:
        alto = max(1, int(imagen.get_height() * ancho / float(imagen.get_width())))
        return pygame.transform.smoothscale(imagen, (ancho, alto))

    def aplastar(self, imagen: pygame.Surface, ancho: int) -> pygame.Surface:
        alto = max(1, int(imagen.get_height() * ancho / float(imagen.get_width()) * 0.6))
        return pygame.transform.smoothscale(imagen, (ancho, alto))

    def separarPiezas(self, hoja, cuantas: int) -> list:
        if isinstance(hoja, str):
            hoja = self.assets.cargarSinFondo(os.path.join(carpetaFritanga, hoja), 1200)
        alfa = pygame.surfarray.array_alpha(hoja)
        ocupadas = (alfa > 60).any(axis=1)
        tramos = []
        inicio = None
        for x, hayAlgo in enumerate(ocupadas):
            if hayAlgo and inicio is None:
                inicio = x
            elif not hayAlgo and inicio is not None:
                tramos.append([inicio, x])
                inicio = None
        if inicio is not None:
            tramos.append([inicio, len(ocupadas)])

        juntos = []
        for tramo in tramos:
            if juntos and tramo[0] - juntos[-1][1] < 30:
                juntos[-1][1] = tramo[1]
            else:
                juntos.append(tramo)
        if len(juntos) != cuantas:
            ancho = hoja.get_width() // cuantas
            juntos = [[i * ancho, (i + 1) * ancho] for i in range(cuantas)]

        piezas = []
        for izquierda, derecha in juntos:
            trozo = hoja.subsurface((izquierda, 0, derecha - izquierda, hoja.get_height()))
            piezas.append(self.recortar(trozo))
        return piezas

    def limpiarHalo(self, imagen: pygame.Surface, vueltas: int = 4) -> pygame.Surface:
        import numpy
        limpia = imagen.copy()
        rgb = pygame.surfarray.array3d(limpia).astype(numpy.int16)
        claro = (rgb.min(axis=2) >= 165) & ((rgb.max(axis=2) - rgb.min(axis=2)) <= 45)
        alfa = pygame.surfarray.pixels_alpha(limpia)
        for _ in range(vueltas):
            vacio = alfa < 30
            pegado = numpy.zeros_like(vacio)
            pegado[1:, :] |= vacio[:-1, :]
            pegado[:-1, :] |= vacio[1:, :]
            pegado[:, 1:] |= vacio[:, :-1]
            pegado[:, :-1] |= vacio[:, 1:]
            borrar = pegado & claro & ~vacio
            if not borrar.any():
                break
            alfa[borrar] = 0
        del alfa
        return limpia

    def borrarHuecos(self, imagen: pygame.Surface, puntos: list) -> pygame.Surface:
        import numpy
        limpia = imagen.copy()
        rgb = pygame.surfarray.array3d(limpia).astype(numpy.int16)
        alfa = pygame.surfarray.pixels_alpha(limpia)
        claro = (rgb.min(axis=2) >= 200) & ((rgb.max(axis=2) - rgb.min(axis=2)) <= 30) & (alfa > 100)
        capa = pygame.Surface(limpia.get_size(), pygame.SRCALPHA)
        pixeles = pygame.surfarray.pixels_alpha(capa)
        pixeles[:] = numpy.where(claro, 255, 0)
        del pixeles
        blancos = pygame.mask.from_surface(capa, 127)
        for punto in puntos:
            if 0 <= punto[0] < limpia.get_width() and 0 <= punto[1] < limpia.get_height() and blancos.get_at(punto):
                mancha = pygame.surfarray.array_alpha(blancos.connected_component(punto).to_surface(
                    setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))) > 0
                crecida = mancha.copy()
                crecida[1:, :] |= mancha[:-1, :]
                crecida[:-1, :] |= mancha[1:, :]
                crecida[:, 1:] |= mancha[:, :-1]
                crecida[:, :-1] |= mancha[:, 1:]
                alfa[crecida & (rgb.min(axis=2) >= 150)] = 0
                alfa[mancha] = 0
        del alfa
        return limpia

    def quitarSobras(self, imagen: pygame.Surface) -> pygame.Surface:
        mascara = pygame.mask.from_surface(imagen, 60)
        partes = mascara.connected_components()
        if len(partes) <= 1:
            return imagen
        mayor = max(p.count() for p in partes)
        queda = pygame.mask.Mask(imagen.get_size())
        for parte in partes:
            if parte.count() >= mayor * 0.02:
                queda.draw(parte, (0, 0))
        limpia = imagen.copy()
        limpia.blit(queda.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)), (0, 0),
                    special_flags=pygame.BLEND_RGBA_MULT)
        return self.recortar(limpia)

    def crearNube(self, radio: int) -> pygame.Surface:
        nube = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
        for r in range(radio, 0, -3):
            claridad = 1.0 - r / float(radio)
            pygame.draw.circle(nube, (235, 228, 220, int(10 + 60 * claridad)), (radio, radio), r)
        return nube

    def crearBordeRojo(self) -> pygame.Surface:
        import numpy
        borde = pygame.Surface((self.screen_w // 4, self.screen_h // 4), pygame.SRCALPHA)
        borde.fill((200, 40, 30, 255))
        w, h = borde.get_size()
        xs = (numpy.arange(w) - w / 2.0) / (w / 2.0)
        ys = (numpy.arange(h) - h / 2.0) / (h / 2.0)
        distancia = numpy.sqrt(xs[:, None] ** 2 + ys[None, :] ** 2)
        alfa = pygame.surfarray.pixels_alpha(borde)
        alfa[:] = (numpy.clip((distancia - 0.6) / 0.6, 0.0, 1.0) * 210).astype(numpy.uint8)
        del alfa
        return pygame.transform.smoothscale(borde, (self.screen_w, self.screen_h))

    def ubicarCaldero(self) -> None:
        if self.listo:
            w, h = self.caldero.get_size()
            self.cajaCaldero = pygame.Rect(1000 - w // 2, self.screen_h - h + 60, w, h)
        else:
            self.cajaCaldero = pygame.Rect(590, 590, 820, 550)
        c = self.cajaCaldero
        self.centroAceite = (c.x + int(c.w * 0.457), c.y + int(c.h * 0.375))
        self.radioAceite = (int(c.w * 0.33), int(c.h * 0.21))
        cx, cy = self.centroAceite
        rx, ry = self.radioAceite
        self.lugares = [(cx - int(rx * 0.58), cy + int(ry * 0.05)),
                        (cx, cy + int(ry * 0.32)),
                        (cx + int(rx * 0.58), cy - int(ry * 0.02))]

        self.cajaBotellon = pygame.Rect(1560, 525, 230, 380)
        self.chorroX = 1748
        if self.listo:
            self.cajaBotellon = self.botellon.get_rect(bottomleft=(1560, 905))
            self.chorroX = self.cajaBotellon.x + self.buscarChorro()
        self.baseVaso = (self.chorroX, 1066)
        self.lineaMostrador = 812
        self.centroCliente = 1565
        self.destinoVitrina = (540, 860)
        self.duracionSacar = 0.8

        self.cajaCelular = pygame.Rect(28, 150, 400, 772)
        if self.listo:
            self.cajaCelular = self.marcoCelular.get_rect(topleft=(28, 150))
        m = self.cajaCelular
        self.pantalla = pygame.Rect(m.x + int(m.w * 0.075), m.y + int(m.h * 0.035),
                                    int(m.w * 0.85), int(m.h * 0.93))
        self.centroGrande = (960, 500)
        self.escalaGrande = 1.15
        self.botonesAviso = [pygame.Rect(0, 0, 300, 90), pygame.Rect(0, 0, 300, 90)]
        self.botonesAviso[0].center = (470, 875)
        self.botonesAviso[1].center = (1450, 875)

        if self.listo:
            w, h = self.mano.get_size()
            self.puntaMano = (int(w * 0.8), int(h * 0.13))
            self.manoReposo = (300.0, float(self.screen_h - h + 150))
        else:
            self.puntaMano = (0, 0)
            self.manoReposo = (300.0, 700.0)

    def buscarChorro(self) -> int:
        alfa = pygame.surfarray.array_alpha(self.botellonSirviendo)
        h = self.botellonSirviendo.get_height()
        abajo = alfa[:, int(h * 0.96):]
        columnas = [x for x in range(abajo.shape[0]) if abajo[x].max() > 60]
        if not columnas:
            return int(self.botellonSirviendo.get_width() * 0.8)
        return sum(columnas) // len(columnas)

    def nuevaArepa(self, lugar: int, coccion: float = 0.0) -> dict:
        x, y = self.lugares[lugar]
        return {
            "lugar": lugar, "x": float(x), "y": float(y), "lado": 1,
            "coccion": coccion, "velocidad": random.uniform(0.16, 0.21),
            "volteo": 0.0, "sacando": 0.0, "entrada": 0.0, "temblor": 0.0, "quemada": 0.0,
            "chapuzon": False, "seVuela": 0.0, "direccion": 1,
        }

    def caminoSacando(self, arepa: dict):
        avance = 1.0 - arepa["sacando"] / self.duracionSacar
        x0, y0 = arepa["x"], arepa["y"]
        if avance < 0.25:
            subida = 1.0 - (1.0 - avance / 0.25) ** 2
            return x0, y0 - 70 * subida, 1.0, avance
        q = (avance - 0.25) / 0.75
        suave = q * q * (3 - 2 * q)
        tx, ty = self.destinoVitrina
        x = x0 + (tx - x0) * suave
        y = (y0 - 70) + (ty - (y0 - 70)) * suave - math.sin(q * math.pi) * 130
        return x, y, 1.0 - 0.45 * suave, avance

    @staticmethod
    def _es_evento_camara(event: pygame.event.Event) -> bool:
        return bool(getattr(event, "camera_pointer", False))

    @staticmethod
    def _es_evento_no_camara(event: pygame.event.Event) -> bool:
        if event.type in (
            pygame.KEYDOWN,
            pygame.KEYUP,
            pygame.JOYBUTTONDOWN,
            pygame.JOYBUTTONUP,
            pygame.JOYAXISMOTION,
            pygame.JOYHATMOTION,
        ):
            return True
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return not bool(getattr(event, "camera_pointer", False))
        return False

    def _camara_es_control_activo(self) -> bool:
        from core import input_state
        return bool(self._control_camara_activo and not input_state.is_gamepad_active())

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if self.is_finished or self.secuencia:
            return
        if self._es_evento_no_camara(event):
            self._control_camara_activo = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self._es_evento_camara(event):
            self._control_camara_activo = True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            es_cam = self._es_evento_camara(event)
            if es_cam and self.vasoLleno() and self.estadoVaso == "listo" and self.clienteEsperando():
                caja_cli = self.cajaCliente()
                if caja_cli is not None:
                    zona_cli = pygame.Rect(caja_cli.x - 80, caja_cli.y - 80, caja_cli.w + 80, caja_cli.h + 80)
                    if zona_cli.collidepoint(event.pos):
                        self.entregarVaso()
                        return
            margen_vaso = (70, 70) if es_cam else (40, 40)
            if self.vasoLleno() and self.estadoVaso == "listo" and self.cajaVasoQuieto().inflate(*margen_vaso).collidepoint(event.pos):
                self.agarrarVaso(event.pos, es_camara=es_cam)
                return
            if self.zonaServir().collidepoint(event.pos):
                self.mouseServir = True
                self._servir_por_camara = es_cam
                self.puntoApretado = event.pos
                return
            arepa = self.arepaEn(event.pos, es_camara=es_cam)
            if arepa is not None:
                self.tocarArepa(arepa)
        elif event.type == pygame.MOUSEMOTION:
            apretado = bool(getattr(event, "buttons", (1, 0, 0))[0])
            if self.estadoVaso == "arrastrando" and apretado:
                self.posArrastre = [float(event.pos[0]), float(event.pos[1])]
            elif apretado and self.mouseServir and self.vasoLleno() and self.estadoVaso == "listo":
                es_cam = self._es_evento_camara(event)
                es_virtual = bool(es_cam or getattr(event, "gamepad_pointer", False))
                salio_botellon = (not self.zonaServir().collidepoint(event.pos)) if es_virtual else True
                if salio_botellon and math.hypot(event.pos[0] - self.puntoApretado[0], event.pos[1] - self.puntoApretado[1]) > 25:
                    self.agarrarVaso(event.pos, es_camara=es_cam or self._servir_por_camara)
                    self.agarreVaso = (0, -70)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.mouseServir = False
            self._servir_por_camara = False
            if self.estadoVaso == "arrastrando":
                es_cam_drag = self._arrastre_por_camara or self._es_evento_camara(event)
                self._arrastre_por_camara = False
                self.soltarVaso(event.pos, es_camara=es_cam_drag)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_e and self.vasoLleno() and self.clienteEsperando():
            self.entregarVaso()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.tocarArepa(self.arepaMasUrgente())
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                lugar = event.key - pygame.K_1
                for arepa in self.arepas:
                    if arepa["lugar"] == lugar:
                        self.tocarArepa(arepa)
            elif event.key in (pygame.K_p, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.teclaServir = True
        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_p, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.teclaServir = False

    def revisarGestos(self) -> None:
        camara = getattr(self, "camara", None)
        if not camara or not camara.enabled:
            return
        if camara.consume_click():
            self.tocarArepa(self.arepaMasUrgente())
        if camara.consume_hand_raise():
            if self.vasoLleno() and self.clienteEsperando():
                self.entregarVaso()
            else:
                self.gestoServir = not self.gestoServir

    def handle_event(self, event: pygame.event.Event) -> None:
        if self._es_evento_no_camara(event):
            self._control_camara_activo = False
        if self.tutorial is not None and self.phase == self.PHASE_PLAY and not self.is_finished:
            self.eventoTutorial(event)
            return
        if self.reflexion and self.phase == self.PHASE_PLAY and not self.is_finished:
            min_refl = 3.2 if getattr(event, "camera_pointer", False) else 2.0
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                super().handle_event(event)
            elif self.reflexion["t"] >= min_refl and (
                    (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
                    or (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE))):
                self.cerrarReflexion()
            return
        if self.trol["estado"] != "aviso" or self.phase != self.PHASE_PLAY or self.is_finished:
            super().handle_event(event)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            super().handle_event(event)
            return
        min_aviso = 1.1 if getattr(event, "camera_pointer", False) else 0.6
        if self.tiempoAviso < min_aviso:
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            for i, caja in enumerate(self.botonesAviso):
                if self.cajaBotonAviso(i).collidepoint(event.pos):
                    if event.type == pygame.MOUSEMOTION and self.opcionAviso != i:
                        self.opcionAviso = i
                        if hasattr(self.audio, "play_hover"):
                            self.audio.play_hover()
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.elegirOpcion(i)
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.opcionAviso = 0
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.opcionAviso = 1
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.elegirOpcion(self.opcionAviso)
            elif event.key == pygame.K_r:
                self.elegirOpcion(0)
            elif event.key == pygame.K_i:
                self.elegirOpcion(1)

    def pasosTutorial(self) -> list:
        olla = self.cajaCaldero
        caldero = pygame.Rect(0, 0, olla.w + 60, int(olla.h * 0.72))
        caldero.center = (olla.centerx, olla.y + int(olla.h * 0.33))
        cuaderno = self.cuaderno.get_rect(topright=(self.screen_w - 14, 8))
        termometro = self.marcoTermometro.get_rect(midtop=(925, 150))
        cliente = self.cajaCliente() or pygame.Rect(1415, 316, 300, 500)
        cliente = cliente.union(pygame.Rect(cliente.centerx - 300, cliente.top - 90, 340, 110))
        return [
            ("elipse", caldero, (960, 70),
             "Estas son tus arepas de huevo. Cuando una esté dorada, haz clic encima o pulsa espacio "
             "para voltearla, y otra vez para sacarla."),
            ("caja", self.zonaServir(), (760, 110),
             "Mantén el clic o la tecla P en el botellón para llenar el vaso. Suelta apenas llegue a la raya: "
             "si te pasas, se derrama."),
            ("caja", cliente.inflate(20, 20), (700, 330),
             "Cuando el vaso esté lleno, arrástralo hasta el cliente o pulsa E. Si lo dejas esperando más de "
             "12 segundos, se va bravo."),
            ("caja", cuaderno.inflate(16, 16), (960, 360),
             "En el cuaderno llevas la cuenta. Abajo hay cinco arepitas: cada arepa quemada o cliente que se va "
             "sin su patillazo tacha una."),
            ("caja", self.cajaCelular.inflate(16, 16), (1150, 330),
             "Este es tu live. En cualquier momento se mete un trol a decir barbaridades, y tú decides "
             "si le respondes o lo ignoras."),
            ("caja", termometro.inflate(24, 16), (960, 360),
             "Este es tu termómetro. Si le respondes al trol, sube la rabia; si lo ignoras, gana la calma. "
             "Si la rabia llega al tope, explotas en vivo."),
        ]

    def iniciarTutorial(self) -> None:
        self.tutorialPendiente = False
        self.tutorial = {"paso": 0, "t": 0.0, "inicioPaso": 0.0}
        self.cliente = {"cual": self.ordenClientes[0], "estado": "esperando", "tiempo": 0.0, "paciencia": 12.0}
        self.cuantosClientes = 1

    def siguientePasoTutorial(self) -> None:
        if self.tutorial is None:
            return
        self.tutorial["paso"] += 1
        self.tutorial["inicioPaso"] = self.tutorial["t"]
        if self.tutorial["paso"] >= len(self.pasosTutorial()):
            self.terminarTutorial()
        elif hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def terminarTutorial(self) -> None:
        self.tutorial = None
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def botonesTutorial(self) -> list:
        tarjeta = self.cajaTarjetaTutorial()
        saltar = pygame.Rect(0, 0, 260, 84)
        seguir = pygame.Rect(0, 0, 260, 84)
        saltar.midtop = (tarjeta.left + 170, tarjeta.bottom + 14)
        seguir.midtop = (tarjeta.right - 170, tarjeta.bottom + 14)
        return [saltar, seguir]

    def cajaTarjetaTutorial(self) -> pygame.Rect:
        _, _, arriba, _ = self.pasosTutorial()[self.tutorial["paso"]]
        tarjeta = pygame.Rect(0, 0, 1040, 230)
        tarjeta.midtop = arriba
        return tarjeta

    def eventoTutorial(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                BaseMicrogame.handle_event(self, event)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_RIGHT):
                self.siguientePasoTutorial()
            elif event.key == pygame.K_s:
                self.terminarTutorial()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            saltar, seguir = self.botonesTutorial()
            if seguir.inflate(30, 20).collidepoint(event.pos):
                self.siguientePasoTutorial()
            elif saltar.inflate(30, 20).collidepoint(event.pos):
                self.terminarTutorial()

    def revisarGestosTutorial(self) -> None:
        camara = getattr(self, "camara", None)
        if camara and camara.enabled and camara.consume_hand_raise() and self.tutorial["t"] - self.tutorial["inicioPaso"] > 0.6:
            self.siguientePasoTutorial()

    def trazoAMano(self, surface: pygame.Surface, caja: pygame.Rect, elipse: bool, color, grosor: int, semilla: float) -> None:
        ancho, alto = caja.w - caja.w % 2, caja.h - caja.h % 2
        clave = ("trazo", ancho, alto, elipse, tuple(color), grosor, round(semilla, 1))
        margen = grosor + 6
        if clave not in self.globosHechos:
            k = 3
            lienzo = pygame.Surface(((ancho + margen * 2) * k, (alto + margen * 2) * k), pygame.SRCALPHA)
            cx, cy = (ancho / 2.0 + margen) * k, (alto / 2.0 + margen) * k
            puntos = []
            for i in range(180):
                angulo = i / 180.0 * math.pi * 2
                temblor = 1.0 + 0.012 * math.sin(angulo * 3 + semilla) + 0.008 * math.sin(angulo * 7 + semilla * 2)
                if elipse:
                    x = cx + math.cos(angulo) * ancho / 2.0 * k * temblor
                    y = cy + math.sin(angulo) * alto / 2.0 * k * temblor
                else:
                    c, s = math.cos(angulo), math.sin(angulo)
                    lado = max(abs(c) / (ancho / 2.0), abs(s) / (alto / 2.0))
                    x = cx + c / lado * k * temblor
                    y = cy + s / lado * k * temblor
                puntos.append((x, y))
            pygame.draw.lines(lienzo, color, True, puntos, grosor * k)
            for punto in puntos:
                pygame.draw.circle(lienzo, color, punto, grosor * k / 2.0)
            self.globosHechos[clave] = pygame.transform.smoothscale(lienzo, (ancho + margen * 2, alto + margen * 2))
        trazo = self.globosHechos[clave]
        surface.blit(trazo, trazo.get_rect(center=caja.center))

    def dibujarTutorial(self, surface: pygame.Surface) -> None:
        pasos = self.pasosTutorial()
        paso = self.tutorial["paso"]
        forma, caja, _, texto = pasos[paso]
        elipse = forma == "elipse"
        enPaso = self.tutorial["t"] - self.tutorial["inicioPaso"]

        claveVelo = ("veloTutorial", paso, caja.size, caja.topleft)
        if claveVelo not in self.globosHechos:
            velo = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            velo.fill((40, 26, 22, 170))
            zona = caja.inflate(8, 8).clip(velo.get_rect())
            k = 3
            hueco = pygame.Surface((zona.w * k, zona.h * k), pygame.SRCALPHA)
            hueco.fill((40, 26, 22, 170))
            dentro = pygame.Rect((caja.x - zona.x) * k, (caja.y - zona.y) * k, caja.w * k, caja.h * k)
            if elipse:
                pygame.draw.ellipse(hueco, (40, 26, 22, 0), dentro)
            else:
                pygame.draw.rect(hueco, (40, 26, 22, 0), dentro, border_radius=24 * k)
            velo.blit(pygame.transform.smoothscale(hueco, zona.size), zona.topleft, special_flags=pygame.BLEND_RGBA_MIN)
            self.globosHechos[claveVelo] = velo
        surface.blit(self.globosHechos[claveVelo], (0, 0))
        pulso = int(4 * math.sin(self.tutorial["t"] * 6.0))
        self.trazoAMano(surface, caja.inflate(8 + pulso * 2, 8 + pulso * 2), elipse, (255, 196, 90), 5, paso)
        self.trazoAMano(surface, caja.inflate(22 + pulso * 2, 22 + pulso * 2), elipse, (110, 50, 25), 2, paso + 0.5)

        clave = ("tutorial", paso)
        if clave not in self.globosHechos:
            banner = self.assets.cargarSinFondo(os.path.join("Interfaz", "bannerUbicacion.jpg"), 1200)
            banner = pygame.transform.smoothscale_by(banner, 230 / float(banner.get_height()))
            tarjeta = self.ponerBordeFino(self.suavizarOrilla(self.estirarCentro(banner, 1040)), (128, 76, 40), 4)
            tarjeta = self.ponerBordeFino(tarjeta, (84, 46, 22), 2)
            lineas = self.partirEnLineas(self.fuenteTutorial, texto, 780)[:3]
            alto = self.fuenteTutorial.get_linesize()
            y = tarjeta.get_height() // 2 - alto * len(lineas) // 2
            for linea in lineas:
                letras = self.fuenteTutorial.render(linea, True, (100, 60, 36))
                tarjeta.blit(letras, letras.get_rect(midtop=(tarjeta.get_width() // 2, y)))
                y += alto
            self.globosHechos[clave] = tarjeta
        tarjeta = self.globosHechos[clave]
        entrada = min(1.0, enPaso / 0.3)
        rebote = 1.0 + 2.7 * (entrada - 1.0) ** 3 + 1.7 * (entrada - 1.0) ** 2
        dibujo = tarjeta if entrada >= 1.0 else pygame.transform.smoothscale_by(tarjeta, max(0.05, 0.6 + 0.4 * rebote))
        cajaTarjeta = self.cajaTarjetaTutorial()
        surface.blit(dibujo, dibujo.get_rect(center=cajaTarjeta.center))

        if "botonesCalidos" not in self.globosHechos:
            self.globosHechos["botonesCalidos"] = (self.tenir(self.botonMorado, (205, 160, 125)),
                                                   self.tenir(self.botonRojo, (255, 150, 60)))
        botonSaltar, botonSeguir = self.globosHechos["botonesCalidos"]
        saltar, seguir = self.botonesTutorial()
        ultimo = paso == len(pasos) - 1
        for boton, imagen, etiqueta, contorno in ((saltar, botonSaltar, "Saltar (S)", (100, 60, 30)),
                                                  (seguir, botonSeguir, "¡A cocinar!" if ultimo else "Siguiente",
                                                   (130, 60, 20))):
            surface.blit(imagen, imagen.get_rect(center=boton.center))
            letras = self.textoBorde(self.fuenteBoton, etiqueta, (255, 248, 236), contorno)
            surface.blit(letras, letras.get_rect(center=(boton.centerx, boton.centery - 3)))
        x0 = (saltar.right + seguir.left) / 2 - (len(pasos) - 1) * 12
        for i in range(len(pasos)):
            centro = (int(x0 + i * 24), saltar.centery)
            if i == paso:
                pygame.draw.circle(surface, (110, 50, 25), centro, 10)
                pygame.draw.circle(surface, (245, 150, 60), centro, 8)
            else:
                pygame.draw.circle(surface, (110, 50, 25), centro, 6)
                pygame.draw.circle(surface, (190, 120, 70) if i < paso else (255, 236, 200), centro, 4)

    def escalaBotonAviso(self, i: int) -> float:
        if i == 0:
            return 1.25 * (1.0 + 0.05 * math.sin(self.tiempoAviso * 8.0))
        return 0.85

    def cajaBotonAviso(self, i: int) -> pygame.Rect:
        caja = self.botonesAviso[i]
        if self.listo:
            boton = self.botonRojo.get_rect()
            boton.size = (int(boton.w * self.escalaBotonAviso(i)), int(boton.h * self.escalaBotonAviso(i)))
            boton.center = caja.center
            caja = boton.union(caja)
        return caja.inflate(40, 30)

    def revisarGestosAviso(self, dt: float = 1 / 60) -> None:
        camara = getattr(self, "camara", None)
        if not camara or not camara.enabled or self.tiempoAviso < 0.6:
            self.reset_binary_camera_choice()
            return
        choice = self.poll_binary_camera_choice(camara, dt)
        if choice is not None:
            self.elegirOpcion(choice)

    def zonaServir(self) -> pygame.Rect:
        return pygame.Rect(self.cajaBotellon.x - 20, self.cajaBotellon.y, self.cajaBotellon.w + 120,
                           self.baseVaso[1] - self.cajaBotellon.y)

    def arepaEn(self, pos, es_camara: bool = False) -> Optional[dict]:
        for arepa in self.arepas:
            dx = (pos[0] - arepa["x"]) / 85.0
            dy = (pos[1] - arepa["y"]) / 55.0
            if dx * dx + dy * dy <= 1.3:
                return arepa
        if not es_camara:
            return None
        candidatas = []
        for arepa in self.arepas:
            if not self.arepaLibre(arepa):
                continue
            dx = (pos[0] - arepa["x"]) / (85.0 * 1.45)
            dy = (pos[1] - arepa["y"]) / (55.0 * 1.45)
            d2 = dx * dx + dy * dy
            if d2 <= 1.3:
                candidatas.append((d2, arepa))
        if not candidatas:
            return None
        listas = [par for par in candidatas if par[1]["coccion"] >= 0.55]
        if listas:
            return max(listas, key=lambda par: par[1]["coccion"])[1]
        return min(candidatas, key=lambda par: par[0])[1]

    def arepaMasUrgente(self) -> Optional[dict]:
        libres = [a for a in self.arepas if self.arepaLibre(a)]
        if not libres:
            return None
        listas = [a for a in libres if a["coccion"] >= 0.55]
        return max(listas or libres, key=lambda a: a["coccion"])

    def arepaLibre(self, arepa: dict) -> bool:
        return (arepa["volteo"] <= 0.0 and arepa["sacando"] <= 0.0 and arepa["quemada"] <= 0.0
                and arepa["seVuela"] <= 0.0 and arepa["entrada"] >= 1.0)

    def tocarArepa(self, arepa: Optional[dict]) -> None:
        if arepa is None or not self.arepaLibre(arepa):
            return
        if self.escribiendo > 0.0:
            return
        self.moverManoA(arepa)
        if arepa["coccion"] < 0.55:
            arepa["temblor"] = 0.3
            self.decir("¡Todavía no!", arepa["x"], arepa["y"] - 70)
            return
        if arepa["lado"] == 1:
            volar = (self.rabia - 0.5) * 1.6 if self.rabia >= 0.6 else 0.0
            if self.respuestas >= 2 and self.rabia >= 0.3:
                volar = max(volar, 0.4)
            if random.random() < min(volar, 0.75):
                arepa["seVuela"] = 0.8
                arepa["direccion"] = random.choice((-1, 1))
                self.decir(random.choice(mensajesRabia), arepa["x"], arepa["y"] - 90)
                return
            arepa["volteo"] = 0.45
            arepa["lado"] = 2
            arepa["coccion"] = 0.1
            self.salpicar(arepa["x"], arepa["y"], 4, False)
            self.golpeAceite = 1.0
            if self.chisporroteo is not None and hasattr(self.audio, "play_sfx"):
                self.audio.play_sfx(self.chisporroteo, 1.0)
        else:
            if any(a["sacando"] > 0.0 for a in self.arepas):
                return
            arepa["sacando"] = self.duracionSacar
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def moverManoA(self, arepa: dict) -> None:
        self.manoObjetivo = (arepa["x"], arepa["y"])
        self.tiempoMano = 0.45

    def elegirOpcion(self, opcion: int) -> None:
        if self.trol["estado"] != "aviso":
            return
        self.callarCancionTrol()
        self.reanudarMusica()
        self.finTrol = self.tiempoJugado
        if opcion == 0:
            self.responder()
        else:
            self.trol["estado"] = "nada"
            self.trol["t"] = 0.0
            antes = self.rabiaMostrada
            self.rabia = max(0.0, self.rabia - 0.15)
            self.destacarTermometro(antes, self.rabia)
            self.agregarComentario(self.elegirComentario(comentariosCalma))
            self.decir("No le pares bolas", 960, 330)
            if self.ultimaDecision != "ignorar":
                self.programarReflexion("ignorar", 0.0, None)
            self.ultimaDecision = "ignorar"
            if hasattr(self.audio, "play_click"):
                self.audio.play_click()

    def programarReflexion(self, tipo: str, espera: float, burla) -> None:
        opciones = reflexionesResponder if tipo == "responder" else reflexionesIgnorar
        indice = self.cuantasReflexiones.get(tipo, 0)
        self.cuantasReflexiones[tipo] = indice + 1
        self.reflexionPendiente = opciones[indice % len(opciones)]
        self.esperaReflexion = espera
        self.burlaPendiente = burla

    def abrirReflexion(self) -> None:
        self.reflexion = {"lineas": self.reflexionPendiente, "t": 0.0}
        self.reflexionPendiente = None
        self.esperaReflexion = -1.0
        self.teclaServir = False
        self.mouseServir = False
        self.gestoServir = False
        self._servir_por_camara = False
        self._arrastre_por_camara = False
        self.devolverVaso()
        self.pausarMusica()
        if hasattr(self.audio, "play_drum"):
            self.audio.play_drum()

    def cerrarReflexion(self) -> None:
        self.reflexion = None
        self.reanudarMusica()
        if self.burlaPendiente is not None and not self.secuencia:
            self.trol["estado"] = "nada"
            self.trol["t"] = 0.0
            self.esperaBurla = 4.0

    def cargarSonido(self, nombre: str):
        guardados = Fritanga84Microgame.__dict__.get("sonidosGuardados")
        if guardados is None:
            guardados = {}
            Fritanga84Microgame.sonidosGuardados = guardados
        if nombre in guardados:
            return guardados[nombre]
        sonido = None
        try:
            if pygame.mixer.get_init():
                sonido = pygame.mixer.Sound(os.path.join("assets", nombre))
        except Exception as e:
            print(f"[Fritanga] Aviso: no se pudo cargar el sonido {nombre}: {e}")
        guardados[nombre] = sonido
        return sonido

    def sonarCancionTrol(self) -> None:
        if self.cancionTrol is None or not getattr(self.audio, "music_enabled", True):
            return
        self.callarCancionTrol()
        self.canalTrol = self.cancionTrol.play(loops=-1, fade_ms=250)
        if self.canalTrol is not None:
            self.canalTrol.set_volume(max(0.0, min(1.0, getattr(self.audio, "music_volume", 0.7))))
            # Es una canción: si otra parte del juego pone música, esta se apaga (nunca dos a la vez)
            if hasattr(self.audio, "registrar_cancion_en_canal"):
                self.audio.registrar_cancion_en_canal(self.canalTrol)

    def callarCancionTrol(self) -> None:
        if self.canalTrol is not None:
            self.canalTrol.fadeout(300)
            self.canalTrol = None

    def pausarMusica(self) -> None:
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
                self.musicaPausada = True
        except Exception:
            pass

    def reanudarMusica(self) -> None:
        if not self.musicaPausada:
            return
        try:
            if getattr(self.audio, "music_enabled", True):
                pygame.mixer.music.unpause()
                if hasattr(self.audio, "sync_music_volume"):
                    self.audio.sync_music_volume()
        except Exception:
            pass
        self.musicaPausada = False

    def responder(self) -> None:
        if self.trol["estado"] != "aviso" or self.escribiendo > 0.0 or self.secuencia:
            return
        self.respuestas += 1
        self.ultimaDecision = "responder"
        self.congelarTermo = True
        if self.vocesRabia and hasattr(self.audio, "play_sfx"):
            self.audio.play_sfx(self.vocesRabia[self.cualVoz % len(self.vocesRabia)])
            self.cualVoz += 1
        self.rabia = min(1.0, self.rabia + 0.26)
        self.escribiendo = self.duracionEscribir
        self.textoEscribiendo = self.trol.get("respuesta", "")
        self.trol["estado"] = "leyendo"
        self.trol["t"] = 0.0
        self.ultimaPelea = self.tiempoJugado
        self.teclaServir = False
        self.mouseServir = False
        self._servir_por_camara = False
        self._arrastre_por_camara = False
        self.seguidoresTrol += random.randint(350, 600)
        self.espectadores += 450
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def actualizarTrol(self, dt: float) -> None:
        t = self.trol
        t["t"] += dt
        if t["estado"] == "nada":
            listo = self.celularCentro <= 0.05 and self.reflexionPendiente is None
            listo = listo and self.burlaPendiente is None and self.tiempoJugado - self.finTrol >= 9.0
            if self.momentosTrol and self.tiempoJugado >= self.momentosTrol[0] and listo:
                self.momentosTrol.pop(0)
                self.provocar(*frasesTrol[self.cuantasFrases % len(frasesTrol)])
                self.cuantasFrases += 1
        elif t["estado"] == "leyendo":
            if self.escribiendo <= 0.0:
                self.agregarComentario(self.textoEscribiendo, propio=True)
                for _ in range(2):
                    self.agregarComentario(self.elegirComentario(comentariosPelea))
                t["estado"] = "pensando"
                t["t"] = 0.0
                self.pausaTermo = 2.4
                self.destacarTermometro(self.rabiaMostrada, self.rabia, True)
                burla = burlasTrol[(self.respuestas - 1) % len(burlasTrol)]
                self.programarReflexion("responder", self.duracionArrebato + 0.3, burla)
        elif t["estado"] == "aburrido" and t["t"] >= 2.5:
            t["estado"] = "fuera"

        if self.escribiendo <= 0.0 and self.burlaPendiente is None:
            self.rabia = max(0.0, self.rabia - 0.06 * dt)

    def provocar(self, frase: str, respuesta: str) -> None:
        yaEstaba = self.trol["estado"] in ("leyendo", "pensando")
        self.trol["estado"] = "aviso"
        self.trol["t"] = 0.31 if yaEstaba else 0.0
        self.trol["frase"] = frase
        self.trol["respuesta"] = respuesta
        self.trol["cuantas"] += 1
        self.tiempoAviso = 0.0
        self.opcionAviso = 1
        self.teclaServir = False
        self.mouseServir = False
        self.gestoServir = False
        self._servir_por_camara = False
        self._arrastre_por_camara = False
        self.devolverVaso()
        self.pausarMusica()
        self.sonarCancionTrol()
        if hasattr(self.audio, "play_hover"):
            self.audio.play_hover()

    def destacarTermometro(self, desde: float, hasta: float, pausado: bool = False) -> None:
        self.congelarTermo = False
        self.destaqueTermo = {"t": 0.0, "desde": desde, "hasta": hasta, "dur": 2.4,
                              "sube": hasta > desde, "sonado": False, "pausado": pausado,
                              "inicio": 0.4 if pausado else 0.35, "llenar": 1.0 if pausado else 0.9}

    def avanzarDestaque(self, dt: float) -> None:
        d = self.destaqueTermo
        if d is None:
            if not self.congelarTermo:
                self.rabiaMostrada = self.rabia
            return
        d["t"] += dt
        llenado = min(1.0, max(0.0, (d["t"] - d["inicio"]) / d["llenar"]))
        llenado = llenado * llenado * (3 - 2 * llenado)
        self.rabiaMostrada = d["desde"] + (d["hasta"] - d["desde"]) * llenado
        if not d["sonado"] and d["t"] >= d["inicio"]:
            d["sonado"] = True
            if d["sube"] and hasattr(self.audio, "play_hit"):
                self.audio.play_hit()
            elif not d["sube"] and hasattr(self.audio, "play_win"):
                self.audio.play_win()
        if d["t"] >= d["dur"]:
            self.destaqueTermo = None

    def empezarArrebato(self) -> None:
        self.arrebato = self.duracionArrebato
        self.golpeAceite = 1.0
        self.trigger_screenshake(10.0, 0.35)
        self.decir("¡Ombe, qué rabia me da ese man!", 900, 480)
        if self.chisporroteo is not None and hasattr(self.audio, "play_sfx"):
            self.audio.play_sfx(self.chisporroteo, 1.0)

    def pringarMano(self) -> None:
        self.manoQuemada = True
        if self.listo:
            punta = (self.posMano[0] + self.puntaMano[0], self.posMano[1] + self.puntaMano[1] + 120)
            self.salpicar(punta[0], punta[1], 6, True)
        self.pausaQuemada = self.duracionQuemada
        self.trigger_screenshake(14.0, 0.3)
        if self.sonidoAy is not None and hasattr(self.audio, "play_sfx"):
            self.audio.play_sfx(self.sonidoAy)
            self.agache = self.sonidoAy.get_length() + 0.2
            self.ajustarMusica(0.25)
        elif hasattr(self.audio, "play_miss"):
            self.audio.play_miss()

    def ajustarMusica(self, factor: float) -> None:
        try:
            if not pygame.mixer.get_init() or not getattr(self.audio, "music_enabled", True):
                return
            if abs(factor - 1.0) < 1e-4 and hasattr(self.audio, "sync_music_volume"):
                self.audio.sync_music_volume()
                return
            duck = getattr(self.audio, "_duck_factor", 1.0)
            base = getattr(self.audio, "music_volume", 0.7) * getattr(self.audio, "_bgm_volume_scale", 1.0) * duck
            pygame.mixer.music.set_volume(max(0.0, min(1.0, base * factor)))
        except Exception:
            pass

    def actualizarAgache(self, dt: float) -> None:
        if self.agache <= 0.0:
            return
        self.agache = max(0.0, self.agache - dt)
        if self.agache <= 0.0:
            self.ajustarMusica(1.0)

    def enfado(self) -> float:
        if self.arrebato <= 0.0:
            return 0.0
        pasado = self.duracionArrebato - self.arrebato
        return min(1.0, pasado / 0.3, self.arrebato / 0.5)

    def calor(self) -> float:
        return max(self.rabia, self.enfado())

    def objetivoCelular(self) -> float:
        if self.secuencia == "explosion":
            return self.celularCentro
        if self.trol["estado"] in ("aviso", "leyendo"):
            return 1.0
        return 0.0

    def animarCelular(self, dt: float) -> None:
        objetivo = self.objetivoCelular()
        paso = dt / 0.35
        if self.celularCentro < objetivo:
            self.celularCentro = min(objetivo, self.celularCentro + paso)
        elif self.celularCentro > objetivo:
            self.celularCentro = max(objetivo, self.celularCentro - paso)
        objetivoFiltro = 1.0 if self.trol["estado"] == "aviso" or self.reflexion or self.pausaTermo > 0.0 else 0.0
        if self.filtro < objetivoFiltro:
            self.filtro = min(1.0, self.filtro + dt / 0.25)
        elif self.filtro > objetivoFiltro:
            self.filtro = max(0.0, self.filtro - dt / 0.25)

    def crearSonidoAceite(self):
        guardado = getattr(Fritanga84Microgame, "sonidoGuardado", None)
        if guardado is not None:
            return guardado
        try:
            import numpy
            if not pygame.mixer.get_init():
                return None
            frecuencia, _, canales = pygame.mixer.get_init()
            muestras = int(frecuencia * 3.0)
            ruido = numpy.random.normal(0.0, 1.0, muestras)
            agudo = numpy.diff(ruido, prepend=0.0)
            t = numpy.arange(muestras) / float(frecuencia)
            vaiven = 0.75 + 0.25 * numpy.sin(2 * numpy.pi * 0.7 * t) * numpy.sin(2 * numpy.pi * 1.9 * t + 1.0)
            base = agudo * vaiven * 0.08
            chasquidos = numpy.zeros(muestras)
            for inicio in numpy.random.randint(0, muestras - 400, 140):
                largo = numpy.random.randint(60, 300)
                caida = numpy.exp(-numpy.arange(largo) / (largo / 5.0))
                chasquidos[inicio:inicio + largo] += numpy.random.uniform(-1, 1, largo) * caida * numpy.random.uniform(0.2, 0.6)
            onda = base + chasquidos * 0.35
            cruce = int(frecuencia * 0.2)
            rampa = numpy.linspace(0.0, 1.0, cruce)
            onda[:cruce] = onda[:cruce] * rampa + onda[-cruce:] * (1.0 - rampa)
            onda = onda[:-cruce]
            onda = numpy.clip(onda / max(0.01, numpy.abs(onda).max()) * 0.6, -1.0, 1.0)
            datos = (onda * 32767).astype(numpy.int16)
            if canales == 2:
                datos = numpy.column_stack((datos, datos))
            sonido = pygame.sndarray.make_sound(numpy.ascontiguousarray(datos))
            Fritanga84Microgame.sonidoGuardado = sonido
            return sonido
        except Exception as e:
            print(f"[Fritanga] Aviso: no se pudo crear el sonido del aceite: {e}")
            return None

    def reforzarAceite(self, sonido):
        guardado = Fritanga84Microgame.__dict__.get("aceiteReforzado")
        if guardado is not None:
            return guardado
        try:
            import numpy
            frecuencia = pygame.mixer.get_init()[0]
            onda = pygame.sndarray.array(sonido).astype(numpy.float32) / 32767.0
            fuerza = float(numpy.sqrt((onda ** 2).mean()))
            ganancia = 0.18 / max(0.001, fuerza)
            fuerte = numpy.tanh(onda * ganancia) * 0.92
            largo = int(frecuencia * 1.1)
            inicio = int(frecuencia * 2.0)
            pedazo = fuerte[inicio:inicio + largo].copy()
            caida = numpy.exp(-numpy.linspace(0.0, 3.5, len(pedazo)))
            subida = numpy.minimum(1.0, numpy.arange(len(pedazo)) / (frecuencia * 0.02))
            envolvente = caida * subida
            if pedazo.ndim == 2:
                envolvente = envolvente[:, None]
            pedazo = pedazo * envolvente
            hecho = (pygame.sndarray.make_sound(numpy.ascontiguousarray((fuerte * 32767).astype(numpy.int16))),
                     pygame.sndarray.make_sound(numpy.ascontiguousarray((pedazo * 32767).astype(numpy.int16))))
            Fritanga84Microgame.aceiteReforzado = hecho
            return hecho
        except Exception as e:
            print(f"[Fritanga] Aviso: no se pudo reforzar el sonido del aceite: {e}")
            return sonido, None

    def actualizarSonido(self) -> None:
        self.ultimoUpdate = pygame.time.get_ticks()
        if self.canalTrol is not None:
            if getattr(self.audio, "music_enabled", True):
                self.canalTrol.set_volume(max(0.0, min(1.0, getattr(self.audio, "music_volume", 0.7))))
                self.canalTrol.unpause()
            else:
                self.canalTrol.pause()
        if not getattr(self.audio, "sound_enabled", True):
            if self.canalAceite is not None:
                self.canalAceite.set_volume(0.0)
                self.canalAceite.pause()
            return
        if self.sonidoAceite is None:
            return
        if self.canalAceite is None:
            self.canalAceite = self.sonidoAceite.play(loops=-1)
            if self.canalAceite is None:
                return
        volumen = 0.0 if self.trol["estado"] == "aviso" or self.reflexion else \
            (0.22 + 0.5 * self.calor()) * self.refuerzoAceite + 0.5 * self.golpeAceite
        if self.agache > 0.0:
            volumen *= 0.2
        self.canalAceite.set_volume(max(0.0, min(1.0, volumen * getattr(self.audio, "sfx_volume", 0.8))))
        self.canalAceite.unpause()

    def callarAceiteSiPausado(self) -> None:
        if self.canalAceite is not None and pygame.time.get_ticks() - self.ultimoUpdate > 150:
            self.canalAceite.pause()
        # La canción del trol es la música del momento: sigue sonando en el menú de pausa.

    def exit(self) -> None:
        if getattr(self, "agache", 0.0) > 0.0:
            self.agache = 0.0
            self.ajustarMusica(1.0)
        if self.canalAceite is not None:
            self.canalAceite.stop()
            self.canalAceite = None
        if getattr(self, "canalTrol", None) is not None:
            self.canalTrol.stop()
            self.canalTrol = None
        if hasattr(self.audio, "sonarEscritura"):
            self.audio.sonarEscritura(False)
        self.reanudarMusica()
        super().exit()

    def elegirComentario(self, lista: list) -> str:
        recientes = [c["texto"] for c in self.chat[-4:]]
        opciones = [texto for texto in lista if texto not in recientes] or lista
        return random.choice(opciones)

    def agregarComentario(self, texto: str, propio: bool = False, trol: bool = False) -> None:
        if not self.listo:
            return
        self.chat.append({"fila": self.filaChat(texto, propio, trol), "t": 0.0, "propio": propio, "texto": texto})
        if len(self.chat) > 12:
            self.chat.pop(0)

    def actualizarLive(self, dt: float) -> None:
        self.espectadores += dt * random.uniform(2.0, 6.0)
        self.esperaComentario -= dt
        if self.esperaComentario <= 0.0:
            if self.trol["estado"] == "aviso":
                apoyo = apoyoPorTema.get(self.trol["frase"], apoyoContraBurla)
                texto = self.elegirComentario(comentariosAnteTrol + apoyo * 3)
                self.esperaComentario = random.uniform(0.45, 0.8)
            elif self.tiempoJugado - self.ultimaPelea < 4.0:
                texto = self.elegirComentario(comentariosPelea)
                self.esperaComentario = random.uniform(0.5, 0.9)
            else:
                texto = self.elegirComentario(comentariosNormales)
                self.esperaComentario = random.uniform(1.4, 2.3)
            self.agregarComentario(texto)
        for c in self.chat:
            c["t"] += dt

    def update(self, dt: float) -> None:
        if hasattr(self.audio, "update"):
            self.audio.update(dt)
        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)
            fuerza = self.shake_intensity * (self.shake_timer / max(0.01, self.shake_duration))
            self.shake_offset_x = int(random.uniform(-fuerza, fuerza))
            self.shake_offset_y = int(random.uniform(-fuerza, fuerza))
        else:
            self.shake_offset_x = 0
            self.shake_offset_y = 0

        if self.phase == self.PHASE_PLAY and not self.is_finished:
            self.animarCelular(dt)
            self.actualizarAgache(dt)
            self.actualizarSonido()
            self.avanzarDestaque(dt)
            if self.tutorialPendiente and self.listo:
                self.iniciarTutorial()
            if self.tutorial is not None:
                self.tutorial["t"] += dt
                self.revisarGestosTutorial()
                return
            if self.pausaTermo > 0.0:
                self.pausaTermo -= dt
                if self.pausaTermo <= 0.0:
                    self.pausaTermo = 0.0
                    self.empezarArrebato()
                return
            if self.pausaQuemada > 0.0:
                self.pausaQuemada = max(0.0, self.pausaQuemada - dt)
                return
            if self.reflexion:
                self.reflexion["t"] += dt
                if self.reflexion["t"] >= 6.5:
                    self.cerrarReflexion()
                return
            if self.trol["estado"] == "aviso":
                self.tiempoAviso += dt
                self.trol["t"] += dt
                self.actualizarLive(dt)
                self.revisarGestosAviso(dt)
                return
            self.avanzarMensajes(dt)
            if self.secuencia:
                self.avanzarSecuencia(dt)
                return
            if self.time_left - dt <= 0.0 and self.fallos < self.maxFallos:
                self.time_left = 0.0
                self.empezarSecuencia("victoria")
                return
        super().update(dt)

    def update_game(self, dt: float) -> None:
        if self.is_finished:
            return
        self.tiempoJugado += dt
        if self.escribiendo > 0.0:
            self.escribiendo = max(0.0, self.escribiendo - dt)
        if not self.CAMERA_POINTER:
            self.revisarGestos()
        if self.arrebato > 0.0:
            self.arrebato = max(0.0, self.arrebato - dt)
            if not self.manoQuemada and self.duracionArrebato - self.arrebato >= 1.2:
                self.pringarMano()
                return
        if self.calor() >= 0.5:
            self.esperaMensajeRabia -= dt
            if self.esperaMensajeRabia <= 0.0:
                self.esperaMensajeRabia = random.uniform(4.0, 6.0)
                self.decir(random.choice(mensajesRabia), 960 + random.uniform(-160, 160), 560)
        self.actualizarTrol(dt)
        self.actualizarLive(dt)
        self.actualizarArepas(dt)
        self.actualizarVaso(dt)
        self.actualizarCliente(dt)
        self.actualizarMano(dt)
        self.actualizarEfectos(dt)

        if self.esperaBurla >= 0.0:
            self.esperaBurla -= dt
            if self.esperaBurla < 0.0 and self.burlaPendiente is not None and not self.secuencia:
                frase, respuesta = self.burlaPendiente
                self.burlaPendiente = None
                self.provocar(frase, respuesta)
                return

        if self.esperaReflexion >= 0.0 and self.reflexionPendiente is not None:
            self.esperaReflexion -= dt
            if self.esperaReflexion < 0.0 and self.rabia < 1.0:
                self.abrirReflexion()
                return

        if self.rabia >= 1.0:
            self.empezarSecuencia("explosion")
        elif self.fallos >= self.maxFallos:
            if self.respuestas > 0:
                self.ensenanzaFinal = {"gana": Fritanga84Microgame.ensenanzaFinal["gana"], "pierde": self.ensenanzaDistraido}
            self.finish_game(False)

    def sumarFallo(self) -> None:
        if self.fallos < self.maxFallos:
            self.fallos += 1

    def actualizarArepas(self, dt: float) -> None:
        for i, arepa in enumerate(self.arepas):
            if arepa["entrada"] < 1.0:
                arepa["entrada"] = min(1.0, arepa["entrada"] + dt / 0.35)
            elif not arepa["chapuzon"]:
                arepa["chapuzon"] = True
                self.salpicar(arepa["x"], arepa["y"], 3, False)
            if arepa["temblor"] > 0.0:
                arepa["temblor"] = max(0.0, arepa["temblor"] - dt)
            if arepa["volteo"] > 0.0:
                arepa["volteo"] = max(0.0, arepa["volteo"] - dt)

            if arepa["seVuela"] > 0.0:
                arepa["seVuela"] -= dt
                if arepa["seVuela"] <= 0.0:
                    self.sumarFallo()
                    self.arepas[i] = self.nuevaArepa(arepa["lugar"], -0.2)
                continue

            if arepa["quemada"] > 0.0:
                arepa["quemada"] -= dt
                if random.random() < dt * 6.0:
                    self.echarHumo(arepa["x"], arepa["y"])
                if arepa["quemada"] <= 0.0:
                    self.arepas[i] = self.nuevaArepa(arepa["lugar"], -0.2)
                continue

            if arepa["sacando"] > 0.0:
                arepa["sacando"] -= dt
                x, y, escala, avance = self.caminoSacando(arepa)
                if avance < 0.4 and random.random() < dt * 14.0 and self.listo:
                    self.gotas.append({"img": random.choice(self.gotasChicas[:2]), "x": x + random.uniform(-40, 40),
                                       "y": y + 20, "vx": random.uniform(-20, 20), "vy": random.uniform(40, 140),
                                       "vida": 0.45, "total": 0.45})
                if arepa["sacando"] <= 0.0:
                    self.arepasListas += 1
                    self.decir("¡Lista!", self.destinoVitrina[0], self.destinoVitrina[1] - 60)
                    self.arepas[i] = self.nuevaArepa(arepa["lugar"], -0.2)
                continue

            limite = self.puntoQuemado - 0.4
            if self.arrebato > 0.0:
                if arepa["coccion"] < limite:
                    arepa["coccion"] = min(limite, arepa["coccion"] + arepa["velocidad"] * dt * 5.0)
            else:
                factor = 1.0
                if self._camara_es_control_activo():
                    factor = 0.80
                    if arepa["coccion"] >= 1.0 and (self.sirviendo() or self.estadoVaso == "arrastrando"):
                        factor *= 0.65
                arepa["coccion"] += arepa["velocidad"] * dt * factor
            if self.arrebato > 0.0 and arepa["coccion"] > 1.1 and random.random() < dt * 4.0:
                self.echarHumo(arepa["x"], arepa["y"])
            if arepa["coccion"] > self.puntoQuemado:
                arepa["quemada"] = 0.9
                self.echarHumo(arepa["x"], arepa["y"])
                self.decir("¡Se quemó!", arepa["x"], arepa["y"] - 70)
                self.sumarFallo()
                if self.sonidoError is not None and hasattr(self.audio, "play_sfx"):
                    self.audio.play_sfx(self.sonidoError)
                elif hasattr(self.audio, "play_miss"):
                    self.audio.play_miss()

    def sirviendo(self) -> bool:
        if self.escribiendo > 0.0:
            return False
        if self.mouseServir and self._servir_por_camara:
            cam = getattr(self, "camara", None)
            if cam is not None and hasattr(cam, "is_pinching") and not cam.is_pinching():
                return False
        return self.teclaServir or self.mouseServir or self.gestoServir

    def actualizarVaso(self, dt: float) -> None:
        ahora = self.sirviendo()
        self.vasoNuevo = max(0.0, self.vasoNuevo - dt)
        if self.estadoVaso in ("regandose", "entregando"):
            self.tiempoVaso += dt
            limite = 0.4
            if self.estadoVaso == "regandose":
                limite = 1.4 if self.vasoAplastado else 1.0
            if self.tiempoVaso >= limite:
                self.estadoVaso = "listo"
                self.llenado = 0.0
                self.vasoNuevo = 0.3
            self.sirviendoAntes = ahora
            return
        if self.estadoVaso == "volviendo":
            self.tiempoVaso += dt
            if self.tiempoVaso >= 0.25:
                self.estadoVaso = "listo"
            self.sirviendoAntes = ahora
            return
        if self.estadoVaso == "arrastrando":
            self.sirviendoAntes = ahora
            return

        if ahora:
            furia = self.furiaServir()
            antes = self.llenado
            tasa = 0.85 * (1.0 + 2.5 * furia)
            if self.mouseServir and self._servir_por_camara and self.llenado >= 0.8 and furia <= 0.0:
                tasa *= 0.55
            self.llenado += dt * tasa
            soloGesto = self.gestoServir and not self.teclaServir and not self.mouseServir
            if soloGesto and furia <= 0.0 and self.llenado >= 0.8:
                self.llenado = 0.8
                self.gestoServir = False
            if antes < 0.8 <= self.llenado and hasattr(self.audio, "play_click"):
                self.audio.play_click()
            if self.llenado >= self.puntoDerrame:
                self.regarVaso(furia > 0.0)
        self.sirviendoAntes = ahora

    def furiaServir(self) -> float:
        return min(1.0, max(0.0, (self.calor() - 0.45) / 0.3))

    def vasoLleno(self) -> bool:
        return self.llenado >= 0.8

    def clienteEsperando(self) -> bool:
        return self.cliente is not None and self.cliente["estado"] == "esperando"

    def cajaVasoQuieto(self) -> pygame.Rect:
        if not self.listo:
            return pygame.Rect(self.baseVaso[0] - 55, self.baseVaso[1] - 150, 110, 150)
        return self.vasos[self.cuadroVaso()].get_rect(midbottom=self.baseVaso)

    def cajaCliente(self) -> Optional[pygame.Rect]:
        if self.cliente is None or not self.listo:
            return None
        return self.clientes[self.cliente["cual"]].get_rect(midbottom=(self.xCliente(self.cliente["cual"]), self.lineaMostrador + 4))

    def xCliente(self, cual: int) -> int:
        corridos = {7: -150}
        return self.centroCliente + corridos.get(cual, 0)

    def agarrarVaso(self, pos, es_camara: bool = False) -> None:
        if self.escribiendo > 0.0:
            return
        caja = self.cajaVasoQuieto()
        self.estadoVaso = "arrastrando"
        self.agarreVaso = (pos[0] - caja.centerx, pos[1] - caja.bottom)
        self.posArrastre = [float(pos[0]), float(pos[1])]
        self.mouseServir = False
        self._servir_por_camara = False
        self._arrastre_por_camara = es_camara
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def soltarVaso(self, pos, es_camara: bool = False) -> None:
        caja = self.cajaCliente()
        if caja is not None and self.clienteEsperando():
            if es_camara:
                if caja.inflate(180, 200).collidepoint(pos) or (pos[0] >= 1280 and pos[1] <= 860):
                    self.entregarVaso()
                    return
            elif caja.inflate(120, 160).collidepoint(pos):
                self.entregarVaso()
                return
        self.devolverVaso()

    def devolverVaso(self) -> None:
        if self.estadoVaso != "arrastrando":
            return
        self.origenEntrega = self.puntoVasoArrastrado()
        self.estadoVaso = "volviendo"
        self.tiempoVaso = 0.0

    def puntoVasoArrastrado(self) -> tuple:
        x = self.posArrastre[0] - self.agarreVaso[0]
        y = self.posArrastre[1] - self.agarreVaso[1]
        return (int(x), int(y))

    def movimientoVaso(self) -> float:
        fuerza = max(0.0, (self.rabia - 0.5) / 0.5)
        return math.sin(self.tiempoJugado * 9.0) * 75.0 * fuerza

    def regarVaso(self, aplastado: bool = False) -> None:
        self.estadoVaso = "regandose"
        self.tiempoVaso = 0.0
        self.vasoPendiente = False
        self.vasoAplastado = aplastado
        self.teclaServir = False
        self.mouseServir = False
        self.gestoServir = False
        self._servir_por_camara = False
        self._arrastre_por_camara = False
        if aplastado:
            self.decir(random.choice(mensajesRabia), self.chorroX - 260, 600)
            self.decir("¡Aplastaste el vaso de la rabia!", self.chorroX - 260, 660)
            self.trigger_screenshake(12.0, 0.3)
        else:
            self.decir("¡Se regó el patillazo!", self.chorroX - 120, 640)
        self.sumarFallo()
        if hasattr(self.audio, "play_miss"):
            self.audio.play_miss()

    def entregarVaso(self) -> None:
        if not self.vasoLleno() or not self.clienteEsperando() or self.escribiendo > 0.0:
            return
        if self.estadoVaso == "arrastrando":
            self.origenEntrega = self.puntoVasoArrastrado()
        elif self.estadoVaso == "listo":
            self.origenEntrega = self.baseVaso
        else:
            return
        self.estadoVaso = "entregando"
        self.tiempoVaso = 0.0
        self.vasoPendiente = False
        self.patillazosServidos += 1
        self.cliente["estado"] = "contento"
        self.cliente["tiempo"] = 0.0
        if hasattr(self.audio, "play_click"):
            self.audio.play_click()

    def actualizarCliente(self, dt: float) -> None:
        if self.cliente is None:
            self.esperaCliente -= dt
            if self.esperaCliente <= 0.0:
                cual = self.ordenClientes[self.cuantosClientes % len(self.ordenClientes)]
                self.cuantosClientes += 1
                self.cliente = {"cual": cual, "estado": "llegando", "tiempo": 0.0, "paciencia": 12.0}
            return

        c = self.cliente
        c["tiempo"] += dt
        if c["estado"] == "llegando" and c["tiempo"] >= 0.4:
            c["estado"] = "esperando"
            c["tiempo"] = 0.0
        elif c["estado"] == "esperando":
            c["paciencia"] -= dt
            if c["paciencia"] <= 0.0:
                c["estado"] = "bravo"
                c["tiempo"] = 0.0
                self.sumarFallo()
        elif c["estado"] in ("contento", "bravo") and c["tiempo"] >= 1.3:
            c["estado"] = "yendose"
            c["tiempo"] = 0.0
        elif c["estado"] == "yendose" and c["tiempo"] >= 0.4:
            self.cliente = None
            self.esperaCliente = random.uniform(1.0, 2.0)

    def frasePedido(self) -> str:
        c = self.cliente
        if c["estado"] == "contento":
            return graciasPorCliente.get(c["cual"], "¡Gracias, mi llave!")
        if c["estado"] == "bravo":
            return "¡Ombe, qué demora! Me voy"
        if c["estado"] == "aplaudiendo":
            return "¡Así se cocina, mi llave!"
        if c["cual"] == 1 and c["tiempo"] < 2.0:
            return "¡Espérate, que lo grabo!"
        frases = pedidosPorCliente.get(c["cual"], pedidosPatillazo)
        return frases[int(c["tiempo"] / 4.0) % len(frases)]

    def actualizarMano(self, dt: float) -> None:
        if not self.listo:
            return
        if self.tiempoMano > 0.0:
            self.tiempoMano -= dt
        for arepa in self.arepas:
            if arepa["sacando"] > 0.0:
                x, y, escala, avance = self.caminoSacando(arepa)
                destino = (x - self.puntaMano[0], y - self.puntaMano[1] + 8)
                if avance < 0.12:
                    suavidad = min(1.0, dt * 18.0)
                    self.posMano[0] += (destino[0] - self.posMano[0]) * suavidad
                    self.posMano[1] += (destino[1] - self.posMano[1]) * suavidad
                else:
                    self.posMano = [destino[0], destino[1]]
                return
        if self.escribiendo > 0.0:
            destino = (self.manoReposo[0] - 120, self.manoReposo[1] + 330)
        elif self.tiempoMano > 0.0 and self.manoObjetivo:
            destino = (self.manoObjetivo[0] - self.puntaMano[0], self.manoObjetivo[1] - self.puntaMano[1] - 20)
        else:
            destino = self.manoReposo
        suavidad = min(1.0, dt * 14.0)
        self.posMano[0] += (destino[0] - self.posMano[0]) * suavidad
        self.posMano[1] += (destino[1] - self.posMano[1]) * suavidad

    def actualizarEfectos(self, dt: float) -> None:
        self.golpeAceite = max(0.0, self.golpeAceite - dt / 0.9)
        calor = self.calor()
        hervor = 12.0 + 45.0 * calor
        cuantas = hervor * dt
        while cuantas > 0.0:
            if random.random() < cuantas:
                self.burbujas.append({
                    "x": random.uniform(-0.88, 0.88), "y": random.uniform(-0.82, 0.82),
                    "r": random.uniform(3, 8) + 9 * calor * random.random(), "vida": 1.0,
                    "rapidez": random.uniform(1.2, 2.2) + 1.5 * calor,
                })
            cuantas -= 1.0
        for b in self.burbujas[:]:
            b["vida"] -= dt * b["rapidez"]
            b["r"] += dt * (8 + 14 * calor)
            if b["vida"] <= 0:
                self.burbujas.remove(b)

        for brillo in self.brillos:
            brillo["fase"] += dt * (0.6 + 2.5 * calor)

        if random.random() < dt * (0.9 + 6.0 * calor):
            self.salpicarCaldero()

        if self.enfado() > 0.5 and random.random() < dt * 5.0:
            x = self.posMano[0] + self.puntaMano[0] * 0.5 + random.uniform(-60, 60)
            self.humo.append({"x": x, "y": self.posMano[1] + 40, "vx": random.uniform(-30, 30),
                              "escala": random.uniform(0.4, 0.6), "vida": 0.9})

        for g in self.gotas[:]:
            g["vy"] += 1100 * dt
            g["x"] += g["vx"] * dt
            g["y"] += g["vy"] * dt
            g["vida"] -= dt
            if g["vida"] <= 0:
                self.gotas.remove(g)

        for h in self.humo[:]:
            h["y"] -= 60 * dt
            h["x"] += h["vx"] * dt
            h["escala"] += dt * 0.6
            h["vida"] -= dt
            if h["vida"] <= 0:
                self.humo.remove(h)

    def avanzarMensajes(self, dt: float) -> None:
        for m in self.mensajes[:]:
            m["vida"] -= dt
            if m["vida"] <= 0:
                self.mensajes.remove(m)

    def decir(self, texto: str, x: float, y: float) -> None:
        self.mensajes.append({"texto": texto, "x": x, "y": y, "vida": 1.4})

    def salpicar(self, x: float, y: float, cuantas: int, grandes: bool) -> None:
        if not self.listo:
            return
        for _ in range(cuantas):
            imagenes = self.gotasGrandes if grandes else self.gotasChicas
            self.gotas.append({
                "img": random.choice(imagenes), "x": x + random.uniform(-30, 30), "y": y,
                "vx": random.uniform(-260, 260), "vy": random.uniform(-720, -380) * (1.3 if grandes else 1.0),
                "vida": random.uniform(0.6, 1.0), "total": 1.0,
            })

    def salpicarCaldero(self) -> None:
        cx, cy = self.centroAceite
        rx, ry = self.radioAceite
        angulo = random.uniform(0, math.pi * 2)
        calor = self.calor()
        grandes = calor > 0.6 and random.random() < calor - 0.4
        self.salpicar(cx + math.cos(angulo) * rx * 0.7, cy + math.sin(angulo) * ry * 0.7, 1 + int(calor * 2), grandes)

    def echarHumo(self, x: float, y: float) -> None:
        for _ in range(3):
            self.humo.append({"x": x + random.uniform(-30, 30), "y": y - 10, "vx": random.uniform(-20, 20),
                              "escala": random.uniform(0.5, 0.8), "vida": 1.1})

    def empezarSecuencia(self, nombre: str) -> None:
        self.secuencia = nombre
        self.tiempoSecuencia = 0.0
        self.teclaServir = False
        self.mouseServir = False
        self.gestoServir = False
        self._servir_por_camara = False
        self._arrastre_por_camara = False
        self.reflexion = None
        self.reflexionPendiente = None
        self.burlaPendiente = None
        self.reanudarMusica()
        if self.estadoVaso in ("arrastrando", "volviendo"):
            self.estadoVaso = "listo"
        if self.estadoVaso == "entregando":
            self.estadoVaso = "listo"
            self.llenado = 0.0
        if nombre == "explosion":
            self.vistasInicio = self.espectadores
            self.manoQuemada = True
            self.trigger_screenshake(26.0, 0.6)
            for arepa in self.arepas:
                if arepa["seVuela"] <= 0.0 and arepa["quemada"] <= 0.0:
                    arepa["seVuela"] = 0.8
                    arepa["direccion"] = random.choice((-1, 1))
            if self.estadoVaso == "listo":
                self.estadoVaso = "regandose"
                self.tiempoVaso = 0.0
                self.vasoAplastado = True
            if hasattr(self.audio, "play_hit"):
                self.audio.play_hit()
        elif nombre == "victoria":
            self.trol["estado"] = "aburrido"
            self.trol["t"] = 0.0
            self.trol["frase"] = "Qué aburrido, este no muerde"
            self.agregarComentario("¡Así se hace, mi llave!")
            self.agregarComentario("Se fue el trol, jajaja")
            self.cliente = {"cual": 3, "estado": "aplaudiendo", "tiempo": 0.0, "paciencia": 0.0}

    def avanzarSecuencia(self, dt: float) -> None:
        self.tiempoSecuencia += dt
        self.actualizarEfectos(dt)
        if self.estadoVaso == "regandose":
            self.tiempoVaso = min(0.9, self.tiempoVaso + dt)
        for arepa in self.arepas:
            if arepa["seVuela"] > 0.0:
                arepa["seVuela"] = max(0.001, arepa["seVuela"] - dt)
        if self.secuencia == "explosion":
            if self.tiempoSecuencia > 0.8 and random.random() < dt * 4.0 and self.listo:
                lado = random.choice((-1, 1))
                self.emojisVolando.append({
                    "img": random.choice(self.emojis), "x": 960 + lado * random.uniform(260, 470),
                    "y": 980.0, "vy": random.uniform(-260, -180), "fase": random.uniform(0, 6),
                })
            for e in self.emojisVolando[:]:
                e["y"] += e["vy"] * dt
                if e["y"] < 80:
                    self.emojisVolando.remove(e)
            if self.tiempoSecuencia >= 5.0:
                self.ensenanzaFinal = {"gana": Fritanga84Microgame.ensenanzaFinal["gana"], "pierde": self.ensenanzaRabia}
                self.finish_game(False)
        elif self.secuencia == "victoria":
            self.trol["t"] += dt
            for c in self.chat:
                c["t"] += dt
            if self.tiempoSecuencia >= 3.0:
                self.finish_game(True)

    def finish_game(self, won: bool) -> None:
        yaTerminado = self.is_finished
        if not yaTerminado:
            if self.canalAceite is not None:
                self.canalAceite.stop()
                self.canalAceite = None
            if getattr(self, "canalTrol", None) is not None:
                self.canalTrol.stop()
                self.canalTrol = None
            if hasattr(self.audio, "sonarEscritura"):
                self.audio.sonarEscritura(False)
        super().finish_game(won)
        if yaTerminado:
            return
        if getattr(self, "finLetrero", None):
            self.outro_duration = max(self.outro_duration, self.finLetrero + self.horarioFinal()[-1] + 3.0)
        self.pausarMusica()

    def lineasFinales(self) -> list:
        ensenanza = getattr(self, "ensenanzaFinal", None) or Fritanga84Microgame.ensenanzaFinal
        return list(ensenanza["gana" if self.is_won else "pierde"]) + [self.fraseRedes]

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

    def render_game(self, surface: pygame.Surface) -> None:
        if not self.listo:
            surface.fill((60, 40, 30))
            return
        surface.blit(self.fondo, (0, 0))
        self.dibujarCamara(surface)
        self.dibujarCliente(surface)
        surface.blit(self.caldero, self.cajaCaldero)
        self.dibujarBurbujas(surface)
        self.dibujarArepas(surface)
        self.dibujarHumo(surface)
        self.dibujarPatillazo(surface)
        if self.secuencia == "victoria":
            self.dibujarPropina(surface)
        verCelular = self.secuencia != "explosion" or self.tiempoSecuencia < 0.8
        if verCelular and self.celularCentro <= 0.0:
            self.dibujarCelular(surface)
        self.dibujarGotas(surface)
        mano = self.manoCuritas if self.manoQuemada else self.mano
        temblor = 0
        calor = self.calor()
        if calor > 0.5:
            temblor = int(math.sin(self.tiempoJugado * 50.0) * 10 * (calor - 0.5) / 0.5)
        if self.enfado() > 0.0:
            rojo = int(80 * self.enfado())
            mano = mano.copy()
            mano.fill((255, 255 - rojo, 255 - rojo), special_flags=pygame.BLEND_RGB_MULT)
        surface.blit(mano, (int(self.posMano[0]) + temblor, int(self.posMano[1])))
        self.dibujarArepasSacando(surface)
        self.dibujarArepasVolando(surface)
        self.dibujarVasoArrastrado(surface)
        if self.shake_offset_x or self.shake_offset_y:
            surface.scroll(self.shake_offset_x, self.shake_offset_y)
        self.dibujarRabia(surface)
        self.dibujarHud(surface)
        self.dibujarMensajes(surface)
        if self.filtro > 0.0:
            tono = int(255 - 175 * self.filtro)
            surface.fill((tono, tono, tono), special_flags=pygame.BLEND_RGB_MULT)
        if verCelular and self.celularCentro > 0.0:
            self.dibujarCelular(surface)
        if self.destaqueTermo is None:
            self.dibujarTermometro(surface)
        if self.trol["estado"] == "aviso" and self.filtro > 0.0:
            self.dibujarOpcionesTrol(surface)
        if self.reflexion:
            surface.fill((120, 115, 125), special_flags=pygame.BLEND_RGB_MULT)
            self.dibujarReflexion(surface)
        if self.destaqueTermo is not None:
            self.dibujarTermometroDestacado(surface)
        if self.pausaQuemada > 0.0:
            self.dibujarQuemada(surface)
        if self.secuencia == "explosion":
            self.dibujarExplosion(surface)
        if self.tutorial is not None:
            self.dibujarTutorial(surface)
        self.callarAceiteSiPausado()

    def dibujarQuemada(self, surface: pygame.Surface) -> None:
        t = self.duracionQuemada - self.pausaQuemada
        primero = 1.1
        if t < primero:
            self.dibujarAyMeQueme(surface, t)
            return
        t -= primero
        visible = min(1.0, t / 0.3, self.pausaQuemada / 0.3)
        velo = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        velo.fill((40, 22, 18, int(100 + 95 * visible)))
        surface.blit(velo, (0, 0))
        self.bordeRojo.set_alpha(int(255 * visible * (0.55 + 0.35 * math.sin(t * 6.0))))
        surface.blit(self.bordeRojo, (0, 0))

        conImagen = getattr(self, "imagenQuemadura", None) is not None
        if "lupaMano" not in self.globosHechos and conImagen:
            lupa = self.aAncho(self.imagenQuemadura, 660)
            mano = self.manoCuritas
            w, h = mano.get_size()
            dedos = mano.subsurface((0, int(h * 0.3), w, h - int(h * 0.3)))
            dedos = pygame.transform.smoothscale_by(dedos, lupa.get_width() * 0.86 / float(dedos.get_width()))
            capa = pygame.Surface(lupa.get_size(), pygame.SRCALPHA)
            capa.blit(dedos, dedos.get_rect(midtop=(lupa.get_width() // 2 + 30, -int(lupa.get_height() * 0.14))))
            anchoL, altoL = lupa.get_size()
            dentro = pygame.mask.from_surface(lupa, 40).scale((int(anchoL * 0.9), int(altoL * 0.88)))
            forma = pygame.Surface((anchoL, altoL), pygame.SRCALPHA)
            forma.fill((255, 255, 255, 0))
            recorte = dentro.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(255, 255, 255, 0))
            forma.blit(recorte, recorte.get_rect(center=(anchoL // 2, altoL // 2)))
            capa.blit(forma, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            lupa.blit(capa, (0, 0))
            self.globosHechos["lupaMano"] = lupa
        if "lupaMano" not in self.globosHechos:
            mano = self.manoCuritas
            w, h = mano.get_size()
            dedos = mano.subsurface((0, int(h * 0.5), w, h - int(h * 0.5)))
            dedos = pygame.transform.smoothscale_by(dedos, 560 / float(dedos.get_width()))
            lupa = pygame.Surface((620, 440), pygame.SRCALPHA)
            pygame.draw.ellipse(lupa, (255, 236, 205, 255), lupa.get_rect())
            lupa.blit(dedos, dedos.get_rect(midtop=(lupa.get_width() // 2 + 30, 20)))
            forma = pygame.Surface(lupa.get_size(), pygame.SRCALPHA)
            pygame.draw.ellipse(forma, (255, 255, 255, 255), forma.get_rect())
            lupa.blit(forma, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            self.globosHechos["lupaMano"] = lupa
        lupa = self.globosHechos["lupaMano"]
        latido = math.sin(t * 7.0)
        crecer = min(1.0, t / 0.35)
        crecer = 1.0 + 2.7 * (crecer - 1.0) ** 3 + 1.7 * (crecer - 1.0) ** 2
        lupa = pygame.transform.smoothscale_by(lupa, max(0.05, (0.3 + 0.7 * crecer) * (1.0 + 0.02 * latido)))
        lupa.set_alpha(int(255 * visible))
        temblor = int(math.sin(t * 70.0) * 8 * max(0.0, 1.0 - t / 0.5))
        hueco = lupa.get_rect(center=(960 + temblor, 680))
        surface.blit(lupa, hueco)
        if not conImagen:
            borde = hueco.inflate(int(14 + 6 * latido), int(14 + 6 * latido))
            self.trazoAMano(surface, borde, True, (255, 196, 90), 5, 2.0)
            self.trazoAMano(surface, borde.inflate(14, 14), True, (110, 50, 25), 2, 2.5)

        for i in range(3):
            subida = (t * 0.6 + i * 0.33) % 1.0
            vapor = pygame.transform.smoothscale_by(self.nube, 0.7 + 0.6 * subida)
            vapor.set_alpha(int(170 * visible * (1.0 - subida)))
            surface.blit(vapor, vapor.get_rect(center=(hueco.centerx - 120 + i * 120, hueco.top + 60 - int(subida * 160))))

        salto = min(1.0, t / 0.6)
        salto = 1.0 - (1.0 - salto) ** 3
        for i in range(12):
            angulo = i * 0.52 + 0.25
            lejos = 0.62 + 0.55 * salto
            x = hueco.centerx + math.cos(angulo) * hueco.w / 2 * lejos
            y = hueco.centery + math.sin(angulo) * hueco.h / 2 * lejos + 220 * max(0.0, t - 0.4) ** 2
            gota = pygame.transform.smoothscale_by(self.gotasGrandes[i % len(self.gotasGrandes)], 0.8 + 0.4 * (i % 3) / 2)
            gota = pygame.transform.rotate(gota, -math.degrees(angulo) + 90)
            gota.set_alpha(int(255 * visible * min(1.0, max(0.0, (2.6 - t) / 0.6))))
            surface.blit(gota, gota.get_rect(center=(int(x), int(y))))

        if "quemada" not in self.globosHechos:
            self.globosHechos["quemada"] = (
                self.textoBorde(self.fuentePregunta, "¡Por cocinar con rabia te quemaste!", (255, 220, 150), (120, 40, 25), 5),
                self.textoBorde(self.fuenteMensaje, "Mira cómo te quedó la mano", (255, 244, 225), (90, 45, 30), 3))
        titulo, debajo = self.globosHechos["quemada"]
        golpe = 1.0 + 0.35 * (1.0 - min(1.0, t / 0.35)) ** 2
        titulo = pygame.transform.smoothscale_by(titulo, golpe)
        titulo.set_alpha(int(255 * visible))
        debajo.set_alpha(int(255 * visible))
        arriba = 210
        surface.blit(titulo, titulo.get_rect(midtop=(960, arriba)))
        surface.blit(debajo, debajo.get_rect(midtop=(960, arriba + 92)))

    def dibujarAyMeQueme(self, surface: pygame.Surface, t: float) -> None:
        oscuro = min(1.0, t / 0.25)
        velo = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        velo.fill((40, 22, 18, int(100 * oscuro)))
        surface.blit(velo, (0, 0))
        destello = max(0.0, 1.0 - t / 0.5)
        self.bordeRojo.set_alpha(int(255 * (0.5 + 0.5 * destello)))
        surface.blit(self.bordeRojo, (0, 0))
        if "ayMeQueme" not in self.globosHechos:
            grande = self.assets.cargarFuenteTitulo(88)
            self.globosHechos["ayMeQueme"] = self.textoBorde(grande, "¡Ay, me quemé!", (255, 236, 200), (150, 30, 20), 6)
        texto = self.globosHechos["ayMeQueme"]
        golpe = 1.0 + 0.6 * (1.0 - min(1.0, t / 0.2)) ** 2
        texto = pygame.transform.smoothscale_by(texto, golpe)
        temblor = (int(math.sin(t * 80.0) * 10), int(math.cos(t * 65.0) * 6))
        mano = self.manoCuritas.get_rect(topleft=(int(self.posMano[0]), int(self.posMano[1])))
        centro = (max(texto.get_width() // 2 + 20, mano.centerx + 120) + temblor[0], mano.top - 40 + temblor[1])
        surface.blit(texto, texto.get_rect(midbottom=centro))

    def textoBorde(self, fuente, texto: str, color=(255, 248, 236), borde=(96, 56, 30), grosor: int = 3) -> pygame.Surface:
        return self.textoConBorde(fuente, texto, color, borde, grosor)

    def textoQueQuepa(self, fuente, texto: str, color, ancho: int) -> pygame.Surface:
        letras = fuente.render(texto, True, color)
        if letras.get_width() > ancho:
            letras = pygame.transform.smoothscale_by(letras, ancho / float(letras.get_width()))
        return letras

    def partirEnLineas(self, fuente, texto: str, anchoMax: int) -> list:
        lineas = []
        actual = ""
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

    def globoHablado(self, texto: str, volteado: bool) -> pygame.Surface:
        clave = ("habla", texto, volteado)
        if clave not in self.globosHechos:
            lineas = [self.fuenteGlobo.render(linea, True, (110, 62, 36))
                      for linea in self.partirEnLineas(self.fuenteGlobo, texto, 440)]
            altoLetras = sum(l.get_height() for l in lineas)
            alto = 96 if len(lineas) == 1 else int(96 + (altoLetras - lineas[0].get_height()) * 1.25)
            base = pygame.transform.smoothscale_by(self.globoTexto, 96 / float(self.globoTexto.get_height()))
            ancho = max(l.get_width() for l in lineas)
            globo = self.estirarCentro(base, max(base.get_width(), ancho + 90))
            if alto != 96:
                globo = pygame.transform.smoothscale(globo, (globo.get_width(), alto))
            if volteado:
                globo = pygame.transform.flip(globo, True, False)
            y = int(globo.get_height() * 0.4) - altoLetras // 2
            for letras in lineas:
                globo.blit(letras, letras.get_rect(midtop=(globo.get_width() // 2, y)))
                y += letras.get_height()
            self.globosHechos[clave] = globo
        return self.globosHechos[clave]

    def filaChat(self, texto: str, propio: bool, trol: bool) -> pygame.Surface:
        anchoMax = self.pantalla.w - 30
        avatar = None if propio else (self.avatarTrol if trol else random.choice(self.avatares))
        espacioAvatar = 0 if avatar is None else avatar.get_width() + 6
        color = (120, 40, 40) if propio else (80, 46, 92)
        letras = self.textoQueQuepa(self.fuenteChat, texto, color, anchoMax - espacioAvatar - 40)
        globo = self.estirarCentro(self.globoComentario, max(letras.get_width() + 36, self.globoComentario.get_height() * 2))
        if propio:
            globo = self.tenir(globo, (255, 200, 170))
        globo.blit(letras, letras.get_rect(center=(globo.get_width() // 2, globo.get_height() // 2 - 1)))
        fila = pygame.Surface((espacioAvatar + globo.get_width(), max(globo.get_height(), avatar.get_height() if avatar else 0)),
                              pygame.SRCALPHA)
        if avatar is not None:
            fila.blit(avatar, avatar.get_rect(midleft=(0, fila.get_height() // 2)))
        fila.blit(globo, globo.get_rect(midleft=(espacioAvatar, fila.get_height() // 2)))
        return fila

    def lugarCelular(self):
        c = self.celularCentro
        suave = c * c * (3 - 2 * c)
        x0, y0 = self.cajaCelular.center
        x1, y1 = self.centroGrande
        centro = (int(x0 + (x1 - x0) * suave), int(y0 + (y1 - y0) * suave))
        return centro, 1.0 + (self.escalaGrande - 1.0) * suave

    def dibujarCelular(self, surface: pygame.Surface) -> None:
        celular = self.armarCelular()
        centro, escala = self.lugarCelular()
        if escala > 1.001:
            celular = pygame.transform.smoothscale_by(celular, escala)
        surface.blit(celular, celular.get_rect(center=centro))

    def armarCelular(self) -> pygame.Surface:
        p = self.pantalla
        lienzo = pygame.Surface(self.cajaCelular.size, pygame.SRCALPHA)
        pantalla = pygame.Surface(p.size, pygame.SRCALPHA)
        pygame.draw.rect(pantalla, (252, 240, 222), pantalla.get_rect(), border_radius=34)

        if "enVivo" not in self.globosHechos:
            etiqueta = self.estirarCentro(self.etiquetaEnVivo, 140)
            texto = self.textoBorde(self.fuenteChat, "En vivo", (255, 248, 236), (130, 30, 40), 2)
            etiqueta.blit(texto, texto.get_rect(midleft=(44, etiqueta.get_height() // 2 - 1)))
            self.globosHechos["enVivo"] = etiqueta
        pantalla.blit(self.globosHechos["enVivo"], (14, 14))
        cifra = f"{int(self.espectadores):,}".replace(",", ".")
        letras = self.fuenteChat.render(cifra, True, (80, 46, 92))
        pastilla = self.estirarCentro(self.pastillaVistas, letras.get_width() + 76)
        pastilla.blit(letras, letras.get_rect(midright=(pastilla.get_width() - 16, pastilla.get_height() // 2 - 1)))
        pantalla.blit(pastilla, pastilla.get_rect(topright=(p.w - 14, 14)))

        arribaChat = 76
        if self.trol["estado"] in ("aviso", "leyendo", "aburrido"):
            arribaChat = self.dibujarTrol(pantalla) + 8

        conBarra = self.trol["estado"] in ("aviso", "leyendo")
        if conBarra:
            abajo = p.h - 150
        else:
            abajo = p.h - 20
        y = abajo
        for c in reversed(self.chat):
            fila = c["fila"]
            entrada = min(1.0, c["t"] / 0.25)
            y -= fila.get_height() + 6
            if y < arribaChat:
                break
            x = p.w - fila.get_width() - 12 if c["propio"] else 12
            pantalla.blit(fila, (x - int((1.0 - entrada) * 20), y))

        if conBarra:
            barra = self.estirarCentro(self.globoComentario, p.w - 24)
            if self.escribiendo > 0.0:
                avance = 1.0 - self.escribiendo / self.duracionEscribir
                escrito = self.textoEscribiendo[:int(len(self.textoEscribiendo) * min(1.0, avance * 1.3))]
                letras = self.textoQueQuepa(self.fuenteChat, escrito + "|", (120, 40, 40), barra.get_width() - 40)
            else:
                cursor = "|" if int(self.tiempoAviso * 2.5) % 2 == 0 else " "
                letras = self.textoQueQuepa(self.fuenteChat, "Escribe un comentario..." + cursor, (150, 125, 140),
                                            barra.get_width() - 40)
            barra.blit(letras, letras.get_rect(midleft=(20, barra.get_height() // 2 - 1)))
            pantalla.blit(barra, barra.get_rect(midbottom=(p.w // 2, p.h - 22)))

        lienzo.blit(pantalla, (p.x - self.cajaCelular.x, p.y - self.cajaCelular.y))
        lienzo.blit(self.marcoCelular, (0, 0))
        return lienzo

    def dibujarCamara(self, surface: pygame.Surface) -> None:
        camara = self.camaraLive
        caja = camara.get_rect(midtop=(1270, self.lineaMostrador - 330))
        visible = max(0, self.lineaMostrador - caja.top)
        surface.blit(camara, caja, (0, 0, caja.w, visible))
        if int(self.tiempoJugado * 2.0) % 2 == 0:
            luz = (caja.x + int(caja.w * 0.417), caja.y + int(caja.h * 0.072))
            brillo = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(brillo, (255, 70, 60, 110), (20, 20), 18)
            pygame.draw.circle(brillo, (255, 120, 100, 200), (20, 20), 8)
            surface.blit(brillo, (luz[0] - 20, luz[1] - 20))

    def dibujarReflexion(self, surface: pygame.Surface) -> None:
        lineas = self.reflexion["lineas"]
        clave = ("reflexion", tuple(lineas))
        if clave not in self.globosHechos:
            self.globosHechos[clave] = self.crearCartel(lineas)
        cartel = self.globosHechos[clave]
        if not cartel:
            return
        t = self.reflexion["t"]
        entrada = min(1.0, t / 0.45)
        rebote = 1.0 + 2.7 * (entrada - 1.0) ** 3 + 1.7 * (entrada - 1.0) ** 2
        escala = max(0.05, 0.2 + 0.8 * rebote)
        salida = min(1.0, max(0.0, (6.5 - t) / 0.35))
        dibujo = pygame.transform.smoothscale_by(cartel, escala)
        if salida < 1.0 or entrada < 1.0:
            dibujo.set_alpha(int(255 * min(entrada, salida)))
        caja = dibujo.get_rect(center=(960, 520))
        surface.blit(dibujo, caja)
        if t >= 2.0:
            seguir = self.textoBorde(self.fuenteAyuda, "Clic o Enter para seguir", (255, 248, 236), (70, 50, 40), 2)
            seguir.set_alpha(int(255 * min(1.0, (t - 2.0) / 0.4) * salida))
            surface.blit(seguir, seguir.get_rect(center=(960, 985)))

    def dibujarOpcionesTrol(self, surface: pygame.Surface) -> None:
        entrada = min(1.0, self.tiempoAviso / 0.35)

        centro, escala = self.lugarCelular()
        p = self.pantalla
        barraX = p.centerx - self.cajaCelular.centerx
        barraY = p.bottom - 22 - 23 - self.cajaCelular.centery
        barra = (int(centro[0] + barraX * escala), int(centro[1] + barraY * escala))
        if "pregunta" not in self.globosHechos:
            self.globosHechos["pregunta"] = self.textoBorde(self.fuentePregunta, "¿Le respondes?", (255, 236, 120),
                                                            (140, 25, 35), 6)
        latido = 1.0 + 0.06 * math.sin(self.tiempoAviso * 7.0)
        pregunta = pygame.transform.smoothscale_by(self.globosHechos["pregunta"], (0.5 + 0.5 * entrada) * latido)
        pregunta.set_alpha(int(255 * entrada))
        caja = pregunta.get_rect(midbottom=(barra[0], barra[1] - 60))
        surface.blit(pregunta, caja)
        bajada = int(4 * math.sin(self.tiempoAviso * 7.0))
        flecha = self.flechaAbajo.copy()
        flecha.set_alpha(int(255 * entrada))
        surface.blit(flecha, flecha.get_rect(midbottom=(barra[0], barra[1] - 18 + bajada)))

        if "moradoApagado" not in self.globosHechos:
            self.globosHechos["moradoApagado"] = self.suavizarColores(self.botonMorado)
            luz = pygame.Surface((520, 230), pygame.SRCALPHA)
            for paso in range(12, 0, -1):
                pygame.draw.ellipse(luz, (255, 90, 60, 30), luz.get_rect().inflate(-paso * 30, -paso * 13))
            self.globosHechos["luzResponder"] = luz
        latido = math.sin(self.tiempoAviso * 8.0)
        etiquetas = ["¡Responderle! (R)", "Ignorar (I)"]
        for i, caja in enumerate(self.botonesAviso):
            elegido = i == self.opcionAviso
            escala = self.escalaBotonAviso(i) * (0.6 + 0.4 * entrada)
            if i == 0:
                luz = self.globosHechos["luzResponder"]
                luz.set_alpha(int(255 * entrada * (0.75 + 0.25 * latido)))
                surface.blit(luz, luz.get_rect(center=caja.center))
            if elegido:
                imagen, contorno, colorLetras = self.botonRojo, (120, 26, 34), (255, 248, 236)
            elif i == 0:
                imagen, contorno, colorLetras = self.botonMorado, (70, 30, 110), (255, 248, 236)
            else:
                imagen, contorno, colorLetras = self.globosHechos["moradoApagado"], (90, 70, 100), (235, 228, 236)
            imagen = pygame.transform.smoothscale_by(imagen, escala)
            surface.blit(imagen, imagen.get_rect(center=caja.center))
            texto = self.textoBorde(self.fuenteBoton, etiquetas[i], colorLetras, contorno)
            if escala != 1.0:
                texto = pygame.transform.smoothscale_by(texto, escala)
            surface.blit(texto, texto.get_rect(center=(caja.centerx, caja.centery - 3)))
        ayuda = "Flechas para elegir y Enter para aceptar"
        camara = getattr(self, "camara", None)
        if camara and camara.enabled:
            ayuda += "  ·  Palma: ignorar  ·  Puño: responder"
        texto = self.textoBorde(self.fuenteAyuda, ayuda, (255, 248, 236), (70, 50, 40), 2)
        surface.blit(texto, texto.get_rect(center=(960, 985)))

    def dibujarTrol(self, pantalla: pygame.Surface) -> int:
        p = self.pantalla
        clave = ("trol", self.trol["frase"], self.seguidoresTrol)
        if clave not in self.globosHechos:
            ancho = p.w - 24
            nombre = self.fuenteTrol.render("@ElQueMásSabe", True, (170, 40, 40))
            seguidores = self.fuenteChat.render(f"{self.seguidoresTrol:,} seguidores".replace(",", "."), True, (130, 90, 70))
            lineas = self.partirEnLineas(self.fuenteTrol, self.trol["frase"], int(ancho * 0.78))[:3]
            textos = [self.fuenteTrol.render(l, True, (90, 50, 36)) for l in lineas]
            alto = nombre.get_height() + sum(t.get_height() for t in textos) + seguidores.get_height()
            globo = self.aAncho(self.globoTexto, ancho)
            altoGlobo = max(globo.get_height(), int((alto + 30) / 0.78))
            globo = pygame.transform.smoothscale(globo, (ancho, altoGlobo))
            cuerpo = int(globo.get_height() * 0.8)
            y = max(10, (cuerpo - alto) // 2)
            for t in [nombre] + textos + [seguidores]:
                globo.blit(t, t.get_rect(midtop=(globo.get_width() // 2, y)))
                y += t.get_height()
            self.globosHechos[clave] = globo
        globo = self.globosHechos[clave]

        entrada = 1.0 if self.trol["estado"] == "leyendo" else min(1.0, self.trol["t"] / 0.3)
        temblor = int(math.sin(self.trol["t"] * 60.0) * 6) if self.trol["t"] < 0.5 and self.trol["estado"] == "aviso" else 0
        visible = 1.0
        if self.trol["estado"] == "aburrido":
            visible = max(0.0, 1.0 - max(0.0, self.trol["t"] - 1.8) / 0.6)
        if visible <= 0.0:
            return 76
        arriba = 70
        dibujo = globo
        if entrada < 1.0 or visible < 1.0:
            dibujo = pygame.transform.smoothscale_by(globo, 0.7 + 0.3 * entrada)
            dibujo.set_alpha(int(255 * min(entrada, visible)))
        caja = dibujo.get_rect(midtop=(p.w // 2 + temblor, arriba))
        pantalla.blit(dibujo, caja)
        punta = (caja.left + int(caja.w * 0.11), caja.bottom)
        pantalla.blit(self.avatarTrol, self.avatarTrol.get_rect(midtop=(punta[0] - 16, punta[1] - 4)))
        return caja.bottom + self.avatarTrol.get_height() - 4

    def dibujarCliente(self, surface: pygame.Surface) -> None:
        c = self.cliente
        if c is None:
            return
        imagen = self.clientes[c["cual"]]
        visible = 1.0
        if c["estado"] == "llegando":
            visible = min(1.0, c["tiempo"] / 0.4)
        elif c["estado"] == "yendose":
            visible = max(0.0, 1.0 - c["tiempo"] / 0.4)
        bajada = int((1.0 - visible) * 60)
        caja = imagen.get_rect(midbottom=(self.xCliente(c["cual"]), self.lineaMostrador + 4 + bajada))
        recorte = (0, 0, caja.w, max(0, caja.h - bajada))
        imagen.set_alpha(int(255 * visible))
        surface.blit(imagen, caja, recorte)
        imagen.set_alpha(None)

        if c["estado"] in ("esperando", "contento", "bravo", "aplaudiendo") and self.secuencia != "explosion":
            globo = self.globoHablado(self.frasePedido(), True)
            temblor = 0
            if c["estado"] == "esperando" and c["paciencia"] < 3.0:
                temblor = int(math.sin(self.tiempoJugado * 40.0) * 5)
            punta = (caja.centerx + 10 + temblor, caja.top + 18)
            surface.blit(globo, (punta[0] - int(globo.get_width() * 0.89), punta[1] - globo.get_height()))

    def dibujarBurbujas(self, surface: pygame.Surface) -> None:
        capa = self.capaBurbujas
        capa.fill((0, 0, 0, 0))
        mitadW, mitadH = capa.get_width() // 2, capa.get_height() // 2
        rx, ry = self.radioAceite
        for brillo in self.brillos:
            x = mitadW + (brillo["x"] + math.sin(brillo["fase"]) * 0.15) * rx
            y = mitadH + (brillo["y"] + math.cos(brillo["fase"] * 0.7) * 0.1) * ry
            caja = pygame.Rect(0, 0, int(rx * 0.35), int(ry * 0.12))
            caja.center = (int(x), int(y))
            pygame.draw.ellipse(capa, (255, 244, 200, int(40 + 25 * math.sin(brillo["fase"] * 1.3))), caja)
        for b in self.burbujas:
            x = mitadW + b["x"] * rx
            y = mitadH + b["y"] * ry
            r = b["r"]
            caja = pygame.Rect(0, 0, int(r * 2), max(2, int(r * 0.9)))
            caja.center = (int(x), int(y))
            pygame.draw.ellipse(capa, (255, 236, 170, int(160 * b["vida"])), caja, 2)
            if b["vida"] > 0.6:
                pygame.draw.circle(capa, (255, 250, 220, int(200 * b["vida"])), (int(x - r * 0.3), int(y - r * 0.15)), max(1, int(r * 0.25)))
        surface.blit(capa, capa.get_rect(center=self.centroAceite))

    def dibujarArepas(self, surface: pygame.Surface) -> None:
        for arepa in self.arepas:
            x, y = arepa["x"], arepa["y"]
            if arepa["temblor"] > 0.0:
                x += math.sin(arepa["temblor"] * 60.0) * 6

            if arepa["volteo"] > 0.0:
                avance = 1.0 - arepa["volteo"] / 0.45
                altura = math.sin(avance * math.pi) * 110
                imagen = self.arepaVolando if 0.25 < avance < 0.75 else self.arepaDorada
                surface.blit(imagen, imagen.get_rect(center=(int(x), int(y - altura))))
                continue

            if arepa["sacando"] > 0.0 or arepa["seVuela"] > 0.0:
                continue
            imagen = self.imagenArepa(arepa)
            if arepa["entrada"] < 1.0:
                y -= (1.0 - arepa["entrada"]) ** 2 * 120
                imagen = imagen.copy()
                imagen.set_alpha(int(255 * min(1.0, arepa["entrada"] * 2.0)))
            surface.blit(imagen, imagen.get_rect(center=(int(x), int(y))))

            if arepa["quemada"] <= 0.0 and self.secuencia is None:
                aviso = self.avisoArepa(arepa)
                if aviso:
                    texto = self.textoBorde(self.fuenteArepa, aviso[0], aviso[1], aviso[2])
                    surface.blit(texto, texto.get_rect(center=(int(x), int(y) + 62)))

    def dibujarArepasSacando(self, surface: pygame.Surface) -> None:
        for arepa in self.arepas:
            if arepa["sacando"] <= 0.0:
                continue
            x, y, escala, avance = self.caminoSacando(arepa)
            imagen = pygame.transform.smoothscale_by(self.imagenArepa(arepa), escala)
            imagen = pygame.transform.rotate(imagen, -12 * min(1.0, avance * 2))
            if avance > 0.88:
                imagen.set_alpha(int(255 * max(0.0, (1.0 - avance) / 0.12)))
            surface.blit(imagen, imagen.get_rect(center=(int(x), int(y))))

    def dibujarArepasVolando(self, surface: pygame.Surface) -> None:
        for arepa in self.arepas:
            if arepa["seVuela"] <= 0.0:
                continue
            avance = 1.0 - arepa["seVuela"] / 0.8
            x = arepa["x"] + arepa["direccion"] * 700 * avance
            y = arepa["y"] - 520 * avance + 900 * avance * avance
            imagen = pygame.transform.rotate(self.arepaVolando, arepa["direccion"] * -540 * avance)
            surface.blit(imagen, imagen.get_rect(center=(int(x), int(y))))

    def imagenArepa(self, arepa: dict) -> pygame.Surface:
        if arepa["quemada"] > 0.0:
            return self.arepaQuemada
        coccion = arepa["coccion"]
        if arepa["lado"] == 1 and coccion <= 1.1:
            mezcla = min(1.0, max(0.0, (coccion - 0.15) / 0.5))
            base, encima = self.arepaCruda, self.arepaDorada
        else:
            mezcla = min(1.0, max(0.0, (coccion - 1.1) / (self.puntoQuemado - 1.1)))
            base, encima = self.arepaDorada, self.arepaQuemada
        if mezcla <= 0.0:
            return base
        if mezcla >= 1.0:
            return encima
        imagen = base.copy()
        capa = encima.copy()
        capa.set_alpha(int(255 * mezcla))
        imagen.blit(capa, (0, 0))
        return imagen

    def avisoArepa(self, arepa: dict):
        coccion = arepa["coccion"]
        if coccion > 1.2:
            return ("¡Se quema!", (255, 236, 210), (150, 40, 40))
        if coccion >= 0.55:
            if arepa["lado"] == 1:
                return ("¡Voltéala!", (255, 248, 236), (96, 56, 30))
            return ("¡Sácala!", (255, 248, 236), (40, 100, 60))
        return None

    def dibujarHumo(self, surface: pygame.Surface) -> None:
        for h in self.humo:
            nube = pygame.transform.smoothscale_by(self.nube, h["escala"])
            nube.set_alpha(int(255 * max(0.0, h["vida"] / 1.1)))
            surface.blit(nube, nube.get_rect(center=(int(h["x"]), int(h["y"]))))

    def dibujarPatillazo(self, surface: pygame.Surface) -> None:
        caja = self.cajaBotellon
        vaso = self.vasos[self.cuadroVaso()] if self.estadoVaso == "listo" else None
        cajaVaso = None
        if vaso is not None:
            cajaVaso = vaso.get_rect(midbottom=(self.baseVaso[0] + int(self.movimientoVaso()), self.baseVaso[1]))
            if self.vasoNuevo > 0.0:
                vaso = vaso.copy()
                vaso.set_alpha(int(255 * (1.0 - self.vasoNuevo / 0.3)))
                cajaVaso = cajaVaso.move(0, -int((self.vasoNuevo / 0.3) ** 2 * 50))
        if self.estadoVaso == "volviendo":
            avance = min(1.0, self.tiempoVaso / 0.25)
            avance = 1.0 - (1.0 - avance) ** 2
            x = self.origenEntrega[0] + (self.baseVaso[0] - self.origenEntrega[0]) * avance
            y = self.origenEntrega[1] + (self.baseVaso[1] - self.origenEntrega[1]) * avance
            surface.blit(self.vasos[3], self.vasos[3].get_rect(midbottom=(int(x), int(y))))

        if self.sirviendo() and self.estadoVaso == "listo":
            alto = (cajaVaso.top + 12 if cajaVaso else self.baseVaso[1]) - caja.top
            surface.blit(self.botellonSirviendo, caja, (0, 0, self.botellonSirviendo.get_width(), max(0, alto)))
        else:
            surface.blit(self.botellon, caja)

        if vaso is not None:
            rebose = max(0.0, (self.llenado - 0.8) / (self.puntoDerrame - 0.8))
            if rebose > 0.0:
                cajaVaso = cajaVaso.move(int(math.sin(self.tiempoJugado * 60.0) * 4 * rebose), 0)
            surface.blit(vaso, cajaVaso)
            if self.sirviendo() or self.llenado > 0.0:
                self.dibujarMedidor(surface, cajaVaso)
            if self.vasoLleno() and self.clienteEsperando() and self.secuencia is None:
                if "llevar" not in self.globosHechos:
                    self.globosHechos["llevar"] = self.textoBorde(self.fuenteArepa, "¡Arrástralo al cliente!",
                                                                  (255, 248, 236), (40, 100, 60))
                aviso = self.globosHechos["llevar"]
                salto = int(abs(math.sin(self.tiempoJugado * 4.0)) * 10)
                surface.blit(aviso, aviso.get_rect(midbottom=(min(self.screen_w - 10 - aviso.get_width() // 2, cajaVaso.centerx),
                                                              cajaVaso.top - 8 - salto)))
        elif self.estadoVaso == "regandose" and self.vasoAplastado:
            t = self.tiempoVaso
            fin = 1.0 if self.secuencia else max(0.0, min(1.0, (1.4 - t) / 0.3))

            def suave(x):
                x = min(1.0, max(0.0, x))
                return x * x * (3 - 2 * x)

            pasoLleno = 1.0 - suave(t / 0.12)
            pasoApretado = min(suave((t - 0.04) / 0.12), 1.0 - suave((t - 0.3) / 0.15))
            pasoCharco = suave((t - 0.3) / 0.15) * fin
            for imagen, peso, lugar in ((self.vasos[3], pasoLleno, (self.baseVaso[0], self.baseVaso[1])),
                                        (self.vasoApretado, pasoApretado, (self.baseVaso[0] + 27, self.baseVaso[1])),
                                        (self.vasoCharco, pasoCharco, (self.baseVaso[0] - 30, self.baseVaso[1] + 6))):
                if peso > 0.0:
                    dibujo = imagen.copy()
                    dibujo.set_alpha(int(255 * peso))
                    surface.blit(dibujo, dibujo.get_rect(midbottom=lugar))
        elif self.estadoVaso == "regandose":
            t = self.tiempoVaso
            aparece = min(1.0, t / 0.12)
            fin = max(0.0, min(1.0, (1.0 - t) / 0.3))
            giro = pygame.transform.smoothscale_by(self.vasoCayendo, 0.9 + 0.1 * aparece)
            giro.set_alpha(int(255 * min(aparece, fin)))
            surface.blit(giro, giro.get_rect(midbottom=(self.baseVaso[0] - 10, self.baseVaso[1])))
        elif self.estadoVaso == "entregando":
            avance = min(1.0, self.tiempoVaso / 0.4)
            lleno = self.vasos[3].copy()
            lleno.set_alpha(int(255 * (1.0 - avance)))
            cual = self.cliente["cual"] if self.cliente else 0
            destino = (self.xCliente(cual) - 40, self.lineaMostrador - 40)
            x = self.origenEntrega[0] + (destino[0] - self.origenEntrega[0]) * avance
            y = self.origenEntrega[1] + (destino[1] - self.origenEntrega[1]) * avance
            surface.blit(lleno, lleno.get_rect(midbottom=(int(x), int(y))))

    def dibujarMedidor(self, surface: pygame.Surface, cajaVaso: pygame.Rect) -> None:
        marco = self.medidorMarco
        caja = marco.get_rect(bottomright=(cajaVaso.left - 10, self.baseVaso[1]))
        arriba, raya, fondo = self.nivelesMedidor
        if self.llenado <= 0.8:
            nivel = fondo - (fondo - raya) * self.llenado / 0.8
        else:
            nivel = raya - (raya - arriba) * min(1.0, (self.llenado - 0.8) / (self.puntoDerrame - 0.8))
        liquido = pygame.Surface(marco.get_size(), pygame.SRCALPHA)
        relleno = self.medidorRelleno
        liquido.blit(relleno, relleno.get_rect(midtop=(marco.get_width() // 2, int(nivel - relleno.get_height() * 0.06))))
        liquido.blit(self.medidorDentro, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(marco, caja)
        surface.blit(liquido, caja)
        surface.blit(self.medidorTrazos, caja)

    def dibujarVasoArrastrado(self, surface: pygame.Surface) -> None:
        if self.estadoVaso != "arrastrando":
            return
        x, y = self.puntoVasoArrastrado()
        if self.rabia > 0.5:
            x += int(math.sin(self.tiempoJugado * 40.0) * 6 * (self.rabia - 0.5) / 0.5)
        lleno = self.vasos[3]
        sombra = pygame.Surface((lleno.get_width(), 24), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, (40, 20, 10, 70), sombra.get_rect())
        surface.blit(sombra, sombra.get_rect(center=(x, y + 30)))
        surface.blit(lleno, lleno.get_rect(midbottom=(x, y)))
        caja = self.cajaCliente()
        if caja is not None and self.clienteEsperando() and caja.inflate(120, 160).collidepoint(self.posArrastre):
            if "soltar" not in self.globosHechos:
                self.globosHechos["soltar"] = self.textoBorde(self.fuenteArepa, "¡Suéltalo!", (255, 248, 236), (40, 100, 60))
            surface.blit(self.globosHechos["soltar"], self.globosHechos["soltar"].get_rect(midbottom=(x, y - lleno.get_height() - 6)))

    def cuadroVaso(self) -> int:
        if self.llenado < 0.1:
            return 0
        if self.llenado < 0.35:
            return 1
        if self.llenado < 0.8:
            return 2
        return 3

    def dibujarPropina(self, surface: pygame.Surface) -> None:
        subida = min(1.0, self.tiempoSecuencia / 0.5)
        caja = self.potePropinas.get_rect(midbottom=(1450, int(905 + (1.0 - subida) * 80)))
        pote = self.potePropinas.copy()
        pote.set_alpha(int(255 * subida))
        surface.blit(pote, caja)
        for i in range(5):
            brillo = math.sin(self.tiempoSecuencia * 6.0 + i * 1.7)
            if brillo > 0.3:
                x = caja.left + 20 + (i * 37) % caja.w
                y = caja.top + 10 + (i * 53) % 90
                pygame.draw.circle(surface, (255, 236, 150), (x, y), int(3 + brillo * 4))

    def dibujarGotas(self, surface: pygame.Surface) -> None:
        for g in self.gotas:
            imagen = g["img"]
            imagen.set_alpha(int(255 * min(1.0, g["vida"] / 0.3)))
            surface.blit(imagen, imagen.get_rect(center=(int(g["x"]), int(g["y"]))))
            imagen.set_alpha(None)

    def dibujarRabia(self, surface: pygame.Surface) -> None:
        fuerza = max(0.0, (self.calor() - 0.35) / 0.65)
        if self.secuencia == "explosion":
            fuerza = max(0.0, 1.0 - self.tiempoSecuencia / 0.9)
        if fuerza <= 0.0:
            return
        latido = 0.85 + 0.15 * math.sin(self.tiempoJugado * 8.0)
        self.bordeRojo.set_alpha(int(255 * min(1.0, fuerza * latido)))
        surface.blit(self.bordeRojo, (0, 0))

    def colorRabia(self) -> tuple:
        calma, medio, rabia = (70, 185, 175), (240, 190, 70), (215, 65, 55)
        if self.rabia < 0.5:
            t = self.rabia / 0.5
            de, a = calma, medio
        else:
            t = (self.rabia - 0.5) / 0.5
            de, a = medio, rabia
        return tuple(int(de[i] + (a[i] - de[i]) * t) for i in range(3))

    def dibujarTermometro(self, surface: pygame.Surface) -> None:
        marco = self.marcoTermometro
        c = self.celularCentro if self.secuencia != "explosion" else 0.0
        suave = c * c * (3 - 2 * c)
        x = int(925 + (self.xTermometroAviso() - 925) * suave)
        y = int(150 + (300 - 150) * suave)
        caja = marco.get_rect(midtop=(x, y))
        surface.blit(self.armarTermometro(), caja.move(-8, 0))

    def xTermometroAviso(self) -> int:
        marco = self.marcoTermometro
        orilla = self.centroGrande[0] - int(self.marcoCelular.get_width() * self.escalaGrande) // 2
        return min(self.botonesAviso[0].centerx, orilla - 70 - marco.get_width() // 2)

    def armarTermometro(self) -> pygame.Surface:
        marco = self.marcoTermometro
        w, h = marco.get_size()
        lienzo = pygame.Surface((w + 16, h), pygame.SRCALPHA)
        canal = self.canalTermometro.move(8, 0)
        ancho = int(canal.w * min(1.0, max(0.0, self.rabiaMostrada)))
        corte = int(w * 0.88)
        lienzo.blit(marco, (8, 0), (0, 0, corte, h))
        if ancho >= 4:
            lienzo.blit(self.rellenoTermometro, canal.topleft, (0, 0, ancho, canal.h))
        temblor = 0
        if self.calor() > 0.6:
            temblor = int(math.sin(self.tiempoJugado * 45.0) * 4 * (self.calor() - 0.6) / 0.4)
        lienzo.blit(marco, (8 + corte + temblor, 0), (corte, 0, w - corte, h))
        return lienzo

    def dibujarTermometroDestacado(self, surface: pygame.Surface) -> None:
        d = self.destaqueTermo
        t = d["t"]
        llegar = min(1.0, t / 0.35, max(0.0, (d["dur"] - t) / 0.35))
        llegar = llegar * llegar * (3 - 2 * llegar)
        c = self.celularCentro if self.secuencia != "explosion" else 0.0
        c = c * c * (3 - 2 * c)
        x0 = 925 + (self.xTermometroAviso() - 925) * c
        y0 = 150 + (300 - 150) * c
        destinoY, crecer = (300, 1.1) if d["pausado"] else (90, 0.75)
        x = x0 + (960 - x0) * llegar
        y = y0 + (destinoY - y0) * llegar
        escala = 1.0 + crecer * llegar
        if d["sube"]:
            contorno, frase = (130, 25, 30), "¡Te azaraste!"
        else:
            contorno, frase = (25, 95, 90), "Mejor no azararse"

        termometro = pygame.transform.smoothscale_by(self.armarTermometro(), escala)
        caja = termometro.get_rect(midtop=(int(x), int(y)))
        surface.blit(termometro, caja)

        inicio = d["inicio"]
        if t >= inicio and llegar > 0.0:
            aparece = min(1.0, (t - inicio) / 0.25)
            golpe = 1.0 + 0.4 * (1.0 - aparece) ** 2
            clave = ("destaque", frase)
            if clave not in self.globosHechos:
                self.globosHechos[clave] = self.textoBorde(self.fuentePregunta, frase, (255, 248, 236), contorno, 5)
            letrero = pygame.transform.smoothscale_by(self.globosHechos[clave], golpe * (0.8 + 0.2 * llegar))
            letrero.set_alpha(int(255 * min(aparece, llegar)))
            surface.blit(letrero, letrero.get_rect(midtop=(caja.centerx, caja.bottom + 6)))

    def dibujarHud(self, surface: pygame.Surface) -> None:
        cuaderno = self.cuaderno
        caja = cuaderno.get_rect(topright=(self.screen_w - 14, 8))
        surface.blit(cuaderno, caja)
        lapiz = (78, 62, 72)
        for cuantos, alto in ((self.arepasListas, 0.34), (self.patillazosServidos, 0.63)):
            numero = self.fuenteCuaderno.render(str(cuantos), True, lapiz)
            surface.blit(numero, numero.get_rect(center=(caja.x + int(caja.w * 0.48), caja.y + int(caja.h * alto))))
        for i in range(self.maxFallos):
            icono = self.iconoQuemadaChica if i < self.fallos else self.iconoArepaChica
            surface.blit(icono, icono.get_rect(center=(caja.x + int(caja.w * (0.15 + i * 0.125)), caja.y + int(caja.h * 0.84))))

    def dibujarMensajes(self, surface: pygame.Surface) -> None:
        for m in self.mensajes:
            subida = (1.4 - m["vida"]) * 40
            texto = self.textoBorde(self.fuenteMensaje, m["texto"], (255, 248, 236), (92, 46, 118))
            texto.set_alpha(int(255 * min(1.0, m["vida"] / 0.4)))
            surface.blit(texto, texto.get_rect(center=(int(m["x"]), int(m["y"] - subida))))

    def dibujarExplosion(self, surface: pygame.Surface) -> None:
        t = self.tiempoSecuencia
        if t < 0.8:
            return
        oscuro = min(1.0, (t - 0.8) / 0.5)
        tono = int(255 - 150 * oscuro)
        surface.fill((tono, tono, tono), special_flags=pygame.BLEND_RGB_MULT)

        avance = 1.0 - (1.0 - min(1.0, (t - 0.8) / 0.6)) ** 3
        (x0, y0), escala0 = self.lugarCelular()
        escala = escala0 + (1.1 - escala0) * avance
        ancho = int(self.cajaCelular.w * escala)
        alto = int(self.cajaCelular.h * escala)
        centro = (int(x0 + (960 - x0) * avance), int(y0 + (540 - y0) * avance))
        marco = pygame.transform.smoothscale(self.marcoCelular, (ancho, alto))
        caja = marco.get_rect(center=centro)
        pantalla = pygame.Rect(caja.x + int(ancho * 0.075), caja.y + int(alto * 0.035), int(ancho * 0.85), int(alto * 0.93))
        pygame.draw.rect(surface, (252, 240, 222), pantalla, border_radius=34)
        surface.blit(marco, caja)

        if avance >= 0.99:
            arriba = pantalla.top + 70
            for linea in ("Tu pelea ya es viral:", "«Cocinero explota", "en vivo»"):
                texto = self.fuenteCelular.render(linea, True, (90, 64, 52))
                surface.blit(texto, texto.get_rect(midtop=(pantalla.centerx, arriba)))
                arriba += texto.get_height()
            cuenta = min(1.0, max(0.0, (t - 1.4) / 1.2))
            vistas = self.vistasInicio + (25000 - self.vistasInicio) * cuenta
            cifra = f"{int(vistas):,}".replace(",", ".")
            numero = self.textoBorde(self.fuenteVistas, cifra, (255, 248, 236), (130, 30, 40))
            surface.blit(numero, numero.get_rect(midtop=(pantalla.centerx, arriba + 30)))
            palabra = self.fuenteCelular.render("vistas", True, (90, 64, 52))
            surface.blit(palabra, palabra.get_rect(midtop=(pantalla.centerx, arriba + 92)))
            trol = self.fuenteTrol.render(f"@ElQueMásSabe: +{self.seguidoresTrol:,} seguidores".replace(",", "."),
                                          True, (170, 40, 40))
            surface.blit(trol, trol.get_rect(midtop=(pantalla.centerx, arriba + 170)))

        quemadas = [(170, 880, -18, 1.2), (390, 990, 24, 1.0), (620, 955, -8, 0.85), (1300, 960, 15, 0.9),
                    (1540, 990, -26, 1.05), (1765, 870, 12, 1.25), (150, 170, 30, 0.9), (1770, 190, -20, 0.95)]
        for i, (x, y, giro, tam) in enumerate(quemadas):
            inicio = 1.0 + i * 0.15
            if t < inicio:
                continue
            entrada = min(1.0, (t - inicio) / 0.3)
            rebote = 1.0 + 2.7 * (entrada - 1.0) ** 3 + 1.7 * (entrada - 1.0) ** 2
            arepa = pygame.transform.rotozoom(self.arepaQuemadaEntera, giro + math.sin(t * 2.0 + i) * 4,
                                              max(0.05, tam * rebote))
            surface.blit(arepa, arepa.get_rect(center=(x, y)))
            if i % 2 == 0:
                subida = (t * 0.5 + i * 0.3) % 1.0
                humo = pygame.transform.smoothscale_by(self.nube, 0.5 + 0.5 * subida)
                humo.set_alpha(int(150 * (1.0 - subida) * entrada))
                surface.blit(humo, humo.get_rect(center=(x + 10, y - 60 - int(subida * 110))))

        for e in self.emojisVolando:
            x = e["x"] + math.sin(e["y"] / 60.0 + e["fase"]) * 20
            surface.blit(e["img"], e["img"].get_rect(center=(int(x), int(e["y"]))))

        comentarios = [("jajajajaja", -1, 300), ("Se picó, jajaja", 1, 420),
                       ("El trol ganó", -1, 560), ("¿Y las arepas qué?", 1, 700)]
        for i, (texto, lado, y) in enumerate(comentarios):
            inicio = 1.6 + i * 0.6
            if t < inicio:
                continue
            globo = self.globoHablado(texto, lado > 0)
            entrada = min(1.0, (t - inicio) / 0.25)
            globo = pygame.transform.smoothscale_by(globo, 0.6 + 0.4 * entrada)
            if lado < 0:
                surface.blit(globo, globo.get_rect(midright=(caja.left - 30, y)))
            else:
                surface.blit(globo, globo.get_rect(midleft=(caja.right + 30, y)))


if __name__ == "__main__":
    from core.engine import Engine
    motor = Engine(title="La fritanga de la Aleta")

    def jugarOtraVez(gano):
        motor.state_machine.change_state(Fritanga84Microgame(on_complete_callback=jugarOtraVez))

    jugarOtraVez(None)
    motor.run()
