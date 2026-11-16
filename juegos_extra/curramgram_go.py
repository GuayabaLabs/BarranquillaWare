"""CurramGram Go: recorre la terminal y practica ciudadanía digital."""
import json
import math
import random
import pygame
from comun import ANCHO, ALTO, FPS, RAIZ, VentanaVirtual, cargar_imagen, cargar_sprite, revisar_recursos, fuente, texto, texto_con_contorno, panel, leer_entrada, menu_pausa, pantalla_final
from animacion import Animacion

# Ajustes del recorrido
DURACION=120.0
MUNDO=6500
ALTURA_PERSONAJE_PX=175
PISO=round(ALTO*.71)
VELOCIDAD_CAMI=320.0
PUERTA_X=MUNDO-115
ZONAS=((0,1450,"ZONA 1"),(1450,3650,"ZONA 2"),(3650,MUNDO,"ZONA 3"))
PUNTOS=(520,1420,2320,3220,4120,5020)
ESTRELLAS_CURRAM=(150,250,350)
# Cada caso es un fenómeno real de redes sociales y la decisión responsable frente a él.
CASOS=[
 ("Viajero","Desinformación","Confirma antes de acusar."),
 ("Turista","Sobreexposición de datos","Protege datos privados."),
 ("Joven","Exposición sin consentimiento","Respeta su privacidad."),
 ("Señora","Noticia falsa viral","Verifica antes de publicar."),
 ("Comparsa","Contenido viral","Comparte con respeto."),
 ("Tamborero","Escrache digital","Busca evidencia y avisa a Policía."),
]
NPC_SPRITES=("hombre_gorra","turista_pasaporte","joven_llorando","senora_cava","bailarina_comparsa","tamborero")

