"""CurramGram Go: recorre la terminal y practica ciudadanía digital."""
import json
import math
import random
import pygame
from comun import ANCHO, ALTO, FPS, RAIZ, VentanaVirtual, cargar_imagen, cargar_sprite, revisar_recursos, fuente, texto, panel, leer_entrada, menu_pausa

# Ajustes del recorrido
DURACION=120.0
MUNDO=5700
ZONAS=((0,1250,"ZONA 1: ENTRADA Y CHECK-IN"),(1250,3250,"ZONA 2: TIENDAS Y COMIDA"),(3250,MUNDO,"ZONA 3: SALA DE ESPERA Y PUERTA"))
PUNTOS=(520,1530,2500,3390,4240,5030)
CASOS=[
 ("Viajero con harina","La bolsa blanca era maizena y harina de yuca.","Acércate a confirmar; no difundas una acusación."),
 ("Tamborero sospechoso","Ocultaba paquetes sellados: era contrabando real.","Esconde la cámara, espera a que mire al otro lado y entrega la prueba a Policía."),
 ("Turista con pasabordo","El código del vuelo permite acceder a datos y al viaje.","Avísale con E. Nunca publiques su boleto."),
 ("Joven en la banca","La persona estaba pasando un momento difícil.","Respeta su privacidad; sigue caminando sin apuntar."),
 ("Señora y cava","Se había derramado el hielo de las butifarras.","Comprueba antes de repetir una acusación."),
 ("Comparsa de marimondas","Los bailarines posaban en una actividad pública.","Una foto respetuosa del evento puede compartirse."),
]
NPC_SPRITES=("hombre_gorra","tamborero","turista_pasaporte","joven_llorando","senora_cava","bailarina_comparsa")

