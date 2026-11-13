"""Utilidades aisladas: lienzo virtual, recursos y paneles del proyecto."""
from pathlib import Path
from functools import lru_cache
import os
import pygame

ANCHO, ALTO, FPS = 1920, 1080, 60
RAIZ = Path(__file__).resolve().parent.parent
RAIZ_EXTRA = Path(__file__).resolve().parent
TOLERANTE = os.environ.get("JUEGOS_EXTRA_TOLERANTE") == "1"

# Catálogo central: los dos ejecutables y los tests validan los mismos recursos.
_COMUNES = (
    "assets/fonts/Impact.ttf", "assets/fonts/ArialBold.ttf",
    "assets/recuadro_menu_pausa.png", "assets/boton_continuar_menu_pausa.png",
    "assets/boton_reiniciar_menu_pausa.png", "assets/boton_salir_menu_pausa.png",
    "assets/7am_ancpg_ost_main_menu.ogg",
)
_EMOJI = (
    "assets/fondo_concentracion_microjuego.png", "assets/char_audio_0_microjuego_puño.ogg",
    "juegos_extra/assets/hojas/hoja_emoji_catch.png",
    "juegos_extra/assets/hojas/hoja_emoji_limpia.png",
    "juegos_extra/assets/emoji/_contacto_emoji.png",
)
_EMOJI_SPRITES = (
    "titulo", "tiempo", "tarjeta_mano_izq", "tarjeta_mano_der", "barra_negatividad",
    "barra_positividad", "mano_morada", "mano_azul_der", "emoji_enojado_naranja",
    "emoji_enojado_rojo", "emoji_triste", "emoji_vomito_1", "emoji_vomito_2",
    "emoji_corazon_roto", "emoji_pulgar_abajo", "emoji_sonriente", "emoji_cara_azul",
    "emoji_corazon", "emoji_pulgar_arriba", "emoji_bolsa_dinero",
)
_CURRAM = (
    "assets/fondo_minijuego_crossy.png", "assets/char_audio_1_microjuego_puño.ogg",
    "juegos_extra/assets/hojas/hoja_curramgram.png",
    "juegos_extra/assets/hojas/hoja_curramgram_limpia.png",
    "juegos_extra/assets/curramgram/_contacto_curramgram.png",
)
_CURRAM_SPRITES = (
    "titulo", "barranquilla", "aeropuerto", "gates_1_10", "hud_pildora", "zona_1",
    "zona_2", "zona_3", "puerta_embarque", "icono_camara", "reloj_grande", "policia",
    "bailarina_comparsa", "trabajador_carrito", "grupo_vendedor_letrero", "cami",
    "tamborero", "hombre_gorra", "turista_pasaporte", "pasajero_sentado_1",
    "joven_llorando", "senor_sentado", "senora_cava", "globito_clickbait",
    "dialogo_toma_foto", "dialogo_salto", "dialogo_confirma", "dialogo_privacidad",
    "dialogo_respeto", "dialogo_pelea", "dialogo_hielo", "cartel_policia",
    "cartel_comparsa", "alerta", "tecla_s_sigilo", "tecla_flash", "tecla_a", "tecla_d",
    "tecla_s", "tecla_space", "tecla_e", "tecla_camara", "tecla_p", "gate_7",
    "letrero_butifarras", "cami_idle", "cami_walk_1", "cami_walk_2", "cami_walk_3", "cami_walk_4", "cami_walk_5",
    "cami_agachar_1", "cami_agachar_2", "cami_cuclillas", "cami_arrodillada", "cami_foto_agachada", "cami_regreso",
)
ASSETS_REQUERIDOS = {
    "emoji_catch": _COMUNES + _EMOJI + tuple(f"juegos_extra/assets/emoji/{n}.png" for n in _EMOJI_SPRITES)
    + ("juegos_extra/assets/atlas_emoji.json", "juegos_extra/assets/anclajes.json"),
    "curramgram_go": _COMUNES + _CURRAM + tuple(f"juegos_extra/assets/curramgram/{n}.png" for n in _CURRAM_SPRITES)
    + ("juegos_extra/assets/atlas_curramgram.json", "juegos_extra/assets/anclajes.json",
      "juegos_extra/assets/curramgram/animaciones.json", "juegos_extra/assets/curramgram/anclajes_cami.json"),
}
_RECURSOS_VALIDOS = set()