class CurramGramGo:
 # Ajustes para cuando el juego corre dentro de BarranquillaWare (microgames/curramgram_go.py).
 CONTROLES_Y=958
 MOSTRAR_RELOJ=True
 TEXTO_REINICIO="R PARA REINICIAR"
 def __init__(self):
  revisar_recursos("curramgram_go")
  self.sprites={}
  nombres={"titulo","barranquilla","aeropuerto","gates_1_10","hud_pildora","zona_1","zona_2","zona_3","puerta_embarque","icono_camara","reloj_grande","policia","bailarina_comparsa","trabajador_carrito","grupo_vendedor_letrero","cami","tamborero","hombre_gorra","turista_pasaporte","pasajero_sentado_1","joven_llorando","senor_sentado","senora_cava","globito_clickbait","dialogo_toma_foto","dialogo_salto","dialogo_confirma","dialogo_privacidad","dialogo_respeto","dialogo_pelea","dialogo_hielo","cartel_policia","cartel_comparsa","alerta","tecla_s_sigilo","tecla_flash","tecla_a","tecla_d","tecla_s","tecla_space","tecla_e","tecla_camara","tecla_p","gate_7","letrero_butifarras"}
  for name in nombres:self.sprites[name]=cargar_sprite(f"{name}.png","curramgram")
  self.animacion=Animacion(RAIZ/"juegos_extra/assets/curramgram/animaciones.json")
  for name in self.animacion.defs:
   for frame in self.animacion.defs[name]["frames"]:
    self.sprites[frame]=cargar_sprite(f"{frame}.png","curramgram")
  try:self.anclajes=json.loads((RAIZ/"juegos_extra/assets/anclajes.json").read_text(encoding="utf-8"))["curramgram"]
  except (OSError,ValueError):self.anclajes={}
  self.anclajes.update(json.loads((RAIZ/"juegos_extra/assets/curramgram/anclajes_cami.json").read_text(encoding="utf-8")))
  self._normalizar_personajes()
  self.sprites_flip={n:pygame.transform.flip(self.sprites[n],True,False) for n in self.personajes if self.sprites.get(n)}
  self.fondo_proyecto=cargar_imagen("fondo_minijuego_crossy.png",(ANCHO,ALTO),alpha=False)
  self.fondo_terminal=self._construir_fondo()
  self._iniciar_audio();self.reiniciar()

 def _normalizar_personajes(self):
  """Preescala una vez a la altura objetivo; Cami conserva escala común por hoja."""
  self.personajes=set(NPC_SPRITES)|{"policia","bailarina_comparsa","trabajador_carrito","pasajero_sentado_1","senor_sentado"}
  frames={f for d in self.animacion.defs.values() for f in d["frames"]}
  self.personajes.update(frames)
  idle=self.sprites.get("cami_idle");factor_cami=ALTURA_PERSONAJE_PX/max(1,idle.get_height()) if idle else 1
  for nombre in self.personajes:
   img=self.sprites.get(nombre)
   if img is None:continue
   factor=factor_cami if nombre in frames else ALTURA_PERSONAJE_PX/max(1,img.get_height())
   size=(max(1,round(img.get_width()*factor)),max(1,round(img.get_height()*factor)))
   self.sprites[nombre]=pygame.transform.scale(img,size)
   anchor=self.anclajes.get(nombre,{}).get("anchor",[img.get_width()//2,img.get_height()])
   self.anclajes[nombre]={**self.anclajes.get(nombre,{}),"anchor":[round(anchor[0]*factor),round(anchor[1]*factor)]}

 def _iniciar_audio(self):
  try:
   if not pygame.mixer.get_init():pygame.mixer.init()
   pygame.mixer.music.load(str(RAIZ/"assets"/"7am_ancpg_ost_main_menu.ogg"));pygame.mixer.music.set_volume(.16);pygame.mixer.music.play(-1,fade_ms=700)
   self.sonido_tambor=pygame.mixer.Sound(str(RAIZ/"assets"/"char_audio_1_microjuego_puño.ogg"));self.sonido_tambor.set_volume(.35)
  except (pygame.error,OSError):self.sonido_tambor=None

 def reiniciar(self):
  self.animacion.seleccionar("idle")
  self.x=350.;self.tiempo=DURACION;self.puntos=0;self.likes=0;self.ocultando=False;self.salto=0.;self.amenaza=False;self.gaze_clock=1.0;self.gaze_right=True
  self.casos=[None]*6;self.foto=None;self.evidencia=False;self.aviso="Explora la terminal y protege la privacidad.";self.aviso_t=4.;self.apunte=None;self.apunte_t=0.
  self.final=None;self.victoria=False;self.pausa=False;self.sel=0;self.rects=[];self.elapsed=0.;self.loss_timer=0.
  self.inicio=True;self.revelados=[False]*6;self.investigacion=[0.]*6;self.racha_casos=0;self.casos_bien=0
  self.guia="A / D";self.guia_vista=False;self.flash_timer=0.;self.anim_event_t=0.;self.anim_event="";self.stumble_t=0.
  self.guia_camino=False;self.guia_salto=False;self.guia_sigilo=False;self.guia_aviso=False
  self.sellos=[{"x":round(440+i*(PUERTA_X-700)/24),"y":PISO-(92,150,205,150,92)[i%5],"recogido":False} for i in range(25)]
  self.flotante=None;self.pop_puntos=0.;self.en_escondite=False;self.persecucion=0.;self.parpadeo=0.;self.invulnerable=0.
  self.maletas=[{"x":x,"hit":False} for x in (930,1880,2790,3720,4630,5740)]
  self.carrito=None;self.carrito_clock=5.;self.jump_avoid=False;self.walk_phase=0.;self.facing=1;self.last_camera=None

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

 def _mensaje(self,frase,d=2.2):self.aviso=" ".join(str(frase).split()[:4]);self.aviso_t=d
 def _camara(self):return max(0,min(MUNDO-ANCHO,self.x-ANCHO*.43))
 def cerca(self,i):return abs(self.x-PUNTOS[i])<210

 def keydown(self,k):
  if self.inicio and k==pygame.K_SPACE:self.inicio=False;self._mensaje("A / D para caminar",3);return
  if k in (pygame.K_s,pygame.K_DOWN):
   self.ocultando=True
   if self.cerca(5):self.guia_sigilo=True
  elif k==pygame.K_SPACE and self.salto<=0:
   self.salto=.72;self.jump_avoid=True
   if self.carrito:self.guia_salto=True
  elif k==pygame.K_e:
   if self.cerca(1):self.guia_aviso=True
   self.interactuar()
  elif k==pygame.K_p:self.publicar()
 def keyup(self,k):
  if k in (pygame.K_s,pygame.K_DOWN):self.ocultando=False

 def interactuar(self):
  if self.x>=PUERTA_X-170:
   self.final="LLEGASTE A GATE 7";self.victoria=True
   self.estrellas=sum(self.puntos>=umbral for umbral in ESTRELLAS_CURRAM)
   return
  if self.x<340 and self.evidencia:
   self._resolver_caso(5,80,"Evidencia entregada a Policía")
   self.tiempo=min(180,self.tiempo+10);self.evidencia=False;self.persecucion=0
   return
  for i in range(6):
   if self.cerca(i) and self.revelados[i] and self.casos[i] is None:
    if i==1:self._resolver_caso(1,40,"Avisó a la turista")
    elif i==4:self._mensaje("¡FOTO Y P!")
    elif i==5:self._mensaje("¡FOTO SIGILOSA!")
    else:self._mensaje("Sigue la señal")
    return
  self._mensaje("Busca el siguiente sello")

 def _resolver_caso(self,i,puntos,decision):
  if self.casos[i] is not None:return
  bonus=min(30,self.racha_casos*10)
  self.racha_casos+=1;self.casos_bien+=1;self.casos[i]=decision
  total=puntos+bonus;self.puntos+=total;self.tiempo=min(180,self.tiempo+4)
  self._popup(f"+{total}",self.x,PISO-210);self._mensaje(f"+{total} ¡Bien!");self.pop_puntos=.35

 def publicar(self):
  if self.foto is None:self._mensaje("No hay foto lista");return
  i=self.foto
  if i==4 and self.casos[4] is None:
   self._resolver_caso(4,40,"Foto pública y respetuosa");self.likes+=120
  elif i==2 and self.casos[2] is None:
   self.puntos=max(0,self.puntos-20);self.casos[2]="ERROR: Publicó una imagen privada";self.racha_casos=0;self._mensaje("-20 Privado")
  self.foto=None;self.last_camera=None

 def _capturar_foto(self,mouse):
  mx,my=mouse;world_x=self._camara()+mx
  candidatos=[i for i,p in enumerate(PUNTOS) if abs(world_x-p)<175 and 350<my<PISO+40]
  if not candidatos:self._mensaje("Enfoca una persona");return
  i=min(candidatos,key=lambda n:abs(world_x-PUNTOS[n]));dist=abs(self.x-PUNTOS[i])
  self.foto=i;self.last_camera=(i,dist)
  if i==2:
   self.puntos=max(0,self.puntos-20);self.casos[i]="ERROR: Foto de momento privado";self.racha_casos=0;self.foto=None;self._mensaje("-20 Privado");return
  if i==5:
   if self.ocultando and self.en_escondite and not self.amenaza:
    self.flash_timer=.18;self.anim_event="foto_agachada" if self.ocultando else "foto_pie";self.anim_event_t=.30;self.animacion.seleccionar(self.anim_event)
    self.evidencia=True;self.persecucion=20.;self._mensaje("¡CORRE AL POLICÍA!")
   else:
    self.tiempo=max(0,self.tiempo-3);self.casos[5]="ERROR: Detectado; sospechoso huyó";self.racha_casos=0;self.foto=None;self._mensaje("¡Eche, qué grabas!")
   return
  if i==4:self.flash_timer=.18;self.anim_event="foto_agachada" if self.ocultando else "foto_pie";self.anim_event_t=.30;self.animacion.seleccionar(self.anim_event);self._mensaje("¡FOTO Y P!")
  else:self._mensaje("No publiques datos privados")

 def _popup(self,texto,x,y):
  self.flotante={"texto":texto,"x":x,"y":y,"t":1.0}

 def _recoger_sellos(self):
  py=PISO-90-(178*math.sin(math.pi*(.72-self.salto)/.72) if self.salto>0 else 0)
  for sello in self.sellos:
   if sello["recogido"]:continue
   if abs(self.x-sello["x"])<48 and abs(py-sello["y"])<76:
    sello["recogido"]=True;self.puntos+=5;self.pop_puntos=.35
    self._popup("+5",self.x,sello["y"]-25)
    self._mensaje("+5 Sello")
    if self.sonido_tambor:
     try:self.sonido_tambor.play()
     except pygame.error:pass

 def _actualizar_interacciones(self,dt):
  for i,x in enumerate(PUNTOS):
   if self.casos[i] is not None:continue
   if abs(self.x-x)<=250:
    self.investigacion[i]+=dt
    if self.investigacion[i]>=.8 and not self.revelados[i]:
     self.revelados[i]=True
     if i==0:self._resolver_caso(i,30,"Confirmó que era maizena")
     elif i==3:self._resolver_caso(i,30,"Era hielo derramado")
     else:self._mensaje(("¡AVÍSALE!" if i==1 else "PRIVADO" if i==2 else "¡FOTO Y P!" if i==4 else "¡FOTO SIGILOSA!"))
   else:self.investigacion[i]=0.
  # Pasar de largo sin apuntar protege a la persona vulnerable.
  if self.casos[2] is None and self.revelados[2] and self.x>=PUNTOS[2]+55 and self.apunte!=2:
   self._resolver_caso(2,30,"Pasó de largo y respetó privacidad")

 def update(self,dt,keys,mouse):
  if self.pausa or self.final or self.inicio:return
  dt=min(dt,.05);self.elapsed+=dt;self.tiempo=max(0,self.tiempo-dt)
  self.salto=max(0,self.salto-dt);self.aviso_t=max(0,self.aviso_t-dt);self.walk_phase+=dt*VELOCIDAD_CAMI/34
  self.invulnerable=max(0,self.invulnerable-dt);self.parpadeo=max(0,self.parpadeo-dt);self.flash_timer=max(0,getattr(self,"flash_timer",0)-dt);self.anim_event_t=max(0,getattr(self,"anim_event_t",0)-dt);self.stumble_t=max(0,getattr(self,"stumble_t",0)-dt)
  if self.anim_event_t==0:self.anim_event=""
  self.pop_puntos=max(0,self.pop_puntos-dt)
  if self.flotante:self.flotante["t"]-=dt;self.flotante["y"]-=28*dt
  if self.flotante and self.flotante["t"]<=0:self.flotante=None
  left=keys[pygame.K_a] or keys[pygame.K_LEFT];right=keys[pygame.K_d] or keys[pygame.K_RIGHT]
  if left!=right:
   self.guia_camino=True
   direction=-1 if left else 1;self.facing=direction;self.x=max(0,min(PUERTA_X,self.x+direction*VELOCIDAD_CAMI*dt))
  self.gaze_clock-=dt
  if self.gaze_clock<=0:self.gaze_right=not self.gaze_right;self.gaze_clock=random.uniform(2.0,3.2)
  self.amenaza=self.gaze_clock<.65
  world_mouse=self._camara()+mouse[0]
  self.apunte=2 if abs(world_mouse-PUNTOS[2])<90 and 430<mouse[1]<840 else None
  self.apunte_t=self.apunte_t+dt if self.apunte is not None else 0.
  self._actualizar_interacciones(dt)
  refugios=(2240,3840,4660,5440,PUNTOS[5]-105)
  self.en_escondite=any(abs(self.x-p)<125 for p in refugios)
  self._recoger_sellos()
  if self.persecucion>0:
   self.persecucion=max(0,self.persecucion-dt)
   if self.persecucion<=0 and self.evidencia:
    self.evidencia=False;self.casos[5]="ERROR: El sospechoso escapó";self.racha_casos=0;self._mensaje("El sospechoso escapó")
  self.carrito_clock-=dt
  if self.carrito is None and self.carrito_clock<=0:
   self.carrito={"x":self.x+520,"hit":False};self.carrito_clock=random.uniform(7,10);self.jump_avoid=False
  if self.carrito:
   self.carrito["x"]-=520*dt;dist=abs(self.carrito["x"]-self.x)
   if 100<dist<260 and not self.carrito["hit"]:self._mensaje("¡SALTA!")
   if not self.carrito["hit"] and dist<95 and self.invulnerable<=0:
    self.carrito["hit"]=True
    if self.salto>0 or (self.ocultando and self.en_escondite):self._mensaje("¡Esquivaste!")
    else:
     self.tiempo=max(0,self.tiempo-3);self.invulnerable=1.5;self.parpadeo=1.5
     self.animacion.seleccionar("empujon");self.stumble_t=.18;self.x=max(0,self.x-36);self._mensaje("-3 s Tropiezo")
   if self.carrito["x"]<self.x-180:self.carrito=None
  for maleta in self.maletas:
   if not maleta["hit"] and abs(maleta["x"]-self.x)<48 and self.invulnerable<=0:
    maleta["hit"]=True
    if self.salto>0 or (self.ocultando and self.en_escondite):self._mensaje("¡Esquivaste!")
    else:
     self.tiempo=max(0,self.tiempo-3);self.invulnerable=1.5;self.parpadeo=1.5
     self.animacion.seleccionar("empujon");self.stumble_t=.18;self.x=max(0,self.x-36);self._mensaje("-3 s Tropiezo")
  if self.evidencia and self.x<340:self._mensaje("¡Entrega a Policía!")
  self._actualizar_animacion(dt,bool(left!=right))
  if self.tiempo<=0:self.final="VUELO PERDIDO";self.victoria=False

 def _actualizar_animacion(self,dt,caminando):
  nombre=self.animacion.nombre
  if self.anim_event_t>0 or self.stumble_t>0:return
  if nombre=="empujon" and not self.animacion.terminada():return
  if nombre in ("foto_pie","foto_agachada") and self.animacion.terminada():
   self.animacion.seleccionar("cuclillas" if self.ocultando else "idle");nombre=self.animacion.nombre
  if self.salto>0:nuevo="salto"
  elif self.ocultando:
   if nombre not in ("agachar","cuclillas"):nuevo="agachar"
   elif nombre=="agachar" and self.animacion.terminada():nuevo="cuclillas"
   else:nuevo=nombre
  elif nombre in ("agachar","cuclillas"):nuevo="levantarse"
  elif nombre=="levantarse" and not self.animacion.terminada():nuevo=nombre
  else:nuevo="walk" if caminando else "idle"
  self.animacion.seleccionar(nuevo)

 def _escala_entera(self,img,factor=2):
  if img is None:return None
  return pygame.transform.scale(img,(img.get_width()*factor,img.get_height()*factor))

 def _sprite_en(self,s,nombre,screen_x,base_y,factor=1,flip=False,bob=0):
  img=self.sprites.get(nombre)
  if img is None:return
  if factor!=1:img=self._escala_entera(img,factor)
  if flip:img=self.sprites_flip[nombre] if nombre in self.sprites_flip else pygame.transform.flip(img,True,False)
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
  cam=self._camara();ground=PISO
  self._sprite_en(s,"policia",180-cam,ground,1,bob=int(math.sin(self.elapsed*1.8)*2))
  self._sprite_en(s,"grupo_vendedor_letrero",1940-cam,ground,2)
  for i,(x,nombre) in enumerate(zip(PUNTOS,NPC_SPRITES)):
   sx=x-cam
   if not -230<sx<ANCHO+230:continue
   bob=int(math.sin(self.elapsed*1.7+i)*3) if i in (4,5) else 0
   flip=(i==5 and not self.gaze_right) or (i==0 and self.facing<0)
   pygame.draw.ellipse(s,(89,73,64),(int(sx-58),ground-5,116,16))
   self._sprite_en(s,nombre,sx,ground+bob,1,flip=flip)
   # Iconos de estado por encima del NPC: investigación, acción o resultado.
   cy=ground-ALTURA_PERSONAJE_PX-34
   if self.casos[i] is None and not self.revelados[i]:
    pygame.draw.circle(s,(244,188,54),(int(sx),cy),20);texto_con_contorno(s,"?",(sx,cy),25,(255,255,255),centro=True,grosor=1)
    progreso=min(1,self.investigacion[i]/.8)
    if progreso:pygame.draw.arc(s,(255,255,255),(sx-28,cy-28,56,56),-math.pi/2,-math.pi/2+math.tau*progreso,4)
   elif self.casos[i] is not None:
    error=str(self.casos[i]).startswith("ERROR:");pygame.draw.circle(s,(207,72,80) if error else (67,166,110),(int(sx),cy),19)
    if error:pygame.draw.line(s,(255,255,255),(sx-7,cy-7),(sx+7,cy+7),4);pygame.draw.line(s,(255,255,255),(sx+7,cy-7),(sx-7,cy+7),4)
    else:pygame.draw.lines(s,(255,255,255),False,[(sx-8,cy),(sx-2,cy+7),(sx+9,cy-8)],4)
    if not error:
     etiqueta_ok={0:"NO ES DELITO",1:"AVISÓ",2:"PRIVADO",3:"SOLO HIELO",4:"FOTO Y P",5:"POLICÍA"}.get(i,"OK")
     texto_con_contorno(s,etiqueta_ok,(sx,cy+29),18,(255,255,255),centro=True,grosor=2)
   else:
    colors={1:(79,149,211),2:(205,73,84),4:(67,166,110),5:(225,143,57)}
    pygame.draw.circle(s,colors.get(i,(67,166,110)),(int(sx),cy),20)
    etiqueta={1:"E",2:"PRIVADO",4:"FOTO + P",5:("S" if self.amenaza else "FOTO")}.get(i,"OK")
    if i==5:
     ojo=(227,65,69) if self.amenaza else (68,179,118)
     pygame.draw.ellipse(s,ojo,(sx-12,cy-8,24,16));pygame.draw.circle(s,(255,255,255),(int(sx),cy),4)
    texto_con_contorno(s,etiqueta,(sx,cy+29),18,(255,255,255),centro=True,grosor=2)
  # Refugios marcados y teclas de sigilo junto a los pilares existentes.
  for wx in (2240,3840,4660,5440,PUNTOS[5]-105):
   sx=wx-cam
   if -50<sx<ANCHO+50:
    pygame.draw.ellipse(s,(95,183,122),(sx-42,ground-7,84,18),3)
    key=self.sprites.get("tecla_s_sigilo")
    if key:s.blit(key,key.get_rect(center=(sx,ground-28)))
  if self.carrito:
   sx=self.carrito["x"]-cam
   if -120<sx<ANCHO+120:pygame.draw.ellipse(s,(240,186,57),(sx-58,ground-200,116,36),4);texto_con_contorno(s,"¡SALTA!",(sx,ground-182),22,(255,255,255),centro=True,grosor=2)
  for maleta in self.maletas:
   sx=maleta["x"]-cam
   if not maleta["hit"] and -30<sx<ANCHO+30:
    pygame.draw.rect(s,(170,104,76),(int(sx-15),ground-22,30,20));pygame.draw.rect(s,(242,209,157),(int(sx-11),ground-18,22,12),2);pygame.draw.line(s,(80,61,59),(sx-4,ground-23),(sx+4,ground-23),3)
  # Puerta del mundo, además del indicador pequeño del HUD.
  door_x=PUERTA_X-cam
  if -160<door_x<ANCHO+160:
   self._blit_escalado(s,"puerta_embarque",(int(door_x-70),ground-190),1)
   texto_con_contorno(s,"E PARA ABORDAR",(door_x,ground-205),23,(255,255,255),centro=True,grosor=2)
  self._dibujar_sellos(s,cam)

 def _dibujar_sellos(self,s,cam):
  for i,sello in enumerate(self.sellos):
   if sello["recogido"]:continue
   sx=sello["x"]-cam;sy=sello["y"]
   if not -30<sx<ANCHO+30:continue
   # Insignia pixel art nueva (no hay un sello equivalente en las hojas).
   pygame.draw.rect(s,(67,166,110),(int(sx-13),int(sy-13),26,26))
   pygame.draw.rect(s,(227,245,212),(int(sx-8),int(sy-8),16,16))
   pygame.draw.rect(s,(65,147,97),(int(sx-5),int(sy),4,5));pygame.draw.rect(s,(65,147,97),(int(sx-2),int(sy+3),4,3));pygame.draw.rect(s,(65,147,97),(int(sx+1),int(sy-4),5,4))
   if i%4==0:pygame.draw.circle(s,(255,241,150),(int(sx+15),int(sy-14)),3)

 def _draw_player(self,s):
  sx=self.x-self._camara();ground=PISO
  jump_y=int(178*math.sin(math.pi*(.72-self.salto)/.72)) if self.salto>0 else 0
  moving=bool(self.facing and not self.ocultando and self.salto<=0)
  bob=0 if self.ocultando or self.salto>0 else int(abs(math.sin(self.walk_phase))*3) if moving else 0
  shadow_scale=max(.35,1-jump_y/230)
  pygame.draw.ellipse(s,(96,76,66),(int(sx-65*shadow_scale),ground-3, int(130*shadow_scale),13))
  frame=self.animacion.cuadro(1/FPS)
  img=self.sprites.get(frame)
  if img and (self.invulnerable<=0 or int(self.elapsed*14)%2==0):
   rendered=self.sprites_flip.get(frame,img) if self.facing<0 else img
   ax,ay=self.anclajes.get(frame,{}).get("anchor",[img.get_width()//2,img.get_height()])
   s.blit(rendered,(int(sx-ax),int(ground-ay-jump_y+bob)))
  if self.ocultando and self.en_escondite:
   key=self.sprites.get("tecla_s_sigilo")
   if key:s.blit(key,key.get_rect(center=(int(sx),ground-207)))
  if self.flash_timer>0:
   flash=pygame.Surface((110,110),pygame.SRCALPHA);flash.fill((255,255,230,150));s.blit(flash,(int(sx-55),ground-225))

 def _draw_carrito(self,s):
  if not self.carrito:return
  sx=self.carrito["x"]-self._camara()
  if -190<sx<ANCHO+190:self._sprite_en(s,"trabajador_carrito",sx,PISO,1,flip=True)

 def _draw_camera(self,s,mouse):
  mx,my=mouse;pygame.draw.rect(s,(246,249,232),(mx-46,my-38,92,76),4);pygame.draw.line(s,(246,249,232),(mx-58,my),(mx+58,my),3);pygame.draw.line(s,(246,249,232),(mx,my-51),(mx,my+51),3)
  pygame.draw.circle(s,(240,248,222),(mx,my),7,2)
  if self.apunte_t>=1:
   panel(s,pygame.Rect(mx-125,my-75,250,46),(255,218,218),(178,44,54),8,3);texto(s,"PRIVACIDAD",(mx,my-52),20,(151,31,44),True)
  if self.foto is not None:
   panel(s,pygame.Rect(ANCHO-300,205,260,54),(239,247,226),(77,113,80),10,2);texto(s,"FOTO LISTA · P",(ANCHO-170,232),20,(55,88,63),True)

 def _draw_hud(self,s):
  titulo=self._escala_entera(self.sprites.get("titulo"),1)
  if titulo:s.blit(titulo,(32,18))
  pop=1.0+max(0,self.pop_puntos)/.35*.10
  score=fuente(round(54*pop),True).render(f"CIUDADANÍA  {self.puntos}",True,(255,248,226))
  rect=score.get_rect(center=(990,54))
  texto_con_contorno(s,f"CIUDADANÍA  {self.puntos}",(990,54),round(54*pop),(255,248,226),centro=True,grosor=4,negrita=True)
  if self.MOSTRAR_RELOJ:texto_con_contorno(s,f"{int(self.tiempo//60)}:{int(self.tiempo%60):02}",(1780,55),38,(255,248,226),centro=True,grosor=3,negrita=True)
  texto_con_contorno(s,"LLEGA A LA PUERTA 7",(42,112),32,(255,248,226),grosor=3,negrita=True)
  pygame.draw.rect(s,(57,48,65),(42,155,440,20),border_radius=8)
  pygame.draw.rect(s,(83,167,200),(42,155,round(440*min(1,self.x/PUERTA_X)),20),border_radius=8)
  # Meta de estrellas por ciudadanía, con hitos visibles.
  pygame.draw.rect(s,(57,48,65),(650,137,620,22),border_radius=9)
  pygame.draw.rect(s,(102,185,123),(650,137,round(620*min(1,self.puntos/ESTRELLAS_CURRAM[-1])),22),border_radius=9)
  for umbral in ESTRELLAS_CURRAM:
   px=650+round(620*umbral/ESTRELLAS_CURRAM[-1]);pygame.draw.polygon(s,(255,226,126),[(px,126),(px+4,135),(px+14,136),(px+7,143),(px+9,153),(px,148),(px-9,153),(px-7,143),(px-14,136),(px-4,135)])
  for i in range(6):
   status=self.casos[i];color=(145,143,145) if status is None else (208,73,82) if str(status).startswith("ERROR:") else (72,170,112)
   cx=1400+i*78;pygame.draw.circle(s,color,(cx,148),20);texto(s,str(i+1),(cx,148),22,(255,255,255),True,True)
  # Controles breves con los iconos de las teclas de la hoja.
  cy=self.CONTROLES_Y
  pygame.draw.rect(s,(52,43,51),(40,cy,ANCHO-80,82),border_radius=17);pygame.draw.rect(s,(181,142,111),(40,cy,ANCHO-80,82),3,border_radius=17)
  grupos=[("tecla_a","A/D"),("tecla_space","SALTAR"),("tecla_s","ESCONDER"),("tecla_e","AVISAR"),("tecla_camara","FOTO"),("tecla_p","PUBLICAR")];centros=(330,585,840,1095,1350,1605)
  for (key,label),cx in zip(grupos,centros):
   img=self.sprites.get(key)
   if img:s.blit(img,img.get_rect(center=(cx,cy+30)))
   texto_con_contorno(s,label,(cx,cy+69),24,(255,246,228),centro=True,grosor=2,negrita=True)
  if self.evidencia:
   texto_con_contorno(s,"¡CORRE AL POLICÍA!",(960,225),42,(255,246,222),centro=True,grosor=4,negrita=True)
   pygame.draw.polygon(s,(255,225,120),[(1000,265),(982,298),(1018,298)])
   pygame.draw.rect(s,(54,48,61),(810,305,300,16),border_radius=7)
   pygame.draw.rect(s,(223,110,77),(810,305,round(300*self.persecucion/20),16),border_radius=7)
  elif self.carrito and 100<abs(self.carrito["x"]-self.x)<260:
   texto_con_contorno(s,"¡SALTA!",(960,225),40,(255,246,222),centro=True,grosor=4,negrita=True)
  if self.flotante:
   sx=self.flotante["x"]-self._camara();texto_con_contorno(s,self.flotante["texto"],(sx,self.flotante["y"]),30,(255,241,153),centro=True,grosor=3,negrita=True)
  if self.aviso_t>0:pass

 def _draw_inicio(self,s):
  velo=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA);velo.fill((22,19,32,210));s.blit(velo,(0,0))
  panel(s,pygame.Rect(350,230,1220,610),(37,31,48),(239,222,190),26,5)
  texto_con_contorno(s,"CAMINA · JUNTA SELLOS · RESUELVE",(960,320),52,(255,247,224),centro=True,grosor=4,negrita=True)
  lineas=("A / D: LLEGA A LA PUERTA 7", "CADA PERSONA ES UN CASO DE REDES SOCIALES:", "DESINFORMACIÓN, PRIVACIDAD, CONTENIDO VIRAL.", "NO PUBLIQUES CHISMES NI DATOS PRIVADOS.")
  for i,linea in enumerate(lineas):texto_con_contorno(s,linea,(960,420+i*78),36,(255,255,255),centro=True,grosor=3,negrita=True)
  texto_con_contorno(s,"ESPACIO PARA EMPEZAR",(960,780),35,(255,225,126),centro=True,grosor=3,negrita=True)

 def _draw_guia(self,s):
  key=label=None
  if not self.guia_camino:key="tecla_a";label="A / D CAMINAR"
  elif self.carrito and not self.guia_salto and 100<abs(self.carrito["x"]-self.x)<260:key="tecla_space";label="¡SALTA!"
  elif self.cerca(5) and not self.guia_sigilo:key="tecla_s_sigilo";label="S ESCONDERSE"
  elif self.cerca(1) and self.revelados[1] and not self.guia_aviso:key="tecla_e";label="E PARA AVISAR"
  if not key:return
  panel(s,pygame.Rect(60,855,360,82),(39,34,52),(248,224,171),16,3)
  img=self.sprites.get(key)
  if img:s.blit(img,img.get_rect(center=(120,895)))
  texto_con_contorno(s,label,(280,895),27,(255,255,255),centro=True,grosor=2,negrita=True)

 def _draw_notificacion(self,s):
  if self.aviso_t<=0:return
  r=pygame.Rect(ANCHO//2-470,836,940,70);panel(s,r,(255,247,229),(105,75,76),14,3)
  texto(s,self.aviso,(ANCHO//2,871),24,(69,51,57),True)

 def _draw_final(self,s):
  estrellas=sum(self.puntos>=umbral for umbral in ESTRELLAS_CURRAM) if self.victoria else 0
  lineas=[f"CIUDADANÍA {self.puntos} · {estrellas} ESTRELLAS"]
  for i,(nombre,fenomeno,leccion) in enumerate(CASOS):
   estado="Pendiente" if self.casos[i] is None else "ERROR" if str(self.casos[i]).startswith("ERROR:") else "OK"
   lineas.append(f"{estado} · {fenomeno} ({nombre}): {leccion}")
  pantalla_final(s,"PERFIL CURRAMGRAM · "+str(self.final),lineas,self.TEXTO_REINICIO)

 def draw(self,s,mouse=(960,540)):
  self._dibujar_fondo(s);self._draw_prop_personajes(s);self._draw_carrito(s);self._draw_player(s)
  self._draw_hud(s);self._draw_camera(s,mouse);self._draw_notificacion(s);self._draw_guia(s)
  if self.inicio:self._draw_inicio(s);return
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
