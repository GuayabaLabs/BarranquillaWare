"""Utilidades aisladas: lienzo virtual, recursos y paneles del proyecto."""
from pathlib import Path
import pygame

ANCHO, ALTO, FPS = 1920, 1080, 60
RAIZ = Path(__file__).resolve().parent.parent


def fuente(tamano=28, negrita=False):
    """Usa las fuentes empaquetadas en el proyecto y una alternativa segura."""
    nombre = "ArialBold.ttf" if negrita else "Impact.ttf"
    try:
        return pygame.font.Font(str(RAIZ / "assets" / "fonts" / nombre), tamano)
    except (OSError, pygame.error):
        return pygame.font.Font(None, tamano)


def cargar_imagen(nombre, tamano=None, alpha=True, carpeta="assets"):
    """Carga solo lectura, devuelve None si falta y nunca escribe un recurso fuente."""
    candidatos = [RAIZ / carpeta / nombre]
    if carpeta == "assets":
        candidatos.insert(0, Path(__file__).resolve().parent / "assets" / nombre)
    for ruta in candidatos:
        try:
            imagen = pygame.image.load(str(ruta))
            imagen = imagen.convert_alpha() if alpha else imagen.convert()
            if tamano:
                imagen = pygame.transform.smoothscale(imagen, tamano)
            return imagen
        except (OSError, pygame.error):
            continue
    return None


def cargar_sprite(nombre, grupo):
    """Carga recortes propios; el escalado se deja al juego para que sea entero."""
    return cargar_imagen(nombre, carpeta=f"juegos_extra/assets/{grupo}")


def texto(superficie, cadena, pos, tamano=28, color=(45, 42, 55), centro=False, negrita=False):
    imagen = fuente(tamano, negrita).render(str(cadena), True, color)
    rect = imagen.get_rect(center=pos) if centro else imagen.get_rect(topleft=pos)
    superficie.blit(imagen, rect)
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
    """Menú de pausa con marco y botones ya usados por los minijuegos del proyecto."""
    velo=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA);velo.fill((20,18,32,178));pantalla.blit(velo,(0,0))
    marco=cargar_imagen("recuadro_menu_pausa.png",(760,650))
    if marco:pantalla.blit(marco,marco.get_rect(center=(960,540)))
    else:panel(pantalla,pygame.Rect(580,215,760,650))
    texto(pantalla,"PAUSA",(960,300),54,(67,49,75),True)
    nombres=("boton_continuar_menu_pausa.png","boton_reiniciar_menu_pausa.png","boton_salir_menu_pausa.png")
    rects=[];separacion=115;alto=102;ancho=440;inicio=395-(len(opciones)-2)*58
    for i,opcion in enumerate(opciones):
        r=pygame.Rect(960-ancho//2,inicio+i*separacion,ancho,alto);rects.append(r)
        ruta=nombres[min(i,len(nombres)-1)]
        img=cargar_imagen(ruta,(ancho,alto))
        if img:
            if i==seleccionado or (cursor is not None and r.collidepoint(cursor)):
                img=pygame.transform.smoothscale(img,(int(ancho*1.04),int(alto*1.04)))
            pantalla.blit(img,img.get_rect(center=r.center))
        else:boton(pantalla,r,opcion,i==seleccionado,cursor)
    return rects


def pantalla_final(pantalla,titulo,lineas,reinicio="R para reiniciar"):
    velo=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA);velo.fill((28,24,42,190));pantalla.blit(velo,(0,0))
    marco=cargar_imagen("recuadro_menu_pausa.png",(1280,840))
    if marco:pantalla.blit(marco,marco.get_rect(center=(960,540)))
    else:panel(pantalla,pygame.Rect(320,120,1280,840))
    texto(pantalla,titulo,(960,230),48,(76,51,74),True)
    for i,linea in enumerate(lineas):texto(pantalla,linea,(960,340+i*68),29,(53,48,60),True)
    texto(pantalla,reinicio,(960,880),28,(85,65,98),True)


def sonido(nombre):
    try:return pygame.mixer.Sound(str(RAIZ/"assets"/nombre))
    except (pygame.error,OSError):return None