class ErrorRecursos(RuntimeError):
    """Recurso requerido ausente o ilegible; incluye rutas probadas."""


def _ruta_recurso(ruta):
    ruta = Path(ruta)
    return ruta if ruta.is_absolute() else RAIZ / ruta


def revisar_recursos(juego, intentar_carga=True):
    """Devuelve una lista de errores del catálogo; lanza por defecto si algo falla."""
    if juego not in ASSETS_REQUERIDOS:
        raise ValueError(f"Juego sin catálogo ASSETS_REQUERIDOS: {juego}")
    if intentar_carga and juego in _RECURSOS_VALIDOS:
        return []
    errores = []
    pygame.font.init()
    if intentar_carga and not pygame.mixer.get_init():
        try:
            pygame.mixer.init()
        except pygame.error:
            # Sin dispositivo de sonido se verificará al menos que el archivo exista.
            pass
    for relativo in ASSETS_REQUERIDOS[juego]:
        ruta = _ruta_recurso(relativo)
        if not ruta.is_file():
            errores.append(f"FALTA {relativo} -> {ruta}")
            continue
        if not intentar_carga:
            continue
        try:
            if ruta.suffix.lower() == ".png":
                imagen = pygame.image.load(str(ruta))
                if imagen.get_width() <= 0 or imagen.get_height() <= 0:
                    raise pygame.error("dimensiones vacías")
            elif ruta.suffix.lower() == ".ttf":
                pygame.font.Font(str(ruta), 16)
            elif ruta.suffix.lower() in (".ogg", ".wav", ".mp3"):
                if pygame.mixer.get_init(): pygame.mixer.Sound(str(ruta))
            elif ruta.suffix.lower() == ".json":
                import json
                json.loads(ruta.read_text(encoding="utf-8-sig"))
        except (OSError, pygame.error, ValueError) as exc:
            errores.append(f"ILEGIBLE {relativo} -> {ruta}: {exc}")
    if errores and not TOLERANTE:
        raise ErrorRecursos("Recursos requeridos no disponibles:\n  - " + "\n  - ".join(errores))
    if errores:
        print("WARNING JUEGOS_EXTRA_TOLERANTE=1; recursos ausentes/ilegibles:\n  - " + "\n  - ".join(errores))
    elif intentar_carga:
        _RECURSOS_VALIDOS.add(juego)
    return errores


@lru_cache(maxsize=256)
def _cargar_imagen_cache(ruta, alpha):
    imagen = pygame.image.load(ruta)
    if pygame.display.get_surface():
        return imagen.convert_alpha() if alpha else imagen.convert()
    return imagen.copy()


def fuente(tamano=28, negrita=False):
    """Usa las fuentes empaquetadas en el proyecto y una alternativa segura."""
    nombre = "ArialBold.ttf" if negrita else "Impact.ttf"
    try:
        return pygame.font.Font(str(RAIZ / "assets" / "fonts" / nombre), tamano)
    except (OSError, pygame.error):
        return pygame.font.Font(None, tamano)


def cargar_imagen(nombre, tamano=None, alpha=True, carpeta="assets"):
    """Carga el archivo exacto; falla con ErrorRecursos salvo modo tolerante explícito."""
    ruta = _ruta_recurso(Path(carpeta) / nombre)
    try:
        if not ruta.is_file():
            raise FileNotFoundError(f"No existe el recurso: {nombre}; ruta probada: {ruta}")
        imagen = _cargar_imagen_cache(str(ruta), bool(alpha))
    except (OSError, pygame.error) as exc:
        if TOLERANTE:
            print(f"WARNING recurso de imagen omitido: {nombre}; ruta probada: {ruta}; {exc}")
            return None
        raise ErrorRecursos(f"No se pudo cargar {nombre}; ruta absoluta probada: {ruta}: {exc}") from exc
    return pygame.transform.smoothscale(imagen, tamano) if tamano else imagen


