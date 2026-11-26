"""Emoji Catch: captura el feed con dos manos y conserva el balance."""
import math
import random
import pygame
from microgames.redes_comun import ANCHO, ALTO, FPS, RAIZ, cargar_imagen, cargar_sprite, revisar_recursos, texto, fuente, panel, load_managed_sound
from microgames.redes_comun import TINTA, barra_acuarela, cartel, circulo_acuarela, sprite_opcional, texto_con_contorno

# Efecto al bloquear un emoji negativo.
SFX_BLOQUEO = "emoji_bloqueo.mp3"

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
POSITIVOS = ("emoji_sonriente", "emoji_cara_azul", "emoji_corazon", "emoji_pulgar_arriba", "emoji_bolsa_dinero", "emoji_estrellas", "emoji_angel")
ALTO_MANO = 270  # Alto en pantalla de las manos acuarela
SPRITES = (*NEGATIVOS, *POSITIVOS)

COMENTARIOS_HATER = (
    ("@troll_baq", "¿Y esa pinta qué?"),
    ("@hater_84", "Nadie ve tu live..."),
    ("@envidia_00", "Puro relleno eso"),
    ("@anonimo_x", "Bloquéate solo mejor"),
    ("@criticon", "Qué stream tan malo"),
    ("@malavibra", "Dedícate a otra cosa"),
)
COMENTARIOS_APOYO = (
    ("@prado_fan", "¡Tú puedes, mi llave!"),
    ("@soledad_ok", "Qué buen contenido"),
    ("@currambera", "Saludos desde el Prado"),
    ("@la_arenosa", "Buena vibra siempre"),
    ("@vecino_baq", "¡Crack, sigue así!"),
    ("@buenavista", "Qué bacano el live"),
)


def tiene_tecla(teclas, codigo):
    """Permite usar tanto el vector de teclas sostenidas como eventos inyectados."""
    try:
        return bool(teclas[codigo])
    except (TypeError, IndexError, KeyError):
        return codigo in teclas


