"""Emoji Catch: captura el feed con dos manos y conserva el balance."""
import math
import random
import pygame
from comun import ANCHO, ALTO, FPS, RAIZ, VentanaVirtual, cargar_imagen, cargar_sprite, revisar_recursos, texto, fuente, panel, leer_entrada, menu_pausa, pantalla_final

# Parámetros configurables
DURACION = 120.0
SALUD_INICIAL = 50
SALUD_ACIERTO = 3
SALUD_COMBO_5 = 1
SALUD_COMBO_10 = 2
SALUD_ESCAPE = 5
SALUD_ESCAPE_MEGA = 10
SALUD_TOPE = 100
ANIMO_DURACION = 8.0
ANIMO_ENFRIAMIENTO = 20.0
UMBRAL_BALANCE = 24
VELOCIDAD_MANO = 680.0
DIFICULTAD_MAX = 1.65
COLOR_MORADO = (133, 79, 185)
COLOR_AZUL = (55, 147, 218)

NEGATIVOS = ("emoji_enojado_naranja", "emoji_enojado_rojo", "emoji_triste", "emoji_vomito_1", "emoji_vomito_2", "emoji_corazon_roto", "emoji_pulgar_abajo")
POSITIVOS = ("emoji_sonriente", "emoji_cara_azul", "emoji_corazon", "emoji_pulgar_arriba", "emoji_bolsa_dinero")
SPRITES = (*NEGATIVOS, *POSITIVOS)


def tiene_tecla(teclas, codigo):
    """Permite usar tanto el vector de teclas sostenidas como eventos inyectados."""
    try:
        return bool(teclas[codigo])
    except (TypeError, IndexError, KeyError):
        return codigo in teclas


