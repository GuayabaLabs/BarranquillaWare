"""CurramGram Go: una aventura de ciudadanía digital en el Cortissoz."""
import math
import pygame
from comun import ANCHO, ALTO, FPS, cargar_imagen, texto, panel, leer_entrada, menu_pausa, pantalla_final

DURACION=120.0
MUNDO=5700
CASOS=[
 ("Viajero con harina","La bolsa parece sospechosa desde lejos; era maizena y harina de yuca.","Acércate con E y no difundas la acusación."),
 ("Tamborero sospechoso","Los paquetes ocultos sí eran contrabando. Una foto discreta puede ayudar.","Escóndete con S, fotografía sin ser visto y entrega la prueba a Policía."),
 ("Turista y pasabordo","El código del tiquete contiene datos que permiten acceder al viaje.","Avísale con E. No publiques ni fotografíes su boleto."),
 ("Joven en la banca","Una persona triste merece privacidad y consideración.","Pasa de largo; no apuntes ni publiques."),
 ("Señora y cava","El hielo de sus butifarras se derramó; no era una pelea.","Investiga de cerca con E y no conviertas el momento en morbo."),
 ("Comparsa de marimondas","Bailarines felices posan en una actividad pública.","Una foto respetuosa y su publicación son apropiadas.")]
# Coordenadas del mundo para cada escena y las tres zonas
PUNTOS=[500,1500,2460,3350,4200,5000]