def cargar_sprite(nombre, grupo):
    """Carga un recorte requerido; los errores conservan la ruta que se intentó."""
    return cargar_imagen(nombre, carpeta=f"juegos_extra/assets/{grupo}")


def texto(superficie, cadena, pos, tamano=28, color=(45, 42, 55), centro=False, negrita=False):
    imagen = fuente(tamano, negrita).render(str(cadena), True, color)
    rect = imagen.get_rect(center=pos) if centro else imagen.get_rect(topleft=pos)
    superficie.blit(imagen, rect)
    return rect


def texto_con_contorno(superficie, cadena, pos, tamano=28, color=(255,255,255), contorno=(28,24,38), centro=False, grosor=3, negrita=False):
    """Texto legible encima de escenas con colores variables."""
    fuente_actual=fuente(tamano,negrita);imagen=fuente_actual.render(str(cadena),True,color)
    rect=imagen.get_rect(center=pos) if centro else imagen.get_rect(topleft=pos)
    for dx in range(-grosor,grosor+1):
        for dy in range(-grosor,grosor+1):
            if dx*dx+dy*dy<=grosor*grosor and (dx or dy):
                superficie.blit(fuente_actual.render(str(cadena),True,contorno),(rect.x+dx,rect.y+dy))
    superficie.blit(imagen,rect)
    return rect


def panel(superficie, rect, color=(255, 247, 234), borde=(94, 66, 73), radio=18, ancho=3):
    pygame.draw.rect(superficie, color, rect, border_radius=radio)
    pygame.draw.rect(superficie, borde, rect, ancho, border_radius=radio)


def boton(superficie, rect, etiqueta, seleccionado=False, cursor=None):
    """Dibuja botón genérico para respaldos y reporta si el cursor está encima."""
    cursor = cursor if cursor is not None else pygame.mouse.get_pos()
    hover = rect.collidepoint(cursor)
    panel(superficie, rect, (228, 222, 250) if seleccionado or hover else (255, 255, 255), (105, 79, 135), 14, 2)
    texto(superficie, etiqueta, rect.center, 30, centro=True)
    return hover