class EmojiCatch:
    def __init__(self):
        revisar_recursos("emoji_catch")
        self.fondo = cargar_imagen("fondo_concentracion_microjuego.png", (ANCHO, ALTO), alpha=False)
        self.sprites = {n: cargar_sprite(f"{n}.png", "emoji") for n in SPRITES}
        self.decoracion = {n: cargar_sprite(f"{n}.png", "emoji") for n in (
            "titulo", "tiempo", "tarjeta_mano_izq", "tarjeta_mano_der", "barra_negatividad", "barra_positividad", "mano_morada", "mano_azul_der")}
        self.mano_morada = self._escalar(self.decoracion["mano_morada"], 2)
        self.mano_azul = self._escalar(self.decoracion["mano_azul_der"], 2)
        self._limpiar_barras_de_matte()
        self._preparar_barras()
        self._preparar_corazon_partido()
        self.sonido_bloqueo = None
        self._iniciar_audio()
        self.reiniciar()

    @staticmethod
    def _escalar(imagen, factor):
        if imagen is None: return None
        return pygame.transform.scale(imagen, (imagen.get_width()*factor, imagen.get_height()*factor))

    def _limpiar_barras_de_matte(self):
        """Recorta la cuadrícula plana y conserva el tubo y rótulo del sprite."""
        for clave in ("barra_negatividad", "barra_positividad"):
            src=self.decoracion.get(clave)
            if src is None: continue
            limpio=src.copy();w,h=limpio.get_size()
            izquierda=clave=="barra_negatividad"
            cuerpo=pygame.Rect(29,2,37,214) if izquierda else pygame.Rect(7,2,37,214)
            etiqueta=pygame.Rect(2,35,28,145) if izquierda else pygame.Rect(43,35,31,145)
            for y in range(h):
                for x in range(w):
                    dentro=cuerpo.collidepoint(x,y)
                    if dentro:
                        radio=17;cx=max(cuerpo.left+radio,min(x,cuerpo.right-radio-1));cy=max(cuerpo.top+radio,min(y,cuerpo.bottom-radio-1))
                        dentro=(x-cx)**2+(y-cy)**2<=radio**2
                    if dentro:continue
                    color=src.get_at((x,y));brillo=max(color.r,color.g,color.b);chroma=brillo-min(color.r,color.g,color.b)
                    # El rótulo va a lados opuestos según el color del tubo.
                    if etiqueta.collidepoint(x,y) and chroma>=24:continue
                    limpio.set_at((x,y),(0,0,0,0))
            self.decoracion[clave]=limpio

    def _preparar_barras(self):
        self.barras = {}
        # Se vacía el relleno ya impreso para animarlo por dentro del marco original.
        for clave, interior in (("barra_negatividad", pygame.Rect(35, 70, 25, 125)), ("barra_positividad", pygame.Rect(13, 70, 25, 125))):
            original = self.decoracion[clave]
            if original is None: self.barras[clave] = None; continue
            marco = original.copy()
            # Blend min fuerza alfa 0; un blit transparente normal no borra el relleno impreso.
            marco.fill((0,0,0,0), interior, special_flags=pygame.BLEND_RGBA_MIN)
            self.barras[clave] = (self._escalar(marco,2), pygame.Rect(interior.x*2,interior.y*2,interior.w*2,interior.h*2))

    def _preparar_corazon_partido(self):
        sprite = self.sprites.get("emoji_corazon_roto")
        self.mitades_corazon = None
        if sprite:
            self.mitades_corazon = (sprite.subsurface((0,0,sprite.get_width()//2,sprite.get_height())).copy(),
                                   sprite.subsurface((sprite.get_width()//2,0,sprite.get_width()-sprite.get_width()//2,sprite.get_height())).copy())

    def _iniciar_audio(self):
        try:
            if not pygame.mixer.get_init(): pygame.mixer.init()
            pygame.mixer.music.load(str(RAIZ / "assets" / "7am_ancpg_ost_main_menu.ogg"))
            pygame.mixer.music.set_volume(0.18); pygame.mixer.music.play(-1, fade_ms=700)
            self.sonido_bloqueo = pygame.mixer.Sound(str(RAIZ / "assets" / "char_audio_0_microjuego_puño.ogg"))
            self.sonido_bloqueo.set_volume(0.45)
        except (pygame.error, OSError):
            self.sonido_bloqueo = None

    def reiniciar(self):
        self.tiempo=DURACION; self.salud=SALUD_INICIAL; self.negatividad=0; self.positividad=0; self.puntos=0
        self.manos=[570.0,1350.0]; self.direccion=[0,0]; self.pulso=[0.0,0.0]
        self.items=[]; self.particulas=[]; self.grietas=[]; self.avisos=[]
        self.spawn=0.5; self.wave_left=0.0; self.wave_kind=None; self.wave_clock=14.0; self.wave_label=""
        self.mega_clock=19.0; self.combo=0; self.mejor_racha=0; self.sponsor=0.0
        self.desbalance=0.0; self.desbalance_aviso=0.0; self.screen_shake=0.0; self.final=""; self.pausa=False; self.sel=0; self.rects=[]
        self.elapsed=0.0;self.victoria=False;self.estrellas=0
        self.salud_visual=float(self.salud);self.salud_flash=0.0;self.salud_flash_color=(70,190,115)
        self.salud_floaters=[];self.animo_activo=0.0;self.animo_enfriamiento=0.0

    def mover_manos(self, teclas, dt):
        """A/D mueven exclusivamente la mano morada; J/L exclusivamente la azul."""
        antes=self.manos[:]
        izq=int(tiene_tecla(teclas,pygame.K_d))-int(tiene_tecla(teclas,pygame.K_a))
        der=int(tiene_tecla(teclas,pygame.K_l))-int(tiene_tecla(teclas,pygame.K_j))
        for i,d in enumerate((izq,der)):
            self.direccion[i]=d
            limites=((120.0,900.0),(1020.0,1800.0))[i]
            self.manos[i]=max(limites[0],min(limites[1],self.manos[i]+d*VELOCIDAD_MANO*dt))
        return self.manos[0]-antes[0], self.manos[1]-antes[1]

    def _aviso(self, frase, color=(255,245,224), tiempo=2.2):
        self.avisos.append({"texto":frase,"color":color,"t":tiempo})

    def _nuevo_item(self, tipo=None, x=None, mega=False, troll=False):
        tipo=tipo or random.choice(SPRITES)
        negativo=tipo in NEGATIVOS or tipo=="mitad_rota"
        limites=(180,900) if negativo else (1020,1740)
        x=float(x if x is not None else random.uniform(*limites))
        x=max(limites[0],min(limites[1],x))
        factor=1.0+min(0.85,self.elapsed/145)
        item={"kind":tipo,"x":x,"base_x":x,"y":175.0,"t":0.0,"speed":random.uniform(210,330)*factor,"phase":random.random()*math.tau,"angle":0.0,"mega":mega,"hp":3 if mega else 1,"troll":troll,"mutated":False,"size":260 if mega else random.randint(100,130)}
        self.items.append(item)
        if tipo=="emoji_corazon_roto" and self.mitades_corazon:
            self.items.remove(item)
            for side,half in enumerate(self.mitades_corazon):
                self.items.append({**item,"kind":"mitad_rota","half":half,"x":x+(side*2-1)*18,"base_x":x+(side*2-1)*18,"speed":item["speed"]*random.uniform(.92,1.08),"phase":item["phase"]+side*math.pi,"size":106})

    def _iniciar_oleada(self):
        self.wave_kind=random.choice(("raid","trend"));self.wave_left=6.0
        self.wave_label={"raid":"¡RAID DE HATERS!","trend":"¡TENDENCIA VIRAL!","troll":""}[self.wave_kind]
        self._aviso(self.wave_label,(255,235,215),3.0)
        self.wave_clock=random.uniform(18,25)

    def _spawn(self,dt):
        self.spawn-=dt
        if self.spawn<=0:
            if self.wave_kind=="raid":tipo=random.choice(NEGATIVOS)
            elif self.wave_kind=="trend":tipo=random.choice(POSITIVOS)
            else:tipo=None
            self._nuevo_item(tipo)
            self.spawn=max(.22,random.uniform(.48,.78)*(1-min(.42,self.elapsed/270)))
        self.wave_clock-=dt
        if self.wave_clock<=0 and self.wave_left<=0:self._iniciar_oleada()
        self.wave_left=max(0,self.wave_left-dt)
        if self.wave_left<=0:self.wave_kind=None
        self.mega_clock-=dt
        if self.mega_clock<=0:
            self._nuevo_item("emoji_enojado_rojo",random.uniform(350,1570),mega=True)
            self._aviso("¡MEGA-HATER! 3 bloqueos para frenarlo",(255,224,220),2.8)
            self.mega_clock=random.uniform(21,26)

    def _puntos_captura(self, mano, item):
        tipo=item["kind"]
        negativo=tipo in NEGATIVOS or tipo=="mitad_rota" or (item.get("troll") and item.get("mutated"))
        mano_correcta=0 if negativo else 1
        if mano!=mano_correcta:return
        if item.get("mega"):
            item["hp"]-=1;self.combo+=1;self.mejor_racha=max(self.combo,self.mejor_racha)
            self._cambiar_salud(SALUD_ACIERTO+(SALUD_COMBO_5 if self.combo>=5 else 0)+(SALUD_COMBO_10 if self.combo>=10 else 0))
            self._particulas(item["x"],item["y"],(248,114,84),24);self.screen_shake=.10
            if item["hp"]>0:self._aviso(f"¡GOLPE! Mega-Hater {item['hp']}/3")
            else:self.puntos+=60*(2 if self.sponsor>0 or self.animo_activo>0 else 1);self.negatividad=min(100,self.negatividad+12);self._aviso("¡MEGA-HATER BLOQUEADO! +60",(255,232,205));self.items.remove(item)
            return
        self.combo+=1;self.mejor_racha=max(self.combo,self.mejor_racha)
        mult=3 if self.combo>=10 else 2 if self.combo>=5 else 1
        self._cambiar_salud(SALUD_ACIERTO+(SALUD_COMBO_5 if self.combo>=5 else 0)+(SALUD_COMBO_10 if self.combo>=10 else 0))
        if item.get("troll") and item.get("mutated"):
            mult=1;self._aviso("Troll desenmascarado: contaste su estado final",(232,228,255))
        score=int(10*mult*(2 if self.sponsor>0 or self.animo_activo>0 else 1));self.puntos+=score
        if negativo:self.negatividad=min(100,self.negatividad+3)
        else:self.positividad=min(100,self.positividad+3)
        self.pulso[mano]=.22;self._particulas(item["x"],item["y"],COLOR_MORADO if mano==0 else COLOR_AZUL,18)
        if negativo:
            if self.sonido_bloqueo:
                try:self.sonido_bloqueo.play()
                except pygame.error:pass
            self._aviso("¡USUARIO BLOQUEADO!"+(f"   +{score}" if mult==1 else f"   COMBO x{mult} +{score}"),(241,228,255))
        else:self._aviso(f"+{score} pts"+(f"  COMBO x{mult}" if mult>1 else ""),(226,243,255))
        if tipo=="emoji_bolsa_dinero":self.sponsor=6.0;self._aviso("PATROCINIO ACTIVO · 6 s de puntos dobles",(255,244,211),3.0)

    def _cambiar_salud(self, cantidad):
        anterior=self.salud
        self.salud=max(0,min(SALUD_TOPE,self.salud+cantidad))
        real=self.salud-anterior
        if real:
            self.salud_flash=.65;self.salud_flash_color=(70,190,115) if real>0 else (225,75,90)
            self.salud_floaters.append({"texto":f"{real:+d}","t":1.0})
            if self.salud==SALUD_TOPE and anterior<SALUD_TOPE and self.animo_enfriamiento<=0:
                self.animo_activo=ANIMO_DURACION;self.animo_enfriamiento=ANIMO_ENFRIAMIENTO
                self._aviso("ÁNIMO A TOPE · PUNTOS x2",(224,249,215),2.2)
            if self.salud<=0:
                self.final="SALUD MENTAL AGOTADA";self.victoria=False;self.estrellas=0

    def _particulas(self,x,y,color,n=12):
        for _ in range(n):
            ang=random.random()*math.tau;v=random.uniform(70,260)
            self.particulas.append({"x":x,"y":y,"vx":math.cos(ang)*v,"vy":math.sin(ang)*v,"t":random.uniform(.35,.8),"color":color,"r":random.randint(3,9)})

    def update(self,dt,teclas):
        if self.pausa or self.final:return
        dt=min(dt,.05)
        if self.tiempo<3:dt*=.38
        self.elapsed+=dt;self.tiempo=max(0,self.tiempo-dt);self.sponsor=max(0,self.sponsor-dt)
        self.animo_activo=max(0,self.animo_activo-dt);self.animo_enfriamiento=max(0,self.animo_enfriamiento-dt)
        self.salud_flash=max(0,self.salud_flash-dt)
        self.salud_visual+=(self.salud-self.salud_visual)*min(1,dt*8)
        self.mover_manos(teclas,dt)
        self._spawn(dt)
        dificultad=1+min(DIFICULTAD_MAX-1,self.elapsed/90)
        for item in list(self.items):
            item["t"]+=dt
            if item["kind"] in ("emoji_vomito_1","emoji_vomito_2"):
                item["x"]=item["base_x"]+math.sin(item["t"]*6+item["phase"])*58
            elif item["kind"]=="emoji_enojado_rojo" or item["kind"]=="emoji_enojado_naranja":
                item["speed"]+=38*dt
            elif item["kind"]=="emoji_pulgar_abajo":item["angle"]=(item["angle"]+dt*85)%360
            if self.sponsor>0 and not item.get("mega"):
                hand=0 if item["kind"] in NEGATIVOS else 1;item["x"]+=(self.manos[hand]-item["x"])*min(.8,dt*.65)
            item["y"]+=item["speed"]*dificultad*dt
            capturada=None
            if 785<item["y"]<1010:
                for i,hx in enumerate(self.manos):
                    if abs(item["x"]-hx)<(125 if item.get("mega") else 104):capturada=i;break
            if capturada is not None:
                self._puntos_captura(capturada,item)
                if item in self.items and not item.get("mega"):self.items.remove(item)
            elif item["y"]>1040:
                self._cambiar_salud(-SALUD_ESCAPE_MEGA if item.get("mega") else -SALUD_ESCAPE)
                self.grietas.append({"x":item["x"],"y":1010,"t":1.8});self.screen_shake=.32
                self._aviso("¡SE ESCAPÓ! Salud mental −10" if item.get("mega") else "¡SE ESCAPÓ! Salud mental −5",(255,222,221))
                if item in self.items:self.items.remove(item)
                self.combo=0
                if self.final:break
        for part in self.particulas:
            part["x"]+=part["vx"]*dt;part["y"]+=part["vy"]*dt;part["vy"]+=160*dt;part["t"]-=dt
        self.particulas=[p for p in self.particulas if p["t"]>0]
        for a in self.avisos:a["t"]-=dt
        self.avisos=[a for a in self.avisos if a["t"]>0]
        for g in self.grietas:g["t"]-=dt
        self.grietas=[g for g in self.grietas if g["t"]>0]
        self.pulso=[max(0,p-dt) for p in self.pulso];self.screen_shake=max(0,self.screen_shake-dt)
        for floater in self.salud_floaters:floater["t"]-=dt
        self.salud_floaters=[f for f in self.salud_floaters if f["t"]>0]
        if not self.final and self.tiempo<=0 and self.salud>0:
            self.final="BALANCE LOGRADO";self.victoria=True
            self.estrellas=1+int(self.salud>=60)+int(self.salud>=85)

    def _draw_fondo(self,s):
        if self.fondo:s.blit(self.fondo,(0,0))
        else:s.fill((248,227,241))
        tinte=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA)
        pygame.draw.rect(tinte,(157,91,191,24),(0,0,ANCHO//2,ALTO));pygame.draw.rect(tinte,(77,169,220,22),(ANCHO//2,0,ANCHO//2,ALTO));s.blit(tinte,(0,0))
        pygame.draw.line(s,(119,111,144),(ANCHO//2,130),(ANCHO//2,ALTO-120),2)
        # destellos suaves ligeros sobre el fondo existente
        for i in range(22):
            x=(i*173+int(self.elapsed*13))%(ANCHO-100)+50;y=250+(i*97)%490
            a=55+int(35*(1+math.sin(self.elapsed*1.5+i)))
            pygame.draw.circle(s,(255,255,255),(x,y),3+(i%3),0)

    def _draw_balance(self,s):
        x,y=960,186;dif=max(-1,min(1,(self.negatividad-self.positividad)/60));angle=dif*20
        pygame.draw.circle(s,(255,247,235),(x,y),54);pygame.draw.circle(s,(99,74,94),(x,y),54,3)
        pygame.draw.line(s,(90,66,92),(x-92,y+12),(x+92,y-12),8)
        pygame.draw.polygon(s,(208,162,90),[(x-26,y+40),(x+26,y+40),(x,y+3)])
        texto(s,"BALANCE",(x,y+69),20,(79,65,89),True)
        for side,c in [(-1,COLOR_MORADO),(1,COLOR_AZUL)]:pygame.draw.circle(s,c,(x+side*80,y-int(dif*12)),12)

    def _draw_barras(self,s):
        for key,x,val,color in (("barra_negatividad",40,self.negatividad,COLOR_MORADO),("barra_positividad",ANCHO-40-152,self.positividad,COLOR_AZUL)):
            data=self.barras.get(key)
            if not data:continue
            frame,inside=data;dest=(x,300);iw,ih=inside.size
            fill_h=int(ih*min(1,val/100));local=pygame.Rect(inside.x,inside.y+ih-fill_h,iw,fill_h)
            surface=pygame.Surface(frame.get_size(),pygame.SRCALPHA)
            if fill_h:
                pygame.draw.rect(surface,(*color,230),local,border_radius=12)
                shine=pygame.Surface((iw,max(1,fill_h//3)),pygame.SRCALPHA);shine.fill((255,255,255,58))
                surface.blit(shine,(local.x,local.y))
            s.blit(surface,(x,dest[1]));s.blit(frame,(x,dest[1]))
            # El marco conserva el tubo original de la hoja de sprites.

    def _draw_sprite(self,s,nombre,center,size=None,angle=0):
        sprite=self.sprites.get(nombre)
        if sprite is None:return
        if size:
            scale=max(1.0,size/max(sprite.get_width(),sprite.get_height()))
            target=(max(1,int(sprite.get_width()*scale)),max(1,int(sprite.get_height()*scale)))
            sprite=pygame.transform.smoothscale(sprite,target)
        if angle:sprite=pygame.transform.rotate(sprite,angle)
        s.blit(sprite,sprite.get_rect(center=(int(center[0]),int(center[1]))))

    def _draw_items(self,s):
        for item in self.items:
            kind=item["kind"];size=item["size"]
            angle=item["angle"] if kind=="emoji_pulgar_abajo" else 0
            if kind=="mitad_rota":
                half=item["half"];scale=1.18;img=pygame.transform.smoothscale(half,(int(half.get_width()*scale),int(half.get_height()*scale)))
                s.blit(img,img.get_rect(center=(int(item["x"]),int(item["y"]))))
            elif item.get("mega"):
                self._draw_sprite(s,kind,(item["x"],item["y"]),size=255)
                for n in range(item["hp"]):pygame.draw.circle(s,(255,233,193),(int(item["x"]-25+n*25),int(item["y"])),7)
                halo=pygame.Surface((310,310),pygame.SRCALPHA);pygame.draw.circle(halo,(206,70,75,45),(155,155),145,12);s.blit(halo,(item["x"]-155,item["y"]-155))
            else:self._draw_sprite(s,kind,(item["x"],item["y"]),size=size,angle=angle)

    def _draw_manos(self,s):
        for i,(x,base,color) in enumerate(((self.manos[0],self.mano_morada,COLOR_MORADO),(self.manos[1],self.mano_azul,COLOR_AZUL))):
            if base is None:continue
            pulse=self.pulso[i];escala=1+0.10*math.sin(pulse*math.pi/.22) if pulse else 1
            img=base
            if escala!=1:img=pygame.transform.smoothscale(base,(int(base.get_width()*escala),int(base.get_height()*escala)))
            img=pygame.transform.rotate(img,-self.direccion[i]*8)
            if self.combo>=5:
                halo=pygame.Surface((img.get_width()+38,img.get_height()+38),pygame.SRCALPHA);pygame.draw.ellipse(halo,(*color,65),(0,0,halo.get_width(),halo.get_height()),10);s.blit(halo,halo.get_rect(center=(int(x),ALTO-172)))
            s.blit(img,img.get_rect(midbottom=(int(x),ALTO-54)))

    def _draw_efectos(self,s):
        if self.screen_shake>0:
            delta=int(8*self.screen_shake/.32);offset=(random.randint(-delta,delta),random.randint(-delta,delta))
            # Temblor contenido: los márgenes no desplazan el HUD fuera del lienzo.
            overlay=s.copy();s.fill((248,239,247));s.blit(overlay,offset)
        for p in self.particulas:
            alpha=max(20,min(240,int(255*p["t"])));pygame.draw.circle(s,(*p["color"],alpha),(int(p["x"]),int(p["y"])),max(1,p["r"]))
        for g in self.grietas:
            x,y=int(g["x"]),int(g["y"]);pygame.draw.lines(s,(102,66,79),False,[(x,y),(x-28,y-22),(x-15,y-53),(x-42,y-79)],4);pygame.draw.lines(s,(102,66,79),False,[(x-15,y-53),(x+13,y-67),(x+20,y-101)],3)
        if self.avisos:
            a=self.avisos[-1];r=pygame.Rect(585,236,750,60);panel(s,r,a["color"],(101,72,92),14,3);texto(s,a["texto"],r.center,26,(75,46,77),True)
        if self.wave_left>0 and self.wave_label:
            texto(s,self.wave_label,(960,255),27,(151,52,75),True)

    def draw(self,s,mouse=(960,540)):
        self._draw_fondo(s)
        # Título original y HUD conservan margen seguro de 40 px.
        titulo=self.decoracion.get("titulo")
        if titulo:
            img=pygame.transform.smoothscale(titulo,(680,80));s.blit(img,(48,24))
        pygame.draw.rect(s,(255,249,238),(760,26,520,76),border_radius=20);pygame.draw.rect(s,(99,75,95),(760,26,520,76),3,border_radius=20)
        texto(s,f"TIEMPO  {int(self.tiempo//60):02}:{int(self.tiempo%60):02}",(900,64),30,(72,56,82),True)
        texto(s,f"PUNTAJE  {self.puntos}",(1144,64),30,(72,56,82),True)
        panel(s,pygame.Rect(1370,28,510,70),(255,248,235),(99,75,95),18,3)
        texto(s,f"ÁNIMO x2  {self.animo_activo:.0f}s" if self.animo_activo>0 else "¡A JUGAR!",(1625,63),26,(66,65,91),True)
        self._draw_balance(s);self._draw_barras(s);self._draw_items(s);self._draw_manos(s)
        # Tarjetas originales de controles quedan abajo dentro del margen.
        for k,x in (("tarjeta_mano_izq",45),("tarjeta_mano_der",ANCHO-45-168)):
            img=self.decoracion.get(k)
            if img:s.blit(pygame.transform.smoothscale(img,(168,190)),(x,ALTO-226))
        # Medidor independiente: la salud solo cambia con capturas y escapes.
        x,y,w,h=690,898,560,42
        pulso=1+int(3*math.sin(self.elapsed*9)) if self.salud<25 else 0
        panel(s,pygame.Rect(x-pulso,y-pulso,w+2*pulso,h+2*pulso),(255,248,235),(225,83,102) if self.salud<25 else (98,76,98),16,3+bool(pulso))
        pygame.draw.rect(s,(76,74,99),(x+14,y+13,w-62,17),border_radius=8)
        relleno=round((w-62)*max(0,min(100,self.salud_visual))/100)
        color=(92,197,150) if self.salud_visual>35 else (225,83,102)
        if relleno:pygame.draw.rect(s,color,(x+14,y+13,relleno,17),border_radius=8)
        if self.salud_flash>0 and relleno:
            glow=pygame.Surface((relleno,17),pygame.SRCALPHA);glow.fill((*self.salud_flash_color,int(105*self.salud_flash/.65)));s.blit(glow,(x+14,y+13))
        texto(s,f"SALUD MENTAL  {round(self.salud_visual)}%",(x+w//2-18,y-20),26,(66,65,91),True)
        cara="emoji_triste" if self.salud_visual<30 else "emoji_sonriente" if self.salud_visual>70 else "emoji_cara_azul"
        cara_img=self.sprites[cara]
        s.blit(pygame.transform.scale(cara_img,(40,40)),cara_img.get_rect(center=(x+w-19,y+h//2)))
        if self.salud_floaters:
            f=self.salud_floaters[-1];alpha=max(0,min(255,round(255*f["t"])));lab=fuente(30,True).render(f["texto"],True,self.salud_flash_color)
            lab.set_alpha(alpha);s.blit(lab,(x+14+relleno,y-12-round((1-f["t"])*28)))
        pygame.draw.rect(s,(76,74,99),(x+6,846,w-12,10),border_radius=5)
        pygame.draw.rect(s,(90,155,210),(x+6,846,round((w-12)*self.tiempo/DURACION),10),border_radius=5)
        if self.animo_activo>0:texto(s,f"ÁNIMO A TOPE · PUNTOS x2 · {self.animo_activo:.0f}s",(960,817),25,(54,139,82),True)
        self._draw_efectos(s)
        if self.pausa:self.rects=menu_pausa(s,["Continuar","Reiniciar","Salir"],self.sel,cursor=mouse)
        if self.final:
            balance="equilibrado" if abs(self.negatividad-self.positividad)<=UMBRAL_BALANCE else "desbalanceado"
            pantalla_final(s,"PERFIL DE ÁNIMO · "+self.final,[f"Puntaje: {self.puntos}  |  Mejor racha: {self.mejor_racha}",f"Positividad {self.positividad}%  ·  Negatividad {self.negatividad}%  ·  {balance}",f"Salud mental restante: {self.salud}%", f"{self.estrellas} ESTRELLAS · salud final {self.salud}%"])

    def run(self):
        ventana=VentanaVirtual("Emoji Catch: Balance!");clock=pygame.time.Clock();running=True
        while running:
            dt=min(clock.tick(FPS)/1000,.05);eventos=pygame.event.get();acciones=leer_entrada(eventos,ventana)
            for e in eventos:ventana.manejar_evento(e)
            if acciones["salir"]:break
            if self.final and pygame.K_r in acciones["teclas"]:self.reiniciar()
            elif pygame.K_ESCAPE in acciones["teclas"] and not self.final:self.pausa=not self.pausa
            elif self.pausa:
                if pygame.K_UP in acciones["teclas"]:self.sel=(self.sel-1)%3
                if pygame.K_DOWN in acciones["teclas"]:self.sel=(self.sel+1)%3
                if pygame.K_RETURN in acciones["teclas"]:
                    if self.sel==0:self.pausa=False
                    elif self.sel==1:self.reiniciar()
                    else:running=False
                if acciones["click"]:
                    for i,r in enumerate(self.rects):
                        if r.collidepoint(acciones["click"]):
                            if i==0:self.pausa=False
                            elif i==1:self.reiniciar()
                            else:running=False
            else:self.update(dt,acciones["held"])
            self.draw(ventana.canvas,acciones["mouse"]);ventana.presentar((249,229,239))
        pygame.quit()

if __name__=="__main__":EmojiCatch().run()


