"""Emoji Catch: dos manos equilibran el feed durante dos minutos."""
import random
import pygame
from comun import ANCHO, ALTO, FPS, RAIZ, cargar_imagen, texto, panel, leer_entrada, menu_pausa, pantalla_final

DURACION = 120.0
SALUD_INICIAL = 100
DIFERENCIA_MAXIMA = 24
VEL_MIN, VEL_MAX = 210, 390
NEGATIVOS = ["😠", "🤢", "😢", "😵", "💔", "👎"]
POSITIVOS = ["😊", "❤️", "👍", "💰", "⭐"]


def cara(s, x, y, tipo):
    """Emoji dibujado: no usa fuentes de emoji del sistema."""
    r = 28
    color = (255, 192, 75) if tipo in NEGATIVOS[:4] or tipo == "😊" else (245, 205, 68)
    if tipo == "❤️":
        pygame.draw.polygon(s, (231, 61, 105), [(x-r,y),(x-r,y-12),(x-10,y-12),(x,y),(x+10,y-12),(x+r,y-12),(x+r,y),(x,y+r)])
        return
    pygame.draw.circle(s, (96, 77, 81), (x, y), r+3)
    pygame.draw.circle(s, color, (x, y), r)
    if tipo in ("💰", "⭐", "👍", "👎", "💔"):
        mark = {"💰":"$", "⭐":"★", "👍":"+", "👎":"−", "💔":"♡"}[tipo]
        texto(s, mark, (x,y), 34, (93,65,35), centro=True, negrita=True); return
    # ojos y gesto básico
    pygame.draw.circle(s, (75, 55, 53), (x-9,y-6), 3); pygame.draw.circle(s, (75,55,53), (x+9,y-6), 3)
    if tipo == "😠":
        pygame.draw.line(s,(75,45,45),(x-17,y-15),(x-5,y-11),3); pygame.draw.line(s,(75,45,45),(x+17,y-15),(x+5,y-11),3)
    if tipo in ("😢", "🤢", "😵"): pygame.draw.arc(s,(85,48,52),(x-10,y+5,20,14),0,3.14,3)
    else: pygame.draw.arc(s,(85,48,52),(x-11,y-2,22,18),3.14,6.28,3)