class VentanaVirtual:
    """Ventana redimensionable que muestra siempre el lienzo 1920x1080 completo."""
    def __init__(self, titulo):
        pygame.init()
        self.titulo = titulo
        self.window_size = (1280, 720)
        self.fullscreen = False
        self.window = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        pygame.display.set_caption(titulo)
        self.canvas = pygame.Surface((ANCHO, ALTO))
        self.offset = (0, 0)
        self.scale = 2/3

    def alternar_pantalla_completa(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.window_size = self.window.get_size()
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        pygame.display.set_caption(self.titulo)

    def manejar_evento(self, evento):
        if evento.type == pygame.VIDEORESIZE and not self.fullscreen:
            ancho=max(640,evento.w);alto=max(360,evento.h)
            self.window_size=(ancho,alto)
            self.window=pygame.display.set_mode(self.window_size,pygame.RESIZABLE)
        elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_F11:
            self.alternar_pantalla_completa()

    def mapear_mouse(self, pos):
        return (int((pos[0]-self.offset[0])/self.scale),int((pos[1]-self.offset[1])/self.scale))

    def presentar(self, fondo=(31, 27, 43)):
        ww,wh=self.window.get_size()
        self.scale=min(ww/ANCHO,wh/ALTO)
        dw=max(1,round(ANCHO*self.scale));dh=max(1,round(ALTO*self.scale))
        self.offset=((ww-dw)//2,(wh-dh)//2)
        self.window.fill(fondo)
        # El escalado final conserva los píxeles definidos y no recorta el lienzo.
        imagen=pygame.transform.scale(self.canvas,(dw,dh))
        self.window.blit(imagen,self.offset)
        pygame.display.flip()


def leer_entrada(eventos, ventana=None):
    """Centraliza eventos, teclas sostenidas y puntero para futuras cámaras/manos."""
    acciones={"pausa":False,"reiniciar":False,"salir":False,"click":None,"teclas":set(),"soltadas":set()}
    for evento in eventos:
        if evento.type==pygame.KEYDOWN:
            acciones["teclas"].add(evento.key)
            if evento.key==pygame.K_ESCAPE:acciones["pausa"]=True
            if evento.key==pygame.K_r:acciones["reiniciar"]=True
        elif evento.type==pygame.KEYUP:acciones["soltadas"].add(evento.key)
        elif evento.type==pygame.MOUSEBUTTONDOWN and evento.button==1:
            acciones["click"]=ventana.mapear_mouse(evento.pos) if ventana else evento.pos
        elif evento.type==pygame.QUIT:acciones["salir"]=True
    pos=pygame.mouse.get_pos()
    acciones["mouse"]=ventana.mapear_mouse(pos) if ventana else pos
    acciones["held"]=pygame.key.get_pressed()
    return acciones


def menu_pausa(pantalla, opciones, seleccionado=0, cursor=None):
    """Pausa con controles propios, legibles y clicables sobre panel opaco."""
    velo=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA);velo.fill((15,13,25,225));pantalla.blit(velo,(0,0))
    panel(pantalla,pygame.Rect(520,120,880,840),(34,29,48),(246,229,197),26,5)
    texto_con_contorno(pantalla,"PAUSA",(960,220),78,(255,250,239),centro=True,grosor=4)
    rects=[];separacion=142;alto=116;ancho=620;inicio=320
    hover_index=next((i for i in range(len(opciones)) if cursor is not None and pygame.Rect(960-ancho//2,inicio+i*separacion,ancho,alto).collidepoint(cursor)),None)
    for i,opcion in enumerate(opciones):
        r=pygame.Rect(960-ancho//2,inicio+i*separacion,ancho,alto);rects.append(r)
        active=i==(hover_index if hover_index is not None else seleccionado)
        pygame.draw.rect(pantalla,(109,78,153) if active else (59,52,73),r,border_radius=18)
        pygame.draw.rect(pantalla,(255,232,154) if active else (183,174,193),r,4,border_radius=18)
        if active:pygame.draw.polygon(pantalla,(255,255,255),[(r.x+28,r.centery-15),(r.x+28,r.centery+15),(r.x+48,r.centery)])
        texto_con_contorno(pantalla,opcion.upper(),(r.centerx+16,r.centery),48,(255,255,255),centro=True,grosor=3)
    texto_con_contorno(pantalla,"↑  ↓  ELEGIR     ENTER  CONFIRMAR     ESC  VOLVER",(960,780),30,(255,250,239),centro=True,grosor=2)
    return rects


def pantalla_final(pantalla,titulo,lineas,reinicio="R para reiniciar"):
    velo=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA);velo.fill((15,13,25,225));pantalla.blit(velo,(0,0))
    panel(pantalla,pygame.Rect(260,90,1400,900),(34,29,48),(246,229,197),26,5)
    texto_con_contorno(pantalla,titulo,(960,190),56,(255,250,239),centro=True,grosor=4)
    for i,linea in enumerate(lineas):texto_con_contorno(pantalla,linea,(960,310+i*78),34,(255,255,255),centro=True,grosor=3)
    texto_con_contorno(pantalla,reinicio,(960,885),30,(255,232,154),centro=True,grosor=2)


def sonido(nombre):
    try:return pygame.mixer.Sound(str(RAIZ/"assets"/nombre))
    except (pygame.error,OSError):return None