class EmojiCatch:
    # Ajustes para cuando el juego corre dentro de BarranquillaWare (microgames/emoji_catch.py).
    MOSTRAR_BARRA_TIEMPO_PROPIA = False  # La barra de tiempo acuarela común la reemplaza

    def __init__(self):
        revisar_recursos("emoji_catch")
        fondo_propio = RAIZ / "assets/emoji_catch/fondo_emoji_catch.png"
        if fondo_propio.is_file():
            self.fondo = pygame.transform.smoothscale(pygame.image.load(str(fondo_propio)).convert(), (ANCHO, ALTO))
        else:
            self.fondo = cargar_imagen("fondo_concentracion_microjuego.png", (ANCHO, ALTO), alpha=False)
        self.marco_live = sprite_opcional("marco_live.png", "emoji")
        self.avatares = {
            k: sprite_opcional(f"avatar_{k}.png", "emoji")
            for k in ("feliz", "neutral", "estresado")
        }
        self.sprites = {n: cargar_sprite(f"{n}.png", "emoji") for n in SPRITES}
        self.decoracion = {n: cargar_sprite(f"{n}.png", "emoji") for n in (
            "titulo", "tiempo", "tarjeta_mano_izq", "tarjeta_mano_der", "barra_negatividad", "barra_positividad", "mano_morada", "mano_azul_der")}
        a_alto = lambda img: pygame.transform.smoothscale_by(img, ALTO_MANO / img.get_height()) if img else None
        self.mano_morada = a_alto(self.decoracion["mano_morada"])
        self.mano_azul = a_alto(self.decoracion["mano_azul_der"])
        # Al atrapar, la mano se cierra en puño (arte acuarela; opcional).
        self.puno = [a_alto(cargar_sprite(f"{n}.png", "emoji")) if (RAIZ / "assets/emoji_catch" / f"{n}.png").is_file() else None
                     for n in ("mano_morada_puno", "mano_azul_puno")]
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
        # La música la pone el microjuego (AudioManager); aquí solo el efecto de bloqueo.
        self.sonido_bloqueo = load_managed_sound(SFX_BLOQUEO, 0.6)

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
        self.chat_feed=[];self.chat_clock=1.2;self.hand_floaters=[];self.viewers=1240

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

    def _push_chat(self, negativo):
        user, msg = random.choice(COMENTARIOS_HATER if negativo else COMENTARIOS_APOYO)
        self.chat_feed.append({"user": user, "texto": msg, "negativo": negativo, "t": 4.2})
        if len(self.chat_feed) > 2:
            self.chat_feed.pop(0)

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
            self._push_chat(True)
            self.mega_clock=random.uniform(21,26)
        self.chat_clock-=dt
        if self.chat_clock<=0:
            neg = True if self.wave_kind=="raid" else False if self.wave_kind=="trend" else random.choice((True, False))
            self._push_chat(neg)
            self.chat_clock=random.uniform(3.0, 4.6)

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
            self.hand_floaters.append({"x":item["x"],"y":item["y"]-28,"texto":f"BLOQUEADO +{score}","color":(225,180,255),"t":0.9})
        else:
            self._aviso(f"+{score} pts"+(f"  COMBO x{mult}" if mult>1 else ""),(226,243,255))
            self.hand_floaters.append({"x":item["x"],"y":item["y"]-28,"texto":f"¡APOYO! +{score}","color":(180,235,255),"t":0.9})
            self.viewers+=random.randint(3,12)
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
        for cf in self.chat_feed:cf["t"]-=dt
        self.chat_feed=[c for c in self.chat_feed if c["t"]>0]
        for hf in self.hand_floaters:hf["t"]-=dt;hf["y"]-=55*dt
        self.hand_floaters=[h for h in self.hand_floaters if h["t"]>0]
        if not self.final and self.tiempo<=0 and self.salud>0:
            self.final="BALANCE LOGRADO";self.victoria=True
            self.estrellas=1+int(self.salud>=60)+int(self.salud>=85)

    def _draw_fondo(self,s):
        if self.fondo:s.blit(self.fondo,(0,0))
        else:s.fill((248,227,241))
        tinte=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA)
        pygame.draw.rect(tinte,(157,91,191,18),(0,0,ANCHO//2,ALTO));pygame.draw.rect(tinte,(77,169,220,16),(ANCHO//2,0,ANCHO//2,ALTO))
        pygame.draw.line(tinte,(119,111,144,65),(ANCHO//2,140),(ANCHO//2,ALTO-110),2)
        s.blit(tinte,(0,0))
        # destellos suaves ligeros sobre el fondo existente
        for i in range(22):
            x=(i*173+int(self.elapsed*13))%(ANCHO-100)+50;y=250+(i*97)%490
            a=55+int(35*(1+math.sin(self.elapsed*1.5+i)))
            pygame.draw.circle(s,(255,255,255),(x,y),3+(i%3),0)

    def _draw_balance(self,s):
        x,y=960,175;dif=max(-1,min(1,(self.negatividad-self.positividad)/60))
        propio=sprite_opcional("balanza.png","emoji")
        if propio is not None:
            img=pygame.transform.smoothscale_by(propio,190/max(propio.get_size()));img=pygame.transform.rotate(img,-dif*14)
            s.blit(img,img.get_rect(center=(x,y)))
        else:
            fondo=circulo_acuarela(124,(250,240,226));s.blit(fondo,fondo.get_rect(center=(x,y)))
            brazo=(x-92,y+12-int(dif*14)),(x+92,y-12+int(dif*14))
            pygame.draw.line(s,TINTA,brazo[0],brazo[1],9)
            pygame.draw.polygon(s,(214,160,92),[(x-26,y+44),(x+26,y+44),(x,y+3)]);pygame.draw.polygon(s,TINTA,[(x-26,y+44),(x+26,y+44),(x,y+3)],3)
            for (px,py),c in zip(brazo,(COLOR_MORADO,COLOR_AZUL)):
                bola=circulo_acuarela(30,c);s.blit(bola,bola.get_rect(center=(px,py)))
        texto_con_contorno(s,"Balance",(x,y+72),22,(255,247,230),TINTA,centro=True,grosor=2)

    def _draw_barras(self,s):
        for label,x,val,color in (("NEG",36,self.negatividad,COLOR_MORADO),("POS",ANCHO-54,self.positividad,COLOR_AZUL)):
            y,w,h=280,18,240
            fondo=pygame.Surface((w,h),pygame.SRCALPHA)
            pygame.draw.rect(fondo,(250,242,230,170),(0,0,w,h),border_radius=9)
            fill_h=int(h*min(1,val/100))
            if fill_h:
                pygame.draw.rect(fondo,(*color,230),(2,h-fill_h+2,w-4,max(1,fill_h-4)),border_radius=7)
            pygame.draw.rect(fondo,TINTA,(0,0,w,h),2,border_radius=9)
            s.blit(fondo,(x,y))
            texto_con_contorno(s,label,(x+w//2,y-18),18,(255,247,230),TINTA,centro=True,grosor=2)

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
            if pulse and self.puno[i] is not None:base=self.puno[i]
            img=base
            if escala!=1:img=pygame.transform.smoothscale(base,(int(base.get_width()*escala),int(base.get_height()*escala)))
            img=pygame.transform.rotate(img,-self.direccion[i]*8)
            s.blit(img,img.get_rect(midbottom=(int(x),ALTO-54)))

    def _draw_live_hud(self,s):
        if self.marco_live is not None:
            s.blit(pygame.transform.smoothscale(self.marco_live,(ANCHO,min(140,self.marco_live.get_height()))),(0,0))
        # Pill LIVE · CurramGram debajo de la barra de Salud Mental (izquierda)
        live_pill=pygame.Surface((268,32),pygame.SRCALPHA)
        pygame.draw.rect(live_pill,(250,242,232,205),(0,0,268,32),border_radius=16)
        pygame.draw.rect(live_pill,TINTA,(0,0,268,32),2,border_radius=16)
        pulso_rojo=220+int(35*math.sin(self.elapsed*5))
        pygame.draw.circle(live_pill,(pulso_rojo,55,70,240),(18,16),6)
        s.blit(live_pill,(48,178))
        texto_con_contorno(s,f"LIVE · CurramGram · {self.viewers/1000:.1f}k",(190,194),17,(255,247,230),TINTA,centro=True,grosor=2)
        # Mini-chat del feed arriba a la derecha (debajo del puntaje, sin tapar caída)
        cy=124
        for c in self.chat_feed:
            alpha=min(230,int(230*min(1.0,c["t"])))
            borde=COLOR_MORADO if c["negativo"] else COLOR_AZUL
            box=pygame.Surface((430,44),pygame.SRCALPHA)
            pygame.draw.rect(box,(252,246,238,alpha),(0,0,430,44),border_radius=14)
            pygame.draw.rect(box,(*borde,alpha),(0,0,430,44),2,border_radius=14)
            u_surf=fuente(17,True).render(c["user"],True,borde)
            m_surf=fuente(17,False).render(c["texto"],True,TINTA)
            u_surf.set_alpha(alpha);m_surf.set_alpha(alpha)
            box.blit(u_surf,(14,5));box.blit(m_surf,(14,22))
            s.blit(box,(ANCHO-478,cy))
            cy+=50

    def _draw_efectos(self,s):
        if self.screen_shake>0:
            delta=int(8*self.screen_shake/.32);offset=(random.randint(-delta,delta),random.randint(-delta,delta))
            # Temblor contenido: los márgenes no desplazan el HUD fuera del lienzo.
            overlay=s.copy();s.fill((248,239,247));s.blit(overlay,offset)
        for p in self.particulas:
            alpha=max(20,min(240,int(255*p["t"])));pygame.draw.circle(s,(*p["color"],alpha),(int(p["x"]),int(p["y"])),max(1,p["r"]))
        for hf in self.hand_floaters:
            texto_con_contorno(s,hf["texto"],(int(hf["x"]),int(hf["y"])),22,hf["color"],TINTA,centro=True,grosor=2)
        if self.avisos:
            a=self.avisos[-1];texto_con_contorno(s,a["texto"],(960,295),28,(255,247,230),TINTA,centro=True,grosor=3)
        if self.wave_left>0 and self.wave_label and not self.avisos:
            texto_con_contorno(s,self.wave_label,(960,295),30,(255,210,225),TINTA,centro=True,grosor=3)

    def draw(self,s,mouse=(960,540)):
        self._draw_fondo(s)
        # Título original y HUD conservan margen seguro de 40 px.
        titulo=self.decoracion.get("titulo")
        if titulo:
            img=pygame.transform.smoothscale(titulo,(680,80));s.blit(img,(48,24))
        # La barra de tiempo común va arriba al centro (TIME_BAR_LAYOUT del minijuego).
        estado=f"Ánimo x2 · {self.animo_activo:.0f}s" if self.animo_activo>0 else "¡A jugar!"
        cartel(s,f"Puntaje {self.puntos}  ·  {estado}",(1625,64),520,80,(140,205,120) if self.animo_activo>0 else None,32)
        self._draw_balance(s);self._draw_barras(s);self._draw_live_hud(s);self._draw_items(s);self._draw_manos(s)
        # Badges limpios de controles y rol en las esquinas inferiores.
        for label,color,cx in (("A / D · BLOQUEAR",COLOR_MORADO,148),("J / L · APOYAR",COLOR_AZUL,ANCHO-148)):
            pill=pygame.Surface((220,38),pygame.SRCALPHA)
            pygame.draw.rect(pill,(*color,215),(0,0,220,38),border_radius=19)
            pygame.draw.rect(pill,TINTA,(0,0,220,38),2,border_radius=19)
            s.blit(pill,pill.get_rect(center=(cx,ALTO-42)))
            texto_con_contorno(s,label,(cx,ALTO-42),20,(255,255,255),TINTA,centro=True,grosor=2)
        # Medidor independiente: la salud solo cambia con capturas y escapes.
        x,y,w,h=48,136,380,32
        pulso=1+int(3*math.sin(self.elapsed*9)) if self.salud<25 else 0
        relleno=round((w-62)*max(0,min(100,self.salud_visual))/100)
        color=(230,105,130) if self.salud_visual>35 else (225,65,85)
        barra_acuarela(s,pygame.Rect(x-pulso,y-pulso,w-50+2*pulso,h+2*pulso),self.salud_visual/100,color)
        if self.salud_flash>0 and relleno:
            glow=pygame.Surface((relleno,14),pygame.SRCALPHA);glow.fill((*self.salud_flash_color,int(90*self.salud_flash/.65)));s.blit(glow,(x+16,y+h//2-7))
        texto_con_contorno(s,f"Salud mental  {round(self.salud_visual)}%",(x+w//2-25,y-16),22,(255,247,230),TINTA,centro=True,grosor=2)
        estado_av="estresado" if self.salud_visual<30 else "feliz" if self.salud_visual>70 else "neutral"
        avatar_custom=self.avatares.get(estado_av)
        if avatar_custom is not None:
            cara_img=pygame.transform.smoothscale(avatar_custom,(46,46))
        else:
            cara="emoji_triste" if estado_av=="estresado" else "emoji_sonriente" if estado_av=="feliz" else "emoji_cara_azul"
            cara_img=pygame.transform.smoothscale(self.sprites[cara],(40,40))
        s.blit(cara_img,cara_img.get_rect(center=(x+w-14,y+h//2)))
        if self.salud_floaters:
            f=self.salud_floaters[-1];alpha=max(0,min(255,round(255*f["t"])));lab=fuente(24,True).render(f["texto"],True,self.salud_flash_color)
            lab.set_alpha(alpha);s.blit(lab,(x+14+relleno,y+h+4+round((1-f["t"])*16)))
        if self.MOSTRAR_BARRA_TIEMPO_PROPIA:
            pygame.draw.rect(s,(76,74,99),(700,78,520,10),border_radius=5)
            pygame.draw.rect(s,(90,155,210),(700,78,round(520*self.tiempo/DURACION),10),border_radius=5)
        if self.animo_activo>0:texto_con_contorno(s,f"¡Ánimo a tope! Puntos x2 · {self.animo_activo:.0f}s",(960,ALTO-42),28,(214,255,204),TINTA,centro=True,grosor=3)
        self._draw_efectos(s)