class EmojiCatch:
    def __init__(self): self.reiniciar()
    def reiniciar(self):
        self.tiempo=DURACION; self.vida=SALUD_INICIAL; self.neg=0; self.pos=0; self.puntos=0
        self.manos=[ANCHO*.34, ANCHO*.66]; self.items=[]; self.spawn=0; self.mensaje=""; self.mensaje_t=0
        self.final=""; self.pausa=False; self.sel=0; self.fx=[]
        self.fondo=cargar_imagen("fondo_concentracion_microjuego.png", (ANCHO,ALTO), False)
    def update(self, dt, keys):
        if self.pausa or self.final: return
        self.tiempo=max(0,self.tiempo-dt)
        velocidad=620
        for i,(izq,der) in enumerate(((pygame.K_a,pygame.K_d),(pygame.K_j,pygame.K_l))):
            if keys[izq]: self.manos[i]-=velocidad*dt
            if keys[der]: self.manos[i]+=velocidad*dt
            self.manos[i]=max(70,min(ANCHO-70,self.manos[i]))
        self.spawn-=dt
        if self.spawn<=0:
            tipo=random.choice(NEGATIVOS+POSITIVOS); x=random.randint(105,ANCHO-105)
            self.items.append([float(x),-45.0,tipo,random.uniform(VEL_MIN,VEL_MAX)*(1+(DURACION-self.tiempo)/170)])
            self.spawn=random.uniform(.38,.8)*max(.45,1-(DURACION-self.tiempo)/220)
        for it in self.items: it[1]+=it[3]*dt
        kept=[]
        for it in self.items:
            x,y,tipo,_=it; destino=0 if tipo in NEGATIVOS else 1
            # Recogida por la mano más cercana, ventanas amplias pero no automáticas.
            captura=y>ALTO-300 and abs(x-self.manos[destino])<92
            captura_otro=y>ALTO-300 and abs(x-self.manos[1-destino])<76
            if captura or captura_otro:
                correcta=captura and not captura_otro
                if correcta:
                    self.puntos+=10; self.neg+=2 if destino==0 else 0; self.pos+=2 if destino==1 else 0
                    if destino==0: self.mensaje="¡USUARIO BLOQUEADO!"
                else: self.puntos=max(0,self.puntos-12); self.vida=max(0,self.vida-12)
                self.mensaje_t=1.15; self.fx.append([x,y,0.45,correcta]); continue
            if y>ALTO-100:
                if tipo in NEGATIVOS: self.vida=max(0,self.vida-12); self.fx.append([x,ALTO-85,.8,False])
                continue
            kept.append(it)
        self.items=kept
        self.fx=[[x,y,t-dt,ok] for x,y,t,ok in self.fx if t>dt]
        if self.mensaje_t>0:self.mensaje_t-=dt
        if self.vida<=0:self.final="DERROTA"
        elif self.tiempo<=0:self.final="BALANCE" if abs(self.neg-self.pos)<=DIFERENCIA_MAXIMA else "BALANCE ROTO"
    def draw(self,s):
        if self.fondo:s.blit(self.fondo,(0,0))
        else:
            s.fill((249,231,239))
            for i in range(30): pygame.draw.circle(s,(255,255,255),(i*67%ANCHO,i*113%ALTO),3)
        pygame.draw.rect(s,(255,246,239),(0,0,ANCHO,112)); pygame.draw.line(s,(127,93,114),(0,112),(ANCHO,112),3)
        texto(s,"EMOJI CATCH: BALANCE!",(ANCHO//2,53),44,(84,59,94),True)
        texto(s,f"TIEMPO  {int(self.tiempo//60):02}:{int(self.tiempo%60):02}",(ANCHO//2,142),30,(48,47,71),True)
        texto(s,f"PUNTAJE  {self.puntos}",(ANCHO-270,145),30,(44,66,104))
        # barras verticales laterales
        for x,label,val,color in ((50,"NEGATIVIDAD",self.neg,(142,72,194)),(ANCHO-82,"POSITIVIDAD",self.pos,(54,153,225))):
            pygame.draw.rect(s,(255,255,255),(x,260,34,540),border_radius=17); pygame.draw.rect(s,color,(x,260+540*(1-min(100,val)/100),34,540*min(100,val)/100),border_radius=17)
            pygame.draw.rect(s,(65,57,82),(x,260,34,540),3,border_radius=17)
            label_img=pygame.transform.rotate(pygame.font.Font(None,28).render(label,True,color),90)
            s.blit(label_img,(x-40 if x<100 else x+40,420))
        for _,(x,_) in enumerate([(0,0)]): pass
        for x,y,tipo,vel in self.items: cara(s,int(x),int(y),tipo)
        for x,y,t,ok in self.fx:
            if not ok:
                pygame.draw.line(s,(85,45,54),(x-32,y-30),(x+25,y+24),5); pygame.draw.line(s,(85,45,54),(x+25,y-30),(x-32,y+24),4)
        # Guantes esquemáticos, con zonas completas de movimiento horizontal
        for x,color,tag in ((self.manos[0],(128,73,184),"A — D"),(self.manos[1],(54,139,212),"J — L")):
            pygame.draw.ellipse(s,(243,205,181),(int(x-42),ALTO-145,84,115)); pygame.draw.ellipse(s,color,(int(x-71),ALTO-245,142,125)); pygame.draw.circle(s,color,(int(x-54),ALTO-264),25); pygame.draw.circle(s,color,(int(x-20),ALTO-280),24); pygame.draw.circle(s,color,(int(x+16),ALTO-281),24); pygame.draw.circle(s,color,(int(x+51),ALTO-264),23)
            pygame.draw.rect(s,(255,246,236),(int(x-95),ALTO-105,190,62),border_radius=10); texto(s,tag,(int(x),ALTO-74),26,(63,54,77),True)
        panel(s,pygame.Rect(115,ALTO-108,330,70)); texto(s,"MANO IZQ  TECLADO A-D",(280,ALTO-73),22,centro=True)
        panel(s,pygame.Rect(ANCHO-445,ALTO-108,330,70)); texto(s,"MANO DER  TECLADO J-L",(ANCHO-280,ALTO-73),22,centro=True)
        panel(s,pygame.Rect(ANCHO//2-190,ALTO-91,380,52),(255,255,255)); texto(s,f"SALUD MENTAL  {self.vida}%",(ANCHO//2,ALTO-65),24,centro=True)
        if self.mensaje_t>0: panel(s,pygame.Rect(ANCHO//2-225,190,450,58),(255,237,206)); texto(s,self.mensaje,(ANCHO//2,219),25,(122,48,76),True)
        if self.pausa:
            rects=menu_pausa(s,["Continuar","Reiniciar","Salir"],self.sel); self.rects=rects
        if self.final: pantalla_final(s,"¡"+self.final+"!",[f"Puntaje: {self.puntos}",f"Salud mental: {self.vida}%",f"Negatividad {self.neg}  |  Positividad {self.pos}","El balance requiere salud y barras equilibradas."])
    def run(self):
        pygame.init(); s=pygame.display.set_mode((ANCHO,ALTO)); pygame.display.set_caption("Emoji Catch: Balance!"); clock=pygame.time.Clock(); running=True
        while running:
            dt=min(clock.tick(FPS)/1000,0.05); ev=pygame.event.get(); a=leer_entrada(ev)
            if a["salir"]:break
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
            else:self.update(dt,a["held"])
            self.draw(s); pygame.display.flip()
        pygame.quit()

if __name__=="__main__": EmojiCatch().run()