class CurramGramGo:
 def __init__(self):
  revisar_recursos("curramgram_go")
  self.sprites={}
  nombres={"titulo","barranquilla","aeropuerto","gates_1_10","hud_pildora","zona_1","zona_2","zona_3","puerta_embarque","icono_camara","reloj_grande","policia","bailarina_comparsa","trabajador_carrito","grupo_vendedor_letrero","cami","tamborero","hombre_gorra","turista_pasaporte","pasajero_sentado_1","joven_llorando","senor_sentado","senora_cava","globito_clickbait","dialogo_toma_foto","dialogo_salto","dialogo_confirma","dialogo_privacidad","dialogo_respeto","dialogo_pelea","dialogo_hielo","cartel_policia","cartel_comparsa","alerta","tecla_s_sigilo","tecla_flash","tecla_a","tecla_d","tecla_s","tecla_space","tecla_e","tecla_camara","tecla_p","gate_7","letrero_butifarras"}
  for name in nombres:self.sprites[name]=cargar_sprite(f"{name}.png","curramgram")
  try:self.anclajes=json.loads((RAIZ/"juegos_extra/assets/anclajes.json").read_text(encoding="utf-8"))["curramgram"]
  except (OSError,ValueError):self.anclajes={}
  self.fondo_proyecto=cargar_imagen("fondo_minijuego_crossy.png",(ANCHO,ALTO),alpha=False)
  self.fondo_terminal=self._construir_fondo()
  self._iniciar_audio();self.reiniciar()

 def _iniciar_audio(self):
  try:
   if not pygame.mixer.get_init():pygame.mixer.init()
   pygame.mixer.music.load(str(RAIZ/"assets"/"7am_ancpg_ost_main_menu.ogg"));pygame.mixer.music.set_volume(.16);pygame.mixer.music.play(-1,fade_ms=700)
   self.sonido_tambor=pygame.mixer.Sound(str(RAIZ/"assets"/"char_audio_1_microjuego_puño.ogg"));self.sonido_tambor.set_volume(.35)
  except (pygame.error,OSError):self.sonido_tambor=None

 def reiniciar(self):
  self.x=350.;self.tiempo=DURACION;self.puntos=0;self.likes=0;self.ocultando=False;self.salto=0.;self.amenaza=False;self.gaze_clock=1.0;self.gaze_right=True
  self.casos=[None]*6;self.foto=None;self.evidencia=False;self.aviso="Explora la terminal y protege la privacidad.";self.aviso_t=4.;self.apunte=None;self.apunte_t=0.
  self.final=None;self.victoria=False;self.pausa=False;self.sel=0;self.rects=[];self.elapsed=0.;self.loss_timer=0.
  self.carrito=None;self.carrito_clock=6.;self.jump_avoid=False;self.walk_phase=0.;self.facing=1;self.last_camera=None

 def _construir_fondo(self):
  """Terminal 2D por capas a 480x270; se escala a 1920 con vecino más cercano."""
  w,h=MUNDO//4+480,270;s=pygame.Surface((w,h));s.fill((222,204,183))
  # Techo cálido y molduras del terminal.
  pygame.draw.rect(s,(218,185,154),(0,0,w,48));pygame.draw.rect(s,(155,103,89),(0,43,w,5))
  for x in range(0,w,36):
   pygame.draw.rect(s,(239,214,185),(x+2,9,27,5));pygame.draw.line(s,(185,145,117),(x,0),(x,43),1)
  # Ventanales amplios con cielo caribeño y pista al fondo.
  pygame.draw.rect(s,(112,175,191),(0,49,w,125))
  pygame.draw.rect(s,(213,229,215),(0,52,w,17))
  for x in range(0,w,146):
   pygame.draw.rect(s,(211,232,225),(x+8,65,124,88));pygame.draw.rect(s,(62,101,118),(x+8,65,124,88),2)
   pygame.draw.rect(s,(104,160,181),(x+13,70,114,77))
   pygame.draw.rect(s,(203,219,196),(x+13,70,114,18))
   # Pista y una aeronave pequeña dentro de cada vista.
   pygame.draw.rect(s,(163,183,172),(x+13,126,114,21));pygame.draw.line(s,(241,225,172),(x+13,140),(x+127,140),1)
   ax=x+38;ay=113
   pygame.draw.rect(s,(245,244,226),(ax,ay,48,4));pygame.draw.polygon(s,(244,244,227),[(ax+14,ay),(ax+23,ay-5),(ax+29,ay),(ax+36,ay+4),(ax+17,ay+4)])
   pygame.draw.rect(s,(65,92,105),(x+130,45,5,132))
  # Pilares gruesos, macetas y palmeras.
  for wx in (1460,2240,3040,3840,4660,5440):
   x=wx//4;pygame.draw.rect(s,(187,157,131),(x-13,42,26,142));pygame.draw.rect(s,(226,205,179),(x-8,47,6,128))
   pygame.draw.rect(s,(118,137,97),(x-14,166,28,9));pygame.draw.rect(s,(149,91,72),(x-18,174,36,10))
   pygame.draw.line(s,(91,127,81),(x,166),(x-2,134),3)
   for dx,dy in ((-12,136),(9,131),(-16,147),(14,145),(0,126)):
    pygame.draw.ellipse(s,(64,132,85),(x+dx-9,dy-4,18,8))
  # Mostrador de check-in y puesto de butifarras.
  for wx,label in ((150,"POLICÍA AEROPORTUARIA"),(590,"CHECK-IN"),(1760,"BUTIFARRAS Y FRITOS")):
   x=wx//4;pygame.draw.rect(s,(116,74,59),(x,135,155,40));pygame.draw.rect(s,(215,165,104),(x-3,130,161,10));pygame.draw.rect(s,(239,213,176),(x+5,139,145,25))
  # Bancas largas de sala de espera.
  for wx in (3540,3860,4380,4730,5200):
   x=wx//4;pygame.draw.rect(s,(128,84,71),(x,152,63,8));pygame.draw.rect(s,(168,124,98),(x+3,160,5,22));pygame.draw.rect(s,(168,124,98),(x+54,160,5,22));pygame.draw.rect(s,(198,148,116),(x,143,63,9))
  # Piso de baldosa terracota clara.
  pygame.draw.rect(s,(205,184,165),(0,184,w,86));pygame.draw.line(s,(134,103,92),(0,184),(w,184),3)
  for x in range(0,w,24):pygame.draw.line(s,(184,160,142),(x,187),(x,270),1)
  for y in (207,232,257):pygame.draw.line(s,(186,163,145),(0,y),(w,y),1)
  return s

 def _mensaje(self,frase,d=3):self.aviso=frase;self.aviso_t=d
 def _camara(self):return max(0,min(MUNDO-ANCHO,self.x-ANCHO*.43))
 def cerca(self,i):return abs(self.x-PUNTOS[i])<210

 def keydown(self,k):
  if k in (pygame.K_s,pygame.K_DOWN):self.ocultando=True
  elif k==pygame.K_SPACE and self.salto<=0:self.salto=.72;self.jump_avoid=True
  elif k==pygame.K_e:self.interactuar()
  elif k==pygame.K_p:self.publicar()
 def keyup(self,k):
  if k in (pygame.K_s,pygame.K_DOWN):self.ocultando=False

 def interactuar(self):
  # Evidencia del delito se entrega primero a la Policía de la Zona 1.
  if self.x<340 and self.evidencia:
   self.casos[1]="Prueba discreta entregada a Policía";self.puntos+=60;self.evidencia=False;self._mensaje("+60 pts: evidencia verificada y entregada a Policía")
   return
  for i in range(6):
   if not self.cerca(i):continue
   if i==0 and self.casos[i] is None:
    self.casos[i]="Confirmó que era harina y no acusó";self.puntos+=30;self._mensaje("+30 pts: ¡No caíste en la falsa acusación!")
   elif i==1:
    self._mensaje("S: escóndete; espera a que mire al otro lado y toma la foto.")
   elif i==2 and self.casos[i] is None:
    self.casos[i]="Avisó a la turista del código visible";self.puntos+=45;self._mensaje("+45 pts: ¡Guarda el tiquete que se ve el código!")
   elif i==3 and self.casos[i] is None:
    self.casos[i]="Pasó de largo y respetó su intimidad";self.puntos+=20;self._mensaje("+20 pts: respetaste un momento vulnerable")
   elif i==4 and self.casos[i] is None:
    self.casos[i]="Comprobó que solo se derramó el hielo";self.puntos+=30;self._mensaje("+30 pts: era hielo de las butifarras, no una pelea")
   elif i==5:
    self._mensaje("La comparsa posa para el evento público. Clic y P para compartir.")
   return
  self._mensaje("Acércate a una situación o al puesto de Policía para interactuar.")

 def publicar(self):
  if self.foto is None:self._mensaje("No tienes una foto encuadrada.");return
  i=self.foto;dist=self.last_camera[1] if self.last_camera else 9999
  if i==5:
   self.casos[i]="Publicó una foto respetuosa de la comparsa";self.puntos+=35;self.likes+=120;self._mensaje("+35 pts: publicación pública y respetuosa")
  elif i==0:
   self.puntos=max(0,self.puntos-20);self.likes+=500;self._mensaje("−20 pts: publicaste una acusación sin verificar")
  elif i==1:
   if self.evidencia:self._mensaje("No publiques la prueba: llévala en privado a Policía.")
   else:self._mensaje("No hay prueba válida que entregar a Policía.")
  elif i==2:
   self.puntos=max(0,self.puntos-35);self.likes+=500;self._mensaje("−35 pts: publicaste el pasabordo con datos privados")
  elif i==3:
   self.puntos=max(0,self.puntos-25);self.likes+=500;self._mensaje("−25 pts: publicaste un momento vulnerable")
  elif i==4:
   self.puntos=max(0,self.puntos-20);self.likes+=500;self._mensaje("−20 pts: compartiste morbo antes de verificar")
  self.foto=None;self.last_camera=None

 def _capturar_foto(self,mouse):
  mx,my=mouse;world_x=self._camara()+mx
  candidatos=[i for i,p in enumerate(PUNTOS) if abs(world_x-p)<175 and 390<my<820]
  if not candidatos:self._mensaje("Apunta el visor a una de las situaciones.");return
  i=min(candidatos,key=lambda n:abs(world_x-PUNTOS[n]));dist=abs(self.x-PUNTOS[i]);self.foto=i;self.last_camera=(i,dist)
  if i in (2,3) and dist<240 and self.apunte_t>=1:
   self.tiempo=max(0,self.tiempo-10);self.puntos=max(0,self.puntos-10);self.casos[i]="Tomó foto de una persona vulnerable: invasión de privacidad";self.foto=None;self._mensaje("Privacidad: la persona se molestó. −10 s y −10 ciudadanía.");return
  if i==1:
   if not self.ocultando or self.amenaza:
    self.tiempo=max(0,self.tiempo-8);self.x=max(0,self.x-110);self.casos[1]="Te vio grabando; el sospechoso escapó";self.final="MISIÓN FALLIDA: SOSPECHOSO ESCAPÓ";self.victoria=False;self._mensaje("¡Eche, qué grabas! Te empujó y escapó.");return
   self.evidencia=True;self._mensaje("Foto sigilosa lista. Regresa a Zona 1 y usa E con Policía.")
  elif dist>240:
   self._mensaje("¿NARCO EN EL CORTISSOZ? · +500 likes (titular engañoso)")
  elif i==2:self._mensaje("Privacidad: el código del boleto queda visible. Avísale con E.")
  elif i==4:self._mensaje("Realidad: el hielo de sus butifarras se derramó.")
  elif i==0:self._mensaje("Realidad: es maizena y harina de yuca; no es delito.")
  elif i==3:self._mensaje("No publiques: la persona está pasando un mal momento.")
  elif i==5:self._mensaje("La comparsa posa en un evento público.")

 def update(self,dt,keys,mouse):
  if self.pausa or self.final:return
  dt=min(dt,.05);self.elapsed+=dt
  if self.loss_timer>0:self.loss_timer=max(0,self.loss_timer-dt)
  else:self.tiempo=max(0,self.tiempo-dt)
  self.salto=max(0,self.salto-dt);self.aviso_t=max(0,self.aviso_t-dt);self.walk_phase+=dt*10
  left=keys[pygame.K_a] or keys[pygame.K_LEFT];right=keys[pygame.K_d] or keys[pygame.K_RIGHT]
  if left!=right:
   direction=-1 if left else 1;self.facing=direction;self.x=max(0,min(MUNDO-100,self.x+direction*350*dt))
  self.gaze_clock-=dt
  if self.gaze_clock<=0:self.gaze_right=not self.gaze_right;self.gaze_clock=random.uniform(2.2,3.8)
  self.amenaza=self.gaze_clock<.65
  # La alerta de privacidad se activa tras mantener el visor sobre una persona vulnerable.
  world_mouse=self._camara()+mouse[0]
  apuntado=next((i for i in (2,3) if abs(world_mouse-PUNTOS[i])<90 and 430<mouse[1]<840),None)
  if apuntado is not None:
   if self.apunte==apuntado:self.apunte_t+=dt
   else:self.apunte=apuntado;self.apunte_t=dt
  else:self.apunte=None;self.apunte_t=0
  # El respeto se registra al pasar junto a la persona sin apuntarle la cámara.
  if self.casos[3] is None and self.apunte!=3 and abs(self.x-PUNTOS[3])<90:
   self.casos[3]="Pasó de largo y respetó su intimidad";self.puntos+=20;self._mensaje("+20 pts: respetaste un momento vulnerable")
  # El carrito cruza de verdad el pasillo; ocultarse o saltar evita perder tiempo.
  self.carrito_clock-=dt
  if self.carrito is None and self.carrito_clock<=0:
   self.carrito={"x":self.x+520,"hit":False};self.carrito_clock=random.uniform(10,14);self.jump_avoid=False
  if self.carrito:
   self.carrito["x"]-=570*dt
   if not self.carrito["hit"] and abs(self.carrito["x"]-self.x)<100:
    self.carrito["hit"]=True
    if self.salto>0 or self.ocultando:self._mensaje("Evitaste el carrito de maletas.")
    else:self.tiempo=max(0,self.tiempo-5);self.loss_timer=.5;self._mensaje("¡Carrito! Perdiste 5 s; salta o escóndete.")
   if self.carrito["x"]<self.x-180:self.carrito=None
  if self.x>=MUNDO-125:self.final="LLEGASTE A GATE 7";self.victoria=True
  if self.tiempo<=0:self.final="VUELO PERDIDO";self.victoria=False

 def _escala_entera(self,img,factor=2):
  if img is None:return None
  return pygame.transform.scale(img,(img.get_width()*factor,img.get_height()*factor))

 def _sprite_en(self,s,nombre,screen_x,base_y,factor=2,flip=False,bob=0):
  img=self.sprites.get(nombre)
  if img is None:return
  if factor!=1:img=self._escala_entera(img,factor)
  if flip:img=pygame.transform.flip(img,True,False)
  anchor=self.anclajes.get(nombre,{}).get("anchor",[img.get_width()//(2*factor),img.get_height()//factor])
  ax,ay=int(anchor[0]*factor),int(anchor[1]*factor)
  s.blit(img,(int(screen_x-ax),int(base_y-ay+bob)))

 def _dibujar_fondo(self,s):
  low=pygame.Surface((480,270));cam=self._camara()/4
  low.blit(self.fondo_terminal,(0,0),(int(cam),0,480,270))
  # Cielo, nubes y avión lejano en una capa con paralaje lento.
  parallax=(int(cam*.18)%480)
  for cloud_x in (55,235,405):
   cx=(cloud_x-parallax)%480
   pygame.draw.ellipse(low,(235,239,222),(cx,55,30,5));pygame.draw.ellipse(low,(235,239,222),(cx+14,51,27,8))
  pygame.draw.rect(s,(246,232,211),(0,0,ANCHO,ALTO))
  s.blit(pygame.transform.scale(low,(ANCHO,ALTO)),(0,0))
  # Sombra ligera de piso para integrar las siluetas pixel art.
  pygame.draw.rect(s,(94,66,58),(0,744,ANCHO,7))

 def _draw_zonas(self,s):
  # Las tres zonas permanecen como carteles fijos para dar orientación sin tapar la escena.
  for name,x in (("zona_1",60),("zona_2",610),("zona_3",1190)):
   img=self._escala_entera(self.sprites.get(name),2)
   if img:s.blit(img,(x,190))
  police_x=int(180-self._camara())
  if 90<police_x<ANCHO-90:self._blit_escalado(s,"cartel_policia",(max(42,police_x-78),385),2)

 def _blit_escalado(self,s,nombre,pos,factor=2):
  img=self._escala_entera(self.sprites.get(nombre),factor)
  if img:s.blit(img,pos)

 def _draw_prop_personajes(self,s):
  cam=self._camara();ground=764
  # Policía aeroportuaria de turno.
  self._sprite_en(s,"policia",180-cam,ground,2,bob=int(math.sin(self.elapsed*1.8)*2))
  # Puesto con vendedor/letrero como grupo manual porque la hoja los superpone.
  self._sprite_en(s,"grupo_vendedor_letrero",1940-cam,ground,2)
  # Seis situaciones representadas con los sprites reales de la hoja.
  for i,(x,nombre) in enumerate(zip(PUNTOS,NPC_SPRITES)):
   sx=x-cam
   if not -230<sx<ANCHO+230:continue
   bob=0
   if i==5:bob=int(math.sin(self.elapsed*5)*7)
   elif i in (2,3,4):bob=int(math.sin(self.elapsed*1.4+i)*2)
   flip=(i==1 and not self.gaze_right) or (i==0 and self.facing<0)
   # Sombras elípticas sostienen los anclajes a pie.
   sw=145 if i in (1,5) else 118
   pygame.draw.ellipse(s,(89,73,64),(int(sx-sw//2),ground-5,sw,18))
   self._sprite_en(s,nombre,sx,ground+bob,2,flip=flip)
   if i==0:
    # Bolsa sencilla de papel: no existe objeto equivalente en las hojas.
    bag=pygame.Rect(int(sx+50),ground-105,34,38);pygame.draw.rect(s,(249,239,215),bag);pygame.draw.rect(s,(116,84,69),bag,3);pygame.draw.line(s,(175,135,97),bag.topleft,(bag.centerx,bag.top+8),3)
    for j in range(2):pygame.draw.circle(s,(80,181,203),(int(sx+18+j*12),ground-300-j*11),4)
   if i==5:
    self._blit_escalado(s,"cartel_comparsa",(int(sx-96),ground-380),1)
   if i==1:
    # Indicador de mirada ? → !, y ojos en la dirección actual.
    alert=self.sprites.get("alerta");self._blit_escalado(s,"alerta",(int(sx-75),400),1)
    pygame.draw.circle(s,(231,74,59) if self.amenaza else (229,180,58),(int(sx),415),15)
    texto(s,"!" if self.amenaza else "?",(int(sx),415),19,(255,255,255),True)
  # Una pequeña comparsa recibe a los viajeros al inicio de la terminal.
  for k,wx in enumerate((860,960,1060)):
   sx=wx-cam
   if -100<sx<ANCHO+100:
    pygame.draw.ellipse(s,(89,73,64),(int(sx-45),ground-4,90,14))
    self._sprite_en(s,"bailarina_comparsa",sx,ground+int(math.sin(self.elapsed*5+k)*5),2,flip=bool(k%2))
  # Pasajeros de sala de espera y comparsa adicional como personajes de fondo.
  for wx,name in ((3800,"pasajero_sentado_1"),(4480,"senor_sentado")):
   sx=wx-cam
   if 80<sx<ANCHO-80:self._sprite_en(s,name,sx,ground-2,2,bob=int(math.sin(self.elapsed*1.2+wx)*2))
  # Vendedor/puesto de comida en zona 2 se marca con su cartel recortado.
  self._blit_escalado(s,"letrero_butifarras",(int(1820-cam),485),2)

 def _draw_player(self,s):
  sx=self.x-self._camara();ground=764
  jump_y=0
  if self.salto>0:jump_y=int(178*math.sin(math.pi*(.72-self.salto)/.72))
  bob=0 if self.ocultando or self.salto>0 else int(abs(math.sin(self.walk_phase))*5) if self.facing else 0
  # La sombra permanece en el piso durante el salto.
  pygame.draw.ellipse(s,(96,76,66),(int(sx-70),ground-3,140,18))
  img=self.sprites.get("cami")
  if img:
   factor=2;scaled=self._escala_entera(img,factor)
   if self.facing<0:scaled=pygame.transform.flip(scaled,True,False)
   if self.ocultando:scaled=pygame.transform.scale(scaled,(scaled.get_width(),int(scaled.get_height()*.68)))
   anchor=self.anclajes.get("cami",{}).get("anchor",[img.get_width()//2,img.get_height()])
   ax=int(anchor[0]*factor);ay=int(anchor[1]*factor)
   if self.ocultando:ay=int(ay*.68)
   s.blit(scaled,(int(sx-ax),int(ground-ay-jump_y+bob)))
  if self.ocultando:
   # Señal de sigilo, no sustituye el arte del personaje.
   panel(s,pygame.Rect(int(sx-64),ground-335,128,40),(229,246,217),(70,127,84),8,2);texto(s,"SIGILO",(int(sx),ground-315),19,(50,108,68),True)

 def _draw_carrito(self,s):
  if not self.carrito:return
  sx=self.carrito["x"]-self._camara()
  if -190<sx<ANCHO+190:self._sprite_en(s,"trabajador_carrito",sx,764,2,flip=True)

 def _draw_camera(self,s,mouse):
  mx,my=mouse;pygame.draw.rect(s,(246,249,232),(mx-46,my-38,92,76),4);pygame.draw.line(s,(246,249,232),(mx-58,my),(mx+58,my),3);pygame.draw.line(s,(246,249,232),(mx,my-51),(mx,my+51),3)
  pygame.draw.circle(s,(240,248,222),(mx,my),7,2)
  if self.apunte_t>=1:
   panel(s,pygame.Rect(mx-125,my-75,250,46),(255,218,218),(178,44,54),8,3);texto(s,"PRIVACIDAD",(mx,my-52),20,(151,31,44),True)
  if self.foto is not None:
   panel(s,pygame.Rect(ANCHO-300,205,260,54),(239,247,226),(77,113,80),10,2);texto(s,"FOTO LISTA · P",(ANCHO-170,232),20,(55,88,63),True)

 def _draw_hud(self,s):
  # Paneles, nombre de ciudad, aeropuerto y gates de la hoja.
  self._blit_escalado(s,"titulo",(40,24),2)
  self._blit_escalado(s,"barranquilla",(640,24),2);self._blit_escalado(s,"aeropuerto",(930,20),2);self._blit_escalado(s,"gates_1_10",(1412,27),2)
  # Píldora original con el reloj/ciudadanía dinámicos encima.
  pill=self._escala_entera(self.sprites.get("hud_pildora"),2)
  if pill:
   # El sprite contiene un ejemplo impreso; cubre solo el interior, no el marco del HUD.
   pygame.draw.rect(pill,(255,247,228),(22,12,pill.get_width()-44,pill.get_height()-24))
   s.blit(pill,(623,112))
  texto(s,f"{int(self.tiempo//60)}:{int(self.tiempo%60):02} / 2:00   ·   CIUDADANÍA: {self.puntos} PTS",(960,147),25,(63,52,57),True)
  self._blit_escalado(s,"puerta_embarque",(ANCHO-40-154,182),2)
  self._draw_zonas(s)
  # Reloj inferior y cámara, dentro del margen seguro.
  self._blit_escalado(s,"icono_camara",(48,730),2)
  reloj=self._escala_entera(self.sprites.get("reloj_grande"),2)
  if reloj:
   pygame.draw.rect(reloj,(255,218,113),(47,29,151,55))
   s.blit(reloj,(40,812))
  texto(s,f"{int(self.tiempo//60)}:{int(self.tiempo%60):02}",(163,869),44,(100,49,44),True)
  # Barra inferior fija: teclas reales y etiquetas textuales, sin tecla F.
  pygame.draw.rect(s,(52,43,51),(40,958,ANCHO-80,82),border_radius=17);pygame.draw.rect(s,(181,142,111),(40,958,ANCHO-80,82),3,border_radius=17)
  grupos=[("tecla_a", "A / D  CAMINAR"),("tecla_s","S / ↓  SIGILO"),("tecla_space","ESPACIO  SALTAR"),("tecla_e","E  INTERACTUAR"),("tecla_camara","MOUSE + CLIC  FOTO"),("tecla_p","P  PUBLICAR")]
  centros=(390,625,880,1123,1378,1615)
  for (key,label),cx in zip(grupos,centros):
   factor=1 if key=="tecla_space" else 1
   img=self._escala_entera(self.sprites.get(key),factor)
   if img:s.blit(img,img.get_rect(center=(cx,990)))
   texto(s,label,(cx,1026),18,(255,246,228),True)
  # Gate de la barra inferior.
  self._blit_escalado(s,"gate_7",(ANCHO-40-60,955),1)
  if self.evidencia:
   panel(s,pygame.Rect(42,744,280,42),(236,246,222),(62,119,79),9,2);texto(s,"PRUEBA SEGURA · LLEVAR A POLICÍA",(182,765),15,(49,98,61),True)

 def _draw_notificacion(self,s):
  if self.aviso_t<=0:return
  r=pygame.Rect(ANCHO//2-470,836,940,70);panel(s,r,(255,247,229),(105,75,76),14,3)
  texto(s,self.aviso,(ANCHO//2,871),24,(69,51,57),True)

 def _draw_final(self,s):
  velo=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA);velo.fill((28,24,42,208));s.blit(velo,(0,0))
  marco=cargar_imagen("recuadro_menu_pausa.png",(1660,960))
  if marco:s.blit(marco,marco.get_rect(center=(960,540)))
  else:panel(s,pygame.Rect(130,60,1660,960))
  texto(s,"TU PERFIL DE CURRAMGRAM · REPORTE DEL VUELO",(960,116),42,(77,51,73),True)
  texto(s,f"{self.final}  ·  CIUDADANÍA DIGITAL {self.puntos} PTS  ·  LIKES {self.likes}",(960,180),26,(58,54,62),True)
  for i,(nombre,real,aprendizaje) in enumerate(CASOS):
   col=i%2;fila=i//2;x=165+col*805;y=230+fila*186;rect=pygame.Rect(x,y,770,164)
   panel(s,rect,(255,251,240),(137,106,94),13,2)
   texto(s,f"{i+1}. {nombre}",(x+18,y+14),23,(100,56,49))
   decision=self.casos[i] or "Sin resolver durante este vuelo."
   texto(s,decision,(x+18,y+51),18,(53,61,62))
   texto(s,aprendizaje,(x+18,y+89),17,(89,73,72))
  texto(s,"VERIFICA ANTES DE PUBLICAR · PROTEGE LOS DATOS · RESPETA LOS MOMENTOS VULNERABLES",(960,842),21,(69,57,72),True)
  texto(s,"R PARA REINICIAR",(960,916),25,(95,75,109),True)

 def draw(self,s,mouse=(960,540)):
  self._dibujar_fondo(s);self._draw_prop_personajes(s);self._draw_carrito(s);self._draw_player(s)
  self._draw_hud(s);self._draw_camera(s,mouse);self._draw_notificacion(s)
  if self.pausa:self.rects=menu_pausa(s,["Continuar","Reiniciar","Salir"],self.sel,cursor=mouse)
  if self.final:self._draw_final(s)

 def run(self):
  ventana=VentanaVirtual("CurramGram Go! · Cortissoz");clock=pygame.time.Clock();running=True
  while running:
   dt=min(clock.tick(FPS)/1000,.05);eventos=pygame.event.get();a=leer_entrada(eventos,ventana)
   for e in eventos:ventana.manejar_evento(e)
   if a["salir"]:break
   for tecla in a["teclas"]:
    if not self.pausa and not self.final:self.keydown(tecla)
   for tecla in a["soltadas"]:self.keyup(tecla)
   if a["click"] and not self.pausa and not self.final:self._capturar_foto(a["click"])
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
     for i,r in enumerate(self.rects):
      if r.collidepoint(a["click"]):
       if i==0:self.pausa=False
       elif i==1:self.reiniciar()
       else:running=False
   else:self.update(dt,a["held"],a["mouse"])
   self.draw(ventana.canvas,a["mouse"]);ventana.presentar((239,221,201))
  pygame.quit()

if __name__=="__main__":CurramGramGo().run()