class CurramGramGo:
 def __init__(self):self.reiniciar()
 def reiniciar(self):
  self.x=120.;self.tiempo=DURACION;self.puntos=0;self.likes=0;self.ocultando=False;self.salto=0.;self.alerta=0.;self.amenaza=False
  self.casos=[None]*6;self.foto=None;self.aviso="Explora la terminal y cuida la privacidad.";self.aviso_t=4.;self.apunte=None;self.apunte_t=0.;self.final=None;self.pausa=False;self.sel=0;self.caminar=True;self.obst_t=8.;self.perdida=0.;self.fondo=cargar_imagen("fondo_minijuego_crossy.png",(ANCHO,ALTO),False);self.player=cargar_imagen("westcol_chibi.png",(100,100))
 def mensaje(self,t,d=3):self.aviso=t;self.aviso_t=d
 def cerca(self,i):return abs(self.x-PUNTOS[i])<200
 def keydown(self,k):
  if k==pygame.K_s or k==pygame.K_DOWN:self.ocultando=True
  if k==pygame.K_SPACE and self.salto<=0:self.salto=.72
  if k==pygame.K_e:self.interactuar()
  if k==pygame.K_p:self.publicar()
 def keyup(self,k):
  if k==pygame.K_s or k==pygame.K_DOWN:self.ocultando=False
 def interactuar(self):
  for i in range(6):
   if self.cerca(i):
    if i==0:
     self.casos[i]="Correcto: no acusó al viajero";self.puntos+=30;self.mensaje("+30 pts: ¡No caíste en la falsa acusación!")
    elif i==1:
     if self.foto==1 and self.ocultando and not self.amenaza:
      self.casos[i]="Prueba entregada al policía";self.puntos+=60;self.mensaje("+60 pts: prueba segura entregada a Policía")
     else:self.mensaje("Policía: trae una foto discreta del tamborero escondido.")
    elif i==2:
     self.casos[i]="Avisó a la turista sobre el código";self.puntos+=45;self.mensaje("+45 pts: ¡Guarda el tiquete que se ve el código!")
    elif i==3:
     self.casos[i]="Respetó la privacidad";self.puntos+=20;self.mensaje("+20 pts: respetaste un momento vulnerable")
    elif i==4:
     self.casos[i]="Investigó: solo se derramó el hielo";self.puntos+=30;self.mensaje("+30 pts: era hielo de las butifarras, no pelea")
    elif i==5:
     self.casos[i]="Conversó con la comparsa";self.puntos+=15;self.mensaje("La comparsa te invita a una foto del evento")
    return
  if self.x<220:self.mensaje("Policía aeroportuaria: E para entregar evidencia del caso.")
  else:self.mensaje("Acércate a una situación para interactuar con E.")
 def publicar(self):
  if self.foto is None:self.mensaje("Aún no tienes una foto encuadrada.");return
  i=self.foto
  if i==1 and self.casos[i] is None:
   if self.ocultando and not self.amenaza:self.mensaje("Foto discreta lista. Vuelve a Zona 1 y entrégala con E.")
   else:self.revelar(i)
   return
  elif i==5:
   self.casos[i]="Foto pública respetuosa publicada";self.puntos+=35;self.likes+=120;self.mensaje("+35 pts: publicación pública y respetuosa")
  elif i==0:self.penal("Publicaste una acusación falsa",20)
  elif i==2:self.penal("Publicaste el pasabordo: datos privados expuestos",35)
  elif i==3:self.penal("Publicaste el momento vulnerable",25)
  elif i==4:self.penal("Publicaste un chisme sin verificar",20)
  self.foto=None
 def penal(self,txt,p):self.puntos=max(0,self.puntos-p);self.likes+=500;self.mensaje(f"- {p} pts: {txt}")
 def revelar(self,i):
  if abs(self.x-PUNTOS[i])>240:self.mensaje("De lejos solo ves un titular engañoso. Acércate para comprobar.");return
  if i==0:self.mensaje("Realidad: está empacando harina y maizena. No es delito.")
  elif i==1:self.mensaje("¡Eche, qué grabas! Escondido (S), espera su mirada y toma foto.")
  elif i==2:self.mensaje("Privacidad: se ve el código del pasabordo. Avísale con E.")
  elif i==3:self.mensaje("No apuntes: la persona está pasando un mal momento.")
  elif i==4:self.mensaje("Realidad: se derramó el hielo de sus butifarras.")
  elif i==5:self.mensaje("La comparsa posa feliz para el evento público.")
 def tomar_foto(self):
  # Apunta con retícula del mouse; sólo activa dentro del cuadro de cámara central.
  mx,my=pygame.mouse.get_pos(); world_x=self.x+(mx-ANCHO/2)
  i=min(range(6),key=lambda n:abs(world_x-PUNTOS[n]))
  if abs(world_x-PUNTOS[i])>190:self.mensaje("Apunta el cuadro a una situación.");return
  if i in (2,3) and abs(self.x-PUNTOS[i])<250:
   if self.apunte!=i:self.apunte=i;self.apunte_t=0
   if self.apunte_t>=1.0:
    self.tiempo=max(0,self.tiempo-10);self.penal("Fotografiaste a una persona vulnerable: perdió 10 s",10);self.casos[i]="Invadió privacidad: foto tomada";self.apunte=None;self.apunte_t=0;return
  self.foto=i
  distancia=abs(self.x-PUNTOS[i])
  if i==1:
   if not self.ocultando or self.amenaza:
    self.revelar(i);self.amenaza=True;self.tiempo=max(0,self.tiempo-8);self.x=max(0,self.x-110);self.casos[i]="Te vio tomando la foto y escapó";self.final="MISIÓN FALLIDA: SOSPECHOSO ESCAPÓ";self.ganador=False;self.mensaje("¡Eche, qué grabas! Te empujó; el sospechoso escapó.")
   else:self.mensaje("Foto sigilosa tomada. Corre a Zona 1 y avisa a Policía.")
  elif i==2 and distancia<220:self.mensaje("Privacidad: el código del boleto queda visible. Usa E para avisar.")
  else:self.revelar(i)
 def update(self,dt,keys):
  if self.pausa or self.final:return
  if self.perdida>0:self.perdida=max(0,self.perdida-dt)
  else:self.tiempo=max(0,self.tiempo-dt)
  if self.salto>0:self.salto=max(0,self.salto-dt)
  if self.aviso_t>0:self.aviso_t-=dt
  if self.apunte_t>0:self.apunte_t-=dt
  mx,my=pygame.mouse.get_pos(); world_x=self.x+(mx-ANCHO/2)
  candidato=min(range(6),key=lambda n:abs(world_x-PUNTOS[n]))
  if candidato in (2,3) and abs(world_x-PUNTOS[candidato])<150:
   if self.apunte==candidato:self.apunte_t+=dt
   else:self.apunte=candidato;self.apunte_t=dt
  else:self.apunte=None;self.apunte_t=0
  # Ojos del sospechoso cambian periódicamente.
  self.alerta=(self.alerta+dt)%5.5;self.amenaza=self.alerta>4.15
  if self.obst_t>0:self.obst_t-=dt
  if self.obst_t<=0:self.obst_t=10.;self.perdida=5.;self.mensaje("¡Carrito de maletas! Salta con ESPACIO o escóndete con S.")
  if self.perdida>0 and (self.salto>0 or self.ocultando):self.perdida=0;self.mensaje("Evitaste el carrito.")
  vel=340
  if keys[pygame.K_a] or keys[pygame.K_LEFT]:self.x=max(0,self.x-vel*dt)
  if keys[pygame.K_d] or keys[pygame.K_RIGHT]:self.x=min(MUNDO-80,self.x+vel*dt)
  if self.x>=MUNDO-110:self.final="LLEGASTE A GATE 7";self.ganador=True
  if self.tiempo<=0:self.final="VUELO PERDIDO";self.ganador=False
 def draw_persona(self,s,sx,sy,i):
  # Siluetas originales: las hojas existentes no tienen sprites de terminal reutilizables.
  colors=[(206,145,88),(125,57,48),(44,143,176),(113,83,137),(220,155,111),(66,145,112)]
  c=colors[i];pygame.draw.ellipse(s,(60,52,50),(sx-34,sy+67,68,17));pygame.draw.rect(s,c,(sx-24,sy+15,48,63),border_radius=13);pygame.draw.circle(s,(215,161,126),(sx,sy),22);pygame.draw.line(s,(40,37,43),(sx-7,sy-3),(sx-2,sy-3),3);pygame.draw.line(s,(40,37,43),(sx+4,sy-3),(sx+9,sy-3),3)
  if i==0:pygame.draw.rect(s,(244,233,206),(sx+26,sy+26,25,32),border_radius=5)
  if i==1:pygame.draw.ellipse(s,(246,231,200),(sx+22,sy+24,34,43));pygame.draw.circle(s,(81,45,33),(sx,sy-20),27,5);pygame.draw.line(s,(74,56,49),(sx,sy+72),(sx,sy+98),5)
  if i==2:pygame.draw.rect(s,(255,250,222),(sx-30,sy+20,23,33));
  if i==3:pygame.draw.line(s,(73,60,67),(sx-11,sy+7),(sx-5,sy+12),3)
  if i==4:pygame.draw.ellipse(s,(239,239,227),(sx-42,sy+51,30,34));
  if i==5:
   for j in range(3):pygame.draw.circle(s,[(215,67,65),(245,192,57),(60,146,179)][j],(sx-22+j*23,sy-28),11)
 def draw(self,s):
  if self.fondo:s.blit(self.fondo,(0,0))
  else:s.fill((215,222,213))
  # Cabecera independiente
  pygame.draw.rect(s,(245,224,205),(0,0,ANCHO,185));pygame.draw.line(s,(104,76,72),(0,185),(ANCHO,185),4)
  texto(s,"CURRAMGRAM GO!",(32,21),46,(110,57,48));texto(s,"ATERRIZANDO EN EL CORTISSOZ",(34,76),28,(68,50,48))
  panel(s,pygame.Rect(650,22,650,82),(255,248,231));texto(s,"BARRANQUILLA  ·  AEROPUERTO ERNESTO CORTISSOZ",(975,64),23,centro=True)
  texto(s,f"{int(self.tiempo//60)}:{int(self.tiempo%60):02} / 2:00   |   CIUDADANÍA: {self.puntos} PTS",(ANCHO//2,139),27,(57,54,60),True)
  # Scroll lateral y tres zonas
  cam=max(0,min(MUNDO-ANCHO,self.x-ANCHO*.43))
  pygame.draw.rect(s,(236,222,207),(0,185,ANCHO,770));pygame.draw.rect(s,(220,209,191),(0,780,ANCHO,175));pygame.draw.line(s,(139,119,100),(0,780),(ANCHO,780),5)
  for x in range(-int(cam)%170,ANCHO,170):pygame.draw.line(s,(201,190,178),(x,187),(x,780),2)
  zonas=[(0,1250,"ZONA 1: ENTRADA Y CHECK-IN"),(1250,3250,"ZONA 2: TIENDAS Y COMIDA"),(3250,MUNDO,"ZONA 3: SALA DE ESPERA Y PUERTA")]
  for a,b,t in zonas:
   xx=int(a-cam);ww=int(b-a);panel(s,pygame.Rect(xx+15,195,ww-30,44),(249,234,218));texto(s,t,(xx+ww//2,217),24,centro=True)
  # Policía, puesto de fritos, columnas/macetas, bancas
  px=int(180-cam);pygame.draw.rect(s,(170,187,195),(px-80,370,160,160),border_radius=12);texto(s,"POLICÍA",(px,400),22,centro=True);pygame.draw.circle(s,(38,75,132),(px,470),23)
  foodx=int(1810-cam);pygame.draw.rect(s,(130,74,47),(foodx-150,515,300,125),border_radius=10);pygame.draw.rect(s,(227,157,85),(foodx-160,485,320,46),border_radius=9);texto(s,"BUTIFARRAS · FRITOS",(foodx,507),20,centro=True)
  for wx in (1500,2260,2920,3800):
   sx=int(wx-cam);pygame.draw.rect(s,(188,163,139),(sx-26,285,52,440),border_radius=13);pygame.draw.rect(s,(86,137,92),(sx-30,681,60,34),border_radius=8);pygame.draw.ellipse(s,(60,139,88),(sx-40,620,80,70))
  for bx in (3540,3850,4480,4780):
   sx=int(bx-cam);pygame.draw.rect(s,(119,82,69),(sx,620,260,25),border_radius=8);pygame.draw.rect(s,(155,118,94),(sx+14,645,18,100));pygame.draw.rect(s,(155,118,94),(sx+225,645,18,100))
  labels=["¿NARCO EN EL CORTISSOZ?","¿PAQUETES OCULTOS?","¡TURISMO!","MEME VIRAL","¡PELEA!","CARNAVAL"]
  for i,p in enumerate(PUNTOS):
   sx=int(p-cam);self.draw_persona(s,sx,600 if i in (3,4) else 555,i)
   if -120<sx<ANCHO+120:
    if i==1: label="!" if self.amenaza else "?"; pygame.draw.circle(s,(220,70,55) if self.amenaza else (239,190,55),(sx,500),24);texto(s,label,(sx,500),25,(255,255,255),True)
    # Clickbait a distancia; descripción real sólo al acercarse
    lejos=abs(self.x-p)>240;cap=labels[i] if lejos else ["HARINA Y MAIZENA","PRUEBA REAL","CÓDIGO VISIBLE","PRIVACIDAD","SE DERRAMÓ EL HIELO","EVENTO PÚBLICO"][i]
    panel(s,pygame.Rect(sx-115,420,230,62),(255,249,233));texto(s,cap,(sx,451),18,(91,51,45),True)
  # Obstáculo carrito
  cartx=int((self.x+430-cam));pygame.draw.rect(s,(95,109,115),(cartx,708,116,31),border_radius=6);pygame.draw.circle(s,(43,43,46),(cartx+20,745),12);pygame.draw.circle(s,(43,43,46),(cartx+94,745),12);pygame.draw.rect(s,(180,135,94),(cartx+25,670,68,36),border_radius=4)
  # jugador independiente
  me_x=int(self.x-cam);me_y=680-int(65*(self.salto/.72)) if self.salto>0 else 680
  if self.player:s.blit(self.player,self.player.get_rect(midbottom=(me_x,me_y+15)))
  else:pygame.draw.rect(s,(62,110,168),(me_x-28,me_y-75,56,75),border_radius=14);pygame.draw.circle(s,(220,172,135),(me_x,me_y-91),22)
  if self.ocultando:pygame.draw.ellipse(s,(80,148,102,160),(me_x-46,me_y-94,92,100),4);texto(s,"SIGILO",(me_x,me_y-120),19,(36,111,69),True)
  # retícula de cámara
  mx,my=pygame.mouse.get_pos();pygame.draw.rect(s,(245,255,235),(mx-35,my-30,70,60),3);pygame.draw.line(s,(245,255,235),(mx-44,my),(mx+44,my),2);pygame.draw.line(s,(245,255,235),(mx,my-42),(mx,my+42),2)
  if self.foto is not None:panel(s,pygame.Rect(ANCHO-310,205,280,50),(244,251,229));texto(s,"FOTO LISTA · P",(ANCHO-170,230),20,centro=True)
  if self.apunte_t>=1.0:panel(s,pygame.Rect(ANCHO//2-150,220,300,58),(255,218,218),(175,43,53));texto(s,"PRIVACIDAD",(ANCHO//2,249),25,(153,34,45),True)
  # Meta visible al final
  gate=int(MUNDO-160-cam);pygame.draw.rect(s,(67,121,169),(gate,260,105,155),border_radius=12);texto(s,"GATE",(gate+52,292),22,(255,255,255),True);texto(s,"7",(gate+52,355),58,(255,255,255),True)
  # Barra inferior fija con exactamente los controles pedidos
  pygame.draw.rect(s,(48,42,53),(0,955,ANCHO,125));texto(s,"A / D o ← / → caminar     S o ↓ agacharte / esconderte     ESPACIO saltar     E interactuar     Mouse + clic tomar foto     P publicar",(ANCHO//2,985),22,(255,248,231),True)
  texto(s,"Gate 7  →",(ANCHO-140,1035),24,(255,220,140),True)
  if self.aviso_t>0:
   panel(s,pygame.Rect(ANCHO//2-510,850,1020,72),(255,245,226));texto(s,self.aviso,(ANCHO//2,886),24,(76,51,58),True)
  if self.perdida>0:panel(s,pygame.Rect(650,740,620,58),(255,226,213));texto(s,f"Carrito: {self.perdida:.0f} s perdidos",(960,768),24,(141,52,50),True)
  if self.pausa:self.rects=menu_pausa(s,["Continuar","Reiniciar","Salir"],self.sel)
  if self.final:
   velo=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA);velo.fill((28,24,42,205));s.blit(velo,(0,0))
   panel(s,pygame.Rect(120,65,1680,950),(255,247,234),(99,65,75),26,5)
   texto(s,"TU PERFIL DE CURRAMGRAM · REPORTE DEL VUELO",(960,125),42,(79,53,74),True)
   texto(s,f"{self.final}   ·   Ciudadanía Digital: {self.puntos} pts   ·   Likes: {self.likes}",(960,188),27,(65,58,67),True)
   for i,(nombre,_real,exp) in enumerate(CASOS):
    col=i%2;fila=i//2;x=165+col*810;y=245+fila*190
    tarjeta=pygame.Rect(x,y,770,164);panel(s,tarjeta,(255,253,246),(164,135,126),16,2)
    texto(s,f"{i+1}. {nombre}",(x+20,y+18),25,(106,58,50))
    decision=self.casos[i] or "Sin resolver durante este vuelo."
    texto(s,decision,(x+20,y+56),19,(52,62,62))
    texto(s,exp,(x+20,y+92),17,(90,77,74))
   texto(s,"Verifica antes de publicar · cuida los datos personales · acompaña sin convertir el dolor en contenido.",(960,850),22,(71,63,74),True)
   texto(s,"R para reiniciar",(960,930),26,(95,75,110),True)
 def run(self):
  pygame.init();s=pygame.display.set_mode((ANCHO,ALTO));pygame.display.set_caption("CurramGram Go! · Cortissoz");clock=pygame.time.Clock();running=True
  while running:
   dt=min(clock.tick(FPS)/1000,.05);events=pygame.event.get();a=leer_entrada(events)
   if a["salir"]:break
   for e in events:
    if e.type==pygame.KEYDOWN and not self.pausa and not self.final:self.keydown(e.key)
    if e.type==pygame.KEYUP:self.keyup(e.key)
    if e.type==pygame.MOUSEBUTTONDOWN and e.button==1 and not self.pausa and not self.final:self.tomar_foto()
   if self.final and pygame.K_r in a["teclas"]:self.reiniciar()
   elif pygame.K_ESCAPE in a["teclas"] and not self.final:self.pausa=not self.pausa
   elif self.pausa:
    if pygame.K_UP in a["teclas"]:self.sel=(self.sel-1)%3
    if pygame.K_DOWN in a["teclas"]:self.sel=(self.sel+1)%3
    if pygame.K_RETURN in a["teclas"]:
     if self.sel==0:self.pausa=False
     elif self.sel==1:self.reiniciar()
     else:running=False
    if a["click"]:
     for i,r in enumerate(getattr(self,"rects",[])):
      if r.collidepoint(a["click"]):
       if i==0:self.pausa=False
       elif i==1:self.reiniciar()
       else:running=False
   else:self.update(dt,pygame.key.get_pressed())
   self.draw(s);pygame.display.flip()
  pygame.quit()

if __name__=="__main__":CurramGramGo().run()

